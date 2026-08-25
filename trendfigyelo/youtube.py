"""YouTube-ág belépő — CSAK a YouTube-szavak (gprop=youtube) 3-m+12-m gyűjtése + regresszió.

KRITIKUS INVARIÁNS: SEMMILYEN más ágat NEM indít (se primer órás, se idosor/felkapott/rss,
se lánc, se ir_gordulo). A pótolhatatlan Google-órás adat érintetlen. Saját, SZŰK plafon.
Használat: python -m trendfigyelo.youtube   (a .github/workflows/youtube.yml futtatja).
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from . import kulcsszavak, nyers_kimenet, regresszio, naplo, seged
from .config import MASODLAGOS_TIMEFRAMEK, betolt
from .kliens import Kliens, AgFeladva, PlafonTullepve

GPROP = "youtube"
AG = "youtube"


def _reg_shim(config):
    """Config-nézet a regresszio_masodlagos_szamit-hoz: a YouTube-szavak + nincs módszertan-marker."""
    return SimpleNamespace(modszertan_valtas=None,
                           osszes_kulcsszo=lambda: config.osszes_youtube_kulcsszo())


def futtat_youtube(config, docs_data, most, kliens=None):
    """A YouTube-szavakat (gprop=youtube) tölti fel MINDKÉT másodlagos timeframe-en (3-m+12-m).

    SAJÁT, SZŰK plafon (cellák × max_probak + 1) — a napi órás gyűjtés kvótáját nem viheti el.
    NEM indít más ágat (primer/idosor/felkapott/lánc/ir_gordulo). 429/plafon-túllépésnél az
    EGÉSZ YouTube-ág feladja magát, de a már kiírt cellák megmaradnak (a Google-adat pótolhatatlan,
    ami eddig letöltve — mentve marad; ami nem, az egyszerűen kimarad).
    Visszaad: {"letoltve": [(szó, timeframe, pont)], "eldobva": [(szó, timeframe)]}.
    """
    szavak = config.osszes_youtube_kulcsszo()
    cellak = len(szavak) * len(MASODLAGOS_TIMEFRAMEK)
    if kliens is None:
        kliens = Kliens(config, plafon=cellak * config.max_probak + 1)  # SZŰK plafon (kvóta-védelem)

    letoltve, eldobva = [], []
    feladva = False
    for tetel in szavak:
        if feladva:
            break
        for timeframe in MASODLAGOS_TIMEFRAMEK:
            try:
                rek = kulcsszavak.gyujt_egy_masodlagos(kliens, config, tetel, most, timeframe,
                                                       gprop=GPROP, ag=AG)
            except (AgFeladva, PlafonTullepve) as e:
                print(f"FIGYELEM: a YouTube-ág feladva ({tetel.kifejezes!r} {timeframe}): {e}")
                feladva = True
                break
            if rek:
                nyers_kimenet.ir_youtube(docs_data, {tetel.kifejezes: rek})
                n = len([p for p in rek["pontok"] if not p.get("reszleges")])
                letoltve.append((tetel.kifejezes, timeframe, n))
                print(f"LETÖLTVE (yt): {tetel.kifejezes!r} {timeframe} ({n} pont)")
            else:
                eldobva.append((tetel.kifejezes, timeframe))
                print(f"ELDOBVA/ÜRES (yt): {tetel.kifejezes!r} {timeframe} (érkezés-ellenőrzés v. üres — NEM mentve)")

    # Regresszió a frissen kiírt youtube_nyers.json-ból (nulla Google-hívás)
    yt_fajl = Path(docs_data) / "youtube_nyers.json"
    if yt_fajl.exists():
        yt_nyers = json.loads(yt_fajl.read_text(encoding="utf-8"))
        adat = regresszio.regresszio_masodlagos_szamit(yt_nyers, {"napok": []}, _reg_shim(config),
                                                       most.isoformat())
        regresszio.regresszio_ir_youtube(docs_data, adat)

    print(f"ÖSSZEGZÉS (youtube): {len(letoltve)} letöltve, {len(eldobva)} eldobva/üres, "
          f"{kliens.osszes_hivas()} hívás. NEM indult primer/idosor/felkapott/lánc ág.")
    return {"letoltve": letoltve, "eldobva": eldobva}


def main(argv=None):
    p = argparse.ArgumentParser(description="YouTube-ág — gprop=youtube gyűjtés + regresszió, más ág NÉLKÜL.")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--docs-data", default="docs/data")
    p.add_argument("--adatok", default="adatok")
    a = p.parse_args(argv)
    config = betolt(a.config)
    most = seged.most_utc()
    ki = futtat_youtube(config, Path(a.docs_data), most)
    # napló: egy 'youtube' ág-sor
    naplo.naplo_ir(Path(a.adatok), most.isoformat(), [{
        "ag": "youtube", "eredmeny": "siker" if ki["letoltve"] else "hiany",
        "hivasok_szama": len(ki["letoltve"]), "hibakodok": "",
    }], config.naplo_max_sor)


if __name__ == "__main__":
    main()
