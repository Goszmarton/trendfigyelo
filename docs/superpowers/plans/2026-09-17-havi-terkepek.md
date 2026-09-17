# Havi elemzés FÁZIS B — interaktív térképek Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A „Havi elemzés" fülön az Országok/Települések listát két interaktív Leaflet-térképre cserélni: világtérkép (országok volumen-choropleth + külföldi városok pontok) és Magyarország-térkép (magyar települések pontok), hover-tooltippel és kattintás=kiemelés+`szavak`-kal.

**Architecture:** Vendorelt Leaflet + geo-assetek (build-időben fetch+konvertál, futásidőben nincs külső hívás). A frontend a Fázis A `volumen`-adatot + a vendored név→koordináta/ISO lookupokat használja. Fail-soft: Leaflet nélkül a volumen-lista marad; a nem-illeszthető nevek egy fallback-listában (semmi nem vész el).

**Tech Stack:** Leaflet 1.9.4 (vendored), GeoJSON, vanilla JS; pytest + Playwright.

**Spec:** docs/superpowers/specs/2026-09-17-havi-terkepek-design.md

## Global Constraints

- **Futásidőben NINCS külső hálózati hívás** (geo-asset vendorelt; nincs csempe-szerver). A build-idejű fetch kimenete a repóban.
- NULLA új Python-dependency. Frontend: NINCS `new Date()`/`Date.now()`. Additív, MUTÁCIÓ=1.
- A vendored assetek `docs/vendor/`-ba; `vendor/FORRAS.md` forrás-dokumentálás.
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással.
- A napi/trend/youtube fül + a havi barchartok/összegzés/klaszterek + a `havi_nlp` backend VÁLTOZATLAN.
- A név-illesztés kisbetűs, ékezet-érzékeny kulccsal (a korpusz-szavakhoz igazítva).

---

### Task 1: Vendor — Leaflet + geo-assetek (build) + jelenlét-teszt

**Files:**
- Create: `docs/vendor/leaflet/leaflet.js`, `docs/vendor/leaflet/leaflet.css`, `docs/vendor/geo/vilag-orszagok.geojson`, `docs/vendor/geo/orszag-nev-iso.json`, `docs/vendor/geo/hu-telepules-koord.json`, `docs/vendor/geo/varos-koord.json`
- Modify: `docs/vendor/FORRAS.md` (források dokumentálása)
- Test: `tests/test_geo_assetek.py`

**Interfaces:**
- Produces (futásidőben olvasott alak): `vilag-orszagok.geojson` (FeatureCollection, feature `id`=ISO3, `properties.name`=angol név); `orszag-nev-iso.json` = `{"<magyar országnév kisbetűs>":"ISO3"}`; `hu-telepules-koord.json` = `{"<magyar településnév kisbetűs>":[lat,lon]}`; `varos-koord.json` = `{"<magyar városnév kisbetűs>":[lat,lon]}`.

- [ ] **Step 1: Write the failing test**

`tests/test_geo_assetek.py`:

```python
import json
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / "docs" / "vendor"

def test_leaflet_vendorelt():
    assert (VENDOR / "leaflet" / "leaflet.js").stat().st_size > 100000     # ~140KB
    assert (VENDOR / "leaflet" / "leaflet.css").stat().st_size > 10000

def test_vilag_orszagok_geojson():
    gj = json.loads((VENDOR / "geo" / "vilag-orszagok.geojson").read_text(encoding="utf-8"))
    assert gj.get("type") == "FeatureCollection"
    feats = gj["features"]
    assert len(feats) > 150                                                # ~177 ország
    assert all("id" in f for f in feats[:5])                               # ISO-kód a feature-ön

def test_orszag_nev_iso_magyar():
    m = json.loads((VENDOR / "geo" / "orszag-nev-iso.json").read_text(encoding="utf-8"))
    assert m.get("magyarország") == "HUN" and m.get("németország") == "DEU"
    assert len(m) > 150

def test_hu_telepules_koord():
    t = json.loads((VENDOR / "geo" / "hu-telepules-koord.json").read_text(encoding="utf-8"))
    assert len(t) > 1000                                                   # sok magyar település
    assert "debrecen" in t and abs(t["debrecen"][0] - 47.53) < 0.3         # ~Debrecen szélesség

def test_varos_koord_magyar_exonimak():
    v = json.loads((VENDOR / "geo" / "varos-koord.json").read_text(encoding="utf-8"))
    for varos in ("moszkva", "kijev", "brüsszel", "porto"):
        assert varos in v and len(v[varos]) == 2                          # a felmerülő városok
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_geo_assetek.py`
Expected: FAIL — a vendored fájlok még nem léteznek.

