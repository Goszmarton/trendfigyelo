# Kapcsolódó keresések (F4) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Új „Kapcsolódó keresések" szekció a Bővítés fülön: a napi felkapott témák mögé nézünk be (Google Trends related_queries top+rising), izolált, saját-plafonú, soft-fail gyűjtő-jobbal.

**Architecture:** Külön gyűjtő-job (a `masodlagos_only` mintája): `kapcsolodo.py` (jeloltek a felkapottakból + related_egy soft-fail + gyujt) → `docs/data/kapcsolodo.json`; napi őr + `kapcsolodo.yml` (a „Napi trendgyűjtés" után, saját Kliens/plafon). A fő `futtato.py` gyűjtés/plafon VÁLTOZATLAN. Frontend: új szekció a `bovites.js`-ben.

**Tech Stack:** Python 3.12 (stdlib + meglévő trendspy/pandas/json_export), vanilla JS, GitHub Actions, pytest + Playwright.

**Spec:** `docs/superpowers/specs/2026-10-08-kapcsolodo-keresesek-design.md`

## Global Constraints

- NULLA új Python-dependency (trendspy + pandas már dependency). Frontend: nincs új vendor/külső betöltés.
- A referer-header `{"referer":"https://www.google.com/"}` KÖTELEZŐ minden related-hívásnál. SOFT-FAIL mindenhol (kvóta/429 → None/skip, a job 0-val tér vissza, NEM dob).
- SAJÁT, SZŰK plafon (`cap × config.max_probak + 1`) a belépő Kliensén — a fő napi gyűjtés plafonja/kvótája ÉRINTETLEN. A `futtato.py` VÁLTOZATLAN.
- Irreplaceable adat (napok/*.json) READ-ONLY; atomi írás (`json_export._ir_json`). NINCS argless `datetime.now()` a modul-logikában (`most` PARAMÉTER; a belépő adja a `seged.most_utc()`-ot).
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; a workflow commit CSAK `docs/data/kapcsolodo.json`; NINCS ANTHROPIC_API_KEY (nincs LLM). Push külön kapuzott kör. SOROS suite zöld.
- Python-teszt: `.venv/bin/python -m pytest …` (`python` NINCS PATH-on). e2e: `npx playwright test …`.
- Nav VÁLTOZATLAN (7 fül). Defaultok: CAP=6, TIMEFRAME="today 3-m", STALENESS_NAP=7, RETENCIO=30, TOP_LIMIT=15.

---

### Task 1: `kapcsolodo.py` — konstansok + `jeloltek` + `_parse_related`

**Files:**
- Create: `trendfigyelo/kapcsolodo.py`
- Test: `tests/test_kapcsolodo.py`

**Interfaces:**
- Consumes: `docs/data/napok/<nap>.json` (`{reggel?/este?:{trendek:[{kifejezes,volumen}]}}` VAGY lapos `trendek`).
- Produces: `CAP/TIMEFRAME/STALENESS_NAP/RETENCIO/TOP_LIMIT/REFERER/AG`; `jeloltek(docs_data, meglevo, most, cap, staleness_nap, napok_vissza=2) -> [(kif, vol)]`; `_parse_related(eredmeny, limit) -> {top, rising}`. A Task 2 fogyasztja.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kapcsolodo.py
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from trendfigyelo import kapcsolodo as kp


def _nap(tmp_path, nap, trendek):
    p = tmp_path / "napok" / f"{nap}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"este": {"trendek": [
        {"kifejezes": k, "volumen": v} for (k, v) in trendek]}}, ensure_ascii=False), encoding="utf-8")


def test_jeloltek_top_volumen_es_cap(tmp_path):
    _nap(tmp_path, "2026-10-06", [("a", 10), ("b", 90)])
    _nap(tmp_path, "2026-10-07", [("b", 50), ("c", 70), ("d", 30)])
    most = datetime(2026, 10, 7, 21, tzinfo=timezone.utc)
    jel = kp.jeloltek(str(tmp_path), {}, most, cap=2, staleness_nap=7)
    assert jel == [("b", 90), ("c", 70)]            # max volumen a 2 napból, top 2


def test_jeloltek_staleness_kizar(tmp_path):
    _nap(tmp_path, "2026-10-07", [("b", 90), ("c", 70)])
    most = datetime(2026, 10, 7, 21, tzinfo=timezone.utc)
    meglevo = {"b": "2026-10-05T21:00:00+00:00"}     # 2 napja frissült → staleness 7-en belül → kizár
    jel = kp.jeloltek(str(tmp_path), meglevo, most, cap=5, staleness_nap=7)
    assert [k for k, _ in jel] == ["c"]


def test_jeloltek_regi_lekerdezes_ujra(tmp_path):
    _nap(tmp_path, "2026-10-07", [("b", 90)])
    most = datetime(2026, 10, 7, 21, tzinfo=timezone.utc)
    meglevo = {"b": "2026-09-01T21:00:00+00:00"}     # >7 napja → újra jelölt
    assert kp.jeloltek(str(tmp_path), meglevo, most, cap=5, staleness_nap=7) == [("b", 90)]


def test_parse_related_df_es_breakout():
    eredmeny = {
        "top": pd.DataFrame({"query": ["benzin ár", "mol benzin"], "value": [100, 19]}),
        "rising": pd.DataFrame({"query": ["benzin ársapka", "új"], "value": [8350, "Breakout"]}),
    }
    out = kp._parse_related(eredmeny, limit=15)
    assert out["top"] == [{"query": "benzin ár", "value": 100}, {"query": "mol benzin", "value": 19}]
    assert out["rising"][0] == {"query": "benzin ársapka", "value": 8350}
    assert out["rising"][1] == {"query": "új", "value": "Breakout"}    # string megőrizve


def test_parse_related_none_es_ures():
    assert kp._parse_related(None) == {"top": [], "rising": []}
    assert kp._parse_related({"top": None, "rising": pd.DataFrame({"query": [], "value": []})}) == {"top": [], "rising": []}


def test_parse_related_limit():
    df = pd.DataFrame({"query": [f"q{i}" for i in range(20)], "value": list(range(20))})
    out = kp._parse_related({"top": df, "rising": df}, limit=15)
    assert len(out["top"]) == 15 and len(out["rising"]) == 15
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_kapcsolodo.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

```python
# trendfigyelo/kapcsolodo.py
"""Kapcsolódó keresések (F4): a napi felkapott témák mögé nézünk be a Google Trends related_queries-szel
(top + rising). IZOLÁLT gyűjtő-job saját, szűk plafonnal (a masodlagos_only mintája) — a fő órás gyűjtés
kvótáját NEM viheti el; soft-fail; a related endpoint referer-headert igényel (lásd spike)."""
import glob
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from trendfigyelo import json_export

_log = logging.getLogger(__name__)

CAP = 6                 # kifejezés / futás (kvóta-biztos)
TIMEFRAME = "today 3-m"
STALENESS_NAP = 7       # egy kifejezés ennyi naponként frissül újra
RETENCIO = 30           # az utolsó ennyi lekérdezett kifejezés megtartva
TOP_LIMIT = 15          # a top/rising lista max hossza
REFERER = {"referer": "https://www.google.com/"}   # KÖTELEZŐ a related endpointhoz
AG = "kapcsolodo"


def _ertek(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return str(v)   # pl. "Breakout"


def _lista(df, limit):
    if df is None:
        return []
    try:
        sorok = df.to_dict("records")       # pandas DataFrame
    except AttributeError:
        sorok = list(df)                    # lista-szerű (teszt-kompat)
    ki = []
    for s in sorok[:limit]:
        q = (s.get("query") or "").strip() if isinstance(s, dict) else ""
        if q:
            ki.append({"query": q, "value": _ertek(s.get("value"))})
    return ki


def _parse_related(eredmeny, limit=TOP_LIMIT):
    e = eredmeny or {}
    return {"top": _lista(e.get("top"), limit), "rising": _lista(e.get("rising"), limit)}


def jeloltek(docs_data, meglevo, most, cap=CAP, staleness_nap=STALENESS_NAP, napok_vissza=2):
    """A legutóbbi `napok_vissza` napfájl felkapottjai max-volumen szerint; a `staleness_nap`-on
    belül frissített kifejezések kizárva; volumen szerint csökkenőben a top `cap`. Csak OLVAS."""
    fajlok = [f for f in sorted(glob.glob(os.path.join(docs_data, "napok", "*.json")))
              if len(Path(f).stem) == 10]
    vol = {}
    for f in fajlok[-napok_vissza:]:
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        trendek = []
        for szeg in ("reggel", "este"):
            trendek += (d.get(szeg) or {}).get("trendek", []) or []
        if not trendek:
            trendek = d.get("trendek") or []
        for tr in trendek:
            kif = (tr.get("kifejezes") or "").strip()
            if not kif:
                continue
            try:
                v = int(tr.get("volumen") or 0)
            except (TypeError, ValueError):
                v = 0
            vol[kif] = max(vol.get(kif, 0), v)
    friss = set()
    for kif, lek in (meglevo or {}).items():
        try:
            if (most - datetime.fromisoformat(lek)).days < staleness_nap:
                friss.add(kif)
        except (TypeError, ValueError):
            pass
    jel = [(k, v) for k, v in vol.items() if k not in friss]
    jel.sort(key=lambda kv: (-kv[1], kv[0]))
    return jel[:cap]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_kapcsolodo.py -q`
Expected: PASS (6 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/kapcsolodo.py tests/test_kapcsolodo.py
git commit -m "feat(kapcsolodo): jeloltek (felkapott top-volumen + staleness) + _parse_related (top/rising)"
```

---

### Task 2: `kapcsolodo.py` — `related_egy` (soft-fail) + `gyujt` + `kapcsolodo_ir`

**Files:**
- Modify: `trendfigyelo/kapcsolodo.py`
- Test: `tests/test_kapcsolodo.py`

**Interfaces:**
- Consumes: `jeloltek`/`_parse_related` (Task 1), `Kliens.hivas`, `config.geo`, `json_export._ir_json`.
- Produces: `related_egy(kliens, kif, config, timeframe) -> {top,rising}|None`; `gyujt(docs_data, kliens, config, most, ...) -> dict`; `kapcsolodo_ir(docs_data, adat)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kapcsolodo.py  (hozzáadás)
class _FakeTr:
    def __init__(self, map_):
        self._map = map_          # kif -> {top, rising} dict VAGY Exception-példány
        self.hivott = []

    def related_queries(self, keyword, geo=None, timeframe=None, headers=None):
        self.hivott.append((keyword, geo, timeframe, headers))
        r = self._map.get(keyword)
        if isinstance(r, Exception):
            raise r
        return r


class _FakeKliens:
    def __init__(self, tr): self.tr = tr
    def hivas(self, ag, fn, *a, **k): return fn(*a, **k)   # throttle nélkül (teszt)


class _Cfg:
    geo = "HU"; max_probak = 4


def _df(rows):
    import pandas as pd
    return pd.DataFrame({"query": [q for q, _ in rows], "value": [v for _, v in rows]})


def test_related_egy_referer_es_parse():
    tr = _FakeTr({"benzin": {"top": _df([("benzin ár", 100)]), "rising": _df([("ársapka", "Breakout")])}})
    out = kp.related_egy(_FakeKliens(tr), "benzin", _Cfg(), timeframe="today 3-m")
    assert out["top"] == [{"query": "benzin ár", "value": 100}]
    assert tr.hivott[0][3] == {"referer": "https://www.google.com/"}   # referer-header átadva
    assert tr.hivott[0][1] == "HU" and tr.hivott[0][2] == "today 3-m"


def test_related_egy_soft_fail():
    tr = _FakeTr({"x": RuntimeError("kvóta")})
    assert kp.related_egy(_FakeKliens(tr), "x", _Cfg()) is None     # nem dob, None


def test_gyujt_merge_lekerdezve_es_retencio(tmp_path):
    _nap(tmp_path, "2026-10-07", [("benzin", 90), ("rezsi", 50)])
    tr = _FakeTr({"benzin": {"top": _df([("benzin ár", 100)]), "rising": _df([])},
                  "rezsi": {"top": _df([("rezsi csökkentés", 80)]), "rising": _df([])}})
    most = datetime(2026, 10, 7, 21, tzinfo=timezone.utc)
    out = kp.gyujt(str(tmp_path), _FakeKliens(tr), _Cfg(), most, cap=5, retencio=30)
    kif = {k["kifejezes"]: k for k in out["kifejezesek"]}
    assert "benzin" in kif and kif["benzin"]["lekerdezve"] == most.isoformat()
    assert kif["benzin"]["volumen"] == 90 and kif["benzin"]["top"][0]["query"] == "benzin ár"
    assert out["frissitve"] == most.isoformat()


def test_gyujt_soft_fail_kihagy(tmp_path):
    _nap(tmp_path, "2026-10-07", [("benzin", 90)])
    tr = _FakeTr({"benzin": RuntimeError("kvóta")})
    out = kp.gyujt(str(tmp_path), _FakeKliens(tr), _Cfg(), datetime(2026, 10, 7, 21, tzinfo=timezone.utc))
    assert out["kifejezesek"] == []     # soft-fail → nincs bejegyzés, de nem dob


def test_kapcsolodo_ir(tmp_path):
    p = kp.kapcsolodo_ir(str(tmp_path), {"frissitve": "x", "kifejezesek": []})
    assert Path(p).exists() and json.loads(Path(p).read_text(encoding="utf-8"))["frissitve"] == "x"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_kapcsolodo.py -q -k "related_egy or gyujt or kapcsolodo_ir"`
Expected: FAIL (`AttributeError`).

- [ ] **Step 3: Write minimal implementation** (a `kapcsolodo.py` végére)

```python
def related_egy(kliens, kif, config, timeframe=TIMEFRAME):
    """Egy kifejezés related_queries-e a Kliens throttle-jén, KÖTELEZŐ referer-headerrel.
    SOFT-FAIL: kvóta/429/parszolási hiba → None (kihagyva + FIGYELEM), a job NEM dől el."""
    try:
        r = kliens.hivas(AG, kliens.tr.related_queries, kif,
                         geo=config.geo, timeframe=timeframe, headers=REFERER)
    except Exception as e:   # noqa: BLE001 — soft-fail: szigorú related-kvóta/429/egyéb
        _log.warning("FIGYELEM: a kapcsolódó keresések kimaradtak (%s): %s", kif, e)
        return None
    return _parse_related(r)


def _betolt(docs_data):
    try:
        return json.loads((Path(docs_data) / "kapcsolodo.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def gyujt(docs_data, kliens, config, most, cap=CAP, timeframe=TIMEFRAME,
          staleness_nap=STALENESS_NAP, retencio=RETENCIO):
    """A felkapott jelöltekre (jeloltek) related_queries-t gyűjt (soft-fail per szó), bemergeli a
    meglévő kapcsolodo.json-ba (lekerdezve=most), lekerdezve szerint rendez + retencio-ra vág."""
    adat = _betolt(docs_data)
    bejegyzesek = {k["kifejezes"]: k for k in (adat.get("kifejezesek") or [])}
    meglevo_lek = {k: v.get("lekerdezve") for k, v in bejegyzesek.items()}
    for kif, vol in jeloltek(docs_data, meglevo_lek, most, cap, staleness_nap):
        res = related_egy(kliens, kif, config, timeframe)
        if res is None:
            continue
        bejegyzesek[kif] = {"kifejezes": kif, "lekerdezve": most.isoformat(),
                            "volumen": vol, "top": res["top"], "rising": res["rising"]}
    lista = sorted(bejegyzesek.values(), key=lambda k: k.get("lekerdezve") or "", reverse=True)[:retencio]
    return {"frissitve": most.isoformat(), "kifejezesek": lista}


def kapcsolodo_ir(docs_data, adat):
    return json_export._ir_json(Path(docs_data) / "kapcsolodo.json", adat)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_kapcsolodo.py -q`
Expected: PASS (11 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/kapcsolodo.py tests/test_kapcsolodo.py
git commit -m "feat(kapcsolodo): related_egy (soft-fail, referer) + gyujt (merge+retencio) + kapcsolodo_ir"
```

---

### Task 3: `kapcsolodo_orzo.py` — napi egyszer-őr

**Files:**
- Create: `trendfigyelo/kapcsolodo_orzo.py`
- Test: `tests/test_kapcsolodo_orzo.py`

**Interfaces:**
- Consumes: `seged.esti_nap`, `seged.most_utc`; a `kapcsolodo.json` `frissitve` mezője.
- Produces: `kell(docs_data, most) -> str` (a logikai nap, ha ma még nem futott; különben ""), `main(argv)`.

Minta: `trendfigyelo/bovites_orzo.py` (napi idempotencia a `frissitve` LOGIKAI napján).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kapcsolodo_orzo.py
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from trendfigyelo import kapcsolodo_orzo as ko


def _bp(y, m, d, h):
    return datetime(y, m, d, h, tzinfo=ZoneInfo("Europe/Budapest")).astimezone(timezone.utc)


def test_kell_ha_meg_nincs(tmp_path):
    assert ko.kell(str(tmp_path), _bp(2026, 10, 7, 21)) == "2026-10-07"


def test_skip_ha_ma_mar(tmp_path):
    (tmp_path / "kapcsolodo.json").write_text(json.dumps({"frissitve": "2026-10-07T21:30:00+00:00"}), encoding="utf-8")
    assert ko.kell(str(tmp_path), _bp(2026, 10, 7, 22)) == ""


def test_korabbi_ujra(tmp_path):
    (tmp_path / "kapcsolodo.json").write_text(json.dumps({"frissitve": "2026-10-06T21:30:00+00:00"}), encoding="utf-8")
    assert ko.kell(str(tmp_path), _bp(2026, 10, 7, 21)) == "2026-10-07"


def test_hajnali_elozo_nap(tmp_path):
    assert ko.kell(str(tmp_path), _bp(2026, 10, 8, 2)) == "2026-10-07"


def test_main_cli(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(ko.seged, "most_utc", lambda: _bp(2026, 10, 7, 21))
    assert ko.main([str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == "2026-10-07"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_kapcsolodo_orzo.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

```python
# trendfigyelo/kapcsolodo_orzo.py
"""A kapcsolódó-keresések NAPI egyszer-őre (a bovites_orzo mintája): a kapcsolodo.yml a 'Napi
trendgyűjtés' után fut, a backupok többször indíthatnak. Egyszer/logikai nap (seged.esti_nap),
hogy a szigorú related-kvótát ne égessük el újrafutáskor. Kimenet: a logikai nap vagy üres sor."""
import json
import sys
from datetime import datetime
from pathlib import Path

from . import seged


def _frissitve_logikai(docs_data):
    try:
        art = json.loads((Path(docs_data) / "kapcsolodo.json").read_text(encoding="utf-8"))
        k = art.get("frissitve") if isinstance(art, dict) else None
        return seged.esti_nap(datetime.fromisoformat(k)) if isinstance(k, str) else None
    except (OSError, ValueError, TypeError):
        return None


def kell(docs_data, most):
    """A logikai nap (futni kell), vagy "" ha ma (a logikai napon) már frissült."""
    logikai = seged.esti_nap(most)
    return "" if _frissitve_logikai(docs_data) == logikai else logikai


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    docs_data = argv[0] if argv else "docs/data"
    print(kell(docs_data, seged.most_utc()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_kapcsolodo_orzo.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/kapcsolodo_orzo.py tests/test_kapcsolodo_orzo.py
git commit -m "feat(kapcsolodo): kapcsolodo_orzo.py - napi egyszer-or (logikai nap)"
```

---

### Task 4: `kapcsolodo.py` belépő (repo gyökér)

**Files:**
- Create: `kapcsolodo.py` (repo gyökér)
- Test: `tests/test_kapcsolodo_belepo.py`

**Interfaces:**
- Consumes: `kapcsolodo.gyujt`/`kapcsolodo_ir`, `config.betolt`, `Kliens` (saját plafon), `seged.most_utc`.
- Produces: `main(argv) -> int` (0 siker; soft-fail).

Minta: `trendfigyelo/masodlagos_only.py` (saját, szűk plafonú Kliens).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kapcsolodo_belepo.py
import kapcsolodo as be


def test_siker_sajat_plafon(monkeypatch):
    hiv = {}
    class _Cfg: max_probak = 4
    monkeypatch.setattr(be, "betolt", lambda: _Cfg())
    monkeypatch.setattr(be, "Kliens", lambda cfg, plafon=None: hiv.setdefault("plafon", plafon) or "KLIENS")
    monkeypatch.setattr(be.kapcsolodo, "gyujt",
                        lambda dd, kl, cfg, most, **kw: hiv.setdefault("gyujt", (dd, kl)) or {"frissitve": "x", "kifejezesek": []})
    monkeypatch.setattr(be.kapcsolodo, "kapcsolodo_ir", lambda dd, adat: hiv.setdefault("ir", adat))
    assert be.main([]) == 0
    assert hiv["plafon"] == be.kapcsolodo.CAP * 4 + 1      # saját, szűk plafon
    assert hiv["gyujt"][1] == "KLIENS" and "ir" in hiv


def test_cap_argumentum(monkeypatch):
    hiv = {}
    class _Cfg: max_probak = 4
    monkeypatch.setattr(be, "betolt", lambda: _Cfg())
    monkeypatch.setattr(be, "Kliens", lambda cfg, plafon=None: hiv.setdefault("plafon", plafon))
    monkeypatch.setattr(be.kapcsolodo, "gyujt", lambda dd, kl, cfg, most, cap=None, **kw: hiv.setdefault("cap", cap) or {"frissitve": "x", "kifejezesek": []})
    monkeypatch.setattr(be.kapcsolodo, "kapcsolodo_ir", lambda dd, adat: None)
    assert be.main(["--cap", "3"]) == 0
    assert hiv["cap"] == 3 and hiv["plafon"] == 3 * 4 + 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_kapcsolodo_belepo.py -q`
Expected: FAIL (`ModuleNotFoundError: kapcsolodo` a gyökérből — figyeld: a modul `trendfigyelo/kapcsolodo.py` is létezik; a gyökér-belépő a `kapcsolodo.py` a repo-gyökérben, amit a pytest a repo-gyökérről `import kapcsolodo`-ként lát. Hogy a kettő ne ütközzön, a belépő a csomag-modult `from trendfigyelo import kapcsolodo`-ként importálja, és a gyökér-fájl NEVE `kapcsolodo.py`, de MÁS tartalom — lásd a megjegyzést a Step 3-ban).

- [ ] **Step 3: Write minimal implementation**

**FONTOS név-ütközés megjegyzés:** a repo-gyökérben lévő `kapcsolodo.py` (belépő) és a `trendfigyelo/kapcsolodo.py` (modul) AZONOS bazális nevűek. A `heti.py`/`havi.py`/`bovites.py` belépők ugyanígy működnek (gyökér-fájl + `trendfigyelo/`-modul), mert a belépő `from trendfigyelo import kapcsolodo`-t importál, és a pytest `rootdir`-ből futva a gyökér-`kapcsolodo.py`-t `import kapcsolodo`-ként, a csomag-modult `trendfigyelo.kapcsolodo`-ként látja — nincs ütközés (külön modul-névtér). A belépő NE `import kapcsolodo`-zzon önmagára.

```python
# kapcsolodo.py  (repo gyökér — a masodlagos_only + heti.py mintája)
"""A kapcsolódó-keresések gyűjtő belépője (a kapcsolodo.yml ezt hívja): saját, SZŰK plafonú Kliens
(kvóta-védelem) → kapcsolodo.gyujt a felkapott jelöltekre → atomi írás. Soft-fail: a related-kvóta
kimerülése nem dob (gyujt soft-fail-el szónként); NEM indít más ágat."""
import argparse

from trendfigyelo import kapcsolodo, seged
from trendfigyelo.config import betolt
from trendfigyelo.kliens import Kliens


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--cap", type=int, default=kapcsolodo.CAP)
    p.add_argument("docs_data", nargs="?", default="docs/data")
    args = p.parse_args(argv)
    config = betolt()
    kliens = Kliens(config, plafon=args.cap * config.max_probak + 1)   # saját, szűk plafon
    adat = kapcsolodo.gyujt(args.docs_data, kliens, config, seged.most_utc(), cap=args.cap)
    kapcsolodo.kapcsolodo_ir(args.docs_data, adat)
    print(f"Kapcsolódó keresések: {len(adat['kifejezesek'])} kifejezés (frissítve {adat['frissitve']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

*(A `betolt`/`Kliens` a belépő névterében — a teszt `be.betolt`/`be.Kliens`-t monkeypatchel; ezért `from ... import betolt` / `from ... import Kliens` a modul tetején.)*

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_kapcsolodo_belepo.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kapcsolodo.py tests/test_kapcsolodo_belepo.py
git commit -m "feat(kapcsolodo): kapcsolodo.py belepo (sajat szuk plafon, soft-fail)"
```

---

### Task 5: `.github/workflows/kapcsolodo.yml`

**Files:**
- Create: `.github/workflows/kapcsolodo.yml`
- Test: `tests/test_kapcsolodo_workflow.py`

**Interfaces:**
- Consumes: `trendfigyelo.kapcsolodo_orzo` (őr, stdlib, pip install előtt), `kapcsolodo.py` (gyűjtés).

Minta: `.github/workflows/bovites.yml`, DE: nincs ANTHROPIC_API_KEY (nincs LLM), a gyűjtés `python kapcsolodo.py`, a commit CSAK `docs/data/kapcsolodo.json`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kapcsolodo_workflow.py
from pathlib import Path
import yaml


def _wf():
    return yaml.safe_load(Path(".github/workflows/kapcsolodo.yml").read_text(encoding="utf-8"))


def test_trigger_a_napi_gyujtesre():
    on = _wf()
    on = on[True] if True in on else on["on"]
    assert on["workflow_run"]["workflows"] == ["Napi trendgyűjtés"]
    assert "workflow_dispatch" in on


def test_or_a_pip_install_elott():
    sz = Path(".github/workflows/kapcsolodo.yml").read_text(encoding="utf-8")
    assert sz.index("trendfigyelo.kapcsolodo_orzo") < sz.index("pip install")
    assert "python kapcsolodo.py" in sz


def test_commit_csak_a_kapcsolodo_json_es_nincs_anthropic():
    sz = Path(".github/workflows/kapcsolodo.yml").read_text(encoding="utf-8")
    assert "git add docs/data/kapcsolodo.json" in sz
    assert "ANTHROPIC_API_KEY" not in sz       # nincs LLM
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_kapcsolodo_workflow.py -q`
Expected: FAIL (fájl nem létezik).

- [ ] **Step 3: Write minimal implementation** (a bovites.yml mintája, ANTHROPIC NÉLKÜL; a komment-csapda miatt a guard feletti kommentben NE legyen „pip install" literál)

```yaml
# .github/workflows/kapcsolodo.yml
name: Kapcsolódó keresések

on:
  workflow_run:
    workflows: ["Napi trendgyűjtés"]   # az esti teljes felkapott után
    types: [completed]
  workflow_dispatch:
    inputs:
      cap:
        description: "Kézi teszt: kifejezés/futás cap (üres = alap 6)"
        required: false
        default: ""

permissions:
  contents: write

concurrency:
  group: kapcsolodo-futtatas
  cancel-in-progress: false

jobs:
  kapcsolodo:
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

      # Az őr a függőség-telepítés ELŐTT: CSAK stdlib (kapcsolodo_orzo/seged).
      - name: "Napi egyszer-őr (fut-e ma; üres = skip)"
        id: guard
        shell: bash
        run: |
          NAP="$(python -m trendfigyelo.kapcsolodo_orzo docs/data)"
          echo "Őr: '$NAP' (üres = ma már futott)"
          echo "nap=$NAP" >> "$GITHUB_OUTPUT"

      - name: Függőségek telepítése (csak futáskor)
        if: steps.guard.outputs.nap != ''
        run: pip install -r requirements.txt

      - name: Kapcsolódó keresések gyűjtése
        if: steps.guard.outputs.nap != ''
        shell: bash
        env:
          CAP_INPUT: ${{ github.event.inputs.cap }}
        run: |
          set -o pipefail
          if [ -n "$CAP_INPUT" ]; then CAPARG="--cap $CAP_INPUT"; else CAPARG=""; fi
          python kapcsolodo.py $CAPARG 2>&1 | tee kapcsolodo.log

      - name: Változások commitolása (CSAK a kapcsolodo.json, KÜLÖN commit)
        if: always() && github.ref == 'refs/heads/main' && steps.guard.outputs.nap != ''
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git pull --rebase --autostash || true
          git add docs/data/kapcsolodo.json
          if git diff --staged --quiet; then
            echo "Nincs kapcsolódó-keresés változás — nincs commit."
          else
            git commit -m "adat: kapcsolódó keresések ($(date -u +%Y-%m-%dT%H:%MZ))"
            git push
          fi

      - name: Artefakt (log + kapcsolodo.json — mindig)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: kapcsolodo-${{ github.run_id }}
          retention-days: 14
          path: |
            kapcsolodo.log
            docs/data/kapcsolodo.json
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_kapcsolodo_workflow.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/kapcsolodo.yml tests/test_kapcsolodo_workflow.py
git commit -m "feat(kapcsolodo): kapcsolodo.yml workflow (Napi gyujtesre, or a pip install elott, csak kapcsolodo.json)"
```

---

### Task 6: `bovites.js` — „Kapcsolódó keresések" szekció + `bovites.html` + CSS + e2e

**Files:**
- Modify: `docs/bovites.html` (új `#bovites-kapcsolodo` szekció)
- Modify: `docs/js/bovites.js` (betöltés + render)
- Modify: `docs/css/app.css` (`.bovites-kapcs-*`)
- Modify: `e2e/bovites.spec.js`

**Interfaces:**
- Consumes: `data/kapcsolodo.json` (`{frissitve, kifejezesek:[{kifejezes, lekerdezve, volumen, top:[{query,value}], rising:[{query,value}]}]}`).
- Produces: a `#bovites-kapcsolodo` szekció renderelése (fail-soft).

- [ ] **Step 1: Write the failing test** (`e2e/bovites.spec.js` — hozzáadás; a meglévő mock-mintát követve)

```javascript
// e2e/bovites.spec.js  (hozzáadás)
const KAPCS = { frissitve: "2026-10-07T21:00:00+00:00", kifejezesek: [
  { kifejezes: "benzin", lekerdezve: "2026-10-07T21:00:00+00:00", volumen: 90,
    top: [{ query: "benzin ár", value: 100 }, { query: "mol benzin", value: 19 }],
    rising: [{ query: "benzin ársapka", value: 8350 }, { query: "hatósági áras benzin", value: "Breakout" }] }]};

test("bővítés: kapcsolódó keresések szekció (top + rising) renderel", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ json: ELM }));
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ json: UGY }));
  await page.route("**/data/kapcsolodo.json", (r) => r.fulfill({ json: KAPCS }));
  await page.goto("/bovites.html");
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("benzin");
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("benzin ár");         // top
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("benzin ársapka");     // rising
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("Breakout");
});

