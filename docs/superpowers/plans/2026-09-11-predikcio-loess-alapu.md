# Predikció (LOESS-alapú, csillapított-trend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Minden kulcsszóra LOESS-alapú, csillapított-trendű előrejelzés 5 külön horizont-gombbal (1 nap / 1 hét / 1 hó / 3 hó / 1 év), MINDIG empirikus (visszatesztelt) bizonytalansági sávval, a hosszú távon ellaposodó ponttal + figyelmeztetéssel.

**Architecture:** Új tiszta-numpy `trendfigyelo/predikcio.py` modul (damped-trend a LOESS széléről + additív szezon ahol ≥2 ciklus + gördülő-origó backteszt RMSE). A `regresszio_szamit` (órás: 1_nap/1_het) és `regresszio_masodlagos_szamit` (napi: 1_ho/3_ho; heti: 1_ev) szó-szinten beágyaz egy `predikcio` blokkot (a `nemlin`-minta szerint). A frontend a két fájlból mergeli, és a teljes (idő-tengelyű) nézeten rajzol előrejelző vonalat + sávot.

**Tech Stack:** numpy (kizárólag), Chart.js (meglévő), Playwright/pytest.

**Spec:** docs/superpowers/specs/2026-09-11-predikcio-loess-alapu-design.md

## Global Constraints

- **CSAK numpy** — semmi új Python-dep (nincs scipy/statsmodels/sklearn). Frontend: nincs `new Date()`/`Date.now()`.
- **Determinizmus:** semmi random / argless `datetime.now()` / `seged.most_utc()` a tesztelt logikában. A jövő-időbélyegek az adat UTOLSÓ pontjából + `h·lépés`-ből (fix timedelta) számolódnak.
- **A lineáris regresszió + a nemlin VÁLTOZATLAN** — a `predikcio` szó-szinten ADDITÍV kulcs. A pótolhatatlan órás lánc READ-ONLY.
- **[0,100]-vágás mindenütt** (pont ÉS sáv).
- **TDD:** minden taskban előbb bukó teszt (RED, futtatva), majd minimál impl (GREEN), majd a TELJES suite: `.venv/bin/python -m pytest -p no:xdist -q` és e2e `npx playwright test --workers=1` (SOROS).
- **git add NÉVRE** (soha `-A`/`.`); az `ATADAS-*.txt` és a nyers adat-JSON-ok SOHA nem staged.
- **Commit-trailerek KÖTELEZŐK:**
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
  ```

---

### Task 1: predikcio.py — konstansok + szint/trend + csillapított extrapoláció

**Files:**
- Create: `trendfigyelo/predikcio.py`
- Test: `tests/test_predikcio.py`

**Interfaces:**
- Produces: `HORIZONTOK` (dict: horizont→lépésszám), `FIGYELMEZTETETT` (set), `_szint_trend(sim, w)->(L,b)`, `_damped_sor(L, b, H, phi)->np.ndarray` (H,).

- [ ] **Step 1: Write the failing test**
```python
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
```

- [ ] **Step 2: Run test to verify it fails**
Run: `.venv/bin/python -m pytest tests/test_predikcio.py -v`
Expected: FAIL (ImportError / AttributeError — a modul/függvények még nincsenek).

- [ ] **Step 3: Write minimal implementation**
```python
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
```

- [ ] **Step 4: Run test to verify it passes**
Run: `.venv/bin/python -m pytest tests/test_predikcio.py -v` → PASS.

- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/predikcio.py tests/test_predikcio.py
git commit -m "feat(predikcio): csillapított-trend mag (szint/trend + damped sor)"
```

---

### Task 2: additív szezon-profil (csak ≥2 ciklus)

**Files:**
- Modify: `trendfigyelo/predikcio.py`
- Test: `tests/test_predikcio.py`

**Interfaces:**
- Consumes: `_szint_trend`, `_damped_sor` (T1).
- Produces: `_szezon_profil(y, sim, m)->np.ndarray|None` (nulla-átlagú, m hosszú), `elorejelzes(y, sim, m, H, phi=0.95)->(np.ndarray, bool)` (pont [0,100]-vágva, szezon-volt-e).

- [ ] **Step 1: Write the failing test**
```python
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
```

- [ ] **Step 2: Run test to verify it fails**
Run: `.venv/bin/python -m pytest tests/test_predikcio.py -k "szezon or elorejelzes" -v` → FAIL (AttributeError).

- [ ] **Step 3: Write minimal implementation**
```python
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
```

