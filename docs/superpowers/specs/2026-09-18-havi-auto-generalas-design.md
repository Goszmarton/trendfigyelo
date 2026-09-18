# Havi NLP-elemzés automatikus generálása (a hó utolsó napján) — design

**Állapot:** jóváhagyott terv (chat), implementáció előtt.
**Dátum:** 2026-09-18.
**Előzmény:** [[havi-nlp-elemzes]] (backend `havi_nlp.py` kész, frontend több-hónap-kész), [[napi-futas-megbizhatosag]] (szerver-trigger + workflow_run lánc + idempotencia-őr), az `elemzes.yml`/`elemzes_orzo.py` minta.

## 1. Cél

A havi NLP-elemzés eddig KÉZZEL futott (`havi_nlp_generalas`). Ezt automatizáljuk: **minden hónap
utolsó napján, az esti napi gyűjtés után** fusson le az adott (épp lezáruló) hónapra, és a Havi fül
hónap-választójában külön kiválasztható hónapként jelenjen meg (2026-09 után 2026-10, stb.).

A `havi_nlp.py` LLM-mag, a grounding, a volumen-dúsítás, a frontend VÁLTOZATLAN. A generálás
backend-belépőt + idempotencia-őrt + egy CI-workflow-t kap, az `elemzes.yml` bevált mintájára.

## 2. Architektúra

- **Trigger:** új `.github/workflows/havi.yml`. `workflow_run` a **„Napi trendgyűjtés"** (este,
  teljes) befejezésére (`types: [completed]`, `conclusion == 'success'`) + `workflow_dispatch` (kézi
  teszt). CSAK az esti gyűjtésre (a reggeli scoped/mid-nap → nem a teljes havi adat). A Hetzner-cron a
  napit indítja (21:00 BP dispatch) → a `workflow_run` automatikusan láncol; **nincs új cron**.
- **Utolsó-nap + idempotencia őr:** új `trendfigyelo/havi_orzo.py` (az `elemzes_orzo.py` mintája,
  `seged.esti_nap` logikai nap). Kimenet: a **generálandó hónap** (`"YYYY-MM"`) ha futni kell,
  különben ÜRES sor (skip). A workflow üres → kihagy.
- **Generálás:** kis `havi.py` belépő (mint `elemzes.py`): `havi_nlp_generalas(docs_data, honap,
  keszult_iso)` (kulccsal, fail-soft: tartós hibán None) → siker esetén `havi_nlp_index_ir(docs_data)`
  (hogy az új hónap megjelenjen a hónap-választóban). Bukáson (None) nem-nulla kilépő (a workflow
  jelzi, de NINCS részleges commit).
- **Commit:** külön commit CSAK a `docs/data/havi_nlp/**`-ra, `git pull --rebase --autostash` +
  push (az `elemzes.yml` mintája). Külön `concurrency: group: havi-futtatas`.
- **Kulcs:** a meglévő `ANTHROPIC_API_KEY` GitHub-secret (a napi elemzés is ezt használja); a
  `havi_nlp_elemez` alapból `_NlpKliens()`-t hoz létre az env-ből.

## 3. `trendfigyelo/havi_orzo.py` (utolsó-nap + idempotencia)

`seged`-alapú (BUDAPEST, `most_utc`, `esti_nap`). Az `elemzes_orzo` `esti` ágának mintája: az
`esti_nap(most)` a hajnali (<6:00 BP) futást az ELŐZŐ estére sorolja → a hó utolsó napja utáni
éjfél-utáni backup NEM csúszik a következő hónapra.

