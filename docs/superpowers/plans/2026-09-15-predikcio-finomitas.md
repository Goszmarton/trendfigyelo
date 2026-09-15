# Predikció-finomítás Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Az órás-only szavaknak ne legyen 3hó/1év előrejelzése (őszinte üzenet helyette), a rövid horizont (1nap/1hét) auto-zoommal jól látszódjon, és az infó-oldal dokumentálja mindkét viselkedést.

**Architecture:** Backend: az elsődleges órás ág a 3hó/1év-re sentinel blokkot (`{nem_becsulheto:true}`) ír, amit a másodlagos napi/heti valós blokk felülír a frontend-merge-ben (így a sentinel csak órás-only szónál marad). Frontend: a sentinel horizontra üzenet (nem görbe); rövid horizontnál az x-tengely a közelmúltra közelít. Minden változás additív; a predikció-mag (LOESS/csillapított trend/backteszt) érintetlen.

**Tech Stack:** Python (numpy) backend, vanilla JS + Chart.js frontend, pytest + Playwright.

**Spec:** docs/superpowers/specs/2026-09-15-predikcio-finomitas-design.md

## Global Constraints

- Tiszta numpy + meglévő SDK; **NULLA új Python-dependency**. Additív, MUTÁCIÓ=1.
- Frontend: NINCS `new Date()` / `Date.now()`. Backend tesztelt logikában NINCS argless `datetime.now()`.
- Irreplaceable adat READ-ONLY (`kulcsszo_*`, `napok/*.json`).
- SOROS suite: `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`.
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással.
- A lineáris trend / nemlin (LOESS) görbe / napi elemzés / kategória-nézet VÁLTOZATLAN.

---

### Task 1: Backend — órás-only 3hó/1év sentinel

**Files:**
- Modify: `trendfigyelo/regresszio.py:371-374` (az elsődleges órás ág predikció-hívása)
- Test: `tests/test_regresszio.py` (új teszt a Task 5 predikció-blokk mellé, ~630. sor után)

**Interfaces:**
- Consumes: `predikcio.sorozat_predikcio(pontok, lepes_mp, horizontok) -> {horizont: blokk}` (létező).
- Produces: az órás-only szó `predikcio` blokkja: `1_nap`/`1_het`/`1_ho` valós forecast, `3_ho`/`1_ev` = `{"nem_becsulheto": True}` sentinel (a másodlagos ág valós blokkja a frontend-merge-ben felülírja, ha van napi/heti sor).

- [ ] **Step 1: Write the failing test**

`tests/test_regresszio.py`-ba (a `test_regresszio_szo_predikcio_blokkot_kap_eleg_oras_ponttal` után):

```python
def test_regresszio_oras_only_hosszu_horizont_nem_becsulheto_sentinel():
    # elég órás pont → 1_nap/1_het/1_ho VALÓS, DE 3_ho/1_ev SENTINEL ({nem_becsulheto:True}),
    # mert az órás-only szónak (nincs napi/heti forrása) a hosszú táv nem becsülhető megbízhatóan
    import numpy as np
    t0 = datetime(2026, 8, 1, tzinfo=timezone.utc)
    pontok = [{"idopont_utc": (t0 + timedelta(hours=i)).isoformat(),
               "ertek": int(50 + 20 * np.sin(i / 12.0)), "reszleges": False} for i in range(400)]
    nyers = {"kulcsszavak": {"benzin": [{"kulcsszo": "benzin",
             "ablak_kezdet_utc": pontok[0]["idopont_utc"], "ablak_veg_utc": pontok[-1]["idopont_utc"],
             "pontok": pontok}]}}
    out = regresszio.regresszio_szamit(nyers, _tortenet({}), _config(["benzin"]), "2026-08-18T00:00:00+00:00")
    pred = out["kulcsszavak"]["benzin"]["predikcio"]
    assert len(pred["1_nap"]["pont"]) > 0 and len(pred["1_ho"]["pont"]) > 0   # rövid/közép VALÓS
    assert pred["3_ho"] == {"nem_becsulheto": True}                           # hosszú táv SENTINEL
    assert pred["1_ev"] == {"nem_becsulheto": True}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_regresszio.py::test_regresszio_oras_only_hosszu_horizont_nem_becsulheto_sentinel`
