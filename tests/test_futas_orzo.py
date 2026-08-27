"""Az idempotencia-őr (napi gyűjtés fallback-cronjaihoz) döntés-logikája.

A pure `mar_gyujtottunk_ma` a `legfrissebb.json` 'frissitve' dátumát veti össze a
mai UTC-dátummal — ez dönti el, hogy egy ütemezett fallback-futás gyűjtsön-e vagy
némán kilépjen. A pótolhatatlan órás Google-utat érinti → tesztelt döntés.
"""
import json

from trendfigyelo import futas_orzo


def _ir_legfrissebb(tmp_path, frissitve):
    p = tmp_path / "legfrissebb.json"
    p.write_text(json.dumps({"geo": "HU", "frissitve": frissitve}), encoding="utf-8")
    return str(p)


def test_mar_gyujtottunk_ma_ugyanaz_a_datum_true(tmp_path):
    path = _ir_legfrissebb(tmp_path, "2026-08-27T21:47:10+00:00")
    assert futas_orzo.mar_gyujtottunk_ma(path, "2026-08-27") is True


def test_mar_gyujtottunk_ma_tegnapi_datum_false(tmp_path):
    path = _ir_legfrissebb(tmp_path, "2026-08-26T21:47:10+00:00")
    assert futas_orzo.mar_gyujtottunk_ma(path, "2026-08-27") is False


def test_mar_gyujtottunk_ma_kesobbi_ido_ugyanaznap_meg_true(tmp_path):
    path = _ir_legfrissebb(tmp_path, "2026-08-27T23:59:00+00:00")
    assert futas_orzo.mar_gyujtottunk_ma(path, "2026-08-27") is True


def test_hianyzo_fajl_false(tmp_path):
    assert futas_orzo.mar_gyujtottunk_ma(str(tmp_path / "nincs.json"), "2026-08-27") is False


def test_hianyzo_frissitve_mezo_false(tmp_path):
    p = tmp_path / "legfrissebb.json"
    p.write_text(json.dumps({"geo": "HU"}), encoding="utf-8")
    assert futas_orzo.mar_gyujtottunk_ma(str(p), "2026-08-27") is False


def test_frissitve_datuma_helper_elotag(tmp_path):
    path = _ir_legfrissebb(tmp_path, "2026-08-27T21:47:10+00:00")
    assert futas_orzo._frissitve_datuma(path) == "2026-08-27"


def test_main_regi_datum_soha_nem_ma_false(tmp_path, capsys):
    # 2000-01-01 sosem lehet "ma" → a CLI determinisztikusan "false"-t ír (gyűjts).
    path = _ir_legfrissebb(tmp_path, "2000-01-01T00:00:00+00:00")
    rc = futas_orzo.main([path])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "false"
