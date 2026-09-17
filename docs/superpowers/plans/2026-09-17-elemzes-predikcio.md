# „Előrejelzések" rész a napi (esti) AI-elemzésben Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Az esti napi AI-elemzés kapjon egy tömör „Előrejelzések – mire számíthatunk?" szekciót, amely a követett kulcsszavak közeltávú előrejelzéseit foglalja össze grounded, őszinte prózában.

**Architecture:** A predikció-adat a két regresszió-fájl merge-éből (másodlagos nyer). Egy tiszta aggregátor per szó kiválasztja a legrövidebb ≥2-pontos horizontot, és a forecast saját trajektóriájából számol irányt/mértéket/bizonytalanságot. Ez a payload `predikcio` blokkja; a séma (csak este, a payload jelenlététől függően) kéri a szekciót; a prompt vezérli a narratívát; a frontend fail-soft rendereli.

**Tech Stack:** Python (numpy, anthropic SDK) backend, vanilla JS frontend, pytest + Playwright.

**Spec:** docs/superpowers/specs/2026-09-17-elemzes-predikcio-design.md

## Global Constraints

- Tiszta numpy + meglévő anthropic SDK; **NULLA új Python-dependency**. Additív, MUTÁCIÓ=1.
- Backend tesztelt logikában NINCS argless `datetime.now()` / `seged.most_utc()` (az aggregátor determinista).
- Frontend: NINCS `new Date()` / `Date.now()`.
- Irreplaceable adat READ-ONLY.
- SOROS suite: `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`.
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással.
- A napi elemzés meglévő szekciói (valtozas/kulcsszavak/felkapott/youtube), a reggeli mód, a predikció-mag (predikcio.py) VÁLTOZATLAN.

---

### Task 1: Backend — `_predikcio_kozeltav` aggregátor

**Files:**
- Modify: `trendfigyelo/elemzo.py` (új konstansok + függvény, a `_kulcsszo_het` köré)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: a `kulcsszo_regresszio.json` és `kulcsszo_masodlagos_regresszio.json` szerkezete: `kulcsszavak[szo] = {domen, predikcio: {horizont: {pont:[{ertek}], also:[...], felso:[...], megbizhatosag, nem_becsulheto?}}}`.
- Produces: `_predikcio_kozeltav(regresszio, masodlagos) -> {"szavak": [{szo, domen, horizont, irany, valtozas_pont, megbizhatosag, sav_pont}], "osszesites": {emelkedo, csokkeno, stagnalo}} | None`.

- [ ] **Step 1: Write the failing test**

`tests/test_elemzo.py`-ba:

```python
def _pred_blk(pontok, sav=4.0, megb=0.9):
    # pontok: y-értékek listája → pont/also/felso blokk (idő nem számít az aggregátornak)
    pont = [{"idopont_utc": f"2026-09-{10+i:02d}T00:00:00+00:00", "ertek": float(y)} for i, y in enumerate(pontok)]
    also = [{"idopont_utc": p["idopont_utc"], "ertek": p["ertek"] - sav} for p in pont]
    felso = [{"idopont_utc": p["idopont_utc"], "ertek": p["ertek"] + sav} for p in pont]
    return {"pont": pont, "also": also, "felso": felso, "megbizhatosag": megb}

def test_predikcio_kozeltav_merge_nearterm_irany_osszesites():
    # órás-only szó: 1_nap 2+ pontból, emelkedő; heti szó: 1_nap/1_het 1-pontos (kihagyva) → 1_ho a near-term
    reg = {"kulcsszavak": {
        "benzin": {"domen": "energia", "predikcio": {
            "1_nap": _pred_blk([50, 62]),                     # +12 → emelkedik
            "3_ho": {"nem_becsulheto": True}, "1_ev": {"nem_becsulheto": True}}},
        "albérlet": {"domen": "lakhatas", "predikcio": {
            "1_nap": _pred_blk([70]), "1_het": _pred_blk([70]),   # 1-pontos → kihagyva
            "1_ho": _pred_blk([70, 66], sav=10.0, megb=0.3)}},     # -4 → csökken, széles sáv
    }}
    masod = {"kulcsszavak": {"albérlet": {"domen": "lakhatas", "predikcio": {
        "1_ho": _pred_blk([70, 66], sav=10.0, megb=0.3)}}}}       # a másodlagos NYER (ugyanaz itt)
    out = elemzo._predikcio_kozeltav(reg, masod)
    sz = {s["szo"]: s for s in out["szavak"]}
    assert sz["benzin"]["horizont"] == "1 nap" and sz["benzin"]["irany"] == "emelkedik"
    assert sz["benzin"]["valtozas_pont"] == 12.0
    assert sz["albérlet"]["horizont"] == "1 hó" and sz["albérlet"]["irany"] == "csökken"
    assert sz["albérlet"]["sav_pont"] == 10.0                  # (felso-also)/2 = (76-56)/2
    assert out["osszesites"] == {"emelkedo": 1, "csokkeno": 1, "stagnalo": 0}

def test_predikcio_kozeltav_stagnal_deadband_es_ures_none():
    reg = {"kulcsszavak": {"csőd": {"domen": "penzugy", "predikcio": {"1_nap": _pred_blk([40, 41])}}}}  # +1 < 2 → stagnál
    out = elemzo._predikcio_kozeltav(reg, {})
    assert out["szavak"][0]["irany"] == "stagnál" and out["osszesites"]["stagnalo"] == 1
    assert elemzo._predikcio_kozeltav({}, {}) is None          # nincs szó → None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_elemzo.py::test_predikcio_kozeltav_merge_nearterm_irany_osszesites`
