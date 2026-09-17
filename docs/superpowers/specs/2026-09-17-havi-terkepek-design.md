# Havi elemzés — FÁZIS B: interaktív térképek (világ choropleth + Magyarország-település) — design

**Állapot:** jóváhagyott terv (chat), implementáció előtt.
**Dátum:** 2026-09-17.
**Előzmény:** [[havi-nlp-elemzes]] Fázis A (fül-újratervezés, `volumen`-dúsítás; az országok/települések most listák).

## 1. Cél

A „Havi elemzés" fülön az **Országok** és **Települések** listát cseréljük **két interaktív Leaflet-térképre**:
1. **Világtérkép** (#6+#7-fele): az országok **volumen szerint színezve** (choropleth) + a **külföldi városok** kör-jelölőként.
2. **Magyarország-térkép** (#7): a **magyar települések** kör-jelölők volumen szerint.

**USER-döntések:** volumen-alapú szám (Fázis A-ból) · **interaktív mapping-lib (Leaflet)** · külföldi városok a
világtérképre pontként · **egy SDD** (közös vendor) · **hover-tooltip + pan/zoom + kattintás = kiemelés**
(a kötött keresőszavak — `szavak` — megjelenítésével).

## 2. Adat (már megvan — Fázis A)

`ner.orszagok[i]`, `ner.telepulesek[i]` mind `{nev, szavak:[korpusz-szavak], volumen:int}`. A térképek ezt
olvassák; **backend nem változik**. A név→geo illesztés a vendored lookupokkal történik (3. szakasz).

## 3. Vendorelt geo-assetek (a hálózat elérhető — igazolt)

Egy **vendor-építő lépés** (build-idő, NEM futásidejű; a subagent fetcheli+konvertálja, majd a kimenetet
vendoreljuk `docs/vendor/`-ba; futásidőben nincs külső hívás, NINCS csempe-szerver):

- **Leaflet** `1.9.4`: `leaflet.js` + `leaflet.css` → `docs/vendor/leaflet/`. (A default marker-képeket kerüljük:
  `L.circleMarker`-t használunk, nincs kép-asset.)
- **Világ-országhatár GeoJSON**: a `world-atlas` `countries-110m.json` (TopoJSON, ~108 KB) → GeoJSON-ná
  konvertálva (build-időben, pl. `topojson-client`/`ndjson`-cli vagy egyenértékű; a KIMENET GeoJSON kerül
  vendorelésre, futásidejű topojson-dep NÉLKÜL) → `docs/vendor/geo/vilag-orszagok.geojson`. A feature-ök
  ISO-kóddal (numerikus ISO 3166-1 vagy ISO3) azonosítottak.
- **Magyar országnév → ISO** lookup: `docs/vendor/geo/orszag-nev-iso.json` = `{"Németország":"DEU", …}` — a
  choropleth-illesztéshez (magyar entitásnév → GeoJSON-feature ISO). Közkincs ISO-lista magyar nevekkel;
  ~200 ország. A nem-illeszthető ország a fallback-listába kerül (5. szakasz).
- **HU-település → koordináta**: `docs/vendor/geo/hu-telepules-koord.json` = `{"debrecen":[47.53,21.62], …}`
  — a **GeoNames HU** (letölthető, igazolt 200) populated-places kivonatából (név KISBETŰS kulcs, a korpusz
  szavaival egyeztethető). Ez dönti el, mely „település" magyar (van koordinátája) vs külföldi.
- **Külföldi város → koordináta**: `docs/vendor/geo/varos-koord.json` = `{"moszkva":[55.75,37.62], …}` —
  a felmerülő + gyakori világvárosokra (GeoNames cities1000/cities5000 kivonat, magyaros nevekkel bővítve
  ahol kell: Moszkva, Kijev, Brüsszel, Porto…).

Minden lookup **kisbetűs, ékezet-érzékeny kulcs** a korpusz-szavakhoz igazítva; a name-matching a
telepulesek/orszagok `nev`-ét normalizálja (kisbetű, trim) a kulcshoz.

## 4. Frontend (`docs/havi.html` + `docs/js/havi.js` + `docs/css/app.css`)

- **havi.html**: Leaflet `leaflet.css` a fej-részbe, `leaflet.js` a `js/havi.js` ELÉ.
- **Világtérkép** (az Országok-lista helyére): `#havi-vilag-terkep` konténer. Leaflet-térkép, `L.geoJSON`
  a világ-országokkal; a **choropleth**: minden ország feature `fillColor`-ja a hozzá tartozó
  `orszagok[].volumen`-ből (magyar-név→ISO→feature; a nincs-adat ország halvány/üres). Szekvenciális szín-
  skála (világos→sötét). A **külföldi városok** `L.circleMarker`-ek a `varos-koord`-ból (a `telepulesek`
  azon elemei, amelyek NEM magyarok = nincs `hu-telepules-koord` találat), sugár/szín a `volumen`-ből.
  **Hover-tooltip**: `nev + " · volumen: " + volumen`. **Kattintás**: kiemelés (vastagabb határ/kiemelt szín)
  + egy oldalsó/alsó dobozban a kötött `szavak` felsorolása.
- **Magyarország-térkép** (a Települések-lista helyére): `#havi-hu-terkep` konténer. Leaflet-térkép
  Magyarországra centrálva/zoomolva; a **magyar települések** (`hu-telepules-koord` találat) `L.circleMarker`-ek
  volumen szerint méret/szín; hover-tooltip + kattintás=kiemelés+`szavak` (mint fent). A külföldi települések
  ide NEM kerülnek.
- **Fail-soft**: ha a Leaflet nincs betöltve (`typeof L === "undefined"`) VAGY a geo-asset nem elérhető →
  a térkép helyén a Fázis A-beli **volumen-lista** jelenik meg (a `ner_csoport` megtartva fallbackként).
- **NINCS `new Date()`/`Date.now()`.** A Chart.js-barchartok (személyek, klaszterek) VÁLTOZATLANOK.

## 5. „Semmi nem vész el csendben" (grounding + akadálymentesítés)

Minden térkép alatt egy tömör **lista/caption**: a térképen NEM megjeleníthető nevek (nincs koordináta/
ISO-match) felsorolva a volumennel — így egyetlen entitás sem tűnik el a listáról-térképre váltással. Ez
egyben a képernyőolvasó-alternatíva (a Leaflet-canvas/SVG önmagában nem elég). A már-megjelenítettek is
elérhetők szövegesen (a kattintás-kiemelés dobozában, ill. egy összecsukható teljes listában).

## 6. Tesztelés (TDD)

- **Vendor-build**: a lookupok betölthetők és nem üresek; a GeoJSON érvényes; determinista (a vendorelt
  fájlok a repóban — a build egyszeri, a teszt a vendorelt fájlok jelenlétét/alakját ellenőrzi).
- **Frontend (e2e, `havi.spec`):** mockolt `havi_nlp/<honap>.json` (volumennel) + a vendored geo-assetek →
  a `#havi-vilag-terkep` és `#havi-hu-terkep` Leaflet-térkép létrejön (`.leaflet-container`); van legalább
  egy színezett ország ÉS legalább egy kör-jelölő; a magyar település a HU-térképen, a külföldi város a
  világtérképen; kattintásra megjelennek a `szavak`; a nem-illeszthető nevek a fallback-listában.
  Fail-soft: Leaflet nélkül a volumen-lista látszik.
- A meglévő havi tesztek (reorg, barchartok, naptár) VÁLTOZATLANUL zöldek (a személy/klaszter rész érintetlen).

## 7. Hatókörön KÍVÜL
- Idősoros/hó-hó térkép-animáció; megye-szintű HU-choropleth; a `varos-koord`/`hu-telepules-koord` teljes
  világ-/HU-lefedettsége (elég a felmerülő + gyakori nevek; a hiány a fallback-listában látszik).
- A backend `havi_nlp` LLM-mag, a `volumen`-dúsítás (Fázis A) VÁLTOZATLAN.

## 8. Global Constraints (a specből, minden taskra kötelező)
- **Futásidőben NINCS külső hálózati hívás** (a geo-asset vendorelt; nincs csempe-szerver, nincs CDN-fetch).
  A vendor-build fetchel (build-idő), de a KIMENET a repóban.
- **NULLA új Python-dependency** (a vendorelés JS/CLI-eszközökkel vagy egyszeri szkripttel, nem a pipeline-ban).
- Frontend: NINCS `new Date()`/`Date.now()`. Additív, MUTÁCIÓ=1.
- A vendored Leaflet/geo assetek a `docs/vendor/`-ba, a `vendor/FORRAS.md` mintájára forrás-dokumentálva.
- Irreplaceable adat READ-ONLY. SOROS suite (pytest + Playwright).
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással.
- A napi elemzés / trendek / youtube fül + a havi barchartok/összegzés/klaszterek VÁLTOZATLANOK.
