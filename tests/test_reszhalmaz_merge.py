"""R1 karakterizáció: a nyers/lánc írók PER-SZÓ upsertek — egy részhalmaz-írás
NEM törli a fájlban lévő MÁSIK szó (pótolhatatlan) sorozatát. Ez az invariáns a
reggeli szubhalmaz-gyűjtés (Task 6) előfeltevése."""

import json
from datetime import datetime, timezone
from pathlib import Path

from trendfigyelo import nyers_kimenet, lanc


def _rekord(kif, orak, ertekek):
    idok = [datetime(2026, 8, d, 10, tzinfo=timezone.utc) for d in orak]
    return {
        "kulcsszo": kif,
        "ablak_kezdet_utc": idok[0].isoformat(),
        "ablak_veg_utc": idok[-1].isoformat(),
        "pontok": [{"idopont_utc": t.isoformat(), "ertek": e, "reszleges": False}
                   for t, e in zip(idok, ertekek)],
    }


def test_ir_gordulo_reszhalmaz_megorzi_esti_szot(tmp_path):
    # seed: 2 "esti" szó a fájlban
    nyers_kimenet.ir_gordulo(tmp_path, {"benzin": _rekord("benzin", [1, 2, 3], [10, 20, 30])})
    nyers_kimenet.ir_gordulo(tmp_path, {"hitel": _rekord("hitel", [1, 2, 3], [5, 6, 7])})
    # reggeli profil-3 szó írása CSAK önmagát
    nyers_kimenet.ir_gordulo(tmp_path, {"korrupció": _rekord("korrupció", [2, 3, 4], [40, 50, 60])})
    adat = json.loads((tmp_path / "kulcsszo_nyers.json").read_text(encoding="utf-8"))["kulcsszavak"]
    assert set(adat) == {"benzin", "hitel", "korrupció"}         # az esti szavak MEGMARADTAK
    assert adat["benzin"][0]["pontok"][0]["ertek"] == 10          # érintetlen


def test_frissit_lanc_reszhalmaz_megorzi_esti_lancot(tmp_path):
    # seed: két szó lánca
    lanc.frissit_lanc(tmp_path, {"benzin": [_rekord("benzin", [1, 2, 3], [10, 20, 30])]})
    lanc.frissit_lanc(tmp_path, {"hitel": [_rekord("hitel", [1, 2, 3], [5, 6, 7])]})
    tarolt_elott = json.loads((tmp_path / lanc.FAJL).read_text(encoding="utf-8"))["kulcsszavak"]
    assert set(tarolt_elott) == {"benzin", "hitel"}
    # reggeli szó bővítése CSAK önmagát érinti
    lanc.frissit_lanc(tmp_path, {"korrupció": [_rekord("korrupció", [2, 3, 4], [40, 50, 60])]})
    utana = json.loads((tmp_path / lanc.FAJL).read_text(encoding="utf-8"))["kulcsszavak"]
    assert set(utana) == {"benzin", "hitel", "korrupció"}         # esti láncok MEGMARADTAK
    assert utana["benzin"] == tarolt_elott["benzin"]             # bájt-azonos (dict(tarolt) megőrzés)
