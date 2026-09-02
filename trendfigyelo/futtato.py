"""Orchestráció: a négy ág futtatása részleges siker + block-stop szemantikával.

Ági sorrend: felkapott_api → felkapott_rss → kulcsszo → idosor. Ha egy ág 429
(AgFeladva) miatt blokkol, a hátralévő ágak kimaradnak, de az addig összegyűjtött
adat kiíródik (CSV-k, JSON-export, napló). A kilépési kód: 0, ha bármilyen adat
gyűlt, különben 1.
"""

import json
import os
import sys
from pathlib import Path

from . import (felkapott, idosorok, json_export, kategoriak, kulcsszavak, lanc, naplo,
               nyers_kimenet, regresszio, seged)
from .config import betolt
from .kliens import AgFeladva, Kliens, PlafonTullepve

# az ágak logolási sorrendje (block-stop kihagyás jelöléséhez) = a valós végrehajtási sorrend
AGAK = ["felkapott_api", "felkapott_rss", "kulcsszo", "idosor", "kulcsszo_masodlagos", "idosor_rekesz"]
# kilépési kód szerződés: 0 = van adat / 1 = nincs adat / 2 = HÍVÁS-PLAFON túllépés
# (call-multiplying bug elleni védőkorlát tüzelt — HANGOS, hogy ne legyen success-vak).
KILEPES_PLAFON = 2


def tervezett_hivasszam(config) -> int:
    """A hibamentes (429 nélküli) futás várható Google-hívásszáma az ágstruktúrából.

    felkapott_api (1) + felkapott_rss (1) + idosor (≤ trend_idosor_max, trendenként)
    + idosor_rekesz (≤ trend_idosor_rekesz_max, GORBE-B forward-only) + kulcsszo (SZÓLÓ:
    szavankénti egy hívás = len(kulcsszavak)).
    """
    return (2 + config.trend_idosor_max + config.trend_idosor_rekesz_max
            + len(config.osszes_kulcsszo()))


# a másodlagos (nap/het) ág napi maximuma — szerkezeti konstans (a 2-2-2-2-1-1-1
# körbeforgó eloszlás csúcsa), NEM naptár-függő; a hívás-plafon fejtere ebből jön.
MAX_MASODLAGOS_NAPI = 2

# a REGGELI másodlagos ág napi cap-je — KÜLÖN az esti 2-től. A reggeli futásnak szabad
# kapacitása van (nem verseng az esti órás gyűjtéssel), ezért a ~15 reggeli szó egy-ablakos
# másodlagosát ~2 reggel alatt körbejárja (staleness szerint).
MAX_MASODLAGOS_REGGELI = 8


def _oras_szavak(config, mode) -> list:
    """A futás órás (elsődleges now 7-d) szavai: `oras` igaz ÉS a mód `futas`-részhalmaza."""
    futas = "reggel" if mode == "reggel" else "este"
    return [t for t in config.osszes_kulcsszo() if t.oras and t.futas == futas]


def masodlagos_szavak_ma(config, most, docs_data_mappa, limit=None, mode="este"):
    """A ma ütemezett (szó × timeframe) cellák — STALENESS-vezérelt, a mód `futas`-részhalmazán.

    `limit` = hány cellát adjon vissza; None → a mód cap-je (reggel MAX_MASODLAGOS_REGGELI / este
    MAX_MASODLAGOS_NAPI). A cellák a mód `futas`-részhalmazának nem-ora szavaiból épülnek, per-szó
    `masodlagos_timeframek(t)` ablakokkal (este mindkettő, reggel egy). A rangsor/fallback/IO-robusztusság
    változatlan.
    """
    from .config import masodlagos_timeframek
    futas = "reggel" if mode == "reggel" else "este"
    limit = limit or (MAX_MASODLAGOS_REGGELI if mode == "reggel" else MAX_MASODLAGOS_NAPI)
    nem_oras = [t for t in config.osszes_kulcsszo() if t.racs != "ora" and t.futas == futas]
    # CELLA = (config-index, tetel, timeframe-index, timeframe) — per-szó ablak(ok) a masodlagos_timeframek-ből
    cellak = [(i, t, tf_i, tf) for i, t in enumerate(nem_oras)
              for tf_i, tf in enumerate(masodlagos_timeframek(t))]
    fajl = Path(docs_data_mappa) / "kulcsszo_masodlagos_nyers.json"
    try:
        sorozatok = json.loads(fajl.read_text(encoding="utf-8")).get("kulcsszavak", {})
    except (OSError, ValueError) as e:
        print(f"FIGYELEM: másodlagos ütemező — a(z) {fajl.name!r} nem olvasható ({type(e).__name__}); "
              f"FALLBACK: config-index+timeframe sorrend első {limit} cellája.")
        return [(t, tf) for _, t, _, tf in cellak[:limit]]

    def _elavultsag(kif, tf):
        rekk = [r for r in (sorozatok.get(kif, []) or []) if r.get("timeframe") == tf]   # cella-szintű (per timeframe)
        korok = [nyers_kimenet._aware_dt(r.get("lekerdezes_utc")) for r in rekk]
        legfrissebb = max((d for d in korok if d is not None), default=None)
        return float("inf") if legfrissebb is None else (most - legfrissebb).days   # never-collected cella = max elavult

    # elavult DESC, majd config-index ASC, majd timeframe-index ASC (determinista tie-break)
    rangsor = sorted(cellak, key=lambda c: (-_elavultsag(c[1].kifejezes, c[3]), c[0], c[2]))
    return [(t, tf) for _, t, _, tf in rangsor[:limit]]


