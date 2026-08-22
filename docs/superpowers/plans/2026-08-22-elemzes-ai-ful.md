# Elemzés-fül — napi AI-elemzés (Claude) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Új „Elemzés" fül a honlapon, amely minden nap automatikusan (Claude Sonnet 5, a CI-ben) elemzi a friss adatokat — kulcsszavak, felkapott keresések, „mi változott ma" — és statikus, visszakereshető artefaktként megjeleníti.

**Architecture:** A `napi.yml` sikeres lefutása után egy `workflow_run`-triggerelt `elemzes.yml` futtatja a `trendfigyelo/elemzo.py`-t: az beolvassa a commitolt adatfájlokat, egy TISZTA Python függvény kigyűjti a KEMÉNY számokat (VALÓS réteg), a Claude ezekből CSAK narratívát ír (ok-okozat tényként tilos, hipotézis = külön `ELMÉLETI` mező), az eredmény `docs/data/elemzes.json` (legfrissebb) + `docs/data/elemzesek/<datum>.json` (archívum) + `index.json`, külön committal. A frontend statikus oldal, ami az artefaktot rajzolja.

**Tech Stack:** Python 3.12, `anthropic` SDK (Sonnet 5, `output_config.format` strukturált kimenet), pytest (SOROS), Playwright (SOROS), GitHub Actions (`workflow_run`), statikus JS/HTML (`docs/`).

**Spec:** `docs/superpowers/specs/2026-08-22-elemzes-ai-ful-design.md`

## Global Constraints

