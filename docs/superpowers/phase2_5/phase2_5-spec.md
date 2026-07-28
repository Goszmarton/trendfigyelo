# Phase 2.5 — Specifikáció: a kulcsszó-mérés helyreállítása

Állapot: **vázlat, jóváhagyásra vár**
Dátum: 2026-07-27
Előzmény: a Phase 3 előkészítése közben kiderült, hogy a kulcsszó-ág
használhatatlan adatot termel. Ez a fázis azt javítja meg. A Phase 3
kulcsszó-részei addig fagyasztva; a felkapott trendekre épülő részek haladnak.

---

## 1. Mi a baj

A `tortenet.json` öt napja alatt a 22 konfigurált kulcsszóból **11 fordul elő
valaha** (`MNB`, `albérlet`, `egészségügy`, `forint árfolyam`, `kormány`,
`kórház`, `lakáshitel`, `nyugdíj`, `pedagógus`, `tüntetés`, `választás`), és az
értékek túlnyomó része a kvantálási padló: a nyers 1-es érték normalizált képe,
ami naponta más (3,72 / 3,61 / 3,35 / 3,79 / 4,15).

### 1.1 Nem volumenhiány, hanem skálaösszenyomás

Kézi Google Trends mérések (Hungary / keresési kifejezés):

- **`albérlet` szólóban, 7 nap:** folytonos, sima görbe 35 és 100 között, több
  tucat szinten, felismerhető napi ritmussal.
- **`MNB` szólóban, 7 nap:** tiszta munkanapi ciklus, öt csúcs 80–100 között,
  éjszakára szabályos lenullázódás.
- **`albérlet` + `időjárás` egy lekérdezésben:** „Átlagos érdeklődés"
  **1 vs 49.**

A bizonyíték nem az, hogy a szóló görbék elérik a 100-at — azt definíció
szerint elérik. A bizonyíték a **simaság és a felbontás**: ilyet csak nagy
mintából lehet előállítani.

### 1.2 A horgony elve is hibás volt

Az „időjárás" **definíció szerint eseményvezérelt** — egy viharos nap felviszi,
és attól minden mért kulcsszó látszólag lejjebb kerül. A napi padló öt nap
alatt 3,35 és 4,15 között mozgott: **24% sodródás**, ami mérésnek álcázva
jelenik meg minden kulcsszó idősorában.

Az „időjárás" nemcsak az albérletnél nagyobb: a végleges lista **legnagyobb**
szavánál (`állás`) is nagyjából tízszeres. A horgony mellett tehát egyetlen
kulcsszó sem élhetett volna túl.

### 1.3 Horgonyjelöltek — miért nem járható ez az út

Egy jó horgonynak **egyszerre három** feltételt kellene teljesítenie:
független a mért témáktól, stabil, és méretben illeszkedő. Az „időjárás" csak
az elsőt teljesíti.

Három jelölt mérve (albérlet = 1,00): `térkép` 7,8×, `névnap` 5,3×,
`horoszkóp` 3,2×. Mind a legnagyobb sávba esik, egyik sem oldja meg a kisebb
szavakat. A `névnap` külön is kiesett: július 26-án (Anna–Anikó) 25–50-ről
100-ra ugrik — naptárvezérelt. A `térkép` és a `horoszkóp` marad, de mindkettőn
~1,6-szeres heti lengés van, és **egy horgony heti ritmusa minden mért
kulcsszóba beleíródik.**

Teljesen lapos szó nem létezik, ezért ez az út elvi okból zsákutca.

### 1.4 A megfogalmazás önálló probléma

`forint` vs `forint árfolyam` egy lekérdezésben: **66 vs 9**, azaz 7,3-szoros
különbség. Egy szó hozzátoldása nagyságrendet vesz el — de a `forint árfolyam`
így is ≈0,90× albérlet, tehát **nem mérhetetlen, csak kicsi**, és a szűkebb
kifejezés *validabb*. A rövidítés lehetőség, nem kötelező javítás.

