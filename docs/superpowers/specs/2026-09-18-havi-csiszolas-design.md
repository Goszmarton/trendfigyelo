# Havi elemzés — csiszolás (megyehatárok + címek/infók + klaszter-kattintás + infó-szöveg + naptár-jelölő) — design

**Állapot:** jóváhagyott terv (chat), implementáció előtt.
**Dátum:** 2026-09-18.
**Előzmény:** [[havi-nlp-elemzes]] Fázis A+B (fül-újratervezés + térképek), [[predikcio-loess]] (infó-szöveg).

## 1. Cél — 6 finomítás (USER-kérés)

Round 1 (frontend/docs, kulcs NÉLKÜL). A Round 2 (havi generálás a hó utolsó napján, CI+kulcs) HATÓKÖRÖN KÍVÜL.

- **A) Megyehatárok**: a Magyarország-térkép alaprétege megye-GeoJSON (megyehatárok + finomabb forma).
- **B) Infó predikció-szöveg**: pontosítás + magyarosítás (a „csak az utolsó pontból" félreértés javítása).
- **C) NER-szekció címek + infó**: jobb címek, „(térkép)" törlése, kék-csíkos infó.
- **D) Személyek**: jobb cím + kék-csíkos infó (a volumen jelentése).
- **E) Klaszterek**: cím-átnevezés + a barchart-oszlopra kattintva ugrás a téma kártyájára + kék-csíkos infó.
- **F) Klaszter-kártya**: a szöveg (értelmezés) elöl, a tag-chipek utána.
- **G2) Napi naptár**: minden hó utolsó napján „Havi elemzés" jelölő → a Havi fülre ugrik.

## 2. B) Infó predikció-szöveg (a KÓD igazsága)

A `predikcio._szint_trend(sim, w=max(8, n//2))`: a **SZINT** `L = sim[-1]` (a LOESS-simított görbe utolsó
értéke — a közeli pontokból átlagolt szint, NEM a nyers utolsó adat); az **IRÁNY** `b` = az utolsó
`w = max(8, n//2)` pontra (a görbe **utolsó felére**, min 8 pont) illesztett egyenes meredeksége.

`docs/adatokrol.html` javítás:
- A téves mondat: „a b meredekség a sima (LOESS) görbe **utolsó néhány pontjára** illesztett egyenesé" →
  „…a görbe **utolsó feléből** (egy nagyobb szakaszából, legalább 8 pont) illesztett egyenesé" (egyezik a
  84. sori mondattal ÉS a kóddal).
- **Szint-vs-irány tisztázás**: kimondjuk, hogy a szintet a simított görbe utolsó értéke adja (ami már a
  közelmúlt pontjait tükrözi), az irányt pedig a görbe egy nagyobb szakasza — tehát **NEM egyetlen pontból**
  jósolunk.
- **Magyarosítás**: az „Előrejelzés – hogyan és meddig?" szakasz fogalmazásának csiszolása (gördülékenyebb,
  pontosabb magyar; a tartalom/mennyiség lényegében változatlan).
- `tests/test_pages.py`: a helyes szöveg jelen („utolsó feléből"), a téves nincs („utolsó néhány pontjára").

## 3. C/D/E) Címek + kék-csíkos infó-jegyzetek (`docs/js/havi.js` + `docs/css/app.css`)

**Kék-csík stílus reuse**: a `.mltrend-info`/`.predikcio-info` mintája (`border-left: 3px solid #3366cc;
padding: .3rem 0 .3rem .6rem; max-width: 40rem`). ÚJ `#havi-tartalom .havi-info` osztály ugyanezzel.

- **C) NER-szekció**:
  - A csoport-cím „Felismert entitások (NER)" → **„Országok és települések a havi keresésekben"**.
  - A világtérkép-szekció alcíme „Országok és külföldi városok (térkép)" → **„Havonta megjelent országok és
    nem-magyar települések a keresésekben"** (a „(térkép)" TÖRÖLVE).
  - A HU-térkép-szekció alcíme „Magyarországi települések (térkép)" → **„Havonta megjelent magyar települések
    a keresésekben"**.
  - **Kék-csíkos infó** a NER-szekció alatt (hosszabb): mit mutat (a havi keresőszavakban felismert
    ország-/település-nevek, gyakoriság/volumen szerint színezve/méretezve; a kattintás a kötött
    keresőszavakat mutatja; a nem-térképezhetők a lista alatt).
- **D) Személyek**: a szekció-cím „Személyek (leggyakoribbak)" → **„Megjelent személynevek a havi
  keresésekben"**; **kék-csíkos infó**: a sáv hossza = **volumen** (a személyhez kötött keresőszavak
  legmagasabb kereső-szintjeinek összege; „mennyi a legtöbb" = a leghosszabb sáv a legnagyobb figyelem).
- **E) Klaszterek cím**: „Témák (klaszterek)" → **„Tematikus besorolás"**; **kék-csíkos infó**: hogyan
  számolódik (a téma volumene = a téma keresőszavaihoz tartozó volumen-összeg; a sávra/kártyára kattintva…).

## 4. E) Klaszter-barchart oszlop-kattintás → kártyára ugrás (`docs/js/havi.js`)

