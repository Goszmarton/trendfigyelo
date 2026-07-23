"""Trend-idősorok ág: top-N trend 24 órás sparkline-ja (geo=HU, now 1-d)."""

from pathlib import Path

from . import seged
from .kliens import AgFeladva


def df_idosor(df, kifejezes: str, forras: str) -> list:
    """Egy oszlopos interest_over_time DataFrame → idősor-pontok."""
    pontok = []
    if df is None or len(df) == 0:
        return pontok
    oszlop = kifejezes if kifejezes in df.columns else _elso_ertek_oszlop(df, kifejezes)
    if oszlop is None:
        return pontok
    for idx, sor in df.iterrows():
        pontok.append({
            "kifejezes": kifejezes,
            "idopont_utc": seged.idopont_iso(idx),
            "ertek": int(sor[oszlop]) if _szam(sor[oszlop]) else seged.szovegge(sor[oszlop]),
            "forras": forras,
        })
    return pontok


def _elso_ertek_oszlop(df, kifejezes):
    for c in df.columns:
        if str(c).lower() != "ispartial":
            return c
    return None


def _szam(x) -> bool:
    try:
        int(x)
        return True
    except (ValueError, TypeError):
        return False


def gyujt(kliens, config, top_kifejezesek) -> list:
    """Top-N kifejezés egyenkénti idősora.

    AgFeladva (429-kimerülés) esetén az EGÉSZ ágat feladjuk (a kivétel
    továbbmegy a futtato-hoz block-detektálásra) — nem hammereljük tovább a
    Google-t trendenként. Egyéb hiba csak az adott trendet hagyja ki.
    """
    pontok = []
    for kif in top_kifejezesek[: config.trend_idosor_max]:
        try:
            df = kliens.hivas(
                "idosor", kliens.tr.interest_over_time,
                [kif], geo=config.geo, timeframe=config.idosor_idokeret,
            )
        except AgFeladva:  # 429-kimerülés → az egész ág feladva
            print(f"FIGYELEM: az idősor-ág feladva (429) a(z) '{kif}' kifejezésnél.")
            raise
        except Exception as e:  # egyetlen trend egyéb hibája nem dönti a többit
            print(f"FIGYELEM: '{kif}' idősora kimaradt ({e}).")
            continue
        pontok.extend(df_idosor(df, kif, "interest_over_time"))
    return pontok


def csv_ir(mappa, idobelyeg, letoltve, geo, pontok):
    if not pontok:
        return None
    fajl = Path(mappa) / f"top_trend_idosor_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow(["kifejezes", "idopont_utc", "ertek", "letoltve_utc", "forras", "geo"])
        for p in pontok:
            iro.writerow([p["kifejezes"], p["idopont_utc"], p["ertek"], letoltve, p["forras"], geo])
    return fajl
