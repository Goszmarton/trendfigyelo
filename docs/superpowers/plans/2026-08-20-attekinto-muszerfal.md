# Áttekintő műszerfal — irány + trend-illeszkedés — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Egy látványos összesítő panel az oldal tetején, amely kulcsszavanként (kategóriánként csoportosítva) mutatja a mai irányt (nő/stagnál/csökken) és azt, hogy a mai érték illeszkedik-e a trendhez vagy a szokásosnál távolabb van tőle.

**Architecture:** A backend (regresszió) új, LEÍRÓ statisztikai mezőket számol (reziduum + szokásos ingadozás MAD-del + kétállapotú illeszkedés-jelző; a `tüntetés`-nél a mediántól); a frontend csak megjeleníti egy új `#attekinto-blokk` szekcióban, a meglévő `egyesitett_reg()` adatból, a meglévő domen-csoportosítás és ⓘ-info mintát követve.

**Tech Stack:** Python 3 (`trendfigyelo/regresszio.py`, `statistics`), pytest; vanilla JS (`docs/js/app.js`, `createElement`), CSS (`docs/css/app.css`), Playwright.

**Spec:** `docs/superpowers/specs/2026-08-20-attekinto-muszerfal-design.md`

## Global Constraints

- **DOC-COMMIT megvolt** (`9a3e079`) — a spec commitolva; a kód ez után jön.
- **A frontend NEM SZÁMOL** — minden új szám a backendben dől el, a JSON-be íródik.
- **Nincs hamis tekintély** — a jelző LEÍRÓ; a szöveg SOSEM mond „szignifikáns"/„anomália". `ILLESZKEDES_SAV = 1.5` dokumentált, konzervatív állandó (nyers MAD-szorzó).
- **Látható, nem néma** — hiányzó mező / kevés pont → a jelző `null` / kimarad, sosem kitalált érték.
- **Adat-relatív** — „mai" = a szó legfrissebb LEZÁRT valós pontja (nem rendszeróra, nem részleges slot).
- **`docs/data/` ÉRINTETLEN** — ez a kör NEM ír adatot; `git status --short docs/data/` végig TISZTA.
- **`ATADAS-2026-08-18.txt` SOHA nem kerül `git add`-be.** `git add` mindig NÉVvel.
- **RED = VISELKEDÉS** — nem Import/Attribute/Name/timeout hiba; a tényleges RED-üzenetet ki kell írni. Ha a RED ezek egyike → STOP.
- **MUTÁCIÓ==1** körönként (a mutáció-teszt marker); a leltár a ZÁRÓ commitban frissül.
- **SOROS suite** — `python -m pytest -p no:randomly` és `npx playwright test --workers=1` végig zöld.
- Kerekítés: az új relatív-pont mezők `round(x, 2)`; az állapotot NYERS (kerekítetlen) értékből döntjük, hogy a kerekítés ne billentse a sávot.

---

### Task 1: Backend — trend-reziduum + szokásos ingadozás + illeszkedés (`regresszio_egy_ablak`)

**Files:**
- Modify: `trendfigyelo/regresszio.py` (új `ILLESZKEDES_SAV` konstans az `IRANY_KUSZOB` mellé; `regresszio_egy_ablak` érvényes-ág return-je bővül)
- Test: `tests/test_regresszio.py`

**Interfaces:**
- Produces: a `regresszio_egy_ablak` ÉRVÉNYES visszatérése bővül négy mezővel:
  - `mai_ertek: float` — az utolsó felhasznált (lezárt) pont értéke, `round(…,2)`
  - `mai_reziduum: float` — `mai_ertek − illesztett_érték(utolsó x)`, `round(…,2)`, előjeles
  - `reziduum_szokasos: float | None` — a reziduumok MAD-je, `round(…,2)`; `None` ha < 2 pont
  - `illeszkedes: "illeszkedik" | "tavolabb" | None`
- A HIBÁS ágak (`nincs_adat`/`keves_pont`/`degeneralt`/`rovid_span`) VÁLTOZATLANOK (nincs új mező).

- [ ] **Step 1: Write the failing test**

`tests/test_regresszio.py` — két teszt (illeszkedő és távoli mai pont). A pontok tökéletes egyenesen ülnek `ertek = 40 + i` (i=0..47), a szokásos ingadozás ~0; az „illeszkedik" esetnél az utolsó pont pontosan a vonalon, a „tavolabb" esetnél az utolsó pontot elrontjuk.

