# Egységes formavilág – a Trendfigyelő vizuális újratervezése

Dátum: 2026-11-28 · Állapot: tervezet, builder-check után (USER-jóváhagyásra vár)

## Szándék és miért

A USER szavaival: „csak szeretném egységesíteni a formavilágot". A mostani oldal fülsoros menüvel és oldalanként eltérő
elrendezésekkel (bal oldali vezérlőoszlopok, eltérő dobozok, JS-be égetett színek) épült ki, feature-ről feature-re.
A cél: **minden oldal ugyanabból a vizuális készletből épüljön** (oldalsáv, felső sáv, oldalfejléc, kártya, chip, stat-sor,
grafikonstílus), és **egy szín mindenhol ugyanazt jelentse**. Siker: bármelyik két oldal egymás mellé téve egy termék része.

Vizuális minta: a USER által csatolt „adattár" képernyőkép (sötét oldalsáv szekciókkal, breadcrumb-os felső sáv, állapot-pill
a cím fölött, nagy félkövér cím, fehér kártyák rácsban, chip-sor). Elfogadott látványterv:
`.superpowers/brainstorm/6624-1795877044/content/google-oldal-v2.html` (a USER: „jó lesz").

## Célok

1. Új oldalkeret mind a 11 oldalon (`index`, `elemzes`, `heti`, `havi`, `valtozasok`, `ugyek`, `kapcsolodo`, `trendek`,
   `youtube`, `adatokrol`, `404`; a `bovites.html` csak átirányítás, keret nélkül marad):
   - **Oldalsáv:** teljes magasságú, grafit; fent logó + „Trendfigyelő"; a mostani menü **pontosan** (ugyanazok a nevek,
     sorrend, linkek, csoportok): Áttekintő │ ELEMZÉSEK: Napi · Heti · Havi │ RADAR: Változások · Ügyek · Kapcsolódó │
     STATISZTIKÁK: Google · YouTube │ Infó. Minden menüpont előtt vonalas ikon (lucide), ahol értelmes, szám-badge.
     Az aktív pont: türkiz „pill".
   - **Felső sáv:** bal oldalt breadcrumb (`Csoport / Oldal`; Áttekintő és Infó csoport nélkül), jobb oldalt diszkréten az
     utolsó gyűjtés ideje, Google és YouTube külön, a forrás színpöttyével.
   - **Oldalfejléc:** állapot-pill a cím fölött, nagy félkövér cím (a mostani `<h1>` szövege), alatta a mostani halvány leírás.
2. Egységes komponensek: kártya, chip-sor, stat-sor/stat-kártya, szakaszcím, info-doboz, gomb, táblázat, grafikonstílus.
3. Minden szín, betűméret, térköz és lekerekítés **CSS-változóként egy helyen** (`docs/css/app.css` eleje, `:root`), és a
   JS-ben rajzolt grafikonok színei is innen olvasnak.
4. Grafikonok: vékony vonalak, halvány rács és tengely, tooltip pontos értékkel és dátummal, **mindenhol azonos magyar
   dátumformátum**.

## Nem-célok

- Adatgyűjtés, workflow-k, gyűjtő szkriptek, adatfájlok, számítások, lekérdezések, útvonalak: **érintetlenek.**
- Új funkció, új szűrés, új mutató: nincs. (Pl. a „múlt héthez képest" változásjelző és a témaszűrő chip a látványtervből
  szándékosan kimaradt, mert új adat/funkció lenne.)
- Sötét mód: nem kérte a USER.

## Anti-célok (ha ez történik, kudarc, még ha „működik" is)