def _masodlagos_ag(bejegyzesek, kliens, config, docs_data_mappa, most, mode="este"):
    """A másodlagos (nap/het) ág: a ma ütemezett szavakat SZAVANKÉNT kéri le és írja.

    LEGUTOLSÓ ág (a pótolhatatlan órás UTÁN). A `kulcsszo_masodlagos` a napló-címke
    és a Kliens-számláló kulcsa → a `naplo.csv`-ben elkülönül az órás `kulcsszo` blokktól.
    429 → CSENDES FELADÁS (saját try/except; NEM propagál, nem block-stop): a futás
    tisztán folytatódik (a nap/het pótolható). SZAVANKÉNTI írás → a blokk ELŐTT lemért
    szavak megmaradnak (a 2026-08-12-i részleges-mentés fix rendszeres éles próbája).
    """
    ag = "kulcsszo_masodlagos"
    try:
        for tetel, timeframe in masodlagos_szavak_ma(config, most, docs_data_mappa, mode=mode):
            rek = kulcsszavak.gyujt_egy_masodlagos(kliens, config, tetel, most, timeframe)
            if rek:
                nyers_kimenet.ir_masodlagos(docs_data_mappa, {tetel.kifejezes: rek})
        bejegyzesek.append({"ag": ag, "eredmeny": "siker",
                            "hivasok_szama": kliens.hivasszam(ag), "hibakodok": ""})
    except AgFeladva as e:
        bejegyzesek.append({"ag": ag, "eredmeny": "blokkolva",
                            "hivasok_szama": kliens.hivasszam(ag), "hibakodok": ",".join(e.hibakodok)})
    except PlafonTullepve:
        # MASODLAGOS-PLAFON: a hívás-plafon HARD (exit 2), de a napló EXPLICIT 'plafon'-t ír (NEM a
        # felső mentő-út 'kihagyva'-ját → nincs összemosás a nem-futott ágakkal), majd PROPAGÁL.
        # A per-szavas írás miatt az addigi szavak a lemezen.
        bejegyzesek.append({"ag": ag, "eredmeny": "plafon",
                            "hivasok_szama": kliens.hivasszam(ag), "hibakodok": "PlafonTullepve"})
        raise


def _rekesz_idosor_ag(bejegyzesek, kliens, config, api_trendek) -> list:
    """LEGUTOLSÓ ág (GORBE-B, forward-only): a holtverseny-rekesz trendjeinek idősora.

    A `_masodlagos_ag`-mintát követi: CSENDES feladás (a `gyujt_rekesz` a 429-et
    elnyeli, nem block-stop, nem exit; a PlafonTullepve HARD marad). KÉTÁLLAPOTÚ
    FIGYELEM (a MASODLAGOS-PLAFON 'kihagyva'-összemosás tanulsága): (a) nincs rekesz
    vs (b) elmaradt N szó, KÜLÖNVÁLASZTVA korlát vs 429. Visszaad: a rekesz-idősor pontjai.
    """
    ag = "idosor_rekesz"
    kerendo, korlat_elmaradt = rekesz_kifejezesek(api_trendek, config)
    if not kerendo:
        # (a) nincs rekesz (üres tie-bucket / D4 0-küszöb) — nincs mit gyűjteni (NEM elmaradás)
        print("FIGYELEM: rekesz-idősor — nincs rekesz (üres tie-bucket), nincs mit gyűjteni.")
        bejegyzesek.append({"ag": ag, "eredmeny": "siker", "hivasok_szama": 0, "hibakodok": ""})
        return []
    try:
        pontok, elmaradt_429 = idosorok.gyujt_rekesz(kliens, config, kerendo)
    except PlafonTullepve:
        # a hívás-plafon HARD (exit 2) — a napló EXPLICIT 'plafon' (NEM 'kihagyva'), majd PROPAGÁL
        bejegyzesek.append({"ag": ag, "eredmeny": "plafon",
                            "hivasok_szama": kliens.hivasszam(ag), "hibakodok": "PlafonTullepve"})
        raise
    # (b) elmaradás KÜLÖNVÁLASZTVA a FIGYELEM-ben ÉS a naplóban is: a napló-kódok KIMERÍTŐK és
    # megkülönböztetők — 'korlat:N' (by-design cap, NEM hiba) vs '429:M' (soft-fail). Nem mosódnak össze.
    if korlat_elmaradt:
        print(f"FIGYELEM: rekesz-idősor — {korlat_elmaradt} rekesz-szó elmaradt "
              f"(korlát: trend_idosor_rekesz_max={config.trend_idosor_rekesz_max}).")
    if elmaradt_429:
        print(f"FIGYELEM: rekesz-idősor — {elmaradt_429} rekesz-szó elmaradt (429).")
    kodok = []
    if korlat_elmaradt:
        kodok.append(f"korlat:{korlat_elmaradt}")
    if elmaradt_429:
        kodok.append(f"429:{elmaradt_429}")
    # eredmeny: 429 = 'reszleges' (soft-fail); a PUSZTA korlát 'siker' (a cap by-design, nem hiba)
    bejegyzesek.append({"ag": ag, "eredmeny": "reszleges" if elmaradt_429 else "siker",
                        "hivasok_szama": kliens.hivasszam(ag), "hibakodok": ",".join(kodok)})
    return pontok


