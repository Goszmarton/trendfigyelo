# Elemzés-fül YouTube-szegmens — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Az Elemzés fül a Google mellett a YouTube-adatokat is elemzi — két nevesített szegmens, VALÓS Python-számok + AI-próza, EGY bővített Claude-hívással.

**Architecture:** Az `elemzo.py` pipeline bővül egy **feltételes `youtube` blokkal**: két új tiszta Python-számoló (`_youtube_szamok`, `_youtube_het`) a `youtube_regresszio.json` + `youtube_nyers.json` fájlokból; az `epit_payload`/`_valasz_sema`/`valasz_to_artefakt` a `youtube` kulcsot CSAK akkor kezeli, ha van YouTube-adat (üres → a Google-út bájt-azonosan változatlan). A frontend (`elemzes.js`) a meglévő rendert egy „Google" szegmens-cím alá zárja, és `art.youtube` esetén egy „YouTube" szegmenst renderel a Google-csempe-render újrahasznosításával.

**Tech Stack:** Python 3 (stdlib json/datetime/pathlib), pytest; vanilla JS (docs/js), Playwright.

**Spec:** `docs/superpowers/specs/2026-08-25-elemzes-youtube-szegmens-design.md`

## Global Constraints

Minden taszk implicit követi ezeket (a [[working-style-gates]] memóriából):

- **Modell:** `claude-opus-4-8` (a meglévő elemzés-hívás bővítése, NEM új hívás).
- **SOROS suite:** `.venv/bin/python -m pytest -p no:xdist -q` és `npx playwright test --workers=1`.
- **TDD valódi RED:** minden implementáció ELŐTT bukó teszt, futtatva, a bukás oka igazolva.
- **Google-út regressziómentes:** a `valtozas`/`kulcsszavak`/`felkapott` payload- és artefakt-blokkok, valamint a meglévő `_kulcsszo_szamok`/`_kulcsszo_het`/`_felkapott`/`nap_diff` BÁJT-AZONOSAN változatlanok; a meglévő `tests/test_elemzo.py` tesztek VÁLTOZATLANUL zöldek.
- **Feltételes `youtube`:** üres/hiányzó YouTube-adatnál a `youtube` kulcs NEM kerül a payloadba/sémába/artefaktba → a Google-elemzés zavartalan (spec §10).
- **Jelölési fegyelem ([[naming-discipline]]):** VALÓS = Python-szám; az AI-próza mezőnevet/„payload"-ot NEM szivárogtat; ok-okozat csak óvatosan.
- **git add BY NAME** (soha `-A`/`.`); a ROOT `ATADAS-*.txt` SOHA nem kerül be. DOC-COMMIT (ez a terv) a kód-commitok ELŐTT.
- **A `docs/data/kulcsszo_*.json` (pótolhatatlan órás Google-adat) READ-ONLY.** Ez a feature nem ír adatot; nincs külön adat-commit.

---

### Task 1: `_youtube_szamok` — VALÓS kulcsszó-számok a YouTube-adatból

A leghosszabb ÉRVÉNYES regressziós intervallumból (a frontend `teljes_valaszt` mintája: legkorábbi `ablak_kezdet_utc`) irány/meredekség/érvényesség/mai_ertek; a csúcs/átlag a nyers HETI (12-m, legkorábbi kezdetű) sorozatból.

**Files:**
- Modify: `trendfigyelo/elemzo.py` (új privát segédek + `_youtube_szamok`)
- Test: `tests/test_elemzo.py` (új tesztek a fájl végén)

**Interfaces:**
- Produces:
  - `_nyers_heti_sorozat(youtube_nyers: dict, szo: str) -> dict | None` — a szó legkorábbi `ablak_kezdet_utc`-jű nyers sorozata (= a 12-m heti sáv), vagy `None`.
  - `_csucs_atlag(series: dict | None) -> tuple` — `(csucs, atlag)` a nem-részleges pontokból; `(None, None)` ha nincs.
  - `_yt_teljes_intervallum(rec: dict) -> dict | None` — a regressziós rekord leghosszabb érvényes intervalluma (legkorábbi `ablak_kezdet_utc`), vagy `None`.
  - `_youtube_szamok(youtube_regresszio: dict | None, youtube_nyers: dict | None) -> list` — szavanként `{szo, domen, irany, meredekseg, ervenyes, mai_ertek, csucs, atlag}`.

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/test_elemzo.py`:

```python
def _yt_reg_egy_szo():
    # 1_het érvénytelen (mint az éles youtube_regresszio-ban), 2_het és 1_ev érvényes;
    # a leghosszabb érvényes = 1_ev (legkorábbi ablak_kezdet_utc).
    return {"kulcsszavak": {"szorongás": {
        "domen": "egeszseg", "racs": "nap", "aktiv": True, "tipus": "szintmero",
        "intervallumok": {
            "1_het": {"ervenyes": False, "ok": "keves_pont"},
            "2_het": {"ervenyes": True, "irany": "csokken", "meredekseg_nap": -0.97,
                       "mai_ertek": 78, "ablak_kezdet_utc": "2026-08-11T00:00:00+00:00"},
            "1_ev": {"ervenyes": True, "irany": "novekszik", "meredekseg_nap": 0.05,
                      "mai_ertek": 43, "ablak_kezdet_utc": "2025-08-24T00:00:00+00:00"},
        }}}}