- **Nyelv:** magyar mindenhol (kód, kommentek, UI, prompt).
- **A számokat PYTHON számolja, nem az AI** — az AI SOHA nem talál ki számot; kizárólag a payloadban kapott számokból ír.
- **Jelölési fegyelem:** ok-okozatot tényként SOHA; hipotézis = külön `ELMÉLETI` mező („feltételezés"); megfigyelés (számok) és magyarázat (miért) külön mezőben; a felkapott híreknél csak a kapott `hirek`/`temak` mezőkből.
- **A pótolhatatlan órás ág fájljaihoz NEM nyúlunk** (`kulcsszo_nyers.json`, `kulcsszo_lanc.json`) — csak OLVASSUK.
- **Fail-soft:** Claude-hiba (429/hálózat/refusal) esetén az előző `elemzes.json` MARAD, FIGYELEM a logba, nem-nulla exit. Az elemzés NEM pótolhatatlan.
- **Modell:** `claude-sonnet-5` (nincs `temperature` — Sonnet 5 nem fogadja; a stílus prompttal).
- **Munkamódszer:** SOROS suite (`--workers=1` Playwrightnál); MUTÁCIÓ==1 végállapotban; TDD valódi RED-del (névre/viselkedésre, nem Import/Attribute/Name/timeout); `git add` NÉVVEL; commit CSAK jóváhagyott üzenettel; a szándékos-zöld fedését MÉRNI (lemezt nézni, nem visszatérési értéket); a DOM-belső egyetlen őre a vizuális szemle.
- **Commit-trailer minden committon:**
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_b0499378-8d8f-4c2a-bf75-ee09b94f1751
  ```
- **Adat-commit KÜLÖN a kód-committól** (az `elemzes.json`/`elemzesek/` írását a workflow commitolja, nem a fejlesztő).

## File Structure

- **Create `trendfigyelo/elemzo.py`** — a teljes backend-ág: `epit_payload` (VALÓS számok + gördülő hét), `nap_diff` (mi változott), `elemez` (Claude-varrat), `valasz_to_artefakt`, `futtat` + `main`. Egy fájl, egy felelősség (az elemzés-ág), a `felkapott.py`/`regresszio.py` mintájára.
- **Create `elemzes.py`** (repo gyökér) — vékony belépő → `trendfigyelo.elemzo.main` (a `top_keresesek.py` mintája).
- **Modify `requirements.txt`** — `anthropic` hozzáadva.
- **Create `.github/workflows/elemzes.yml`** — `workflow_run` a napi.yml után.
- **Create `docs/elemzes.html`** — az „Elemzés" oldal (az `adatokrol.html` mintája).
- **Create `docs/js/elemzes.js`** — a fül renderere (az artefaktot rajzolja).
- **Modify `docs/index.html`, `docs/adatokrol.html`** — `#fomenu` bővítése egy „Elemzés" taggal (2 → 3 link).
- **Create tests:** `tests/test_elemzo.py` (backend), `e2e/elemzes.spec.js` (frontend).
- **Modify `e2e/menu.spec.js`** — a menü immár 3 fül.

---

### Task 1: Payload-építő — VALÓS számok (kulcsszavak + felkapott + gördülő hét)

**Files:**
- Create: `trendfigyelo/elemzo.py`
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Produces: `epit_payload(adatok: dict, tegnapi_szamok: list | None = None) -> dict` — tiszta függvény; `adatok` a beolvasott JSON-ok szótára (`{"regresszio":..., "tortenet":..., "legfrissebb":..., "napok_trendek": {"<datum>": [...]}}`); visszaad `{"kulcsszavak": {"szamok": [...]}, "felkapott": {"top": [...], "het": {...}}, "kulcsszo_het": {...}}`. A `szamok` per szó: `{"szo", "irany", "meredekseg", "ervenyes", "mai_ertek", "csucs", "atlag"}`. (A `tegnapi_szamok` a Task 2 diffjéhez kell — itt még nem használt, csak a szignatúra rögzíti.)

- [ ] **Step 1: Írd meg a bukó tesztet — a kulcsszó VALÓS számok kinyerése**

`tests/test_elemzo.py`:
```python
from trendfigyelo import elemzo


def _regresszio_egy_szo(irany, meredekseg, ervenyes, mai):
    return {
        "kulcsszavak": {
            "állás": {
                "domen": "munkaeropiac", "tipus": "szintmero", "racs": "ora",
                "intervallumok": {
                    "1_het": {
                        "ervenyes": ervenyes, "irany": irany,
                        "meredekseg_nap": meredekseg, "mai_ertek": mai,
                        "ablak_veg_utc": "2026-08-22T18:00:00+00:00",
                    }
                },
            }
        }
    }


def test_kulcsszo_szamok_a_regresszio_1_het_intervallumbol():
    adatok = {
        "regresszio": _regresszio_egy_szo("emelkedik", 1.23, True, 42.0),
        "tortenet": {"napok": [{"nap": "2026-08-22",
                                "kulcsszavak": [{"kulcsszo": "állás", "atlag": 25.0, "csucs": 100.0}]}]},
        "legfrissebb": {"top_trendek": []},
        "napok_trendek": {},
    }
    payload = elemzo.epit_payload(adatok)
    szamok = payload["kulcsszavak"]["szamok"]
    assert len(szamok) == 1
    szo = szamok[0]
    assert szo["szo"] == "állás"
    assert szo["irany"] == "emelkedik"
    assert szo["meredekseg"] == 1.23
    assert szo["ervenyes"] is True
    assert szo["mai_ertek"] == 42.0
    assert szo["csucs"] == 100.0
    assert szo["atlag"] == 25.0
```

- [ ] **Step 2: Futtasd — bukjon**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_kulcsszo_szamok_a_regresszio_1_het_intervallumbol -v`
Expected: FAIL — `AttributeError: module 'trendfigyelo.elemzo' has no attribute 'epit_payload'`

- [ ] **Step 3: Minimális implementáció — `epit_payload` a kulcsszó-számokkal**

`trendfigyelo/elemzo.py`:
```python
"""Napi AI-elemzés ág: a commitolt adatokból VALÓS számok (Python) → Claude narratíva.

A számokat MINDIG ez a modul számolja; az AI (elemez) SOHA nem talál ki számot,
kizárólag a payloadban kapott számokból ír (spec §2.1). Ok-okozat tényként tilos;
hipotézis = külön ELMÉLETI mező (spec §2.2).
"""

# A kulcsszó VALÓS iránya/meredeksége az 1_het (órás, napi frissülő) intervallumból jön.
KULCSSZO_IV = "1_het"


def _tortenet_utolso_nap_szavak(tortenet):
    napok = tortenet.get("napok", []) if isinstance(tortenet, dict) else []
    if not napok:
        return {}
    utolso = napok[-1]
    return {k["kulcsszo"]: k for k in utolso.get("kulcsszavak", [])}


def _kulcsszo_szamok(regresszio, tortenet):
    szavak = regresszio.get("kulcsszavak", {}) if isinstance(regresszio, dict) else {}
    tort = _tortenet_utolso_nap_szavak(tortenet)
    ki = []
    for szo, rec in szavak.items():
        iv = rec.get("intervallumok", {}).get(KULCSSZO_IV, {})
        t = tort.get(szo, {})
        ki.append({
            "szo": szo,
            "irany": iv.get("irany"),
            "meredekseg": iv.get("meredekseg_nap"),
            "ervenyes": iv.get("ervenyes"),
            "mai_ertek": iv.get("mai_ertek"),
            "csucs": t.get("csucs"),
            "atlag": t.get("atlag"),
        })
    return ki


def epit_payload(adatok, tegnapi_szamok=None):
    regresszio = adatok.get("regresszio", {})
    tortenet = adatok.get("tortenet", {})
    szamok = _kulcsszo_szamok(regresszio, tortenet)
    return {
        "kulcsszavak": {"szamok": szamok},
        "felkapott": {"top": [], "het": {}},
        "kulcsszo_het": {},
    }
```

- [ ] **Step 4: Futtasd — menjen át**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_kulcsszo_szamok_a_regresszio_1_het_intervallumbol -v`
Expected: PASS

- [ ] **Step 5: Írd meg a bukó tesztet — felkapott top + gördülő heti aggregátum**

`tests/test_elemzo.py` (add):
```python
def test_felkapott_top_es_gordulo_het():
    adatok = {
        "regresszio": {"kulcsszavak": {}},
        "tortenet": {"napok": []},
        "legfrissebb": {"top_trendek": [
            {"kifejezes": "viharos szél", "volumen": "50000", "novekedes_pct": "1000", "temak": ["Other"]},
        ]},
        "napok_trendek": {
            "2026-08-21": [{"kifejezes": "eső", "volumen": "20000", "temak": ["Weather"]},
                           {"kifejezes": "viharos szél", "volumen": "10000", "temak": ["Weather"]}],
            "2026-08-22": [{"kifejezes": "viharos szél", "volumen": "50000", "temak": ["Other"]}],
        },
    }
    payload = elemzo.epit_payload(adatok)
    felk = payload["felkapott"]
    assert felk["top"][0]["kifejezes"] == "viharos szél"
    assert felk["top"][0]["volumen"] == "50000"
    # gördülő hét: hányszor bukkant fel egy kifejezés az elmúlt napokban
    het = {e["kifejezes"]: e["napok_szama"] for e in felk["het"]["visszateroek"]}
    assert het["viharos szél"] == 2      # 08-21 és 08-22
    assert het["eső"] == 1
```

- [ ] **Step 6: Futtasd — bukjon**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_felkapott_top_es_gordulo_het -v`
Expected: FAIL — `KeyError: 'kifejezes'` (a `top` üres, `het` üres)

- [ ] **Step 7: Implementáld a felkapott top + heti aggregátumot**

`trendfigyelo/elemzo.py` (bővítsd az `epit_payload`-ot; add hozzá a helpert):
```python
def _felkapott(legfrissebb, napok_trendek):
    top = []
    for t in (legfrissebb.get("top_trendek", []) if isinstance(legfrissebb, dict) else []):
        top.append({
            "kifejezes": t.get("kifejezes"), "volumen": t.get("volumen"),
            "novekedes_pct": t.get("novekedes_pct"), "temak": t.get("temak", []),
        })
    # gördülő hét: hány külön napon szerepelt egy kifejezés (napok_trendek = utolsó ≤7 nap)
    szamlalo = {}
    for _datum, trendek in sorted(napok_trendek.items()):
        for t in trendek:
            kif = t.get("kifejezes")
            if kif:
                szamlalo[kif] = szamlalo.get(kif, 0) + 1
    visszateroek = sorted(
        ({"kifejezes": k, "napok_szama": n} for k, n in szamlalo.items()),
        key=lambda e: (-e["napok_szama"], e["kifejezes"]),
    )
    return {"top": top, "het": {"napok": len(napok_trendek), "visszateroek": visszateroek}}
```
majd az `epit_payload`-ban:
```python
    felkapott = _felkapott(adatok.get("legfrissebb", {}), adatok.get("napok_trendek", {}))
    return {
        "kulcsszavak": {"szamok": szamok},
        "felkapott": felkapott,
        "kulcsszo_het": {},
    }
```

- [ ] **Step 8: Futtasd — mindkét teszt menjen át**

Run: `.venv/bin/pytest tests/test_elemzo.py -v`
Expected: PASS (2 teszt)

- [ ] **Step 9: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit
```
Üzenet (jóváhagyásra): `feat(elemzo): payload-építő — kulcsszó VALÓS számok + felkapott top + gördülő hét`

---

### Task 2: Nap-diff — „mi változott ma?"

**Files:**
- Modify: `trendfigyelo/elemzo.py`
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: `epit_payload` `szamok` alakja Task 1-ből (`{"szo","irany","meredekseg",...}`).
- Produces: `nap_diff(mai_szamok: list, tegnapi_szamok: list | None, mai_top: list, tegnapi_top: list | None) -> dict` — `{"irany_valtok": [...], "mozgok": [...], "felkapott_uj": [...], "felkapott_eltunt": [...], "van_elozo": bool}`. `epit_payload` mostantól ezt beépíti a payloadba `valtozas` kulcs alatt, ha kap tegnapi adatot.

- [ ] **Step 1: Írd meg a bukó tesztet — irányváltás + új/eltűnt felkapott**

`tests/test_elemzo.py` (add):
```python
def test_nap_diff_iranyvaltas_es_felkapott_valtozas():
    mai = [{"szo": "állás", "irany": "emelkedik", "meredekseg": 2.0},
           {"szo": "benzin", "irany": "stagnal", "meredekseg": 0.0}]
    tegnapi = [{"szo": "állás", "irany": "csokken", "meredekseg": -1.0},
               {"szo": "benzin", "irany": "stagnal", "meredekseg": 0.1}]
    mai_top = [{"kifejezes": "eső"}, {"kifejezes": "viharos szél"}]
    tegnapi_top = [{"kifejezes": "eső"}, {"kifejezes": "hőség"}]
    diff = elemzo.nap_diff(mai, tegnapi, mai_top, tegnapi_top)
    assert diff["van_elozo"] is True
    assert {"szo": "állás", "elozo": "csokken", "mai": "emelkedik"} in diff["irany_valtok"]
    assert all(v["szo"] != "benzin" for v in diff["irany_valtok"])   # benzin nem váltott irányt
    assert "viharos szél" in diff["felkapott_uj"]
    assert "hőség" in diff["felkapott_eltunt"]


def test_nap_diff_elso_futas_nincs_elozo():
    diff = elemzo.nap_diff([{"szo": "állás", "irany": "emelkedik", "meredekseg": 1.0}], None,
                           [{"kifejezes": "eső"}], None)
    assert diff["van_elozo"] is False
    assert diff["irany_valtok"] == []
    assert diff["felkapott_uj"] == []
    assert diff["felkapott_eltunt"] == []
```

- [ ] **Step 2: Futtasd — bukjon**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_nap_diff_iranyvaltas_es_felkapott_valtozas tests/test_elemzo.py::test_nap_diff_elso_futas_nincs_elozo -v`
Expected: FAIL — `AttributeError: ... has no attribute 'nap_diff'`

- [ ] **Step 3: Implementáld a `nap_diff`-et**

`trendfigyelo/elemzo.py` (add):
```python
def nap_diff(mai_szamok, tegnapi_szamok, mai_top, tegnapi_top):
    if not tegnapi_szamok and not tegnapi_top:
        return {"irany_valtok": [], "mozgok": [], "felkapott_uj": [],
                "felkapott_eltunt": [], "van_elozo": False}
    tegnap = {s["szo"]: s for s in (tegnapi_szamok or [])}
    irany_valtok, mozgok = [], []
    for s in mai_szamok:
        elozo = tegnap.get(s["szo"])
        if not elozo:
            continue
        if elozo.get("irany") != s.get("irany"):
            irany_valtok.append({"szo": s["szo"], "elozo": elozo.get("irany"), "mai": s.get("irany")})
        m_mai, m_teg = s.get("meredekseg"), elozo.get("meredekseg")
        if isinstance(m_mai, (int, float)) and isinstance(m_teg, (int, float)):
            mozgok.append({"szo": s["szo"], "valtozas": round(m_mai - m_teg, 3)})
    mozgok.sort(key=lambda e: -abs(e["valtozas"]))
    mai_kif = {t.get("kifejezes") for t in (mai_top or [])}
    teg_kif = {t.get("kifejezes") for t in (tegnapi_top or [])}
    return {
        "irany_valtok": irany_valtok,
        "mozgok": mozgok[:5],
        "felkapott_uj": sorted(mai_kif - teg_kif),
        "felkapott_eltunt": sorted(teg_kif - mai_kif),
        "van_elozo": True,
    }
```

- [ ] **Step 4: Futtasd — menjen át**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_nap_diff_iranyvaltas_es_felkapott_valtozas tests/test_elemzo.py::test_nap_diff_elso_futas_nincs_elozo -v`
Expected: PASS

- [ ] **Step 5: Írd meg a bukó tesztet — `epit_payload` beépíti a `valtozas`-t, ha kap tegnapit**

`tests/test_elemzo.py` (add):
```python
def test_epit_payload_beepiti_a_valtozast_ha_van_tegnapi():
    adatok = {
        "regresszio": _regresszio_egy_szo("emelkedik", 1.0, True, 10.0),
        "tortenet": {"napok": []},
        "legfrissebb": {"top_trendek": [{"kifejezes": "eső"}]},
        "napok_trendek": {},
    }
    tegnapi_szamok = [{"szo": "állás", "irany": "csokken", "meredekseg": -1.0}]
    tegnapi_top = [{"kifejezes": "hőség"}]
    payload = elemzo.epit_payload(adatok, tegnapi_szamok=tegnapi_szamok, tegnapi_top=tegnapi_top)
    assert payload["valtozas"]["van_elozo"] is True
    assert payload["valtozas"]["irany_valtok"][0]["szo"] == "állás"
    assert "eső" in payload["valtozas"]["felkapott_uj"]
```

- [ ] **Step 6: Futtasd — bukjon**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_epit_payload_beepiti_a_valtozast_ha_van_tegnapi -v`
Expected: FAIL — `TypeError: epit_payload() got an unexpected keyword argument 'tegnapi_top'`

- [ ] **Step 7: Kösd be a `valtozas`-t az `epit_payload`-ba**

`trendfigyelo/elemzo.py` — módosítsd az `epit_payload` szignatúráját és végét:
```python
def epit_payload(adatok, tegnapi_szamok=None, tegnapi_top=None):
    regresszio = adatok.get("regresszio", {})
    tortenet = adatok.get("tortenet", {})
    szamok = _kulcsszo_szamok(regresszio, tortenet)
    felkapott = _felkapott(adatok.get("legfrissebb", {}), adatok.get("napok_trendek", {}))
    valtozas = nap_diff(szamok, tegnapi_szamok, felkapott["top"], tegnapi_top)
    return {
        "kulcsszavak": {"szamok": szamok},
        "felkapott": felkapott,
        "valtozas": valtozas,
        "kulcsszo_het": {},
    }
```

- [ ] **Step 8: Futtasd — az egész fájl menjen át**

Run: `.venv/bin/pytest tests/test_elemzo.py -v`
Expected: PASS (5 teszt)

- [ ] **Step 9: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit
```
Üzenet (jóváhagyásra): `feat(elemzo): nap-diff — irányváltók, mozgók, új/eltűnt felkapott (mi változott ma)`

---

### Task 3: Claude-varrat (`elemez`) + `valasz_to_artefakt`

**Files:**
- Modify: `trendfigyelo/elemzo.py`, `requirements.txt`
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: `epit_payload` kimenete Task 1–2-ből.
- Produces:
  - `elemez(payload: dict, kliens=None, modell: str = "claude-sonnet-5") -> dict` — a Claude-hívás; `kliens` injektálható varrat (alap: `_alap_kliens()`; teszt: kamu, aminek van `.uzenet(payload, modell)` metódusa, ami `dict`-et ad vissza). Visszaadja a strukturált AI-narratívát: `{"valtozas": {...}, "kulcsszavak": {...}, "felkapott": {...}}`, minden szekció `{"szoveg", "megfigyelesek": [...], "elmeleti": [...]}`.
  - `valasz_to_artefakt(ai_valasz: dict, payload: dict, nap: str, modell: str) -> dict` — a spec §5 `elemzes.json` alakja: VALÓS réteg (payloadból) + AI-narratíva (ai_valasz) + meta.
- A kliens-varrat interfésze: bármely objektum egy `uzenet(self, payload, modell) -> dict` metódussal. Az alap implementáció az `anthropic` SDK-t hívja `output_config.format` json_schema-val.

- [ ] **Step 1: Add az `anthropic`-ot a requirements-hez**

`requirements.txt` — új sor:
```
anthropic>=0.116
```

- [ ] **Step 2: Írd meg a bukó tesztet — `elemez` a kamu-klienssel (NINCS hálózat)**

`tests/test_elemzo.py` (add):
```python
class KamuKliens:
    def __init__(self, valasz):
        self._valasz = valasz
        self.hivasok = []

    def uzenet(self, payload, modell):
        self.hivasok.append((payload, modell))
        return self._valasz


def _ai_valasz():
    szekcio = {"szoveg": "sz", "megfigyelesek": ["m"], "elmeleti": ["e"]}
    return {"valtozas": szekcio, "kulcsszavak": {"napi": szekcio, "teljes_kep": szekcio, "het": szekcio},
            "felkapott": {"napi": szekcio, "het": szekcio}}


def test_elemez_a_varrat_mogott_nem_hiv_halozatot():
    kliens = KamuKliens(_ai_valasz())
    payload = {"kulcsszavak": {"szamok": []}, "felkapott": {"top": []}, "valtozas": {}}
    valasz = elemzo.elemez(payload, kliens=kliens)
    assert kliens.hivasok[0][1] == "claude-sonnet-5"      # a modell átment
    assert valasz["kulcsszavak"]["napi"]["szoveg"] == "sz"
    assert valasz["valtozas"]["elmeleti"] == ["e"]
```

- [ ] **Step 3: Futtasd — bukjon**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_elemez_a_varrat_mogott_nem_hiv_halozatot -v`
Expected: FAIL — `AttributeError: ... has no attribute 'elemez'`

- [ ] **Step 4: Implementáld az `elemez`-t (varrat) — az SDK-hívás lazy importtal**

`trendfigyelo/elemzo.py` (add). A rendszer-prompt a jelölési fegyelmet rögzíti; az SDK importja a függvényben (hogy a tesztek `anthropic` nélkül is fussanak):
```python
MODELL = "claude-sonnet-5"

RENDSZER_PROMPT = (
    "Magyar nyelvű elemző vagy egy magyar Google Trends figyelő oldalhoz. "
    "SZABÁLYOK, kivétel nélkül: (1) SOHA nem találsz ki számot — kizárólag a kapott "
    "payload számaiból dolgozol. (2) Ok-okozatot TÉNYKÉNT SOHA nem állítasz; a "
    "megfigyelés (mit mutatnak a számok) és a magyarázat (miért) külön mezőben van. "
    "(3) Minden feltételezést az 'elmeleti' mezőbe teszel, 'feltételezés' megfogalmazással; "
    "a tényszerű leolvasásokat a 'megfigyelesek' mezőbe. (4) A felkapott hírekről csak a "
    "kapott 'temak'/'hirek' alapján írsz, hírt/forrást/eseményt nem találsz ki. "
    "Tömör, óvatos, magyar mondatok."
)

# Az AI válaszának sémája (szekciónként szöveg + megfigyelések + elméleti).
def _szekcio_sema():
    return {"type": "object", "additionalProperties": False,
            "required": ["szoveg", "megfigyelesek", "elmeleti"],
            "properties": {"szoveg": {"type": "string"},
                           "megfigyelesek": {"type": "array", "items": {"type": "string"}},
                           "elmeleti": {"type": "array", "items": {"type": "string"}}}}


def _valasz_sema():
    sz = _szekcio_sema()
    return {"type": "object", "additionalProperties": False,
            "required": ["valtozas", "kulcsszavak", "felkapott"],
            "properties": {
                "valtozas": sz,
                "kulcsszavak": {"type": "object", "additionalProperties": False,
                                "required": ["napi", "teljes_kep", "het"],
                                "properties": {"napi": sz, "teljes_kep": sz, "het": sz}},
                "felkapott": {"type": "object", "additionalProperties": False,
                              "required": ["napi", "het"],
                              "properties": {"napi": sz, "het": sz}}}}


class _AnthropicKliens:
    """Alap kliens-varrat: az anthropic SDK-t hívja strukturált kimenettel."""

    def uzenet(self, payload, modell):
        import json
        import anthropic
        kliens = anthropic.Anthropic()   # ANTHROPIC_API_KEY a környezetből
        valasz = kliens.messages.create(
            model=modell, max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium",
                           "format": {"type": "json_schema", "schema": _valasz_sema()}},
            system=RENDSZER_PROMPT,
            messages=[{"role": "user", "content":
                       "Elemezd az alábbi VALÓS számokat (JSON). Csak ezekből dolgozz:\n"
                       + json.dumps(payload, ensure_ascii=False)}],
        )
        szoveg = next(b.text for b in valasz.content if b.type == "text")
        return json.loads(szoveg)