Expected: FAIL — jelenleg a `3_ho` egy valós forecast-blokk (van `pont`), nem `{"nem_becsulheto": True}`.

- [ ] **Step 3: Write minimal implementation**

`trendfigyelo/regresszio.py`, a `371-374` sorokat cseréld:

```python
        oras_pontok = _oras_sorozat(nyers, lanc_map, szo)
        # Az órás sorozatból CSAK a rövid/közép horizontokat becsüljük valósnak; a 3_ho/1_ev egy pár
        # hónapnyi órás pillanatkép-láncból nem megbízható → SENTINEL. A másodlagos (napi/heti) ág valós
        # hosszú-horizontja a frontend-merge-ben felülírja, ha a szónak van napi/heti sora → a sentinel
        # CSAK az órás-only szónál (benzin/nyugdíj) marad meg.
        pred = predikcio.sorozat_predikcio(oras_pontok, 3600, ("1_nap", "1_het", "1_ho"))
        if pred:
            pred["3_ho"] = {"nem_becsulheto": True}
            pred["1_ev"] = {"nem_becsulheto": True}
            ki[szo]["predikcio"] = pred
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_regresszio.py`
Expected: PASS (az új teszt + a meglévő `..._blokkot_kap_eleg_oras_ponttal` [csak `1_nap`-ot ellenőriz] + `..._hianyzik_keves_oras_pontnal` továbbra is zöld).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/regresszio.py tests/test_regresszio.py
git commit -m "feat(predikcio): oras-only 3ho/1ev sentinel (nem_becsulheto) az oras agban"
```

---

### Task 2: Frontend — „nem becsülhető" üzenet a sentinel horizontra

**Files:**
- Modify: `docs/js/app.js` (`kartya_letrehoz`, ~1056-1072: a `predikcio_blk` kiválasztása + üzenet)
- Modify: `docs/css/app.css` (~197 után: `.predikcio-nem-becsulheto` muted-note stílus)
- Test: `e2e/kulcsszo.spec.js` (új teszt a predikció-tesztek közé)

**Interfaces:**
- Consumes: `szoreg.predikcio[horizont]` lehet valós blokk VAGY `{nem_becsulheto:true}` sentinel (Task 1).
- Produces: sentinel horizontnál a kártyán `<p class="predikcio-nem-becsulheto">` felirat, NINCS predikció-dataset.

- [ ] **Step 1: Write the failing test**

`e2e/kulcsszo.spec.js`-be (a „Predikció: 1_ev horizont figyelmeztetést mutat" teszt után):

```javascript
test("Predikció: órás-only szó hosszú horizontja 'nem becsülhető' üzenet, NINCS görbe", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "benzin": { ...regSzo({ domen: "energia" }),
      predikcio: { "1_nap": predikcioBlokk(), "1_het": predikcioBlokk(), "1_ho": predikcioBlokk(),
                   "3_ho": { nem_becsulheto: true }, "1_ev": { nem_becsulheto: true } } } }),
    nyersObj: nyers({ "benzin": [nyersRekord("benzin")] }),
  });
  await page.goto("/trendek.html");
  await page.locator('#kulcsszo-blokk .predikcio-gomb[data-horizont="1_ev"]').click();
  const kartya = page.locator('#kulcsszo-blokk .kulcsszo-chart[data-kulcsszo="benzin"]');
  await expect(kartya).toHaveAttribute("data-rendered", "true");
  await expect(kartya.locator(".predikcio-nem-becsulheto")).toContainText("nem becsülhető megbízhatóan");
  const vanGorbe = await page.evaluate(() => {
    const p = (window.chart_peldanyok || {})["benzin"];
    return !!p && p.data.datasets.some(d => d.borderColor === "#16a085");   // előrejelző vonal színe
  });
  expect(vanGorbe).toBe(false);   // sentinel → NINCS előrejelző görbe
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test --workers=1 -g "nem becsülhető"`
Expected: FAIL — jelenleg nincs `.predikcio-nem-becsulheto` elem (a sentinelt `szoreg.predikcio["1_ev"]` valós blokként kezeli, de nincs `pont` → JS-hiba vagy néma; nincs üzenet).

- [ ] **Step 3: Write minimal implementation**

`docs/js/app.js`, a `kartya_letrehoz`-ban a `predikcio_blk` definícióját (~1056-1058) cseréld:

```javascript
  // A szónak lehet a kiválasztott horizonthoz mergelt blokkja (predikcio) — VAGY egy sentinel
  // ({nem_becsulheto:true}, órás-only hosszú táv, Task 1): az utóbbi NEM rajzolható, üzenetet kap.
  const predikcio_nyers = (aktiv_kulcs === TELJES_KULCS && predikcio_horizont && predikcio_horizont !== "ki" && szoreg.predikcio)
    ? szoreg.predikcio[predikcio_horizont] : null;
  const predikcio_nem_becsulheto = !!(predikcio_nyers && predikcio_nyers.nem_becsulheto);
  const predikcio_blk = (predikcio_nyers && !predikcio_nem_becsulheto) ? predikcio_nyers : null;
