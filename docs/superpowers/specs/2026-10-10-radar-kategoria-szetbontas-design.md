# Radar nagykategória szétbontása 3 önálló oldalra + idősáv-jelzés — terv

**Dátum:** 2026-10-10
**Típus:** architekturális (nav-átszervezés + egy oldal szétbontása 3 önálló oldalra)
**Állapot:** jóváhagyásra vár

## Cél (egy mondat)

A mostani egyetlen „Radar" fül (3 belső alfüllel) helyett a **RADAR** egy valódi nav-nagykategória
legyen (mint az ELEMZÉSEK), alatta **3 önálló oldallal** — Változások / Ügyek / Kapcsolódó —, és
mindegyik oldal tetején jól látható **idősáv-jelzés** mutassa, milyen időtartományt fed.

## Szándék és háttér (a közös megértés rögzítése)

- **USER-felvetés:** a Radar eddig egyetlen fülként a két címkézett csoport (ELEMZÉSEK / STATISZTIKÁK)
  közé ékelődött, és egy utólagos „JELZÉSEK" csoportcímke egy tételre redundáns volt. A USER ragaszkodik a
  „Radar" névhez → a **RADAR** legyen maga a többtételes nagykategória, így a redundancia megszűnik.
- **USER-kérés 2:** derüljön ki, **melyik Radar-aleszköz milyen időtartományt** használ (eloszlatja a
  „ez most napi/heti/havi?" bizonytalanságot).
- **Döntés (jóváhagyott):** 3 KÜLÖN oldal (nem egy oldal mélylinkekkel); NINCS külön „áttekintő" fül;
  semmit nem viszünk át más fülre (a 3 eszköz a Radar alatt marad).
- **Siker-kritérium:** a nav-ban a RADAR 3 önálló, linkelhető füllel jelenik meg; mindegyik oldal
  önmagában betölt és működik; mindegyik tetején ott az idősáv-jelzés; a backend/adat/workflow
  VÁLTOZATLAN; a meglévő render-logika újrahasznosítva (nem újraírva).

## Hatókör

**Benne van:**
- A közös `<nav id="fomenu">` blokk frissítése mind a 8 oldalon: a mostani egy „Radar" tétel helyett
  egy `RADAR` `.fomenu-csoport` 3 linkkel.
- 3 ÚJ oldal: `docs/valtozasok.html`, `docs/ugyek.html`, `docs/kapcsolodo.html`.
- `docs/bovites.html` → átirányítás a `valtozasok.html`-re (régi link/bookmark grace).
- `docs/js/bovites.js` init-je oldal-érzékennyé válik (a render-függvények újrahasznosítva); az
  alfül-váltó logika (`bov_alful_valt`/`bov_alfulek_kot` + panel-kezelés) kiesik.
- Minden oldal tetején idősáv-jelzés (`.radar-idosav`).
- Nyitóoldali „Radar" kártya 3 linkje a 3 új oldalra.
- Infó-oldal „A Radar fül" szekció frissítése (3 önálló eszköz).
- `docs/css/app.css`: `.radar-idosav` + (ha kell) kis nav-finomítás.
- e2e: menu.spec frissítés; a `bovites.spec.js` 3 per-oldal specre bontása; nyitooldal.spec kártya-linkek;
  `tests/test_pages.py` ha hivatkozik bovites.html-re.

**Nincs benne (out of scope):**
- Backend/Python/workflow/adatfájl változás (SEMMI).
- A render-függvények belső logikájának átírása (csak újrahasznosítás).
- A `#bovites-*` szekció-id-k és `.bovites-*` CSS-osztályok átnevezése (belső nevek maradnak).
- Új elemzési tartalom/feature.

## Globális megkötések

- Tisztán frontend; a `#bovites-*`/`.bovites-*` belső nevek változatlanok (csak a látható feliratok + a
  fájl-/oldal-szerkezet változik).
- `fetch` csak a saját JSON-hoz oldalanként; fail-soft mindenhol.
- Magyar UI; tipográfiai idézőjel HTML-ben `„…"`, JS-stringben `„`/`”`.
- `aria-current="page"` az aktív linken; a nav-csoportok `aria-label`-lel.
- NINCS `new Date()` a frontend-JS-ben (az időpontok az adatból).

## 1. Navigáció (mind a 8 oldalon)

```
Áttekintő │ ELEMZÉSEK: Napi·Heti·Havi │ RADAR: Változások·Ügyek·Kapcsolódó │ STATISZTIKÁK: Google·YouTube │ Infó
```

A mostani `RADAR`/`Radar` blokk (a 449bf50 commitban `.fomenu-csoport` „Jelzések" + 1 Radar link, ill.
korábban `.fomenu-onallo`) helyére:

```html
<div class="fomenu-csoport" aria-label="Radar">
  <span class="fomenu-cimke">Radar</span>
  <a href="valtozasok.html">Változások</a>
  <a href="ugyek.html">Ügyek</a>
  <a href="kapcsolodo.html">Kapcsolódó</a>
</div>
```

- 10 `<a>` link összesen (Áttekintő·Napi·Heti·Havi·Változások·Ügyek·Kapcsolódó·Google·YouTube·Infó) + 3
  `<span class="fomenu-cimke">` (Elemzések, Radar, Statisztikák).
- Aktív-jelölés: a `valtozasok.html`/`ugyek.html`/`kapcsolodo.html` oldalakon a megfelelő linken
  `class="aktiv" aria-current="page"`.
- Mobil: a nav tördel (meglévő `@media (max-width:640px)` szabályok a csoportra).

## 2. A 3 önálló oldal

Mindhárom a meglévő oldal-sablont követi (fejléc-doboz + `<main>` + lábléc), a közös navval, és a
MEGLÉVŐ `#bovites-*` szekció-id-ket használja, hogy a render-függvények változatlanul működjenek.

### 2.1 `valtozasok.html` — Szokatlan változások
- `<h1>Szokatlan változások</h1>`, `<p class="halvany" id="bovites-fejlec">`
- **Idősáv-jelzés** (`.radar-idosav`): „Aktuális kiugrások — a szavak szokásos szintjéhez képest ·
  számítva: <elmozdulas.szamitva_utc>". (Nincs fix naptári ablak; a „mióta tart" kártyánként marad.)
