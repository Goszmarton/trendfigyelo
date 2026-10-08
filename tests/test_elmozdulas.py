# tests/test_elmozdulas.py
import json
from pathlib import Path

from trendfigyelo import elmozdulas as em


def _ir(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _reg(tmp_path, kulcsszavak):
    _ir(tmp_path / "kulcsszo_regresszio.json", {"szamitva_utc": "2026-10-07T18:00:00+00:00",
                                                "kulcsszavak": kulcsszavak})
    _ir(tmp_path / "kulcsszo_masodlagos_regresszio.json", {"kulcsszavak": {}})


def _nyers(tmp_path, szo, pontok):
    _ir(tmp_path / "kulcsszo_nyers.json", {"kulcsszavak": {szo: [
        {"kulcsszo": szo, "ablak_kezdet_utc": pontok[0]["idopont_utc"],
         "ablak_veg_utc": pontok[-1]["idopont_utc"], "pontok": pontok}]}})


def _iv(**kw):
    alap = {"ervenyes": True, "irany": "novekszik", "meredekseg_nap": 1.0, "se_meredekseg": 0.2,
            "r2": 0.6, "pontok_hasznalt": 160, "reziduum_szokasos": 4.0, "mai_reziduum": 12.0,
            "illeszkedes": "felette",
            "illesztes_vonal": [{"idopont_utc": "2026-10-01T00:00:00+00:00", "ertek": 30.0},
                                {"idopont_utc": "2026-10-07T00:00:00+00:00", "ertek": 48.0}]}
    alap.update(kw)
    return alap


def test_szokatlan_es_irany_es_elteres(tmp_path):
    _reg(tmp_path, {"benzin": {"domen": "megelhetes", "tipus": "szintmero", "racs": "ora",
                               "intervallumok": {"1_het": _iv()}}})
    _nyers(tmp_path, "benzin", [{"idopont_utc": "2026-10-07T18:00:00+00:00", "ertek": 60, "reszleges": False}])
    ki = em.elmozdulas_szamit(str(tmp_path))
    b = ki["kulcsszavak"]["benzin"]
    assert b["szokatlan"] is True
    assert b["irany"] == "emelkedik"                 # illeszkedes felette → emelkedik
    assert round(b["elteres"], 2) == 3.0             # 12.0 / max(4.0, 3.0) = 3.0
    assert b["elteres_nyers"] == 12.0
    assert b["szakpolitika"] == "energia_rezsi"
    assert "1_het" in b["sav"] and b["sav"]["1_het"]["also"] and b["sav"]["1_het"]["felso"]


def test_illeszkedik_nem_szokatlan(tmp_path):
    _reg(tmp_path, {"iskola": {"domen": "oktatas", "tipus": "szintmero", "racs": "het",
                               "intervallumok": {"1_ho": _iv(illeszkedes="illeszkedik", mai_reziduum=1.0)}}})
    _nyers(tmp_path, "iskola", [{"idopont_utc": "2026-10-07T18:00:00+00:00", "ertek": 40, "reszleges": False}])
    ki = em.elmozdulas_szamit(str(tmp_path))
    assert ki["kulcsszavak"]["iskola"]["szokatlan"] is False
    assert "iskola" not in ki["szokatlan_lista"]      # csak a szokatlanok a listában


def test_megbizhatosag_label(tmp_path):
    _reg(tmp_path, {"a": {"domen": "x", "tipus": "szintmero", "racs": "ora",
                          "intervallumok": {"1_het": _iv(r2=0.7, pontok_hasznalt=150)}},
                    "b": {"domen": "x", "tipus": "szintmero", "racs": "ora",
                          "intervallumok": {"1_het": _iv(r2=0.05, pontok_hasznalt=20)}}})
    _nyers(tmp_path, "a", [{"idopont_utc": "2026-10-07T18:00:00+00:00", "ertek": 60, "reszleges": False}])
    ki = em.elmozdulas_szamit(str(tmp_path))
    assert ki["kulcsszavak"]["a"]["megbizhatosag"] == "magas"
    assert ki["kulcsszavak"]["b"]["megbizhatosag"] == "alacsony"


def test_idotartam_egymas_utani_savon_kivuli_pontok(tmp_path):
    # a trendvonal ~30→48 (10-01..10-07). Az utolsó 3 pont magasan a sáv fölött, előtte illesztő.
    _reg(tmp_path, {"benzin": {"domen": "megelhetes", "tipus": "szintmero", "racs": "ora",
                               "intervallumok": {"1_het": _iv()}}})
    pts = [{"idopont_utc": f"2026-10-07T{h:02d}:00:00+00:00", "ertek": e, "reszleges": False}
           for h, e in [(10, 48), (11, 49), (12, 90), (13, 92), (14, 95)]]  # utolsó 3 kiugró
    _nyers(tmp_path, "benzin", pts)
    ki = em.elmozdulas_szamit(str(tmp_path))
    assert ki["kulcsszavak"]["benzin"]["idotartam_pont"] == 3
    assert ki["kulcsszavak"]["benzin"]["idotartam_ota_utc"] == "2026-10-07T12:00:00+00:00"


def test_elmozdulas_ir(tmp_path):
    _reg(tmp_path, {"benzin": {"domen": "megelhetes", "tipus": "szintmero", "racs": "ora",
                               "intervallumok": {"1_het": _iv()}}})
    _nyers(tmp_path, "benzin", [{"idopont_utc": "2026-10-07T18:00:00+00:00", "ertek": 60, "reszleges": False}])
    p = em.elmozdulas_ir(str(tmp_path))
    assert Path(p).exists()
    mentve = json.loads(Path(p).read_text(encoding="utf-8"))
    assert "benzin" in mentve["kulcsszavak"] and "szamitva_utc" in mentve
