# Trendfigyelő — Phase 2 tervdokumentum (spec): közzététel + automatizálás

**Dátum:** 2026-07-24
**Repó:** Goszmarton/trendfigyelo (publikus)
**Ág:** Phase 2 munka a `feature/phase2-kozzetetel` ágon (a `main`-merge után).
**Állapot:** jóváhagyott terv, implementáció előtt
**Előzmény:** Phase 1 (adatréteg) lezárva — l. `docs/superpowers/specs/2026-07-23-trendfigyelo-design.md` és `docs/superpowers/plans/2026-07-23-trendfigyelo-phase1-adatreteg.md`.

## 1. Cél és hatókör

A Phase 1 adatréteg **közzététele és automatizálása**. A hatókör **szűk** és
szándékosan az: adatminőségi fixek + a munka `main`-be emelése + napi egy
GitHub Actions cron-futás + a GitHub Pages **infrastruktúra** bekapcsolása a
`docs/`-ból. A **teljes interaktív webes felület** (Chart.js grafikonok,
csoportszűrő, dátumválasztó, hírek) **külön Phase 3** — ide nem tartozik.

Ez az eredeti terv (2026-07-23) fázisbontását követi (Phase 2 = automatizálás,
Phase 3 = web), azzal az egy kiegészítéssel, hogy a **Pages-infra** (a statikus
kiszolgálás bekapcsolása + egy placeholder oldal) már itt megtörténik, hogy a
napi futás kimenete azonnal élő URL-en elérhető legyen.

### Ami BENNE van
1. Három Phase 1-es Minor-review-észrevétel javítása (adatminőség/robusztusság).
2. A 429-blokkolás elleni **önjavítás** a kulcsszó-történetben (0 extra hívásból).
3. Phase 1 → `main` merge.
4. `.github/workflows/napi.yml` — napi egy futás, commit+push.
5. GitHub Pages bekapcsolása a `docs/`-ból + statikus placeholder oldal.
6. README-kiegészítés + escalation-függelék (proxy — csak dokumentum).

### Ami KÍVÜL van (Phase 3+)
- Chart.js-alapú interaktív webes felület, csoportszűrő, dátumválasztó, hírek.
- Proxy tényleges implementálása (a `config.proxy` mező kész, de nem használjuk).
- Bármilyen sűrűbb, mint napi egy futás.

## 2. Nem-alkudható követelmények (Phase 1-ből öröklött, érvényben)

- **Magyarország-fókusz mindenhol** (`geo="HU"`, `nyelv="hu"`, elmúlt 24 óra),
  egyetlen konfigforrás (`config.yaml`).
- **IP-blokkolás elleni védelem az elsődleges kockázat.** Napi **egy** futás;
  nincs rövid ciklusú tömeges retry; 429 → exponenciális backoff → ág-feladás +
  naplózás; részleges siker is siker; teljes blokk → nem-nulla kilépési kód.
- **Nincs élő Google-teszt** a unit tesztekben — mock/fixtúra. Az egyetlen éles
  teszt Phase 2-ben a valós `workflow_dispatch` futás (l. 6. pont).
- **Munkamódszer:** a terv az egyetlen forrás; taskonként friss implementer +
  külön review-agent; TDD (RED→GREEN); taskonként commit **review után**; záró
  ledger a plan végén.

## 3. Alapfeltevés a 429-ről (Phase 2 kiindulópont)

Megfigyelt, de **nem bizonyított** minta (kevés adatpont): minden aznapi **első**
futás tiszta volt, minden aznapi **ismételt** futás 429-be futott — a lassított
(request_delay 6.0 + 6–10 mp jitter) ütem mellett is. Ebből **nem** vonunk le
erős következtetést; a Phase 2 alapfeltevése: **napi egy cron-futás**, és a
cron-logok (`adatok/naplo.csv` + Actions-logok) idővel kirajzolják a valódi
mintázatot. A runner-IP (adatközponti) viselkedése ismeretlen — az első éles
teszt épp ezt méri fel.

## 4. Adatminőségi fixek (a Phase 1 záró review 3 Minor-ja)

