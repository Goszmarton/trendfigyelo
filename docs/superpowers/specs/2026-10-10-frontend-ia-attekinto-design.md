# Frontend információs-architektúra + „Áttekintő" nyitóoldal — terv

**Dátum:** 2026-10-10
**Típus:** architekturális (az egész oldal navigációját és belépő-pontját érinti)
**Állapot:** jóváhagyásra vár

## Cél (egy mondat)

A lapos 7-tabos navigációt fogalmilag csoportosított navigációra cseréljük, és az
átirányító `index.html` helyett egy valódi „Áttekintő" nyitóoldalt adunk, hogy a
felhasználó ránézésre elkülönítse az **elemzéseket** (napi/heti/havi), a **radar-jelzéseket**
és a **nyers statisztikákat**.

## Szándék és háttér (a közös megértés rögzítése)

- **Probléma (USER szavaival):** „rengeteg elemzés és adat keveredik"; a fő fájdalom, hogy
  **nem látszik, mi elemzés és mi statisztika**.
- **Közönség:** vegyes — laikus, első látogatók ÉS vissza-visszatérő használók.
- **Megoldás-irány (jóváhagyott „B"):** csoportosított navigáció **+** könnyű „Áttekintő"
  nyitóoldal. (Az „A" = csak nav, elvetve, mert a vegyes közönségnek kell belépő pont; a „C" =
  oldalak összevonása alfülekbe, későbbre halasztva a nagyobb regressziós kockázat miatt.)
- **Siker-kritérium:** egy új látogató pár másodperc alatt érti a három tartalmi területet és
  tudja, hova menjen; a visszatérő továbbra is egy kattintással a tartalomban van; a backend és
  az adat-pipeline VÁLTOZATLAN.

## Hatókör

**Benne van:**
- A közös `<nav id="fomenu">` blokk újratervezése és egységes cseréje mind a 8 HTML-oldalon.
- Az `index.html` átalakítása átirányításról valódi „Áttekintő" nyitóoldallá.
- Egy kis `docs/js/attekinto.js`, amely csak a „mai kiemeltet" tölti be.
- `docs/css/app.css` új, szűk blokkjai (`.fomenu-*`, `.attekinto-*`).
- e2e: új `e2e/attekinto.spec.js`, frissített `e2e/menu.spec.js`.

**Nincs benne (out of scope):**
- Backend-, workflow-, adatfájl-változás (SEMMI Python, SEMMI új adat).
- Az oldalak belső tartalmának átrendezése (az „egy oldalon túl sok" fájdalom külön kör).
- Oldalak összevonása alfülekbe (a „C" megközelítés — későbbi, önálló spec).

## Globális megkötések

- Tiszta statikus HTML + vanilla JS; a meglévő minták (fejléc-doboz, kártya-stílus, színek az
  `app.css`-ből). NINCS új külső függőség, NINCS build-lépés.
- `fetch` csak a nyitóoldal mai-kiemeltjéhez (`data/elemzes.json`), minden más statikus link.
- Fail-soft mindenhol: adat hiánya sosem töri az oldalt.
- Magyar UI-szövegek; tipográfiai idézőjel (`„…"`) HTML-szövegben, JS-stringben `„`/`”`
  (tanulság a Radar-körből: ASCII `"` lezárja a JS-stringet).
- Akadálymentesség: `aria-current="page"` az aktív linken, csoportok `aria-label`-lel.

## 1. Csoportosított navigáció

A mostani lapos sor helyett látható kategóriákkal, egyetlen kanonikus nav-blokk minden oldalon:

```
Áttekintő  │  ELEMZÉSEK: Napi · Heti · Havi  │  Radar  │  STATISZTIKÁK: Google · YouTube  │  Infó
```

**Sorrend és indoklás:** gradiens a feldolgozottság szerint — *következtetés → jelzés → nyers adat*:
Áttekintő → Elemzések (AI-narratíva) → Radar (értelmezett jelzések) → Statisztikák (nyers grafikon) → Infó.

**Tételek (link → cél):**

| Pozíció | Megjelenített név | Cél | Típus |
|---|---|---|---|
| 1 | Áttekintő | `index.html` | önálló link (home) |
| 2 | *ELEMZÉSEK* | — | kategória-címke (nem link) |
| 2a | Napi | `elemzes.html` | link |
| 2b | Heti | `heti.html` | link |
| 2c | Havi | `havi.html` | link |
| 3 | Radar | `bovites.html` | önálló link |
| 4 | *STATISZTIKÁK* | — | kategória-címke (nem link) |
| 4a | Google | `trendek.html` | link |
| 4b | YouTube | `youtube.html` | link |
| 5 | Infó | `adatokrol.html` | önálló link (mindig látható) |

**Névrövidítés:** a csoport-címke hordozza a kontextust, ezért a tételek rövidülnek
(„Napi Elemzések" → **Napi**, „Google Trendek" → **Google**). Az oldalankénti `<h1>`-ek a teljes
nevükön maradnak (pl. „Google Trendek – Mire keresnek rá Magyarországon?").

**DOM-szerkezet (vázlat):**
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
Az aktuális oldal `<a>`-ja kapja a meglévő `class="aktiv"` + `aria-current="page"` jelölést
(oldalanként a saját linkjén).

**Megjelenés:** a két `.fomenu-csoport` halvány, kis nagybetűs `.fomenu-cimke` felirattal és finom
elválasztóval a csoportok közt. A kategória-címke nem kattintható. Desktopon egy sor; mobilon a nav
tördel, a `.fomenu-cimke` a saját csoportja fölé kerül (a csoport `display` blokkszerűvé vált kis
kijelzőn).

## 2. „Áttekintő" nyitóoldal (`index.html`)

Az átirányítás helyett valódi oldal, a közös navval és láblécel. Felülről lefelé:

**a) Hero (fejléc-doboz):** cím + egymondatos leírás:
> „Trendfigyelő — mire figyel ma Magyarország? Napi, heti és havi AI-elemzések, radar-jelzések és
> nyers keresési statisztikák egy helyen."

**b) Mai kiemelt (`#attekinto-kiemelt`, dinamikus):** lásd a 3. szakaszt a pontos forrásért.
Tartalom: egy **vezető mondat** (a mód szerinti narratíva első mondata) + **3-5 felkapott szó** chipként
+ „Tovább a napi elemzéshez →" link (`elemzes.html`). Ha nincs adat: a teljes blokk kimarad (fail-soft).

**c) Három terület-kártya (`.attekinto-kartyak`, a gradiens-sorrendben):**

| Kártya | Leírás | Linkek |
|---|---|---|
| **Elemzések** | „Napi, heti és havi AI-összefoglalók arról, mi mozgatja a közbeszédet." | Napi `elemzes.html` · Heti `heti.html` · Havi `havi.html` |
| **Radar** | „Szokatlan elmozdulások, ügyek életútja és kapcsolódó keresések." | Radar `bovites.html` |
| **Statisztikák** | „Nyers keresési és YouTube-nézettségi grafikonok." | Google `trendek.html` · YouTube `youtube.html` |

**d) Infó-belépő (`.attekinto-info-sav`):** a kártyák alatt egy jól látható sáv:
> „Hogyan készül? Mit jelentenek az adatok? → Infó" (`adatokrol.html`)

