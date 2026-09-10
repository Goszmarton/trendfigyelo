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

def _pontok(ertekek):
    # napi lépcsős idopontok (determinista, marker-független)
    return [{"idopont_utc": f"2026-01-{1 + i // 28:02d}T{(i % 28):02d}:00:00+00:00", "ertek": float(v)}
            for i, v in enumerate(ertekek)]

def test_nemlin_trend_gorbere_struktura_van_zajra_nincs():
    x = np.arange(60)
    gorbe = 50 + 20 * np.sin(x / 10.0)                 # erős nemlineáris jel
    zaj = np.array([50 + (-1) ** i * 5 for i in range(60)], float)
    ok = ml_trend.nemlin_trend(_pontok(gorbe))
    ne = ml_trend.nemlin_trend(_pontok(zaj))
    assert ok["van_struktura"] is True
    assert ok["cv_r2"] > ok["lin_cv_r2"] + 0.05        # az őr átengedi
    assert len(ok["gorbe"]) <= 60 and ok["gorbe"][0]["idopont_utc"]
    assert ne["van_struktura"] is False                # a zajra az őr NEM enged trendet
    assert ne["gorbe"] == []

def test_nemlin_trend_negativ_cv_nem_ad_strukturat_meg_ha_veri_is_a_linearist():
    # determinista, zajos sorozat: a LOESS out-of-sample R²-e NEGATÍV (rosszabb, mint a
    # lapos átlag), de a lineáris MÉG rosszabb → a puszta relatív őr (cv >= lin+margo)
    # átengedné. Az abszolút padló (cv > 0) ilyenkor is False-t ad: negatív R²-ű görbét
    # NEM rajzolunk (naming-discipline: ne olvassunk struktúrát a zajba).
    ertekek = [4, 8, 38, 84, 40, 79, 31, 24, 79, 88, 8, 5, 67, 33, 57, 15]
    r = ml_trend.nemlin_trend(_pontok(ertekek))
    assert r["cv_r2"] < 0                               # a nemlineáris illesztés is negatív out-of-sample
    assert r["cv_r2"] >= r["lin_cv_r2"] + 0.05          # ÉS veri a (még rosszabb) lineárist
    assert r["van_struktura"] is False                 # mégsem struktúra — az abszolút padló miatt
    assert r["gorbe"] == []