---

## 2. A kulcsszólista

### 2.1 Az elv

Egy out-of-sample vizsgálat szerint a keresési adatok megőrzik előrejelző
értéküket a **munkanélküliségre**, de a **fogyasztói árindexre és a fogyasztói
bizalomra nem**. Az indoklás: az online keresés viszonylag megbízhatóan jelzi
az egyén *saját helyzetét*, de kevésbé olyan változókat, amelyeket az egyén nem
ismer (CPI), vagy amelyek túl általánosak konkrét kifejezéshez kötni
(fogyasztói bizalom).

**Ebből következik a lista vezérelve: minden kulcsszó valakinek a saját
helyzete legyen, ne absztrakció.** Ezért esett ki az `infláció`, a
`munkanélküliség` és az `adóváltozás` — nem azért, mert kevesen keresik, hanem
mert az infláció nem az egyén saját helyzete.

**Fontos következmény a projekt céljára:** a Google Trends **viselkedést mér,
nem véleményt.** A „lakossági vélemény" mint cél a kutatás szerint nem
elérhető. Ami elérhető: mivel foglalkoznak az emberek konkrétan. Ezt a keretet
a honlapnak is vállalnia kell.

Magyar-specifikus bizonyíték: egy visegrádi tanulmány a magyar
munkanélküliségre az **„állás"** szót használta, és külön kiemeli, hogy jobban
működik, mint a „munka". A nowcasting korrigált R² 0,359-ről 0,447-re nőtt.
Fenntartás: négy országból háromnál találtak Granger-oksági kapcsolatot,
**Magyarország volt a kivétel** — itt együttmozgás van, nem bizonyított
előrejelzés.

### 2.2 A lista

| Domén | Kulcsszó | Karakter | Megjegyzés |
|---|---|---|---|
| munkaerőpiac | `állás` | szintmérő | kutatással validált; a lista legnagyobb szava; karácsonyi beszakadás |
| közigazgatás | `kormányablak` | szintmérő | stabil, dráma nélkül; őszi esés + tavaszi visszaugrás (ok ismeretlen) |
| lakhatás | `eladó lakás` | szintmérő | egy éve folyamatosan csökken (100→40) |
| lakhatás | `albérlet` | szintmérő | mérsékelt szezonalitás |
| fogyasztás | `akciós újság` | szintmérő | **szezonmentes**, −9% év/év |
| fogyasztás | `benzin` | szintmérő | jelenleg kiugróban |
| fogyasztás | `nyaralás` | szintmérő | nyári hullám |
| egészség | `kórház` | szintmérő | stabil, nagy |
| egészség | `betegség` | szintmérő | téli hullám, −4% |
| energia | `napelem` | **hibrid** | alapvonal + két éles eseménycsúcs; támogatásfüggő; **előretekintő szándék** |
| jövedelem | `nyugdíj` | **hibrid** | alapvonal + eseményre reagál (+1150% év/év a mérés hetében) |
| háztartási pénzügy | `hitel` | szintmérő | munkanapi ritmus; éves felezés (45→20) |
| közélet | `tüntetés` | **eseményjelző** | alacsony alapvonal (3–7), négy kiugrás 20–62 között |

**Tizenhárom szó, kilenc doménben.**

### 2.3 Karaktertípusok — ez konfigurációs mező legyen

- **szintmérő** (11 szó): folyamatos értéke van, az érdekes, hogy hol áll.
- **eseményjelző** (`tüntetés`): a legtöbb időben nincs mit mérni; az érdekes,
  hogy mikor és mekkorát ugrik.
- **hibrid** (`nyugdíj`, `napelem`): van alapvonala is, és eseményre is ugrik.

Ez nem kozmetika: a **láncolás előtt az eseményjelző csúcsmagassága nem
összehasonlítható**, mert minden hét a saját maximumára normalizálódik — egy
nagy és egy kicsi tüntetés is 100-on tetőzik. A típus ezért a `config.yaml`-ba
kerüljön, és a Phase 3 felülete is eltérően kezelje.