```

Majd a `return kartya;` (~1143) ELÉ told be az üzenet-blokkot:

```javascript
  // SENTINEL (órás-only hosszú táv): őszinte felirat forecast helyett (a horizont ragozott nevével).
  if (predikcio_nem_becsulheto) {
    const hdef = PREDIKCIO_HORIZONTOK.find(function (h) { return h.kulcs === predikcio_horizont; }) || {};
    const nb = document.createElement("p");
    nb.className = "predikcio-nem-becsulheto";
    nb.textContent = (hdef.ragozott || predikcio_horizont)
      + " ezen a szón nem becsülhető megbízhatóan – csak órás mérés áll rendelkezésre, "
      + "amiből ilyen hosszú távra nem adunk előrejelzést.";
    kartya.appendChild(nb);
  }
```

`docs/css/app.css`, a `.elettartam` muted-note (~197) mellé:

```css
#kulcsszo-blokk .predikcio-nem-becsulheto { font-size: .75rem; color: #8a6d3b; margin: .3rem 0 0; font-style: italic; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --check docs/js/app.js && npx playwright test --workers=1 -g "nem becsülhető"`
Expected: PASS. Ellenőrzés: a meglévő „Predikció: kiválasztott horizont előrejelző vonalat + sávot rajzol" (valós blokk → van #16a085 görbe) továbbra is zöld.

- [ ] **Step 5: Commit**

```bash
git add docs/js/app.js docs/css/app.css e2e/kulcsszo.spec.js
git commit -m "feat(predikcio): oras-only hosszu tav 'nem becsulheto' uzenet (nincs gorbe)"
```

---

### Task 3: Frontend — rövid-horizont auto-zoom

**Files:**
- Modify: `docs/js/app.js` (~116-127: két új konstans; `chart_letrehoz` teljes-mód x-tengely, ~1181-1185)
- Test: `e2e/kulcsszo.spec.js` (új teszt)

**Interfaces:**
- Consumes: `kartya._predikcio_xy` (létező, a jövő-pontok), `teljes_pts` (a mért adatpontok).
- Produces: rövid horizontnál a Chart x-tengely `min`-je a közelmúltra emelve (`scales.x.min > első mért pont`).

- [ ] **Step 1: Write the failing test**

`e2e/kulcsszo.spec.js`-be:

```javascript
test("Predikció: rövid horizont ráközelít – az x-tengely a közelmúltra szűkül", async ({ page }) => {
  // benzin órás-only, 1_nap blokk (default pont a 169. óránál) → a 168 órás előzményhez képest a
  // forecast-szakasz apró → az x_min a mért kezdet ELÉ emelkedik (ráközelítés).
  await mock(page, {
    regObj: reg({ "benzin": { ...regSzo({ domen: "energia" }),
      predikcio: { "1_nap": predikcioBlokk() } } }),
    nyersObj: nyers({ "benzin": [nyersRekord("benzin")] }),
  });
  await page.goto("/trendek.html");
  await page.locator('#kulcsszo-blokk .predikcio-gomb[data-horizont="1_nap"]').click();
  await expect(page.locator('#kulcsszo-blokk .kulcsszo-chart[data-kulcsszo="benzin"]'))
    .toHaveAttribute("data-rendered", "true");
  const kozelit = await page.evaluate(() => {
    const p = (window.chart_peldanyok || {})["benzin"];
    if (!p) return null;
    const mert = p.data.datasets[0].data.filter(d => d.y !== null);
    return { xmin: p.scales.x.min, elso: mert[0].x };
  });
  expect(kozelit.xmin).toBeGreaterThan(kozelit.elso);   // az x_min a mért kezdet ELÉ emelve = ráközelítés
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test --workers=1 -g "ráközelít"`
Expected: FAIL — jelenleg `x_min` = az első mért pont (nincs zoom), tehát `xmin === elso`, nem `>`.

- [ ] **Step 3: Write minimal implementation**

`docs/js/app.js`, a predikció-konstansok mellé (~117 után):

```javascript
const PREDIKCIO_ZOOM_KUSZOB = 0.25;   // ha a forecast-szakasz < ennyi · előzmény → RÖVID horizont: ráközelítünk
const PREDIKCIO_ZOOM_SZORZO = 4;      // az x_min a forecast-hossz ennyiszeresével a mért vég elé (forecast ~1/5 szélesség)
```

A `chart_letrehoz` teljes-mód x-tengely predikció-ágát (~1181-1185) cseréld:

```javascript
    // PREDIKCIÓ: a jövő-pontok jobbra nyújtják a tengelyt (a sáv/vonal a mért adat UTÁN folytatódik).
    if (kartya._predikcio_xy && kartya._predikcio_xy.pont.length) {
      const pr_veg = kartya._predikcio_xy.pont[kartya._predikcio_xy.pont.length - 1].x;
      if (x_max === undefined || pr_veg > x_max) x_max = pr_veg;
      // RÖVID HORIZONT AUTO-ZOOM: ha a forecast jövő-szakasza kicsi a mért előzményhez képest, az x_min-t
      // a közelmúltra emeljük → a rövid előrejelzés kitölti a szélesség jó részét (jól látszódjon). Hosszú
      // horizontnál (nagy forecast-szakasz) a feltétel nem teljesül → nincs zoom, a teljes előzmény látszik.
      const adat_veg = teljes_pts.length ? teljes_pts[teljes_pts.length - 1].x : undefined;
      if (adat_veg !== undefined && x_min !== undefined) {
        const forecast_span = pr_veg - adat_veg;
        const elozmeny_span = adat_veg - x_min;
        if (forecast_span > 0 && elozmeny_span > 0 && forecast_span < PREDIKCIO_ZOOM_KUSZOB * elozmeny_span) {
          x_min = Math.max(x_min, adat_veg - PREDIKCIO_ZOOM_SZORZO * forecast_span);
        }
      }
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --check docs/js/app.js && npx playwright test --workers=1 -g "ráközelít"`
Expected: PASS. Ellenőrzés: a „Predikció: kiválasztott horizont előrejelző vonalat + sávot rajzol" (a görbe MÉG rajzolódik, csak a nézet szűkül) továbbra is zöld.