def _yt_nyers_egy_szo():
    # két sorozat: napi (3-m) + heti (12-m, legkorábbi kezdet) — a csúcs/átlag a hetiből jön
    return {"kulcsszavak": {"szorongás": [
        {"ablak_kezdet_utc": "2026-05-25T00:00:00+00:00", "ablak_veg_utc": "2026-08-25T00:00:00+00:00",
         "pontok": [{"idopont_utc": "2026-08-24T00:00:00+00:00", "ertek": 90, "reszleges": False}]},
        {"ablak_kezdet_utc": "2025-08-24T00:00:00+00:00", "ablak_veg_utc": "2026-08-23T00:00:00+00:00",
         "pontok": [{"idopont_utc": "2025-08-24T00:00:00+00:00", "ertek": 40, "reszleges": False},
                    {"idopont_utc": "2026-08-16T00:00:00+00:00", "ertek": 50, "reszleges": False},
                    {"idopont_utc": "2026-08-23T00:00:00+00:00", "ertek": 88, "reszleges": True}]},
    ]}}


def test_youtube_szamok_leghosszabb_ervenyes_intervallum_es_nyers_csucs_atlag():
    szamok = elemzo._youtube_szamok(_yt_reg_egy_szo(), _yt_nyers_egy_szo())
    assert len(szamok) == 1
    s = szamok[0]
    assert s["szo"] == "szorongás"
    assert s["domen"] == "egeszseg"
    # a leghosszabb ÉRVÉNYES = 1_ev (2025-08-24 a legkorábbi kezdet), NEM a 2_het
    assert s["irany"] == "novekszik"
    assert s["meredekseg"] == 0.05
    assert s["mai_ertek"] == 43
    assert s["ervenyes"] is True
    # csúcs/átlag a HETI nyers sorozatból, csak a nem-részleges pontok (40, 50; a 88 részleges kimarad)
    assert s["csucs"] == 50
    assert s["atlag"] == 45.0


def test_youtube_szamok_nincs_ervenyes_intervallum_fail_soft():
    reg = {"kulcsszavak": {"klíma": {"domen": "otthon", "intervallumok": {
        "1_het": {"ervenyes": False, "ok": "keves_pont"}}}}}
    szamok = elemzo._youtube_szamok(reg, {"kulcsszavak": {}})
    assert szamok[0]["szo"] == "klíma"
    assert szamok[0]["irany"] is None
    assert szamok[0]["ervenyes"] is False
    assert szamok[0]["csucs"] is None
    assert szamok[0]["atlag"] is None


def test_youtube_szamok_hianyzo_adat_ures_lista():
    assert elemzo._youtube_szamok(None, None) == []
    assert elemzo._youtube_szamok({}, {}) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -k youtube_szamok -p no:xdist -q`
Expected: FAIL with `AttributeError: module 'trendfigyelo.elemzo' has no attribute '_youtube_szamok'`

- [ ] **Step 3: Write the minimal implementation**

Add to `trendfigyelo/elemzo.py` (a `_kulcsszo_het` után, a `_felkapott` elé):

```python
def _nyers_heti_sorozat(youtube_nyers, szo):
    """A szó LEGKORÁBBI ablak_kezdetű nyers sorozata = a 12-m heti sáv (a legteljesebb tartomány)."""
    kw = (youtube_nyers or {}).get("kulcsszavak", {}) if isinstance(youtube_nyers, dict) else {}
    lista = kw.get(szo) or []
    if not lista:
        return None
    return min(lista, key=lambda s: s.get("ablak_kezdet_utc", ""))


def _csucs_atlag(series):
    pontok = (series or {}).get("pontok") or []
    ertekek = [p["ertek"] for p in pontok if not p.get("reszleges")]
    if not ertekek:
        return None, None
    return max(ertekek), round(sum(ertekek) / len(ertekek), 1)


def _yt_teljes_intervallum(rec):
    """A regressziós rekord leghosszabb ÉRVÉNYES intervalluma = legkorábbi ablak_kezdet_utc
    (a frontend teljes_valaszt mintája, app.js:290)."""
    ivk = (rec or {}).get("intervallumok", {})
    ervenyesek = [iv for iv in ivk.values() if iv.get("ervenyes") and iv.get("ablak_kezdet_utc")]
    if not ervenyesek:
        return None
    return min(ervenyesek, key=lambda iv: iv["ablak_kezdet_utc"])