### 2.4 Kiesett kulcsszavak és okuk

| Kulcsszó | Ok |
|---|---|
| `infláció`, `munkanélküliség`, `adóváltozás` | absztrakció — a kutatás szerint nem működik (2.1) |
| `MNB`, `kamat` | szakmai közönség, illetve kétértelmű (`kamat` matekleckéket is behúz) |
| `forint árfolyam`, `euró árfolyam`, `élelmiszerárak`, `rezsi`, `minimálbér` | elemzői megfogalmazás, kicsi |
| `oktatás`, `pedagógus` | absztrakció |
| `kormány` | **kétértelmű**: a kapcsolódó keresések közt `tisza kormány`, `kormányablak`, `kerékpár kormány` — három független folyamat egy görbében |
| `választás` | **naptárvezérelt**, epizodikus; a felkapott ág úgyis elkapja |
| `felvételi` | **naptárvezérelt** (ponthatár-kihirdetés): egyetlen éves csúcs |
| `népszavazás`, `ellenzék`, `részletfizetés` | túl kicsi |
| `gázszámla`, `magánorvos`, `munka külföldön` | megmérve: nem keresik |

### 2.5 A méretmérésről — miért nincs a listában méret

A mérés során a szavak relatív méretét páronkénti Trends-lekérdezésekkel
állapítottuk meg. **Ezek a számok a tervbe nem kerülnek be**, mert szóló
lekérdezésnél a méret nem számít: minden szó megkapja a saját 0–100
tartományát.

A mérés két dolgot végzett el, és ezzel ki is merült a szerepe: bebizonyította,
hogy **nincs jó horgony** (a régi config szórása 158-szoros volt), és
kirostálta a kétértelmű, illetve naptárvezérelt szavakat.

Módszertani megjegyzés a jövőnek: a Trends **soha nem ad abszolút számot** —
az „Átlagos érdeklődés" mindig a lekérdezésen belüli maximumhoz viszonyít, és
egyetlen kifejezésnél meg sem jelenik. Két különböző lekérdezésből származó
szám ezért nem hasonlítható össze közös szó nélkül.

---

## 3. Döntések

| Döntés | Választás | Indoklás |
|---|---|---|
| Horgony | **Elvetve** | 1.2, 1.3 |
| Lekérdezés | **Szóló, kulcsszavanként** | Minden szó megkapja a teljes 0–100 tartományt |
| Ablak | 7 nap, órás felbontás | Változatlan; ma is ez a visszapótlás alapja |
| Kulcsszólista | A 2.2 szerinti 13 szó | Kézi méréssel megalapozva |
| Csoportok | Domének (2.2), nem a régi `megelhetes`/`gazdasag`/`közélet` | A régi bontás erre a listára nem illik |
| Karaktertípus | Új config-mező (2.3) | A megjelenítés és a láncolás is függ tőle |
| Napok közti összehasonlítás | **Egyelőre nincs** | A Trends a saját maximumra normalizál |
| Láncolás | Későbbi fázis, **de most elő kell készíteni** | 4. fejezet |

---

## 4. A láncolás

### 4.1 Az elv

A napok közti összehasonlítás **horgony nélkül is visszahozható**: a 7 napos
ablakok egymást követő napokon **hat napban átfednek**. Ugyanaz a valóság, két
különböző skálán — az átfedő szakaszok átlagainak hányadosa megadja a két nap
közötti szorzót.

Jelöléssel: a D napi lekérdezés `[D-7, D]`-t fedi, a D+1 napi `[D-6, D+1]`-et.
Az átfedésen `a_i = k_A · t_i` és `b_i = k_B · t_i`, ahol `t_i` a valós érték.
A hányados `mean(b)/mean(a) = k_B/k_A` — konstans, tehát becsülhető.

### 4.2 Amit ehhez most el kell tenni

**Napi átlagból nem visszafejthető.** Kötelező ezért:

- A **nyers órás sorozat** kulcsszavanként, **a lekérdezés pontos
  ablakhatáraival együtt**, verziókövetett kimenetbe kerüljön. A per-futás
  CSV-ket a workflow nem commitolja (csak `docs/data` + `adatok/naplo.csv`),
  tehát friss klónon elvesznének; a repóban lévő régi `adatok/`-CSV-k kézzel
  kerültek be, nem a napi futásból.
- Nem kell örökre minden nap: a lánc következő szemének kiszámításához elég az
  **előző futás** nyers sorozata. Gördülő ablak (pl. utolsó 7–14 nap) elég.
- Ablakhatárok nélkül az átfedés nem azonosítható — azok nélkül a mentés
  értéktelen.

### 4.3 A részleges farok kihagyása kötelező

A Trends minden lekérdezés végén **részleges adatot** ad vissza a legfrissebb
órákra (a felületen szaggatott vonal jelzi), amit később felülír. Élő példa a
mérésből: a `nyugdíj` heti görbéjén **maga a 100-as csúcs** — ami az egész
sorozat skáláját beállítja — szaggatott szakaszban van.

Ha ezek a pontok bekerülnek az átfedésbe, **rendszeres, egyirányú torzítást**
visznek a szorzóba. A láncolás ezért csak a **lezárt szakaszt** használhatja,
és a mentett nyers sorozatnál jelölni kell, meddig végleges. A lezárt szakasz
azonosítása a kliens által visszaadott **`isPartial` oszlopra** épüljön, ne
heurisztikára: a trendspy DataFrame tartalmazza ezt az oszlopot (az
`idosorok._elso_ertek_oszlop` ma át is ugorja), és pontosan azt jelöli, mely
órák részlegesek.

### 4.4 A hibahalmozás természete

**Véletlen hiba** (mintavételi zaj, kerekítés) gyök n szerint nő: 144 átfedő
pontból számolt szorzónál a lépésenkénti zaj ~0,4%, harminc lépés után ~2% —
elhanyagolható.

**Rendszeres torzítás lineárisan halmozódik**: lépésenként 1% egyirányú hiba
harminc nap alatt ~35% sodródás. A részleges farok pontosan ilyen forrás,
ezért nem opcionális a kihagyása (4.3).

Periodikus újrahorgonyzás (pl. havi, hosszabb ablakú lekérdezés) a maradék
sodródást is korrigálja — ez a későbbi fázis feladata.

---

## 5. Kockázatok

- **A szóló lekérdezés a zajt is felnagyítja — ez a fázis legveszélyesebb
  kockázata.** A Trends a saját maximumra normalizál **függetlenül attól,
  mennyi adat van mögötte.** Egy vékony mintájú szó görbéje is kitölti a 0–100
  tartományt, csak mintavételi zajjal. Az új hibamód **megtévesztőbb, mint a
  régi**: a lapos nulláról ránézésre látszik, hogy hibás, egy hullámzó
  zajgörbéről nem. Ezért kötelező a 6.1 objektív kritérium.
  Szóló bizonyítékunk **csak két szóra** van (`albérlet`, `MNB`); a `tüntetés`
  és a `betegség` viselkedése órás felbontásban ismeretlen.
- **A skála ugrik, nem sodródik.** A 7 napos ablakban a skálát a *historikus
  maximum* állítja be. Amikor ez kicsúszik az ablakból, a skála **egyik napról
  a másikra átvált**. Emiatt a Phase 3 kulcsszó-feature-e **napon belüli görbe
  lesz, nem többnapos történet**, és a napi `atlag`/`csucs` **nem jeleníthető
  meg követhető mérőszámként** a láncolás előtt.
