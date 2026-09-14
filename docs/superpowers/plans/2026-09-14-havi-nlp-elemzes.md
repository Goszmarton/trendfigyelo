# Havi NLP-elemzés Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Havonta MÉLY, megbízható, pontos magyar NLP-elemzés a felkapott keresőszavakról (tokenizálás/lemmatizálás + NER országok/települések/személyek + tematikus klaszterek + értelmezés), új „Havi elemzés" füllel; a meglévő „Elemzések" fül átnevezve „Napi Elemzések"-re.

**Architecture:** Új `trendfigyelo/havi_nlp.py` (tiszta Python korpusz-építő + a meglévő `elemzo._AnthropicKliens`-mintát újrahasználó Claude-hívás strukturált JSON-nal + grounding-validáció + atomi írás). Új `docs/havi.html` + `docs/havi.js` fül (az elemzes.js render-mintájára). Nav-frissítés MIND az oldalon.

**Tech Stack:** Python (numpy/anthropic SDK — a projekt már használja), Claude Opus 4.8, Playwright/pytest.

**Spec:** docs/superpowers/specs/2026-09-14-havi-nlp-elemzes-design.md

## Global Constraints

- **CSAK a meglévő függőségek** — numpy + a MÁR használt `anthropic` SDK (elemzo.py). Semmi új Python-dep (semmi huspaCy/spaCy/fordító). Frontend: nincs `new Date()`/`Date.now()`.
- **A magyar NLP LLM-alapú** (Claude Opus 4.8, adaptive thinking), strukturált JSON `output_config` json_schema-val, az `elemzo._AnthropicKliens` mintájára (injektálható SDK teszthez, bounded retry, fail-soft). Az LLM-kimenet NEM determinista → AI-jelölés a fülön.
- **Determinizmus a tesztelt logikában:** a KORPUSZ-építés és a GROUNDING-VALIDÁCIÓ determinista (nincs random / argless `datetime.now()`); a `keszult` időbélyeg PARAMÉTERként jön (nem `datetime.now()` a tesztelt függvényben). A tesztek MOCKOLT SDK-t használnak, SOHA valódi API-hívást.
- **A pótolhatatlan adat READ-ONLY:** a `napok/*.json` (felkapott) csak OLVASVA; a kimenet külön `docs/data/havi_nlp/YYYY-MM.json` (atomi írás `json_export._ir_json`-nal).
- **A meglévő oldalak/funkciók VÁLTOZATLANOK** — a nav bővül (rename + új fül), a napi elemzés/Google/YouTube érintetlen.
- **TDD:** bukó teszt előbb (RED, futtatva), majd impl (GREEN), majd a TELJES suite: `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1` (SOROS).
- **git add NÉVRE**; `ATADAS-*.txt` és a nyers/adat-JSON-ok SOHA nem staged.
- **Commit-trailerek KÖTELEZŐK:**
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
  ```

---

### Task 1: havi_korpusz — a hónap felkapott szavainak aggregálása (tiszta Python)

**Files:**
- Create: `trendfigyelo/havi_nlp.py`
- Test: `tests/test_havi_nlp.py`

**Interfaces:**
- Produces: `havi_korpusz(docs_data, honap) -> dict` — `honap` = "YYYY-MM"; olvassa a `docs_data/napok/<honap>-*.json`-okat, a `reggel`+`este` `trendek`-ből aggregál. Visszaad:
  `{"honap", "napok": <hány napfájl>, "egyedi_szo": N, "szavak": [{"kifejezes","gyakorisag","max_volumen","temak":[...],"hirek":[...]}]}` (gyakoriság szerint csökkenő).

- [ ] **Step 1: Write the failing test**
```python
import json
from trendfigyelo import havi_nlp

def _napfajl(tmp, nap, reggel_szavak, este_szavak=None):
    d = {"nap": nap, "reggel": {"trendek": reggel_szavak}}
    if este_szavak is not None:
        d["este"] = {"trendek": este_szavak}
    (tmp / "napok").mkdir(exist_ok=True)
    (tmp / "napok" / f"{nap}.json").write_text(json.dumps(d), encoding="utf-8")

def _szo(kif, vol=100, temak=None, hirek=None):
    return {"kifejezes": kif, "volumen": str(vol), "novekedes_pct": "100",
            "temak": temak or ["Hírek"], "hirek": hirek or []}