def elemez(payload, kliens=None, modell=MODELL):
    kliens = kliens or _AnthropicKliens()
    return kliens.uzenet(payload, modell)
```

- [ ] **Step 5: Futtasd — menjen át**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_elemez_a_varrat_mogott_nem_hiv_halozatot -v`
Expected: PASS

- [ ] **Step 6: Írd meg a bukó tesztet — `valasz_to_artefakt` a spec §5 alakot adja**

`tests/test_elemzo.py` (add):
```python
def test_valasz_to_artefakt_valos_reteg_es_ai_narrativa():
    payload = {
        "kulcsszavak": {"szamok": [{"szo": "állás", "irany": "emelkedik", "meredekseg": 1.0,
                                    "ervenyes": True, "mai_ertek": 10.0, "csucs": 100.0, "atlag": 25.0}]},
        "felkapott": {"top": [{"kifejezes": "eső", "volumen": "20000", "novekedes_pct": "500", "temak": ["W"]}],
                      "het": {"napok": 2, "visszateroek": []}},
        "valtozas": {"irany_valtok": [], "mozgok": [], "felkapott_uj": [], "felkapott_eltunt": [], "van_elozo": False},
    }
    art = elemzo.valasz_to_artefakt(_ai_valasz(), payload, nap="2026-08-22", modell="claude-sonnet-5")
    assert art["nap"] == "2026-08-22"
    assert art["modell"] == "claude-sonnet-5"
    # VALÓS réteg átvéve a payloadból (nem az AI-tól):
    assert art["kulcsszavak"]["szamok"][0]["csucs"] == 100.0
    assert art["felkapott"]["top"][0]["kifejezes"] == "eső"
    assert art["valtozas"]["diff"]["van_elozo"] is False
    # AI-narratíva a helyén:
    assert art["kulcsszavak"]["napi"]["szoveg"] == "sz"
    assert art["felkapott"]["het"]["elmeleti"] == ["e"]
```