- **A kérésszám nő.** A kulcsszó-ág néhány kötegről 13 szóló lekérdezésre vált.
  A gyűjtő négy ágon dolgozik, és a felkapott trendekhez trendenként is jön
  idősor — a **teljes futásonkénti hívásszám a repóból olvasandó ki** (Task 8).
  Nagyságrendi becslés: 12–16 másodperc hívásonként, tehát a kulcsszó-ág
  önmagában ~3 perc, plusz a 429-ekre eső backoff. A 429-esély hívásonként
  adódik, tehát a futásidő nem lineárisan nő.
  **Enyhítés, ami már létezik:** a „részleges siker is siker" elv — ha a
  kulcsszó-ág félúton feladja, a napi trendlista attól még publikálódik.
  **Tartalék, ha kell:** a lista nagyságrendi szórása jóval kisebb, mint a régi
  configé volt, tehát a szavak horgony nélkül köteghetők. Ára, hogy a köteg
  skálája attól függ, melyik tag kapott aznap hírt — ez a láncolást bonyolítja,
  ezért **tartalék, nem alapterv**.
  **További tartalék:** a kulcsszavak nem feltétlenül kell napi gyakorisággal
  jöjjenek — 7 napos ablaknál a láncoláshoz 4-5 napos átfedés is elég, tehát
  szavanként háromnaponta is elegendő lehet. Ez viszont állapotot visz a
  gyűjtőbe; csak a Task 8 eredménye alapján érdemes elővenni.
  **Tartalék a másik irányból:** a `trend_idosor_max` (ma 15) csökkentése
  tisztán configból apasztja az `idosor`-ág hívásait. Rejtett ára, hogy ez a
  szám a `top_trendek` méretét is vezérli — 5-re véve a Phase 3 napi
  trendlistája (7.1) is ötre rövidülne, nem csak a görbék száma (7.2). A kettő
  szétválasztása már kódmunka, ezért ez is tartalék, nem alapterv.
- **Az idősor töréspontja.** A javítás előtti és utáni napok
  összehasonlíthatatlanok. A váltás dátuma kerüljön **az adatba**, ne csak
  commit-üzenetbe.
- **A `csucs` jelentése megváltozik.** Eddig a horgonyhoz mértük, ezután a szó
  saját heti maximumához.
- **Szezonalitás és eseményfüggőség.** Több szónál ismert: `albérlet` és
  `nyaralás` nyári, `betegség` téli, `napelem` támogatásfüggő, `hitel`
  munkanapi ritmusú. **Évnyi alapvonal nélkül a szezonalitás és a valódi
  elmozdulás nem szétválasztható** — a honlapon ezért nem szabad az emelkedést
  aggodalomként értelmezni. A becsületes megfogalmazás: „ennyien keresték".

---

## 6. Task-lista

| # | Task | Függőség |
|---|---|---|
| 1 | **Mérés:** a 2.2 tizenhárom szava **szólóban**, 7 napos ablakban, órás felbontásban — a 6.1 objektív kritérium szerint. **Eldobható mérő-script megengedett; repóba kerülő kód és commit nem** | — |
| 2 | `config.yaml` átírása: új kulcsszólista (2.2), domének, karaktertípus-mező (2.3), a Task 1-en elbukott szavak elhagyása. **Tartalmi döntés, külön jóváhagyással** | 1 |
| 3 | Szerződés-teszt a nyers órás kimenetre: mezők, ablakhatárok, típusok, véglegesség-jelölés (4.3) | — |
| 4 | A gyűjtő átállítása szólóra, horgony elvetése. **Nem config-szintű:** `kulcsszavak.py` (kötegelés, referenciaszó, normalizálás) és `config.py` (betöltés/validáció/`osszes_kulcsszo`) átírása; a trendspy-kliens és az anti-block motor (`kliens.py`) nem változik | 2, 3 |
| 5 | **Ágsorrend csere:** a gyűjtő ágsorrendje `felkapott_api → felkapott_rss → kulcsszo → idosor` (ma a `kulcsszo` az utolsó, előtte az `idosor` 15 hívása). Orchestráció-szintű (`futtato.py` + az `AGAK` konstans), a kliens nem változik. **Csak a Task 4 után** — lásd az indoklást a táblázat alatt | 4 |
| 6 | Nyers órás sorozat verziókövetett kimenete gördülő ablakkal (4.2) | 3, 4 |
| 7 | Töréspont rögzítése az adatban + szerződés-teszt rá | 4 |
| 8 | **Kérésszám-mérés élesben:** hány hívás megy ki futásonként ágakra bontva, hány 429 jön, mennyi a futásidő | 4 |
| 9 | README-frissítés + whole-branch review | mind |