def test_havi_korpusz_aggregal_dedup_gyakorisag(tmp_path):
    _napfajl(tmp_path, "2026-09-01", [_szo("csalás", 500), _szo("albérlet")])
    _napfajl(tmp_path, "2026-09-02", [_szo("csalás", 800)], [_szo("időjárás")])
    kor = havi_nlp.havi_korpusz(str(tmp_path), "2026-09")
    assert kor["honap"] == "2026-09" and kor["napok"] == 2
    szavak = {s["kifejezes"]: s for s in kor["szavak"]}
    assert szavak["csalás"]["gyakorisag"] == 2                 # két külön napon
    assert szavak["csalás"]["max_volumen"] == 800             # a max
    assert set(szavak) == {"csalás", "albérlet", "időjárás"}  # egyedi, reggel+este
    assert kor["egyedi_szo"] == 3
    # gyakoriság szerint rendezve (csalás elöl)
    assert kor["szavak"][0]["kifejezes"] == "csalás"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `.venv/bin/python -m pytest tests/test_havi_nlp.py -v` → FAIL (ImportError/AttributeError).

- [ ] **Step 3: Write minimal implementation**
```python
"""Havi NLP-elemzés a felkapott keresőszavakról (magyar, LLM-alapú). A korpusz-építés és a
grounding-validáció tiszta/determinista; az NLP-hívás a Claude Opus (nem determinista, AI-jelölt)."""
import glob
import json
import os

def havi_korpusz(docs_data, honap):
    """A hónap (YYYY-MM) felkapott szavai aggregálva: egyedi kifejezés + gyakoriság (hány külön nap),
    max volumen, témák-halmaz, pár hír-cím. Csak OLVAS (napok/*.json READ-ONLY)."""
    minta = os.path.join(docs_data, "napok", honap + "-*.json")
    fajlok = sorted(glob.glob(minta))
    agg = {}
    for f in fajlok:
        try:
            nap = json.loads(open(f, encoding="utf-8").read())
        except (OSError, ValueError):
            continue
        napi_kif = set()
        for szeg in ("reggel", "este"):
            for tr in (nap.get(szeg) or {}).get("trendek", []) or []:
                kif = (tr.get("kifejezes") or "").strip()
                if not kif:
                    continue
                napi_kif.add(kif)
                a = agg.setdefault(kif, {"kifejezes": kif, "gyakorisag": 0, "max_volumen": 0,
                                         "temak": set(), "hirek": []})
                try:
                    a["max_volumen"] = max(a["max_volumen"], int(tr.get("volumen") or 0))
                except (TypeError, ValueError):
                    pass
                a["temak"].update(tr.get("temak") or [])
                for h in (tr.get("hirek") or [])[:2]:
                    cim = h.get("cim") if isinstance(h, dict) else h
                    if cim and cim not in a["hirek"] and len(a["hirek"]) < 3:
                        a["hirek"].append(cim)
        for kif in napi_kif:
            agg[kif]["gyakorisag"] += 1                       # naponta EGYSZER számít
    szavak = sorted(agg.values(), key=lambda a: (-a["gyakorisag"], -a["max_volumen"], a["kifejezes"]))
    for a in szavak:
        a["temak"] = sorted(a["temak"])
    return {"honap": honap, "napok": len(fajlok), "egyedi_szo": len(szavak), "szavak": szavak}
```

- [ ] **Step 4: Run test to verify it passes** → PASS. Teljes suite zöld.

- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/havi_nlp.py tests/test_havi_nlp.py
git commit -m "feat(havi_nlp): havi felkapott-korpusz aggregalas (dedup + gyakorisag)"
```

---

### Task 2: NLP-séma + magyar prompt + Claude-hívás (mockolt SDK-val tesztelve)

**Files:**
- Modify: `trendfigyelo/havi_nlp.py`
- Test: `tests/test_havi_nlp.py`

**Interfaces:**
- Consumes: `havi_korpusz` kimenete (T1).
- Produces: `_nlp_sema() -> dict` (JSON-schema: `lemmak`, `ner`{orszagok/telepulesek/szemelyek}, `klaszterek`, `osszegzes`), `RENDSZER_PROMPT_NLP` (str), `havi_nlp_elemez(korpusz, kliens=None, modell="claude-opus-4-8", probak=3, backoff_mp=(5,20,60), alvo=None) -> dict`.

**Mintakövetés (KÖTELEZŐ):** az `elemzo.py` `_AnthropicKliens` + `elemez` a minta — `anthropic.Anthropic()`, `messages.stream(model, max_tokens, thinking={"type":"adaptive"}, output_config={"effort":"medium","format":{"type":"json_schema","schema":...}}, system=..., messages=[...])`, `get_final_message()`, `json.loads(text)`; injektálható SDK (`__init__(self, sdk=None)`); bounded retry (a hívás intermittens 400-ját tűri), csak az utolsó bukás propagál (fail-soft a hívón kívül). Ezt TÜKRÖZD egy `_NlpKliens`-ben (VAGY általánosítsd az `elemzo._AnthropicKliens`-t — a task-review dönti el melyik tisztább).

- [ ] **Step 1: Write the failing test** (MOCKOLT SDK — SOHA valódi hívás)
```python
class _FakeStream:
    def __init__(self, valasz): self._v = valasz
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self):
        class M:
            content = [type("B", (), {"type": "text", "text": None})()]
        M.content[0].text = self._v
        return M

