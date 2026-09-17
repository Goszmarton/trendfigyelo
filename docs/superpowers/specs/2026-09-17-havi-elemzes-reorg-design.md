# Havi elemzés fül újratervezése — FÁZIS A (elrendezés + volumen-számok + barchartok + naptár) — design

**Állapot:** jóváhagyott terv (chat), implementáció előtt.
**Dátum:** 2026-09-17.
**Előzmény:** [[havi-nlp-elemzes]] (a havi NLP-fül és adat).

## 1. Cél

A „Havi elemzés" fül átalakítása a felhasználó 8 pontos kérése szerint. Ez a **FÁZIS A**: elrendezés-
átrendezés + volumen-alapú számok + barchartok + hónap-naptár + napi→havi kereszt-link. A **FÁZIS B**
(HATÓKÖRÖN KÍVÜL, következő kör): a két interaktív Leaflet-térkép (világ choropleth + Magyarország-
település-térkép) + a geo-adat vendorelése.

**USER-döntések:** volumen-alapú szám · top ~15-20 személy · külföldi városok (Fázis B-ben) a
világtérképre pontként · Fázis A most, térkép külön.

## 2. Új oldal-sorrend (fentről le)

1. **Fejléc** (gépi-elemzés jelölés) + **bal oldali hónap-naptár** panel.
2. **Összegzés** (a havi próza) — LEGFELÜL (#4).
3. **Országok** — volumen szerint rendezett lista (interim; Fázis B → világtérkép).
4. **Települések** — volumen szerint rendezett lista (interim; Fázis B → Magyarország-térkép).
5. **Személyek** — **barchart** (top ~15-20, volumen szerint csökkenő; NINCS lemma-alak / „— szavak") (#5).
6. **Klaszterek** — LEGALUL (#8): élen egy **eloszlás-barchart** (klaszterek volumen szerint), alatta a
   kártyák.
- **Törölve** a „Szó → lemma térkép" szekció (#2).

## 3. Adat — volumen-dúsítás (DETERMINISTA, nincs LLM)

A `max_volumen` a korpuszban szavanként megvan (a napok/-ból). Minden **NER-entitáshoz** és
**klaszterhez** hozzáadunk egy `volumen` mezőt: a hozzá kötött korpusz-szavak `max_volumen`-jének
**összege** (a szó→volumen a korpuszból). Ez a barchart-magasság és (Fázis B-ben) a térkép-színezés
forrása. A grounding már a korpuszra szűrte a `szavak`-at, így minden kötött szó a korpuszban van.

- ÚJ `_volumen_terkep(korpusz) -> {kifejezes: max_volumen}`.
- ÚJ `_entitas_volumen(szavak, vol_map) -> int` (a kötött szavak volumenének összege).
- ÚJ `volumen_dusit(eredmeny, korpusz) -> eredmeny'` — minden `ner.*` entitáshoz és `klaszterek`-hez
  `volumen` mezőt fűz (tiszta, nem mutálja a bemenetet). Beépül a `havi_nlp_generalas`-ba (grounding UTÁN).
- ÚJ `havi_nlp_index_ir(docs_data) -> Path` → `data/havi_nlp/index.json`:
  `{"honapok": [...rendezve], "legutolso": "<max>"}` a `havi_nlp/*.json` fájlokból (az `index.json`-t
  kihagyva). A frontend hónap-választója ezt olvassa.
- **Meglévő 2026-09 frissítése (kulcs nélkül):** ÚJ `havi_nlp_volumen_utodusit(docs_data, honap)` — a
  meglévő artefaktot + a korpuszt (napok/) beolvassa, `volumen`-t fűz, visszaírja (atomi). Ezt EGYSZER
  lefuttatjuk a 2026-09-re (nincs LLM/kulcs), + az index.json-t. Külön adat-commit.

Adat-séma (additív): minden `ner.orszagok[i]` / `ner.telepulesek[i]` / `ner.szemelyek[i]` és
`klaszterek[i]` kap egy `"volumen": <int>` mezőt. A régi mezők érintetlenek; a frontend fail-soft
(hiányzó `volumen` → 0).

## 4. Frontend

### 4.1 Elrendezés (`docs/havi.html` + `docs/css/app.css`)
- **Két-oszlopos** fő-tartalom: bal `#havi-honap-panel` (hónap-naptár), jobb `#havi-tartalom`.
  A trendek-fül „Kulcsszó-időszak" bal-panel mintáját követi (reszponzív: keskenyen egymás alá).
- **Chart.js vendor** hozzáadva: `<script src="vendor/chartjs/chart.umd.js"></script>` (a `havi.js` ELŐTT).

### 4.2 Render (`docs/js/havi.js`)
- `rajzol(art)`: az új sorrend (2. szakasz). A `lemma_terkep` **törölve**.
- **Hónap-naptár** (`#havi-honap-panel`): az `index.json` `honapok`-jából gomb-lista (YYYY-MM,
  emberi „2026. szeptember" címkével); a kiválasztott aktív; kattintásra `havi_betolt(honap)`+`rajzol`.
  A kezdő hónap: az URL `?honap=YYYY-MM` (ha érvényes és elérhető), különben `index.legutolso`, különben
  `HAVI_ALAPHONAP`. NINCS `new Date()` (a hónap-címke fix magyar hónapnév-tömbből).
- **Országok/Települések**: a jelenlegi lista, de **volumen szerint csökkenő** rendezve, a `volumen`
  megjelenítve (pl. „Magyarország — 12 400"); a `szavak` marad (grounding).
- **Személyek – barchart**: Chart.js **vízszintes bar**, a top `SZEMELY_TOP = 18` személy volumen
  szerint; NINCS „— szavak". Ha 0 személy → „nincs" üzenet.
- **Klaszterek – eloszlás-barchart**: Chart.js bar a klaszterek `volumen`-jéből (csökkenő), majd a
  meglévő klaszter-kártyák (az üres-szavú kiszűrve, mint eddig).
- Minden barchart-magasság a `volumen`; a „gépi elemzés" jelölés marad.

### 4.3 Napi elemzés → havi (`docs/js/elemzes.js`) (#3)
- A napi elemzés artefaktja tartalmazza a `nap`-ot (YYYY-MM-DD). Ha a `nap` a **hónap utolsó napja**
  (determinista: `napok_a_honapban(ev, ho)` szökőév-szabállyal; NINCS `new Date()`), a fül tetejére egy
  kis jelölő-link kerül: „→ Havi elemzés (YYYY. hónap)", ami a `havi.html?honap=YYYY-MM`-re mutat.
  Ha nem utolsó nap → nincs link (fail-soft).

## 5. Tesztelés (TDD)

- **Backend** (`havi_nlp`): `_entitas_volumen` a kötött szavak volumenét összegzi (nem-korpuszbeli
  szó 0); `volumen_dusit` minden entitáshoz+klaszterhez fűz `volumen`-t; `havi_nlp_index_ir` a
  fájlokból helyes `{honapok, legutolso}`-t ír; `volumen_utodusit` a meglévő artefaktot bővíti.
- **Frontend (e2e, `havi.spec`):** mockolt `havi_nlp/<honap>.json` (+`index.json`) → az összegzés
  ELÖL, a klaszter-kártyák LEGALUL; a lemma-térkép NINCS; a személy-barchart megvan (Chart-példány,
  top N, nincs „— szavak"); a klaszter-eloszlás-barchart megvan; a hónap-naptár az index-ből (gombok);
  `?honap=` URL-param a kezdő hónapot állítja; országok/települések volumen szerint rendezve.
- **Frontend (e2e, `elemzes.spec`):** a hónap utolsó napján a „→ Havi elemzés" link megvan (helyes
  href); nem-utolsó napon NINCS.

## 6. Hatókörön KÍVÜL (FÁZIS B, következő kör)
- A két interaktív Leaflet-térkép (világ choropleth + külföldi városok pontok; Magyarország-térkép a
  magyar településekkel) + a vendored geo-adat (Natural Earth országok, HU-település + világváros
  koordináták). A Fázis A az országok/települések listáit adja, a slotok a Fázis B térképeire cserélődnek.

## 7. Global Constraints (a specből, minden taskra kötelező)
- Tiszta numpy + meglévő SDK; **NULLA új Python-dependency**. Additív, MUTÁCIÓ=1.
- Frontend: NINCS `new Date()` / `Date.now()` (a hónap-utolsó-nap + a magyar hónapnév determinista).
- Backend tesztelt logikában NINCS argless `datetime.now()`; a volumen-dúsítás determinista.
- Irreplaceable adat READ-ONLY (`napok/*.json` stb.).
- SOROS suite: `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`.
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással.
- A napi elemzés / trendek / youtube fül + a havi NLP-generálás LLM-magja VÁLTOZATLAN.
