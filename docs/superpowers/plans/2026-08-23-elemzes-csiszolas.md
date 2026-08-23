# ELEMZÉS-CSISZOLÁS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A napi AI-elemzés kimenetét folyó prózává, mezőnév-szivárgás nélkülivé és Opus-alapúvá tenni, a `kulcsszo_het` szekciót valós heti pályával feltölteni, és az elrendezést kétoszlopossá (naptár bal / elemzés jobb) alakítani.

**Architecture:** A backend (`trendfigyelo/elemzo.py`) továbbra is MINDEN számot Pythonban számol; az AI csak narratívát ír. A szekció-séma egyszerűsödik (csak `szoveg`), a prompt tiltja a mezőnév-/„payload"-szivárgást és folyó bekezdéseket kér, a `kulcsszo_het` a láncból számolt valós trajektóriát kap, az üres-nap „mi változott ma" szövegét Python birtokolja. A frontend (`docs/js/elemzes.js`, `docs/elemzes.html`, `docs/css/app.css`) prózát renderel `<p>`-ként és kétoszlopos gridbe rendezi a naptárt és a tartalmat.

**Tech Stack:** Python 3 (stdlib `datetime`, `json`; `anthropic` SDK a varratban, tesztben nem hívva), pytest; statikus JS (ES5-stílus, `textContent`), CSS grid; Playwright e2e.

**Spec:** `docs/superpowers/specs/2026-08-23-elemzes-csiszolas-design.md`

## Global Constraints

- MINDEN szám Pythonból; az AI SOHA nem talál ki számot (spec §1.1). Az új `kulcsszo_het` heti pálya is Pythonból jön.
- Fail-soft VÁLTOZATLAN: `futtat` a `try` csak az `elemez` köré; API-hibán a `return 2` és az előző `elemzes.json` bit-azonosan marad (spec §1.2).
- A pótolhatatlan `kulcsszo_lanc.json` CSAK OLVASVA. `git add` MINDIG NÉVVEL (soha `-A`/`.`); a ROOT `ATADAS-2026-08-18.txt`-t SOHA ne add-eld.
- Suite SOROS: `.venv/bin/pytest -q` + `npx playwright test --workers=1`. Végállapot: MUTÁCIÓ marad PONTOSAN 1 (`grep -rn "MUTÁCIÓ" docs/js docs/css e2e tests trendfigyelo` == 1).
- TDD VALÓDI RED-del: a „futtasd, hogy elhasaljon" lépésben a LITERÁL pytest-kimenetet kell beilleszteni; előrejelzett/„(vár)"-jelölt RED = ELUTASÍTVA. A RED viselkedési legyen (KeyError/AssertionError), ne Import/Name.
- Minden commit üzenet magyar, és a záró két sor KÖTELEZŐ:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_b0499378-8d8f-4c2a-bf75-ee09b94f1751
  ```
- A DOC-COMMIT (spec) MÁR MEGTÖRTÉNT (`41d3260`). Nincs adat-commit ebben a tervben.

## File Structure

- `trendfigyelo/elemzo.py` — MODIFY: új `_kulcsszo_het(lanc)`; `_szekcio_sema` egyszerűsítés; `RENDSZER_PROMPT` újraírás; `MODELL` → Opus; `epit_payload` + `futtat` láncbekötés; `valasz_to_artefakt` üres-nap felülírás.
- `tests/test_elemzo.py` — MODIFY: új tesztek a fentiekre.
- `docs/js/elemzes.js` — MODIFY: `szekcio_elem` próza-render; a `diffOsszegzes` csak `van_elozo`-ra.
- `docs/elemzes.html` — nincs strukturális változás szükséges (a grid a `#elemzes` két gyerekére hat forrás-sorrendben); csak akkor módosul, ha a Task 6 mégis igényli.
- `docs/css/app.css` — MODIFY: `#elemzes` grid; `#elemzes-naptar` a bal oszlopban; `.elemzes-szoveg` sorköz; mobil media query.
- `e2e/elemzes.spec.js` — MODIFY: fixture új alak; próza-/réteg-asszertek; új elrendezés-teszt.

---

### Task 1: `_kulcsszo_het(lanc)` — valós heti pálya a láncból