Expected: FAIL — `_predikcio_kozeltav` még nem létezik (AttributeError).

- [ ] **Step 3: Write minimal implementation**

`trendfigyelo/elemzo.py`-ba (a `_kulcsszo_het` függvény UTÁN, ~159. sor):

```python
NEAR_TERM_HORIZONTOK = ("1_nap", "1_het", "1_ho")   # near-term jelöltek, legfinomabbtól
_HORIZONT_CIMKE = {"1_nap": "1 nap", "1_het": "1 hét", "1_ho": "1 hó"}
IRANY_DEADBAND = 2.0                                 # |változás_pont| ennél kisebb → stagnál


def _predikcio_kozeltav(regresszio, masodlagos):
    """A követett szavak KÖZELTÁVÚ előrejelzés-összefoglalója (csak esti). A két regresszió merge-e
    (a másodlagos NYER, mint a frontend); szavanként a legrövidebb ≥2-pontos horizont, az irányt a
    forecast SAJÁT trajektóriájából (skála-konzisztens). Determinista. Üres → None."""
    primer = (regresszio or {}).get("kulcsszavak", {}) if isinstance(regresszio, dict) else {}
    masod = (masodlagos or {}).get("kulcsszavak", {}) if isinstance(masodlagos, dict) else {}
    szavak = []
    for szo, prec in primer.items():
        pred = dict((prec or {}).get("predikcio", {}) or {})
        pred.update((masod.get(szo, {}) or {}).get("predikcio", {}) or {})   # másodlagos felülír
        blk = hz = None
        for h in NEAR_TERM_HORIZONTOK:
            b = pred.get(h)
            if isinstance(b, dict) and not b.get("nem_becsulheto") and len(b.get("pont") or []) >= 2:
                blk, hz = b, h
                break
        if not blk:
            continue
        pont = blk["pont"]
        valtozas = round(float(pont[-1]["ertek"]) - float(pont[0]["ertek"]), 1)
        irany = ("emelkedik" if valtozas > IRANY_DEADBAND
                 else "csökken" if valtozas < -IRANY_DEADBAND else "stagnál")
        also, felso = blk.get("also") or [], blk.get("felso") or []
        sav = (round((float(felso[-1]["ertek"]) - float(also[-1]["ertek"])) / 2, 1)
               if also and felso else None)
        domen = (prec or {}).get("domen") or (masod.get(szo, {}) or {}).get("domen")
        szavak.append({"szo": szo, "domen": domen, "horizont": _HORIZONT_CIMKE[hz],
                       "irany": irany, "valtozas_pont": valtozas,
                       "megbizhatosag": blk.get("megbizhatosag"), "sav_pont": sav})
    if not szavak:
        return None
    szavak.sort(key=lambda s: -abs(s["valtozas_pont"]))
    osszesites = {"emelkedo": sum(1 for s in szavak if s["irany"] == "emelkedik"),
                  "csokkeno": sum(1 for s in szavak if s["irany"] == "csökken"),
                  "stagnalo": sum(1 for s in szavak if s["irany"] == "stagnál")}
    return {"szavak": szavak, "osszesites": osszesites}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_elemzo.py`
