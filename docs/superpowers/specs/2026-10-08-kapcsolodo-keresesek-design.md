# Kapcsolódó keresések követése (F4) — design

**Állapot:** jóváhagyott terv (chat), implementáció előtt.
**Dátum:** 2026-10-08.
**Előzmény:** [[bovites-ful]] (a Bővítés fül F1–F3 — ebbe kerül az F4 új szekciója), `trendfigyelo/kliens.py` (`Kliens.hivas` throttle/429), `trendfigyelo/masodlagos_only.py` (saját szűk plafonú, staleness-választó, soft-fail belépő — az F4 gyűjtés mintája), [[reggeli-esti-felkapott]] (a felkapott napfájlok forrása), [[napi-futas-megbizhatosag]] (workflow-lánc), [[working-style-gates]].

## 0. Kontextus és SPIKE-eredmény

Ez a Bővítés fül **4. feature-e** (az F1–F3 már ÉL). USER-döntés: a kapcsolódó kereséseket arra gyűjtsük, **amit az emberek NAPONTA ténylegesen kerestek** = a **felkapott (trending) kifejezésekre**, nem a 28 követett kulcsszóra; naponta pár téma (staleness-cap); új szekció a Bővítés fülön.

**SPIKE (igazolt, élő hívással):** `trendspy==0.1.6` (már dependency) `Trends.related_queries(keyword, timeframe='today 12-m', geo='', cat=0, gprop='', headers=None)` → `{'top': DataFrame, 'rising': DataFrame}`, oszlopok `['query','value']`. `top.value` 0–100 (relatív népszerűség), `rising.value` = % növekedés (int) VAGY „Breakout" (string). **A related endpointnak KÜLÖN, SZIGORÚ kvótája van** (`TrendsQuotaExceededError`), és **kötelező a referer-header**: `headers={'referer':'https://www.google.com/'}` (header nélkül azonnal kvóta-hiba; headerrel sikeres). Példa `benzin` → top: *benzin ár, mol benzin*; rising: *benzin védett ár, benzin ársapka, hatósági áras benzin*.

## 1. Cél

Egy új **„Kapcsolódó keresések" szekció a Bővítés fülön**: a napi felkapott témák mögé nézünk be — témánként a **top** (megszokott) és **rising** (most felfutó) kapcsolódó Google-keresések. „Mire kíváncsiak egy témán belül az emberek?" ÚJ adatgyűjtés; nincs backfill.

## 2. Architektúra — IZOLÁLT, saját-plafonú gyűjtő-job (a `masodlagos_only` mintája)

A szigorú related-kvóta miatt az F4 **külön job**, saját `Kliens`-szel és saját SZŰK plafonnal → a related-kvóta kimerülése **NEM veszélyezteti a fő (pótolhatatlan órás) gyűjtést**. A `futtato.py` plafonja/`tervezett_hivasszam`-ja VÁLTOZATLAN.

