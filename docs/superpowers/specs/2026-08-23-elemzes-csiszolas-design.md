# ELEMZÉS-CSISZOLÁS — design (2026-08-23)

Az ELEMZES-FUL (napi AI-elemzés) tartalmi/minőségi csiszolása. Az első éles
kimenetből (2026-08-22) fakadó konkrét hibák javítása: mezőnév-/„payload"-szivárgás,
felsorolásos szerkezet folyó próza helyett, üres `kulcsszo_het` szekció, kínos elrendezés,
és a modell váltása Opusra. A design a `2026-08-22-elemzes-ai-ful-design.md` folytatása;
az ott rögzített SÉRTHETETLENEK (minden szám Pythonból, fail-soft) VÁLTOZATLANOK.

## 0. Motiváció (mit tapasztaltunk élesben, 2026-08-22)

- A szöveg BELSŐ MEZŐNEVEKET és „payload"-ot szivárogtat: „van_elozo: false", „a kapott
  payload szerint", „a kulcsszo_het mező üres objektumot tartalmaz", „ervenyes: false".
- A kimenet FELSOROLÁSOS (kék bal-szegélyes pontok + „feltételezés: Feltételezés:" dupla
  felirat), a felhasználó FOLYÓ BEKEZDÉSEKET kér.
- A „Kulcsszavak — 1 hét" szekció ADAT NÉLKÜL kér elemzést (`kulcsszo_het = {}`), ezért
  a saját ürességéről ír.
- Elrendezés: a naptár legyen BAL oszlop, az elemzés-szövegdoboz JOBBRA mellette.
- A napi elemzés modellje legyen OPUS.

## 1. Sérthetetlenek (VÁLTOZATLAN, a 08-22 designból)

1. MINDEN számot Python számol; az AI KIZÁRÓLAG narratívát ír a kapott számokból, számot
   SOHA nem talál ki. Az új `kulcsszo_het` heti pálya is Pythonból jön.
2. Fail-soft: API-hibán az előző `elemzes.json` bit-azonosan marad (`futtat` a `try` csak az
   `elemez` köré; a `return 2` ág változatlan).
3. A pótolhatatlan órás ág (`kulcsszo_lanc.json`) CSAK OLVASVA; `git add` NÉVVEL.

## 2. Döntések (a brainstormingból, jóváhagyva)

