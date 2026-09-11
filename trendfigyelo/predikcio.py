"""LOESS-alapú, csillapított-trendű előrejelzés empirikus (visszatesztelt) hibasávval.
Tiszta numpy, determinista. A számítás a napi futásban, a regresszió után fut (0 Google-hívás)."""
import numpy as np

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