- [ ] **Step 3: Build + vendor the assets**

A subagentnek van hálózata. Futtasd (a repó gyökeréből), majd ellenőrizd a kimeneteket:

```bash
mkdir -p docs/vendor/leaflet docs/vendor/geo
# 1) Leaflet 1.9.4 (js+css) — circleMarker-t használunk, marker-kép NEM kell
curl -sL https://unpkg.com/leaflet@1.9.4/dist/leaflet.js  -o docs/vendor/leaflet/leaflet.js
curl -sL https://unpkg.com/leaflet@1.9.4/dist/leaflet.css -o docs/vendor/leaflet/leaflet.css
# 2) Világ országhatár GeoJSON (feature id=ISO3, properties.name=angol) — kész GeoJSON, nincs konverzió
curl -sL https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json \
     -o docs/vendor/geo/vilag-orszagok.geojson
# 3) Magyar országnév → ISO3 (i18n-iso-countries HU-lokál)
node -e '
  const c = require("i18n-iso-countries");
  c.registerLocale(require("i18n-iso-countries/langs/hu.json"));
  const hu = c.getNames("hu"); const out = {};
  for (const [a2, name] of Object.entries(hu)) { const a3=c.alpha2ToAlpha3(a2); if(a3) out[name.toLowerCase()] = a3; }
  require("fs").writeFileSync("docs/vendor/geo/orszag-nev-iso.json", JSON.stringify(out));
' || npm i i18n-iso-countries && node -e '...(fenti...)'   # ha a modul nincs: npx/telepítés a build-környezetben
# 4) GeoNames HU → hu-telepules-koord.json (feature class P = populated place; név col2 kisbetűs → [lat,lon])
curl -sL https://download.geonames.org/export/dump/HU.zip -o /tmp/HU.zip
python3 - <<'PY'
import zipfile, io, json
z = zipfile.ZipFile("/tmp/HU.zip"); raw = z.read("HU.txt").decode("utf-8")
out = {}
for sor in raw.splitlines():
    m = sor.split("\t")
    if len(m) < 15: continue
    nev, lat, lon, fclass, pop = m[1], m[4], m[5], m[6], m[14]
    if fclass != "P": continue
    kulcs = nev.strip().lower()
    try: p = int(pop or 0)
    except ValueError: p = 0
    # a legnépesebb azonos-nevűt tartjuk meg
    if kulcs not in out or p > out[kulcs][2]:
        out[kulcs] = [round(float(lat),4), round(float(lon),4), p]
telepulesek = {k: [v[0], v[1]] for k, v in out.items()}
json.dump(telepulesek, open("docs/vendor/geo/hu-telepules-koord.json","w"), ensure_ascii=False)
print("HU települések:", len(telepulesek))
PY
# 5) Külföldi városok — magyar exonimákkal (curált; a korpusz magyar neveket ad). Seed + bővíthető.
python3 - <<'PY'
import json
varosok = {
  "moszkva":[55.7558,37.6173], "kijev":[50.4501,30.5234], "brüsszel":[50.8503,4.3517],
  "porto":[41.1579,-8.6291], "bécs":[48.2082,16.3738], "berlin":[52.52,13.405],
  "párizs":[48.8566,2.3522], "london":[51.5074,-0.1278], "róma":[41.9028,12.4964],
  "madrid":[40.4168,-3.7038], "prága":[50.0755,14.4378], "varsó":[52.2297,21.0122],
  "pozsony":[48.1486,17.1077], "bukarest":[44.4268,26.1025], "belgrád":[44.7866,20.4489],
  "zágráb":[45.815,15.9819], "ljubljana":[46.0569,14.5058], "szófia":[42.6977,23.3219],
  "isztambul":[41.0082,28.9784], "athén":[37.9838,23.7275], "amszterdam":[52.3676,4.9041],
  "koppenhága":[55.6761,12.5683], "stockholm":[59.3293,18.0686], "oslo":[59.9139,10.7522],
  "helsinki":[60.1699,24.9384], "lisszabon":[38.7223,-9.1393], "washington":[38.9072,-77.0369],
  "new york":[40.7128,-74.006], "peking":[39.9042,116.4074], "tokió":[35.6762,139.6503],
  "moszkva ":[55.7558,37.6173],
}
json.dump(varosok, open("docs/vendor/geo/varos-koord.json","w"), ensure_ascii=False)
print("városok:", len(varosok))
PY
```