- [ ] **Step 7: Futtasd — bukjon**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_valasz_to_artefakt_valos_reteg_es_ai_narrativa -v`
Expected: FAIL — `AttributeError: ... has no attribute 'valasz_to_artefakt'`

- [ ] **Step 8: Implementáld a `valasz_to_artefakt`-ot**

`trendfigyelo/elemzo.py` (add):
```python
from trendfigyelo import seged


def valasz_to_artefakt(ai_valasz, payload, nap, modell):
    return {
        "frissitve": seged.idopont_iso(seged.most_utc()),
        "modell": modell,
        "nap": nap,
        "valtozas": {"diff": payload["valtozas"], **ai_valasz["valtozas"]},
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
        },
    }
```

- [ ] **Step 9: Futtasd — az egész fájl menjen át**

Run: `.venv/bin/pytest tests/test_elemzo.py -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py requirements.txt
git commit
```
Üzenet (jóváhagyásra): `feat(elemzo): Claude-varrat (Sonnet 5, strukturált) + artefakt-alak (VALÓS + AI)`

---

### Task 4: `futtat` — archívum/index + fail-soft + belépő

**Files:**
- Modify: `trendfigyelo/elemzo.py`
- Create: `elemzes.py` (repo gyökér)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: `epit_payload`, `elemez`, `valasz_to_artefakt`, `nap_diff`.
- Produces:
  - `futtat(docs_data: Path, nap: str, kliens=None) -> int` — beolvas (`kulcsszo_regresszio.json`, `tortenet.json`, `legfrissebb.json`, az utolsó ≤7 `napok/<datum>.json` `trendek`-je), betölti a tegnapi archívumot ha van, payload → elemez → artefakt → lemez: `elemzes.json` (legfrissebb) + `elemzesek/<nap>.json` + `elemzesek/index.json` frissítés. Visszaad `0`-t sikerkor. Claude-hiba → az `elemzes.json`-hoz NEM nyúl, FIGYELEM, visszaad `2`-t.
  - `main() -> int` — a belépő (env `ELEMZES_NAP` opcionális, alap: mai budapesti nap; `docs/data` a repo gyökérből).

- [ ] **Step 1: Írd meg a bukó tesztet — `futtat` sikeres úton írja az artefaktot + archívumot + indexet**

`tests/test_elemzo.py` (add):
```python
import json
from pathlib import Path


