"""Felkapott keresések ág: trending_now API + RSS → a meglévő 3 CSV (változatlan séma)."""

from pathlib import Path

from . import seged


def volumen_szam(t) -> int:
    """A trend numerikus volumene rendezéshez; hibás/hiányzó → 0."""
    try:
        return int(getattr(t, "volume", 0) or 0)
    except (ValueError, TypeError):
        return 0


def api_trend_dict(t, sorszam: int) -> dict:
    return {
        "sorszam": sorszam,
        "kifejezes": t.keyword,
        "volumen": seged.szovegge(getattr(t, "volume", None)),
        "novekedes_pct": seged.szovegge(getattr(t, "volume_growth_pct", None)),
        "trend_indult_utc": seged.idove(getattr(t, "started_timestamp", None)),
        "trend_veget_ert_utc": seged.idove(getattr(t, "ended_timestamp", None)),
        "aktiv": "nem" if getattr(t, "is_trend_finished", False) else "igen",
        "kapcsolodo_kifejezesek": seged.szovegge(getattr(t, "trend_keywords", None)),
        "temak": seged.szovegge(getattr(t, "topic_names", None)),
        "normalizalt_kifejezes": seged.szovegge(getattr(t, "normalized_keyword", None)),
    }


def rss_trend_dict(t, sorszam: int) -> dict:
    return {
        "sorszam": sorszam,
        "kifejezes": t.keyword,
        "volumen": seged.szovegge(getattr(t, "volume", None)),
        "kapcsolodo_kifejezesek": seged.szovegge(getattr(t, "trend_keywords", None)),
        "trend_indult_utc": seged.idove(getattr(t, "started", None)),
        "kep_url": seged.szovegge(getattr(t, "picture", None)),
        "kep_forras": seged.szovegge(getattr(t, "picture_source", None)),
        "hirek_szama": len(getattr(t, "news", None) or []),
    }


def hir_sorok(rss_trendek) -> list:
    sorok = []
    for i, t in enumerate(rss_trendek, 1):
        for hir in getattr(t, "news", None) or []:
            sorok.append({
                "sorszam": i,
                "kifejezes": t.keyword,
                "hir_cim": seged.szovegge(getattr(hir, "title", None)),
                "hir_forras": seged.szovegge(getattr(hir, "source", None)),
                "hir_url": seged.szovegge(getattr(hir, "url", None)),
                "hir_ido_utc": seged.idove(getattr(hir, "time", None)),
                "hir_kep": seged.szovegge(getattr(hir, "picture", None)),
                "hir_kivonat": seged.szovegge(getattr(hir, "snippet", None)),
            })
    return sorok


def gyujt_api(kliens, config) -> list:
    """trending_now API — a teljes 24 órás HU lista."""
    return kliens.hivas("felkapott_api", kliens.tr.trending_now,
                        geo=config.geo, hours=config.idoablak_orak) or []


def gyujt_rss(kliens, config) -> list:
    """RSS — tartalék + hírek."""
    return kliens.hivas("felkapott_rss", kliens.tr.trending_now_by_rss,
                        geo=config.geo) or []


def csv_ir_api(mappa, idobelyeg, letoltve, geo, api_trendek):
    if not api_trendek:
        return None
    fajl = Path(mappa) / f"top_keresesek_api_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow([
            "sorszam", "kifejezes", "volumen", "novekedes_pct",
            "trend_indult_utc", "trend_veget_ert_utc", "aktiv",
            "kapcsolodo_kifejezesek", "temak", "normalizalt_kifejezes",
            "letoltve_utc", "forras", "geo",
        ])
        for i, t in enumerate(api_trendek, 1):
            d = api_trend_dict(t, i)
            iro.writerow([
                d["sorszam"], d["kifejezes"], d["volumen"], d["novekedes_pct"],
                d["trend_indult_utc"], d["trend_veget_ert_utc"], d["aktiv"],
                d["kapcsolodo_kifejezesek"], d["temak"], d["normalizalt_kifejezes"],
                letoltve, "trending_now", geo,
            ])
    return fajl


def csv_ir_rss(mappa, idobelyeg, letoltve, geo, rss_trendek):
    if not rss_trendek:
        return None
    fajl = Path(mappa) / f"top_keresesek_rss_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow([
            "sorszam", "kifejezes", "volumen", "kapcsolodo_kifejezesek",
            "trend_indult_utc", "kep_url", "kep_forras", "hirek_szama",
            "letoltve_utc", "forras", "geo",
        ])
        for i, t in enumerate(rss_trendek, 1):
            d = rss_trend_dict(t, i)
            iro.writerow([
                d["sorszam"], d["kifejezes"], d["volumen"], d["kapcsolodo_kifejezesek"],
                d["trend_indult_utc"], d["kep_url"], d["kep_forras"], d["hirek_szama"],
                letoltve, "rss", geo,
            ])
    return fajl


def csv_ir_hirek(mappa, idobelyeg, geo, rss_trendek):
    if not rss_trendek:
        return None
    fajl = Path(mappa) / f"top_keresesek_hirek_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow([
            "sorszam", "kifejezes", "hir_cim", "hir_forras", "hir_url",
            "hir_ido_utc", "hir_kep", "hir_kivonat",
        ])
        for s in hir_sorok(rss_trendek):
            iro.writerow([
                s["sorszam"], s["kifejezes"], s["hir_cim"], s["hir_forras"],
                s["hir_url"], s["hir_ido_utc"], s["hir_kep"], s["hir_kivonat"],
            ])
    return fajl