Ha a `johan/world.geo.json` feature-jein a `properties.name` van, de nincs top-level `id`, akkor a Step-1 teszt `"id" in f` bukhat → HASZNÁLD azt a forrást/alakot, ahol a feature-nek van ISO3 `id`-ja (a johan-forrás feature-jein `id`=ISO3 van; ha mégsem, válts a `properties.iso_a3`/`ISO_A3`-ra ÉS igazítsd a Step-1 tesztet + a Task 2 illesztést egységesen). Dokumentáld a tényleges kulcsot a FORRAS.md-ben.

Egészítsd ki a `docs/vendor/FORRAS.md`-t a 4 geo-forrással (URL + licenc: Leaflet BSD; world.geo.json közkincs; i18n-iso-countries MIT; GeoNames CC-BY).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_geo_assetek.py`
Expected: PASS (mind az 5 asset-teszt).

- [ ] **Step 5: Commit**

```bash
git add docs/vendor/leaflet/leaflet.js docs/vendor/leaflet/leaflet.css docs/vendor/geo/vilag-orszagok.geojson docs/vendor/geo/orszag-nev-iso.json docs/vendor/geo/hu-telepules-koord.json docs/vendor/geo/varos-koord.json docs/vendor/FORRAS.md tests/test_geo_assetek.py
git commit -m "feat(havi): Leaflet + geo-assetek vendorelese (vilag GeoJSON, HU/varos koord, orszag-ISO)"
```

---

### Task 2: Világtérkép — ország-choropleth + külföldi városok + hover + kattintás=szavak

**Files:**
- Modify: `docs/havi.html` (Leaflet css/js include), `docs/js/havi.js`, `docs/css/app.css`
- Test: `e2e/havi.spec.js`

**Interfaces:**
- Consumes: `art.ner.orszagok[i]={nev,szavak,volumen}`, `art.ner.telepulesek[i]={...}`; a vendored assetek (Task 1) `fetch`-elve; `L` (Leaflet globális).
- Produces: `#havi-vilag-terkep` Leaflet-térkép (`.leaflet-container`), ország-choropleth + külföldi-város kör-jelölők, hover-tooltip, kattintás→`szavak` doboz; fail-soft a volumen-listára.

