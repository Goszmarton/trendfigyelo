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

def test_backteszt_rmse_monoton_no_es_zajra_nagyobb():
    rng = np.arange(120, dtype=float)
    tiszta = 50 + 0.1 * rng
    zajos = tiszta + 8 * np.sin(rng)                   # determinista „zaj"
    r_tiszta = predikcio._backteszt_rmse(tiszta, m=7, H=20, phi=0.95, K=15)
    r_zajos = predikcio._backteszt_rmse(zajos, m=7, H=20, phi=0.95, K=15)
    assert r_tiszta.shape == (20,)
    assert np.all(np.diff(r_tiszta) >= -1e-9)          # MONOTON nem-csökkenő (kumulatív max)
    assert r_zajos.mean() > r_tiszta.mean()            # zajosabb sorozat → nagyobb hiba
    r2 = predikcio._backteszt_rmse(zajos, m=7, H=20, phi=0.95, K=15)
    assert np.array_equal(r_zajos, r2)                 # DETERMINISTA

def _sor(n, lepes_mp, bazis=50.0, trend=0.1):
    """Teszt-segéd: n pont, lineáris trend."""
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [{"idopont_utc": (t0 + timedelta(seconds=i * lepes_mp)).isoformat(),
             "ertek": float(bazis + trend * i)} for i in range(n)]

def test_horizont_blokk_savval_es_jovo_idobelyegekkel():
    pontok = _sor(200, 3600)                              # 200 órás pont
    blk = predikcio.horizont_blokk(pontok, "1_nap", 3600, m=24)
    assert blk is not None
    for kulcs in ("pont", "also", "felso"):
        assert len(blk[kulcs]) > 0
        assert all(0.0 <= p["ertek"] <= 100.0 for p in blk[kulcs])   # [0,100]-vágva
    # a sáv körbeveszi a pontot; a jövő időbélyeg > az utolsó adat
    assert blk["also"][-1]["ertek"] <= blk["pont"][-1]["ertek"] <= blk["felso"][-1]["ertek"]
    assert blk["pont"][0]["idopont_utc"] > pontok[-1]["idopont_utc"]
    assert blk["figyelmeztetes"] is False                # 1_nap nem figyelmeztetett

def test_horizont_blokk_figyelmeztetett_es_keves_pont_none():
    assert predikcio.horizont_blokk(_sor(10, 3600), "1_nap", 3600, m=24) is None   # túl kevés
    blk = predikcio.horizont_blokk(_sor(200, 604800), "1_ev", 604800, m=None)
    assert blk["figyelmeztetes"] is True and blk["szezon"] is False                 # heti: nincs szezon
