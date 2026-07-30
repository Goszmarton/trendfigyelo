# Task 8 — Hívásszám-mérés / első éles integráció (jegyzőkönyv)

> **Mérés, nem fejlesztés.** Nincs repóba kerülő script. A jegyzőkönyv az egyetlen artefakt (a letöltött futás-artefakt a fejlesztői scratchpadban, nem a repóban).
> A Task 8 **merge-előtti** hatóköre a `dfea2e3` (Task 8 újrafogalmazás) szerint: **első éles integráció + ágankénti hívásszám igazolása**. A 429-ráta/rezsim a merge utáni napló-monitorozásra van tolva (lásd 4.).

## 1. Futás-metaadat

| Mező | Érték |
|---|---|
| run | `30537101369` |
| trigger | `workflow_dispatch` |
| ág | `phase-2.5-kulcsszo-meres` @ `886cdbc` |
| időablak | 2026-07-30 11:03 → 11:25 UTC |
| futásidő | 21m48s |
| eredmény | `success` |
| commit-step | **skipped** (ág-guard: `always() && github.ref == 'refs/heads/main'` a phase-2.5-ön hamis → semmi nem került az ágra; `origin/phase-2.5-kulcsszo-meres` maradt `886cdbc`) |
| artefakt | `trendfutas-30537101369-1` (napló + `docs/data/**` + `run.log`) |

## 2. Ágankénti hívásszám a config-jóslat ellen

| Ág | próbák (napló) | logikai várt | retry (429) | eredmény |
|---|---|---|---|---|
| felkapott_api | 1 | 1 | 0 | siker |
| felkapott_rss | 1 | 1 | 0 | siker |
| kulcsszo | 18 | 13 | 5 | siker |
| idosor | 16 | min(15,#trend)=15 | 1 | siker |
| **Össz** | **36** | **30** | **6** | mind siker |

A `run.log`: „Várható Google-hívásszám (429 nélkül): ~30" és „Összes Google-hívás: 36". A `legfrissebb.json` **15 top_trendje** igazolja az `idosor` logikai 15-ét (`min(15,#trend)`, #trend ≥ 15). A jóslat (2+15+13 = **30**) pontosan teljesül; 6 lágy retry, egyetlen ág sem adta fel, egyetlen szó sem esett ki.

**FONTOS MEGFOGALMAZÁS — a 36 a kliens SZÁMLÁLÓJA, nem a valódi HTTP-kérésszám.**
A 36 az `osszes_hivas()` (a mi logikai próbáink, retryval). A trendspy **hívásonként belül token-/segéd-kérést is indíthat**, amit ez az instrumentáció **nem lát**. Ezért a **„13 szó = 13 valódi HTTP-hívás" kérdés NYITVA MARAD** — a lezárása nem a kliens-számláló, hanem egy **proxy- vagy HTTPConnection-szintű** mérés. A `plafon = tervezett_hivasszam * max_probak = 120` ettől **érvényes marad**, mert a *mi* call-multiplikációnkat (a saját hurkainkat/retryjeinket) korlátozza, nem a trendspy belső al-kéréseit.

## 3. A négy élő-csak kérdés lezárása (bizonyítékkal)

- **a) Szóló `interest_over_time([kif], geo="HU", timeframe="now 7-d")` — JÓ.** Mind a 13 szó valid egy-oszlopos sorozatot adott; a szignatúra helyes a trendspy 0.1.6-ban.
- **b) tz-aware UTC index — IGEN.** Az ablakhatárok és a pontok időbélyege végig `+00:00`. A **legmagasabb kockázat** (naiv index → `ValueError` a validátorban) **nem materializálódott**.
- **c) `ir_gordulo` szerződés-átmenet — 13/13 rekord, 0 érvénytelen** (a repó `ervenyes_nyers_rekord`-jával, a letöltött `kulcsszo_nyers.json`-on). Az `isPartial` **felismerve**: pontosan **13 pont `reszleges=True`** (szavanként a záró óra). Összesen **2197 órás pont** = 169/szó × 13.
- **d) `kulcsszo_nyers.json` nulláról** — az ágon nem létezett, most **13 kulcsszóval** jött létre.

## 4. Amit ez a futás NEM igazol (explicit hatókör-vágás)

- 429-**ráta**, rezsim-jellemzés, **kapu-blokk-viselkedés** az új sorrenden, **cron-késés**.
- Indok: ez `workflow_dispatch`, **délelőtti (11:03 UTC), torlódáson kívüli** futás; a `schedule` **csak a default (main) ágon** fut → az új ágsorrend schedule-rezsimje csak **merge után** figyelhető meg (a mainre akkumulálódó `naplo.csv`, ~2 hét).
- Ez a `dfea2e3`-ban rögzített Task 8 újrafogalmazás szerinti **szándékos hatókör-vágás, nem hiányosság.**

## 5. Megfigyelés a Task 5 ágsorrendhez (döntést NEM javasol)

A 429-teher az **ÚJ** sorrenden a **kulcsszó**-ra esett (5/6 retry), nem az `idosor`-ra — a régi sorrend (idosor 10/11) tükörképe. **Lágy rezsim: nulla blokk, mind a 13 szó megvan.** Ez a „a teher az elöl futó / többet hívó ágra esik" mintát erősíti; most a **pótolhatatlan kulcsszó** viselte, de **adat nem veszett el**. (A block-viselkedés a schedule-rezsimben, merge után dől el — lásd 4.)

## 6. Jegyzet a hiányos történetről

Az artefakt `tortenet.json`-ja **hiányos** történetet mutat, mert az ág `docs/data`-ja a `b12722e` pillanatkép (a 07-27/28/29 napi JSON-ok CSAK a mainen vannak, az ág egyetlen commitja sem nyúlt `docs/data`-hoz). **Ez NEM integrációs hiba.**

