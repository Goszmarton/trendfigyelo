# Esti AI-elemzés reggel/este/teljes-nap felkapott bontás — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A napi AI-elemzés felkapott-része 2 próza (napi+heti) helyett 4-re bomlik: Reggeli (9:00) · Esti (21:00) · Teljes nap (a nap íve) · Heti — a reggeli/esti szegmentált napfájlból, visszafelé kompatibilisen.

**Architecture:** Új Python-adatfüggvények (`_ma_szegmensek`, `_felkapott_szegmensek`) a `napok/<nap>.json` reggel/este szegmenseiből + egy valós reggel↔este diff; a payload/séma/prompt/artefakt bővül; a frontend 4 szekciót rajzol az új artefakt-alaknál és a régi 2-t a réginél. A kulcsszó/YouTube/nap-diff út bájt-azonos.

**Tech Stack:** Python 3.12 (elemzo.py, pytest), vanília JS (elemzes.js, Playwright e2e).

**Spec:** `docs/superpowers/specs/2026-08-31-elemzes-reggel-este-felkapott-design.md`

## Global Constraints

- **Determinizmus:** minden SZÁM/lista a Python-kódból; az AI CSAK prózát ír. A hiányzó-szegmens jelzés DETERMINISZTIKUS (Python canned), NEM AI-próza.
- **Visszafelé kompatibilitás:** a régi `elemzesek/<nap>.json` `felkapott={napi,het}` artefaktokat NEM írjuk át; a frontend detektálja az alakot (`art.felkapott.reggel` → új; különben régi).
- **Bájt-azonos marad:** `kulcsszavak`, `youtube`, `valtozas`/`nap_diff` út — nem változtatjuk a viselkedésüket.
- **Frontend determinizmus:** böngésző-kódban TILOS `new Date()`/`Date.now()`.
- **git add NÉV SZERINT** — soha `-A`/`.`; a gyökér `ATADAS-2026-08-18.txt` SOHA nem stagelt.
- **Commit-trailerek** minden commiten:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN`
- **Push KÜLÖN, kapuzott kör** (fetch → divergencia → rebase → push → rev-list 0 0), user-jóváhagyással. A terv NEM pushol.
- **SOROS suite:** `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`. TDD valódi RED→GREEN, MUTÁCIÓ=1.
- **Szegmens-kulcsok:** `"reggel"`, `"este"`. Frontend szekció-címek: „Felkapott — reggeli (9:00)", „Felkapott — esti (21:00)", „Felkapott — a nap íve", „Felkapott — heti összesítés".

---

### Task 1: Szegmens-adatfüggvények (`_ma_szegmensek` + `_felkapott_szegmensek`)

**Files:**
- Modify: `trendfigyelo/elemzo.py` (új függvények a `_felkapott` közelébe, ~182 után)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: `json_export._nap_szegmensek` (meglévő), `elemzo._betolt` (meglévő).
- Produces: `_ma_szegmensek(docs_data, nap) -> dict` — `{"reggel":[...], "este":[...]}` csak a jelenlévő szegmensekkel; hiányzó fájl → `{}`.
- Produces: `_felkapott_szegmensek(ma_szegmensek, legfrissebb) -> dict` — `{"reggel_top":[...], "este_top":[...], "reggel_este_diff":{"uj_estere":[...],"eltunt_estere":[...],"megmaradt":[...]}, "van_reggel":bool, "van_este":bool}`. `este` hiánya → `legfrissebb.top_trendek` fallback.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_elemzo.py`:

```python
def test_ma_szegmensek_reggel_este(tmp_path):
    napok = tmp_path / "napok"; napok.mkdir()
    (napok / "2026-08-31.json").write_text(json.dumps({
        "nap": "2026-08-31",
        "reggel": {"trendek": [{"kifejezes": "r1"}], "frissitve": "x"},
        "este": {"trendek": [{"kifejezes": "e1"}, {"kifejezes": "e2"}], "frissitve": "y"},
    }), encoding="utf-8")
    ms = elemzo._ma_szegmensek(tmp_path, "2026-08-31")
    assert [t["kifejezes"] for t in ms["reggel"]] == ["r1"]
    assert [t["kifejezes"] for t in ms["este"]] == ["e1", "e2"]


def test_ma_szegmensek_regi_lapos_este(tmp_path):
    napok = tmp_path / "napok"; napok.mkdir()
    (napok / "2026-08-20.json").write_text(json.dumps({"nap": "2026-08-20", "trendek": [{"kifejezes": "x"}]}), encoding="utf-8")
    ms = elemzo._ma_szegmensek(tmp_path, "2026-08-20")
    assert "reggel" not in ms
    assert [t["kifejezes"] for t in ms["este"]] == ["x"]


def test_ma_szegmensek_hianyzo_fajl(tmp_path):
    assert elemzo._ma_szegmensek(tmp_path, "2026-08-31") == {}


def test_felkapott_szegmensek_diff():
    ms = {"reggel": [{"kifejezes": "a", "volumen": "5"}, {"kifejezes": "b"}],
          "este": [{"kifejezes": "b"}, {"kifejezes": "c"}]}
    r = elemzo._felkapott_szegmensek(ms, {})
    assert [t["kifejezes"] for t in r["reggel_top"]] == ["a", "b"]
    assert [t["kifejezes"] for t in r["este_top"]] == ["b", "c"]
    assert r["reggel_este_diff"] == {"uj_estere": ["c"], "eltunt_estere": ["a"], "megmaradt": ["b"]}
    assert r["van_reggel"] is True and r["van_este"] is True


def test_felkapott_szegmensek_este_fallback_legfrissebb():
    # nincs napfájl-este → a legfrissebb.top_trendek a settled esti kép
    r = elemzo._felkapott_szegmensek({"reggel": [{"kifejezes": "a"}]},
                                     {"top_trendek": [{"kifejezes": "z"}]})
    assert [t["kifejezes"] for t in r["este_top"]] == ["z"]
    assert r["van_reggel"] is True and r["van_este"] is True


def test_felkapott_szegmensek_csak_este():
    r = elemzo._felkapott_szegmensek({"este": [{"kifejezes": "e"}]}, {})
    assert r["van_reggel"] is False and r["van_este"] is True
    assert r["reggel_top"] == []
    assert r["reggel_este_diff"]["uj_estere"] == ["e"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -k "ma_szegmensek or felkapott_szegmensek" -q`
Expected: FAIL (`_ma_szegmensek`/`_felkapott_szegmensek` nem létezik).

- [ ] **Step 3: Implement**

In `trendfigyelo/elemzo.py`, add after `_felkapott` (after line 204):

```python
def _ma_szegmensek(docs_data, nap):
    """A mai nap (nap) reggel+este szegmenseinek trend-listái a napok/<nap>.json-ból.

    A json_export._nap_szegmensek-kel normalizál (a régi {nap,trendek} este-ként).
    Visszaad: {"reggel":[...], "este":[...]} — csak a JELENLÉVŐ szegmensekkel; hiányzó fájl → {}.
    """
    from . import json_export
    nap_adat = _betolt(Path(docs_data) / "napok" / f"{nap}.json")
    szeg = json_export._nap_szegmensek(nap_adat or {})
    ki = {}
    for s in ("reggel", "este"):
        if s in szeg and isinstance(szeg[s].get("trendek"), list):
            ki[s] = szeg[s]["trendek"]
    return ki


def _felkapott_szegmensek(ma_szegmensek, legfrissebb):
    """A reggeli/esti pillanatkép trend-listái + a reggel↔este diff (a "nap íve"-hez).

    este hiánya esetén a legfrissebb.top_trendek a settled esti kép (fallback).
    """
    def _top(trendek):
        return [{"kifejezes": t.get("kifejezes"), "volumen": t.get("volumen"),
                 "novekedes_pct": t.get("novekedes_pct"), "temak": t.get("temak", []),
                 "hirek": t.get("hirek", [])} for t in (trendek or [])]
    ms = ma_szegmensek if isinstance(ma_szegmensek, dict) else {}
    reggel = ms.get("reggel")
    este = ms.get("este")
    if este is None:
        este = legfrissebb.get("top_trendek", []) if isinstance(legfrissebb, dict) else []
    reggel_top, este_top = _top(reggel), _top(este)
    reggel_kif = {t["kifejezes"] for t in reggel_top if t.get("kifejezes")}
    este_kif = {t["kifejezes"] for t in este_top if t.get("kifejezes")}
    return {
        "reggel_top": reggel_top,
        "este_top": este_top,
        "reggel_este_diff": {
            "uj_estere": sorted(este_kif - reggel_kif),
            "eltunt_estere": sorted(reggel_kif - este_kif),
            "megmaradt": sorted(reggel_kif & este_kif),
        },
        "van_reggel": bool(reggel_top),
        "van_este": bool(este_top),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -q`