### 4.1 NaN → üres string (`idosorok.df_idosor`)
**Probléma:** `df_idosor`-ban `int(sor[oszlop]) if _szam(...) else szovegge(sor[oszlop])`.
NaN esetén `_szam` False-t ad (`int(NaN)` dob), így `szovegge(NaN)` → a literál
`"nan"` string kerül a kimenetbe.
**Fix:** nem-szám / NaN érték → `""` (üres), sosem `"nan"`. A kulcsszó-ág
`parse_koteg` már helyesen `""`-t ad NaN-ra — a fix a `df_idosor`-t hozza vele
szimmetriába; teszt rögzíti mindkét ág viselkedését.

### 4.2 `config.betolt` lista-aritás validáció
**Probléma:** `szoras_mp=(float(szoras[0]), float(szoras[1]))` skalár vagy < 2 elemű
bemenetnél nyers `IndexError`/`TypeError`-t dob, nem érthető `KonfigHiba`-t.
**Fix — validáció érthető `KonfigHiba`-val:**
- `szoras_mp`: pontosan 2 szám, és `low ≤ high`.
- `backoff_mp`: nem-üres, csupa-szám lista.
- `max_probak`: egész, `≥ 1`.
- `alap_keses_mp`, `szoras_mp` elemek: `≥ 0`.
Minden hibaüzenet megnevezi a mezőt (a meglévő `_kell` mintát követve).

### 4.3 `naplo.csv` görgő sor-cap
**Probléma:** a `naplo_ir` korlátlanul hozzáfűz.
**Fix:** íráskor, ha a fájl sorszáma túllépi a konfigurálható `naplo_max_sor`-t
(alap ~2000 ≈ ~500 nap napi ~4 sornál), a fájl újraírása **fejléc + utolsó N
adatsor** formában. Egyszerű, korlátos, egy fájl; működik helyben és CI-ben is.
Új config-mező: `naplo_max_sor: 2000` (opcionális, alapértékkel).

## 5. 429-önjavítás — kulcsszó-történet visszapótlás (Option B, N=3)

### 5.1 A felismerés
`kulcsszavak.gyujt` **már most** `now 7-d` ablakot kér kötegenként, de a
`parse_koteg` az `utolso_teljes_nap`-ra szűr — a **7 napból 6-ot eldob**. A
szélesebb ablak tehát már ki van fizetve. A visszapótlás **0 extra Google-hívás**.

### 5.2 A csúszó-ablak wrinkle és a megoldás
A `now 7-d` ablak naponta **csúszik**, és a Google minden sorozatot a kért
ablak maximumára skáláz 0–100-ra. Ezért **ugyanaz a naptári nap** normalizált
értéke futásonként kissé eltérhet. Ha vakon felülírnánk, az már rögzített, jó
történeti értékek **churn**-jét okozná. Megoldás:
- **insert-if-absent** a régebbi napoknak (csak a valóban hiányzó napok
  pótlódnak — a rögzített értékek stabilak maradnak),
- a **legfrissebb teljes nap felülír** (frissen mérve autoritatív).

### 5.3 Blast-radius korlátozás
A **CSV és a `legfrissebb.json` egynapos marad** (a legfrissebb teljes nap) —
pontosan mint most; sem a fájlszerkezet, sem a „mai 24 órás grafikon" szemantika
nem változik. **Csak a `tortenet.json`** kap többnapos upsertet.

### 5.4 Mechanika
- Új: `utolso_N_teljes_nap(df, mai_datum, n)` — a df budapesti dátumai közül a
  legnagyobb `n`, amelyek `< mai_datum`.
- A kulcsszó-ág a lekért kötegenkénti DataFrame-ekből az utolsó `N` teljes napra
  is kiszámolja a napi összesítést (kulcsszavanként átlag+csúcs), a
  **naponkénti** referencia-normalizálással (minden nap a saját referencia-
  átlagára skálázva — a jelenlegi logika napokra általánosítva).
- `json_export`: többnapos upsert — a legfrissebb nap felülír, a régebbiek
  insert-if-absent. A `tortenet.json` `napok` listája dátum szerint rendezve marad.
- **Top-trend ág:** változatlan; kihagyott nap = gap a `napok/`-ban (elkerülhetetlen,
  mert `now 1-d`, nincs szélesebb ablak lekérve). Ezt elfogadjuk.
