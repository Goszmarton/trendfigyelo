# Heti értékelés — új fül (hétfőnkénti heti riport) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Egy új „Heti értékelés" fül, amely hétfő reggel (a Reggeli felkapott-gyűjtés után) az előző hétfő–vasárnap hetet összegzi 6 strukturált részben, grounded (VALÓS számok Python + Claude Opus narratíva) + egy determinista divergáló sávdiagrammal.

**Architecture:** A havi NLP-alrendszer PÁRHUZAMOS mintája: determinista Python-korpusz (`heti_korpusz`) → Claude Opus strukturált JSON (`heti_elemez`) → grounding → atomi írás `docs/data/heti/<hétfő>.json` + index; hétfő+idempotencia-őr (`heti_orzo`); belépő (`heti.py`); workflow (`heti.yml`, a „Reggeli felkapott-gyűjtés"-re); új frontend (`heti.html`+`heti.js`) 6 szekcióval + hét-választóval + 1 Chart.js divergáló sávdiagrammal; nav 6. füle minden oldalon.

**Tech Stack:** Python 3.12 (stdlib: glob/json/calendar/datetime/pathlib; anthropic SDK streaming), Chart.js (vendorelt), vanilla JS, GitHub Actions, pytest + Playwright.

**Spec:** `docs/superpowers/specs/2026-10-08-heti-ertekeles-design.md`

## Global Constraints

- NULLA új Python-dependency (csak stdlib + a meglévő anthropic SDK); a frontend a meglévő vendorelt Chart.js-t használja (nincs új vendor-asset, nincs külső betöltés).
- Grounding: a Python a VALÓS számokat szállítja; a Claude SOHA nem talál ki kulcsszót/entitást/eseményt; ok/esemény CSAK a korpuszban adott hír esetén. `grounding_validal` a hivatkozott szó-listákat a korpuszra szűri.
- Irreplaceable adat READ-ONLY (napok/*.json, kulcsszo_regresszio.json, youtube_regresszio.json csak OLVASÁS); a heti artefakt atomi írással (`json_export._ir_json`).
- NINCS argless `datetime.now()` a modul-logikában — minden „most"/„készült" PARAMÉTER (a determinizmus + idempotencia miatt); a belépő a `seged.most_utc()`-ot adja át.
- `MODELL = "claude-opus-4-8"`, adaptive thinking, STREAMING kötelező (nagy max_tokens), nincs beta-header. `MAX_TOKENS_HETI = 64000` (a napi 32000 és a havi 128000 közt; a heti kimenet 6 rész + 2–3 mély elemzés — ÉLES-figyelés az első futásnál).
- `git add` NÉVRE; az `ATADAS-2026-08-18.txt` SOSEM staged. A workflow commitja CSAK `docs/data/heti`-t érinti. Push külön kapuzott kör USER-jóváhagyással.
- SOROS teszt-suite (pytest + Playwright) zöld. TDD: minden produkciós kód előtt bukó teszt.
- A napi/havi elemzés (séma/prompt/fül/backend) VÁLTOZATLAN. A backend regresszió/lánc-számítás VÁLTOZATLAN.
- A hét: hétfő–vasárnap. A heti artefakt fájl-kulcsa a hét HÉTFŐJÉNEK ISO-dátuma (`YYYY-MM-DD`).
- Nav sorrend MINDEN oldalon: `Napi Elemzések · Heti értékelés · Havi elemzés · Google Trendek · YouTube Trendek · Infó`.

---

### Task 1: `heti_korpusz` — determinista heti aggregálás

**Files:**
- Create: `trendfigyelo/heti_ertekeles.py`
- Test: `tests/test_heti_ertekeles.py`

**Interfaces:**
- Consumes: `docs/data/kulcsszo_regresszio.json` (`kulcsszavak[<szó>].intervallumok["1_het"]` → `irany/illeszkedes/mai_ertek/mai_reziduum/reziduum_szokasos/meredekseg_nap/illesztes_vonal/ervenyes` + top-level `domen/tipus`), `docs/data/youtube_regresszio.json` (ugyanaz a forma, 12 szó), `docs/data/napok/<YYYY-MM-DD>.json` (szegmentált `reggel`/`este` → `.trendek[]` VAGY régi lapos top-level `trendek[]`; minden trend: `kifejezes/volumen/temak/hirek`).
- Produces: `heti_korpusz(docs_data, het_kezdet_iso) -> dict` a lenti alakkal; a 2–6. taskok ezt fogyasztják.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_heti_ertekeles.py
import json
from pathlib import Path

from trendfigyelo import heti_ertekeles as he


def _ir(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _regresszio_fajl(tmp_path):
    # két követett szó: egy „felette" (erősödő, pozitív eltérés) és egy „alatta" (gyengülő)
    _ir(tmp_path / "kulcsszo_regresszio.json", {
        "szamitva_utc": "2026-10-05T18:00:00+00:00",
        "kulcsszavak": {
            "benzinár": {"domen": "megelhetes", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": True, "irany": "nő", "illeszkedes": "felette",
                          "mai_ertek": 80, "mai_reziduum": 20.0, "reziduum_szokasos": 8.0,
                          "meredekseg_nap": 2.5,
                          "illesztes_vonal": [{"idopont_utc": "2026-09-29T00:00:00+00:00", "ertek": 60.0},
                                              {"idopont_utc": "2026-10-05T00:00:00+00:00", "ertek": 78.0}]}}},
            "nyugdíj": {"domen": "megelhetes", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": True, "irany": "csökken", "illeszkedes": "alatta",
                          "mai_ertek": 30, "mai_reziduum": 5.0, "reziduum_szokasos": 12.0,
                          "meredekseg_nap": -1.0, "illesztes_vonal": []}}},
        },
    })


def _youtube_fajl(tmp_path):
    _ir(tmp_path / "youtube_regresszio.json", {
        "szamitva_utc": "2026-10-05T18:00:00+00:00",
        "kulcsszavak": {
            "szorongás": {"domen": "egeszseg", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": True, "irany": "stagnál", "illeszkedes": "illeszkedik",
                          "mai_ertek": 14}}},
            "fejfájás": {"domen": "egeszseg", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": False, "ok": "kevés pont"}}},
        },
    })


def _nap(tmp_path, nap, kifejezesek):
    _ir(tmp_path / "napok" / f"{nap}.json",
        {"este": {"trendek": [{"kifejezes": k, "volumen": v, "temak": tm, "hirek": hi}
                               for (k, v, tm, hi) in kifejezesek]}})


def test_heti_korpusz_het_hatarok_es_iso(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")   # hétfő
    assert k["het_kezdet"] == "2026-09-29"
    assert k["het_veg"] == "2026-10-05"                # vasárnap
    assert k["iso_het"] == "2026-W40"


def test_heti_korpusz_kulcsszavak_elteres_es_irany(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    szavak = {s["szo"]: s for s in k["kulcsszavak"]}
    assert szavak["benzinár"]["irany"] == "nő"
    assert szavak["benzinár"]["illeszkedes"] == "felette"
    assert round(szavak["benzinár"]["elteres_szokasostol"], 2) == 12.0   # 20.0 - 8.0
    assert round(szavak["nyugdíj"]["elteres_szokasostol"], 2) == -7.0    # 5.0 - 12.0
    assert szavak["benzinár"]["domen"] == "megelhetes"
    assert szavak["benzinár"]["palya"][0]["ertek"] == 60.0


def test_heti_korpusz_elteres_none_ha_ervenytelen_vagy_hianyzik(tmp_path):
    _ir(tmp_path / "kulcsszo_regresszio.json", {"kulcsszavak": {
        "x": {"domen": "d", "tipus": "t", "intervallumok": {"1_het": {"ervenyes": False}}}}})
    _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    assert k["kulcsszavak"][0]["elteres_szokasostol"] is None
    assert k["kulcsszavak"][0]["irany"] is None


def test_heti_korpusz_felkapott_csak_a_het_napjaibol_napok_szama(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    _nap(tmp_path, "2026-09-28", [("héten kívül", 90, [], [])])        # előző vasárnap — KIMARAD
    _nap(tmp_path, "2026-09-29", [("tüntetés", 70, ["Politika"], [{"cim": "H1"}])])
    _nap(tmp_path, "2026-09-30", [("tüntetés", 90, ["Politika"], [{"cim": "H2"}])])
    _nap(tmp_path, "2026-10-05", [("tüntetés", 50, [], [])])
    _nap(tmp_path, "2026-10-06", [("héten kívül2", 10, [], [])])       # köv. hétfő — KIMARAD
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    fel = {f["kifejezes"]: f for f in k["felkapott"]}
    assert "héten kívül" not in fel and "héten kívül2" not in fel
    assert fel["tüntetés"]["napok_szama"] == 3
    assert fel["tüntetés"]["max_volumen"] == 90
    assert "Politika" in fel["tüntetés"]["temak"]
    assert "H1" in fel["tüntetés"]["hirek"] and len(fel["tüntetés"]["hirek"]) <= 3
    assert k["napok"] == 3        # a 3 héten-belüli nap


def test_heti_korpusz_youtube_ervenyes_es_ervenytelen(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    yt = {y["szo"]: y for y in k["youtube"]}
    assert yt["szorongás"]["irany"] == "stagnál" and yt["szorongás"]["nincs_adat"] is False
    assert yt["fejfájás"]["nincs_adat"] is True and yt["fejfájás"]["irany"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_heti_ertekeles.py -q`
Expected: FAIL (`ModuleNotFoundError: trendfigyelo.heti_ertekeles` / `AttributeError`).

- [ ] **Step 3: Write minimal implementation**

```python
# trendfigyelo/heti_ertekeles.py
"""Heti értékelés az előző (hétfő–vasárnap) hétről (magyar, LLM-alapú). A korpusz-építés és a
grounding tiszta/determinista; a Claude Opus hívás nem determinista (AI-jelölt). A havi_nlp.py
PÁRHUZAMOS mintája — a napi/havi elemzés érintetlen."""
import glob
import json
import logging
import os
import time
from datetime import date, timedelta
from pathlib import Path

from trendfigyelo import json_export

_log = logging.getLogger(__name__)


def _het_veg(het_kezdet_iso):
    return (date.fromisoformat(het_kezdet_iso) + timedelta(days=6)).isoformat()


def _iso_het(het_kezdet_iso):
    ev, het, _ = date.fromisoformat(het_kezdet_iso).isocalendar()
    return f"{ev}-W{het:02d}"


def _het_1het(regr_szo):
    iv = ((regr_szo or {}).get("intervallumok") or {}).get("1_het") or {}
    return iv if iv.get("ervenyes") else {}


def _kulcsszavak_het(docs_data):
    """A 28 követett szó heti jele a regresszió `1_het` (érvényes) ablakából: irány, illeszkedés a
    szokásos szinthez, eltérés (mai_reziduum − reziduum_szokasos), heti pálya (illesztes_vonal)."""
    fajl = Path(docs_data) / "kulcsszo_regresszio.json"
    try:
        d = json.loads(fajl.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for szo, w in (d.get("kulcsszavak") or {}).items():
        iv = _het_1het(w)
        mr, rsz = iv.get("mai_reziduum"), iv.get("reziduum_szokasos")
        elteres = (mr - rsz) if isinstance(mr, (int, float)) and isinstance(rsz, (int, float)) else None
        out.append({
            "szo": szo, "domen": w.get("domen"), "tipus": w.get("tipus"),
            "irany": iv.get("irany"), "illeszkedes": iv.get("illeszkedes"),
            "mai_ertek": iv.get("mai_ertek"), "meredekseg_nap": iv.get("meredekseg_nap"),
            "elteres_szokasostol": elteres,
            "palya": [{"idopont_utc": p.get("idopont_utc"), "ertek": p.get("ertek")}
                      for p in (iv.get("illesztes_vonal") or [])],
        })
    return out


def _youtube_het(docs_data):
    fajl = Path(docs_data) / "youtube_regresszio.json"
    try:
        d = json.loads(fajl.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for szo, w in (d.get("kulcsszavak") or {}).items():
        iv = _het_1het(w)
        van = bool(iv)
        out.append({"szo": szo, "domen": w.get("domen"), "tipus": w.get("tipus"),
                    "irany": iv.get("irany") if van else None,
                    "illeszkedes": iv.get("illeszkedes") if van else None,
                    "mai_ertek": iv.get("mai_ertek") if van else None,
                    "nincs_adat": not van})
    return out


def _felkapott_het(docs_data, het_kezdet_iso, het_veg_iso):
    """A hét (hétfő–vasárnap) napfájljaiból aggregált felkapott kifejezések: napok_szama (hány külön
    napon), max_volumen, témák, pár hír. A napfájl szegmentált (reggel/este) VAGY régi lapos — a
    havi_korpusz-szal azonos visszafelé-kompat szabály, de DÁTUM-ABLAKRA szűrve (nem hónap-prefixre)."""
    agg, beolvasott = {}, 0
    for f in sorted(glob.glob(os.path.join(docs_data, "napok", "*.json"))):
        nap = Path(f).stem
        if len(nap) != 10 or nap < het_kezdet_iso or nap > het_veg_iso:
            continue
        try:
            with open(f, encoding="utf-8") as fp:
                d = json.loads(fp.read())
        except (OSError, ValueError):
            continue
        beolvasott += 1
        trend_lista = []
        for szeg in ("reggel", "este"):
            trend_lista += (d.get(szeg) or {}).get("trendek", []) or []
        if not trend_lista:
            trend_lista = d.get("trendek") or []
        napi = set()
        for tr in trend_lista:
            kif = (tr.get("kifejezes") or "").strip()
            if not kif:
                continue
            napi.add(kif)
            a = agg.setdefault(kif, {"kifejezes": kif, "napok_szama": 0, "max_volumen": 0,
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
        for kif in napi:
            agg[kif]["napok_szama"] += 1
    szavak = sorted(agg.values(), key=lambda a: (-a["napok_szama"], -a["max_volumen"], a["kifejezes"]))
    for a in szavak:
        a["temak"] = sorted(a["temak"])
    return szavak, beolvasott


def heti_korpusz(docs_data, het_kezdet_iso):
    """Az előző hét (hétfő=het_kezdet_iso … vasárnap) DETERMINISTA aggregálása. Csak OLVAS."""
    het_veg = _het_veg(het_kezdet_iso)
    felkapott, napok = _felkapott_het(docs_data, het_kezdet_iso, het_veg)
    return {
        "het_kezdet": het_kezdet_iso, "het_veg": het_veg, "iso_het": _iso_het(het_kezdet_iso),
        "napok": napok,
        "kulcsszavak": _kulcsszavak_het(docs_data),
        "felkapott": felkapott,
        "youtube": _youtube_het(docs_data),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_heti_ertekeles.py -q`
Expected: PASS (6 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/heti_ertekeles.py tests/test_heti_ertekeles.py
git commit -m "feat(heti): heti_korpusz - determinista heti aggregalas (kovetett/felkapott/youtube)"
```

---

### Task 2: Séma + prompt + kliens + `heti_elemez`

**Files:**
- Modify: `trendfigyelo/heti_ertekeles.py`
- Test: `tests/test_heti_ertekeles.py`

**Interfaces:**
- Consumes: `heti_korpusz` kimenete (Task 1).
- Produces: `_valasz_sema() -> dict` (a 6 rész JSON-sémája); `RENDSZER_PROMPT_HETI` (str); `_HetiKliens(sdk=None).uzenet(korpusz, modell) -> dict`; `heti_elemez(korpusz, kliens=None, ...) -> dict` (bounded retry); `MODELL/MAX_TOKENS_HETI`. A Task 3 generalas ezt hívja.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_heti_ertekeles.py  (hozzáadás)
def test_valasz_sema_hat_resz():
    s = he._valasz_sema()
    assert s["additionalProperties"] is False
    props = s["properties"]
    assert set(s["required"]) == {
        "vezetoi_osszefoglalo", "figyelem_atrendezodes", "ugyek_eletutja",
        "melyebb_temak", "google_youtube_osszefugges", "jovo_heti_figyelendok"}
    assert props["vezetoi_osszefoglalo"]["maxItems"] == 5
    assert set(props["figyelem_atrendezodes"]["required"]) == {"erosodo", "gyengulo"}
    assert set(props["ugyek_eletutja"]["required"]) == {"rovid_kiugras", "hosszabb_kiugras", "visszatero"}
    assert props["melyebb_temak"]["maxItems"] == 3
    tema = props["melyebb_temak"]["items"]
    assert set(tema["required"]) == {
        "tema", "keresesi_palya", "kapcsolodo_kifejezesek", "ellenorzott_esemenyek", "magyarazat"}
    assert tema["additionalProperties"] is False


def test_rendszer_prompt_grounding_es_hat_resz():
    p = he.RENDSZER_PROMPT_HETI
    assert "hétfő" in p and "vasárnap" in p
    assert "GROUNDING" in p or "nem találsz ki" in p
    assert "tartóssság" in p or "tartóss" in p or "tartós" in p   # az ügyek tartóssága
    assert "ellenőrzött" in p or "hír" in p                       # események csak hírből


class _HamisStream:
    def __init__(self, valasz): self._v = valasz
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self):
        class _B:
            type = "text"
            text = None
        b = _B(); b.text = json.dumps(self._v, ensure_ascii=False)
        return type("M", (), {"content": [b]})


class _HamisSdk:
    def __init__(self, valasz): self.messages = self; self._v = valasz; self.hivasok = 0
    def stream(self, **kw): self.hivasok += 1; return _HamisStream(self._v)


def _teljes_valasz():
    return {"vezetoi_osszefoglalo": ["a", "b"],
            "figyelem_atrendezodes": {"erosodo": ["benzinár"], "gyengulo": ["nyugdíj"]},
            "ugyek_eletutja": {"rovid_kiugras": "x", "hosszabb_kiugras": "y", "visszatero": "z"},
            "melyebb_temak": [{"tema": "T", "keresesi_palya": "p", "kapcsolodo_kifejezesek": "k",
                               "ellenorzott_esemenyek": "e", "magyarazat": "m"}],
            "google_youtube_osszefugges": "gy",
            "jovo_heti_figyelendok": ["f1"]}


def test_heti_elemez_mock_sdk_atveszi_a_valaszt():
    sdk = _HamisSdk(_teljes_valasz())
    out = he.heti_elemez({"het_kezdet": "2026-09-29", "kulcsszavak": [], "felkapott": [], "youtube": []},
                         kliens=he._HetiKliens(sdk=sdk))
    assert out["vezetoi_osszefoglalo"] == ["a", "b"]
    assert sdk.hivasok == 1


def test_heti_elemez_bounded_retry(monkeypatch):
    class _Buko:
        def uzenet(self, *a, **k):
            self.n = getattr(self, "n", 0) + 1
            if self.n < 2:
                raise RuntimeError("intermittens")
            return _teljes_valasz()
    out = he.heti_elemez({}, kliens=_Buko(), alvo=lambda s: None)
    assert out["google_youtube_osszefugges"] == "gy"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_heti_ertekeles.py -q -k "sema or prompt or elemez"`
Expected: FAIL (`AttributeError`).

- [ ] **Step 3: Write minimal implementation** (a Task 1 `heti_ertekeles.py` VÉGÉRE, a `heti_korpusz` elé/után — a `_log`/importok megvannak)

```python
def _valasz_sema():
    """A heti értékelés 6 részének strukturált sémája (spec §4). Minden mező kötelező (üres megengedett),
    additionalProperties:False."""
    str_lista = {"type": "array", "items": {"type": "string"}}
    return {
        "type": "object", "additionalProperties": False,
        "required": ["vezetoi_osszefoglalo", "figyelem_atrendezodes", "ugyek_eletutja",
                     "melyebb_temak", "google_youtube_osszefugges", "jovo_heti_figyelendok"],
        "properties": {
            "vezetoi_osszefoglalo": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
            "figyelem_atrendezodes": {
                "type": "object", "additionalProperties": False,
                "required": ["erosodo", "gyengulo"],
                "properties": {"erosodo": str_lista, "gyengulo": str_lista}},
            "ugyek_eletutja": {
                "type": "object", "additionalProperties": False,
                "required": ["rovid_kiugras", "hosszabb_kiugras", "visszatero"],
                "properties": {"rovid_kiugras": {"type": "string"},
                               "hosszabb_kiugras": {"type": "string"},
                               "visszatero": {"type": "string"}}},
            "melyebb_temak": {
                "type": "array", "maxItems": 3,
                "items": {"type": "object", "additionalProperties": False,
                          "required": ["tema", "keresesi_palya", "kapcsolodo_kifejezesek",
                                       "ellenorzott_esemenyek", "magyarazat"],
                          "properties": {"tema": {"type": "string"},
                                         "keresesi_palya": {"type": "string"},
                                         "kapcsolodo_kifejezesek": {"type": "string"},
                                         "ellenorzott_esemenyek": {"type": "string"},
                                         "magyarazat": {"type": "string"}}}},
            "google_youtube_osszefugges": {"type": "string"},
            "jovo_heti_figyelendok": {"type": "array", "items": {"type": "string"}},
        },
    }


RENDSZER_PROMPT_HETI = (
    "Heti értékelést készítő elemző vagy egy magyar Google Trends és YouTube figyelő oldalhoz. A "
    "bemeneted egy HETI korpusz az előző HÉTFŐ–VASÁRNAP hétről: (1) a KÖVETETT keresőszavak heti "
    "iránya (nő/csökken/stagnál), a szokásos szintjükhöz mért helyzete (felette/alatta/illeszkedik) "
    "és a szokásostól való eltérésük; (2) a héten FELKAPOTT (trendelt) keresőszavak, szavanként azzal, "
    "hogy hány külön napon trendeltek, a legmagasabb volumennel, a Google-témacímkékkel és néhány "
    "hír-címmel; (3) a YouTube-keresőszavak heti iránya/szintje. A feladatod az ÜGYEK TARTÓSSÁGÁNAK és "
    "ÖSSZEFÜGGÉSÉNEK értékelése — mi tartott ki, mi volt rövid kiugrás, mi tért vissza, és hol látszik "
    "kapcsolat a témák és a két adatforrás között. "
    "SZABÁLYOK, kivétel nélkül: "
    "(1) MINDEN kimenet magyar nyelven, LAIKUS olvasónak, folyó mondatokban — SOHA ne írj mezőnevet, "
    "JSON-t vagy technikai kulcsot a szövegbe. "
    "(2) GROUNDING: kizárólag a kapott korpusz számaiból/szavaiból/híreiből dolgozol; keresőszót, "
    "eseményt vagy okot SOHA nem találsz ki. Okot vagy eseményt CSAK akkor írsz, ha a korpuszban "
    "ténylegesen van hozzá hír — hír nélkül csak a megfigyelt mozgást írod le, magyarázat nélkül. "
    "(3) A hat rész: "
    "`vezetoi_osszefoglalo` = legfeljebb 5 megállapítás arról, mi változott a héten és miért érdemes "
    "vele foglalkozni (ha csendes volt a hét, ezt őszintén jelezd). "
    "`figyelem_atrendezodes` = mely témák ERŐSÖDTEK (`erosodo`) és mely GYENGÜLTEK (`gyengulo`) a "
    "szokásos szintjükhöz képest — az illeszkedés/irány/eltérés alapján. "
    "`ugyek_eletutja` = az ügyek TARTÓSSÁGA: `rovid_kiugras` (ami csak egy-két napig szökött fel), "
    "`hosszabb_kiugras` (ami több napon át kitartott), `visszatero` (ami a héten belül vagy korábbról "
    "vissza-visszatért). "
    "`melyebb_temak` = 2–3 kiemelt téma MÉLYEBB elemzése, mindegyikhez: `keresesi_palya` (hogyan "
    "mozgott a héten a keresés), `kapcsolodo_kifejezesek` (a korpuszból kapcsolódó szavak), "
    "`ellenorzott_esemenyek` (CSAK a korpusz hír-címeiből), `magyarazat` (grounded értelmezés). "
    "`google_youtube_osszefugges` = hol látszik közös vagy párhuzamos mozgás a követett Google-szavak "
    "és a YouTube-szavak között (téma- vagy iránybeli egybeesés) — ha nincs, ezt mondd ki. "
    "`jovo_heti_figyelendok` = mire érdemes figyelni a jövő héten, a heti pályából és a visszatérőkből "
    "levezetve, ÓVATOSAN (ez nem eseményjóslás, hanem figyelmeztetés, mit érdemes nézni). "
    "(4) Ahol a fogalmazás óvatosabb, azt a mondat maga hordozza; a rövid gondolatjel „–"."
)


MODELL = "claude-opus-4-8"
MAX_TOKENS_HETI = 64000   # gondolkodás + strukturált kimenet KÖZÖS kerete; a heti a napi (32000) és a
#  havi (128000) közt — 6 rész + 2–3 mély elemzés. Csonkolásnál (json.loads hiba) emelni (max 128000).


class _HetiKliens:
    """A heti Claude-kliens: az anthropic SDK-t STREAMELVE hívja strukturált kimenettel (a havi_nlp
    _NlpKliens mintája). Az `sdk` injektálható (teszt); None → anthropic.Anthropic() a kulccsal."""

    def __init__(self, sdk=None):
        self._sdk = sdk

    def _kliens(self):
        if self._sdk is not None:
            return self._sdk
        import anthropic
        return anthropic.Anthropic()

    def uzenet(self, korpusz, modell):
        kliens = self._kliens()
        with kliens.messages.stream(
            model=modell, max_tokens=MAX_TOKENS_HETI,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium",
                           "format": {"type": "json_schema", "schema": _valasz_sema()}},
            system=RENDSZER_PROMPT_HETI,
            messages=[{"role": "user", "content":
                       "Értékeld az alábbi heti korpuszt (JSON). Csak ebből dolgozz:\n"
                       + json.dumps(korpusz, ensure_ascii=False)}],
        ) as folyam:
            valasz = folyam.get_final_message()
        szoveg = next(b.text for b in valasz.content if b.type == "text")
        return json.loads(szoveg)


RETRY_PROBAK = 3
RETRY_BACKOFF_MP = (5, 20, 60)


def heti_elemez(korpusz, kliens=None, modell=MODELL,
                probak=RETRY_PROBAK, backoff_mp=RETRY_BACKOFF_MP, alvo=None):
    """A heti Claude-hívás BOUNDED RETRY-vel (a havi_nlp_elemez mintája): intermittens API-hibánál
    `probak` próba, közöttük `backoff_mp` várakozás; csak az utolsó bukás propagál."""
    kliens = kliens or _HetiKliens()
    alvo = alvo if alvo is not None else time.sleep
    utolso = None
    for i in range(probak):
        try:
            return kliens.uzenet(korpusz, modell)
        except Exception as e:   # noqa: BLE001 — intermittens API-hiba: bounded retry, végül propagál
            utolso = e
            if i + 1 < probak:
                _log.warning("FIGYELEM: a heti elemzés elhasalt (%s); újrapróba %d/%d %d mp múlva.",
                             e, i + 2, probak, backoff_mp[i])
                alvo(backoff_mp[i])
    raise utolso
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_heti_ertekeles.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/heti_ertekeles.py tests/test_heti_ertekeles.py
git commit -m "feat(heti): valasz-sema (6 resz) + prompt + streaming kliens + bounded-retry elemez"
```

---

### Task 3: Grounding + írás + index + `heti_generalas` + figyelem-adat

**Files:**
- Modify: `trendfigyelo/heti_ertekeles.py`
- Test: `tests/test_heti_ertekeles.py`

**Interfaces:**
- Consumes: `heti_korpusz` (Task 1), `heti_elemez`/`_valasz_sema` (Task 2), `json_export._ir_json`.
- Produces: `grounding_validal(eredmeny, korpusz) -> dict`; `figyelem_adat(korpusz) -> list` (a divergáló diagram adata); `heti_ir(docs_data, het_kezdet, eredmeny)`; `heti_index_ir(docs_data)`; `heti_generalas(docs_data, het_kezdet, keszult_iso, kliens=None) -> dict|None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_heti_ertekeles.py  (hozzáadás)
def test_grounding_kiszuri_a_nem_korpuszbeli_hivatkozast():
    korpusz = {"kulcsszavak": [{"szo": "benzinár"}, {"szo": "nyugdíj"}],
               "felkapott": [{"kifejezes": "tüntetés"}], "youtube": [{"szo": "szorongás"}]}
    eredmeny = {"figyelem_atrendezodes": {"erosodo": ["benzinár", "KITALÁLT"], "gyengulo": ["nyugdíj"]},
                "vezetoi_osszefoglalo": ["x"], "ugyek_eletutja": {},
                "melyebb_temak": [], "google_youtube_osszefugges": "", "jovo_heti_figyelendok": []}
    out = he.grounding_validal(eredmeny, korpusz)
    assert "benzinár" in out["figyelem_atrendezodes"]["erosodo"]
    assert "KITALÁLT" not in out["figyelem_atrendezodes"]["erosodo"]   # nem korpuszbeli → kiesik


def test_figyelem_adat_rendezett_nem_none():
    korpusz = {"kulcsszavak": [
        {"szo": "a", "elteres_szokasostol": 12.0, "irany": "nő", "illeszkedes": "felette", "domen": "d"},
        {"szo": "b", "elteres_szokasostol": None, "irany": None, "illeszkedes": None, "domen": "d"},
        {"szo": "c", "elteres_szokasostol": -7.0, "irany": "csökken", "illeszkedes": "alatta", "domen": "d"}]}
    adat = he.figyelem_adat(korpusz)
    assert [x["szo"] for x in adat] == ["a", "c"]            # None kiesik, eltérés szerint csökkenő
    assert adat[0]["elteres"] == 12.0 and adat[1]["elteres"] == -7.0


def test_heti_generalas_ir_es_meta(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    sdk = _HamisSdk(_teljes_valasz())
    out = he.heti_generalas(str(tmp_path), "2026-09-29", "2026-10-06T07:00:00+00:00",
                            kliens=he._HetiKliens(sdk=sdk))
    assert out is not None
    p = tmp_path / "heti" / "2026-09-29.json"
    assert p.exists()
    mentve = json.loads(p.read_text(encoding="utf-8"))
    assert mentve["het_kezdet"] == "2026-09-29" and mentve["het_veg"] == "2026-10-05"
    assert mentve["iso_het"] == "2026-W40"
    assert mentve["keszult"] == "2026-10-06T07:00:00+00:00"
    assert mentve["modell"] == "claude-opus-4-8"
    assert mentve["vezetoi_osszefoglalo"] == ["a", "b"]
    # a diagram-adat (figyelem) + a korpusz-meta benne van
    assert any(x["szo"] == "benzinár" for x in mentve["figyelem"])
    assert mentve["korpusz"]["napok"] == 0


def test_heti_generalas_fail_soft_none(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    class _Buko:
        def uzenet(self, *a, **k): raise RuntimeError("tartós")
    out = he.heti_generalas(str(tmp_path), "2026-09-29", "2026-10-06T07:00:00+00:00",
                            kliens=_Buko())
    assert out is None
    assert not (tmp_path / "heti" / "2026-09-29.json").exists()


def test_heti_index_ir(tmp_path):
    for h in ("2026-09-22", "2026-09-29"):
        (tmp_path / "heti").mkdir(parents=True, exist_ok=True)
        (tmp_path / "heti" / f"{h}.json").write_text("{}", encoding="utf-8")
    he.heti_index_ir(str(tmp_path))
    idx = json.loads((tmp_path / "heti" / "index.json").read_text(encoding="utf-8"))
    assert idx["hetek"] == ["2026-09-22", "2026-09-29"]
    assert idx["legutolso"] == "2026-09-29"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_heti_ertekeles.py -q -k "grounding or figyelem or generalas or index"`
Expected: FAIL (`AttributeError`).

- [ ] **Step 3: Write minimal implementation** (a `heti_ertekeles.py` végére)

```python
def grounding_validal(eredmeny, korpusz):
    """Hallucináció-védelem: az `erosodo`/`gyengulo` szó-listákat a korpusz kulcsszó-halmazára szűri
    (a nem-korpuszbeli kiesik). A prózai mezők (vezetoi_osszefoglalo, melyebb_temak, összefüggés,
    figyelendők) NEM szűrtek — ezek a modell értelmezései a grounded számok fölött. Determinista,
    nem mutálja a bemenetet."""
    kov = {s.get("szo") for s in (korpusz.get("kulcsszavak") or [])}
    kov |= {s.get("kifejezes") for s in (korpusz.get("felkapott") or [])}
    kov |= {s.get("szo") for s in (korpusz.get("youtube") or [])}
    fa = eredmeny.get("figyelem_atrendezodes") or {}
    tiszta = {
        "erosodo": [sz for sz in (fa.get("erosodo") or []) if sz in kov],
        "gyengulo": [sz for sz in (fa.get("gyengulo") or []) if sz in kov],
    }
    return {**eredmeny, "figyelem_atrendezodes": tiszta}


def figyelem_adat(korpusz):
    """A divergáló sávdiagram DETERMINISTA adata: a nem-None eltérésű követett szavak, az eltérés
    szerint CSÖKKENŐ sorrendben (erősödő = pozitív felül, gyengülő = negatív alul)."""
    sorok = [{"szo": s.get("szo"), "elteres": s.get("elteres_szokasostol"),
              "irany": s.get("irany"), "illeszkedes": s.get("illeszkedes"), "domen": s.get("domen")}
             for s in (korpusz.get("kulcsszavak") or []) if s.get("elteres_szokasostol") is not None]
    return sorted(sorok, key=lambda x: x["elteres"], reverse=True)


def heti_ir(docs_data, het_kezdet, eredmeny):
    """A heti eredmény külön `heti/<het_kezdet>.json`-ba, atomi írással (a havi_nlp_ir mintája)."""
    mappa = Path(docs_data) / "heti"
    mappa.mkdir(parents=True, exist_ok=True)
    return json_export._ir_json(mappa / (het_kezdet + ".json"), eredmeny)


def heti_index_ir(docs_data):
    """A heti mappa hetei a frontend hét-választójához (az index.json-t kihagyva)."""
    mappa = Path(docs_data) / "heti"
    hetek = sorted(p.stem for p in mappa.glob("*.json") if p.stem != "index")
    return json_export._ir_json(mappa / "index.json",
                                {"hetek": hetek, "legutolso": hetek[-1] if hetek else None})


def heti_generalas(docs_data, het_kezdet, keszult_iso, kliens=None):
    """A heti értékelés generáló belépési pontja: korpusz → Claude (fail-soft: tartós hibán None) →
    grounding → figyelem-diagramadat + het/keszult/modell/korpusz-meta → atomi írás. A keszult_iso
    PARAMÉTER (nincs argless datetime.now())."""
    korpusz = heti_korpusz(docs_data, het_kezdet)
    try:
        eredmeny = heti_elemez(korpusz, kliens=kliens)
    except Exception as e:   # noqa: BLE001 — tartós API-hiba a bounded retry után: fail-soft
        _log.error("HIBA: a heti értékelés tartósan elhasalt (%s hét): %s", het_kezdet, e)
        return None
    eredmeny = grounding_validal(eredmeny, korpusz)
    eredmeny["het_kezdet"] = korpusz["het_kezdet"]
    eredmeny["het_veg"] = korpusz["het_veg"]
    eredmeny["iso_het"] = korpusz["iso_het"]
    eredmeny["figyelem"] = figyelem_adat(korpusz)
    eredmeny["keszult"] = keszult_iso
    eredmeny["modell"] = MODELL
    eredmeny["korpusz"] = {"het_kezdet": korpusz["het_kezdet"], "het_veg": korpusz["het_veg"],
                           "iso_het": korpusz["iso_het"], "napok": korpusz["napok"],
                           "egyedi_felkapott": len(korpusz["felkapott"])}
    heti_ir(docs_data, het_kezdet, eredmeny)
    return eredmeny
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_heti_ertekeles.py -q`
Expected: PASS (az összes).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/heti_ertekeles.py tests/test_heti_ertekeles.py
git commit -m "feat(heti): grounding + figyelem-diagramadat + atomi iras + index + generalas (fail-soft)"
```

---

### Task 4: `heti_orzo.py` — hétfő + idempotencia-őr

**Files:**
- Create: `trendfigyelo/heti_orzo.py`
- Test: `tests/test_heti_orzo.py`

**Interfaces:**
- Consumes: `seged.esti_nap(most)`, `seged.most_utc()`; a `heti/<het_kezdet>.json` `keszult` mezője.
- Produces: `elozo_het_hetfo(most) -> str` (az előző, lezárult hét hétfője, YYYY-MM-DD); `hetfo_e(most) -> bool`; `mar_kesz(docs_data, het_kezdet, logikai_nap_iso) -> bool`; `kell_generalni(docs_data, most) -> str|None`; `main(argv=None)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_heti_orzo.py
from datetime import datetime, timezone
import json

from trendfigyelo import heti_orzo as ho


def _bp(y, m, d, h):   # budapesti falióra → UTC-aware datetime (a seged.esti_nap BP-re számol)
    from zoneinfo import ZoneInfo
    return datetime(y, m, d, h, tzinfo=ZoneInfo("Europe/Budapest")).astimezone(timezone.utc)


def test_hetfo_e():
    assert ho.hetfo_e(_bp(2026, 10, 5, 9)) is True       # 2026-10-05 hétfő
    assert ho.hetfo_e(_bp(2026, 10, 6, 9)) is False      # kedd


def test_elozo_het_hetfoje():
    # hétfő reggel → az ELŐZŐ (lezárult) hét hétfője = egy héttel korábbi hétfő
    assert ho.elozo_het_hetfo(_bp(2026, 10, 5, 9)) == "2026-09-28"


def test_hajnali_hetfo_az_elozo_estehez_sorolodik_de_meg_hetfo():
    # 2026-10-05 01:00 BP → esti_nap = 2026-10-04 (vasárnap) → NEM hétfő → skip
    assert ho.hetfo_e(_bp(2026, 10, 5, 1)) is False


def test_kell_generalni_nem_hetfon_none(tmp_path):
    assert ho.kell_generalni(str(tmp_path), _bp(2026, 10, 6, 9)) is None


def test_kell_generalni_hetfon_az_elozo_hetet(tmp_path):
    assert ho.kell_generalni(str(tmp_path), _bp(2026, 10, 5, 9)) == "2026-09-28"


def test_idempotencia_ma_mar_kesz_skip(tmp_path):
    (tmp_path / "heti").mkdir(parents=True)
    # a keszult LOGIKAI napja 2026-10-05 (hétfő reggel) → ma már kész → skip
    (tmp_path / "heti" / "2026-09-28.json").write_text(
        json.dumps({"keszult": "2026-10-05T07:00:00+00:00"}), encoding="utf-8")
    assert ho.kell_generalni(str(tmp_path), _bp(2026, 10, 5, 9)) is None


def test_idempotencia_korabbi_keszult_ujra(tmp_path):
    (tmp_path / "heti").mkdir(parents=True)
    (tmp_path / "heti" / "2026-09-28.json").write_text(
        json.dumps({"keszult": "2026-09-30T07:00:00+00:00"}), encoding="utf-8")
    assert ho.kell_generalni(str(tmp_path), _bp(2026, 10, 5, 9)) == "2026-09-28"


def test_main_cli(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(ho.seged, "most_utc", lambda: _bp(2026, 10, 5, 9))
    assert ho.main([str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == "2026-09-28"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_heti_orzo.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

```python
# trendfigyelo/heti_orzo.py
"""A heti értékelés hétfő + idempotencia-őre (a havi_orzo.py mintájára).

A heti.yml a „Reggeli felkapott-gyűjtés" befejezésére fut; a reggeli/napi backupok ugyanazon a napon
többször is elindíthatják. Ez a modul eldönti: (1) MA hétfő-e a `seged.esti_nap` logikai nap szerint
(a hajnali <6:00 BP futás az ELŐZŐ naphoz sorolódik, így egy vasárnap hajnali backup nem indít heti
futást), és (2) az ELŐZŐ (lezárult) hétre MA már generálódott-e (a keszult LOGIKAI napja alapján,
a backup-újraindítás kihagyása). Kimenet: a generálandó hét hétfője („YYYY-MM-DD") vagy None/üres sor.
"""
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from . import seged


def _logikai_datum(most):
    return date.fromisoformat(seged.esti_nap(most))


def hetfo_e(most):
    """True, ha az esti_nap logikai nap HÉTFŐ (isoweekday()==1)."""
    return _logikai_datum(most).isoweekday() == 1


def elozo_het_hetfo(most):
    """Az előző, LEZÁRULT hét hétfője (YYYY-MM-DD). Hétfőn futtatva a mai hétfő − 7 nap."""
    d = _logikai_datum(most)
    ezen_het_hetfo = d - timedelta(days=d.isoweekday() - 1)
    return (ezen_het_hetfo - timedelta(days=7)).isoformat()


def _keszult_logikai_nap(docs_data, het_kezdet):
    """A meglévő heti/<het_kezdet>.json keszult-jének LOGIKAI (esti_nap) napja, vagy None (a hajnali
    dedup: a hajnali generálás keszultje logikailag az előző estéhez tartozik)."""
    fajl = Path(docs_data) / "heti" / f"{het_kezdet}.json"
    try:
        art = json.loads(fajl.read_text(encoding="utf-8"))
        k = art.get("keszult") if isinstance(art, dict) else None
        return seged.esti_nap(datetime.fromisoformat(k)) if isinstance(k, str) else None
    except (OSError, ValueError, TypeError):
        return None


def mar_kesz(docs_data, het_kezdet, logikai_nap_iso):
    """True, ha erre a hétre MA (a logikai napon) már generálódott."""
    return _keszult_logikai_nap(docs_data, het_kezdet) == logikai_nap_iso


def kell_generalni(docs_data, most):
    """A generálandó hét hétfője („YYYY-MM-DD"), vagy None: ha nem hétfő, vagy MA már kész."""
    if not hetfo_e(most):
        return None
    het_kezdet = elozo_het_hetfo(most)
    if mar_kesz(docs_data, het_kezdet, seged.esti_nap(most)):
        return None
    return het_kezdet


def main(argv=None):
    """CLI: `<docs_data>` → a generálandó hét hétfője (pl. '2026-09-28'), vagy ÜRES sor (skip)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    docs_data = argv[0] if argv else "docs/data"
    het = kell_generalni(docs_data, seged.most_utc())
    print(het or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_heti_orzo.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/heti_orzo.py tests/test_heti_orzo.py
git commit -m "feat(heti): heti_orzo - hetfo + idempotencia-or (elozo lezarult het, hajnali dedup)"
```

---

### Task 5: `heti.py` belépő

**Files:**
- Create: `heti.py` (repo gyökér)
- Test: `tests/test_heti_belepo.py`

**Interfaces:**
- Consumes: `heti_ertekeles.heti_generalas` + `heti_index_ir`, `seged.most_utc`.
- Produces: `main(argv=None) -> int` (0 siker, 1 bukás/nincs hét).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_heti_belepo.py
import importlib
import sys

import heti as heti_belepo


def test_ures_argv_nincs_teendo(capsys):
    assert heti_belepo.main([]) == 0
    assert "Nincs" in capsys.readouterr().out


def test_siker_generalas_es_index(monkeypatch, tmp_path):
    hivott = {}
    monkeypatch.setattr(heti_belepo.heti_ertekeles, "heti_generalas",
                        lambda dd, het, ki, kliens=None: hivott.setdefault("gen", (dd, het, ki)) or {"ok": 1})
    monkeypatch.setattr(heti_belepo.heti_ertekeles, "heti_index_ir",
                        lambda dd: hivott.setdefault("idx", dd))
    assert heti_belepo.main(["2026-09-28"]) == 0
    assert hivott["gen"][1] == "2026-09-28"
    assert "idx" in hivott


def test_fail_soft_nincs_index(monkeypatch):
    monkeypatch.setattr(heti_belepo.heti_ertekeles, "heti_generalas",
                        lambda *a, **k: None)
    hivott = {}
    monkeypatch.setattr(heti_belepo.heti_ertekeles, "heti_index_ir",
                        lambda dd: hivott.setdefault("idx", True))
    assert heti_belepo.main(["2026-09-28"]) == 1
    assert "idx" not in hivott        # bukott generálás → NINCS index-frissítés
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_heti_belepo.py -q`
Expected: FAIL (`ModuleNotFoundError: heti`).

- [ ] **Step 3: Write minimal implementation**

```python
# heti.py  (repo gyökér — a havi.py mintája)
"""A heti értékelés generáló belépője (a heti.yml workflow ezt hívja): a heti_orzo által megadott
hétre generál (fail-soft), siker esetén frissíti a hét-indexet is. A kulcsot a heti_ertekeles
_HetiKliens az ANTHROPIC_API_KEY env-ből olvassa."""
import sys

from trendfigyelo import heti_ertekeles, seged


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or not argv[0]:
        print("Nincs megadott hét — nincs teendő.")
        return 0
    het_kezdet = argv[0]
    docs_data = "docs/data"
    keszult_iso = seged.most_utc().isoformat()
    eredmeny = heti_ertekeles.heti_generalas(docs_data, het_kezdet, keszult_iso)
    if eredmeny is None:
        print(f"A heti értékelés generálása elhasalt ({het_kezdet}) — nincs index-frissítés.")
        return 1
    heti_ertekeles.heti_index_ir(docs_data)
    print(f"Heti értékelés kész: {het_kezdet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_heti_belepo.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add heti.py tests/test_heti_belepo.py
git commit -m "feat(heti): heti.py belepo (fail-soft generalas + index-frissites sikerkor)"
```

---

### Task 6: `.github/workflows/heti.yml` — hétfői workflow

**Files:**
- Create: `.github/workflows/heti.yml`
- Test: `tests/test_heti_workflow.py`

**Interfaces:**
- Consumes: `trendfigyelo.heti_orzo` (őr, stdlib, pip install ELŐTT), `heti.py` (generálás), `ANTHROPIC_API_KEY` secret.
- Produces: a workflow yaml (a havi.yml mintája, a „Reggeli felkapott-gyűjtés"-re).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_heti_workflow.py
from pathlib import Path

import yaml   # a projekt tesztjei már használják (pl. config); ha nem elérhető, lásd Step 3 megjegyzés


def _wf():
    return yaml.safe_load(Path(".github/workflows/heti.yml").read_text(encoding="utf-8"))


def test_trigger_a_reggeli_gyujtesre():
    wf = _wf()
    on = wf[True] if True in wf else wf["on"]           # a yaml az `on`-t True-ra oldhatja
    assert on["workflow_run"]["workflows"] == ["Reggeli felkapott-gyűjtés"]
    assert "workflow_dispatch" in on


def test_or_a_pip_install_elott_es_anthropic_secret():
    szoveg = Path(".github/workflows/heti.yml").read_text(encoding="utf-8")
    i_or = szoveg.index("trendfigyelo.heti_orzo")
    i_pip = szoveg.index("pip install")
    assert i_or < i_pip                                  # az őr a pip install ELŐTT
    assert "ANTHROPIC_API_KEY" in szoveg
    assert "secrets.ANTHROPIC_API_KEY" in szoveg


def test_commit_csak_a_heti_mappat():
    szoveg = Path(".github/workflows/heti.yml").read_text(encoding="utf-8")
    assert "git add docs/data/heti" in szoveg
    assert "python heti.py" in szoveg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_heti_workflow.py -q`
Expected: FAIL (fájl nem létezik).

- [ ] **Step 3: Write minimal implementation** (ha a `yaml` import nem elérhető a teszt-envben, a teszt a `yaml`-os assertet hagyd ki és csak a szöveg-alapú asserteket tartsd meg — a repo tesztjei általában elérik a PyYAML-t a requirements-ből)

```yaml
# .github/workflows/heti.yml
name: Heti értékelés

on:
  workflow_run:
    workflows: ["Reggeli felkapott-gyűjtés"]   # hétfő reggel, a reggeli pillanatkép után
    types: [completed]
  workflow_dispatch:
    inputs:
      het:
        description: "Kézi teszt: adott hét (a hét HÉTFŐJE, YYYY-MM-DD) újragenerálása; üres = az őr dönt"
        required: false
        default: ""

permissions:
  contents: write

concurrency:
  group: heti-futtatas
  cancel-in-progress: false

jobs:
  heti:
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

      # Az őr a pip install ELŐTT: CSAK stdlib (heti_orzo/seged). A nem-hétfői (napi) reggeli
      # futások így nem telepítenek feleslegesen — a költséges pip install csak akkor fut, ha az
      # őr tényleg hetet kér (het != '').
      - name: "Hétfő + idempotencia-őr (a generálandó hét hétfője, vagy üres = skip)"
        id: guard
        shell: bash
        env:
          KEZI_INPUT: ${{ github.event.inputs.het }}
        run: |
          KEZI="$KEZI_INPUT"
          if [ -n "$KEZI" ]; then
            echo "Kézi (workflow_dispatch) felülbírálás: $KEZI"
            echo "het=$KEZI" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          HET="$(python -m trendfigyelo.heti_orzo docs/data)"
          echo "Őr szerint generálandó hét: '$HET' (üres = ma nincs teendő)"
          echo "het=$HET" >> "$GITHUB_OUTPUT"

      - name: Függőségek telepítése (csak generáláskor)
        if: steps.guard.outputs.het != ''
        run: pip install -r requirements.txt

      - name: Heti értékelés generálása
        if: steps.guard.outputs.het != ''
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          HET: ${{ steps.guard.outputs.het }}
        run: |
          set -o pipefail
          python heti.py "$HET" 2>&1 | tee heti.log

      - name: Változások commitolása (CSAK a heti fájlok, KÜLÖN commit)
        if: always() && github.ref == 'refs/heads/main' && steps.guard.outputs.het != ''
        env:
          HET: ${{ steps.guard.outputs.het }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git pull --rebase --autostash || true
          git add docs/data/heti
          if git diff --staged --quiet; then
            echo "Nincs heti-értékelés-változás — nincs commit."
          else
            git commit -m "adat: heti értékelés ($HET, $(date -u +%Y-%m-%dT%H:%MZ))"
            git push
          fi

      - name: Artefakt (a log + a heti fájlok — mindig)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: heti-${{ github.run_id }}
          retention-days: 14
          path: |
            heti.log
            docs/data/heti/**
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_heti_workflow.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/heti.yml tests/test_heti_workflow.py
git commit -m "feat(heti): heti.yml workflow (Reggeli gyujtesre, or a pip install elott, csak heti commit)"
```

---

### Task 7: `heti.html` váz + nav 6. fül minden oldalon

**Files:**
- Create: `docs/heti.html`
- Modify: `docs/elemzes.html`, `docs/havi.html`, `docs/trendek.html`, `docs/youtube.html`, `docs/adatokrol.html` (mind az 5: a `#fomenu`-be a 6. fül „Heti értékelés", az `elemzes.html` és `havi.html` közé)
- Modify: `e2e/menu.spec.js` (5→6 fül, az új ordered list, új heti-teszt)

**Interfaces:**
- Produces: `docs/heti.html` a `#heti` main-nel (`#heti-het-panel` aside + `#heti-tartalom` section), a vendorelt `js/app.js` + `vendor/chartjs/chart.umd.js` + `js/heti.js` betöltve. A nav minden oldalon 6 fül.

- [ ] **Step 1: Write the failing test** (`e2e/menu.spec.js` — a meglévő asserteket frissítjük 6-ra, és új heti-teszt)

```javascript
// e2e/menu.spec.js — az ELSŐ teszt címe és állításai 5→6-ra:
test("menüsor: 6 fül, aktív = Google Trendek; a linkek helyesek + sorrend", async ({ page }) => {
  await page.goto("/trendek.html");
  await expect(page.locator("#fomenu a")).toHaveCount(6);
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Google Trendek");
  await expect(page.locator('#fomenu a[href="elemzes.html"]')).toHaveText("Napi Elemzések");
  await expect(page.locator('#fomenu a[href="heti.html"]')).toHaveText("Heti értékelés");
  await expect(page.locator('#fomenu a[href="havi.html"]')).toHaveText("Havi elemzés");
  await expect(page.locator('#fomenu a[href="trendek.html"]')).toHaveText("Google Trendek");
  await expect(page.locator('#fomenu a[href="youtube.html"]')).toHaveText("YouTube Trendek");
  await expect(page.locator('#fomenu a[href="adatokrol.html"]')).toHaveText("Infó");
  await expect(page.locator("#fomenu a")).toHaveText(
    ["Napi Elemzések", "Heti értékelés", "Havi elemzés", "Google Trendek", "YouTube Trendek", "Infó"]);
  await expect(page.locator("#labresz")).toBeAttached();
  await expect(page.locator("#adatokrol")).toHaveCount(0);
});

// a „havi.html: …" teszt ordered-listáját is 6-ra (ugyanaz a 6-elemű tömb), és ÚJ teszt:
test("heti.html: a fül betölt, a Heti értékelés menüpont aktív", async ({ page }) => {
  await page.goto("/heti.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Heti értékelés");
  await expect(page.locator("#fomenu a")).toHaveText(
    ["Napi Elemzések", "Heti értékelés", "Havi elemzés", "Google Trendek", "YouTube Trendek", "Infó"]);
  await expect(page.locator("#heti")).toBeAttached();
});
```

(A `havi.html` meglévő teszt `toHaveText([...])` tömbjét is cseréld a 6-eleműre.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx playwright test e2e/menu.spec.js`
Expected: FAIL (5 fül van, nincs heti.html).

- [ ] **Step 3: Write minimal implementation**

`docs/heti.html` (a havi.html mintája, Leaflet NÉLKÜL):

```html
<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Heti értékelés – Trendfigyelő</title>
  <link rel="stylesheet" href="css/app.css">
</head>
<body>
  <nav id="fomenu" aria-label="Fő menü">
    <a href="elemzes.html">Napi Elemzések</a>
    <a href="heti.html" class="aktiv" aria-current="page">Heti értékelés</a>
    <a href="havi.html">Havi elemzés</a>
    <a href="trendek.html">Google Trendek</a>
    <a href="youtube.html">YouTube Trendek</a>
    <a href="adatokrol.html">Infó</a>
  </nav>

  <header class="fejlec-doboz">
    <h1>Heti értékelés</h1>
    <p class="halvany" id="heti-fejlec">Betöltés…</p>
  </header>

  <main id="heti">
    <aside id="heti-het-panel" aria-label="Hét választó"></aside>
    <section id="heti-tartalom" aria-live="polite"></section>
  </main>

  <footer id="labresz" aria-label="Lábléc"></footer>

  <script src="js/app.js"></script>
  <script src="vendor/chartjs/chart.umd.js"></script>
  <script src="js/heti.js"></script>
</body>
</html>
```

A másik 5 oldalon a `#fomenu`-be az `elemzes.html` sor UTÁN told be (az `aktiv`/`aria-current` CSAK a saját oldalon marad; a heti sornál ezeken NINCS `class="aktiv"`):

```html
    <a href="heti.html">Heti értékelés</a>
```

Konkrétan mind az 5 fájlban (`elemzes.html`, `havi.html`, `trendek.html`, `youtube.html`, `adatokrol.html`) a meglévő
`<a href="elemzes.html"...>Napi Elemzések</a>` és `<a href="havi.html"...>Havi elemzés</a>` sorok KÖZÉ kerül a `<a href="heti.html">Heti értékelés</a>` sor (a `havi.html`-ben a havi link marad `aktiv`, a heti nem).

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test e2e/menu.spec.js`
Expected: PASS. Majd a teljes e2e menü-rész zöld.

- [ ] **Step 5: Commit**

```bash
git add docs/heti.html docs/elemzes.html docs/havi.html docs/trendek.html docs/youtube.html docs/adatokrol.html e2e/menu.spec.js
git commit -m "feat(heti): heti.html vaz + nav 6. ful (Heti ertekeles) minden oldalon"
```

---

### Task 8: `docs/js/heti.js` — 6 szekció + divergáló sávdiagram + hét-választó

**Files:**
- Create: `docs/js/heti.js`
- Modify: `docs/css/app.css` (a `.heti-*` stílusok — a `.havi-*` mintája)
- Create: `e2e/heti.spec.js`

**Interfaces:**
- Consumes: `data/heti/<het>.json` (`vezetoi_osszefoglalo/figyelem_atrendezodes/ugyek_eletutja/melyebb_temak/google_youtube_osszefugges/jovo_heti_figyelendok/figyelem/korpusz/het_kezdet/het_veg/iso_het/modell`) + `data/heti/index.json` (`hetek/legutolso`); a globális `Chart`.
- Produces: a `#heti-tartalom` renderelése + `#heti-het-panel` hét-választó.

- [ ] **Step 1: Write the failing test** (`e2e/heti.spec.js` — a havi/elemzes spec mintája, route-mockkal)

```javascript
const { test, expect } = require("@playwright/test");

const INDEX = { hetek: ["2026-09-21", "2026-09-28"], legutolso: "2026-09-28" };

function hetiArt(het) {
  return {
    het_kezdet: het, het_veg: "2026-10-04", iso_het: "2026-W40", modell: "claude-opus-4-8",
    korpusz: { het_kezdet: het, het_veg: "2026-10-04", iso_het: "2026-W40", napok: 7, egyedi_felkapott: 12 },
    vezetoi_osszefoglalo: ["Megállapítás egy.", "Megállapítás kettő."],
    figyelem_atrendezodes: { erosodo: ["benzinár"], gyengulo: ["nyugdíj"] },
    ugyek_eletutja: { rovid_kiugras: "Rövid x.", hosszabb_kiugras: "Hosszú y.", visszatero: "Vissza z." },
    melyebb_temak: [{ tema: "Üzemanyag", keresesi_palya: "nőtt", kapcsolodo_kifejezesek: "benzin, gázár",
                      ellenorzott_esemenyek: "Hír A.", magyarazat: "Mert." }],
    google_youtube_osszefugges: "Párhuzam a szorongásnál.",
    jovo_heti_figyelendok: ["Figyeld a benzinárat."],
    figyelem: [{ szo: "benzinár", elteres: 12.0, irany: "nő", illeszkedes: "felette", domen: "megelhetes" },
               { szo: "nyugdíj", elteres: -7.0, irany: "csökken", illeszkedes: "alatta", domen: "megelhetes" }],
  };
}

async function mock(page, art) {
  await page.route("**/data/heti/index.json", (r) => r.fulfill({ json: INDEX }));
  await page.route("**/data/heti/*.json", (r) => {
    if (r.request().url().includes("index.json")) return r.continue();
    return r.fulfill({ json: art });
  });
}

test("heti: a 6 rész + a figyelem-diagram renderel", async ({ page }) => {
  await mock(page, hetiArt("2026-09-28"));
  await page.goto("/heti.html");
  await expect(page.locator("#heti-tartalom")).toContainText("Megállapítás egy.");
  await expect(page.locator("#heti-tartalom")).toContainText("Üzemanyag");
  await expect(page.locator("#heti-tartalom")).toContainText("Párhuzam a szorongásnál.");
  await expect(page.locator("#heti-tartalom")).toContainText("Figyeld a benzinárat.");
  // a figyelem-diagram adatlistája (a11y-fallback) a két szót tartalmazza
  await expect(page.locator(".heti-figyelem-chart-doboz")).toBeAttached();
  await expect(page.locator("#heti-tartalom")).toContainText("benzinár");
  await expect(page.locator("#heti-tartalom")).toContainText("nyugdíj");
});

test("heti: hét-választó — korábbi hét betölthető", async ({ page }) => {
  await mock(page, hetiArt("2026-09-28"));
  await page.goto("/heti.html");
  await expect(page.locator(".heti-het-gomb")).toHaveCount(2);
  await page.locator('.heti-het-gomb[data-het="2026-09-21"]').click();
  await expect(page.locator('.heti-het-gomb[data-het="2026-09-21"]')).toHaveAttribute("aria-pressed", "true");
});

test("heti: fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/heti/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.route("**/data/heti/*.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/heti.html");
  await expect(page.locator("#heti-tartalom")).toContainText("nem érhető el");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx playwright test e2e/heti.spec.js`
Expected: FAIL (nincs heti.js).

- [ ] **Step 3: Write minimal implementation**

```javascript
// docs/js/heti.js
"use strict";
// „Heti értékelés" fül — a heti AI-riport (docs/data/heti/<het>.json) renderelése 6 részben:
// vezetői összefoglaló, figyelem átrendeződése (+ determinista divergáló sávdiagram), ügyek életútja,
// 2–3 mélyebb téma, Google–YouTube összefüggés, jövő heti figyelendők. A szöveges részek AI-generáltak
// és a korpuszra grounding-validáltak (lásd trendfigyelo/heti_ertekeles.py); a diagram a VALÓS
// számokból (eltérés a szokásos szinttől) determinista. NINCS new Date() — a hét az index.json-ból.

const HETI_SZIN_EROS = "#2a78d6";    // erősödő (pozitív eltérés) — az IDOSOR_PALETTA validált kékje
const HETI_SZIN_GYENGE = "#eb6834";  // gyengülő (negatív eltérés) — az IDOSOR_PALETTA validált narancsa
const heti_chartok = {};
window.heti_chartok = heti_chartok;

function helem(tag, cls, szoveg) {
  const h = document.createElement(tag);
  if (cls) h.className = cls;
  if (szoveg != null) h.textContent = szoveg;
  return h;
}

function url_het() {
  const m = (location.search || "").match(/[?&]het=(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : null;
}

function heti_cimke(h) {   // "2026-09-28" → "2026-09-28 – (hét)"; az ISO-hetet a fejléc adja
  return h;
}

async function heti_betolt(het) {
  const r = await fetch(`data/heti/${het}.json`);
  if (!r.ok) throw new Error("nem elérhető: " + het);
  return r.json();
}

// egy szekció: cím + opcionális bevezető + tetszőleges tartalom-elem
function heti_szekcio(cim) {
  const s = helem("section", "elemzes-szekcio heti-szekcio");
  s.appendChild(helem("h2", "elemzes-csoport-cim", cim));
  return s;
}

function lista_ul(elemek, cls) {
  const ul = helem("ul", cls || null);
  (elemek || []).filter((x) => x != null && String(x).trim()).forEach((x) =>
    ul.appendChild(helem("li", null, String(x))));
  return ul;
}

// divergáló sávdiagram: erősödő (pozitív) kék, gyengülő (negatív) narancs; legenda + a11y-adatlista
function heti_figyelem_chart(figyelem) {
  const doboz = helem("div", "heti-figyelem-chart-doboz");
  const sorok = (figyelem || []).filter((x) => x && typeof x.elteres === "number");
  if (!sorok.length) { doboz.appendChild(helem("p", "ures", "Nincs megjeleníthető eltérés-adat.")); return doboz; }
  // legenda (az identitás sosem csak szín: címkézett)
  const leg = helem("div", "heti-figyelem-legenda");
  const l1 = helem("span", "heti-leg-elem"); l1.appendChild(_szin_pont(HETI_SZIN_EROS));
  l1.appendChild(document.createTextNode(" erősödő (a szokásos fölött)")); leg.appendChild(l1);
  const l2 = helem("span", "heti-leg-elem"); l2.appendChild(_szin_pont(HETI_SZIN_GYENGE));
  l2.appendChild(document.createTextNode(" gyengülő (a szokásos alatt)")); leg.appendChild(l2);
  doboz.appendChild(leg);
  const chartDoboz = helem("div", "heti-chart-vaszon");
  chartDoboz.style.height = Math.max(240, sorok.length * 30) + "px";
  const canvas = helem("canvas"); canvas.id = "heti-figyelem-chart"; chartDoboz.appendChild(canvas);
  doboz.appendChild(chartDoboz);
  if (typeof Chart !== "undefined") {
    if (heti_chartok.figyelem && typeof heti_chartok.figyelem.destroy === "function") heti_chartok.figyelem.destroy();
    heti_chartok.figyelem = new Chart(canvas, {
      type: "bar",
      data: { labels: sorok.map((x) => x.szo),
              datasets: [{ data: sorok.map((x) => x.elteres),
                           backgroundColor: sorok.map((x) => x.elteres >= 0 ? HETI_SZIN_EROS : HETI_SZIN_GYENGE) }] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false } },
        scales: { x: { title: { display: true, text: "eltérés a szokásos szinttől" } },
                  y: { ticks: { autoSkip: false } } } },
    });
  }
  // a11y-adatlista (a canvas tartalma nem olvasható ki)
  const lista = helem("ul", "heti-chart-adatlista");
  sorok.forEach((x) => lista.appendChild(helem("li", null,
    `${x.szo} – ${x.elteres > 0 ? "+" : ""}${Math.round(x.elteres * 10) / 10}`)));
  doboz.appendChild(lista);
  return doboz;
}
function _szin_pont(szin) { const s = helem("span", "heti-leg-pont"); s.style.backgroundColor = szin; return s; }

function heti_tema_kartya(t) {
  const box = helem("section", "elemzes-szekcio heti-tema");
  box.appendChild(helem("h3", null, t.tema || "Téma"));
  const sor = (cimke, ertek) => { if (ertek && String(ertek).trim()) {
    const p = helem("p", "elemzes-szoveg");
    p.appendChild(helem("strong", null, cimke + " "));
    p.appendChild(document.createTextNode(String(ertek)));
    box.appendChild(p); } };
  sor("Keresési pálya:", t.keresesi_palya);
  sor("Kapcsolódó kifejezések:", t.kapcsolodo_kifejezesek);
  sor("Ellenőrzött események:", t.ellenorzott_esemenyek);
  sor("Magyarázat:", t.magyarazat);
  return box;
}

function rajzol_heti(art) {
  const t = document.getElementById("heti-tartalom");
  t.textContent = "";
  document.getElementById("heti-fejlec").textContent =
    `Heti értékelés – ${art.het_kezdet} … ${art.het_veg} (${art.iso_het || ""})`;
  t.appendChild(helem("p", "halvany",
    `Gépi elemzés — a(z) ${art.modell || "AI"} modell automatikusan generálta az előző hét kereséseiből.`));

  // 1) Vezetői összefoglaló
  const s1 = heti_szekcio("Vezetői összefoglaló");
  s1.appendChild(lista_ul(art.vezetoi_osszefoglalo, "heti-lista"));
  t.appendChild(s1);

  // 2) A figyelem átrendeződése + diagram
  const s2 = heti_szekcio("A figyelem átrendeződése");
  const fa = art.figyelem_atrendezodes || {};
  if ((fa.erosodo || []).length) { s2.appendChild(helem("h3", null, "Erősödő témák")); s2.appendChild(lista_ul(fa.erosodo)); }
  if ((fa.gyengulo || []).length) { s2.appendChild(helem("h3", null, "Gyengülő témák")); s2.appendChild(lista_ul(fa.gyengulo)); }
  s2.appendChild(heti_figyelem_chart(art.figyelem));
  t.appendChild(s2);

  // 3) Ügyek életútja
  const s3 = heti_szekcio("Az ügyek életútja");
  const ue = art.ugyek_eletutja || {};
  const ujsor = (cimke, ertek) => { if (ertek && String(ertek).trim()) {
    const p = helem("p", "elemzes-szoveg");
    p.appendChild(helem("strong", null, cimke + " "));
    p.appendChild(document.createTextNode(String(ertek)));
    s3.appendChild(p); } };
  ujsor("Rövid kiugrás:", ue.rovid_kiugras);
  ujsor("Hosszabb kiugrás:", ue.hosszabb_kiugras);
  ujsor("Visszatérő:", ue.visszatero);
  t.appendChild(s3);

  // 4) Mélyebb témák
  const s4 = heti_szekcio("Mélyebb témaelemzés");
  const temak = (art.melyebb_temak || []).filter((x) => x && x.tema);
  if (!temak.length) s4.appendChild(helem("p", "ures", "Ezen a héten nincs kiemelt mélyebb téma."));
  else temak.forEach((x) => s4.appendChild(heti_tema_kartya(x)));
  t.appendChild(s4);

  // 5) Google–YouTube összefüggés
  const s5 = heti_szekcio("Google–YouTube összefüggés");
  s5.appendChild(helem("p", "elemzes-szoveg", art.google_youtube_osszefugges || ""));
  t.appendChild(s5);

  // 6) Jövő heti figyelendők
  const s6 = heti_szekcio("Mit érdemes figyelni a jövő héten");
  s6.appendChild(lista_ul(art.jovo_heti_figyelendok, "heti-lista"));
  t.appendChild(s6);
}

function heti_panel_epit(hetek, aktiv) {
  const panel = document.getElementById("heti-het-panel");
  panel.textContent = "";
  panel.appendChild(helem("h2", "halvany", "Hét"));
  hetek.slice().sort().reverse().forEach((h) => {
    const g = document.createElement("button");
    g.type = "button"; g.className = "heti-het-gomb";
    g.setAttribute("data-het", h);
    g.setAttribute("aria-pressed", h === aktiv ? "true" : "false");
    g.textContent = heti_cimke(h);
    g.addEventListener("click", () => {
      panel.querySelectorAll(".heti-het-gomb").forEach((b) =>
        b.setAttribute("aria-pressed", b.getAttribute("data-het") === h ? "true" : "false"));
      heti_valt(h);
    });
    panel.appendChild(g);
  });
}

async function heti_valt(het) {
  try { rajzol_heti(await heti_betolt(het)); }
  catch (e) {
    document.getElementById("heti-fejlec").textContent = "Heti értékelés – nem érhető el";
    document.getElementById("heti-tartalom").textContent =
      "A heti értékelés jelenleg nem érhető el (még nem készült el ehhez a héthez).";
  }
}

async function heti_indit() {
  let idx = { hetek: [], legutolso: null };
  try {
    const r = await fetch("data/heti/index.json");
    if (r.ok) idx = await r.json();
  } catch (e) { /* nincs index */ }
  const hetek = (idx.hetek && idx.hetek.length) ? idx.hetek.slice() : [];
  if (!hetek.length) { await heti_valt("_nincs_"); return; }   // fail-soft: üres → „nem érhető el"
  const kert = url_het();
  const kezdo = (kert && hetek.indexOf(kert) >= 0) ? kert
    : (idx.legutolso && hetek.indexOf(idx.legutolso) >= 0 ? idx.legutolso : hetek[hetek.length - 1]);
  heti_panel_epit(hetek, kezdo);
  await heti_valt(kezdo);
}