Expected: PASS (a két új teszt + a meglévők).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "feat(elemzes): _predikcio_kozeltav aggregator (merge + near-term + irany/osszesites)"
```

---

### Task 2: Backend — payload + séma + prompt + artefakt bekötés

**Files:**
- Modify: `trendfigyelo/elemzo.py` (`futtat`, `epit_payload`, `_valasz_sema`, `_AnthropicKliens.uzenet`, `valasz_to_artefakt`, `RENDSZER_PROMPT`)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: `_predikcio_kozeltav` (Task 1).
- Produces: `payload["predikcio"]` (csak este, ha van adat); a séma este-ben kéri a `predikcio` szekciót ha a payloadban van; `art["predikcio"] = {szoveg}` az esti artefaktban.

- [ ] **Step 1: Write the failing test**

`tests/test_elemzo.py`-ba:

```python
def test_epit_payload_predikcio_csak_este():
    reg = {"kulcsszavak": {"benzin": {"domen": "energia",
        "predikcio": {"1_nap": _pred_blk([50, 62])}}}}
    adatok = {"regresszio": reg, "masodlagos_regresszio": {}, "tortenet": {},
              "legfrissebb": {}, "napok_trendek": {}, "ma_szegmensek": {}, "lanc": {}}
    este = elemzo.epit_payload(adatok, mode="este")
    reggel = elemzo.epit_payload(adatok, mode="reggel")
    assert "predikcio" in este and este["predikcio"]["szavak"][0]["szo"] == "benzin"
    assert "predikcio" not in reggel                          # reggel scoped → nincs predikció

def test_valasz_sema_predikcio_flaggel_keri_a_szekciot():
    s_van = elemzo._valasz_sema(mode="este", predikcio=True)
    s_nincs = elemzo._valasz_sema(mode="este", predikcio=False)
    assert "predikcio" in s_van["required"] and "predikcio" in s_van["properties"]
    assert "predikcio" not in s_nincs["required"]

def test_artefakt_predikcio_bekerul_ha_van_payloadban():
    payload = _payload_szegmensekkel(van_reggel=True, van_este=True)
    payload["predikcio"] = {"szavak": [], "osszesites": {}}    # jelenlét → az artefakt átveszi az AI-szöveget
    ai = _ai_valasz(); ai["predikcio"] = {"szoveg": "Előrejelzés-próza."}
    art = elemzo.valasz_to_artefakt(ai, payload, nap="2026-08-31", modell="m")
    assert art["predikcio"]["szoveg"] == "Előrejelzés-próza."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_elemzo.py::test_valasz_sema_predikcio_flaggel_keri_a_szekciot tests/test_elemzo.py::test_epit_payload_predikcio_csak_este tests/test_elemzo.py::test_artefakt_predikcio_bekerul_ha_van_payloadban`
Expected: FAIL — `_valasz_sema` nem fogad `predikcio` paramétert / a payloadban nincs `predikcio` / az artefaktban nincs.

- [ ] **Step 3: Write minimal implementation**

**(a)** `epit_payload` — a `if mode != "reggel":` ág BŐVÍTÉSE (a youtube-blokk mellé), a `regresszio` már ki van szedve a fv. elején:

```python
    if mode != "reggel":
        p = _predikcio_kozeltav(regresszio, adatok.get("masodlagos_regresszio", {}))
        if p:
            payload["predikcio"] = p
        yt_szamok = _youtube_szamok(adatok.get("youtube_regresszio"), adatok.get("youtube_nyers"))
        if yt_szamok:
            payload["youtube"] = {"szamok": yt_szamok,
                                  "het_valos": _youtube_het(adatok.get("youtube_nyers"))["szavak"]}
