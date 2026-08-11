# Design — Task 10: mobil-geometria + célzott hozzáférhetőség

**Dátum:** 2026-08-11
**Hatókör:** mobil-geometria (VERIFIKÁCIÓ, nem retune) + célzott a11y + egy kozmetikai lelet. Tisztán frontend (CSS + egy kevés JS-mentes) + e2e-őrök. NINCS Google-hívás, NINCS adat-commit.
**Sorrend a munkarendben:** A (kész) → **Task 10 (ez)** → B (minden kártyán görbe) → Task 11 (fázis-zárás) → C (heti táblázat).

## 0. A mérés átszabta a hatókört (a fő indoklás megdőlt kód előtt)

A Task 10 eredeti fő indoka a `rootMargin` újrahangolása volt az A1 +77px offszetjén. A **mérés (élő oldal, docs/data)
megdöntötte ezt a premisszát**, mielőtt egy sor kód megszületett volna (lásd §1). Ezért a Task 10 valós tartalma:
touch-target + `:focus-visible` + kozmetika + egy render-on-load **regressziós őr** — NEM rootMargin-változtatás.

## 1. Geometria — `rootMargin` VÁLTOZATLAN marad + render-on-load guard

### 1.1 MÉRT tények (élő oldal, több mobil-viewport, scroll=0)
- Az első **kulcsszó**-kártya (`#kulcsszo-blokk .kulcsszo-chart`) teteje **~708px** MINDEN reális nézeten
  (360×640, 390×844, 360×740, 360×380-rövid; szélesebb fekvőn 812×375 → 585px).
- `rootMargin:"400px"` → a lusta-render zóna alja = `viewport_magasság + 400`. Még a rövid 360×380-nál is
  `380+400 = 780px ≥ 708` → az első kártya **FEDVE**. Igazolva: az első kártya **canvas-a JELEN van betöltéskor**
  (count=1) 360×640-en ÉS 360×380-on is → az observer ténylegesen lefut.
- Kritikus küszöb: az első kártya csak akkor esne ki, ha `viewport_magasság + 400 < 708`, azaz **vh < ~308px** —
  gyakorlatilag sosem áll elő (a legrövidebb valós mobil-magasság is jóval e felett van).
- **A +77px (A1) a TREND-blokk első kártyájára esett** (`~7216px` a lap tetejétől), NEM a kulcsszó-blokkra. Ez volt
  a korábbi feltevés hibája. A trend-blokk kártyái ilyen mélyen a lusta-rendert HELYESEN görgetésre kapják.

