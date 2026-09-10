# Nemlineáris (ML) trend a kulcsszó-chartokon — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Minden kulcsszó-charton a lineáris trend MELLÉ egy nem-túltanult nemlineáris (LOESS) trend, kapcsolóval be/ki (alapból KI), a főbb metrikákkal.

**Architecture:** Új tiszta-numpy `ml_trend.py` modul (LOESS + determinista k-fold CV + túltanulás-őr) → a metrikák + a sima görbe a meglévő regresszió-fájlok minden érvényes intervallumába `nemlin` blokként ágyazva → a frontend kapcsolóval rárajzolja a lila görbét és kiírja a metrikákat.

**Tech Stack:** Python 3.12, numpy (MEGLÉVŐ — nincs új dep); vanilla JS + Chart.js (vendor); pytest + Playwright.

**Spec:** `docs/superpowers/specs/2026-09-10-nemlinearis-ml-trend-design.md`

## Global Constraints
- **NULLA új Python-függőség** — csak numpy (scipy/sklearn/statsmodels/xgboost/torch TILOS).
- **Determinizmus:** semmi argless random / `datetime.now()` a tesztelt logikában; a CV fold-particionálás `i % k`.
- **A pótolhatatlan órás lánc + a lineáris regresszió (illesztes_vonal, meredekseg_nap, R²) VÁLTOZATLAN.**
- **MUTÁCIÓ=1** commitonként; SOROS suite: `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`.
- `git add` NÉVRE (soha `-A`/`.`); az `ATADAS-*.txt` SOHA nem staged.
- Commit-trailerek: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` + `Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN`.
- Frontend: nincs `new Date()`/`Date.now()`; a dátum→ms az `iso_ms` helperrel.

---

### Task 1: LOESS mag (`ml_trend.loess`)

**Files:**
- Create: `trendfigyelo/ml_trend.py`
- Test: `tests/test_ml_trend.py`

**Interfaces:**
- Produces: `loess(x, y, span, robusztus_iter=1) -> np.ndarray` — az `x` pontokra illesztett sima értékek (ugyanaz a hossz, mint `x`/`y`). `x`,`y` 1D float np.ndarray; `span` ∈ (0,1].

- [ ] **Step 1: Failing test**
```python
# tests/test_ml_trend.py
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
```

- [ ] **Step 2: Run — expect FAIL** (`AttributeError: module ... has no attribute 'loess'`)
Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_ml_trend.py::test_loess_sima_gorbet_ad_zajos_parabolan`

- [ ] **Step 3: Implement**
```python
# trendfigyelo/ml_trend.py
"""Nemlineáris (LOESS) trend — tiszta numpy, determinista, nulla új függőség."""
import numpy as np


def loess(x, y, span=0.4, robusztus_iter=1):
    """Lokális súlyozott lineáris regresszió (tricube kernel). Visszaad: sima értékek az x-en.
    `span` = az ablak aránya (a legközelebbi ceil(span*N) pont)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    n = len(x)
    if n < 3:
        return y.copy()
    k = max(3, int(np.ceil(span * n)))
    sulyok = np.ones(n)                       # robusztussági súlyok (kezdetben 1)
    yhat = y.copy()
    for _ in range(max(1, robusztus_iter)):
        for i in range(n):
            d = np.abs(x - x[i])
            idx = np.argsort(d)[:k]
            dm = d[idx].max() or 1.0
            w = (1 - (d[idx] / dm) ** 3) ** 3
            w[w < 0] = 0
            w = w * sulyok[idx]
            X = np.vstack([np.ones(k), x[idx]]).T
            W = np.diag(w)
            try:
                beta = np.linalg.solve(X.T @ W @ X + 1e-9 * np.eye(2), X.T @ W @ y[idx])
                yhat[i] = beta[0] + beta[1] * x[i]
            except np.linalg.LinAlgError:
                yhat[i] = np.average(y[idx], weights=w) if w.sum() else y[i]
        # robusztussági súlyok frissítése a reziduumból (bisquare)
        r = y - yhat
        s = np.median(np.abs(r)) or 1.0
        u = np.clip(r / (6 * s), -1, 1)
        sulyok = (1 - u ** 2) ** 2
    return yhat
```

- [ ] **Step 4: Run — expect PASS**
Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_ml_trend.py::test_loess_sima_gorbet_ad_zajos_parabolan`

- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/ml_trend.py tests/test_ml_trend.py
git commit -m "feat(ml_trend): LOESS mag (tiszta numpy, tricube + robusztus)"
```