- `havi_logikai_honap(most)`: `seged.esti_nap(most)` → dátum → `"YYYY-MM"`.
- `utolso_nap_e(most)`: `d = esti_nap(most)`; `d.day == calendar.monthrange(d.year, d.month)[1]`.
- `mar_kesz(docs_data, honap, logikai_datum_iso)`: True, ha a `docs/data/havi_nlp/<honap>.json`
  LÉTEZIK **és** a `keszult[:10] == logikai_datum_iso` (azaz MA, az utolsó napon már generálódott).
  - Egy hó-KÖZBEN kézzel generált fájl (`keszult` korábbi dátum) → `mar_kesz=False` az utolsó napon
    → ÚJRAGENERÁL a teljes havi adattal (a 2026-09 pont ilyen: 09-17-i `keszult`).
  - A backup-újraindítás (ugyanaz a logikai nap, `keszult` már a mai) → `mar_kesz=True` → skip.
  - Hiányzó/olvashatatlan/`keszult` nélküli fájl → False (fail-open: inkább fusson).
  - Ha a generálás bukott (fail-soft None → nincs fájlírás/`keszult`-frissítés) → a következő
    backup újrapróbálja (fail-open retry).
- `kell_generalni(docs_data, most)`: ha NEM utolsó nap → None; ha utolsó nap és NOT `mar_kesz` →
  a hónap; különben None.
- **CLI `main`**: `python -m trendfigyelo.havi_orzo <docs_data>` → kiírja a hónapot (`"2026-09"`)
  ha kell, különben üres sor. (A `keszult_iso`-t a generáló belépő adja, az őr csak a dátumot nézi.)

NINCS argless `datetime.now()` a modul-logikában (a `most` paraméter/`seged.most_utc()` a belépőn).

## 4. `havi.py` (generáló belépő)

Az `elemzes.py` mintája (repo-gyökér szkript). Lépések:
1. `honap` = `sys.argv[1]` (a workflow a `havi_orzo` kimenetét adja át).
2. `docs_data = "docs/data"`, `keszult_iso = seged.most_utc().isoformat()`.
3. `eredmeny = havi_nlp.havi_nlp_generalas(docs_data, honap, keszult_iso)` (a kliens env-ből).
4. Ha `eredmeny is None` → `sys.exit(1)` (fail-soft: nincs index-frissítés, nincs commit-anyag).
5. `havi_nlp.havi_nlp_index_ir(docs_data)` (az új hónap a hónap-választóba).

## 5. `.github/workflows/havi.yml`

Az `elemzes.yml` szerkezete, `docs/data/havi_nlp`-re szabva:
- `on: workflow_run: workflows: ["Napi trendgyűjtés"] types: [completed]` + `workflow_dispatch: {}`.
- `permissions: contents: write`; `concurrency: group: havi-futtatas, cancel-in-progress: false`.
- `if: workflow_dispatch || workflow_run.conclusion == 'success'`.
- Lépések: checkout (ref main) → setup-python 3.12 → `pip install -r requirements.txt` →
  **őr**: `HONAP="$(python -m trendfigyelo.havi_orzo docs/data)"` (kézi dispatchnál is fut; ha a
  dispatch felül akarja bírálni: az üres HONAP=skip; a kézi teszthez a `workflow_dispatch` egy
  opcionális `honap` inputtal felülírhat — lásd lent) → **generálás** `if HONAP != ''`:
  `ANTHROPIC_API_KEY` env, `python havi.py "$HONAP" 2>&1 | tee havi.log` → **commit** `if success &&
  HONAP != ''`: `git pull --rebase --autostash`, `git add docs/data/havi_nlp`, ha van staged változás
  → commit `"adat: havi NLP-elemzés (<honap>, <ISO>)"` + push → **artefakt** (mindig: `havi.log` +
  `docs/data/havi_nlp/**`).
- **Kézi teszt-input** (`workflow_dispatch.inputs.honap`, opcionális): ha megadva, felülírja az őr
  kimenetét (a `havi_orzo` kihagyásával), hogy egy adott hónap kézzel újragenerálható legyen. Üres
  input → az őr dönt.

## 6. Infó-doksi frissítés (`docs/adatokrol.html`)