class _FakeSDK:
    def __init__(self, valasz): self.messages = self; self._v = valasz; self.hivva = 0
    def stream(self, **kw): self.hivva += 1; self._kw = kw; return _FakeStream(self._v)

def test_havi_nlp_elemez_strukturalt_JSON_mockolt_sdkval():
    korpusz = {"honap": "2026-09", "napok": 2, "egyedi_szo": 2,
               "szavak": [{"kifejezes": "csalás", "gyakorisag": 2, "max_volumen": 800, "temak": [], "hirek": []},
                          {"kifejezes": "debrecen időjárás", "gyakorisag": 1, "max_volumen": 100, "temak": [], "hirek": []}]}
    valasz = json.dumps({"lemmak": [{"szo": "csalás", "lemma": "csalás"},
                                    {"szo": "debrecen időjárás", "lemma": "debrecen időjárás"}],
                         "ner": {"orszagok": [], "telepulesek": [{"nev": "Debrecen", "szavak": ["debrecen időjárás"]}],
                                 "szemelyek": []},
                         "klaszterek": [{"cimke": "Bűnügy", "szavak": ["csalás"], "ertelmezes": "…", "uralkodo_temak": []},
                                        {"cimke": "Időjárás", "szavak": ["debrecen időjárás"], "ertelmezes": "…", "uralkodo_temak": []}],
                         "osszegzes": "A hónap…"})
    sdk = _FakeSDK(valasz)
    kliens = havi_nlp._NlpKliens(sdk=sdk)
    er = havi_nlp.havi_nlp_elemez(korpusz, kliens=kliens)
    assert sdk.hivva == 1
    assert er["ner"]["telepulesek"][0]["nev"] == "Debrecen"
    assert {k["cimke"] for k in er["klaszterek"]} == {"Bűnügy", "Időjárás"}
    # a séma-hívás strukturált JSON-t kért:
    assert sdk._kw["output_config"]["format"]["type"] == "json_schema"
```

- [ ] **Step 2: Run test to verify it fails** → FAIL (AttributeError).

- [ ] **Step 3: Write minimal implementation** — `_nlp_sema()` a 3.2 séma (`additionalProperties:false`); `RENDSZER_PROMPT_NLP` a spec §3.1 elveit betartató magyar prompt (magyar kimenet; GROUNDING: csak a kapott szavakból; minden szó egy klaszterbe + minden szóra lemma; magyar lemmatizálás/NER; jelentés-alapú klaszterek). `_NlpKliens` az `elemzo._AnthropicKliens` mintája (a séma+prompt ITT). `havi_nlp_elemez` = bounded retry a hívásra (mint `elemzo.elemez`), a payload a korpusz JSON-ja.

- [ ] **Step 4: Run test to verify it passes** → PASS. Teljes suite zöld (mock, nincs hálózat).

- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/havi_nlp.py tests/test_havi_nlp.py
git commit -m "feat(havi_nlp): magyar NLP-sema + prompt + Claude-hivas (mockolt SDK)"
```

---

### Task 3: grounding-validáció + írás + generáló belépési pont

**Files:**
- Modify: `trendfigyelo/havi_nlp.py`
- Test: `tests/test_havi_nlp.py`

**Interfaces:**
- Consumes: `havi_korpusz`, `havi_nlp_elemez`.
- Produces: `grounding_validal(eredmeny, korpusz) -> dict` (kiszűri a NEM korpusz-beli NER-entitást/klaszter-tagot; minden szóra lemma; nincs lógó szó), `havi_nlp_ir(docs_data, honap, eredmeny) -> Path`, `havi_nlp_generalas(docs_data, honap, keszult_iso, kliens=None) -> dict|None` (korpusz→elemez→validál→ír; fail-soft None tartós hibán).

