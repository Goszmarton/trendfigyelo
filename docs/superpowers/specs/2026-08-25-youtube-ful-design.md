# YouTube-fül — társadalmi videó-igény-monitor — tervdokumentum (spec)

**Dátum:** 2026-08-25
**Repó:** Goszmarton/trendfigyelo (publikus)
**Állapot:** jóváhagyott terv, implementáció előtt (Phase 4)
**Adatforrás:** Google Trends `gprop='youtube'` (a `trendspy` `interest_over_time`), geo=HU

## 1. Cél és fogalmi keret

Új **„YouTube"** fül a honlapon, amely a Google-kulcsszó-fül testvéreként **társadalmi
érdeklődés-monitor**, de a YouTube logikája szerint. A Google-fül INFORMÁCIÓS keresésként
méri az érdeklődést (állás, hitel, kórház); a YouTube ugyanazt **VIDEÓ-IGÉNYként** — „meg
akarom nézni / megtanulni csinálni / kikapcsolni". Örökzöld kategória-szavakat követünk,
NEM viral neveket; a jel napi/heti görbe minden szóra a saját 0–100 skáláján.

A programnyelv **Python** (a gyűjtő is az); a determinisztikus helyesség és a pótolhatatlan
Google-adat védelme elsődleges.

## 2. Empirikus alap (élő mérés, 2026-08-25)

A 12 szót MINDHÁROM Google-timeframe-en lemértük élőben (`gprop='youtube'`, geo=HU),
szó × timeframe = 36 cella. A jel-sűrűség (nem-nulla napok %-a) MONOTON javul a
timeframe hosszával — a magyar YouTube-volumen alacsony, ezért:

| rács / timeframe | tanulság |
|---|---|
| **órás `now 7-d`** | **halott** — a 12 szóból 8 gyakorlatilag csupa nulla; YouTube-ra HASZNÁLHATATLAN |
| **napi `today 3-m`** | az 5 nagy-volumenű evergreen telített (99–100%), a többi ritka |
| **heti `today 12-m`** | szinte minden szó értelmes (53–100%), egészséges szórással |

**Két következmény, ami a tervet vezérli:**
1. **A YouTube-nak NINCS órás elsődlegese** (szemben a Google-fül `now 7-d` gerincével).
   Ezzel elesik az egész **órás-lánc** komplexitás is (a Google-lánc épp az órás 7-nap
   kiterjesztésére kell; a 12-m egyetlen hívásban ad 1 év heti adatot).
2. A gyűjtés a MEGLÉVŐ **másodlagos** modell (`MASODLAGOS_TIMEFRAMEK = (today 3-m, today 12-m)`),
   csak `gprop='youtube'`-bal és külön kimenettel — nagy újrahasznosítás.

## 3. A követett szavak (VÉGLEGES mátrix — nem cserélünk)

12 szó, 8 kosár. A `rács` a **megjelenítési alapértelmezés** (melyik gomb az „anyanyelvi"
felbontás a szónak) — NEM gyűjtési vágás; gyűjteni MINDEN szóra mindkét timeframe-et
gyűjtjük (§4).

| kosár (domén) | szó | rács-default | mérési indok |
|---|---|---|---|
| Egészség/jóllét | **edzés** | napi | 3-m 100% |
| Egészség/jóllét | **meditáció** | napi | 3-m 100% |
| Egészség/jóllét | szorongás | heti | 3-m 16% → 12-m 53% σ32 |
| Pénzügy | befektetés | heti | 3-m 15% → 12-m 53% σ36 |
| Pénzügy | bitcoin | heti | 3-m 16% → 12-m 94% |
| Közélet/hír | hírek | heti | 3-m 35% → 12-m 100% |
| Közélet/hír | **magyar péter** | napi | 3-m 100% σ17 |
| Háztartás/megélhetés | **recept** | napi | 3-m 99% |
| Család | **mese** | napi | 3-m 100% |
| Szabadidő/utazás | nyaralás | heti | 3-m 29% → 12-m 100% (szezonális) |
| Tanulás | tanulás | heti | 3-m 26% → 12-m 100% |
| Otthon/energia | klíma | heti | 3-m 47% → 12-m 94% |