- Leíró doboz (a mostani `.bovites-leiras` szövege a szokatlan változásokról).
- `#bovites-szuro-elm` (szakpolitika-chipek) + `#bovites-elmozdulas` (tartalom).
- Adat: `data/elmozdulas.json`.

### 2.2 `ugyek.html` — Ügyek életútja
- `<h1>Ügyek életútja</h1>`
- **Idősáv-jelzés:** „Gördülő 30 napos ablak: <ugyek.ablak.kezdet> – <ugyek.ablak.veg>
  (<ugyek.ablak.nap> nap)".
- Leíró doboz (ügyek).
- `#bovites-szuro-ugy` (szakpolitika-chipek + rendezés) + `#bovites-ugyek` (tartalom).
- Adat: `data/ugyek.json`.

### 2.3 `kapcsolodo.html` — Kapcsolódó keresések
- `<h1>Kapcsolódó keresések</h1>`
- **Idősáv-jelzés:** „Naponta frissül · utolsó: <kapcsolodo.frissitve>".
- Leíró doboz (kapcsolódó + a Top/Felfutó számok magyarázata).
- `#bovites-kapcsolodo` (tartalom).
- Adat: `data/kapcsolodo.json`.

### 2.4 `bovites.html` → átirányítás
A `bovites.html` tartalma meta-refresh redirect a `valtozasok.html`-re (régi link/bookmark grace).

## 3. JS (`docs/js/bovites.js`) — oldal-érzékeny init

A meglévő render-függvények (`bov_elmozdulas_render`, `bov_ugyek_render`, `bov_kapcsolodo_render`,
`bov_szakpolitika_epit`, `bov_rendezes_epit`, `bov_idovonal`, `bov_kapcs_*`) és az `bov_allapot`
VÁLTOZATLANOK. Az `bov_init` helyére **oldal-érzékeny init** kerül:

- Megállapítja, melyik oldalon van: a jelenlévő tartalom-konténer alapján
  (`#bovites-elmozdulas` → Változások; `#bovites-ugyek` → Ügyek; `#bovites-kapcsolodo` → Kapcsolódó).
- CSAK a saját JSON-ját tölti (`bov_json(...)`), kitölti a `.radar-idosav` jelölőt a megfelelő
  mezőből, felépíti a saját vezérlőit (Változások: szakpolitika; Ügyek: szakpolitika + rendezés;
  Kapcsolódó: nincs), és meghívja a saját render-függvényét.
- Az alfül-váltó (`bov_alful_valt`, `bov_alfulek_kot`, panel `hidden` kezelés) és a 3-az-egyben
  `bov_rajzol` TÖRLÉSRE kerül; helyette per-oldal `bov_rajzol_<nézet>()` (vagy a meglévő render-fn
  közvetlen hívása az állapot-szinkronnal).
- Fail-soft: hiányzó JSON → a tartalom-szekció „nem érhető el" üzenete (a render-fn már kezeli), az
  idősáv-jelző kimarad; az oldal váza marad.