- [ ] **Step 5: Commit**

```bash
git add docs/js/app.js e2e/kulcsszo.spec.js
git commit -m "feat(predikcio): rovid horizont auto-zoom (x-tengely a kozelmultra szukul)"
```

---

### Task 4: Infó-oldal — a két új viselkedés dokumentálása

**Files:**
- Modify: `docs/adatokrol.html` (az „Előrejelzés – hogyan és meddig?" szekció, ~87 után)
- Test: `tests/test_pages.py` (új teszt: az adatokrol.html az új szövegeket tartalmazza)

**Interfaces:**
- Consumes: semmi (statikus tartalom).
- Produces: két új `<p>` az infó-szekcióban (rövid-horizont zoom + órás-only hosszú táv „nem becsülhető").

- [ ] **Step 1: Write the failing test**

`tests/test_pages.py`-ba (a fájl végére):

```python
def test_adatokrol_predikcio_uj_viselkedesek():
    # az infó-oldal dokumentálja a rövid-horizont ráközelítést ÉS az órás-only hosszú táv "nem becsülhető"-t
    szoveg = (DOCS / "adatokrol.html").read_text(encoding="utf-8")
    assert "ráközelít" in szoveg                       # rövid horizont láthatóság
    assert "nem becsülhető" in szoveg                  # órás-only 3hó/1év
    assert "csak órás" in szoveg                       # az ok: nincs napi/heti forrás
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_pages.py::test_adatokrol_predikcio_uj_viselkedesek`
Expected: FAIL — ezek a szövegek még nincsenek az adatokrol.html-ben.

- [ ] **Step 3: Write minimal implementation**

`docs/adatokrol.html`, a „Miért óvatos a hosszú táv?" `<p>` (87. sor) UTÁN, a „A képletek dióhéjban" (88) ELÉ:

```html
      <p><strong>Rövid és hosszú horizont, felbontás.</strong> A horizont naptári hossza a megjelenített sorozat felbontásán lépésekre vált (a heti sorozaton az egy nap és az egy hét is a legközelebbi heti lépés). Rövid horizontot választva a chart a <strong>közelmúltra ráközelít</strong>, hogy a közeli előrejelzés – ami egy hosszú idősor jobb szélén amúgy elveszne – jól látszódjon.</p>
      <p><strong>Miért nincs 3 hó / 1 év minden szóra?</strong> Néhány szót csak <strong>órás</strong> felbontásban mérünk (nincs napi/heti sora). Egy pár hónapnyi órás pillanatkép-láncból egy évet előrejelezni <strong>nem megbízható</strong>, ezért ezeknél a hosszú horizontokon nem rajzolunk előrejelzést, hanem őszintén jelezzük: ez a horizont ezen a szón <strong>nem becsülhető</strong> megbízhatóan.</p>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_pages.py`
Expected: PASS (az új teszt + a meglévő oldal-tesztek zöldek).

- [ ] **Step 5: Commit**

```bash
git add docs/adatokrol.html tests/test_pages.py
git commit -m "docs(predikcio): info-oldal rovid-horizont zoom + oras-only hosszu tav magyarazat"
```

---

## Önellenőrzés (a terv írója)

- **Spec-lefedettség:** #1 → Task 1 (backend sentinel) + Task 2 (frontend üzenet); #2 → Task 3 (auto-zoom); #3 → Task 4 (infó). ✓
- **Placeholder-szken:** nincs TBD/„handle edge cases"; a zoom-konstansok konkrét kezdőértékkel (0.25 / 4), a szemle/élő-előnézet hangolhatja. ✓
- **Típus-konzisztencia:** a sentinel alak `{"nem_becsulheto": true}` MINDENHOL azonos (Task 1 backend írja, Task 2 frontend olvassa, e2e mockolja); a `predikcio_blk` null a sentinelnél → nincs rajzolás/± szöveg. ✓
