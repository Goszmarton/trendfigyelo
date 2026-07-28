# Phase 3 — Specifikáció: interaktív honlap

Állapot: **vázlat, jóváhagyásra vár**
Dátum: 2026-07-26
Előzmény: Phase 1 (adatréteg) és Phase 2 (közzététel + automatizálás) lezárva.
A **Phase 2.5** (kulcsszó-mérés helyreállítása) ezzel párhuzamosan fut; az
alábbi kulcsszó-feature attól függ, a többi nem.

---

## 1. Kiindulás

A `docs/index.html` ma statikus, JS-mentes placeholder, amelyet a
`tests/test_pages.py` őriz. Az adatréteg viszont naponta három JSON-t publikál,
amelyeket semmi nem jelenít meg.

Architektúra-adottság: GitHub Pages statikus kiszolgálás, nincs backend.
Minden megjelenítés kliensoldali JavaScript.

### 1.1 Mit tudunk az adatról (mérés, nem feltételezés)

**A trend- és a kulcsszó-adat két külön időtartományban él, amelyek
szerkezetileg eltérnek, és sosem fognak találkozni.** A `tortenet.json` a
kulcsszavakat visszafelé építi (429-önjavítás), de előre **egy teljes napot
lemarad**; a `napok/index.json` a trendeket csak előre építi, a feature
indulásától. A lyuk mérete **állandó** — 2 árva nap elöl (kulcsszó nélküli
trendnapok), 1 hátul (trend nélküli kulcsszónap) —, az átfedés viszont a
felhalmozódással **nő**. **Ez nem hiba:** a szerződés-teszt rögzítse így,
különben valaki később „javításból" eldobja a legújabb trendlistát vagy a
legrégebbi kulcsszónapokat.

Pillanatfelvétel a konkrét számokhoz — a **dátumok holnapra elavulnak, a fenti
szerkezet nem** (2026-07-26-i állapot):

| Fájl | Lefedett napok (2026-07-26-kor) | Megjegyzés |
|---|---|---|
| `tortenet.json` | 07-21 … 07-25 (5 nap) | Visszafelé nő, előre egy napot lemarad |
| `napok/index.json` | 07-23 … 07-26 (4 nap) | Csak előre nő |
| `legfrissebb.json` trendek | 07-25 19:04 – 07-26 19:04 | 8 perces felbontás, ~181 pont/trend |
| `legfrissebb.json` kulcsszavak | 07-24 22:00 – 07-25 21:00 UTC | = a 07-25-i teljes budapesti nap |

Az átfedés ebben a pillanatban ~40% eltérés volt; egy hónap felhalmozódás után
~8% lesz — a *szám* csökken, a szerkezeti lyuk nem tűnik el.

További megállapítások a fájlokból:

- **Nincs `kategoria` mező** sehol — a Task 3a indokolt.
- **Az idősor kétszer szerepel** a `legfrissebb.json`-ban: `top_trendek[].idosor`
  és `trend_idosorok` ugyanaz az adat, más alakban.
- **`hir_kep` külső URL-ekre mutat** (`encrypted-tbn*.gstatic.com`).
- **`volumen` és `novekedes_pct` string**, nem szám; a `novekedes_pct` szinte
  mindenütt `"1000"` — felső korlát, nem mérés.
- **Csoportnév-inkonzisztencia**: `megelhetes` ékezet nélkül, `gazdaság` és
  `közélet` ékezettel.
- A `tortenet.json` **nap-kulcsú** (`napok[].kulcsszavak[]`), nem kulcsszó-kulcsú.
- A `hirek` tömb többnyire üres; ahol nem, ott a `hir_ido_utc` és `hir_kivonat`
  üres string.
- **A kulcsszó-réteg jelenlegi tartalma használhatatlan** — lásd a Phase 2.5
  specet. Ez a fázis nem próbálja megjeleníteni.

---

## 2. Célok

1. **Napi felkapott trendek listája** a `legfrissebb.json`-ból, kategória-címkével.
2. **Felkapott trend napi görbéje** — itt él az „alapszint + csúcs" kettősség,
   8 perces felbontású, kifejező adaton.
3. **Dátumválasztó** a trend-archívumhoz, az `index.json` alapján.
4. **Kulcsszó napi görbéje** — *fagyasztva a Phase 2.5 lezárásáig* (7.4).

---

## 3. Nem-célok

