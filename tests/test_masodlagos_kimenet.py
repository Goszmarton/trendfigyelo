"""Task 2 (Phase 4) — a másodlagos (nap/het) nyers kimenet szerződés-validátora + gördülő írója.

A másodlagos fájl (kulcsszo_masodlagos_nyers.json) az órástól KÜLÖN: per-rekord `racs`
("nap"|"het") + kötelező `lekerdezes_utc` (a 3 pillanatkép rendezéséhez). Retenció:
szavanként a 3 legutóbbi rekord `lekerdezes_utc` szerint (ADAT-relatív, nem falióra).
Az órás `ervenyes_nyers_rekord`-hoz NEM nyúlunk — a bázist újrahasználjuk.
"""

import json

import pytest

from trendfigyelo import nyers_kimenet
from trendfigyelo.nyers_kimenet import ervenyes_masodlagos_rekord


def _pont(iso, ertek=5, reszleges=False):
    return {"idopont_utc": iso, "ertek": ertek, "reszleges": reszleges}


def _mrekord(kezd="2026-05-16T00:00:00+00:00", veg="2026-08-13T00:00:00+00:00",
             pontok=None, kulcsszo="hitel", racs="nap",
             lekerdezes="2026-08-13T09:00:00+00:00"):
    if pontok is None:
        pontok = [_pont(kezd, 5, False), _pont(veg, 6, True)]
    return {"kulcsszo": kulcsszo, "racs": racs, "lekerdezes_utc": lekerdezes,
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
    # LEMEZRŐL visszaolvasott sérült örökség (racs nélkül) KIHAGYVA, a friss kiíródik
    fajl = tmp_path / "kulcsszo_masodlagos_nyers.json"
    serult = _mrekord(kulcsszo="régi")
    del serult["racs"]
    fajl.write_text(json.dumps({"kulcsszavak": {"régi": [serult]}}), encoding="utf-8")
    p = nyers_kimenet.ir_masodlagos(tmp_path, {"hitel": _mrekord()})   # nem dob kivételt
    adat = json.loads(p.read_text(encoding="utf-8"))
    assert "régi" not in adat["kulcsszavak"]                          # a sérült örökség karanténba
    assert adat["kulcsszavak"]["hitel"]                               # a friss kiíródott


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