Expected: PASS (az összes, a meglévők is).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "$(cat <<'EOF'
feat(elemzo): reggel/este szegmens-adatfüggvények + reggel↔este diff

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 2: Payload-bekötés (`epit_payload` + `futtat`)

**Files:**
- Modify: `trendfigyelo/elemzo.py` — `epit_payload` (234–250), `futtat` `adatok` dict (383–391)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: Task 1 `_ma_szegmensek`, `_felkapott_szegmensek`.
- Produces: `payload["felkapott"]` mostantól tartalmazza a `reggel_top, este_top, reggel_este_diff, van_reggel, van_este` kulcsokat is (a meglévő `top, het` MELLETT). `futtat` az `adatok["ma_szegmensek"]`-et tölti a `napok/<nap>.json`-ból.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_elemzo.py`:

```python
def test_epit_payload_felkapott_szegmensek(tmp_path):
    # a ma_szegmensek az adatok-ból jön (futtat tölti); itt közvetlenül adjuk
    adatok = {
        "regresszio": {}, "tortenet": {},
        "legfrissebb": {"top_trendek": [{"kifejezes": "e1"}]},
        "napok_trendek": {},
        "ma_szegmensek": {"reggel": [{"kifejezes": "r1"}], "este": [{"kifejezes": "e1"}]},
        "lanc": {},
    }
    p = elemzo.epit_payload(adatok)
    fk = p["felkapott"]
    assert "top" in fk and "het" in fk                    # a régi kulcsok maradnak
    assert [t["kifejezes"] for t in fk["reggel_top"]] == ["r1"]
    assert [t["kifejezes"] for t in fk["este_top"]] == ["e1"]
    assert fk["van_reggel"] is True and fk["van_este"] is True
    assert fk["reggel_este_diff"]["uj_estere"] == ["e1"]  # e1 este-ben, reggel-ben nincs
```

Also add an integration check to the existing `_minimal_docs_data` fixture path: if the fixture writes a `napok/<nap>.json`, assert `futtat` loads `ma_szegmensek`. If the fixture does not create napok files, ADD a segmented `napok/<nap>.json` to `_minimal_docs_data` and assert the artifact's `felkapott` gets `reggel_top` (this is covered end-to-end by Task 4's test; here just verify `epit_payload` wiring).

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -k "epit_payload_felkapott_szegmensek" -q`
Expected: FAIL (`fk["reggel_top"]` KeyError — `epit_payload` még nem fűzi be).

- [ ] **Step 3: Implement**

In `epit_payload` (line 238), a `felkapott = _felkapott(...)` UTÁN, a `valtozas = ...` ELÉ:

```python
    felkapott = _felkapott(adatok.get("legfrissebb", {}), adatok.get("napok_trendek", {}))
    felkapott.update(_felkapott_szegmensek(adatok.get("ma_szegmensek", {}), adatok.get("legfrissebb", {})))
    valtozas = nap_diff(szamok, tegnapi_szamok, felkapott["top"], tegnapi_top)
```

In `futtat` `adatok` dict (383–391), add a kulcsot (a `napok_trendek` sor mellé):

