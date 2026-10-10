# Frontend IA + „Áttekintő" nyitóoldal — Implementációs terv

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Csoportosított főmenü + valódi „Áttekintő" nyitóoldal, hogy a felhasználó elkülönítse az elemzéseket (napi/heti/havi), a radar-jelzéseket és a nyers statisztikákat.

**Architecture:** Tisztán frontend. (1) A közös `<nav id="fomenu">` blokkot egységes, csoportosított változatra cseréljük mind a 8 oldalon. (2) Az átirányító `index.html`-t valódi Áttekintő oldallá alakítjuk (hero + mai kiemelt + 3 kártya + Infó-sáv). (3) Egy kis `attekinto.js` tölti a mai kiemeltet a napi elemzésből. Backend/adat/workflow VÁLTOZATLAN.

**Tech Stack:** Statikus HTML + vanilla JS; Playwright e2e; `app.css`. Nincs új függőség, nincs build.

**Spec:** `docs/superpowers/specs/2026-10-10-frontend-ia-attekinto-design.md`

## Global Constraints

- Tisztán frontend: SEMMI Python, workflow, adatfájl nem változik.
- `fetch` kizárólag a nyitóoldal mai-kiemeltjéhez (`data/elemzes.json`); minden más statikus link.
- Fail-soft mindenhol: adat hiánya sosem töri az oldalt.
- Magyar UI; tipográfiai idézőjel HTML-ben `„…"`, JS-stringben `„`/`”` (ASCII `"` lezárja a JS-stringet).
- `aria-current="page"` az aktív linken; a két nav-csoport `aria-label`-lel.
- NINCS `new Date()` a frontend-JS-ben.
- Nav-sorrend (link-sorrend): Áttekintő · Napi · Heti · Havi · Radar · Google · YouTube · Infó (8 link); a két kategória-címke `<span>`, NEM link.

## Review Focus