- **PR-check CI workflow.** A `napi.yml` adatgyűjtő workflow marad, ami —
  helyesen — nem futtat tesztet. A teszt-suite (Playwrighttal együtt) **lokális
  fejlesztői eszköz marad.** Vállalt kompromisszum: nincs automatikus
  regressziós kapu; ezt a no-commit protokoll és a review-agentek fogják meg.
  Ha később mégis kell, a helyes vágás: gyors Python-tesztek CI-ban, Playwright
  lokálisan.
- **Többnapos kulcsszó-történet.** A Phase 2.5 után a skála napok között ugrik
  (lásd ott az 5. fejezetet); a többnapos idősor a **láncolással** jön vissza,
  egy későbbi fázisban.
- **A `napok/*.json` archívum visszapótlása kategóriával.** A per-futás CSV-k
  nincsenek gitben; a backfill részleges és nem reprodukálható lenne. A régi
  napok tartósan kategória nélkül maradnak.
- **Gyűjtés-oldali módosítás.** Az a Phase 2.5 dolga.
- Backend, adatbázis, felhasználói fiókok, analitika.

---

## 4. Döntések

### 4.1 Eldöntött

| Döntés | Választás | Indoklás |
|---|---|---|
| Dátumválasztó hatóköre | Csak a trend-archívum | Más időszemantika: „válassz egy napot" vs. „lásd a sorozatot" |
| Tartomány-eltérés | Legitim, tesztben rögzítve | Szerkezeti, nem hiba (1.1) |
| Kategória tárolása | **Kettős: `topics` (`list[int]`) + `temak` (`list[str]`)** | Adathűség és olvashatóság együtt (7.1); a magyar címke a frontendben cserélhető |
| Cache-busting | `?v=` + `Date.now()` | Az aznapi dátum lyukas: a 21:07-es publikálás után a reggel betöltött URL cache-ből jönne |
| Hírbélyegképek | **Nem jelenítjük meg** | A `hir_kep` külső origó; így a tesztpolitika tiszta marad, és nem függünk a Google képgyorsítótárától |
| Feliratok nyelve | Minden magyarul | — |
| Playwright hol fut | Lokálisan | A PR-check nem-cél |

### 4.2 Nyitott

**Grafikon-könyvtár (Task 4-ig ráér).** Alapértelmezett javaslat: **vendorolt
Chart.js 4.x**, pinelt verzióval és hash-teszttel. Az érv aszimmetrikus: saját
SVG esetén a tooltip hit-testing, a mobil érintéskezelés és a tengelyskálázás
minden sora saját tesztelendő kód; Chart.js esetén az ár egyetlen hash-teszt.
Elvetve: CDN (külső origó, és kiesés esetén viszi a honlapot).

**Playwright bevezetése (Task 5-ig ráér).** Alapértelmezett javaslat: **igen.**
A JSON-szerződés-tesztek Pythonban amúgy is kellenek; a grafikonra viszont
böngésző nélkül csak vacuous RED írható — abból Phase 2-ben már volt egy.

---

## 5. A teszt-politika átalakítása