def _minimal_docs_data(tmp_path):
    dd = tmp_path / "data"
    (dd / "napok").mkdir(parents=True)
    (dd / "kulcsszo_regresszio.json").write_text(json.dumps(
        _regresszio_egy_szo("emelkedik", 1.0, True, 10.0)), encoding="utf-8")
    (dd / "tortenet.json").write_text(json.dumps(
        {"napok": [{"nap": "2026-08-22", "kulcsszavak": [{"kulcsszo": "állás", "atlag": 25.0, "csucs": 100.0}]}]}),
        encoding="utf-8")
    (dd / "legfrissebb.json").write_text(json.dumps({"top_trendek": [{"kifejezes": "eső"}]}), encoding="utf-8")
    (dd / "napok" / "index.json").write_text(json.dumps({"napok": ["2026-08-22"]}), encoding="utf-8")
    (dd / "napok" / "2026-08-22.json").write_text(json.dumps({"nap": "2026-08-22", "trendek": [{"kifejezes": "eső"}]}),
                                                  encoding="utf-8")
    return dd


def test_futtat_sikeres_ut_ir_artefaktot_archivumot_indexet(tmp_path):
    dd = _minimal_docs_data(tmp_path)
    kod = elemzo.futtat(dd, nap="2026-08-22", kliens=KamuKliens(_ai_valasz()))
    assert kod == 0
    art = json.loads((dd / "elemzes.json").read_text(encoding="utf-8"))
    assert art["nap"] == "2026-08-22"
    assert art["kulcsszavak"]["napi"]["szoveg"] == "sz"
    # archívum + index
    assert (dd / "elemzesek" / "2026-08-22.json").exists()
    idx = json.loads((dd / "elemzesek" / "index.json").read_text(encoding="utf-8"))
    assert idx["napok"] == ["2026-08-22"]
```

- [ ] **Step 2: Futtasd — bukjon**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_futtat_sikeres_ut_ir_artefaktot_archivumot_indexet -v`
Expected: FAIL — `AttributeError: ... has no attribute 'futtat'`

- [ ] **Step 3: Implementáld a `futtat`-ot (sikeres út)**

`trendfigyelo/elemzo.py` (add; a `Path`/`json` importok a fájl tetejére):
```python
import json
from pathlib import Path


def _betolt(fajl):
    p = Path(fajl)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _utolso_napok_trendek(docs_data, hany=7):
    idx = _betolt(Path(docs_data) / "napok" / "index.json") or {"napok": []}
    ki = {}
    for datum in idx["napok"][-hany:]:
        nap_adat = _betolt(Path(docs_data) / "napok" / f"{datum}.json")
        if nap_adat:
            ki[datum] = nap_adat.get("trendek", [])
    return ki


def _index_frissit(elemzesek_dir, nap):
    idx_fajl = elemzesek_dir / "index.json"
    idx = _betolt(idx_fajl) or {"napok": []}
    if nap not in idx["napok"]:
        idx["napok"].append(nap)
        idx["napok"].sort()
    seged.atomi_ir_szoveg(idx_fajl, json.dumps(idx, ensure_ascii=False, indent=0))


def futtat(docs_data, nap, kliens=None):
    docs_data = Path(docs_data)
    adatok = {
        "regresszio": _betolt(docs_data / "kulcsszo_regresszio.json") or {},
        "tortenet": _betolt(docs_data / "tortenet.json") or {},
        "legfrissebb": _betolt(docs_data / "legfrissebb.json") or {},
        "napok_trendek": _utolso_napok_trendek(docs_data),
    }
    tegnapi = _elozo_archivum(docs_data, nap)
    payload = epit_payload(
        adatok,
        tegnapi_szamok=(tegnapi or {}).get("kulcsszavak", {}).get("szamok") if tegnapi else None,
        tegnapi_top=(tegnapi or {}).get("felkapott", {}).get("top") if tegnapi else None,
    )
    ai_valasz = elemez(payload, kliens=kliens)
    art = valasz_to_artefakt(ai_valasz, payload, nap=nap, modell=MODELL)
    szoveg = json.dumps(art, ensure_ascii=False, indent=0)
    elemzesek_dir = docs_data / "elemzesek"
    elemzesek_dir.mkdir(exist_ok=True)
    seged.atomi_ir_szoveg(elemzesek_dir / f"{nap}.json", szoveg)
    seged.atomi_ir_szoveg(docs_data / "elemzes.json", szoveg)
    _index_frissit(elemzesek_dir, nap)
    return 0


def _elozo_archivum(docs_data, nap):
    """A legutolsó, `nap`-nál korábbi archivált elemzés (a nap-diffhez)."""
    idx = _betolt(Path(docs_data) / "elemzesek" / "index.json") or {"napok": []}
    korabbi = [d for d in idx["napok"] if d < nap]
    if not korabbi:
        return None
    return _betolt(Path(docs_data) / "elemzesek" / f"{max(korabbi)}.json")
```

- [ ] **Step 4: Futtasd — menjen át**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_futtat_sikeres_ut_ir_artefaktot_archivumot_indexet -v`
Expected: PASS

- [ ] **Step 5: Írd meg a bukó tesztet — fail-soft: Claude-hiba esetén az előző `elemzes.json` MARAD (lemezt nézzük)**

`tests/test_elemzo.py` (add):
```python
class HibasKliens:
    def uzenet(self, payload, modell):
        raise RuntimeError("429 szimulált")


def test_futtat_fail_soft_megorzi_az_elozo_elemzest(tmp_path):
    dd = _minimal_docs_data(tmp_path)
    regi = json.dumps({"nap": "2026-08-21", "modell": "regi"}, ensure_ascii=False)
    (dd / "elemzes.json").write_text(regi, encoding="utf-8")
    kod = elemzo.futtat(dd, nap="2026-08-22", kliens=HibasKliens())
    assert kod == 2
    # a LEMEZEN a régi maradt (SZANDEKOS-ZOLD-VAK: a lemezt nézzük, nem a visszatérést)
    a_lemezen = json.loads((dd / "elemzes.json").read_text(encoding="utf-8"))
    assert a_lemezen["nap"] == "2026-08-21"
    assert not (dd / "elemzesek" / "2026-08-22.json").exists()
```

- [ ] **Step 6: Futtasd — bukjon**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_futtat_fail_soft_megorzi_az_elozo_elemzest -v`
Expected: FAIL — a `RuntimeError` kibuborékol (nincs elkapva) → a teszt hibával áll el, nem `assert`-tel

- [ ] **Step 7: Told fail-soft-ba a `futtat` Claude-hívását**

`trendfigyelo/elemzo.py` — az `elemez` hívást csomagold be a `futtat`-ban:
```python
import logging
_log = logging.getLogger(__name__)

# ... a futtat-ban, az `ai_valasz = elemez(...)` sort cseréld erre:
    try:
        ai_valasz = elemez(payload, kliens=kliens)
    except Exception as e:                       # noqa: BLE001 — fail-soft: az elemzés nem pótolhatatlan
        _log.warning("FIGYELEM: az AI-elemzés elhasalt (%s) — az előző elemzes.json marad.", e)
        return 2
```
(A `try` a `payload = ...` UTÁN, a `valasz_to_artefakt`/lemezírás ELŐTT van, így hiba esetén semmit nem írunk.)

