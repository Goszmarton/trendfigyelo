# Egységes formavilág – kivitelezési terv

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mind a 11 oldal egyetlen vizuális készletből épüljön (grafit oldalsáv, felső sáv, állapot-pill, kártya, chip, stat-sor, egységes grafikonstílus), egy helyen definiált színekkel – adat, szöveg és szám változatlan.

**Architecture:** Helyben átalakítás. A HTML-ek megtartják azonosítóikat és osztályaikat. A menü statikus HTML-ként kap új oldalsáv-szerkezetet. Az `app.css` `:root` tokenekre épül, a JS-színeket egy új `szinek.js` olvassa ki a tokenekből. A felső sávot, a pillt és a badge-eket egy új `keret.js` tölti ki a meglévő adatfájlokból.

**Tech Stack:** statikus HTML/CSS/vanilla JS (`docs/`), Chart.js 4.5.1 és Leaflet 1.9.4 (vendorált), Inter 4.1 (vendorált woff2), lucide-static (vendorált SVG-sprite), pytest + Playwright.

**Spec:** `docs/superpowers/specs/2026-11-28-egyseges-formavilag-design.md`

## Global Constraints

- Adatgyűjtés, workflow-k, `trendfigyelo/` Python-kód, `docs/data/`: **nem módosul**.
- Egyetlen megjelenített szöveg vagy szám sem változik; új szöveg csak a keret-elemekben: breadcrumb, gyűjtési idők, állapot-pill, badge-szám.
- A badge-szám és az ikon nem kerülhet egy link `textContent`-jébe (badge = CSS `::after { content: attr(data-badge) }`, ikon = `<svg aria-hidden="true">`).
- Nincs külső betöltés, nincs inline script / inline eseménykezelő (a `tests/test_pages.py` őrzi). Új vendor fájl → `docs/vendor/FORRAS.md` gépi sor: `` `<rel/útvonal>` — sha256: `<64 hex>` ``.
- Meglévő azonosítók/osztályok maradnak. Új osztály csak `keret-*` vagy `ui-*` névtérben, előtte `grep -rn "<név>" docs e2e tests` → 0 találat. Új e2e spec neve előtte ellenőrizve, hogy nem létezik.
- Tokenértékek a spec táblázatából, szó szerint (`--oldalsav-hatter:#202326` … `--youtube:#D6453D`). Témák: `--tema-1..8` = `#0072B2 #E69F00 #009E73 #CC79A7 #56B4E9 #D55E00 #F0E442 #4D4D4D`; a `--tema-7` csak kitöltés/pötty, vonalként nem.
- A már ma létező grafikonjelentések tokenre kerülnek **a mostani értékükkel** (az e2e ezekre szűr): `--graf-ml:#8e44ad`, `--graf-elorejelzes:#16a085`, `--graf-elorejelzes-sav:rgba(22, 160, 133, 0.15)`, `--graf-trend:#cc3333`, `--graf-szint:#e69138`, `--graf-sav:rgba(120, 120, 120, 0.14)`, `--graf-jelolo:#8a8a8a`. A mért adatvonal (`ADAT_VONAL_SZIN`, ma `#3366cc`) → `--google`, a YouTube-on → `--youtube`.
- A Havi Leaflet-térképek stílusa változatlan (a `#ef6c33` jelölőt e2e rögzíti); csak a keretük lesz kártya.
- Dátumformátum: a grafikon-tooltip/tengely formátuma marad a meglévő `ms_datum` szerinti (`2025. 08. 10.`); új formátum csak a felső sáv gyűjtési idejében: „ma 21:00” / „tegnap 21:00” / „nov. 27. 21:00” (Budapest).
- Suite: SOROS futtatás (`.venv/bin/python -m pytest -q tests/`, `npx playwright test`); a meglévő 774 Python + 230 e2e zöld marad. Meglévő tesztet csak akkor szabad módosítani, ha kifejezetten régi **vizuális** szerkezetet rögzít; ezt a commitüzenetben meg kell indokolni.
- Minden task külön commit; push csak a végén, USER-jóváhagyás után.