def _youtube_szamok(youtube_regresszio, youtube_nyers):
    szavak = (youtube_regresszio or {}).get("kulcsszavak", {}) if isinstance(youtube_regresszio, dict) else {}
    ki = []
    for szo, rec in szavak.items():
        iv = _yt_teljes_intervallum(rec) or {}
        csucs, atlag = _csucs_atlag(_nyers_heti_sorozat(youtube_nyers, szo))
        ki.append({
            "szo": szo,
            "domen": rec.get("domen"),
            "irany": iv.get("irany"),
            "meredekseg": iv.get("meredekseg_nap"),
            "ervenyes": bool(iv.get("ervenyes")),
            "mai_ertek": iv.get("mai_ertek"),
            "csucs": csucs,
            "atlag": atlag,
        })
    return ki
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -k youtube_szamok -p no:xdist -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "feat(elemzo): _youtube_szamok — VALÓS YouTube kulcsszó-számok (leghosszabb érvényes IV + nyers csúcs/átlag)"
```

---

### Task 2: `_youtube_het` — heti mozgás a nyers heti sorozatból

Szavanként a legutóbbi lezárt heti pont változása az előzőhöz képest (a nyers heti sorozat utolsó két NEM-részleges pontja), abszolút változás szerint rendezve. YouTube-nál NINCS lánc — a heti mozgás közvetlenül a nyersből.

**Files:**
- Modify: `trendfigyelo/elemzo.py` (új `_youtube_het`)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: `_nyers_heti_sorozat` (Task 1).
- Produces: `_youtube_het(youtube_nyers: dict | None) -> dict` — `{"szavak": [{szo, kezdo, veg, valtozas}, ...]}`, `abs(valtozas)` szerint csökkenően.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_elemzo.py`:

```python
def test_youtube_het_utolso_ket_nem_reszleges_heti_pont():
    nyers = {"kulcsszavak": {
        "bitcoin": [
            {"ablak_kezdet_utc": "2025-08-24T00:00:00+00:00", "ablak_veg_utc": "2026-08-23T00:00:00+00:00",
             "pontok": [{"idopont_utc": "2026-08-09T00:00:00+00:00", "ertek": 30, "reszleges": False},
                        {"idopont_utc": "2026-08-16T00:00:00+00:00", "ertek": 57, "reszleges": False},
                        {"idopont_utc": "2026-08-23T00:00:00+00:00", "ertek": 99, "reszleges": True}]}],
        "mese": [
            {"ablak_kezdet_utc": "2025-08-24T00:00:00+00:00", "ablak_veg_utc": "2026-08-23T00:00:00+00:00",
             "pontok": [{"idopont_utc": "2026-08-09T00:00:00+00:00", "ertek": 90, "reszleges": False},
                        {"idopont_utc": "2026-08-16T00:00:00+00:00", "ertek": 95, "reszleges": False}]}],
    }}
    het = elemzo._youtube_het(nyers)
    szavak = {s["szo"]: s for s in het["szavak"]}
    # a részleges (2026-08-23) pont kimarad → az utolsó két lezárt: 30 → 57
    assert szavak["bitcoin"]["kezdo"] == 30
    assert szavak["bitcoin"]["veg"] == 57
    assert szavak["bitcoin"]["valtozas"] == 27
    assert szavak["mese"]["valtozas"] == 5
    # rendezés: a nagyobb abszolút mozgó elöl
    assert het["szavak"][0]["szo"] == "bitcoin"


def test_youtube_het_keves_pont_kimarad():
    nyers = {"kulcsszavak": {"klíma": [
        {"ablak_kezdet_utc": "2025-08-24T00:00:00+00:00", "ablak_veg_utc": "2026-08-23T00:00:00+00:00",
         "pontok": [{"idopont_utc": "2026-08-16T00:00:00+00:00", "ertek": 7, "reszleges": False}]}]}}
    assert elemzo._youtube_het(nyers)["szavak"] == []


def test_youtube_het_hianyzo_adat():
    assert elemzo._youtube_het(None) == {"szavak": []}
    assert elemzo._youtube_het({}) == {"szavak": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -k youtube_het -p no:xdist -q`
Expected: FAIL with `AttributeError: ... '_youtube_het'`

- [ ] **Step 3: Write the minimal implementation**

Add to `trendfigyelo/elemzo.py` (a `_youtube_szamok` után):