- Minden klaszter-kártya kap egy azonosítót: `id = "havi-klaszter-" + slug(cimke)` (vagy adat-attribútum
  `data-klaszter-cimke`), a `klaszter_kartya`-ban.
- A klaszter-barchart Chart.js `options.onClick`: a kattintott elem indexéből → a rendezett `kSorolt[i].cimke`
  → a megfelelő kártya (`data-klaszter-cimke` egyezés) → `scrollIntoView({behavior:"smooth", block:"start"})`
  + rövid kiemelés (átmeneti CSS-osztály). NINCS `new Date()`.
- A barchart-oszlop kurzora „pointer" (jelezve a kattinthatóságot).

## 5. F) Klaszter-kártya sorrend (`docs/js/havi.js`)

A `klaszter_kartya`-ban: a **cím** (h3) után az **`ertelmezes` szöveg**, majd a **tag-chipek**
(`tag_lista(k.szavak)`), végül a domináns témák. (Jelenleg: chipek → szöveg; cél: szöveg → chipek.)

## 6. A) Megyehatárok (`docs/vendor/geo/` + `docs/js/havi.js`)

- **Vendor** (build-idő, hálózat elérhető): egy **Magyarország-megyék GeoJSON** — a Natural Earth
  `admin-1 states/provinces`-ból Magyarországra szűrve (`iso_a2=="HU"` / `admin=="Hungary"`), ~20 feature
  (19 megye + Budapest) → `docs/vendor/geo/hu-megyek.geojson` (kis fájl). A FORRAS.md + sha256-guard bővül.
  (Ha a 10m túl nagy a build-fetchhez, a 50m felbontás is elég a kontúrhoz.)
- **HU-térkép alapréteg**: a `hu_terkep`-ben a mostani ország-körvonal (a világ-GeoJSON HUN feature-e)
  HELYETT a `hu-megyek.geojson` betöltve `L.geoJSON(..., { interactive: false, style: {…megyehatár…} })`,
  `fitBounds` a megyékre. Fail-soft: ha a megye-asset nem tölt, marad a HUN-körvonal fallback (a mostani).

## 7. G2) Napi naptár „Havi elemzés" jelölő (`docs/js/app.js` naptar_epit + `docs/js/elemzes.js`)

- `naptar_epit` a `cellaAllapot(iso, szomszed)` visszatérésében kap egy opcionális `haviHonap` mezőt
  (`"YYYY-MM"`); ha jelen, a cellába egy kis **jelölő elem** (`<span class="nap-havi-jelolo" data-havi="YYYY-MM"
  title="Havi elemzés">` — pl. „H" vagy pötty) kerül. ADDITÍV: a trendek-fül cellaAllapotja nem ad haviHonap-ot
  → ott nincs jelölő.
- `elemzes.js`: a `cellaAllapot` a **hónap utolsó napján** (a saját hónap, nem szomszéd; `napok_a_honapban`
  determinista) `haviHonap: "YYYY-MM"`-et ad. A naptár delegált klikk-kezelőjében: ha a klikk a
  `.nap-havi-jelolo`-ra esett → `location.href = "havi.html?honap=" + data-havi` (a Havi fülre ugrás);
  különben a cella normál viselkedése (napi elemzés betöltése) VÁLTOZATLAN. NINCS `new Date()`.
- Kis CSS a jelölőnek (sarok-pötty/„H" badge).

## 8. Tesztelés (TDD)

- **A**: `tests/test_geo_assetek.py` bővül (`hu-megyek.geojson` létezik, FeatureCollection, >10 feature);
  e2e: a HU-térkép rétegei közt a megye-GeoJSON (több path).
- **B**: `tests/test_pages.py` — „utolsó feléből" jelen, „utolsó néhány pontjára" NINCS.
- **C/D/E-cím/F**: e2e (`havi.spec`): az új címek jelen; a klaszter-kártyán a szöveg a chipek ELŐTT; a
  kék-csíkos `.havi-info` szekciónként megvan.
- **E-kattintás**: e2e — a klaszter-barchartra kattintva a megfelelő kártya id-jére ugrik (a kártya láthatóvá
  válik / megkapja a kiemelő-osztályt).
- **G2**: e2e (`elemzes.spec`): a hónap utolsó napi cellája `.nap-havi-jelolo`-t kap `data-havi`-val; a
  jelölőre kattintva `havi.html?honap=YYYY-MM`-re navigál (a nem-utolsó napokon nincs jelölő).

## 9. Hatókörön KÍVÜL
- **Round 2 (G1)**: havi generálás a hó utolsó napján (CI/cron + `ANTHROPIC_API_KEY`).
- A backend `havi_nlp` LLM-mag, a `volumen`-dúsítás, a barchart-adatok VÁLTOZATLANOK.

## 10. Global Constraints
- Frontend: NINCS `new Date()`/`Date.now()`. Additív, MUTÁCIÓ=1.
- Futásidőben NINCS külső hálózat (a megye-GeoJSON vendorelt; a build-fetch kimenete a repóban).
- NULLA új Python-dependency. Irreplaceable adat READ-ONLY.
- SOROS suite: pytest + Playwright. `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással.
- A vendored assetek `docs/vendor/`-ba, FORRAS.md + sha256. A napi/trend/youtube fül egyéb része + a havi térkép-mag/barchartok/összegzés VÁLTOZATLAN (az érintett részeken kívül).