```python
        "ma_szegmensek": _ma_szegmensek(docs_data, nap),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "$(cat <<'EOF'
feat(elemzo): a felkapott payload megkapja a reggel/este szegmenseket

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 3: Séma + prompt (`_valasz_sema` felkapott 4-mezős + `RENDSZER_PROMPT` keret)

**Files:**
- Modify: `trendfigyelo/elemzo.py` — `_valasz_sema` felkapott blokk (267–269), `RENDSZER_PROMPT` (21–51)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Produces: `_valasz_sema(...)` felkapott blokkja `required=["reggel","este","teljes_nap","het"]`, mind próza (`_szekcio_sema`). A `kulcsszavak`/`youtube` blokk VÁLTOZATLAN.
- Produces: `RENDSZER_PROMPT` egy új (9) szabállyal a felkapott négy bekezdéséről.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_elemzo.py`:

```python
def test_valasz_sema_felkapott_negy_mezo():
    sema = elemzo._valasz_sema()
    fk = sema["properties"]["felkapott"]
    assert set(fk["required"]) == {"reggel", "este", "teljes_nap", "het"}
    assert set(fk["properties"]) == {"reggel", "este", "teljes_nap", "het"}


def test_rendszer_prompt_felkapott_negy_bekezdes():
    p = elemzo.RENDSZER_PROMPT.lower()
    assert "reggeli" in p and "esti" in p and "nap íve" in p
```

Also SEARCH `tests/test_elemzo.py` for any existing assertion that the felkapott schema has `napi`/`het` and update it to the new keys.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -k "valasz_sema_felkapott or rendszer_prompt_felkapott" -q`
Expected: FAIL (a séma még `{napi,het}`; a prompt nem említi a négy bekezdést).

- [ ] **Step 3: Implement**

Replace the felkapott block in `_valasz_sema` (267–269):

```python
        "felkapott": {"type": "object", "additionalProperties": False,
                      "required": ["reggel", "este", "teljes_nap", "het"],
                      "properties": {"reggel": sz, "este": sz, "teljes_nap": sz, "het": sz}},
```

Append to `RENDSZER_PROMPT` (a `(8)` szabály után, a záró `")"` elé — a záró idézőjelet a `(8)` utolsó sorából told át):

```python
    "(9) A felkapott (napi Google trend-keresések) részt NÉGY külön bekezdésben írod: a "
    "REGGELI pillanatkép (mi pörög reggel 9-kor), az ESTI pillanatkép (mi pörög este 9-kor), a "
    "NAP ÍVE (mi lett estére új, mi halványult el, mi tartott ki egész nap — a nap dinamikája, "
    "nem a két lista újramondása), és a HETI kép (a több napon vissza-visszatérő szavak). Ha "
    "egy pillanatkép hiányzik, egy rövid tényszerű mondattal jelzed, nem találsz ki adatot."
```

> Implementálói megjegyzés: a `RENDSZER_PROMPT` egy zárójeles string-konkatenáció; a (8) szabály utolsó sora `...vonatkozik."` — a `)` a végén. Told a `)`-t az új (9) blokk UTÁNRA, és a (8) utolsó sorának végi `"`-t tartsd meg. Ne törd el a stringet.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -q`
Expected: PASS (a séma-teszt + prompt-teszt zöld; a meglévő `test_rendszer_prompt_folyo_proza_es_tiltas` is marad).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "$(cat <<'EOF'
feat(elemzo): séma+prompt — felkapott 4 bekezdés (reggel/este/nap íve/heti)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 4: Artefakt + determinisztikus fail-soft (`valasz_to_artefakt`)

**Files:**
- Modify: `trendfigyelo/elemzo.py` — `valasz_to_artefakt` felkapott blokk (325–330)
- Modify: `tests/test_elemzo.py` — a `_ai_valasz()` helper (223) felkapott-alakja
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: Task 1/2 `payload["felkapott"]` (reggel_top, este_top, reggel_este_diff, van_reggel, van_este, top, het), Task 3 séma-alak.
- Produces: `art["felkapott"]` = `{top, reggel_top, este_top, reggel_este_diff, reggel, este, teljes_nap, het, het_valos}`. Hiányzó szegmens → a `reggel`/`este`/`teljes_nap` DETERMINISZTIKUS canned szövegre cserélődik (az AI prózáját eldobja).

