"""Task 3 — a nyers órás kimenet szerződés-validátorának tesztjei.

RED-diszkriminátor: a validátornak EL KELL utasítania az ablakhatár nélküli
és a véglegesség-jelölés (`reszleges`) nélküli rekordot — egy „mindig []-t adó"
csonk-validátor ezen a két negatív teszten megbukik.
"""

import json
from datetime import datetime, timedelta

import pytest

from trendfigyelo import nyers_kimenet
from trendfigyelo.nyers_kimenet import ervenyes_nyers_rekord


def _rekord(kezd, veg, pontok, kulcsszo="hitel"):
    return {"kulcsszo": kulcsszo, "ablak_kezdet_utc": kezd,
            "ablak_veg_utc": veg, "pontok": pontok}


def _pont(iso, ertek=5, reszleges=False):
    return {"idopont_utc": iso, "ertek": ertek, "reszleges": reszleges}


def test_hianyzo_ablakhatar_elutasitva():
    rek = {"kulcsszo": "hitel", "ablak_veg_utc": "2026-07-27T21:00:00+00:00",
           "pontok": [{"idopont_utc": "2026-07-27T20:00:00+00:00", "ertek": 5, "reszleges": False}]}
    hibak = ervenyes_nyers_rekord(rek)
    assert any("ablak_kezdet_utc" in h for h in hibak)  # csonk-validátor ([]) itt bukik


def test_veglegesseg_jeloles_nelkul_elutasitva():
    rek = {"kulcsszo": "hitel", "ablak_kezdet_utc": "2026-07-20T21:00:00+00:00",
           "ablak_veg_utc": "2026-07-27T21:00:00+00:00",
           "pontok": [{"idopont_utc": "2026-07-27T20:00:00+00:00", "ertek": 5}]}  # nincs 'reszleges'
    hibak = ervenyes_nyers_rekord(rek)
    assert any("reszleges" in h for h in hibak)


def test_ervenyes_rekord_atmegy():
    rek = {"kulcsszo": "hitel", "ablak_kezdet_utc": "2026-07-20T21:00:00+00:00",
           "ablak_veg_utc": "2026-07-27T21:00:00+00:00",
           "pontok": [{"idopont_utc": "2026-07-27T20:00:00+00:00", "ertek": 5, "reszleges": True}]}
    assert ervenyes_nyers_rekord(rek) == []


# --- Task 6: szerződés-szigorítás (tz-aware + ablakon-belüliség) ---

def test_naiv_ablakhatar_elutasitva():
    # tz-szigor (Task 6): a naiv (offset nélküli) ablakhatár ELUTASÍTVA.
    # (Korábban a guard „nem szállt el" TypeError-ral; most kötelező tz-aware,
    #  a naiv határ már a mező-szinten megbukik — kivételt továbbra sem dob.)
    rek = _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00",  # veg naiv
                  [_pont("2026-07-27T20:00:00+00:00", 5, True)])
    hibak = ervenyes_nyers_rekord(rek)  # nem szabad kivételt dobnia
    assert any("ablak_veg_utc" in h for h in hibak)


def test_date_only_idobelyeg_elutasitva():
    # date-only (idő/offset nélküli) szintén nem tz-aware → elutasítva.
    rek = _rekord("2026-07-20", "2026-07-27",
                  [_pont("2026-07-27T20:00:00+00:00", 5, True)])
    hibak = ervenyes_nyers_rekord(rek)
    assert any("ablak_kezdet_utc" in h for h in hibak)


def test_ablakon_kivuli_pont_elutasitva():
    # in-window (Q2, inkluzív): a veg utáni idopont_utc-jű pont elutasítva.
    rek = _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                  [_pont("2026-07-28T20:00:00+00:00", 5, True)])  # 07-28 > veg 07-27
    hibak = ervenyes_nyers_rekord(rek)
    assert any("ablakon kívül" in h for h in hibak)


def test_ablakhataron_levo_pont_ervenyes():
    # inkluzív: a pont pontosan a kezdet ill. a vég időbélyegén érvényes.
    rek = _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                  [_pont("2026-07-20T21:00:00+00:00", 3, False),
                   _pont("2026-07-27T21:00:00+00:00", 7, True)])
    assert ervenyes_nyers_rekord(rek) == []


# --- Task 6: gördülő verziókövetett író (ir_gordulo) ---