- [ ] **Step 8: Futtasd — menjen át + az egész fájl zöld**

Run: `.venv/bin/pytest tests/test_elemzo.py -v`
Expected: PASS

- [ ] **Step 9: Add a `main` belépőt és a vékony `elemzes.py`-t**

`trendfigyelo/elemzo.py` (add a fájl aljára):
```python
def main():
    import os
    nap = os.environ.get("ELEMZES_NAP") or seged.bp_idobelyeg(seged.most_utc())[:10]
    docs_data = Path(__file__).resolve().parent.parent / "docs" / "data"
    return futtat(docs_data, nap=nap)
```
`elemzes.py` (repo gyökér):
```python
"""Vékony belépő: a napi AI-elemzés futtatása (a trendfigyelo.elemzo modul)."""

import sys

from trendfigyelo.elemzo import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 10: Írd meg a bukó tesztet — `main` a mai napra fut (env-nappal)**

`tests/test_elemzo.py` (add):
```python
def test_main_env_nappal_fut(tmp_path, monkeypatch):
    # a main a docs/data-t a repo gyökérből veszi; itt csak azt igazoljuk, hogy az env-nap átmegy
    hivott = {}
    monkeypatch.setattr(elemzo, "futtat", lambda docs_data, nap, kliens=None: hivott.setdefault("nap", nap) or 0)
    monkeypatch.setenv("ELEMZES_NAP", "2026-08-22")
    assert elemzo.main() == 0
    assert hivott["nap"] == "2026-08-22"
```

- [ ] **Step 11: Futtasd — menjen át (a `main` már létezik a Step 9-ből)**

Run: `.venv/bin/pytest tests/test_elemzo.py::test_main_env_nappal_fut -v`
Expected: PASS

- [ ] **Step 12: Futtasd a TELJES pytest suite-ot (SOROS mérvadó)**

Run: `.venv/bin/pytest -q`
Expected: PASS (a meglévő 361 + az új elemzo-tesztek)

- [ ] **Step 13: Commit**

```bash
git add trendfigyelo/elemzo.py elemzes.py tests/test_elemzo.py
git commit
```
Üzenet (jóváhagyásra): `feat(elemzo): futtat — archívum/index + fail-soft + belépő (elemzes.py)`

---

### Task 5: Workflow — `elemzes.yml` (`workflow_run` a napi.yml után)

**Files:**
- Create: `.github/workflows/elemzes.yml`

**Interfaces:**
- Consumes: `elemzes.py` belépő (Task 4), `ANTHROPIC_API_KEY` repo-secret.
- Produces: külön commit `docs/data/elemzes.json` + `docs/data/elemzesek`-re a napi.yml sikere után.

- [ ] **Step 1: Írd meg a workflow-t**

`.github/workflows/elemzes.yml`:
```yaml
name: Napi AI-elemzés

on:
  workflow_run:
    workflows: ["Napi trendgyűjtés"]   # a napi.yml `name`-je
    types: [completed]
  workflow_dispatch: {}                # kézi teszt

permissions:
  contents: write

concurrency:
  group: napi-futtatas                 # NE fusson a gyűjtéssel párban
  cancel-in-progress: false

