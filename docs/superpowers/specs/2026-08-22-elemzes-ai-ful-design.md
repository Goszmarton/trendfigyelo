# Elemzés-fül — napi AI-elemzés (Claude) — tervdokumentum (spec)

**Dátum:** 2026-08-22
**Repó:** Goszmarton/trendfigyelo (publikus)
**Állapot:** jóváhagyott terv, implementáció előtt (Phase 4)
**Modell:** `claude-sonnet-5` (Anthropic Python SDK)

## 1. Cél és kontextus

Új **„Elemzés"** fül a honlapon, amely **minden nap automatikusan** egy AI-elemzést
(Claude, Sonnet 5) készít a friss adatokból, és statikus artefaktként megjeleníti.
Az elemzés két blokkja:

1. **Kulcsszavak** (a 13 követett szó): mit látunk ma; a teljes kép; a gördülő
   1 hét trend-irányai; mit lehet ebből leszűrni.
2. **Felkapott keresések** (a napi `top_trendek`): napi elemzés + gördülő heti
   összesítés.

Plusz két, a jóváhagyáskor kért követelmény:

3. **„Mi változott ma?"** — a mai VALÓS számok különbsége a tegnapihoz képest
   (irányt váltott szavak, új/eltűnt felkapott kifejezések, legnagyobb mozgók),
   AI-narratívával.
4. **Archívum + visszakereshetőség** — a napi elemzések gyűlnek a honlapon, a
   már megépített naptár-választóval visszalapozhatók.

Az adat már strukturált JSON-ban áll (`kulcsszo_nyers`/`kulcsszo_lanc`/
`kulcsszo_regresszio` a 13 szóra; `legfrissebb.top_trendek` a felkapottakra;
`tortenet.napok` a napi történet). Az AI-nak nem kell „böngésznie" — a commitolt
adatfájlok EGYBEN a honlap adatai, azokat olvassa a backend.

**A programnyelv Python** (a gyűjtő is az); a megbízhatóság és a helyesség elsődleges.

## 2. Két kiemelt, nem-alkudható követelmény

### 2.1 A számokat PYTHON számolja, nem az AI (MÉRJ, NE TIPPELJ)

A rendszer legnagyobb kockázata, hogy egy AI kitalál számot vagy okot. Ezért:

- **VALÓS réteg (determinisztikus, Pythonból):** szavankénti trend-irány, meredekség,
  érvényesség a `kulcsszo_regresszio.json`-ból; csúcs/átlag/pontszám a
  `nyers`/`lanc`/`tortenet`-ből; a felkapottak volumene + növekedése a
  `legfrissebb.top_trendek`-ből; gördülő 7-nap statisztikák; nap-diffek.
- **Az AI SOHA nem talál ki számot** — kizárólag a payloadban kapott számokból ír.
  A számok a payloadban mennek át; a válasz strukturált (json_schema).
- A determinisztikus számok az artefaktban is tárolódnak (a VALÓS réteg forrása),
  a frontend ezeket badge-ként/csempeként rajzolja — külön az AI-narratívától.

### 2.2 Jelölési fegyelem: megfigyelés ≠ ok; VALÓS vs ELMÉLETI

A system prompt kőbe vési (a repo `naming-discipline` elve):

- Ok-okozatot **tényként SOHA nem** állít.
- Minden hipotézist **KÜLÖN, explicit `ELMÉLETI`** mezőben ad vissza, „feltételezés"
  megfogalmazással.
- A felkapott híreknél csak a kapott `hirek`/`temak` mezőkből dolgozik — nem talál
  ki hírt, forrást vagy eseményt.
- A tényszerű megfigyelés (mit mutatnak a számok) és a magyarázat (miért) mindig
  külön mezőben.

## 3. Architektúra és adatfolyam

Négy komponens, tiszta határokkal:

```
napi.yml (adat-commit)  ──workflow_run(success)──▶  elemzes.yml
                                                       │ checkout (friss adat)
                                                       ▼
  docs/data/*.json  ──▶  elemzo.py                     │
     ├─ beolvas                                        │
     ├─ epit_payload()  (determinisztikus VALÓS számok)│
     ├─ Claude-hívás (Sonnet 5, kliens-varrat mögött)  │
     └─ valasz_to_artefakt()  ──▶  docs/data/elemzes.json (legfrissebb)
                                    docs/data/elemzesek/ÉÉÉÉ-HH-NN.json (archívum)
                                    docs/data/elemzesek/index.json
                                                       │ külön commit
                                                       ▼
  docs/elemzes.html + renderer  ──▶  a felhasználó látja (statikus)
```

### 3.1 Backend — `trendfigyelo/elemzo.py`

Négy elkülönített, egyenként tesztelhető rész:

- **`epit_payload(adatok, mai_datum) -> dict`** — TISZTA, determinisztikus. Az átadott
  adatokból (nem globálisan olvasva) felépíti a VALÓS számokat: szavankénti irány/
  meredekség/csúcs/átlag/érvényesség, top-felkapott lista, gördülő 7-nap aggregátumok,
  ÉS a nap-diff (lásd 3.2). Nincs I/O a függvényen belül a fájl-átvételen túl.

  **Adatforrások (mind meglévő, csak OLVASSUK):**
  - kulcsszavak, mai: `kulcsszo_regresszio.json` (irány/meredekség/érvényesség),
    `kulcsszo_nyers.json` + `kulcsszo_lanc.json` (csúcs/átlag/pont).
  - kulcsszavak, gördülő 7 nap: `tortenet.json` `napok[]` (napi szó-statisztikák:
    átlag/csúcs/érvényes-pontok) az utolsó 7 napra.
  - felkapott, mai: `legfrissebb.json` `top_trendek` (kifejezés/volumen/növekedés/témák/hírek).
  - felkapott, gördülő 7 nap: `docs/data/napok/<datum>.json` `trendek[]` az utolsó 7 napra
    (ugyanaz az alak — MÉRVE 2026-08-22: 29 nap történet áll rendelkezésre). Ha egy nap
    hiányzik, a hét részleges → az AI ezt jelzi, nem fabrikál.
  - nap-diff: az `elemzesek/<tegnap>.json` VALÓS `szamok` blokkja (3.2).
- **`elemez(payload, kliens) -> valasz`** — a Claude-hívás vékony burka. A `kliens` egy
  **injektálható varrat** (alap: `anthropic.Anthropic()`; teszt: kamu, ami kanonikus
  strukturált JSON-t ad). Sonnet 5, `output_config.format` json_schema, adaptív
  gondolkodás, `effort: "medium"`. A system prompt a 2.2 szabályokat rögzíti.
- **`valasz_to_artefakt(valasz, payload, mai_datum) -> dict`** — a validált AI-választ +
  a VALÓS számokat + a metaadatot az `elemzes.json` alakjára hozza (5. szakasz).
- **`futtat(...)`** — az összefűző: beolvas → payload → elemez → artefakt → lemezre ír
  (legfrissebb + archívum + index frissítés). **Hiba-tudatos:** ha a Claude-hívás
  elhasal (429, hálózat, refusal), az **előző `elemzes.json` MARAD**, FIGYELEM a logba,
  nem-nulla exit — a régi nézet nem törik. Az elemzés **NEM pótolhatatlan** (bármikor
  újragenerálható a nyers adatból), ezért ez a fail-soft elfogadható.

### 3.2 Nap-diff („Mi változott ma?")

A `epit_payload` a **tegnapi archivált elemzés** (`elemzesek/<tegnap>.json`) VALÓS
`szamok` blokkját összeveti a maival:

- **irányt váltott** szavak (emelkedő↔csökkenő↔lapos);
- **legnagyobb mozgók** (meredekség/átlag legnagyobb abszolút változása);
- **felkapott: új és eltűnt** kifejezések (mai `top` halmaz vs tegnapi);
- ha nincs tegnapi archívum (első futás), a diff üres → az AI ezt jelzi
  („nincs összevethető előző nap"), nem talál ki változást.

A diff determinisztikus (Python); az AI csak narrálja a kapott delta-listát.

### 3.3 Workflow — `.github/workflows/elemzes.yml`

- **Trigger:** `workflow_run` a `napi.yml` (Napi trendgyűjtés) **SIKERES** lefutására
  (`types: [completed]`, `if: workflow_run.conclusion == 'success'`) + `workflow_dispatch`
  (kézi teszthez). Nincs időzítés-tippelés; mindig a friss, épp commitolt adaton fut.
- **Concurrency:** közös `napi-futtatas` csoport (ne fusson a gyűjtéssel párban).
- **Secret:** `ANTHROPIC_API_KEY` (env-be adva a lépésnek).
- **Commit:** `git add` NÉVVEL, CSAK az elemzés-fájlokra
  (`docs/data/elemzes.json docs/data/elemzesek`), **külön commit** a napi adat-committól
  (a „külön adat-commit" elv). Artefakt-feltöltés mindig (hogy lássd, mi történt).
- **Előfeltétel (USER teszi meg, a kód nem):** a repo `ANTHROPIC_API_KEY` secretje.

### 3.4 Frontend — `docs/elemzes.html` + renderer

- Statikus oldal, a kész artefaktot rajzolja (mint az `adatokrol.html`).
- `#fomenu`: **Trendek / Elemzés / Az adatokról** (a menü bővül egy taggal).
- A fül szekciói (7. szakasz): Mi változott ma → Kulcsszavak (napi / teljes kép /
  1 hét) → Felkapott (napi / heti). A VALÓS számok csempeként/badge-ként; az AI-szöveg
  külön; az `ELMÉLETI` tételek megkülönböztető jelöléssel („feltételezés").
- **Archívum:** a meglévő inline naptár-választóval visszalapozható a korábbi napokra
  (`elemzesek/<datum>.json`); az `index.json` adja a választható napokat. A default a
  legfrissebb.

## 4. Modell és költség

- **`claude-sonnet-5`**, Python `anthropic` SDK, `messages` + `output_config.format`.
- Kurált payload (a kigyűjtött SZÁMOK, nem a 4 MB-os nyers JSON): ~10–20k input token/nap.
- ~2 érdemi hívás/nap (kulcsszavak; felkapott) → **filléres, ~havi pár dollár** (Sonnet 5
  bevezető ár $2/$10 per MTok 2026-08-31-ig, utána $3/$15).
- Nincs `temperature` (Sonnet 5 nem fogadja) — a stílus a prompttal irányítva.

## 5. Az `elemzes.json` alakja

```jsonc
{
  "frissitve": "2026-08-22T...Z",
  "modell": "claude-sonnet-5",
  "nap": "2026-08-22",
  "adat_bazis": { "nyers_veg": "...", "felkapott_frissitve": "...", "lanc_vegek": { "<szo>": "..." } },
  "valtozas": {                                  // „Mi változott ma?"
    "diff": { "irany_valtok": [...], "mozgok": [...], "felkapott_uj": [...], "felkapott_eltunt": [...] },  // VALÓS
    "szoveg": "...", "megfigyelesek": [...], "elmeleti": [...]
  },
  "kulcsszavak": {
    "szamok": [ { "szo": "...", "irany": "emelkedo|csokkeno|lapos", "meredekseg": 0.0,
                  "csucs": 0.0, "atlag": 0.0, "ervenyes": true } ],   // VALÓS réteg
    "napi":       { "szoveg": "...", "megfigyelesek": [...], "elmeleti": [...] },  // „mit látunk ma"
    "teljes_kep": { "szoveg": "...", "megfigyelesek": [...], "elmeleti": [...] },  // teljes nézet, minden szó
    "het":        { "szoveg": "...", "megfigyelesek": [...], "elmeleti": [...] }   // gördülő 7 nap, irányok
  },
  "felkapott": {
    "top":  [ { "kifejezes": "...", "volumen": "...", "novekedes_pct": "...", "temak": [...] } ],  // VALÓS
    "napi": { "szoveg": "...", "megfigyelesek": [...], "elmeleti": [...] },
    "het":  { "szoveg": "...", "megfigyelesek": [...], "elmeleti": [...] }         // heti összesítés
  }
}
```

Az `elemzesek/<datum>.json` ugyanez az alak egy adott napra; az `elemzes.json` a
legfrissebb másolata; az `elemzesek/index.json` = `{ "napok": ["2026-08-22", ...] }`.

## 6. Tesztelhetőség (TDD valódi RED-del, SOROS, MUTÁCIÓ==1)

- `epit_payload` — tiszta, determinisztikus → RED, ha egy szám/diff rossz (fabrikált
  bemeneti fájlokkal; a nap-diff RED-je: tegnapi archívummal vs anélkül).
- `valasz_to_artefakt` — kamu AI-válasszal, a mező-alak és a VALÓS-réteg átvétele
  ellenőrizve.
- `elemez` — a Claude-hívás a **varrat** mögött; a tesztek SOHA nem hívnak hálózatot
  (kamu kliens kanonikus strukturált JSON-t ad); a hiba-út (kamu dob 429-et) RED-del
  igazolja, hogy az előző artefakt MARAD.
- `futtat` — az archívum + index frissítés és a fail-soft lemez-viselkedés lemez-olvasóval
  igazolva (SZANDEKOS-ZOLD-VAK: a lemezt nézzük, nem a visszatérési értéket).
- Frontend renderer Playwright-tal, fixture `elemzes.json` ellen (SOROS); a VALÓS és az
  ELMÉLETI réteg vizuális szétválasztása szemlézve (SZEMLE-SZABÁLY).

## 7. A fül megjelenése (vázlat)

```
[ Trendek | Elemzés | Az adatokról ]      ← #fomenu

Elemzés — 2026-08-22        [◀ naptár ▶]  ← archívum-választó (meglévő helper)

▸ Mi változott ma?
   VALÓS: irányt váltott: X, Y · új felkapott: „…" · eltűnt: „…"
   [AI-szöveg]     · feltételezés (ELMÉLETI): …

▸ Kulcsszavak
   VALÓS csempék: szó → irány/meredekség/csúcs (13 szó)
   • Mit látunk ma  [AI]           · ELMÉLETI: …
   • Teljes kép     [AI]           · ELMÉLETI: …
   • 1 hét (irányok)[AI]           · ELMÉLETI: …

▸ Felkapott keresések
   VALÓS: top lista (volumen, növekedés, témák)
   • Napi   [AI]                   · ELMÉLETI: …
   • Heti összesítés [AI]          · ELMÉLETI: …
```

## 8. Munkamódszer (a repo kapui, változatlanul)

Magyar; `Co-Authored-By: Claude Opus 4.8` + `Claude-Session`; **külön adat-commit**;
SOROS suite; MUTÁCIÓ==1 körönként; commit CSAK jóváhagyott üzenettel; `git add` NÉVVEL;
**DOC-COMMIT a kód ELŐTT**; TDD valódi RED-del; a szándékos-zöld fedését MÉRNI; a canvas/
DOM-belső egyetlen őre a vizuális szemle; leltár-frissítés a lezáró commitban; a
`kulcsszo_nyers`/`kulcsszo_lanc` (pótolhatatlan órás ág) fájljaihoz **nem nyúlunk** —
csak OLVASSUK.

## 9. Ütemezés (szeletek)

A pontos szeletelést a writing-plans adja; a várható tagolás:

- **Sz1 — backend payload:** `epit_payload` + VALÓS számok + nap-diff, tesztekkel (0 AI-hívás).
- **Sz2 — Claude-varrat + artefakt:** `elemez` (kliens-varrat) + `valasz_to_artefakt` +
  `futtat` (archívum/index/fail-soft), kamu-klienssel.
- **Sz3 — workflow:** `elemzes.yml` (`workflow_run`, secret, külön commit, kézi teszt).
- **Sz4 — frontend:** `elemzes.html` + renderer + menü-bővítés + archívum-választó, Playwright.

## 10. Nyitott előfeltétel (USER)

A repo `ANTHROPIC_API_KEY` secretje (Settings → Secrets → Actions). Enélkül a Sz3
workflow nem tud hívni — a kézi (`workflow_dispatch`) teszt ekkor mutatja a hiányt.