- Bármely **megjelenített szöveg vagy szám megváltozik**, vagy eltűnik egy oldal, menüpont, blokk vagy vezérlő.
- A badge, ikon vagy új keret-elem **megváltoztatja egy meglévő elem szövegtartalmát** (pl. a menülink szövege „Ügyek"-ről
  „Ügyek 44"-re változik): a badge-szám és az ikon nem kerülhet a link `textContent`-jébe.
- Külső betöltés (CDN-betűtípus, CDN-ikon) – az oldal tesztekkel kikényszerített szabálya ezt tiltja.
- A meglévő 773 Python- és 230 e2e-teszt bármelyikének „lazítása" a zöldért. Tesztet csak ott szabad módosítani, ahol a
  teszt kifejezetten a régi **vizuális** szerkezetet rögzíti (pl. fülsor-osztály); a tartalmi állításai maradnak.

## Megszorítások (a kódból)

- **Nincs külső betöltés:** a `tests/test_pages.py` tiltja a külső `@import`/`url()`/script/link hivatkozást. Az **Inter**
  betűtípust (woff2, latin + latin-ext a magyar ékezetekhez) és a **lucide** ikonokat (csak a használt ~12 SVG, inline-ként
  vagy egy helyi sprite-ban) a `docs/vendor/` alá kell tenni, sha256-tal a `docs/vendor/FORRAS.md`-ben (a
  `test_vendor_*` tesztek ezt ellenőrzik). Licenc: Inter – SIL OFL, lucide – ISC; a FORRAS.md-be bejegyezve.
- **Nincs build-lépés:** a GitHub Pages és a Hetzner-önhoszt a `docs/`-t közvetlenül szolgálja ki.
- **Nincs inline script / inline eseménykezelő** (tesztek őrzik): minden JS külön fájlban.
- **A meglévő azonosítók és osztályok maradnak**, mert a JS és a 230 e2e-teszt ezekre épül (`#fomenu`, `#labresz`,
  `.fejlec-doboz`, `#dashboard`, `#kulcsszo-blokk`, `#intervallum-vezerlo`, `.vezerlo-sav`, `#radar-idosav`, `#ai-szunet-sav`
  stb.). Új osztály csak új névtérben (`keret-*`, `ui-*`), előtte grep-pel ellenőrizve, hogy nem foglalt (korábbi tanulság:
  névütközés az `attekinto-*`/`e2e/attekinto.spec.js` körül).
- A menü-tesztek (`e2e/menu.spec.js`) a `#fomenu a` linkek **pontos szövegét és sorrendjét** ellenőrzik (10 link,
  3 csoportcímke) → az oldalsáv megtartja a `#fomenu` azonosítót, a `.fomenu-cimke` csoportcímkéket és a link-szövegeket.

## Megközelítések

1. **Helyben átalakítás, közös keretszkripttel – VÁLASZTOTT** (a USER az ajánlást elfogadta). A 11 HTML megtartja a
   tartalmát és az azonosítóit; a menü minden fájlban statikus HTML-ként kapja az új oldalsáv-szerkezetet (JS nélkül is
   látszik); az `app.css` tokenekre újraíródik; a JS-színek tokenekből olvasnak; a felső sávot, az állapot-pillt és a
   badge-eket egy új közös `docs/js/keret.js` tölti ki. A 11 menü-másolat egyezését egy teszt őrzi.
2. Menü JS-ből, egy helyről – elvetve: a menü csak a szkript után jelenik meg, és a menüre épülő tesztek nagy részét át
   kellene írni.
3. Sablonrendszer build-lépéssel – elvetve: új eszközlánc egy szándékosan build nélküli oldalhoz; aránytalan.

## A USER döntései

- Kulcsszó-színek (**1. opció**): a **téma (domén) kap színt**, a kulcsszó a témája színét viszi. Egykulcsszavas
  grafikonon a mért adatvonal a **forrás színe** (Google #3B6FD8, YouTube #D6453D); a kártyán kis színpötty/címke
  jelzi a témát. Több sorozatos grafikonon (pl. kategória-idősor) a sorozatok a témapalettából kapnak színt.
- Minden oldal és menüpont megmarad, a mostani menü **pontosan** (lásd USER-képernyőkép, 2026-11-28).
- A Radar-oldalakon meglévő frissességi jelölő (`#radar-idosav`, pl. „Naponta frissül · utolsó: 2026-11-27") **maga lesz**
  az állapot-pill, ugyanazzal a szöveggel; nem kerül mellé második pill.
- A látványterv elrendezése elfogadva (sötét oldalsáv, chip-sor a tartalom fölött, kártyarács).

## Színek (tokenek, `:root`)

| Token | Érték | Szerep |
|---|---|---|
| `--oldalsav-hatter` | #202326 | oldalsáv háttér |
| `--oldalsav-szoveg` | #C9CED2 | oldalsáv szöveg |
| `--oldalsav-cim` | #858D94 | szekciócímek (kicsi, nagybetűs, ritkított) |
| `--aktiv-hatter` / `--aktiv-szoveg` | #8FDCD0 / #202326 | aktív menüpont pill |
| `--hatter` / `--kartya` / `--keret` | #F5F6F4 / #FFFFFF / #E2E5E3 | fő háttér, kártya, keret |
| `--szoveg` / `--szoveg-2` | #1A1D20 / #66707A | fő és másodlagos szöveg |
| `--akcentus` | #1F8A8A | linkek, fókusz, aktív chip kerete |
| `--ok` / `--figy` / `--hiba` / `--semleges` | #2E8B57 / #D9A21B / #C8414B / #98A0A8 | állapotok |
| `--google` / `--youtube` | #3B6FD8 / #D6453D | adatforrás, mindenhol |
| `--tema-1` … `--tema-8` | Okabe–Ito: #0072B2, #E69F00, #009E73, #CC79A7, #56B4E9, #D55E00, #F0E442*, #000000→#4D4D4D | témák (színtévesztő-barát) |

\* A #F0E442 sárga fehér háttéren gyenge kontrasztú: csak kitöltésként/pöttyként használható, vonalként nem; a 8. szín
grafitszürke. Jelentések, amik **már ma** léteznek a JS-ben és most tokenre kerülnek: trend-vonal (piros szaggatott),
szintvonal (narancs), ML-görbe (lila), előrejelzés (türkiz-zöld + sáv), szokásos sáv (szürke), élő-mérés jelölő (szürke).
Ezek tokent kapnak (`--graf-trend`, `--graf-szint`, `--graf-ml`, `--graf-elorejelzes`, `--graf-sav`, `--graf-jelolo`),
a jelentésük változatlan; az árnyalat igazodhat a palettához, ha a megkülönböztethetőség megmarad.

**Témák hozzárendelése** (rögzített, sorrendtartó): Google (5): megélhetés → tema-1, egészségügy → tema-2,
oktatás → tema-3, gazdaság → tema-4, politika → tema-5. YouTube (8 kosár): a `youtube.js` `YT_DOMEN_SORREND` sorrendjében
tema-1…tema-8. A hozzárendelés egyetlen JS-térképben él (`keret.js` vagy egy közös `szinek.js`), amit minden oldal használ.

## Tipográfia és térköz

Inter (vendorált), tartalék: `system-ui, "Segoe UI", sans-serif`. Számokhoz `font-variant-numeric: tabular-nums`.
Skála (tokenek): oldalcím 30/800, szakaszcím 17/700, kártyacím 14.5/600, törzs 14/400, segéd 12–12.5, mikro-címke
10.5–11 nagybetűs, ritkított. Térköz: 4-es rács (4/8/12/16/20/24/32). Lekerekítés: kártya 12px, chip 8px, pill 999px.
Kártya: fehér, 1px keret, hoverre finom árnyék.

## Oldalkeret – részletek

**Oldalsáv (`#fomenu`)**: a meglévő `<nav id="fomenu">` kapja az új szerkezetet; a 10 link és a 3 `.fomenu-cimke`
szövege, sorrendje, `href`-je, `aria-current`-je változatlan. Ikon: inline `<svg aria-hidden="true">` a link elején
(nincs szövege). Badge: **CSS-sel** rajzolva egy `data-badge` attribútumból (`::after { content: attr(data-badge) }`),
így nem kerül a link szövegébe. Badge-ek (a `keret.js` tölti a meglévő adatfájlokból, hiba esetén nincs badge):
Változások = `elmozdulas.json` `szokatlan_lista` hossza; Ügyek = `ugyek.json` `ugyek` hossza; Google = követett kulcsszavak
száma; YouTube = YouTube-kulcsszavak száma. Az AI-oldalak (Napi, Heti, Havi) badge-e szünet idején egy kis „szünetel"-jel
(`ai_szunet.json`). Mobilon (≤ 900px) az oldalsáv felső sávvá csukódik, menügombbal nyitható (fiókmenü).

**Felső sáv**: breadcrumb + „Google: <idő> · YouTube: <idő>". Források: Google = `legfrissebb.json` `frissitve`,
YouTube = `youtube_regresszio.json` `szamitva_utc`. Formátum: ma → „ma 21:00", tegnap → „tegnap 21:00", egyébként
„nov. 27. 21:00" (budapesti idő). Hiba esetén „–".

**Állapot-pill**: a cím fölött. Szabály (a terv saját döntése, a USER javíthatja):
- Statisztika- és Áttekintő-oldalak: a releváns forrás(ok) utolsó gyűjtése alapján **zöld „GYŰJTÉS RENDBEN"** (≤ 26 óra),
  **sárga „GYŰJTÉS KÉSIK"** (26–48 óra), **piros „GYŰJTÉS HIBA"** (> 48 óra), mellette a dátum.
  **USER-döntés (A):** a pill **csak az időbeliséget** nézi. Az RSS-tartalék (a Google teljes felkapott-listája 11-05 óta
  nem érhető el) NEM teszi sárgává; azt a felkapott-blokk címe már jelzi („rövidített lista (Google RSS)").
- AI-oldalak (Napi, Heti, Havi): ha az `ai_szunet.json` szerint szünetel → **sárga „SZÜNETEL"**; a meglévő
  `#ai-szunet-sav` szövege változatlanul megmarad alatta. Ha nem szünetel: **nincs pill** (saját döntés: nincs mihez
  mérni a „rendben"-t anélkül, hogy új szabályt találnánk ki; a szünet feloldásakor újragondolható).
- Radar-oldalak (Változások, Kapcsolódó): a meglévő `#radar-idosav` szöveg lesz a pill (új stílus, ugyanaz a szöveg).
- **Ügyek** (egyszerre Radar és AI-oldal; saját döntés): szünetben a pill **sárga „SZÜNETEL"**, és a pill dátum-része
  (a látványtervben a dátum helye) a meglévő `#radar-idosav` szöveg („Gördülő N napos ablak: …"). Egy pill, két forrás,
  szöveg nem változik. Nem szünetelő állapotban a Radar-szabály érvényes.
- Infó, 404: nincs pill.

## Látványterv vs. megvalósítás (saját döntés)

A látványtervben szereplő, a mai oldalon **nem létező** szövegek NEM épülnek meg: „28 követett kifejezés · Google Trends,
HU", „· 13 kulcsszó", „Magyarország · geo=HU", „szokásosnál magasabb ma", a rövid témanevek („Megélhetés"). Új szöveg
**csak** a keret-elemekben jelenik meg, amiket a USER kért: breadcrumb, gyűjtési idők, állapot-pill, badge-szám.
A kulcsszókártyán a téma jelzése: **színpötty a meglévő domén-csoportcím mellett** (a `DOMEN_MAGYAR` hosszú nevei, pl.
„Megélhetési problémák", változatlanul); a kártyán belül csak pötty, szöveg nélkül.

## Oldalankénti átalakítás (a tartalom változatlan, csak a forma)

- **Bal oldali vezérlőoszlopok** (`.vezerlo-sav`: Google-oldal 4×, YouTube 1×) → a szakasz fölé kerülő **chip-sor**
  (a mostani gombok chip-stílust kapnak, a `.vezerlo-cim` lesz a chip-sor kis címkéje). A gombok, azonosítók, működés,
  szövegek változatlanok.
- **Szakaszok** (`.szekcio`, `#kulcsszo-blokk`, `#idosor-blokk`, `#trend-blokk`, `#heti-blokk`, Radar-listák, Heti/Havi
  részek) → kártyák egyenletes rácsban, ahol a tartalom kártyalista (kulcsszó-kártyák, trendkártyák, ügyek, témakörök).
- **Mutatók** (kiemelt összefoglaló, mérőszám-sorok, stat-jellegű számok) → stat-sor: halvány címke, nagyobb tabular szám,
  a már meglévő emelkedés/csökkenés jelek (▲▼■) állapotszínnel; 0 érték `--semleges` színnel.
- **Szűrő-/választó-sorok** (időszak-gombok, kategória-legend, dátum- és hétválasztó, Radar-szűrők, Havi/Heti/Napi
  naptárak) → chip-sor ill. egységes naptár-stílus, aktív elem kiemelve.
- **Térképek (Havi, Leaflet)**: a meglévő térképstílus marad, csak a keretük kártya lesz; a színeik a tokenekhez igazodnak.
- **Grafikonok (Chart.js)**: közös alapbeállítás (`Chart.defaults`) egy helyen: betűtípus, rácsszín, tengelyszín, tooltip
  (pontos érték + magyar dátum, pl. „2026. nov. 27. 21:00"), vonalvastagság; minden diagram ebből indul.

## Tesztelés

- A meglévő 773 Python + 230 e2e teszt **zöld marad** (tartalmi állítások változatlanok).
- Új tesztek: (a) a 11 HTML menüje azonos (az `aria-current`/`.aktiv` kivételével); (b) minden színt a `:root` definiál,
  a JS-ben nincs beégetett hex szín (kivéve a token-olvasó tartalékértékeket); (c) a keret-elemek (felső sáv, pill,
  badge) megjelennek és fail-soft-ok hiányzó adatfájlnál; (d) a badge nem változtatja a link szövegét; (e) a vendorált
  Inter/lucide a FORRAS.md-ben hash-sel szerepel; (f) mobil szélességen az oldalsáv fiókmenüvé csukódik (`mobil.spec.js`
  mintájára); (g) tabular-nums és magyar dátumformátum a tooltipben.
- Vizuális ellenőrzés: minden oldal képernyőképe asztali és mobil szélességen, élő adattal (lásd élő-UI előnézet
  workflow), a USER-rel átnézve.

## Builderre hagyott döntések

- A pontos CSS-szerkezet és a fájlok bontása (egy `app.css` vagy `app.css` + `keret.css`).
- Az ikon pontos választása menüpontonként (lucide készletből).
- A feladatok sorrendje és darabolása (javasolt: tokenek + vendor → keret (oldalsáv/felső sáv/pill) → komponensek →
  oldalanként → grafikon-alapbeállítás → mobil → vizuális átnézés).
