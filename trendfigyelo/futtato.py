"""Orchestráció: a négy ág futtatása részleges siker + block-stop szemantikával.

Ági sorrend: felkapott_api → felkapott_rss → kulcsszo → idosor. Ha egy ág 429
(AgFeladva) miatt blokkol, a hátralévő ágak kimaradnak, de az addig összegyűjtött
adat kiíródik (CSV-k, JSON-export, napló). A kilépési kód: 0, ha bármilyen adat
gyűlt, különben 1.
"""

import json
import sys
from pathlib import Path

from . import (felkapott, idosorok, json_export, kulcsszavak, naplo, nyers_kimenet,
               regresszio, seged)
from .config import betolt
from .kliens import AgFeladva, Kliens

# az ágak logolási sorrendje (block-stop kihagyás jelöléséhez) = a valós végrehajtási sorrend
AGAK = ["felkapott_api", "felkapott_rss", "kulcsszo", "idosor"]


def tervezett_hivasszam(config) -> int:
    """A hibamentes (429 nélküli) futás várható Google-hívásszáma az ágstruktúrából.

    felkapott_api (1) + felkapott_rss (1) + idosor (≤ trend_idosor_max, trendenként)
    + kulcsszo (SZÓLÓ: szavankénti egy hívás = len(kulcsszavak)).
    """
    return 2 + config.trend_idosor_max + len(config.osszes_kulcsszo())


def top_trend_struktura(api_trendek, trend_idosorok, rss_trendek, config) -> list:
    """A legnagyobb volumenű trendek strukturált listája: idősor + hírek párosítva.

    Az idősor a trend_idosorok-ból, a hírek az RSS-ből (felkapott.hir_sorok)
    párosítva a kifejezés szerint.
    """
    hir_map = {}
    for sor in felkapott.hir_sorok(rss_trendek):
        hir_map.setdefault(sor["kifejezes"], []).append({
            k: v for k, v in sor.items() if k not in ("sorszam", "kifejezes")
        })

    idosor_map = {}
    for p in trend_idosorok:
        idosor_map.setdefault(p["kifejezes"], []).append({
            "idopont_utc": p["idopont_utc"], "ertek": p["ertek"],
        })

    legnagyobbak = sorted(api_trendek, key=felkapott.volumen_szam, reverse=True)
    legnagyobbak = legnagyobbak[: config.trend_idosor_max]

    struktura = []
    ures_topics = []
    for t in legnagyobbak:
        kifejezes = getattr(t, "keyword", "")
        # kategória CSAK az API-ág TrendKeyword-jén van; az RSS-ág TrendKeywordLite-ján NINCS
        # topics/topic_names attribútum → a getattr-fallback [] (nem AttributeError). Mindkét mező
        # MINDIG jelen, üres esetben []. A temak a topics-ból derivált (len egyezik, trend_keyword.py:46).
        topics = list(getattr(t, "topics", []) or [])
        temak = list(getattr(t, "topic_names", []) or [])
        if not topics:
            ures_topics.append(kifejezes)
        struktura.append({
            "kifejezes": kifejezes,
            "volumen": seged.szovegge(getattr(t, "volume", None)),
            "novekedes_pct": seged.szovegge(getattr(t, "volume_growth_pct", None)),
            "topics": topics,
            "temak": temak,
            "idosor": idosor_map.get(kifejezes, []),
            "hirek": hir_map.get(kifejezes, []),
        })
    if ures_topics:   # csak ha VAN üres-topics-ú trend; üres trendlistánál semmi
        print(f"FIGYELEM: {len(ures_topics)} trend üres topics-szal: {', '.join(ures_topics)}")
    return struktura


