# Havi elemzés fül újratervezése — FÁZIS A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A „Havi elemzés" fül átrendezése: összegzés felülre, klaszterek alulra, lemma-térkép törölve, volumen-alapú számok + személy/klaszter barchartok, bal oldali hónap-naptár, és a napi elemzésből egy „→ Havi elemzés" link a hónap utolsó napján.

**Architecture:** A `havi_nlp` kimenetet determinista volumen-mezőkkel dúsítjuk (a korpusz max_volumen-összege entitásonként/klaszterenként; nincs LLM). A frontend (`havi.js`) újrarendez, a személy/klaszter barchartokhoz Chart.js-t használ (vendored), és egy `index.json`-ból épített hónap-naptárt kap. A napi fül (`elemzes.js`) a hónap utolsó napján kereszt-linket mutat.

**Tech Stack:** Python (numpy) backend, vanilla JS + Chart.js frontend, pytest + Playwright.

**Spec:** docs/superpowers/specs/2026-09-17-havi-elemzes-reorg-design.md

## Global Constraints

- Tiszta numpy + meglévő SDK; **NULLA új Python-dependency**. Additív, MUTÁCIÓ=1.
- Frontend: NINCS `new Date()` / `Date.now()` (a hónap-utolsó-nap + a magyar hónapnév determinista tömbből).
- Backend tesztelt logikában NINCS argless `datetime.now()`; a volumen-dúsítás determinista.
- Irreplaceable adat READ-ONLY (`napok/*.json`).
- SOROS suite: `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`.
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással.
- A napi elemzés / trendek / youtube fül + a havi NLP-generálás LLM-magja VÁLTOZATLAN.
- FÁZIS B (HATÓKÖRÖN KÍVÜL): a két Leaflet-térkép. Az országok/települések itt volumen-listák.

---

### Task 1: Backend — volumen-dúsítás + index.json + utólagos dúsító

**Files:**
- Modify: `trendfigyelo/havi_nlp.py`
- Test: `tests/test_havi_nlp.py`

**Interfaces:**
- Consumes: `havi_korpusz(docs_data, honap)` (létező) → `{szavak:[{kifejezes, max_volumen, ...}]}`; a `havi_nlp` artefakt `{ner:{orszagok,telepulesek,szemelyek}, klaszterek, ...}`.
- Produces: `volumen_dusit(eredmeny, korpusz)` (minden NER-entitás + klaszter kap `volumen` int mezőt); `havi_nlp_index_ir(docs_data)`; `havi_nlp_volumen_utodusit(docs_data, honap)`; a `havi_nlp_generalas` a dúsítást beépíti.

- [ ] **Step 1: Write the failing test**

`tests/test_havi_nlp.py`-ba:

```python
def test_volumen_dusit_entitas_es_klaszter():
    korpusz = {"szavak": [{"kifejezes": "csalás", "max_volumen": 800},
                          {"kifejezes": "átverés", "max_volumen": 200},
                          {"kifejezes": "debrecen", "max_volumen": 500}]}
    er = {"ner": {"orszagok": [], "telepulesek": [{"nev": "Debrecen", "szavak": ["debrecen"]}], "szemelyek": []},
          "klaszterek": [{"cimke": "Bűnügy", "szavak": ["csalás", "átverés"]}], "osszegzes": "…"}
    v = havi_nlp.volumen_dusit(er, korpusz)
    assert v["klaszterek"][0]["volumen"] == 1000                 # 800 + 200
    assert v["ner"]["telepulesek"][0]["volumen"] == 500
    assert er["klaszterek"][0].get("volumen") is None            # NEM mutálja a bemenetet

def test_havi_nlp_index_ir(tmp_path):
    mappa = tmp_path / "havi_nlp"; mappa.mkdir()
    (mappa / "2026-08.json").write_text("{}", encoding="utf-8")
    (mappa / "2026-09.json").write_text("{}", encoding="utf-8")
    p = havi_nlp.havi_nlp_index_ir(str(tmp_path))
    idx = json.loads(p.read_text(encoding="utf-8"))
    assert idx["honapok"] == ["2026-08", "2026-09"] and idx["legutolso"] == "2026-09"

def test_havi_nlp_volumen_utodusit(tmp_path):
    _napfajl(tmp_path, "2026-09-01", [_szo("csalás", 800)])
    (tmp_path / "havi_nlp").mkdir()
    (tmp_path / "havi_nlp" / "2026-09.json").write_text(json.dumps(
        {"ner": {"orszagok": [], "telepulesek": [], "szemelyek": []},
         "klaszterek": [{"cimke": "B", "szavak": ["csalás"]}], "osszegzes": "x"}), encoding="utf-8")
    havi_nlp.havi_nlp_volumen_utodusit(str(tmp_path), "2026-09")
    art = json.loads((tmp_path / "havi_nlp" / "2026-09.json").read_text(encoding="utf-8"))
    assert art["klaszterek"][0]["volumen"] == 800
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_havi_nlp.py::test_volumen_dusit_entitas_es_klaszter tests/test_havi_nlp.py::test_havi_nlp_index_ir tests/test_havi_nlp.py::test_havi_nlp_volumen_utodusit`
Expected: FAIL — a függvények még nem léteznek.

