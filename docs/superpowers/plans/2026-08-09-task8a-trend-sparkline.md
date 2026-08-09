# Task 8a — Trend-sparkline + görbe nélküli kártya — Implementációs terv

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A trend-blokk minden kártyája kapjon napi idősor-sparkline-t; a görbe nélküli (D1-kiterjesztett) kártya elemenkénti üzenetet, a mind-üres nap egyetlen blokk-szintű jelzést.

**Architecture:** A `trend_kartya_epit` DOM-oldalon eldönti a `data-idosor-allapot`-ot (BINÁRIS: van/nincs) és vagy sparkline-konténert, vagy üres-szöveget tesz. A Chart.js-példányok KÜLÖN életciklust kapnak (`trend_chart_peldanyok` map, AZONNALI rajzolás — mint a `kategoria_chart` ma), amit a globális kulcsszó-`chart_takarit()` NEM érint. **Lusta IntersectionObserver-t szándékosan NEM vezetünk be** (a (b) döntés: „a második observer ne előfeltevésből szülessen"; a rootMargin/L10-hangolás nem duplikálódik). A lusta rajzolás a 8a UTÁN, egy ELDOBHATÓ diagnosztikai spec költség-kimutatása alapján jöhet, külön kör. A mind-üres napot a `trend_blokk_render` összevonja.

**Tech Stack:** Vanilla JS (`docs/js/app.js`), Chart.js (globális), CSS (`docs/css/app.css`), Playwright e2e (`e2e/trend.spec.js`).

## Global Constraints

- Nyelv: minden kód + komment + teszt + ledger **MAGYARUL**.
- **A teljes Playwright-suite `--workers=1` alatt fut** (L12: a párhuzamos futás flaky; a soros a mérvadó). pytest változatlanul `.venv/bin/pytest`.
- **Kiindulási alap (soros):** Playwright **51**, pytest **224** — mind zöld. Minden commit ELŐTT teljes soros suite; ha bármelyik piros vagy a szám a várttól eltér → **REGRESSZIÓ = STOP**.
- TDD **valódi RED-del**; a RED-előrejelzés NÉVRE és HIBATÍPUSRA szól.
- Mutáció EGYENKÉNT, `/* MUTÁCIÓ */` kommenttel; a kör végén `grep -rn "MUTÁCIÓ" .` → **PONTOSAN 1** (`e2e/kulcsszo.spec.js:487`, a dokumentált példa).
- `git add` **NÉVVEL**; commit **CSAK jóváhagyás után**, az üzenetet előbb jóváhagyatni. Push **külön kör** (nem e terv része).
- DOM-szerződés a smoke-oknak: a teszt **az attribútumból** assertál (`data-idosor-allapot`), nem a szövegből.
- **BINÁRIS `data-idosor-allapot` (mért indok):** az `idosor` kulcs mind a 247+21 archív elemen JELEN van (üresen is) → nincs `hianyzik` ág. Ez MÉRT eltérés a `data-kategoria-allapot` hármasától.
- **Copy verbatim:** elemenkénti = `nincs idősor ezen a napon`; blokk-szintű = `Ezen a napon egyetlen felkapott trendhez sincs idősor.`
- **Öt smoke** (a design 4 nevesített + a §7.3 Tétel-4 blokk-szintű): (i) van→canvas, (ii) nincs→szöveg, (iii) archív→sparkline megvan, (iv) kulcsszó-váltás nem öli a sparkline-t, (v) mind-üres nap→blokk-jelzés. Végállapot: **Playwright 56**, pytest 224.
- **Teszt-számozás:** a meglévő `e2e/trend.spec.js` 1–17-ig számozott (a fejléc-komment „16 db"-ja elavult volt). Az új tesztek: Task 1 → 18./19., Task 2 → 20., Task 3 → 21., Task 4 → 22. A fájl fejléc-komment tesztszámát minden új teszttel frissítsd (Task 1 után 19; utána 20/21/22).

---

## File Structure

- `docs/js/app.js` — a trend-blokk logikája (OSZT_T/ATTR_T konstansok :590–600; `trend_kartya_epit` :706; `trend_chart_takarit` :658; `trend_blokk_render` :807). Itt történik a fő munka.
- `docs/css/app.css` — a `.trend-sparkline-doboz` fix-magasságú wrapper + üres-szövegek (:71 után).
- `e2e/trend.spec.js` — az 5 új smoke + a `trend()` fixture-helper bővítése idősorral (:14 körül).

Nincs pytest-érintettség (Task 8a tisztán frontend). Nincs új fájl.

---

## Task 1: DOM-szerződés — sparkline-konténer + elemenkénti üres állapot (BINÁRIS attribútum)

**Files:**
- Modify: `docs/js/app.js` (OSZT_T `:590`, ATTR_T `:596`, új konstansok `:604` után, `trend_kartya_epit` `:706`)
- Modify: `docs/css/app.css` (`:71` után)
- Test: `e2e/trend.spec.js` (a `trend()` helper `:14`, két új smoke a fájl végén)

**Interfaces:**
- Consumes: `OSZT_T`, `ATTR_T`, `trend_kartya_epit(t)` (jelenlegi egyparaméteres alak).
- Produces:
  - `OSZT_T.sparkline_doboz = "trend-sparkline-doboz"`, `OSZT_T.idosor_ures = "trend-idosor-ures"`
  - `ATTR_T.idosor_allapot = "data-idosor-allapot"` (érték `"van"`/`"nincs"`), `ATTR_T.idosor_rendered = "data-idosor-rendered"`
  - `TREND_IDOSOR_URES_ELEM = "nincs idősor ezen a napon"`
  - `trend_kartya_epit(t, blokk_ures)` — új 2. paraméter (boolean; `true` → az elemenkénti üres-szöveg ELMARAD, de a `data-idosor-allapot="nincs"` MARAD). A `van` ágon a kártyára kerül `k._idosor` (a pontok tömbje) a Task 2 lusta rajzolásához.

- [ ] **Step 1: Bővítsd a `trend()` fixture-helpert idősorral (e2e/trend.spec.js)**

A jelenlegi `:14` helper `idosor: []`-t ír. Add hozzá egy opcionális 4. paramétert és egy NEM-uniform sorozat-építőt (0.2/13 fixture-őr):

```javascript
// egy trend-elem; temak === undefined → a mező HIÁNYZIK (régi archív nap), [] → nincs besorolás, [...] → van.
// idosor: opcionális pont-tömb ({idopont_utc, ertek}); alap [] (üres — D1-kiterjesztett / mind-üres eset).
function trend(kifejezes, volumen, temak, idosor) {
  const e = { kifejezes, volumen, novekedes_pct: "100", idosor: idosor || [], hirek: [] };
  if (temak !== undefined) { e.temak = temak; e.topics = temak.map(function (_, i) { return i + 1; }); }
  return e;
}

// SZÁNDÉKOSAN nem-uniform sorozat: n pont, adott kezdettel, 8 perces ráccsal, szórt értékekkel.
// A fixture-ben két eltérő hosszú/kezdetű sorozat bizonyítja, hogy a kód nem feltételez fix pontszámot/közös kezdetet.
function idosor_sorozat(n, kezdet_iso) {
  const t0 = new Date(kezdet_iso).getTime();
  const pontok = [];
  for (let i = 0; i < n; i++) {
    pontok.push({ idopont_utc: new Date(t0 + i * 8 * 60000).toISOString(), ertek: (i % 3 === 0) ? 100 : 0 });
  }
  return pontok;
}
```

- [ ] **Step 2: Írd meg a két bukó smoke-ot (e2e/trend.spec.js, a fájl végére)**

```javascript
// ── T18 — idősoros kártya: canvas + data-idosor-allapot="van" (nem-uniform sorozatok) ──
test("18. idősoros kártya → canvas + data-idosor-allapot=van (nem-uniform)", async ({ page }) => {
  const VAN = [
    trend("alfa", "50000", ["Other"], idosor_sorozat(4, "2026-08-06T20:52:00+00:00")),
    trend("beta", "50000", ["Other"], idosor_sorozat(3, "2026-08-06T21:00:00+00:00")),
  ];
  await mock(page, { legfrissebb: { top_trendek: VAN } });
  await page.goto("/");
  const kartyak = page.locator(`${T} .trend-kartya[data-idosor-allapot="van"]`);
  await expect(kartyak).toHaveCount(2);
  await expect(kartyak.first().locator(".trend-sparkline-doboz canvas")).toHaveCount(1);
});

// ── T19 — D1-kiterjesztett (üres idosor) kártya: elemenkénti üzenet + data-idosor-allapot="nincs", NINCS canvas ──
test("19. üres idosor → 'nincs idősor ezen a napon' + data-idosor-allapot=nincs, nincs canvas", async ({ page }) => {
  const VEGYES = [
    trend("van-gorbe", "50000", ["Other"], idosor_sorozat(4, "2026-08-06T20:52:00+00:00")),
    trend("nincs-gorbe", "2000", ["Other"]),   // D1-kiterjesztett: idosor []
  ];
  await mock(page, { legfrissebb: { top_trendek: VEGYES } });
  await page.goto("/");
  const nincs = page.locator(`${T} .trend-kartya[data-idosor-allapot="nincs"]`);
  await expect(nincs).toHaveCount(1);
  await expect(nincs.locator(".trend-idosor-ures")).toHaveText("nincs idősor ezen a napon");
  await expect(nincs.locator("canvas")).toHaveCount(0);
});
```

- [ ] **Step 3: Futtasd — RED (a viselkedés még nincs)**

Run: `npx playwright test e2e/trend.spec.js:"18. idősoros" e2e/trend.spec.js:"19. üres idosor" --workers=1`
Expected: **FAIL** — a `.trend-kartya[data-idosor-allapot="van"]` locator 0 elemet talál (`toHaveCount(2)` vs 0), mert a `trend_kartya_epit` még nem állít `data-idosor-allapot`-ot.

- [ ] **Step 4: Add hozzá a konstansokat (docs/js/app.js)**

Az `OSZT_T` (`:590`) `kifejezes`/`volumen`/`kategoria`/`ures` sora mellé:

```javascript
  kifejezes: "trend-kifejezes", volumen: "trend-volumen", kategoria: "trend-kategoria", ures: "ures",
  sparkline_doboz: "trend-sparkline-doboz", idosor_ures: "trend-idosor-ures",
```

Az `ATTR_T` (`:596`) `kategoria`/`count` sora mellé:

```javascript
  kategoria: "data-kategoria", count: "data-count",
  idosor_allapot: "data-idosor-allapot", idosor_rendered: "data-idosor-rendered",
```

A `TREND_URES_SZOVEG` (`:604`) alá:

```javascript
const TREND_IDOSOR_URES_ELEM = "nincs idősor ezen a napon";               // elemenkénti (D1-kiterjesztett kártya)
const TREND_IDOSOR_URES_BLOKK = "Ezen a napon egyetlen felkapott trendhez sincs idősor.";  // blokk-szintű (mind-üres nap, Task 3)
```

- [ ] **Step 5: Bővítsd a `trend_kartya_epit`-et (docs/js/app.js:706)**

A szignatúra kapjon 2. paramétert (`blokk_ures`) — ez a Task 1-ben **HOLT előre-deklaráció**: nincs hívó, aki `true`-t adna (a hívók `undefined`-et adnak → falsy → elemenkénti szöveg). A `true`-t majd a Task 3 hozza. Ezért a Task 1 commit-üzenete CSAK az elemenkénti üres állapotot + a konténert állítja, blokk-szintű viselkedést NEM. A `k.appendChild(kat);` UTÁN, a `return k;` ELŐTT jöjjön az idősor-blokk:

```javascript
function trend_kartya_epit(t, blokk_ures) {
```

```javascript
  k.appendChild(kat);

  // 8a: idősor-állapot BINÁRIS (az idosor kulcs mind a napi elemeken jelen van, üresen is → nincs "hianyzik")
  const idosor = Array.isArray(t.idosor) ? t.idosor : [];
  const van_idosor = idosor.length > 0;
  k.setAttribute(ATTR_T.idosor_allapot, van_idosor ? "van" : "nincs");
  if (van_idosor) {
    // H2b: fix-magasságú, position:relative WRAPPER (különben a canvas összeesik) — a Chart.js LUSTA (Task 2)
    const doboz = document.createElement("div");
    doboz.className = OSZT_T.sparkline_doboz;
    const canvas = document.createElement("canvas");
    doboz.appendChild(canvas);
    k.appendChild(doboz);
    k._idosor = idosor;   // a lusta Chart-példányosításhoz (Task 2)
  } else if (!blokk_ures) {
    // elemenkénti üzenet — CSAK ha NEM blokk-szintű összevonás (Task 3: mind-üres napon a szöveg összevonódik)
    const u = document.createElement("p");
    u.className = OSZT_T.idosor_ures;
    u.textContent = TREND_IDOSOR_URES_ELEM;
    k.appendChild(u);
  }
  return k;
}
```

- [ ] **Step 6: Add hozzá a CSS-t (docs/css/app.css, a `:71` `.trend-kartya` sor után)**

```css
#trend-blokk .trend-sparkline-doboz { position: relative; height: 64px; margin-top: .4rem; }
#trend-blokk .trend-idosor-ures { color: #666; font-style: italic; font-size: .85rem; margin-top: .4rem; }
```

- [ ] **Step 7: Futtasd — GREEN**

Run: `npx playwright test e2e/trend.spec.js:"18. idősoros" e2e/trend.spec.js:"19. üres idosor" --workers=1`
Expected: **PASS** (2 passed).

- [ ] **Step 8: Mutáció — a teszt tényleg harap?**

Írd át ideiglenesen a `van_idosor ? "van" : "nincs"`-et `"nincs"`-re `/* MUTÁCIÓ */` kommenttel:
`k.setAttribute(ATTR_T.idosor_allapot, "nincs" /* MUTÁCIÓ */);`
Run: `npx playwright test e2e/trend.spec.js:"18. idősoros" --workers=1` → **FAIL** (0 vs 2). Állítsd vissza. `grep -rn "MUTÁCIÓ" .` → PONTOSAN 1.

- [ ] **Step 9: Teljes soros suite (regresszió-őr)**

Run: `npx playwright test --workers=1` → **53 passed** (51 + 2). Run: `.venv/bin/pytest -q` → **224 passed**.

- [ ] **Step 10: Commit (jóváhagyott üzenettel, add NÉVVEL)**

```bash
git add docs/js/app.js docs/css/app.css e2e/trend.spec.js
git commit -F <jóváhagyott üzenet>
```
Javasolt üzenet: `feat(phase3): §7.3 Task 8a/1 — trend-kártya idősor-állapot (BINÁRIS) + sparkline-konténer + elemenkénti üres`

---

## Task 2: Lusta sparkline-életciklus — KÜLÖN a kulcsszó-charttól

**Files:**
- Modify: `docs/js/app.js` (`kategoria_chart` deklaráció mellé `:606`; `trend_chart_takarit` `:658`; új fn-ek `:658` köré; `trend_blokk_render` `:840` után)
- Test: `e2e/trend.spec.js` (egy új smoke)

**Interfaces:**
- Consumes: `k._idosor` (Task 1), `ATTR_T.idosor_allapot`, `ATTR_T.idosor_rendered`, `ATTR_T.kifejezes`, `OSZT_T.kartya`.
- Produces:
  - `trend_chart_peldanyok` (objektum: `kifejezes` → Chart) — KÜLÖN a kulcsszó `chart_peldanyok`-tól
  - `trend_sparkline_letrehoz(kartya)` — AZONNALI Chart-példányosítás, `data-idosor-rendered="true"` idempotencia-őrrel
  - a bővített `trend_chart_takarit()` a `kategoria_chart`-ot ÉS a `trend_chart_peldanyok`-ot is destroy-olja (nincs observer, amit disconnectálni kellene)

- [ ] **Step 1: Írd meg a bukó életciklus-őr smoke-ot (e2e/trend.spec.js)**

A kulcsszó-intervallum váltás (ami a globális `chart_takarit()`-ot hívja) NEM ölheti meg a trend-sparkline Chart-példányt. Megfigyelhető: `Chart.getChart(canvas)` a váltás UTÁN is példányt ad.

```javascript
// ── T20 — KÜLÖN életciklus: kulcsszó-intervallum váltás NEM destroy-olja a trend-sparkline-t (L9-őr) ──
test("20. kulcsszó-intervallum váltás után a trend-sparkline Chart él (KÜLÖN életciklus)", async ({ page }) => {
  // LOKÁLIS route CSAK ide (a közös mock()-ot a 16 meglévő smoke használja — ott NEM bővítünk). Két intervallum
  // ervenyes → van kattintható, a default-kiválasztottól (leghosszabb=1_ho) KÜLÖNBÖZŐ gomb (1_het) is.
  await page.route(/kulcsszo_regresszio\.json/, function (r) {
    r.fulfill({ contentType: "application/json", body: JSON.stringify({
      kulcsszavak: { "próba": { aktiv: true, domen: "g", tipus: "szintmero", intervallumok: {
        "1_het": { ervenyes: true, meredekseg_nap: -1.0, se_meredekseg: 0.5, irany: "csokken" },
        "2_het": { ervenyes: false, ok: "nincs_lancolas" },
        "1_ho":  { ervenyes: true, meredekseg_nap: -1.0, se_meredekseg: 0.5, irany: "csokken" },
        "3_ho":  { ervenyes: false, ok: "nincs_lancolas" },
        "1_ev":  { ervenyes: false, ok: "nincs_lancolas" },
      } } },
    }) });
  });
  await mock(page, {
    legfrissebb: { top_trendek: [ trend("alfa", "50000", ["Other"], idosor_sorozat(4, "2026-08-06T20:52:00+00:00")) ] },
  });
  await page.goto("/");
  const canvas = page.locator(`${T} .trend-sparkline-doboz canvas`).first();
  await expect(canvas).toHaveCount(1);
  // AZONNALI rajzolás: a Chart már a renderkor létezik (nincs scrollIntoView / első poll)
  expect(await canvas.evaluate((c) => !!Chart.getChart(c))).toBe(true);
  // kulcsszó-intervallum váltás (1_het, ≠ a default-kiválasztott 1_ho) → globális chart_takarit() fut
  await page.locator("#intervallum-vezerlo button:not([disabled])").first().click();
  // a trend-sparkline Chart TOVÁBBRA is él (a KÜLÖN életciklus nem engedte destroy-olni)
  expect(await canvas.evaluate((c) => !!Chart.getChart(c))).toBe(true);
});
```

- [ ] **Step 2: Futtasd — RED**

Run: `npx playwright test e2e/trend.spec.js:"20. kulcsszó-intervallum" --workers=1`
Expected: **FAIL** — a `.trend-sparkline-doboz canvas` létezik (Task 1), de nincs `trend_sparkline_letrehoz`, így Chart sem rajzolódik → a KATTINTÁS ELŐTTI `expect(... Chart.getChart(c)).toBe(true)` bukik (`false` a `true` helyett). A RED tehát a lényegi állításon (van-e Chart), nem timeouton.

- [ ] **Step 3: Add hozzá a KÜLÖN életciklus-állapotot (docs/js/app.js, a `:606` `kategoria_chart` sor mellé)**

```javascript
let kategoria_chart = null;        // az eloszlás-chart SAJÁT példánya (NEM a kulcsszó chart_peldanyok/chart_takarit)
let trend_chart_peldanyok = {};    // 8a: kifejezes -> sparkline Chart — KÜLÖN a kulcsszó chart_peldanyok-tól
```

- [ ] **Step 4: Írd meg az azonnali sparkline-rajzolót (docs/js/app.js, a `trend_chart_takarit` `:658` fölé)**

```javascript
// egy trend-sparkline AZONNALI Chart-példányosítása (mint a kategoria_chart ma — NINCS lusta observer).
// Önnormalizált y (0–100), mért nullák (spanGaps:false), NEM feltételez folytonos alapszintet; tengely/legend/
// tooltip nélkül (sparkline; a tooltip a 8b hatóköre). A data-idosor-rendered idempotencia-őr.
function trend_sparkline_letrehoz(kartya) {
  if (kartya.getAttribute(ATTR_T.idosor_rendered) === "true") return;
  const idosor = kartya._idosor;
  const canvas = kartya.querySelector("canvas");
  if (!idosor || !canvas || typeof Chart === "undefined") return;
  trend_chart_peldanyok[kartya.getAttribute(ATTR_T.kifejezes)] = new Chart(canvas, {
    type: "line",
    data: {
      labels: idosor.map(function (p) { return p.idopont_utc; }),   // időbélyeg-alapú (SOHA nem index-alapú)
      datasets: [{ data: idosor.map(function (p) { return p.ertek; }), spanGaps: false,
                   borderColor: "#3366cc", borderWidth: 1, pointRadius: 0 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      scales: { x: { display: false }, y: { display: false, min: 0, max: 100 } },
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });
  kartya.setAttribute(ATTR_T.idosor_rendered, "true");
}
```

- [ ] **Step 5: Bővítsd a `trend_chart_takarit`-ot (docs/js/app.js:658)**

```javascript
function trend_chart_takarit() {
  if (kategoria_chart) { kategoria_chart.destroy(); kategoria_chart = null; }
  Object.keys(trend_chart_peldanyok).forEach(function (k) {   // 8a: a sparkline-példányok is destroy (nem halmozódhatnak)
    if (trend_chart_peldanyok[k]) trend_chart_peldanyok[k].destroy();
    delete trend_chart_peldanyok[k];
  });
}
```

- [ ] **Step 6: Kösd be a `trend_blokk_render`-be (docs/js/app.js, a `blokk.appendChild(lista);` `:840` UTÁN)**

```javascript
  blokk.appendChild(lista);

  // 8a: a "van" kártyák sparkline-jai AZONNAL rajzolódnak (mint a kategoria_chart ma) — a lista már a DOM-ban van
  Array.prototype.slice.call(
    lista.querySelectorAll("." + OSZT_T.kartya + "[" + ATTR_T.idosor_allapot + "='van']"))
    .forEach(trend_sparkline_letrehoz);

  trend_szinkron(blokk);   // a kezdő állapot (nincs szűrés) szinkronja
```

- [ ] **Step 7: Futtasd — GREEN**

Run: `npx playwright test e2e/trend.spec.js:"20. kulcsszó-intervallum" --workers=1`
Expected: **PASS** (1 passed).

- [ ] **Step 8: Mutáció — a KÜLÖN életciklus tényleg véd?**

A `trend_sparkline_letrehoz`-ban írd a példányt ideiglenesen a GLOBÁLIS mapbe `/* MUTÁCIÓ */` kommenttel:
`chart_peldanyok[kartya.getAttribute(ATTR_T.kifejezes)] = new Chart(...` — így a globális `chart_takarit()` a kulcsszó-váltáskor destroy-olná.
Run: `npx playwright test e2e/trend.spec.js:"20. kulcsszó-intervallum" --workers=1` → **FAIL** (a második poll `false`). Állítsd vissza. `grep -rn "MUTÁCIÓ" .` → PONTOSAN 1.

- [ ] **Step 9: Teljes soros suite**

Run: `npx playwright test --workers=1` → **54 passed**. Run: `.venv/bin/pytest -q` → **224 passed**.

- [ ] **Step 10: Commit**

```bash
git add docs/js/app.js e2e/trend.spec.js
git commit -F <jóváhagyott üzenet>
```
Javasolt üzenet: `feat(phase3): §7.3 Task 8a/2 — trend-sparkline KÜLÖN életciklus (trend_chart_peldanyok + trend_megfigyelo)`

---

## Task 3: Blokk-szintű összevonás — mind-üres nap

**Files:**
- Modify: `docs/js/app.js` (`trend_blokk_render` `:807`; `OSZT_T` `:590`)
- Modify: `docs/css/app.css` (`:71` után)
- Test: `e2e/trend.spec.js` (egy új smoke)

**Interfaces:**
- Consumes: `trend_kartya_epit(t, blokk_ures)` (Task 1), `TREND_IDOSOR_URES_BLOKK` (Task 1), `ATTR_T.idosor_allapot`.
- Produces: `OSZT_T.idosor_ures_blokk = "trend-idosor-ures-blokk"`; a `trend_blokk_render` a `trendek.every(üres)` esetben egyetlen blokk-jelzést tesz a szekció élére, és a kártyáknak `blokk_ures=true`-t ad (elemenkénti szöveg elmarad, `data-idosor-allapot="nincs"` marad).

- [ ] **Step 1: Írd meg a bukó smoke-ot (e2e/trend.spec.js)**

```javascript
// ── T21 — mind-üres nap (idosor-ág bukása): EGY blokk-szintű jelzés, NINCS elemenkénti fal ──
test("21. mind-üres nap → egyetlen blokk-jelzés, N kártya data-idosor-allapot=nincs, nincs elemenkénti szöveg", async ({ page }) => {
  const MIND_URES = [
    trend("egy", "50000", ["Other"]),    // mind idosor: []
    trend("ketto", "10000", ["Politics"]),
    trend("harom", "5000", ["Other"]),
  ];
  await mock(page, { legfrissebb: { top_trendek: MIND_URES } });
  await page.goto("/");
  await expect(page.locator(`${T} .trend-idosor-ures-blokk`)).toHaveText("Ezen a napon egyetlen felkapott trendhez sincs idősor.");
  await expect(page.locator(`${T} .trend-kartya[data-idosor-allapot="nincs"]`)).toHaveCount(3);
  await expect(page.locator(`${T} .trend-idosor-ures`)).toHaveCount(0);   // az elemenkénti szöveg ÖSSZEVONÓDOTT
});
```

- [ ] **Step 2: Futtasd — RED**

Run: `npx playwright test e2e/trend.spec.js:"21. mind-üres" --workers=1`
Expected: **FAIL** — nincs `.trend-idosor-ures-blokk` (0 vs szöveg), és a `.trend-idosor-ures` count 3 (elemenkénti fal) a várt 0 helyett.

- [ ] **Step 3: Add hozzá a blokk-osztály konstansát (docs/js/app.js:590, OSZT_T)**

Az `idosor_ures` mellé:

```javascript
  sparkline_doboz: "trend-sparkline-doboz", idosor_ures: "trend-idosor-ures", idosor_ures_blokk: "trend-idosor-ures-blokk",
```

- [ ] **Step 4: Bővítsd a `trend_blokk_render`-t (docs/js/app.js:834–840)**

A `const eloszlas = ...` és a lista-építés közé kerül a mind-üres detektálás és a blokk-jelzés; a kártya-építés `mind_ures`-t ad át:

```javascript
  const eloszlas = kategoria_eloszlas(trendek);
  if (eloszlas.length > 0) blokk.appendChild(trend_osszefoglalo_epit(trendek, eloszlas, blokk));

  // 8a Tétel-4: ha a nap MINDEN eleme üres idosor-ú (idosor-ág bukása), az elemenkénti üzenet EGY blokk-jelzéssé
  // vonódik össze (üres == elemszám; köztes arányoknál elemenkénti marad). A kártyák data-idosor-allapot="nincs"-e MARAD.
  const mind_ures = trendek.every(function (t) { return !Array.isArray(t.idosor) || t.idosor.length === 0; });
  if (mind_ures) {
    const bu = document.createElement("p");
    bu.className = OSZT_T.idosor_ures_blokk;
    bu.textContent = TREND_IDOSOR_URES_BLOKK;
    blokk.appendChild(bu);   // a szekció élén, a lista előtt
  }

  const lista = document.createElement("div");
  lista.className = OSZT_T.lista;
  trendek.forEach(function (t) { lista.appendChild(trend_kartya_epit(t, mind_ures)); });   // NINCS fix hossz-feltevés
  blokk.appendChild(lista);
```

Fontos: a `trend_blokk_render` takarító sora (`:816`) is bővüljön, hogy a napváltás eltakarítsa a régi blokk-jelzést:

```javascript
  blokk.querySelectorAll("." + OSZT_T.osszefoglalo + ", ." + OSZT_T.lista + ", ." + OSZT_T.ures + ", ." + OSZT_T.idosor_ures_blokk)
    .forEach(function (e) { e.remove(); });
```

- [ ] **Step 5: Add hozzá a CSS-t (docs/css/app.css, a `.trend-idosor-ures` sor mellé)**

```css
#trend-blokk .trend-idosor-ures-blokk { color: #666; font-style: italic; margin: .5rem 0; }
```

- [ ] **Step 6: Futtasd — GREEN**

Run: `npx playwright test e2e/trend.spec.js:"21. mind-üres" --workers=1`
Expected: **PASS** (1 passed).

- [ ] **Step 7: Mutáció — a küszöb tényleg "mind"?**

Írd a `.every`-t `.some`-ra `/* MUTÁCIÓ */`-val: `trendek.some(function (t) {... } /* MUTÁCIÓ */)`. Egy vegyes napon ez tévesen összevonna; a T19 (vegyes nap) elbukna. Run: `npx playwright test e2e/trend.spec.js:"19. üres idosor" --workers=1` → **FAIL** (a `.trend-idosor-ures` eltűnt). Állítsd vissza. `grep -rn "MUTÁCIÓ" .` → PONTOSAN 1.

- [ ] **Step 8: Teljes soros suite**

Run: `npx playwright test --workers=1` → **55 passed**. Run: `.venv/bin/pytest -q` → **224 passed**.

- [ ] **Step 9: Commit**

```bash
git add docs/js/app.js docs/css/app.css e2e/trend.spec.js
git commit -F <jóváhagyott üzenet>
```
Javasolt üzenet: `feat(phase3): §7.3 Task 8a/3 — mind-üres nap blokk-szintű összevonása (Tétel 4)`

---

## Task 4: Archív-nap diszkriminátor smoke (idősor ott is MEGVAN)

**Files:**
- Test: `e2e/trend.spec.js` (egy új smoke — tiszta teszt-task, a §5 diszkriminátort őrzi)

**Interfaces:**
- Consumes: `trend()`, `idosor_sorozat()`, `mock()` (index + napok route), `ATTR_T.idosor_allapot`.
- Produces: nincs kódtermék — a viselkedést (archív napon idősor van, de kategória-chart+szűrő nincs) rögzítő őr.

Indok (spec §5): a `2026-07-30` archívumban a kártyáknak VAN `idosor`-uk, de NINCS `temak`-juk. A meglévő T10 azt őrzi, hogy régi napon a chart+szűrő ELTŰNIK; ez az őr azt teszi hozzá, hogy a **sparkline viszont MEGVAN** — jó diszkriminátor.

- [ ] **Step 1: Írd meg a smoke-ot (e2e/trend.spec.js)**

```javascript
// ── T22 — archív nap (temak nélkül, idosor-ral): sparkline MEGVAN, de kategória-chart + szűrő NINCS ──
test("22. archív nap → sparkline megvan, kategória-chart+szűrő nincs (diszkriminátor)", async ({ page }) => {
  const REGI_IDOS = [
    trend("autóversenyző", "10000", undefined, idosor_sorozat(4, "2026-07-29T20:52:00+00:00")),
    trend("valami", "5000", undefined, idosor_sorozat(3, "2026-07-29T21:00:00+00:00")),
  ];
  await mock(page, {
    legfrissebb: { top_trendek: [] },   // a legfrissebb nap üres, hogy a dátumválasztó a régi napra váltson
    index: { napok: ["2026-07-30", "2026-08-08"] },
    napok: { "2026-07-30": REGI_IDOS },
  });
  await page.goto("/");
  await page.locator("#datum-valaszto select").selectOption("2026-07-30");
  // sparkline MEGVAN
  await expect(page.locator(`${T} .trend-kartya[data-idosor-allapot="van"]`)).toHaveCount(2);
  await expect(page.locator(`${T} .trend-sparkline-doboz canvas`)).toHaveCount(2);
  // kategória-chart + szűrő NINCS (nincs temak → nincs eloszlás → nincs összefoglaló)
  await expect(page.locator(`${T} .kategoria-chart-doboz`)).toHaveCount(0);
  await expect(page.locator(`${T} .kategoria-szuro`)).toHaveCount(0);
});
```

- [ ] **Step 2: Futtasd — GREEN (a viselkedés a Task 1–2 után már megvan)**

Run: `npx playwright test e2e/trend.spec.js:"22. archív nap" --workers=1`
Expected: **PASS** (1 passed). Ha RED: ellenőrizd a dátumválasztó opció-értékét (`#datum-valaszto select` létező-e a fixture index-szel) — a mock `index`+`napok` route-jának egyeznie kell.

> Megjegyzés: ez a task tiszta teszt (nincs implementáció), ezért nincs külön mutáció-lépés — a T22 a Task 1–2 kódját GREEN-ként fedi le, a diszkriminátort a kettős assert (van sparkline / nincs kategória-chart) adja.

- [ ] **Step 3: Teljes soros suite**

Run: `npx playwright test --workers=1` → **56 passed**. Run: `.venv/bin/pytest -q` → **224 passed**.

- [ ] **Step 4: Commit**

```bash
git add e2e/trend.spec.js
git commit -F <jóváhagyott üzenet>
```
Javasolt üzenet: `test(phase3): §7.3 Task 8a/4 — archív-nap diszkriminátor, SZÁNDÉKOS ZÖLD (sparkline megvan, kategória-chart nincs)`

---

## Self-Review

**Spec-lefedettség (§7.3 patch tételei):**
- Tétel 1 (mért görbe-adatalak, önnormalizált 100, mért nullák spanGaps:false, nincs folytonos alapszint) → Task 2 `trend_sparkline_letrehoz` (y 0–100, spanGaps:false). ✔
- Tétel 2 (nem-uniform rács, időbélyeg-alapú) → Task 1 `idosor_sorozat` nem-uniform fixture + Task 2 `labels: idopont_utc` (nem index). ✔
- Tétel 3 (file:line drift) → nincs kód-teendő (a DOC-commit `776a471` már kiment). ✔
- Tétel 4 (blokk-szintű mind-üres nap) → Task 3. ✔
- Elemenkénti üres állapot (§7.3:398-406) → Task 1 (T19). ✔
- §7.5-től való különbözőség → a T21 a `.trend-idosor-ures-blokk`-ot a lista-szintű `.ures`-től elkülöníti; a mind-üres napon VAN trend (a §7.5 nem tüzel). ✔
- KÜLÖN chart-életciklus (design b) → Task 2 (T20). ✔
- BINÁRIS `data-idosor-allapot` (design c) → Task 1, Global Constraints. ✔
- Archív-diszkriminátor (§5) → Task 4 (T22). ✔

**Placeholder-ellenőrzés:** minden lépés valós kóddal/paranccsal; nincs TBD. ✔

**Típus-konzisztencia:** `k._idosor` (Task 1 állítja) ↔ `kartya._idosor` (Task 2 olvassa); `ATTR_T.idosor_allapot`/`idosor_rendered`, `OSZT_T.sparkline_doboz`/`idosor_ures`/`idosor_ures_blokk`, `TREND_IDOSOR_URES_ELEM`/`TREND_IDOSOR_URES_BLOKK` — a nevek végig egyeznek. ✔

**Számlálók:** 51 → 53 → 54 → 55 → 56 Playwright; pytest végig 224. ✔