test("bővítés: kapcsolódó keresések fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ json: ELM }));
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ json: UGY }));
  await page.route("**/data/kapcsolodo.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/bovites.html");
  await expect(page.locator("#bovites")).toContainText("Üzemanyagárak");   // a többi blokk változatlan
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test e2e/bovites.spec.js -g "kapcsolódó"`
Expected: FAIL (nincs szekció).

- [ ] **Step 3: Write minimal implementation**

`docs/bovites.html`: a `#bovites-ugyek` UTÁN:
```html
    <section id="bovites-kapcsolodo" aria-label="Kapcsolódó keresések" aria-live="polite"></section>
```

`docs/js/bovites.js`: READ a meglévő fájlt és illeszd a mintájához. Töltsd be a `data/kapcsolodo.json`-t (a meglévő `bov_json`/fetch-mintával, fail-soft: hiányzik → a szekció üres/kihagyva, a többi blokk változatlan). Egy új render-függvény a `#bovites-kapcsolodo`-ba: kifejezésenként (a `kifejezesek` sorrendjében, legfrissebb elöl) egy kártya: a felkapott kifejezés (cím) + két lista: **Top** (`query` chipek, a `value` halványan) és **Felfutó** (`rising`, a „Breakout"/nagy % jelölve). XSS-mentes (textContent/createElement). Üres `kifejezesek` → „Még nincs kapcsolódó keresés." A render a meglévő `bov_rajzol`/init láncba illesztve (a szűrők — Task 13 — a kapcsolódó szekciót NEM szűrik, az a felkapottakról szól, nem szakpolitikáról).

`docs/css/app.css`: `.bovites-kapcs-*` (kártya, top/rising lista, chip — a `.bovites-*` mintájára).

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test e2e/bovites.spec.js e2e/menu.spec.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/bovites.html docs/js/bovites.js docs/css/app.css e2e/bovites.spec.js
git commit -m "feat(kapcsolodo): Kapcsolodo keresesek szekcio a Bovites fulon (top+rising) + e2e"
```

---

### Task 7: Infó-oldal doboz + `menu.spec.js` szám

**Files:**
- Modify: `docs/adatokrol.html` (4. doboz a „A Bővítés fül" csoportba)
- Modify: `e2e/menu.spec.js` (Infó-teszt doboz-szám)

**Interfaces:**
- Produces: egy új `.adat-doboz` a kapcsolódó keresésekről a meglévő „A Bővítés fül" csoportban.

- [ ] **Step 1: Write the failing test** (`e2e/menu.spec.js` Infó-teszt)

```javascript
// az "Infó oldal" tesztben a doboz-szám: 31 → 32 (a csoport-szám marad 6)
await expect(page.locator("#adatokrol .adat-doboz")).toHaveCount(32);
await expect(page.locator("#adatokrol")).toContainText("kapcsolódó keresés");
```

(Az implementer ELLENŐRIZZE a `docs/adatokrol.html` AKTUÁLIS doboz-számát a teszt írásakor — jelenleg 31; a +1 ebből indul. A csoport-szám 6 marad — ugyanabba a „A Bővítés fül" csoportba kerül.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx playwright test e2e/menu.spec.js -g "Infó"`
Expected: FAIL (31≠32).

- [ ] **Step 3: Write minimal implementation**

A `docs/adatokrol.html` „A Bővítés fül" csoportjába (a meglévő 3 doboz MELLÉ, a csoporton belül) egy 4. `section.adat-doboz` a meglévő markup-mintát követve:
- **Kapcsolódó keresések:** a napi felkapott témák mögé nézünk be — a Google Trends „kapcsolódó keresések" (related queries) alapján témánként a **megszokott** (top) és a **most felfutó** (rising) keresések. Naponta pár felkapott téma frissül (új adatgyűjtés). „Mire kíváncsiak egy témán belül az emberek?"

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test e2e/menu.spec.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/adatokrol.html e2e/menu.spec.js
git commit -m "feat(kapcsolodo): Info-oldal doboz a kapcsolodo keresesekrol"
```

---

## Self-Review

**Spec coverage:** gyűjtés (jeloltek/parse/related_egy/gyujt) → Task 1-2; napi őr → Task 3; belépő (saját plafon) → Task 4; workflow → Task 5; frontend szekció → Task 6; Infó → Task 7. ✓

**Placeholder scan:** a backend-taskok (1-5) teljes kóddal; a frontend (6) a meglévő `bovites.js`-t olvasva implementálandó (teljes verbatim a meglévő fájl kontextusa nélkül találgatás lenne) — konkrét adatalak + e2e + render-leírás adott. ✓

**Type consistency:** `kapcsolodo.json` mezői (Task 2 `gyujt` kimenet: `frissitve`, `kifejezesek[].{kifejezes,lekerdezve,volumen,top,rising}`, `top/rising[].{query,value}`) ↔ Task 6 render. `jeloltek` → `(kif,vol)` ↔ `gyujt`. `related_egy` None → `gyujt` skip. ✓

**Ordering ruling:** Task 1 (jeloltek/parse) ELŐBB mint Task 2 (gyujt használja). Task 2 előbb mint Task 4 (belépő gyujt-ot hív). Task 3/5 független. Task 6 a meglévő Bővítés-frontendre épül (F1-3 már ÉL a main-en). — A pre-flight megerősíti.

**Név-ütközés (tanulság):** a tervezett ÚJ nevek ELŐRE ütközés-ellenőrizve (spec-fázis) — mind tiszta. A gyökér-`kapcsolodo.py` (belépő) és a `trendfigyelo/kapcsolodo.py` (modul) azonos bazális nevűek, DE külön modul-névtér (mint heti.py/havi.py/bovites.py) — a belépő `from trendfigyelo import kapcsolodo`-t importál, nem önmagát. A Task 4 ezt explicit kezeli.

**Kvóta/soft-fail:** a related-kvóta a fő gyűjtést NEM érinti (külön job, külön Kliens/plafon); minden related-hiba soft-fail (None/skip). A referer-header FIX. ✓