- [ ] **Step 3: Write minimal implementation**

`trendfigyelo/havi_nlp.py`-ba (a `grounding_validal` UTÁN):

```python
def _volumen_terkep(korpusz):
    return {s["kifejezes"]: int(s.get("max_volumen") or 0) for s in (korpusz.get("szavak") or [])}


def _entitas_volumen(szavak, vol_map):
    return sum(int(vol_map.get(sz, 0)) for sz in (szavak or []))


def volumen_dusit(eredmeny, korpusz):
    """Minden NER-entitáshoz és klaszterhez `volumen` = a kötött korpusz-szavak max_volumen-összege.
    Determinista; NEM mutálja a bemenetet (a barchartok magassága + a Fázis-B térkép-színezés forrása)."""
    vol = _volumen_terkep(korpusz)
    ner = {}
    for csoport, entitasok in (eredmeny.get("ner") or {}).items():
        ner[csoport] = [{**e, "volumen": _entitas_volumen(e.get("szavak"), vol)} for e in (entitasok or [])]
    klaszterek = [{**k, "volumen": _entitas_volumen(k.get("szavak"), vol)}
                  for k in (eredmeny.get("klaszterek") or [])]
    return {**eredmeny, "ner": ner, "klaszterek": klaszterek}


def havi_nlp_index_ir(docs_data):
    """A havi_nlp mappa hónapjainak index-e a frontend hónap-választójához (az index.json-t kihagyva)."""
    mappa = Path(docs_data) / "havi_nlp"
    honapok = sorted(p.stem for p in mappa.glob("*.json") if p.stem != "index")
    return json_export._ir_json(mappa / "index.json",
                                {"honapok": honapok, "legutolso": honapok[-1] if honapok else None})


def havi_nlp_volumen_utodusit(docs_data, honap):
    """A meglévő artefaktot a korpuszból volumen-dúsítja és visszaírja (determinista, LLM/kulcs NÉLKÜL)."""
    p = Path(docs_data) / "havi_nlp" / (honap + ".json")
    eredmeny = json.loads(p.read_text(encoding="utf-8"))
    return havi_nlp_ir(docs_data, honap, volumen_dusit(eredmeny, havi_korpusz(docs_data, honap)))
```

Majd a `havi_nlp_generalas`-ban a `eredmeny = grounding_validal(eredmeny, korpusz)` UTÁN told be:

```python
    eredmeny = volumen_dusit(eredmeny, korpusz)
```

(A `json` és `Path` már importált a modulban.)

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_havi_nlp.py`
Expected: PASS (az új 3 teszt + a meglévők).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/havi_nlp.py tests/test_havi_nlp.py
git commit -m "feat(havi): volumen-dusitas (NER+klaszter) + index.json + utolagos dusito"
```

---

### Task 2: Frontend — render-átrendezés (összegzés felül, klaszterek alul, lemma törölve, volumen-listák)

**Files:**
- Modify: `docs/js/havi.js`
- Test: `e2e/havi.spec.js`