## Review Focus

1. **Hiányzó/lassú adatfájl a keretben** (pl. `legfrissebb.json` 404 vagy hibás JSON): a felső sáv „–”-t mutat, a pill nem jelenik meg, a badge nem jelenik meg; az oldal többi része hiba nélkül renderel. → Task 4 tesztje.
2. **Keskeny képernyő (360px)**: nincs vízszintes görgetés egyetlen oldalon sem; az oldalsáv fiókmenü. → Task 3 és Task 8 tesztje.
3. **JS nélkül**: a menü (`#fomenu`) látható és minden link működik; a keret-elemek egyszerűen hiányoznak. → Task 3 tesztje.
4. **Billentyűzetes navigáció**: a menülinkeken és chipeken a fókusz látható (`--akcentus` körvonal). → Task 3 és Task 5 tesztje.
5. **Hosszú szövegek** (hosszú felkapott kifejezés, hosszú ügycím): kártyán belül tördelődnek, nem lógnak ki. → Task 5 tesztje.

---

### Task 1: Tokenek, Inter és lucide vendorálása

**Files:**
- Modify: `docs/css/app.css` (eleje: `@font-face` + `:root` tokenek; `body` alapstílus tokenekre)
- Create: `docs/vendor/inter/InterVariable.woff2`, `docs/vendor/lucide/ikonok.svg`
- Modify: `docs/vendor/FORRAS.md`
- Test: `tests/test_formavilag.py` (új)

**Interfaces:**
- Produces: a spec és a Global Constraints összes tokene `:root`-ban; további tokenek: `--betu: "Inter", system-ui, "Segoe UI", sans-serif`, `--r-kartya:12px`, `--r-chip:8px`, `--r-pill:999px`, `--ter-1..8` (4/8/12/16/20/24/32/40px), `--betu-cim:30px`, `--betu-szakasz:17px`, `--betu-kartya:14.5px`, `--betu-torzs:14px`, `--betu-seged:12.5px`, `--betu-mikro:11px`. Sprite szimbólum-azonosítók: `i-attekinto` (layout-grid), `i-napi` (calendar), `i-heti` (chart-column), `i-havi` (globe), `i-valtozasok` (activity), `i-ugyek` (list), `i-kapcsolodo` (share-2), `i-google` (search), `i-youtube` (youtube), `i-info` (info), `i-menu` (menu), `i-logo` (trending-up).

- [ ] **Step 1: Write the failing test** – `tests/test_formavilag.py::test_root_tokenek_a_spec_ertekeivel`: beolvassa az `app.css` első `:root{…}` blokkját, és minden token–érték párt ellenőriz a fenti listából (kis- és nagybetűtől független összevetés). `test_inter_font_face_helyi`: van `@font-face` `font-family:"Inter"` és `src: url("../vendor/inter/InterVariable.woff2")`. `test_lucide_sprite_szimbolumok`: az `ikonok.svg` mind a 12 `id`-t tartalmazza `<symbol>` elemként.
- [ ] **Step 2:** `.venv/bin/python -m pytest -q tests/test_formavilag.py` → FAIL.
- [ ] **Step 3: Vendorálás.** Inter 4.1: a `rsms/inter` GitHub-kiadás `Inter-4.1.zip`-jének `web/InterVariable.woff2` tagja (OFL-1.1). lucide: `lucide-static` npm-tarball (a letöltéskor aktuális, legalább két hetes verzió pinelve, ISC), a 12 ikon `icons/*.svg`-jéből `<symbol id="i-…" viewBox="0 0 24 24">` sprite (stroke="currentColor", fill="none", stroke-width 1.8). A FORRAS.md-be a chart.js-szakasz mintájára: csomag, verzió, licenc, letöltési URL, tarball-integritás, gépi sha256-sor mindkét fájlra.
- [ ] **Step 4:** `:root` tokenek + `@font-face` (`font-display: swap`, `font-weight: 100 900`) + `body { font-family: var(--betu); background: var(--hatter); color: var(--szoveg); }`. A régi szabályok ezen kívül érintetlenek.
- [ ] **Step 5:** `pytest -q tests/` és `npx playwright test` → minden zöld (a vendor-guard is).
- [ ] **Step 6: Commit** `feat(ui): design-tokenek + vendorált Inter és lucide-ikonkészlet`