- [ ] **Step 1: Write the failing test**
```python
def test_grounding_validal_kiszuri_a_nem_korpuszbeli_entitast():
    korpusz = {"szavak": [{"kifejezes": "csalás"}, {"kifejezes": "albérlet"}]}
    er = {"lemmak": [{"szo": "csalás", "lemma": "csalás"}],
          "ner": {"orszagok": [{"nev": "Kitalált", "szavak": ["nincs ilyen szó"]}], "telepulesek": [], "szemelyek": []},
          "klaszterek": [{"cimke": "A", "szavak": ["csalás", "kamu szó"], "ertelmezes": "…"}],
          "osszegzes": "…"}
    v = havi_nlp.grounding_validal(er, korpusz)
    # a nem-korpuszbeli entitás/tag KIESIK
    assert v["ner"]["orszagok"] == []                                  # a "nincs ilyen szó" nem korpusz-szó
    assert "kamu szó" not in v["klaszterek"][0]["szavak"]              # a lógó tag kiesik
    assert "csalás" in v["klaszterek"][0]["szavak"]

def test_havi_nlp_ir_kulon_fajlba(tmp_path):
    p = havi_nlp.havi_nlp_ir(str(tmp_path), "2026-09", {"honap": "2026-09", "klaszterek": []})
    assert p.name == "2026-09.json" and p.parent.name == "havi_nlp"
    assert json.loads(p.read_text(encoding="utf-8"))["honap"] == "2026-09"
```

- [ ] **Step 2: Run test to verify it fails** → FAIL.

- [ ] **Step 3: Write minimal implementation** — `grounding_validal`: a korpusz-szavak halmaza; a NER `szavak` és a klaszter `szavak` szűrve, hogy KORPUSZ-szavak legyenek (üres entitás kiesik); a `lemmak` a korpusz-szavakra csonkolva/kiegészítve. `havi_nlp_ir` = `json_export._ir_json(Path(docs_data)/"havi_nlp"/(honap+".json"), eredmeny)` (a mappát `mkdir(parents,exist_ok)`). `havi_nlp_generalas`: `keszult_iso` PARAMÉTER (nincs `datetime.now()`); korpusz→`havi_nlp_elemez` (fail-soft)→`grounding_validal`→a `keszult`/`modell`/`korpusz`-meta hozzáadva→`havi_nlp_ir`.

- [ ] **Step 4: Run test to verify it passes** → PASS. Teljes suite zöld.

- [ ] **Step 5: Commit**
```bash
git add trendfigyelo/havi_nlp.py tests/test_havi_nlp.py
git commit -m "feat(havi_nlp): grounding-validacio + atomi iras + generalo belepesi pont"
```

---

### Task 4: frontend — „Havi elemzés" fül (havi.html + havi.js)

**Files:**
- Create: `docs/havi.html`, `docs/js/havi.js`
- Test: `e2e/havi.spec.js`

