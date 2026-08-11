# Design — Esztétikai kör (Category A), Phase 3

**Dátum:** 2026-08-11
**Hatókör:** UI-CSS finomítás + EGY látható cím csere. NEM Task 10.
**Sorrend a munkarendben:** **A (ez) → Task 10 (rootMargin/mobil) → B (minden kártyán görbe) → Task 11 (fázis-zárás) → C (heti táblázat, spec-bővítés).**

## 0. Miért ELŐBB, mint a Task 10

Minden dobozmodell-változás (keret, árnyék, padding, szekció-elválasztó) eltolja a görgetési geometriát.
A Task 10 fő feladata a lusta-render `rootMargin`-ját a **végleges** magasságon hangolni (L10). Ha az esztétika
utána jönne, kétszer mérnénk. Ezért az A **mért** geometriai deltái (lásd §1.4) a Task 10 **bemenetei**.

## 1. A1 — kártya- és blokk-elkülönítés

### 1.1 Jelen állapot (mért/olvasott tény)
- Kártyák (`.trend-kartya`, `.kulcsszo-chart`): `1px solid #eee` keret (~1,09:1 fehéren → gyakorlatilag láthatatlan) + `radius 4px`.
- A két nagy blokk (`.szekcio`) között NINCS vizuális elválasztás, csak margó.

### 1.2 Terv
- **Kártyák:** keret `#eee → #d0d0d0` (finom, de látható) + `box-shadow: 0 1px 2px rgba(0,0,0,.06)`; `radius 4px` marad.
  Ugyanaz a `.trend-kartya` és `.kulcsszo-chart` szinten (konzisztens kártya-nyelv).
- **Szekció-elválasztó:** `.szekcio + .szekcio { border-top: 1px solid #e3e3e3; padding-top: 1.5rem; }`.
- **Vezérlősáv mint „sín":** `.vezerlo-sav { background:#fafafa; border:1px solid #e3e3e3; border-radius:6px; padding:.75rem; box-sizing:border-box; }`.

### 1.3 KÖVETELMÉNY: `box-sizing: border-box` a `.vezerlo-sav`-on (mérés indokolta)
A sáv `flex: 0 0 14rem` (content-box alap). `border-box` NÉLKÜL a `.75rem` padding + `1px` keret KIFELÉ nő → a sáv
14rem-ről ~15,6rem-re szélesedik, a 2-oszlopos rács tartalma szűkül, és **a desktop kártya −13px-t veszít szélességből**
(mérve). A `box-sizing: border-box` a paddinget BEFELÉ teszi → a sáv 14rem marad, a **kártya-szélesség delta 0** (mérve).
Ez NEM a jóváhagyott vizuális designt változtatja, csak a mellékhatását szünteti meg.

### 1.4 MÉRT geometria-delták (Category A1, a fenti értékekkel; eldobható e2e-diag, mint a 8b/96px)

Mérés: 4 valós trend-kártya (idősorral + kategóriával), `#trend-blokk` első kártya `boundingBox` + a szekció + a sáv,
`előtte` (jelen CSS) vs `utána` (A1 CSS injektálva), két nézetben. Kártya-box `előtte` magasság = 196px mindkét nézetben.

| Delta (utána − előtte) | Desktop 1280 | Column 380 |
|---|---|---|
| **Kártya-box magasság** | **+0px** | **+0px** |
| **Kártya-szélesség** (border-box-szal) | **+0px** | **+0px** |
| **Első trend-kártya viewport-top** | **+25px** | **+77px** |
| Vezérlősáv-magasság | +26px | +26px |

**Értelmezés:**
- **Kártya-magasság +0px:** a keret WIDTH-e változatlan (1px → 1px, csak SZÍN), a `box-shadow` festett, nem foglal layout-helyet.
- **Desktop első-kártya +25px** = a trend-szekció (2., alsó) saját `border-top 1px + padding-top 1.5rem(24px)`.
- **Column első-kártya +77px** = 26px (a kulcsszó-szekció sávja +26px → lejjebb tolja a trend-szekciót)
  + 25px (a trend-szekció saját border-top+padding-top) + 26px (a trend-sáv +26px, álló módban a tartalom FÖLÖTT).

**Task 10 bemenet (IDE tartozik, NEM itt oldjuk meg):** álló (≤900px) módban az első trend-kártya **+77px-rel lejjebb**
kerül. L10 kiindulása: az első kártya 750,7px-en, a `rootMargin:"400px"` zóna alja 720px-en (már 30px túl). A1 UTÁN a
`rootMargin`-t a **+77px-cel eltolt** geometrián kell újrahangolni — ezt a Task 10 végzi, ezekkel a számokkal.

## 2. A2 — gombok (kevésbé szürkék; a formai különbség MARAD)

### 2.1 Jelen állapot (olvasott tény)
- Intervallum-gombok (`#intervallum-vezerlo button`): NINCS explicit háttér/keret → a böngésző **natív szürke** gombja.
  Ez a „szürkeség" forrása. `aria-pressed=true → #e8e8e8`. Letiltott: `color:#999` (app.css:35, az EGYETLEN `#999`).
- Kategória-gombok (`.kategoria-gomb`): már fehér/kék **pill** (`border-radius:999px`) — NEM szürkék, a szándékos
  „Other"-gyűjtő-szürkét kivéve.

### 2.2 Terv
- **Intervallum-gomb:** explicit, szándékos stílus — `background:#fff; border:1px solid #ccc; border-radius:4px; color:#222`.
  **Szögletes marad (NEM pill)** → megőrzi a formai különbséget a kategória-pilltől. `aria-pressed=true → #e8e8e8` marad.