```python
def _youtube_het(youtube_nyers):
    kw = (youtube_nyers or {}).get("kulcsszavak", {}) if isinstance(youtube_nyers, dict) else {}
    szavak = []
    for szo in kw:
        pontok = [p for p in ((_nyers_heti_sorozat(youtube_nyers, szo) or {}).get("pontok") or [])
                  if not p.get("reszleges")]
        if len(pontok) < 2:
            continue
        kezdo, veg = round(pontok[-2]["ertek"], 1), round(pontok[-1]["ertek"], 1)
        szavak.append({"szo": szo, "kezdo": kezdo, "veg": veg, "valtozas": round(veg - kezdo, 1)})
    szavak.sort(key=lambda s: -abs(s["valtozas"]))
    return {"szavak": szavak}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -k youtube_het -p no:xdist -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "feat(elemzo): _youtube_het — heti mozgás a nyers heti sorozatból (lánc nélkül)"
```

---

### Task 3: `epit_payload` feltételes `youtube` kulcs + `futtat` betölti a YouTube-adatot

A payload egy `youtube` kulccsal bővül CSAK ha van YouTube-szám (üres → nincs kulcs → Google-út bájt-azonos). A `futtat` betölti a két YouTube-fájlt az `adatok`-ba.

**Files:**
- Modify: `trendfigyelo/elemzo.py` (`epit_payload`, `futtat`)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: `_youtube_szamok`, `_youtube_het` (Task 1–2).
- Produces: `epit_payload(...)` — ha van YouTube-adat, a visszatérés tartalmaz `"youtube": {"szamok": [...], "het_valos": [...]}` kulcsot; egyébként NEM. A `futtat` az `adatok`-ba `"youtube_regresszio"` és `"youtube_nyers"` kulcsokat tölt.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_elemzo.py` (a `_yt_reg_egy_szo()` és `_yt_nyers_egy_szo()` segédeket a Task 1 már a fájlba tette — ezeket használjuk):

```python
def test_epit_payload_youtube_kulcs_ha_van_adat():
    adatok = {
        "regresszio": _regresszio_egy_szo("emelkedik", 1.0, True, 10.0),
        "tortenet": {"napok": []}, "legfrissebb": {"top_trendek": []}, "napok_trendek": {},
        "youtube_regresszio": _yt_reg_egy_szo(), "youtube_nyers": _yt_nyers_egy_szo(),
    }
    payload = elemzo.epit_payload(adatok)
    assert "youtube" in payload
    assert payload["youtube"]["szamok"][0]["szo"] == "szorongás"
    assert "het_valos" in payload["youtube"]
    # a Google-kulcsok VÁLTOZATLANOK
    assert payload["kulcsszavak"]["szamok"][0]["szo"] == "állás"


def test_epit_payload_nincs_youtube_kulcs_ha_nincs_adat():
    adatok = {"regresszio": _regresszio_egy_szo("emelkedik", 1.0, True, 10.0),
              "tortenet": {"napok": []}, "legfrissebb": {"top_trendek": []}, "napok_trendek": {}}
    payload = elemzo.epit_payload(adatok)
    assert "youtube" not in payload
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -k "epit_payload_youtube or epit_payload_nincs_youtube" -p no:xdist -q`
Expected: FAIL — `assert "youtube" in payload` (KeyError-mentes, de a kulcs hiányzik)

- [ ] **Step 3: Write the minimal implementation**

In `trendfigyelo/elemzo.py`, `epit_payload` végén cseréld a `return {...}`-t erre:

```python
def epit_payload(adatok, tegnapi_szamok=None, tegnapi_top=None):
    regresszio = adatok.get("regresszio", {})
    tortenet = adatok.get("tortenet", {})
    szamok = _kulcsszo_szamok(regresszio, tortenet)
    felkapott = _felkapott(adatok.get("legfrissebb", {}), adatok.get("napok_trendek", {}))
    valtozas = nap_diff(szamok, tegnapi_szamok, felkapott["top"], tegnapi_top)
    payload = {
        "kulcsszavak": {"szamok": szamok},
        "felkapott": felkapott,
        "valtozas": valtozas,
        "kulcsszo_het": _kulcsszo_het(adatok.get("lanc", {})),
    }
    yt_szamok = _youtube_szamok(adatok.get("youtube_regresszio"), adatok.get("youtube_nyers"))
    if yt_szamok:
        payload["youtube"] = {"szamok": yt_szamok,
                              "het_valos": _youtube_het(adatok.get("youtube_nyers"))["szavak"]}
    return payload
```

In `futtat`, bővítsd az `adatok` dictet a két új betöltéssel:

```python
    adatok = {
        "regresszio": _betolt(docs_data / "kulcsszo_regresszio.json") or {},
        "tortenet": _betolt(docs_data / "tortenet.json") or {},
        "legfrissebb": _betolt(docs_data / "legfrissebb.json") or {},
        "napok_trendek": _utolso_napok_trendek(docs_data),
        "lanc": _betolt(docs_data / "kulcsszo_lanc.json") or {},
        "youtube_regresszio": _betolt(docs_data / "youtube_regresszio.json"),
        "youtube_nyers": _betolt(docs_data / "youtube_nyers.json"),
    }