def _jelez_elavult_masodlagos(docs_data_mappa, most):
    """Ha egy másodlagos szó legfrissebb `lekerdezes_utc`-je > 10 napja (kimaradt a
    rotációból / tartósan blokkolt), FIGYELEM a run.log-ba. A success-vakság ellenszere:
    a nap/het ág némán is elavulhat. Derivált, IDEMPOTENS napi jelzés (a forrás-tény a
    commitolt fájlban van); ha nincs elavult, NÉMA (a néma siker itt helyes).
    """
    fajl = Path(docs_data_mappa) / "kulcsszo_masodlagos_nyers.json"
    if not fajl.exists():
        return
    try:
        sorozatok = json.loads(fajl.read_text(encoding="utf-8")).get("kulcsszavak", {})
    except (ValueError, OSError):
        return
    elavultak = nyers_kimenet.elavult_masodlagos_szavak(sorozatok, most)
    if not elavultak:
        return
    reszek = [f"{kif} ({napok} napja)" if napok is not None else f"{kif} (nincs adat)"
              for kif, napok in elavultak]
    print(f"FIGYELEM: elavult másodlagos: {', '.join(reszek)}")


def rangsorolt_trendek(api_trendek) -> list:
    """Az api-trendek volumen-CSÖKKENŐ rangsora, tie-break az EREDETI API-POZÍCIÓ (a
    rendezés ELŐTTI lista-index). A `sorted` ma is stabil, de az explicit (index) kulcs
    egy jövőbeli refaktor ellen is véd. EGYETLEN közös forrás a megjelenített és az
    idősoros listához → a prefix-invariáns szerkezetileg teljesül."""
    return [t for _, t in sorted(
        enumerate(api_trendek),
        key=lambda p: (-felkapott.volumen_szam(p[1]), p[0]))]


def megjelenitendo_trendek(api_trendek, config) -> list:
    """A MEGJELENÍTETT trendlista (spec §7.3 D1–D4). Alap: a top `trend_idosor_max`
    (változatlan). Kiterjesztés (D1): a levágott lista UTOLSÓ elemének volumenével
    MEGEGYEZŐ további trendek is bekerülnek (a teljes holtverseny-rekesz). Felső korlát
    (D3): `max(trend_megjelenites_max, trend_idosor_max)`, a vágás a tie-break szerint.
    0-kapu (D4): ha a küszöb-volumen 0, a kiterjesztés ELMARAD (az alap top-N változatlan)."""
    rangsor = rangsorolt_trendek(api_trendek)
    alap = rangsor[: config.trend_idosor_max]
    if not alap:
        return alap                                    # üres bemenet → üres kimenet, kivétel nélkül
    kuszob = felkapott.volumen_szam(alap[-1])           # a LEVÁGOTT lista tényleges utolsó eleme (nem [max-1] index)
    if kuszob == 0:
        return alap                                     # D4: 0-volumenű küszöb → nincs kiterjesztés
    korlat = max(config.trend_megjelenites_max, config.trend_idosor_max)
    bovitett = [t for t in rangsor if felkapott.volumen_szam(t) >= kuszob]
    return bovitett[:korlat]                             # D3: felső korlát, a rangsor (tie-break) szerint vágva


