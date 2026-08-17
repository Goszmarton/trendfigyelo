# Phase 3 — Specifikáció: interaktív honlap

Állapot: **vázlat, jóváhagyásra vár**
Dátum: 2026-07-31
Előzmény: Phase 1 (adatréteg), Phase 2 (közzététel + automatizálás) és
**Phase 2.5 (szóló kulcsszó-mérés) lezárva**, a mainre mergelve `e8ac032`.
Ez a dokumentum a 2026-07-26-i v1 spec **felülvizsgálata**: a v1 a Phase 2.5
befejezése előtt készült, és a kulcsszó-réteget használhatatlannak minősítve
kizárta a hatóköréből. Ez már nem áll.

---

## 0. Mi változott a v1 óta

| v1 állítás | v2 állapot | Forrás |
|---|---|---|
| „A kulcsszó-réteg jelenlegi tartalma használhatatlan; ez a fázis nem próbálja megjeleníteni" | **Érvénytelen.** A szóló mérés él, első éles nap 2026-07-30 | Phase 2.5, Task 8 jegyzőkönyv |
| 7.4 kulcsszó-görbe **FAGYASZTVA** | **Kinyílik**, és a v1-nél lényegesen nagyobb hatókörrel | jelen spec 7.2 |
| A kulcsszó-adat forrása `legfrissebb.json` → `kulcsszavak` | Mellé lép a **`kulcsszo_nyers.json`** (7 napos órás nyers sorozat) — a v1 írásakor még nem létezett | Phase 2.5 Task 6 |
| 1.1 pillanatkép-táblázat (07-26) | Elavult; a **szerkezeti** megállapítások érvényben | jelen spec 1.2 |
| Nincs `modszertan_valtas` fogalom | A törésponti marker él, értéke `"2026-07-30"` | Phase 2.5 Task 7 |
| Dátumválasztó egyetlen vezérlő | **Kettéosztva**, szemantika szerint | jelen spec 7.1 |
| Kulcsszó-görbe = egy napi görbe | **Kulcsszavanként külön chart + regresszió + intervallum** | jelen spec 7.2 |

Ami a v1-ből **változatlanul érvényes**, és ide nincs újra bemásolva, csak
hivatkozva: az 5. fejezet teszt-politikája, a 6. fejezet háromrétegű
tesztstratégiája, a kategória-kezelés három állapota (7.1), a hírek
kép nélküli megjelenítése, a cache-busting, és a 3. fejezet nem-céljainak
nagy része.

---

## 1. Kiindulás

### 1.1 Architektúra-adottság

GitHub Pages, statikus kiszolgálás, nincs backend. Minden megjelenítés
kliensoldali JavaScript. A `docs/index.html` ma 32 soros, JS-mentes statikus
placeholder, amelyet a `tests/test_pages.py` őriz — ennek átírása (Task 1)
minden további frontend-munka előfeltétele. A fájl **két** tesztet tartalmaz:
`test_index_html_js_mentes` a JS-tiltó invariáns (nincs `<script`, nincs
`javascript:`, nincs inline `on…=` handler) — ezt írja át az 5. fejezet; a
`test_index_html_letezik_es_hivatkozik_az_adatra` a `Trendfigyelő` címet, a
`data/…json` href-eket és a `"Phase 3"` szöveget várja — utóbbi hármat a valós
dashboard váltja ki, tehát Task 1 ezt a tesztet is átszabja.

### 1.2 Az adatréteg mai állapota

Négy publikált JSON, két külön időszemantikával:

| Fájl | Tartalom | Felbontás / ablak | Láncolódik? |
|---|---|---|---|
| `legfrissebb.json` → `top_trendek` | napi felkapott trendek + `idosor` | 8 perc, `now 1-d`, 180 pont/trend | **nem** |
| `legfrissebb.json` → `trend_idosorok` | ugyanaz más alakban (15 sorozat × ~180 pont ≈ ~2705, futásonként ingadozik) | 8 perc, `now 1-d` | **nem** |
| `legfrissebb.json` → `kulcsszavak`, `kulcsszo_osszesites` | a nap kulcsszó-metszete, `atlag`/`csucs` | napi aggregátum | — |
| `kulcsszo_nyers.json` | **kulcsszavanként nyers órás sorozat** | 1 óra, `now 7-d`, 169 pont/szó | **ez a láncolás bemenete** |
| `napok/YYYY-MM-DD.json` + `index.json` | trend-archívum | napi | csak előre nő |
| `tortenet.json` | kulcsszó-történet, nap-kulcsú | napi | visszafelé is nő (visszapótlás) |

Mért tények a 2026-07-30-i első éles szóló futásból (run `30578843096`):

- **Minden kulcsszó sorozata a saját maximumára normalizált** — mind a 12
  kiírt szó pontosan eléri a 100-at. Ugyanez igaz a 15 trend-idősorra.
- Az órás rács hiánytalan, duplikátum nélkül; minden időbélyeg **tz-aware
  UTC** (`+00:00`).
- **Egy futáson belül az `ablak_veg_utc` minden szónál azonos**, mert a
  trendspy órahatárra igazít — a közös perem **szerkezeti**, nem a futás
  rövidségének következménye. A `kulcsszo_nyers.json` mára **halmozódó**
  (`nyers_kimenet.ir_gordulo`), ezért az akkumulált fájlban **futásonként egy**
  perem van, nem globálisan egyetlen; a fenti „minden szónál azonos" az első,
  egyszeri szóló futásra volt szó szerint igaz. A szerződés ezt futásonként
  őrzi: minden `ablak_veg_utc`-hez **pontosan egy** `ablak_kezdet_utc` tartozik,
  és a `(kezdet, veg)` párok száma a megtartott napok nagyságrendjében marad
  (nem szó×nap). A láncolás „közös perem" feltevése ezért — futáson belül —
  tartható.
- Szavanként pontosan a záró órás pont `reszleges: true` (a Trends `isPartial`
  oszlopából); sehol máshol.
- A `trend_idosorok` pontjain **nincs** `reszleges` mező — tudatos
  aszimmetria, mert ez az út nem láncolódik (lásd 1.4).

### 1.3 A két tartomány szerkezeti eltérése

A v1 1.1 megállapítása **változatlanul érvényes**, és a szerződés-teszt
rögzítse: a `tortenet.json` csak **teljes budapesti napokat** tart, ezért
előre egy napot lemarad; a `napok/index.json` csak előre nő. A lyuk mérete
állandó, az átfedés a felhalmozódással nő. **Ez nem hiba** — enélkül valaki
később „javításból" eldobja a legújabb trendlistát vagy a legrégebbi
kulcsszónapokat.

Konkrét igazolás 2026-07-31-én: a `tortenet.json` 9 napot tart (07-21…07-29),
a 07-30 azért nincs benne, mert a futás 20:22 UTC = 22:22 CEST-kor a 07-30 még
folyó nap volt. A 07-30 a 07-31-i futással kerül be a visszapótlás révén.

### 1.4 Normalizálási szemantika — a fázis legfontosabb korlátja

Három különböző normalizálás él egy oldalon, és ezek **soha nem
összemérhetők**:

1. **Kulcsszó-sorozat** (`kulcsszo_nyers`): minden szó a saját `now 7-d`
   lekérdezésén belüli maximumához viszonyítva 0–100.
2. **Trend-idősor**: minden trend a saját `now 1-d` napi maximumához.
3. **`volumen`**: abszolút, de durva — a 2026-07-23-i (egyetlen megfigyelt)
   futásban HÉT szint fordult elő: 100 / 200 / 500 / 1000 / 2000 / 5000 /
   10000 (a 20000 egyszer sem), és **string típusú**. Ez EGY futás mérése — a
   szintek száma és értékei futásonként változhatnak, ne általánosíts belőle.
   A `novekedes_pct` szinte mindenütt `"1000"`, azaz felső korlát, nem mérés →
   **használhatatlan**.