- [ ] **Step 4: Run test to verify it passes** → PASS. Majd a teljes modul-suite zöld.

- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/predikcio.py tests/test_predikcio.py
git commit -m "feat(predikcio): additív szezon-profil (csak >=2 ciklus) + elorejelzes"
```

---

### Task 3: olcsó él-simító + gördülő-origó backteszt (RMSE horizontonként)

**Files:**
- Modify: `trendfigyelo/predikcio.py`
- Test: `tests/test_predikcio.py`

**Interfaces:**
- Consumes: `elorejelzes` (T2).
- Produces: `_olcso_sim(y)->np.ndarray` (mozgóátlag-simító a backteszthez), `_backteszt_rmse(y, m, H, phi, K)->np.ndarray` (H,) — monoton nem-csökkenő RMSE(h).

- [ ] **Step 1: Write the failing test**
```python
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
```

- [ ] **Step 2: Run test to verify it fails** → FAIL (AttributeError).

- [ ] **Step 3: Write minimal implementation**
```python
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
```

- [ ] **Step 4: Run test to verify it passes** → PASS. Teljes modul-suite zöld.

- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/predikcio.py tests/test_predikcio.py
git commit -m "feat(predikcio): olcso el-simito + gorulo-origo backteszt RMSE (monoton)"
```

---

### Task 4: horizont-blokk összeállítás (pont + sáv + időbélyegek + metaadat)

**Files:**
- Modify: `trendfigyelo/predikcio.py`
- Test: `tests/test_predikcio.py`

**Interfaces:**
- Consumes: `elorejelzes`, `_backteszt_rmse`, `HORIZONTOK`, `FIGYELMEZTETETT`, `ml_trend.loess`.
- Produces: `horizont_blokk(pontok, horizont, lepes_mp, m, phi=0.95, z=1.28, K=15, ritkitas=40)->dict|None`
  — a `pontok` = lezárt `[{idopont_utc, ertek}]` (rendezve); `lepes_mp` = a felbontás lépése másodpercben
  (3600/86400/604800). Visszaad: `{"pont":[{idopont_utc,ertek}], "also":[…], "felso":[…], "rmse_veg",
  "szezon", "modszer":"damped-LOESS", "megbizhatosag", "figyelmeztetes"}` VAGY None (túl kevés pont).
- A jövő-időbélyeg: `_jovo_ido(utolso_iso, lepes_mp, h)` — az utolsó időpont + h·lépés, ISO (UTC),
  `datetime.fromisoformat` + `timedelta` (NINCS `datetime.now()`).

- [ ] **Step 1: Write the failing test**
```python
from datetime import datetime, timezone, timedelta
def _sor(n, lepes_mp, bazis=50.0, trend=0.1):
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
```

- [ ] **Step 2: Run test to verify it fails** → FAIL (AttributeError).

- [ ] **Step 3: Write minimal implementation**
```python
from datetime import datetime, timedelta
from .ml_trend import loess

def _jovo_ido(utolso_iso, lepes_mp, h):
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
```

- [ ] **Step 4: Run test to verify it passes** → PASS. Teljes modul-suite zöld.

- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/predikcio.py tests/test_predikcio.py
git commit -m "feat(predikcio): horizont_blokk (pont + empirikus sav + jovo-idobelyegek)"
```

---

### Task 5: backend integráció — `predikcio` blokk a regresszió-fájlokban

**Files:**
- Modify: `trendfigyelo/regresszio.py` (`regresszio_szamit` és `regresszio_masodlagos_szamit`)
- Test: `tests/test_regresszio.py`

**Interfaces:**
- Consumes: `predikcio.horizont_blokk`.
- Produces: a szó-rekord `predikcio` kulcsa: `{"1_nap":{…}|hiányzik, "1_het":…, "1_ho":…, "3_ho":…, "1_ev":…}`.

**Kontextus / mintakövetés (KÖTELEZŐ olvasni):** a `nemlin` beágyazása a `regresszio_egy_ablak`-ban
(intervallum-szinten) a minta. A `predikcio` viszont **szó-szinten** kerül a rekordba. A soronkénti
felbontás-sorozatot a meglévő bemenetből kell kinyerni:
- **Órás sorozat** (1_nap, 1_het): a `regresszio_szamit`-ban a szó legfrissebb órás pontjaiból. A
  leghosszabb tiszta órás sor forrása a lánc, ha van (`lanc_map.get(szo)`), különben a `nyers`
  `kulcsszavak[szo]` UTOLSÓ ablakának `pontok`-ja (a `reszleges:true` kihagyva, `idopont_utc` szerint
  rendezve). Az implementer a `_intervallumok`/`regresszio_egy_ablak` meglévő pont-kinyerését tükrözze
  (lezárt = `not p.get("reszleges")`), és a lánc alakját a `lanc.betolt_lanc` kimenetéből ellenőrizze.
- **Napi (1_ho, 3_ho) és heti (1_ev) sorozat**: a `regresszio_masodlagos_szamit`-ban a
  `masodlagos_nyers` szó-rekordjából a megfelelő `timeframe`/`racs` sorozat (napi = 3-hó/`nap`,
  heti = 12-hó/`het`) lezárt pontjai. Az implementer a másodlagos nyers alakját a
  `masodlagos_szavak_ma`/a meglévő másodlagos pont-kinyerés szerint tükrözze.
- **Lépés (mp):** órás=3600, napi=86400, heti=604800.

- [ ] **Step 1: Write the failing test** (karakterizációs — fabrikált bemenettel, NEM a valós adat-JSON-okból)
```python
def test_regresszio_szo_predikcio_blokkot_kap_eleg_oras_ponttal():
    # elég órás pont → a szó-rekord 'predikcio'-t kap, benne 1_nap horizont pont+sávval
    import numpy as np
    from datetime import datetime, timezone, timedelta
    t0 = datetime(2026, 8, 1, tzinfo=timezone.utc)
    pontok = [{"idopont_utc": (t0 + timedelta(hours=i)).isoformat(),
               "ertek": int(50 + 20 * np.sin(i / 12.0)), "reszleges": False} for i in range(400)]
    nyers = {"kulcsszavak": {"benzin": [{"kulcsszo": "benzin",
             "ablak_kezdet_utc": pontok[0]["idopont_utc"], "ablak_veg_utc": pontok[-1]["idopont_utc"],
             "pontok": pontok}]}}
    reg = regresszio.regresszio_szamit(nyers, {}, _config(), "2026-08-18T00:00:00+00:00")
    szo = reg["kulcsszavak"]["benzin"]
    assert "predikcio" in szo and "1_nap" in szo["predikcio"]
    assert len(szo["predikcio"]["1_nap"]["pont"]) > 0
```
(`_config()` = a meglévő teszt-fixture konfig; a task-vég-review a valós config-betöltést használó
helper mintáját várja el.)

- [ ] **Step 2: Run test to verify it fails** → FAIL (`'predikcio' not in szo`).

- [ ] **Step 3: Write minimal implementation**
A `regresszio_szamit` szó-ciklusában (a `ki[szo] = {...}` után), az órás lezárt sorozatból:
```python
# szó-szintű ELŐREJELZÉS (órás horizontok) — additív, a lineáris/nemlin érintetlen
oras_pontok = _oras_sorozat(nyers, lanc_map, szo)      # [{idopont_utc, ertek}] lezárt, rendezve
pred = {}
for hz in ("1_nap", "1_het"):
    blk = predikcio.horizont_blokk(oras_pontok, hz, 3600, m=24)
    if blk is not None:
        pred[hz] = blk
if pred:
    ki[szo]["predikcio"] = pred
```
A `regresszio_masodlagos_szamit`-ban a napi/heti sorozatból ugyanígy, `("1_ho","3_ho")` napi
(`86400`, `m=7`) és `("1_ev",)` heti (`604800`, `m=None`), és a meglévő szó-rekordba MERGE-elve a
`predikcio` kulcsba (ha az elsődleges már írt órás horizontokat, a frontend a két fájlból mergeli —
itt a másodlagos a SAJÁT fájljába írja a napi/heti horizontokat). Segéd-kinyerők (`_oras_sorozat`,
`_napi_sorozat`, `_heti_sorozat`) a fenti mintakövetés szerint, a `reszleges` kihagyásával.

- [ ] **Step 4: Run test to verify it passes** → PASS. Majd a TELJES suite zöld (a nemlin/lineáris tesztek változatlanul).

- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/regresszio.py tests/test_regresszio.py
git commit -m "feat(regresszio): szo-szintu predikcio blokk (oras + napi/heti horizontok)"
```

---

### Task 6: frontend — Predikció-sáv (5 kizáró gomb) + adat-merge + info

**Files:**
- Modify: `docs/js/app.js`, `docs/css/app.css`
- Test: `e2e/kulcsszo.spec.js`

