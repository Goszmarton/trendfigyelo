# Áttekintő műszerfal — irány + trend-illeszkedés (design)

Dátum: 2026-08-20
Hatókör: **adatréteg (regresszió) + felület.** Új összesítő panel legfelülre,
és a hozzá szükséges új, leíró statisztikai mezők a regresszió-kimenetben.
NEM hatókör: a részletes szó-kártyák / chartok változtatása, új kulcsszó,
másodlagos szavak megjelenítése a panelen (csak a 13 elsődleges + a `tüntetés`
medián-ága).

## 1. Cél

Egy **látványos, gyorsan olvasható összefoglaló** az oldal tetején, amely
minden elsődleges kulcsszót a **kategóriájával** (domén) csoportosítva mutat,
és két kérdésre válaszol egy pillantásra:

1. **Merre tart most?** — nő / stagnál / csökken, ikonnal.
2. **Kiugró-e a mai nap?** — a mai érték illeszkedik-e a trendhez, vagy a
   szokásosnál távolabb van tőle.

A `tüntetés`-nél (és minden `esemenyjelzo`-nál) nincs trend; ott a „kiugró"
a **mediántól** való eltérést jelenti.

## 2. Vezérelvek (a projektből, kötelező)

- **A frontend NEM SZÁMOL.** Minden új szám (reziduum, szokásos ingadozás,
  illeszkedés-állapot) a **backendben** dől el, a regresszió-JSON-be íródik;
  a frontend csak megjeleníti. (Mint az `illesztes_vonal`, `irany` eddig.)
- **Nincs hamis tekintély.** A jelző **leíró**, nem szignifikancia-teszt.
  A szöveg sosem mond „szignifikáns"-at vagy „anomáliá"-t; a sáv-szorzó
  dokumentált és konzervatív. (Naming-discipline: megfigyelés ≠ ok; ahogy az
  `irany` „iránya csökkenő", nem „Csökken", és az R²-legenda a skálát írja le,
  nem ítéli meg.)
- **Látható, nem néma.** Hiányzó mező / kevés pont → a jelző kimarad, nem
  kitalált érték; a szó attól még megjelenik azzal, ami van.
- **Adat-relatív, nem falóra.** A „mai" = a szó **legfrissebb LEZÁRT valós
  pontja** (nem a rendszeróra, nem részleges slot) — összhangban a
  retenció-horgony (MINOR-2) és a frissesség-felirat elvével.

## 3. A „kiugró" mérce — leíró kétállapot-sáv (①)

Két üzemmód, a szó típusa szerint.

### 3.1 Trend-alapú szavak (`szintmero`, `hibrid`)

Az illesztés helyén (`regresszio.py::regresszio_egy_ablak`) már megvan a
meredekség (`b`), a metszet és az összes felhasznált pont. Ezekből:

- `mai_reziduum` = az utolsó felhasznált (lezárt, nem részleges) valós pont
  értéke − az illesztett egyenes értéke ugyanazon időpontban. Relatív pont,
  előjeles (pozitív = a trend fölött).
- `reziduum_szokasos` = a reziduumok szokásos szórása az ablakon. **MAD**
  (median absolute deviation) — robusztus a kiugró pontokra, nem az a
  torzított `se_meredekseg`, amit a felület szándékosan nem ír ki. Ha < 2
  felhasznált pont vagy a szórás nem értelmezhető → `null`.
- `illeszkedes` = leíró állapot:
  - `"illeszkedik"` ha `reziduum_szokasos` érvényes ÉS
    `|mai_reziduum| ≤ SAV × reziduum_szokasos`;
  - `"tavolabb"` ha `reziduum_szokasos` érvényes ÉS a fenti nem teljesül;
  - `null` ha nincs elég adat (nem találunk ki állapotot).

`SAV` = dokumentált konzervatív állandó, **1,5** (a modul tetején nevesített
konstans, a spec-hivatkozással). NEM szignifikancia-küszöb; a választás
tudatosan kerek, óvatos, és a JSON `megjegyzes`-e kimondja, hogy leíró.

### 3.2 Szint-alapú szavak (`esemenyjelzo`, pl. `tüntetés`)

Ezeknek nincs trendje (az elsődleges regresszióban minden intervallum
`ervenytelen`, `ok: esemenyjelzo`); a **szint = medián** a másodlagos ágban
(`regresszio_masodlagos_szamit`, jelenleg `tüntetés.szint = 8,0`,
`szint_modszer: "median"`). Ott, a szint mellé:

- `mai_szint` = a legfrissebb lezárt szint-érték (a szint-idősor utolsó pontja).
- `mai_elteres` = `mai_szint − szint` (a mediántól való eltérés, előjeles).
- `szint_szokasos` = a szint-értékek szokásos szórása (MAD a mediánhoz).
- `illeszkedes` = ugyanaz a kétállapot-logika, de a **mediánhoz** mérve
  (`|mai_elteres| ≤ SAV × szint_szokasos`).

