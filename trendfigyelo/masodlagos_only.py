"""MÁSODLAGOS-ONLY belépő — CSAK a másodlagos (nap/het) cellák feltöltése.

KRITIKUS INVARIÁNS (§10): SEMMILYEN más ágat NEM indít — se primer órás (`kulcsszavak.gyujt`, now 7-d), se
idosor/felkapott/rss, se lánc-frissítés (`lanc.frissit_lanc`), se `ir_gordulo`, se adat-commit. A primer órás az
EGYETLEN pótolhatatlan adat; egy párhuzamos futás / kvóta-kimerítés a napi órás gyűjtést vinné el.

Használat:
  lokálisan:  python -m trendfigyelo.masodlagos_only --max-cella 4
              python -m trendfigyelo.masodlagos_only --cella "hitel:today 3-m" --cella "napelem:today 12-m"
  workflow_dispatch: a .github/workflows/masodlagos_only.yml futtatja.
A futás CSAK a kulcsszo_masodlagos_nyers.json-t írja (ir_masodlagos); NEM committol — a persistálást/időzítést a user dönti.
"""

import argparse
from pathlib import Path

from . import futtato, kulcsszavak, nyers_kimenet, seged
from .config import MASODLAGOS_TIMEFRAMEK, betolt
from .kliens import Kliens

MASODLAGOS_ONLY_ALAP_CELLA = 2   # ÓVATOS alapérték (a user emelheti)


def _cellak_feloldas(config, cellak):
    """A (szó, timeframe) string-párokat (KulcsszoTetel, timeframe)-re; a nem-jogosultat (ora / ismeretlen) KIHAGYJA."""
    aktivak = {t.kifejezes: t for t in config.osszes_kulcsszo()}
    ki = []
    for kif, tf in cellak:
        t = aktivak.get(kif)
        if t is None or t.racs == "ora" or tf not in MASODLAGOS_TIMEFRAMEK:
            print(f"FIGYELEM: kihagyva a nem-jogosult cella: {kif!r} {tf!r} (ora / ismeretlen szó v. timeframe).")
            continue
        ki.append((t, tf))
    return ki


def futtat_masodlagos_only(config, docs_data_mappa, most, max_cella=MASODLAGOS_ONLY_ALAP_CELLA,
                           cellak=None, kliens=None):
    """A megadott (vagy staleness szerint választott) cellákat tölti fel. Visszaad:
    {"letoltve": [(szó, timeframe, pont)], "eldobva": [(szó, timeframe)]}.

    SAJÁT, SZŰK plafon (`max_cella × max_probak + 1`) — NEM a napi plafon, így a napi órás gyűjtés kvótáját nem viheti
    el. NEM indít más ágat. A mai érkezés-ellenőrzés (`masodlagos_alak_ok`, a `gyujt_egy_masodlagos`-ban) ÉLES:
    csonka/rossz cella ELDOBVA + FIGYELEM, nem mentve."""
    if cellak is None:
        valasztott = futtato.masodlagos_szavak_ma(config, most, docs_data_mappa, limit=max_cella)
    else:
        valasztott = _cellak_feloldas(config, cellak)[:max_cella]   # a SAJÁT limit (a napi MAX_MASODLAGOS_NAPI-t NEM használja)
    if kliens is None:
        kliens = Kliens(config, plafon=max_cella * config.max_probak + 1)   # saját, szűk plafon (kvóta-védelem)
    letoltve, eldobva = [], []
    for tetel, timeframe in valasztott:
        rek = kulcsszavak.gyujt_egy_masodlagos(kliens, config, tetel, most, timeframe)
        if rek:
            nyers_kimenet.ir_masodlagos(docs_data_mappa, {tetel.kifejezes: rek})
            n = len([p for p in rek["pontok"] if not p.get("reszleges")])
            letoltve.append((tetel.kifejezes, timeframe, n))
            print(f"LETÖLTVE: {tetel.kifejezes!r} {timeframe} ({n} pont, MENTVE)")
        else:
            eldobva.append((tetel.kifejezes, timeframe))
            print(f"ELDOBVA/ÜRES: {tetel.kifejezes!r} {timeframe} (érkezés-ellenőrzés v. üres — NEM mentve)")
    print(f"ÖSSZEGZÉS (másodlagos-only): {len(letoltve)} letöltve, {len(eldobva)} eldobva/üres. "
          f"NEM indult primer/idosor/felkapott/lánc/commit ág.")
    return {"letoltve": letoltve, "eldobva": eldobva}


def main(argv=None):
    p = argparse.ArgumentParser(description="Másodlagos-only feltöltő — CSAK a nap/het cellák, más ág NÉLKÜL.")
    p.add_argument("--max-cella", type=int, default=MASODLAGOS_ONLY_ALAP_CELLA,
                   help="hány cellát töltsön (ÓVATOS alap: 2)")
    p.add_argument("--cella", action="append", default=[], metavar="SZÓ:TIMEFRAME",
                   help='konkrét cella, pl. "hitel:today 3-m" (többször megadható)')
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--docs-data", default="docs/data")
    a = p.parse_args(argv)
    config = betolt(a.config)
    most = seged.most_utc()
    cellak = None
    if a.cella:
        cellak = []
        for c in a.cella:
            kif, _, tf = c.partition(":")
            cellak.append((kif.strip(), tf.strip()))
    futtat_masodlagos_only(config, Path(a.docs_data), most, max_cella=a.max_cella, cellak=cellak)


if __name__ == "__main__":
    main()