### 1.2 DÖNTÉS és INDOKLÁS
`rootMargin` **marad `"400px"`**. **Miért:** nincs javítandó hiba → a `rootMargin` emelése kizárólag ELREJTENE
(pontosan az L10-ben ELVETETT maszkolás-elv: „ha nincs valódi hiba, az emelés csak elfed"). A mérés a valós
lefedettséget igazolta, nem a hiányát.

### 1.3 Render-on-load GUARD (a mérést kód-formában őrzi)
e2e (Playwright): **360×640** viewporton, betöltés után (scroll=0), az első `#kulcsszo-blokk .kulcsszo-chart`
tartalmaz `canvas`-t (count ≥ 1).
- **Miért 360×640 (nem önkényes):** valós, gyakori Android portré méret. A valós `rootMargin:400` zóna-alja
  `1040 ≥ 708` → fedve (canvas jelen). A **mutáció** `rootMargin:"0px"` → zóna-alja `640 < 708` → NEM fedve
  (canvas hiányzik) → a guard **bukik**. Így a guard bizonyítottan a **zóna-LEFEDETTSÉGET** méri, nem pusztán a
  canvas létezését. (A mérés külön igazolta, hogy a rövidebb nézetek 360×380-ig szintén fedve vannak; a guard
  valós eszközt használ a nem-önkényességért.)
- **Szándékos ZÖLD** őr (a kód már helyes): a nem-vakságot a fenti mutáció (`rootMargin:"0px"`) igazolja; a plan
  ezt egy körben elvégzi és VISSZAÁLLÍTJA (a végén `grep MUTÁCIÓ == 1`).

## 2. Érintési célméret (WCAG 2.5.8 AA = 24px minimum)

### 2.1 MÉRT magasságok (rendered boundingBox, mobil)
- dátum-`<select>`: **19px → BUKIK** a 24px AA-minimumot.
- kategória-gomb (`.kategoria-gomb`): **25px** — épphogy átmegy (24px + 1px).
- intervallum-gomb: **26,6px** — átmegy.

### 2.2 Terv
- **dátum-`<select>` GLOBÁLISAN `min-height` ≥ 24px** (cél ~32px). A 19px egérrel is bukó AA, tehát nem csak érintőn
  javítjuk.
- **`@media (pointer: coarse)` réteg:** érintő-eszközön az intervallum-gomb + kategória-gomb + reset-gomb + a
  `<select>` tap-magassága **≥ 44px** (AAA 2.5.5 komfort). A **desktop egér-UI VÁLTOZATLAN** marad (kompakt).
  A pill-forma (kategória) és a szögletes forma (intervallum) MEGMARAD — csak a magasság/padding nő coarse pointeren.
- **A kategória-gomb desktopon SZÁNDÉKOSAN marad 25px** (1px ráhagyás a 24px AA-hoz) — mivel a coarse-réteg érintőn
  úgyis 44px-re viszi, desktopon a kompakt 25px marad. Ez TUDATOS döntés, nem elnézés; a jövőbeli olvasó ne
  javításnak vélje.

## 3. Fókusz-láthatóság (`:focus-visible`)

Jelenleg NINCS `:focus`/`outline`/`focus-visible` CSS-szabály — a fókuszgyűrű a böngésző alapértelmezettjére van
bízva, ami az A2 explicit gomb-háttere mellett inkonzisztens lehet.
**Terv:** explicit `:focus-visible { outline: 2px solid #3366cc; outline-offset: 2px; }` az intervallum-, kategória-,
reset-gombokra és a `<select>`-re. `:focus-visible` (NEM `:focus`) → csak billentyűzet-fókusznál látszik, egér-
kattintásnál nem villan. A `#3366cc` (az aktív kategória-szín) fehéren jól látható.

## 4. Kozmetika — intervallum ok-oszlop igazítás (08-10 lelet)

### 4.1 MÉRT jelenség (screenshot, 360px)
A letiltott intervallumok ok-szövege („Ehhez több összefűzött nap kell") **ragadt bal-éllel** indul, mert az
intervallum-gombok eltérő szélesek (1 hét / 2 hét / 1 hó / 3 hó / 1 év) → az ok-oszlop nem igazodik egy vonalba.

### 4.2 Terv (MÉRT min-width, nem becsült)
- **MÉRÉS:** a legszélesebb gomb FÉLKÖVÉR (kiválasztott) állapotban „1 hét" = **55,5px** (border-box). A többi:
  2 hét 45,2 · 1 hó 43 · 3 hó 43 · 1 év 42,2.
- **`#intervallum-vezerlo button { min-width: 3.5rem; box-sizing: border-box; white-space: nowrap; }`** — a 3,5rem
  (56px) felülről fedi a mért 55,5px-t → minden gomb legalább ilyen széles → az ok-szövegek EGY oszlopban igazodnak.
  A `white-space: nowrap` megakadályozza a label két sorba törését keskeny nézeten.
  (A `box-sizing: border-box` itt konzisztens az A2-ből örökölt kerettel; a min-width a teljes gombra vonatkozik.)

## 5. MÉRT tény — a reduced-motion TÁRGYTALAN (nem építünk hozzá)

**Mérés (nem feltevés):** mind a **3** `new Chart(` hívás — `app.js:493` (kulcsszó), `:688` (trend-sparkline),
`:729` (kategória) — `animation: false`-szal készül (`:497`, `:696`, `:737`). Az `app.css`-ben **NINCS** CSS-mozgás
(`transition`/`animation`/`@keyframes`/`transform`: 0 db). EBBŐL következik: az oldalnak nincs mozgása → a
`prefers-reduced-motion`-nek nincs mit kikapcsolnia.
**KÖVETKEZMÉNY (ledger-constraint):** az `animation:false` MINDHÁROM Chart-configban **KÖTELEZŐ marad**. Ha valaha
bekapcsolják az animációt bármelyik helyen, AKKOR (és csak akkor) kell `prefers-reduced-motion`-t bevezetni. Most
NEM teszünk be dead media-query-t (YAGNI).

## 6. L10 LEZÁRÁSA (explicit — nehogy nyitottnak tűnjön)

Az **L10 EZENNEL LEZÁRVA**: a fix-basis vezérlősáv álló módú magasság-problémáját a 08-08-i `@media flex:0 0
auto/static` fix megoldotta, a MAI mérés pedig kód-előtt igazolta (első kulcsszó-kártya 708px vs zóna-alja ≥780px;
kritikus küszöb ~308px vh, ami sosem áll elő; a +77px a trend-blokkra esett, nem a kulcsszóra). A `rootMargin`
maradt 400px, mert nem volt javítandó hiba.
**Következmény a dokumentumokra:** az ATADAS jelenlegi „L10 — … Task 10: rootMargin ÚJRAHANGOLÁS …" sora és a §3
Task 10-nél a +77px-re hivatkozó „a rootMargin-t a KEZDŐ OFFSZETRE kell hangolni" megjegyzés **átírandó ZÁRTRA**
(a Task 10 végén, a §7 plan-lépés szerint), különben a következő olvasó nyitott hatókörnek hiszi.

## 7. Tesztelés / regresszió

- **Szilárd e2e (2 db):** (1) §1.3 render-on-load guard (360×640, canvas jelen; mutáció rootMargin:"0px");
  (2) §2 date-`<select>` magassága ≥ 24px (mért érték-őr; mutáció: a `min-height` eltávolítása bukjon).
- **Media-query jelenlét-guard:** a `@media (pointer: coarse)` szabály LÉTEZIK az app.css-ben (könnyű, nem törékeny;
  a coarse-emuláció megbízhatatlan Playwrightban).
- **L9-osztály (vizuális szemle, NEM törékeny assert):** a `:focus-visible` körvonal és a `pointer:coarse` 44px
  tényleges megjelenése — kézi szemle, nem erőltetett computed-style/emuláció.
- Kapuk: SOROS suite (`--workers=1`), a végén `grep -rn "MUTÁCIÓ" … == 1`, adat-commit nincs.
- **Plan-lépés a kör végére:** az ATADAS L10/Task-10 sorainak ZÁRTRA írása (§6).

## 8. YAGNI / hatókör-korlát

- NINCS `rootMargin`-változtatás (a mérés szerint fölösleges és maszkoló lenne).
- NINCS `prefers-reduced-motion` media-query (nincs mozgás; §5).
- NINCS egyéb refaktor. A B (minden kártyán görbe) és C (heti táblázat) NEM ennek a körnek a része.