A jelenlegi `tests/test_pages.py` invariánsa („nincs JS az oldalon") Phase 3-ban
szükségszerűen megbukik. **Ez nem felpuhítás, hanem az invariáns
újrafogalmazása a valós fenyegetésre:** az eredeti szándék sosem a JS tiltása
volt, hanem a harmadik felek kizárása — tracker, idegen kód, supply chain.

Új invariáns: **csak saját és vendorolt eszköz, semmi külső betöltés.**

1. **Erőforrás vs. navigációs link.** Minden *betöltött* erőforrás
   (`script src`, `link rel=stylesheet`, `img src`, `iframe src`) kizárólag
   relatív útvonal lehet. Az `<a href>` navigációs link mehet kifelé.
2. **Inline script tiltott.** `<script>` csak `src` attribútummal, és az `src`
   létező fájlra mutasson. Mellékhatás: a JS külön fájlba kerül → lintelhető.
3. **Nincs inline event handler** (`onclick=` stb.) — `addEventListener` kötelező.
4. **Nincs `javascript:` URL.**
5. **Nincs külső URL a saját JS-ben** — grep a `docs/js/` fájljain, üres
   allowlisttel. Így a `fetch` sem szökhet ki.
6. **Vendorolt fájlok nyilvántartása.** Minden `docs/vendor/` alatti fájlhoz
   kötelező bejegyzés a `docs/vendor/FORRAS.md`-ben: forrás-URL, verzió, licenc,
   sha256. A teszt a **tényleges hasht** ellenőrzi.

A politika generikus: ha végül saját SVG lesz Chart.js helyett, a
`docs/vendor/` üresen marad, és a hash-teszt nulla fájlon fut le.

---

## 6. Tesztelési stratégia

Három réteg, mind lokálisan:

- **Strukturális tesztek (pytest, gyors)** — az 5. fejezet szabályai a `docs/`
  fájljain.
- **JSON-szerződés tesztek (pytest, gyors).** Ma hiányoznak, és a frontend
  ezekre épül. **Két szintre bontva**, különben a kategória miatt vagy
  törékeny, vagy vacuous lesz:
  - *Exporter-szint:* a `json_export` kimenete fixtúra-bemenetből — a `topics`
    és `temak` kulcs **kötelezően jelen van**, típusa **lista** (`int`, illetve
    `str`), és `len(topics) == len(temak)`. **Az üres tömb ([]) érvényes** — a
    nem-üresség NEM követelmény (65 sorból 0 üres, de egyetlen futás nem
    garancia). Ez a valódi szerződés.
  - *Archívum-szint:* a lemezen lévő `napok/*.json` — a mező **opcionális** (a
    régi napokban nincs), de ha jelen van, a fenti típus- és hossz-kötés áll.

  Rögzítendő továbbá: a string-típusú `volumen`/`novekedes_pct`, a nap-kulcsú
  `tortenet.json` alak, és a két tartomány **legitim** eltérése (1.1).
- **Playwright smoke-tesztek (lassú, kevés).** Nem 40 böngészőteszt, hanem a
  gerinc: a feature-ök működése, a hibaállapotok, és a cache-busting paraméter
  jelenléte a kimenő kéréseken.

---

## 7. Feature-ök

### 7.1 Napi felkapott trendek listája

- Forrás: `legfrissebb.json` → `top_trendek`
- **Kategória-címke** minden elemen (Task 3a után). A kategória **nem egyetlen
  érték, hanem tömb** — egy trend több témába is tartozhat. A JSON kettőt tárol:
  `topics` (nyers `list[int]` ID-k) és `temak` (`list[str]` angol nevek); a
  magyar címke a frontend leképezési táblájában él, ID vagy angol név alapján.
  Ismeretlen ID-nél (`"Unknown Topic (<id>)"`) a nyers érték jelenjen meg — jobb
  egy angol szó vagy egy ID, mint egy eltűnt információ.
- **A szűrő többértékű:** egy trend egyszerre több kategóriában is megjelenhet.
- **Három állapot, külön kezelve:**
  - `[]` → **nincs besorolás** (a trendnek nincs top-ja),
  - `[11]` / `["Other"]` → **valódi „Other" kategória** — nem hiányzó adat,
  - a mező hiánya → **régi archív nap**, amelyben még nem volt kategória-réteg.
- **A felületen** a `[]` és a hiányzó mező egyaránt „egyéb"/címke nélkül
  jelenhet meg; **az adatban viszont a három állapot maradjon
  megkülönböztethető** (üres tömb ≠ hiányzó mező ≠ `Other`).
- **Opcionális kategória-szűrő.** Ha a betöltött napon egyetlen elemen sincs
  kategória, a szűrő **ne jelenjen meg**, vagy legyen letiltva — különben
  működésképtelennek látszik. Ez tesztelendő eset.
- **Hírek:** cím + forrás + link, **kép nélkül** (4.1). Az üres `hirek` tömb a
  normális eset, nem hiba.
- **Üres állapot:** ha a legutóbbi futásban egy ág feladta (`AgFeladva`), a
  lista lehet rövid vagy üres — ezt magyarul, érthetően kell közölni, nem néma
  üres dobozzal.

### 7.2 Felkapott trend napi görbéje

- Forrás: `top_trendek[].idosor` (~181 pont, 8 perc)
- **Itt él az eredeti ábra-ötlet:** alapszint mint folytonos vonal, napi csúcs
  kiemelve. Ezen az adaton a kettősség tényleg látszik.
- **Minden trend a saját maximumára normalizált — és ez helyes tervezés, nem
  hiba.** Mind a tizenöt trend pontosan eléri a 100-at. Közös skálán a 2000-es
  volumenű trendek 10 körül lapulnának, és a görbéjük olvashatatlan lenne:
  pontosan a kulcsszavak betegsége állna elő. Az önnormalizálás ez ellen véd.
- A felkapott lista naponta kicserélődik, **nincs folytonosság, amit meg
  kellene őrizni** — a kereszt-összehasonlíthatóság itt nem elvárás. A
  nagyságrendet a `volumen` és a lista sorrendje hordozza.
- **Egyetlen megkötés, feliratozási szintű:** ha több trend kerül egy ábrára, a
  tengely mondja ki, hogy relatív skála. Több görbét egymásra tenni legitim, ha
  a kérdés az, hogy **mikor** csúcsosodtak. Csak a „melyik volt nagyobb"
  olvasat hamis, és ezt kell megelőzni: kiírt `volumen` vagy egyértelmű felirat.
- Ismert korlát, nem javítandó: a magnitúdót egyedül a `volumen` hordozza, négy
  szinten (2000 / 5000 / 10000 / 20000). A `novekedes_pct` használhatatlan.
- A `trend_idosorok` tömb ugyanazt az adatot tartalmazza; a frontend **az
  egyiket használja**, ne mindkettőt töltse be.

### 7.3 Dátumválasztó / trend-archívum

- Forrás: `napok/index.json`, majd `napok/YYYY-MM-DD.json`
- Csak az `index.json`-ban ténylegesen szereplő napok választhatók.
- Dátumformátum végig: `2026. 07. 26.`
- **Csak a trendekre vonatkozik** (4.1). A kulcsszavakat nem érinti.
- Nem létező nap kérése esetén érthető hibaüzenet, nem néma hiba.

### 7.4 Kulcsszó napi görbéje — FAGYASZTVA

Forrás: `legfrissebb.json` → `kulcsszavak`. Szerkezetileg ugyanaz, mint a 7.2:
egy kulcsszó napon belüli görbéje, átlaggal és csúccsal.

**Ma nem implementálható**, mert az adat a horgony miatt szinte végig nulla
(Phase 2.5, 1. fejezet). A Phase 2.5 lezárása után ez a feature **változatlan
formában** elővehető — a szóló lekérdezés pontosan ilyen alakú adatot ad.

Amit a specnek már most rögzítenie kell:

- **Nem többnapos történet.** A 7 napos ablakban a skálát a historikus maximum
  állítja be, és az ugrik, amikor a csúcs kicsúszik az ablakból. Többnapos
  vonal ebből hamis lépcsőt rajzolna.
- **A napi `atlag` és `csucs` nem jeleníthető meg követhető mérőszámként.**
  Ezek a szó saját heti maximumához viszonyulnak, ami naponta változhat — egy
  kiírt „átlag: 45" azt sugallná, hogy összevethető a tegnapival, pedig nem.
  A görbe és a relatív tengely becsületes; a kiemelt szám nem.
- **Felirat kötelező:** a kulcsszóadat a legutóbbi *teljes* napot mutatja,
  tehát egy napot késik a trendekhez képest (1.1). E nélkül a látogató tegnapi
  számokat néz mai címke alatt.
- **A kulcsszólista mozgó célpont.** Kivett szó árva sorozatot hagy a
  `tortenet.json`-ban (soha nem törlünk); új szó a felvétele napján kezd. A
  frontend a **ténylegesen előforduló** kulcsszavakból dolgozzon, ne beégetett
  listából.
- A törés előtti (Phase 2.5 előtti) napok **nem köthetők össze** a későbbiekkel.

### 7.5 Kategória-aggregátum (csak adatréteg, felület nélkül)

Új kimenet: `docs/data/kategoriak.json`. Phase 3-ban **nincs hozzá felület** — a
fájl azért készül most, hogy a történet a Task 3a élesítésétől épüljön.
Ugyanaz az upsert-logika, mint a `tortenet.json`-nál.

Tárolandó a **nyers darabszám ÉS a napi trendlista teljes hossza** is: a lista
hossza ingadozik (feladott ág → rövid lista), így a puszta darabszám félrevezet,
a részesedés viszont rövid listán ugrál. Kategória nélküli elemek külön
gyűjtőben, nem eldobva.

**Mivel a kategória többértékű** (7.1), egy trend több kategória darabszámába is
beleszámít — a kategóriánkénti darabszámok összege ezért **meghaladhatja a napi
lista hosszát**. A „kategória nélküli" gyűjtő a `[]` és a hiányzó mezős elemeké
(az `Other` nem ide tartozik: az valódi kategória).

---

## 8. Task-lista

| # | Task | Függőség |
|---|---|---|
| 1 | Teszt-politika átírása (`test_pages.py`) — az 5. fejezet szerint | — |
| 2 | JSON-szerződés tesztek, kétszintű (6. fejezet) | — |
| 3a | **Adatréteg:** a kategória (`topics: list[int]` + `temak: list[str]`) átvezetése a `json_export`-ban a `legfrissebb.json` és `napok/*.json` trend-elemeire; **üres `topics` naplózása** (7.1); + szerződés-teszt. Nulla extra hívás: az adat már a `trending_now` objektumon van, ma a `top_trend_struktura` dobja el | 2 |
| 3b | **Adatréteg:** `kategoriak.json` aggregátum upserttel (7.5), **felület nélkül** | 3a |
| 4 | Grafikon-könyvtár döntés + vendorolás + `FORRAS.md` + hash-teszt | 1 |
| 5 | Váz-HTML/CSS + adatbetöltő réteg: fetch, cache-busting (`?v=Date.now()`), hibaállapotok | 1, 2 |
| 6 | Felkapott trendek szekció + kategória-címke + opcionális szűrő | 3a, 5 |
| 7a | Trend napi görbe: statikus rajzolás fix adattal | 4, 5 |
| 7b | Trend napi görbe: interakció, tooltip, normalizálás-magyarázat | 7a |
| 8 | Dátumválasztó + trend-archívum | 5 |
| 9 | Mobil-nézet + hozzáférhetőség | 6, 7b, 8 |
| 10 | README-frissítés + whole-branch review | mind |
| F | *Kulcsszó napi görbe (7.4)* — **fagyasztva**, a Phase 2.5 után nyílik | Phase 2.5 |

A Task 1 egyik nyitott döntéstől sem függ, és amíg nincs kész, minden
frontend-munka blokkolva van a piros teszt miatt — **ezzel kezdünk.**

A Task 7 kettébontása szándékos: ez a legnagyobb falat, és bontatlanul
megismételné a Phase 2 Task 5-ös „egy task túl nagyra nő" jelenségét.

A Task 3a azért van korán, mert a frontend kategória-munkája (Task 6) csak
akkor tesztelhető valódi adaton, ha az export már előállítja a mezőt. A forrás
tisztázva: a trendspy `TrendKeyword.topics` (`list[int]` ID-k) és a belőle
származó `topic_names` (`list[str]`, a 21-elemű `TREND_TOPICS` táblából) — a
per-futás CSV-ben ez a `temak` oszlop. Külön „kategoria" mező nem létezik; a
`topics`/`temak` kettőse ez, és a `top_trend_struktura` ma eldobja.

---

## 9. Kockázatok

- **Háromféle normalizálás egy oldalon.** A trend-görbe a *saját kifejezés*
  napi maximumához, a `volumen` abszolút (de durva) skálán, a Phase 2.5 után
  pedig a kulcsszó a *saját heti* maximumához lesz normalizálva. Ezt vizuálisan
  és feliratban is el kell választani, különben a látogató összemérhetőnek hiszi
  őket.
- **A `trend_idosor_max` (Phase 2.5-config, ma 15) egyszerre vezérli a napi
  trendlista hosszát (7.1) és a lekért görbék számát (7.2).** Ha a Phase 2.5
  hívásszám-tartalékként lecsökkenti (pl. 5-re), a napi lista is rövidül, nem
  csak a görbék. Ismert csatolás, itt rögzítve, hogy a frontend **ne
  feltételezzen fix 15-öt** — a ténylegesen kapott elemszámból dolgozzon.
- **Nincs automatikus regressziós kapu** (3. fejezet). Vállalt.
- **Heterogén archívum.** A Task 3a után a `napok/` fájlok tartósan kétféle
  alakban léteznek (kategóriával és anélkül). Ez **végleges állapot, nem
  átmeneti** — a frontend és a szerződés-tesztek is erre épüljenek.
- **Vendorolt blob a repóban.** A hash-teszt és a `FORRAS.md` kezeli, de a
  frissítés kézi művelet marad.
- **Pages cache.** A `?v=Date.now()` a JSON-okét megoldja; a HTML/JS/CSS
  frissülésére a Pages saját cache-viselkedése vonatkozik — deploy után hard
  reloaddal érdemes ellenőrizni.

---

## 10. Megjegyzés az implementernek

Az 1.1 fejezet a publikált JSON-fájlok tényleges átolvasásából származik, de a
`tests/test_pages.py` pontos tartalmát, a `json_export` felépítését és a
`config.yaml` szerkezetét ez a spec **nem látta**. Ezek ellenőrizendők — ha
eltérés van, **ez a dokumentum javítandó, nem a kód igazítandó hozzá.**