```

- [ ] **Step 4: Run the FULL elemzo suite to verify pass + no regression**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -p no:xdist -q`
Expected: PASS (minden korábbi teszt + az újak; a Google-út érintetlen)

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "feat(elemzo): epit_payload feltételes youtube kulcs + futtat betölti a youtube_regresszio/nyers fájlt"
```

---

### Task 4: `_valasz_sema(youtube)` + `RENDSZER_PROMPT` YouTube-keret + kliens séma-a-payloadból

A séma feltételesen kap egy `youtube` próza-szekció-csoportot (`napi`/`teljes_kep`/`het`); a valódi kliens a payload jelenlétéből dönti el, kér-e YouTube-prózát. A rendszerprompt rövid YouTube-fogalmi kerettel bővül (a tiltások változatlanul rá is állnak).

**Files:**
- Modify: `trendfigyelo/elemzo.py` (`_valasz_sema`, `RENDSZER_PROMPT`, `_AnthropicKliens.uzenet`)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Produces: `_valasz_sema(youtube: bool = False) -> dict` — `youtube=True` esetén a `required` és `properties` tartalmaz egy szigorú `youtube` szekció-csoportot (`{napi, teljes_kep, het}`, mind `{szoveg}`, `additionalProperties: False`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_elemzo.py`:

```python
def test_valasz_sema_google_alap_valtozatlan():
    s = elemzo._valasz_sema()
    assert set(s["required"]) == {"valtozas", "kulcsszavak", "felkapott"}
    assert "youtube" not in s["properties"]


def test_valasz_sema_youtube_szekcio_szigoru():
    s = elemzo._valasz_sema(youtube=True)
    assert "youtube" in s["required"]
    yt = s["properties"]["youtube"]
    assert yt["additionalProperties"] is False
    assert set(yt["required"]) == {"napi", "teljes_kep", "het"}
    assert set(yt["properties"]["napi"]["properties"]) == {"szoveg"}


def test_rendszer_prompt_youtube_keret():
    p = elemzo.RENDSZER_PROMPT.lower()
    assert "youtube" in p                 # a YouTube-keret jelen van
    assert "payload" in p and "mező" in p  # a meglévő tiltások VÁLTOZATLANUL érvényben
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -k "valasz_sema or rendszer_prompt_youtube" -p no:xdist -q`
Expected: FAIL — `_valasz_sema() got ... youtube` / `"youtube" in p` bukik

- [ ] **Step 3: Write the minimal implementation**

In `trendfigyelo/elemzo.py`, cseréld a `_valasz_sema`-t:

```python
def _valasz_sema(youtube=False):
    sz = _szekcio_sema()
    props = {
        "valtozas": sz,
        "kulcsszavak": {"type": "object", "additionalProperties": False,
                        "required": ["napi", "teljes_kep", "het"],
                        "properties": {"napi": sz, "teljes_kep": sz, "het": sz}},
        "felkapott": {"type": "object", "additionalProperties": False,
                      "required": ["napi", "het"],
                      "properties": {"napi": sz, "het": sz}},
    }
    required = ["valtozas", "kulcsszavak", "felkapott"]
    if youtube:
        props["youtube"] = {"type": "object", "additionalProperties": False,
                            "required": ["napi", "teljes_kep", "het"],
                            "properties": {"napi": sz, "teljes_kep": sz, "het": sz}}
        required = required + ["youtube"]
    return {"type": "object", "additionalProperties": False,
            "required": required, "properties": props}
```

Bővítsd a `RENDSZER_PROMPT` végét (a `(6) ...leszűrni."` után, a záró `)` elé) ezzel a mondattal:

```python
    "(7) Ha a bemenet YouTube-szegmenst is tartalmaz: az a magyarországi YouTube-keresések "
    "videó-igénye (NEM a webes keresés), a videós figyelem közelítése. A YouTube-szavak "
    "egymással NEM összemérhetők, mert mindegyik saját 0–100 skálán mozog — ne rangsorold "
    "őket egymáshoz. UGYANEZEK a szabályok (folyó bekezdés, mezőnév/„payload\" tilalma, "
    "óvatos ok-okozat) érvényesek a YouTube-prózára is."
```

In `_AnthropicKliens.uzenet`, a séma legyen a payloadtól függő:

```python
            output_config={"effort": "medium",
                           "format": {"type": "json_schema",
                                      "schema": _valasz_sema(youtube="youtube" in payload)}},
```

- [ ] **Step 4: Run the FULL elemzo suite**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -p no:xdist -q`
Expected: PASS (a `test_rendszer_prompt_folyo_proza_es_tiltas` VÁLTOZATLANUL zöld — a tiltó szavak megmaradtak)

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "feat(elemzo): _valasz_sema feltételes youtube szekció + RENDSZER_PROMPT YouTube-keret + kliens séma-a-payloadból"
```