- `data/elemzes.json` betölt, de a `felkapott` kulcs hiányzik → a mai kiemelt csendben kimarad, nincs JS-hiba. (Task 3)
- A `mode` szerinti narratíva placeholder („…az esti futáskor…") vagy üres → a másik mód szövegére esünk vissza, nem placeholder jelenik meg. (Task 3)
- `felkapott.top` elem `kifejezes` nélkül → az üres chip kiszűrve, nem jön üres chip. (Task 3)
- A nav kategória-címkék (`.fomenu-cimke`) NEM linkek és nem navigálhatók (`#fomenu a` csak a 8 valódi linket adja). (Task 1)
- Az `index.html` mai-kiemelt `fetch` 404 / hálózati hiba → a hero, a 3 kártya és az Infó-sáv MINDIG megjelenik. (Task 3)

---

## Task 1: Csoportosított főmenü + CSS (7 tartalmi oldal) + e2e-frissítés

**Files:**
- Modify (nav-blokk csere): `docs/elemzes.html`, `docs/heti.html`, `docs/havi.html`, `docs/trendek.html`, `docs/youtube.html`, `docs/bovites.html`, `docs/adatokrol.html`
- Modify (CSS): `docs/css/app.css` (a `#fomenu` szabályok után)
- Modify (teszt): `e2e/menu.spec.js`, `e2e/elemzes.spec.js:23`

**Interfaces:**
- Produces: a kanonikus nav-blokk, amit a Task 2 (`index.html`) is használ, az „Áttekintő" linken `aktiv` jelöléssel. Osztályok: `.fomenu-home`, `.fomenu-csoport`, `.fomenu-cimke`, `.fomenu-onallo`.

**A kanonikus nav-blokk** (minden oldalon ez; az AKTÍV oldal linkje kap `class="aktiv" aria-current="page"`-t):

```html
<nav id="fomenu" aria-label="Fő menü">
  <a href="index.html" class="fomenu-home">Áttekintő</a>
  <div class="fomenu-csoport" aria-label="Elemzések">
    <span class="fomenu-cimke">Elemzések</span>
    <a href="elemzes.html">Napi</a>
    <a href="heti.html">Heti</a>
    <a href="havi.html">Havi</a>
  </div>
  <a href="bovites.html" class="fomenu-onallo">Radar</a>
  <div class="fomenu-csoport" aria-label="Statisztikák">
    <span class="fomenu-cimke">Statisztikák</span>
    <a href="trendek.html">Google</a>
    <a href="youtube.html">YouTube</a>
  </div>
  <a href="adatokrol.html" class="fomenu-onallo">Infó</a>
</nav>
```

**Aktív-jelölés oldalanként** (a felsorolt `href`-ű linkre `class="aktiv" aria-current="page"`):

| Oldal | Aktív link `href` |
|---|---|
| `elemzes.html` | `elemzes.html` |
| `heti.html` | `heti.html` |
| `havi.html` | `havi.html` |
| `trendek.html` | `trendek.html` |
| `youtube.html` | `youtube.html` |
| `bovites.html` | `bovites.html` |
| `adatokrol.html` | `adatokrol.html` |

- [ ] **Step 1: A menu.spec.js nav-elvárások frissítése (bukó teszt)**

A `e2e/menu.spec.js` első tesztjét (`menüsor: ...`) cseréld erre (a link-darab 8-ra, az új rövid címkékre, az új sorrendre, és az aktív = „Google"):

```javascript
test("menüsor: 8 link + 2 csoportcímke, aktív = Google; a linkek helyesek + sorrend", async ({ page }) => {
  await page.goto("/trendek.html");
  await expect(page.locator("#fomenu a")).toHaveCount(8);
  await expect(page.locator("#fomenu .fomenu-cimke")).toHaveText(["Elemzések", "Statisztikák"]);
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Google");
  await expect(page.locator('#fomenu a[href="index.html"]')).toHaveText("Áttekintő");
  await expect(page.locator('#fomenu a[href="elemzes.html"]')).toHaveText("Napi");
  await expect(page.locator('#fomenu a[href="heti.html"]')).toHaveText("Heti");
  await expect(page.locator('#fomenu a[href="havi.html"]')).toHaveText("Havi");
  await expect(page.locator('#fomenu a[href="bovites.html"]')).toHaveText("Radar");
  await expect(page.locator('#fomenu a[href="trendek.html"]')).toHaveText("Google");
  await expect(page.locator('#fomenu a[href="youtube.html"]')).toHaveText("YouTube");
  await expect(page.locator('#fomenu a[href="adatokrol.html"]')).toHaveText("Infó");
  await expect(page.locator("#fomenu a")).toHaveText(["Áttekintő", "Napi", "Heti", "Havi", "Radar", "Google", "YouTube", "Infó"]);
  await expect(page.locator("#labresz")).toBeAttached();
  await expect(page.locator("#adatokrol")).toHaveCount(0);
});
```

A per-oldal tesztekben (`youtube.html`, `havi.html`, `heti.html`, `bovites.html`) cseréld az aktív-szöveget és a nav-tömböt:
- `youtube.html` teszt: `aria-current` → `"YouTube"`;
- `havi.html` teszt: `aria-current` → `"Havi"`;
- `heti.html` teszt: `aria-current` → `"Heti"`;
- `bovites.html` teszt: `aria-current` → `"Radar"`;
- mindegyik `toHaveText([...])` nav-tömböt erre: `["Áttekintő", "Napi", "Heti", "Havi", "Radar", "Google", "YouTube", "Infó"]`.

Az Infó-oldal tesztben (`Infó oldal: ...`): `aria-current` → `"Infó"` (a `.adat-doboz`/`.adat-csoport` elvárások VÁLTOZATLANOK).

A „landing" tesztben (`landing: a gyökér ...`) csak az aktív-szöveget igazítsd (az index EKKOR MÉG átirányít; a viselkedést a Task 2 írja át):
```javascript
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Napi");
```

- [ ] **Step 2: elemzes.spec.js aktív-szöveg frissítése**

`e2e/elemzes.spec.js:23` sor:
```javascript
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Napi");
```

- [ ] **Step 3: Futtasd — bukjon**

Run: `npx playwright test e2e/menu.spec.js`
Expected: FAIL (a nav még a régi lapos szerkezet, nincs `.fomenu-cimke`, a linkek a régi hosszú szövegek).

- [ ] **Step 4: CSS — a csoportosítás stílusa**

`docs/css/app.css`-ben a `#fomenu a.aktiv { ... }` szabály UTÁN szúrd be:

```css
/* Csoportosított főmenü */
.fomenu-csoport { display: inline-flex; align-items: center; gap: .2rem; padding-left: .5rem; margin-left: .25rem; border-left: 1px solid #ddd; }
.fomenu-onallo { padding-left: .5rem; margin-left: .25rem; border-left: 1px solid #ddd; }
.fomenu-cimke { font-size: .64rem; text-transform: uppercase; letter-spacing: .04em; color: #999; white-space: nowrap; padding-right: .1rem; }
@media (max-width: 640px) {
  #fomenu { flex-wrap: wrap; }
  .fomenu-csoport { flex-basis: 100%; flex-wrap: wrap; border-left: none; padding-left: .2rem; margin-left: 0; }
  .fomenu-onallo { border-left: none; padding-left: .4rem; margin-left: 0; }
  .fomenu-cimke { flex-basis: 100%; padding-left: .2rem; }
}
```

- [ ] **Step 5: A nav-blokk cseréje mind a 7 tartalmi oldalon**

A 7 fájl (`elemzes.html`, `heti.html`, `havi.html`, `trendek.html`, `youtube.html`, `bovites.html`, `adatokrol.html`) jelenlegi `<nav id="fomenu">…</nav>` blokkját cseréld a fenti kanonikus blokkra, az adott oldalhoz tartozó linken `class="aktiv" aria-current="page"` jelöléssel (lásd a táblát). Például `trendek.html`-en:
```html
    <a href="trendek.html" class="aktiv" aria-current="page">Google</a>
```

- [ ] **Step 6: Futtasd — menjen át, és ne törjön más**

Run: `npx playwright test e2e/menu.spec.js e2e/elemzes.spec.js e2e/dashboard.spec.js`
Expected: PASS (minden nav-teszt zöld; a dashboard H1-teszt érintetlen).

- [ ] **Step 7: Commit**

```bash
git add docs/elemzes.html docs/heti.html docs/havi.html docs/trendek.html docs/youtube.html docs/bovites.html docs/adatokrol.html docs/css/app.css e2e/menu.spec.js e2e/elemzes.spec.js
git commit -m "feat(ui): csoportositott fomenu (Elemzesek/Radar/Statisztikak) + Info"
```

---

## Task 2: „Áttekintő" nyitóoldal statikus váza (`index.html`) + CSS

**Files:**
- Modify: `docs/index.html` (átirányítás → valódi oldal)
- Modify: `docs/css/app.css` (a nav-CSS után)
- Create: `e2e/attekinto.spec.js`
- Modify: `e2e/menu.spec.js` (a „landing" teszt viselkedés-átírása)

**Interfaces:**
- Consumes: a Task 1 kanonikus nav-blokkja (itt az „Áttekintő" link kap `aktiv`-ot).
- Produces: `#attekinto-kiemelt` üres konténer, amit a Task 3 `attekinto.js`-e tölt; `.attekinto-kartya` kártyák; `.attekinto-info-sav`.

**Az `index.html` teljes tartalma:**
```html
<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Trendfigyelő – Áttekintő</title>
  <link rel="stylesheet" href="css/app.css">
</head>
<body>
  <nav id="fomenu" aria-label="Fő menü">
    <a href="index.html" class="fomenu-home aktiv" aria-current="page">Áttekintő</a>
    <div class="fomenu-csoport" aria-label="Elemzések">
      <span class="fomenu-cimke">Elemzések</span>
      <a href="elemzes.html">Napi</a>
      <a href="heti.html">Heti</a>
      <a href="havi.html">Havi</a>
    </div>
    <a href="bovites.html" class="fomenu-onallo">Radar</a>
    <div class="fomenu-csoport" aria-label="Statisztikák">
      <span class="fomenu-cimke">Statisztikák</span>
      <a href="trendek.html">Google</a>
      <a href="youtube.html">YouTube</a>
    </div>
    <a href="adatokrol.html" class="fomenu-onallo">Infó</a>
  </nav>

  <header class="fejlec-doboz attekinto-hero">
    <h1>Trendfigyelő</h1>
    <p>Mire figyel ma Magyarország? Napi, heti és havi AI-elemzések, radar-jelzések és nyers keresési statisztikák egy helyen.</p>
  </header>

  <main id="attekinto">
    <section id="attekinto-kiemelt" aria-label="Mai kiemelt" aria-live="polite"></section>

    <div class="attekinto-kartyak">
      <section class="attekinto-kartya">
        <h2>Elemzések</h2>
        <p>Napi, heti és havi AI-összefoglalók arról, mi mozgatja a közbeszédet.</p>
        <nav class="attekinto-kartya-linkek" aria-label="Elemzések">
          <a href="elemzes.html">Napi</a>
          <a href="heti.html">Heti</a>
          <a href="havi.html">Havi</a>
        </nav>
      </section>
      <section class="attekinto-kartya">
        <h2>Radar</h2>
        <p>Szokatlan elmozdulások, ügyek életútja és kapcsolódó keresések.</p>
        <nav class="attekinto-kartya-linkek" aria-label="Radar">
          <a href="bovites.html">Radar megnyitása</a>
        </nav>
      </section>
      <section class="attekinto-kartya">
        <h2>Statisztikák</h2>
        <p>Nyers keresési és YouTube-nézettségi grafikonok.</p>
        <nav class="attekinto-kartya-linkek" aria-label="Statisztikák">
          <a href="trendek.html">Google</a>
          <a href="youtube.html">YouTube</a>
        </nav>
      </section>
    </div>

    <a class="attekinto-info-sav" href="adatokrol.html">Hogyan készül? Mit jelentenek az adatok? → Infó</a>
  </main>

  <footer id="labresz" aria-label="Lábléc"></footer>

  <script src="js/attekinto.js"></script>
</body>
</html>
```

**CSS** — `docs/css/app.css`-ben a nav-CSS után:
```css
/* Áttekintő nyitóoldal */
.attekinto-hero p { margin: .3rem 0 0; color: #444; max-width: 60ch; }
#attekinto { padding: 0 .4rem; }
#attekinto-kiemelt:empty { display: none; }
#attekinto-kiemelt { background: #f3f6fb; border-left: 3px solid #2a78d6; border-radius: 6px; padding: .7rem .9rem; margin: 0 0 1rem; }
.attekinto-kiemelt-cim { margin: 0 0 .3rem; font-size: 1rem; }
.attekinto-kiemelt-mondat { margin: 0 0 .5rem; color: #333; line-height: 1.5; }
.attekinto-kiemelt-chipek { display: flex; flex-wrap: wrap; gap: .35rem; margin-bottom: .5rem; }
.attekinto-chip { display: inline-block; padding: .1rem .55rem; border-radius: 999px; background: #e6eefb; color: #1b3a63; font-size: .82rem; }
.attekinto-kiemelt-link { font-size: .9rem; }
.attekinto-kartyak { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: .9rem; margin-bottom: 1rem; }
.attekinto-kartya { border: 1px solid #e3e3e3; border-radius: 8px; padding: .9rem 1rem; background: #fff; }
.attekinto-kartya h2 { margin: 0 0 .3rem; font-size: 1.1rem; }
.attekinto-kartya p { margin: 0 0 .6rem; color: #555; line-height: 1.45; }
.attekinto-kartya-linkek { display: flex; flex-wrap: wrap; gap: .5rem; }
.attekinto-kartya-linkek a { font-size: .9rem; color: #2a78d6; text-decoration: none; padding: .2rem .5rem; border: 1px solid #cfe0f5; border-radius: 6px; }
.attekinto-kartya-linkek a:hover { background: #eef4fc; }
.attekinto-info-sav { display: block; text-align: center; padding: .7rem; border: 1px dashed #c9c9c9; border-radius: 8px; color: #444; text-decoration: none; }
.attekinto-info-sav:hover { background: #f6f6f6; }
```

- [ ] **Step 1: Új e2e-fájl a statikus szerkezethez (bukó teszt)**

Hozd létre: `e2e/attekinto.spec.js`
```javascript
const { test, expect } = require("@playwright/test");

test("áttekintő: nav aktív = Áttekintő, 3 kártya + Infó-belépő, helyes linkek", async ({ page }) => {
  await page.goto("/index.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Áttekintő");
  await expect(page.locator(".attekinto-kartya")).toHaveCount(3);
  await expect(page.locator(".attekinto-kartya h2")).toHaveText(["Elemzések", "Radar", "Statisztikák"]);
  // terület-linkek
  await expect(page.locator('.attekinto-kartya a[href="elemzes.html"]')).toBeVisible();
  await expect(page.locator('.attekinto-kartya a[href="heti.html"]')).toBeVisible();
  await expect(page.locator('.attekinto-kartya a[href="havi.html"]')).toBeVisible();
  await expect(page.locator('.attekinto-kartya a[href="bovites.html"]')).toBeVisible();
  await expect(page.locator('.attekinto-kartya a[href="trendek.html"]')).toBeVisible();
  await expect(page.locator('.attekinto-kartya a[href="youtube.html"]')).toBeVisible();
  // Infó-belépő a nyitóoldalon is
  await expect(page.locator('.attekinto-info-sav[href="adatokrol.html"]')).toBeVisible();
});
```

- [ ] **Step 2: A „landing" teszt viselkedés-átírása a menu.spec.js-ben**

`e2e/menu.spec.js` „landing" tesztje (a gyökér már nem átirányít, hanem az Áttekintőt szolgálja):
```javascript
test("landing: a gyökér (/) az Áttekintő nyitóoldalt szolgálja", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Áttekintő");
  await expect(page.locator(".attekinto-kartya")).toHaveCount(3);
});
```

- [ ] **Step 3: Futtasd — bukjon**

Run: `npx playwright test e2e/attekinto.spec.js e2e/menu.spec.js`
Expected: FAIL (az `index.html` még átirányít, nincsenek `.attekinto-kartya` elemek).

- [ ] **Step 4: Az index.html átírása + CSS**

Írd felül `docs/index.html`-t a fenti teljes tartalommal, és told be a fenti CSS-blokkot `docs/css/app.css`-be.

- [ ] **Step 5: Futtasd — menjen át**

Run: `npx playwright test e2e/attekinto.spec.js e2e/menu.spec.js`
Expected: PASS (a statikus szerkezet-tesztek zöldek; a `#attekinto-kiemelt` üres — a Task 3 tölti).

- [ ] **Step 6: Commit**

```bash
git add docs/index.html docs/css/app.css e2e/attekinto.spec.js e2e/menu.spec.js
git commit -m "feat(ui): Attekinto nyitooldal statikus vaza (hero + 3 kartya + Info-sav)"
```

---

## Task 3: `attekinto.js` — mai kiemelt betöltése + e2e

**Files:**
- Create: `docs/js/attekinto.js`
- Modify: `e2e/attekinto.spec.js` (dinamikus tesztek + fail-soft + Review Focus)

**Interfaces:**
- Consumes: a Task 2 `#attekinto-kiemelt` konténere; a `data/elemzes.json` szerkezete: `{ mode: "reggel"|"este", felkapott: { top: [{kifejezes,...}], reggel: {szoveg}, este: {szoveg} } }`.
- Produces: a `#attekinto-kiemelt`-be renderelt „Mai kiemelt" blokk (cím + vezető mondat + top chipek + „Tovább…" link).

**Az `attekinto.js` teljes tartalma:**
```javascript
"use strict";
// Áttekintő nyitóoldal: a „mai kiemelt" betöltése a napi elemzésből (data/elemzes.json).
// NINCS new Date(); a nap/mód az adatból jön. Fail-soft: hiány esetén a blokk üres marad.

function attekinto_el(tag, cls, szoveg) {
  const h = document.createElement(tag);
  if (cls) h.className = cls;
  if (szoveg != null) h.textContent = szoveg;
  return h;
}

async function attekinto_json(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch (e) { return null; }
}

function attekinto_elso_mondat(szoveg) {
  if (!szoveg) return "";
  const s = String(szoveg).trim();
  if (!s) return "";
  const m = s.match(/^[\s\S]*?[.!?](\s|$)/);
  let r = (m ? m[0] : s).trim();
  if (r.length > 240) r = r.slice(0, 240).trim() + "…";
  return r;
}

function attekinto_placeholder(t) {
  return !t || !String(t).trim() || String(t).indexOf("az esti futáskor") !== -1;
}

function attekinto_narrativa(fel, mode) {
  const sorrend = mode === "este" ? ["este", "reggel"] : ["reggel", "este"];
  for (let i = 0; i < sorrend.length; i++) {
    const k = sorrend[i];
    const t = fel && fel[k] && fel[k].szoveg;
    if (!attekinto_placeholder(t)) return t;
  }
  return "";
}

function attekinto_kiemelt_render(cel, d) {
  if (!cel) return;
  cel.innerHTML = "";
  const fel = (d && d.felkapott) || {};
  const mondat = attekinto_elso_mondat(attekinto_narrativa(fel, d && d.mode));
  const top = (fel.top || []).map(function (x) { return x && x.kifejezes; }).filter(Boolean).slice(0, 5);
  if (!mondat && !top.length) return;   // fail-soft: nincs mit mutatni
  cel.appendChild(attekinto_el("h2", "attekinto-kiemelt-cim", "Mai kiemelt"));
  if (mondat) cel.appendChild(attekinto_el("p", "attekinto-kiemelt-mondat", mondat));
  if (top.length) {
    const chipek = attekinto_el("div", "attekinto-kiemelt-chipek");
    top.forEach(function (sz) { chipek.appendChild(attekinto_el("span", "attekinto-chip", sz)); });
    cel.appendChild(chipek);
  }
  const link = attekinto_el("a", "attekinto-kiemelt-link", "Tovább a napi elemzéshez →");
  link.href = "elemzes.html";
  cel.appendChild(link);
}

async function attekinto_init() {
  const d = await attekinto_json("data/elemzes.json");
  attekinto_kiemelt_render(document.getElementById("attekinto-kiemelt"), d);
}

attekinto_init();
```

- [ ] **Step 1: Dinamikus + fail-soft tesztek (bukó)**

Told be `e2e/attekinto.spec.js`-be (a meglévő statikus teszt UTÁN):
```javascript
const EL_REGGEL = { nap: "2026-10-10", mode: "reggel", felkapott: {
  top: [{ kifejezes: "időjárás", volumen: "100000" }, { kifejezes: "andoni iraola" }, { kifejezes: "atomerőmű" },
        { kifejezes: "" }, { kifejezes: "farm vip 2026" }, { kifejezes: "galavízió" }],
  reggel: { szoveg: "Ma reggel az időjárás viszi a prímet. Mögötte több hír áll." },
  este: { szoveg: "Ez a rész az esti futáskor (21:00) frissül." } } };

test("áttekintő: mai kiemelt reggel — vezető mondat + top chipek (üres kifejezés kiszűrve)", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: EL_REGGEL }));
  await page.goto("/index.html");
  await expect(page.locator("#attekinto-kiemelt")).toContainText("Mai kiemelt");
  await expect(page.locator("#attekinto-kiemelt .attekinto-kiemelt-mondat")).toHaveText("Ma reggel az időjárás viszi a prímet.");
  await expect(page.locator("#attekinto-kiemelt .attekinto-chip")).toHaveCount(5);   // a 6-ból az üres kifejezés kiesik
  await expect(page.locator("#attekinto-kiemelt .attekinto-chip").first()).toHaveText("időjárás");
  await expect(page.locator('#attekinto-kiemelt a[href="elemzes.html"]')).toBeVisible();
});

test("áttekintő: este módban placeholder esti szöveg → a reggeli narratívára esik vissza", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: {
    nap: "2026-10-10", mode: "este",
    felkapott: { top: [{ kifejezes: "benzin" }], reggel: { szoveg: "Reggeli vezető mondat. Folytatás." },
                 este: { szoveg: "Ez a rész az esti futáskor (21:00) frissül." } } } }));
  await page.goto("/index.html");
  await expect(page.locator("#attekinto-kiemelt .attekinto-kiemelt-mondat")).toHaveText("Reggeli vezető mondat.");
});

test("áttekintő: mai kiemelt fail-soft — hiányzó felkapott + 404", async ({ page }) => {
  // 404: a kiemelt üres, de a kártyák + Infó megmaradnak
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/index.html");
  await expect(page.locator("#attekinto-kiemelt")).toBeEmpty();
  await expect(page.locator(".attekinto-kartya")).toHaveCount(3);
  await expect(page.locator('.attekinto-info-sav[href="adatokrol.html"]')).toBeVisible();
});

test("áttekintő: mai kiemelt fail-soft — elemzes.json van, de nincs felkapott kulcs", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: { nap: "2026-10-10", mode: "reggel" } }));
  await page.goto("/index.html");
  await expect(page.locator("#attekinto-kiemelt")).toBeEmpty();
  await expect(page.locator(".attekinto-kartya")).toHaveCount(3);
});
```

- [ ] **Step 2: Futtasd — bukjon**

Run: `npx playwright test e2e/attekinto.spec.js`
Expected: FAIL (nincs `attekinto.js`, a `#attekinto-kiemelt` üres marad, a dinamikus tesztek buknak).

- [ ] **Step 3: Hozd létre a `docs/js/attekinto.js`-t** a fenti teljes tartalommal.

- [ ] **Step 4: Futtasd — menjen át**

Run: `npx playwright test e2e/attekinto.spec.js`
Expected: PASS (minden dinamikus + fail-soft teszt zöld).

- [ ] **Step 5: Szintaxis-ellenőrzés + teljes suite**

Run: `node --check docs/js/attekinto.js && npx playwright test && .venv/bin/python -m pytest -q`
Expected: `SYNTAX OK` implicit (hibátlan), a teljes Playwright suite zöld, a pytest 733 zöld (érintetlen).

- [ ] **Step 6: Commit**

```bash
git add docs/js/attekinto.js e2e/attekinto.spec.js
git commit -m "feat(ui): Attekinto mai kiemelt (napi elemzesbol, fail-soft) + e2e"
```

---

## Self-Review

**1. Spec-lefedettség:**
- Csoportos nav (spec §1) → Task 1. ✓
- Áttekintő oldal hero + kártyák + Infó-sáv (spec §2) → Task 2. ✓
- Mai kiemelt forrása/logika (spec §3) → Task 3. ✓
- Stílus/reszponzivitás (spec §4) → Task 1 (nav-CSS) + Task 2 (attekinto-CSS). ✓
- Hibatűrés (spec §5) → Task 3 fail-soft tesztek + `#attekinto-kiemelt:empty{display:none}`. ✓
- Tesztelés (spec §6) → mindhárom task e2e-vel; menu.spec + elemzes.spec frissítve. ✓
- Rollout (spec §7) → a 7 oldal Task 1-ben, index Task 2-ben, js Task 3-ban. ✓

**2. Placeholder-scan:** nincs TBD/TODO; minden lépés konkrét kóddal. ✓

**3. Típus-konzisztencia:** a nav-osztályok (`.fomenu-home/-csoport/-cimke/-onallo`) a Task 1 és Task 2 közt egyeznek; a `#attekinto-kiemelt` id és a `.attekinto-*` osztályok a Task 2 (HTML/CSS) és Task 3 (JS) közt egyeznek; a `data/elemzes.json` mezőnevek (`mode`, `felkapott.top[].kifejezes`, `felkapott.reggel/este.szoveg`) megegyeznek az élő adattal. ✓

**4. Review Focus:** mind az 5 tétel kap tesztet — hiányzó `felkapott` (Task 3 Step 1, utolsó teszt), placeholder-fallback (Task 3, este-teszt), üres `kifejezes` kiszűrés (Task 3, reggel-teszt chip-count=5), kategória-címke nem link (Task 1, `#fomenu a` count=8 + `.fomenu-cimke` külön), 404 fail-soft (Task 3, 404-teszt). ✓