def rekesz_kifejezesek(api_trendek, config) -> tuple:
    """A holtverseny-rekesz kifejezései (GORBE-B): a MEGJELENÍTETT lista top-N feletti
    farka, a `trend_idosor_rekesz_max` korlátra vágva. A megjelenitendo_trendek KÖZÖS
    forrás (prefix-invariáns) → a rekesz PONTOSAN a megjelenített, de idősor nélküli szavak.
    Visszaad: (kerendo, korlat_elmaradt) — a korlat_elmaradt a korlát miatt le NEM kért szavak.
    """
    megj = megjelenitendo_trendek(api_trendek, config)
    farok = [getattr(t, "keyword", "") for t in megj[config.trend_idosor_max:]]
    kerendo = farok[: config.trend_idosor_rekesz_max]
    return kerendo, len(farok) - len(kerendo)


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

    legnagyobbak = megjelenitendo_trendek(api_trendek, config)

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


def parositas_szamit(rss_trendek, api_trendek, top_trendek):
    """RSS↔API párosítás-diagnosztika (TISZTA: nincs IO/óra/hálózat). Visszaad:
    (rss_db, api_egyezes, megjelenitett_hirrel, nem_egyezok).

    A kérdés: az RSS-halmaz részhalmaza-e az api_trendek TELJES keyword-halmazának
    (NEM a top-N/megjelenített listának). A rss_db és a nem_egyezok az rss_trendek-ből
    KÖZVETLENÜL (NEM a hir_sorok-ból — az kihagyná a hír nélküli RSS-trendet). A
    nem_egyezok az RSS EREDETI SORRENDJÉBEN (nem halmaz-iterációból, ami futásonként
    ingadozna). A megjelenitett_hirrel a MEGLÉVŐ top_trendek["hirek"] mezőből, nem újraszámolva.
    Üres bemenet → (0, 0, 0, [])."""
    api_kulcsok = {getattr(t, "keyword", "") for t in api_trendek}
    rss_kulcsok = [getattr(t, "keyword", "") for t in rss_trendek]
    nem_egyezok = [k for k in rss_kulcsok if k not in api_kulcsok]
    api_egyezes = len(rss_kulcsok) - len(nem_egyezok)
    megjelenitett_hirrel = sum(1 for t in top_trendek if t["hirek"])
    return len(rss_trendek), api_egyezes, megjelenitett_hirrel, nem_egyezok


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
    except PlafonTullepve as e:  # hívás-plafon → HARD ABORT: hangos jel + propagál (nem néma 'hiba')
        bejegyzesek.append({"ag": ag, "eredmeny": "plafon",
                            "hivasok_szama": kliens.hivasszam(ag), "hibakodok": type(e).__name__})
        print(f"FIGYELEM: a(z) '{ag}' ág HÍVÁS-PLAFONT lépett túl ({e}) — a futás leáll (exit {KILEPES_PLAFON}).")
        raise
    except Exception as e:
        hibakodok = ",".join(getattr(e, "hibakodok", []) or [type(e).__name__])
        bejegyzesek.append({"ag": ag, "eredmeny": "hiba",
                            "hivasok_szama": kliens.hivasszam(ag), "hibakodok": hibakodok})
        print(f"FIGYELEM: a(z) '{ag}' ág elbukott ({e}).")
        return None