- [ ] **Step 1: Update `_ai_valasz()` + write the failing tests**

First, update the `_ai_valasz()` helper (around line 223) so its `felkapott` matches the new schema:

```python
def _ai_valasz():
    sz = lambda s: {"szoveg": s}
    return {
        "valtozas": sz("valtozas-szoveg"),
        "kulcsszavak": {"napi": sz("k-napi"), "teljes_kep": sz("k-teljes"), "het": sz("k-het")},
        "felkapott": {"reggel": sz("f-reggel"), "este": sz("f-este"),
                      "teljes_nap": sz("f- iv"), "het": sz("f-het")},
    }
```

> Ha az `_ai_valasz()` youtube-változatot is tartalmaz máshol, azt ne bántsd; csak a felkapott-kulcsot igazítsd.

Then add tests:

```python
def _payload_szegmensekkel(van_reggel=True, van_este=True):
    reggel = [{"kifejezes": "r"}] if van_reggel else []
    este = [{"kifejezes": "e"}] if van_este else []
    ms = {}
    if van_reggel: ms["reggel"] = reggel
    if van_este: ms["este"] = este
    adatok = {"regresszio": {}, "tortenet": {},
              "legfrissebb": {"top_trendek": este}, "napok_trendek": {},
              "ma_szegmensek": ms, "lanc": {}}
    return elemzo.epit_payload(adatok)


def test_artefakt_felkapott_negy_szekcio():
    payload = _payload_szegmensekkel(van_reggel=True, van_este=True)
    art = elemzo.valasz_to_artefakt(_ai_valasz(), payload, nap="2026-08-31", modell="m")
    fk = art["felkapott"]
    assert fk["reggel"]["szoveg"] == "f-reggel"
    assert fk["este"]["szoveg"] == "f-este"
    assert fk["teljes_nap"]["szoveg"] == "f- iv"
    assert fk["het"]["szoveg"] == "f-het"
    assert "reggel_top" in fk and "este_top" in fk and "reggel_este_diff" in fk
    assert "het_valos" in fk


def test_artefakt_fail_soft_csak_este():
    payload = _payload_szegmensekkel(van_reggel=False, van_este=True)
    art = elemzo.valasz_to_artefakt(_ai_valasz(), payload, nap="2026-08-31", modell="m")
    fk = art["felkapott"]
    assert "nem volt reggeli" in fk["reggel"]["szoveg"].lower()      # DETERMINISZTIKUS, nem az AI
    assert "nem rajzolható" in fk["teljes_nap"]["szoveg"].lower()
    assert fk["este"]["szoveg"] == "f-este"                          # az esti marad AI-próza
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -k "artefakt_felkapott_negy or fail_soft_csak_este" -q`
Expected: FAIL (`valasz_to_artefakt` még `ai_valasz["felkapott"]["napi"]`-t olvas → KeyError, mert az `_ai_valasz()` már az új alakot adja).

- [ ] **Step 3: Implement**

Replace the felkapott block in `valasz_to_artefakt` (325–330):

```python
    fk = payload["felkapott"]
    van_reggel = fk.get("van_reggel", True)
    van_este = fk.get("van_este", True)
    reggel_szoveg = ai_valasz["felkapott"]["reggel"]
    este_szoveg = ai_valasz["felkapott"]["este"]
    teljes_nap_szoveg = ai_valasz["felkapott"]["teljes_nap"]
    if not van_reggel:
        reggel_szoveg = {"szoveg": "Ma nem volt reggeli gyűjtés, ezért a reggeli kép nem elemezhető."}
        teljes_nap_szoveg = {"szoveg": "Reggeli pillanatkép híján a nap íve (a reggeltől estig tartó elmozdulás) nem rajzolható."}
    elif not van_este:
        este_szoveg = {"szoveg": "Ma nem volt esti gyűjtés, ezért az esti kép nem elemezhető."}
        teljes_nap_szoveg = {"szoveg": "Esti pillanatkép híján a nap íve nem rajzolható."}
```

and the `art["felkapott"]` dict (325–330) becomes:

```python
        "felkapott": {
            "top": fk["top"],
            "reggel_top": fk["reggel_top"],
            "este_top": fk["este_top"],
            "reggel_este_diff": fk["reggel_este_diff"],
            "reggel": reggel_szoveg,
            "este": este_szoveg,
            "teljes_nap": teljes_nap_szoveg,
            "het": ai_valasz["felkapott"]["het"],
            "het_valos": fk["het"],
        },
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_elemzo.py -q`
Expected: PASS (az egész test_elemzo.py — a `_ai_valasz()`-t használó meglévő artefakt-tesztek is, mert a felkapott-alak most konzisztens).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "$(cat <<'EOF'
feat(elemzo): artefakt 4 felkapott szekció + determinisztikus fail-soft

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 5: Frontend render (4 szekció + visszafelé kompat)

**Files:**
- Modify: `docs/js/elemzes.js` — `rajzol` felkapott blokk (119–121)
- Test: `e2e/elemzes.spec.js`

**Interfaces:**
- Consumes: az artefakt `felkapott` alakja (új: `{reggel,este,teljes_nap,het,...}`; régi: `{napi,het,...}`).
- Produces: a Google-szegmensen belül 4 `<h3>` szekció új artefaktnál, 2 régi artefaktnál.

- [ ] **Step 1: Write the failing test**

Add to `e2e/elemzes.spec.js` (a fájl `FIXTURE`/route-mintáját követve; a régi `FIXTURE` a `felkapott:{napi,het}` alakot használja — azt HAGYD, egy külön ÚJ fixture-rel tesztelj):

```javascript
test("Elemzés fül: ÚJ felkapott 4 szekció (reggeli/esti/nap íve/heti)", async ({ page }) => {
  const UJ = {
    nap: "2026-09-01", modell: "claude-opus-4-8",
    valtozas: { diff: { irany_valtok: [], mozgok: [], felkapott_uj: [], felkapott_eltunt: [], van_elozo: false }, szoveg: "v" },
    kulcsszavak: { szamok: [], napi: { szoveg: "k1" }, teljes_kep: { szoveg: "k2" }, het: { szoveg: "k3" } },
    felkapott: {
      top: [], reggel_top: [], este_top: [], reggel_este_diff: { uj_estere: [], eltunt_estere: [], megmaradt: [] },
      reggel: { szoveg: "reggeli próza" }, este: { szoveg: "esti próza" },
      teljes_nap: { szoveg: "a nap íve próza" }, het: { szoveg: "heti próza" }, het_valos: { napok: 0, visszateroek: [] },
    },
  };
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: UJ }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — reggeli (9:00)")) .elemzes-szoveg')).toHaveText("reggeli próza");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — esti (21:00)")) .elemzes-szoveg')).toHaveText("esti próza");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — a nap íve")) .elemzes-szoveg')).toHaveText("a nap íve próza");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — heti összesítés")) .elemzes-szoveg')).toHaveText("heti próza");
  // a régi „Felkapott — napi" cím NEM jelenik meg az új alaknál
  await expect(page.locator('h3:text-is("Felkapott — napi")')).toHaveCount(0);
});

test("Elemzés fül: RÉGI felkapott {napi,het} → a mostani 2 szekció (visszafelé kompat)", async ({ page }) => {
  const REGI = {
    nap: "2026-08-22", modell: "m",
    valtozas: { diff: { irany_valtok: [], mozgok: [], felkapott_uj: [], felkapott_eltunt: [], van_elozo: false }, szoveg: "v" },
    kulcsszavak: { szamok: [], napi: { szoveg: "k1" }, teljes_kep: { szoveg: "k2" }, het: { szoveg: "k3" } },
    felkapott: { top: [], napi: { szoveg: "régi napi" }, het: { szoveg: "régi heti" }, het_valos: { napok: 0, visszateroek: [] } },
  };
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: REGI }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — napi")) .elemzes-szoveg')).toHaveText("régi napi");
  await expect(page.locator('h3:text-is("Felkapott — reggeli (9:00)")')).toHaveCount(0);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test e2e/elemzes.spec.js --workers=1 -g "ÚJ felkapott 4 szekció"`
