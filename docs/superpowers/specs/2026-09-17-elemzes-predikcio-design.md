# „Előrejelzések" rész a napi (esti) AI-elemzésben — design

**Állapot:** jóváhagyott terv (chat), implementáció előtt.
**Dátum:** 2026-09-17.
**Előzmény:** [[predikcio-loess]] (LOESS-előrejelzés, 5 horizont), [[elemzes-ful-fast-follow]] (napi AI-elemzés).
Ez a [[predikcio-loess]] „AI-elemzés predikció-összefoglaló külön kör" NYITOTT tételét zárja.

## 1. Cél

A napi (esti) AI-elemzés kapjon egy új, tömör **„Előrejelzések"** szekciót, amely a követett
kulcsszavak **közeltávú előrejelzéseit** foglalja össze folyó, grounded magyar prózában: mely
keresések előrejelzése emelkedik/csökken a közeljövőben, melyik a legmagabiztosabb, és őszintén jelzi
a bizonytalanokat. **Őszinte keret:** az előrejelzés a közelmúlt trendjének matematikai folytatása,
NEM eseményjóslat.

**Döntések (USER):** (a) tartalom = **közeltávú kitekintés**; (b) hatókör = **csak az esti** (teljes)
elemzés — a reggeli scoped pillanatkép nem kapja; (c) mélység = **egy tömör rész** (folyó próza).

## 2. Az adat — közeltávú előrejelzés-összefoglaló (payload)

A predikció-adat a két regresszió-fájl **merge**-éből jön (mint a frontendnél): az
`elemzo.futtat` MOST csak a `kulcsszo_regresszio.json`-t tölti; a `kulcsszo_masodlagos_regresszio.json`-t
is betöltjük, és szavanként `predikcio = {**elsődleges, **másodlagos}` (a másodlagos NYER).

**Near-term horizont kiválasztása (skála-konzisztens):** szavanként a `("1_nap","1_het","1_ho")` közül
a LEGRÖVIDEBB, amelynek merged blokkja `pont`-ja ≥2 pontból áll (a sentinel `{nem_becsulheto}` és a
hiányzó/1-pontos kihagyva). Így az irányt a forecast SAJÁT trajektóriájából (`pont`) számoljuk —
nincs kereszt-forrású skála-eltérés, és minden szó (órás/napi/heti) a legfinomabb ÉRTELMES horizontját
kapja: órás→„1 nap" (24 pont), napi→„1 hét" (7 pont), heti→„1 hó" (~4 pont, mert a heti 1_hét 1 lépés).

