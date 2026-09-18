# Havi elemzés csiszolás Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Havi elemzés fül 6 finomítása: megyehatárok a HU-térképre, jobb címek + kék-csíkos infók, klaszter-barchart oszlop-kattintás a téma kártyájára, klaszter-kártya szöveg-elöl sorrend, az Infó-oldal predikció-szövegének pontosítása+magyarosítása, és a Napi naptárban a hó utolsó napján „Havi elemzés" jelölő.

**Architecture:** Frontend/docs (kulcs nélkül). A megyehatárhoz egy kis vendorelt megye-GeoJSON. A `volumen`-adat + a barchart-mag változatlan.

**Tech Stack:** vanilla JS + Leaflet + Chart.js (vendored), HTML/CSS; pytest + Playwright.

**Spec:** docs/superpowers/specs/2026-09-18-havi-csiszolas-design.md

## Global Constraints

- Frontend: NINCS `new Date()`/`Date.now()`. Additív, MUTÁCIÓ=1.
- Futásidőben NINCS külső hálózat (megye-GeoJSON vendorelt; build-fetch kimenete a repóban).
- NULLA új Python-dependency. Irreplaceable adat READ-ONLY.
- SOROS suite: `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`.
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással.
- A napi/trend/youtube fül egyéb része + a havi térkép-mag/barchartok/összegzés VÁLTOZATLAN (az érintett részeken kívül).

---

### Task 1: A) Megyehatárok — megye-GeoJSON vendor + HU-térkép alapréteg

**Files:** Create `docs/vendor/geo/hu-megyek.geojson`; Modify `docs/vendor/FORRAS.md`, `docs/js/havi.js`; Test `tests/test_geo_assetek.py`, `e2e/havi.spec.js`.

- [ ] **Step 1: Write the failing test**
`tests/test_geo_assetek.py`-ba:
```python
def test_hu_megyek_geojson():
    gj = json.loads((VENDOR / "geo" / "hu-megyek.geojson").read_text(encoding="utf-8"))
    assert gj.get("type") == "FeatureCollection" and len(gj["features"]) >= 10   # 19 megye + Budapest ~20
```

- [ ] **Step 2: Run test to verify it fails** — `.venv/bin/python -m pytest -p no:xdist -q tests/test_geo_assetek.py::test_hu_megyek_geojson` → FAIL (nincs fájl).

- [ ] **Step 3: Build + implement**
Vendor (hálózat elérhető) — a Natural Earth admin-1-ből Magyarországra szűrve. Próbáld a 10m-et, ha túl nagy a fetch, a 50m is elég:
```bash
curl -sL --max-time 120 "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson" -o /tmp/adm1.geojson
python3 - <<'PY'
import json
gj = json.load(open("/tmp/adm1.geojson"))
def hu(f):
    p = f.get("properties", {})
    return (p.get("iso_a2") == "HU") or (p.get("admin") == "Hungary") or (str(p.get("adm0_a3")) == "HUN")
feats = [f for f in gj["features"] if hu(f)]
# csak a geometria + a megye-nev property (a fájlméret kicsi maradjon)
karcsu = {"type":"FeatureCollection","features":[
    {"type":"Feature","properties":{"name": f["properties"].get("name")}, "geometry": f["geometry"]} for f in feats]}
json.dump(karcsu, open("docs/vendor/geo/hu-megyek.geojson","w"), ensure_ascii=False)
print("megye-feature:", len(feats))
PY
```
(Ha a 10m-ből túl sok/nagy: a `ne_50m_admin_1_states_provinces.geojson`-ra válts — a kontúrhoz elég. A FORRAS.md-t + sha256-ot frissítsd — a repo `vendor_integritas` guardja zöld maradjon.)

`docs/js/havi.js` — a `hu_terkep` alaprétege: a HUN-körvonal helyett a megye-GeoJSON. Bővítsd a `geo_assetek()`-et egy `megyek` fetchszel (fail-soft: hiba → null), és a `hu_terkep` térkép-init blokkjában a mostani `const hun = ... HUN ...` alapréteg HELYETT:
```javascript
    if (g.megyek && (g.megyek.features || []).length) {
      const alap = L.geoJSON(g.megyek, { interactive: false, style: { color: "#999", weight: 1, fillColor: "#f2f2f2", fillOpacity: 0.9 } }).addTo(map);
      try { map.fitBounds(alap.getBounds(), { padding: [12, 12] }); } catch (e) { /* üres bounds */ }
    } else {   // fallback: a világ-GeoJSON HUN-körvonala (a mostani viselkedés)
      const hun = (g.vilag.features || []).find((f) => f.id === "HUN");
      if (hun) { const alap = L.geoJSON(hun, { interactive: false, style: { color: "#888", weight: 1, fillColor: "#f2f2f2", fillOpacity: 0.9 } }).addTo(map);
        try { map.fitBounds(alap.getBounds(), { padding: [12, 12] }); } catch (e) {} }
    }
```
A `geo_assetek()` `Promise.all`-jába vedd fel: `fetch("vendor/geo/hu-megyek.geojson").then(r => r.json())` → `megyek` (a try/catch-en belül, hogy fail-soft maradjon).

