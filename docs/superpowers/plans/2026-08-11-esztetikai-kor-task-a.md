# Esztétikai kör (Category A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vizuálisan elkülöníteni a kártyákat/blokkokat, olvashatóbbá tenni az intervallum-gombokat (letiltott állapot is), és a trend-blokk látható címét megkülönböztetni a Kulcsszavak-tól — a Task 10 rootMargin-hangolása ELŐTT.

**Architecture:** Tisztán `docs/css/app.css` + `docs/index.html` (egy cím) módosítás, két új Playwright-őrrel. Nincs Python, nincs adat-commit. A geometriai delták már MÉRVE (spec §1.4): a kártya-magasság 0px-szel nő, a +77px column-eltolás tisztán offszet → a Task 10 bemenete.

**Tech Stack:** CSS3 (saját, külső `@import`/`url()` TILOS — Task 1 CSS-guard), Playwright (`@playwright/test`), HTML.

## Global Constraints

- **SOROS a mérvadó:** minden futás `--workers=1`. A kör VÉGÉN várt: **pytest 237** (Python érintetlen), **Playwright 62** (60 + T27 + (b2)).
- **Mutáció-kapu:** a kör végén `grep -rn "MUTÁCIÓ" docs/js docs/css e2e tests trendfigyelo` == **PONTOSAN 1** (kulcsszo.spec.js:487, régi). Az új tesztek RED→GREEN ciklusa a nem-vakság bizonyítéka; külön MUTÁCIÓ-komment NEM marad.
- **Nincs adat-commit** — tisztán kód/CSS/HTML. `git add` NÉVVEL (nem -A/.).
- **Nyelv:** minden kód+komment MAGYARUL.
- **KIFEJEZETTEN JÓVÁHAGYOTT, NEM változtatható:** (1) a kategória-pill (`.kategoria-gomb` border-radius:999px) érintetlen; (2) az intervallum-gomb SZÖGLETES marad (nem pill); (3) az „Other"-szürke (`.kategoria-gomb--other`) szándékos, marad; (4) az `aria-label` és a `h2` EGYÜTT cserélődik.
- **TDD-előrejelzés:** stub-RED előtt a hiba NÉVRE és TÍPUSRA jósolt, és VISELKEDÉSBELI (assert-eltérés), NEM Import/Attribute/timeout.

---

## Task 1: A1 — kártya- és blokk-elkülönítés (CSS)

**Files:**
- Modify: `docs/css/app.css` (kártya-keret+árnyék: 47, 75; `.szekcio + .szekcio` új; `.vezerlo-sav`: 15)
- Verify (nem módosít): `e2e/layout.spec.js` (ST1 szerkezet, ST2 `position:sticky`)

**Interfaces:**
- Consumes: — (önálló CSS)
- Produces: a `.vezerlo-sav` `box-sizing:border-box`-ot kap (a Task 2/3 gombjai ezen a sávon belül maradnak; a rootMargin-geometria a Task 10 bemenete, spec §1.4).

**Megjegyzés a teszt-hiányról (naming-discipline):** az A1 tisztán VIZUÁLIS (keret-szín, árnyék, padding). DOM-ból értelmesen nem assertálható (L9-korlát) → nincs ÚJ teszt; a regressziós őr az, hogy az EGY
`.szekcio`/`.vezerlo-sav` szerkezetet és a `sticky` pozíciót őrző `layout.spec.js` (ST1/ST2) ZÖLD marad, és a §1.4 mért geometria bizonyítja, hogy a kártya-magasság nem nő. NE koholj vizuális tesztet.

- [ ] **Step 1: Kártya-keret + árnyék — `.kulcsszo-chart` (app.css:47)**

Csere:
```css
#kulcsszo-blokk .kulcsszo-chart { border: 1px solid #d0d0d0; border-radius: 4px; padding: .5rem;
  box-shadow: 0 1px 2px rgba(0,0,0,.06); }
```

- [ ] **Step 2: Kártya-keret + árnyék — `.trend-kartya` (app.css:75)**

Csere:
```css
#trend-blokk .trend-kartya { border: 1px solid #d0d0d0; border-radius: 4px; padding: .6rem;
  box-shadow: 0 1px 2px rgba(0,0,0,.06); }
```

- [ ] **Step 3: Szekció-elválasztó — új szabály a `.szekcio` (app.css:14) UTÁN**

Beszúrás közvetlenül a `.szekcio { ... }` sor után:
```css
/* A1: a két nagy blokk vizuális elválasztása (a margó önmagában nem látszott) */
.szekcio + .szekcio { border-top: 1px solid #e3e3e3; padding-top: 1.5rem; }
```

- [ ] **Step 4: Vezérlősáv mint „sín" — `.vezerlo-sav` (app.css:15)**