def futtat(config, kliens, adatok_mappa, docs_data_mappa, most=None, mode="este") -> int:
    """A teljes futás: négy ág, öt CSV, JSON-export, napló, kilépési kód.

    `mode="reggel"`: csak a felkapott/idősor ágak futnak (a kulcsszó-ág és a belőle
    származtatott lépések kimaradnak), a napi_ir a 'reggel' szegmensbe ír, a
    legfrissebb.json kulcsszó-része megőrződik. `mode="este"` (alap) = a teljes futás.
    """
    csak_felkapott = (mode == "reggel")
    if most is None:
        most = seged.most_utc()
    adatok_mappa = Path(adatok_mappa)
    docs_data_mappa = Path(docs_data_mappa)
    adatok_mappa.mkdir(parents=True, exist_ok=True)

    idobelyeg = seged.bp_idobelyeg(most)
    letoltve = most.isoformat(timespec="seconds")
    # este-mód: a LOGIKAI esti nap (hajnali backup = az ELŐZŐ este pótlása, nincs hamis
    # másnapi esti szegmens); reggel-mód: a budapesti naptári nap (nincs hajnali eset).
    nap_iso = (most.astimezone(seged.BUDAPEST).date().isoformat()
               if csak_felkapott else seged.esti_nap(most))

    bejegyzesek = []
    plafon_tullepes = False           # L4: a hívás-plafon tüzelt-e (→ KILEPES_PLAFON exit)
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
        if csak_felkapott:
            kulcsszo_pontok, kulcsszo_napi_pontok, kulcsszo_nyers = [], {}, {}
        else:
            kulcsszo_eredmeny = _ag(bejegyzesek, kliens, "kulcsszo",
                                lambda: kulcsszavak.gyujt(kliens, config, most))
            kulcsszo_pontok, kulcsszo_napi_pontok, kulcsszo_nyers = kulcsszo_eredmeny or ([], {}, {})
        # a KÖZÖS rangsor kifejezéslistája (a megjelenítéssel azonos forrás → prefix-invariáns);
        # az idősor-ág belül vág trend_idosor_max-ra, a hívásköltség NEM nő
        top_kifejezesek = [getattr(t, "keyword", "") for t in rangsorolt_trendek(api_trendek)]
        trend_idosorok = _ag(bejegyzesek, kliens, "idosor",
                            lambda: idosorok.gyujt(kliens, config, top_kifejezesek)) or []
        # másodlagos (nap/het) ág — LEGUTOLSÓ, pótolható; csendes feladás (saját try/except,
        # NEM block-stop). Ha egy korábbi ág block-stopol, ide nem jutunk → a lenti except
        # az AGAK-ban "kulcsszo_masodlagos"-t "kihagyva"-ra teszi.
        if not csak_felkapott:
            _masodlagos_ag(bejegyzesek, kliens, config, docs_data_mappa, most)
        # rekesz-idősor ág — LEGUTOLSÓ (GORBE-B, forward-only): a holtverseny-rekesz
        # trendjei is kapjanak sparkline-t; másodrendű, csendes feladás (nem block-stop/exit).
        # A pontokat a trend_idosorok-hoz fűzzük → a top_trend_struktura idosor_map-je fedi őket.
        trend_idosorok = trend_idosorok + _rekesz_idosor_ag(bejegyzesek, kliens, config, api_trendek)
    except (AgFeladva, PlafonTullepve) as e:
        # KÖZÖS MENTŐ-ÚT: a block-stop (429) ÉS a plafon-túllépés (L4) is a blokk ELŐTT lemért
        # szavakat MENTI (a kivételre akasztott e.reszleges-ből; a másodlagos ág per-szavas írása
        # eleve a lemezen). A plafon-túllépés viszont KILEPES_PLAFON (2) exittel jár, nem 0/1.
        plafon_tullepes = isinstance(e, PlafonTullepve)
        # HATÓKÖR: csak a kivételre akasztott részleg jön vissza; más esetben nincs e.reszleges.
        resz = getattr(e, "reszleges", None)
        if resz:
            kulcsszo_pontok, kulcsszo_napi_pontok, kulcsszo_nyers = resz
            print(f"FIGYELEM: részleges mentés — {len(kulcsszo_nyers)} kulcsszó adata megmaradt a blokk előtt.")
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
    # legfrissebb: az EGYETLEN feltétel nélküli kanonikus felülíró (a tortenet/napi/nyers guardolt).
    # Két guard-réteg, a diszkriminátor az ÁG-STÁTUSZ (NEM a darabszám — a legit csökkenés siker ágon
    # nem nullázza a blokkot, tehát nem fagyaszt; LEGFRISSEBB-RESZLEGES):
    #  (A) RÉGI total-guard (a (B) RÉSZHALMAZA): MIND a 3 blokk üres (bármely okból) → skip.
    #  (B) RÉSZLEGES-hiba: egy MAG-blokk ÜRES, MERT az ága BUKOTT → a részleges NE írja felül a jó TELJES fájlt.
    # A top_trendek NEM mag: bukása (felkapott_api) block-stopol → mindent kiürít → (A) fedi.
    _lf_reszek = {"top_trendek": top_trendek, "trend_idosorok": trend_idosorok, "kulcsszavak": kulcsszo_pontok}
    _lf_ures = [nev for nev, ertek in _lf_reszek.items() if not ertek]
    _LF_MAG_AG = {"kulcsszavak": "kulcsszo", "trend_idosorok": "idosor"}
    _LF_AG_BUKOTT = {"blokkolva", "kihagyva", "plafon", "hiba"}
    _lf_ag = {b["ag"]: b for b in bejegyzesek}
    _lf_reszleges = [(blokk, _lf_ag[ag]) for blokk, ag in _LF_MAG_AG.items()
                     if not _lf_reszek[blokk] and _lf_ag.get(ag, {}).get("eredmeny") in _LF_AG_BUKOTT]
    if len(_lf_ures) == len(_lf_reszek):
        print(f"FIGYELEM: legfrissebb.json kiírása KIHAGYVA — a futás nulla érdemi adatot termelt "
              f"(üres: {', '.join(_lf_ures)}); a meglévő fájl érintetlen.")
    elif _lf_reszleges:
        _megorzott = _legfrissebb_frissitve_datum(docs_data_mappa)
        print("FIGYELEM: legfrissebb.json felülírása KIHAGYVA — RÉSZLEGES futás (ág-hiba):")
        for _blokk, _be in _lf_reszleges:
            _kod = f" — {_be['hibakodok']}" if _be.get("hibakodok") else ""
            print(f"  üres blokk: {_blokk!r} (a(z) {_be['ag']!r} ág: {_be['eredmeny']}{_kod})")
        print(f"  a jó TELJES fájl ÉRINTETLEN — marad a(z) {_megorzott} teljes snapshotja.")
    else:
        json_export.legfrissebb_ir(docs_data_mappa, top_trendek, trend_idosorok,
                                   kulcsszo_pontok, letoltve, config.geo,
                                   valtas_datum=config.modszertan_valtas,
                                   kulcsszo_megorzes=(json_export.legfrissebb_kulcsszo_megorzes(docs_data_mappa)
                                                      if csak_felkapott else None))

    van_adat = bool(api_trendek or rss_trendek or trend_idosorok or kulcsszo_pontok)
    # független feltételek: üres kulcsszó-napi adat NE írja felül a meglévő
    # (jó) tortenet.json-bejegyzéseket; üres top-trend NE hozzon üres napi fájlt
    # tortenet: a valós adat-napokra (utolsó N teljes nap), NEM a futás napjára —
    # a legfrissebb nap felülír, a régebbiek insert-if-absent (visszapótlás)
    if kulcsszo_napi_pontok and not csak_felkapott:
        json_export.tortenet_frissit_napok(docs_data_mappa, kulcsszo_napi_pontok,
                                           valtas_datum=config.modszertan_valtas)
    if top_trendek:
        json_export.napi_ir(docs_data_mappa, nap_iso, top_trendek,
                            szegmens=("reggel" if csak_felkapott else "este"),
                            frissitve_iso=letoltve)
    # nyers órás sorozat verziókövetett gördülő kimenete (üres sorozat NE írjon fájlt)
    if kulcsszo_nyers and not csak_felkapott:
        nyers_kimenet.ir_gordulo(docs_data_mappa, kulcsszo_nyers)
        # LANC-ORAS (§8.2): a perzisztens órás lánc frissítése a RETENÁLT ablakokból (a most kiírt fájlból);
        # bootstrap vagy napi bővítés + POTÓLHATATLANSÁG-guard. Származtatott, VÉDETT (hiba nem viszi el az adatmentést).
        try:
            _retenalt = json.loads((docs_data_mappa / "kulcsszo_nyers.json").read_text(encoding="utf-8")).get("kulcsszavak", {})
            lanc.frissit_lanc(docs_data_mappa, _retenalt, marker=config.modszertan_valtas)
        except Exception as e:
            print(f"FIGYELEM: az órás lánc frissítése kimaradt — nem blokkolja az adatmentést ({e}).")

    # ---------- kategória-aggregátum (származtatott, VÉDETTEN; CSAK naplóz) ----------
    # A napok/*.json determinisztikus tükre → kategoriak.json (spec 8.1). Nulla Google-hívás.
    # A regresszió-ág védelmi mintája: hiba SOHA nem viheti el az adatmentést/exit-kódot,
    # de NEM néma (finding 6) — FIGYELEM a run.log-ba + kategoriak naplósor.
    try:
        kategoriak.kategoriak_ir(docs_data_mappa)
        bejegyzesek.append({"ag": "kategoriak", "eredmeny": "siker",
                            "hivasok_szama": 0, "hibakodok": ""})
    except Exception as e:
        bejegyzesek.append({"ag": "kategoriak", "eredmeny": "hiba",
                            "hivasok_szama": 0, "hibakodok": type(e).__name__})
        print(f"FIGYELEM: a kategória-aggregátum kimaradt — nem blokkolja az adatmentést ({e}).")

    if csak_felkapott:
        pass   # reggeli mód: a származtatott kulcsszó-regressziók KIMARADNAK (nincs friss kulcsszó-adat)
    else:
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
                    regresszio.regresszio_szamit(nyers, tortenet, config, letoltve,
                                                 lanc_map=lanc.betolt_lanc(docs_data_mappa)))
                bejegyzesek.append({"ag": "regresszio", "eredmeny": "siker",
                                    "hivasok_szama": 0, "hibakodok": ""})
            except Exception as e:
                bejegyzesek.append({"ag": "regresszio", "eredmeny": "hiba",
                                    "hivasok_szama": 0, "hibakodok": type(e).__name__})
                print(f"FIGYELEM: a regresszió kimaradt — nem blokkolja az adatmentést ({e}).")

        # ---------- másodlagos (nap/het) regresszió (származtatott, VÉDETTEN; Task 6a) ----------
        # KÜLÖN fájl (kulcsszo_masodlagos_regresszio.json), hogy az órás nézet érintetlen legyen.
        # Nulla Google-hívás; az órás regresszió mintája szerint egy hibája SOHA nem viheti el az
        # adatmentést vagy az exit-kódot, de NEM néma (FIGYELEM + naplósor). A bemenet hiánya → kihagyva.
        masodlagos_nyers_fajl = docs_data_mappa / "kulcsszo_masodlagos_nyers.json"
        if not masodlagos_nyers_fajl.exists():
            bejegyzesek.append({"ag": "regresszio_masodlagos", "eredmeny": "kihagyva",
                                "hivasok_szama": 0, "hibakodok": ""})
        else:
            try:
                masodlagos = json.loads(masodlagos_nyers_fajl.read_text(encoding="utf-8"))
                tortenet_fajl = docs_data_mappa / "tortenet.json"
                tortenet = (json.loads(tortenet_fajl.read_text(encoding="utf-8"))
                            if tortenet_fajl.exists() else {})
                regresszio.regresszio_ir_masodlagos(
                    docs_data_mappa,
                    regresszio.regresszio_masodlagos_szamit(masodlagos, tortenet, config, letoltve))
                bejegyzesek.append({"ag": "regresszio_masodlagos", "eredmeny": "siker",
                                    "hivasok_szama": 0, "hibakodok": ""})
            except Exception as e:
                bejegyzesek.append({"ag": "regresszio_masodlagos", "eredmeny": "hiba",
                                    "hivasok_szama": 0, "hibakodok": type(e).__name__})
                print(f"FIGYELEM: a másodlagos regresszió kimaradt — nem blokkolja az adatmentést ({e}).")

    # ---------- folytonosság-diagnosztika (B2, származtatott; CSAK naplóz, VÉDETTEN) ----------
    # A napi_ir ekkorra már beírta a mai nap_iso-t az index.json-ba. Az utolsó két rögzített
    # dátum köze mutatja, kimaradt-e futás (belső folytonosság, NEM a „ma"-hoz mérve). CSAK
    # naplóz: egy múltbeli rés nem viheti el a ma összegyűjtött adatot (mint a regresszio-ág).
    # VÉDETTEN (C1): sérült/nem-dict/olvashatatlan index.json (JSONDecodeError/AttributeError/OSError)
    # SEM viheti el az EGÉSZ futás naplóját — hiba esetén folytonossag;hiba sor + FIGYELEM, futás tovább.
    # A bejegyzes MINDIG bekerül (heartbeat), akkor is, ha maga a checker bukott.
    index_fajl = docs_data_mappa / "napok" / "index.json"
    try:
        napok_index = (json.loads(index_fajl.read_text(encoding="utf-8")).get("napok", [])
                       if index_fajl.exists() else [])
        res = seged.utolso_res(napok_index)
        bejegyzesek.append({"ag": "folytonossag",
                            "eredmeny": "hiany" if res else "siker",
                            "hivasok_szama": 0, "hibakodok": ",".join(res)})
    except Exception as e:
        bejegyzesek.append({"ag": "folytonossag", "eredmeny": "hiba",
                            "hivasok_szama": 0, "hibakodok": type(e).__name__})
        print(f"FIGYELEM: a folytonosság-ellenőrzés kimaradt — nem blokkolja a naplót ({e}).")

    # ---------- párosítás-diagnosztika (RSS↔API, származtatott; CSAK naplóz, VÉDETTEN) ----------
    # Ugyanaz a minta, mint a folytonosság/regresszió: 0 Google-hívás, heartbeat (a bejegyzes MINDIG
    # bekerül, akkor is, ha a checker bukik), CSAK naplóz — a diagnosztika hibája nem viheti el a ma
    # összegyűjtött adatot. A kérdés: az RSS-halmaz részhalmaza-e a TELJES api_trendek keyword-
    # halmazának (a hírblokk erre az állításra épülne). A formázás ITT történik, a helper adatot ad.
    try:
        rss_db, api_egyezes, hirrel, nem_egyezok = parositas_szamit(rss_trendek, api_trendek, top_trendek)
        bejegyzesek.append({"ag": "parositas",
                            "eredmeny": "siker" if api_egyezes == rss_db else "hiany",
                            "hivasok_szama": 0,
                            "hibakodok": "|".join([f"{rss_db}/{api_egyezes}/{hirrel}"] + nem_egyezok)})
    except Exception as e:
        bejegyzesek.append({"ag": "parositas", "eredmeny": "hiba",
                            "hivasok_szama": 0, "hibakodok": type(e).__name__})
        print(f"FIGYELEM: a párosítás-diagnosztika kimaradt — nem blokkolja a naplót ({e}).")

    # ---------- másodlagos elavultság-jelzés (Task 4, származtatott; CSAK stdout) ----------
    # Ha egy nap/het szó legfrissebb lekerdezes_utc-je > 10 napja (kimaradt a rotációból vagy
    # tartósan blokkolt), FIGYELEM a run.log-ba. A (B) ütemező csak SZŰKÍTI az elavulás-ablakot;
    # tartós blokknál minden szó némán elavul → ez a success-vakság KÖZVETLEN ellenszere.
    _jelez_elavult_masodlagos(docs_data_mappa, most)

    # ---------- napló ----------
    naplo.naplo_ir(adatok_mappa, letoltve, bejegyzesek, config.naplo_max_sor)

    print(f"Összes Google-hívás: {kliens.osszes_hivas()}")
    if plafon_tullepes:               # L4: a védőkorlát tüzelt → HANGOS, nem-nulla (nem van_adat→0)
        return KILEPES_PLAFON
    return 0 if van_adat else 1


