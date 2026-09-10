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
