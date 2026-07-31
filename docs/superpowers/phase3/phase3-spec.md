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
| `legfrissebb.json` → `trend_idosorok` | ugyanaz más alakban (15 sorozat, 2700 pont) | 8 perc, `now 1-d` | **nem** |
| `legfrissebb.json` → `kulcsszavak`, `kulcsszo_osszesites` | a nap kulcsszó-metszete, `atlag`/`csucs` | napi aggregátum | — |
| `kulcsszo_nyers.json` | **kulcsszavanként nyers órás sorozat** | 1 óra, `now 7-d`, 169 pont/szó | **ez a láncolás bemenete** |
| `napok/YYYY-MM-DD.json` + `index.json` | trend-archívum | napi | csak előre nő |
| `tortenet.json` | kulcsszó-történet, nap-kulcsú | napi | visszafelé is nő (visszapótlás) |

Mért tények a 2026-07-30-i első éles szóló futásból (run `30578843096`):

- **Minden kulcsszó sorozata a saját maximumára normalizált** — mind a 12
  kiírt szó pontosan eléri a 100-at. Ugyanez igaz a 15 trend-idősorra.
- Az órás rács hiánytalan, duplikátum nélkül; minden időbélyeg **tz-aware
  UTC** (`+00:00`).
- **Az `ablak_veg_utc` minden szónál azonos**, mert a trendspy órahatárra
  igazít — a közös perem **szerkezeti**, nem a futás rövidségének
  következménye. A láncolás „közös perem" feltevése ezért tartható.
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
3. **`volumen`**: abszolút, de durva — négy szinten (2000 / 5000 / 10000 /
   20000), és **string típusú**. A `novekedes_pct` szinte mindenütt `"1000"`,
   azaz felső korlát, nem mérés → **használhatatlan**.

