# tests/test_heti_orzo.py
from datetime import datetime, timezone
import json

from trendfigyelo import heti_orzo as ho


def _bp(y, m, d, h):   # budapesti falióra → UTC-aware datetime (a seged.esti_nap BP-re számol)
    from zoneinfo import ZoneInfo
    return datetime(y, m, d, h, tzinfo=ZoneInfo("Europe/Budapest")).astimezone(timezone.utc)


def test_hetfo_e():
    assert ho.hetfo_e(_bp(2026, 10, 5, 9)) is True       # 2026-10-05 hétfő
    assert ho.hetfo_e(_bp(2026, 10, 6, 9)) is False      # kedd


def test_elozo_het_hetfoje():
    # hétfő reggel → az ELŐZŐ (lezárult) hét hétfője = egy héttel korábbi hétfő
    assert ho.elozo_het_hetfo(_bp(2026, 10, 5, 9)) == "2026-09-28"


def test_hajnali_hetfo_az_elozo_estehez_sorolodik_de_meg_hetfo():
    # 2026-10-05 01:00 BP → esti_nap = 2026-10-04 (vasárnap) → NEM hétfő → skip
    assert ho.hetfo_e(_bp(2026, 10, 5, 1)) is False


def test_kell_generalni_nem_hetfon_none(tmp_path):
    assert ho.kell_generalni(str(tmp_path), _bp(2026, 10, 6, 9)) is None


def test_kell_generalni_hetfon_az_elozo_hetet(tmp_path):
    assert ho.kell_generalni(str(tmp_path), _bp(2026, 10, 5, 9)) == "2026-09-28"


def test_idempotencia_ma_mar_kesz_skip(tmp_path):
    (tmp_path / "heti").mkdir(parents=True)
    # a keszult LOGIKAI napja 2026-10-05 (hétfő reggel) → ma már kész → skip
    (tmp_path / "heti" / "2026-09-28.json").write_text(
        json.dumps({"keszult": "2026-10-05T07:00:00+00:00"}), encoding="utf-8")
    assert ho.kell_generalni(str(tmp_path), _bp(2026, 10, 5, 9)) is None


def test_idempotencia_korabbi_keszult_ujra(tmp_path):
    (tmp_path / "heti").mkdir(parents=True)
    (tmp_path / "heti" / "2026-09-28.json").write_text(
        json.dumps({"keszult": "2026-09-30T07:00:00+00:00"}), encoding="utf-8")
    assert ho.kell_generalni(str(tmp_path), _bp(2026, 10, 5, 9)) == "2026-09-28"


def test_main_cli(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(ho.seged, "most_utc", lambda: _bp(2026, 10, 5, 9))
    assert ho.main([str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == "2026-09-28"
