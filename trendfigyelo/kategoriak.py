"""Kategória-aggregátum: a kategoriak.json SZÁRMAZTATOTT nézet előállítása (spec 8.1).

A napi felkapott trendlista `temak` kategóriáit napi bontásban aggregálja. A
kategoriak.json a napok/*.json determinisztikus tükre (mint a regresszio.json a
nyersből) — nulla Google-hívás, felület nélkül.

Az `ok` mező MEGFIGYELÉST rögzít, nem OKOT: a "nincs_kategoria_adat" nem állítja,
MIÉRT nincs adat (a valódi ág utólag a naplo.csv felkapott_api sorából fejthető
vissza). Az "Other" valódi Google-kategória (topic ID 11), nem a kategoria_nelkul gyűjtő.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import json_export


def kategoria_aggregatum(nap_iso: str, trendek: list[dict]) -> dict | None:
    """Egy nap trendlistája → kategória-rekord, VAGY None (3a előtti nap, kihagyandó).

    None: egyetlen elemnek sincs "temak" KULCSA (3a előtti korszak).
    merve:false: a kulcs jelen, de minden temak üres → ok="nincs_kategoria_adat".
    merve:true: van legalább egy nem-üres temak; a []/kulcs nélküli elemek a
                kategoria_nelkul-ba esnek (§8.1 gyűjtő), a nap egésze mért (vegyes nap).
    """
    tem_m = sum(1 for e in trendek if "temak" in e)
    if tem_m == 0:
        return None                                  # 3a előtti nap — kihagyva
    lista_hossz = len(trendek)
    if not any(e.get("temak") for e in trendek):     # a kulcs jelen, de mind üres
        return {"nap": nap_iso, "merve": False,
                "ok": "nincs_kategoria_adat", "lista_hossz": lista_hossz}
    kategoriak = {}
    kategoria_nelkul = 0
    lista_kategoriaval = 0
    for e in trendek:
        temak = e.get("temak") or []                 # hiányzó kulcs VAGY [] → []
        if not temak:
            kategoria_nelkul += 1
        else:
            lista_kategoriaval += 1
            for k in temak:
                kategoriak[k] = kategoriak.get(k, 0) + 1
    return {"nap": nap_iso, "merve": True, "lista_hossz": lista_hossz,
            "lista_kategoriaval": lista_kategoriaval,
            "kategoria_nelkul": kategoria_nelkul, "kategoriak": kategoriak}


def kategoriak_ir(docs_data) -> Path:
    """A napok/*.json determinisztikus tükre → kategoriak.json (spec 8.1).

    A napok/index.json szerinti összes napi fájlt beolvassa, minden napra
    kategoria_aggregatum-ot hív, a None-t (3a előtti nap) kihagyja, nap szerint
    rendez, kiír. Idempotens: a kimenet a napi fájlok determinisztikus függvénye.
    """
    napok_mappa = Path(docs_data) / "napok"
    index_fajl = napok_mappa / "index.json"
    napok_index = (json.loads(index_fajl.read_text(encoding="utf-8")).get("napok", [])
                   if index_fajl.exists() else [])
    rekordok = []
    for nap_iso in sorted(napok_index):
        nap_fajl = napok_mappa / f"{nap_iso}.json"
        if not nap_fajl.exists():
            continue                                 # index-ben van, fájl nincs → nem reprezentáljuk
        nap = json.loads(nap_fajl.read_text(encoding="utf-8"))
        rek = kategoria_aggregatum(nap_iso, nap.get("trendek", []))
        if rek is not None:
            rekordok.append(rek)
    return json_export._ir_json(Path(docs_data) / "kategoriak.json", {"napok": rekordok})