```

**(b)** `_valasz_sema` — új `predikcio=False` paraméter; este-ben, ha igaz, a `predikcio` szekció bekerül:

```python
def _valasz_sema(youtube=False, mode="este", predikcio=False):
    if mode == "reggel":
        return {"type": "object", "additionalProperties": False,
                "required": ["felkapott"],
                "properties": {"felkapott": _szekcio_csoport("reggel")}}
    props = {
        "valtozas": _szekcio_sema(),
        "kulcsszavak": _szekcio_csoport("napi"),
        "felkapott": _szekcio_csoport("reggel", "este", "teljes_nap", "het"),
    }
    required = ["valtozas", "kulcsszavak", "felkapott"]
    if predikcio:
        props["predikcio"] = _szekcio_sema()
        required = required + ["predikcio"]
    if youtube:
        props["youtube"] = _szekcio_csoport("napi", "teljes_kep")
        required = required + ["youtube"]
    return {"type": "object", "additionalProperties": False,
            "required": required, "properties": props}
```

**(c)** `_AnthropicKliens.uzenet` — a séma-hívás (a `_valasz_sema(...)` a ~400. sorban) kapja a flaget:

```python
                           "schema": _valasz_sema(youtube="youtube" in payload, mode=mode,
                                                   predikcio="predikcio" in payload)}},
```

**(d)** `valasz_to_artefakt` — az esti `art` felépítése UTÁN (a `return art` ELŐTT), a payload jelenlétéből:

```python
    if "predikcio" in payload:
        art["predikcio"] = ai_valasz["predikcio"]
```

**(e)** `futtat` — az `adatok` dict bővítése:

```python
        "regresszio": _betolt(docs_data / "kulcsszo_regresszio.json") or {},
        "masodlagos_regresszio": _betolt(docs_data / "kulcsszo_masodlagos_regresszio.json") or {},
```

**(f)** `RENDSZER_PROMPT` — a (10) gondolatjel-szabály UTÁN, a záró idézőjel ELÉ, új szabály (a `+` konkatenáció mintáját követve):

```python
    "(11) Ha a bemenet előrejelzés-részt is tartalmaz: írj egy TÖMÖR „Előrejelzések\" bekezdést arról, "
    "mely követett keresések iránya mutat a közeljövőben emelkedést vagy csökkenést, és melyik a "
    "legmagabiztosabb. FONTOS őszinteség: ez a közelmúlt trendjének matematikai FOLYTATÁSA, NEM "
    "eseményjóslat – a valóság eltérhet; ezt a fogalmazás hordozza. A nagyon bizonytalan (széles "
    "bizonytalansági sávú vagy alacsony megbízhatóságú) előrejelzéseket őszintén jelzed, nem állítod "
    "biztosnak. NEM sorolod fel újra minden szót – a szembetűnő mozgókat emeled ki, a stagnáló többséget "
    "egy-két mondattal, csoportosítva összefoglalod. A szokásos szabályok itt is: folyó bekezdés, "
    "felsorolás/mezőnév tilalma, óvatos fogalmazás, rövid „–\" gondolatjel, számot sosem találsz ki. "
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_elemzo.py`
Expected: PASS (az új 3 teszt + minden meglévő elemzo-teszt zöld).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "feat(elemzes): predikcio payload + dinamikus sema + prompt + artefakt bekotes (csak este)"
```

---

### Task 3: Frontend — „Előrejelzések" szekció render