**Files:**
- Modify: `trendfigyelo/elemzo.py` (új modul-szintű konstans + függvény, a `_felkapott` közelébe)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Produces: `_kulcsszo_het(lanc: dict) -> {"ablak_napok": int, "szavak": [{"szo": str, "kezdo": num, "veg": num, "valtozas": num, "min": num, "max": num}, ...]}`. A `lanc` a `kulcsszo_lanc.json` teljes dictje (`{"kulcsszavak": {szo: {"pontok": [{"idopont_utc","ertek"}, ...]}}}`). A `szavak` a `valtozas` abszolút értéke szerint csökkenőn rendezett. Modul-konstans: `HET_ABLAK_NAPOK = 7`.

- [ ] **Step 1: Írd meg a bukó teszteket**

`tests/test_elemzo.py`-hoz add hozzá (a meglévő importok mellé kell `from trendfigyelo import elemzo`, ha még nincs):

```python
def test_kulcsszo_het_valos_palya():
    lanc = {"kulcsszavak": {
        "állás": {"ablak_kezdet_utc": "2026-08-01T00:00:00+00:00",
                   "ablak_veg_utc": "2026-08-22T18:00:00+00:00",
                   "pontok": [
                       {"idopont_utc": "2026-08-14T18:00:00+00:00", "ertek": 40},  # ablakon KÍVÜL (< 08-15T18:00)
                       {"idopont_utc": "2026-08-15T18:00:00+00:00", "ertek": 42},  # ablak eleje = kezdo
                       {"idopont_utc": "2026-08-18T18:00:00+00:00", "ertek": 55},  # max
                       {"idopont_utc": "2026-08-22T18:00:00+00:00", "ertek": 51},  # veg
                   ]},
        "tüntetés": {"ablak_kezdet_utc": "2026-08-01T00:00:00+00:00",
                      "ablak_veg_utc": "2026-08-17T18:00:00+00:00",
                      "pontok": [
                          {"idopont_utc": "2026-08-16T18:00:00+00:00", "ertek": 5},
                          {"idopont_utc": "2026-08-17T18:00:00+00:00", "ertek": 0},  # elavult vég → KIMARAD
                      ]},
    }}
    ki = elemzo._kulcsszo_het(lanc)
    assert ki["ablak_napok"] == 7
    assert [s["szo"] for s in ki["szavak"]] == ["állás"]   # a szakasz-törött tüntetés kimaradt
    allas = ki["szavak"][0]
    assert allas["kezdo"] == 42     # az ablak első pontja (08-15); a 08-14 KÍVÜL van
    assert allas["veg"] == 51
    assert allas["valtozas"] == 9   # 51 - 42
    assert allas["min"] == 42
    assert allas["max"] == 55


def test_kulcsszo_het_ures_lanc():
    assert elemzo._kulcsszo_het({}) == {"ablak_napok": 7, "szavak": []}
    assert elemzo._kulcsszo_het({"kulcsszavak": {}}) == {"ablak_napok": 7, "szavak": []}
```

- [ ] **Step 2: Futtasd, hogy elhasaljon (LITERÁL kimenet kötelező)**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_kulcsszo_het_valos_palya tests/test_elemzo.py::test_kulcsszo_het_ures_lanc -q`
Expected: FAIL — `AttributeError: module 'trendfigyelo.elemzo' has no attribute '_kulcsszo_het'`. Illeszd be a TELJES, tényleges pytest-kimenetet (előrejelzés = elutasítva).

- [ ] **Step 3: Írd meg a minimális implementációt**

`trendfigyelo/elemzo.py` — a fájl tetején a meglévő `from pathlib import Path` mellé: `from datetime import datetime, timedelta`. A `_felkapott` fölé vagy alá:

```python
HET_ABLAK_NAPOK = 7