- **`trendfigyelo/kapcsolodo.py`**:
  - `jeloltek(docs_data, meglevo, most, cap, staleness_nap, napok_vissza=2)`: a legutóbbi `napok_vissza` nap `napok/<nap>.json` felkapott kifejezéseit aggregálja (max volumen), KIHAGYJA azokat, amelyek a `meglevo`-ben `staleness_nap`-on belül frissültek, volumen szerint csökkenőben rendez, és a top `cap` kifejezést adja vissza. Determinista, csak olvas.
  - `_parse_related(eredmeny, limit)`: a trendspy `{top, rising}` dict-ből (DataFrame VAGY None) → `{top:[{query, value}], rising:[{query, value}]}`; defenzív (üres/None → `[]`; `value` int ha numerikus, különben a string pl. „Breakout"); listánként `limit` (pl. 15) elemre vágva.
  - `related_egy(kliens, kif, config, timeframe)`: `kliens.hivas("kapcsolodo", kliens.tr.related_queries, kif, geo=config.geo, timeframe=timeframe, headers={"referer":"https://www.google.com/"})` → `_parse_related`. **SOFT-FAIL per szó**: `AgFeladva`/`PlafonTullepve`/bármely hiba → `None` (kihagyva + FIGYELEM-log), a job NEM dől el.
  - `gyujt(docs_data, kliens, config, most, cap=CAP, timeframe=TIMEFRAME, staleness_nap=STALENESS_NAP, retencio=RETENCIO)`: betölti a meglévő `kapcsolodo.json`-t → `jeloltek` → kifejezésenként `related_egy` (soft-fail) → a sikeres eredményt bemergeli (a kifejezés bejegyzése `lekerdezve=most`, `top`, `rising`, `volumen`) → `lekerdezve` szerint csökkenőben tartja, a `retencio`-n túli (legrégebben lekérdezett) kifejezéseket elvágja → visszaadja a dict-et.
  - `kapcsolodo_ir(docs_data, adat)`: atomi írás `docs/data/kapcsolodo.json` (`json_export._ir_json`).
- **`kapcsolodo.py`** (repo gyökér, belépő — a `masodlagos_only`/`heti.py` mintája): `config = betolt()`, `kliens = Kliens(config, plafon=cap*config.max_probak + 1)` (saját SZŰK plafon — kvóta-védelem), `adat = kapcsolodo.gyujt(docs_data, kliens, config, seged.most_utc(), ...)`, `kapcsolodo.kapcsolodo_ir(docs_data, adat)`. Fail-soft; CLI `--cap` opció.
- **`trendfigyelo/kapcsolodo_orzo.py`**: NAPI egyszer-őr (az `elemzes_orzo`/`bovites_orzo` mintája) — a `kapcsolodo.json` `frissitve` LOGIKAI napja (`seged.esti_nap`) alapján, hogy a napi backup-újraindítások NE égessenek el extra related-kvótát. Kimenet: „kell"/üres.
- **`.github/workflows/kapcsolodo.yml`**: `workflow_run` a **„Napi trendgyűjtés"** (esti, a teljes napi felkapott után) befejezésére + `workflow_dispatch` (opcionális `cap`); őr a `pip install` ELŐTT; commit CSAK `docs/data/kapcsolodo.json`; **NINCS ANTHROPIC_API_KEY** (nincs LLM); `git pull --rebase --autostash`; soft-fail (a job hibája nem blokkol mást).

## 3. Adat — `docs/data/kapcsolodo.json`
```
{ frissitve: <iso>, kifejezesek: [
    { kifejezes: string, lekerdezve: <iso>, volumen: int,
      top:    [{query: string, value: int}],
      rising: [{query: string, value: int|string}] }
] }  # lekerdezve szerint csökkenőben, max RETENCIO kifejezés
```

## 4. Frontend — új szekció a Bővítés fülön
- **`docs/bovites.html`**: egy új `<section id="bovites-kapcsolodo">` a meglévő `#bovites-ugyek` után.
- **`docs/js/bovites.js`**: betölti a `data/kapcsolodo.json`-t (fail-soft: hiányzik → a szekció „még nem érhető el" / kihagyva, a többi blokk változatlan); rendereli kifejezésenként: a felkapott téma + a **top** (megszokott) és **rising** (most felfutó) kapcsolódó keresések (chip/lista; a „Breakout"/nagy % jelölve). Legfrissebb elöl.
- **Infó-oldal**: egy 4. doboz a meglévő „A Bővítés fül" csoportba a kapcsolódó keresésekről (Google Trends related, naponta pár felkapott téma, top+rising).
- Nav VÁLTOZATLAN (7 fül; nincs új fül).

## 5. Rulings (defaultok)
`CAP = 6` (kifejezés/futás), `TIMEFRAME = "today 3-m"`, `STALENESS_NAP = 7` (egy kifejezés ~hetente frissül újra), `RETENCIO = 30` (az utolsó 30 lekérdezett kifejezés), `TOP_LIMIT = 15` (lista-hossz top/rising). A referer-header a `related_egy`-ben FIX. Az `ag` = `"kapcsolodo"`.

## 6. Hatókörön KÍVÜL
- A 28 követett kulcsszó related-gyűjtése NEM (USER: a felkapottakra).
- A fő `futtato.py` gyűjtés/plafon VÁLTOZATLAN (külön job, külön Kliens/plafon).
- related_topics / suggestions NEM (csak related_queries); backfill NEM.
- Az F1–F3 (Bővítés) séma/logika VÁLTOZATLAN — csak egy új szekció + egy új adatfájl adódik.

## 7. Tesztelés (TDD)
- `tests/test_kapcsolodo.py`: `jeloltek` (befőttes napfájlok top-volumen + staleness-kizárás + cap); `_parse_related` (DataFrame→lista, None/üres→[], „Breakout"/string value megőrzése, limit-vágás); `related_egy` SOFT-FAIL (mock kliens AgFeladva/Exception → None, nem dob); `gyujt` (mock Kliens injektált fake `related_queries`-szel → merge, lekerdezve, retenció-vágás); `kapcsolodo_ir` atomi.
- `tests/test_kapcsolodo_orzo.py`: napi idempotencia (mai frissitve → skip; korábbi → kell; hajnali él).
- `tests/test_kapcsolodo_belepo.py` + `tests/test_kapcsolodo_workflow.py`: a belépő (mock, saját plafon), a yml (workflow_run a „Napi trendgyűjtés"-re, őr a pip install előtt, commit csak `docs/data/kapcsolodo.json`, NINCS ANTHROPIC_API_KEY).
- `e2e/bovites.spec.js` (kiterjesztés): a `#bovites-kapcsolodo` szekció top+rising renderelése `van`/`nincs` adaton; fail-soft hiányzó `kapcsolodo.json`-nál.
- `e2e/menu.spec.js` (Infó): a „A Bővítés fül" csoport doboz-száma 31→32 (a 4. doboz).

## 8. Global Constraints
- NULLA új Python-dependency (trendspy már dependency; pandas már dependency a DataFrame-ekhez). Frontend: nincs új vendor/külső betöltés.
- **A referer-header (`{'referer':'https://www.google.com/'}`) KÖTELEZŐ** minden related-hívásnál (a spike igazolta). **SOFT-FAIL mindenhol**: a related-kvóta kimerülése NEM blokkol — a sikeres rész mentve, a job 0-val tér vissza.
- SAJÁT, SZŰK plafon (`cap × max_probak + 1`) — a fő napi gyűjtés plafonja/kvótája ÉRINTETLEN. A futás a `Kliens.hivas` throttle-jén (request_delay + szórás + 429-backoff) megy.
- Irreplaceable adat READ-ONLY (napok/*.json); atomi írás. NINCS argless `datetime.now()` a modul-logikában (a `most` PARAMÉTER; a belépő adja a `seged.most_utc()`-ot).
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; a workflow commit CSAK `docs/data/kapcsolodo.json`. Push külön kapuzott kör. SOROS suite (pytest + Playwright) zöld. SDD-folyamat.
- Fájlnév-ütközés ELŐZETES ellenőrzése (tanulság): `kapcsolodo.py`, `kapcsolodo_orzo.py`, `kapcsolodo.yml`, `kapcsolodo.json`, `test_kapcsolodo*` — ütközés-vizsgálat a pre-flightban.
- ÉLŐ-figyelem: a related-kvóta viselkedése a GitHub-runner IP-n (efemer, futásonként más — ez akár KEDVEZŐ is lehet); az első éles futás kvóta/parszolás-ellenőrzése.