Ebből következik a fázis egyik alapszabálya, amely már a README-ben is
rögzítve van: **a kulcsszavak pontszámai egymással nem összemérhetők; közös
horgony nélkül rangsort (pl. „legnépszerűbb kulcsszó") nem képezünk.**

**Egy lekérdezésen belül viszont a skála konzisztens.** Ez a v2 kulcsfelismerése:
a `kulcsszo_nyers` egyetlen napi pillanatképe 169 órás pontot, azaz **7 teljes
napot** fed le, egyetlen normalizálás alatt. Ezen a hét napon belül a
sorozat alakja, iránya és meredeksége **értelmezhető** — láncolás nélkül is.

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
| Kiírt mérőszámok | Meredekség + irány **elsődlegesen**, R² **mellette**, nem helyette | Autokorrelált órás soron az R² rendszeresen magas anélkül, hogy bármit bizonyítana |
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

**A `napelem`-típusú gyenge szavak kezelése.** Lásd 7.6 — nem eldöntött,
hogy a tartósan üres chart elrejtendő-e vagy megjelenítendő üres állapottal.

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
  módon ingadozik (lásd 7.6) — a teszt **ne** kössön 13-ra.
- `modszertan_valtas`: ha jelen van, kanonikus `YYYY-MM-DD` **string**
  (a betöltő `.isoformat()`-tal normalizál; idő-komponens `KonfigHiba`).
- A `reszleges: true` **pontosan a záró órás ponton** áll, sehol máshol.

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

Három blokk, kétfelé osztott vezérlővel:

```
┌─────────────────┐  ┌───────────────────────────────────────┐
│ DASHBOARD       │  │ KULCSSZAVAK                           │
│                 │  │  13 külön chart, mindegyiken saját    │
│ ── felső ──     │  │  regresszióval + mérőszámokkal        │
│ intervallum:    │  │                                       │
│ 1 hét / 2 hét / │  └───────────────────────────────────────┘
│ 1 hó / 3 hó /   │
│ 1 év            │  ┌───────────────────────────────────────┐
│                 │  │ NAPI LEGFRISSEBB TRENDEK              │
│ ── alsó ──      │  │  aznapi szavak + görbék + kategória    │
│ dátumválasztó   │  │  REGRESSZIÓ NINCS                     │
│ (egy nap)       │  │                                       │
└─────────────────┘  └───────────────────────────────────────┘
```

A kettéosztás **szemantikai, nem esztétikai**: a felső vezérlő „lásd a
sorozatot", az alsó „válassz egy napot". A vezérlők **nem hatnak egymásra**
— ezt a felületnek vizuálisan egyértelművé kell tennie (elválasztó, külön
fejléc), különben a látogató azt hiszi, egy globális szűrőt állít.

### 7.2 Kulcsszó-blokk

- **Forrás:** `kulcsszo_nyers.json` (7 napos ablak), illetve hosszabb
  tartományhoz a láncolt sorozat (8.2, Phase 4-ig nem elérhető).
- **Kulcsszavanként külön chart.** Egy charton egy vonal. Több szó egy
  ábrára tétele **tilos** (1.4).
- **Lineáris regresszió** minden charton, a lezárt pontokra illesztve.
  Kiírandó: **meredekség** (irány + nagyságrend, egységgel: relatív
  pont / nap), és mellette **R²**. A tengely mondja ki, hogy **relatív skála**.
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

### 7.3 Trend-blokk

- **Forrás:** `legfrissebb.json` → `top_trendek` (a `trend_idosorok` ugyanaz
  az adat más alakban — a frontend **az egyiket** használja, ne mindkettőt
  töltse be).
- **A lista kizárólag az API-ágból épül.** A `futtato.top_trend_struktura`
  (`futtato.py:47`) csak az `api_trendek`-et rendezi és vágja top-N-re; az
  RSS-ág (`rss_trendek`) **csak a `hirek`-et párosítja** kifejezés szerint,
  listaelemet nem ad. Ezért **minden friss-napi elem kategória-képes** (az
  `api_trendek` `TrendKeyword`-jén ott a `topics`/`topic_names`), és **nincs
  negyedik állapot** a kategória-címke három esete mellett. Ha az API-ág
  kapu-blokk vagy bukás miatt nem ad adatot, a lista **üres vagy rövid** (7.5),
  nem pedig kategória nélküli — ezt a felület a 7.5 üres-állapotával kezeli.
- **Regresszió nincs.** A felkapott lista naponta kicserélődik, nincs
  folytonosság, amit meg kellene őrizni; egy trendvonal itt értelmetlen.
- **Kategória-címke** minden elemen (Task 3a után), a v1 7.1 három
  állapotával: `[]` = nincs besorolás, `["Other"]` = valódi „Other"
  kategória, hiányzó mező = régi archív nap. A felületen a `[]` és a hiányzó
  mező egyaránt „egyéb"; **az adatban a három maradjon megkülönböztethető**.
- **Többértékű szűrő**: egy trend több kategóriában is megjelenhet. Ha a
  betöltött napon egyetlen elemen sincs kategória, a szűrő ne jelenjen meg
  vagy legyen letiltva.
- **Görbe:** a v1 7.2 szerint — alapszint mint folytonos vonal, napi csúcs
  kiemelve; az önnormalizálás itt **helyes tervezés**, mert közös skálán a
  2000-es volumenű trendek 10 körül lapulnának. Több görbe egy ábrán legitim,
  **ha a kérdés az, hogy mikor csúcsosodtak** — a „melyik volt nagyobb"
  olvasatot felirattal vagy kiírt `volumen`-nel kell megelőzni.
- **Hírek:** cím + forrás + link, kép nélkül. Az üres `hirek` tömb a normális
  eset.
- **Ne feltételezz fix 15 elemet** — a `trend_idosor_max` konfigurálható, és
  egy feladott ág rövid listát hagy.

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

A letiltott gomb **magyarázatot adjon** (pl. „ehhez még nincs elég mért nap"),
ne csak szürkén álljon; a szöveg az `ok` mezőből származhat. A kulcsszó-történet
gyakorlatilag **2026-07-30-nál kezdődik**: a `modszertan_valtas` előtti napok
horgonyos módszertanúak, és **nem köthetők össze** a későbbiekkel.

**Alsó (trend) — dátumválasztó.** A v1 7.3 változatlanul: forrás
`napok/index.json`, majd `napok/YYYY-MM-DD.json`; csak az `index.json`-ban
ténylegesen szereplő napok választhatók; dátumformátum végig `2026. 07. 26.`;
nem létező nap kérése esetén érthető hibaüzenet.

**Felirat kötelező** a két blokk eltérő frissességéről: a kulcsszóadat a
legutóbbi *teljes* napot mutatja, tehát egy napot késik a trendekhez képest
(1.3). E nélkül a látogató tegnapi számokat néz mai címke alatt.

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

### 8.3 Regressziós kimenet (`kulcsszo_regresszio.json`)

A regresszió **az exportban, Pythonban** számolódik, a napi futás részeként, a
`kulcsszo_nyers.json` (és később a láncolt sorozat) alapján. A frontend ezt a
fájlt betölti és **kirajzolja** — nem számol.

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
      "1_het": {
        "ervenyes": true,
        "ablak_kezdet_utc": "2026-07-24T21:00:00+00:00",
        "ablak_veg_utc":   "2026-07-31T20:00:00+00:00",
        "meredekseg_nap": -2.14,
        "r2": 0.31,
        "pontok_hasznalt": 168,
        "pontok_kihagyva_reszleges": 1,
        "pontok_hianyzo": 0
      },
      "2_het": { "ervenyes": false, "ok": "nincs_lancolas" }
    }
  }
}
```

Szerződés-tételek:

- A **meredekség egysége relatív pont / nap**, és a felületnek ezt ki kell
  írnia — a nyers szám önmagában félrevezető (1.4).
- A `pontok_kihagyva_reszleges` és a `pontok_hianyzo` **kötelező mező**, mert
  a felület ezekből tudja megmondani, hány napból hány mért (7.5).
- Az `ervenyes: false` ághoz **kötelező `ok`** (pl. `nincs_lancolas`,
  `keves_pont`, `nincs_adat`), hogy a letiltott gomb magyarázatot adhasson.
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
- **A regresszió tekintélyt kölcsönöz.** Egy kiírt R² azt sugallja, hogy a
  szám megbízható. Autokorrelált órás soron ez rendszeresen félrevezet — a
  feliratozásnak ezt ellensúlyoznia kell (mit mér, mit nem).
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
- **A gyűjtés még nem stabil rezsimben van.** A 429-viselkedés
  jellemzése ~2 hét naplóra vár; addig egy-egy nap kiesése reális, és a
  felületnek ezt el kell viselnie (7.5).
- **Python-verzió eltérés a teszt-futtatásban.** A fejlesztői venv 3.14, az
  átadó/CI-környezet (`napi.yml`) 3.12. Mivel a teszt-suite **nem CI-kapu**,
  hanem lokális eszköz (3. fejezet), a Phase 3 megnövelt pytest-felülete (Task
  2, 9a) a fejlesztői 3.14-en fut; egy verzió-függő eltérés csak átadáskor
  bukna ki. Task 9 környékén eldöntendő (venv 3.12-re igazítása, vagy explicit
  elfogadás). Ledgerből áthozva.

---

## 11. Nyitott kérdések

1. **Grafikon-könyvtár** — Chart.js vendorolva vs. saját SVG (4.2), a 13
   chart teljesítményével együtt mérlegelve.
2. **Tartósan üres kulcsszó-chart** — elrejtés vagy üres állapot (4.2).
3. **A `domen`/`tipus` melyike csoportosítson** a kulcsszó-blokkban, és
   legyen-e egyáltalán csoportosítás az első körben.
4. **A `kulcsszo_osszesites` sorsa** — a Task 9 review megállapította, hogy
   ma nem közöl szavak közti rangsort, és így is kell maradnia; eldöntendő,
   hogy a felület használja-e egyáltalán.
5. **A nyers fájl retenciós ablaka — LEZÁRVA** (2026-07-31, kód-ellenőrzés).
   **Nincs `config.yaml`-kulcs.** Az érték a `nyers_kimenet.ir_gordulo`
   `megtartott_nap: int = 14` **kód-szintű alapértelmezése** (nem konfig). A
   retenció **adat-relatív**: a legkésőbbi `ablak_veg_utc`-hez képest vágja a 14
   napnál régebbi rekordokat, nem faliórához (`nyers_kimenet.py:103,147`). Ez
   szabja meg, meddig számolható a nyers fájlból visszamenőleg a láncoló (8.2):
   **~14 nap**. Ha ennél mélyebb visszatekintés kell, a kumulált skálázót külön,
   tartós kimenetbe kell menteni (8.2).
6. **A kettéosztott dashboard mobilon** — a tervrajz asztali elrendezés
   (bal sáv + két jobb panel). Mobilon a bal sáv nem maradhat sáv; el kell
   dönteni, hogy a két vezérlő a saját blokkja fölé kerül-e, vagy egy
   összecsukható fejlécbe. A Task 10 ezt megvalósítja, de a **döntés** ide
   tartozik, mert a két vezérlő szétválasztottsága (7.1) mobilon is
   megőrzendő.

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