- [ ] **Step 1: Write the failing test** — `e2e/havi.spec.js`-be egy teszt, amely mockolja a `havi_nlp/2026-09.json`-t (orszagok: Magyarország/Németország volumennel; telepulesek: egy külföldi „Moszkva"), és a valós vendored assetek mellett `page.goto("/havi.html")` után: `#havi-vilag-terkep .leaflet-container` létezik (`toHaveCount(1)`); van legalább egy `path.leaflet-interactive` (choropleth ország) ÉS egy `path.leaflet-interactive`/kör-jelölő; kattintásra a `szavak` megjelenik egy `.havi-terkep-szavak` dobozban. (A pontos szelektorokat az implementer a Leaflet-DOM-ból igazítja.)

- [ ] **Step 2: Run test to verify it fails** — nincs `#havi-vilag-terkep`.

- [ ] **Step 3: Write minimal implementation**

`docs/havi.html`: `<link rel="stylesheet" href="vendor/leaflet/leaflet.css">` a fejbe; `<script src="vendor/leaflet/leaflet.js"></script>` a `js/havi.js` ELÉ.

`docs/js/havi.js`: ÚJ async geo-loader (egyszer tölti be és cache-eli a 4 assetet):
```javascript
let _geo = null;
async function geo_assetek() {
  if (_geo) return _geo;
  const [vilag, iso, huk, varos] = await Promise.all([
    fetch("vendor/geo/vilag-orszagok.geojson").then(r => r.json()),
    fetch("vendor/geo/orszag-nev-iso.json").then(r => r.json()),
    fetch("vendor/geo/hu-telepules-koord.json").then(r => r.json()),
    fetch("vendor/geo/varos-koord.json").then(r => r.json()),
  ]);
  _geo = { vilag, iso, huk, varos };
  return _geo;
}
function kulcs(nev) { return (nev || "").trim().toLowerCase(); }
function szin_skala(v, max) {   // világos→sötét kék a volumen arányában
  const t = max > 0 ? Math.min(1, v / max) : 0;
  const l = Math.round(85 - 55 * t);       // 85%→30% világosság
  return `hsl(212, 70%, ${l}%)`;
}
```
A világtérkép-építő (a rajzol-ban az „Országok" szekció helyére hívva, `await`-tel — a rajzol legyen async, VAGY a térkép-építés külön async fv. ami a konténerbe tölt):
```javascript
async function vilag_terkep(orszagok, telepulesek) {
  const doboz = elem("div"); doboz.id = "havi-vilag-terkep"; doboz.className = "havi-terkep-doboz";
  // (a kötött-szavak megjelenítő doboz)
  const szavakDoboz = elem("div", "havi-terkep-szavak");
  if (typeof L === "undefined") { return _terkep_fallback("Országok", orszagok); }   // fail-soft
  const g = await geo_assetek();
  const orszMap = {}; (orszagok||[]).forEach(o => { const iso = g.iso[kulcs(o.nev)]; if (iso) orszMap[iso] = o; });
  const maxO = Math.max(1, ...(orszagok||[]).map(o => o.volumen || 0));
  // térkép (későn, a doboz DOM-ba kerülése után inicializálva)
  setTimeout(() => {
    const map = L.map(doboz, { attributionControl: true }).setView([30, 10], 1.4);
    L.geoJSON(g.vilag, {
      style: f => { const o = orszMap[f.id]; return { weight: 1, color: "#888",
        fillColor: o ? szin_skala(o.volumen||0, maxO) : "#eee", fillOpacity: o ? 0.85 : 0.25 }; },
      onEachFeature: (f, layer) => { const o = orszMap[f.id]; if (o) {
        layer.bindTooltip(`${o.nev} · volumen: ${o.volumen||0}`);
        layer.on("click", () => { szavakDoboz.textContent = `${o.nev}: ${(o.szavak||[]).join(", ")}`; }); } },
    }).addTo(map);
    // külföldi városok (nincs HU-koordinátájuk) kör-jelölőként
    const kulf = (telepulesek||[]).filter(t => !g.huk[kulcs(t.nev)] && g.varos[kulcs(t.nev)]);
    const maxV = Math.max(1, ...kulf.map(t => t.volumen || 0));
    kulf.forEach(t => { const c = g.varos[kulcs(t.nev)];
      L.circleMarker(c, { radius: 5 + 9 * ((t.volumen||0)/maxV), color: "#c0392b", fillColor: "#e74c3c", fillOpacity: 0.8, weight: 1 })
        .bindTooltip(`${t.nev} · volumen: ${t.volumen||0}`)
        .on("click", () => { szavakDoboz.textContent = `${t.nev}: ${(t.szavak||[]).join(", ")}`; })
        .addTo(map); });
    havi_terkepek.vilag = map;
  }, 0);
  const wrap = elem("section", "elemzes-szekcio");
  wrap.appendChild(elem("h3", null, "Országok és külföldi városok (térkép)"));
  wrap.appendChild(doboz); wrap.appendChild(szavakDoboz);
  return wrap;
}
```
`havi_terkepek` objektum a `window`-on (mint `havi_chartok`), `_terkep_fallback` a Fázis A `ner_csoport`-ját adja vissza. `rajzol`: az „Országok" `ner_csoport` HELYETT `t.appendChild(await vilag_terkep(ner.orszagok, ner.telepulesek))` (a rajzol legyen `async`, a hívói `await`-eljék).

`docs/css/app.css`: `#havi-tartalom .havi-terkep-doboz { height: 26rem; margin:.5rem 0; } .havi-terkep-szavak { font-size:.85rem; color:#333; margin:.3rem 0 1rem; min-height:1.2rem; }`

- [ ] **Step 4: Run test to verify it passes** — `node --check docs/js/havi.js && npx playwright test --workers=1 e2e/havi.spec.js`. A korábbi havi tesztek maradjanak zöldek (a rajzol async-esítése ne törje őket — a betöltő `honap_valt` await-elje a rajzolt).

- [ ] **Step 5: Commit**
```bash
git add docs/havi.html docs/js/havi.js docs/css/app.css e2e/havi.spec.js
git commit -m "feat(havi): vilagterkep (orszag-choropleth + kulfoldi varosok + hover + kattintas=szavak)"
```

---

### Task 3: Magyarország-térkép — magyar települések + hover + kattintás=szavak

**Files:**
- Modify: `docs/js/havi.js`, `docs/css/app.css`
- Test: `e2e/havi.spec.js`

**Interfaces:**
- Consumes: `art.ner.telepulesek`; a vendored `hu-telepules-koord.json`; `L`.
- Produces: `#havi-hu-terkep` Leaflet-térkép a magyar településekkel (kör-jelölők), hover + kattintás=szavak; fail-soft.

- [ ] **Step 1: Write the failing test** — `e2e/havi.spec.js`: a mock `telepulesek` tartalmazzon egy magyar „Debrecen"-t (van HU-koordinátája) → `#havi-hu-terkep .leaflet-container` létezik, van kör-jelölő, kattintásra a `szavak` a `.havi-terkep-szavak`-ban.

- [ ] **Step 2: Run test to verify it fails** — nincs `#havi-hu-terkep`.

- [ ] **Step 3: Write minimal implementation** — `docs/js/havi.js` ÚJ `hu_terkep(telepulesek)` (a `vilag_terkep` mintájára): a magyar települések = `telepulesek.filter(t => g.huk[kulcs(t.nev)])`; `L.map(...).setView([47.16, 19.5], 6.6)` (Magyarország); a szűrt települések `L.circleMarker(g.huk[kulcs(t.nev)], {radius: 5+9*arány, …})` + tooltip + kattintás=szavak; `havi_terkepek.hu = map`; fail-soft `_terkep_fallback("Települések", telepulesek)`. A `rajzol`-ban a „Települések" `ner_csoport` HELYETT `t.appendChild(await hu_terkep(ner.telepulesek))`.
`docs/css/app.css`: a `#havi-hu-terkep` ugyanazt a `.havi-terkep-doboz` magasságot kapja.

- [ ] **Step 4: Run test to verify it passes** — `node --check` + `npx playwright test --workers=1 e2e/havi.spec.js` (minden havi teszt zöld).

- [ ] **Step 5: Commit**
```bash
git add docs/js/havi.js docs/css/app.css e2e/havi.spec.js
git commit -m "feat(havi): Magyarorszag-terkep (magyar telepulesek + hover + kattintas=szavak)"
```

---

### Task 4: Jelmagyarázat + „nem-illeszthető nevek" fallback-lista + csiszolás

**Files:**
- Modify: `docs/js/havi.js`, `docs/css/app.css`
- Test: `e2e/havi.spec.js`

**Interfaces:**
- Produces: mindkét térkép alatt egy tömör lista a térképen NEM megjeleníthető (nincs koord/ISO-match) nevekről + volumenről; egy egyszerű jelmagyarázat (szín=volumen).

- [ ] **Step 1: Write the failing test** — `e2e/havi.spec.js`: a mock tartalmazzon egy ország-nevet ISO-match NÉLKÜL (pl. „Seholország") ÉS egy külföldi várost koord NÉLKÜL → egy `.havi-terkep-fallback` listában megjelennek (névvel+volumennel), NEM tűnnek el csendben. A magyar térkép fallback-listája hasonlóan a koord-nélküli településekre.

- [ ] **Step 2: Run test to verify it fails** — nincs `.havi-terkep-fallback`.

- [ ] **Step 3: Write minimal implementation** — a `vilag_terkep`/`hu_terkep`-ben számold ki a NEM-illeszthető entitásokat (ország: nincs `g.iso[kulcs(nev)]` VAGY az ISO nincs a GeoJSON-ban; külföldi város: nincs `g.varos`; HU: nincs `g.huk`), és egy `.havi-terkep-fallback` `<ul>`-ba `nev · volumen` formában told a doboz alá (ha van ilyen). Egy egyszerű jelmagyarázat-sor (`.havi-terkep-jelmagyarazat`: „Sötétebb = nagyobb volumen"). Kis CSS.

- [ ] **Step 4: Run test to verify it passes** — `node --check` + a teljes `e2e/havi.spec.js` zöld.

- [ ] **Step 5: Commit**
```bash
git add docs/js/havi.js docs/css/app.css e2e/havi.spec.js
git commit -m "feat(havi): terkep jelmagyarazat + nem-illesztheto nevek fallback-lista (grounding/a11y)"
```

---

## Önellenőrzés (a terv írója)

- **Spec-lefedettség:** vendor (Leaflet+geo) → T1; világtérkép (choropleth+városok+hover+kattintás) → T2; HU-térkép → T3; fallback-lista+jelmagyarázat+fail-soft → T4 (+T2/T3 fail-soft). ✓
- **Placeholder-szken:** a T1 build-parancsok konkrétak; a Leaflet-DOM-szelektorokat a T2/T3 implementer a valós DOM-ból igazítja (jelezve). A `world.geo.json` feature-`id` vs `properties.iso_a3` kulcsot a T1 dokumentálja, a T2 illesztés ehhez igazodik. ✓
- **Típus-konzisztencia:** minden lookup KISBETŰS kulcs; a `kulcs(nev)` normalizál; a `volumen` (Fázis A) int; a `havi_terkepek` a window-on (mint `havi_chartok`). A `rajzol` async — a hívói (`honap_valt`) await-elik. ✓
