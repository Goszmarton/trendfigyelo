# Vendorolt eszközök — forrás és integritás

A `docs/vendor/` alatti fájlok külső eszközök **pinelt** másolatai. Minden fájlhoz
egy gépi sor tartozik (relatív útvonal + sha256), amit a `tests/test_pages.py`
`vendor_integritas_ellenorzes` guardja őriz: a fájl tényleges sha256-jának egyeznie
kell az itt rögzítettel, és nem lóghat sem listázatlan fájl, sem hiányzó bejegyzés.

## chart.js 4.5.1 (MIT)

- Csomag: `chart.js`, verzió: **4.5.1**
- Fájl: `chartjs/chart.umd.js` (a tarball `package/dist/chart.umd.js` tagja)
- Méret: 208 518 bájt (~204 KB)
- Licenc: **MIT**
- Tarball: https://registry.npmjs.org/chart.js/-/chart.js-4.5.1.tgz
- Tarball sha512 (npm registry `dist.integrity`, letöltéskor egyeztetve):
  `sha512-GIjfiT9dbmHRiYi6Nl2yFCq7kkwdkp1W/lp2J99rX0yo9tgJGn3lKQATztIjb5tVtevcBtIdICNWqlq5+E8/Pw==`

**Őszinte korlát:** a fenti registry-integrity a **kiadott tarballt** pinneli (a
szállítási csatorna, az npm registry attesztációja), **nem** a Chart.js szerzőinek
kriptográfiai aláírása. A letöltött tarball sha512-je bájtra egyezett ezzel az
értékkel; ebből a **verifikált** tarballból bontottuk ki a fájlt, és annak sha256-ja
szerepel a gépi sorban (ezt őrzi a guard). Adapter nélkül vendoroljuk (kategória-tengely,
magyar címkék előre formázva); a date-adapter + date-fns nincs vendorolva.

`chartjs/chart.umd.js` — sha256: `ecc3cd1eeb8c34d2178e3f59fd63ec5a3d84358c11730af0b9958dc886d7652a`

## Leaflet 1.9.4 (BSD-2-Clause)

- Csomag: `leaflet`, verzió: **1.9.4**
- Fájlok: `leaflet/leaflet.js`, `leaflet/leaflet.css`
- Forrás: https://unpkg.com/leaflet@1.9.4/dist/leaflet.js , https://unpkg.com/leaflet@1.9.4/dist/leaflet.css
- Licenc: **BSD-2-Clause**
- Marker-kép (PNG ikon) NINCS vendorolva — a tervezett térképek `circleMarker`-t
  használnak, nincs szükség a Leaflet alapértelmezett marker-image-ekre.

`leaflet/leaflet.js` — sha256: `db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a`
`leaflet/leaflet.css` — sha256: `a7837102824184820dfa198d1ebcd109ff6d0ff9a2672a074b9a1b4d147d04c6`

## Világ országhatár GeoJSON — johan/world.geo.json (közkincs / public domain)

- Fájl: `geo/vilag-orszagok.geojson`
- Forrás: https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json
- Licenc: **közkincs / public domain** (a repó CC0-hoz hasonló feltétellel terjeszti,
  eredetileg a Natural Earth adatból származik, ami szintén közkincs)
- Alak (futásidőben olvasott, PINELT kulcs): `FeatureCollection`, 180 feature;
  **minden feature top-level `id` mezője az ISO3 országkód** (pl. `"id": "HUN"`),
  `properties.name` az angol országnév (pl. `"Hungary"`). A letöltött fájl
  ellenőrzötten ezt az alakot adja (nem `properties.iso_a3`/`ISO_A3`) — a Task 2
  (magyar országnév → ISO → feature-illesztés) erre a top-level `id`-ra
  illeszkedik.

`geo/vilag-orszagok.geojson` — sha256: `bc2356a26a2976f98e4aaf1b24c5693d5a4dc9b6178aeb952dbafbcd42c73bcd`

