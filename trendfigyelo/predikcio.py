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
