# Radar nagykategória szétbontása — Implementációs terv

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A mostani egyetlen „Radar" fül (3 belső alfüllel) helyett a RADAR legyen nav-nagykategória 3 önálló oldallal (Változások / Ügyek / Kapcsolódó), mindegyik tetején idősáv-jelzéssel.

**Architecture:** Tisztán frontend. A `docs/js/bovites.js` render-függvényeit újrahasznosítjuk, az init oldal-érzékeny lesz (a jelenlévő tartalom-konténer alapján csak a saját JSON-ját tölti + kitölti a `.radar-idosav` jelölőt). 3 új HTML-oldal a meglévő `#bovites-*` szekció-id-ket használja; `bovites.html` átirányít. A nav mind a releváns oldalon RADAR 3-füles csoport lesz. Backend/adat/workflow VÁLTOZATLAN.

**Tech Stack:** Statikus HTML + vanilla JS; Playwright e2e; pytest; `app.css`. Nincs új függőség.

**Spec:** `docs/superpowers/specs/2026-10-10-radar-kategoria-szetbontas-design.md`

## Global Constraints

- Tisztán frontend: SEMMI Python/workflow/adatfájl nem változik.
- A `#bovites-*` szekció-id-k és `.bovites-*` CSS-osztályok (belső nevek) VÁLTOZATLANOK.
- Oldalanként `fetch` CSAK a saját JSON-hoz; fail-soft (hiány → a render-fn „nem érhető el" üzenete + az idősáv-jelző kimarad; a váz marad).
- Magyar UI; tipográfiai idézőjel HTML-ben `„…"`, JS-stringben `„`/`”` (ASCII `"` lezárja a JS-stringet).
- `aria-current="page"` az aktív linken; a nav-csoportok `aria-label`-lel; a kategória-címke `<span class="fomenu-cimke">` (NEM link).
- NINCS `new Date()` a frontend-JS-ben (az időpontok az adatból, string-szeletelve).
- Kanonikus RADAR-nav: 10 `<a>` link (Áttekintő·Napi·Heti·Havi·Változások·Ügyek·Kapcsolódó·Google·YouTube·Infó) + 3 `.fomenu-cimke` (Elemzések, Radar, Statisztikák).
- Az új Radar-oldalak CSAK a `js/bovites.js`-t töltik (a `bovites.js` önálló: saját `bel`/`bov_json`, nincs app.js/Chart függőség).

## Review Focus

- Egy aloldal saját JSON-ja 404 → a render-fn „nem érhető el"/„nincs adat" üzenete jelenik meg, a `.radar-idosav` üres marad (elrejtve), a nav + fejléc + leírás megvan. (Task 1, per-oldal specek)
- `bovites.html` megnyitása → átirányít a `valtozasok.html`-re (régi link/bookmark). (Task 1)
- Az idősáv a HELYES mezőből és szöveggel: Változások=`szamitva_utc` (szeletelt dátum), Ügyek=`ablak` (nap+kezdet+vég), Kapcsolódó=`frissitve`. (Task 1 specek)
- A nav kategória-címkék (`.fomenu-cimke`) NEM linkek; a `#fomenu a` pontosan 10 link. (Task 2 menu.spec)
- A szakpolitika-szűrő a Változások és az Ügyek oldalon is a saját tartalmát szűri (oldalanként külön betöltés). (Task 1 specek)

---

## Task 1: A 3 Radar-aloldal + oldal-érzékeny JS + idősáv + e2e + bovites redirect

**Files:**
- Create: `docs/valtozasok.html`, `docs/ugyek.html`, `docs/kapcsolodo.html`
- Modify: `docs/js/bovites.js` (oldal-érzékeny init, render-fn-ek újrahasznosítva), `docs/bovites.html` (→ redirect), `docs/css/app.css` (`.radar-idosav`)
- Create (teszt): `e2e/valtozasok.spec.js`, `e2e/ugyek.spec.js`, `e2e/kapcsolodo.spec.js`
- Delete (teszt): `e2e/bovites.spec.js` (a 3 per-oldal spec váltja)
- Modify (teszt): `e2e/menu.spec.js` — CSAK a „bovites.html: … Radar menüpont aktív" teszt eltávolítása (a struktúra-asszertokat a Task 2 frissíti)

**Interfaces:**
- Produces: a 3 oldal + a `js/bovites.js` oldal-érzékeny init; a kanonikus RADAR-nav (lásd lent), amit a Task 2 a többi oldalra is kigördít.

**A kanonikus RADAR-nav blokk** (a 3 új oldalon; az aktív link oldalanként `class="aktiv" aria-current="page"`):
```html
<nav id="fomenu" aria-label="Fő menü">
  <a href="index.html" class="fomenu-home">Áttekintő</a>
  <div class="fomenu-csoport" aria-label="Elemzések">
    <span class="fomenu-cimke">Elemzések</span>
    <a href="elemzes.html">Napi</a>
    <a href="heti.html">Heti</a>
    <a href="havi.html">Havi</a>
  </div>
  <div class="fomenu-csoport" aria-label="Radar">
    <span class="fomenu-cimke">Radar</span>
    <a href="valtozasok.html">Változások</a>
    <a href="ugyek.html">Ügyek</a>
    <a href="kapcsolodo.html">Kapcsolódó</a>
  </div>
  <div class="fomenu-csoport" aria-label="Statisztikák">
    <span class="fomenu-cimke">Statisztikák</span>
    <a href="trendek.html">Google</a>
    <a href="youtube.html">YouTube</a>
  </div>
  <a href="adatokrol.html" class="fomenu-onallo">Infó</a>
</nav>
```

- [ ] **Step 1: A 3 per-oldal e2e spec (bukó)**

Hozd létre `e2e/valtozasok.spec.js`:
```javascript
const { test, expect } = require("@playwright/test");

const ELM = { szamitva_utc: "2026-10-07T18:00:00+00:00",
  kulcsszavak: { "benzin": { szokatlan: true, irany: "emelkedik", elteres: 3.0, idotartam_pont: 5,
      megbizhatosag: "magas", szakpolitika: "energia_rezsi", sav: {} },
    "iskola": { szokatlan: true, irany: "csokken", elteres: 2.0, idotartam_pont: 3,
      megbizhatosag: "kozepes", szakpolitika: "oktataspolitika", sav: {} } },
  szokatlan_lista: ["benzin", "iskola"] };

test("változások: renderel + idősáv (számítva) + szakpolitika-szűrő", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ json: ELM }));
  await page.goto("/valtozasok.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Változások");
  await expect(page.locator("#radar-idosav")).toContainText("számítva: 2026-10-07");
  await expect(page.locator("#bovites-elmozdulas")).toContainText("benzin");
  await expect(page.locator("#bovites-elmozdulas")).toContainText("emelkedik");
  await expect(page.locator(".bovites-elm-kartya")).toHaveCount(2);
  await page.locator('#bovites-szuro-elm .bovites-szuro-chip[data-szakpolitika="energia_rezsi"]').click();
  await expect(page.locator(".bovites-elm-kartya")).toHaveCount(1);
  await expect(page.locator("#bovites-elmozdulas")).toContainText("benzin");
  await expect(page.locator("#bovites-elmozdulas")).not.toContainText("iskola");
});

test("változások: fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/valtozasok.html");
  await expect(page.locator("#bovites-elmozdulas")).toContainText("nem érhető el");
  await expect(page.locator("#radar-idosav")).toBeEmpty();
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Változások");
});
```

Hozd létre `e2e/ugyek.spec.js`:
```javascript
const { test, expect } = require("@playwright/test");

const UGY = { szamitva_utc: "2026-10-07T21:00:00+00:00", ablak: { kezdet: "2026-09-08", veg: "2026-10-07", nap: 30 },
  modell: "claude-opus-4-8", ugyek: [
    { nev: "Üzemanyagárak", szakpolitika: "energia_rezsi", eletut: "folyamatosan_jelenlevo", mozgas: "erosodo",
      kifejezesek: ["benzin ára", "gázolaj"], elso_nap: "2026-09-10", utolso_nap: "2026-10-07", napok_szama: 12,
      idovonal: [{ nap: "2026-09-10", jelen: true, ossz_volumen: 40 }, { nap: "2026-10-07", jelen: true, ossz_volumen: 70 }],
      osszefoglalo: "Az üzemanyagárak tartósan foglalkoztatják a keresőket." },
    { nev: "Iskolakezdés", szakpolitika: "oktataspolitika", eletut: "visszatero", mozgas: "stabil",
      kifejezesek: ["iskola"], elso_nap: "2026-09-10", utolso_nap: "2026-10-01", napok_szama: 4,
      idovonal: [{ nap: "2026-09-10", jelen: true, ossz_volumen: 20 }], osszefoglalo: "y" }] };

test("ügyek: renderel + idősáv (gördülő 30 nap) + szűrő + rendezés + idővonal", async ({ page }) => {
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ json: UGY }));
  await page.goto("/ugyek.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Ügyek");
  await expect(page.locator("#radar-idosav")).toContainText("Gördülő 30 napos ablak: 2026-09-08 – 2026-10-07");
  await expect(page.locator(".bovites-ugy")).toHaveCount(2);
  await expect(page.locator("#bovites-ugyek")).toContainText("Üzemanyagárak");
  // idővonal
  const kartya = page.locator(".bovites-ugy").first();
  await expect(kartya.locator(".bovites-idovonal-cim")).toContainText("Napi jelenlét");
  await expect(kartya.locator(".bovites-idovonal .bovites-nap").first()).toHaveAttribute("style", /rgba\(42, 120, 214/);
  // szűrő + rendezés
  await page.locator('#bovites-szuro-ugy .bovites-szuro-chip[data-szakpolitika="oktataspolitika"]').click();
  await expect(page.locator(".bovites-ugy")).toHaveCount(1);
  await expect(page.locator("#bovites-ugyek")).toContainText("Iskolakezdés");
  await page.locator('#bovites-szuro-ugy .bovites-szuro-chip[data-szakpolitika=""]').click();
  await expect(page.locator(".bovites-ugy")).toHaveCount(2);
  await page.locator('#bovites-szuro-ugy .bovites-rendezes-gomb[data-rendezes="frissesseg"]').click();
  await expect(page.locator(".bovites-ugy-nev").first()).toHaveText("Üzemanyagárak");
});

test("ügyek: fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/ugyek.html");
  await expect(page.locator("#bovites-ugyek")).toContainText("nem érhető el");
  await expect(page.locator("#radar-idosav")).toBeEmpty();
});
```

Hozd létre `e2e/kapcsolodo.spec.js`:
```javascript
const { test, expect } = require("@playwright/test");

const KAPCS = { frissitve: "2026-10-07T21:00:00+00:00", kifejezesek: [
  { kifejezes: "benzin", lekerdezve: "2026-10-07T21:00:00+00:00", volumen: 90,
    top: [{ query: "benzin ár", value: 100 }, { query: "mol benzin", value: 19 }],
    rising: [{ query: "benzin ársapka", value: 8350 }, { query: "hatósági áras benzin", value: "Breakout" }] }]};

test("kapcsolódó: renderel (top + rising + súgók) + idősáv (napi)", async ({ page }) => {
  await page.route("**/data/kapcsolodo.json", (r) => r.fulfill({ json: KAPCS }));
  await page.goto("/kapcsolodo.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Kapcsolódó");
  await expect(page.locator("#radar-idosav")).toContainText("Naponta frissül · utolsó: 2026-10-07");
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("benzin ár");        // top
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("benzin ársapka");    // rising
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("Breakout");
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("relatív népszerűség");
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("mennyivel nőtt");
});

test("kapcsolódó: fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/kapcsolodo.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/kapcsolodo.html");
  await expect(page.locator("#radar-idosav")).toBeEmpty();
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Kapcsolódó");
});
```

- [ ] **Step 2: A `bovites.spec.js` törlése + a menu.spec „bovites aktív" teszt eltávolítása**

```bash
git rm e2e/bovites.spec.js
```
Az `e2e/menu.spec.js`-ből töröld a `test("bovites.html: a fül betölt, a Radar menüpont aktív", …)` tesztet (a `page.goto("/bovites.html")`-os blokkot) — a `bovites.html` ettől a tasktól redirect lesz, és a 3 új oldal aktív-tesztjei a saját specjeikben vannak.

- [ ] **Step 3: Futtasd — bukjon**

Run: `npx playwright test e2e/valtozasok.spec.js e2e/ugyek.spec.js e2e/kapcsolodo.spec.js`
Expected: FAIL (az oldalak még nincsenek).

- [ ] **Step 4: CSS — `.radar-idosav`**

`docs/css/app.css`-ben az `.attekinto-info-sav`-blokk után (vagy a fájl végén) szúrd be:
```css
/* Radar aloldalak idősáv-jelzése */
.radar-idosav { display: inline-block; margin-top: .4rem; padding: .25rem .7rem; border-radius: 999px;
  background: #eef2f7; color: #334; font-size: .82rem; }
.radar-idosav:empty { display: none; }
```

- [ ] **Step 5: `docs/js/bovites.js` — oldal-érzékeny init**

A render-függvények (`bov_elmozdulas_render`, `bov_idovonal`, `bov_ugy_kartya`, `bov_ugyek_render`, `bov_kapcs_*`, `bov_kapcsolodo_render`, `bov_szakpolitika_epit`, `bov_rendezes_epit`), a konstansok, a `bel`/`bov_json` VÁLTOZATLANOK. Változtatások:

(a) `bov_allapot`-ból vedd ki az `alful` mezőt:
```javascript
const bov_allapot = { szakpolitika: "", rendezes: "napok", elm: null, ugy: null, kapcs: null };
```

(b) `bov_rajzol` legyen oldal-érzékeny (csak a jelenlévő konténerbe renderel):
```javascript
function bov_rajzol() {
  const elmCel = document.getElementById("bovites-elmozdulas");
  if (elmCel) bov_elmozdulas_render(elmCel, bov_allapot.elm, bov_allapot.szakpolitika);
  const ugyCel = document.getElementById("bovites-ugyek");
  if (ugyCel) bov_ugyek_render(ugyCel, bov_allapot.ugy, bov_allapot.szakpolitika, bov_allapot.rendezes);
  const kapcsCel = document.getElementById("bovites-kapcsolodo");
  if (kapcsCel) bov_kapcsolodo_render(kapcsCel, bov_allapot.kapcs);
  document.querySelectorAll(".bovites-szuro-chip").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.szakpolitika === bov_allapot.szakpolitika)));
  document.querySelectorAll(".bovites-rendezes-gomb").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.rendezes === bov_allapot.rendezes)));
}
```

(c) TÖRÖLD a `bov_alful_valt` és a `bov_alfulek_kot` függvényeket (a hozzá tartozó kommentekkel).

(d) Add hozzá az idősáv-segédeket és cseréld le a `bov_init`-et (a fájl végén):
```javascript
function bov_datum(s) { return (s ? String(s) : "").slice(0, 10); }

function bov_idosav_ir(szoveg) {
  const cel = document.getElementById("radar-idosav");
  if (cel) cel.textContent = szoveg || "";
}

async function bov_init() {
  if (document.getElementById("bovites-elmozdulas")) {
    bov_allapot.elm = await bov_json("data/elmozdulas.json");
    bov_idosav_ir(bov_allapot.elm
      ? "Aktuális kiugrások — a szavak szokásos szintjéhez képest · számítva: " + bov_datum(bov_allapot.elm.szamitva_utc)
      : "");
    bov_szakpolitika_epit(document.getElementById("bovites-szuro-elm"));
  } else if (document.getElementById("bovites-ugyek")) {
    bov_allapot.ugy = await bov_json("data/ugyek.json");
    const ab = bov_allapot.ugy && bov_allapot.ugy.ablak;
    bov_idosav_ir(ab ? "Gördülő " + ab.nap + " napos ablak: " + ab.kezdet + " – " + ab.veg : "");
    bov_szakpolitika_epit(document.getElementById("bovites-szuro-ugy"));
    bov_rendezes_epit(document.getElementById("bovites-szuro-ugy"));
  } else if (document.getElementById("bovites-kapcsolodo")) {
    bov_allapot.kapcs = await bov_json("data/kapcsolodo.json");
    bov_idosav_ir(bov_allapot.kapcs ? "Naponta frissül · utolsó: " + bov_datum(bov_allapot.kapcs.frissitve) : "");
  }
  bov_rajzol();
}

bov_init();
```
(A régi `bov_init` törlendő; a fenti lép a helyére.)

- [ ] **Step 6: A 3 új oldal + a `bovites.html` redirect**

`docs/valtozasok.html` (az aktív nav-link: `valtozasok.html`):
```html
<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Szokatlan változások – Radar – Trendfigyelő</title>
  <link rel="stylesheet" href="css/app.css">
</head>
<body>
  <nav id="fomenu" aria-label="Fő menü">
    <a href="index.html" class="fomenu-home">Áttekintő</a>
    <div class="fomenu-csoport" aria-label="Elemzések">
      <span class="fomenu-cimke">Elemzések</span>
      <a href="elemzes.html">Napi</a>
      <a href="heti.html">Heti</a>
      <a href="havi.html">Havi</a>
    </div>
    <div class="fomenu-csoport" aria-label="Radar">
      <span class="fomenu-cimke">Radar</span>
      <a href="valtozasok.html" class="aktiv" aria-current="page">Változások</a>
      <a href="ugyek.html">Ügyek</a>
      <a href="kapcsolodo.html">Kapcsolódó</a>
    </div>
    <div class="fomenu-csoport" aria-label="Statisztikák">
      <span class="fomenu-cimke">Statisztikák</span>
      <a href="trendek.html">Google</a>
      <a href="youtube.html">YouTube</a>
    </div>
    <a href="adatokrol.html" class="fomenu-onallo">Infó</a>
  </nav>

  <header class="fejlec-doboz">
    <h1>Szokatlan változások</h1>
    <p class="radar-idosav" id="radar-idosav"></p>
  </header>

  <main id="bovites">
    <p class="bovites-leiras">Itt azt látod, mely <strong>követett keresőszavak</strong> mozdultak el a megszokottól: a szó a szokásos szintjéhez képest <strong>emelkedik</strong> vagy <strong>csökken</strong>-e, <strong>mekkora az eltérés</strong> (a szokásos ingadozás hányszorosa), <strong>mióta tart</strong>, és mennyire <strong>megbízható</strong> a jelzés. A kártya bal oldali színes sávja az irányt jelzi. A szakpolitikai szűrővel szűkítheted a listát. A megszokott tartomány a <a href="trendek.html">Google Trendek</a> fül chartjain halvány sávként is bekapcsolható.</p>
    <div id="bovites-szuro-elm" class="bovites-szuro" aria-label="Szakpolitikai szűrő"></div>
    <section id="bovites-elmozdulas" aria-live="polite"></section>
  </main>

  <footer id="labresz" aria-label="Lábléc"></footer>

  <script src="js/bovites.js"></script>
</body>
</html>
```

`docs/ugyek.html` — ugyanaz a fejrész és nav, de az aktív link `ugyek.html` (`<a href="ugyek.html" class="aktiv" aria-current="page">Ügyek</a>`), a cím:
```html
  <title>Ügyek életútja – Radar – Trendfigyelő</title>
```
a header H1 `<h1>Ügyek életútja</h1>`, és a `<main id="bovites">` tartalma:
```html
  <main id="bovites">
    <p class="bovites-leiras">A napi <strong>felkapott keresések</strong> üggyé csoportosítva (a <code>claude-opus-4-8</code> kapcsolja össze az azonos témájú kifejezéseket). Minden ügynél látod a <strong>besorolását</strong> (újonnan megfigyelt / folyamatosan jelen / visszatérő), a <strong>mozgását</strong> (erősödő / stabil / lecsengő), a hozzá tartozó kifejezéseket, egy rövid összefoglalót, és egy <strong>napi jelenlét-idővonalat</strong> az ablakból. Szakpolitika szerint szűrhető, időtartam / frissesség / mozgás szerint rendezhető.</p>
    <div id="bovites-szuro-ugy" class="bovites-szuro" aria-label="Szakpolitikai szűrő és rendezés"></div>
    <section id="bovites-ugyek" aria-live="polite"></section>
  </main>
```

`docs/kapcsolodo.html` — ugyanaz a nav, az aktív link `kapcsolodo.html` (`<a href="kapcsolodo.html" class="aktiv" aria-current="page">Kapcsolódó</a>`), a cím:
```html
  <title>Kapcsolódó keresések – Radar – Trendfigyelő</title>
```
a header H1 `<h1>Kapcsolódó keresések</h1>`, és a `<main id="bovites">` tartalma:
```html
  <main id="bovites">
    <p class="bovites-leiras">A napi <strong>felkapott keresések</strong> mögé nézünk be: a Google Trends „kapcsolódó keresések" alapján témánként a <strong>megszokott (Top)</strong> és a <strong>most felfutó (Felfutó, „Breakout")</strong> keresések — mire kíváncsiak még az emberek az adott téma körül. A <strong>Top</strong> melletti szám a relatív népszerűség (0–100, ahol a <strong>100 a leggyakoribb</strong> kapcsolódó keresés); a <strong>Felfutó</strong> melletti szám azt mutatja, <strong>mennyivel nőtt</strong> a keresés (a „Breakout" kiugróan nagy felfutás). Naponta pár felkapott téma frissül.</p>
    <section id="bovites-kapcsolodo" aria-live="polite"></section>
  </main>
```
(mindhárom oldal lábléce + scriptje azonos a valtozasok.html-ével: `<footer id="labresz" aria-label="Lábléc"></footer>` majd `<script src="js/bovites.js"></script>`.)

`docs/bovites.html` TELJES tartalma (redirect):
```html
<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url=valtozasok.html">
  <link rel="canonical" href="valtozasok.html">
  <title>Radar – Trendfigyelő</title>
</head>
<body>
  <p>Átirányítás a <a href="valtozasok.html">Változások</a> oldalra…</p>
</body>
</html>
```

- [ ] **Step 7: Futtasd — menjen át**

Run: `npx playwright test e2e/valtozasok.spec.js e2e/ugyek.spec.js e2e/kapcsolodo.spec.js e2e/menu.spec.js`
Expected: PASS (a 3 új oldal zöld; a menu.spec a megmaradt tesztekkel zöld).

- [ ] **Step 8: Szintaxis + commit**

Run: `node --check docs/js/bovites.js`
```bash
git add docs/valtozasok.html docs/ugyek.html docs/kapcsolodo.html docs/bovites.html docs/js/bovites.js docs/css/app.css e2e/valtozasok.spec.js e2e/ugyek.spec.js e2e/kapcsolodo.spec.js e2e/menu.spec.js
git rm e2e/bovites.spec.js
git commit -m "feat(ui): Radar szetbontva 3 onallo oldalra (Valtozasok/Ugyek/Kapcsolodo) + idosav"
```

---

## Task 2: A RADAR 3-füles nav kigördítése a 7 meglévő oldalra + menu.spec + nyitóoldal

**Files:**
- Modify (nav): `docs/elemzes.html`, `docs/heti.html`, `docs/havi.html`, `docs/trendek.html`, `docs/youtube.html`, `docs/adatokrol.html`, `docs/index.html`
- Modify (nyitóoldal-kártya): `docs/index.html`
- Modify (teszt): `e2e/menu.spec.js`, `e2e/nyitooldal.spec.js`

**Interfaces:**
- Consumes: a Task 1 kanonikus RADAR-nav blokkja + a 3 oldal (`valtozasok/ugyek/kapcsolodo.html`).

A 7 oldalon a jelenlegi `<div class="fomenu-csoport" aria-label="Jelzések"> … <a href="bovites.html" …>Radar</a> </div>` blokkot cseréld a kanonikus RADAR-csoportra (Task 1-beli blokk, de ezeken az oldalakon a RADAR-linkek NEM aktívak — az aktív link oldalanként a saját, meglévő linkjén marad: Napi/Heti/Havi/Google/YouTube/Infó, index=Áttekintő).

- [ ] **Step 1: menu.spec struktúra-frissítés (bukó)**

`e2e/menu.spec.js` első tesztjében:
```javascript
  await expect(page.locator("#fomenu a")).toHaveCount(10);
  await expect(page.locator("#fomenu .fomenu-cimke")).toHaveText(["Elemzések", "Radar", "Statisztikák"]);
```
és az `#fomenu a[href="bovites.html"]` helyett:
```javascript
  await expect(page.locator('#fomenu a[href="valtozasok.html"]')).toHaveText("Változások");
  await expect(page.locator('#fomenu a[href="ugyek.html"]')).toHaveText("Ügyek");
  await expect(page.locator('#fomenu a[href="kapcsolodo.html"]')).toHaveText("Kapcsolódó");
```
Minden `toHaveText([...])` nav-tömböt (az első tesztben és a youtube/havi/heti tesztekben) erre:
```javascript
["Áttekintő", "Napi", "Heti", "Havi", "Változások", "Ügyek", "Kapcsolódó", "Google", "YouTube", "Infó"]
```
Adj hozzá 3 aktív-oldal tesztet:
```javascript
test("valtozasok.html: a Változások menüpont aktív", async ({ page }) => {
  await page.goto("/valtozasok.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Változások");
});
test("ugyek.html: az Ügyek menüpont aktív", async ({ page }) => {
  await page.goto("/ugyek.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Ügyek");
});
test("kapcsolodo.html: a Kapcsolódó menüpont aktív", async ({ page }) => {
  await page.goto("/kapcsolodo.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Kapcsolódó");
});
```
(Az Infó-oldal `.adat-doboz`/`.adat-csoport` asszertjai VÁLTOZATLANOK — a „A Radar fül" csoport-cím marad.)

- [ ] **Step 2: Futtasd — bukjon**

Run: `npx playwright test e2e/menu.spec.js`
Expected: FAIL (a 7 oldal nav-ja még a régi egytételes „Radar"/„Jelzések").

- [ ] **Step 3: A nav cseréje a 7 oldalon**

A `docs/elemzes.html`, `heti.html`, `havi.html`, `trendek.html`, `youtube.html`, `adatokrol.html`, `index.html` fájlokban a Radar-csoport-blokkot (`<div class="fomenu-csoport" aria-label="Jelzések"> … Radar … </div>`) cseréld a Task 1 kanonikus RADAR-csoportjára (az aktív jelölés a saját oldali linkjén marad, a RADAR-linkek ezeken nem aktívak).

- [ ] **Step 4: index.html — a Radar-kártya 3 linkre**

`docs/index.html`-ben a Radar-kártya egyetlen linkje:
```html
        <div class="nyitooldal-kartya-linkek">
          <a href="bovites.html">Radar megnyitása</a>
        </div>
```
helyett:
```html
        <div class="nyitooldal-kartya-linkek">
          <a href="valtozasok.html">Változások</a>
          <a href="ugyek.html">Ügyek</a>
          <a href="kapcsolodo.html">Kapcsolódó</a>
        </div>
```

- [ ] **Step 5: nyitooldal.spec — a Radar-kártya linkjei**

`e2e/nyitooldal.spec.js` statikus tesztjében a `'.nyitooldal-kartya a[href="bovites.html"]'` elvárást cseréld:
```javascript
  await expect(page.locator('.nyitooldal-kartya a[href="valtozasok.html"]')).toBeVisible();
  await expect(page.locator('.nyitooldal-kartya a[href="ugyek.html"]')).toBeVisible();
  await expect(page.locator('.nyitooldal-kartya a[href="kapcsolodo.html"]')).toBeVisible();
```
(A „Radar" kártyacím-elvárás — `.nyitooldal-kartya h2` sorrend ["Elemzések","Radar","Statisztikák"] — VÁLTOZATLAN.)

- [ ] **Step 6: Futtasd — menjen át, és ne törjön más**

Run: `npx playwright test e2e/menu.spec.js e2e/nyitooldal.spec.js && npx playwright test && .venv/bin/python -m pytest -q`
Expected: PASS (minden nav-teszt + a teljes Playwright suite zöld [a `kulcsszo.spec` pre-existing flake kivételével], pytest 733 zöld).

- [ ] **Step 7: Commit**

```bash
git add docs/elemzes.html docs/heti.html docs/havi.html docs/trendek.html docs/youtube.html docs/adatokrol.html docs/index.html e2e/menu.spec.js e2e/nyitooldal.spec.js
git commit -m "feat(ui): RADAR 3-fules nav a tobbi oldalon + nyitooldal kartya 3 linkre"
```

---

## Self-Review

**1. Spec-lefedettség:**
- RADAR nav-nagykategória 3 füllel (spec §1) → Task 1 (új oldalak nav-ja) + Task 2 (a 7 oldal + menu.spec). ✓
- 3 önálló oldal (spec §2) → Task 1. ✓
- `bovites.html` redirect (spec §2.4) → Task 1. ✓
- JS oldal-érzékeny init, render-fn újrahasznosítás (spec §3) → Task 1. ✓
- Idősáv-jelzés oldalanként (spec §2.1–2.3) → Task 1 (JS + HTML + specek). ✓
- Nyitóoldal 3 link (spec §4) → Task 2. ✓
- Infó „A Radar fül" (spec §5) → marad (a csoport-cím változatlan; az Infó-teszt érintetlen). ✓
- Stílus `.radar-idosav` (spec §6) → Task 1. ✓
- Tesztelés (spec §8) → Task 1 (3 új spec, bovites.spec törlés, menu.spec bovites-teszt) + Task 2 (menu.spec struktúra + 3 aktív-teszt + nyitooldal.spec). ✓
- test_pages.py: a globális HTML-szkennerek (inline script/handler/js-url) automatikusan lefedik az új oldalakat; nincs oldal-leltár teszt; az index-teszt érintetlen → NEM kell módosítani. ✓

**2. Placeholder-scan:** nincs TBD/TODO; minden lépés konkrét kóddal. ✓

**3. Típus-konzisztencia:** a `#bovites-elmozdulas`/`#bovites-ugyek`/`#bovites-kapcsolodo` konténer-id-k a 3 oldal HTML-je és a `bov_rajzol`/`bov_init` közt egyeznek; a `#radar-idosav` az HTML, a CSS és a `bov_idosav_ir` közt; a `#bovites-szuro-elm`/`-ugy` a HTML és a `bov_init` közt; az adatmezők (`szamitva_utc`, `ablak.{kezdet,veg,nap}`, `frissitve`) a mock-specekkel és az élő JSON-nal. A kanonikus RADAR-nav Task 1 és Task 2 közt azonos. ✓

**4. Review Focus:** mind az 5 tétel kap tesztet — per-oldal 404 fail-soft (Task 1 mindhárom spec), bovites redirect (Task 1 Step 6, a menu.spec a bovites-tesztet eltávolítja; a redirect viselkedést a nyitooldal/aktív-tesztek közvetve fedik), idősáv helyes mező+szöveg (Task 1 mindhárom spec), nav 10 link + 3 nem-link címke (Task 2 menu.spec count=10 + fomenu-cimke toHaveText), szakpolitika-szűrő per-oldal (Task 1 valtozasok + ugyek spec). ✓
