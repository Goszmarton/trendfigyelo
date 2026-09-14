"""LOESS-alapú, csillapított-trendű előrejelzés empirikus (visszatesztelt) hibasávval.
Tiszta numpy, determinista. A számítás a napi futásban, a regresszió után fut (0 Google-hívás).

A forecast SIMA csillapított trend (SZEZON NÉLKÜL): a szezon-komponens a charton zajnak
látszik és a néző számára félrevezető, a bizonytalansági SÁV úgyis hordozza a bizonytalanságot.
A trend a LOESS-görbe NAGYOBB szakaszából (utolsó fele) becsült, hogy az irány stabil legyen."""
import numpy as np
from datetime import datetime, timedelta
from .ml_trend import loess

# horizont -> naptári NAP (a lépésszám = nap · 86400 / felbontás-lépés → felbontás-független horizont)
HORIZONT_NAP = {"1_nap": 1, "1_het": 7, "1_ho": 30, "3_ho": 90, "1_ev": 365}
FIGYELMEZTETETT = {"3_ho", "1_ev"}          # a charton + gombon „szemléltető — nagy bizonytalanság"

def _szint_trend(sim, w):
    """L = a (LOESS) simító utolsó értéke; b = az utolsó `w` pontjára illesztett egyenes
    meredeksége (per lépés). NAGY `w` (a görbe jelentős szakasza) → stabil, nem ugráló irány."""
    sim = np.asarray(sim, float)
    n = len(sim)
    w = int(min(max(w, 3), n))
    xs = np.arange(w, dtype=float)
    ys = sim[-w:]
    xm = xs.mean(); ym = ys.mean()
    denom = float(((xs - xm) ** 2).sum())
    b = float(((xs - xm) * (ys - ym)).sum() / denom) if denom > 0 else 0.0
    return float(sim[-1]), b

def _damped_sor(L, b, H, phi):
    """Csillapított-trend előrejelzés: ŷ(h) = L + b·Σ_{i=1..h} φ^i, h=1..H → (H,) vektor.
    φ<1 → a trend hozzájárulása b·φ/(1-φ)-hoz telít (ellaposodik, nem szalad el)."""
    i = np.arange(1, int(H) + 1)
    kum = phi * (1.0 - phi ** i) / (1.0 - phi)
    return L + b * kum

def elorejelzes(y, sim, H, phi=0.95):
    """H-lépéses SIMA csillapított előrejelzés (SZEZON NÉLKÜL), [0,100]-ra vágva → (H,) tömb.
    A trend a LOESS-görbe utolsó felének (min 8 pont) robusztus meredekségéből."""
    sim = np.asarray(sim, float)
    n = len(sim)
    L, b = _szint_trend(sim, w=max(8, n // 2))
    return np.clip(_damped_sor(L, b, H, phi), 0.0, 100.0)

def _olcso_sim(y, ablak=None):
    """Olcsó, szél-korrigált mozgóátlag-simító a backteszthez (NEM teljes LOESS minden origón)."""
    y = np.asarray(y, float); n = len(y)
    w = ablak or max(3, min(n // 5, 25))
    if w % 2 == 0:
        w += 1
    sim = np.convolve(y, np.ones(w) / w, mode="same")
    fel = w // 2
    for i in list(range(fel)) + list(range(n - fel, n)):   # szél: részleges átlag
        sim[i] = y[max(0, i - fel):min(n, i + fel + 1)].mean()
    return sim

def _backteszt_rmse(y, H, phi, K):
    """Gördülő-origó visszatesztelés: az utolsó K origóból H-lépés előrejelzés, RMSE(h)
    horizontonként (az él-simító OLCSÓ mozgóátlag). Hiányzó h → reziduál-alapú fallback
    (σ·√h). Végül KUMULATÍV MAX → monoton nem-csökkenő (a sáv nem szűkül vissza)."""
    y = np.asarray(y, float); n = len(y)
    H = int(H)
    hibak = [[] for _ in range(H)]
    origok = [o for o in range(max(16, n - K), n) if o < n]
    for o in origok:
        yo = y[:o]
        po = elorejelzes(yo, _olcso_sim(yo), min(H, n - o), phi)
        for h in range(len(po)):
            if o + h < n:
                hibak[h].append(y[o + h] - po[h])
    resid = float(np.std(y - _olcso_sim(y))) or 1.0
    rmse = np.array([float(np.sqrt(np.mean(np.square(hibak[h])))) if hibak[h]
                     else resid * np.sqrt(h + 1) for h in range(H)])
    return np.maximum.accumulate(rmse)

def _jovo_ido(utolso_iso, lepes_mp, h):
    """Az utolsó ISO-időpont + h·lépés (másodpercben). NINCS datetime.now()."""
    return (datetime.fromisoformat(utolso_iso) + timedelta(seconds=lepes_mp * h)).isoformat()

def _megbizhatosag(rmse_veg):
    return round(float(max(0.0, 1.0 - rmse_veg / 50.0)), 2)   # durva 0–1 (nagy hiba → alacsony)

def sorozat_predikcio(pontok, lepes_mp, horizontok, phi=0.95, z=1.28, K=15, ritkitas=40):
    """EGY sorozatból a kért horizontok teljes blokkjai, a LOESS-t és a backtesztet EGYSZER
    számolva (a rövidebb horizontok a leghosszabb prefixei). Visszaad: {horizont: blokk}.
    A horizont naptári: H = nap · 86400 / lepes_mp (felbontás-független). Kevés pont → {}.

    Blokk: {pont, also, felso (mind [{idopont_utc,ertek}]), rmse_veg, modszer, megbizhatosag,
    figyelmeztetes}. A sáv `ŷ ± z·RMSE(h)` (~80%), [0,100]-ra vágva."""
    y = np.array([p["ertek"] for p in pontok], float)
    n = len(y)
    if n < 24:                                       # túl kevés a stabil illesztéshez
        return {}
    H_map = {h: max(1, round(HORIZONT_NAP[h] * 86400 / lepes_mp)) for h in horizontok if h in HORIZONT_NAP}
    if not H_map:
        return {}
    Hmax = max(H_map.values())
    sim = loess(np.arange(n, dtype=float), y, span=0.4)
    pont_teljes = elorejelzes(y, sim, Hmax, phi)     # a rövidebb horizontok ennek prefixei
    rmse_teljes = _backteszt_rmse(y, Hmax, phi, K)
    utolso = pontok[-1]["idopont_utc"]
    out = {}
    for hz, H in H_map.items():
        pont = pont_teljes[:H]; rmse = rmse_teljes[:H]
        also = np.clip(pont - z * rmse, 0.0, 100.0)
        felso = np.clip(pont + z * rmse, 0.0, 100.0)
        lep = max(1, H // ritkitas)                  # ritkítás ~ritkitas pontra
        idx = list(range(0, H, lep))
        if idx[-1] != H - 1:
            idx.append(H - 1)
        def _pts(arr, _idx=idx):
            return [{"idopont_utc": _jovo_ido(utolso, lepes_mp, i + 1), "ertek": round(float(arr[i]), 1)}
                    for i in _idx]
        out[hz] = {"pont": _pts(pont), "also": _pts(also), "felso": _pts(felso),
                   "rmse_veg": round(float(rmse[-1]), 1), "modszer": "damped-LOESS",
                   "megbizhatosag": _megbizhatosag(rmse[-1]), "figyelmeztetes": hz in FIGYELMEZTETETT}
    return out