**Files:**
- Modify: `docs/js/elemzes.js` (a „Google kulcsszavak" csoport, a valtozas UTÁN)
- Test: `e2e/elemzes.spec.js`

**Interfaces:**
- Consumes: `art.predikcio = {szoveg}` (Task 2 írja az esti artefaktba).
- Produces: „Előrejelzések – mire számíthatunk?" szekció a fülön; fail-soft, ha `art.predikcio` hiányzik.

- [ ] **Step 1: Write the failing test**

`e2e/elemzes.spec.js`-be (új teszt; a meglévő FIXTURE mintájára):

```javascript
test("Előrejelzések szekció megjelenik, ha van art.predikcio (és kimarad, ha nincs)", async ({ page }) => {
  const alap = {
    frissitve: "2026-08-31T19:00:00+00:00", modell: "m", nap: "2026-08-31", mode: "este",
    valtozas: { diff: { van_elozo: true, mozgok: [] }, szoveg: "Változás." },
    kulcsszavak: { szamok: [], napi: { szoveg: "Napi." } },
    felkapott: { top: [], reggel_top: [], este_top: [], reggel_este_diff: {}, het_valos: [],
      reggel: { szoveg: "R." }, este: { szoveg: "E." }, teljes_nap: { szoveg: "Í." }, het: { szoveg: "H." } },
  };
  // (1) VAN predikció → a szekció megjelenik, a „Mi változott ma?" UTÁN
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: { ...alap, predikcio: { szoveg: "Előrejelzés-próza." } } }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  const szek = page.locator('.elemzes-szekcio:has(h3:text-is("Előrejelzések – mire számíthatunk?"))');
  await expect(szek).toHaveCount(1);
  await expect(szek.locator(".elemzes-szoveg")).toContainText("Előrejelzés-próza.");
  const cimek = await page.locator(".elemzes-szekcio h3").allTextContents();
  expect(cimek.indexOf("Mi változott ma?")).toBeLessThan(cimek.indexOf("Előrejelzések – mire számíthatunk?"));
});

test("Előrejelzések szekció KIMARAD, ha nincs art.predikcio (régi archív-nap)", async ({ page }) => {
  const alap = {
    frissitve: "2026-08-31T19:00:00+00:00", modell: "m", nap: "2026-08-31", mode: "este",
    valtozas: { diff: { van_elozo: true, mozgok: [] }, szoveg: "Változás." },
    kulcsszavak: { szamok: [], napi: { szoveg: "Napi." } },
    felkapott: { top: [], reggel_top: [], este_top: [], reggel_este_diff: {}, het_valos: [],
      reggel: { szoveg: "R." }, este: { szoveg: "E." }, teljes_nap: { szoveg: "Í." }, het: { szoveg: "H." } },
  };
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: alap }));   // NINCS predikcio
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Előrejelzések – mire számíthatunk?"))')).toHaveCount(0);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test --workers=1 -g "Előrejelzések szekció"`
Expected: FAIL — az első teszt: a szekció nincs (a render még nem rakja ki).

- [ ] **Step 3: Write minimal implementation**

`docs/js/elemzes.js`, a „Mi változott ma?" sor (a `t.appendChild(szekcio_elem("Mi változott ma?", art.valtozas));`) UTÁN:

```javascript
  // Előrejelzések – közeltávú forecast-összefoglaló (csak esti elemzésben van art.predikcio; fail-soft)
  if (art.predikcio) t.appendChild(szekcio_elem("Előrejelzések – mire számíthatunk?", art.predikcio));
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --check docs/js/elemzes.js && npx playwright test --workers=1 -g "Előrejelzések szekció"`
Expected: PASS. Ellenőrzés: a meglévő elemzes.spec tesztek (szekció-sorrend, YouTube) zöldek.

- [ ] **Step 5: Commit**

```bash
git add docs/js/elemzes.js e2e/elemzes.spec.js
git commit -m "feat(elemzes): 'Elorejelzesek' szekcio render a napi elemzes fulon (fail-soft)"
```

---

## Önellenőrzés (a terv írója)

- **Spec-lefedettség:** §2 adat → Task 1 (aggregátor) + Task 2 (payload); §3 séma+prompt → Task 2; §4.2 frontend → Task 3. ✓
- **Placeholder-szken:** nincs TBD; a konstansok konkrét értékkel (IRANY_DEADBAND=2.0, horizont-címkék). ✓
- **Típus-konzisztencia:** a `predikcio` alak `{szavak, osszesites}` a payloadban (Task 1→2), a séma/artefakt `{szoveg}` prózát ad (Task 2), a frontend `art.predikcio.szoveg`-et olvas (Task 3, a `szekcio_elem` a `.szoveg`-et várja). A séma a payload `"predikcio" in payload` jelenlétéből aktiválódik (mint a youtube). ✓