## 7. Adat-plauzibilitás (érték-szintű, a séma-validátoron túl)

### 7.1 `kulcsszo_nyers.json`
- **Mind a 13 szó max=100** → a szóló-lekérdezés 0–100 normalizálás értelmezése **igazolva** (élő-csak megfigyelés; a séma-validátor ezt átereszti).
- **Órás rács:** 169 pont/szó, pontos 1h lépés, **nincs hiány, nincs duplikátum**.
- **`ablak_veg_utc` mind a 13 azonos:** `2026-07-30T11:00:00+00:00` (kezdet `2026-07-23T11:00:00+00:00`). A trendspy **órahatárra igazít**, tehát a közös perem **szerkezeti**, nem a 22 perces futás rövidségének következménye (a futás ellenére egységes). A spec **4.2 „közös perem"** feltevése teljesül, és a **Minor 3 dedup-kulcs (`ablak_veg_utc`) stabil**.
- **`reszleges=True`** szavanként pontosan a **záró órán**, sehol máshol.
- **Adatminőség:** `tüntetés` **168/169 nulla**, egyetlen 100-as csúccsal — eseményjelző-szignatúra (lapos alapvonal + izolált csúcs), egyezik a Task 1 megfigyeléssel; a szó a **6.2 szerint védett**. **NEM hiba**, de alacsony információtartalmú sorozat. Ellenben `betegség` (43 nulla) és `kórház` (18 nulla) **NEM lapos** — mindkettő max=100, sok nem-nulla pont (órás/7-d felbontásban mindkettő mérhető ezen a héten).
- **`napok/2026-07-30.json`:** 15 trend, olvasható magyar, **nincs `\uXXXX` escape, nincs mojibake, nincs üres kifejezés**; volumen+növekedés kitöltve.
- **`legfrissebb.json`:** `modszertan_valtas` kulcs **NINCS benne** (helyes, default None — merge-ig nem íródik).
- A nyers JSON **13 szava halmazként egyezik** a `config.yaml` kulcsszavaival.
- **`naplo.csv`** 07-30-i **4 sora séma-egyező** (5 oszlop: futas_ido_utc/ag/eredmeny/hivasok_szama/hibakodok).

### 7.2 `trend_idosorok` (a második élő kódút, most először élesben)
- Mind a **15 top_trendhez van idősor** (2713 pont, 15 egyedi kifejezés, nincs üres, nincs lóg-ki).
- **Felbontás: 8 PERCES rács** (difs=480 s), ~180–181 pont, 24h span, `now 1-d` `idosor_idokeret`; 15 sorozat = `trend_idosor_max`. A kulcsszó-út ezzel szemben `now 7-d` **órás** (169 pont) — a két ág **szándékosan** más ablak/felbontás.
- **tz:** NEM tér el a kulcsszó-úttól, minden időbélyeg **`+00:00` aware** (`seged.idopont_iso`), noha a szigorú `ervenyes_nyers_rekord` validátor **csak a nyers-ágra** fut.
- **Max:** mind a 15 sorozat **max=100** → szóló kérés, ugyanaz a normalizálás (ugyanaz az összemérhetőségi következtetés érvényes rájuk is).
- **`reszleges`/isPartial: NINCS mező** (a mezők: `ertek/forras/idopont_utc/kifejezes`). Az `idosorok.df_idosor` nem nyeri ki, szemben a kulcsszó-út `_nyers_sorozat`-ával.
- A `trend_idosorok` szakaszai **szándékosan nem láncolódnak** (napi, önálló `now 1-d` sparkline); a láncolás a `kulcsszo_nyers`-re van fenntartva. Ezért az **isPartial-aszimmetria nem hézag**, hanem a két út szerepének következménye: a spec **4.3** az isPartial-t a **láncoláshoz** írja elő, és ez az út nem láncolódik.

## 8. Task 9 review fókuszpontok

- **(a)** Az **isPartial-aszimmetriát** a review **tudatos döntésként** rögzítse, ne nyissa újra: a spec 4.3 a láncoláshoz írja elő, a trend-idősor út nem láncolódik.
- **(b)** A `kulcsszo_osszesites` és a frontend közöl-e **szavak közti rangsort/összevetést**. A szóló-normalizálás (minden szó max=100) miatt a szavak pontszámai egymással **NEM összemérhetők**, tehát egy ilyen rangsor érvénytelen következtetés lenne. **Elemzési kérdés, nem integrációs hiba; a merge-öt nem blokkolja.**
- **(c)** **Action-verzió-bump:** `checkout@v4` / `setup-python@v5` / `upload-artifact@v4` Node 20-at céloz, a runner Node 24-re kényszeríti. A main `napi.yml`-jét is érinti; **kozmetikai, nem blokkoló.**
- **(d)** A nyitott kérdések **4. tételét (Task 6 integrációs teszt)** jelöljük **[LEZÁRVA]**-ra. Az indok a **T6 saját döntése** (in-window bekerült a szerződésbe, a sorrendet az író garantálja) — **NEM a mai mérőfutás**. *A pontos tétel azonosítása a review feladata.*

## 9. Nettó

Minden **merge-előtti** Task 8-cél teljesült: első éles trendspy-integráció az új ágsorrenden, ágankénti hívásszám a jóslat szerint (**30 logikai**), a nyers-kimenet szerződés-helyessége **valós adaton**, **integrációs hiba nincs.** A 429-ráta/rezsim/kapu-blokk a merge utáni napló-monitorozásra tolva (4.). Új nyitott kérdés: a valódi HTTP-kérésszám (2.).