- Új config-mező: `tortenet_visszapotlas_nap: 3` (opcionális, alapértékkel).

### 5.5 Önjavítás-viselkedés
Ha egy napi futás kimarad/blokkol, a **következő** futás (amely `now 7-d`-t kér)
a hiányzó kulcsszó-napo(ka)t visszatölti a `tortenet.json`-ba — legfeljebb `N`
egymást követő kimaradt napig. Ennél hosszabb kiesés a történeti gap-et hagyja
(ritka; ekkor lép működésbe a 7. pont escalation-döntésfája).

## 6. GitHub Actions — `.github/workflows/napi.yml`

### 6.1 Kétlépcsős élesítés (a runner-IP első tesztje)
- **Első verzió: CSAK `workflow_dispatch:`** — nincs `schedule:`. Néhány kézi
  indítás felméri a runner-IP (adatközponti) 429-viselkedését; a `naplo.csv` +
  Actions-logok kirajzolják a mintát.
- **Külön, későbbi kis commit:** ha a kézi futások stabilan tiszták, hozzáadjuk a
  `schedule: "7 19 * * *"`-t (**19:07 UTC** — 21:07 nyár / 20:07 tél budapesti idő,
  késő este, éjfél előtt mindkét évszakban; a pár perc offset a top-of-hour
  runner-torlódás ellen). A GitHub cron fix UTC, nincs DST-igazítás — a 19:07 UTC
  mindkét évszakban késő budapesti estére esik, a nap-attribúció biztonságos.

### 6.2 Jogosultság és mechanika
- `permissions: contents: write` — a `GITHUB_TOKEN` commitolhat/pusholhat.
- `concurrency` guard (`group: napi-futtatas`, `cancel-in-progress: false`) —
  nincs átfedő futás.
- Lépések: checkout → Python-setup → `pip install -r requirements.txt` →
  `python top_keresesek.py` → **szelektív** `git add docs/data adatok/naplo.csv`
  → commit + push **csak ha van diff**.

### 6.3 Mit commitol a CI (és mit nem)
- Commitolja: **`docs/data/*.json`** (a web adata) + **`adatok/naplo.csv`**
  (blokkolás-detektálási napló).
- **Nem** commitolja a per-futás `adatok/*.csv` fájlokat: a workflow sosem
  stage-eli őket (szelektív `git add`), így a runner CSV-i a futó megsemmisülésekor
  elpárolognak. **Nincs `.gitignore`-változás** — a helyi commitolás érintetlen
  marad (a felhasználó helyben továbbra is bármit commitolhat kézzel).
- **Indok:** a web csak a JSON-ból dolgozik; a napi timestampelt CSV-k gitbe
  gyűjtése évi ~1800 apró fájllal hizlalná a repót, felhő-forrásból kevés haszonnal.

### 6.4 Blokk-kezelés a workflow-ban
A Phase 1-es szemantika érvényes: részleges siker → 0 kód → commit; teljes blokk
(semmi adat) → nem-nulla kód → GitHub e-mail értesítés. A workflow **nem** próbál
makacsul újra (az hosszabb blokkot válthatna ki); a következő napi futásé a szó.

## 7. GitHub Pages infra + escalation-függelék

### 7.1 Pages bekapcsolás (manuális GitHub-UI lépés)
A Pages forrása: `main` ág, `/docs` mappa (Settings → Pages). Ez **manuális
kattintás** a GitHub felületén — a plan és a README lépésről lépésre leírja; a
kód/CI nem tudja bekapcsolni.