**Interfaces:**
- Consumes: `art = {osszegzes, ner:{orszagok,telepulesek,szemelyek} (entitás: {nev, szavak, volumen}), klaszterek:[{cimke, szavak, ertelmezes, uralkodo_temak, volumen}], ...}`.
- Produces: az új render-sorrend; a `lemma_terkep` törölve; országok/települések volumen szerint rendezett listák.

- [ ] **Step 1: Write the failing test**

`e2e/havi.spec.js`-be (ÚJ teszt; a meglévő „…lemma…" tesztet Task 2 Step 3-ban átírjuk):

```javascript
test("Havi reorg: összegzés ELÖL, klaszterek ALUL, nincs lemma-térkép, országok volumen szerint", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-09"], legutolso: "2026-09" } }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: {
    honap: "2026-09", modell: "m", korpusz: { egyedi_szo: 3, napok: 2 },
    lemmak: [{ szo: "csalások", lemma: "csalás" }],
    ner: { orszagok: [{ nev: "Németország", szavak: ["a"], volumen: 100 },
                      { nev: "Magyarország", szavak: ["b"], volumen: 900 }],
           telepulesek: [], szemelyek: [] },
    klaszterek: [{ cimke: "Bűnügy", szavak: ["csalás"], ertelmezes: "leírás", uralkodo_temak: [], volumen: 500 }],
    osszegzes: "A hónap keresései…" } }));
  await page.goto("/havi.html");
  await expect(page.locator("#havi")).toContainText("A hónap keresései");
  // sorrend: az összegzés a klaszter-cím ELŐTT van a DOM-ban
  const cimek = await page.locator("#havi-tartalom .elemzes-csoport-cim").allTextContents();
  expect(cimek.indexOf("Összegzés")).toBeLessThan(cimek.indexOf("Témák (klaszterek)"));
  // nincs lemma-térkép
  await expect(page.locator("#havi-tartalom")).not.toContainText("lemma térkép");
  // országok volumen szerint csökkenő: Magyarország (900) a Németország (100) ELŐTT
  const orsz = await page.locator("#havi-tartalom .havi-ner-csoport", { hasText: "Országok" }).innerText();
  expect(orsz.indexOf("Magyarország")).toBeLessThan(orsz.indexOf("Németország"));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test --workers=1 -g "Havi reorg"`
Expected: FAIL — jelenleg a klaszterek vannak elöl, az összegzés alul, és van lemma-térkép.

- [ ] **Step 3: Write minimal implementation**

`docs/js/havi.js`:
(a) Töröld a `lemma_terkep` függvényt (85–111. sor).
(b) A `ner_csoport` rendezze a listát volumen szerint csökkenő és jelenítse meg a volument: a `const lista = (entitasok || []).filter((e) => e && e.nev);` sort cseréld:

```javascript
  const lista = (entitasok || []).filter((e) => e && e.nev)
    .sort((a, b) => (b.volumen || 0) - (a.volumen || 0));
```
és a li építésénél a név után told a volument (a `szavak` elé):
```javascript
    nev.textContent = e.nev;
    li.appendChild(nev);
    li.appendChild(document.createTextNode("  ·  " + (e.volumen || 0)));
    if (Array.isArray(e.szavak) && e.szavak.length) {
      li.appendChild(document.createTextNode(" — " + e.szavak.join(", ")));
    }
```
(c) A `rajzol(art)` törzsét rendezd át EBBEN a sorrendben (a `gépi elemzés` jelölés után):

```javascript
  // 1) Összegzés — LEGFELÜL
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Összegzés"));
  t.appendChild(elem("p", "elemzes-szoveg", art.osszegzes || ""));

  // 2) NER — Országok / Települések (volumen-listák; Fázis B → térképek), majd Személyek
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Felismert entitások (NER)"));
  const ner = art.ner || {};
  t.appendChild(ner_csoport("Országok", ner.orszagok));
  t.appendChild(ner_csoport("Települések", ner.telepulesek));
  t.appendChild(ner_csoport("Személyek", ner.szemelyek));

  // 3) Klaszterek — LEGALUL
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Témák (klaszterek)"));
  const klaszterek = (art.klaszterek || []).filter((k) => Array.isArray(k.szavak) && k.szavak.length);
  if (!klaszterek.length) {
    t.appendChild(elem("p", "ures", "Nincs megjeleníthető téma ebben a hónapban."));
  } else {
    klaszterek.forEach((k) => t.appendChild(klaszter_kartya(k)));
  }
```
(Töröld a régi klaszter-/NER-/lemma-/összegzés-blokkokat; a fejléc + „gépi elemzés" bekezdés marad.)

(d) Írd át a meglévő „…lemma…" e2e tesztet (a fájl 1. tesztje): a címét és a lemma-assertet vedd ki, és mockold az `index.json`-t is (a `**/data/havi_nlp/**` egyetlen route helyett külön `index.json` + `2026-09.json` route), hogy ne törjön a hónap-választó (Task 4) előtt sem. A klaszter/NER/összegzés assertek maradhatnak.

- [ ] **Step 4: Run test to verify it passes**

Run: `node --check docs/js/havi.js && npx playwright test --workers=1 e2e/havi.spec.js`
Expected: PASS (az új „Havi reorg" + az átírt meglévő teszt).

- [ ] **Step 5: Commit**

```bash
git add docs/js/havi.js e2e/havi.spec.js
git commit -m "feat(havi): render-atrendezes (osszegzes felul, klaszterek alul, lemma torolve, volumen-listak)"
```

---

### Task 3: Frontend — személy- és klaszter-barchart (Chart.js)

**Files:**
- Modify: `docs/havi.html` (Chart.js vendor include), `docs/js/havi.js`
- Test: `e2e/havi.spec.js`

**Interfaces:**
- Consumes: `art.ner.szemelyek[i].volumen`, `art.klaszterek[i].volumen` (Task 1).
- Produces: a Személyek szekció egy vízszintes **barchart** (top `SZEMELY_TOP=18`); a Klaszterek szekció élén egy **eloszlás-barchart**; mindkettő Chart.js-példány a `window`-on elérhető.

- [ ] **Step 1: Write the failing test**

`e2e/havi.spec.js`-be:

```javascript
test("Havi barchartok: személy-barchart (top N, nincs '— szavak') + klaszter-eloszlás", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-09"], legutolso: "2026-09" } }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: {
    honap: "2026-09", modell: "m", korpusz: { egyedi_szo: 3, napok: 2 }, lemmak: [],
    ner: { orszagok: [], telepulesek: [],
           szemelyek: [{ nev: "Orbán Viktor", szavak: ["orbán viktor kötcse"], volumen: 900 },
                       { nev: "Magyar Péter", szavak: ["magyar péter"], volumen: 400 }] },
    klaszterek: [{ cimke: "Sport", szavak: ["foci"], ertelmezes: "s", uralkodo_temak: [], volumen: 700 },
                 { cimke: "Bűnügy", szavak: ["csalás"], ertelmezes: "b", uralkodo_temak: [], volumen: 300 }],
    osszegzes: "össz" } }));
  await page.goto("/havi.html");
  await expect(page.locator("#havi-szemely-chart")).toHaveCount(1);        // személy-barchart canvas
  await expect(page.locator("#havi-klaszter-chart")).toHaveCount(1);       // klaszter-eloszlás canvas
  // a személy neve megvan, de a kötött szó („— szavak") NEM jelenik meg a szekcióban
  const szem = await page.locator(".havi-szemely-szekcio").innerText();
  expect(szem).toContain("Orbán Viktor");
  expect(szem).not.toContain("orbán viktor kötcse");
  // a Chart-példányok léteznek és 2 személy / 2 klaszter adattal
  const adat = await page.evaluate(() => ({
    szem: (window.havi_chartok && window.havi_chartok.szemely) ? window.havi_chartok.szemely.data.labels.length : 0,
    kl: (window.havi_chartok && window.havi_chartok.klaszter) ? window.havi_chartok.klaszter.data.labels.length : 0 }));
  expect(adat.szem).toBe(2);
  expect(adat.kl).toBe(2);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test --workers=1 -g "Havi barchartok"`
Expected: FAIL — nincs `#havi-szemely-chart` / `#havi-klaszter-chart` canvas, nincs `window.havi_chartok`.

- [ ] **Step 3: Write minimal implementation**

`docs/havi.html`: a `js/havi.js` ELÉ told be:
```html
  <script src="vendor/chartjs/chart.umd.js"></script>
```

`docs/js/havi.js`:
(a) A fájl tetejére: `const SZEMELY_TOP = 18;` és `const havi_chartok = {};` és tedd elérhetővé: `window.havi_chartok = havi_chartok;`

(b) ÚJ barchart-helper (a `Chart` globális a vendored lib-ből):
```javascript
// vízszintes barchart egy szekcióba (cimkek + ertekek), a Chart-példányt kulcson eltárolva
function havi_barchart(kulcs, canvasId, cimkek, ertekek) {
  const doboz = document.createElement("div");
  doboz.className = "havi-chart-doboz";
  const canvas = document.createElement("canvas");
  canvas.id = canvasId;
  doboz.appendChild(canvas);
  if (typeof Chart !== "undefined" && cimkek.length) {
    havi_chartok[kulcs] = new Chart(canvas, {
      type: "bar",
      data: { labels: cimkek, datasets: [{ data: ertekek, backgroundColor: "#3366cc" }] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, title: { display: true, text: "volumen" } } } },
    });
  }
  return doboz;
}
```

(c) A `rajzol`-ban a **Személyek**-nél a `ner_csoport("Személyek", ...)` HELYETT egy barchart-szekció:
```javascript
  const szemSzek = document.createElement("section");
  szemSzek.className = "elemzes-szekcio havi-szemely-szekcio";
  szemSzek.appendChild(elem("h3", null, "Személyek (leggyakoribbak)"));
  const szemelyek = (ner.szemelyek || []).filter((e) => e && e.nev)
    .sort((a, b) => (b.volumen || 0) - (a.volumen || 0)).slice(0, SZEMELY_TOP);
  if (!szemelyek.length) {
    szemSzek.appendChild(elem("p", "ures", "Nincs felismert személy ebben a hónapban."));
  } else {
    szemSzek.appendChild(havi_barchart("szemely", "havi-szemely-chart",
      szemelyek.map((e) => e.nev), szemelyek.map((e) => e.volumen || 0)));
  }
  t.appendChild(szemSzek);
```
(A Személyek NER-lista helyére kerül; az Országok/Települések listák maradnak Task 2-ből.)

(d) A **Klaszterek** szekció ÉLÉRE (a `Témák (klaszterek)` cím után, a kártyák ELÉ) egy eloszlás-barchart:
```javascript
  if (klaszterek.length) {
    const kSorolt = klaszterek.slice().sort((a, b) => (b.volumen || 0) - (a.volumen || 0));
    t.appendChild(havi_barchart("klaszter", "havi-klaszter-chart",
      kSorolt.map((k) => k.cimke || "Névtelen"), kSorolt.map((k) => k.volumen || 0)));
  }
```

`docs/css/app.css`: a chart-doboz fix magasság (a Chart.js responsive-hoz):
```css
#havi-tartalom .havi-chart-doboz { position: relative; height: 22rem; margin: .5rem 0 1rem; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --check docs/js/havi.js && npx playwright test --workers=1 e2e/havi.spec.js`
Expected: PASS (az új „Havi barchartok" + a Task 2 tesztek zöldek).

- [ ] **Step 5: Commit**

```bash
git add docs/havi.html docs/js/havi.js docs/css/app.css e2e/havi.spec.js
git commit -m "feat(havi): szemely-barchart (top N) + klaszter-eloszlas-barchart (Chart.js)"
```

---

### Task 4: Frontend — bal oldali hónap-naptár + honap URL-param

**Files:**
- Modify: `docs/havi.html` (két-oszlopos elrendezés + bal panel), `docs/js/havi.js`, `docs/css/app.css`
- Test: `e2e/havi.spec.js`

**Interfaces:**
- Consumes: `data/havi_nlp/index.json` → `{honapok:[...], legutolso}`.
- Produces: bal `#havi-honap-panel` gomb-lista; a kezdő hónap az URL `?honap=`-ból (ha érvényes+elérhető), különben `legutolso`; kattintásra újratölt.

- [ ] **Step 1: Write the failing test**

`e2e/havi.spec.js`-be:

```javascript
test("Havi hónap-naptár: index.json-ból gombok + ?honap= URL-param a kezdő hónap", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-08", "2026-09"], legutolso: "2026-09" } }));
  const art = (h) => ({ honap: h, modell: "m", korpusz: { egyedi_szo: 1, napok: 1 }, lemmak: [],
    ner: { orszagok: [], telepulesek: [], szemelyek: [] }, klaszterek: [], osszegzes: "össz-" + h });
  await page.route("**/data/havi_nlp/2026-08.json", r => r.fulfill({ json: art("2026-08") }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: art("2026-09") }));
  // ?honap=2026-08 → a 2026-08 töltődik be
  await page.goto("/havi.html?honap=2026-08");
  await expect(page.locator("#havi-tartalom")).toContainText("össz-2026-08");
  await expect(page.locator("#havi-honap-panel .havi-honap-gomb")).toHaveCount(2);   // két hónap-gomb
  // kattintás a 2026-09-re → átvált
  await page.locator('#havi-honap-panel .havi-honap-gomb[data-honap="2026-09"]').click();
  await expect(page.locator("#havi-tartalom")).toContainText("össz-2026-09");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test --workers=1 -g "Havi hónap-naptár"`
Expected: FAIL — nincs `#havi-honap-panel`, a `?honap=` nincs kezelve.

- [ ] **Step 3: Write minimal implementation**

`docs/havi.html`: a `<main id="havi">` tartalmát tedd két-oszlopossá:
```html
  <main id="havi">
    <aside id="havi-honap-panel" aria-label="Hónap választó"></aside>
    <section id="havi-tartalom" aria-live="polite"></section>
  </main>
```

`docs/css/app.css`:
```css
#havi { display: flex; gap: 1.5rem; align-items: flex-start; }
#havi-honap-panel { flex: 0 0 12rem; }
#havi-tartalom { flex: 1 1 auto; min-width: 0; }
#havi-honap-panel .havi-honap-gomb { display: block; width: 100%; text-align: left; margin: .25rem 0; padding: .4rem .6rem; cursor: pointer; }
#havi-honap-panel .havi-honap-gomb[aria-pressed="true"] { font-weight: 700; }
@media (max-width: 640px) { #havi { flex-direction: column; } #havi-honap-panel { flex-basis: auto; } }
```

`docs/js/havi.js`:
(a) Magyar hónapnevek (NINCS new Date()):
```javascript
const HONAP_NEV = ["január", "február", "március", "április", "május", "június",
                   "július", "augusztus", "szeptember", "október", "november", "december"];
function honap_cimke(h) {                       // "2026-09" → "2026. szeptember"
  const [ev, ho] = (h || "").split("-");
  const i = parseInt(ho, 10) - 1;
  return (i >= 0 && i < 12) ? `${ev}. ${HONAP_NEV[i]}` : h;
}
function url_honap() {                           // ?honap=YYYY-MM (NINCS new Date())
  const m = (location.search || "").match(/[?&]honap=(\d{4}-\d{2})/);
  return m ? m[1] : null;
}
```
(b) `havi_indit` átírás: töltsd be az indexet, építsd a panelt, válaszd a kezdő hónapot:
```javascript
async function havi_indit() {
  let idx = { honapok: [], legutolso: null };
  try {
    const r = await fetch("data/havi_nlp/index.json");
    if (r.ok) idx = await r.json();
  } catch (e) { /* nincs index — HAVI_ALAPHONAP-ra esünk */ }
  const honapok = (idx.honapok && idx.honapok.length) ? idx.honapok.slice() : [HAVI_ALAPHONAP];
  const kert = url_honap();
  const kezdo = (kert && honapok.indexOf(kert) >= 0) ? kert
    : (idx.legutolso && honapok.indexOf(idx.legutolso) >= 0 ? idx.legutolso : honapok[honapok.length - 1]);
  honap_panel_epit(honapok, kezdo);
  await honap_valt(kezdo);
}
function honap_panel_epit(honapok, aktiv) {
  const panel = document.getElementById("havi-honap-panel");
  panel.textContent = "";
  panel.appendChild(elem("h2", "halvany", "Hónap"));
  honapok.slice().sort().reverse().forEach((h) => {
    const g = document.createElement("button");
    g.type = "button"; g.className = "havi-honap-gomb";
    g.setAttribute("data-honap", h);
    g.setAttribute("aria-pressed", h === aktiv ? "true" : "false");
    g.textContent = honap_cimke(h);
    g.addEventListener("click", () => {
      panel.querySelectorAll(".havi-honap-gomb").forEach((b) =>
        b.setAttribute("aria-pressed", b.getAttribute("data-honap") === h ? "true" : "false"));
      honap_valt(h);
    });
    panel.appendChild(g);
  });
}
async function honap_valt(honap) {
  try { rajzol(await havi_betolt(honap)); }
  catch (e) {
    document.getElementById("havi-fejlec").textContent = "Havi elemzés – nem érhető el";
    document.getElementById("havi-tartalom").textContent =
      "A havi elemzés jelenleg nem érhető el (még nem készült el ehhez a hónaphoz).";
  }
}
```
(Töröld a régi `havi_honap_dontes`-t és a régi `havi_indit` törzsét; a `DOMContentLoaded → havi_indit` marad.)

- [ ] **Step 4: Run test to verify it passes**

Run: `node --check docs/js/havi.js && npx playwright test --workers=1 e2e/havi.spec.js`
Expected: PASS (az új „Havi hónap-naptár" + minden korábbi havi teszt).

- [ ] **Step 5: Commit**

```bash
git add docs/havi.html docs/js/havi.js docs/css/app.css e2e/havi.spec.js
git commit -m "feat(havi): bal oldali honap-naptar (index.json) + ?honap= URL-param"
```

---

### Task 5: Napi elemzés → havi kereszt-link (a hónap utolsó napján)

**Files:**
- Modify: `docs/js/elemzes.js`
- Test: `e2e/elemzes.spec.js`

**Interfaces:**
- Consumes: `art.nap` (YYYY-MM-DD) a napi elemzés artefaktban.
- Produces: ha `art.nap` a hónap utolsó napja → a fül tetején „→ Havi elemzés (YYYY. hónap)" link a `havi.html?honap=YYYY-MM`-re; különben nincs.

- [ ] **Step 1: Write the failing test**

`e2e/elemzes.spec.js`-be (a meglévő FIXTURE-minta szerint; a `nap`-ot állítva):

```javascript
test("Napi → havi link: a hónap utolsó napján megjelenik (nem-utolsón nem)", async ({ page }) => {
  const alap = (nap) => ({ frissitve: "x", modell: "m", nap, mode: "este",
    valtozas: { diff: { van_elozo: true, mozgok: [] }, szoveg: "V." },
    kulcsszavak: { szamok: [], napi: { szoveg: "N." } },
    felkapott: { top: [], reggel_top: [], este_top: [], reggel_este_diff: {}, het_valos: [],
      reggel: { szoveg: "R." }, este: { szoveg: "E." }, teljes_nap: { szoveg: "Í." }, het: { szoveg: "H." } } });
  await page.route("**/data/elemzesek/index.json", r => r.fulfill({ status: 404, body: "" }));
  // 2026-09-30 = szeptember utolsó napja → van link
  await page.route("**/data/elemzes.json", r => r.fulfill({ json: alap("2026-09-30") }));
  await page.goto("/elemzes.html");
  const link = page.locator('a.havi-atugras[href="havi.html?honap=2026-09"]');
  await expect(link).toHaveCount(1);
  await expect(link).toContainText("Havi elemzés");
});

test("Napi → havi link: nem-utolsó napon NINCS", async ({ page }) => {
  const alap = { frissitve: "x", modell: "m", nap: "2026-09-15", mode: "este",
    valtozas: { diff: { van_elozo: true, mozgok: [] }, szoveg: "V." },
    kulcsszavak: { szamok: [], napi: { szoveg: "N." } },
    felkapott: { top: [], reggel_top: [], este_top: [], reggel_este_diff: {}, het_valos: [],
      reggel: { szoveg: "R." }, este: { szoveg: "E." }, teljes_nap: { szoveg: "Í." }, het: { szoveg: "H." } } };
  await page.route("**/data/elemzesek/index.json", r => r.fulfill({ status: 404, body: "" }));
  await page.route("**/data/elemzes.json", r => r.fulfill({ json: alap }));
  await page.goto("/elemzes.html");
  await expect(page.locator("a.havi-atugras")).toHaveCount(0);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test --workers=1 -g "Napi → havi link"`
Expected: FAIL — nincs `a.havi-atugras`.

- [ ] **Step 3: Write minimal implementation**

`docs/js/elemzes.js`: adj hozzá egy determinista utolsó-nap segédfüggvényt (NINCS new Date()) és a render elejére a linket. A napi render-belépőben (ahol `art`-ból épül a fül, a `#elemzes`/`#elemzes-tartalom` tetejére):

```javascript
function napok_a_honapban(ev, ho) {              // ho: 1..12 ; NINCS new Date()
  const szoko = (ev % 4 === 0 && ev % 100 !== 0) || ev % 400 === 0;
  return [31, szoko ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][ho - 1];
}
function havi_atugras_link(nap) {                // "YYYY-MM-DD" → <a> ha a hó utolsó napja, különben null
  const m = (nap || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;
  const ev = parseInt(m[1], 10), ho = parseInt(m[2], 10), d = parseInt(m[3], 10);
  if (ho < 1 || ho > 12 || d !== napok_a_honapban(ev, ho)) return null;
  const a = document.createElement("a");
  a.className = "havi-atugras";
  a.href = `havi.html?honap=${m[1]}-${m[2]}`;
  a.textContent = `→ Havi elemzés (${m[1]}. ${HONAP_NEV_E[ho - 1]})`;
  return a;
}
```
ahol a magyar hónapnév-tömb (ha még nincs a fájlban): `const HONAP_NEV_E = ["január", ..., "december"];`

A napi render-függvény elején (miután a konténer törölve, az első szekció ELÉ):
```javascript
  const atug = havi_atugras_link(art.nap);
  if (atug) t.appendChild(atug);   // t = a napi tartalom-konténer
```
(A pontos konténer-változót az implementer a fájlból olvassa ki — ugyanaz, amibe a napi szekciók kerülnek.)

- [ ] **Step 4: Run test to verify it passes**

Run: `node --check docs/js/elemzes.js && npx playwright test --workers=1 e2e/elemzes.spec.js`
Expected: PASS (a 2 új teszt + a meglévő elemzes-tesztek).

- [ ] **Step 5: Commit**

```bash
git add docs/js/elemzes.js e2e/elemzes.spec.js
git commit -m "feat(elemzes): napi->havi atugras-link a honap utolso napjan"
```

---

## Önellenőrzés (a terv írója)

- **Spec-lefedettség:** #1 naptár → T4; #2 lemma törölve → T2; #3 napi→havi → T5; #4 összegzés felül → T2; #5 személy-barchart → T3; #8 klaszterek alul + eloszlás-barchart → T2 (sorrend) + T3 (barchart); #6/#7 térképek → Fázis B (T2 interim listák). Volumen-adat → T1. ✓
- **Placeholder-szken:** nincs TBD; konstansok konkrétak (SZEMELY_TOP=18). A T5 „konténer-változó" pontját az implementer a fájlból olvassa (a plan jelzi). ✓
- **Típus-konzisztencia:** `volumen` int a T1 kimenetén, a T2/T3 `e.volumen || 0`-val olvassa; a `?honap=` a T4-ben áll be és a T5 link ugyanabban a formátumban (`havi.html?honap=YYYY-MM`) mutat rá. ✓