---

### Task 5: `valasz_to_artefakt` feltételes `youtube` blokk

Az artefakt egy `youtube` blokkal bővül CSAK ha a payload tartalmaz `youtube`-ot: VALÓS `szamok`/`het_valos` a payloadból, `napi`/`teljes_kep`/`het` próza az AI-válaszból.

**Files:**
- Modify: `trendfigyelo/elemzo.py` (`valasz_to_artefakt`)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Produces: `valasz_to_artefakt(...)` — ha `"youtube" in payload`, a visszatérés tartalmaz `art["youtube"] = {szamok, het_valos, napi, teljes_kep, het}`; egyébként NEM (a Google-artefakt bájt-azonos).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_elemzo.py`:

```python
def _ai_valasz_youtubebal():
    sz = {"szoveg": "sz"}
    return {"valtozas": sz, "kulcsszavak": {"napi": sz, "teljes_kep": sz, "het": sz},
            "felkapott": {"napi": sz, "het": sz},
            "youtube": {"napi": {"szoveg": "yt-napi"}, "teljes_kep": {"szoveg": "yt-teljes"},
                        "het": {"szoveg": "yt-het"}}}


def test_valasz_to_artefakt_youtube_blokk_valos_es_ai():
    payload = {
        "kulcsszavak": {"szamok": []},
        "felkapott": {"top": [], "het": {"napok": 0, "visszateroek": []}},
        "valtozas": {"irany_valtok": [], "mozgok": [], "felkapott_uj": [], "felkapott_eltunt": [], "van_elozo": False},
        "youtube": {"szamok": [{"szo": "szorongás", "domen": "egeszseg", "irany": "novekszik",
                                "meredekseg": 0.05, "ervenyes": True, "mai_ertek": 43, "csucs": 50, "atlag": 45.0}],
                    "het_valos": [{"szo": "bitcoin", "kezdo": 30, "veg": 57, "valtozas": 27}]},
    }
    art = elemzo.valasz_to_artefakt(_ai_valasz_youtubebal(), payload, nap="2026-08-26", modell="claude-opus-4-8")
    # VALÓS a payloadból
    assert art["youtube"]["szamok"][0]["csucs"] == 50
    assert art["youtube"]["het_valos"][0]["valtozas"] == 27
    # AI-próza a válaszból
    assert art["youtube"]["napi"]["szoveg"] == "yt-napi"
    assert art["youtube"]["teljes_kep"]["szoveg"] == "yt-teljes"
    assert art["youtube"]["het"]["szoveg"] == "yt-het"


def test_valasz_to_artefakt_nincs_youtube_ha_nincs_payloadban():
    payload = _mini_payload(van_elozo=True)   # nincs "youtube" kulcs
    art = elemzo.valasz_to_artefakt(_mini_ai("napi"), payload, nap="2026-08-26", modell="claude-opus-4-8")
    assert "youtube" not in art
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -k "valasz_to_artefakt_youtube or valasz_to_artefakt_nincs_youtube" -p no:xdist -q`
Expected: FAIL — `KeyError: 'youtube'` (art nem tartalmazza)

- [ ] **Step 3: Write the minimal implementation**

In `trendfigyelo/elemzo.py`, `valasz_to_artefakt` — a `return {...}` helyett építs egy változót és told hozzá a youtube blokkot:

```python
def valasz_to_artefakt(ai_valasz, payload, nap, modell):
    valtozas_szoveg = ai_valasz["valtozas"]["szoveg"]
    if not payload["valtozas"].get("van_elozo"):
        valtozas_szoveg = ("Ma nincs korábbi nap, amivel összevethetnénk, így a napi "
                           "elmozdulás egyelőre nem értékelhető. A friss kép a lenti "
                           "szekciókban olvasható.")
    art = {
        "frissitve": seged.idopont_iso(seged.most_utc()),
        "modell": modell,
        "nap": nap,
        "valtozas": {"diff": payload["valtozas"], "szoveg": valtozas_szoveg},
        "kulcsszavak": {
            "szamok": payload["kulcsszavak"]["szamok"],
            "napi": ai_valasz["kulcsszavak"]["napi"],
            "teljes_kep": ai_valasz["kulcsszavak"]["teljes_kep"],
            "het": ai_valasz["kulcsszavak"]["het"],
        },
        "felkapott": {
            "top": payload["felkapott"]["top"],
            "napi": ai_valasz["felkapott"]["napi"],
            "het": ai_valasz["felkapott"]["het"],
            "het_valos": payload["felkapott"]["het"],
        },
    }
    if "youtube" in payload:
        art["youtube"] = {
            "szamok": payload["youtube"]["szamok"],
            "het_valos": payload["youtube"]["het_valos"],
            "napi": ai_valasz["youtube"]["napi"],
            "teljes_kep": ai_valasz["youtube"]["teljes_kep"],
            "het": ai_valasz["youtube"]["het"],
        }
    return art