- **D1 — Folyó próza, jelölt hipotézissel (egy bekezdés/szekció):** szekciónként egy
  összefüggő, folyó magyar szöveg (1–3 bekezdés). A feltevés a MONDATBAN marad, egyértelmű
  hedge-eléssel („feltehetően", „elképzelhető", „ezt az adat nem igazolja"); KÜLÖN
  „Feltételezés:" felirat NINCS. Nincs felsorolás/bullet/címke.
- **D2 — `kulcsszo_het` valós heti pályával:** a `kulcsszo_lanc.json` egészséges szavainak
  utolsó 7 napos ablakából Python számol valós trajektóriát; az AI ezt meséli el.
- **D3 — Modell: `claude-opus-4-8`** a napi elemzéshez.

## 3. Backend — `trendfigyelo/elemzo.py`

### 3.1 Modell
`MODELL = "claude-opus-4-8"` (volt `claude-sonnet-5`). A hívás-paraméterek változatlanok
(`thinking={"type":"adaptive"}`, `output_config={"effort":"medium","format":{json_schema}}`,
`max_tokens=16000`). KOCKÁZAT: ha Opus 4.8 elutasít egy paramétert, az implementáció
igazítja (a varrat injektálható, a tesztek nem hívnak éles API-t).

### 3.2 AI-séma egyszerűsítés — `_szekcio_sema` / `_valasz_sema`
A szekció mostantól CSAK `szoveg` (string). A `megfigyelesek[]` és `elmeleti[]` tömbök
TÖRÖLVE. A `szoveg` folyó bekezdés(ek); a bekezdéseket ÜRES SOR (`\n\n`) választja el.

```
_szekcio_sema() -> {"type":"object","additionalProperties":false,
                    "required":["szoveg"],
                    "properties":{"szoveg":{"type":"string"}}}
```

A `_valasz_sema` felső szintje VÁLTOZATLAN kulcsokkal (`valtozas`,
`kulcsszavak.{napi,teljes_kep,het}`, `felkapott.{napi,het}`), csak a szekció-alak egyszerűsödik.

### 3.3 Rendszer-prompt újraírás — `RENDSZER_PROMPT`
Új, szigorú szabályok (magyar), a tartalom lényege:
1. KIZÁRÓLAG a kapott számokból dolgozol; számot SOHA nem találsz ki.
2. FOLYÓ, összefüggő magyar BEKEZDÉSEKET írsz — SOHA nem felsorolást, nem bullet-pontot,
   nem címkét, nem kulcs–érték párokat.
3. SOHA nem említesz mezőnevet, technikai kulcsot, sem a „payload"/„adat(struktúra)" szót;
   a felhasználó nem lát JSON-t. Ha valamiről NINCS adat, természetes magyar mondattal
   mondod (pl. „ma még nincs mihez hasonlítani"), NEM a mezőt nevezed meg.
4. Ok-okozatot TÉNYKÉNT nem állítasz; ahol magyarázatot feltételezel, a mondatban
   hedge-eled („feltehetően", „elképzelhető", „ezt az adat nem igazolja") — külön
   „Feltételezés:" felirat NÉLKÜL, a szöveg maga hordozza az óvatosságot.
5. Hírt/forrást/eseményt nem találsz ki; csak a megadott témák/hírek alapján írsz.
6. Tömör, óvatos, DE ÉRDEMI: mondd el, mit látunk, milyen irányba mozdul, mit lehet
   óvatosan leszűrni.

A prompt EXPLICITEN tiltja a szivárgott kulcsokat is (pl. „van_elozo", „ervenyes",
„kulcsszo_het", „meredekség" MINT KULCS). A konkrét metrikák (mai érték, csúcs, átlag,
meredekség mint fogalom) használhatók a szövegben.

### 3.4 Payload — `_kulcsszo_het(lanc)` + `epit_payload` + `futtat`
Új helper: `_kulcsszo_het(lanc)` a `kulcsszo_lanc.json`-ból heti pályát számol.

- Horgony (`anchor`) = a legfrissebb szó utolsó lánc-pontjának időpontja
  (`pontok[-1].idopont_utc`) — nem az `ablak_veg_utc`. Ez SZÁNDÉKOS: így a horgony
  egy alapon áll a frissességi küszöbbel (az is pont-alapú), így egy elavult végű
  szó pontjai és a küszöb konzisztensen zárják ki azt. Az élő láncban ez egybeesik
  az `ablak_veg_utc`-vel.
- Ablak = `[anchor - 7 nap, anchor]`.
- Egy szó BENNE VAN, ha a lánca eléri az ablakot (a szó utolsó `pontok` időpontja
  `>= anchor - 1 nap`). Ez természetesen KIZÁRJA a szakasz-törött szót (pl. tüntetés,
  amelynek vége 08-17), így a ~12 egészséges szó marad.
- Szavanként: `kezdo` = az ablak első pontjának értéke, `veg` = az utolsóé,
  `min`/`max` az ablakon belül, `valtozas = veg - kezdo`. Mind az öt szám
  (`kezdo`/`veg`/`valtozas`/`min`/`max`) 1 tizedesre kerekítve (`round(x, 1)`) a
  tiszta megjelenítés érdekében.
- Visszatérés: `{"ablak_napok": 7, "szavak": [{"szo","kezdo","veg","valtozas","min","max"}, ...]}`
  (a `szavak` a `valtozas` abszolút értéke szerint csökkenőn rendezve).

`epit_payload(adatok, ...)`: a `kulcsszo_het` mostantól `_kulcsszo_het(adatok.get("lanc", {}))`
(volt üres `{}`). `futtat` az `adatok`-hoz betölti a láncot:
`"lanc": _betolt(docs_data / "kulcsszo_lanc.json") or {}` (CSAK OLVASVA).

### 3.5 „Mi változott ma" előzmény nélkül — Python birtokolja
A szivárgás-mentesség garanciája: ha `payload["valtozas"]["van_elozo"]` HAMIS, a
`valasz_to_artefakt` FELÜLÍRJA a `valtozas` szekció szövegét egy fix, természetes mondattal
(az AI szövegét eldobjuk erre a szekcióra):

> „Ma nincs korábbi nap, amivel összevethetnénk, így a napi elmozdulás egyelőre nem
>  értékelhető. A friss kép a lenti szekciókban olvasható."

Így az üres-nap kimenete DETERMINISZTIKUS és szivárgásmentes, függetlenül az AI-tól.
(Ha `van_elozo` IGAZ, az AI írja a `valtozas` szöveget, mint eddig.) Az artefakt-alak
egyébként VÁLTOZATLAN: `valtozas = {"diff": payload["valtozas"], "szoveg": <AI vagy fix>}`.

## 4. Frontend — `docs/elemzes.html`, `docs/js/elemzes.js`, `docs/css/app.css`

### 4.1 Kétoszlopos elrendezés
Az elemzés fő tartalma két oszlop:
- BAL: a naptár (dátumválasztó), fix szélesség (kb. `minmax(240px, 320px)`).
- JOBB (`1fr`): a teljes elemzés — a prózadobozok ÉS a VALÓS csempék.
- CSS grid, `gap`; kb. `760px` alatt egy oszlopba csúszik (naptár felül, elemzés alatta).
- A meglévő fejléc-doboz (cím + „Elemzés — <nap> (<modell>)") a rács FÖLÖTT marad,
  teljes szélességben.

### 4.2 Próza-render (felsorolás helyett)
A szekció-render mostantól: `<h*>` cím + a `szoveg` `\n\n` mentén `<p>` bekezdésekre bontva
(üres bekezdés kihagyva, minden `textContent` — XSS-biztos). A `megfigyelesek`
bullet-lista és az `elmeleti` „feltételezés:" prefixes render TÖRÖLVE. A dupla
„Feltételezés: Feltételezés:" ezzel megszűnik (a hedge a prózában van).

### 4.3 Csempék (VALÓS) — maradnak
A kulcsszó-csempék (`szó: irány (mai X, csúcs Y)`) és a felkapott-csempék VÁLTOZATLANOK
(determinisztikus VALÓS megjelenítés), a JOBB oszlopban. A „tüntetés: null (mai –, csúcs …)"
csempe kezelése változatlan (érvénytelen jelölés) — nem ennek a körnek a tárgya.

## 5. Tesztelés (TDD, valódi RED, SOROS suite, MUTÁCIÓ == 1)

### 5.1 pytest — `tests/test_elemzo.py`
- `_kulcsszo_het`: adott mini-láncból helyes `kezdo/veg/valtozas/min/max`; a szakasz-törött
  (elavult végű) szó KIMARAD; rendezés a `valtozas` abszolút értéke szerint; üres lánc → `{"ablak_napok":7,"szavak":[]}`.
- `_valasz_sema`/`_szekcio_sema`: a szekcióban VAN `szoveg`, NINCS `megfigyelesek`/`elmeleti`.
- `epit_payload`: a `kulcsszo_het` NEM üres, ha van lánc (a `szavak` lista tartalmas).
- `valasz_to_artefakt`: ha `van_elozo=False` → a `valtozas.szoveg` a FIX mondat (az AI
  szövegét felülírja); ha `van_elozo=True` → az AI `valtozas.szoveg`-je marad.
- `MODELL == "claude-opus-4-8"` (és az artefakt `modell` mezője ezt kapja).

### 5.2 Playwright — `e2e/elemzes.spec.js`
- A prózadoboz `<p>` bekezdés(eke)t renderel, NEM `<li>`-t; a `\n\n` több `<p>`-t ad.
- Az elrendezés: a naptár a BAL oszlopban, az elemzés a JOBB oszlopban (grid-ellenőrzés
  a tényleges DOM-pozícióból, nem CSS-property olvasásából, ahol lehet).
- Nincs a szövegben „feltételezés: Feltételezés:" dupla felirat.
- Üres/„nincs előzmény" nap: a „Mi változott ma" a FIX mondatot mutatja, NINCS
  „kulcsszo_het"/„payload"/„van_elozo" a látható szövegben.
- (A meglévő menü/archívum-tesztek zöldek maradnak.)

## 6. Nem ennek a körnek a tárgya (későbbi fast-follow)

- `indent=0` → `indent=2` az elemzés-JSON-írásoknál (konzisztencia).
- A JS mozgók tizedes-formázása (`2` → `2.0`).
- A prompt HANGNEM/MÉLYSÉG további finomhangolása több éles kimenet után.

## 7. Migráció / kompatibilitás

- A régi archivált `elemzesek/<nap>.json` fájlok a RÉGI (tömbös) alakot tartalmazzák. A
  frontend próza-render `\n\n`-bontása stringre dolgozik; a régi `megfigyelesek[]` már nem
  renderelődik. Elfogadható: a régi napok szövege a `szoveg` mezőből jön (ami a régiben is
  megvan), a bullet-melléklet elmarad — nincs törés, csak kevesebb a régi napokon.
- Az első ÚJ éles futás felülírja az aznapi artefaktot az új alakkal.
