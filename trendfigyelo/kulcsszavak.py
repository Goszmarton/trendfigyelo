"""Kulcsszó-idősorok ág: 4+1 kötegelt interest_over_time, nyers + normalizált érték."""

from pathlib import Path

from . import seged
from .kliens import AgFeladva

KOTEG_MERET = 4  # 4 kulcsszó + 1 referenciaszó = 5 (a Trends max 5-öt hasonlít össze)


def kotegek(config) -> list:
    """A kulcsszavakat 4-es kötegekre bontja, mindegyikbe a referenciaszóval."""
    parok = config.osszes_kulcsszo()
    kotek = []
    for i in range(0, len(parok), KOTEG_MERET):
        kotek.append({
            "id": i // KOTEG_MERET,
            "tagok": parok[i : i + KOTEG_MERET],
            "referenciaszo": config.referenciaszo,
        })
    return kotek


def koteg_lekerdezes_szavai(koteg) -> list:
    """A köteg 4 kulcsszava + a referenciaszó (utolsóként)."""
    return [kulcsszo for kulcsszo, _ in koteg["tagok"]] + [koteg["referenciaszo"]]


def skalazo(ref_ertekek):
    """100 / referenciaszó-átlag, ha az átlag > 0, különben None."""
    ervenyes = [float(x) for x in ref_ertekek if _szam(x)]
    if not ervenyes:
        return None
    atlag = sum(ervenyes) / len(ervenyes)
    return 100.0 / atlag if atlag > 0 else None


def _szam(x) -> bool:
    try:
        float(x)
        return True
    except (ValueError, TypeError):
        return False


def parse_koteg(df, koteg) -> list:
    """Köteg DataFrame → pontok nyers és normalizált értékkel."""
    pontok = []
    if df is None or len(df) == 0:
        return pontok
    ref = koteg["referenciaszo"]
    sk = skalazo(list(df[ref])) if ref in df.columns else None
    for kulcsszo, csoport in koteg["tagok"]:
        if kulcsszo not in df.columns:
            continue
        for idx, sor in df.iterrows():
            nyers = sor[kulcsszo]
            nyers_ert = int(nyers) if _szam(nyers) else seged.szovegge(nyers)
            norm = round(float(nyers) * sk, 2) if (sk is not None and _szam(nyers)) else ""
            pontok.append({
                "kulcsszo": kulcsszo,
                "csoport": csoport,
                "idopont_utc": seged.idopont_iso(idx),
                "nyers_ertek": nyers_ert,
                "normalizalt_ertek": norm,
                "koteg_id": koteg["id"],
                "referenciaszo": ref,
            })
    return pontok


def gyujt(kliens, config) -> list:
    """Minden köteget lekér és parse-ol.

    AgFeladva (429-kimerülés) esetén az EGÉSZ ágat feladjuk (a kivétel
    továbbmegy a futtato-hoz block-detektálásra) — nem hammereljük tovább a
    Google-t kötegenként. Egyéb hiba csak az adott köteget hagyja ki.
    """
    pontok = []
    for koteg in kotegek(config):
        szavak = koteg_lekerdezes_szavai(koteg)
        try:
            df = kliens.hivas(
                "kulcsszo", kliens.tr.interest_over_time,
                szavak, geo=config.geo, timeframe=config.idosor_idokeret,
            )
        except AgFeladva:  # 429-kimerülés → az egész ág feladva
            print(f"FIGYELEM: a kulcsszó-ág feladva (429) a(z) {koteg['id']}. kötegnél.")
            raise
        except Exception as e:  # egyetlen köteg egyéb hibája nem dönti a többit
            print(f"FIGYELEM: a(z) {koteg['id']}. köteg kimaradt ({e}).")
            continue
        pontok.extend(parse_koteg(df, koteg))
    return pontok


def csv_ir(mappa, idobelyeg, letoltve, geo, pontok):
    if not pontok:
        return None
    fajl = Path(mappa) / f"kulcsszo_idosor_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow([
            "kulcsszo", "csoport", "idopont_utc", "nyers_ertek", "normalizalt_ertek",
            "koteg_id", "referenciaszo", "letoltve_utc", "geo",
        ])
        for p in pontok:
            iro.writerow([
                p["kulcsszo"], p["csoport"], p["idopont_utc"], p["nyers_ertek"],
                p["normalizalt_ertek"], p["koteg_id"], p["referenciaszo"], letoltve, geo,
            ])
    return fajl