```python
def _pontok_egyenes(n, meredek=1.0, bazis=40.0, utolso_elteres=0.0):
    # n lezárt óránkénti pont egy egyenesen; az utolsó ponthoz opcionális eltérés
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2026, 8, 1, tzinfo=timezone.utc)
    pts = []
    for i in range(n):
        e = bazis + meredek * i + (utolso_elteres if i == n - 1 else 0.0)
        pts.append({"idopont_utc": (t0 + timedelta(hours=i)).isoformat(),
                    "ertek": e, "reszleges": False})
    return pts, t0

def test_regresszio_egy_ablak_mai_pont_illeszkedik():
    from trendfigyelo import regresszio
    pts, t0 = _pontok_egyenes(48, utolso_elteres=0.0)
    from datetime import timedelta
    iv = regresszio.regresszio_egy_ablak(
        pts, t0.isoformat(), (t0 + timedelta(hours=47)).isoformat(), 2)
    assert iv["ervenyes"] is True
    assert iv["mai_ertek"] == 87.0                 # 40 + 47
    assert abs(iv["mai_reziduum"]) < 0.01          # a vonalon ül
    assert iv["illeszkedes"] == "illeszkedik"

def test_regresszio_egy_ablak_mai_pont_tavolabb():
    from trendfigyelo import regresszio
    pts, t0 = _pontok_egyenes(48, utolso_elteres=30.0)   # az utolsó pont 30 ponttal a vonal fölött
    from datetime import timedelta
    iv = regresszio.regresszio_egy_ablak(
        pts, t0.isoformat(), (t0 + timedelta(hours=47)).isoformat(), 2)
    assert iv["ervenyes"] is True
    assert iv["mai_reziduum"] > 10                 # jóval a vonal fölött
    assert iv["reziduum_szokasos"] is not None
    assert iv["illeszkedes"] == "tavolabb"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_regresszio.py::test_regresszio_egy_ablak_mai_pont_illeszkedik tests/test_regresszio.py::test_regresszio_egy_ablak_mai_pont_tavolabb -v`
Expected: FAIL — `KeyError: 'mai_ertek'` (viselkedés: a mező még nem létezik). Írd ki a tényleges üzenetet. Ha a hiba Import/Attribute/Name → STOP.

- [ ] **Step 3: Write minimal implementation**

`regresszio.py` — konstans az `IRANY_KUSZOB` sora mellé:

```python
# ILLESZKEDES_SAV: LEÍRÓ kétállapot-sáv szorzó a mai reziduum és a szokásos ingadozás (MAD) között.
# NEM szignifikancia-küszöb; konzervatív, kerek választás (spec 2026-08-20-attekinto-muszerfal-design §3).
ILLESZKEDES_SAV = 1.5
```

`regresszio_egy_ablak`-ban, közvetlenül az `illesztes_vonal = [...]` UTÁN, a `return {`-ba beépítve:

```python
    illesztett = [a + b * x for x in xs]
    reziduumok = [y - f for y, f in zip(ys, illesztett)]
    mai_reziduum = reziduumok[-1]
    if len(reziduumok) >= 2:
        med = statistics.median(reziduumok)
        mad = statistics.median([abs(r - med) for r in reziduumok])
        reziduum_szokasos = round(mad, 2)
        illeszkedes = "illeszkedik" if abs(mai_reziduum) <= ILLESZKEDES_SAV * mad else "tavolabb"
    else:
        reziduum_szokasos = None
        illeszkedes = None
```

és a return dict-be (az `illesztes_vonal` mellé):

```python
        "mai_ertek": round(ys[-1], 2),
        "mai_reziduum": round(mai_reziduum, 2),
        "reziduum_szokasos": reziduum_szokasos,
        "illeszkedes": illeszkedes,
```

