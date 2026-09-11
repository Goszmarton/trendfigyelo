import numpy as np
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

def test_szint_trend_a_gorbe_szelerol():
    sim = np.linspace(10, 30, 40)                # meredekség = 20/39 per lépés
    L, b = predikcio._szint_trend(sim, w=10)
    assert abs(L - 30.0) < 1e-6
    assert abs(b - 20.0 / 39.0) < 1e-3

def test_szezon_profil_csak_ket_ciklustol_es_nulla_atlagu():
    m = 7
    x = np.arange(28)                                  # 4 ciklus
    szez = np.array([0, 5, -5, 0, 3, -3, 0], float)
    y = 50 + szez[x % m]
    sim = np.full(28, 50.0)                             # a „simító" a szint
    prof = predikcio._szezon_profil(y, sim, m)
    assert prof is not None and prof.shape == (7,)
    assert abs(prof.mean()) < 1e-9                      # nulla-átlagú
    assert np.allclose(prof, szez, atol=1e-9)
    assert predikcio._szezon_profil(y[:10], sim[:10], m) is None   # < 2m → None

def test_elorejelzes_szezont_hozzaad_es_vag():
    m = 7
    x = np.arange(28)
    y = 50 + np.array([0, 5, -5, 0, 3, -3, 0], float)[x % m]
    sim = np.full(28, 50.0)
    pont, volt = predikcio.elorejelzes(y, sim, m, H=7, phi=0.95)
    assert volt is True and pont.shape == (7,)
    assert pont.min() >= 0.0 and pont.max() <= 100.0   # [0,100]-vágás