## 4. Felület

### 4.1 Elhelyezés

Új `<section id="attekinto-blokk" aria-label="Áttekintő – mai irány és trend">`
a `<main>` tetején, a `#kulcsszo-blokk` ELÉ. A meglévő blokkok és a lusta
canvas-rajzolás változatlan.

### 4.2 Szerkezet

- Kategóriánként (`DOMEN_SORREND` sorrend, `DOMEN_MAGYAR` felirat; `null` →
  „Egyéb" a végén) egy alcím + egy **kártya-rács** (CSS grid, reszponzív,
  `max-width:100%`, vízszintes túlcsordulás tiltva).
- Kártyánként egy szó:
  - **irány-ikon**: `▲` novekszik / `▬` stagnal / `▼` csokken; visszafogott
    szín (zöld / szürke / tompa piros — NEM riasztó élénk piros). Az ikon a
    CSS-ből jön (nem a szövegbe kézzel írt karakter), a meglévő ⓘ-mintához
    hasonlóan.
  - **szó** + a mai érték + az `IRANY_MAGYAR` leíró irány-szó.
  - **illeszkedés-jelző**: `✓` „illeszkedik a trendhez" / `⚠` „a szokásosnál
    távolabb a trendtől" (semleges sárga a ⚠-nál, nem piros). `tüntetés`-nél a
    szöveg „a megszokott szint körül" / „a megszokottnál távolabb a mediántól".
  - `illeszkedes === null` → nincs jelző (üres, nem kitalált).
  - `esemenyjelzo` → **nincs irány-nyíl**, csak a szint + medián-eltérés.

### 4.3 Őszinte keretezés (ⓘ-doboz)

A panel tetején egy magyarázó `ⓘ`-doboz a **meglévő közös mintában**
(`border-left: 3px solid #3366cc` + `::before { content: "ⓘ " }`, dőlt,
`#555`). Új szelektor csatlakozik a közös szabályhoz (app.css:139-151),
így bájt-azonos a többivel. Szövege kimondja:

> Ez számolt, leíró jelző: a mai érték eltérése a szokásos ingadozáshoz mérve —
> NEM szignifikancia-teszt. A tüntetésnél a mediántól való eltérés.

## 5. Peremesetek (nem hazudunk adatot)

| Eset | Viselkedés |
|---|---|
| Intervallum `ervenytelen` / < 2 pont | irány, ha van; **nincs** illeszkedés-jelző |
| `irany` hiányzik (`esemenyjelzo` elsődleges) | nincs nyíl; csak szint + medián-eltérés |
| `illeszkedes === null` | a jelző kimarad, a kártya megmarad |
| Hiányzó mező a JSON-ban | a frontend **kihagyja** az adott jelzőt (nem dob) |
| `domen === null` | „Egyéb" csoport, a lista végén |
| Ismeretlen `irany` érték | látható nyers érték (mint a `? <érték>` minta), nem néma default |

## 6. Tesztelés (a szokásos kapuk)

### 6.1 Backend (pytest, SOROS)

- `regresszio_egy_ablak`: szintetikus pontokból (ismert egyenes + ismert
  eltérésű utolsó pont) várt `mai_reziduum`, `reziduum_szokasos` (MAD),
  `illeszkedes` mindkét állapotra (a sáv alatt/fölött); < 2 pont → `null`.
- `regresszio_masodlagos_szamit` (`tüntetés`-ág): ismert szint-sorból várt
  `mai_szint`, `mai_elteres`, `szint_szokasos`, `illeszkedes`.
- RED→GREEN, egy VISELKEDÉST jósoló named teszt, egy mutáció.

### 6.2 Frontend (Playwright)

- A panel legfelül renderel; kategória-csoportosítás és -sorrend helyes.
- Irány-ikon a három `irany`-értékből; a két illeszkedés-állapot szövege.
- `esemenyjelzo` → nincs nyíl; a medián-eltérés szövege.
- Az ⓘ-doboz jelen van, a közös mintában.
- Peremeset: `illeszkedes: null` → nincs jelző (nem kitalált állapot).

### 6.3 Kapuk

Teljes SOROS suite zöld; `git status --short docs/data/` TISZTA; MUTÁCIÓ=1
körönként; leltár a záró commitban; DOC-COMMIT a kód előtt.

## 7. Nyitott / szándékosan kizárt

- A `SAV = 1,5` **leíró választás**, nem statisztikai küszöb — a JSON
  `megjegyzes` és az ⓘ-doboz ezt kimondja. Későbbi finomítás lehet, de nem
  ebben a körben.
- A másodlagos (heti cellás) szavak panelre vétele **kizárva** (a felhasználó
  a 13 elsődlegest + `tüntetés`-t kérte).
- Kategória-szintű aggregált állapot (pl. „Munkaerőpiac összességében csökken")
  **kizárva** — a legtöbb kategóriában 1-2 szó van, keveset adna.