A Task 5 (ágsorrend) **szándékosan a Task 4 után áll, `dep 4`.** A csere
önmagában triviális, és block-napon a `kulcsszo`-ágat védi: nincs funkcionális
függés (a `kulcsszo` csak a configot és az órát fogyasztja), az `idosor` adata
naponta újratermelődik, a `kulcsszo`-é pótolhatatlan. **De a Task 4 előtt
kontraproduktív:** ekkor a `kulcsszo` még a régi 22 szót gyűjti horgonnyal —
pontosan azt a használhatatlan adatot, amit ez a fázis kidob —, tehát a csere a
*jó* `idosor`-adatot áldozná fel a *szemétért*. A swap csak akkor nyer értelmet,
amikor a Task 4 után a `kulcsszo` szólóban valid, pótolhatatlan adatot ad. (Élő
eset a mai állapotból: egy 429-es futásban a tervezett 23 hívásból 6 ment ki, és
a `kulcsszo` el sem indult — ez a Task 4 után lesz igazán fájó veszteség.)

A Task 1 azért van elöl, mert a Task 2 döntése nélküle vakrepülés lenne — és
mert minden nap, amit a jelenlegi beállítással futtatunk, egy véglegesen
elveszett nap a kulcsszó-rétegben.

### 6.1 Mikor használható egy kulcsszó — objektív kritérium

A „sima vagy szemét" szemmérték nem elég, mert a szóló lekérdezés **minden
szót kitölt 0-tól 100-ig** (5. fejezet). A 7 napos, órás sorozat (~168 pont)
alapján:

- **Különböző értékek száma.** Gazdag sorozatban több tucat különböző érték
  fordul elő. Ha csak néhány diszkrét szint van (pl. 0 / 25 / 50 / 75 / 100),
  az kvantálás, nem mérés.
- **Nullák aránya.** Ha az órás pontok jelentős része 0, a szó órás
  felbontásban nem mérhető. **Kivétel a valódi napi ciklus** — az `MNB`
  éjszaka legitimen nulla —, ezt a nullák *eloszlása* különbözteti meg a
  zajtól: ciklikus szónál összefüggő éjszakai blokkokban állnak, zajos szónál
  szétszórtan.
- **Szomszédos pontok különbsége.** Valódi jelnél a görbe folytonos; zajnál
  szomszédos órák között nagy, előjelet váltó ugrások vannak.

A pontos küszöböket a Task 1 mérése állapítsa meg. A lényeg, hogy a döntés
**számokon alapuljon**. A mérés **verziókövetett jegyzőkönyvbe** kerüljön
(`docs/superpowers/phase2_5/task1-meres.md`), amely **kulcsszavanként megőrzi a
nyers számokat is** (különböző értékek száma, nullák aránya és eloszlása,
szomszéd-különbségek), nem csak a következtetést — így ha a küszöb később
rossznak bizonyul, **új Trends-lekérdezés nélkül újraszámolható**. A
véglegesített küszöbök ezután **ide, a 6.1-be íródjanak vissza**.

**Az `eseményjelző` típusra a kritérium másképp alkalmazandó:** a `tüntetés`
alapvonala legitimen alacsony, tehát a sok kis érték nem automatikusan zaj.
Itt az a kérdés, hogy a *csúcsok* alakja folytonos-e.

### 6.2 Ne húzzunk a listából előre

A vágás csak a Task 1 vagy a Task 8 eredménye alapján indokolt. Az aszimmetria
egyértelmű: egy fölöslegesen gyűjtött szó ára néhány másodperc futásidő; egy
hiányzóé **egy hónap visszapótolhatatlan adat**.

