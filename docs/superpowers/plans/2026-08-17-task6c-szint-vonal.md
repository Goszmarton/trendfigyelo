# 6c — tüntetés szint-vonal (esemény-jelző: medián szint-nézet, NINCS trendvonal)

Dátum: 2026-08-17
Előzmény: 6b LESZÁLLÍTVA (878547f, megismételt vizuális szemle 6/6). A 6c a
`tüntetés` (az egyetlen `esemenyjelzo`, n=1) üres állapotát cseréli le egy
tényleges SZINT-VONALRA. A döntés a spec §8 nyitott pontját zárja
(„a helyette rajzolt tartalom Task 6-ban dől el").

A terv 2026-08-16-án tervező-körben JÓVÁHAGYVA; ez a doc-commit rögzíti a
jóváhagyott, finomított formát, a friss (n=5) mérés utáni kapuszámmal. A kód
ezután, a doc-commit UTÁN indul (spec-eltérés → doc előre).

## A négy kérdés — MÉRVE (nem becsülve)

- **Q1 (szint bázisa): (a) FUTÁSIDEJŰ, rács-specifikus medián.** A backend
  `regresszio_masodlagos_szamit` a lezárt heti pontok mediánját számítja
  (`szint = statistics.median(lezart)`, `szint_modszer="median"`). MÉRVE a friss
  JSON-on: `tüntetés` szint = **8.0**, racs=het. Rács-specifikus (het=8,0 / órás=0,0)
  → NEM negyedik rács-vak konstans (szemben a MIN_PONT / irany_kuszob /
  ALAPNEZET-KONSTANS beégetett értékekkel).
- **Q2 (hatókör): típus-kapu, NEM szólista.** A mechanika `tipus == "esemenyjelzo"`
  config-vezérelt; a config-ban PONTOSAN 1 ilyen szó (`tüntetés`, racs=het). A
  másik 12 szónak trendvonala van, amit egy lapos medián meghazudtolna → nem
  általánosítjuk rájuk.
- **Q3 („stabil szint"): medián + IQR jellemzi, stdev NEM kapuz.** A stdev-et az
  esemény-csúcs felfújja (épp az a szó, amit meg akarunk fogni) → a stabilitás
  jelölésére nem gate. n=1-en áll (lentebb leltárba).
- **Q4 (ütközés az IRANY-KUSZOB-bel): ÉLŐ BUG, MÉRVE.** Ma a `tüntetés` 1_het-en
  az ÓRÁS ágon `ervenyes:true, irany:stagnal` (R²≈0,006, az illesztés-vonal
  3,20→−0,02-ra csúszik) → a spec §8 „trendvonal NEM készül" pontját SÉRTI. A 6c
  ezt a backendben elnyomja (nem a frontend maszkolja).

## Alapdöntés: szeleteléssel, NEM felülírással

Az `esemenyjelzo` SOHA nem kap trendvonalat; minden intervallumon szint-nézet a
cél — DE a het-rekordot a MÁR MEGLÉVŐ `_intervallumok` mechanika SZELETELI a
választott ablakra, NEM írjuk felül minden intervallumot ugyanazzal az 52 hetes
görbével. A felülírás ugyanaz a hiba-osztály, mint a 6b-ben elkapott nyaralás
1_ev: minden ablak ugyanazt rajzolná, az intervallum-választó no-op lenne, a
feliratok hazudnának — csak itt a GÖRBE HOSSZA hazudna (még nehezebben fogja
auto-teszt). Ahol a heti ablak túl rövid (< RACS_MIN_PONT[het]=7), a MÁR LÉTEZŐ
`rovid_het_ablak` felirat jelenik meg.

## Kapuszám — ÚJRAMÉRVE n=5-ön (a doc-commit feltétele, TELJESÜL)

A másodlagos rotáció n=4 → **n=5** (új: `kórház`, racs=het). Ezért a tegnapi
(n=4-es) kapuszámot újramértem a friss JSON-on. A `tüntetés` het-rekordját a
`_intervallumok` szeleteli; a heti ablak hetekben ⌊nap/7⌋:

| intervallum | 1_het | 2_het | 1_ho | 3_ho | 1_ev |
|---|---|---|---|---|---|
| hetek (het-rács) | 1 | 2 | 4 | 12 | 52 |
| tüntetés 6c után | rovid_het_ablak | rovid_het_ablak | rovid_het_ablak | **szint** | **szint** |
| RAJZOL összesen — 6c ELŐTT | 13 | 2 | 2 | 4 | 2 |
| **RAJZOL összesen — 6c UTÁN** | **12** | 2 | 2 | **5** | **3** |

A `tüntetés` kiesik az 1_het-ről (13→12), és megjelenik a 3_ho/1_ev szint-nézeten.
Az 1_het TOVÁBBRA IS az EGYEDÜLI maximum (12 vs. a következő 5) → az
**ALAPNEZET-KONSTANS NEM nyílik újra**. (A tegnapi n=4-es szám {1_het:12,
2_het:2, 1_ho:2, 3_ho:4, 1_ev:2} volt; a kórház másodlagosa a 3_ho-t 4→5-re, a
1_ev-et 2→3-ra emelte — a VERDIKT változatlan.) Az ALAPNEZET-KONSTANS indoklás
új száma: „1_het = 12/13".

## Routing helye: BACKEND (nem frontend)

A frontend-routing a JSON-ban `ervenyes:true, irany:stagnal`-t hagyna, amit a spec
§8 tilt, és a UI csak maszkolná — ez HARMADSZOR lenne ugyanaz a mintázat
(nincs_lancolas-fordítás, MASODLAGOS-OK-NEV után). A javítás a backendben:
az `esemenyjelzo` szó órás intervallumai `ervenyes:false, ok:"esemenyjelzo"`.

## Szeletek

### Szelet 1 — BACKEND routing + ok-réteg (auto-teszttel őrizhető)
- **Órás ág** (`regresszio_szamit`): az `esemenyjelzo` szóra a `_intervallumok`
  ELŐTT rövidre zár → minden órás intervallum `ervenyes:false, ok:"esemenyjelzo"`;
  **nincs** stagnal-trendvonal, **nincs** halott irany/meredekseg/R² számítás.
  (Ellenőrzendő és kimondandó: ma számol-e a backend ezen az ágon használatlan
  irany/meredekseg/R²/illesztes_vonal mezőt.)
- **Másodlagos ág** (`regresszio_masodlagos_szamit`): a het `_intervallumok`
  ADJA a szeletelést, DE a trend-mezők (irany/meredekseg/r2/**illesztes_vonal**)
  STRIPPELVE (különben a frontend `racs_epit` MÁSODIK, piros trendvonalat
  rajzolna a 2 végpontból); a `szint` szó-szinten marad.
- **Frontend** (`egyesitett_reg`): a het-esemenyjelzo 1_het/2_het/1_ho ágon
  `rovid_het_ablak` (a 184-es 1_het-ág kis igazítása); a „szint-nézet készül"
  OK_MAGYAR üzenet NYUGDÍJAZVA.

**TDD — Szelet 1 három RED (NÉVRE és HIBATÍPUSRA, viselkedésbeli):**
1. `test_esemenyjelzo_oras_intervallum_nem_ervenyes` (pytest, backend): a
   `regresszio_szamit` kimenetén `tüntetés` MINDEN órás intervalluma
   `ervenyes is False and ok == "esemenyjelzo"`. RED a mai kódon: a stagnal-ág
   `ervenyes:true`-t ad → **AssertionError** (`True is not False`).
2. `test_esemenyjelzo_masodlagos_nincs_trend_mezo` (pytest, backend): a
   `regresszio_masodlagos_szamit` `tüntetés` szeletelt intervallumain nincs
   `illesztes_vonal`/`irany`/`meredekseg`/`r2` kulcs, de a `szint` megvan. RED:
   ma a másodlagos ág `intervallumok`-ja `ervenyes:False, ok:"esemenyjelzo"`-t ad
   szeletelés NÉLKÜL (nincs per-ablak rekord) → **KeyError/AssertionError** a
   hiányzó szeletelt intervallumra.
3. `test_esemenyjelzo_het_rovid_ablak_felirat` (Playwright e2e): `tüntetés`
   kártya 1_het gomb ok-szövege „A heti rácson ez az ablak túl rövid", NEM
   „Eseményjelző — szint-nézet készül". RED: ma a régi OK_MAGYAR üzenet →
   **toContainText AssertionError**.

SZÁNDÉKOS-ZÖLD (előre jelölve): a 12 nem-esemenyjelzo szó órás/másodlagos útja
VÁLTOZATLAN; a `szint` mező értéke (8,0) VÁLTOZATLAN.

### Szelet 2 — rendering (VIZUÁLIS SZEMLE a záró kapu, §8.3/L9)
- A het sorozat + KONSTANS szint-vonal (`Array(n).fill(szint)`, NEM
  `illesztes_vonal` — az 2 végpontból rajzol, ez vízszintes).
- Felirat MINDIG a bázissal, a 3_ho-n is: **`szint: 8 (heti medián, 52 hét)`**.
- **`data-szint="8"`** attribútum a kártyán (az e2e a jelenlétet+értéket
  assertálja; a vonal maga canvas-belső → csak szemle őrzi, L9).

### Szelet 3 — IQR-sáv: KIMARAD (első körből).

### Szelet 4 — szemle + leltár (a záró commitban, a 2 megfigyeléssel).

## Szint-bázis: (a) szó-szintű 52-hetes medián
A backend már így számol (futásidőben); minden RAJZOLÓ intervallumon (3_ho és
1_ev) UGYANAZ a referencia-vonal (8,0), és a felirat MINDIG kimondja a bázist
(„heti medián, 52 hét"), a 3_ho-n is — nem a 13 hetes ablak mediánja.

## Spec-eltérés → ez a DOC-COMMIT (a kód ELŐTT)
- phase4-spec §8: a „trendvonal NEM készül" pont KITERJESZTVE — a helyette
  rajzolt tartalom = het sorozat + medián szint-vonal (rács-tudatosan szeletelve,
  rövid ablakon `rovid_het_ablak`).
- Az órás `esemenyjelzo`-elnyomás rögzítve: az órás ág `ervenyes:false,
  ok:"esemenyjelzo"` (a mai §8-sértő stagnal-trendvonal megszűnik).

## Leltárba a 6c záró commitjában (2 megfigyelés)
1. A szint-vonal FELTÉTEL NÉLKÜL rajzolódik `esemenyjelzo`-re; nincs ellenőrizve,
   hogy az alapszint lapos-e. Ma n=1 → nem ellenőrizhető. Ha egy jövőbeli
   esemenyjelzo szó alapszintje EMELKEDIK, a vízszintes vonal ELREJTI.
   Újramérési feltétel: a 2. esemenyjelzo szó megjelenése.
2. A „stabil szint" definíciója n=1-en áll — annak jelölve.
