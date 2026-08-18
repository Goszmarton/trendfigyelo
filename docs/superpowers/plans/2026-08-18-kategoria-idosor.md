# Terv — Kategória-idősor chart (jóváhagyva 2026-08-18, 2 kikötéssel + elhelyezés-módosítással)

Frontend/CSS kör, a canvas-érintő szelet SZEMLE-KÖTELES. A napi kategória-találatok IDŐSORA kategóriánként
egy vonalként, a meglévő egynapos oszlopdiagram MELLÉ (nem helyette). A bar = MA mi pörög; az idősor = HOGYAN
alakult — két külön kérdés.

## MÉRT alapok (a KATEGÓRIA-IDŐSOR mérési jelentésből, 2026-08-18)
- **Adat tárolódik + backup:** a kategória a `napok/<nap>.json` `trendek[].temak`-jában (`felkapott.py:26` = Google
  `topic_names` passthrough). `temak`-kulcs 2026-08-05-től. 26 napok-fájl + `kategoriak.json` git-követett.
- **Származtatott aggregátum kész:** `trendfigyelo/kategoriak.py` → `docs/data/kategoriak.json`, napi rekord
  `{nap, merve, lista_hossz, lista_kategoriaval, kategoria_nelkul, kategoriak:{Cat:count}}`. **Ez a chart forrása.**
- **Auto-frissül, külön lépés NEM kell:** `futtato.py` védetten hívja `kategoriak.kategoriak_ir()`-t (hiba sosem
  viszi el az adatmentést, de naplóz); `napi.yml:52` `git add docs/data` committolja.
- **Történet ma:** 12 nap (2026-08-05 … 2026-08-17), mind `merve:true`. **08-06 HIÁNYZIK** (FOLYT-lelet napja) →
  belső rés. Átlag 18,3 trend/nap, 20,2 kat-találat/nap.
- **Készlet MÉRVE (15, angolul):** Other 84 · Sports 42 · Law and Government 32 · Entertainment 28 · Politics 20 ·
  Business and Finance 14 · Jobs and Education 4 · Hobbies and Leisure 4 · Health 4 · Science 3 · Pets and Animals 3 ·
  Climate 1 · Technology 1 · Travel and Transportation 1 · Food and Drink 1. Other = 34,7%.
- **A 4 még-nem-látott** (a user 19-éből): Autos and Vehicles, Games, Shopping, Beauty and Fashion.
- **VÁLTOZÓ készlet:** új kategória a bázisnap UTÁN is jött (08-07 Jobs and Education; 08-08 Health, Hobbies and
  Leisure; 08-09 Pets and Animals; 08-12 Food and Drink, Travel and Transportation).