Ebből következik a fázis egyik alapszabálya, amely már a README-ben is
rögzítve van: **a kulcsszavak pontszámai egymással nem összemérhetők; közös
horgony nélkül rangsort (pl. „legnépszerűbb kulcsszó") nem képezünk.**

**Egy lekérdezésen belül viszont a skála konzisztens.** Ez a v2 kulcsfelismerése:
a `kulcsszo_nyers` egyetlen napi pillanatképe 169 órás pontot, azaz **7 teljes
napot** fed le, egyetlen normalizálás alatt. Ezen a hét napon belül a
sorozat alakja, iránya és meredeksége **értelmezhető** — láncolás nélkül is.

#### 1.4.1 Ablak-relatív újranormálás — a harmadik mechanizmus (MEGFIGYELÉS)

Az azonos naptári órához tartozó pontszám **futásról futásra változhat**, és ez
NEM azonos két korábban ismert jelenséggel: nem az órás jitter (a Google enyhe
zaja), és nem a kigördülés (a 7 napos ablak elejéről kieső órák). Egy **harmadik**
mechanizmus is működik, amit 2026-08-13-án pontról pontra megmértünk:

- **A mérés:** két egymást követő nap `now 7-d` lekérdezésének **71 átfedő
  órájából 69 bájt-azonos**; a 2 eltérő pont **pontosan a régi ablak csúcsai**.
- **A megfigyelt viselkedés:** a `now 7-d` minden pontszámot **az adott lekérdezés
  ablakán belüli maximumhoz** normál 0–100-ra. Amikor az új ablakba a réginél
  **nagyobb valós csúcs** kerül (a tegnapelőtti max, 08-08T01:00 = 100, kigördült,
  és az új ablakban magasabb csúcsok jelentek meg), a régi **al-csúcsok relatív
  értéke lecsökken**, a legkisebbek **0-ra kerekednek**. A `tüntetés` 5→2 esete
  ennek a keveréke volt (kigördülés + újranormálás), nem jitter.

**A megfogalmazás szándékosan MEGFIGYELÉST rögzít, nem okot:** azt mondjuk ki, MIT
mértünk (átfedő pontok viselkedése), nem azt, hogy a Google belső algoritmusa
pontosan hogyan dönt. A gyakorlati következmény ugyanaz, mint az 1.4 fő
szabályáé: **különböző lekérdezésekből származó pontszámok nem összemérhetők**, és
egy korábbi pillanatkép sub-csúcs értékei nem tekinthetők stabilnak, ha közben az
ablak maximuma megváltozott. Ez a §8.2 láncolás egyik nyitott kockázatának is
forrása.

---

## 2. Célok

1. **Kulcsszó-blokk:** kulcsszavanként **külön chart**, mindegyiken **saját
   lineáris regresszióval** és kiírt mérőszámokkal; időtartomány-választóval.
2. **Trend-blokk:** napi felkapott trendek listája, kategória-címkével, és a
   trendek napi görbéje. **Regresszió nélkül.**
3. **Kettéosztott dashboard:** külön vezérlő a két blokkhoz, mert két külön
   időszemantikáról van szó.
4. **Kategória átvezetése az adatrétegben** (`topics` + `temak`), és a
   `kategoriak.json` aggregátum felépítése — felület nélkül.

---

## 3. Nem-célok

Változatlanul a v1 3. fejezete szerint (PR-check CI workflow; a
`napok/*.json` archívum visszapótlása kategóriával; gyűjtés-oldali
módosítás; backend, adatbázis, felhasználói fiókok, analitika), az alábbi
**egy módosítással**:

- A v1 „többnapos kulcsszó-történet" nem-célja **részlegesen feloldva**: a
  **7 napos ablak beleértendő** (egyetlen lekérdezés, konzisztens skála,
  lásd 1.4). Az **ennél hosszabb** tartomány továbbra is nem-cél, mert
  láncolást igényel — az a Phase 4 dolga (lásd 8.2).

Új nem-cél:

- **Nincs kereszt-kulcsszó összevetés, rangsor vagy „top kulcsszó" lista.**
  Sem a felületen, sem a `kulcsszo_osszesites` értelmezésében. Ez nem
  ízlés kérdése, hanem a mérés érvényessége (1.4).

---

## 4. Döntések

### 4.1 Eldöntött

| Döntés | Választás | Indoklás |
|---|---|---|
| Dashboard szerkezete | **Kettéosztva**: felső = kulcsszó (intervallum), alsó = trend (nap) | A v1 4.1 indoklásának („más időszemantika: válassz egy napot vs. lásd a sorozatot") felületi megvalósítása |
| Kulcsszó-megjelenítés | **Szavanként külön chart** | Szerkezetileg kizárja a 1.4 szerinti érvénytelen összevetést; közös charton 13 vonal épp azt hívná elő |
| Regresszió hatóköre | **Csak a kulcsszó-blokkban** | A trendlista naponta kicserélődik, nincs folytonosság, amin trendvonal értelmes lenne |
| Regresszió bemenete | A **lezárt** pontok; a `reszleges: true` záró pont **kihagyva** | A részleges óra csonka aggregátum, lefelé húzná a meredekséget |
| Kiírt mérőszámok | Az irány **leíró tendencia** (nem verdikt), a meredekség egységgel, az R² **önmagyarázó legendával** (0–1) | MÉRT (2026-08-12): az R² NEM „rendszeresen magas", hanem **0,00–0,30** — a hamis tekintély forrása az IRÁNYSZÓ, nem az R²; a régi „(másodlagos)" épp a becsületes jelet fokozta le |
| **Regresszió számítási helye** | **Az exportban, Pythonban** → `kulcsszo_regresszio.json`; a frontend csak rajzol | Lásd 8.3 — a `reszleges` kizárása és a lyukas sorozat kezelése adat-szemantika, nem megjelenítés, tehát pytesttel kell őrizni |
| Intervallum-gombok | A ténylegesen elérhető napszámból **számolva** engedélyezettek | Precedens: v1 7.1 opcionális kategória-szűrő („ne látszódjon működésképtelennek") |
| Taxonómia | **Két külön**: kulcsszó → `domen`/`tipus` (config), trend → `topics`/`temak` (trendspy) | Két különböző fogalom, két blokk; keveredésük hibaforrás |
| Kategória tárolása | Kettős: `topics` (`list[int]`) + `temak` (`list[str]`) | v1 4.1 változatlan |
| Cache-busting | `?v=` + `Date.now()` | v1 4.1 változatlan |
| Hírbélyegképek | Nem jelenítjük meg | v1 4.1 változatlan (külső origó) |
| Feliratok nyelve | Minden magyarul | — |
| Playwright hol fut | Lokálisan | v1 3. fejezet, változatlan |

### 4.2 Nyitott

**Grafikon-könyvtár.** v1 javaslata áll: **vendorolt Chart.js 4.x**, pinelt
verzióval és hash-teszttel. Az érv aszimmetrikus (saját SVG-nél a tooltip
hit-testing, mobil érintés és tengelyskálázás minden sora saját tesztelendő
kód). **Új szempont a v2-ben:** 13 külön chart egy oldalon — a döntésnél a
teljesítmény és a lusta (viewportba érés szerinti) rajzolás is mérlegelendő.

**A `napelem`-típusú gyenge szavak kezelése — LEZÁRVA** (Task 9b, lásd 11.2):
megjelenítendő üres/csupa-nulla állapottal (7.5), nem elrejtve.

---

## 5. Teszt-politika

**Változatlanul a v1 5. fejezete szerint.** Az új invariáns: *csak saját és
vendorolt eszköz, semmi külső betöltés* — relatív erőforrás-útvonalak, tiltott
inline script és inline event handler, nincs `javascript:` URL, nincs külső URL
a saját JS-ben, és `docs/vendor/FORRAS.md` sha256-tal, tényleges hash-ellenőrzéssel.

A v2-ben ez a fejezet **szűkebb hatókörű lett**, mint ahogy a v1 alapján
várható volna: mivel a regresszió az exportban számolódik (4.1, 8.3), a
`docs/js/` alá csak betöltő- és rajzoló-kód kerül. Numerikus logika nincs a
böngészőben, tehát a teszt-politikának nem kell számítási helyességet őriznie
— az pytest hatáskörében marad.

---

## 6. Tesztelési stratégia

**Változatlanul a v1 6. fejezete szerint** (strukturális pytest; kétszintű
JSON-szerződés-teszt exporter- és archívum-szinten; kevés, gerinc-jellegű
Playwright smoke).

Új szerződés-tételek, amelyeket a v1 nem ismerhetett:

- `kulcsszo_nyers.json`: kulcsszavanként rekordlista, minden rekordban
  `ablak_kezdet_utc` / `ablak_veg_utc` (tz-aware, órahatárra igazított),
  pontlista `idopont_utc` + `ertek` + `reszleges` mezőkkel.
- **A kulcsszó-halmaz nem konstans.** A kiírt szavak száma naponta legitim
  módon ingadozik (lásd 7.5) — a teszt **ne** kössön 13-ra.
- `modszertan_valtas`: ha jelen van, kanonikus `YYYY-MM-DD` **string**
  (a betöltő `.isoformat()`-tal normalizál; idő-komponens `KonfigHiba`).
- A `reszleges: true` **pontosan a záró órás ponton** áll, sehol máshol.
- **A `tortenet.json` napjainak száma sosem csökken** két egymást követő futás
  között (halmozódó fájl, sosem nyesett). Ez a `meres_kezdete` visszafejthető-
  ségének szerződéses alapja (8.3) — egy néma „takarítsuk a régi napokat"
  változás ezt bukná meg.

Új Playwright-tétel: az intervallum-váltás után a megjelenített mérőszámok a
**kiválasztott intervallushoz tartozó** rekordból jönnek, és az `ervenyes:
false` intervallum gombja letiltott, magyarázattal.

Új pytest-tétel (8.3): a regressziós számítás egységtesztje — a `reszleges`
pont kihagyása, a lyukas sorozat kezelése, és az `ervenyes: false` ág.
**Ez a v2 egyik fő nyeresége:** a numerikus helyesség valódi RED-del
kikényszeríthető, nem böngészőben.

---

## 7. Felület

### 7.1 Elrendezés

Két szekció, mindegyik a SAJÁT vezérlőjével egy bal oldali sávban (asztali nézet):

```
┌──────────────┐  ┌────────────────────────────────────┐
│ intervallum  │  │ KULCSSZAVAK                        │
│ 1 hét/2 hét/ │  │  szavanként külön chart +          │
│ 1 hó/3 hó/1év│  │  regresszió + mérőszámok           │
│  (sticky)    │  │                                    │
└──────────────┘  └────────────────────────────────────┘
┌──────────────┐  ┌────────────────────────────────────┐
│ dátumválasztó│  │ NAPI LEGFRISSEBB TRENDEK           │
│  (egy nap)   │  │  eloszlás-chart + kategória-szűrő  │
│  (sticky)    │  │  + trendlista — REGRESSZIÓ NINCS   │
└──────────────┘  └────────────────────────────────────┘
```

ELTÉRÉS a v2 első tervrajzától: az EGY közös bal „DASHBOARD" sáv helyett
PER-SZEKCIÓ sávok. Indok: a kettéosztás szemantikai (a felső „lásd a sorozatot",
az alsó „válassz egy napot"); egy KÖZÖS sávban a felhasználó nem látja, melyik
vezérlő mire hat — ezt eddig egy külön magyarázó mondat kompenzálta (§7.4). A
vezérlő közvetlenül a vezérelt szekció mellett magától egyértelmű → a magyarázó
mondat elhagyható (§7.4). A sávok `position: sticky`: görgetéskor a saját
szekciójuk mellett láthatók maradnak. A MOBIL viselkedés (a sáv nem maradhat sáv)
a Task 10 hatóköre (§11.6) — az asztali sticky itt épül, a reszponzív összecsukás ott.

### 7.2 Kulcsszó-blokk

- **Forrás:** `kulcsszo_nyers.json` (7 napos ablak), illetve hosszabb
  tartományhoz a láncolt sorozat (8.2, Phase 4-ig nem elérhető).
- **Kulcsszavanként külön chart.** Egy charton egy vonal. Több szó egy
  ábrára tétele **tilos** (1.4).
- **Lineáris regresszió** minden charton, a lezárt pontokra illesztve.
  Kiírandó: **meredekség** (nagyságrend, egységgel: relatív pont / nap), és mellette
  **R²**. A tengely mondja ki, hogy **relatív skála**. **Az irány LEÍRÓ TENDENCIA, nem
  verdikt** („iránya csökkenő/növekvő/stagnáló", nem „Csökken/Növekszik/Stagnál") — mert a
  hamis tekintély forrása épp a verdikt-erejű irányszó (§10, MÉRT: R²=0,00–0,30). Az R²
  **önmagyarázó legendával** áll, amely a SKÁLÁT írja le, nem az adott értéket ítéli meg:
  `R² = X (illeszkedés-jóság 0–1; a magasabb érték erősebb irányt jelent)`. A legenda **fix**
  (nincs R²-küszöbhöz kötött szöveg — az tristate-mintázat volna, spec-bővítés, 7.5).
  A mérőszám-sor **záró eleme a fedettség, a nem-nulla számmal ELÖL**:
  `N/M óra nem-nulla (M/M lezárt, K részleges kihagyva)` — az első szám a **jel
  erőssége** (`pontok_nem_nulla`/lezárt), nem a puszta fedettség. A régi, egyedül álló
  „lezárt/lezárt" alak (pl. „168/168 óra") **teljes mérést sugallt** egy túlnyomóan
  nulla sorozatnál is; a nem-nulla szám elöl ezt helyesbíti (8.3, a `pontok_nem_nulla`
  indoka és a mérés: 2026-08-12).
- **A `reszleges: true` záró pont kimarad a fittelésből**, de a görbén
  megjelenhet, vizuálisan megkülönböztetve (szaggatott vég vagy halvány pont).
- **Csoportosítás:** a chartok a config `domen` (esetleg `tipus`) mezője
  szerint csoportosíthatók. Ez a kulcsszavak saját taxonómiája — **nem
  keverendő** a trendek `topics`/`temak` címkéivel (7.3).
- **Nincs kiírt „átlag" vagy „csúcs" mérőszám** követhető számként. A v1 7.4
  indoklása áll: ezek a szó saját ablakbeli maximumához viszonyulnak, ami
  ablakonként változhat; egy kiírt „átlag: 45" azt sugallná, hogy összevethető
  a tegnapival, pedig nem. **A görbe és a relatív tengely becsületes; a
  kiemelt szám nem.**
- **A kulcsszólista mozgó célpont.** Kivett szó árva sorozatot hagy (soha nem
  törlünk); új szó a felvétele napján kezd. A frontend a **ténylegesen
  előforduló** kulcsszavakból dolgozzon, ne beégetett listából.
- **A kulcsszólista változása — felvétel és eltávolítás.** A lista nem
  állandó; a felvétel és az eltávolítás külön megjelenítési szabályt kíván,
  és egyik sem keverendő a 7.5 néma skipjével.
  - **Új szó felvétele:** a szónak a felvétele napjától van sorozata, ezért a
    hosszabb intervallumokon a görbéje **rövidebb**, mint a régi szavaké — nem
    azért, mert nulláról indult, hanem mert korábban nem mértük. A felület ezt
    **írja ki** (pl. „mérés kezdete: 2026-08-14"), különben az olvasó ott lát
    hiányt vagy nullpontot, ahol valójában nincs adat. Ugyanez a vizuális
    minta már látszik a `tortenet.json`-ban: a horgonyos korszak 07-21…07-28
    napjain 5–9/13 a fedettség, a szóló korszakban 07-30-tól 13/13 — a régebbi
    napok rövidebb szó-lefedettsége nem hiány, hanem eltérő mérési kezdet.
  - **Szó eltávolítása a `config.yaml`-ból:** a korábbi sorozat **nem törlődik**
    (soha nem törlünk adatot), tehát a nyers/tortenet fájlokban árva sorozatként
    megmarad. **Döntés (a mezőket lásd 8.3): a felület a történeti adatot
    megjeleníti, „már nem mérjük (utolsó mérés: YYYY-MM-DD)" jelöléssel** — nem
    rejti el és nem törli, de vizuálisan halványíthatja/összecsukhatja, hogy ne
    zsúfolja az aktív listát. A puszta elrejtés és a config-lista mint
    kizárólagos szűrő elvetve: az előbbi a „soha nem törlünk" ígéretet mossa el
    a felületen, az utóbbi olyan forrásra (repo-beli config) támaszkodna, amely
    ma nem frontend-adat. Opcionális „csak aktív szavak" kapcsoló megengedett,
    de nem az alapértelmezés.
  - **Visszatett szó:** ha egy eltávolított szó később visszakerül a configba,
    az `aktiv` újra igaz, de a sorozatban **lyuk marad**. Ezt a felület a 7.5
    szakadó vonalával jeleníti meg (nincs interpoláció); a `meres_kezdete`
    továbbra is az **első** szóló mérés napja marad, nem a visszatétel napja.
  - **Három élettartam-állapot, nem azonos a 7.5 skipjével:** „sosem volt mérve"
    (a szó a felvétele előtt) ≠ „mértük, de aznap kiesett" (7.5 néma skip) ≠
    „már nem mérjük" (eltávolított szó). A felület a hármat **ne mossa össze**;
    az eldöntésükhöz szükséges mezőket a 8.3 exportja adja.
- **Alapértelmezett nézet: „1 hét" (a legtöbb kártyát rajzoló intervallum).**
  Betöltéskor a kulcsszó-chartok az „1 hét" (órás) nézeten nyílnak, ahol
  jelenleg mind a 13 szó rajzol; a hosszabb (nap/het) nézetek kattintásra
  érhetők el. Az előre kiválasztott gomb az „1 hét", ha `ervenyes: true`;
  különben a leghosszabb érvényesre esik vissza. Ha egyetlen intervallum sem
  érvényes, a 7.5 üres állapota jön.
  - **REVÍZIÓ (2026-08-16, 6b Szelet 3).** Az eredeti szabály „a leghosszabb
    érvényes időszak" volt (nem beégetett; magától tolódik kifelé). Ez arra a
    FELTEVÉSRE épült, hogy az érvényesség MONOTON nő ÉS a leghosszabb egyben
    minden-szó-érvényes — az órás-csak világban az „1 hét" mindkettő volt. A
    nap/het másodlagos adat ezt MEGTÖRTE: a hosszú intervallumokon az
    érvényesség RITKA (pl. 1_ev: 1/13 szó), így a „leghosszabb érvényes
    globálisan" 13-ból 1 rajzoló kártyás nézetet adott (rossz első benyomás).
    A default innentől a legtöbb kártyát rajzoló intervallum = „1 hét". A
    hosszabb nézetek kattintásra tágulnak. (A jelenlegi „1 hét = 13/13" azért
    áll, mert csak 4 szónak van másodlagos adata — a Task 5 utáni lefedettségnél
    a „legtöbb kártya" intervallum ÚJRAMÉRENDŐ; ma beégetett „1 hét", lásd a
    leltár ALAPNEZET-VEGYES-lezárását és a re-mérési feltételt.)

### 7.3 Trend-blokk

- **Forrás:** `legfrissebb.json` → `top_trendek` (a `trend_idosorok` ugyanaz
  az adat más alakban — a frontend **az egyiket** használja, ne mindkettőt
  töltse be).
- **A lista kizárólag az API-ágból épül.** A rendezés EGY közös helyen történik — a
  `rangsorolt_trendek` helper (ma `futtato.py:31`, `sorted` explicit
  `(-volumen, eredeti_index)` kulccsal); ezt a `megjelenitendo_trendek` (ma
  `futtato.py:41`) hívja, a `top_trend_struktura` (ma `futtato.py:59`) pedig AZON
  keresztül jut a rangsorhoz; a MEGJELENÍTETT lista hossza az alábbi holtverseny-szabály szerint
  áll elő, nem pusztán top-`trend_idosor_max`. Az
  RSS-ág (`rss_trendek`) **csak a `hirek`-et párosítja** kifejezés szerint,
  listaelemet nem ad. Ezért **minden friss-napi elem kategória-képes** (az
  `api_trendek` `TrendKeyword`-jén ott a `topics`/`topic_names`), és **nincs
  negyedik állapot** a kategória-címke három esete mellett. Ha az API-ág
  kapu-blokk vagy bukás miatt nem ad adatot, a lista **üres vagy rövid** (7.5),
  nem pedig kategória nélküli — ezt a felület a 7.5 üres-állapotával kezeli.
- **Megjelenített lista vs. idősor-lista — holtverseny-kiterjesztés (D1).** A
  Google `volumen`-e sáv, nem darabszám (§1.4: durva, sávos; a 2026-07-23-i
  futásban hét szint 100–10000 között). A top-`trend_idosor_max` vágás így egy
  volumen-rekesz KÖZEPÉRE eshet, és azonos keresettségű trendek közül önkényesen
  dob ki (2026-07-23: 65 trend; a 15-ös vágás a 2000-es rekesz közepén — 7
  jelölt 4 helyre). Ezért a két lista SZÉTVÁLIK:
  - **idősor-lista** (hálózati költség): a top `trend_idosor_max`, **REVÍZIÓ
    (2026-08-17, GORBE-B): FORWARD-ONLY kiterjesztve a rekeszre** — a top-N UTÁN
    egy LEGUTOLSÓ, csendes-feladású ág (`_masodlagos_ag`-minta) legfeljebb
    `trend_idosor_rekesz_max` (=5) rekesz-trendhez is kér idősort, hogy a
    megjelenített rekesznek is legyen sparkline-ja. A `Kliens` plafonja
    (`tervezett_hivasszam`) EMELT: `2 + trend_idosor_max + trend_idosor_rekesz_max
    + len(kulcsszavak)` (a rekesz-ág 429/korlát esetén CSENDESEN elmarad, nem
    job-piros; a napló kétállapotú FIGYELEM-et ír: nincs-rekesz vs elmaradt-N).
    A régi napok forward-only NEM telnek fel (üres-felirat marad). Terv:
    `plans/2026-08-17-gorbe-b-rekesz-idosor.md`.
  - **megjelenített lista**: a top `trend_idosor_max`, KIBŐVÍTVE mindazon
    trendekkel, amelyek `volumen`-e MEGEGYEZIK a küszöb-trendével (az utolsó
    bekerülőével) — a TELJES holtverseny-rekesz, nem csak a véletlenül „befért"
    része.
  Ez **monoton** változás: az eddig bekerült top-`trend_idosor_max` ezután is
  bekerül (a tie-break bitre azonos a mai viselkedéssel, lásd lent), a rekesz
  többi tagja MELLÉ jön — semmi nem esik ki. Ezért **nem** igényel
  `modszertan_valtas` töréspont-jelölőt. Vö. a lenti „Ne feltételezz fix 15
  elemet" ponttal: a hossz eddig is változó volt, ez csak egy további,
  adatvezérelt forrása a változásnak.
- **Tie-break: az EREDETI API-POZÍCIÓ (D2)** — a volumen-rendezés ELŐTTI
  lista-index, NEM ábécé és NEM a `keyword`. Azonos bemenetre azonos kimenet
  kell; bemenet-független (pl. ábécé) rendezés NEM. Az API-pozíció megőrzi a
  Google sávon belüli maradék rangsorát, és **bitre azonos a mai viselkedéssel**
  (a `sorted` stabil, az `api_trendek` sorrendje = az API-pozíció). A tie-break
  EGYETLEN közös helyről megy: a `rangsorolt_trendek` helper (ma `futtato.py:31`)
  — ebből merít mind a megjelenített lista (`megjelenitendo_trendek`, ma
  `futtato.py:41`), mind az idősor-ág kifejezéslistája (`top_kifejezesek`, ma
  `futtato.py:177`). A korábbi kockázat (két külön `volumen`-rendezés, szétcsúszó
  listák) így **orvosolva** — a prefix-invariánst a közös helper biztosítja.
  **Invariáns (tesztelendő):** az idősor-lista a megjelenített lista első
  `trend_idosor_max` eleme — PREFIX. A közös helper követelménye ezt biztosítja;
  ez az invariáns az, ami ellenőrizhető.
- **Felső korlát: `trend_megjelenites_max` config-kulcs (D3)** — opcionális,
  default **25**, a `naplo_max_sor` mintájára (visszafelé kompatibilis). A
  tényleges korlát `max(trend_megjelenites_max, trend_idosor_max)`, különben egy
  `trend_idosor_max=30` config kisebb megjelenített listát adna, mint az
  idősoros. A rekesz mérete ADATFÜGGŐ és nem korlátos; ha a kiterjesztés átlépné
  a korlátot, a vágás a korlátnál történik — és ott ISMÉT egy holtverseny
  KÖZEPÉRE eshet (a felső korlát nem oldja fel a holtversenyt, csak a lista
  méretét fékezi meg). A vágás ekkor is a fenti tie-break (API-pozíció) szerint
  dönt.
- **A kiterjesztés 0-volumenű sávba NEM lép be (D4).** A `volumen_szam`
  (`felkapott.py:8`) 0-t ad hiányzó, nem numerikus ÉS „5000+" alakú volumenre
  is; ezek egyetlen nagy blokkba esnek a lista alján. Ha a küszöb-volumen 0, a
  kiterjesztés ELMARAD (a megjelenített lista marad top-`trend_idosor_max`).
  FIGYELEM: ez KIZÁRÓLAG a kiterjesztésre vonatkozik. Az alap top-N változatlan —
  oda ma is bejuthat 0-volumenű trend, ha nincs elég nem-nulla; ezt a szabály
  NEM módosítja (az viselkedésváltozás lenne).
- **Regresszió nincs.** A felkapott lista naponta kicserélődik, nincs
  folytonosság, amit meg kellene őrizni; egy trendvonal itt értelmetlen.
- **Kategória-címke** minden elemen (Task 3a után), a v1 7.1 három
  állapotával: `[]` = nincs besorolás, `["Other"]` = valódi „Other"
  kategória, hiányzó mező = régi archív nap. A felületen a `[]` és a hiányzó
  mező egyaránt „egyéb"; **az adatban a három maradjon megkülönböztethető**.
- **Többértékű szűrő**: egy trend több kategóriában is megjelenhet. Ha a
  betöltött napon egyetlen elemen sincs kategória, a szűrő ne jelenjen meg
  vagy legyen letiltva.
- **Görbe (MÉRT adatalak, 2026-08-08).** A napi `idosor` a `now 1-d` ablak
  **8 perces** rácsa (`{idopont_utc, ertek}` pontok), 24h span. A `0` értékek
  **mért nullák, nem hézagok** → `spanGaps`-kérdés NINCS. Az ábrázolás **NEM
  feltételezhet folytonos alapszintet** (a mért nulla-arány sorozatonként
  **30–86%, medián 69%** — 2026-08-08); nagy volumenű napon valódi alapszint is
  előfordulhat, ezért a forma **egyik képet sem** (se folytonos vonal, se fésű)
  írja elő kötelezően. A `max` **mindig 100** (szóló lekérdezés, önnormalizálás)
  — **helyes tervezés**, mert közös skálán a 2000-es volumenű trendek 10 körül
  lapulnának; ára, hogy minden kártya 100-ig skálázódik, ezért a „melyik volt
  nagyobb" olvasatot a kártyán kiírt `volumen` előzi meg (már a kódban).
  **Regresszió nincs** (lásd fent), így **a regresszióból fakadó hamis
  pontosság** veszélye nem áll fenn. Több sorozat egy ábrán legitim, **ha a
  kérdés az, mikor csúcsosodtak** — de az összeillesztés **KIZÁRÓLAG időbélyeg
  (`idopont_utc`) szerint**, SOHA index szerint.
- **A rács nem uniform — se fix pontszám, se közös kezdet (MÉRT 2026-08-07).** A
  `now 1-d` ablak a KÉRÉS idejéhez horgonyzódik, a hívások szét vannak húzva
  (`alap_keses_mp`/`szoras_mp` → 15 hívás több percen át), ezért a korábbi
  kérések még egy korábbi 8-perces slotba esnek: `2026-08-07` — **4 sorozat 181
  pont** (kezdet `19:52`), **11 sorozat 180 pont** (kezdet `20:00`); a **vég
  közös** (`2026-08-07T19:52:00Z`). Futásidő-függő, nem determinisztikus (a
  `2026-07-30` mind 180, a `2026-08-08` mind 181). **TILOS** fix pontszámot vagy
  közös kezdetet feltételezni; a teszt-fixture ELTÉRŐ hosszú/kezdetű sorozatokat
  tartalmazzon (0.2/13).
- **Elemenkénti üres görbe (a D1-kiterjesztés következménye).** A
  holtverseny-kiterjesztéssel bekerülő elemek NINCSENEK az idősor-listában (az
  idősor a top `trend_idosor_max`-ra fut), ezért az `idosor`-uk ÜRES (a
  `top_trend_struktura` `idosor_map.get(kif, [])` fallbackja). Lesz tehát
  trendkártya GÖRBE NÉLKÜL. Ez **elemenkénti** üres-állapot, KÜLÖNBÖZŐ a §7.5
  lista-szintű üres-állapotától (az az egész listára szól). A felületnek kezelnie
  kell: az ilyen kártya a `volumen`/kategória/`hirek` alapján megjelenik, de
  görbe helyett elemenkénti „nincs idősor ezen a napon" jelölést kap — ne törje
  meg az elrendezést, és ne keveredjen a lista-szintű üres állapottal.
- **Blokk-szintű üres görbe — mind-üres nap (MÉRT, 2026-07-27/28).** Ha az
  idősor-ág BUKIK / 429 / feladás (`AgFeladva` → `trend_idosorok=[]`), a nap
  MINDEN eleme üres `idosor`-t kap — nem D1-szórtan, hanem **100%**
  (`2026-07-27` és `2026-07-28` = 15/15). Ekkor a 15+ elemenkénti „nincs
  idősor…" egy ismételt fal lenne, ami akaratlanul átvenné a §7.5 szerepét.
  Ezért a felület **blokk-szinten összevon**: egyetlen jelzés a szekció élén, az
  elemenkénti copy helyett. **DOM-szerződés:** a kártyák MEGTARTJÁK a
  `data-idosor-allapot="nincs"` attribútumot; csak a LÁTHATÓ elemenkénti szöveg
  vonódik össze egyetlen szekció-szintű jelzésbe — a smoke az **attribútumból**
  assertál. Kiváltó: **üres == elemszám**. Köztes arányoknál (pl. 14/15) az
  elemenkénti kezelés marad (**VÁLLALT**); a 0% / szórt / 100% hármas az
  archívum **2026-08-09-i állapotának MEGFIGYELÉSE, nem garancia**. KÜLÖNBÖZŐ a
  §7.5-től: itt VAN trend (volumen/kategória), csak idősor nincs — a §7.5
  `TREND_URES_SZOVEG` (nulla trend) NEM tüzel.
- **Hírek:** cím + forrás + link, kép nélkül. Az üres `hirek` tömb a normális
  eset.
- **Ne feltételezz fix 15 elemet** — a `trend_idosor_max` konfigurálható, és
  egy feladott ág rövid listát hagy.
- **Alapértelmezett nap: a legfrissebb elérhető.** A dátumválasztó belépéskor a
  `napok/index.json` **legutolsó** napján álljon, ahonnan a látogató korábbi
  napokra léphet vissza. Ez nem feltétlenül a mai naptári nap, hanem az utolsó
  **sikeres** gyűjtésé; kiesett napon a legutolsó meglévő (7.5). A vezérlő
  részletei a 7.4-ben.

### 7.4 Vezérlők és adat-elérhetőség

**Felső (kulcsszó) — intervallum.** A gombok engedélyezettsége a
**ténylegesen elérhető** adatból számolandó, nem beégetve:

| Gomb | Feltétel | Ma (2026-07-31) |
|---|---|---|
| 1 hét | egyetlen `kulcsszo_nyers` pillanatkép elég | **működik** |
| 2 hét | láncolt sorozat ≥ 14 nap | letiltva |
| 1 hónap | láncolt sorozat ≥ 30 nap | letiltva |
| 3 hónap | láncolt sorozat ≥ 90 nap | letiltva |
| 1 év | láncolt sorozat ≥ 365 nap | letiltva |

**A frontend ezt nem számolja ki.** Az érvényesség a `kulcsszo_regresszio.json`
`ervenyes` mezőjéből jön (8.3), intervallumonként — a böngészőben nincs
dátumaritmetika, csak renderelés. Így a „mikor nyílik ki egy gomb" kérdés
egyetlen, pytesttel őrzött helyen dől el.

**Előre kiválasztott gomb.** Belépéskor az „1 hét" az aktív, ha `ervenyes: true`
(a legtöbb kártyát rajzolja); különben a leghosszabb érvényes (7.2 REVÍZIÓ,
2026-08-16 — az eredeti „leghosszabb érvényes" a nap/het másodlagossal 1/13
rajzoló nézetet adott). A kiválasztás is a fenti egyetlen forrásból dől el, a
frontend itt sem számol.

A letiltott gomb **magyarázatot adjon** (pl. „ehhez még nincs elég mért nap"),
ne csak szürkén álljon; a szöveg az `ok` mezőből származhat. A kulcsszó-történet
gyakorlatilag **2026-07-30-nál kezdődik**: a `modszertan_valtas` előtti napok
horgonyos módszertanúak, és **nem köthetők össze** a későbbiekkel.

**Alsó (trend) — dátumválasztó.** A v1 7.3 változatlanul: forrás
`napok/index.json`, majd `napok/YYYY-MM-DD.json`; csak az `index.json`-ban
ténylegesen szereplő napok választhatók; dátumformátum végig `2026. 07. 26.`.
Belépéskor a **legfrissebb** szereplő napon áll — nem feltétlenül a mai naptári
nap, hanem az utolsó sikeres gyűjtésé (7.3) —, innen léphet a látogató korábbi
napokra. Nem létező nap kérése esetén érthető hibaüzenet.

**Felirat kötelező** a kulcsszó-blokkban, de **NEM késésről**: a 9b a
`kulcsszo_nyers.json` órás `now 7-d` ablakából rajzol (7.2), amely a futás
pillanatáig ér — normál esetben ugyanabból a futásból, mint a `legfrissebb.json`
trendlistája. (A §1.3 egy napos lemaradás a `tortenet.json` napi aggregátumára
vonatkozik, amelyet a 9b nem használ; egy „teljes nap"-dátum a friss órás görbe
alatt önellentmondó volna.) **A felirat dátuma mindig a rajzolt intervallum
tényleges `ablak_veg_utc`-jéből jön**, nem a „közös futás" feltevésből. Ez a
derivált dátum **egyetlen dolgot garantál, negatívan:** megakadályozza a HAMIS
frissesség-állítást (nem írja ki a mai naptári napot, ha a rajzolt adat régebbi).
Amit **NEM** tesz: nem jelzi, hogy aznap **nem érkezett új kulcsszó-adat**. Ez
**vállalt korlát, nem megoldott kérdés** (§7.5), nem „a derivált dátum magától,
helyesen kezel".

**A kulcsszó-ág blokkolása kaszkád; a blokk ELŐTT lemért szavakat a 2026-08-12-i javítás
menti (a 08-11-i eset még a RÉGI, mindent-vagy-semmit viselkedés alatt esett) — VALÓS eset,
a 2026-08-11-i schedule-futás (run #20) mért lefolyása:**
- A kulcsszó-ág a **2. szónál** (`kormányablak`) 4× 429 után **feladta** (`AgFeladva`):
  a stdout szó-szinten jelzi („a kulcsszó-ág feladva (429) a(z) 'kormányablak' szónál"),
  majd az `_ag` a teljes ágat **`blokkolva`**-ként naplózza („a hátralévő ágak
  kimaradnak") → az `idosor` `kihagyva`. A `blokkolva` tehát **nem** az `AgFeladva`
  alternatívája, hanem UGYANANNAK az eseménynek az ág-szintű naplócímkéje.
- **A két csatorna nem ugyanazt mutatja:** a `naplo.csv` csak
  `kulcsszo;blokkolva;5;429,429,429,429`-et rögzít (az 5 = `állás` 1 sikeres +
  `kormányablak` 4× 429); a **stdout** viszont MINDKETTŐT (a szó-szintű feladást ÉS
  az ág-blokkot). A napló-csatornából a WHY (melyik szónál) nem derül ki.
- **Részleges mentés (JAVÍTVA — 2026-08-12; a 08-11-i eset még a RÉGI viselkedés alatt esett):**
  az `állás` (1. szó) **sikeresen mért** (a 7 hívásból 1 az övé), mielőtt a `kormányablak`
  blokkolt. **RÉGI viselkedés:** a `kulcsszavak.gyujt` az `AgFeladva`-t a felhalmozott részleg
  **visszaadása előtt** dobta (`kulcsszavak.py:128–130`, `raise` a `return` ELŐTT) → a
  `kulcsszo_nyers` üres maradt, az `ir_gordulo` nem futott, a `kulcsszo_nyers.json` érintetlen
  (a 08-11-i `e660f2e` nem tartalmazza; mind a 13 szó vége `08-10T19:00`). Az
  `if kulcsszo_nyers:` guard (`futtato.py:212`) itt csak **tünet** — a részleg már a `gyujt`-ban
  elveszett. **ÚJ viselkedés:** a `gyujt` az `AgFeladva`-ra **ráakasztja a részleget**
  (`e.reszleges`), a futtato `except AgFeladva`-ja **kicsomagolja** → a blokk **ELŐTT** lemért
  szavak (itt `állás`) **megmaradnak**; csak a blokkolt szótól kezdve vész el az adat. A guard
  marad (valódi üresnél helyesen skippel). A napló `blokkolva`-sora változatlan; a megmentett
  szavak számát a **stdout `FIGYELEM` sora** jelzi (a `naplo.csv` külön oszlopa szerkezet-
  változás → külön kör).
  - **HATÓKÖR-SZŰKÍTÉS (SZÁNDÉKOS, nem felejtés):** a részleg-mentés **KIZÁRÓLAG** az
    `AgFeladva` (429-blokk) ágon él. Ha a `gyujt` MÁS kivétellel hasal el, nincs `e.reszleges`,
    és a részleg elveszik, mint a régi viselkedésben. Elfogadható: a 429 az **egyetlen mért**
    blokk-eset. A spec ezt **kimondja**, nehogy a következő olvasó azt higgye, minden hibaágra véd.

Ebből **a két blokk dátuma legálisan szétcsúszik**: a kulcsszó-blokk `ablak_veg`-je
**2026-08-10**, a trend-blokk alap-napja **2026-08-11** → a felületen **egyszerre két
dátum** jelenik meg, magyarázat nélkül. (Külön csapda: a `kulcsszo_regresszio.json`
top-szintű `szamitva_utc`-je a 08-11-i újraszámoláskor **08-11-re ugrott** a
változatlan 08-10-es adat mellett — ezért a felirat **kizárólag** az `ablak_veg`-ből
jöhet, sosem a `szamitva_utc`-ből. **Grep-igazolt** (2026-08-12): a frontend
(`docs/js`, `docs/index.html`) nem hivatkozza a `szamitva_utc`-t; a `.frissesseg`
felirat az aktív intervallum `ablak_veg`-jéből jön, és ezt e2e-őr rögzíti
(`e2e/kulcsszo.spec.js:326`, a fixture-ben szándékosan KÉSŐBBI `szamitva_utc`-vel).
Ez az egyetlen **helyességi** állítás a blokkban — a csapda ellenőrizve nem él, nem
feltételezés.) A spec **nem** állít szerkezeti
frissesség-azonosságot (ez szándékos), de a szétcsúszás **látható következményét** a
felület ma nem jelzi; ezt a §7.5 rögzíti vállalt korlátként, a feloldása külön tétel (Phase 4).
A felirat két tényt közöljön: (1) meddig tart az adat (a fenti `ablak_veg_utc`,
böngészőbeli dátumaritmetika nélkül, 7.4 elve); (2) hogy a pontszámok szavanként
külön 0–100 skálán állnak, egymással nem összemérhetők (1.4). A dátumválasztó-
tagmondat NEM része a feliratnak; a kulcsszó- és trend-vezérlő szétválasztottságát
a §7.1 per-szekció elrendezése közli.

**Közös elv.** Mindkét blokk a legtöbb elérhető kontextussal indul — a
kulcsszavaknál ez a leghosszabb érvényes időszak, a trendeknél a legfrissebb
nap —, a szűkítés a felhasználó döntése.

### 7.5 Üres és hiányos állapotok

Ez a fejezet a Phase 2.5 egyik legkésőbbi felismeréséből származik, és
**tesztelendő eset, nem szépészeti kérdés**.

A kulcsszó-gyűjtés **csendes skip-úttal** rendelkezik: ha a Google üres
sorozatot ad egy szóra, az a kimenetből **teljesen kimarad** (a kulcs
hiányzik, nem üres lista), és ezt sem a napló, sem a stdout nem jelzi. Ezért
**három külön eset** kezelendő, és ezek nem azonosak:

1. **Hiányzó kulcs** — a szó azon a napon nem mérhető volt (kihagyott nap).
2. **Üres lista** — mért, de nulla pont (ma nem fordul elő; szerződésben
   engedett).
3. **Csupa nulla sorozat** — mért, valós, alacsony volumenű adat.

Igazolt eset: a `tüntetés` (az egyetlen `esemenyjelzo` típusú szó) a
`tortenet.json` 9 napjából **kizárólag 07-22-n** szerepel; a 07-30-i éles
futásból teljesen kimaradt. A bent maradt szavak közül a `napelem` a
leggyengébb (169-ből 51 nulla pont), utána a `betegség` (44) — ezek a
következő jelöltek a kiesésre.

Következmények a felületre:

- **Bármelyik chart lehet üres vagy lyukas** egy adott intervallumon. Kell rá
  explicit magyar üres-állapot („ezen az időszakon nincs mért adat erre a
  szóra"), **nem néma üres doboz**.
- A **lyukas sorozatot ne interpoláljuk** — a hiányzó nap hiányzó nap, nem
  nulla. A vonal szakadjon meg.
- **Regressziót lyukas sorozaton** csak a ténylegesen mért pontokra szabad
  illeszteni, és jelezni kell, hány napból hány mért.
- Ha a legutóbbi futásban egy ág feladta (`AgFeladva`), a trendlista lehet
  rövid vagy üres — ezt magyarul, érthetően kell közölni.
- **A kulcsszó-ág is kieshet — nem csak a trendlista.** A fenti `AgFeladva`-eset a
  kulcsszó-ágra is áll: ha az ág egy szónál 429 miatt feladja (`kulcsszo;blokkolva`
  a naplóban; VALÓS: 2026-08-11, a `kormányablak` szónál), a **blokkolt szótól kezdve**
  vész el az adat — a blokk ELŐTT lemért szavakat a 2026-08-12-i javítás **menti** (7.4).
  Ha a blokk az ELSŐ szónál csap le, aznap **nincs új `kulcsszo_nyers` pont**; ekkor (és a
  `tüntetés`-hez hasonló néma skipnél) a kulcsszó-blokk a trend-blokknál **régebbi** adatot
  mutat, a két blokk dátuma szétcsúszik.
  **VÁLLALT KORLÁT (Phase 3):** a felület ezt ma **nem jelzi** — a frissesség-felirat
  csak az adat *végét* mutatja, nem azt, hogy aznap nem frissült, és a workflow-státusz
  is **Success** marad (§10). A folytonosság-diagnosztika (`seged.utolso_res`, „B2") ma
  kizárólag a naplóba kerül (`futtato.py`), a frontendhez nem jut el. A feloldás — a B2
  kimenetének publikálása egy JSON-ba + elavultság-jelzés a kulcsszó-blokkon — **külön
  tétel (Phase 4 jelölt)**, nem Phase 3; rokon az L7 bemenet-perzisztálás adat-útjával,
  de nem olvad össze vele.

---

## 8. Adatréteg-munka

### 8.1 Kategória-aggregátum (`kategoriak.json`)

Változatlanul a v1 7.5 szerint: új kimenet, **felület nélkül**, hogy a
történet a Task 3a élesítésétől épüljön. Tárolandó a **nyers darabszám ÉS a
napi trendlista teljes hossza** is (a puszta darabszám félrevezet, a
részesedés rövid listán ugrál). Mivel a kategória többértékű, a
kategóriánkénti darabszámok összege **meghaladhatja** a napi lista hosszát. A
„kategória nélküli" gyűjtő a `[]` és a hiányzó mezős elemeké — az `Other`
nem ide tartozik.

### 8.2 A láncolás előfeltételei — Phase 4, itt csak rögzítve

A 2 hétnél hosszabb kulcsszó-tartomány láncolást igényel. Az elv: egymást
követő napok 7 napos ablakai **6 napon átfednek**, és az átfedésből
visszaszámolható a napi skálázó — **de csak a lezárt (nem részleges)
szakaszból**.

Amit már most rögzíteni kell, mert a Phase 3 adatszerkezetét érinti:

- **A nyers fájl retenciója véges** (gördülő ablak: ma **14 nap**, a
  `nyers_kimenet.ir_gordulo` `megtartott_nap` kód-szintű alapértelmezése,
  **adat-relatív** — nem config, lásd 11.5). A láncolás tehát **nem
  számolható újra** tetszőleges visszamenőleg a nyers adatból: a kumulált
  skálázó tényezőket **külön, tartósan tárolni kell**, futásról futásra
  továbbvíve. Ez új kimenetet igényel — nem a `kulcsszo_nyers.json`
  megnövelését.

  **Következmény:** a 14 napos nyers retenció és a 2 hetes legrövidebb láncolt
  intervallum egybeesik, tartalék nélkül. Mivel a lánc szomszédos napok
  átfedéséből épül, egyetlen kiesett nap megtöri. A Phase 4 tervezésekor
  eldöntendő: (a) a `megtartott_nap` emelése (tárhely-költség), vagy (b) a
  kumulált skálázó tartós mentése **első naptól**, ami a nyers retenciótól
  függetlenné teszi a láncot. A (b) az erősebb, mert a retenció ekkor csak a
  javíthatóság ablaka marad, nem a történet hossza.
- A `modszertan_valtas` **abszolút határ**: a lánc előtte nem folytatható.
- A **hiányzó napok** (7.5) megtörik a láncot; a szomszédos átfedés hiányában
  a skálázó nem számolható, tehát a lánc szakaszokra bomlik. Ezt a Phase 4
  tervezésének kezelnie kell — a Minor 3 dedup **nem** erre való.

**NYITOTT KÉRDÉS (2026-08-14, nem megoldva) — a lezárt szakasz sem invariáns.**
A skálázó-visszaszámolás feltételezi, hogy a két szomszédos ablak **átfedő
szakasza stabil** (ugyanazok a pontszámok mindkét lekérdezésben), és ezért a lánc
a **lezárt (nem részleges)** részből biztonságosan épül. Az §1.4.1-ben megmért
ablak-relatív újranormálás azonban azt mutatja, hogy **még a lezárt szakasz sem
feltétlenül invariáns**: ha a két lekérdezés között az ablak maximuma
megváltozik (új, nagyobb valós csúcs kerül be), az átfedő — akár lezárt — pontok
relatív értéke elcsúszhat, a legkisebbek 0-ra kerekedhetnek. Ekkor a két ablakból
számolt skálázó **nem konzisztens**, és a lánc egy rejtett törést kap, amit a
hiányzó-nap-detektálás NEM lát (a nap megvan, csak a skálája csúszott). A feloldás
Phase 4 tervezési kérdés (pl. csúcs-váltás detektálása az átfedésben, vagy a
skálázó több átfedő pontra vett robusztus becslése) — itt csak **rögzítve, nem
eldöntve**.

### 8.3 Regressziós kimenet (`kulcsszo_regresszio.json`)

A regresszió **az exportban, Pythonban** számolódik, a napi futás részeként, a
`kulcsszo_nyers.json` (és később a láncolt sorozat) alapján; a kulcsszó-szintű
élettartam-mezőkhöz (lentebb) az exporter emellett a **halmozódó
`tortenet.json`-t és a mai `config.yaml` listáját** is beolvassa. A frontend ezt
a fájlt betölti és **kirajzolja** — nem számol.

Az indoklás négy pontja, rögzítve, hogy a döntés ne nyíljon újra:

1. **Nincs tetszőleges tartomány.** Öt intervallum × a szavak száma = néhány
   tucat szám. A kliensoldal fő érve (dinamikus újraszámolás) itt nem áll.
2. **A `reszleges` kizárása és a lyukas sorozat kezelése adat-szemantika.**
   A Phase 2.5 tanulsága, hogy a szemantikai hibák némán mennek át (finding 6,
   néma skip) — az ilyen logika nem élhet teszteletlen helyen.
3. **Nincs JS-teszt-infrastruktúra.** A projekt pytest-alapú, TDD valódi RED
   diszkriminátorral. Egy numerikus algoritmus JS-ben vagy teszteletlen marad,
   vagy új eszközláncot igényel; mindkettő rosszabb egy `test_regresszio.py`-nál.
4. **Az intervallum-elérhetőség is innen jön** (7.4) — az exporter tudja, hány
   lezárt nap van, tehát ő mondja meg, melyik gomb érvényes.

Vázlatos alak (a pontos séma a Task 9a szerződés-tesztjében dől el):

```json
{
  "szamitva_utc": "2026-07-31T20:00:00+00:00",
  "kulcsszavak": {
    "állás": {
      "meres_kezdete": "2026-07-30",
      "meres_vege": null,
      "aktiv": true,
      "1_het": {
        "ervenyes": true,
        "ablak_kezdet_utc": "2026-07-24T21:00:00+00:00",
        "ablak_veg_utc":   "2026-07-31T20:00:00+00:00",
        "meredekseg_nap": -2.14,
        "r2": 0.31,
        "pontok_hasznalt": 168,
        "pontok_nem_nulla": 166,
        "pontok_kihagyva_reszleges": 1,
        "pontok_hianyzo": 0
      },
      "2_het": { "ervenyes": false, "ok": "nincs_lancolas" }
    }
  }
}
```

> Task 9a döntése, hogy az intervallumokat egy `intervallumok` kulcs alá
> fészkeli-e, hogy a metaadat (`meres_kezdete`/`meres_vege`/`aktiv`) és az
> intervallum-kulcsok ne keveredjenek egy objektumban — a vázlat fent a régi
> (közvetlen) alakot mutatja.

Szerződés-tételek:

- A **meredekség egysége relatív pont / nap**, és a felületnek ezt ki kell
  írnia — a nyers szám önmagában félrevezető (1.4).
- A `pontok_kihagyva_reszleges` és a `pontok_hianyzo` **kötelező mező**, mert
  a felület ezekből tudja megmondani, hány napból hány **mért** (= nem-hiányzó,
  van értéke; 7.5). Ez **nem** azonos a jel erősségével — a mért pont lehet 0.
- A **`pontok_nem_nulla`** (a lezárt pontok közül a **nem-0 értékűek** száma)
  **kötelező mező** ott, ahol a `pontok_hasznalt` is jelen van (a
  `keves_pont`/`degeneralt`/`rovid_span` hibaágakon ÉS az `ervenyes`-en; a
  `nincs_adat`-ról hiányzik, épp mint a `pontok_hasznalt` — nincs lezárt pont).
  Indoka a mérés (2026-08-12): a nullák **éjszakai mintavételi artefaktumok** (a szó
  a kvantálási küszöb alá süllyed), nem valós volumen; egy 97%-ban nulla eseményjelző
  (`tüntetés`: 168 lezárt, 5 nem-nulla) `ervenyes:true` regressziót és „168/168 óra"
  feliratot kap, ami **teljes mérést állít**, holott a görbe 5 valós pontból áll. A
  `pontok_nem_nulla` teszi a jel erősségét láthatóvá.
  - **CSAPDA — két hasonló nevű, ELTÉRŐ jelentésű szám (mint a `szamitva_utc` vs
    `ablak_veg`: NEM felcserélhetők):** a `json_export.ervenyes_pontok` (a
    `kulcsszo_osszesites`-ben) a **nem-nulla `nyers_ertek`** száma **NAPI** hatókörben,
    az üres/NaN pontot külön kezelve; a `pontok_nem_nulla` a **nem-nulla `ertek`** száma
    a **7 NAPOS órás regressziós ablakban**, csak a részlegest kizárva. Más ponthalmaz,
    más span, más NaN-kezelés → **a kettő nem ugyanaz, nem cserélhető fel.**
- Az `ervenyes: false` ághoz **kötelező `ok`** (pl. `nincs_lancolas`,
  `keves_pont`, `nincs_adat`), hogy a letiltott gomb magyarázatot adhasson.
- **Kulcsszó-szintű élettartam-mezők** (a 7.2 lista-változásához), szavanként
  egyszer:
  - `meres_kezdete`: az első nap, amelyen a szót a **szóló** módszertannal
    mértük. A `tortenet.json` halmozódó (sosem nyesett) fájl, ezért ez az
    export idején a legkorábbi előfordulásból visszafejthető — **de a
    `modszertan_valtas`-ra vágva** (a horgonyos korszak korábbi előfordulása
    nem láncolható, 7.4). A `kulcsszo_nyers.json` erre önmagában nem elég, mert
    14 napra nyesett (8.2). **A `meres_kezdete` visszafejthetősége azon áll,
    hogy a `tortenet.json` HALMOZÓDÓ (sosem nyesett) — ez szerződés (6.), nem
    véletlen. Ha a történet valaha retenciót kapna, a `meres_kezdete`-t attól
    kezdve perzisztálni kell, különben a mező némán elromlik.**
  - `aktiv`: igaz, ha a szó a mai `config.yaml` listáján van; hamis, ha csak a
    történetben él (eltávolított szó).
  - `meres_vege`: `null`, ha `aktiv`; egyébként a szó utolsó mért napja.

  Mindhárom **az exporterben, a történet + a config alapján** dől el, **nulla
  extra Google-hívással**, a `test_regresszio.py`-ban tesztelve. A felület
  ezekből írja ki a „mérés kezdete" és „már nem mérjük" jelölést, és tartja
  szét a 7.2 három élettartam-állapotát.
- **Nulla extra Google-hívás:** a számítás a már letöltött adatból dolgozik.
  A `tervezett_hivasszam` és a hívás-plafon (Phase 2.5) **nem változik**.

**Ismert korlát, tudatosan vállalva:** ez az irány nem támogatja a charton
belüli nagyítást újraszámolt regresszióval (az a képlet kettőzését
igényelné). Ha a nagyítás később mégis cél lesz, az a döntés újranyitása.

---

## 9. Task-lista

| # | Task | Függőség | Adat kell? |
|---|---|---|---|
| 1 | Teszt-politika átírása (`test_pages.py`) az 5. fejezet szerint | — | nem |
| 2 | JSON-szerződés tesztek, kétszintű + a 6. fejezet új tételei | — | nem |
| 3a | **Adatréteg:** kategória (`topics`+`temak`) megtartása a **`futtato.top_trend_struktura`**-ban (`futtato.py:29` — **ma ez dobja el**; a `json_export.legfrissebb_ir`/`napi_ir` csak továbbadja a kész struktúrát), a `legfrissebb.json` és `napok/*.json` trend-elemein; üres `topics` naplózása; szerződés-teszt. **Forrás:** trendspy `TrendKeyword.topics` (`list[int]`) + `.topic_names` (`list[str]`) — csak az **API-ág** (`gyujt_api`) objektumán; az RSS-ág `TrendKeywordLite`-ja egyiket sem adja. Ma csak a `.topic_names` olvasódik (`felkapott.py:26`, CSV `temak`), a `.topics` (int ID-k) még nem | 2 | nem |
| 3b | **Adatréteg:** `kategoriak.json` aggregátum upserttel, felület nélkül | 3a | nem |
| 4 | Grafikon-könyvtár döntés + vendorolás + `FORRAS.md` + hash-teszt | 1 | nem |
| 5 | Váz-HTML/CSS + adatbetöltő réteg: fetch, cache-busting, hibaállapotok | 1, 2 | nem |
| 6 | Kettéosztott dashboard váza + a két vezérlő (intervallum / dátum), elérhetőség-számítással | 5 | nem |
| 7 | Trend-blokk: lista + kategória-címke + opcionális szűrő | 3a, 6 | nem |
| 8a | Trend napi görbe: statikus rajzolás fix adattal | 4, 6 | nem |
| 8b | Trend napi görbe: interakció, tooltip, normalizálás-magyarázat | 8a | nem |
| 9a | **Adatréteg:** `kulcsszo_regresszio.json` (8.3) — illesztés, `reszleges` kihagyása, lyukas sorozat, `ervenyes`/`ok`; TDD + szerződés-teszt | 2 | nem |
| 9b | Kulcsszó-blokk: szavankénti chartok + a 9a mérőszámainak kiírása + üres állapotok | 9a, 6 | **1 nap elég** |
| 10 | Mobil-nézet + hozzáférhetőség | 7, 8b, 9b | nem |
| 11 | README-frissítés + whole-branch review | mind | nem |

**A Task 1 semmitől nem függ, és mindent blokkol** a piros teszt miatt —
ezzel kezdünk. A táblázat utolsó oszlopa a lényeg: **egyetlen task sem vár
adatgyűjtésre.** A 9b-hez egy napi pillanatkép elég (a 7 napos ablak
önmagában teljes), a hosszabb intervallumok pedig letiltott gombként
jelennek meg, amíg nincs láncolás.

A Task 9 kettébontása szándékos, és a 4.1 döntés után a vágás **rétegek
mentén** fut: a **9a adatréteg-munka** (Python, pytest, nulla frontend), a 9b
tiszta megjelenítés. Ezért a 9a **nem függ a grafikon-könyvtár döntésétől**
(Task 4), és **a Task 1-gyel párhuzamosan, ma elkezdhető** — egyedül a
szerződés-tesztektől (Task 2) függ.

---

## 10. Kockázatok

- **Háromféle normalizálás egy oldalon** (1.4). Vizuálisan és feliratban is
  el kell választani, különben a látogató összemérhetőnek hiszi őket. Ez a
  fázis legnagyobb helyességi kockázata.
- **A regresszió tekintélyt kölcsönöz — de MÉRT módon (2026-08-12) átkeretezve.** A v1
  feltevés („egy kiírt R² azt sugallja, hogy a szám megbízható; autokorrelált órás soron
  rendszeresen **MAGAS**") **empirikusan téves**: az R² **0,00–0,30** (őszintén alacsony)
  minden szónál. A hamis tekintély forrása tehát **az IRÁNYSZÓ** — a verdikt-erejű
  „Csökken"/„Növekszik" —, nem az R². A régi „(másodlagos)" címke **rossz irányba**
  ellensúlyozott (a becsületes, alacsony R²-t fokozta le). A felirat ellensúlya: az irány
  **leíró tendencia** (nem verdikt), az R² pedig **önmagyarázó legendával** áll, hogy a szám
  maga beszéljen (7.2).
- **13 chart egy oldalon** — teljesítmény, mobil-görgetés, lusta rajzolás
  (4.2).
- **Heterogén archívum.** A Task 3a után a `napok/` fájlok tartósan kétféle
  alakban léteznek (kategóriával és anélkül). **Végleges állapot, nem
  átmeneti.**
- **Nincs automatikus regressziós kapu** (v1 3. fejezet). Vállalt.
- **Vendorolt blob a repóban.** A hash-teszt és a `FORRAS.md` kezeli, a
  frissítés kézi marad.
- **Pages cache.** A `?v=Date.now()` a JSON-okét megoldja; a HTML/JS/CSS-re a
  Pages saját cache-viselkedése áll — deploy után hard reload.
- **A gyűjtés még nem stabil rezsimben van.** A 429-viselkedés jellemzése ~2 hét
  naplóra várt; a jelenség **létezése** 2026-08-11-én igazolódott: az új ágsorrenden
  az első éles **kapu-blokk** (`kulcsszo;blokkolva;5;429,429,429,429`, a `kormányablak`
  szónál), amivel a **Task 8 jegyzőkönyv §4** kapu-blokk-pontja beteljesült. **DE n=1:**
  egyetlen megfigyelt eset a rátát NEM jellemzi — a **429-ráta jellemzése NYITVA marad**,
  további napló kell hozzá. Egy-egy nap kiesése reális, a felületnek ezt el kell viselnie (7.5).
- **Elveszett nap = ZÖLD workflow (monitorozási vakság).** A 08-11-i futás státusza
  **Success** volt (`van_adat=True` → exit 0; az egyetlen warning Node.js-deprekáció).
  Egy elveszett kulcsszó-nap tehát **sem a CI-ben, sem a felületen** nem jelez — ez
  erősíti az L1-et (blokkolt nap jelzése, 7.5); a **blokkolt nap felületi jelzése** külön
  tétel (Phase 4).
- **MÉRT hívás-adat (a jövőnek):** a várt ~30 hívás helyett **7 tényleges** futott le
  (api 1 + rss 1 + `állás` 1 + `kormányablak` 4× 429). Ez a „minden kártyán legyen görbe"
  (+6 trend-idősor-hívás) döntés bemenete: **nem a hívás-plafon a korlát, hanem a
  429-rezsim** — a plafon (120) messze a tényleges terhelés felett van.
- **Python-verzió eltérés a teszt-futtatásban.** A fejlesztői venv 3.14, az
  átadó/CI-környezet (`napi.yml`) 3.12. Mivel a teszt-suite **nem CI-kapu**,
  hanem lokális eszköz (3. fejezet), a Phase 3 megnövelt pytest-felülete (Task
  2, 9a) a fejlesztői 3.14-en fut; egy verzió-függő eltérés csak átadáskor
  bukna ki. Task 9 környékén eldöntendő (venv 3.12-re igazítása, vagy explicit
  elfogadás). Ledgerből áthozva.

---

## 11. Nyitott kérdések

1. **Grafikon-könyvtár — LEZÁRVA** (2026-08-05, Task 4, commit 0c76b78):
   vendorolt **Chart.js 4.5.1** (MIT), `docs/vendor/FORRAS.md` sha256-tal +
   hash-teszttel; a 13-chart teljesítményét a lusta (viewportba érés szerinti)
   rajzolás kezeli (Task 9b, #3 döntés).
2. **Tartósan üres/gyenge kulcsszó-chart — LEZÁRVA** (2026-08-06, Task 9b #4 +
   7.5): NEM elrejtés → explicit üres állapot. Adat nélküli intervallumon a szó
   `.ures` magyar üzenetet kap (7.5); a mért-de-csupa-nulla szó a lapos görbét +
   informatív feliratot (szigorú „minden lezárt pont = 0" küszöb). A puszta
   elrejtés elvetve (a „soha nem törlünk" ígéretet mosná el). Ide tartozik a §4.2
   `napelem`-gyenge-szó kérdése is.
3. **Csoportosítás — LEZÁRVA** (2026-08-06, Task 9b #2): IGEN, `domen` szerint
   (nem `tipus`), slug→magyar fejléc-térképpel; `domen: null` → „Egyéb", a lista
   végén.
4. **A `kulcsszo_osszesites` sorsa — LEZÁRVA** (2026-08-12, grep-igazolt): a
   **felület NEM használja** (`docs/js/` + `docs/index.html` = nulla hivatkozás);
   egyetlen termelője a `json_export.py`, a `legfrissebb.json` hordozza, fogyasztó
   nélkül. A frontend a mérőszámokat a `kulcsszo_regresszio.json`-ból veszi (9a/9b).
   Az export ettől még kiírja — **ártalmatlan holt-adat**; az eltávolítása opcionális
   takarítás (Phase 4 jelölt), nem Phase 3-ügy. A „nem közöl szavak közti rangsort"
   invariáns áll (1.4).
5. **A nyers fájl retenciós ablaka — LEZÁRVA** (2026-07-31, kód-ellenőrzés).
   **Nincs `config.yaml`-kulcs.** Az érték a `nyers_kimenet.ir_gordulo`
   `megtartott_nap: int = 14` **kód-szintű alapértelmezése** (nem konfig). A
   retenció **adat-relatív**: a legkésőbbi `ablak_veg_utc`-hez képest vágja a 14
   napnál régebbi rekordokat, nem faliórához (`nyers_kimenet.py:103,147`). Ez
   szabja meg, meddig számolható a nyers fájlból visszamenőleg a láncoló (8.2):
   **~14 nap**. Ha ennél mélyebb visszatekintés kell, a kumulált skálázót külön,
   tartós kimenetbe kell menteni (8.2).
6. **A kettéosztott dashboard mobilon — LEZÁRVA** (2026-08-12, a §7.1
   per-szekció elrendezésből + a leszállított kódból). **Döntés: a két vezérlő a
   SAJÁT blokkja fölé kerül** (NEM összecsukható fejléc). Megvalósítás: minden
   szekció a saját `.vezerlo-sav`-jában hordozza a vezérlőjét (asztalin balra,
   `position: sticky`, `flex: 0 0 14rem`); mobilon a `@media (max-width: 900px)` a
   `.szekcio`-t **flex-column**-ná teszi, a `.vezerlo-sav` `position: static;
   flex: 0 0 auto` → a vezérlő a saját blokkja **fölé** kerül (`docs/css/app.css:20-24`,
   `docs/index.html` per-szekció `.vezerlo-sav`). A **7.1 szétválasztottság mobilon
   is megmarad** (a két vezérlő nem olvad össze egy fejlécbe). A Task 10 ehhez az
   érintési célméretet (coarse pointer) és a fókusz-láthatóságot adta, **nem** a
   layout-döntést. (A döntés eddig csak kódban élt; ezért rögzítjük itt is.)

7. **A nyers retenció-horgony robusztussága (Minor 2, Task 6-ból áthozva).**
   Az `ir_gordulo` a retenciós határt `max(ablak_veg_utc) − megtartott_nap`-ként
   számolja (adat-relatív, 11.5). Két kockázat, amit Phase 3-nak a
   láncolás-szemantikával együtt el kell döntenie:
   **(a) befagyás** — ha a producer huzamosan elavult ablakot ad vissza, a
   horgony az adat-időhöz tapad, nem a faliórához, így a régi rekordok a
   vártnál tovább maradnak (N adat-nap ≠ N naptári nap);
   **(b) egyetlen jövőbeli `ablak_veg_utc` kivágja a történetet** — egy
   séma-érvényes, de jövőre datált rekord `max(vegek)`-ké válik, a határ
   előreugrik, és a valódi múlt kiesik; a karantén nem fogja meg (séma-érvényes).
   Ma a producer nem datál jövőt (a részleges farok az aktuális óra), de egy
   sérült/kézzel írt legacy-fájl vagy Trends-fura kiválthatja. Lehetséges
   mitigáció: a horgony clamp-elése `min(max(vegek), most)`-ra, vagy a
   jövő-datált rekordok kizárása a horgony-számításból (akár karantén-szabály:
   `ablak_veg_utc > most + tűrés` → gyanús). Task 6-ban **szándékosan** kihagyva
   (hatókör); itt csak rögzítve. **Eldöntendő legkésőbb a Phase 4 láncolás
   tervezésekor**, mert a lánc a nyers előzményre épül, és a (b) forgatókönyv
   visszaállíthatatlan adatvesztést okoz (a gördülő fájlban a törölt rekordok
   már nincsenek meg). Ha a döntés a clamp vagy a karantén-szabály, az onnantól
   **TASK, nem nyitott kérdés.**
8. **Azonos-doménű kulcsszavak jelentés-átfedése (Task 1-ből áthozva).** A
   `betegség` és `kórház` (mindkettő `egeszseg` domén) mérheti ugyanazt a
   szezonális hullámot. Eldöntése **nem** a frontend dolga (mindkettő külön
   chartot kap, 7.2), hanem utólagos elemzésé: két külön szóló `today 12-m`
   lekérdezés + Pearson-r (átskálázásra érzéketlen) + csúcs-hónap egybeesés —
   **nem közös hívással** (az a horgony-hibát reprodukálná). Phase 3 vagy egy
   későbbi nappali mérő-sáv döntheti el; a felületet nem befolyásolja. Azért
   **itt** rögzítve, mert a ledger gitignore-olt (nincs verziókövetve), a
   tartós tételek helye a specben van.

*(A „regresszió helye" kérdés a 4.1-ben lezárva: exportban, Pythonban.)*

---

## 12. Megjegyzés az implementernek

Ez a dokumentum a v1 specből, a Phase 2.5 lezáró dokumentumaiból (Task 8
jegyzőkönyv, README, ledger) és a 2026-07-30-i első éles futás mért
adataiból készült. **Nem látta** a `tests/test_pages.py`, a `json_export.py`,
a `kulcsszavak.py`, az `idosorok.py` és a `config.yaml` pontos tartalmát —
ezek ellenőrizendők. A file:line hivatkozások a Phase 2.5 review-ból
származnak, és elavulhattak.

**Ha eltérés van, ez a dokumentum javítandó, nem a kód igazítandó hozzá.**