(A `statistics` már importált — a `regresszio_masodlagos_szamit` használja.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_regresszio.py -v`
Expected: PASS (a két új teszt + a meglévők).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/regresszio.py tests/test_regresszio.py
git commit  # üzenet: feat(attekinto-muszerfal): trend-reziduum + szokásos ingadozás (MAD) + illeszkedés-jelző a regresszio_egy_ablak-ban
```

---

### Task 2: Backend — `tüntetés` (esemenyjelzo) mediántól-eltérés + illeszkedés

**Files:**
- Modify: `trendfigyelo/regresszio.py` (`regresszio_masodlagos_szamit` esemenyjelzo-ága)
- Test: `tests/test_masodlagos_ag.py`

**Interfaces:**
- Consumes: `ILLESZKEDES_SAV` (Task 1).
- Produces: az esemenyjelzo szó SZÓ-SZINTŰ kimenete bővül (a `szint` mellé):
  - `mai_szint: float` — a legfrissebb lezárt szint-érték
  - `mai_elteres: float` — `mai_szint − szint`, `round(…,2)`, előjeles
  - `szint_szokasos: float | None` — a szint-értékek MAD-je a mediánhoz, `round(…,2)`; `None` ha < 2 pont
  - `illeszkedes: "illeszkedik" | "tavolabb" | None`

- [ ] **Step 1: Write the failing test**

`tests/test_masodlagos_ag.py`:

```python
def _mp_nyers_esemeny(ertekek):
    # egy heti esemenyjelzo rekord növekvő idővel; az utolsó érték = a legfrissebb szint
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    pts = [{"idopont_utc": (t0 + timedelta(weeks=i)).isoformat(),
            "ertek": e, "reszleges": False} for i, e in enumerate(ertekek)]
    return {"kulcsszavak": {"tüntetés": [{
        "racs": "het", "timeframe": "today 12-m",
        "ablak_kezdet_utc": pts[0]["idopont_utc"],
        "ablak_veg_utc": pts[-1]["idopont_utc"], "pontok": pts}]}}

def test_masodlagos_esemenyjelzo_median_elteres():
    from trendfigyelo import regresszio
    from trendfigyelo.config import KulcsszoTetel
    # a `_config` helper (a fájl tetején) — a tüntetést esemenyjelzo-ként ismeri → _domen_tipus
    # a config-ból adja a tipus="esemenyjelzo"-t (nincs szükség tortenet-re)
    config = _config([KulcsszoTetel("tüntetés", "kozelet", "esemenyjelzo", "het")])
    nyers = _mp_nyers_esemeny([8, 8, 8, 8, 9, 8, 8, 30])   # medián 8; az utolsó (30) messze
    out = regresszio.regresszio_masodlagos_szamit(
        nyers, {"napok": []}, config, "2026-08-20T19:00:00+00:00")
    t = out["kulcsszavak"]["tüntetés"]
    assert t["szint"] == 8
    assert t["mai_szint"] == 30
    assert t["mai_elteres"] == 22.0
    assert t["szint_szokasos"] is not None
    assert t["illeszkedes"] == "tavolabb"
```

Megjegyzés: a `_config` és a `_eles_config()` a `tests/test_masodlagos_ag.py` TETEJÉN már léteznek, és a `KulcsszoTetel(kifejezes, domen, tipus, racs)` sorrenddel a `tüntetés`-t `esemenyjelzo`-ként veszik fel — így a `_domen_tipus` a config-ból (nem a tortenet-ből) adja a típust, üres `{"napok": []}` tortenet mellett is. NE találj ki `ures_config`-ot.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_masodlagos_ag.py::test_masodlagos_esemenyjelzo_median_elteres -v`
Expected: FAIL — `KeyError: 'mai_szint'` (viselkedés). Írd ki a tényleges üzenetet. Import/Attribute/Name → STOP.

- [ ] **Step 3: Write minimal implementation**

`regresszio_masodlagos_szamit` esemenyjelzo-ágában a jelenlegi

```python
            lezart = [p["ertek"] for p in rek["pontok"] if not p.get("reszleges")] if rek else []
            ki[szo]["szint"] = statistics.median(lezart) if lezart else None
            ki[szo]["szint_modszer"] = "median"
```

helyére (idő-rendezett, hogy a „legfrissebb" jól legyen; a medián rendezés-független → változatlan):

```python
            lezart_pontok = sorted((p for p in rek["pontok"] if not p.get("reszleges")),
                                   key=lambda p: p["idopont_utc"]) if rek else []
            ertekek = [p["ertek"] for p in lezart_pontok]
            szint = statistics.median(ertekek) if ertekek else None
            ki[szo]["szint"] = szint
            ki[szo]["szint_modszer"] = "median"
            if szint is not None and len(ertekek) >= 2:
                mai_szint = ertekek[-1]
                mai_elteres = mai_szint - szint
                mad = statistics.median([abs(e - szint) for e in ertekek])
                ki[szo]["mai_szint"] = mai_szint
                ki[szo]["mai_elteres"] = round(mai_elteres, 2)
                ki[szo]["szint_szokasos"] = round(mad, 2)
                ki[szo]["illeszkedes"] = ("illeszkedik"
                    if abs(mai_elteres) <= ILLESZKEDES_SAV * mad else "tavolabb")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_masodlagos_ag.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/regresszio.py tests/test_masodlagos_ag.py
git commit  # üzenet: feat(attekinto-muszerfal): esemenyjelzo (tüntetés) mediántól-eltérés + illeszkedés-jelző
```

---

### Task 3: Frontend — panel-váz (szekció + render + domen-csoportok + irány-ikon)

**Files:**
- Modify: `docs/index.html` (új `<section id="attekinto-blokk">` a `<main>` ELSŐ gyereke)
- Modify: `docs/js/app.js` (`RENDEREK` bővítés a lista ELEJÉN; új konstansok + `attekinto_blokk_render`)
- Modify: `docs/css/app.css` (kártya-rács + irány-ikon glyph)
- Test: `e2e/attekinto.spec.js` (ÚJ)

**Interfaces:**
- Consumes: `egyesitett_reg()` (meglévő), `DOMEN_SORREND`/`DOMEN_MAGYAR`/`EGYEB_KULCS`/`INTERVALLUMOK`/`IRANY_MAGYAR` (meglévő).
- Produces: `attekinto_blokk_render()`; DOM-szerződés: `#attekinto-blokk .attekinto-csoport[data-domen] > h3` + `.attekinto-kartya[data-kulcsszo] .attekinto-ikon[data-irany]`. Segéd `elsodleges_iv(szoreg)` → az első ÉRVÉNYES intervallum objektum, vagy `null`.

- [ ] **Step 1: Write the failing test**

`e2e/attekinto.spec.js` (ÚJ) — saját, minimál mockkal (a 4 kulcsszó-fájlt route-oljuk):

```javascript
const { test, expect } = require("@playwright/test");

function iv(over = {}) {
  return { ervenyes: true, meredekseg_nap: over.meredekseg_nap ?? 1.5,
    irany: over.irany ?? "novekszik", r2: 0.3,
    ablak_kezdet_utc: "2026-08-12T19:00:00+00:00", ablak_veg_utc: "2026-08-19T19:00:00+00:00",
    pontok_hasznalt: 168, pontok_nem_nulla: 160, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 0,
    illesztes_vonal: [{ idopont_utc: "2026-08-12T19:00:00+00:00", ertek: 70 },
                      { idopont_utc: "2026-08-19T18:00:00+00:00", ertek: 77 }],
    mai_ertek: over.mai_ertek ?? 74, mai_reziduum: over.mai_reziduum ?? -3,
    reziduum_szokasos: over.reziduum_szokasos ?? 6, illeszkedes: over.illeszkedes ?? "illeszkedik" };
}
function ivHibas(ok) { return { ervenyes: false, ok }; }
function szo(over = {}) {
  return { meres_kezdete: "2026-07-30", meres_vege: null, aktiv: true,
    domen: over.domen ?? "munkaeropiac", tipus: over.tipus ?? "szintmero", racs: over.racs,
    intervallumok: { "1_het": over.iv1het ?? iv(over),
      "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
      "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } };
}
function reg(kulcsszavak) {
  return { szamitva_utc: "2026-08-19T19:00:00+00:00", meredekseg_egyseg: "relatív pont / nap",
    irany_kuszob: 1.0, megjegyzes: "teszt", kulcsszavak };
}
async function mock(page, regObj, mpRegObj) {
  await page.route(/kulcsszo_masodlagos_regresszio\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify(mpRegObj || { kulcsszavak: {} }) }));
  await page.route(/kulcsszo_masodlagos_nyers\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify({ kulcsszavak: {} }) }));
  await page.route(/kulcsszo_regresszio\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify(regObj) }));
  await page.route(/kulcsszo_nyers\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify({ kulcsszavak: {} }) }));
}
const A = "#attekinto-blokk";

test("attekinto: panel legfelül, domen-csoportok, irány-ikon", async ({ page }) => {
  await mock(page, reg({
    "állás": szo({ domen: "munkaeropiac", irany: "csokken" }),
    "albérlet": szo({ domen: "lakhatas", irany: "stagnal" }),
  }));
  await page.goto("/");
  // a panel a #kulcsszo-blokk ELŐTT áll a DOM-ban
  const sorrend = await page.evaluate(() => {
    const a = document.querySelector("#attekinto-blokk");
    const k = document.querySelector("#kulcsszo-blokk");
    return a && k ? (a.compareDocumentPosition(k) & Node.DOCUMENT_POSITION_FOLLOWING) > 0 : false;
  });
  expect(sorrend).toBe(true);
  await expect(page.locator(A + " .attekinto-csoport[data-domen='munkaeropiac'] h3")).toHaveText("Munkaerőpiac");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='állás'] .attekinto-ikon"))
    .toHaveAttribute("data-irany", "csokken");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='albérlet'] .attekinto-ikon"))
    .toHaveAttribute("data-irany", "stagnal");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test e2e/attekinto.spec.js --workers=1`
Expected: FAIL — a `#attekinto-blokk` locator nem található / 0 elem (viselkedés: nincs panel). Írd ki a tényleges üzenetet.

- [ ] **Step 3: Write minimal implementation**

`docs/index.html` — a `<main>` ELSŐ gyerekeként (a `#kulcsszo-blokk` ELÉ):

```html
      <section id="attekinto-blokk" aria-label="Áttekintő – mai irány és trend">
        <h2>Mai áttekintő</h2>
      </section>
```

`docs/js/app.js` — a `RENDEREK` tömb ELEJÉRE:

```javascript
  { id: "attekinto-blokk", fn: attekinto_blokk_render },
```

`app.js` — a kulcsszó-render konstansai közelébe (pl. az `IRANY_MAGYAR` sor mellé):

```javascript
const IRANY_IKON = { novekszik: "novekszik", stagnal: "stagnal", csokken: "csokken" };  // data-irany értékek
// az első ÉRVÉNYES intervallum (legrövidebb ablak = a legfrissebb) — a panel „mai" nézete
function elsodleges_iv(szoreg) {
  const ivk = (szoreg && szoreg.intervallumok) || {};
  for (let i = 0; i < INTERVALLUMOK.length; i++) {
    const iv = ivk[INTERVALLUMOK[i].kulcs];
    if (iv && iv.ervenyes) return iv;
  }
  return null;
}
function attekinto_blokk_render() {
  const blokk = document.getElementById("attekinto-blokk");
  if (!blokk) return;
  blokk.querySelectorAll(".attekinto-csoport").forEach(function (e) { e.remove(); });
  const reg = egyesitett_reg();
  if (!reg || !reg.kulcsszavak) return;
  const csoportok = {};
  Object.keys(reg.kulcsszavak).forEach(function (szo) {
    const d = reg.kulcsszavak[szo].domen;
    const kulcs = DOMEN_MAGYAR[d] ? d : EGYEB_KULCS;
    (csoportok[kulcs] = csoportok[kulcs] || []).push(szo);
  });
  DOMEN_SORREND.forEach(function (d) {
    const kulcs = d === null ? EGYEB_KULCS : d;
    const szavak = csoportok[kulcs];
    if (!szavak || !szavak.length) return;
    const cs = document.createElement("div");
    cs.className = "attekinto-csoport";
    cs.setAttribute("data-domen", d === null ? "egyeb" : d);
    const h3 = document.createElement("h3");
    h3.textContent = d === null ? "Egyéb" : DOMEN_MAGYAR[d];
    cs.appendChild(h3);
    szavak.forEach(function (szo) {
      cs.appendChild(attekinto_kartya(szo, reg.kulcsszavak[szo]));
    });
    blokk.appendChild(cs);
  });
}
function attekinto_kartya(szo, szoreg) {
  const k = document.createElement("div");
  k.className = "attekinto-kartya";
  k.setAttribute("data-kulcsszo", szo);
  const iv = elsodleges_iv(szoreg);
  const ikon = document.createElement("span");
  ikon.className = "attekinto-ikon";
  if (iv && IRANY_IKON[iv.irany]) ikon.setAttribute("data-irany", iv.irany);
  k.appendChild(ikon);
  const nev = document.createElement("span");
  nev.className = "attekinto-szo";
  nev.textContent = szo;
  k.appendChild(nev);
  if (iv && IRANY_MAGYAR[iv.irany]) {
    const it = document.createElement("span");
    it.className = "attekinto-irany-szoveg";
    it.textContent = IRANY_MAGYAR[iv.irany];
    k.appendChild(it);
  }
  return k;
}
```

`docs/css/app.css` — a fájl végére:

```css
#attekinto-blokk .attekinto-csoport { margin: .6rem 0; }
#attekinto-blokk .attekinto-kartya { display: flex; align-items: center; gap: .5rem;
  padding: .4rem .6rem; border: 1px solid #e2e2e2; border-radius: 6px; margin: .3rem 0; max-width: 100%; }
#attekinto-blokk .attekinto-ikon[data-irany="novekszik"]::before { content: "▲"; color: #2e7d32; }
#attekinto-blokk .attekinto-ikon[data-irany="stagnal"]::before   { content: "▬"; color: #777; }
#attekinto-blokk .attekinto-ikon[data-irany="csokken"]::before   { content: "▼"; color: #b23c3c; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx playwright test e2e/attekinto.spec.js --workers=1`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/index.html docs/js/app.js docs/css/app.css e2e/attekinto.spec.js
git commit  # üzenet: feat(attekinto-muszerfal): panel-váz — szekció legfelül, domen-csoportok, irány-ikon
```

---

### Task 4: Frontend — illeszkedés-jelző + ⓘ-info-doboz (+ null-peremeset)

**Files:**
- Modify: `docs/js/app.js` (`attekinto_kartya` bővítés az illeszkedés-jelzővel; az ⓘ-doboz a render-be)
- Modify: `docs/css/app.css` (a közös ⓘ-szelektorhoz csatlakozás + jelző-szín)
- Test: `e2e/attekinto.spec.js`

**Interfaces:**
- Consumes: az intervallum `illeszkedes` mezője (Task 1).
- Produces: `.attekinto-kartya .attekinto-illeszkedes[data-illeszkedes]` (érték `"illeszkedik"`/`"tavolabb"`); `#attekinto-blokk .attekinto-magyarazat` (ⓘ-doboz). `illeszkedes == null` → NINCS jelző.

- [ ] **Step 1: Write the failing test**

`e2e/attekinto.spec.js` — új tesztek:

```javascript
test("attekinto: illeszkedés-jelző két állapota + null → nincs jelző", async ({ page }) => {
  await mock(page, reg({
    "állás": szo({ domen: "munkaeropiac", irany: "csokken", illeszkedes: "illeszkedik" }),
    "hitel": szo({ domen: "haztartasi_penzugy", irany: "novekszik", illeszkedes: "tavolabb" }),
    "benzin": szo({ domen: "energia", iv1het: { ervenyes: false, ok: "keves_pont" } }),
  }));
  await page.goto("/");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='állás'] .attekinto-illeszkedes"))
    .toHaveAttribute("data-illeszkedes", "illeszkedik");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='hitel'] .attekinto-illeszkedes"))
    .toHaveAttribute("data-illeszkedes", "tavolabb");
  // benzin: nincs érvényes intervallum → nincs illeszkedés-jelző (nem kitalált)
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='benzin'] .attekinto-illeszkedes")).toHaveCount(0);
});

test("attekinto: ⓘ-magyarázó doboz jelen van", async ({ page }) => {
  await mock(page, reg({ "állás": szo({ domen: "munkaeropiac" }) }));
  await page.goto("/");
  await expect(page.locator(A + " .attekinto-magyarazat")).toHaveCount(1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test e2e/attekinto.spec.js --workers=1`
Expected: FAIL — a `.attekinto-illeszkedes` / `.attekinto-magyarazat` locator 0 elem (viselkedés).

- [ ] **Step 3: Write minimal implementation**

`app.js` — a jelző-szövegek konstansként (a `IRANY_IKON` mellé):

```javascript
const ILLESZKEDES_SZOVEG = { illeszkedik: "illeszkedik a trendhez", tavolabb: "a szokásosnál távolabb a trendtől" };
const ATTEKINTO_MAGYARAZAT = "Ez számolt, leíró jelző: a mai érték eltérése a szokásos ingadozáshoz mérve — " +
  "nem szignifikancia-teszt. A tüntetésnél a mediántól való eltérés.";
```

`attekinto_kartya`-ban, a return előtt (az irány-szöveg után):

```javascript
  if (iv && iv.illeszkedes && ILLESZKEDES_SZOVEG[iv.illeszkedes]) {
    const j = document.createElement("span");
    j.className = "attekinto-illeszkedes";
    j.setAttribute("data-illeszkedes", iv.illeszkedes);
    j.textContent = ILLESZKEDES_SZOVEG[iv.illeszkedes];
    k.appendChild(j);
  }
```

`attekinto_blokk_render`-ben, a `blokk.querySelectorAll(".attekinto-csoport")…remove()` UTÁN, a csoportok építése ELŐTT (idempotens: előbb töröljük, ha van):

```javascript
  blokk.querySelectorAll(".attekinto-magyarazat").forEach(function (e) { e.remove(); });
  const magy = document.createElement("p");
  magy.className = "attekinto-magyarazat";
  magy.textContent = ATTEKINTO_MAGYARAZAT;
  const h2 = blokk.querySelector("h2");
  if (h2) h2.insertAdjacentElement("afterend", magy); else blokk.appendChild(magy);
```

`docs/css/app.css` — a `.attekinto-magyarazat`-ot csatold a MEGLÉVŐ közös ⓘ-szabályhoz (a két szelektor-listához, app.css:139-151 tájékán add hozzá `#attekinto-blokk .attekinto-magyarazat,` egy-egy sorral), hogy bájt-azonos legyen (kék szegély + ⓘ ::before). A jelző-színhez a fájl végére:

```css
#attekinto-blokk .attekinto-illeszkedes { font-size: .82rem; color: #555; }
#attekinto-blokk .attekinto-illeszkedes[data-illeszkedes="tavolabb"]::before { content: "⚠ "; color: #b8860b; }
#attekinto-blokk .attekinto-illeszkedes[data-illeszkedes="illeszkedik"]::before { content: "✓ "; color: #2e7d32; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx playwright test e2e/attekinto.spec.js --workers=1`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/js/app.js docs/css/app.css e2e/attekinto.spec.js
git commit  # üzenet: feat(attekinto-muszerfal): illeszkedés-jelző (✓/⚠) + ⓘ-magyarázó doboz a közös mintában
```

---

### Task 5: Frontend — `tüntetés` (esemenyjelzo): nyíl nélkül + mediántól-eltérés

**Files:**
- Modify: `docs/js/app.js` (`egyesitett_reg` — az esemenyjelzo szó-szintű új mezőit átvezetni; `attekinto_kartya` — esemenyjelzo-ág)
- Test: `e2e/attekinto.spec.js`

**Interfaces:**
- Consumes: a másodlagos regresszió szó-szintű `mai_szint`/`mai_elteres`/`szint_szokasos`/`illeszkedes` (Task 2).
- Produces: esemenyjelzo kártya — NINCS `data-irany`, van `.attekinto-illeszkedes[data-illeszkedes]` a MEDIÁN-szöveggel; a `tobb` objektum bővül.

- [ ] **Step 1: Write the failing test**

`e2e/attekinto.spec.js`:

```javascript
function mpReg(kulcsszavak) {
  return { szamitva_utc: "2026-08-19T19:00:00+00:00", meredekseg_egyseg: "relatív pont / nap",
    elmozdulas_kuszob: 7.0, megjegyzes: "teszt", kulcsszavak };
}

test("attekinto: tüntetés esemenyjelzo — nincs nyíl, mediántól-eltérés", async ({ page }) => {
  const regObj = reg({
    "tüntetés": szo({ domen: "kozelet", tipus: "esemenyjelzo",
      iv1het: { ervenyes: false, ok: "esemenyjelzo" } }),
  });
  const mp = mpReg({ "tüntetés": { racs: "het", aktiv: true, domen: "kozelet", tipus: "esemenyjelzo",
    szint: 8, szint_modszer: "median", mai_szint: 30, mai_elteres: 22, szint_szokasos: 1,
    illeszkedes: "tavolabb", intervallumok: {} } });
  await mock(page, regObj, mp);
  await page.goto("/");
  const kartya = page.locator(A + " .attekinto-kartya[data-kulcsszo='tüntetés']");
  await expect(kartya).toHaveCount(1);
  await expect(kartya.locator(".attekinto-ikon")).not.toHaveAttribute("data-irany", /.+/);   // nincs nyíl
  await expect(kartya.locator(".attekinto-illeszkedes")).toHaveAttribute("data-illeszkedes", "tavolabb");
  await expect(kartya.locator(".attekinto-illeszkedes")).toContainText("mediántól");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test e2e/attekinto.spec.js --workers=1`
Expected: FAIL — a `tüntetés` kártyán nincs `.attekinto-illeszkedes` / a szöveg nem „mediántól" (viselkedés). Írd ki a tényleges üzenetet.

- [ ] **Step 3: Write minimal implementation**

`egyesitett_reg` — a `tobb` objektum (app.js:269) bővítése, hogy az esemenyjelzo szó-szintű új mezői is átjöjjenek:

```javascript
    const tobb = (m && m.szint != null)
      ? { szint: m.szint, szint_modszer: m.szint_modszer,
          mai_szint: m.mai_szint, mai_elteres: m.mai_elteres,
          szint_szokasos: m.szint_szokasos, illeszkedes_szint: m.illeszkedes }
      : null;
```

(Az `illeszkedes`-t `illeszkedes_szint` néven visszük át, hogy ne ütközzön a trend-intervallum `illeszkedes`-ével.)

`app.js` — esemenyjelzo jelző-szövegek (az `ILLESZKEDES_SZOVEG` mellé):

```javascript
const ILLESZKEDES_SZINT_SZOVEG = { illeszkedik: "a megszokott szint körül",
  tavolabb: "a megszokottnál távolabb a mediántól" };
```

`attekinto_kartya` — a függvény elején ágazz el esemenyjelzo-ra (az `elsodleges_iv` UTÁN):

```javascript
  if (szoreg.tipus === "esemenyjelzo") {
    // NINCS irány-nyíl (a backend nem ad irányt); a „kiugró" a MEDIÁNTÓL való eltérés
    const all = szoreg.illeszkedes_szint;
    if (all && ILLESZKEDES_SZINT_SZOVEG[all]) {
      const j = document.createElement("span");
      j.className = "attekinto-illeszkedes";
      j.setAttribute("data-illeszkedes", all);
      j.textContent = ILLESZKEDES_SZINT_SZOVEG[all];
      k.appendChild(j);
    }
    return k;
  }
```

FONTOS: ez az ág az `ikon` és a `nev` létrehozása UTÁN, de a trend-jelző (Task 4) ELŐTT álljon — a `nev` (szó) minden kártyán kell. Rendezd úgy: (1) `ikon` (esemenyjelzo-nál üres, nincs `data-irany`), (2) `nev`, (3) ha esemenyjelzo → medián-jelző + `return k`, (4) különben irány-szöveg + trend-jelző.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx playwright test e2e/attekinto.spec.js --workers=1`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/js/app.js e2e/attekinto.spec.js
git commit  # üzenet: feat(attekinto-muszerfal): tüntetés (esemenyjelzo) — nyíl nélkül, mediántól-eltérés a panelen
```

---

### Task 6: Zárás — teljes SOROS suite + leltár + záró commit

**Files:**
- Modify: `docs/superpowers/leltar.md` (új LESZÁLLÍTVA sor + invariáns-számok)

- [ ] **Step 1: Teljes SOROS suite**

Run: `python -m pytest -p no:randomly -q` → minden zöld; jegyezd fel a darabszámot.
Run: `npx playwright test --workers=1` → minden zöld; jegyezd fel a darabszámot.

- [ ] **Step 2: `docs/data/` tisztaság + MUTÁCIÓ ellenőrzés**

Run: `git status --short docs/data/` → ÜRES (semmit nem írtunk az adatrétegbe).
Run: `grep -rn "MUTÁCIÓ" trendfigyelo/ tests/ | wc -l` → pontosan `1` (vagy a projekt aktuális marker-száma; ne nőjön).

- [ ] **Step 3: Leltár frissítése**

`docs/superpowers/leltar.md` — új LESZÁLLÍTVA tétel (`ATTEKINTO-MUSZERFAL`), a backend + frontend körök összefoglalójával, a MÉRT pytest/Playwright darabszámmal, a spec- és terv-hivatkozással. Az invariáns bucket-mozgás: az aktív→kész/rekord számokat a záró állapot szerint frissítsd, NÉVvel ellenőrizve bucketenként (a `NAPI RUTIN` invariáns-szabály szerint).

- [ ] **Step 4: Záró commit (üzenet-jóváhagyás UTÁN)**

Kérj commit-üzenet jóváhagyást a felhasználótól (a projekt-kapu), majd:

```bash
git add docs/superpowers/leltar.md
git commit  # üzenet: a jóváhagyott záró üzenet (feat(attekinto-muszerfal): … + leltár)
```

- [ ] **Step 5: Push — KÜLÖN körben**

A push a projekt-szabály szerint külön kör, `git fetch` + `rev-list 0 0` ellenőrzéssel; NE toldd a záró commit lépésébe.

---

## Self-Review (a terv a spec ellen)

- **Spec-lefedettség:** §3.1 trend-reziduum+MAD+állapot → Task 1. §3.2 esemenyjelzo mediántól → Task 2. §4.1 elhelyezés + §4.2 csoport/ikon → Task 3. §4.2 illeszkedés-jelző + §4.3 ⓘ-doboz → Task 4. §4.2 esemenyjelzo nyíl-nélkül + medián-szöveg → Task 5. §5 peremesetek: érvénytelen intervallum→nincs jelző (Task 4 `benzin` teszt), esemenyjelzo→nincs nyíl (Task 5), `illeszkedes==null`→nincs jelző (Task 1/4). §6 tesztelés → minden task RED→GREEN + Task 6 kapuk. §2 „frontend nem számol" → minden szám a backendből (Task 1/2), a frontend csak olvas.
- **Placeholder-vizsgálat:** nincs TBD/TODO; minden lépés konkrét kódot ad. A Task 2 fixture-nél explicit utasítás: kövesd a meglévő esemenyjelzo-teszt config/tortenet felépítését (ne találj ki újat).
- **Típus-konzisztencia:** `illeszkedes` a trend-intervallumon (`iv.illeszkedes`), az esemenyjelzo-nál a szó-szinten átvezetve `illeszkedes_szint` néven (ütközés-elkerülés, Task 5) — a render külön szövegtérképet használ (`ILLESZKEDES_SZOVEG` vs `ILLESZKEDES_SZINT_SZOVEG`). A DOM-attribútum mindkét ágon `data-illeszkedes` (közös CSS). `mai_ertek`/`mai_reziduum`/`reziduum_szokasos` végig ugyanígy nevezve.
- **Hatókör:** egy implementációs tervhez elég szűk (13 szó + tüntetés, egy panel); nincs adatréteg-írás.
