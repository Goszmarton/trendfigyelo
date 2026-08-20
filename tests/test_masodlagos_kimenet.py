"""Task 2 (Phase 4) — a másodlagos (nap/het) nyers kimenet szerződés-validátora + gördülő írója.

A másodlagos fájl (kulcsszo_masodlagos_nyers.json) az órástól KÜLÖN: per-rekord `racs`
("nap"|"het") + kötelező `lekerdezes_utc` (a 3 pillanatkép rendezéséhez). Retenció:
szavanként a 3 legutóbbi rekord `lekerdezes_utc` szerint (ADAT-relatív, nem falióra).
Az órás `ervenyes_nyers_rekord`-hoz NEM nyúlunk — a bázist újrahasználjuk.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from trendfigyelo import nyers_kimenet
from trendfigyelo.config import RACS_IDOKERET
from trendfigyelo.nyers_kimenet import elavult_masodlagos_szavak, ervenyes_masodlagos_rekord


def _pont(iso, ertek=5, reszleges=False):
    return {"idopont_utc": iso, "ertek": ertek, "reszleges": reszleges}


def _mrekord(kezd="2026-05-16T00:00:00+00:00", veg="2026-08-13T00:00:00+00:00",
             pontok=None, kulcsszo="hitel", racs="nap",
             lekerdezes="2026-08-13T09:00:00+00:00"):
    if pontok is None:
        pontok = [_pont(kezd, 5, False), _pont(veg, 6, True)]
    return {"kulcsszo": kulcsszo, "racs": racs, "timeframe": RACS_IDOKERET[racs], "lekerdezes_utc": lekerdezes,
            "ablak_kezdet_utc": kezd, "ablak_veg_utc": veg, "pontok": pontok}


# --- validátor ---

def test_masodlagos_ervenyes_atmegy():
    assert ervenyes_masodlagos_rekord(_mrekord()) == []


def test_masodlagos_hianyzo_racs():
    rek = _mrekord()
    del rek["racs"]
    hibak = ervenyes_masodlagos_rekord(rek)
    assert any("racs" in h for h in hibak)          # csonk-validátor ([]) itt bukik


def test_masodlagos_ervenytelen_racs():
    # az "ora" a config-ban érvényes, de a MÁSODLAGOS fájlban NEM (csak nap/het)
    hibak = ervenyes_masodlagos_rekord(_mrekord(racs="ora"))
    assert any("racs" in h for h in hibak)


def test_masodlagos_hianyzo_lekerdezes_utc():
    rek = _mrekord()
    del rek["lekerdezes_utc"]
    hibak = ervenyes_masodlagos_rekord(rek)
    assert any("lekerdezes_utc" in h for h in hibak)


def test_masodlagos_orokli_a_bazis_hibakat():
    # a bázis (ervenyes_nyers_rekord) hibái is fognak: ablakon kívüli pont
    rek = _mrekord(pontok=[_pont("2026-09-01T00:00:00+00:00", 5, True)])  # veg 08-13 után
    hibak = ervenyes_masodlagos_rekord(rek)
    assert any("ablakon kívül" in h for h in hibak)


# --- gördülő író ---

def test_ir_masodlagos_racs_es_lekerdezes_megorzodik(tmp_path):
    p = nyers_kimenet.ir_masodlagos(tmp_path, {"hitel": _mrekord(racs="het")})
    adat = json.loads(p.read_text(encoding="utf-8"))
    rek = adat["kulcsszavak"]["hitel"][-1]
    assert rek["racs"] == "het"
    assert rek["lekerdezes_utc"] == "2026-08-13T09:00:00+00:00"
    assert ervenyes_masodlagos_rekord(rek) == []


def test_ir_masodlagos_megtart_3_legutobbit(tmp_path):
    for lek in ["09:00", "10:00", "11:00", "12:00"]:
        nyers_kimenet.ir_masodlagos(
            tmp_path, {"hitel": _mrekord(lekerdezes=f"2026-08-13T{lek}:00+00:00")})
    adat = json.loads((tmp_path / "kulcsszo_masodlagos_nyers.json").read_text(encoding="utf-8"))
    lekek = sorted(r["lekerdezes_utc"] for r in adat["kulcsszavak"]["hitel"])
    assert len(lekek) == 3                                       # csak 3 marad
    assert lekek[0] == "2026-08-13T10:00:00+00:00"              # a legrégebbi (09:00) kiesett
    assert "2026-08-13T09:00:00+00:00" not in lekek


def test_masodlagos_retencio_timeframe_kulon(tmp_path):
    # RED (2. rész): egy szó 3× 3-m (racs=nap) + 3× 12-m (racs=het) → MIND a 6 marad (3/timeframe), nem 3 (össz).
    for lek in ["10:00", "11:00", "12:00"]:
        nyers_kimenet.ir_masodlagos(tmp_path, {"hitel": _mrekord(racs="nap", lekerdezes=f"2026-08-13T{lek}:00+00:00")})
    for lek in ["13:00", "14:00", "15:00"]:
        nyers_kimenet.ir_masodlagos(tmp_path, {"hitel": _mrekord(racs="het", lekerdezes=f"2026-08-13T{lek}:00+00:00")})
    rekk = json.loads((tmp_path / "kulcsszo_masodlagos_nyers.json").read_text(encoding="utf-8"))["kulcsszavak"]["hitel"]
    tf_szam = {}
    for r in rekk:
        tf_szam[r["timeframe"]] = tf_szam.get(r["timeframe"], 0) + 1
    assert len(rekk) == 6                                        # RED: ma 3-ra vág (össz, timeframe-független) → len 3
    assert tf_szam == {"today 3-m": 3, "today 12-m": 3}          # timeframe-enként külön 3


def test_ir_masodlagos_legacy_timeframe_backfill(tmp_path):
    # RED (KARANTEN-LEGACY): a régi, timeframe NÉLKÜLI rekord kapja meg a timeframe-et a racs-ból a karantén ELŐTT
    # (visszamenőleges migráció), NEM dobódik ki. Ma: az ir_masodlagos karanténba dobja → NÉMA ADATVESZTÉS.
    legacy = {"kulcsszo": "kórház", "racs": "het", "lekerdezes_utc": "2026-08-16T12:00:00+00:00",
              "ablak_kezdet_utc": "2025-08-10T00:00:00+00:00", "ablak_veg_utc": "2026-08-16T00:00:00+00:00",
              "pontok": [{"idopont_utc": "2025-08-10T00:00:00+00:00", "ertek": 50, "reszleges": False}]}   # NINCS timeframe
    (tmp_path / "kulcsszo_masodlagos_nyers.json").write_text(
        json.dumps({"kulcsszavak": {"kórház": [legacy]}}, ensure_ascii=False), encoding="utf-8")
    # egy ÚJ (érvényes) rekord írása egy MÁSIK szóra → az ir_masodlagos beolvassa a legacy kórház-rekordot
    nyers_kimenet.ir_masodlagos(tmp_path, {"állás": _mrekord(kulcsszo="állás", racs="het")})
    adat = json.loads((tmp_path / "kulcsszo_masodlagos_nyers.json").read_text(encoding="utf-8"))["kulcsszavak"]
    assert "kórház" in adat                                    # a legacy NEM veszett el (ma: kidobva → RED)
    assert adat["kórház"][0]["timeframe"] == "today 12-m"      # a het-racs-ból visszatöltve


def test_ir_masodlagos_nem_urul_ha_nem_frissul(tmp_path):
    # a szó 2 pillanatképe MEGMARAD, ha egy későbbi futásban nem frissül (adat-relatív)
    nyers_kimenet.ir_masodlagos(tmp_path, {"állás": _mrekord(kulcsszo="állás", racs="het",
                                                             lekerdezes="2026-08-13T09:00:00+00:00")})
    nyers_kimenet.ir_masodlagos(tmp_path, {"állás": _mrekord(kulcsszo="állás", racs="het",
                                                             lekerdezes="2026-08-13T10:00:00+00:00")})
    nyers_kimenet.ir_masodlagos(tmp_path, {"hitel": _mrekord()})   # állás NEM frissül
    adat = json.loads((tmp_path / "kulcsszo_masodlagos_nyers.json").read_text(encoding="utf-8"))
    assert len(adat["kulcsszavak"]["állás"]) == 2                  # állás története megvan


def test_ir_masodlagos_karanten(tmp_path):
    # KARANTEN-LEGACY Sz1: a karantén CSAK (iii)-STRUKTURÁLIS okból dob — itt ÜRES pontok ("nincs egyetlen
    # pont sem"). (Korábban `del racs`-ot használt; az MOST visszatöltődik timeframe-ből → MEGTARTÁS, lásd
    # test_ir_masodlagos_ismeretlen_uj_kotelezo_mezo_nem_uriti_a_lemezt / legacy_timeframe_backfill.)
    fajl = tmp_path / "kulcsszo_masodlagos_nyers.json"
    serult = _mrekord(kulcsszo="régi", pontok=[])
    fajl.write_text(json.dumps({"kulcsszavak": {"régi": [serult]}}), encoding="utf-8")
    p = nyers_kimenet.ir_masodlagos(tmp_path, {"hitel": _mrekord()})   # nem dob kivételt
    adat = json.loads(p.read_text(encoding="utf-8"))
    assert "régi" not in adat["kulcsszavak"]                          # a strukturálisan sérült örökség karanténba
    assert adat["kulcsszavak"]["hitel"]                               # a friss kiíródott


def test_ir_masodlagos_ismeretlen_uj_kotelezo_mezo_nem_uriti_a_lemezt(tmp_path):
    # A #3 másodlagos ág őre: egy jövőbeli kötelező mező (a rétegnek ISMERETLEN, a VALÓDI _TOVABBI_KOTELEZO_MEZOK
    # mechanizmuson át) NEM üríti a másodlagos lemezt — MEGTARTÁS + FIGYELEM; a drop CSAK strukturális.
    fajl = tmp_path / "kulcsszo_masodlagos_nyers.json"
    legacy = _mrekord(kulcsszo="kórház", racs="het")
    fajl.write_text(json.dumps({"kulcsszavak": {"kórház": [legacy]}}, ensure_ascii=False), encoding="utf-8")
    nyers_kimenet._TOVABBI_KOTELEZO_MEZOK.append("ujmezo")
    try:
        nyers_kimenet.ir_masodlagos(tmp_path, {})                     # üres friss → csak a legacy örökséget olvassa
    finally:
        nyers_kimenet._TOVABBI_KOTELEZO_MEZOK.clear()
    adat = json.loads(fajl.read_text(encoding="utf-8"))["kulcsszavak"]
    assert "kórház" in adat, "a 'kórház' másodlagos rekord eltűnt a lemezről"


def test_ir_masodlagos_friss_hibas_hard_fail(tmp_path):
    # a FRISS producer-rekord hibája a MI bugunk → ValueError, nem karantén
    rossz = {"hitel": _mrekord(racs="ora")}                           # ora nem érvényes másodlagosban
    with pytest.raises(ValueError):
        nyers_kimenet.ir_masodlagos(tmp_path, rossz)


def test_ir_masodlagos_rendezi_a_pontokat(tmp_path):
    ny = {"hitel": _mrekord(pontok=[
        _pont("2026-08-13T00:00:00+00:00", 7, True),      # később elöl
        _pont("2026-05-16T00:00:00+00:00", 3, False)])}   # korábbi hátul
    p = nyers_kimenet.ir_masodlagos(tmp_path, ny)
    adat = json.loads(p.read_text(encoding="utf-8"))
    idok = [pt["idopont_utc"] for pt in adat["kulcsszavak"]["hitel"][0]["pontok"]]
    assert idok == sorted(idok)


# --- Task 4 (Ciklus A): elavult_masodlagos_szavak — tiszta függvény ------------
# A `most`-hoz relatív kor: legfrissebb lekerdezes_utc kora > kuszob_nap → elavult.
# ORA-BIZTONSÁG: a függvény CSAK a `sorozatok` kulcsain iterál → a benzin/nyugdíj
# (sosem másodlagos-kulcs) SOSEM jelenhet meg. A never-collected (kulcs nélküli)
# nem-ora szó NEM elavult (a rotációba még be nem került; Task 5 dolga).

_MOST = datetime(2026, 8, 14, 12, tzinfo=timezone.utc)


def _mrek(napja, racs="nap"):
    """Egy másodlagos rekord, aminek lekerdezes_utc-je `napja` nappal _MOST előtt."""
    utc = (_MOST - timedelta(days=napja)).isoformat()
    return {"racs": racs, "timeframe": RACS_IDOKERET[racs], "lekerdezes_utc": utc,
            "pontok": [_pont("2026-05-16T00:00:00+00:00")]}


def test_elavult_regi_lekerdezes_riaszt():
    # 1 friss (3 napos) + 1 régi (12 napos) → csak a régi jön vissza
    sorozatok = {"albérlet": [_mrek(3)], "állás": [_mrek(12, "het")]}
    assert elavult_masodlagos_szavak(sorozatok, _MOST, 10) == [("állás", 12)]


def test_elavult_hatar_pontosan_10_nap_nem_riaszt():
    # a `>` határ: 10 nap NEM riaszt, 11 nap IGEN
    sorozatok = {"hitel": [_mrek(10)], "napelem": [_mrek(11)]}
    assert elavult_masodlagos_szavak(sorozatok, _MOST, 10) == [("napelem", 11)]


def test_elavult_kor_szerint_csokkeno_sorrend():
    # több elavult → a régebbi elöl (kor csökkenő), tie-break ábécé
    sorozatok = {"kórház": [_mrek(11, "het")], "állás": [_mrek(13, "het")]}
    assert elavult_masodlagos_szavak(sorozatok, _MOST, 10) == [("állás", 13), ("kórház", 11)]


def test_elavult_kulcs_ures_rekordlista_nincs_adat():
    # kulcs jelen, de nincs érvényes lekerdezes_utc → "nincs adat = elavult" (napok=None)
    assert elavult_masodlagos_szavak({"állás": []}, _MOST, 10) == [("állás", None)]


# --- SZÁNDÉKOS-ZÖLD (előre jelölve): regresszió-őrök, nincs valódi RED-fázisuk ---
# A sorozatok-only konstrukció miatt eleve igazak; a stub `[]`-je ellen is zöldek.

def test_elavult_ora_szo_sosem_jelenik_SZANDEKOS_ZOLD():
    # a benzin/nyugdíj SOSEM másodlagos-kulcs → messze jövő `most` mellett sem jelenik
    sorozatok = {"állás": [_mrek(30, "het")]}
    kifejezesek = [k for k, _ in elavult_masodlagos_szavak(sorozatok, _MOST, 10)]
    assert "benzin" not in kifejezesek and "nyugdíj" not in kifejezesek


def test_elavult_mind_friss_ures_SZANDEKOS_ZOLD():
    # minden szó 3 napos → nincs elavult
    sorozatok = {"albérlet": [_mrek(3)], "hitel": [_mrek(2)]}
    assert elavult_masodlagos_szavak(sorozatok, _MOST, 10) == []
