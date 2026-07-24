"""Kulcsszó-idősorok ág: 4+1 kötegelt interest_over_time, nyers + normalizált érték."""

from datetime import datetime, timezone
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
        f = float(x)
    except (ValueError, TypeError):
        return False
    return f == f  # NaN esetén False (NaN != NaN)


def _bp_datum(idx):
    """Egy (pandas) index-időbélyeg budapesti naptári dátuma."""
    dt = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(seged.BUDAPEST).date()


def utolso_teljes_nap(df, mai_datum):
    """A df budapesti dátumai közül a legnagyobb, amely < mai_datum; egyébként None."""
    if df is None or len(df) == 0:
        return None
    korabbi = {_bp_datum(idx) for idx in df.index if _bp_datum(idx) < mai_datum}
    return max(korabbi) if korabbi else None


def _ref_atlag(df, ref):
    """A referenciaszó nem-nulla pontjainak átlaga; ha nincs mérhető pont, None."""
    if ref not in df.columns:
        return None
    ertekek = [float(x) for x in df[ref] if _szam(x) and float(x) != 0.0]
    if not ertekek:
        return None
    return sum(ertekek) / len(ertekek)


def utolso_N_teljes_nap(df, mai_datum, n: int) -> list:
    """A df budapesti dátumai közül az utolsó n, amely < mai_datum; növekvő sorrendben."""
    if df is None or len(df) == 0:
        return []
    korabbi = sorted({_bp_datum(idx) for idx in df.index if _bp_datum(idx) < mai_datum})
    return korabbi[-n:]


def parse_koteg_napok(df, koteg, mai_datum, min_atlag, n: int) -> dict:
    """Köteg DataFrame → {nap_iso: [pontok]} az utolsó n teljes napra (üres napok nélkül)."""
    if df is None or len(df) == 0:
        return {}
    ki = {}
    for nap in utolso_N_teljes_nap(df, mai_datum, n):
        napi = df[[_bp_datum(idx) == nap for idx in df.index]]
        pontok = _parse_egy_nap(napi, koteg, min_atlag)
        if pontok:
            ki[nap.isoformat()] = pontok
    return ki


def _parse_egy_nap(napi, koteg, min_atlag) -> list:
    """Egy nap (már leszűrt) DataFrame-je → pontok, nyers + (érvényes ref-nél) normalizált."""
    pontok = []
    ref = koteg["referenciaszo"]
    ref_atlag = _ref_atlag(napi, ref)
    ervenyes = ref_atlag is not None and ref_atlag >= min_atlag
    sk = skalazo([ref_atlag]) if ervenyes else None  # 100 / ref_atlag
    for kulcsszo, csoport in koteg["tagok"]:
        if kulcsszo not in napi.columns:
            continue
        for idx, sor in napi.iterrows():
            nyers = sor[kulcsszo]
            if _szam(nyers):
                nyers_ert = int(nyers)
                norm = round(float(nyers) * sk, 2) if sk is not None else ""
            else:
                nyers_ert = ""
                norm = ""
            pontok.append({
                "kulcsszo": kulcsszo,
                "csoport": csoport,
                "idopont_utc": seged.idopont_iso(idx),
                "nyers_ertek": nyers_ert,
                "normalizalt_ertek": norm,
                "koteg_id": koteg["id"],
                "referenciaszo": ref,
                "referencia_atlag": round(ref_atlag, 2) if ref_atlag is not None else "",
                "referencia_ervenyes": ervenyes,
            })
    return pontok


def parse_koteg(df, koteg, mai_datum, min_atlag) -> list:
    """Köteg DataFrame → pontok az UTOLSÓ TELJES napra szűrve."""
    if df is None or len(df) == 0:
        return []
    nap = utolso_teljes_nap(df, mai_datum)
    if nap is None:
        return []
    napi = df[[_bp_datum(idx) == nap for idx in df.index]]
    return _parse_egy_nap(napi, koteg, min_atlag)


def aggregalt_nap(pontok):
    """A pontok közös budapesti napja ISO-ban ('%Y-%m-%d'); üres lista → None."""
    for p in pontok:
        iso = p.get("idopont_utc")
        if iso:
            return f"{datetime.fromisoformat(iso).astimezone(seged.BUDAPEST):%Y-%m-%d}"
    return None


def gyujt(kliens, config, most=None) -> list:
    """Minden köteget lekér (now 7-d), és az utolsó teljes napra parse-ol.

    AgFeladva (429) → az EGÉSZ ág feladva (továbbmegy a futtato-hoz). Egyéb hiba
    csak az adott köteget hagyja ki.
    """
    most = most or seged.most_utc()
    mai_datum = most.astimezone(seged.BUDAPEST).date()
    pontok = []
    for koteg in kotegek(config):
        szavak = koteg_lekerdezes_szavai(koteg)
        try:
            df = kliens.hivas(
                "kulcsszo", kliens.tr.interest_over_time,
                szavak, geo=config.geo, timeframe=config.kulcsszo_idokeret,
            )
        except AgFeladva:
            print(f"FIGYELEM: a kulcsszó-ág feladva (429) a(z) {koteg['id']}. kötegnél.")
            raise
        except Exception as e:
            print(f"FIGYELEM: a(z) {koteg['id']}. köteg kimaradt ({e}).")
            continue
        pontok.extend(parse_koteg(df, koteg, mai_datum, config.referencia_min_atlag))
    return pontok


def csv_ir(mappa, idobelyeg, letoltve, geo, pontok):
    if not pontok:
        return None
    fajl = Path(mappa) / f"kulcsszo_idosor_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow([
            "kulcsszo", "csoport", "idopont_utc", "nyers_ertek", "normalizalt_ertek",
            "koteg_id", "referenciaszo", "referencia_atlag", "letoltve_utc", "geo",
        ])
        for p in pontok:
            iro.writerow([
                p["kulcsszo"], p["csoport"], p["idopont_utc"], p["nyers_ertek"],
                p["normalizalt_ertek"], p["koteg_id"], p["referenciaszo"],
                p["referencia_atlag"], letoltve, geo,
            ])
    return fajl