def test_ir_gordulo_atmegy_a_szerzodesen(tmp_path):
    ny = {"hitel": _rekord(
        "2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
        [_pont("2026-07-27T20:00:00+00:00", 5, False),
         _pont("2026-07-27T21:00:00+00:00", 7, True)])}
    p = nyers_kimenet.ir_gordulo(tmp_path, ny)
    adat = json.loads(p.read_text(encoding="utf-8"))
    for lst in adat["kulcsszavak"].values():
        for rek in lst:
            assert ervenyes_nyers_rekord(rek) == []      # minden rekord átmegy a Task 3 szerződésen
    assert adat["kulcsszavak"]["hitel"][-1]["pontok"][-1]["reszleges"] is True  # a farok részleges


def _rek_ablak(nap):
    k, v = f"{nap}T20:00:00+00:00", f"{nap}T21:00:00+00:00"
    return _rekord(k, v, [_pont(k, 5, False), _pont(v, 6, True)])


def test_ir_gordulo_eldobja_a_regit(tmp_path):
    nyers_kimenet.ir_gordulo(tmp_path, {"hitel": _rek_ablak("2026-06-01")}, megtartott_nap=14)
    p = nyers_kimenet.ir_gordulo(tmp_path, {"hitel": _rek_ablak("2026-07-27")}, megtartott_nap=14)
    adat = json.loads(p.read_text(encoding="utf-8"))
    vegek = [datetime.fromisoformat(r["ablak_veg_utc"]) for r in adat["kulcsszavak"]["hitel"]]
    hatar = datetime.fromisoformat("2026-07-27T21:00:00+00:00") - timedelta(days=14)
    assert all(v >= hatar for v in vegek)                                    # nincs a határnál régebbi
    assert datetime.fromisoformat("2026-06-01T21:00:00+00:00") not in vegek  # a régi ablak kiesett
    assert datetime.fromisoformat("2026-07-27T21:00:00+00:00") in vegek      # a friss megmaradt


def test_ir_gordulo_rendezi_a_pontokat(tmp_path):
    # Q1: az író rendez idopont_utc szerint (a validátor NEM ír elő sorrendet).
    ny = {"hitel": _rekord(
        "2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
        [_pont("2026-07-27T21:00:00+00:00", 7, True),    # később elöl
         _pont("2026-07-20T21:00:00+00:00", 3, False)])}  # korábbi hátul
    p = nyers_kimenet.ir_gordulo(tmp_path, ny)
    adat = json.loads(p.read_text(encoding="utf-8"))
    idok = [pt["idopont_utc"] for pt in adat["kulcsszavak"]["hitel"][0]["pontok"]]
    assert idok == sorted(idok)          # a lemezen időrendi


def test_ir_gordulo_a_visszaolvasott_hibas_rekordot_karantenba_teszi(tmp_path):
    # Q2 (finomítva): a LEMEZRŐL visszaolvasott sérült örökség-rekordot KIHAGYJA
    # (karantén), de a friss adat kiíródik — egy romlott legacy-rekord nem
    # béníthatja meg a napi írást.
    fajl = tmp_path / "kulcsszo_nyers.json"
    serult = _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                     [_pont("2026-07-28T20:00:00+00:00", 5, False)])  # 07-28 > veg → ablakon kívül
    fajl.write_text(json.dumps({"kulcsszavak": {"hitel": [serult]}}), encoding="utf-8")
    friss = {"betegség": _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                                 [_pont("2026-07-27T20:00:00+00:00", 5, True)])}
    p = nyers_kimenet.ir_gordulo(tmp_path, friss)    # NEM dob kivételt
    adat = json.loads(p.read_text(encoding="utf-8"))
    assert "hitel" not in adat["kulcsszavak"]        # a sérült örökség karanténba került
    assert adat["kulcsszavak"]["betegség"]           # a friss adat kiíródott
    for rek in adat["kulcsszavak"]["betegség"]:
        assert ervenyes_nyers_rekord(rek) == []


def test_ir_gordulo_friss_hibas_rekord_hard_fail(tmp_path):
    # A FRISS producer-kimenet hibája a MI bugunk → hard fail (ValueError), nem karantén.
    friss = {"hitel": _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                              [_pont("2026-07-28T20:00:00+00:00", 5, True)])}  # ablakon kívül
    with pytest.raises(ValueError):
        nyers_kimenet.ir_gordulo(tmp_path, friss)