```

- [ ] **Step 4: Run the FULL elemzo suite**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -p no:xdist -q`
Expected: PASS (a Google-artefakt tesztek — pl. `test_valasz_to_artefakt_valos_reteg_es_ai_narrativa` — VÁLTOZATLANUL zöldek)

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "feat(elemzo): valasz_to_artefakt feltételes youtube blokk (VALÓS payload + AI próza)"
```

---

### Task 6: Frontend — két szegmens-cím + YouTube-szegmens render (elemzes.js + elemzes.html)

A meglévő render egy „Google keresések napi elemzése" `<h2>` alá kerül; `art.youtube` esetén egy „YouTube keresések napi elemzése" `<h2>` + VALÓS csempék (a `valos_kulcsszo_csempek` újrahasznosításával) + 3 AI-szekció renderel. Régi archív-nap (nincs `youtube`) → nincs YouTube-szegmens.

**Files:**
- Modify: `docs/js/elemzes.js` (`rajzol` + két új segéd)
- Test: `e2e/elemzes.spec.js` (új tesztek)

**Interfaces:**
- Consumes: `valos_kulcsszo_csempek`, `szekcio_elem` (meglévő, elemzes.js).
- Produces: DOM — `h2.elemzes-szegmens` szegmens-címek; `art.youtube` esetén `#youtube-szegmens` konténer a YouTube-csempékkel és 3 szekcióval.

- [ ] **Step 1: Write the failing Playwright tests**

Add to `e2e/elemzes.spec.js` (a meglévő fájl végén, a záró sor után):

```javascript
const FIXTURE_YT = Object.assign({}, FIXTURE, {
  youtube: {
    szamok: [{ szo: "szorongás", domen: "egeszseg", irany: "novekszik", meredekseg: 0.05,
               ervenyes: true, mai_ertek: 43, csucs: 50, atlag: 45.0 }],
    het_valos: [{ szo: "bitcoin", kezdo: 30, veg: 57, valtozas: 27 }],
    napi: { szoveg: "YouTube napi próza." },
    teljes_kep: { szoveg: "YouTube teljes kép." },
    het: { szoveg: "YouTube heti mozgás." },
  },
});

test("Elemzés: két nevesített szegmens + YouTube-csempék és 3 szekció, ha van youtube blokk", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: FIXTURE_YT }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  // két szegmens-cím
  await expect(page.locator("h2.elemzes-szegmens")).toHaveText([
    "Google keresések napi elemzése", "YouTube keresések napi elemzése"]);
  // YouTube VALÓS csempe a szóval + iránnyal
  await expect(page.locator("#youtube-szegmens .elemzes-csempe")).toContainText("szorongás");
  // 3 YouTube AI-szekció renderel (folyó próza <p>-ként)
  await expect(page.locator("#youtube-szegmens .elemzes-szekcio")).toHaveCount(3);
  await expect(page.locator("#youtube-szegmens")).toContainText("YouTube napi próza.");
});

test("Elemzés: régi archív-nap (nincs youtube blokk) → nincs YouTube-szegmens, a Google-rész ép", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: FIXTURE }));  // nincs youtube
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator("#youtube-szegmens")).toHaveCount(0);
  await expect(page.locator("h2.elemzes-szegmens")).toHaveText(["Google keresések napi elemzése"]);
  await expect(page.locator(".elemzes-csempe")).toContainText("állás");   // Google-rész változatlan
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx playwright test e2e/elemzes.spec.js --workers=1`
Expected: FAIL — `h2.elemzes-szegmens` count 0, `#youtube-szegmens` nem létezik

- [ ] **Step 3: Write the minimal implementation**

In `docs/js/elemzes.js`, add two helpers a `rajzol` fölé:

```javascript
// egy nevesített szegmens-cím (Google / YouTube)
function szegmens_cim(szoveg) {
  const h = document.createElement("h2");
  h.className = "elemzes-szegmens";
  h.textContent = szoveg;
  return h;
}

// YouTube-szegmens: VALÓS csempék (a Google-render újrahasznosításával) + 3 AI-szekció
function youtube_szegmens(yt) {
  const box = document.createElement("section");
  box.id = "youtube-szegmens";
  box.appendChild(szegmens_cim("YouTube keresések napi elemzése"));
  box.appendChild(valos_kulcsszo_csempek(yt.szamok));
  box.appendChild(szekcio_elem("YouTube — mit néznek ma", yt.napi));
  box.appendChild(szekcio_elem("YouTube — teljes kép", yt.teljes_kep));
  box.appendChild(szekcio_elem("YouTube — heti mozgás", yt.het));
  return box;
}
```

