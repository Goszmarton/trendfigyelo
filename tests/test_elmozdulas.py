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


# ---- megerosito tesztek (mutacios ellenorzes utan) ----
def _p(h, e, reszleges=False):
    return {"idopont_utc": f"2026-10-07T{h:02d}:00:00+00:00", "ertek": e, "reszleges": reszleges}


def _egy(tmp_path, iv, pts, racs="ora", ivn="1_het", szo="benzin"):
    _reg(tmp_path, {szo: {"domen": "megelhetes", "tipus": "szintmero", "racs": racs,
                          "intervallumok": {ivn: iv}}})
    if pts:
        _nyers(tmp_path, szo, pts)
    return em.elmozdulas_szamit(str(tmp_path))["kulcsszavak"][szo]


def test_idotartam_egymast_koveto_nem_osszes(tmp_path):
    # vonal a 10-07 h. orajan: 48 + 0.125*h ; ki, be, ki, ki (legfrissebb a vegen)
    b = _egy(tmp_path, _iv(), [_p(10, 70), _p(11, 49.4), _p(12, 70), _p(13, 70)])
    assert b["idotartam_pont"] == 2
    assert b["idotartam_ota_utc"] == "2026-10-07T12:00:00+00:00"


def test_idotartam_negativ_shift_iranya(tmp_path):
    iv = _iv(illeszkedes="alatta", mai_reziduum=-12.0)
    b = _egy(tmp_path, iv, [_p(10, 20), _p(11, 20), _p(12, 20)])
    assert b["idotartam_pont"] == 3
    # a shift iranyaval ellentetes kiugro legfrissebb pont nem szamit
    p2 = tmp_path / "m"
    b2 = _egy(p2, iv, [_p(10, 20), _p(11, 20), _p(12, 90)])
    assert b2["idotartam_pont"] == 0


def test_idotartam_reszleges_kihagyva(tmp_path):
    b = _egy(tmp_path, _iv(), [_p(11, 70), _p(12, 70), _p(13, 5, reszleges=True)])
    assert b["idotartam_pont"] == 2
    assert b["idotartam_ota_utc"] == "2026-10-07T11:00:00+00:00"


def test_idotartam_sav_padlo(tmp_path):
    # MAD=0.5 -> sav = max(1, 3) = 3 ; vonal 13h-kor 49.625
    iv = _iv(reziduum_szokasos=0.5)
    assert _egy(tmp_path, iv, [_p(13, 51.625)])["idotartam_pont"] == 0   # rez 2 < 3
    assert _egy(tmp_path / "k", iv, [_p(13, 53.625)])["idotartam_pont"] == 1  # rez 4 > 3


def test_trendvonal_meredekseg_es_tengelymetszet(tmp_path):
    # vonal 13h-kor 49.625 ; sav=8 -> kuszob 57.625
    assert _egy(tmp_path, _iv(), [_p(13, 58)])["idotartam_pont"] == 1
    assert _egy(tmp_path / "k", _iv(), [_p(13, 57)])["idotartam_pont"] == 0


def test_sav_pontos_ertekek(tmp_path):
    s = _egy(tmp_path, _iv(reziduum_szokasos=4.0), [_p(13, 60)])["sav"]["1_het"]
    assert s["also"][0]["ertek"] == 30 - 8 and s["felso"][0]["ertek"] == 30 + 8
    assert s["also"][1]["ertek"] == 48 - 8 and s["felso"][1]["ertek"] == 48 + 8


def test_elteres_padlo(tmp_path):
    b = _egy(tmp_path, _iv(reziduum_szokasos=1.0, mai_reziduum=6.0), [])
    assert b["elteres"] == 2.0


def test_megbizhatosag_kozepes_es_hatar(tmp_path):
    assert _egy(tmp_path, _iv(r2=0.3, pontok_hasznalt=60), [])["megbizhatosag"] == "kozepes"
    b = _egy(tmp_path / "k", _iv(r2=0.7, pontok_hasznalt=30), [])
    assert b["megbizhatosag"] == "alacsony"
    assert _egy(tmp_path / "l", _iv(r2=0.3, pontok_hasznalt=150), [])["megbizhatosag"] == "kozepes"


def test_irany_alatta_es_illeszkedik(tmp_path):
    assert _egy(tmp_path, _iv(illeszkedes="alatta", mai_reziduum=-12.0), [])["irany"] == "csokken"
    assert _egy(tmp_path / "k", _iv(illeszkedes="illeszkedik"), [])["irany"] == "stabil"


def test_lista_abszolut_elteres_szerint(tmp_path):
    _reg(tmp_path, {
        "kicsi": {"domen": "x", "tipus": "szintmero", "racs": "ora",
                  "intervallumok": {"1_het": _iv(illeszkedes="alatta", mai_reziduum=-12.0)}},
        "nagy": {"domen": "x", "tipus": "szintmero", "racs": "ora",
                 "intervallumok": {"1_het": _iv(mai_reziduum=20.0)}}})
    ki = em.elmozdulas_szamit(str(tmp_path))
    assert ki["kulcsszavak"]["nagy"]["elteres"] == 5.0
    assert ki["kulcsszavak"]["kicsi"]["elteres"] == -3.0
    assert ki["szokatlan_lista"] == ["nagy", "kicsi"]


def test_racs_nap_a_1_ho_intervallumot_hasznalja(tmp_path):
    b = _egy(tmp_path, _iv(), [], racs="nap", ivn="1_ho")
    assert b["szokatlan"] is True and "1_ho" in b["sav"]


def test_megbizhatosag_kozepes_also_hatar(tmp_path):
    assert _egy(tmp_path, _iv(r2=0.2, pontok_hasznalt=50), [])["megbizhatosag"] == "kozepes"
    assert _egy(tmp_path / "a", _iv(r2=0.19, pontok_hasznalt=50), [])["megbizhatosag"] == "alacsony"
    assert _egy(tmp_path / "b", _iv(r2=0.2, pontok_hasznalt=49), [])["megbizhatosag"] == "alacsony"