---

### Task 2: Determinista k-fold CV out-of-sample R²

**Files:**
- Modify: `trendfigyelo/ml_trend.py`
- Test: `tests/test_ml_trend.py`

**Interfaces:**
- Produces: `cv_r2(x, y, fit_predict, k=5) -> float` — out-of-sample R²; a fold = `i % k` (determinista). `fit_predict(x_tr, y_tr, x_q) -> y_q`.

- [ ] **Step 1: Failing test**
```python
def test_cv_r2_determinista_es_a_zajra_nem_ad_jo_illeszkedest():
    x = np.arange(50, dtype=float)
    zaj = np.array([(-1) ** i for i in range(50)], float) * 5   # determinista cikk-cakk (nincs trend)
    def lin_fp(xt, yt, xq):
        b1, b0 = np.polyfit(xt, yt, 1); return b0 + b1 * xq
    r2a = ml_trend.cv_r2(x, zaj, lin_fp)
    r2b = ml_trend.cv_r2(x, zaj, lin_fp)
    assert r2a == r2b            # DETERMINISTA (kétszer ugyanaz)
    assert r2a < 0.1             # zajra nincs érdemi out-of-sample illeszkedés
```

- [ ] **Step 2: Run — expect FAIL**
Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_ml_trend.py::test_cv_r2_determinista_es_a_zajra_nem_ad_jo_illeszkedest`

- [ ] **Step 3: Implement (append to ml_trend.py)**
```python
def cv_r2(x, y, fit_predict, k=5):
    """Determinista k-fold out-of-sample R². Fold = index % k (NINCS véletlen)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    n = len(x)
    if n < k + 2:
        return 0.0
    yhat = np.full(n, np.nan)
    for f in range(k):
        teszt = np.arange(n) % k == f
        tren = ~teszt
        if tren.sum() < 2 or teszt.sum() == 0:
            continue
        yhat[teszt] = fit_predict(x[tren], y[tren], x[teszt])
    ok = ~np.isnan(yhat)
    ss_tot = ((y[ok] - y[ok].mean()) ** 2).sum()
    if ss_tot <= 0:
        return 0.0
    return float(1 - ((y[ok] - yhat[ok]) ** 2).sum() / ss_tot)
```

- [ ] **Step 4: Run — expect PASS**
- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/ml_trend.py tests/test_ml_trend.py
git commit -m "feat(ml_trend): determinista k-fold CV out-of-sample R²"
```

---

### Task 3: `nemlin_trend` — span-választás + túltanulás-őr + metrikák

**Files:**
- Modify: `trendfigyelo/ml_trend.py`
- Test: `tests/test_ml_trend.py`

**Interfaces:**
- Produces: `nemlin_trend(pontok, gorbe_pont=60, margo=0.05, spanok=(0.3, 0.5, 0.7), k=5) -> dict | None`.
  `pontok` = a lezárt pontok listája `[{"idopont_utc": str, "ertek": num}, ...]` (időrendben).
  Visszaad: `{van_struktura, gorbe:[{idopont_utc,ertek}], cv_r2, lin_cv_r2, span, eff_df, irany, fordulopontok, rezidualis_szoras}` — vagy `None` ha < ~12 pont.

- [ ] **Step 1: Failing test**
```python
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
```

- [ ] **Step 2: Run — expect FAIL**
Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_ml_trend.py::test_nemlin_trend_gorbere_struktura_van_zajra_nincs`

- [ ] **Step 3: Implement (append to ml_trend.py)**
```python
def _linearis_fp(xt, yt, xq):
    b1, b0 = np.polyfit(xt, yt, 1)
    return b0 + b1 * xq


def nemlin_trend(pontok, gorbe_pont=60, margo=0.05, spanok=(0.3, 0.5, 0.7), k=5):
    y = np.array([p["ertek"] for p in pontok], float)
    n = len(y)
    if n < 12:
        return None
    x = np.arange(n, dtype=float)
    idok = [p["idopont_utc"] for p in pontok]
    lin_cv = cv_r2(x, y, _linearis_fp, k)
    # legjobb span CV szerint
    best = None
    for sp in spanok:
        fp = (lambda s: (lambda xt, yt, xq: _loess_predict(xt, yt, xq, s)))(sp)
        cv = cv_r2(x, y, fp, k)
        if best is None or cv > best[1]:
            best = (sp, cv)
    span, cv = best
    van = cv >= lin_cv + margo
    if not van:
        return {"van_struktura": False, "gorbe": [], "cv_r2": round(cv, 3),
                "lin_cv_r2": round(lin_cv, 3), "span": span, "eff_df": None,
                "irany": None, "fordulopontok": None, "rezidualis_szoras": None}
    sim = loess(x, y, span)
    # metrikák
    resid = float(np.std(y - sim))
    irany = "novekszik" if sim[-1] - sim[0] > 1 else ("csokken" if sim[-1] - sim[0] < -1 else "hullamzik")
    d = np.diff(sim)
    fordulo = int(np.sum(np.abs(np.diff(np.sign(d))) > 0))   # előjelváltások a deriváltban
    eff_df = round(_eff_df(x, span), 1)
    # görbe ritkítva ~gorbe_pont pontra (a sima elég sűrű, kevesebb pont is jó)
    lep = max(1, n // gorbe_pont)
    gorbe = [{"idopont_utc": idok[i], "ertek": round(float(sim[i]), 1)} for i in range(0, n, lep)]
    if gorbe[-1]["idopont_utc"] != idok[-1]:
        gorbe.append({"idopont_utc": idok[-1], "ertek": round(float(sim[-1]), 1)})
    return {"van_struktura": True, "gorbe": gorbe, "cv_r2": round(cv, 3),
            "lin_cv_r2": round(lin_cv, 3), "span": span, "eff_df": eff_df,
            "irany": irany, "fordulopontok": fordulo, "rezidualis_szoras": round(resid, 1)}


def _loess_predict(xt, yt, xq, span):
    """LOESS becslés tetszőleges xq query-pontokon (a CV-hez; a train-only pontokból)."""
    xt = np.asarray(xt, float); yt = np.asarray(yt, float); xq = np.asarray(xq, float)
    k = max(3, int(np.ceil(span * len(xt))))
    out = np.empty(len(xq))
    for i, x0 in enumerate(xq):
        d = np.abs(xt - x0); idx = np.argsort(d)[:k]; dm = d[idx].max() or 1.0
        w = (1 - (d[idx] / dm) ** 3) ** 3; w[w < 0] = 0
        X = np.vstack([np.ones(len(idx)), xt[idx]]).T; W = np.diag(w)
        try:
            beta = np.linalg.solve(X.T @ W @ X + 1e-9 * np.eye(2), X.T @ W @ yt[idx])
            out[i] = beta[0] + beta[1] * x0
        except np.linalg.LinAlgError:
            out[i] = np.average(yt[idx], weights=w) if w.sum() else yt[idx].mean()
    return out


def _eff_df(x, span):
    """Effektív szabadságfok ≈ a simító-mátrix nyoma (trace(L)). O(N*k)."""
    n = len(x); k = max(3, int(np.ceil(span * n))); tr = 0.0
    for i in range(n):
        d = np.abs(x - x[i]); idx = np.argsort(d)[:k]; dm = d[idx].max() or 1.0
        w = (1 - (d[idx] / dm) ** 3) ** 3; w[w < 0] = 0
        X = np.vstack([np.ones(len(idx)), x[idx]]).T; W = np.diag(w)
        try:
            H = X @ np.linalg.solve(X.T @ W @ X + 1e-9 * np.eye(2), X.T @ W)
            j = list(idx).index(i)
            tr += H[j, j]
        except np.linalg.LinAlgError:
            tr += 1.0 / k
    return tr
```
Megjegyzés: a `loess` Task 1-beli belső hurkát is a `_loess_predict`-re lehet cserélni DRY-ért (refaktor, a Task 1 teszt zöld marad) — opcionális.

- [ ] **Step 4: Run — expect PASS** (a 3 ml_trend teszt)
Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_ml_trend.py`

- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/ml_trend.py tests/test_ml_trend.py
git commit -m "feat(ml_trend): nemlin_trend span-CV + túltanulás-őr + metrikák"
```

---

### Task 4: Backend-integráció — `nemlin` blokk minden érvényes intervallumba

**Files:**
- Modify: `trendfigyelo/regresszio.py` (a `regresszio_egy_ablak` visszatérése)
- Test: `tests/test_regresszio.py`

**Interfaces:**
- Consumes: `ml_trend.nemlin_trend(pontok)` (Task 3).
- Produces: minden `ervenyes:True` intervallum-dict egy `"nemlin"` kulcsot kap (a Task 3 kimenete), ha ≥12 lezárt pont; különben nincs `nemlin` kulcs.

- [ ] **Step 1: Failing test** (a valós ablak-számoló ág karakterizációja)
```python
# tests/test_regresszio.py — a meglévő regresszio_egy_ablak-hívó minta szerint
def test_regresszio_egy_ablak_nemlin_blokkot_ad_eleg_ponttal():
    import numpy as np
    pontok = [{"idopont_utc": f"2026-01-{1+i:02d}T00:00:00+00:00",
               "ertek": float(50 + 20 * np.sin(i / 5.0)), "reszleges": False} for i in range(40)]
    out = regresszio.regresszio_egy_ablak(pontok, pontok[0]["idopont_utc"], pontok[-1]["idopont_utc"], 40)
    assert out["ervenyes"] is True
    assert "nemlin" in out and out["nemlin"]["van_struktura"] is True
```

- [ ] **Step 2: Run — expect FAIL** (`KeyError: 'nemlin'`)
Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_regresszio.py::test_regresszio_egy_ablak_nemlin_blokkot_ad_eleg_ponttal`

- [ ] **Step 3: Implement** — a `regresszio_egy_ablak`-ban, az `ervenyes:True` visszatérés ELŐTT:
```python
    # (a függvény már kiszámolta a `lezart` listát és eldöntötte az ervenyes-t)
    from . import ml_trend
    nemlin = ml_trend.nemlin_trend([{"idopont_utc": p["idopont_utc"], "ertek": p["ertek"]} for p in lezart])
    # ... a visszatérő dict-be, csak ervenyes ágon:
    if nemlin is not None:
        eredmeny["nemlin"] = nemlin
```
(A pontos beillesztés a `regresszio_egy_ablak` valós szerkezetéhez igazítva; a `nemlin` CSAK az `ervenyes:True` dict-be kerül. Import a modul tetejére is mozgatható.)

- [ ] **Step 4: Run — expect PASS** + a teljes regresszió-suite (regressziómentesség)
Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_regresszio.py`

- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/regresszio.py tests/test_regresszio.py
git commit -m "feat(regresszio): nemlin (LOESS) blokk minden érvényes intervallumba"
```

---

### Task 5: Frontend — kapcsoló-gomb + állapot + `nemlin_xy` a rácsépítőbe

**Files:**
- Modify: `docs/js/app.js` (ATTR + konstansok; `racs_epit`; `kulcsszo_blokk_render` gomb)
- Modify: `docs/css/app.css`
- Test: `e2e/kulcsszo.spec.js`

**Interfaces:**
- Produces: `#kulcsszo-blokk[data-mltrend="be"|"ki"]` (alapból ki); a `.mltrend-gomb` + `.mltrend-info`; a `racs` objektum `nemlin_xy` mezője (a `nemlin.gorbe`-ből `{x:iso_ms,y}`), ha `van_struktura`.

- [ ] **Step 1: Failing e2e** (az adatforras-marker teszt mintája szerint; fixture: `nemlin` blokk egy szó intervallumában)
```javascript
test("ML-trend: alapból KI (nincs lila görbe), a gomb bekapcsolja", async ({ page }) => {
  // hetIvErv-hez hasonló, de nemlin blokkal — segéd a fixture-építőben:
  const ivNemlin = { ...hetIvErv(0, 52), nemlin: { van_struktura: true,
    gorbe: Array.from({length: 20}, (_, i) => ({ idopont_utc: racs_iso(i*2, 7), ertek: 40 + i })),
    cv_r2: 0.42, lin_cv_r2: 0.08, span: 0.3, eff_df: 6.2, irany: "novekszik",
    fordulopontok: 2, rezidualis_szoras: 7.1 } };
  await mock(page, {
    regObj: reg({ "kórház": regSzo({ domen: "egeszseg", intervallumok: {
      "1_het": ivHibas("keves_pont"), "2_het": ivHibas("keves_pont"), "1_ho": ivHibas("keves_pont"),
      "3_ho": ivHibas("keves_pont"), "1_ev": ivHibas("nincs_lancolas") } }) }),
    nyersObj: nyers({ "kórház": [nyersRekord("kórház")] }),
    mpRegObj: mpReg({ "kórház": mpSzo("het", { "1_het": ivHibas("keves_pont"), "2_het": ivHibas("keves_pont"),
      "1_ho": ivHibas("keves_pont"), "3_ho": ivHibas("keves_pont"), "1_ev": ivNemlin }, { domen: "egeszseg" }) }),
    mpNyersObj: mpNyers({ "kórház": [racs_nyersRekord("kórház", 52, 7)] }),
  });
  await page.goto("/");
  const gomb = page.locator("#kulcsszo-blokk .mltrend-gomb");
  await expect(gomb).toHaveCount(1);
  await expect(page.locator("#kulcsszo-blokk .mltrend-info")).toHaveCount(1);
  // alapból KI: a kártyán nincs nemlin-jelző
  const k = page.locator('#kulcsszo-blokk .kulcsszo-chart[data-kulcsszo="kórház"]');
  await expect(k).not.toHaveAttribute("data-nemlin", /.*/);
  await gomb.click();  // BE
  await expect(page.locator('#kulcsszo-blokk .kulcsszo-chart[data-kulcsszo="kórház"]'))
    .toHaveAttribute("data-nemlin", "true");
});
```

- [ ] **Step 2: Run — expect FAIL** (nincs `.mltrend-gomb`)
Run: `npx playwright test e2e/kulcsszo.spec.js -g "ML-trend" --workers=1`

- [ ] **Step 3: Implement**
- `ATTR`-hez: `mltrend: "data-mltrend"`, `nemlin: "data-nemlin"`; konstansok: `NEMLIN_SZIN = "#8e44ad"`, `MLTREND_GOMB_BE/KI`, `MLTREND_INFO`.
- `racs_epit`-ben: `const nemlin_xy = (iv.nemlin && iv.nemlin.van_struktura) ? iv.nemlin.gorbe.map(p => ({ x: iso_ms(p.idopont_utc), y: p.ertek })) : null;` és add a visszatérő objektumhoz.
- `kartya_letrehoz`-ban (teljes-ág + normál): ha `mltrend_be && racs.nemlin_xy`, `kartya.setAttribute(ATTR.nemlin, "true")`.
- `kulcsszo_blokk_render`-ben: a 2. gomb-sáv (`.mltrend-sav` + `.mltrend-gomb` + `.mltrend-info`) az adatforras-sáv mintájára; `mltrend_be = blokk.getAttribute(ATTR.mltrend) === "be"`, átadva a `kartya_letrehoz`-nak (új param). A takarító-sorba `.mltrend-sav`.
- CSS: `.mltrend-gomb`/`.mltrend-info` az `.adatforras-gomb`/`.adatforras-info` mintájára (a lila kiemelést a görbe adja, a gomb kék aktív marad).

- [ ] **Step 4: Run — expect PASS** + teljes Playwright
Run: `npx playwright test --workers=1`

- [ ] **Step 5: Commit**
```bash
git add docs/js/app.js docs/css/app.css e2e/kulcsszo.spec.js
git commit -m "feat(app): ML-trend kapcsoló + nemlin_xy a rácsépítőben (default KI)"
```

---

### Task 6: Frontend — a lila LOESS-görbe rajzolása + metrikák a kártyán

**Files:**
- Modify: `docs/js/app.js` (`chart_letrehoz` teljes + normál ág datasetek; a mérőszám-szöveg)
- Test: `e2e/kulcsszo.spec.js`

**Interfaces:**
- Consumes: `racs.nemlin_xy` (Task 5), `#kulcsszo-blokk[data-mltrend]` (Task 5), `iv.nemlin` metrikák.

- [ ] **Step 1: Failing e2e** — bekapcsolva a chart datasetjei közt ott a lila görbe (a Chart-példányon), és a kártya-szövegben a nemlineáris R².
```javascript
test("ML-trend: bekapcsolva lila görbe-dataset + metrika-szöveg a kártyán", async ({ page }) => {
  // ugyanaz a mock, mint Task 5 (ivNemlin)
  await page.goto("/");
  await page.locator("#kulcsszo-blokk .mltrend-gomb").click();
  // a Chart-példány datasetjei közt van egy a NEMLIN_SZIN-nel
  const vanLila = await page.evaluate(() => {
    const p = (window.chart_peldanyok || {})["kórház"];
    return !!p && p.data.datasets.some(d => d.borderColor === "#8e44ad");
  });
  expect(vanLila).toBe(true);
  await expect(page.locator('#kulcsszo-blokk .kulcsszo-chart[data-kulcsszo="kórház"] .merteszamok'))
    .toContainText("nemlineáris");
});
```
(Ha a `chart_peldanyok` nem globális, tedd `window`-ra teszt-célra, vagy ellenőrizd a data-attribútumon keresztül — a Task 5 `data-nemlin` is elég a rajzolás-guardhoz; a szöveg-assert mindenképp megy.)

- [ ] **Step 2: Run — expect FAIL**
Run: `npx playwright test e2e/kulcsszo.spec.js -g "lila görbe" --workers=1`

- [ ] **Step 3: Implement**
- `chart_letrehoz` teljes-ág `ds` + normál ág `datasetek`: ha a blokk `[data-mltrend="be"]` ÉS `racs.nemlin_xy`, push:
```javascript
ds.push({ data: racs.nemlin_xy, spanGaps: true, borderColor: NEMLIN_SZIN, borderWidth: 2, pointRadius: 0, tension: 0.3 });
```
  (a normál — label-indexelt — ághoz a `nemlin` görbét a `labels`-hez kell illeszteni, vagy a normál ágban is xy-t használni; egyszerűbb: a nemlin görbét CSAK a teljes/xy ágban rajzoljuk, és a normál nézetben is xy-ra váltunk a nemlinnél — a tervben: a nemlin görbe a teljes nézetben rajzol, mint a marker.)
- a `merteszamok_szoveg`-hez (vagy egy külön `.nemlin-metrika` sor a kártyán): ha `iv.nemlin && iv.nemlin.van_struktura`, told hozzá: `„nemlineáris illeszkedés R²=" + fmt(iv.nemlin.cv_r2) + " (lineáris " + fmt(iv.nemlin.lin_cv_r2) + " helyett) · " + iv.nemlin.fordulopontok + " fordulópont · a görbe " + IRANY_MAGYAR[iv.nemlin.irany]`. Ha `van_struktura:false`, a szöveg: „nincs érdemi nemlineáris szerkezet".

- [ ] **Step 4: Run — expect PASS** + teljes SOROS suite
Run: `.venv/bin/python -m pytest -p no:xdist -q` ÉS `npx playwright test --workers=1`

- [ ] **Step 5: Commit**
```bash
git add docs/js/app.js e2e/kulcsszo.spec.js
git commit -m "feat(app): lila LOESS-görbe rajzolása + nemlineáris metrikák a kártyán"
```

---

## Záró lépések (a plan végén, nem taskonként)
- [ ] **Élő verifikáció:** a [[eloUI-preview-workflow]] szerint regeneráld a regressziót lokálisan (a `nemlin` blokkal), szolgáld ki `localhost:8000`-en, kapcsold be az ML-trend gombot → a lila görbe a strukturált szavakon (akciós újság/állás/infláció) rajzol, a zajosakon (kórház/hitel) „nincs érdemi nemlineáris szerkezet". `git checkout` a regenerált fájlokra.
- [ ] **Számítási-idő mérés:** a napi futás regresszió-lépésének ideje a `naplo.csv`-ből / lokális futással — ha érdemben nő (>pár mp), a `spanok`/`k` csökkenthető.
- [ ] **Kapuzott push** (külön kör, USER-jóváhagyással): fetch → rev-list → rebase ha kell → push → 0 0.
- [ ] **Memória + leltár** frissítés a leszállítás után.

## Self-Review jegyzet
- **Spec-lefedettség:** LOESS (T1) + CV (T2) + őr/metrikák (T3) + backend-ágyazás (T4) + kapcsoló/görbe/metrika-frontend (T5–T6) = a spec 3–4. szekciói. Az AI-elemzés (spec §6) KÍVÜL (későbbi kör) — szándékos.
- **Determinizmus:** fold=`i%k` (T2), nincs random — kapu teljesül.
- **Nincs új dep:** csak numpy (T1–T3).
- **Nyitott finomítás implementációkor:** a nemlin görbe a normál (label-indexelt) nézetben — a tervben a teljes/xy nézetre korlátozva rajzol (mint a marker); ha a normál nézetben is kell, a normál ág is xy-ra vált a nemlinnél (kis extra, T6-ban jelölve).