def _legfrissebb_frissitve_datum(docs_data):
    """A meglévő legfrissebb.json 'frissitve' dátuma (a megőrzött TELJES snapshot napja) — a RÉSZLEGES-skip
    FIGYELEM-je NEVEZZE MEG, MELYIK nap marad. Konkrét dátum, nem címke; hiányzó/olvashatatlan fájlnál jelzés."""
    utvonal = Path(docs_data) / "legfrissebb.json"
    try:
        friss = json.loads(utvonal.read_text(encoding="utf-8")).get("frissitve", "")
    except (OSError, ValueError):
        return "ismeretlen (nincs korábbi teljes fájl)"
    return friss[:10] if friss else "ismeretlen (nincs 'frissitve' a meglévő fájlban)"


def _szamitott_plafon(config):
    """A strukturális maximum: minden logikai hívás mind a max_probak próbát kimeríti."""
    return (tervezett_hivasszam(config) + MAX_MASODLAGOS_NAPI) * config.max_probak


def _plafon_override_env():
    """A PLAFON_OVERRIDE env-változó int-ként (a (c) CI-piros-út dispatch-hez), vagy None
    (hiány/érvénytelen → figyelmen kívül; érvénytelenre hangos FIGYELEM)."""
    ny = os.environ.get("PLAFON_OVERRIDE")
    if not ny:                                               # hiány VAGY üres string (cron ág) → None, némán
        return None
    try:
        return int(ny)
    except ValueError:
        print(f"FIGYELEM: PLAFON_OVERRIDE értéke érvénytelen ({ny!r}) — figyelmen kívül hagyva.")
        return None