def _kulcsszo_het(lanc):
    """A lánc utolsó HET_ABLAK_NAPOK napos ablakából valós heti pálya szavanként.
    A szakasz-törött (elavult végű) szavak kimaradnak — így a ~12 egészséges szó marad."""
    szavak_dict = (lanc or {}).get("kulcsszavak", {}) if isinstance(lanc, dict) else {}

    def _veg(rec):
        p = (rec or {}).get("pontok") or []
        return p[-1]["idopont_utc"] if p else None

    vegek = [v for v in (_veg(r) for r in szavak_dict.values()) if v]
    if not vegek:
        return {"ablak_napok": HET_ABLAK_NAPOK, "szavak": []}
    anchor = max(datetime.fromisoformat(v) for v in vegek)
    ablak_kezdet = anchor - timedelta(days=HET_ABLAK_NAPOK)
    frissessegi_kuszob = anchor - timedelta(days=1)   # ennél régebbi vég = szakasz-törött → kimarad
    szavak = []
    for szo, rec in szavak_dict.items():
        pontok = (rec or {}).get("pontok") or []
        if not pontok:
            continue
        if datetime.fromisoformat(pontok[-1]["idopont_utc"]) < frissessegi_kuszob:
            continue
        ablakban = [pt for pt in pontok
                    if datetime.fromisoformat(pt["idopont_utc"]) >= ablak_kezdet]
        if not ablakban:
            continue
        ertekek = [pt["ertek"] for pt in ablakban]
        kezdo, veg = round(ertekek[0], 1), round(ertekek[-1], 1)
        szavak.append({"szo": szo, "kezdo": kezdo, "veg": veg,
                       "valtozas": round(veg - kezdo, 1),
                       "min": round(min(ertekek), 1), "max": round(max(ertekek), 1)})
    szavak.sort(key=lambda s: -abs(s["valtozas"]))
    return {"ablak_napok": HET_ABLAK_NAPOK, "szavak": szavak}
```

- [ ] **Step 4: Futtasd, hogy zöld legyen**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_kulcsszo_het_valos_palya tests/test_elemzo.py::test_kulcsszo_het_ures_lanc -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -F - <<'EOF'
feat(elemzo): _kulcsszo_het — valós heti pálya a láncból (szakasz-törött szó kimarad)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_b0499378-8d8f-4c2a-bf75-ee09b94f1751
EOF
```

---

### Task 2: Séma-egyszerűsítés + prompt-újraírás + Opus modell

**Files:**
- Modify: `trendfigyelo/elemzo.py:17` (`MODELL`), `:19-28` (`RENDSZER_PROMPT`), `_szekcio_sema` (`:128-133`)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Produces: `_szekcio_sema() -> {"type":"object","additionalProperties":False,"required":["szoveg"],"properties":{"szoveg":{"type":"string"}}}`. `MODELL == "claude-opus-4-8"`. `RENDSZER_PROMPT` tiltja a mezőnév-/„payload"-szivárgást és folyó bekezdéseket kér.
- Consumes: semmi Task 1-ből (független).

- [ ] **Step 1: Írd meg a bukó teszteket**

```python
def test_szekcio_sema_csak_szoveg():
    s = elemzo._szekcio_sema()
    assert s["required"] == ["szoveg"]
    assert set(s["properties"]) == {"szoveg"}
    assert "megfigyelesek" not in s["properties"]
    assert "elmeleti" not in s["properties"]


def test_modell_opus():
    assert elemzo.MODELL == "claude-opus-4-8"


def test_rendszer_prompt_folyo_proza_es_tiltas():
    p = elemzo.RENDSZER_PROMPT.lower()
    assert "bekezdés" in p          # folyó bekezdéseket kér
    assert "payload" in p           # explicit tiltja a „payload" szót
    assert "mező" in p              # tiltja a mezőnév-hivatkozást
```

