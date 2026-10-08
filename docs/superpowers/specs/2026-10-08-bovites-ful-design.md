# Bővítés fül — elmozdulásfigyelő + ügy-életút + közpolitikai szűrő — design

**Állapot:** jóváhagyott terv (chat), implementáció előtt.
**Dátum:** 2026-10-08.
**Előzmény:** [[heti-ertekeles-ful]] (heti LLM-összegző — a HETI/HAVI LLM-kör mintája a F2-höz), [[havi-nlp-elemzes]] (havi klaszterezés — a szemantikus csoportosítás mintája), `trendfigyelo/regresszio.py` (per-kulcsszó szokásos-szint/eltérés = a F1 forrása), `docs/js/app.js` `chart_letrehoz` (a predikció-sáv `fill:"-1"` technikája = a F1 szokásos-sáv mintája), [[working-style-gates]], [[naming-discipline]].

## 0. Hatókör és sorrend (USER-döntés)

Ez az ELSŐ alprojekt: a Bővítés fül **F1+F2+F3** feature- e egy SDD-körben. A **F4 (kapcsolódó keresések, ÚJ Google Trends gyűjtés)** KÜLÖN spec+kör lesz utána (nagyobb rate-limit/megbízhatósági kockázat) — ez a spec NEM tartalmazza.

USER-döntések: F1-sáv a MEGLÉVŐ Google Trendek chartokon (kapcsolóval); F2-összekapcsolás LLM-mel (Claude Opus csoportosít, a Python számol); F3 ÚJ 8-kategóriás közpolitikai taxonómia; F2-kadencia gördülő 30 nap, naponta az esti gyűjtés után.

## 1. Cél

Egy új **„Bővítés" fül** három, a MÁR MEGLÉVŐ adatokra épülő képességgel:
1. **Elmozdulásfigyelő** — szokatlan keresési elmozdulások: egy kulcsszó a megszokotthoz képest emelkedik/csökken-e, **mekkora az eltérés**, **mióta tart**, **mennyire megbízható**; „szokatlan változások" blokk; a megszokott tartomány **halvány sávként** a kulcsszó-grafikonokon.
2. **Ügyek életútja** — egy ügy egyszeri felvillanás vagy tartós-e; a kifejezéseket **LLM** kapcsolja üggyé; determinista besorolás (újonnan megfigyelt / folyamatosan jelenlévő / visszatérő; mozgás: erősödő / stabil / lecsengő / nem megállapítható); rendezhető ügy-lista + idővonal.
3. **Közpolitikai relevanciaszűrő** — ÚJ 8-kategóriás szakpolitikai taxonómia az ügyekhez/kulcsszavakhoz rendelve; szűrők (szakpolitika / Google-kategória / téma).

Grounding: a Python a VALÓS számokat adja (szokásos szint, eltérés, életút-metrikák); az LLM CSAK csoportosít/nevez/sorol be (a korpuszból, nem talál ki). A napi/heti/havi elemzés és a backend-számítás VÁLTOZATLAN.

## 2. F1 — Elmozdulásfigyelő (DETERMINISTA, LLM nélkül)

