# Predikció-finomítás: órás-only hosszú táv + rövid-horizont láthatóság + infó — design

**Állapot:** jóváhagyott terv (chat), implementáció előtt.
**Dátum:** 2026-09-15.
**Előzmény:** [[predikcio-loess]] (LOESS-alapú előrejelzés, 5 horizont-gomb), [[oras-only-hosszu-ablak]].

## 1. Cél

A meglévő predikció-feature három konkrét finomítása (a lineáris/nemlin trend és a napi elemzés
ÉRINTETLEN, minden változás additív):

1. **Órás-only szavak (benzin, nyugdíj — nincs napi/heti soruk) ne kapjanak 3 hó / 1 év
   előrejelzést.** Egy pár hónapnyi órás pillanatkép-láncból egy évet előrejelezni nem megbízható.
   Helyette a kártya egy **őszinte üzenetet** ír ki ezekre a horizontokra.
2. **Az 1 nap / 1 hét előrejelzés jól látszódjon a chartokon.** Ma a chart a szó leghosszabb sorát
   (heti = 1 év) rajzolja, és a rövid előrejelzés parányi sáv a jobb szélen → **auto-zoom**: rövid
   horizontnál az x-tengely a közelmúltra szűkül, így a forecast kitölti a szélesség jó részét.
3. **A predikció számítása képletekkel az infó-oldalon** — a képletek már bent vannak
   (`adatokrol.html`); kiegészítjük az új viselkedésekkel.

## 2. Háttér — a jelenlegi működés

- `predikcio.sorozat_predikcio(pontok, lepes_mp, horizontok)` egy sorozatból kiszámolja a kért
  horizontok blokkjait (`pont`/`also`/`felso`/`rmse_veg`/`modszer`/`megbizhatosag`/`figyelmeztetes`).
  A horizont naptári: `H = nap · 86400 / lepes_mp` (felbontás-független). `n < 24` → `{}`.
- `regresszio.py` KÉT forrásból ír predikciót:
  - **elsődleges (órás):** `sorozat_predikcio(oras_pontok, 3600, mind az 5 horizont)` — az órás-only
    szavaknak ez az EGYETLEN forrás a hosszú horizontokra.
  - **másodlagos (napi/heti):** `sorozat_predikcio(heti|napi, 604800|86400, mind az 5)` — a teljes-
    nézettel AZONOS 0–100 skálán.
- **frontend-merge** (`app.js egyesitett_reg`): `Object.assign({}, elsődleges.predikcio, másodlagos.predikcio)`
  → a másodlagos (napi/heti) blokk FELÜLÍRJA az elsődleges (órás) azonos kulcsú blokkját.
- A chart (`app.js chart_letrehoz`, teljes-mód) az x-tengelyt a `[első mért pont … utolsó forecast pont]`
  tartományra illeszti (nincs padding). A rövid horizont forecastja emiatt a teljes szélesség
  parányi töredéke.

## 3. A megoldás

### 3.1 Órás-only 3 hó / 1 év → sentinel + üzenet (#1)

**Backend** (`regresszio.py`, elsődleges órás ág):
- Az órás sorozatból CSAK a `("1_nap", "1_het", "1_ho")` horizontokat számoljuk valós forecastnak.
- Ha van elég órás adat (a `sorozat_predikcio` NEM üres blokkot adott vissza), a `"3_ho"` és `"1_ev"`
  kulcsra egy **sentinel** blokkot írunk: `{"nem_becsulheto": True}`. (Kevés órás adatnál — üres
  eredmény — NINCS sentinel, mert ott a szó egyszerűen még nem becsülhető semmire.)
- A **másodlagos** (napi/heti) ág VÁLTOZATLAN: valós `3_ho`/`1_ev`-et számol. A merge ezt ráírja a
  sentinelre, ha a szónak van napi/heti sora → a sentinel CSAK az órás-only szónál marad meg.

**Frontend** (`app.js`):
- A merge (`egyesitett_reg`) VÁLTOZATLAN (a sentinel átmegy rajta; a másodlagos felülírja, ha van).
- `kartya_letrehoz`: a kiválasztott horizont nyers blokkját megvizsgáljuk. Ha `nem_becsulheto` igaz →
  NEM rajzolható blokk (nincs `pont`/`also`/`felso`), és a kártyára egy őszinte feliratot teszünk
  (új `<p class="predikcio-nem-becsulheto">`): pl. *„1 évre ezen a szón nem becsülhető megbízhatóan —
  csak órás mérés áll rendelkezésre, amiből ilyen hosszú távra nem adunk előrejelzést."* (a horizont
  ragozott neve behelyettesítve).
- A rajzoló ág (`chart_letrehoz`) csak akkor tolja ki a predikció-datasetet, ha VAN valós `pont` —
  a sentinel sosem kerül rajzolásra.

### 3.2 Rövid-horizont auto-zoom (#2)