- [ ] **Step 4: Run test to verify it passes** — `.venv/bin/python -m pytest -p no:xdist -q tests/test_geo_assetek.py && node --check docs/js/havi.js && npx playwright test --workers=1 e2e/havi.spec.js`. Adj egy e2e-assertet: a HU-térképen a megye-réteg jelen (több `path.leaflet-interactive`, VAGY a fitBounds Magyarországra állt).

- [ ] **Step 5: Commit**
```bash
git add docs/vendor/geo/hu-megyek.geojson docs/vendor/FORRAS.md docs/js/havi.js tests/test_geo_assetek.py e2e/havi.spec.js
git commit -m "feat(havi): megyehatarok a HU-terkepen (vendorelt megye-GeoJSON alapreteg)"
```

---

### Task 2: C/D/E-cím + kék-csíkos infók + F) klaszter-kártya sorrend

**Files:** Modify `docs/js/havi.js`, `docs/css/app.css`; Test `e2e/havi.spec.js`.

- [ ] **Step 1: Write the failing test** — `e2e/havi.spec.js`: az új címek jelen („Országok és települések a havi keresésekben", „Havonta megjelent országok és nem-magyar települések a keresésekben", „Megjelent személynevek a havi keresésekben", „Tematikus besorolás"); NINCS „(térkép)" a térkép-alcímekben; van legalább 3 `#havi-tartalom .havi-info`; a klaszter-kártyán az `ertelmezes` szöveg a tag-chipek ELŐTT (DOM-sorrend: a `.elemzes-szoveg` a `.havi-tag-lista` előtt).

- [ ] **Step 2: Run test to verify it fails** — a régi címek/sorrend miatt FAIL.

- [ ] **Step 3: Write minimal implementation**
`docs/js/havi.js`:
- `klaszter_kartya` (F): a sorrend `h3` → `ertelmezes` (`.elemzes-szoveg`) → `tag_lista(k.szavak)` → domináns témák.
- `vilag_terkep` wrap-cím: „Országok és külföldi városok (térkép)" → **„Havonta megjelent országok és nem-magyar települések a keresésekben"**.
- `hu_terkep` wrap-cím: „Magyarországi települések (térkép)" → **„Havonta megjelent magyar települések a keresésekben"**.
- `rajzol`: a „Felismert entitások (NER)" csoport-cím → **„Országok és települések a havi keresésekben"**; utána egy `.havi-info` (C-infó). A Személyek szekció-cím „Személyek (leggyakoribbak)" → **„Megjelent személynevek a havi keresésekben"** + `.havi-info` (D-infó). A „Témák (klaszterek)" → **„Tematikus besorolás"** + `.havi-info` (E-infó).
- Kis segéd: `function havi_info(szoveg){ return elem("p","havi-info",szoveg); }`. Az infó-szövegek (magyar, tömör, de érdemi) a spec 3. szakasza szerint.
`docs/css/app.css`: `#havi-tartalom .havi-info { border-left: 3px solid #3366cc; padding: .3rem 0 .3rem .6rem; margin: .4rem 0 .8rem; max-width: 44rem; color: #333; font-size: .9rem; }`

- [ ] **Step 4: Run test to verify it passes** — `node --check docs/js/havi.js && npx playwright test --workers=1 e2e/havi.spec.js` (minden havi teszt zöld).

- [ ] **Step 5: Commit**
```bash
git add docs/js/havi.js docs/css/app.css e2e/havi.spec.js
git commit -m "feat(havi): jobb szekcio-cimek + kek-csikos infok + klaszter-kartya szoveg-elol sorrend"
```

---

### Task 3: E) Klaszter-barchart oszlop-kattintás → téma kártyájára ugrás

**Files:** Modify `docs/js/havi.js`, `docs/css/app.css`; Test `e2e/havi.spec.js`.

**Interfaces:** Consumes: a klaszter-barchart `kSorolt` (rendezett cimke-lista) + a klaszter-kártyák. Produces: a barchart-oszlopra kattintva a megfelelő kártyára görget + rövid kiemelés.