### Task 2: `szinek.js` – tokenolvasó, témaszínek, közös Chart.js-alap, JS-színek kiszervezése

**Files:**
- Create: `docs/js/szinek.js`
- Modify: `docs/js/app.js` (színkonstansok: 105–151., 689–692. sor környéke, `IDOSOR_PALETTA`), `docs/js/heti.js:8-9`, `docs/js/havi.js:127` (csak a bar-chart), `docs/js/bovites.js:97`, `docs/js/youtube.js` (ha saját színt használ)
- Modify: mind a HTML, ami Chart.js-t vagy a fenti JS-eket tölti: `<script src="js/szinek.js">` a `chart.umd.js` UTÁN, az oldal saját JS-e ELŐTT
- Test: `tests/test_formavilag.py`, `e2e/formavilag.spec.js` (új; előtte ellenőrizd, hogy nem létezik)

**Interfaces:**
- Produces (globális függvények, `module.exports`-tal is a Node-tesztekhez, az `ai_szunet.js` mintájára):
  - `szin(nev: string, tartalek: string) -> string` – `getComputedStyle(document.documentElement).getPropertyValue("--"+nev).trim()` vagy `tartalek`.
  - `TEMA_SORREND_GOOGLE = ["megelhetes","egeszsegugy","oktatas","gazdasag","politika"]` → `tema-1..5`.
  - `tema_szin(domen: string, forras: "google"|"youtube") -> string` – Google: a fenti sorrend; YouTube: a `youtube.js` `YT_DOMEN_SORREND` indexe → `tema-(i+1)`; ismeretlen → `--semleges`.
  - `grafikon_alap()` – egyszer, betöltéskor beállítja: `Chart.defaults.font.family = szin("betu")`, `Chart.defaults.color = szin("szoveg-2")`, `Chart.defaults.borderColor = "#EEF0EE"` (rács), tooltip háttér `--szoveg`, a vonalvastagság alapja 1.5.
- Consumes: Task 1 tokenek.

- [ ] **Step 1: Failing tests.** Python: `test_js_nincs_beegetett_hex_szin` – a `docs/js/*.js`-ben (kivéve `szinek.js` és `havi.js` Leaflet-stílus sorait: 204., 256–261., 302–308. környék, explicit allowlist sorminta alapján) nincs `#[0-9a-fA-F]{3,6}\b` és `rgba?\(` literál. e2e `formavilag.spec.js`: „tema_szin: megelhetes → #0072B2, politika → #56B4E9, ismeretlen → #98A0A8” (`page.evaluate` a `trendek.html`-en); „kulcsszó-chart adatvonala a --google színű” (a chart-példány első datasetjének `borderColor`-ja kisbetűsítve `#3b6fd8`).
- [ ] **Step 2:** futtatás → FAIL.
- [ ] **Step 3:** `szinek.js` megírása; az `app.js`/`heti.js`/`havi.js`/`bovites.js`/`youtube.js` konstansai `szin("…", "<régi érték>")`-re cserélve (a tartalékérték a régi hex, hogy JS-hiba esetén se törjön). `HETI_SZIN_EROS` → `--tema-1`, `HETI_SZIN_GYENGE` → `--tema-6`. A `bovites.js` hőtérkép-rgba alapja `--akcentus` RGB-je (`szin`-ből számolva). `IDOSOR_PALETTA` → `tema-1..8`. A YouTube adatvonala `--youtube`.
- [ ] **Step 4:** a domén-csoportcímek (`.domen-csoport` címe a Google- és YouTube-fülön) elé `<span class="ui-tema-potty" style="--potty: …">` (a szín `tema_szin`-ből, inline CSS-változóként; a cím szövege változatlan).
- [ ] **Step 5:** teljes suite → zöld (a `#8e44ad`/`#16a085` szűrő e2e-k változatlanul zöldek, mert a token értéke azonos).
- [ ] **Step 6: Commit** `feat(ui): szinek.js – minden grafikonszín tokenből, témaszínek, közös Chart.js-alap`