def _plafon(config, override=None):
    """A tényleges hívás-plafon. Az override CSAK CSÖKKENTHET (min) — a biztonsági szelepet
    egy bent felejtett/magas env NE kapcsolhassa ki csendben. Ha az env be van állítva, HANGOS
    FIGYELEM (akkor is, ha no-op), hogy ne lehessen véletlenül bent felejteni."""
    szamitott = _szamitott_plafon(config)
    if override is None:
        return szamitott
    eff = min(szamitott, override)                            # sosem emel
    jelzo = "CSÖKKENTVE" if eff < szamitott else f"NO-OP (a számított {szamitott} marad)"
    print(f"FIGYELEM: PLAFON_OVERRIDE={override} beállítva — effektív hívás-plafon {eff} ({jelzo}).")
    return eff


def _mode_parse(argv):
    """A --mode kapcsoló (reggel/este), alap 'este'. Ismeretlen érték → argparse-hiba."""
    import argparse
    p = argparse.ArgumentParser(description="Trendfigyelő napi/reggeli futtatás.")
    p.add_argument("--mode", choices=["reggel", "este"], default="este")
    return p.parse_args(argv).mode


def main(argv=None) -> int:
    """Belépő: config betöltése, Kliens felépítése, teljes futás a --mode szerint."""
    import sys as _sys
    mode = _mode_parse(_sys.argv[1:] if argv is None else argv)
    config = betolt()
    # hívás-plafon = a strukturális maximum (efölött már csak call-multiplying bug lehet →
    # azonnali leállás). A PLAFON_OVERRIDE env CSAK CSÖKKENTHETI (a (c) CI-igazoláshoz).
    kliens = Kliens(config, plafon=_plafon(config, _plafon_override_env()))
    print(f"Mód: {mode} · Várható Google-hívásszám (429 nélkül): ~{tervezett_hivasszam(config)}")
    return futtat(config, kliens, Path("adatok"), Path("docs") / "data", mode=mode)


if __name__ == "__main__":
    sys.exit(main())