A most megírt „A havi elemzés" csoport **„Mikor készül el?"** szekciója az AUTOMATIKUS folyamatra
pontosítva: a havi elemzés egy teljes naptári hónapot fed le, és **automatikusan, a hó utolsó napján**
(közvetlenül a napi esti adatgyűjtés után) készül el, amikor a teljes havi adat összegyűlt; ha az
AI-hívás nem sikerül, a következő futás újrapróbálja. A napi elemzés naptárában a hó utolsó napján a
„Havi" jelölő visz rá; a Havi fülön a hónap-választóból bármely korábbi hónap előhívható. (A doksi
többi havi szekciója változatlan.)

## 7. Marker: NINCS változás

USER-döntés: a napi naptár „Havi" jelölője MARAD a hó utolsó napján (a szeptemberi naptárban látszik,
a szeptemberi összefoglalóra mutat; felfedezhetőbb, és a Havi fül fail-softol, ha még nincs kész).
Nincs frontend-változás a markeren.

## 8. Tesztelés (TDD)

- **`tests/test_havi_orzo.py`**: `utolso_nap_e` igaz a hó utolsó napján / hamis nem-utolsón (több
  hónap: 28/29/30/31 nap, szökőév febr.); `havi_logikai_honap` az esti_nap szerinti hónap; a hajnali
  (<6:00 BP) él az ELŐZŐ hónap utolsó napjára esik (nem a következő 1-re); `mar_kesz`: hiányzó fájl →
  False, mai `keszult` → True, korábbi (hó-közbeni) `keszult` → False (újragenerál), `keszult` nélkül
  → False; `kell_generalni` végpontok; a CLI kiírja a hónapot / üres sort. `tmp_path` + befőttes
  fájlok, injektált `most` (nincs valós idő).
- **`tests/test_havi_belepo.py`**: a `havi.py` mock `havi_nlp_generalas`-szal — siker → `index_ir`
  hívódik + exit 0; None → exit 1, `index_ir` NEM hívódik. (Belépő-szintű, gyors.)
- **`tests/test_workflow_havi.py`** (vagy a meglévő workflow-teszthez): a `havi.yml` létezik,
  `workflow_run` a „Napi trendgyűjtés"-re, `ANTHROPIC_API_KEY` env a generáló lépésen, a commit CSAK
  `docs/data/havi_nlp`-t stage-el, van `git pull --rebase`. (YAML-parse, nincs valós futás.)

## 9. Hatókörön KÍVÜL / kockázatok

- A `havi_nlp.py` LLM-mag, grounding, volumen-dúsítás, prompt VÁLTOZATLAN.
- A frontend (Havi fül, hónap-naptár, térképek, diagramok) VÁLTOZATLAN — a több-hónap már támogatott.
- KÖLTSÉG: havonta EGY Opus-hívás (max_tokens 64000); az őr + idempotencia megvédi a duplázástól.
  Nagy hónapnál (600–800 szó) a 64000 kevés lehet → külön jövőbeli kör (nem itt). Lásd
  [[havi-nlp-elemzes]] max_tokens-tanulság.
- FAIL-SOFT: API-hibán nincs részleges fájl/commit; a következő backup újrapróbál. Nincs email-spam
  (a workflow bukása artefaktba/UI-ba megy, mint az elemzes.yml).

## 10. Global Constraints

- SOROS suite: pytest + Playwright (a frontend nem változik, de a teljes suite zöld kell legyen).
- NULLA új Python-dependency (`calendar` stdlib). Irreplaceable adat READ-ONLY; a generálás atomi írás.
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással.
- NINCS argless `datetime.now()` a modul-logikában (paraméter/`seged.most_utc()` a belépőn).
- A workflow a meglévő `ANTHROPIC_API_KEY` secretet használja; a commit-lépés CSAK a
  `docs/data/havi_nlp`-t érinti (a napi/YT/trend adatot NEM).