Then in `rajzol(art)`, a `document.getElementById("elemzes-fejlec")...` sor UTÁN told be a Google szegmens-címet, és a függvény VÉGÉRE a YouTube-szegmenst:

```javascript
  document.getElementById("elemzes-fejlec").textContent =
    `Elemzés — ${art.nap} (${art.modell})`;

  t.appendChild(szegmens_cim("Google keresések napi elemzése"));

  // Mi változott ma? — a szekció (folyó AI-próza) ELŐBB, a VALÓS diff-összegzés
```

...(a meglévő törzs változatlan)... és a `rajzol` legutolsó sora (`t.appendChild(szekcio_elem("Felkapott — heti összesítés", art.felkapott.het));`) UTÁN:

```javascript
  // YouTube-szegmens — fail-soft: régi archív-nap (nincs art.youtube) → nincs YouTube-rész
  if (art.youtube) t.appendChild(youtube_szegmens(art.youtube));
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test e2e/elemzes.spec.js --workers=1`
Expected: PASS (a két új teszt + a két meglévő elemzés-teszt zöld)

- [ ] **Step 5: Commit**

```bash
git add docs/js/elemzes.js e2e/elemzes.spec.js
git commit -m "feat(elemzes-ui): két nevesített szegmens + YouTube-szegmens render (VALÓS csempék + 3 AI-szekció)"
```

---

### Task 7: Teljes suite-kapu + leltár + memória

A teljes SOROS suite zöld (Python + Playwright), a leltár és a memória frissítve. Nincs kód-változás, csak igazolás + dokumentáció.

**Files:**
- Modify: `docs/superpowers/leltar.md`
- Modify: `/home/goszt/.claude/projects/-home-goszt-trendfigyelo/memory/elemzes-youtube-szegmens.md` (+ MEMORY.md index)

- [ ] **Step 1: Run the FULL Python suite (SOROS)**

Run: `.venv/bin/python -m pytest -p no:xdist -q`
Expected: minden zöld (a `test_elemzo.py` bővült; a Google-út érintetlen).

- [ ] **Step 2: Run the FULL Playwright suite (SOROS)**

Run: `npx playwright test --workers=1`
Expected: minden zöld (az `elemzes.spec.js` bővült; menu/dashboard érintetlen).
> Megjegyzés: a `TELJES-NEZET-FLAKE` (`e2e/kulcsszo.spec.js:555`, parkolt, feature-független) ha felbukkan, izolált újrafuttatással igazold, hogy nem a mostani változás okozza.

- [ ] **Step 3: Fizikai leltár-mérés**

Mérd meg a tényleges teszt-darabszámokat:

Run: `.venv/bin/python -m pytest -p no:xdist -q --collect-only | tail -1` és `npx playwright test --list --workers=1 | tail -5`
Ezekből vezesd le a leltár-deltát (elemzo-tesztek +N, elemzes e2e +2). NE tippelj — a mért számot írd be.

- [ ] **Step 4: Update leltár + memória**

- `docs/superpowers/leltar.md`: új sor „ELEMZES-YOUTUBE-SZEGMENS LESZÁLLÍTVA" + delta-log a mért törzs/kész számokkal + invariáns.
- Memória `elemzes-youtube-szegmens.md`: állapot → LESZÁLLÍTVA (commit-hash-ekkel), a KÖVETKEZŐ mező törölve/aktualizálva; MEMORY.md sor frissítve.

- [ ] **Step 5: Commit (DOC)**

```bash
git add docs/superpowers/leltar.md
git commit -m "doc(leltar): ELEMZES-YOUTUBE-SZEGMENS leszállítva — teljes SOROS suite zöld, invariáns mérve"
```

(A memória-fájlok a `~/.claude/...` alatt vannak, NEM a repóban — külön Write, nem git.)

---

## Végső lépések (a taszkok után, subagent-driven záró review)

1. **superpowers:requesting-code-review** — a teljes branch átnézése (a code-reviewer.md szerint), különös figyelemmel: a Google-út bájt-azonossága; a feltételes `youtube` minden ponton konzisztens; a jelölési fegyelem a prózán.
2. **Élő előnézet** ([[eloUI-preview-workflow]]): a `_youtube_szamok`/`_youtube_het` valós `youtube_regresszio.json`+`youtube_nyers.json`-ból regenerált `elemzes.json`-nal localhost:8000-en — a két szegmens és a YouTube-csempék ellenőrzése, a docs/data szennyezése NÉLKÜL (git checkout utána).
3. **Push** — külön gated kör (fetch → divergencia → sync → push → `rev-list 0 0`), USER-jóváhagyással.
4. Az első ÉLES `elemzes.yml` futásnál FIGYELEM: a bővített Opus-hívás YouTube-prózát is ír; a fail-soft (API-hiba → régi `elemzes.json` marad) fedi mindkét szegmenst.