### 7.2 Statikus placeholder oldal (`docs/index.html`)
Egyetlen kézzel írt, **JS- és build-mentes** HTML: cím („Trendfigyelő —
magyarországi keresési trendek"), rövid HU-fókusz mondat, „az interaktív
grafikonok a Phase 3-ban érkeznek" jegyzet, és linkek a nyers adatra
(`data/legfrissebb.json`, `data/tortenet.json`, `data/napok/index.json`).
Célja: bizonyítani, hogy a Pages él és a data-URL-ek elérhetők. Phase 3 lecseréli.

### 7.3 Escalation-függelék (csak dokumentum, nem implementáció)
A README (vagy a plan) végén döntési fa: **csak ha minden szelídebb megoldás
kevés** (a napi-egy ütem, a részleges siker, a helyi B-terv sem elég a runner-IP
tartós blokkja ellen), akkor a `config.proxy` mezőn keresztüli HTTP(S)-proxy a
következő lépés. Phase 2-ben **nem** implementáljuk; a mező már kész.

## 8. Repó-szerkezet (Phase 2 után, célállapot)

```
trendfigyelo/
├── top_keresesek.py
├── trendfigyelo/            # csomag — módosul: idosorok, config, naplo, kulcsszavak, json_export
├── config.yaml              # + naplo_max_sor, tortenet_visszapotlas_nap
├── requirements.txt
├── README.md                # + workflow, Pages-bekapcsolás, escalation-függelék
├── .github/workflows/napi.yml   # ÚJ — napi futás (előbb dispatch-only)
├── adatok/                  # CSV-k (helyi) + naplo.csv (CI is commitolja)
└── docs/
    ├── index.html          # ÚJ — statikus placeholder
    └── data/*.json         # a napi futás kimenete
```

## 9. Task-vázlat (a részletes lépések a writing-plans tervbe kerülnek)

- **Előfeltétel:** Phase 1 → `main` (PR). *Kifelé ható — külön jóváhagyás.*
- **Task 1:** NaN → `""` a `df_idosor`-ban (TDD).
- **Task 2:** `config.betolt` lista-validáció (TDD).
- **Task 3:** `naplo.csv` görgő sor-cap + `naplo_max_sor` config (TDD).
- **Task 4:** `utolso_N_teljes_nap` + többnapos kulcsszó-parse, napi
  normalizálás (TDD).
- **Task 5:** `tortenet.json` többnapos upsert (insert-if-absent régi, felülír
  friss) + `tortenet_visszapotlas_nap` config + `futtato` bekötés (TDD).
- **Task 6:** `.github/workflows/napi.yml` — **dispatch-only**, szelektív add,
  commit-ha-diff, concurrency, permissions.
- **Task 7 (idő-kapuzott):** a `schedule: "7 19 * * *"` hozzáadása külön kis
  committal — **a kézi futások megfigyelése után**. Ez a task a valós
  runner-viselkedésre vár; a többi task után, akár napokkal később zárul.
- **Task 8:** `docs/index.html` placeholder + Pages-bekapcsolás dokumentálása.
- **Task 9:** README-kiegészítés (workflow, Pages, napló-cap, önjavítás) +
  escalation-függelék.
- **Záró:** ledger-bejegyzés a plan végén + az első éles `workflow_dispatch`
  megfigyelt kimenete.

## 10. Elfogadási feltételek

1. A teljes teszt-suite zöld; a 3 Minor-fix TDD-vel rögzített.
2. A kulcsszó-`tortenet.json` egy szimulált kimaradt nap után a **következő**
   futásból visszatölti a hiányzó napot (0 extra hívás), a rögzített napok
   értékei stabilak (insert-if-absent); a CSV és `legfrissebb.json` egynapos marad.
3. A `naplo.csv` a cap fölött fejléc + utolsó N sorra korlátozódik, sorrend-tartón.
4. A `workflow_dispatch` futás lefut, és **csak** `docs/data/*.json` +
   `adatok/naplo.csv` változást commitol (per-futás CSV-t nem); teljes blokknál
   nem-nulla kód.
5. A Pages a `main` /docs-ból kiszolgálja a placeholder oldalt, a data-URL-ek
   elérhetők.
6. Új kulcsszó felvétele továbbra is kizárólag a `config.yaml` szerkesztésével
   működik (Phase 1-es garancia sértetlen).

## 11. Megjegyzés a következő fázishoz (Phase 3, nem itt)

A teljes webes felület (Chart.js, csoportszűrő, dátumválasztó, hírek,
reszponzív, hibatűrő JSON-betöltés) az eredeti spec 9. pontja szerint külön
tervben, saját spec → plan → implementáció ciklusban készül, a most élővé tett
Pages-infrára és a napi JSON-kimenetre építve.
