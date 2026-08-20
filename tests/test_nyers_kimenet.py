"""Task 3 — a nyers órás kimenet szerződés-validátorának tesztjei.

RED-diszkriminátor: a validátornak EL KELL utasítania az ablakhatár nélküli
és a véglegesség-jelölés (`reszleges`) nélküli rekordot — egy „mindig []-t adó"
csonk-validátor ezen a két negatív teszten megbukik.
"""

import json
import os
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
    # KARANTEN-LEGACY Sz1: a karantén CSAK (iii)-STRUKTURÁLIS okból dob — itt egy ELHELYEZHETETLEN pont
    # (érvénytelen idopont_utc). A friss adat kiíródik — egy strukturálisan romlott legacy nem bénít.
    # (Korábban ablakon-kívüli pontot használt; az MOST NEM strukturális → külön keep-teszt lentebb.)
    fajl = tmp_path / "kulcsszo_nyers.json"
    serult = _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                     [_pont("NEM-DATUM", 5, False)])  # elhelyezhetetlen pont → (iii)-strukturális
    fajl.write_text(json.dumps({"kulcsszavak": {"hitel": [serult]}}), encoding="utf-8")
    friss = {"betegség": _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                                 [_pont("2026-07-27T20:00:00+00:00", 5, True)])}
    p = nyers_kimenet.ir_gordulo(tmp_path, friss)    # NEM dob kivételt
    adat = json.loads(p.read_text(encoding="utf-8"))
    assert "hitel" not in adat["kulcsszavak"]        # a strukturálisan sérült örökség karanténba került
    assert adat["kulcsszavak"]["betegség"]           # a friss adat kiíródott
    for rek in adat["kulcsszavak"]["betegség"]:
        assert ervenyes_nyers_rekord(rek) == []


def test_ir_gordulo_ablakon_kivuli_pont_nem_dob_hanem_megtart(tmp_path):
    # Sz1 — a ZÁRT DOBÁSI LISTA szűkítése: az ablakon kívüli pont NEM (iii)-strukturális (a pont elhelyezhető,
    # van érvényes idopont_utc-je) → a rekord MEGMARAD + FIGYELEM, NEM ürül. A pontszintű kezelés = Szelet 2.
    fajl = tmp_path / "kulcsszo_nyers.json"
    legacy = _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                     [_pont("2026-07-28T20:00:00+00:00", 5, False)], kulcsszo="hitel")  # 07-28 > veg
    fajl.write_text(json.dumps({"kulcsszavak": {"hitel": [legacy]}}), encoding="utf-8")
    nyers_kimenet.ir_gordulo(tmp_path, {})
    adat = json.loads(fajl.read_text(encoding="utf-8"))
    assert "hitel" in adat["kulcsszavak"], "az ablakon kívüli pont nem dobhatja el a teljes rekordot"


def test_ir_gordulo_friss_uj_kotelezo_mezo_nelkul_tovabbra_is_hard_fail(tmp_path):
    # Aszimmetria-őr: a fail-open NEM szivároghat az ÍRÁSRA. A friss producer-rekord, amiből az új kötelező
    # mező hiányzik, TOVÁBBRA IS hard-fail (ValueError) — a szigor a friss ágon marad (#2).
    nyers_kimenet._TOVABBI_KOTELEZO_MEZOK.append("ujmezo")
    try:
        friss = {"hitel": _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                                  [_pont("2026-07-27T20:00:00+00:00", 5, True)])}  # nincs ujmezo
        with pytest.raises(ValueError):
            nyers_kimenet.ir_gordulo(tmp_path, friss)
    finally:
        nyers_kimenet._TOVABBI_KOTELEZO_MEZOK.clear()


# --- MINOR-2: a retenció-horgony a legfrissebb VALÓS adatpontra áll (nem max ablak_veg) ---

