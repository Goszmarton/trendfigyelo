# tests/test_heti_ertekeles.py
import json
from pathlib import Path

from trendfigyelo import heti_ertekeles as he


def _ir(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _regresszio_fajl(tmp_path):
    # két követett szó: egy „felette" (erősödő, pozitív eltérés) és egy „alatta" (gyengülő)
    _ir(tmp_path / "kulcsszo_regresszio.json", {
        "szamitva_utc": "2026-10-05T18:00:00+00:00",
        "kulcsszavak": {
            "benzinár": {"domen": "megelhetes", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": True, "irany": "nő", "illeszkedes": "felette",
                          "mai_ertek": 80, "mai_reziduum": 20.0, "reziduum_szokasos": 8.0,
                          "meredekseg_nap": 2.5,
                          "illesztes_vonal": [{"idopont_utc": "2026-09-29T00:00:00+00:00", "ertek": 60.0},
                                              {"idopont_utc": "2026-10-05T00:00:00+00:00", "ertek": 78.0}]}}},
            "nyugdíj": {"domen": "megelhetes", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": True, "irany": "csökken", "illeszkedes": "alatta",
                          "mai_ertek": 30, "mai_reziduum": 5.0, "reziduum_szokasos": 12.0,
                          "meredekseg_nap": -1.0, "illesztes_vonal": []}}},
        },
    })


def _youtube_fajl(tmp_path):
    _ir(tmp_path / "youtube_regresszio.json", {
        "szamitva_utc": "2026-10-05T18:00:00+00:00",
        "kulcsszavak": {
            "szorongás": {"domen": "egeszseg", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": True, "irany": "stagnál", "illeszkedes": "illeszkedik",
                          "mai_ertek": 14}}},
            "fejfájás": {"domen": "egeszseg", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": False, "ok": "kevés pont"}}},
        },
    })


def _nap(tmp_path, nap, kifejezesek):
    _ir(tmp_path / "napok" / f"{nap}.json",
        {"este": {"trendek": [{"kifejezes": k, "volumen": v, "temak": tm, "hirek": hi}
                               for (k, v, tm, hi) in kifejezesek]}})


def test_heti_korpusz_het_hatarok_es_iso(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")   # hétfő
    assert k["het_kezdet"] == "2026-09-29"
    assert k["het_veg"] == "2026-10-05"                # vasárnap
    assert k["iso_het"] == "2026-W40"


def test_heti_korpusz_kulcsszavak_elteres_es_irany(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    szavak = {s["szo"]: s for s in k["kulcsszavak"]}
    assert szavak["benzinár"]["irany"] == "nő"
    assert szavak["benzinár"]["illeszkedes"] == "felette"
    assert round(szavak["benzinár"]["elteres_szokasostol"], 2) == 12.0   # 20.0 - 8.0
    assert round(szavak["nyugdíj"]["elteres_szokasostol"], 2) == -7.0    # 5.0 - 12.0
    assert szavak["benzinár"]["domen"] == "megelhetes"
    assert szavak["benzinár"]["palya"][0]["ertek"] == 60.0


def test_heti_korpusz_elteres_none_ha_ervenytelen_vagy_hianyzik(tmp_path):
    _ir(tmp_path / "kulcsszo_regresszio.json", {"kulcsszavak": {
        "x": {"domen": "d", "tipus": "t", "intervallumok": {"1_het": {"ervenyes": False}}}}})
    _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    assert k["kulcsszavak"][0]["elteres_szokasostol"] is None
    assert k["kulcsszavak"][0]["irany"] is None


def test_heti_korpusz_felkapott_csak_a_het_napjaibol_napok_szama(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    _nap(tmp_path, "2026-09-28", [("héten kívül", 90, [], [])])        # előző vasárnap — KIMARAD
    _nap(tmp_path, "2026-09-29", [("tüntetés", 70, ["Politika"], [{"cim": "H1"}])])
    _nap(tmp_path, "2026-09-30", [("tüntetés", 90, ["Politika"], [{"cim": "H2"}])])
    _nap(tmp_path, "2026-10-05", [("tüntetés", 50, [], [])])
    _nap(tmp_path, "2026-10-06", [("héten kívül2", 10, [], [])])       # köv. hétfő — KIMARAD
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    fel = {f["kifejezes"]: f for f in k["felkapott"]}
    assert "héten kívül" not in fel and "héten kívül2" not in fel
    assert fel["tüntetés"]["napok_szama"] == 3
    assert fel["tüntetés"]["max_volumen"] == 90
    assert "Politika" in fel["tüntetés"]["temak"]
    assert "H1" in fel["tüntetés"]["hirek"] and len(fel["tüntetés"]["hirek"]) <= 3
    assert k["napok"] == 3        # a 3 héten-belüli nap


def test_heti_korpusz_youtube_ervenyes_es_ervenytelen(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    yt = {y["szo"]: y for y in k["youtube"]}
    assert yt["szorongás"]["irany"] == "stagnál" and yt["szorongás"]["nincs_adat"] is False
    assert yt["fejfájás"]["nincs_adat"] is True and yt["fejfájás"]["irany"] is None