- [ ] **Step 2: Futtasd, hogy elhasaljon (LITERÁL kimenet kötelező)**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_szekcio_sema_csak_szoveg tests/test_elemzo.py::test_modell_opus tests/test_elemzo.py::test_rendszer_prompt_folyo_proza_es_tiltas -q`
Expected: FAIL — `test_szekcio_sema_csak_szoveg` AssertionError (a `required` `["szoveg","megfigyelesek","elmeleti"]`), `test_modell_opus` AssertionError (`claude-sonnet-5`), `test_rendszer_prompt...` AssertionError (nincs „bekezdés"). Illeszd be a LITERÁL kimenetet.

- [ ] **Step 3: Írd meg az implementációt**

`trendfigyelo/elemzo.py:17`:
```python
MODELL = "claude-opus-4-8"
```

`trendfigyelo/elemzo.py:19-28` — a `RENDSZER_PROMPT` teljes cseréje:
```python
RENDSZER_PROMPT = (
    "Magyar nyelvű elemző vagy egy magyar Google Trends figyelő oldalhoz. A közönség "
    "laikus olvasó, aki NEM lát JSON-t, mezőneveket vagy technikai részleteket. "
    "SZABÁLYOK, kivétel nélkül: "
    "(1) KIZÁRÓLAG a kapott számokból dolgozol; számot SOHA nem találsz ki. "
    "(2) FOLYÓ, összefüggő magyar BEKEZDÉSEKET írsz. SOHA nem használsz felsorolást, "
    "bullet-pontot, címkét, kulcs–érték párt vagy szakszót. Ha egy szekcióhoz több "
    "gondolat tartozik, azokat külön BEKEZDÉSBE (üres sorral elválasztva) fűzöd. "
    "(3) SOHA nem említesz mezőnevet, technikai kulcsot, sem a „payload\", „adat­struktúra\" "
    "vagy hasonló szót. A felhasználó nem tudja, milyen mezőkből dolgozol. Ha valamiről "
    "nincs adatod, azt természetes magyar mondattal írod le (pl. „ma még nincs mihez "
    "hasonlítani\"), NEM a hiányzó mezőt nevezed meg. "
    "(4) Ok-okozatot TÉNYKÉNT nem állítasz. Ahol magyarázatot feltételezel, a mondatban "
    "óvatosan jelzed („feltehetően\", „elképzelhető\", „ezt az adat önmagában nem igazolja\") "
    "— külön „feltételezés\" felirat NÉLKÜL, a fogalmazás maga hordozza az óvatosságot. "
    "(5) Hírt, forrást vagy eseményt nem találsz ki; a felkapott témákról csak a kapott "
    "témák és hírek alapján írsz. "
    "(6) Tömör, óvatos, DE ÉRDEMI: mondd el, mit látunk ma, milyen irányba mozdul a kép, "
    "és mit lehet ebből óvatosan leszűrni."
)
```

`_szekcio_sema` (`:128-133`) teljes cseréje:
```python
def _szekcio_sema():
    return {"type": "object", "additionalProperties": False,
            "required": ["szoveg"],
            "properties": {"szoveg": {"type": "string"}}}
```
(A `_valasz_sema` VÁLTOZATLAN — a `_szekcio_sema`-t használja.)

- [ ] **Step 4: Futtasd, hogy zöld legyen**

Run: `.venv/bin/pytest tests/test_elemzo.py -q -k "szekcio_sema or modell_opus or rendszer_prompt"`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -F - <<'EOF'
feat(elemzo): folyó-próza séma (szekció=csak szoveg) + prompt-újraírás (mezőnév/payload tiltás, bekezdések) + Opus modell

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_b0499378-8d8f-4c2a-bf75-ee09b94f1751
EOF
```

---

### Task 3: `epit_payload` + `futtat` — kulcsszo_het bekötése a láncból

**Files:**
- Modify: `trendfigyelo/elemzo.py` `epit_payload` (`:123` a `"kulcsszo_het": {}`), `futtat` (`:234-239` az `adatok` dict)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: `_kulcsszo_het` (Task 1).
- Produces: `epit_payload` visszatérésében `payload["kulcsszo_het"] == _kulcsszo_het(adatok.get("lanc", {}))`. `futtat` az `adatok`-ba betölti a `"lanc"` kulcsot a `kulcsszo_lanc.json`-ból (CSAK OLVASVA).

- [ ] **Step 1: Írd meg a bukó tesztet**

```python
def test_epit_payload_kulcsszo_het_a_lancbol():
    adatok = {"regresszio": {}, "tortenet": {}, "legfrissebb": {}, "napok_trendek": {},
              "lanc": {"kulcsszavak": {"állás": {"pontok": [
                  {"idopont_utc": "2026-08-15T18:00:00+00:00", "ertek": 42},
                  {"idopont_utc": "2026-08-22T18:00:00+00:00", "ertek": 51}]}}}}
    p = elemzo.epit_payload(adatok)
    assert p["kulcsszo_het"]["szavak"], "a kulcsszo_het NEM lehet üres, ha van lánc"
    assert p["kulcsszo_het"]["szavak"][0]["szo"] == "állás"
    assert p["kulcsszo_het"]["szavak"][0]["valtozas"] == 9
```

- [ ] **Step 2: Futtasd, hogy elhasaljon (LITERÁL kimenet kötelező)**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_epit_payload_kulcsszo_het_a_lancbol -q`
Expected: FAIL — `KeyError: 'szavak'` (a jelenlegi `epit_payload` `"kulcsszo_het": {}`-t ad). Illeszd be a LITERÁL kimenetet.

- [ ] **Step 3: Írd meg az implementációt**

`trendfigyelo/elemzo.py` `epit_payload` — a `"kulcsszo_het": {},` sort cseréld:
```python
        "kulcsszo_het": _kulcsszo_het(adatok.get("lanc", {})),