### Task 3: Oldalsáv (11 HTML menüje) + mobil fiókmenü

**Files:**
- Modify: a 11 HTML `<nav id="fomenu">` blokkja és a `<body>` közvetlen szerkezete; `docs/css/app.css` (oldalsáv + rács)
- Create: `docs/js/keret.js` (ebben a taskban csak a fiókmenü-kapcsoló)
- Test: `tests/test_formavilag.py`, `e2e/formavilag.spec.js`

**Interfaces:**
- Produces: HTML-váz minden oldalon:
  `<body class="keret">` → `<aside class="keret-oldalsav">` [logó: `<div class="keret-logo"><svg…><use href="vendor/lucide/ikonok.svg#i-logo"/></svg>Trendfigyelő</div>` – NEM link, a `#fomenu`-n KÍVÜL] + a meglévő `<nav id="fomenu">` (a 10 link és a 3 `.fomenu-cimke` szövege/sorrendje/href-je/`aria-current`-je változatlan; minden link elején `<svg class="keret-ikon" aria-hidden="true"><use href="vendor/lucide/ikonok.svg#i-…"/></svg>`; badge-helyek: `data-keret-badge="valtozasok|ugyek|napi|heti|havi"` attribútum a linken; a Google- és YouTube-link STATIKUS `data-badge`-et kap a követett kulcsszavak számával – a `legfrissebb.json` csak a legutóbbi futás szavait tartja (élőben 13, nem 28), a teljes lista csak 1,9–3,5 MB-os fájlokban van) `</aside>` + `<div class="keret-fo">` [`<div class="keret-felso" id="keret-felso"></div>` + a lap meglévő tartalma (header, main, footer) változatlan sorrendben] `</div>`. Mobil gomb: `<button class="keret-menugomb" id="keret-menugomb" aria-controls="fomenu" aria-expanded="false">` a `.keret-felso`-ben (felirat nélkül, `aria-label="Menü"`).
  - `keret.js`: `keret_menu_init()` – a gomb `aria-expanded`-et és a `body.keret-menu-nyitva` osztályt váltja.
  - CSS: ≥ 901px: kétoszlopos rács (`240px 1fr`), a sáv sticky teljes magasságú. ≤ 900px: a sáv rejtett, `body.keret-menu-nyitva` esetén fiókként a tartalom fölött.
- Consumes: Task 1 tokenek és sprite.

- [ ] **Step 1: Failing tests.** Python `test_menu_mind_a_11_oldalon_azonos`: a 11 HTML (a `bovites.html` redirect kivételével) `<nav id="fomenu">…</nav>` blokkja egyezik, miután az `aria-current="page"` és `class="aktiv"` attribútumokat eltávolítottuk. `test_minden_oldalon_keret_vaz`: van `class="keret-oldalsav"`, `id="keret-felso"`, `src="js/keret.js"`. `test_statikus_badge_egyezik_a_configgal` (a `test_adatokrol_kulcsszo_szam_egyezik_a_configgal` mintájára): a Google-link `data-badge`-e == a `config.yaml` kulcsszavainak száma, a YouTube-linké == a YouTube-konfiguráció kulcsszavainak száma, mind a 11 oldalon. e2e: „oldalsáv 1280px: #fomenu látható, bal oldalt, szélessége 240±2px, az aktív link háttere rgb(143, 220, 208)”; „360px: #fomenu rejtett, menügomb katt → látható, aria-expanded=true”; „360px: document.scrollWidth <= 360 mind a 11 oldalon” (Review Focus 2); „JS kikapcsolva (`javaScriptEnabled:false`) 1280px: a 10 menülink látható” (Review Focus 3); „Tab-bal a második menülinkre: outline színe rgb(31, 138, 138)” (Review Focus 4).
- [ ] **Step 2:** futtatás → FAIL.
- [ ] **Step 3:** a 11 HTML átírása egy szkripttel (a scratchpadban, NEM a repóban), ami a nav-blokkot cseréli; utána diff-ellenőrzés, hogy a navon kívül csak a burkoló `aside`/`div` változott.
- [ ] **Step 4:** CSS + `keret.js` fiókmenü.
- [ ] **Step 5:** teljes suite → zöld; a `menu.spec.js` VÁLTOZATLANUL zöld (10 link, 3 címke, pontos szövegek).
- [ ] **Step 6: Commit** `feat(ui): grafit oldalsáv ikonokkal, mobil fiókmenü (mind a 11 oldal)`