Ha a Task 8 alapján mégis vágni kell, javasolt sorrend:
1. `betegség` — valószínűleg ugyanazt méri, mint a `kórház` (mindkettő téli
   hullámú); ez egy közös éves lekérdezéssel ellenőrizhető
2. `nyaralás` — erősen szezonális, a fogyasztás doménben van két erősebb társa
3. `albérlet` — a lakhatásban ott az `eladó lakás`, nagyobb és tisztább trenddel

A `tüntetés` **ne kerüljön a vágólistára**, pedig a legkisebb: ő az egyetlen
eseményjelző és az egyetlen szó a közéleti doménben.

**A gyűjtés nem egyenlő a megjelenítéssel.** Tizenhárom szót gyűjteni és hatot
megjeleníteni teljesen legitim — a honlapon tizenhárom vonal amúgy is sok
lenne.

---

## 7. Javasolt config-szerkezet

Illusztráció, nem kötelező forma — a tényleges `config.yaml` szerkezetéhez
igazítandó:

```yaml
kulcsszavak:
  - kifejezes: "állás"
    domen: munkaeropiac
    tipus: szintmero
  - kifejezes: "kormányablak"
    domen: kozigazgatas
    tipus: szintmero
  - kifejezes: "eladó lakás"
    domen: lakhatas
    tipus: szintmero
  - kifejezes: "albérlet"
    domen: lakhatas
    tipus: szintmero
  - kifejezes: "akciós újság"
    domen: fogyasztas
    tipus: szintmero
  - kifejezes: "benzin"
    domen: fogyasztas
    tipus: szintmero
  - kifejezes: "nyaralás"
    domen: fogyasztas
    tipus: szintmero
  - kifejezes: "kórház"
    domen: egeszseg
    tipus: szintmero
  - kifejezes: "betegség"
    domen: egeszseg
    tipus: szintmero
  - kifejezes: "napelem"
    domen: energia
    tipus: hibrid
  - kifejezes: "nyugdíj"
    domen: jovedelem
    tipus: hibrid
  - kifejezes: "hitel"
    domen: haztartasi_penzugy
    tipus: szintmero
  - kifejezes: "tüntetés"
    domen: kozelet
    tipus: esemenyjelzo
```

A doménnevek ékezet nélküliek — a régi configban `megelhetes` ékezet nélkül,
de `gazdaság` és `közélet` ékezettel szerepelt, ami inkonzisztencia. A magyar
megjelenítendő címke a frontend leképezési táblájában éljen.

**A horgony-konfiguráció (`időjárás`, `referencia_min_atlag`) elhagyandó.**

**A `config.py` is átírandó, nem csak a YAML** (Task 4). A jelenlegi betöltő a
`kulcsszavak`-at csoport→lista dictként várja; a fenti listás, per-kulcsszó
attribútumos (`domen`, `tipus`) szerkezet ezzel inkompatibilis. Átírandó a
betöltés, a validáció (ma csoportonkénti nem-üres listát ellenőriz) és az
`osszes_kulcsszo()` (ma `(szó, csoport)` párokat gyárt).

---

## 8. Megjegyzés az implementernek

Ez a spec **kézi Google Trends mérésekre és publikált JSON-fájlok
átolvasására** épül, nem a repó kódjának olvasására. Ellenőrizendő:

- hogyan áll össze ma egy köteg, hány kulcsszó megy egy hívásba
- hol és hogyan történik az `időjárás`-horgonyhoz normalizálás
- a kliens milyen ablakot és felbontást kér
- a nyers órás sorozat hol keletkezik, és hova íródik ki
- a `config.yaml` tényleges szerkezete
- **hány hívás megy ki futásonként, ágakra bontva** (a Task 8 bemenete)

Ha eltérés van, **ez a dokumentum javítandó, nem a kód igazítandó hozzá.**