def test_ir_gordulo_jovobeli_ablak_veg_nem_gorditi_ki_a_jo_multat(tmp_path):
    # MINOR-2: egy JÖVŐBELI ablak_veg (metaadat-hiba/legacy) NE húzza a retenció-horizontot a jövőbe → a jó,
    # friss MÚLT NE gördüljön ki a PÓTOLHATATLAN lemezről. RED: a régi max(ablak_veg) horgony a 09-30-ra ugrik,
    # a hatar 09-16 lesz, a 07-27-i jó rekord (< hatar) kigördül.
    jo = _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                 [_pont("2026-07-27T20:00:00+00:00", 5, False)], kulcsszo="hitel")
    jovo_veg = _rekord("2026-06-01T00:00:00+00:00", "2026-09-30T00:00:00+00:00",     # veg JÖVŐBELI, de a pont RÉGI
                       [_pont("2026-07-01T00:00:00+00:00", 5, False)], kulcsszo="hitel")
    fajl = tmp_path / "kulcsszo_nyers.json"
    fajl.write_text(json.dumps({"kulcsszavak": {"hitel": [jo, jovo_veg]}}), encoding="utf-8")
    nyers_kimenet.ir_gordulo(tmp_path, {})            # üres friss, megtartott_nap=14
    adat = json.loads(fajl.read_text(encoding="utf-8"))
    vegek = [r["ablak_veg_utc"] for r in adat["kulcsszavak"].get("hitel", [])]
    assert "2026-07-27T21:00:00+00:00" in vegek, "a jó, friss múlt kigördült a jövőbeli veg miatt"


# --- ATOMI-IRAS: a pótolhatatlan lemezírás atomi (temp + os.replace) ---

def test_ir_gordulo_megszakadt_iras_megorzi_a_regi_fajlt(tmp_path, monkeypatch):
    # ATOMI-IRAS: ha a KOMMIT lépés (os.replace) elhasal (crash/leállás írás közben), a RÉGI fájl bájtjai
    # SÉRTETLENEK maradnak, és nincs szemét temp. RED: a régi write_text in-place felülírja a régit.
    fajl = tmp_path / "kulcsszo_nyers.json"
    regi = _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                   [_pont("2026-07-27T20:00:00+00:00", 5, False)], kulcsszo="hitel")
    fajl.write_text(json.dumps({"kulcsszavak": {"hitel": [regi]}}), encoding="utf-8")
    regi_tartalom = fajl.read_text(encoding="utf-8")

    def _crash(*a, **k):
        raise OSError("megszakadt írás (kommit)")
    monkeypatch.setattr(os, "replace", _crash)

    friss = {"betegség": _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                                 [_pont("2026-07-27T20:00:00+00:00", 5, True)])}
    try:
        nyers_kimenet.ir_gordulo(tmp_path, friss)
    except OSError:
        pass                                     # az atomi kommit elhasalt — VÁRT az atomi írónál
    assert fajl.read_text(encoding="utf-8") == regi_tartalom, "a régi fájl tartalma megsérült a megszakadt írásnál"
    assert not list(tmp_path.glob("*.tmp")), "maradt szemét temp fájl"


def test_ir_gordulo_friss_hibas_rekord_hard_fail(tmp_path):
    # A FRISS producer-kimenet hibája a MI bugunk → hard fail (ValueError), nem karantén.
    friss = {"hitel": _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                              [_pont("2026-07-28T20:00:00+00:00", 5, True)])}  # ablakon kívül
    with pytest.raises(ValueError):
        nyers_kimenet.ir_gordulo(tmp_path, friss)


# --- KARANTEN-LEGACY Szelet 1: zárt dobási lista (drop CSAK strukturális) ---

def test_ir_gordulo_ismeretlen_uj_kotelezo_mezo_nem_uriti_a_lemezt(tmp_path):
    # A ZÁRT DOBÁSI LISTA őre: egy jövőbeli fejlesztő ÚJ kötelező mezőt vesz fel a VALÓDI mechanizmuson
    # (_TOVABBI_KOTELEZO_MEZOK), amiből a MEGLÉVŐ lemez-rekord hiányzik. A visszaolvasó karantén NEM
    # dobhatja ki (hiányzó mező != (iii)-strukturális): MEGTARTÁS + FIGYELEM. RED (régi logika): kidobja.
    fajl = tmp_path / "kulcsszo_nyers.json"
    legacy = _rekord("2026-07-20T21:00:00+00:00", "2026-07-27T21:00:00+00:00",
                     [_pont("2026-07-27T20:00:00+00:00", 5, False)], kulcsszo="állás")
    fajl.write_text(json.dumps({"kulcsszavak": {"állás": [legacy]}}), encoding="utf-8")
    nyers_kimenet._TOVABBI_KOTELEZO_MEZOK.append("ujmezo")   # a jövőbeli kötelező mező (a rétegnek ISMERETLEN)
    try:
        nyers_kimenet.ir_gordulo(tmp_path, {})               # üres friss → csak a legacy örökséget olvassa
    finally:
        nyers_kimenet._TOVABBI_KOTELEZO_MEZOK.clear()
    adat = json.loads(fajl.read_text(encoding="utf-8"))
    assert "állás" in adat["kulcsszavak"], "az 'állás' rekord eltűnt a lemezről"