### Task 4: `keret.js` – felső sáv, gyűjtési idők, állapot-pill, badge-ek

**Files:**
- Modify: `docs/js/keret.js`, `docs/css/app.css`
- Test: `e2e/formavilag.spec.js`, `tests/test_formavilag.py`

**Interfaces:**
- Produces (pure, `module.exports`-tal is):
  - `keret_ido_szoveg(iso: string|null, most: Date) -> string` – Budapest-idő: azonos nap → `"ma HH:MM"`, előző nap → `"tegnap HH:MM"`, egyébként `"<hó röv.> <nap>. HH:MM"` (`jan. feb. márc. ápr. máj. jún. júl. aug. szept. okt. nov. dec.`); null/hibás → `"–"`.
  - `keret_pill(iso_lista: (string|null)[], most: Date) -> {allapot: "ok"|"figy"|"hiba", szoveg: string} | null` – a LEGRÉGEBBI időponthoz mért kor: ≤ 26 h → `{ok, "Gyűjtés rendben"}`, ≤ 48 h → `{figy, "Gyűjtés késik"}`, > 48 h → `{hiba, "Gyűjtés hiba"}`; bármely null → `null`. (Megjelenítés CSS-ben nagybetűs.)
  - `keret_init()` – oldalanként (a `body` `data-keret-oldal` attribútuma alapján; Task 3 ezt nem állította be → itt kerül minden HTML `<body>`-jára: `attekinto|napi|heti|havi|valtozasok|ugyek|kapcsolodo|google|youtube|info|404`):
    - Felső sáv: breadcrumb = az aktív link csoportjának `.fomenu-cimke` szövege + „ / ” + az aktív link szövege (csoport nélküli lapon csak a link szövege); jobb oldalt „Google: …” és „YouTube: …” a forráspöttyel. Források: `data/legfrissebb.json` → `frissitve`; `data/youtube_regresszio.json` → `szamitva_utc`. Fetch: `{cache: "no-cache"}`, mindkettő egyszer.
    - Pill (`<div class="keret-pill keret-pill--<allapot>">`, a `header.fejlec-doboz` ELSŐ gyereke): `google` → `keret_pill([google])`; `youtube` → `[youtube]`; `attekinto` → `[google, youtube]`; `napi|heti|havi` → ha az `ai_szunet.json` `szunetel.<tipus>` igaz: `{figy, "Szünetel"}` + dátum a `ota`-ból, egyébként nincs pill; `valtozasok|kapcsolodo` → nincs új pill, a meglévő `#radar-idosav` kap `keret-pill keret-pill--semleges` osztályt és CSS-sel a cím fölé kerül (`order:-1` a flex-oszlop fejlécben), szövege változatlan; `ugyek` → szünetben `{figy, "Szünetel"}` pill, a dátum-rész helyére a `#radar-idosav` elem kerül át (DOM-mozgatás, szöveg változatlan); `info|404` → semmi. Pill mellett a dátum: `2026. november 28.` (Budapest, `most`).
    - Badge (dinamikus): `valtozasok` = `elmozdulas.json` `szokatlan_lista.length`; `ugyek` = `ugyek.json` `ugyek.length`; `napi|heti|havi` = `"⏸"`, ha szünetel. Írás: `link.setAttribute("data-badge", …)`; 0 vagy hiba → nincs attribútum. A `google`/`youtube` badge statikus (Task 3), a JS nem írja felül.