**Interfaces:** `docs/havi.html` (az `youtube.html` fej/nav/script mintája, + `havi.js`); `havi.js` a `data/havi_nlp/<honap>.json`-t tölti (fail-soft), és renderel: **klaszterek** (címke + tag-szavak + értelmezés + domináns témák), **NER** 3 csoport (országok/települések/személyek), **szó→lemma térkép** (auditálható), **összegzés**. Hónap-választó (opcionális az 1. fázisban: a legfrissebb `havi_nlp` fájl). AI-jelölés („gépi elemzés"). Az `elemzes.js` `elemzes_betolt`/`rajzol`/`indit` mintáját tükrözi. Nincs `new Date()`.

- [ ] **Step 1: Write the failing test** (mockolt `data/havi_nlp/...json`)
```javascript
const { test, expect } = require("@playwright/test");
test("Havi elemzés fül: klaszterek + NER + lemma + összegzés renderel", async ({ page }) => {
  await page.route("**/data/havi_nlp/**", r => r.fulfill({ json: {
    honap: "2026-09", keszult: "2026-09-30T00:00:00Z", modell: "claude-opus-4-8",
    korpusz: { egyedi_szo: 2, napok: 2 },
    lemmak: [{ szo: "csalások", lemma: "csalás" }],
    ner: { orszagok: [], telepulesek: [{ nev: "Debrecen", szavak: ["debrecen időjárás"] }], szemelyek: [] },
    klaszterek: [{ cimke: "Bűnügy", szavak: ["csalás"], ertelmezes: "leírás", uralkodo_temak: [] }],
    osszegzes: "A hónap keresései…" } }));
  await page.goto("/havi.html");
  await expect(page.locator("#havi")).toContainText("Bűnügy");
  await expect(page.locator("#havi")).toContainText("Debrecen");         // NER település
  await expect(page.locator("#havi")).toContainText("csalás");           // klaszter-tag / lemma
  await expect(page.locator("#havi")).toContainText("A hónap keresései");// összegzés
});
```

- [ ] **Step 2: Run test to verify it fails** → FAIL (nincs havi.html/#havi).

- [ ] **Step 3: Write minimal implementation** — `havi.html` a `youtube.html` mintája (`<main id="havi">`, `havi.js` include); `havi.js` az `elemzes.js` mintájára: `fetch("data/havi_nlp/<honap>.json")` (fail-soft), `rajzol(art)` a klaszter/NER/lemma/összegzés DOM-mal, AI-jelöléssel. A legfrissebb hónap az `data/havi_nlp/index.json`-ból VAGY egy fix jelenlegi hónapból (1. fázis; a task-review elfogadja a fail-soft egyszerűsítést).

- [ ] **Step 4: Run test to verify it passes** → PASS (SOROS Playwright).

- [ ] **Step 5: Commit**
```bash
git add docs/havi.html docs/js/havi.js e2e/havi.spec.js
git commit -m "feat(havi): Havi elemzes ful (klaszterek + NER + lemma + osszegzes render)"
```

---

### Task 5: nav — „Elemzések" → „Napi Elemzések" + új „Havi elemzés" fül MIND az oldalon

**Files:**
- Modify: `docs/trendek.html`, `docs/elemzes.html`, `docs/youtube.html`, `docs/adatokrol.html`, `docs/havi.html` (a nav mindegyikben) + `docs/elemzes.html` h1/`<title>` (a „Napi elemzés" felirat marad/pontosítva)
- Test: `e2e/menu.spec.js`

**Interfaces:** minden oldal `#fomenu`-ja: **Napi Elemzések** (`elemzes.html`) · **Havi elemzés** (`havi.html`) · Google Trendek (`trendek.html`) · YouTube Trendek · Infó. Az `aria-current="page"` az adott oldalon a helyes fülre. A landing (`/` → `elemzes.html`) változatlan.

- [ ] **Step 1: Write the failing test** — a `menu.spec.js` frissítve: 5 fül, a sorrend `["Napi Elemzések","Havi elemzés","Google Trendek","YouTube Trendek","Infó"]`; a `havi.html`-en az aktív = „Havi elemzés"; az `elemzes.html`-en az aktív = „Napi Elemzések"; a landing-teszt (`/`→elemzes.html) marad.
- [ ] **Step 2: Run test to verify it fails** → FAIL (4 fül / régi „Elemzések" felirat).
- [ ] **Step 3: Write minimal implementation** — MIND az 5 HTML nav-jában: a „Napi Elemzések" + „Havi elemzés" (`havi.html`) fül; az „Elemzések" szöveg → „Napi Elemzések"; a sorrend a fenti. (Az e2e-ben a korábbi „Elemzések"-re asszertáló helyek → „Napi Elemzések".)
- [ ] **Step 4: Run test to verify it passes** → PASS. TELJES e2e + pytest zöld.
- [ ] **Step 5: Commit**
```bash
git add docs/trendek.html docs/elemzes.html docs/youtube.html docs/adatokrol.html docs/havi.html e2e/menu.spec.js
git commit -m "feat(nav): Napi Elemzesek atnevezes + uj Havi elemzes ful minden oldalon"
```

---

## Záró lépések (a plan végén, az SDD/executor végzi)
- Teljes-ág review (legképesebb modell): a korpusz-aggregálás helyessége, a grounding-validáció (nincs hallucináció átengedve), a fail-soft, a nav-konzisztencia MIND az oldalon, az AI-jelölés.
- **Élő generálás (1. fázis):** a jelenlegi hónap korpuszából egyszer legenerálom a `havi_nlp/2026-09.json`-t (a `keszult` paraméterrel, valós Claude-hívással, a kulccsal) → valós adat a fülön; élő-előnézet + git checkout (a data ne szennyeződjön előnézet-adattal, KIVÉVE ha a valós havi_nlp fájlt commitoljuk — USER-döntés: az 1. fázisban commitolható a legenerált havi_nlp fájl, hogy a fülön legyen mit nézni).
- Kapuzott merge/push USER-jóváhagyással (finishing-a-development-branch); memória + leltár frissítés.
- 2. FÁZIS (külön kör): utolsó-nap-ütemezés + Elemzések-jelzés + a napi futásba integrálás.