```

`futtat` — az `adatok` dictbe (a `"napok_trendek"` sor mellé) vedd fel:
```python
        "lanc": _betolt(docs_data / "kulcsszo_lanc.json") or {},
```

- [ ] **Step 4: Futtasd, hogy zöld legyen**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_epit_payload_kulcsszo_het_a_lancbol -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -F - <<'EOF'
feat(elemzo): epit_payload + futtat — kulcsszo_het a láncból (valós heti pálya bekötve)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_b0499378-8d8f-4c2a-bf75-ee09b94f1751
EOF
```

---

### Task 4: `valasz_to_artefakt` — üres-nap „mi változott ma" Python-birtoklás

**Files:**
- Modify: `trendfigyelo/elemzo.py` `valasz_to_artefakt` (`:176-194`)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: a Task 2 utáni szekció-alak (`ai_valasz[...] = {"szoveg": str}`).
- Produces: ha `payload["valtozas"].get("van_elozo")` HAMIS, az `art["valtozas"]["szoveg"]` a FIX magyar mondat (az AI szövegét eldobja); ha IGAZ, az AI `valtozas.szoveg`-je marad. Az artefakt többi kulcsa VÁLTOZATLAN.

- [ ] **Step 1: Írd meg a bukó teszteket**

```python
def _mini_payload(van_elozo):
    return {"kulcsszavak": {"szamok": []},
            "felkapott": {"top": [], "het": {"napok": 0, "visszateroek": []}},
            "valtozas": {"van_elozo": van_elozo, "irany_valtok": [], "mozgok": [],
                         "felkapott_uj": [], "felkapott_eltunt": []},
            "kulcsszo_het": {"ablak_napok": 7, "szavak": []}}


def _mini_ai(valtozas_szoveg):
    sz = {"szoveg": "sz"}
    return {"valtozas": {"szoveg": valtozas_szoveg},
            "kulcsszavak": {"napi": sz, "teljes_kep": sz, "het": sz},
            "felkapott": {"napi": sz, "het": sz}}


def test_artefakt_ures_nap_python_szoveg():
    art = elemzo.valasz_to_artefakt(_mini_ai("AI-SZÖVEG-NE-JELENJEN-MEG"),
                                    _mini_payload(van_elozo=False),
                                    nap="2026-08-22", modell="claude-opus-4-8")
    assert "nincs korábbi nap" in art["valtozas"]["szoveg"].lower()
    assert "AI-SZÖVEG-NE-JELENJEN-MEG" not in art["valtozas"]["szoveg"]
    assert art["valtozas"]["diff"]["van_elozo"] is False


def test_artefakt_van_elozo_ai_szoveg_marad():
    art = elemzo.valasz_to_artefakt(_mini_ai("Az AI napi összefoglalója."),
                                    _mini_payload(van_elozo=True),
                                    nap="2026-08-22", modell="claude-opus-4-8")
    assert art["valtozas"]["szoveg"] == "Az AI napi összefoglalója."
```