- Consumes: Task 3 HTML-váz, `data-keret-badge`.

- [ ] **Step 1: Failing tests.** Node-ból (`node -e` a Playwright-teszt `test.describe` előtt, vagy `page.evaluate`) a pure függvényekre: `keret_ido_szoveg("2026-11-28T20:00:00Z", new Date("2026-11-28T21:30:00Z")) === "ma 21:00"`; előző napra `"tegnap 21:00"`; `"2026-11-25T20:00:00Z"` → `"nov. 25. 21:00"`; `null` → `"–"`. `keret_pill(["2026-11-28T08:00:00Z"], 2026-11-28T20:00Z)` → `{allapot:"ok",…}`; 30 h → `figy`; 50 h → `hiba`; `[ok, null]` → `null`. e2e (route-mockkal): „trendek: pill = Gyűjtés rendben, a header első gyereke”; „trendek: legfrissebb.json 404 → nincs pill, a felső sávban »Google: –«, a #kulcsszo-blokk renderel” (Review Focus 1); „ugyek: egyetlen .keret-pill, szövege tartalmazza a #radar-idosav szövegét”; „kapcsolodo: a #radar-idosav szövege változatlan, osztálya keret-pill”; „#fomenu a[href=ugyek.html] textContent === 'Ügyek' akkor is, ha a data-badge='44'”; „breadcrumb a heti.html-en: »Elemzések / Heti«”.
- [ ] **Step 2:** futtatás → FAIL.
- [ ] **Step 3:** `keret.js` + CSS (`.keret-felso`, `.keret-pill`, `--ok/--figy/--hiba/--semleges` pötty + szöveg, `[data-badge]::after`).
- [ ] **Step 4:** teljes suite → zöld (`ai-szunet.spec.js`, `ugyek.spec.js`, `valtozasok.spec.js`, `kapcsolodo.spec.js` változatlanul).
- [ ] **Step 5: Commit** `feat(ui): felső sáv gyűjtési időkkel, állapot-pill és menü-badge-ek`

### Task 5: Komponensek + Statisztikák-oldalak (Google, YouTube)

**Files:**
- Modify: `docs/css/app.css` (komponensek: `.fejlec-doboz` oldalfejléc, kártya, `.szekcio`/`.vezerlo-sav` → chip-sor, gombok → chip, stat-sor, info-doboz, táblázat; a `#dashboard` és `#youtube-blokk` alatti szabályok)
- Test: `e2e/formavilag.spec.js`; `e2e/layout.spec.js` (csak ha indokolt)

**Interfaces:**
- Produces (osztályok, amelyeket a Task 6–7 újrahasznosít): `.ui-kartya`, `.ui-chipsor`, `.ui-chip` / `.ui-chip[aria-pressed="true"]` vagy a meglévő aktív-jelölés, `.ui-statsor` / `.ui-stat` / `.ui-stat-szam` / `.ui-stat-cimke`, `.ui-szakaszcim`. Ahol a meglévő elemnek már van osztálya, a stílus a MEGLÉVŐ osztályra kerül (pl. `.vezerlo-sav` = chip-sor), új osztály csak ott, ahol nincs.
- Consumes: tokenek.