jobs:
  elemzes:
    # csak a napi.yml SIKERES lefutása után (kézi indításnál a feltétel átugorható)
    if: ${{ github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout (a friss, épp commitolt adat)
        uses: actions/checkout@v4
        with:
          ref: main

      - name: Python beállítása
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Függőségek telepítése
        run: pip install -r requirements.txt

      - name: Elemzés futtatása
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          set -o pipefail
          python elemzes.py 2>&1 | tee elemzes.log

      - name: Változások commitolása (CSAK az elemzés-fájlok, KÜLÖN commit)
        if: always() && github.ref == 'refs/heads/main'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git pull --rebase --autostash || true
          git add docs/data/elemzes.json docs/data/elemzesek
          if git diff --staged --quiet; then
            echo "Nincs elemzés-változás — nincs commit."
          else
            git commit -m "adat: napi AI-elemzés ($(date -u +%Y-%m-%dT%H:%MZ))"
            git push
          fi

      - name: Artefakt (a log + az elemzés-fájlok — mindig)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: elemzes-${{ github.run_id }}
          retention-days: 14
          path: |
            elemzes.log
            docs/data/elemzes.json
            docs/data/elemzesek/**
```

- [ ] **Step 2: Strukturális ellenőrzés (a YAML érvényes és a kulcs-mezők jók)**

Run:
```bash
grep '^name:' .github/workflows/napi.yml   # igazold: pontosan "Napi trendgyűjtés"
python -c "import yaml; d=yaml.safe_load(open('.github/workflows/elemzes.yml')); \
assert d['on']['workflow_run']['workflows']==['Napi trendgyűjtés'], 'a trigger-név nem egyezik a napi.yml name-jével'; \
assert d['concurrency']['group']=='napi-futtatas', 'közös concurrency-csoport kell'; \
lepesek=[s.get('name') for s in d['jobs']['elemzes']['steps']]; \
assert any('Elemzés futtatása'==n for n in lepesek) and any('commitolása' in (n or '') for n in lepesek); \
print('OK, lépések:', lepesek)"
```
Expected: kiírja a `Napi trendgyűjtés` sort és `OK, lépések: [...]`, nincs `AssertionError`. (Ha a `napi.yml` `name:`-je más, javítsd az `elemzes.yml` `workflows:` értékét arra.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/elemzes.yml
git commit
```
Üzenet (jóváhagyásra): `feat(elemzes-wf): napi AI-elemzés workflow — workflow_run a napi.yml után, külön commit`

> **USER-ELŐFELTÉTEL:** a repo `Settings → Secrets and variables → Actions → New repository secret`: `ANTHROPIC_API_KEY`. Enélkül a `workflow_dispatch` kézi teszt megmutatja a hiányt (auth-hiba a logban), de a fail-soft miatt nem tör el a meglévő oldal.

---

### Task 6: Frontend — „Elemzés" fül + renderer + menü + archívum-választó

**Files:**
- Create: `docs/elemzes.html`, `docs/js/elemzes.js`
- Modify: `docs/index.html`, `docs/adatokrol.html` (menü 2 → 3 fül)
- Test: `e2e/elemzes.spec.js`, `e2e/menu.spec.js` (a 3-fül-igazítás)

**Interfaces:**
- Consumes: `docs/data/elemzes.json` (legfrissebb) és `docs/data/elemzesek/<datum>.json` + `index.json` (archívum); a `naptar_epit(honap, elso_ho, utolso_ho, cellaAllapot)` helper (`docs/js/app.js:454`) — az `elemzes.js` ezt újrahasznosítja a nap-választóhoz.

- [ ] **Step 1: Bővítsd a menüt 3 fülre — index.html**

`docs/index.html` — a `#fomenu` blokk (10–13. sor környéke) — add az „Elemzés" linket a Trendek és az „Az adatokról" közé:
```html
  <nav id="fomenu" aria-label="Fő menü">
    <a href="index.html" aria-current="page">Trendek</a>
    <a href="elemzes.html">Elemzés</a>
    <a href="adatokrol.html">Az adatokról</a>
  </nav>
```

- [ ] **Step 2: Bővítsd a menüt az adatokrol.html-ben is (ugyanaz a 3-fül nav, az aktív = Az adatokról)**

`docs/adatokrol.html` — a `#fomenu` blokkban legyen a 3 link, `aria-current="page"` az `adatokrol.html`-en.

- [ ] **Step 3: Igazítsd a bukó smoke-tesztet — a menü immár 3 fül**

`e2e/menu.spec.js` — az első teszt `toHaveCount(2)` → `toHaveCount(3)`, és add az új link-ellenőrzést:
```javascript
  await expect(linkek).toHaveCount(3);
  await expect(page.locator('#fomenu a[href="elemzes.html"]')).toHaveText("Elemzés");
```

- [ ] **Step 4: Futtasd a menü-tesztet — bukjon (a linkek még nem 3-asak minden oldalon / nincs elemzes.html)**

Run: `npx playwright test e2e/menu.spec.js --workers=1`
Expected: FAIL — a `toHaveCount(3)` vagy az `elemzes.html` link hiányzik valamelyik oldalon

- [ ] **Step 5: Hozd létre az `elemzes.html`-t (az adatokrol.html szerkezeti mintájára)**

`docs/elemzes.html` — a `#fomenu` (Elemzés az aktív), egy `#elemzes` konténer, egy `#elemzes-naptar` a nap-választóhoz, `#labresz` üres lábléc, és a `docs/js/elemzes.js` betöltése. A `<head>`/CSS az `adatokrol.html`-ből másolva (ugyanaz a téma).
```html
<!doctype html>
<html lang="hu">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Elemzés — Magyar trendfigyelő</title>
  <link rel="stylesheet" href="css/stilus.css" />
</head>
<body>
  <nav id="fomenu" aria-label="Fő menü">
    <a href="index.html">Trendek</a>
    <a href="elemzes.html" aria-current="page">Elemzés</a>
    <a href="adatokrol.html">Az adatokról</a>
  </nav>
  <main id="elemzes">
    <h1>Napi elemzés</h1>
    <div id="elemzes-fejlec"></div>
    <div id="elemzes-naptar"></div>
    <section id="elemzes-tartalom" aria-live="polite"></section>
  </main>
  <footer id="labresz"></footer>
  <script src="js/app.js"></script>
  <script src="js/elemzes.js"></script>
</body>
</html>
```
> Igazold a CSS-fájl nevét: `ls docs/css/` — ha nem `stilus.css`, írd a valósat (az `adatokrol.html` `<link>`-jét másold).

- [ ] **Step 6: Írd meg a renderert — `docs/js/elemzes.js`**

`docs/js/elemzes.js` — betölti a `data/elemzes.json`-t (vagy archívum-napot), és kirajzolja a szekciókat: „Mi változott ma?" (VALÓS diff + AI), Kulcsszavak (VALÓS csempék + napi/teljes/hét), Felkapott (VALÓS top + napi/hét). A VALÓS és az `elmeleti` réteg megkülönböztető osztállyal. A nap-választó a `naptar_epit`-tel (app.js) az `elemzesek/index.json` napjaira.
```javascript
"use strict";

async function elemzes_betolt(datum) {
  const url = datum ? `data/elemzesek/${datum}.json` : "data/elemzes.json";
  const r = await fetch(url);
  if (!r.ok) throw new Error("nem elérhető: " + url);
  return r.json();
}

function szekcio_elem(cim, szekcio) {
  const box = document.createElement("section");
  box.className = "elemzes-szekcio";
  const h = document.createElement("h3");
  h.textContent = cim;
  box.appendChild(h);
  if (szekcio && szekcio.szoveg) {
    const p = document.createElement("p");
    p.className = "elemzes-szoveg";
    p.textContent = szekcio.szoveg;
    box.appendChild(p);
  }
  (szekcio && szekcio.megfigyelesek || []).forEach((m) => {
    const li = document.createElement("div");
    li.className = "elemzes-megfigyeles";        // VALÓS/tényszerű réteg
    li.textContent = m;
    box.appendChild(li);
  });
  (szekcio && szekcio.elmeleti || []).forEach((e) => {
    const li = document.createElement("div");
    li.className = "elemzes-elmeleti";           // ELMÉLETI — feltételezés, külön jelölés
    li.textContent = "feltételezés: " + e;
    box.appendChild(li);
  });
  return box;
}

function valos_kulcsszo_csempek(szamok) {
  const wrap = document.createElement("div");
  wrap.className = "elemzes-csempek";
  (szamok || []).forEach((s) => {
    const c = document.createElement("div");
    c.className = "elemzes-csempe irany-" + (s.irany || "ismeretlen");
    c.textContent = `${s.szo}: ${s.irany} (mai ${s.mai_ertek ?? "–"}, csúcs ${s.csucs ?? "–"})`;
    wrap.appendChild(c);
  });
  return wrap;
}

function rajzol(art) {
  const t = document.getElementById("elemzes-tartalom");
  t.textContent = "";
  document.getElementById("elemzes-fejlec").textContent =
    `Elemzés — ${art.nap} (${art.modell})`;

  // Mi változott ma?
  const valt = document.createElement("div");
  const d = art.valtozas.diff;
  const valos = document.createElement("p");
  valos.className = "elemzes-megfigyeles";
  valos.textContent = d.van_elozo
    ? `Irányt váltott: ${d.irany_valtok.map((v) => v.szo).join(", ") || "–"} · új felkapott: ${d.felkapott_uj.join(", ") || "–"} · eltűnt: ${d.felkapott_eltunt.join(", ") || "–"}`
    : "Nincs összevethető előző nap.";
  valt.appendChild(valos);
  valt.appendChild(szekcio_elem("Mi változott ma?", art.valtozas));
  t.appendChild(valt);

  // Kulcsszavak
  t.appendChild(valos_kulcsszo_csempek(art.kulcsszavak.szamok));
  t.appendChild(szekcio_elem("Kulcsszavak — mit látunk ma", art.kulcsszavak.napi));
  t.appendChild(szekcio_elem("Kulcsszavak — teljes kép", art.kulcsszavak.teljes_kep));
  t.appendChild(szekcio_elem("Kulcsszavak — 1 hét", art.kulcsszavak.het));

  // Felkapott
  t.appendChild(szekcio_elem("Felkapott — napi", art.felkapott.napi));
  t.appendChild(szekcio_elem("Felkapott — heti összesítés", art.felkapott.het));
}

async function elemzes_indit() {
  try {
    rajzol(await elemzes_betolt(null));
  } catch (e) {
    document.getElementById("elemzes-tartalom").textContent =
      "Az elemzés jelenleg nem érhető el.";
  }
  // archívum-választó (naptar_epit az app.js-ből) — opcionális, ha van index.json
  try {
    const idx = await (await fetch("data/elemzesek/index.json")).json();
    epit_archivum_valaszto(idx.napok);
  } catch (e) { /* nincs archívum — a fül a legfrissebbet mutatja */ }
}

function epit_archivum_valaszto(napok) {
  if (!napok || !napok.length || typeof naptar_epit !== "function") return;
  const el = document.getElementById("elemzes-naptar");
  const elso = napok[0].slice(0, 7), utolso = napok[napok.length - 1].slice(0, 7);
  const keszlet = new Set(napok);
  el.appendChild(naptar_epit(utolso, elso, utolso, function (iso) {
    return keszlet.has(iso) ? "valaszthato" : "tiltott";
  }));
  el.addEventListener("click", async (ev) => {
    const cella = ev.target.closest("[data-iso]");
    if (cella && keszlet.has(cella.getAttribute("data-iso"))) {
      rajzol(await elemzes_betolt(cella.getAttribute("data-iso")));
    }
  });
}

