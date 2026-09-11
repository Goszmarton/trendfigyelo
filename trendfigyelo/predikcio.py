"""LOESS-alapú, csillapított-trendű előrejelzés empirikus (visszatesztelt) hibasávval.
Tiszta numpy, determinista. A számítás a napi futásban, a regresszió után fut (0 Google-hívás)."""
import numpy as np
from datetime import datetime, timedelta
from .ml_trend import loess

# horizont -> hány LÉPÉS az adott sorozat felbontásán (1_nap/1_het órás; 1_ho/3_ho napi; 1_ev heti)
HORIZONTOK = {"1_nap": 24, "1_het": 168, "1_ho": 30, "3_ho": 90, "1_ev": 52}
FIGYELMEZTETETT = {"3_ho", "1_ev"}          # a charton + gombon „szemléltető — nagy bizonytalanság"

def _szint_trend(sim, w):
    """L = a (LOESS) simító utolsó értéke; b = az utolsó `w` pontjára illesztett egyenes
    meredeksége (per lépés) — robusztus él-becslés."""
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

def _szezon_profil(y, sim, m):
    """Additív, NULLA-ÁTLAGÚ szezon-profil (m hosszú): a (y - sim) átlagos eltérése fázisonként.
    None, ha m<2 vagy n<2m (nincs ≥2 teljes ciklus → nem becsülhető őszintén)."""
    y = np.asarray(y, float); sim = np.asarray(sim, float)
    n = len(y)
    if not m or m < 2 or n < 2 * m:
        return None
    dev = y - sim
    prof = np.array([dev[k::m].mean() if dev[k::m].size else 0.0 for k in range(m)])
    return prof - prof.mean()

def elorejelzes(y, sim, m, H, phi=0.95):
    """H-lépéses csillapított előrejelzés + additív szezon (ahol becsülhető), [0,100]-ra vágva.
    Visszaad: (pont (H,), szezon_volt bool)."""
    y = np.asarray(y, float); sim = np.asarray(sim, float)
    n = len(y)
    L, b = _szint_trend(sim, w=max(3, min(n // 10, 24)))
    pont = _damped_sor(L, b, H, phi)
    prof = _szezon_profil(y, sim, m)
    if prof is not None:
        faz = ((n - 1) + np.arange(1, int(H) + 1)) % m
        pont = pont + prof[faz]
    return np.clip(pont, 0.0, 100.0), (prof is not None)

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

def _backteszt_rmse(y, m, H, phi, K):
    """Gördülő-origó visszatesztelés: az utolsó K origóból H-lépés előrejelzés, RMSE(h)
    horizontonként (az él-simító OLCSÓ mozgóátlag). Hiányzó h → reziduál-alapú fallback
    (σ·√h). Végül KUMULATÍV MAX → monoton nem-csökkenő (a sáv nem szűkül vissza)."""
    y = np.asarray(y, float); n = len(y)
    H = int(H)
    hibak = [[] for _ in range(H)]
    also = max(2 * (m or 1) + 5, 20)
    origok = [o for o in range(max(also, n - K), n) if o < n]
    for o in origok:
        yo = y[:o]
        po, _ = elorejelzes(yo, _olcso_sim(yo), m, min(H, n - o), phi)
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

def horizont_blokk(pontok, horizont, lepes_mp, m, phi=0.95, z=1.28, K=15, ritkitas=40):
    """Egy horizont teljes blokkja (pont + 80%-os empirikus sáv + jövő-időbélyegek + metaadat).
    None, ha túl kevés pont a stabil illesztéshez (< 3m vagy < 24)."""
    y = np.array([p["ertek"] for p in pontok], float)
    n = len(y)
    minimum = max(3 * (m or 1), 24)
    if n < minimum:
        return None
    H = HORIZONTOK[horizont]
    sim = loess(np.arange(n, dtype=float), y, span=0.4)
    pont, szezon = elorejelzes(y, sim, m, H, phi)
    rmse = _backteszt_rmse(y, m, H, phi, K)
    also = np.clip(pont - z * rmse, 0.0, 100.0)
    felso = np.clip(pont + z * rmse, 0.0, 100.0)
    utolso = pontok[-1]["idopont_utc"]
    lep = max(1, H // ritkitas)                          # ritkítás ~ritkitas pontra
    idx = list(range(0, H, lep))
    if idx[-1] != H - 1:
        idx.append(H - 1)
    def _pts(arr):
        return [{"idopont_utc": _jovo_ido(utolso, lepes_mp, h + 1), "ertek": round(float(arr[h]), 1)} for h in idx]
    megb = round(float(max(0.0, 1.0 - rmse[-1] / 50.0)), 2)   # durva 0–1 megbízhatóság (nagy hiba→alacsony)
    return {"pont": _pts(pont), "also": _pts(also), "felso": _pts(felso),
            "rmse_veg": round(float(rmse[-1]), 1), "szezon": bool(szezon),
            "modszer": "damped-LOESS", "megbizhatosag": megb,
            "figyelmeztetes": horizont in FIGYELMEZTETETT}