- [ ] **Step 1: Failing tests.** e2e `trendek.html` 1280px: „a .vezerlo-sav a saját szakasza fölött van (bounding box y < a #kulcsszo-blokk y-ja) és a gombjai egy sorban (azonos y)”; „aktív intervallum-gomb kerete rgb(31, 138, 138)”; „a kulcsszó-kártya border-radius 12px, háttere fehér, kerete rgb(226, 229, 227)”; „h1 font-size 30px, font-weight 800”; „hosszú felkapott kifejezés (80 karakter, route-mock) nem lóg ki a trendkártyából: scrollWidth <= clientWidth” (Review Focus 5); „Tab-fókusz egy chipen: outline rgb(31, 138, 138)” (Review Focus 4). Ugyanezek a `youtube.html`-en a `#youtube-intervallum-vezerlo`-val.
- [ ] **Step 2:** futtatás → FAIL.
- [ ] **Step 3:** CSS-átírás. A `layout.spec.js` ST2 (`.vezerlo-sav` sticky) megmarad: a chip-sor sticky a szakasz tetején. Ha egy meglévő e2e kifejezetten a régi bal oldali oszlop-elrendezést rögzíti (pl. x-koordináta), azt a commitüzenetben indokolva frissítsd; tartalmi állítás nem változhat.
- [ ] **Step 4:** teljes suite → zöld.
- [ ] **Step 5: Commit** `feat(ui): kártya-, chip- és stat-komponensek; Google és YouTube oldal`

### Task 6: Elemzések, Áttekintő, Infó, 404

**Files:**
- Modify: `docs/css/app.css` (`#elemzes`, `#heti`, `#havi`, `#nyitooldal`, `.nyitooldal-*`, `.attekinto-*`, `#adatokrol`/Infó, `.ai-szunet-sav`, naptárak `.nap-cella*`), `docs/404.html` (oldalkeret, ha a Task 3 nem fedte)
- Test: `e2e/formavilag.spec.js`

**Interfaces:** Consumes: Task 5 komponensosztályok és tokenek.

- [ ] **Step 1: Failing tests.** e2e: „index.html: a 3 .nyitooldal-kartya egy rácsban (azonos y), radius 12px”; „elemzes/heti/havi: a .ai-szunet-sav háttere a --figy tónusa és a header után áll”; „havi: a Leaflet-térkép konténere .ui-kartya keretet kap, a #ef6c33 jelölő megvan”; „naptár nap-cella érintési célmérete >= 24px” (a `mobil.spec.js` G2 változatlanul zöld).
- [ ] **Step 2:** FAIL. **Step 3:** CSS. **Step 4:** teljes suite → zöld.
- [ ] **Step 5: Commit** `feat(ui): Elemzések, Áttekintő, Infó és 404 az új formavilágban`

### Task 7: Radar-oldalak (Változások, Ügyek, Kapcsolódó)

**Files:**
- Modify: `docs/css/app.css` (a `bovites.js` által renderelt listák/kártyák/szűrők osztályai)
- Test: `e2e/formavilag.spec.js`

**Interfaces:** Consumes: Task 5 komponensosztályok, Task 4 pill.

- [ ] **Step 1: Failing tests.** e2e: „valtozasok: az elmozdulás-tételek kártyák (radius 12px), az irány-jel ▲ színe rgb(46, 139, 87), ▼ rgb(200, 65, 75)”; „ugyek: hosszú ügycím (120 karakter, route-mock) tördelődik” (Review Focus 5); „kapcsolodo: a szűrő-gombok chip-stílusúak”.
- [ ] **Step 2:** FAIL. **Step 3:** CSS. **Step 4:** teljes suite → zöld.
- [ ] **Step 5: Commit** `feat(ui): Radar-oldalak az új formavilágban`

### Task 8: Régi stílus-maradványok takarítása + élő vizuális átnézés

**Files:**
- Modify: `docs/css/app.css` (a már nem használt régi szabályok törlése; minden szín `var(--…)`)
- Test: `tests/test_formavilag.py`

- [ ] **Step 1: Failing test** `test_css_szinek_csak_tokenbol`: az `app.css`-ben a `:root` blokkon kívül nincs `#hex` és `rgb(a)?(` literál (kivétel: `rgba(var(--…))`-alapú vagy `color-mix` kifejezés).
- [ ] **Step 2:** FAIL. **Step 3:** takarítás. **Step 4:** teljes suite → zöld; 360px-es no-horizontal-scroll teszt mind a 11 oldalon zöld.
- [ ] **Step 5:** Élő képernyőképek (élő `docs/data`-val, `python3 -m http.server` a `docs/`-ból, Playwright-szkript a scratchpadban) mind a 11 oldalról 1280px és 390px szélességen → a USER-nek megmutatva; a visszajelzés alapján javítás ugyanebben a taskban.
- [ ] **Step 6: Commit** `refactor(ui): régi stílusok takarítása, minden szín tokenből`