**Interfaces:**
- Produces: `#kulcsszo-blokk[data-predikcio="1_nap|1_het|1_ho|3_ho|1_ev|ki"]` (alap `ki`);
  `.predikcio-sav`, `.predikcio-gomb[data-horizont]` (5 db, egymást kizáró), `.predikcio-info`;
  `PREDIKCIO_SZIN = "#16a085"`. A szó `predikcio` blokkja a KÉT regresszió-fájlból mergelve
  (elsődleges: 1_nap/1_het; másodlagos: 1_ho/3_ho/1_ev).

**Kontextus:** a `mltrend-sáv` (ML-kapcsoló) az UI-minta — a Predikció-sáv szerkezetileg hasonló, de
5 **egymást kizáró** gomb (rádió-szerű: egy aktív; újrakattintás → `ki`). A meglévő két-fájl merge
(elsődleges + másodlagos szó-rekordok egyesítése) a helyszín, ahová a `predikcio` mergelése bekerül.

- [ ] **Step 1: Write the failing test**
```javascript
test("Predikció: 5 egymást kizáró gomb, alapból egyik sincs kiválasztva", async ({ page }) => {
  // fixture: benzin szó predikcio blokkal (1_nap + 1_ev)
  // … mock reg/masodlagos a predikcio kulccsal …
  await page.goto("/");
  const blokk = page.locator("#kulcsszo-blokk");
  await expect(blokk).toHaveAttribute("data-predikcio", "ki");           // alap: ki
  await expect(page.locator("#kulcsszo-blokk .predikcio-gomb")).toHaveCount(5);
  await page.locator('#kulcsszo-blokk .predikcio-gomb[data-horizont="1_nap"]').click();
  await expect(blokk).toHaveAttribute("data-predikcio", "1_nap");        // kiválaszt
  await page.locator('#kulcsszo-blokk .predikcio-gomb[data-horizont="1_ev"]').click();
  await expect(blokk).toHaveAttribute("data-predikcio", "1_ev");         // VÁLT (kizáró)
  await page.locator('#kulcsszo-blokk .predikcio-gomb[data-horizont="1_ev"]').click();
  await expect(blokk).toHaveAttribute("data-predikcio", "ki");           // újrakattintás → ki
});
```

- [ ] **Step 2: Run test to verify it fails** → FAIL (nincs sáv/gomb).

- [ ] **Step 3: Write minimal implementation** — a `mltrend-sáv`-mintát követve: az 5 gomb + info sáv
  a `kulcsszo_blokk_render`-be (a mltrend-sáv mellé); a gomb-klikk a `#kulcsszo-blokk`
  `data-predikcio`-ját állítja (kizáró logika: aktív→`ki`, egyébként az új horizont), és újrarajzol.
  A szó `predikcio`-ja a két-fájl merge-ben egyesül (`Object.assign(elsődleges.predikcio||{},
  másodlagos.predikcio||{})`). `PREDIKCIO_SZIN` + a gomb/info CSS a `mltrend`-minta szerint.

- [ ] **Step 4: Run test to verify it passes** → PASS (SOROS Playwright).

- [ ] **Step 5: Commit**
```bash
git add docs/js/app.js docs/css/app.css e2e/kulcsszo.spec.js
git commit -m "feat(app): predikcio-sav 5 kizaro gombbal + adat-merge (default ki)"
```

---

### Task 7: frontend — előrejelző vonal + sáv rajzolása a teljes nézeten + figyelmeztetés

**Files:**
- Modify: `docs/js/app.js`
- Test: `e2e/kulcsszo.spec.js`

**Interfaces:**
- Consumes: `data-predikcio`, a szó `predikcio` blokkja, `PREDIKCIO_SZIN` (T6).
- A kiválasztott horizont: a teljes (idő-tengelyű) charton egy szaggatott **előrejelző vonal**
  (a `pont` időbélyeges {x,y}) + **árnyékolt sáv** (`also`/`felso` közti kitöltés, Chart.js `fill`
  a két dataset közt). A jövő-pontok az x-tengelyt jobbra nyújtják. Kategória-nézetből a
  predikció-gomb a **teljes nézetre vált**. A `figyelmeztetes:true` horizontnál felirat a charton +
  a gomb mellett. A kártya kiírja: „80%-os sáv: ±<rmse_veg> pont (<horizont>-ra)".