- **A `trend_szin` ma 2 színt ad** (Other=#9e9e9e, minden más = egyetlen kék #3366cc) → line-charthoz paletta kell.
- **A trend-blokk JS-épített** (index.html:33 üres section) → az új elemek a render-függvényben jönnek létre.

## Döntések (a user rögzítette, nem kérdezendő újra)
1. **Vonal-készlet ADAT-VEZÉRELT**, nem beégetett lista (nincs 6. rejtett kalibrált konstans). Vonal a feltűnéskor
   jelenik meg; a 4 nem-látott NEM kap lapos nulla-vonalat.
2. **Címkék ANGOLUL**, ahogy Google adja. Nincs magyar mapping.
3. **Mérték: DARABSZÁM** (napi kategória-találat).
4. **08-06 = LÁTSZÓ RÉS (null), nem összekötött vonal** (a rács-összefűzés-tilalom elve).
5. **Alapból bekapcsolt: a kumulatív top-5 az Other NÉLKÜL, SZÁMÍTVA** (ma: Sports, Law and Government, Entertainment,
   Politics, Business and Finance). Other + a többi kikapcsolva, egy kattintással behozható.
6. **A chart alatt a magyarázat marad** (egy trend több kategóriába tartozhat → az összeg > trendek száma) +
   „a kategória-adat 2026-08-05-től" (a dátum a `kategoriak.json` első napjából, nem beégetve).

## Elhelyezés (MÓDOSÍTVA: idősor FÖLÉ) — a trend-blokk sorrendje
1. **kategória-idősor chart (történet)** ← ÚJ, legfelül
2. napi oszlopdiagram (mai pillanatkép) ← MARAD, változatlan
3. magyarázó mondatok (kiegészítve a 08-05 megjegyzéssel)
4. trend-lista

## Backend: NINCS változás
A teljes adat megvan, auto-generált, auto-committed. Tiszta frontend kör. (Ha a szeleteknél ez megdől → STOP.)

## Szelet 1 — shaper + betöltés (canvast NEM érint, DOM-assertálható, NINCS szemle)
- `kategoriak.json` a trend-blokk fajl-listájába (OSZT `fajlok`).
- Tiszta függvény: `kategoriak.json → { napok:[ISO min..max, belső rések beszúrva], vonalak:[{nev, ertekek:[db|null], elso_nap}] }`.
  - **Naptár:** `[legkorábbi tükrözött .. legkésőbbi]`, belső hiányzó nap beszúrva (08-06). A szélek nem tágulnak.
  - **Vonal-készlet:** csak a legalább egyszer előfordult kategóriák (ma 15). A 4 nem-látott NINCS.
  - **Érték-szabály:** hiányzó nap → null (minden vonal); kategória első megjelenése ELŐTT → null; egyébként a
    darabszám, jelen-nap-0-előfordulás → VALÓS 0 (nem null). Ellenőrző: Pets and Animals null 08-05..08-08, 08-09 valós.
- A shaper eredménye DOM `data-*` tükörbe (repo-minta: `data-kategoriak`/`data-count`) → a null-rés / első-megjelenés /
  0-vs-null szabály DOM-assertálható, canvas nélkül.

**Szelet 1 RED (AssertionError, valós üzenetekkel):**
- `idosor-adat: a naptár-tengely tartalmazza a 08-06 rést, ott minden vonal null` → RED: hiányzó dátum / nem-null.
- `idosor-adat: Pets and Animals null 08-05..08-08, első valós érték 08-09` → RED: 0/hiány az első-megjelenés előtt.
- `idosor-adat: jelen-napon a 0-előfordulás VALÓS 0 (nem null)` → RED: null a 0 helyett.
- `idosor-adat: 15 vonal (a 4 nem-látott NINCS)` → RED: 19 vagy más szám.

## Szelet 2 — line-chart + legend + paletta + magyarázat (CANVAS → SZEMLE-KÖTELES)
- Chart.js **line**, dataset/kategória, `spanGaps:false`, y `beginAtZero`+`precision:0`, DARABSZÁM.
- **Default-látható = kumulatív top-5 Other nélkül, SZÁMÍTVA** a shaper adatából; a többi + Other `hidden:true`.
- **Legend `onClick`** = beépített dataset-toggle (Other/bármi egy kattintással).
- **Paletta:** kategóriánként külön, STABIL, **első-megjelenés szerint append-only** (új kategória a következő színt
  kapja, régiek nem csúsznak); Other mindig szürke. Kozmetika (túlcsordulásnál ciklizál, nem hallgat el), nem kalibrált.
- **Elhelyezés:** a napi oszlopdiagram FÖLÉ a trend-blokkban.
- **Magyarázat:** meglévő mondat + „A kategória-adat 2026-08-05-től érhető el (előtte nincs `temak`-kulcs)" (dátum adatból).

**Szelet 2 RED (DOM / data-* tükör):**
- `idosor-chart: canvas jelen + data-idosor-rendered="true"` → RED: nincs canvas/flag.
- `idosor-chart: pontosan 5 látható dataset ÉS az Other NEM látható ÉS a látható halmaz == a shaper-adatból SZÁMÍTOTT
  kumulatív top-5 (Other nélkül)` → RED: rossz hidden-halmaz. **KIKÖTÉS 1: a SZABÁLYT assertálja, NEM a mai névsort**
  (a mai konkrét névsor a jelentésben van, a tesztben nem — pár hét múlva drift-elne).
- `idosor-chart: kategóriánként KÜLÖN szín, Other=#9e9e9e` → **RED valódi** (ma a `trend_szin` egyetlen kék → a
  különböző-szín assert bukik, míg a paletta be nem kerül).
- `idosor-chart: a magyarázat tartalmazza a két mondatot + "2026-08-05"` → RED: hiányzó szöveg.

**Szándékos-zöld (SZANDEKOS-ZOLD-VAK, előre jelölve):**
- `a meglévő egynapos oszlopdiagram VÁLTOZATLAN (regresszió-őr)` — szándékos-zöld. **Fedés a Szelet 2 VÉGÉN MÉRVE**
  diszkriminátorral (az idősor-render ideiglenes elrontása NEM boríthatja a bar-teszt zöldjét kell hogy borítsa);
  **0 fedés → cserélem** élesített asszertre. Nem előre feltételezem.

## Mi CSAK SZEMLE (pixel, nem DOM-assertálható)
- A rés vizuálisan megszakad-e; a vonalak szét­válnak-e; a **15 szín elég kontrasztos-e** (KIKÖTÉS 2: ha nem, JELZEM,
  NEM tuningolok magamtól — lehet, hogy kevesebb alapból látható vonal a válasz, nem több szín); a top-5-default
  olvasható-e (nem spagetti); a legend-kattintás érzete.

## Szemle / zárás rend
Szelet 1 (RED→GREEN, nincs szemle) → Szelet 2 (RED→GREEN) → **EGY SZEMLE a végén, push ELŐTT**. grep MUTÁCIÓ==1 →
`git status docs/data` tiszta → commit (kód+teszt+leltár §11a, PARKOLT-sorral) → push KÜLÖN körben, rev-list 0 0.

## PARKOLT lelet (a záró commitba, nem dolgozom rajta)
**KATEGORIA-CIMKE-PASSTHROUGH** — `temak` a Google `topic_names` nyers átvétele (`felkapott.py:26`), kód-oldali
kanonikus lista NÉLKÜL → egy Google-átnevezés vagy 20. kategória némán új angol vonalként jelenne meg; a magyar
19-mapping nem fogná. ELMÉLETI, valós adaton 0 előfordulás. A chart ezért adat-vezérelt címkézést használ.

## Új tétel-kapu
Nem hoz adatvesztést/néma hibát (tiszta megjelenítés auto-mentett adatból). Ha implementáció közben ilyet találok →
STOP + jelzés. Egyéb lelet → PARKOLT sor, egy mondat.