## Magyar országnév → ISO3 — i18n-iso-countries (MIT)

- Csomag: `i18n-iso-countries` (npm), build-időben futtatva (`node -e ...`), NEM
  kerül a projekt `package.json`/`requirements.txt`-jébe — csak a generált
  statikus JSON-t vendoroljuk.
- Fájl: `geo/orszag-nev-iso.json` = `{"<magyar országnév kisbetűs>": "<ISO3>"}`
- Generálás: `i18n-iso-countries` HU-lokál `getNames("hu")` + `alpha2ToAlpha3`
  konverzió, kisbetűsítve.
- Licenc: **MIT**
- 250 bejegyzés; ellenőrizve: `"magyarország"` → `"HUN"`, `"németország"` → `"DEU"`
  — mindkettő megegyezik a `vilag-orszagok.geojson` feature `id`-jével.

`geo/orszag-nev-iso.json` — sha256: `f9b58618a6d5678772e0dcc12fdea4ddc6178777eb767f9e9813a99d8a89a213`

## Magyar települések koordinátái — GeoNames HU dump (CC-BY 4.0)

- Forrás: https://download.geonames.org/export/dump/HU.zip (`HU.txt`)
- Licenc: **CC-BY 4.0** (GeoNames)
- Fájl: `geo/hu-telepules-koord.json` = `{"<magyar településnév kisbetűs>": [lat, lon]}`
- Szűrés: `feature class` = `P` (populated place); azonos nevű találatok közül a
  legnépesebb (`population` oszlop) marad meg.
- 13 471 bejegyzés; ellenőrizve: `"debrecen"` → `[47.5317, 21.6244]`.

`geo/hu-telepules-koord.json` — sha256: `69f01dacfc4a5f448b839fced1829ef7ae33dd45b23ceb1b34e07c1c7723371c`

## Külföldi városok koordinátái — curált magyar exonima-lista

- Fájl: `geo/varos-koord.json` = `{"<magyar városnév/exonima kisbetűs>": [lat, lon]}`
- Eredet: kézzel curált seed-lista (a felmerülő trend-kulcsszavakban várható
  külföldi városnevek magyar exonimával), koordináták közismert/nyilvános
  földrajzi adatok — nincs harmadik féltől átvett fájl, nincs licenc-kötöttség.
  Bővíthető listaként kezelendő (Task 2+ igény szerint egészítheti ki).
- 30 bejegyzés, köztük a próza által elvárt `moszkva`, `kijev`, `brüsszel`, `porto`.

`geo/varos-koord.json` — sha256: `718b6e0959f4568ea71ae1d1aff932943cde8002b92767883324fb0f074b382e`

## Magyar megyehatárok — Natural Earth admin-1 (public domain / CC0)

- Forrás: https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson
  (Natural Earth admin-1 states/provinces, 10m felbontás)
- Licenc: **közkincs / public domain** (Natural Earth minden adata CC0-ként terjeszthető)
- Fájl: `geo/hu-megyek.geojson` = `FeatureCollection`, csak `geometry` + `properties.name`
  (megyenév) — a letöltött ~40MB teljes admin-1 fájlból Magyarországra szűrve
  (`properties.iso_a2 == "HU"` VAGY `admin == "Hungary"` VAGY `adm0_a3 == "HUN"`), majd
  `properties.type` alapján csak a valódi megyehatárokra (`"Megye"` + a főváros `"Fovaros"`) —
  a Natural Earth 10m adatban a megyei jogú városok (`"Megyei jogu város"`) külön
  feature-ként is szerepelnek, azokat kihagytuk, hogy a réteg a 19 megye + Budapest
  körvonalát adja, ne aprózódjon tovább.
- 20 feature (19 megye + Budapest), ~70 KB.

`geo/hu-megyek.geojson` — sha256: `90747320b8af6fe42f6c7c1427c3dbed6dd3f07602a473f806cd3be887b3996c`