document.addEventListener("DOMContentLoaded", elemzes_indit);
```
> **Igazold a `naptar_epit` cella-interfészét** (`docs/js/app.js:454`): a `cellaAllapot` visszatérési értékei és a kattintható cella `data-*` attribútuma (a fenti `data-iso` feltételezés). Ha az app.js más attribútumot/állapotnevet használ, igazítsd a `epit_archivum_valaszto`-t a valósághoz (ez a Task egyetlen, kódból igazolandó pontja).

- [ ] **Step 7: Futtasd a menü-tesztet — most menjen át**

Run: `npx playwright test e2e/menu.spec.js --workers=1`
Expected: PASS (3 fül minden oldalon)

- [ ] **Step 8: Írd meg az `elemzes.spec.js` renderer-tesztet fixture-rel**

`e2e/elemzes.spec.js` — mockold a `data/elemzes.json`-t egy fixture-rel, és igazold, hogy a VALÓS és az ELMÉLETI réteg külön jelenik meg:
```javascript
const { test, expect } = require("@playwright/test");

const FIXTURE = {
  frissitve: "2026-08-22T20:00:00+00:00", modell: "claude-sonnet-5", nap: "2026-08-22",
  valtozas: { diff: { van_elozo: true, irany_valtok: [{ szo: "állás" }], mozgok: [], felkapott_uj: ["eső"], felkapott_eltunt: [] },
              szoveg: "Változás-összefoglaló.", megfigyelesek: ["állás emelkedésbe váltott"], elmeleti: ["időjárás hathat"] },
  kulcsszavak: { szamok: [{ szo: "állás", irany: "emelkedik", mai_ertek: 10, csucs: 100 }],
                 napi: { szoveg: "Napi.", megfigyelesek: [], elmeleti: [] },
                 teljes_kep: { szoveg: "Teljes.", megfigyelesek: [], elmeleti: [] },
                 het: { szoveg: "Heti.", megfigyelesek: [], elmeleti: [] } },
  felkapott: { top: [{ kifejezes: "eső", volumen: "20000" }],
               napi: { szoveg: "Felk. napi.", megfigyelesek: [], elmeleti: [] },
               het: { szoveg: "Felk. heti.", megfigyelesek: [], elmeleti: [] } },
};

test("Elemzés fül: VALÓS és ELMÉLETI réteg külön, aktív fül", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: FIXTURE }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Elemzés");
  await expect(page.locator("#elemzes-fejlec")).toContainText("2026-08-22");
  await expect(page.locator(".elemzes-megfigyeles").first()).toContainText("állás emelkedésbe váltott");
  await expect(page.locator(".elemzes-elmeleti").first()).toContainText("feltételezés:");
  await expect(page.locator(".elemzes-csempe")).toContainText("állás");
});
```

- [ ] **Step 9: Futtasd — bukjon, majd (a Step 5–6 után) menjen át**

Run: `npx playwright test e2e/elemzes.spec.js --workers=1`
Expected: a Step 5–6 megléte után PASS. (Ha a fejlesztő a tesztet a renderer előtt írja, először FAIL: nincs `elemzes.html` / `.elemzes-elmeleti`.)

- [ ] **Step 10: Add a minimális CSS-osztályokat (VALÓS vs ELMÉLETI vizuális szétválasztás)**

`docs/css/stilus.css` (vagy a valós CSS-fájl) — add:
```css
.elemzes-megfigyeles { border-left: 3px solid #3366cc; padding-left: .6em; margin: .3em 0; }
.elemzes-elmeleti { border-left: 3px dashed #999; padding-left: .6em; margin: .3em 0; color: #555; font-style: italic; }
.elemzes-csempe { display: inline-block; border: 1px solid #e3e3e3; border-radius: 6px; padding: .3em .6em; margin: .2em; }
```
> Szemle-köteles (SZEMLE-SZABÁLY): a VALÓS (tömör kék vonal) és az ELMÉLETI (szaggatott, dőlt) réteg VIZUÁLISAN egyértelműen elkülönül. A pontos színek illeszkedjenek a meglévő témához (`ADAT_VONAL_SZIN` = `#3366cc`).

- [ ] **Step 11: Futtasd a TELJES Playwright suite-ot (SOROS)**

Run: `npx playwright test --workers=1`
Expected: PASS (a meglévő 128 + az új elemzés-tesztek; a menü-teszt a 3-fülre igazítva)

- [ ] **Step 12: Élő vizuális szemle (SZEMLE-SZABÁLY — a DOM-belső egyetlen őre)**

Regeneráld/tölts be egy valós vagy fixture `elemzes.json`-t localhost-on, és nézd meg: a „Mi változott ma?" olvasható; a VALÓS csempék és az AI-szöveg elkülönül; az `ELMÉLETI` tételek „feltételezés"-ként, megkülönböztetve jelennek meg; az archívum-választó a meglévő naptár-stílusban ül. Bármi eltér → javítsd a szeleten belül (ZOLD-NEM-SZALLIT).

- [ ] **Step 13: Commit**

```bash
git add docs/elemzes.html docs/js/elemzes.js docs/index.html docs/adatokrol.html \
        docs/css/stilus.css e2e/elemzes.spec.js e2e/menu.spec.js
git commit
```
Üzenet (jóváhagyásra): `feat(elemzes-ui): „Elemzés" fül + renderer (VALÓS/ELMÉLETI) + 3-fül menü + archívum-választó`

---

## Záró ellenőrzés (a leszállítás előtt)

- [ ] **TELJES SOROS suite:** `.venv/bin/pytest -q` + `npx playwright test --workers=1` — mind zöld.
- [ ] **MUTÁCIÓ == 1:** `grep -rn "MUTÁCIÓ" docs/js docs/css e2e tests trendfigyelo | wc -l` → 1.
- [ ] **A pótolhatatlan ág érintetlen:** `git diff --name-only origin/main` NEM tartalmaz `kulcsszo_nyers.json`/`kulcsszo_lanc.json`-t.
- [ ] **Leltár-frissítés** a lezáró commitban (új tétel: ELEMZES-FUL — LESZÁLLÍTVA; invariáns MÉRÉSSEL, önhivatkozó hash nélkül).
- [ ] **USER-előfeltétel jelzése:** az `ANTHROPIC_API_KEY` secret hiányában a workflow kézi (`workflow_dispatch`) tesztje mutatja a hiányt; a fail-soft miatt az oldal nem tör el.

## Self-Review jegyzet (a terv írója)

- **Spec-fedés:** §3.1 (elemzo.py 4 rész) → Task 1–4; §3.2 nap-diff → Task 2; §3.3 workflow → Task 5; §3.4 frontend + archívum → Task 6; §2.1/§2.2 (VALÓS/ELMÉLETI) → a RENDSZER_PROMPT (Task 3) + a renderer két rétege (Task 6); §5 artefakt-alak → Task 3–4; fail-soft → Task 4. Nincs fedetlen szekció.
- **Kódból igazolandó, nem fabrikált pont** (a terv explicit jelzi): (a) a `naptar_epit` cella-`data-*`/állapot-interfésze (Task 6 Step 6); (b) a CSS-fájl neve (Task 6 Step 5); (c) a `napi.yml` `name:` pontos egyezése (Task 5 Step 2). Ezek a meglévő kód olvasásával zárhatók, nem tippel a terv.