**Frontend** (`app.js chart_letrehoz`, teljes-mód, x-tengely min/max számítás):
- A meglévő `x_min` (első mért pont) / `x_max` (utolsó forecast pont) mellett: ha van forecast ÉS a
  forecast jövő-szakasza **kicsi** a mért előzményhez képest — konkrétan
  `forecast_span < ARANY_KUSZOB · elozmeny_span` (kezdő javaslat `ARANY_KUSZOB = 0.25`) —, akkor az
  `x_min`-t a közelmúltra emeljük: `x_min = max(elso_mert, utolso_mert − ZOOM_SZORZO · forecast_span)`
  (kezdő javaslat `ZOOM_SZORZO = 4`, hogy a forecast ~20% szélesség legyen; implementáláskor
  élő-előnézeten hangoljuk, hogy a rövid előrejelzés kényelmesen látszódjon és legyen elég
  előzmény-pont a kontextushoz).
- Hosszú horizontnál (3 hó / 1 év: `forecast_span` nagy) a feltétel nem teljesül → NINCS zoom
  (a teljes előzmény látszik, mint eddig).
- CSAK a teljes-módú per-szó tengelyt érinti; a kategória-nézet és a lineáris/nemlin datasetek
  változatlanok. A rövid előzmény-ablak KITÖLTI a szélességet (a Chart.js a `min/max`-ra vág).

### 3.3 Infó-oldal (#3)

`docs/adatokrol.html` — az előrejelzés-szekció (a képletek MÁR ott vannak) kiegészítése:
- **Rövid vs. hosszú horizont felbontása:** a horizont naptári hossza a rajzolt sorozat felbontásán
  lépésekre vált; heti sorozaton az 1 nap és az 1 hét egyaránt a legközelebbi heti lépés.
- **Rövid horizont ráközelítés:** rövid horizont választásakor a chart a közelmúltra közelít, hogy a
  közeli előrejelzés jól látszódjon.
- **Miért nincs 3 hó / 1 év csak-órás adatból:** az órás-only szavaknál (nincs napi/heti soruk) a
  hosszú horizontot nem becsüljük — egy pár hónapnyi órás pillanatkép-láncból egy évet előrejelezni
  nem megbízható; ilyenkor őszinte üzenetet mutatunk forecast helyett.

## 4. Adat-séma változás

A predikció-blokk egy ÚJ, opcionális alakot kap: a szokásos
`{pont, also, felso, rmse_veg, modszer, megbizhatosag, figyelmeztetes}` MELLETT egy
**sentinel** alak: `{"nem_becsulheto": true}` (nincs `pont`/`also`/`felso`). A frontend a `nem_becsulheto`
jelenlétéből dönt (rajzol vs. üzenet). A `_ir_json` séma additív; a régi blokkok érintetlenek.

## 5. Tesztelés (TDD)

- **Backend** (`regresszio` / `predikcio`): az elsődleges órás ág elég adatnál `3_ho`/`1_ev` sentinelt
  (`nem_becsulheto: true`) ad, `1_nap`/`1_het`/`1_ho`-t valósat; kevés órás adatnál nincs sentinel; a
  másodlagos ág valós hosszú-horizontja a merge után FELÜLÍRJA a sentinelt (integráció-szintű
  ellenőrzés a merge-logikára — vagy frontend e2e-ben).
- **Frontend (e2e):** órás-only szó (csak órás predikció, sentinel a hosszúra) + 1 év horizont →
  a kártyán megjelenik a „nem becsülhető" üzenet, NINCS zöld predikció-görbe. Napi/heti szó 1 év →
  valós görbe (nincs üzenet). Rövid horizont (1 nap/1 hét) → a chart x-tartománya SZŰKEBB, mint a
  teljes előzmény (a forecast látható arányt tölt).
- **Infó-oldal:** a `test_pages` az új szövegek jelenlétét ellenőrzi (rövid-horizont zoom + órás-only
  hosszú táv „nem becsülhető").

## 6. Hatókörön KÍVÜL

- A rövid horizontok FINOMABB felbontású (órás/napi) forrásból rajzolása külön nézetben (a
  „finomabb sorozat" opció) — most az auto-zoom marad, a heti-only 1 nap ≈ 1 hét felbontás elfogadott.
- A predikció-számítás magja (`predikcio.py` LOESS/csillapított trend/backteszt) VÁLTOZATLAN.

## 7. Global Constraints (a specből, minden taskra kötelező)

- Tiszta numpy + meglévő SDK; **NULLA új Python-dependency**. Additív változások, MUTÁCIÓ=1.
- Frontend: NINCS `new Date()` / `Date.now()`. Backend tesztelt logikában NINCS argless
  `datetime.now()` / `seged.most_utc()`.
- Irreplaceable adat READ-ONLY (`kulcsszo_*`, `napok/*.json`).
- SOROS suite: `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`.
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással.