- NINCS `new Date()`.

## 4. Nyitóoldal (`docs/index.html`)

A „Radar" kártya címe marad „Radar". A benne lévő egyetlen „Radar megnyitása" link helyett **3 link**:
Változások (`valtozasok.html`) · Ügyek (`ugyek.html`) · Kapcsolódó (`kapcsolodo.html`). A kártya
leírása maradhat, vagy rövid felsorolás.

## 5. Infó-oldal (`docs/adatokrol.html`)

A „A Radar fül" szekció frissül: a 3 eszköz immár 3 önálló oldal; a szövegben az idősávok is
megjelenhetnek. A meglévő `.adat-doboz`/`.adat-csoport` szerkezet marad; a menu.spec elvárt
csoport-címe („A Radar fül") a tényleges új címre frissül.

## 6. Stílus (`docs/css/app.css`)

- `.radar-idosav`: kis, jól látható jelölő a H1 alatt (pl. halvány háttér, kerekített, ikon-szerű), a
  meglévő dizájnnyelvben.
- A nav a meglévő `.fomenu-*` szabályokkal működik (a RADAR csoport ugyanúgy, mint a másik kettő);
  a 449bf50-ben hozzáadott egytételes megoldás helyére a 3-tételes csoport kerül.

## 7. Hibatűrés

- Oldalanként: a saját JSON hiánya → a render-fn „nem érhető el" üzenete + az idősáv-jelző kimarad;
  a fejléc, a leírás és a nav mindig megjelenik.
- `bovites.html` redirect: statikus meta-refresh, nincs futásidejű hibalehetőség.

## 8. Tesztelés (Playwright e2e + pytest)

- **`e2e/menu.spec.js`:** a nav most 10 `<a>` + 3 `.fomenu-cimke` (Elemzések, Radar, Statisztikák);
  a RADAR 3 linkje helyes célra mutat; a 3 új oldal aktív-jelölése; a nav-sorrend tömb frissül. A
  „landing" és a többi oldal tesztje érintetlen (a saját aktív-szövegük).
- **A `e2e/bovites.spec.js` szétbontása 3 specre:** `e2e/valtozasok.spec.js`, `e2e/ugyek.spec.js`,
  `e2e/kapcsolodo.spec.js` — oldalanként: a tartalom renderel, a szűrő/rendezés működik (ahol van), az
  **idősáv-jelzés** megjelenik a mockolt JSON megfelelő mezőjéből, és fail-soft (404). A sub-tab-váltó
  tesztek kiesnek. (Fájlnév-ellenőrzés: e három spec-név szabad.)
- **`e2e/nyitooldal.spec.js`:** a „Radar" kártya 3 linkje a 3 új oldalra.
- **`tests/test_pages.py`:** ha hivatkozik `bovites.html` tartalmára, frissül a redirectre; ha a nav
  horgonyokat ellenőrzi, a 3 új oldal felvételre kerül.
- Teljes pytest + Playwright suite zöld záráskor (a `kulcsszo.spec` pre-existing flake kivételével).

## 9. Rollout (fájlok)

| Fájl | Művelet |
|---|---|
| `docs/elemzes.html`, `heti.html`, `havi.html`, `trendek.html`, `youtube.html`, `adatokrol.html`, `index.html` | nav-blokk: a Radar-rész → RADAR csoport 3 linkkel |
| `docs/valtozasok.html`, `docs/ugyek.html`, `docs/kapcsolodo.html` | ÚJ oldalak |
| `docs/bovites.html` | → redirect a `valtozasok.html`-re |
| `docs/js/bovites.js` | oldal-érzékeny init; alfül-logika törlés; render-fn-ek újrahasznosítva |
| `docs/css/app.css` | `.radar-idosav` |
| `docs/adatokrol.html` | „A Radar fül" szekció frissítés |
| `docs/index.html` | a Radar-kártya 3 linkje |
| `e2e/menu.spec.js` | nav 10 link + 3 címke + új oldalak |
| `e2e/bovites.spec.js` → `valtozasok/ugyek/kapcsolodo.spec.js` | per-oldal tesztek + idősáv |
| `e2e/nyitooldal.spec.js` | kártya-linkek |
| `tests/test_pages.py` | bovites.html redirect / nav horgonyok (ha érintett) |

## Nyitott kérdés (nincs blokkoló)

A „Változások" idősáv-szövege „Aktuális kiugrások…" — ha a USER fix ablakot szeretne ott is, az egy
szöveg-csere. A nav-szélesség 10 fülnél desktopon rendben, mobilon tördel.