Napi-default: 5 szó (edzés, meditáció, magyar péter, recept, mese). Heti-default: 7 szó.
**Fenntartás (dokumentálva):** `magyar péter` személynév, hír-ciklussal ingadozik,
elhalványulhat — közéleti szonda, nem klasszikus örökzöld.

## 4. Gyűjtési modell

**Szavanként MINDKÉT másodlagos timeframe-et bekérjük** (a „biztos ami biztos" döntés,
2026-08-25) — így a teljes idő-ablak gombsor (§7) egységesen működik, és nem számolunk el
semmit:

- **`today 3-m`** (napi felbontás, ~90 pont) — a rövid ablakok (1 hét / 2 hét / 1 hó / 3 hó)
  forrása; a napi-default szavaknál éles, a heti-default szavaknál ritka (a frontend a
  meglévő „túl rövid a heti rácshoz" üzenettel kezeli).
- **`today 12-m`** (heti felbontás, ~53 pont) — az 1 hó / 3 hó / 1 év ablakok forrása,
  minden szónál értelmes.

**Hívásszám:** 12 szó × 2 timeframe = **24 SOLO hívás/nap**. NINCS órás, NINCS lánc.
Minden hívás a valódi `Kliens`-en át (429-backoff, véletlen késleltetés, hívás-plafon).

**Érkezés-ellenőrzés:** a meglévő `masodlagos_alak_ok` ÉLES marad — a ritka (alacsony
értékű) sorozat is ÁTMEGY, mert a rács-szabályosságot és a span-t ellenőrzi, nem az érték
nagyságát; csak a csonka/rossz-timeframe cella dobódik el.

## 5. Ütemezés — KÜLÖN ág, KÜLÖN időben

A YouTube-gyűjtés **saját GitHub Actions workflow**, elkülönítve a napi Google-futástól,
hogy ne torlódjon a 429:

- **`.github/workflows/youtube.yml`**, `cron: "0 15 * * *"` = **15:00 UTC** (17:00 nyár /
  16:00 tél budapesti idő) — ~4 órával a napi Google-futás (`19:07 UTC`) ELŐTT.
- **KÜLÖN adat-commit** („adat: napi YouTube-gyűjtés (…Z)"), a napi/elemzés commitoktól
  függetlenül — a „szerver csak kiszolgál" architektúra (a GitHub Actions gyűjt+commitol;
  az önhoszt-szerver az esti ablakban lehúzza).
- A `masodlagos_only.yml` mintáját követi (önálló modul-entrypoint), de **cron-ütemezett**
  (nem csak `workflow_dispatch`) és **committol**.

## 6. Backend

**Újrahasznosítás elve:** a meglévő `kulcsszavak.gyujt_egy_masodlagos` a mag — egyetlen
kiterjesztéssel (`gprop` paraméter, alap `''` → a Google-viselkedés BÁJT-AZONOS marad).

- **`config.yaml`** — új `youtube:` szekció a 12 szóval (kifejezes/domen/racs); a `gprop`
  konstans a modulban (`"youtube"`). A meglévő `kulcsszavak:` szekció ÉRINTETLEN.
- **`config.py`** — a YouTube-szavak betöltése (a `KulcsszoTetel` szerkezet újrahasznosítva);
  a `RACS_IDOKERET`/`MASODLAGOS_TIMEFRAMEK`/`TIMEFRAME_RACS` VÁLTOZATLAN (újrahasználva).
- **`kulcsszavak.gyujt_egy_masodlagos`** — `gprop=""` paraméter hozzáadva, továbbítva a
  `kliens.hivas`-nak; ág-név paraméter (a Kliens-számláló/napló címkéje) `"youtube"` a
  YouTube-hívásoknál. A `"kulcsszo_masodlagos"` hívások VÁLTOZATLANOK.
- **`trendfigyelo/youtube.py`** (ÚJ modul, a `masodlagos_only.py` testvére) — betölti a
  YouTube-szavakat, végigmegy a 12 szó × 2 timeframe cellán, `gyujt_egy_masodlagos`-szal
  gyűjt, a `youtube_nyers.json`-ba ír. SAJÁT, SZŰK plafon (`24 × max_probak + 1`) — a napi
  órás kvótát NEM viheti el. NEM indít más ágat. Entrypoint: `python -m trendfigyelo.youtube`.
- **`nyers_kimenet`** — új `ir_youtube` (az `ir_masodlagos` mintája), atomi írással.
- **`naplo`** — a YouTube-ág `siker/…` sorai a meglévő `naplo.csv`-be (külön ág-címke).

**Adatszerződés — `docs/data/youtube_nyers.json`** (a `kulcsszo_masodlagos_nyers.json`
sémáját tükrözi): `{ "youtube": { "<szó>": { "<timeframe>": { kulcsszo, racs, timeframe,
lekerdezes_utc, ablak_kezdet_utc, ablak_veg_utc, pontok:[{idopont_utc, ertek, reszleges}] } } } }`.
A szó × timeframe kulcsolás upsert (a napi-frissülő 3-m és a lassan mozgó 12-m külön cella).

**Trend-számítás és -illesztés (KÖTELEZŐ, MVP — a Google-fül paritása):** a YouTube-szavakra
UGYANÚGY trendet számolunk és illesztünk, mint a Google-kulcsszavakra. Új
`docs/data/youtube_regresszio.json` a meglévő **`regresszio` modul** mintájára:
- **szavankénti, intervallumonkénti meredekség** (1_het / 2_het / 1_ho / 3_ho / 1_ev) az
  `irany` (növekvő / csökkenő / stagnál) és `ervenyes` jelzővel, a `meredekseg_egyseg` +
  `irany_kuszob` küszöbökkel — a Google `kulcsszo_regresszio.json` sémáját tükrözve;
- a **forrás a `youtube_nyers` sorozat** (3-m napi + 12-m heti), NEM órás/lánc;
- a heti-default szavak rövid intervallumai (1_het, 2_het) strukturálisan **`ervenyes:false`**
  (kevés heti pont) — a MEGLÉVŐ regressziós érvényesség-logika ezt kezeli (mint a Google het
  szavainál), nem adathiba;
- a determinizmus alap: a **VALÓS** (Pythonból számolt) irány, nem AI-tipp (jelölési fegyelem).
Az aktív **IRANY-KUSZOB** leltár-tétel küszöb-döntése erre a fülre is érvényes/örökölhető.

## 7. Frontend / UI

Új **„YouTube"** menüpont a `#fomenu`-ben (Trendek / Elemzés / **YouTube** / Infó) → új
`docs/youtube.html` + `docs/js/youtube.js`.

- **Újrahasznosított idő-ablak gombsor** (Teljes időszak / 1 hét / 2 hét / 1 hó / 3 hó /
  1 év) — a Google-fül `app.js` windowing-logikáját tükrözi: a napi/heti szavak MINDEN
  ablaka a másodlagos (3-m/12-m) sorozatból rajzol (nincs órás ág, nincs lánc-forrás).
- **A napi/heti default** szavanként kiválasztja a kezdő felbontást; a heti szavak
  `1 hét`/`2 hét` gombja a MEGLÉVŐ **„Heti felbontású szó – ez az ablak túl rövid a heti
  rácshoz"** üzenetet hozza (megoldott UX, nem hiba).
- **Kosár-csoportosítás** (8 kosár) a szó-választóban — a társadalmi olvasat kerete.
- **TREND-panel** (a Google-fül paritása): a szó keresettségének IRÁNYA az adott ablakban
  (a trendvonal meredeksége a `youtube_regresszio.json`-ból, `irany` + `ervenyes`) — a
  meglévő trend-panel megjelenítését tükrözve.
- **Fogalmi keret-doboz** a fülön: mit mér a YouTube (videó-igény ≠ információs keresés),
  óvatos fogalmazással, a 0–100 relatív-skála figyelmeztetéssel — a meglévő „Infó" oldal
  hangnemében.

**Fenntartás a hatókörben:** a frontend windowing (`app.js`) jelenleg a Google-fülre van
huzalozva; a YouTube-fül ennek egy **lehatárolt újrafelhasználása** (közös modul kiemelése
VAGY a YouTube-specifikus `youtube.js` a szükséges részek átvételével) — a pontos kódszervezést
a writing-plans dönti el, a cél a duplikáció minimalizálása a Google-fül regressziója nélkül.

## 8. Hibakezelés / kvóta

- **429 / AgFeladva:** a YouTube-ág a `masodlagos_only` mintáját követi — az addig gyűjtött
  cellák megmaradnak; az ág csendesen feladja a maradékot (pótolható adat, nem a pótolhatatlan
  órás). A saját szűk plafon védi a Google-kvótát.
- **A pótolhatatlan Google-órás ág VÉDELME (kritikus invariáns):** a YouTube-ág SOHA nem
  indítja a `kulcsszavak.gyujt` (now 7-d) / idosor / felkapott / lánc ágakat, és külön
  workflow-run — nulla esély a napi órás gyűjtés kvótájának elvitelére.
- **Üres/csonka cella:** `masodlagos_alak_ok` eldobja + FIGYELEM; a fül a meglévő üres-ablak
  szövegeket használja.

## 9. Tesztelés (TDD, valódi RED)

- **`gyujt_egy_masodlagos` gprop-továbbítás:** a `gprop='youtube'` eljut a `kliens.hivas`
  kwargs-áig; alap `''` esetén a hívás BÁJT-AZONOS a mostanival (regresszió-őr, fabrikált
  kliens-dummyval MÉRVE).
- **`youtube.py` cella-loop:** 12 szó × 2 timeframe = 24 cella; a sikeres cella a
  `youtube_nyers.json` helyes kulcsán landol; a szűk plafon MÉRVE (nem lép a napi kvótába);
  NEM indít primer/idosor/felkapott/lánc/commit ágat (a `masodlagos_only` invariáns-tesztek
  mintája).
- **`ir_youtube` upsert + atomicitás:** szó × timeframe upsert; `.tmp`-átnevezéses atomi írás.
- **Trend-számítás (`youtube_regresszio.json`):** a szavankénti/intervallumonkénti meredékség +
  `irany`/`ervenyes` a `youtube_nyers` sorozatból (a `regresszio` tesztek mintájára); a heti-
  default szó rövid intervalluma MÉRTEN `ervenyes:false`; az irány-küszöb határeseteinek RED-je.
- **Frontend (Playwright):** a YouTube-fül renderel; a gombsor vált; a napi szó éles rövid
  ablakot, a heti szó a „túl rövid" üzenetet hozza; a csupa-nulla üzenet a ritka cellán.
- **A meglévő 386 pytest + 130 Playwright VÁLTOZATLANUL ZÖLD** (a Google-fül regressziómentes).
- SOROS suite, MUTÁCIÓ==1 fegyelem, a pótolhatatlan órás ág CSAK OLVASVA.

## 10. Nem-cél (YAGNI)

- **NINCS órás YouTube-gyűjtés / lánc** — mérésileg halott, elhagyva.
- **NINCS Fázis-2 „rising/friss" réteg** (`related_queries(gprop='youtube')`) — a spike
  szerint QuotaExceeded-be fut, törékeny; külön, későbbi kör, ha egyáltalán.
- **NINCS AI-elemzés a YouTube-fülön** az MVP-ben (a meglévő Elemzés-fül a Google-adaton
  marad) — külön fast-follow lehet.
- **NEM cserélünk szót** — a 12 szó a végleges mátrix.

(Megjegyzés: a **trend-számítás/illesztés KÖTELEZŐ** az MVP-ben — §6, a Google-fül paritása;
NEM YAGNI-zzuk ki.)

## 11. Nyitott / a writing-plans dönti el

- A frontend windowing pontos kódmegosztása (közös modul kiemelése vs. lehatárolt átvétel).
- A `youtube_nyers.json` „Teljes időszak" számítása kezdetben a 12-m span (~1 év); a >1 év
  akkumuláció (napi upsert egy gördülő tárba) későbbi kérdés — az MVP a 3-m/12-m ablakokra
  épít.
- A `regresszio` modul újrahasznosításának pontos módja a `youtube_regresszio.json`-hoz
  (közös számoló-mag paraméterezve vs. YouTube-specifikus hívó) — a writing-plans dönti el;
  a KÖVETELMÉNY (trend minden szóra, a Google-paritás) rögzített (§6).