def _ag(bejegyzesek, kliens, ag, fn):
    """Egy ág futtatása naplózással. AgFeladva propagál (block-stop), egyéb hiba
    csak az adott ágat bukja (None-t ad vissza)."""
    try:
        eredmeny = fn()
        bejegyzesek.append({"ag": ag, "eredmeny": "siker",
                            "hivasok_szama": kliens.hivasszam(ag), "hibakodok": ""})
        return eredmeny
    except AgFeladva as e:
        hibakodok = ",".join(getattr(e, "hibakodok", []) or ["429"])
        bejegyzesek.append({"ag": ag, "eredmeny": "blokkolva",
                            "hivasok_szama": kliens.hivasszam(ag), "hibakodok": hibakodok})
        print(f"FIGYELEM: a(z) '{ag}' ág BLOKKOLVA (429) — a hátralévő ágak kimaradnak.")
        raise
    except Exception as e:
        hibakodok = ",".join(getattr(e, "hibakodok", []) or [type(e).__name__])
        bejegyzesek.append({"ag": ag, "eredmeny": "hiba",
                            "hivasok_szama": kliens.hivasszam(ag), "hibakodok": hibakodok})
        print(f"FIGYELEM: a(z) '{ag}' ág elbukott ({e}).")
        return None


def futtat(config, kliens, adatok_mappa, docs_data_mappa, most=None) -> int:
    """A teljes futás: négy ág, öt CSV, JSON-export, napló, kilépési kód."""
    if most is None:
        most = seged.most_utc()
    adatok_mappa = Path(adatok_mappa)
    docs_data_mappa = Path(docs_data_mappa)
    adatok_mappa.mkdir(parents=True, exist_ok=True)

    idobelyeg = seged.bp_idobelyeg(most)
    letoltve = most.isoformat(timespec="seconds")
    nap_iso = most.astimezone(seged.BUDAPEST).date().isoformat()

    bejegyzesek = []
    # négy külön lista, hogy block-stop után is a részleges adat legyen kéznél
    api_trendek = []
    rss_trendek = []
    trend_idosorok = []
    kulcsszo_pontok = []
    kulcsszo_napi_pontok = {}
    kulcsszo_nyers = {}

    try:
        api_trendek = _ag(bejegyzesek, kliens, "felkapott_api",
                          lambda: felkapott.gyujt_api(kliens, config)) or []
        rss_trendek = _ag(bejegyzesek, kliens, "felkapott_rss",
                          lambda: felkapott.gyujt_rss(kliens, config)) or []
        # a kulcsszo-ág az idosor ELŐTT fut: block-napon az idosor az olcsóbb veszteség
        # (a kulcsszó-adat a 24-órás horgony-nélküli mérés, az idosor a top-trend sparkline)
        kulcsszo_eredmeny = _ag(bejegyzesek, kliens, "kulcsszo",
                            lambda: kulcsszavak.gyujt(kliens, config, most))
        kulcsszo_pontok, kulcsszo_napi_pontok, kulcsszo_nyers = kulcsszo_eredmeny or ([], {}, {})
        # volumen szerint rendezett kifejezéslista — az idősor-ág belül vág top-N-re
        top_kifejezesek = [
            getattr(t, "keyword", "")
            for t in sorted(api_trendek, key=felkapott.volumen_szam, reverse=True)
        ]
        trend_idosorok = _ag(bejegyzesek, kliens, "idosor",
                            lambda: idosorok.gyujt(kliens, config, top_kifejezesek)) or []
    except AgFeladva:
        # a blokkolt ág után minden még nem naplózott ág kimarad
        logolt = {b["ag"] for b in bejegyzesek}
        for ag in AGAK:
            if ag not in logolt:
                bejegyzesek.append({"ag": ag, "eredmeny": "kihagyva",
                                    "hivasok_szama": kliens.hivasszam(ag), "hibakodok": ""})

    # ---------- CSV-k (öt fájl) ----------
    felkapott.csv_ir_api(adatok_mappa, idobelyeg, letoltve, config.geo, api_trendek)
    felkapott.csv_ir_rss(adatok_mappa, idobelyeg, letoltve, config.geo, rss_trendek)
    felkapott.csv_ir_hirek(adatok_mappa, idobelyeg, config.geo, rss_trendek)
    idosorok.csv_ir(adatok_mappa, idobelyeg, letoltve, config.geo, trend_idosorok)
    kulcsszavak.csv_ir(adatok_mappa, idobelyeg, letoltve, config.geo, kulcsszo_pontok)

    # ---------- JSON-export ----------
    top_trendek = top_trend_struktura(api_trendek, trend_idosorok, rss_trendek, config)
    json_export.legfrissebb_ir(docs_data_mappa, top_trendek, trend_idosorok,
                               kulcsszo_pontok, letoltve, config.geo,
                               valtas_datum=config.modszertan_valtas)

    van_adat = bool(api_trendek or rss_trendek or trend_idosorok or kulcsszo_pontok)
    # független feltételek: üres kulcsszó-napi adat NE írja felül a meglévő
    # (jó) tortenet.json-bejegyzéseket; üres top-trend NE hozzon üres napi fájlt
    # tortenet: a valós adat-napokra (utolsó N teljes nap), NEM a futás napjára —
    # a legfrissebb nap felülír, a régebbiek insert-if-absent (visszapótlás)
    if kulcsszo_napi_pontok:
        json_export.tortenet_frissit_napok(docs_data_mappa, kulcsszo_napi_pontok,
                                           valtas_datum=config.modszertan_valtas)
    if top_trendek:
        json_export.napi_ir(docs_data_mappa, nap_iso, top_trendek)
    # nyers órás sorozat verziókövetett gördülő kimenete (üres sorozat NE írjon fájlt)
    if kulcsszo_nyers:
        nyers_kimenet.ir_gordulo(docs_data_mappa, kulcsszo_nyers)

    # ---------- regresszió (származtatott nézet, VÉDETTEN) ----------
    # Nulla Google-hívás; egy hibája SOHA nem viheti el az adatmentést vagy az exit-kódot,
    # de NEM néma (finding 6): hiba → FIGYELEM a run.log-ba + naplósor. A kulcsszo_nyers a
    # regresszió bemenete (hiánya → kihagyva); a tortenet csak élettartam-kontextus, a
    # hiánya NEM hiba (kecses degradáció: meres_kezdete=null, ezt a 9b kezeli).
    nyers_fajl = docs_data_mappa / "kulcsszo_nyers.json"
    if not nyers_fajl.exists():
        bejegyzesek.append({"ag": "regresszio", "eredmeny": "kihagyva",
                            "hivasok_szama": 0, "hibakodok": ""})
        print("FIGYELEM: regresszió kihagyva — nincs kulcsszo_nyers.json.")
    else:
        try:
            # várt kivételek: FileNotFoundError, json.JSONDecodeError, KeyError, ValueError,
            # TypeError, OSError — az Exception-backstop mindet elnyeli; a
            # KeyboardInterrupt/SystemExit (BaseException) továbbmegy.
            nyers = json.loads(nyers_fajl.read_text(encoding="utf-8"))
            tortenet_fajl = docs_data_mappa / "tortenet.json"
            tortenet = (json.loads(tortenet_fajl.read_text(encoding="utf-8"))
                        if tortenet_fajl.exists() else {})
            regresszio.regresszio_ir(
                docs_data_mappa,
                regresszio.regresszio_szamit(nyers, tortenet, config, letoltve))
            bejegyzesek.append({"ag": "regresszio", "eredmeny": "siker",
                                "hivasok_szama": 0, "hibakodok": ""})
        except Exception as e:
            bejegyzesek.append({"ag": "regresszio", "eredmeny": "hiba",
                                "hivasok_szama": 0, "hibakodok": type(e).__name__})
            print(f"FIGYELEM: a regresszió kimaradt — nem blokkolja az adatmentést ({e}).")

    # ---------- napló ----------
    naplo.naplo_ir(adatok_mappa, letoltve, bejegyzesek, config.naplo_max_sor)

    print(f"Összes Google-hívás: {kliens.osszes_hivas()}")
    return 0 if van_adat else 1


def main() -> int:
    """Belépő: config betöltése, Kliens felépítése, teljes futás."""
    config = betolt()
    # hívás-plafon = a strukturális maximum (minden logikai hívás mind a max_probak
    # próbát kimeríti); efölött már csak call-multiplying bug lehet → azonnali leállás
    kliens = Kliens(config, plafon=tervezett_hivasszam(config) * config.max_probak)
    print(f"Várható Google-hívásszám (429 nélkül): ~{tervezett_hivasszam(config)}")
    return futtat(config, kliens, Path("adatok"), Path("docs") / "data")


if __name__ == "__main__":
    sys.exit(main())