**Per-szó összefoglaló** (csak azoknál, amelyeknek van használható near-term blokkjuk):
- `szo`, `domen`
- `horizont`: a választott horizont emberi címkéje („1 nap" / „1 hét" / „1 hó")
- `valtozas_pont`: `round(pont[utolsó].ertek − pont[első].ertek, 1)` — a forecast-ablakon belüli
  nettó szintváltozás (0–100 skálán)
- `irany`: `"emelkedik"` ha `valtozas_pont > IRANY_DEADBAND`, `"csökken"` ha `< −IRANY_DEADBAND`,
  különben `"stagnál"` (kezdő `IRANY_DEADBAND = 2.0` pont)
- `megbizhatosag`: a blokk `megbizhatosag`-ja (0–1)
- `sav_pont`: `round((felso[utolsó].ertek − also[utolsó].ertek) / 2, 1)` — a bizonytalansági sáv
  fél-szélessége a horizont végén (± pont); nagy érték = bizonytalan előrejelzés

**Összesítés:** `osszesites = {emelkedo, csokkeno, stagnalo}` darabszámok, hogy az LLM lássa az arányokat.

A payload `predikcio` blokkja: `{"szavak": [...], "osszesites": {...}}`. CSAK `mode != "reggel"` esetén
épül; ha egyetlen szónak sincs használható near-term forecastja, a blokk kimarad (fail-soft).

## 3. A séma és a prompt

### 3.1 Séma (`_valasz_sema`, csak `mode="este"`)
Új `predikcio` kulcs = `_szekcio_sema()` (egyetlen folyó `{szoveg}` szekció). Kötelező mezők:
`["valtozas", "kulcsszavak", "felkapott", "predikcio"]` (+ `youtube`, ha van). A reggeli séma
VÁLTOZATLAN (nincs predikció). Fail-soft: ha a payloadban nincs `predikcio` blokk (nincs adat), a
séma akkor is kérheti a szekciót, de a prompt kimondja, hogy ilyenkor egy rövid „ma még nincs
előrejelzés" mondat íródjon — VAGY a `predikcio` a payload jelenlététől függően kerül a required-be.
**Döntés:** a `predikcio` a required-ben van ha a payload tartalmaz `predikcio` blokkot; enélkül nem
kérjük (a séma dinamikus a payload alapján). Így nincs üres-erőltetett szekció.

### 3.2 Prompt (RENDSZER_PROMPT bővítés, új szabály)
Új bekezdés-szabály az „Előrejelzések" szekcióhoz:
- A rész a követett kulcsszavak **közeltávú előrejelzését** foglalja össze — mire számíthatunk a
  közeljövőben az egyes keresések iránya alapján.
- **Őszinte keret KÖTELEZŐ:** kimondod, hogy ez a közelmúlt trendjének **matematikai folytatása**,
  nem eseményjóslat; a valóság eltérhet.
- **Kiemelés:** a legvilágosabb, legmagabiztosabb közeltávú mozgókat (fel és le) emeld ki, a
  megbízhatóság és a bizonytalansági sáv alapján; a nagyon bizonytalanokat (széles sáv / alacsony
  megbízhatóság) őszintén jelezd („ezt egyelőre nem lehet biztosan megmondani").
- **NEM** sorolod fel újra minden szót (azt a mai/változás szekciók megteszik) — a forward-looking kép
  a lényeg; a szokásos/stagnáló többséget egy-két mondattal, csoportosítva összefoglalod.
- Ugyanazok a szabályok: KIZÁRÓLAG a kapott számokból; folyó bekezdés, felsorolás/mezőnév/„payload"
  TILALMA; óvatos ok-okozat; rövid „–" gondolatjel; számot sosem találsz ki.

## 4. Architektúra

### 4.1 Backend (`trendfigyelo/elemzo.py`)
- `futtat`: az `adatok`-hoz `"masodlagos_regresszio": _betolt(docs_data / "kulcsszo_masodlagos_regresszio.json") or {}`.
- ÚJ `_predikcio_kozeltav(regresszio, masodlagos) -> dict | None` — a merge + near-term kiválasztás +
  per-szó összefoglaló + összesítés (determinista, tiszta; nincs argless `datetime.now()`).
- `epit_payload`: `mode != "reggel"` ágon `p = _predikcio_kozeltav(regresszio, adatok.get("masodlagos_regresszio", {}))`;
  ha `p`, akkor `payload["predikcio"] = p`.
- `_valasz_sema(youtube, mode, predikcio=False)`: a `predikcio` paraméter true-nál a required+properties
  bővül a `predikcio` szekcióval (este). Az `elemez`/`futtat` a payloadban lévő `predikcio` jelenlétéből
  adja tovább a flaget.
- `RENDSZER_PROMPT`: a 3.2 szabály hozzáfűzve.

### 4.2 Frontend (`docs/js/elemzes.js`)
- Új szekció a „Google kulcsszavak" csoportban, a „Mi változott ma?" (valtozas) UTÁN:
  `t.appendChild(szekcio_elem("Előrejelzések – mire számíthatunk?", art.predikcio));` — CSAK ha
  `art.predikcio` létezik (fail-soft: régi archív-nap, reggeli elemzés → nincs `predikcio` → kimarad).

### 4.3 Adat-séma (`docs/data/elemzes.json`, este)
`{ ..., "predikcio": { "szoveg": "…" }, ... }` — additív; a régi napok (nincs `predikcio`) érintetlenek,
a frontend fail-soft.

## 5. Tesztelés (TDD)

- **Backend `_predikcio_kozeltav`** (fabrikált regresszió+másodlagos): a merge a másodlagost preferálja;
  a near-term a legrövidebb ≥2-pontos horizont; az `irany` deadband-del helyes (emelkedik/csökken/stagnál);
  a `valtozas_pont`/`sav_pont` a `pont`/`also`/`felso`-ból; a `osszesites` számol; sentinel/1-pontos kihagyva;
  üres → None.
- **`epit_payload`**: `mode="este"` + van predikció → `payload["predikcio"]` jelen; `mode="reggel"` →
  NINCS `predikcio`.
- **Séma/prompt** MOCKOLT SDK-val (mint az elemzo-tesztek): a `predikcio`-flag true-nál a séma kéri a
  szekciót; a válaszban megjelenik; fail-soft, ha nincs adat.
- **Frontend (e2e):** mockolt `elemzes.json` `predikcio`-val → a fül kirajzolja az „Előrejelzések – mire
  számíthatunk?" szekciót; `predikcio` nélküli (régi) artefakt → a szekció KIMARAD (nincs hiba).

## 6. Hatókörön KÍVÜL (v1)
- Hosszú-táv (1 hó/3 hó/1 év) narratíva; a reggeli elemzés predikció-része; a „nem becsülhető" (órás-only
  hosszú táv) esetek külön tárgyalása (a near-term úgyis mindig becsülhető).
- A predikció-számítás magja (`predikcio.py`) VÁLTOZATLAN — csak olvassuk a kimenetét.

## 7. Global Constraints (a specből, minden taskra kötelező)
- Tiszta numpy + meglévő anthropic SDK; **NULLA új Python-dependency**. Additív, MUTÁCIÓ=1.
- Backend tesztelt logikában NINCS argless `datetime.now()` / `seged.most_utc()`.
- Frontend: NINCS `new Date()` / `Date.now()`.
- Irreplaceable adat READ-ONLY.
- SOROS suite: `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`.
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással.
- Az élő generálás igényli az `ANTHROPIC_API_KEY`-t (a mockolt tesztek NEM); a valós esti elemzés a
  szerver-cronban fut a kulccsal.