- **Letiltott intervallum-gomb:** `color:#999` helyett `background:#f0f0f0; color:#6b6b6b` (`cursor:not-allowed` marad).
  A világos háttér + közepes szöveg egyszerre **olvasható ÉS egyértelműen inaktív**.

### 2.3 Az a11y-indoklás (KÖTELEZŐEN a specben — nehogy a Task 10 a11y-köre „szabálysértésként" újranyissa)
- **Mérés:** `#999` fehéren = **2,85:1**. Ez numerikusan a WCAG AA normál (4,5:1) ÉS a nagy-szöveg (3:1) küszöb alatt van.
- **DE ez NEM 1.4.3-szabálysértés:** a WCAG 1.4.3 **kifejezetten kiveszi** az inaktív (letiltott) UI-vezérlőket a
  kontraszt-követelmény alól.
- **Akkor miért javítjuk?** Mert a letiltott intervallum-gomb **jelentést hordoz** („ez a táv még nem elérhető"),
  ezért **olvashatónak kell lennie**. A javítás indoka tehát **használhatóság/olvashatóság, NEM szabály-megfelelés.**
- **Új érték:** `#6b6b6b` a `#f0f0f0` háttéren ≈ **5:1** (olvasható). A cél nem egy küszöb „teljesítése", hanem
  hogy a letiltott állapot üzenete olvasható maradjon, miközben vizuálisan egyértelműen inaktív.

## 3. A3 — látható cím csere

### 3.1 DOM-szerződés (grep-elt tény)
`Napi legfrissebb trendek` él KIZÁRÓLAG `docs/index.html`-ben (33: `aria-label`, 34: `<h2>`). `e2e/` és `tests/`: SEHOL.
Az e2e a szekciókat `#trend-blokk` id-vel fogja (stabil); a trend-`h2` SZÖVEGÉRE ma NINCS assert (csak a
kulcsszó-`h2`="Kulcsszavak"-ra, `loader.spec.js:27`). → A látható cím cseréje NEM töri a szerződést.

### 3.2 Terv
- `docs/index.html` 33+34: **„Napi legfrissebb trendek" → „Ma felkapott keresések"** (rövidebb, párhuzamos a
  „Kulcsszavak"-kal, egy tiszta h2-sor).
- A `<h2>` ÉS az `aria-label` **is** cserélődik. Indok: az `aria-label` AT-felé MEGJELENŐ címke (nem belső id, mint a
  `#trend-blokk`); a láthatóval szinkronban tartása helyes a11y. Belső id/elnevezés érintetlen.
- **Miért kell a csere:** a másik blokk „Kulcsszavak"; ha mindkettő „…szó/trend"-del van megnevezve, a felhasználó
  ugyanannak hiszi őket. Pedig a kulcsszavak fix lista időben követve, a trendek a mai hirtelen keresések.

### 3.3 Regressziós őr (HELY FONTOS)
- Az új assert a **`trend.spec.js`-be** megy (NEM a `loader.spec.js`-be — az a betöltési hibaágat őrzi mockolt 404-gyel),
  a meglévők mellé, mint **T27**: `#trend-blokk h2` szövege == „Ma felkapott keresések" (szimmetrikus a meglévő
  „Kulcsszavak"-asserttel).
- **Fejléc-szám JAVÍTÁSA:** a `trend.spec.js` fejléce ma „22 db"-ot állít, DE ténylegesen **26 teszt van (T1–T26)** —
  a fejléc MÁR elavult (a T23–T26 „8b" tesztek nem frissítették). Ez pontosan az a hiba, ami korábban egy duplikált
  teszt-számot elrejtett. A T27 hozzáadásakor a fejléc **„27 db"-ra** javítandó (a teljes 22→26 sodródást is korrigálva),
  és a felsorolt taskok közé a „Task 7 + 8a"-hoz `+ 8b + A3-cím` illesztendő.

## 4. KIFEJEZETTEN JÓVÁHAGYOTT — NEM változtatható

- A **kategória-pill érintetlen** marad (formai különbség megőrizve).
- Az **intervallum-gomb szögletes** marad, csak explicit stílust kap (nem lesz pill).
- Az **„Other"-szürke szándékos**, marad (naming-discipline: az osztályon keresztül, nem számított szín).
- Az **`aria-label` és a `h2` együtt** cserélődik.

## 5. Tesztelés / regresszió

- **A3 cím:** valódi viselkedési őr (T27, §3.3), fejléc-szám javítással.
- **A2 letiltott olvashatóság:** MÉRLEGELENDŐ a tervben egy computed-style őr (a letiltott intervallum-gomb
  `color` == `rgb(107,107,107)`), hogy az a11y-motivált érték ne csússzon vissza némán. Ha bekerül, valódi
  diszkriminátorként (mutáció: az érték visszaállítása `#999`-re bukjon).
- **A1 kártya/szekció stílus:** tisztán vizuális (keret-szín, árnyék, padding). DOM-ból értelmesen nem assertálható
  (L9-korlát) → kézi szemle; a §1.4 mért geometria a bizonyíték, hogy a magasság nem nő.
- Kapuk: SOROS suite (`--workers=1`), a végén `grep -rn "MUTÁCIÓ" … == 1`, adat-commit nincs (tisztán kód/CSS).

## 6. YAGNI / hatókör-korlát

- Nincs egyéb refaktor. Nem nyúlunk a `rootMargin`-hoz (az a Task 10). Nem nyúlunk a kategória-pillhez, az „Other"-höz.
- A B (minden kártyán görbe) és C (heti táblázat) NEM ennek a körnek a része.