- [ ] **Step 1: Write the failing test** — `e2e/havi.spec.js`: a klaszter-kártyák `data-klaszter-cimke`-t kapnak; a klaszter-barchartra (a `#havi-klaszter-chart` canvas-ra) kattintva a program a megfelelő kártyát kiemeli (`.havi-klaszter-kiemelt` osztály megjelenik rajta). (A Chart.js kattintást e2e-ben a `chart_peldanyok`/`window.havi_chartok.klaszter` `options.onClick` közvetlen hívásával VAGY a canvas-koordinátás kattintással teszteld; a robusztus út: a kártya-ugrás logikát egy külön `havi_klaszter_ugras(cimke)` fv-be tenni, és az e2e ezt hívja `page.evaluate`-tel + ellenőrzi a kiemelést.)

- [ ] **Step 2: Run test to verify it fails** — nincs `data-klaszter-cimke` / nincs ugrás-logika.

- [ ] **Step 3: Write minimal implementation**
`docs/js/havi.js`:
- `klaszter_kartya`: `box.setAttribute("data-klaszter-cimke", k.cimke || "");`
- ÚJ `function havi_klaszter_ugras(cimke) { const kartya = document.querySelector('#havi-tartalom .havi-klaszter[data-klaszter-cimke="' + (cimke||"").replace(/"/g,'\\"') + '"]'); if (!kartya) return; kartya.scrollIntoView({ behavior: "smooth", block: "start" }); kartya.classList.add("havi-klaszter-kiemelt"); setTimeout(() => kartya.classList.remove("havi-klaszter-kiemelt"), 1600); }` (NINCS new Date()).
- A klaszter-barchart `havi_barchart(...)` hívásához add át a `kSorolt` cimkéit egy `onClick`-hez. Mivel a `havi_barchart` közös, bővítsd egy opcionális 5. paraméterrel: `onOszlop(index)`. A `havi_barchart` `options`-ébe: `onClick: (e, elemek) => { if (onOszlop && elemek && elemek.length) onOszlop(elemek[0].index); }`, és a datasetnél/`options`-nál `hover`/kurzor pointer. A klaszter-hívásnál: `havi_barchart("klaszter", "havi-klaszter-chart", cimkek, ertekek, (i) => havi_klaszter_ugras(kSorolt[i].cimke))`. (A személy-barchart hívása marad `onOszlop` nélkül.)
`docs/css/app.css`: `#havi-tartalom .havi-klaszter-kiemelt { outline: 2px solid #3366cc; outline-offset: 2px; transition: outline-color .3s; }`

- [ ] **Step 4: Run test to verify it passes** — `node --check docs/js/havi.js && npx playwright test --workers=1 e2e/havi.spec.js`.

- [ ] **Step 5: Commit**
```bash
git add docs/js/havi.js docs/css/app.css e2e/havi.spec.js
git commit -m "feat(havi): klaszter-barchart oszlop-kattintas -> a tema kartyajara ugras"
```

---

### Task 4: B) Infó-oldal predikció-szöveg pontosítás + magyarosítás

**Files:** Modify `docs/adatokrol.html`; Test `tests/test_pages.py`.

- [ ] **Step 1: Write the failing test** — `tests/test_pages.py`:
```python
def test_adatokrol_predikcio_nem_csak_utolso_pont():
    sz = (DOCS / "adatokrol.html").read_text(encoding="utf-8")
    assert "utolsó feléből" in sz                      # a helyes, kóddal egyező megfogalmazás
    assert "utolsó néhány pontjára" not in sz          # a téves/félrevezető mondat MEGSZŰNT
```

- [ ] **Step 2: Run test to verify it fails** — jelenleg „utolsó néhány pontjára" JELEN, „utolsó feléből" NINCS a képlet-bulletben → FAIL.

- [ ] **Step 3: Write minimal implementation** — `docs/adatokrol.html`, az „Előrejelzés – hogyan és meddig?" szakasz:
  - A képlet-bulletben (a `<code>ŷ(h) = L + b·…</code>` sor): „a b meredekség a sima (LOESS) görbe **utolsó néhány pontjára** illesztett egyenesé" → „a b meredekség a sima (LOESS) görbe **utolsó feléből** (egy nagyobb szakaszából, legalább 8 pontból) illesztett egyenesé".
  - A „A módszer." bekezdésben told hozzá egy tisztázó mondatot: az L szint a **simított görbe utolsó értéke** (ami már a közelmúlt pontjait összegzi, tehát NEM egyetlen nyers pontból jósolunk), az irányt pedig a görbe **egy nagyobb szakasza** adja.
  - Csiszold a szakasz magyar fogalmazását (gördülékenyebb, pontosabb; a tartalom lényegében változatlan, csak jobban magyaros). NE találj ki új számot/módszert — a meglévő VALÓS módszert írd pontosabban.