Expected: FAIL (a render még `art.felkapott.napi`-t olvas, az új alaknál nincs → nincs 4 szekció).

- [ ] **Step 3: Implement**

Replace the felkapott render in `docs/js/elemzes.js` (119–121):

```javascript
  // Felkapott — új alak (reggel/este/teljes_nap/het) vagy régi (napi/het), visszafelé kompat
  if (art.felkapott.reggel) {
    t.appendChild(szekcio_elem("Felkapott — reggeli (9:00)", art.felkapott.reggel));
    t.appendChild(szekcio_elem("Felkapott — esti (21:00)", art.felkapott.este));
    t.appendChild(szekcio_elem("Felkapott — a nap íve", art.felkapott.teljes_nap));
    t.appendChild(szekcio_elem("Felkapott — heti összesítés", art.felkapott.het));
  } else {
    t.appendChild(szekcio_elem("Felkapott — napi", art.felkapott.napi));
    t.appendChild(szekcio_elem("Felkapott — heti összesítés", art.felkapott.het));
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx playwright test e2e/elemzes.spec.js --workers=1`
Expected: PASS (a meglévő elemzés-tesztek is — a régi `FIXTURE` a visszafelé-kompat ágon megy).

- [ ] **Step 5: Commit**

```bash
git add docs/js/elemzes.js e2e/elemzes.spec.js
git commit -m "$(cat <<'EOF'
feat(elemzes): felkapott 4 szekció render + visszafelé kompat a régi alakra

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 6: Teljes suite + leltár

**Files:**
- Modify: `docs/superpowers/leltar.md` (ha a felkapott/elemzés-kört számon tartja)
- Test: teljes SOROS suite

- [ ] **Step 1: Teljes Python suite** — `.venv/bin/python -m pytest -p no:xdist -q` → PASS.
- [ ] **Step 2: Teljes Playwright suite** — `npx playwright test --workers=1` → PASS.
- [ ] **Step 3: Leltár-invariáns fizikai mérése** — mérd a tényleges teszt-számokat és frissítsd a `docs/superpowers/leltar.md`-ben az ELEMZES-REGGEL-ESTE kört (új LESZÁLLÍTVA sor + a `kész`/`törzs`/invariáns MÉRT értékkel; ops-tétel nincs). Ha a leltár nem tart ilyen számot, jelezd és ne commitolj.
- [ ] **Step 4: Commit (ha volt leltár-változás)**

```bash
git add docs/superpowers/leltar.md
git commit -m "$(cat <<'EOF'
teszt(elemzes): leltár-invariáns a reggel/este felkapott elemzéssel (mért)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

## Önellenőrzés (a terv a spec ellen)

- **Spec §3 payload** → Task 1 (`_ma_szegmensek`, `_felkapott_szegmensek`) + Task 2 (`epit_payload`/`futtat`). ✓
- **Spec §4 séma** → Task 3. ✓
- **Spec §5 prompt** → Task 3. ✓
- **Spec §6 artefakt + §9 fail-soft** → Task 4 (determinisztikus canned felülírás). ✓
- **Spec §7 frontend + visszafelé kompat** → Task 5. ✓
- **Spec §8 időzítés (nem változik)** → nincs task (megerősítve, nem nyúlunk hozzá). ✓
- **Spec §10 tesztelés** → minden task TDD + Task 6 teljes suite. ✓
- **Type-konzisztencia:** `_felkapott_szegmensek` kulcsai (`reggel_top, este_top, reggel_este_diff, van_reggel, van_este`) végig egyeznek (Task 1 produkál → Task 2 payloadba → Task 4 artefakt olvassa); az `_ai_valasz()` felkapott-alak (Task 4) illeszkedik a sémához (Task 3) és a `valasz_to_artefakt`-olvasáshoz. A frontend `art.felkapott.reggel` detektor (Task 5) illeszkedik a Task 4 artefakt-alakhoz. ✓
- **YAGNI:** nincs nyers csempe vissza, nincs kulcsszó/YouTube-változás, nincs időzítés-változás, nincs történelmi újraszámolás. ✓