- [ ] **Step 1: Write the failing test**
```javascript
test("Predikció: kiválasztott horizont előrejelző vonalat + sávot rajzol a jövőbe", async ({ page }) => {
  // benzin, 1_nap predikcio blokk (pont/also/felso), teljes nézet
  await page.goto("/");
  await page.locator('#kulcsszo-blokk .predikcio-gomb[data-horizont="1_nap"]').click();
  const van = await page.evaluate(() => {
    const p = (window.chart_peldanyok || {})["benzin"];
    return !!p && p.data.datasets.some(d => d.borderColor === "#16a085");  // előrejelző vonal
  });
  expect(van).toBe(true);
});

test("Predikció: 1_ev horizont figyelmeztetést mutat", async ({ page }) => {
  await page.goto("/");
  await page.locator('#kulcsszo-blokk .predikcio-gomb[data-horizont="1_ev"]').click();
  await expect(page.locator('#kulcsszo-blokk .kulcsszo-chart[data-kulcsszo="benzin"]'))
    .toContainText("nagy bizonytalanság");
});
```

- [ ] **Step 2: Run test to verify it fails** → FAIL (nincs előrejelző dataset).

- [ ] **Step 3: Write minimal implementation** — a teljes (xy) rajzoló ágban (ahol a nemlin lila
  dataset készül): ha `data-predikcio !== "ki"` ÉS a szónak van rá blokkja, told hozzá (1) az
  előrejelző vonal datasetet (`PREDIKCIO_SZIN`, `borderDash`), (2) a sáv-kitöltést (`also`+`felso`
  két dataset, a felső `fill: '-1'`/index a `also`-ra, halvány `PREDIKCIO_SZIN`). A `merteszamok`-hoz
  told a „80%-os sáv: ±X pont (H-ra)" + `figyelmeztetes` esetén „szemléltető — nagy bizonytalanság".
  Kategória-nézeten a gomb `aktiv_intervallum_valt("teljes")`-t hív, majd rajzol.

- [ ] **Step 4: Run test to verify it passes** → PASS. TELJES e2e + pytest suite zöld.

- [ ] **Step 5: Commit**
```bash
git add docs/js/app.js e2e/kulcsszo.spec.js
git commit -m "feat(app): elorejelzo vonal + sav rajzolasa + figyelmeztetes a hosszu tavon"
```

---

### Task 8: „Az adatokról" oldal — Előrejelzés doboz

**Files:**
- Modify: `docs/adatokrol.html`
- Test: `e2e/menu.spec.js` (doboz-szám + tartalmi asszertálás)

**Interfaces:** új `<section class="adat-doboz">` a nemlin-doboz után, „Előrejelzés — hogyan és meddig?"
címmel; a doboz-szám 18→19.

- [ ] **Step 1: Write the failing test** — `menu.spec.js`-ben a doboz-szám 18→19, és
  `toContainText("csillapított")` + `toContainText("bizonytalansági sáv")` + `toContainText("visszatesztel")`.
- [ ] **Step 2: Run test to verify it fails** → FAIL (18 doboz / hiányzó szöveg).
- [ ] **Step 3: Write minimal implementation** — a doboz: módszer (LOESS-szint + csillapított trend +
  szezon ahol ≥2 ciklus), miért csillapított (nem szalad el), mit jelent a 80%-os empirikus
  (visszatesztelt) sáv, miért óvatos a hosszú táv (a Google Trends nem hordoz 1 év előre jelezhető
  jelet; a sáv szélessége a figyelmeztetés). A képletek dióhéjban (damped `ŷ(h)=L+b·Σφⁱ`, empirikus
  RMSE(h)). A `menu.spec.js` doboz-szám 18→19.
- [ ] **Step 4: Run test to verify it passes** → PASS.
- [ ] **Step 5: Commit**
```bash
git add docs/adatokrol.html e2e/menu.spec.js
git commit -m "doc(adatokrol): Elorejelzes doboz (modszer, sav, ovatos hosszu tav)"
```

---

## Záró lépések (a plan végén, az SDD/executor végzi)
- Teljes-ág review (legképesebb modell): a statisztikai helyesség (csillapítás, szezon-feltétel, sáv
  monotonitása, [0,100]-vágás), a determinizmus, a lineáris/nemlin érintetlensége, a két-fájl merge.
- **Compute-mérés:** a `predikcio` (főleg a backteszt) hozzáadott ideje a napi regresszióhoz — read-only,
  a nemlin-mérés mintájára; ha sok, `K`/horizont-ritkítás USER-döntésre.
- Élő-előnézet (regen + localhost + git checkout): pár szó előrejelzése + sávja, tüntetés, egy hosszú
  horizont figyelmeztetéssel.
- Kapuzott merge/push USER-jóváhagyással (finishing-a-development-branch); memória + leltár frissítés.
