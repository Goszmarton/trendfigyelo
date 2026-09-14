import numpy as np
from datetime import datetime, timezone, timedelta
from trendfigyelo import predikcio

def test_damped_sor_ellaposodik_es_nem_szall_el():
    # emelkedő trend: a csillapítás miatt a lépések NEM lineárisan nőnek, telítenek
    sor = predikcio._damped_sor(L=50.0, b=2.0, H=100, phi=0.9)
    assert sor.shape == (100,)
    assert sor[0] > 50.0                       # emelkedik
    d = np.diff(sor)
    assert d[0] > d[-1] > 0 or d[-1] >= 0       # a növekmény CSÖKKEN (csillapítás)
    tel = 50.0 + 2.0 * 0.9 / (1 - 0.9)          # telítési szint L + b·φ/(1-φ)
    assert sor[-1] < tel + 1e-6                  # sosem lépi túl a telítést

def test_szint_trend_a_gorbe_szakaszabol():
    sim = np.linspace(10, 30, 40)                # meredekség = 20/39 per lépés
    L, b = predikcio._szint_trend(sim, w=20)
    assert abs(L - 30.0) < 1e-6
    assert abs(b - 20.0 / 39.0) < 1e-3

def test_elorejelzes_SIMA_a_szezont_NEM_adja_hozza():
    # erős heti (m=7) mintájú sorozat: az ÚJ forecast SIMA — a szezon-zigzag NEM jelenik meg
    x = np.arange(60)
    szez = np.array([0, 8, -8, 4, -4, 6, -6], float)   # nagy amplitúdójú heti minta
    y = 50 + 0.05 * x + szez[x % 7]
    sim = predikcio._olcso_sim(y)
    pont = predikcio.elorejelzes(y, sim, H=14, phi=0.95)   # ÚJ szignatúra: (y, sim, H, phi), NINCS m
    assert isinstance(pont, np.ndarray) and pont.shape == (14,)
    assert pont.min() >= 0.0 and pont.max() <= 100.0
    assert np.std(pont) < 3.0                          # a ±8 szezon NEM jelenik meg → SIMA
    d = np.diff(pont)
    elojel = int(np.sum(np.abs(np.diff(np.sign(d))) > 0))
    assert elojel <= 1                                  # monoton/sima, nem zigzag

def test_backteszt_rmse_monoton_no_es_zajra_nagyobb():
    rng = np.arange(120, dtype=float)
    tiszta = 50 + 0.1 * rng
    zajos = tiszta + 8 * np.sin(rng)                   # determinista „zaj"
    r_tiszta = predikcio._backteszt_rmse(tiszta, H=20, phi=0.95, K=15)   # ÚJ: nincs m
    r_zajos = predikcio._backteszt_rmse(zajos, H=20, phi=0.95, K=15)
    assert r_tiszta.shape == (20,)
    assert np.all(np.diff(r_tiszta) >= -1e-9)          # MONOTON nem-csökkenő (kumulatív max)
    assert r_zajos.mean() > r_tiszta.mean()            # zajosabb sorozat → nagyobb hiba
    assert np.array_equal(r_zajos, predikcio._backteszt_rmse(zajos, H=20, phi=0.95, K=15))  # DETERMINISTA

def _sor(n, lepes_mp, bazis=50.0, trend=0.1):
    """Teszt-segéd: n pont, lineáris trend."""
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [{"idopont_utc": (t0 + timedelta(seconds=i * lepes_mp)).isoformat(),
             "ertek": float(bazis + trend * i)} for i in range(n)]

def test_sorozat_predikcio_minden_kert_horizontot_ad_egy_sorozatbol():
    pontok = _sor(300, 3600)                                     # 300 órás pont
    out = predikcio.sorozat_predikcio(pontok, 3600, ["1_nap", "1_het", "1_ho"])
    assert set(out.keys()) == {"1_nap", "1_het", "1_ho"}
    for hz, blk in out.items():
        for kulcs in ("pont", "also", "felso"):
            assert len(blk[kulcs]) > 0
            assert all(0.0 <= p["ertek"] <= 100.0 for p in blk[kulcs])
        assert blk["also"][-1]["ertek"] <= blk["pont"][-1]["ertek"] <= blk["felso"][-1]["ertek"]
        assert blk["pont"][0]["idopont_utc"] > pontok[-1]["idopont_utc"]
        assert "szezon" not in blk                               # a szezon-mező ELTŰNT
        assert blk["modszer"] == "damped-LOESS"
    assert out["1_nap"]["figyelmeztetes"] is False
    assert out["1_ho"]["figyelmeztetes"] is False               # 1_ho nem figyelmeztetett

def test_sorozat_predikcio_naptari_H_a_felbontasbol():
    # 1_ho vége ~30 nappal az utolsó adat után, FÜGGETLENÜL a felbontástól (órás 720 lépés / napi 30 lépés)
    def veg_nap(pontok, lepes_mp):
        blk = predikcio.sorozat_predikcio(pontok, lepes_mp, ["1_ho"])["1_ho"]
        d0 = datetime.fromisoformat(pontok[-1]["idopont_utc"])
        d1 = datetime.fromisoformat(blk["pont"][-1]["idopont_utc"])
        return (d1 - d0).days
    assert veg_nap(_sor(800, 3600), 3600) == 30                 # órásból: 720 lépés = 30 nap
    assert veg_nap(_sor(60, 86400), 86400) == 30                # napiból: 30 lépés = 30 nap

def test_sorozat_predikcio_keves_pont_ures():
    assert predikcio.sorozat_predikcio(_sor(10, 3600), 3600, ["1_nap"]) == {}