Csere (a `box-sizing: border-box` KÖTELEZŐ — enélkül a padding KIFELÉ nő, a sáv 14rem→15,6rem, a desktop kártya −13px-t veszít; border-box-szal a kártya-szélesség delta 0px, spec §1.3):
```css
.vezerlo-sav { flex: 0 0 14rem; position: sticky; top: 1rem; align-self: flex-start;
  background: #fafafa; border: 1px solid #e3e3e3; border-radius: 6px; padding: .75rem; box-sizing: border-box; }
```

- [ ] **Step 5: layout.spec.js ST1/ST2 ZÖLD marad (a box-sizing viselkedés-változás, de sem szerkezetet, sem `position`-t nem érint)**

Run: `npx playwright test e2e/layout.spec.js --workers=1 --reporter=line`
Expected: **2 passed** (ST1 szerkezet + ST2 `position:sticky` — a `box-sizing` egyiket sem befolyásolja).

- [ ] **Step 6: Teljes Playwright SOROS — nincs regresszió**

Run: `npx playwright test --workers=1 --reporter=line`
Expected: **60 passed** (a §1.4 mérés szerint a kártya-magasság nem nő → semmi nem törik).

- [ ] **Step 7: Kézi vizuális szemle (L9)**

A `docs`-ot HTTP-n kiszolgálva (`.venv/bin/python -m http.server 8000 --directory docs`) nézd meg: a kártyák láthatóan elválnak (keret #d0d0d0 + finom árnyék), a bal vezérlősáv külön „sín"-ként olvasódik (halvány háttér+keret), a két nagy blokk közt vékony elválasztó. A magasság-invarianciát a §1.4 mérés adja, nem szemre.

- [ ] **Step 8: Commit**

```bash
git add docs/css/app.css
git commit -m "$(cat <<'EOF'
feat(phase3): A1 — kártya/szekció vizuális elkülönítés (esztétikai kör)

Kártya-keret #eee→#d0d0d0 + finom box-shadow; .szekcio+.szekcio elválasztó;
.vezerlo-sav halvány „sín" (háttér+keret+padding) box-sizing:border-box-szal
(a sáv 14rem marad, kártya-szélesség delta 0px). A kártya-magasság 0px-szel
nő (mérve, spec §1.4); layout.spec.js ST1/ST2 zöld.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01WJBGrwZ6giKnbZwnHYaTLz
EOF
)"
```

---

## Task 2: A2 — intervallum-gombok (kevésbé szürkék + letiltott olvashatóság)

**Files:**
- Modify: `docs/css/app.css` (intervallum-gomb alap: 33; letiltott: 35)
- Test: `e2e/vezerlok.spec.js` (új `(b2)` a `(b)` UTÁN, ~61. sor)

**Interfaces:**
- Consumes: a `(b)` fixture-mintája (`mock_regresszio` + mind az 5 `ervenyes:false` → 5 letiltott gomb).
- Produces: — (önálló CSS + őr)

**A11y-indoklás (a specből, hogy a Task 10 a11y-köre ne nyissa újra „szabálysértésként"):** a letiltott vezérlő a WCAG 1.4.3 alól KIVÉTEL → NEM szabálysértés. DE a letiltott intervallum-gomb JELENTÉST hordoz („ez a táv még nem elérhető"), ezért OLVASHATÓNAK kell lennie. #999 fehéren = 2,85:1; új: #6b6b6b a #f0f0f0 háttéren ≈ 5:1.

- [ ] **Step 1: Írd meg a bukó tesztet — `(b2)` a `vezerlok.spec.js`-ben, a `(b)` teszt (61. sor) UTÁN**

**FONTOS: ez ÚJ `test(...)` blokk (+1 a suite-számhoz: 60→61), NEM a `(b)` bővítése egy asserttel. A `vezerlok.spec.js` nem használ `Tn`-számozást és NINCS fejléc-darabszáma → a név `(b2)`, nincs ütköző szám.**

```js
test("(b2) a letiltott intervallum-gomb OLVASHATÓ marad (a11y: jelentést hordoz — »ez a táv nem elérhető«)", async ({ page }) => {
  // Ugyanaz a fixture, mint (b): mind az 5 intervallum ervenyes:false → letiltott gombok.
  // A letiltott vezérlő WCAG 1.4.3 alól KIVÉTEL (nem szabálysértés), DE jelentést hordoz → olvashatónak kell lennie.
  // Ez az őr a #999 (2,85:1) → #6b6b6b (~5:1) váltást rögzíti. Diszkriminátor: #999-re visszaállítva ez a teszt bukik.
  await mock_regresszio(page, {
    "1_het": { ervenyes: false, ok: "nincs_adat" }, "2_het": NL, "1_ho": NL, "3_ho": NL, "1_ev": NL,
  });
  await page.goto("/");
  const gomb = page.locator("#intervallum-vezerlo button[disabled]").first();
  await expect(gomb).toBeVisible();
  const szin = await gomb.evaluate(function (el) { return getComputedStyle(el).color; });
  expect(szin).toBe("rgb(107, 107, 107)");
});
```

- [ ] **Step 2: Futtasd — VISELKEDÉSBELI RED (nem timeout)**

Run: `npx playwright test e2e/vezerlok.spec.js -g "b2" --workers=1 --reporter=line`
Expected: **FAIL** — a gomb LÁTHATÓ (nincs timeout), de a computed color a mai `#999` → `rgb(153, 153, 153)`, az assert `Expected "rgb(107, 107, 107)" Received "rgb(153, 153, 153)"`.

- [ ] **Step 3: Intervallum-gomb ALAP explicit stílusa (app.css:33) — szögletes marad**

Csere (fehér háttér + #ccc keret + radius 4px → SZÖGLETES, NEM pill; ez a „szándékos, nem natív szürke"):
```css
#intervallum-vezerlo button { padding: .3rem .7rem; cursor: pointer;
  background: #fff; border: 1px solid #ccc; border-radius: 4px; color: #222; }
```

- [ ] **Step 4: Letiltott gomb — olvasható + egyértelműen inaktív (app.css:35)**

Csere:
```css
#intervallum-vezerlo button[disabled] { cursor: not-allowed; color: #6b6b6b; background: #f0f0f0; }
```

- [ ] **Step 5: Futtasd a `(b2)`-t — GREEN**

Run: `npx playwright test e2e/vezerlok.spec.js -g "b2" --workers=1 --reporter=line`
Expected: **PASS** (`rgb(107, 107, 107)`).

- [ ] **Step 6: Teljes `vezerlok.spec.js` + teljes Playwright SOROS**

Run: `npx playwright test e2e/vezerlok.spec.js --workers=1 --reporter=line` majd `npx playwright test --workers=1 --reporter=line`
Expected: `vezerlok.spec.js` zöld (aria-pressed/disabled szerkezeti tesztek nem törnek a restyle-tól); teljes suite **61 passed**.

- [ ] **Step 7: Commit**

```bash
git add docs/css/app.css e2e/vezerlok.spec.js
git commit -m "$(cat <<'EOF'
feat(phase3): A2 — intervallum-gombok explicit stílusa + letiltott olvashatóság

Natív szürke gomb → fehér/#ccc-keret/radius4 (SZÖGLETES marad, a pill a
kategória-gomboké). Letiltott #999 (2,85:1) → #6b6b6b a #f0f0f0 háttéren
(~5:1): olvasható ÉS egyértelműen inaktív. Indok: a letiltott gomb jelentést
hordoz („ez a táv nem elérhető"); a WCAG 1.4.3 KIVESZI (nem szabálysértés),
a javítás használhatósági. Új őr (b2) valódi diszkriminátorral (#999→bukik).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01WJBGrwZ6giKnbZwnHYaTLz
EOF
)"
```

---

## Task 3: A3 — látható trend-cím csere + regressziós őr (T27)

**Files:**
- Modify: `docs/index.html` (33: `aria-label`, 34: `<h2>`)
- Test: `e2e/trend.spec.js` (új T27 a T26 UTÁN; fejléc-szám 3. sor: 22→27)

**Interfaces:**
- Consumes: a meglévő `mock()` helper + `MAI16` fixture (trend.spec.js).
- Produces: — (végállapot)

- [ ] **Step 1: Írd meg a bukó tesztet — T27 a `trend.spec.js`-ben, a T26 teszt UTÁN (~460. sor)**

```js
// ── T27 — A3: a látható trend-cím »Ma felkapott keresések« (megkülönböztetés a »Kulcsszavak«-tól; DOM-szerződés-őr) ──
test("27. a trend-blokk h2 szövege »Ma felkapott keresések« (nem »Napi legfrissebb trendek«)", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  await expect(page.locator(`${T} h2`)).toHaveText("Ma felkapott keresések");
});
```

- [ ] **Step 2: Futtasd — VISELKEDÉSBELI RED (nem timeout)**

Run: `npx playwright test e2e/trend.spec.js -g "27\." --workers=1 --reporter=line`
Expected: **FAIL** — a `h2` LÉTEZIK (nincs timeout), de a szövege a mai `Napi legfrissebb trendek`: `Expected "Ma felkapott keresések" Received "Napi legfrissebb trendek"`.

- [ ] **Step 3: Cím csere — `docs/index.html` 33+34 (h2 ÉS aria-label EGYÜTT)**

`docs/index.html:33`:
```html
      <section id="trend-blokk" aria-label="Ma felkapott keresések">
```
`docs/index.html:34`:
```html
        <h2>Ma felkapott keresések</h2>
```

- [ ] **Step 4: Fejléc-szám JAVÍTÁSA — `trend.spec.js:3` (22→27, a 22→26 drift is korrigálva)**

**ELŐBB VERIFIKÁLD a tényleges számot (a 22→26 drift épp abból jött, hogy a fejléc nem követte a valóságot — NE csak írd át a számot):**

Run: `grep -c '^\s*test(' e2e/trend.spec.js`
Expected: **27** (26 meglévő T1–T26 + az új T27). CSAK ezt az egyező számot írd a fejlécbe:
```js
// Trend-blokk smoke-ok (27 db; Task 7 + 8a + 8b + A3-cím) — MOCKOLT legfrissebb.json + napok/index.json + napok/<nap>.json.
```
Ha a grep NEM 27-et ad → STOP (nem a fejlécet igazítod a valósághoz, hanem megkeresed, miért nem 27 a valós szám).

- [ ] **Step 5: Futtasd a T27-et — GREEN**

Run: `npx playwright test e2e/trend.spec.js -g "27\." --workers=1 --reporter=line`
Expected: **PASS**.

- [ ] **Step 6: Teljes `trend.spec.js` SOROS — 27 teszt zöld**

Run: `npx playwright test e2e/trend.spec.js --workers=1 --reporter=line`
Expected: **27 passed** (a fejléc-szám mostantól egyezik a valósággal).

- [ ] **Step 7: Commit**

```bash
git add docs/index.html e2e/trend.spec.js
git commit -m "$(cat <<'EOF'
feat(phase3): A3 — látható trend-cím »Ma felkapott keresések« + őr (T27)

A »Napi legfrissebb trendek« → »Ma felkapott keresések« (h2 ÉS aria-label
együtt; belső id érintetlen), hogy ne olvadjon a »Kulcsszavak«-ba. Grep:
a szöveg csak az index.html-ben élt, e2e/tests sehol → DOM-szerződés nem törik.
Új őr T27 a trend.spec.js-ben; fejléc-szám 22→27 (a meglévő 22→26 drift is javítva).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01WJBGrwZ6giKnbZwnHYaTLz
EOF
)"
```

---

## A kör lezárása (a Task 3 után)

- [ ] **Mutáció-kapu:** `grep -rn "MUTÁCIÓ" docs/js docs/css e2e tests trendfigyelo` → várt **PONTOSAN 1** (kulcsszo.spec.js:487).
- [ ] **Teljes SOROS suite:** `pytest -q` (várt **237**, `--workers=1` a pytest-konfig szerint) + `npx playwright test --workers=1 --reporter=line` (várt **62**).
- [ ] **git status:** csak a szándékolt kód/CSS/HTML változott; NINCS adatfájl-módosítás (`docs/data/*`), NINCS `.atadas-archiv/`-ba nyúlás.
- [ ] **Whole-round review** (subagent-driven-development zárása): spec-lefedettség (A1/A2/A3 mind), a jóváhagyott-fagyasztott lista betartva (pill, szögletes intervallum-gomb, Other-szürke, aria+h2 együtt).
- [ ] **PUSH — KÜLÖN, user-jóváhagyással** (nem a terv része automatikusan): `git fetch` → `git log HEAD..origin/main` → ha nem üres: `pull --rebase` + suite ÚJRA, csak zöld után push; `rev-list --left-right origin/main...HEAD` == `0 0`.
- [ ] **Következő:** Task 10 — a rootMargin-hangolás a MÉRT +77px column-eltolással (spec §1.4), az OFFSZETEN, NEM a kártya-magasságon.

## Self-review (a terv a spec ellen)

- **Spec-lefedettség:** A1 §1.2/§1.3 → Task 1 (border-box KÖTELEZŐ Step 4). A2 §2.2/§2.3 → Task 2 (+a11y-indoklás a commit-üzenetben). A3 §3.2/§3.3 → Task 3 (h2+aria együtt, T27, fejléc 22→27). §4 fagyasztott lista → Global Constraints. §5 tesztelés → Task 1 (nincs vizuális koholt teszt), Task 2 ((b2) diszkriminátor), Task 3 (T27). §1.4 mért geometria → a Task 10-nek átadva a lezárásban. ✓ nincs fedetlen követelmény.
- **Placeholder-szken:** nincs TBD/TODO; minden CSS/JS blokk konkrét. ✓
- **Típus-konzisztencia:** a computed-color assert `rgb(107, 107, 107)` == #6b6b6b (Step 4 háttér #f0f0f0); a T27 szöveg == az index.html 33/34 csere. `mock`/`mock_regresszio`/`MAI16`/`NL` a meglévő helperek. ✓
