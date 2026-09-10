import numpy as np
from trendfigyelo import ml_trend

def test_loess_sima_gorbet_ad_zajos_parabolan():
    x = np.arange(60, dtype=float)
    tiszta = 50 + 0.02 * (x - 30) ** 2          # parabola
    y = tiszta + np.sin(x)                        # + kis determinista zaj
    sim = ml_trend.loess(x, y, span=0.4)
    assert sim.shape == x.shape
    # a sima görbe közelebb van a tiszta jelhez, mint a nyers y
    assert np.mean((sim - tiszta) ** 2) < np.mean((y - tiszta) ** 2)

def test_cv_r2_determinista_es_a_zajra_nem_ad_jo_illeszkedest():
    x = np.arange(50, dtype=float)
    zaj = np.array([(-1) ** i for i in range(50)], float) * 5   # determinista cikk-cakk (nincs trend)
    def lin_fp(xt, yt, xq):
        b1, b0 = np.polyfit(xt, yt, 1); return b0 + b1 * xq
    r2a = ml_trend.cv_r2(x, zaj, lin_fp)
    r2b = ml_trend.cv_r2(x, zaj, lin_fp)
    assert r2a == r2b            # DETERMINISTA (kétszer ugyanaz)
    assert r2a < 0.1             # zajra nincs érdemi out-of-sample illeszkedés