### 2.1 Backend — `trendfigyelo/elmozdulas.py` → `docs/data/elmozdulas.json`
Az esti `futtato.py`-ban fut a regresszió UTÁN (zéró Google-hívás, determinista, mint a `kategoriak_ir`). Olvas: `kulcsszo_regresszio.json` + `kulcsszo_masodlagos_regresszio.json` (az `egyesitett` nézethez), `kulcsszo_nyers.json` / `kulcsszo_masodlagos_nyers.json` (a „mióta tart" nyers sorhoz), `tortenet.json`.

Per követett kulcsszó, egy **elsődleges intervallumból** (óránkénti szónál `1_het`, napi/heti szónál `1_ho`) számol:
- `szokatlan` (bool): `illeszkedes != "illeszkedik"`.
- `irany`: `emelkedik` / `csokken` (a `mai_reziduum` előjele / `illeszkedes` felette/alatta).
- `elteres`: normált eltérés = `mai_reziduum / max(reziduum_szokasos, SAV_MIN)` (hány „szokásos sávnyira" van); `elteres_nyers` = `mai_reziduum`.
- `idotartam_pont` (ÚJ): hány egymást követő LEGUTÓBBI nyers pont maradt a szokásos sávon kívül (a trendvonalhoz mért reziduum alapján, visszafelé számolva); `idotartam_ota_utc`: az első ilyen pont időbélyege (az eltérés kezdete).
- `megbizhatosag`: `magas` / `kozepes` / `alacsony` az `r2` + `pontok_hasznalt` + `se_meredekseg` egyszerű kombinációjából.
- `sav` (a charthoz): per intervallum `{also: [{idopont_utc, ertek}], felso: [...]}` = `illesztes_vonal` ± `max(SAV_SZORZO*reziduum_szokasos, SAV_MIN)` a két végponton (a `_illeszkedes_allapot` küszöbével konzisztens: `SAV_SZORZO=2.0`, `SAV_MIN=3.0`).

Kimenet `elmozdulas.json`: `{szamitva_utc, kulcsszavak: {<szo>: {szokatlan, irany, elteres, elteres_nyers, idotartam_pont, idotartam_ota_utc, megbizhatosag, domen, tipus, szakpolitika, sav: {<intervallum>: {also, felso}}}}, szokatlan_lista: [<szo> csökkenő |elteres| szerint, csak szokatlan=true]}`. A `szakpolitika` a `szakpolitika.py` determinista besorolásból (lásd §4).

### 2.2 Frontend — halvány sáv a MEGLÉVŐ kulcsszó-chartokon (`docs/js/app.js`)
A `chart_letrehoz`-ban a predikció-sáv `fill:"-1"` technikájával egy halvány „szokásos tartomány" sáv (az `elmozdulas.json` `sav` pontjaiból, az éppen mutatott intervallumhoz illesztve), **kapcsolóval BE/KI** (default KI, a nemlin/LOESS-kapcsoló mintája; a kapcsoló a vezérlősorban). Mindkét ág (kompakt category-x és teljes linear-x) kap sávot. A tooltip változatlan (csak `datasetIndex===0`). A fül maga NEM ismétli a 28 chartot.

## 3. F2 — Ügyek életútja (LLM csoportosít + Python számol)

### 3.1 Backend — `trendfigyelo/ugyek.py` → `docs/data/ugyek.json`
Gördülő **30 nap**, naponta az esti gyűjtés után (lásd §6 kadencia).

- `ugy_korpusz(docs_data, veg_nap, ablak_nap=30)` (determinista, csak olvas): a `napok/<nap>.json` felkapott kifejezéseit aggregálja az ablakban → per kifejezés `{kifejezes, elso_nap, utolso_nap, napok: [jelenléti napok], napok_szama, volumen_sor: [{nap, max_volumen}], temak, hirek(≤3)}`; + a 28 követett kulcsszó iránya a regresszióból. Per kifejezés DETERMINISTA életút-metrika:
  - `eletut`: `ujonnan_megfigyelt` (első nap az ablak utolsó ~7 napján belül ÉS rövid span) / `folyamatosan_jelenlevo` (a napok nagy részén jelen) / `visszatero` (van ≥1 napos szünet, majd újra jelen) / `egyeb`.
  - `mozgas`: `erosodo` / `stabil` / `lecsengo` / `nem_megallapithato` a `volumen_sor` egyszerű (robusztus) meredekségéből.
- `ugy_elemez(korpusz, kliens=None)` (LLM, Claude Opus streaming, strukturált JSON, bounded-retry 3×, fail-soft — a `heti_ertekeles`/`havi_nlp` mintája): a bemenet a korpusz (kifejezések + determinista metrikáik); a kimenet ÜGYEK: `{ugyek: [{nev, kifejezesek: [a korpuszból csoportosított kifejezések], szakpolitika: <a 8 enum egyike>, osszefoglalo: <rövid grounded próza>}]}`. Az LLM CSAK csoportosít + nevez + sorol be; NEM talál ki kifejezést.
- `grounding_validal`: minden ügy `kifejezesek`-je a korpusz kifejezés-halmazára szűrve (nem-korpuszbeli kiesik); üres taggé vált ügy kiesik; `szakpolitika` a 8-enumra validálva (ismeretlen → a determinista `szakpolitika.py` besorolás a tagokból).
- `ugy_osszegez` (determinista POST-lépés): minden ügy ÉLETÚT-metrikáját a TAGJAI metrikáiból aggregálja (`eletut`/`mozgas`/`elso_nap`/`utolso_nap`/`napok_szama`/`idovonal` = a tag-kifejezések napi jelenlét-uniója). Így az ügy-szintű besorolás VALÓS számból áll, nem az LLM-től.

Kimenet `ugyek.json`: `{szamitva_utc, ablak: {kezdet, veg, nap}, modell, ugyek: [{nev, szakpolitika, eletut, mozgas, kifejezesek, elso_nap, utolso_nap, napok_szama, volumen_sor, idovonal: [{nap, jelen, ossz_volumen}], osszefoglalo}]}`.

### 3.2 Belépő/őr/workflow
`bovites.py` (belépő, az őr adta napra generál → fail-soft). `trendfigyelo/bovites_orzo.py` (NAPI őr: a `seged.esti_nap` logikai napon egyszer, idempotencia a `szamitva_utc` logikai napjából — az `elemzes_orzo`/`heti_orzo` mintája). `.github/workflows/bovites.yml` (`workflow_run` a „Napi trendgyűjtés"-re, őr a pip install előtt, commit CSAK `docs/data/ugyek.json`, `ANTHROPIC_API_KEY`). Az `elmozdulas.json` NEM itt készül (az a főfutásban, determinista).

### 3.3 Frontend — `docs/js/bovites.js`
Rendezhető **ügy-lista** (rendezés: frissesség / időtartam / mozgás / szakpolitika) + **idővonal** nézet (per ügy a napi jelenlét sávja az ablakon). Fail-soft üres adaton.

## 4. F3 — Közpolitikai taxonómia + szűrők

### 4.1 `trendfigyelo/szakpolitika.py` (ÚJ, izolált — a `config.yaml` gyűjtés-kritikus fájl ÉRINTETLEN)
- `SZAKPOLITIKAK`: a 8 kategória (slug + magyar címke): `szocialpolitika` (Szociálpolitika), `egeszsegpolitika` (Egészségpolitika), `oktataspolitika` (Oktatáspolitika), `gazdasag_foglalkoztatas` (Gazdaság- és foglalkoztatáspolitika), `lakhatas` (Lakhatás), `energia_rezsi` (Energia és rezsi), `kozelet_kozigazgatas` (Közélet és közigazgatás), `egyeb` (Egyéb / nem közpolitikai).
- `KULCSSZO_SZAKPOLITIKA`: a 28 követett kulcsszó → kategória (determinista kézi térkép; pl. nyugdíj/segély/fizetés→szocialpolitika v. gazdasag_foglalkoztatas a jelentés szerint; kórház/várólista/háziorvos/műtét/sürgősségi/betegség→egeszsegpolitika; iskola/pedagógus→oktataspolitika; infláció/munkanélküliség/csőd/állás→gazdasag_foglalkoztatas; albérlet/eladó lakás/hitel/kölcsön→lakhatas; benzin/rezsi/napelem→energia_rezsi; kormányablak/tüntetés/korrupció/kormány→kozelet_kozigazgatas; a többi→egyeb).
- `DOMEN_SZAKPOLITIKA`: az 5 domén → kategória (fallback).
- `GOOGLE_TEMA_SZAKPOLITIKA`: a Google angol témacímkék → kategória (pl. Politics/Law and Government→kozelet_kozigazgatas, Health→egeszsegpolitika, Business and Finance/Jobs and Education→gazdasag_foglalkoztatas…; az ismeretlen/Other→egyeb).
- `szakpolitika_besorol(kifejezes=None, domen=None, temak=None) -> slug`: kulcsszó-térkép → domén-fallback → Google-téma-fallback → `egyeb`.

Az LLM (F2) a `szakpolitika` enum-ot kapja és sorol be; a determinista besorolás a validáció/fallback. A F1 `elmozdulas.json` szintén kap `szakpolitika`-t (kulcsszó-térképből) → a szűrő a szokatlan-listát is szűri.

### 4.2 Frontend szűrők (`bovites.js`)
Egy vezérlősor: **szakpolitika-chipek** (8) + **Google-kategória** + **téma** szűrő, amelyek EGYSZERRE szűrik a szokatlan-változások blokkot ÉS az ügy-listát. (A legfelkapott-lista meglévő kategória-chip-mintája a `app.js`-ben a vizuális minta.)

## 5. Fül + navigáció
ÚJ `docs/bovites.html` (a `heti.html` mintája, Chart.js-sel az idővonalhoz/esetleges mini-chartokhoz). Nav **7. fül** MINDEN oldalon, sorrend: Napi Elemzések · Heti értékelés · Havi elemzés · Google Trendek · YouTube Trendek · **Bővítés** · Infó. (A „Bővítés" címke a USER szava; átnevezhető — kozmetikai.) Infó-oldal „A Bővítés fül" csoport.

## 6. Kadencia
- **F1 `elmozdulas.json`**: az esti főfutásban (`futtato.py`), minden esti gyűjtéskor, determinista. A `napi.yml` commit-lépése már `git add docs/data` → automatikusan commitolódik (nincs új workflow).
- **F2 `ugyek.json`**: ÚJ `bovites.yml`, `workflow_run` a „Napi trendgyűjtés" (esti) SIKERES futására; napi őr (egyszer/logikai nap) + fail-soft; külön commit CSAK `docs/data/ugyek.json`.

## 7. Séma (`ugyek._valasz_sema`, LLM)
```
{ ugyek: [ { nev: string, kifejezesek: [string], szakpolitika: <enum 8>, osszefoglalo: string } ] }
```
`additionalProperties:false`, minden mező kötelező; `szakpolitika` JSON-schema `enum` a 8 slugból. Az életút-mezők NEM az LLM-től jönnek (determinista post-lépés).

## 8. Prompt (`RENDSZER_PROMPT_UGYEK`)
A `havi_nlp`/`heti` mintája: magyar, grounded; a bemenet a 30-napos korpusz (kifejezések + determinista metrikák). Feladat: a KORPUSZ kifejezéseit **jelentés szerint** ÜGYEKbe csoportosítani (egy ügy = ugyanazon közügy/téma körüli kifejezések — pl. ugyanannak az árnak a különböző megfogalmazásai), minden ügynek rövid magyar NÉV, 1–2 mondatos grounded ÖSSZEFOGLALÓ, és a 8 szakpolitikai kategória egyike. SZABÁLYOK: csak a korpusz kifejezéseiből dolgozik (nincs kitalálás); egy kifejezés legfeljebb egy ügybe kerül; a besorolás a megadott jelentés/témák alapján; a prózába SOHA nem ír mezőnevet/JSON-t; rövid „–" gondolatjel.

## 9. Hatókörön KÍVÜL
- F4 (kapcsolódó keresések / új Google Trends gyűjtés) — KÜLÖN spec.
- A `config.yaml` (gyűjtés-kritikus) ÉRINTETLEN — a szakpolitika izolált modul.
- A napi/heti/havi elemzés, a regresszió/lánc-számítás, a YouTube-ág VÁLTOZATLAN.
- Szemantikus kifejezés-összevonás CSAK a F2 LLM-körében (nem a F1-ben, az determinista).

## 10. Tesztelés (TDD)
- `tests/test_elmozdulas.py`: `idotartam` (sávon kívüli egymás utáni pontok, befőttes nyers sorral), `elteres` normálás, `megbizhatosag` label, `sav` pontok, `szokatlan_lista` rendezés, `szakpolitika` mező; determinista (nincs LLM).
- `tests/test_ugyek.py`: `ugy_korpusz` (30-napos aggregálás, elso/utolso nap, napok_szama, volumen_sor), `eletut`/`mozgas` osztályozás (újonnan/tartós/visszatérő; erősödő/stabil/lecsengő/nem megállapítható), `_valasz_sema` (enum szakpolitika), `grounding_validal` (nem-korpuszbeli kifejezés kiesik, enum-validálás), `ugy_osszegez` (ügy-metrika a tagokból), `ugy_generalas` mock SDK-val.
- `tests/test_szakpolitika.py`: a 3-szintű besorolás (kulcsszó → domén → Google-téma → egyeb), mind a 28 kulcsszó kap kategóriát, a 8 enum.
- `tests/test_bovites_orzo.py` + `tests/test_bovites_belepo.py` + `tests/test_bovites_workflow.py`: napi őr (egyszer/logikai nap, idempotencia), belépő (fail-soft), yml (workflow_run a „Napi trendgyűjtés"-re, őr a pip install előtt, commit csak `docs/data/ugyek.json`, ANTHROPIC_API_KEY).
- `tests/test_futtato.py` (kiterjesztés): az `elmozdulas_ir` meghívódik az esti futásban (mock), zéró extra Google-hívás (a plafon-formula VÁLTOZATLAN).
- `e2e/bovites.spec.js`: szokatlan-változások blokk, ügy-lista + idővonal, szűrők (szakpolitika/kategória/téma) `van`/`nincs` adaton, fail-soft, nav 7. fül.
- `e2e/kulcsszo.spec.js` (kiterjesztés) + app.js: a szokásos-sáv kapcsoló BE/KI, a sáv rajzolódik (mock `elmozdulas.json`).
- `e2e/menu.spec.js`: 6→7 fül, az új sorrend, Bővítés-teszt; Infó-teszt doboz/csoport-számok.

## 11. Global Constraints
- NULLA új Python-dependency (stdlib + meglévő anthropic/json_export; az `elmozdulas` numpy-mentes vagy a meglévő regresszió-infrastruktúrán). Frontend: meglévő vendorelt Chart.js, nincs új vendor/külső betöltés.
- Grounding: a Python a VALÓS számok; az LLM csak csoportosít/nevez/sorol be a korpuszból; `grounding_validal` szűr. „A frontend NEM SZÁMOL" — a sáv/metrikák a backend JSON-ból.
- NINCS argless `datetime.now()` a modul-logikában (ablak-vég/keszult = PARAMÉTER; a belépő adja a `seged.most_utc()`-ot).
- `ugy_elemez`: `claude-opus-4-8`, adaptive thinking, STREAMING kötelező, nincs beta-header, bounded-retry + fail-soft. `MAX_TOKENS_UGYEK` a havi (128000) mintájára (nagy 30-napos korpusz → csonkolás-figyelés az első éles futásnál).
- Atomi írás (`json_export._ir_json`); irreplaceable adat READ-ONLY. A `bovites.yml` commit CSAK `docs/data/ugyek.json`; a főfutás `napi.yml` commitolja az `elmozdulas.json`-t a többi `docs/data`-val.
- A plafon/`tervezett_hivasszam` (`futtato.py`) VÁLTOZATLAN — F1/F2 nem hív Google-t (a F1 determinista, a F2 LLM).
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással. SOROS suite (pytest + Playwright) zöld. SDD-folyamat (friss implementer/task + task-review + záró opus review).
- Nav bővítés 6→7 fül MINDEN HTML-oldalon, konzisztens sorrend. ELŐZETES fájlnév-ütközés-ellenőrzés (tanulság a heti körből: a terv által bevezetett ÚJ fájlnevek — `bovites.html/js`, `elmozdulas.py`, `ugyek.py`, `szakpolitika.py`, `bovites_*` — ütközés-vizsgálata a meglévő fákkal a pre-flightban).