Így az Infó a nyitóoldalon is jelen van, nem csak a navban.

## 3. „Mai kiemelt" adatforrása

A `docs/data/elemzes.json`-ban **nincs** egységes, reggel-este egyaránt kész „TL;DR" mező
(`valtozas.szoveg` reggel placeholder). A mindkét módban megbízhatóan meglévő mezők:
- `felkapott.top` — lista: `{kifejezes, volumen, novekedes_pct, temak, hirek}` (a legfelkapottabb szavak).
- `felkapott.reggel.szoveg` / `felkapott.este.szoveg` — mód szerinti rövid narratíva.
- `mode` — `"reggel"` vagy `"este"`.

**Kiválasztási logika (`attekinto.js`):**
1. **Vezető mondat:** a `mode`-nak megfelelő narratíva (`felkapott[mode].szoveg`) **első mondata**
   (az első `. ` / `! ` / `? ` határig). Ha az adott mód szövege hiányzik vagy placeholder
   (tartalmazza: „az esti futáskor" / üres), a másik mód szövegét próbáljuk; ha az sincs, a vezető
   mondat kimarad, csak a chipek jönnek.
2. **Chipek:** `felkapott.top` első **legfeljebb 5** eleme, a `kifejezes` mezőből.
3. Ha sem narratíva, sem `top` nincs → a teljes `#attekinto-kiemelt` blokk nem jelenik meg.

Az `attekinto.js` NINCS hatással más oldalra (csak az `index.html` tölti be). Nincs `new Date()`
(a mód és a nap az adatból jön).

## 4. Stílus és reszponzivitás

- A meglévő `app.css` dizájnnyelve (fejléc-doboz, kártya-radius, színek). Új blokkok:
  - `.fomenu-csoport`, `.fomenu-cimke`, `.fomenu-home`, `.fomenu-onallo` — nav-csoportosítás.
  - `.attekinto-hero`, `.attekinto-kiemelt`, `.attekinto-kartyak`, `.attekinto-kartya`,
    `.attekinto-info-sav` — nyitóoldal.
- Kártyarács: desktop 3 egy sorban (`grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))`),
  mobilon egymás alatt.
- Nav: desktop egy sor `flex`-szel; mobilon (`max-width: 640px`) tördel, a `.fomenu-cimke` a csoportja
  fölé kerül.

## 5. Hibatűrés

- Nyitóoldal mai kiemelt: `fetch` hiba / 404 / hiányzó mező → a `#attekinto-kiemelt` blokk üresen
  marad vagy kimarad; a hero, a 3 kártya és az Infó-sáv MINDIG megjelenik (statikus HTML).
- A navigáció teljesen statikus → nincs futásidejű hibalehetőség.

## 6. Tesztelés (Playwright e2e)

**Új `e2e/attekinto.spec.js`:**
- A nyitóoldal betölt; a hero cím, a 3 terület-kártya és az Infó-belépő látható.
- A mai kiemelt a mockolt `data/elemzes.json`-ból renderel: a vezető mondat + a top chipek
  megjelennek (reggel és este mock is).
- Fail-soft: `elemzes.json` 404 → a kiemelt kimarad, de a kártyák + Infó-sáv megvannak.
- A kártyák linkjei a helyes célra mutatnak (`elemzes.html`, `heti.html`, …, `adatokrol.html`).

**Frissített `e2e/menu.spec.js`:**
- A nav tartalmazza az „Áttekintő"-t és a két csoport-címkét (Elemzések, Statisztikák).
- Minden link célja helyes; a kategória-címkék NEM linkek.
- Az aktív oldal linkje `aria-current="page"`.

**Teljes suite:** a meglévő oldal-specek várhatóan érintetlenek (a link-célok nem változnak);
a teljes pytest + Playwright suite zöld kell legyen záráskor.

## 7. Rollout (fájlok)

| Fájl | Művelet |
|---|---|
| `docs/index.html` | átirányítás → valódi „Áttekintő" oldal |
| `docs/elemzes.html`, `heti.html`, `havi.html`, `trendek.html`, `youtube.html`, `bovites.html`, `adatokrol.html` | a `<nav id="fomenu">` blokk egységes cseréje (az aktív link oldalanként jelölve) |
| `docs/js/attekinto.js` | ÚJ — mai kiemelt betöltése |
| `docs/css/app.css` | ÚJ `.fomenu-*` + `.attekinto-*` blokkok |
| `e2e/attekinto.spec.js` | ÚJ |
| `e2e/menu.spec.js` | frissítés a csoportos navra |

## Nyitott kérdés (nincs blokkoló)

A „mai kiemelt" vezető mondata a mód szerinti narratíva első mondata lesz; ha a USER később mást
szeretne ott (pl. csak a top-3 szó, vagy az esti „mi változott" egy sora), az egy sor csere az
`attekinto.js`-ben.