- [ ] **Step 2: Futtasd, hogy elhasaljon (LITERÁL kimenet kötelező)**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_artefakt_ures_nap_python_szoveg tests/test_elemzo.py::test_artefakt_van_elozo_ai_szoveg_marad -q`
Expected: FAIL — `test_artefakt_ures_nap_python_szoveg` AssertionError (a jelenlegi kód `**ai_valasz["valtozas"]`-t spread-el, így a szöveg „AI-SZÖVEG-NE-JELENJEN-MEG"). A `van_elozo`-teszt zöld lehet — ez rendben van, a RED az üres-napé. Illeszd be a LITERÁL kimenetet.

- [ ] **Step 3: Írd meg az implementációt**

`trendfigyelo/elemzo.py` `valasz_to_artefakt` — a `valtozas` sort cseréld a következőre, és a `return` elé told a szöveg-számítást:
```python
def valasz_to_artefakt(ai_valasz, payload, nap, modell):
    valtozas_szoveg = ai_valasz["valtozas"]["szoveg"]
    if not payload["valtozas"].get("van_elozo"):
        valtozas_szoveg = ("Ma nincs korábbi nap, amivel összevethetnénk, így a napi "
                           "elmozdulás egyelőre nem értékelhető. A friss kép a lenti "
                           "szekciókban olvasható.")
    return {
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
```

- [ ] **Step 4: Futtasd, hogy zöld legyen (a TELJES pytest is)**

Run: `.venv/bin/pytest -q`
Expected: PASS (minden korábbi + az új tesztek). Ha egy régi elemzo-teszt a régi szekció-alakot (`megfigyelesek`/`elmeleti`) várta, azt frissítsd az új alakra (csak `szoveg`) ebben a lépésben, és jegyezd fel a commit-üzenetben.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -F - <<'EOF'
feat(elemzo): valasz_to_artefakt — üres-nap „mi változott ma" szövegét Python birtokolja (szivárgásmentes)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_b0499378-8d8f-4c2a-bf75-ee09b94f1751
EOF
```

---

### Task 5: Frontend próza-render (`elemzes.js`) + e2e fixture új alak

**Files:**
- Modify: `docs/js/elemzes.js` `szekcio_elem` (`:14-39`), `rajzol` diff-összegzés (`:99-104`)
- Test: `e2e/elemzes.spec.js` (fixture + asszertek)

**Interfaces:**
- Consumes: az új artefakt-alak (szekció = `{szoveg}` `\n\n`-nal elválasztott bekezdésekkel; `valtozas={diff, szoveg}`).
- Produces: szekciónként cím + `<p class="elemzes-szoveg">` bekezdés(ek); NINCS `.elemzes-elmeleti`, nincs „feltételezés:" prefix. A `diffOsszegzes` (VALÓS) CSAK `van_elozo`-ra jelenik meg.

- [ ] **Step 1: Írd meg / frissítsd a bukó e2e-tesztet**

`e2e/elemzes.spec.js` — a `FIXTURE`-t cseréld az ÚJ alakra (a szekciók csak `szoveg`; a `napi` több bekezdéssel):
```javascript
const FIXTURE = {
  frissitve: "2026-08-22T20:00:00+00:00", modell: "claude-opus-4-8", nap: "2026-08-22",
  valtozas: { diff: { van_elozo: true, irany_valtok: [{ szo: "állás" }],
                       mozgok: [{ szo: "állás", valtozas: 2.0 }, { szo: "benzin", valtozas: -0.5 }],
                       felkapott_uj: ["eső"], felkapott_eltunt: [] },
              szoveg: "Változás-összefoglaló." },
  kulcsszavak: { szamok: [{ szo: "állás", irany: "emelkedik", mai_ertek: 10, csucs: 100 }],
                 napi: { szoveg: "Napi első bekezdés.\n\nNapi második bekezdés." },
                 teljes_kep: { szoveg: "Teljes." },
                 het: { szoveg: "Heti." } },
  felkapott: { top: [{ kifejezes: "eső", volumen: "20000" }],
               napi: { szoveg: "Felk. napi." },
               het: { szoveg: "Felk. heti." },
               het_valos: { napok: 3, visszateroek: [{ kifejezes: "eső", napok_szama: 2 }] } },
};
```
A meglévő teszt asszertjeit cseréld ezekre (a `.elemzes-megfigyeles`/`.elemzes-elmeleti` szekció-asszertek TÖRÖLVE):
```javascript
test("Elemzés fül: folyó próza <p>-ként, nincs feltételezés-réteg, VALÓS csempék", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: FIXTURE }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Elemzés");
  await expect(page.locator("#elemzes-fejlec")).toContainText("2026-08-22");
  // folyó próza: a „Kulcsszavak — mit látunk ma" szekció 2 bekezdést renderel <p>-ként
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Kulcsszavak — mit látunk ma")) .elemzes-szoveg')).toHaveCount(2);
  // nincs ELMÉLETI/feltételezés-réteg és nincs bullet-lista
  await expect(page.locator(".elemzes-elmeleti")).toHaveCount(0);
  await expect(page.locator("#elemzes-tartalom")).not.toContainText("feltételezés:");
  // VALÓS csempék + heti visszatérés + mozgók változatlanul
  await expect(page.locator(".elemzes-csempe")).toContainText("állás");
  await expect(page.locator("#felkapott-het-valos .elemzes-felkapott-csempe")).toHaveText(["eső — 2 nap"]);
  await expect(page.locator(".elemzes-diff-osszegzes")).toContainText("állás");
  await expect(page.locator(".elemzes-diff-mozgok")).toContainText("benzin");
});
```

- [ ] **Step 2: Futtasd, hogy elhasaljon (LITERÁL kimenet kötelező)**

Run: `npx playwright test e2e/elemzes.spec.js --workers=1`
Expected: FAIL — a `.elemzes-szoveg` count 1 (a jelenlegi render egyetlen `<p>`-be teszi az egész szöveget, nem bont `\n\n`-nál), és/vagy a régi asszertek. Illeszd be a LITERÁL Playwright-kimenetet.

- [ ] **Step 3: Írd meg az implementációt**

`docs/js/elemzes.js` `szekcio_elem` teljes cseréje:
```javascript
function szekcio_elem(cim, szekcio) {
  const box = document.createElement("section");
  box.className = "elemzes-szekcio";
  const h = document.createElement("h3");
  h.textContent = cim;
  box.appendChild(h);
  const szoveg = (szekcio && szekcio.szoveg) || "";
  szoveg.split(/\n\s*\n/).map((s) => s.trim()).filter(Boolean).forEach((bek) => {
    const p = document.createElement("p");
    p.className = "elemzes-szoveg";
    p.textContent = bek;
    box.appendChild(p);
  });
  return box;
}
```

`docs/js/elemzes.js` `rajzol` — a `diffOsszegzes` blokk (`:99-104`) cseréje úgy, hogy CSAK `van_elozo`-ra jelenjen meg (az üres-napi „Nincs összevethető előző nap." sor törölve, mert a szekció-próza már ezt mondja):
```javascript
  if (d.van_elozo) {
    const diffOsszegzes = document.createElement("p");
    diffOsszegzes.className = "elemzes-diff-osszegzes elemzes-megfigyeles";   // VALÓS réteg (diff-számítás)
    diffOsszegzes.textContent =
      `Irányt váltott: ${d.irany_valtok.map((v) => v.szo).join(", ") || "–"} · új felkapott: ${d.felkapott_uj.join(", ") || "–"} · eltűnt: ${d.felkapott_eltunt.join(", ") || "–"}`;
    valt.appendChild(diffOsszegzes);
  }
```
(A `mozgok` blokk `:106-113` VÁLTOZATLAN — már `d.van_elozo`-ra guardolt.)

- [ ] **Step 4: Futtasd, hogy zöld legyen**

Run: `npx playwright test e2e/elemzes.spec.js --workers=1`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/js/elemzes.js e2e/elemzes.spec.js
git commit -F - <<'EOF'
feat(elemzes-ui): folyó-próza render (<p> bekezdések), ELMÉLETI/feltételezés-réteg megszüntetve; diff-összegzés csak van_elozo esetén

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_b0499378-8d8f-4c2a-bf75-ee09b94f1751
EOF
```

---

### Task 6: Kétoszlopos elrendezés (naptár bal / elemzés jobb) + e2e

**Files:**
- Modify: `docs/css/app.css` (`#elemzes` `:134`, `#elemzes-naptar` `:135`, `.elemzes-szoveg` `:139`)
- Test: `e2e/elemzes.spec.js` (új elrendezés-teszt)

**Interfaces:**
- Consumes: a `#elemzes` két gyereke forrás-sorrendben (`#elemzes-naptar`, majd `#elemzes-tartalom`) — Task 5 után változatlan HTML.
- Produces: desktopon a naptár a bal oszlopban (a tartalomtól balra), ~760px alatt egymás alá csúszva.

- [ ] **Step 1: Írd meg a bukó e2e-tesztet**

`e2e/elemzes.spec.js`-hez add hozzá:
```javascript
test("Elemzés elrendezés: naptár bal, elemzés jobb; mobilon egymás alá", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: FIXTURE }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ json: { napok: ["2026-08-22"] } }));
  await page.setViewportSize({ width: 1200, height: 900 });
  await page.goto("/elemzes.html");
  await expect(page.locator("#elemzes-naptar .nap-cella").first()).toBeVisible();
  const nap = await page.locator("#elemzes-naptar").boundingBox();
  const tart = await page.locator("#elemzes-tartalom").boundingBox();
  expect(nap.x + nap.width).toBeLessThanOrEqual(tart.x + 1);        // naptár a tartalomtól BALRA
  await page.setViewportSize({ width: 480, height: 900 });
  const nap2 = await page.locator("#elemzes-naptar").boundingBox();
  const tart2 = await page.locator("#elemzes-tartalom").boundingBox();
  expect(tart2.y).toBeGreaterThan(nap2.y + nap2.height - 1);         // tartalom a naptár ALATT
});
```

- [ ] **Step 2: Futtasd, hogy elhasaljon (LITERÁL kimenet kötelező)**

Run: `npx playwright test e2e/elemzes.spec.js --workers=1 -g "elrendezés"`
Expected: FAIL — desktopon a naptár NEM a tartalomtól balra van (jelenleg egymás alatt, blokk-elrendezés), így `nap.x + nap.width <= tart.x + 1` hamis (a naptár a tartalom FÖLÖTT, azonos x-en, teljes szélességben). Illeszd be a LITERÁL kimenetet.

- [ ] **Step 3: Írd meg az implementációt**

`docs/css/app.css` — a `#elemzes` és `#elemzes-naptar` sorok cseréje + a `.elemzes-szoveg` sorköz + mobil media query:
```css
#elemzes { display: grid; grid-template-columns: minmax(15rem, 20rem) 1fr; gap: 1.5rem; align-items: start; max-width: 72rem; }
#elemzes-naptar { margin: 0; max-width: none; position: sticky; top: 1rem; }
```
A `.elemzes-szoveg` sor cseréje:
```css
.elemzes-szoveg { color: #333; margin: .3rem 0 .7rem; line-height: 1.55; }
```
Az `.elemzes-felkapott-csempe { ... }` blokk UTÁN (a `#elemzes` szabályok végén, a fájl elemzés-szekciójában) add hozzá a mobil összecsúsztatást:
```css
@media (max-width: 760px) { #elemzes { grid-template-columns: 1fr; } #elemzes-naptar { position: static; } }
```

- [ ] **Step 4: Futtasd, hogy zöld legyen (a TELJES suite SOROSAN)**

Run: `npx playwright test --workers=1` majd `.venv/bin/pytest -q`
Expected: mindkettő PASS.

- [ ] **Step 5: Ellenőrizd a MUTÁCIÓ-invariánst, majd commit**

Run: `grep -rn "MUTÁCIÓ" docs/js docs/css e2e tests trendfigyelo | wc -l` → Expected: `1`.
```bash
git add docs/css/app.css e2e/elemzes.spec.js
git commit -F - <<'EOF'
feat(elemzes-ui): kétoszlopos elrendezés — naptár bal (sticky) / elemzés jobb, mobilon egymás alá; próza sorköz

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_b0499378-8d8f-4c2a-bf75-ee09b94f1751
EOF
```

---

## Záró teendők (a Task 6 után, KÜLÖN kör — a subagent-driven-development záró szemléje kezeli)

- Teljes-branch szemle (opus): a két SÉRTHETETLEN (minden szám Pythonból; fail-soft) sértetlen; a pótolhatatlan lánc CSAK olvasva; `git add` végig névvel.
- Élő-UI előnézet (a memória `eloUI-preview-workflow` szerint) a próza-render + elrendezés vizuális ellenőrzéséhez, a docs/data szennyezése nélkül.
- Push KÜLÖN kör: `fetch → HEAD..origin/main → ha nem üres: pull --rebase + TELJES SOROS suite ÚJRA → push → rev-list 0 0`.
- Az ÉLES modellváltás (Opus) igazolása: az első automata/kézi futás után az artefakt `modell: claude-opus-4-8`, és a hívás-paraméterek (thinking/effort/json_schema) elfogadottak — ha Opus 4.8 elutasít valamit, az a `_AnthropicKliens.uzenet` varratban igazítandó (külön, mérve).

## Self-Review (a terv a spec ellen)

- Spec §3.1 (Opus) → Task 2. §3.2 (séma) → Task 2. §3.3 (prompt) → Task 2. §3.4 (kulcsszo_het + futtat) → Task 1 + Task 3. §3.5 (üres-nap Python) → Task 4. §4.1 (kétoszlopos) → Task 6. §4.2 (próza-render) → Task 5. §4.3 (csempék maradnak) → Task 5 (érintetlen). §5.1 (pytest) → Task 1–4. §5.2 (Playwright) → Task 5–6. §6 (nem-cél) → nincs task (helyes). §7 (migráció) → Task 5 render stringre dolgozik, a régi `megfigyelesek[]` nem renderelődik (lefedve). Nincs fedetlen spec-rész.
- Placeholder-scan: minden lépés tényleges kódot/parancsot tartalmaz. Nincs „TBD".
- Típus-konzisztencia: `_kulcsszo_het` visszatérése (`ablak_napok`/`szavak`/`szo`/`kezdo`/`veg`/`valtozas`/`min`/`max`) azonos a Task 1 és a fixture között; `MODELL == "claude-opus-4-8"` a Task 2 és a Task 5 fixture között egyezik; a `valtozas={diff, szoveg}` alak a Task 4 és a Task 5 render között egyezik.