document.addEventListener("DOMContentLoaded", heti_indit);
```

`docs/css/app.css` — a `.havi-*` szekció közelébe (a meglévő tokeneket használva):

```css
/* Heti értékelés fül */
#heti { display: flex; gap: 1rem; align-items: flex-start; flex-wrap: wrap; }
#heti-het-panel { flex: 0 0 160px; display: flex; flex-direction: column; gap: 0.35rem; }
#heti-tartalom { flex: 1 1 320px; min-width: 0; }
.heti-het-gomb { text-align: left; padding: 0.4rem 0.6rem; border: 1px solid #c9d3df; border-radius: 8px;
  background: #fff; cursor: pointer; }
.heti-het-gomb[aria-pressed="true"] { background: #2a78d6; color: #fff; border-color: #2a78d6; }
.heti-lista li { margin: 0.2rem 0; }
.heti-figyelem-chart-doboz { margin-top: 0.8rem; }
.heti-figyelem-legenda { display: flex; gap: 1.2rem; font-size: 0.9rem; margin-bottom: 0.4rem; flex-wrap: wrap; }
.heti-leg-pont { display: inline-block; width: 12px; height: 12px; border-radius: 3px; vertical-align: middle;
  margin-right: 4px; }
.heti-chart-vaszon { position: relative; }
.heti-chart-adatlista { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
@media (max-width: 640px) { #heti-het-panel { flex-basis: 100%; flex-direction: row; flex-wrap: wrap; } }
```

(A `.heti-chart-adatlista` vizuálisan rejtett, de a DOM-ban jelen van — az e2e `toContainText("benzinár")` ráillik.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test e2e/heti.spec.js`
Expected: PASS (3 teszt). A validáló paletta-ellenőrzés: a két szín (`#2a78d6`, `#eb6834`) az IDOSOR_PALETTA már validált párja — ha a reviewer kéri, futtasd:
`node /tmp/claude-1000/bundled-skills/*/dataviz/scripts/validate_palette.js "#2a78d6,#eb6834" --mode light` (elvárt: a pár elkülönül; a legenda-címkék a kontraszt-WARM-ot feloldják).

- [ ] **Step 5: Commit**

```bash
git add docs/js/heti.js docs/css/app.css e2e/heti.spec.js
git commit -m "feat(heti): heti.js - 6 szekcio + divergalo savdiagram + het-valaszto + CSS + e2e"
```

---

### Task 9: Infó-oldal — „A heti elemzés" szekció-csoport

**Files:**
- Modify: `docs/adatokrol.html` (új `.adat-csoport` „A heti elemzés", a napi és a havi csoport közé, a nav-sorrenddel összhangban)
- Modify: `e2e/menu.spec.js` (az Infó-teszt doboz- és csoport-számai + az új csoportcím)

**Interfaces:**
- Consumes: a meglévő `#adatokrol .adat-csoport`/`.adat-doboz` szerkezet.
- Produces: egy új csoport a heti értékelésről (mikor fut, mit tartalmaz a 6 rész, grounding, a divergáló diagram).

- [ ] **Step 1: Write the failing test** (`e2e/menu.spec.js` Infó-teszt frissítése)

```javascript
// az "Infó oldal: …" tesztben:
await expect(page.locator("#adatokrol .adat-doboz")).toHaveCount(28);  // +4 heti doboz (24→28)
await expect(page.locator("#adatokrol .adat-csoport")).toHaveCount(5); // +1 „A heti elemzés"
await expect(page.locator("#adatokrol .adat-csoport")).toHaveText([
  "Google Trend adatok", "YouTube Trend adatok", "Az elemzés (napi AI-összefoglaló)",
  "A heti elemzés (heti AI-összefoglaló)", "A havi elemzés (havi AI-összefoglaló)"]);
await expect(page.locator("#adatokrol")).toContainText("hétfő");
await expect(page.locator("#adatokrol")).toContainText("ügyek tartóssága");
```

(A csoport-sorrend a nav-sorrendet követi: napi → heti → havi. A heti csoport a napi és a havi KÖZÉ kerül.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx playwright test e2e/menu.spec.js -g "Infó"`
Expected: FAIL (24 doboz / 4 csoport van).

- [ ] **Step 3: Write minimal implementation**

A `docs/adatokrol.html`-ben a napi elemzés („Az elemzés (napi AI-összefoglaló)") `.adat-csoport` UTÁN, a havi csoport ELÉ illeszd be (4 `.adat-doboz`-szal; a meglévő `.adat-csoport`/`.adat-doboz` markup-mintát KÖVETVE — ugyanazok az osztályok és a belső szerkezet, mint a havi csoportnál):

```html
<section class="adat-csoport">
  <h2>A heti elemzés (heti AI-összefoglaló)</h2>

  <div class="adat-doboz">
    <h3>Mikor készül</h3>
    <p>Minden <strong>hétfő reggel</strong>, a reggeli felkapott-gyűjtés után, automatikusan
       lefut az előző <strong>hétfő–vasárnap</strong> hétre. Az új heti értékelés magától megjelenik
       a „Heti értékelés" fülön; a korábbi hetek a hét-választóval visszanézhetők.</p>
  </div>

  <div class="adat-doboz">
    <h3>Mit tartalmaz</h3>
    <p>Hat részt: vezetői összefoglaló; a figyelem átrendeződése (mely témák erősödtek/gyengültek a
       szokásos szintjükhöz képest); az <strong>ügyek tartóssága</strong> és életútja (rövid kiugrás,
       hosszabb kiugrás, visszatérő); 2–3 mélyebb témaelemzés; a Google- és YouTube-adatok összefüggése;
       és mit érdemes figyelni a jövő héten.</p>
  </div>

  <div class="adat-doboz">
    <h3>Honnan jönnek a számok</h3>
    <p>A számokat Python számolja a már meglévő mérésekből (a követett szavak heti iránya és a szokásos
       szinttől való eltérése, a héten felkapott szavak, a YouTube-trendek); a <code>claude-opus-4-8</code>
       modell ebből írja a szöveget. A modell semmit nem talál ki: okot vagy eseményt csak akkor ír,
       ha a héten tényleg volt hozzá hír (grounding).</p>
  </div>

  <div class="adat-doboz">
    <h3>A figyelem-diagram</h3>
    <p>A „figyelem átrendeződése" résznél egy sávdiagram a követett szavakat a szokásos szintjüktől való
       eltérésük szerint rendezi: a <strong>kék</strong> sávok a szokásos fölötti (erősödő), a
       <strong>narancs</strong> sávok a szokásos alatti (gyengülő) heteket jelölik. Ez a diagram a VALÓS
       mért számokból készül.</p>
  </div>
</section>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test e2e/menu.spec.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/adatokrol.html e2e/menu.spec.js
git commit -m "feat(heti): Info-oldal 'A heti elemzes' csoport (mikor/mit/szamok/diagram)"
```

---

## Self-Review

**Spec coverage:**
- §2 (6 rész) → Task 2 séma + prompt, Task 8 render. ✓
- §2 divergáló diagram → Task 1 `elteres_szokasostol`, Task 3 `figyelem_adat`, Task 8 chart. ✓
- §3 backend (korpusz/elemez/grounding/ir/index/generalas) → Task 1–3. ✓
- §3 orzo / entry / workflow → Task 4/5/6. ✓
- §3 frontend + hét-választó → Task 7/8. ✓ Nav 6. fül → Task 7. ✓
- §3 adat `heti/<hétfő>.json` + index → Task 3. ✓
- §4 séma → Task 2. §5 prompt → Task 2. §6 (mindig generál) → az orzo nem tartalmaz „csendes hét" kaput; a prompt a vezetői összefoglalóban jelzi a csendet. ✓
- §8 tesztek → minden task TDD-vel. Info-oldal → Task 9. ✓

**Placeholder scan:** nincs TBD/„add validation"; minden lépés konkrét kódot/yaml-t/html-t ad. ✓

**Type consistency:** `heti_korpusz` kulcs-mezők (`szo`/`elteres_szokasostol`/`irany`/`illeszkedes`/`palya`) konzisztensek Task 1↔3↔8 közt; `figyelem` lista mezője `elteres` (nem `elteres_szokasostol`) — a `figyelem_adat` átnevezi, a frontend `x.elteres`-t olvas (Task 3 teszt + Task 8 teszt egyezik). `het_kezdet`/`het_veg`/`iso_het` végig azonos. A `youtube` `nincs_adat` bool Task 1↔render. ✓

**Ruling (plan-szkennelés):** a `_felkapott_het` (Task 1) a `havi_korpusz` logikájához HASONLÓ, de NEM verbatim: dátum-ablakra szűr (nem hónap-prefix), és a mező `napok_szama` (nem `gyakorisag`). A közös 8 soros „reggel/este/lapos trendek" olvasás párhuzamos, de a két modul független windowinggal — a havi érintetlenségének (scope) megőrzése érdekében NEM vezetünk be közös helpert a havi_nlp.py-ba. A task-reviewer ezt párhuzamos-de-eltérő kódként fogadja el, nem duplikáció-defektként. — Költség, ha téves: egy jövőbeli közös-helper-refaktor (olcsó, izolált).