- [ ] **Step 4: Run test to verify it passes** — `.venv/bin/python -m pytest -p no:xdist -q tests/test_pages.py`.

- [ ] **Step 5: Commit**
```bash
git add docs/adatokrol.html tests/test_pages.py
git commit -m "docs(predikcio): info-szoveg pontositas (utolso fele, nem egy pont) + magyarositas"
```

---

### Task 5: G2) Napi naptár „Havi elemzés" jelölő a hó utolsó napján

**Files:** Modify `docs/js/app.js` (naptar_epit), `docs/js/elemzes.js`, `docs/css/app.css`; Test `e2e/elemzes.spec.js`.

**Interfaces:** `naptar_epit` `cellaAllapot` visszatérésébe egy opcionális `haviHonap: "YYYY-MM"`; jelen esetén a cella egy `.nap-havi-jelolo[data-havi]` elemet kap. Az `elemzes.js` a hó utolsó napján adja; a jelölőre kattintva a Havi fülre navigál.

- [ ] **Step 1: Write the failing test** — `e2e/elemzes.spec.js`: a napi elemzés naptárában a hónap utolsó napi cellája (nem szomszéd-hónap) `.nap-havi-jelolo`-t tartalmaz `data-havi="2026-09"`-cel; egy nem-utolsó nap cellája NEM; a jelölőre kattintva a böngésző a `havi.html?honap=2026-09`-re navigál (ellenőrizd `page.waitForURL(/havi\.html\?honap=2026-09/)` VAGY a jelölő `data-havi` + a klikk-navigáció-logika egységteszttel).

- [ ] **Step 2: Run test to verify it fails** — nincs `.nap-havi-jelolo`.

- [ ] **Step 3: Write minimal implementation**
`docs/js/app.js` `naptar_epit`: a cella felépítése UTÁN (a `cella.setAttribute("data-nap", iso)` közelében), ha `st.haviHonap`:
```javascript
    if (st.haviHonap) {
      const jel = document.createElement("span");
      jel.className = "nap-havi-jelolo";
      jel.setAttribute("data-havi", st.haviHonap);
      jel.setAttribute("title", "Havi elemzés");
      jel.textContent = "H";
      cella.appendChild(jel);
    }
```
`docs/js/elemzes.js`:
- A `elemzes_naptar_render` `cellaAllapot` visszatérését bővítsd: a `napok_a_honapban(ev, ho)` (MÁR létezik a fájlban, Fázis A) alapján, ha `!szomszed` ÉS a nap a hó utolsó napja → `st.haviHonap = iso.slice(0, 7)`.
- Az `elemzes_esemeny_kot` klikk-kezelőjének ELEJÉRE (a `closest("button")` ELŐTT): 
```javascript
    const jel = ev.target && ev.target.closest ? ev.target.closest(".nap-havi-jelolo") : null;
    if (jel) { window.location.href = "havi.html?honap=" + jel.getAttribute("data-havi"); return; }
```
`docs/css/app.css`: `.nap-havi-jelolo { display:inline-block; margin-left:.15rem; font-size:.6rem; font-weight:700; color:#fff; background:#3366cc; border-radius:3px; padding:0 .2rem; vertical-align:super; cursor:pointer; }`

- [ ] **Step 4: Run test to verify it passes** — `node --check docs/js/app.js docs/js/elemzes.js && npx playwright test --workers=1 e2e/elemzes.spec.js` (a meglévő napi tesztek + a naptár-tesztek zöldek).

- [ ] **Step 5: Commit**
```bash
git add docs/js/app.js docs/js/elemzes.js docs/css/app.css e2e/elemzes.spec.js
git commit -m "feat(elemzes): naptar 'Havi elemzes' jelolo a ho utolso napjan -> Havi fulre ugras"
```

---

## Önellenőrzés (a terv írója)

- **Spec-lefedettség:** A→T1, B→T4, C/D/E-cím+F→T2, E-kattintás→T3, G2→T5. ✓
- **Placeholder-szken:** a T1 build-parancsok konkrétak; a NER/Person/klaszter info-szövegeket az implementer a spec 3. szakasza alapján írja (magyar, tömör). ✓
- **Típus-konzisztencia:** a `havi_barchart` opcionális 5. `onOszlop` paramétere additív (a személy-hívás nem adja); a `haviHonap` opcionális a cellaAllapot-ban (a trendek-cellaAllapot nem adja → ott nincs jelölő); a `.havi-info`/`.nap-havi-jelolo`/`.havi-klaszter-kiemelt` osztályok egyediek. ✓
