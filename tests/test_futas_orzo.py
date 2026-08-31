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


# ── YouTube-ág: a jel a youtube_nyers.json kulcsszó-rekordjainak legfrissebb 'lekerdezes_utc'-je ──

def _ir_youtube(tmp_path, kulcsszavak):
    """kulcsszavak: {szó: [lekerdezes_utc, ...]} → youtube_nyers.json a valós alakban."""
    adat = {"kulcsszavak": {
        szo: [{"kulcsszo": szo, "timeframe": "today 3-m", "lekerdezes_utc": lk} for lk in lekerdezesek]
        for szo, lekerdezesek in kulcsszavak.items()
    }}
    p = tmp_path / "youtube_nyers.json"
    p.write_text(json.dumps(adat), encoding="utf-8")
    return str(p)


def test_youtube_mai_lekerdezes_true(tmp_path):
    path = _ir_youtube(tmp_path, {"szorongás": ["2026-08-27T00:17:23.243069+00:00"]})
    assert futas_orzo.youtube_mar_gyujtottunk_ma(path, "2026-08-27") is True


def test_youtube_tegnapi_lekerdezes_false(tmp_path):
    path = _ir_youtube(tmp_path, {"szorongás": ["2026-08-26T16:19:40.811997+00:00"]})
    assert futas_orzo.youtube_mar_gyujtottunk_ma(path, "2026-08-27") is False


def test_youtube_vegyes_datum_a_legfrissebbet_veszi_true(tmp_path):
    # a történet több gyűjtést tart meg; a MAI akkor is számít, ha nem az első/utolsó elem
    path = _ir_youtube(tmp_path, {"szorongás": [
        "2026-08-25T15:31:35+00:00", "2026-08-27T00:17:23+00:00", "2026-08-26T16:19:40+00:00",
    ]})
    assert futas_orzo.youtube_mar_gyujtottunk_ma(path, "2026-08-27") is True


def test_youtube_legfrissebb_masik_kulcsszoban_is_szamit_true(tmp_path):
    # a maximumot MINDEN kulcsszó minden rekordján kell venni, nem csak az elsőn
    path = _ir_youtube(tmp_path, {
        "szorongás": ["2026-08-25T15:31:35+00:00"],
        "bitcoin": ["2026-08-27T00:17:23+00:00"],
    })
    assert futas_orzo.youtube_mar_gyujtottunk_ma(path, "2026-08-27") is True


def test_youtube_hianyzo_fajl_false(tmp_path):
    assert futas_orzo.youtube_mar_gyujtottunk_ma(str(tmp_path / "nincs.json"), "2026-08-27") is False


def test_youtube_ures_kulcsszavak_false(tmp_path):
    p = tmp_path / "youtube_nyers.json"
    p.write_text(json.dumps({"kulcsszavak": {}}), encoding="utf-8")
    assert futas_orzo.youtube_mar_gyujtottunk_ma(str(p), "2026-08-27") is False


def test_youtube_romlott_json_false(tmp_path):
    p = tmp_path / "youtube_nyers.json"
    p.write_text("{nem valós json", encoding="utf-8")
    assert futas_orzo.youtube_mar_gyujtottunk_ma(str(p), "2026-08-27") is False


def test_youtube_utolso_datuma_helper_a_maxot_adja(tmp_path):
    path = _ir_youtube(tmp_path, {
        "szorongás": ["2026-08-25T15:31:35+00:00", "2026-08-27T00:17:23+00:00"],
        "bitcoin": ["2026-08-26T16:19:40+00:00"],
    })
    assert futas_orzo._youtube_utolso_datuma(path) == "2026-08-27"


def test_main_youtube_regi_datum_false(tmp_path, capsys):
    # --youtube kapcsoló a youtube-jelre vált; 2000-01-01 sosem "ma" → "false".
    path = _ir_youtube(tmp_path, {"szorongás": ["2000-01-01T00:00:00+00:00"]})
    rc = futas_orzo.main(["--youtube", path])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "false"


# ── Szegmens-tudatos idempotencia-őr (reggel/este) ──

def _ir_nap_szegmens(tmp_path, nap_iso, szegmens, frissitve):
    napok = tmp_path / "napok"; napok.mkdir(parents=True, exist_ok=True)
    (napok / f"{nap_iso}.json").write_text(
        json.dumps({"nap": nap_iso, szegmens: {"trendek": [], "frissitve": frissitve}}),
        encoding="utf-8")


def test_szegmens_mai_reggel_true(tmp_path):
    _ir_nap_szegmens(tmp_path, "2026-08-31", "reggel", "2026-08-31T07:00:00+00:00")
    assert futas_orzo.szegmens_mar_gyujtottunk_ma(tmp_path, "reggel", "2026-08-31") is True


def test_szegmens_masik_szegmens_nem_szamit(tmp_path):
    # csak ESTI van ma → a REGGELI őr False (nem blokkolja a reggelit)
    _ir_nap_szegmens(tmp_path, "2026-08-31", "este", "2026-08-31T19:00:00+00:00")
    assert futas_orzo.szegmens_mar_gyujtottunk_ma(tmp_path, "reggel", "2026-08-31") is False
    assert futas_orzo.szegmens_mar_gyujtottunk_ma(tmp_path, "este", "2026-08-31") is True


def test_szegmens_tegnapi_false(tmp_path):
    _ir_nap_szegmens(tmp_path, "2026-08-30", "reggel", "2026-08-30T07:00:00+00:00")
    assert futas_orzo.szegmens_mar_gyujtottunk_ma(tmp_path, "reggel", "2026-08-31") is False


def test_szegmens_hianyzo_fajl_false(tmp_path):
    assert futas_orzo.szegmens_mar_gyujtottunk_ma(tmp_path, "reggel", "2026-08-31") is False


def test_cli_szegmens(tmp_path, capsys):
    _ir_nap_szegmens(tmp_path, "2026-08-31", "reggel", "2026-08-31T07:00:00+00:00")
    # a „ma"-t a CLI a Budapest-napból számítja; itt a determinizmushoz a szegmens-fn közvetlen tesztje a mérvadó,
    # a CLI-ág füst-szintű: hiányzó fájl → 'false'
    futas_orzo.main(["--szegmens", "reggel", str(tmp_path)])
    assert capsys.readouterr().out.strip() in {"true", "false"}
