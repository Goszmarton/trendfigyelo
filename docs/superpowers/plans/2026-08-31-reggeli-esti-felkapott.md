# Reggeli és esti felkapott-gyűjtés — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Napi KÉT felkapott-pillanatkép — reggeli (9:00 Budapest, csak felkapott keresések) és esti (21:00, felkapott + kulcsszó) — gyűjtése és megjelenítése három frontend-felületen.

**Architecture:** A meglévő `futtat()` pipeline egy `mode` kapcsolót kap (`reggel`/`este`); reggeli módban kihagyja a kulcsszó-ágakat és megőrzi a kulcsszó-adatot. A per-nap felkapott fájl (`napok/<dátum>.json`) szegmentálódik `{nap, reggel, este}` alakra, visszafelé kompatibilisen (régi `{nap, trendek}` = esti). A frontend a szegmensekből rajzol: #1 két blokk egymás alatt, #2 Reggel/Este váltó, #3 heti elválasztó. A szerver-cron helyi Budapest-időben indít.

**Tech Stack:** Python 3.12 (gyűjtő, pytest), vanília JS + Chart.js (frontend, Playwright e2e), GitHub Actions (YAML), bash (szerver-trigger).

**Spec:** `docs/superpowers/specs/2026-08-31-reggeli-esti-felkapott-design.md`

## Global Constraints

- **Determinisztikus frontend:** böngésző-kódban TILOS `new Date()` / `Date.now()` (nem-determinisztikus); `new Date(Date.UTC(explicit args))` OK.
- **git add NÉV SZERINT** — soha `-A`/`.`; a gyökér `ATADAS-2026-08-18.txt` SOHA nem stagelt.
- **Commit-trailerek** minden commiten:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN`
- **Push KÜLÖN, kapuzott kör** (fetch → divergencia-ellenőrzés → rebase ha kell → push → rev-list 0 0), külön user-jóváhagyással. A terv NEM pushol.
- **SOROS suite:** `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`. TDD valódi RED→GREEN, MUTÁCIÓ=1.
- **Visszafelé kompatibilitás:** a régi `napok/<dátum>.json` `{nap, trendek}` fájlokat NEM írjuk át; minden olvasó normalizálón megy át (régi = esti szegmens).
- **Pótolhatatlan Google-adat** (`kulcsszo_nyers.json`, `kulcsszo_lanc.json`) CSAK-OLVASHATÓ — ezekhez a terv nem nyúl.
- **Szegmens-kulcsok (kanonikus):** `"reggel"`, `"este"`. Címkék a felületen: „Reggeli · 9:00", „Esti · 21:00".

---

## FÁZIS 1 — Backend adatmodell és gyűjtés

### Task 1: Szegmentált `napi_ir` + szegmens-normalizáló

**Files:**
- Modify: `trendfigyelo/json_export.py:136-148` (`napi_ir`) + új `_nap_szegmensek` helper
- Test: `tests/test_json_export.py`

**Interfaces:**
- Produces: `json_export._nap_szegmensek(adat: dict) -> dict` — `{'reggel': {'trendek':[...], 'frissitve': str|None}, 'este': {...}}`, csak a jelenlévő szegmensekkel; régi `{nap, trendek}` → `{'este': {'trendek': ..., 'frissitve': adat.get('frissitve')}}`.
- Produces: `json_export.napi_ir(docs_data, nap_iso, top_trendek, szegmens='este', frissitve_iso=None) -> Path` — a megadott szegmenst írja/frissíti, a MÁSIKAT megőrzi; az index-upsert változatlan.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_json_export.py`:

```python
def test_nap_szegmensek_regi_alak_este_lesz():
    regi = {"nap": "2026-08-10", "trendek": [{"kifejezes": "a"}], "frissitve": "2026-08-10T19:00:00+00:00"}
    szeg = json_export._nap_szegmensek(regi)
    assert set(szeg) == {"este"}
    assert szeg["este"]["trendek"] == [{"kifejezes": "a"}]
    assert szeg["este"]["frissitve"] == "2026-08-10T19:00:00+00:00"


def test_nap_szegmensek_uj_alak_atmegy():
    uj = {"nap": "2026-08-10",
          "reggel": {"trendek": [{"kifejezes": "r"}], "frissitve": "2026-08-10T07:00:00+00:00"},
          "este": {"trendek": [{"kifejezes": "e"}], "frissitve": "2026-08-10T19:00:00+00:00"}}
    szeg = json_export._nap_szegmensek(uj)
    assert set(szeg) == {"reggel", "este"}
    assert szeg["reggel"]["trendek"] == [{"kifejezes": "r"}]


def test_napi_ir_reggel_majd_este_megorzi_a_reggelit(tmp_path):
    d = tmp_path
    json_export.napi_ir(d, "2026-08-10", [{"kifejezes": "r"}], szegmens="reggel",
                        frissitve_iso="2026-08-10T07:00:00+00:00")
    json_export.napi_ir(d, "2026-08-10", [{"kifejezes": "e"}], szegmens="este",
                        frissitve_iso="2026-08-10T19:00:00+00:00")
    adat = json.loads((d / "napok" / "2026-08-10.json").read_text(encoding="utf-8"))
    assert adat["nap"] == "2026-08-10"
    assert adat["reggel"]["trendek"] == [{"kifejezes": "r"}]      # a reggeli MEGMARADT
    assert adat["este"]["trendek"] == [{"kifejezes": "e"}]
    assert adat["reggel"]["frissitve"] == "2026-08-10T07:00:00+00:00"
    idx = json.loads((d / "napok" / "index.json").read_text(encoding="utf-8"))
    assert idx["napok"] == ["2026-08-10"]


def test_napi_ir_alap_szegmens_este(tmp_path):
    json_export.napi_ir(tmp_path, "2026-08-10", [{"kifejezes": "x"}])   # alap szegmens = este
    adat = json.loads((tmp_path / "napok" / "2026-08-10.json").read_text(encoding="utf-8"))
    assert "este" in adat and "reggel" not in adat
    assert adat["este"]["trendek"] == [{"kifejezes": "x"}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_json_export.py -k "szegmens or napi_ir_reggel or napi_ir_alap" -q`
Expected: FAIL (`_nap_szegmensek` nem létezik; `napi_ir` nem fogad `szegmens` kwargot).

- [ ] **Step 3: Implement**

In `trendfigyelo/json_export.py`, add before `napi_ir` (near line 136):

```python
def _nap_szegmensek(adat) -> dict:
    """Meglévő napfájl dict → {szegmens: {trendek, frissitve}} normalizált alak.

    Csak a jelenlévő (reggel/este) szegmenseket adja vissza. A régi {nap, trendek}
    alakot 'este' szegmensként értelmezi (a nap beállt képe). Hibás/hiányos input → {}.
    """
    if not isinstance(adat, dict):
        return {}
    szeg = {}
    for s in ("reggel", "este"):
        v = adat.get(s)
        if isinstance(v, dict) and isinstance(v.get("trendek"), list):
            szeg[s] = {"trendek": v["trendek"], "frissitve": v.get("frissitve")}
    if not szeg and isinstance(adat.get("trendek"), list):
        szeg["este"] = {"trendek": adat["trendek"], "frissitve": adat.get("frissitve")}
    return szeg
```

Replace `napi_ir` (lines 136-148) with:

```python
def napi_ir(docs_data, nap_iso, top_trendek, szegmens="este", frissitve_iso=None) -> Path:
    napok_mappa = Path(docs_data) / "napok"
    fajl = napok_mappa / f"{nap_iso}.json"
    meglevo = {}
    if fajl.exists():
        try:
            meglevo = json.loads(fajl.read_text(encoding="utf-8"))
        except ValueError:
            meglevo = {}
    szeg = _nap_szegmensek(meglevo)
    szeg[szegmens] = {"trendek": top_trendek, "frissitve": frissitve_iso}
    ki = {"nap": nap_iso}
    for s in ("reggel", "este"):
        if s in szeg:
            ki[s] = szeg[s]
    _ir_json(fajl, ki)

    index_fajl = napok_mappa / "index.json"
    if index_fajl.exists():
        index = json.loads(index_fajl.read_text(encoding="utf-8"))
    else:
        index = {"napok": []}
    napok = sorted(set(index.get("napok", [])) | {nap_iso})
    _ir_json(index_fajl, {"napok": napok})
    return fajl
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_json_export.py -q`
Expected: PASS (az összes, a meglévők is).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/json_export.py tests/test_json_export.py
git commit -m "$(cat <<'EOF'
feat(felkapott): szegmentált napi_ir (reggel/este) + normalizáló

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 2: Szegmensenkénti `kategoriak_ir` + régi-nap normalizálás

**Files:**
- Modify: `trendfigyelo/kategoriak.py:50-70` (`kategoriak_ir`)
- Test: `tests/test_kategoriak.py`

**Interfaces:**
- Consumes: `json_export._nap_szegmensek` (Task 1), `kategoriak.kategoria_aggregatum(nap_iso, trendek)` (változatlan).
- Produces: `kategoriak.json` új alak: `{"napok": [{"nap": ISO, "reggel"?: <aggregátum>, "este"?: <aggregátum>}]}`. Régi `{nap, trendek}` fájl → csak `este`. Egy nap csak akkor kerül be, ha van legalább egy nem-None szegmens-aggregátum.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_kategoriak.py`:

```python
def _ir_nap(tmp_path, nap_iso, obj):
    napok = tmp_path / "napok"
    napok.mkdir(exist_ok=True)
    (napok / f"{nap_iso}.json").write_text(json.dumps(obj), encoding="utf-8")
    idx = napok / "index.json"
    lista = json.loads(idx.read_text()) if idx.exists() else {"napok": []}
    idx.write_text(json.dumps({"napok": sorted(set(lista["napok"]) | {nap_iso})}), encoding="utf-8")


def test_kategoriak_ir_szegmentalt_nap(tmp_path):
    _ir_nap(tmp_path, "2026-08-10", {
        "nap": "2026-08-10",
        "reggel": {"trendek": [{"kifejezes": "a", "temak": ["Sports"]}], "frissitve": "x"},
        "este": {"trendek": [{"kifejezes": "b", "temak": ["Health"]},
                             {"kifejezes": "c", "temak": ["Sports"]}], "frissitve": "y"},
    })
    kategoriak.kategoriak_ir(tmp_path)
    kj = json.loads((tmp_path / "kategoriak.json").read_text(encoding="utf-8"))
    nap = kj["napok"][0]
    assert nap["nap"] == "2026-08-10"
    assert nap["reggel"]["kategoriak"] == {"Sports": 1}
    assert nap["este"]["kategoriak"] == {"Health": 1, "Sports": 1}


def test_kategoriak_ir_regi_nap_csak_este(tmp_path):
    _ir_nap(tmp_path, "2026-08-09", {"nap": "2026-08-09",
                                     "trendek": [{"kifejezes": "a", "temak": ["Politics"]}]})
    kategoriak.kategoriak_ir(tmp_path)
    kj = json.loads((tmp_path / "kategoriak.json").read_text(encoding="utf-8"))
    nap = kj["napok"][0]
    assert "reggel" not in nap
    assert nap["este"]["kategoriak"] == {"Politics": 1}


def test_kategoriak_ir_3a_elotti_nap_kihagyva(tmp_path):
    # egyik szegmensben sincs 'temak' kulcs → a nap nem reprezentálódik
    _ir_nap(tmp_path, "2026-08-08", {"nap": "2026-08-08",
                                     "este": {"trendek": [{"kifejezes": "a"}], "frissitve": "z"}})
    kategoriak.kategoriak_ir(tmp_path)
    kj = json.loads((tmp_path / "kategoriak.json").read_text(encoding="utf-8"))
    assert kj["napok"] == []
```

Also UPDATE any existing `kategoriak_ir` test in this file that asserts the OLD flat shape (`nap["kategoriak"]` directly on the day record): change it to read `nap["este"]["kategoriak"]`. Search the file for `kategoriak_ir` usages and reconcile.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_kategoriak.py -k "szegmentalt or regi_nap or 3a_elotti" -q`
Expected: FAIL (a régi `kategoriak_ir` a `nap.get("trendek", [])`-ből számol, nincs szegmens).

- [ ] **Step 3: Implement**

Replace `kategoriak_ir` in `trendfigyelo/kategoriak.py` (lines 50-70) with:

```python
def kategoriak_ir(docs_data) -> Path:
    """A napok/*.json determinisztikus, SZEGMENTÁLT tükre → kategoriak.json.

    Minden naphoz szegmensenként (reggel/este) kategoria_aggregatum-ot számol a
    json_export._nap_szegmensek normalizálásából. A None (3a előtti) szegmenst
    kihagyja; a régi {nap, trendek} fájl 'este'-ként számít. Egy nap csak akkor
    kerül be, ha van legalább egy nem-None szegmens-aggregátum. Idempotens.
    """
    napok_mappa = Path(docs_data) / "napok"
    index_fajl = napok_mappa / "index.json"
    napok_index = (json.loads(index_fajl.read_text(encoding="utf-8")).get("napok", [])
                   if index_fajl.exists() else [])
    rekordok = []
    for nap_iso in sorted(napok_index):
        nap_fajl = napok_mappa / f"{nap_iso}.json"
        if not nap_fajl.exists():
            continue
        nap = json.loads(nap_fajl.read_text(encoding="utf-8"))
        szeg = json_export._nap_szegmensek(nap)
        rek = {"nap": nap_iso}
        van = False
        for s in ("reggel", "este"):
            if s in szeg:
                agg = kategoria_aggregatum(nap_iso, szeg[s]["trendek"])
                if agg is not None:
                    rek[s] = agg
                    van = True
        if van:
            rekordok.append(rek)
    return json_export._ir_json(Path(docs_data) / "kategoriak.json", {"napok": rekordok})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_kategoriak.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/kategoriak.py tests/test_kategoriak.py
git commit -m "$(cat <<'EOF'
feat(felkapott): szegmensenkénti kategoriak.json (reggel/este) tükör

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 3: `legfrissebb_ir` kulcsszó-megőrzés (reggeli mód)

**Files:**
- Modify: `trendfigyelo/json_export.py:81-94` (`legfrissebb_ir`)
- Test: `tests/test_json_export.py`

**Interfaces:**
- Produces: `legfrissebb_ir(docs_data, top_trendek, trend_idosorok, kulcsszo_pontok, frissitve_iso, geo, valtas_datum=None, kulcsszo_megorzes=None) -> Path`. Ha `kulcsszo_megorzes` egy dict (`{"kulcsszavak": ..., "kulcsszo_osszesites": ...}`), a `kulcsszavak`/`kulcsszo_osszesites` mezők ONNAN jönnek (nem a `kulcsszo_pontok`-ból) — a reggeli mód így nem üríti a kulcsszó-diagramot.
- Produces: `json_export.legfrissebb_kulcsszo_megorzes(docs_data) -> dict` — a meglévő `legfrissebb.json`-ból kiolvassa a `kulcsszavak` + `kulcsszo_osszesites` mezőket; hiányzó fájl/mező → `{"kulcsszavak": {}, "kulcsszo_osszesites": []}`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_json_export.py`:

```python
def test_legfrissebb_kulcsszo_megorzes_olvas(tmp_path):
    (tmp_path / "legfrissebb.json").write_text(json.dumps({
        "kulcsszavak": {"hitel": {"pontok": [1]}},
        "kulcsszo_osszesites": [{"kulcsszo": "hitel", "atlag": 5}],
    }), encoding="utf-8")
    m = json_export.legfrissebb_kulcsszo_megorzes(tmp_path)
    assert m["kulcsszavak"] == {"hitel": {"pontok": [1]}}
    assert m["kulcsszo_osszesites"] == [{"kulcsszo": "hitel", "atlag": 5}]


def test_legfrissebb_kulcsszo_megorzes_hianyzo_fajl(tmp_path):
    m = json_export.legfrissebb_kulcsszo_megorzes(tmp_path)
    assert m == {"kulcsszavak": {}, "kulcsszo_osszesites": []}


def test_legfrissebb_ir_megorzi_a_kulcsszot(tmp_path):
    megorzes = {"kulcsszavak": {"hitel": {"pontok": [1]}},
                "kulcsszo_osszesites": [{"kulcsszo": "hitel", "atlag": 5}]}
    json_export.legfrissebb_ir(tmp_path, [{"kifejezes": "r"}], [], [],   # kulcsszo_pontok ÜRES (reggel)
                               "2026-08-10T07:00:00+00:00", "HU", kulcsszo_megorzes=megorzes)
    adat = json.loads((tmp_path / "legfrissebb.json").read_text(encoding="utf-8"))
    assert adat["top_trendek"] == [{"kifejezes": "r"}]
    assert adat["kulcsszavak"] == {"hitel": {"pontok": [1]}}       # NEM ürült ki
    assert adat["kulcsszo_osszesites"] == [{"kulcsszo": "hitel", "atlag": 5}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_json_export.py -k "megorzes or megorzi" -q`
Expected: FAIL (`legfrissebb_kulcsszo_megorzes` nincs; `legfrissebb_ir` nem fogad `kulcsszo_megorzes`-t).

- [ ] **Step 3: Implement**

In `trendfigyelo/json_export.py`, add helper (near `legfrissebb_ir`):

```python
def legfrissebb_kulcsszo_megorzes(docs_data) -> dict:
    """A meglévő legfrissebb.json kulcsszó-részei (reggeli mód megőrzéséhez).

    Hiányzó fájl / hibás JSON / hiányzó mező → üres alap ({} / []).
    """
    fajl = Path(docs_data) / "legfrissebb.json"
    try:
        adat = json.loads(fajl.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"kulcsszavak": {}, "kulcsszo_osszesites": []}
    return {
        "kulcsszavak": adat.get("kulcsszavak", {}) or {},
        "kulcsszo_osszesites": adat.get("kulcsszo_osszesites", []) or [],
    }
```

Replace `legfrissebb_ir` (lines 81-94) with:

```python
def legfrissebb_ir(docs_data, top_trendek, trend_idosorok, kulcsszo_pontok,
                   frissitve_iso, geo, valtas_datum=None, kulcsszo_megorzes=None) -> Path:
    if kulcsszo_megorzes is not None:
        kulcsszavak = kulcsszo_megorzes.get("kulcsszavak", {})
        osszesites = kulcsszo_megorzes.get("kulcsszo_osszesites", [])
    else:
        kulcsszavak = _kulcsszo_idosorok(kulcsszo_pontok)
        osszesites = kulcsszo_napi_osszesites(kulcsszo_pontok)
    adat = {
        "geo": geo,
        "frissitve": frissitve_iso,
        "top_trendek": top_trendek,
        "trend_idosorok": trend_idosorok,
        "kulcsszavak": kulcsszavak,
        "kulcsszo_osszesites": osszesites,
    }
    if valtas_datum is not None:
        adat["modszertan_valtas"] = valtas_datum
    return _ir_json(Path(docs_data) / "legfrissebb.json", adat)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_json_export.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/json_export.py tests/test_json_export.py
git commit -m "$(cat <<'EOF'
feat(felkapott): legfrissebb_ir kulcsszó-megőrzés a reggeli módhoz

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 4: `futtat` mód-kapcsoló (reggeli kihagy-halmaz + szegmens-írás)

**Files:**
- Modify: `trendfigyelo/futtato.py:299-534` (`futtat`) + `main` (579-586)
- Test: `tests/test_futtato.py`

**Interfaces:**
- Consumes: Task 1 `napi_ir(..., szegmens=, frissitve_iso=)`, Task 3 `legfrissebb_ir(..., kulcsszo_megorzes=)` + `legfrissebb_kulcsszo_megorzes`.
- Produces: `futtat(config, kliens, adatok_mappa, docs_data_mappa, most=None, mode="este") -> int`. `mode="reggel"` esetén: NEM fut `kulcsszo`, `kulcsszo_masodlagos`, `tortenet`, `lanc`, `regresszio`, `regresszio_masodlagos`; a `napi_ir` a `reggel` szegmensbe ír; a `legfrissebb_ir` a kulcsszó-részt megőrzi. `mode="este"` (alap) = a mostani teljes viselkedés, a `napi_ir` az `este` szegmensbe ír.
- Produces: `main(argv=None) -> int` — `--mode {reggel,este}` (alap `este`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_futtato.py` (kövesd a fájl meglévő Kliens/config-fixture mintáját; ha van közös helper a `futtat` hívására, azt használd — itt a lényegi assertek):

```python
def test_futtat_reggel_mod_szegmens_es_kihagyas(tmp_path, monkeypatch):
    """Reggeli mód: napi_ir a 'reggel' szegmensbe ír, ÉS a kulcsszó-ág NEM fut."""
    from trendfigyelo import futtato, kulcsszavak
    hivott = {"kulcsszo": False}
    monkeypatch.setattr(kulcsszavak, "gyujt",
                        lambda *a, **k: (hivott.__setitem__("kulcsszo", True) or ([], {}, {})))
    # a felkapott/idosor ágakat a meglévő teszt-fixture/mock adja (üres is elég a szegmens-assserthez);
    # kövesd a fájlban már használt Kliens-stub + config-fixture mintát.
    config = _teszt_config()                     # a fájl meglévő helpere
    kliens = _stub_kliens(config, api_trendek=[_trend("alma", ["Sports"])])   # meglévő helper-minta
    most = seged.most_utc()
    docs = tmp_path / "docs" / "data"
    futtato.futtat(config, kliens, tmp_path / "adatok", docs, most=most, mode="reggel")
    nap_iso = most.astimezone(seged.BUDAPEST).date().isoformat()
    adat = json.loads((docs / "napok" / f"{nap_iso}.json").read_text(encoding="utf-8"))
    assert "reggel" in adat and "este" not in adat
    assert hivott["kulcsszo"] is False           # a kulcsszó-ág KI volt hagyva


def test_futtat_este_mod_szegmens_es_kulcsszo_fut(tmp_path, monkeypatch):
    from trendfigyelo import futtato, kulcsszavak
    hivott = {"kulcsszo": False}
    monkeypatch.setattr(kulcsszavak, "gyujt",
                        lambda *a, **k: (hivott.__setitem__("kulcsszo", True) or ([], {}, {})))
    config = _teszt_config()
    kliens = _stub_kliens(config, api_trendek=[_trend("alma", ["Sports"])])
    most = seged.most_utc()
    docs = tmp_path / "docs" / "data"
    futtato.futtat(config, kliens, tmp_path / "adatok", docs, most=most, mode="este")
    nap_iso = most.astimezone(seged.BUDAPEST).date().isoformat()
    adat = json.loads((docs / "napok" / f"{nap_iso}.json").read_text(encoding="utf-8"))
    assert "este" in adat
    assert hivott["kulcsszo"] is True            # este módban FUT a kulcsszó-ág


def test_main_mode_argparse_alap_este():
    from trendfigyelo import futtato
    assert futtato._mode_parse([]) == "este"
    assert futtato._mode_parse(["--mode", "reggel"]) == "reggel"
    assert futtato._mode_parse(["--mode", "este"]) == "este"
```

> Megjegyzés az implementálónak: a `_teszt_config`/`_stub_kliens`/`_trend` a `tests/test_futtato.py`-ban már létező (vagy a fájl mintája szerint felépítendő) segédek — a lényeg a két assert: (a) a `reggel`/`este` szegmens a napfájlban, (b) a `kulcsszavak.gyujt` hívott-e. Ha a fájl más stub-mintát használ, illeszd ahhoz; NE vezess be új globális mockolási stílust.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_futtato.py -k "reggel_mod or este_mod or mode_argparse" -q`
Expected: FAIL (`futtat` nem fogad `mode`-ot; `_mode_parse` nincs).

- [ ] **Step 3: Implement**

In `trendfigyelo/futtato.py`:

(a) `futtat` szignatúra (line 299): `def futtat(config, kliens, adatok_mappa, docs_data_mappa, most=None, mode="este") -> int:` és rögtön a docstring után:

```python
    csak_felkapott = (mode == "reggel")
```

(b) A kulcsszó-ág (328-330) gate-elése:

```python
        if csak_felkapott:
            kulcsszo_pontok, kulcsszo_napi_pontok, kulcsszo_nyers = [], {}, {}
        else:
            kulcsszo_eredmeny = _ag(bejegyzesek, kliens, "kulcsszo",
                                lambda: kulcsszavak.gyujt(kliens, config, most))
            kulcsszo_pontok, kulcsszo_napi_pontok, kulcsszo_nyers = kulcsszo_eredmeny or ([], {}, {})
```

(c) A másodlagos ág (339) gate-elése:

```python
        if not csak_felkapott:
            _masodlagos_ag(bejegyzesek, kliens, config, docs_data_mappa, most)
```

(d) A `legfrissebb_ir` hívás (394-396) — reggeli módban kulcsszó-megőrzés:

```python
    else:
        json_export.legfrissebb_ir(docs_data_mappa, top_trendek, trend_idosorok,
                                   kulcsszo_pontok, letoltve, config.geo,
                                   valtas_datum=config.modszertan_valtas,
                                   kulcsszo_megorzes=(json_export.legfrissebb_kulcsszo_megorzes(docs_data_mappa)
                                                      if csak_felkapott else None))
```

(e) A tortenet-blokk (403-405) gate-elése:

```python
    if kulcsszo_napi_pontok and not csak_felkapott:
        json_export.tortenet_frissit_napok(docs_data_mappa, kulcsszo_napi_pontok,
                                           valtas_datum=config.modszertan_valtas)
```

(f) A `napi_ir` hívás (406-407) — szegmens + frissitve:

```python
    if top_trendek:
        json_export.napi_ir(docs_data_mappa, nap_iso, top_trendek,
                            szegmens=("reggel" if csak_felkapott else "este"),
                            frissitve_iso=letoltve)
```

(g) A nyers/lánc-blokk (409-417) gate-elése — a külső `if`-et bővítsd:

```python
    if kulcsszo_nyers and not csak_felkapott:
```

(h) A `regresszio` (437-460) és `regresszio_masodlagos` (466-484) blokkokat reggeli módban ki kell hagyni. A legkevésbé invazív: a két blokk elé egy közös gate. A `regresszio` blokk (line 437 `nyers_fajl = ...` előtt) helyett:

```python
    if csak_felkapott:
        pass   # reggeli mód: a származtatott kulcsszó-regressziók KIMARADNAK (nincs friss kulcsszó-adat)
    else:
        # ---------- regresszió (származtatott nézet, VÉDETTEN) ----------
        <a MEGLÉVŐ regresszió + regresszió_masodlagos blokk BEHÚZVA ide, változatlan törzzsel>
```

> Implementálói megjegyzés: a (h) lépésnél a meglévő két blokkot (437–484) egyetlen `else:` ág alá húzd be (indentálás), a törzsük VÁLTOZATLAN. Ne írd át a logikát, csak feltételes futtatásba tedd.

(i) `main` (579-586) — argparse + `_mode_parse`:

```python
def _mode_parse(argv):
    """A --mode kapcsoló (reggel/este), alap 'este'. Ismeretlen érték → argparse-hiba."""
    import argparse
    p = argparse.ArgumentParser(description="Trendfigyelő napi/reggeli futtatás.")
    p.add_argument("--mode", choices=["reggel", "este"], default="este")
    return p.parse_args(argv).mode


def main(argv=None) -> int:
    """Belépő: config betöltése, Kliens felépítése, teljes futás a --mode szerint."""
    import sys as _sys
    mode = _mode_parse(_sys.argv[1:] if argv is None else argv)
    config = betolt()
    kliens = Kliens(config, plafon=_plafon(config, _plafon_override_env()))
    print(f"Mód: {mode} · Várható Google-hívásszám (429 nélkül): ~{tervezett_hivasszam(config)}")
    return futtat(config, kliens, Path("adatok"), Path("docs") / "data", mode=mode)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_futtato.py -q`
Expected: PASS (a meglévők is — az `este` alap = korábbi viselkedés + szegmens-írás; ha egy meglévő teszt a régi `napok/<nap>.json` `{nap, trendek}` alakot assertálja, frissítsd `este.trendek`-re).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/futtato.py tests/test_futtato.py
git commit -m "$(cat <<'EOF'
feat(felkapott): futtat --mode reggel|este (kihagy-halmaz + szegmens-írás)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 5: Szegmens-tudatos idempotencia-őr

**Files:**
- Modify: `trendfigyelo/futas_orzo.py`
- Test: `tests/test_futas_orzo.py`

**Interfaces:**
- Produces: `futas_orzo.szegmens_mar_gyujtottunk_ma(docs_data, szegmens, ma_bp) -> bool` — a `docs_data/napok/<ma_bp>.json` `<szegmens>.frissitve` dátum-előtagja == `ma_bp`? Hiányzó fájl/mező → False.
- Produces: CLI `python -m trendfigyelo.futas_orzo --szegmens reggel docs/data` → `true`/`false`. A „ma" Budapest-nap (`seged.most_utc().astimezone(seged.BUDAPEST)`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_futas_orzo.py`:

```python
def _ir_nap_szegmens(tmp_path, nap_iso, szegmens, frissitve):
    napok = tmp_path / "napok"; napok.mkdir(parents=True, exist_ok=True)
    (napok / f"{nap_iso}.json").write_text(
        json.dumps({"nap": nap_iso, szegmens: {"trendek": [], "frissitve": frissitve}}),
        encoding="utf-8")


def test_szegmens_mai_reggel_true(tmp_path):
    _ir_nap_szegmens(tmp_path, "2026-08-31", "reggel", "2026-08-31T07:00:00+00:00")
    assert futas_orzo.szegmens_mar_gyujtottunk_ma(tmp_path, "reggel", "2026-08-31") is True


def test_szegmens_masik_szegmens_nem_szamit(tmp_path):
    # csak ESTI van ma → a REGGELI őr False (nem blokkolja a reggelit)
    _ir_nap_szegmens(tmp_path, "2026-08-31", "este", "2026-08-31T19:00:00+00:00")
    assert futas_orzo.szegmens_mar_gyujtottunk_ma(tmp_path, "reggel", "2026-08-31") is False
    assert futas_orzo.szegmens_mar_gyujtottunk_ma(tmp_path, "este", "2026-08-31") is True


def test_szegmens_tegnapi_false(tmp_path):
    _ir_nap_szegmens(tmp_path, "2026-08-30", "reggel", "2026-08-30T07:00:00+00:00")
    assert futas_orzo.szegmens_mar_gyujtottunk_ma(tmp_path, "reggel", "2026-08-31") is False


def test_szegmens_hianyzo_fajl_false(tmp_path):
    assert futas_orzo.szegmens_mar_gyujtottunk_ma(tmp_path, "reggel", "2026-08-31") is False


def test_cli_szegmens(tmp_path, capsys):
    _ir_nap_szegmens(tmp_path, "2026-08-31", "reggel", "2026-08-31T07:00:00+00:00")
    # a „ma"-t a CLI a Budapest-napból számítja; itt a determinizmushoz a szegmens-fn közvetlen tesztje a mérvadó,
    # a CLI-ág füst-szintű: hiányzó fájl → 'false'
    futas_orzo.main(["--szegmens", "reggel", str(tmp_path)])
    assert capsys.readouterr().out.strip() in {"true", "false"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_futas_orzo.py -k "szegmens or cli_szegmens" -q`
Expected: FAIL (`szegmens_mar_gyujtottunk_ma` nincs; a CLI nem ismeri a `--szegmens`-t).

- [ ] **Step 3: Implement**

In `trendfigyelo/futas_orzo.py`:

Add import and helper (a meglévő `from . import seged` NINCS — add hozzá):

```python
from . import seged
```

```python
def _szegmens_datuma(docs_data, szegmens, nap_bp):
    """A napok/<nap_bp>.json <szegmens>.frissitve dátum-előtagja (YYYY-MM-DD), vagy None."""
    fajl = os.path.join(str(docs_data), "napok", f"{nap_bp}.json")
    try:
        with open(fajl, encoding="utf-8") as f:
            adat = json.load(f)
    except (OSError, ValueError):
        return None
    szeg = adat.get(szegmens) if isinstance(adat, dict) else None
    fr = szeg.get("frissitve") if isinstance(szeg, dict) else None
    if not isinstance(fr, str) or len(fr) < 10:
        return None
    return fr[:10]


def szegmens_mar_gyujtottunk_ma(docs_data, szegmens, ma_bp):
    """True, ha a <szegmens>.frissitve dátuma == ma_bp (YYYY-MM-DD).

    Hiányzó/olvashatatlan jel → False (inkább gyűjtsünk, mint tévesen kihagyjunk).
    """
    return _szegmens_datuma(docs_data, szegmens, ma_bp) == ma_bp
```

Add `import os` a fájl tetejére (ha nincs). Extend `main` a `--szegmens` ággal (a `--youtube` mintájára):

```python
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--szegmens" in argv:
        i = argv.index("--szegmens")
        szegmens = argv[i + 1]
        maradek = argv[:i] + argv[i + 2:]
        docs_data = maradek[0] if maradek else "docs/data"
        ma_bp = seged.most_utc().astimezone(seged.BUDAPEST).date().isoformat()
        print("true" if szegmens_mar_gyujtottunk_ma(docs_data, szegmens, ma_bp) else "false")
        return 0
    youtube = "--youtube" in argv
    argv = [a for a in argv if a != "--youtube"]
    ma = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if youtube:
        path = argv[0] if argv else ALAP_YOUTUBE_NYERS
        megvan = youtube_mar_gyujtottunk_ma(path, ma)
    else:
        path = argv[0] if argv else ALAP_LEGFRISSEBB
        megvan = mar_gyujtottunk_ma(path, ma)
    print("true" if megvan else "false")
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_futas_orzo.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/futas_orzo.py tests/test_futas_orzo.py
git commit -m "$(cat <<'EOF'
feat(felkapott): szegmens-tudatos idempotencia-őr (reggel/este)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

## FÁZIS 2 — Workflow-k (CI)

### Task 6: `reggeli.yml` + `napi.yml` mód/őr/ütemezés + trigger-doksi

**Files:**
- Create: `.github/workflows/reggeli.yml`
- Modify: `.github/workflows/napi.yml`
- Modify: `scripts/trigger_workflow.sh:14-16` (cron-doksi Budapest-időre)
- Test: nincs unit-teszt (YAML/config); verifikáció = a Task 5 CLI + `python -c` import-smoke + kézi YAML-szemle.

**Interfaces:**
- Consumes: Task 4 `--mode reggel|este`, Task 5 `--szegmens reggel|este`.

- [ ] **Step 1: `reggeli.yml` létrehozása**

Create `.github/workflows/reggeli.yml`:

```yaml
name: Reggeli felkapott-gyűjtés

on:
  workflow_dispatch:
    inputs:
      plafon_override:
        description: "Hívás-plafon override (CSAK csökkent). Üresen normál."
        required: false
        default: ""
  # ELSŐDLEGES út: szerver-trigger (Hetzner-cron → workflow_dispatch, 9:00 Budapest).
  # A GitHub-cron a BACKUP, a szerver MÖGÉ időzítve; a szegmens-őr (reggel) dedup-olja.
  schedule:
    - cron: "30 8 * * *"    # 08:30 UTC — backup (10:30 nyár / 09:30 tél Budapest)
    - cron: "0 11 * * *"    # 11:00 UTC — késői backup

permissions:
  contents: write

concurrency:
  group: reggeli-futtatas
  cancel-in-progress: false

jobs:
  gyujtes:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Python beállítása
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: "Idempotencia-őr (ütemezett fallback: ma már gyűjtöttünk reggelit?)"
        id: guard
        shell: bash
        run: |
          if [ "${{ github.event_name }}" != "schedule" ]; then
            echo "Kézi (workflow_dispatch) futás — az őr nem aktív, gyűjtünk."
            echo "skip=false" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          skip="$(python -m trendfigyelo.futas_orzo --szegmens reggel docs/data)"
          echo "Ütemezett futás — ma már van reggeli? skip=$skip"
          echo "skip=$skip" >> "$GITHUB_OUTPUT"

      - name: Függőségek telepítése
        if: steps.guard.outputs.skip != 'true'
        run: pip install -r requirements.txt

      - name: Reggeli felkapott-gyűjtés
        if: steps.guard.outputs.skip != 'true'
        shell: bash
        env:
          PLAFON_OVERRIDE: ${{ github.event_name == 'workflow_dispatch' && inputs.plafon_override || '' }}
        run: |
          set -o pipefail
          python top_keresesek.py --mode reggel 2>&1 | tee run.log

      - name: Változások commitolása (csak JSON + napló)
        if: always() && steps.guard.outputs.skip != 'true' && github.ref == 'refs/heads/main'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add docs/data adatok/naplo.csv
          if git diff --staged --quiet; then
            echo "Nincs változás — nincs commit."
          else
            git commit -m "adat: reggeli HU felkapott-gyűjtés ($(date -u +%Y-%m-%dT%H:%MZ))"
            git push
          fi

      - name: Artefakt feltöltése (napló + JSON + stdout)
        if: always() && steps.guard.outputs.skip != 'true'
        uses: actions/upload-artifact@v4
        with:
          name: reggeli-futas-${{ github.run_id }}-${{ github.run_attempt }}
          retention-days: 14
          path: |
            adatok/naplo.csv
            docs/data/**
            run.log
```

- [ ] **Step 2: `napi.yml` módosítása (esti mód + szegmens-őr)**

In `.github/workflows/napi.yml`:
- A `schedule` blokk (17-18) MARAD (`30 20` + `0 23` UTC — ezek már 21:00 Budapest UTÁN vannak; frissítsd a kommentet: „backup a 21:00 Budapest szerver-trigger MÖGÉ").
- Az őr-lépés (51): cseréld
  `skip="$(python -m trendfigyelo.futas_orzo docs/data/legfrissebb.json)"`
  erre:
  `skip="$(python -m trendfigyelo.futas_orzo --szegmens este docs/data)"`
- A „Trendfigyelő futtatása" lépés (68): cseréld
  `python top_keresesek.py 2>&1 | tee run.log`
  erre:
  `python top_keresesek.py --mode este 2>&1 | tee run.log`
- A `name:` (1) maradhat „Napi trendgyűjtés"; a fejléc-komment (10-15) frissítése: a szerver-trigger MOST 21:00 Budapest (nem 19:10 UTC).

- [ ] **Step 3: `trigger_workflow.sh` cron-doksi frissítése**

In `scripts/trigger_workflow.sh`, replace the cron example (14-16) with Budapest-local scheduling (a szerver TZ Europe/Budapest — nincs `CRON_TZ=UTC`, a helyi idő kezeli a nyári/téli váltást):

```bash
# Cron-példa (szerver helyi ideje = Europe/Budapest; NINCS CRON_TZ):
#   0 9  * * *  bash /home/trendfigyelo/trendfigyelo/scripts/trigger_workflow.sh reggeli.yml >> ~/trigger.log 2>&1
#   0 21 * * *  bash /home/trendfigyelo/trendfigyelo/scripts/trigger_workflow.sh napi.yml    >> ~/trigger.log 2>&1
#   0 15 * * *  bash /home/trendfigyelo/trendfigyelo/scripts/trigger_workflow.sh youtube.yml >> ~/trigger.log 2>&1
```

- [ ] **Step 4: Verify (import-smoke + YAML-szemle)**

Run:
```bash
.venv/bin/python -c "from trendfigyelo import futtato, futas_orzo; print(futtato._mode_parse(['--mode','reggel']))"
.venv/bin/python -m trendfigyelo.futas_orzo --szegmens reggel docs/data
python -c "import yaml,sys; [yaml.safe_load(open(f)) for f in ['.github/workflows/reggeli.yml','.github/workflows/napi.yml']]; print('YAML OK')"
```
Expected: `reggel`, egy `true`/`false` sor, `YAML OK`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/reggeli.yml .github/workflows/napi.yml scripts/trigger_workflow.sh
git commit -m "$(cat <<'EOF'
feat(felkapott): reggeli.yml + napi.yml esti mód & szegmens-őr; cron Budapest-idő

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

## FÁZIS 3 — Frontend (3 felület)

### Task 7: #3 Heti blokk — reggel/este elválasztó

**Files:**
- Modify: `docs/js/app.js:1926-1936` (`heti_tabla_render` szó-cellája)
- Modify: `docs/css/app.css:49-53` (heti-tabla stílus)
- Test: `e2e/heti.spec.js`

**Interfaces:**
- Consumes: a `napok/<nap>.json` szegmentált (`{reggel, este}`) VAGY régi (`{trendek}`) alakja.
- Produces: DOM: `td.heti-szavak` cellában szegmentált napnál két `div.heti-szegmens` (`data-szegmens="reggel"`/`"este"`), régi/egy-szegmensű napnál egyetlen szöveg (mint most).

- [ ] **Step 1: Write the failing test**

Add to `e2e/heti.spec.js` (a fájl `mock` mintáját követve; bővítsd a `NAPOK`/`mock`-ot egy szegmentált nappal, vagy adj külön tesztet saját route-tal):

```javascript
test("N. heti: szegmentált nap reggel/este elválasztóval, régi nap egy lista", async ({ page }) => {
  const IDX = { napok: ["2026-08-17"] };
  await page.route(/kategoriak\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: [] }) }));
  await page.route(/legfrissebb\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: [] }) }));
  await page.route(/napok\/index\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify(IDX) }));
  await page.route(/napok\/2026-08-17\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({
    nap: "2026-08-17",
    reggel: { trendek: [{ kifejezes: "reg1" }, { kifejezes: "reg2" }], frissitve: "2026-08-17T07:00:00+00:00" },
    este: { trendek: [{ kifejezes: "est1" }], frissitve: "2026-08-17T19:00:00+00:00" },
  }) }));
  await page.goto("/");
  const sor = page.locator('#heti-blokk .heti-nap-sor[data-nap="2026-08-17"]');
  await expect(sor.locator('.heti-szegmens[data-szegmens="reggel"]')).toContainText("reg1, reg2");
  await expect(sor.locator('.heti-szegmens[data-szegmens="este"]')).toContainText("est1");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test e2e/heti.spec.js --workers=1 -g "szegmentált nap"`
Expected: FAIL (`.heti-szegmens` nem létezik; a cella `napi.trendek`-ből épül, ami a szegmentált napon `undefined`).

- [ ] **Step 3: Implement**

In `docs/js/app.js`, a `heti_tabla_render` szó-cella építése (1931-1934) helyett. Először egy kis helper közvetlenül `heti_tabla_render` FÖLÉ:

```javascript
// egy napfájl → megjelenítendő szegmensek [{szegmens, cimke, szavak}] (heti nézet).
// Szegmentált nap → reggel/este (ahol van); régi {trendek} → egyetlen, címke nélküli lista.
function heti_nap_szegmensek(napi) {
  if (napi && (napi.reggel || napi.este)) {
    const ki = [];
    if (napi.reggel && Array.isArray(napi.reggel.trendek))
      ki.push({ szegmens: "reggel", cimke: "Reggel", szavak: napi.reggel.trendek.map(function (t) { return t.kifejezes; }) });
    if (napi.este && Array.isArray(napi.este.trendek))
      ki.push({ szegmens: "este", cimke: "Este", szavak: napi.este.trendek.map(function (t) { return t.kifejezes; }) });
    return ki;
  }
  const szavak = (napi && Array.isArray(napi.trendek)) ? napi.trendek.map(function (t) { return t.kifejezes; }) : [];
  return [{ szegmens: "", cimke: "", szavak: szavak }];
}
```

Replace lines 1931-1934 (`const tdSz = ...` … `tdSz.textContent = ...`) with:

```javascript
    const tdSz = document.createElement("td"); tdSz.className = "heti-szavak";
    const napi = adat["napok/" + d + ".json"];
    const szegmensek = heti_nap_szegmensek(napi).filter(function (s) { return s.szavak.length; });
    if (!szegmensek.length) {
      tdSz.textContent = "nincs adat";
    } else if (szegmensek.length === 1 && !szegmensek[0].cimke) {
      tdSz.textContent = szegmensek[0].szavak.join(", ");   // régi nap: változatlan
    } else {
      szegmensek.forEach(function (s) {
        const div = document.createElement("div");
        div.className = "heti-szegmens";
        div.setAttribute("data-szegmens", s.szegmens);
        const cimke = document.createElement("span");
        cimke.className = "heti-szegmens-cimke";
        cimke.textContent = s.cimke + ": ";
        div.appendChild(cimke);
        div.appendChild(document.createTextNode(s.szavak.join(", ")));
        tdSz.appendChild(div);
      });
    }
```

In `docs/css/app.css` (a `.heti-szavak` szomszédságában, ~49-53), add:

```css
.heti-szegmens + .heti-szegmens { margin-top: .35rem; padding-top: .35rem; border-top: 1px solid #e6e6e6; }
.heti-szegmens-cimke { font-weight: 600; color: #555; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx playwright test e2e/heti.spec.js --workers=1`
Expected: PASS (a meglévő heti-tesztek is — a régi `{nap, trendek}` mock az egy-lista ágon megy).

- [ ] **Step 5: Commit**

```bash
git add docs/js/app.js docs/css/app.css e2e/heti.spec.js
git commit -m "$(cat <<'EOF'
feat(heti): reggel/este elválasztó a heti felkapott szó-cellában

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 8: #2 Kategória-idősor — Reggel/Este váltó

**Files:**
- Modify: `docs/js/app.js:1372-1393` (`kategoria_idosor`), `1505-1542` (`idosor_blokk_render`)
- Modify: `docs/css/app.css` (váltó-gomb stílus)
- Test: `e2e/trend.spec.js` (vagy `e2e/vezerlok.spec.js` — ahol az `#idosor-blokk` tesztek élnek)

**Interfaces:**
- Consumes: `kategoriak.json` szegmentált (`{napok:[{nap, reggel?, este?}]}`) VAGY régi (`{napok:[{nap, kategoriak}]}`) alak.
- Produces: `kategoria_idosor(kj, szegmens="este") -> {napok, vonalak}` — a `<szegmens>.kategoriak`-ból; ha a rekord régi (közvetlen `kategoriak`) és `szegmens==="este"`, fallback arra. DOM: `#idosor-blokk` fölött `.idosor-szegmens-valto` két gombbal (`data-szegmens="reggel"`/`"este"`, `aria-pressed`), az aktív a modul `idosor_szegmens` (alap `"este"`).

- [ ] **Step 1: Write the failing test**

Add to the `#idosor-blokk` spec file:

```javascript
test("N. idősor: Reggel/Este váltó — alap Este, váltásra a reggeli számok", async ({ page }) => {
  const KJ = { napok: [
    { nap: "2026-08-10",
      reggel: { kategoriak: { "Sports": 3 } },
      este:   { kategoriak: { "Sports": 1, "Politics": 2 } } },
  ]};
  await page.route(/kategoriak\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify(KJ) }));
  await page.route(/legfrissebb\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: [] }) }));
  await page.route(/napok\/index\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: ["2026-08-10"] }) }));
  await page.goto("/");
  const tukor = page.locator("#idosor-blokk .idosor-adat");
  await expect(tukor).toHaveAttribute("data-vonal-szam", "2");                 // este: Sports + Politics
  await expect(page.locator('.idosor-szegmens-valto [data-szegmens="este"]')).toHaveAttribute("aria-pressed", "true");
  await page.locator('.idosor-szegmens-valto [data-szegmens="reggel"]').click();
  await expect(page.locator("#idosor-blokk .idosor-adat")).toHaveAttribute("data-vonal-szam", "1");  // reggel: csak Sports
});
```

> Az `ATTR_T.vonal_szam` a rejtett tükör `data-vonal-szam` attribútuma (az `idosor.vonalak.length`); a spec ezt olvassa.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test e2e/trend.spec.js --workers=1 -g "Reggel/Este váltó"`
Expected: FAIL (nincs `.idosor-szegmens-valto`; a `kategoria_idosor` a `n.kategoriak`-ot olvassa, ami szegmentált rekordon `undefined`).

- [ ] **Step 3: Implement**

In `docs/js/app.js`:

(a) Modul-változó a többi `idosor_*` globális mellé (~1319 környékén, ahol `idosor_aktiv` deklarált):

```javascript
let idosor_szegmens = "este";   // #2 Reggel/Este váltó — alap az esti (teljes) pillanatkép
```

(b) `kategoria_idosor` szegmens-paraméter + normalizálás. Cseréld a függvény ELEJÉT (1372-1376):

```javascript
function kategoria_idosor(kj, szegmens) {
  const szeg = szegmens || "este";
  function kat(n) {   // a rekord kategoriak-ja a kért szegmensre; régi lapos rekord 'este'-ként
    if (n[szeg] && n[szeg].kategoriak) return n[szeg].kategoriak;
    if (szeg === "este" && n.kategoriak) return n.kategoriak;   // visszafelé kompat
    return null;
  }
  const rekordok = ((kj && kj.napok) || []).filter(function (n) { return n && n.nap && kat(n); });
  if (!rekordok.length) return { napok: [], vonalak: [] };
  const jelen = {};
  rekordok.forEach(function (n) { jelen[n.nap] = kat(n); });
```

A függvény törzsének többi része (a `napok`/`elso`/`vonalak` számítás, 1377-1393) VÁLTOZATLAN.

(c) `idosor_blokk_render` — a shaper hívása szegmenssel + a váltó megépítése. Cseréld az 1518-as sort:

```javascript
  const idosor = kategoria_idosor(adat["kategoriak.json"], idosor_szegmens);
```

A `blokk.appendChild(doboz);` (1526) UTÁN, a tükör ELŐTT szúrd be a váltót:

```javascript
  blokk.appendChild(idosor_szegmens_valto_epit());
```

És add a helpert `idosor_blokk_render` FÖLÉ:

```javascript
// a #2 Reggel/Este váltó — az egész kategória-idősort átváltja (alap Este). Katt → idosor_szegmens + újrarender.
function idosor_szegmens_valto_epit() {
  const valto = document.createElement("div");
  valto.className = "idosor-szegmens-valto";
  [["reggel", "Reggeli 9:00"], ["este", "Esti 21:00"]].forEach(function (par) {
    const g = document.createElement("button");
    g.type = "button";
    g.setAttribute("data-szegmens", par[0]);
    g.setAttribute("aria-pressed", idosor_szegmens === par[0] ? "true" : "false");
    g.textContent = par[1];
    g.addEventListener("click", function () {
      if (idosor_szegmens === par[0]) return;
      idosor_szegmens = par[0];
      idosor_blokk_render();
    });
    valto.appendChild(g);
  });
  return valto;
}
```

A takarítás (1513-1514) bővítése, hogy a régi váltó is törlődjön újrarenderkor — a `blokk.querySelectorAll(...)` szelektorlistához add: `+ ", .idosor-szegmens-valto"`.

In `docs/css/app.css`, add:

```css
.idosor-szegmens-valto { display: flex; gap: .5rem; margin: .25rem 0 .75rem; }
.idosor-szegmens-valto button { padding: .25rem .75rem; border: 1px solid #ccc; border-radius: 999px; background: #fff; cursor: pointer; }
.idosor-szegmens-valto button[aria-pressed="true"] { background: #3366cc; color: #fff; border-color: #3366cc; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx playwright test e2e/trend.spec.js e2e/vezerlok.spec.js --workers=1`
Expected: PASS (a meglévő idősor-tesztek is — a régi `{nap, kategoriak}` mock a fallback-ágon, alap `este`).

- [ ] **Step 5: Commit**

```bash
git add docs/js/app.js docs/css/app.css e2e/trend.spec.js
git commit -m "$(cat <<'EOF'
feat(idosor): Reggel/Este váltó a kategória-idősoron (alap Este)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 9: #1 Napi „Ma felkapott" — két blokk egymás alatt

**Files:**
- Modify: `docs/js/app.js` — `trend_blokk_render` (1765-1827), `trend_adat_nap` (1334-1341), `trend_chart_epit` (1600-1620), `trend_chart_szinez` (1623-1630), `trend_szinkron` (1712-1732), `trend_chart_takarit` (~1593-1598)
- Modify: `docs/css/app.css` (szegmens-blokk + fejléc stílus)
- Test: `e2e/trend.spec.js`

**Interfaces:**
- Consumes: Task 1 szegmentált napfájl; a per-nap adat a `napok/<nap>.json`-ból (mind a legfrissebb nap is).
- Produces: `#trend-blokk`-on belül szegmensenként egy `section.trend-szegmens[data-szegmens]` (opcionális `h3.trend-szegmens-cim`), mindegyikben saját oszlopdiagram + szűrő-chipek + kártyák; a szűrés PER-SZEGMENS (a chart-példány a szegmens-konténeren: `container._kchart`).
- Produces: `trend_szegmensek_nap(nap) -> [{szegmens, cimke, trendek}]|null` — a napfájl `_nap_szegmensek`-ének JS-párja + legfrissebb-fallback; `null` = a nap még tölt.

- [ ] **Step 1: Write the failing test**

Add to `e2e/trend.spec.js` (a fájl `trend()`/`napValt` mintáit használva; a legfrissebb nap MOST a napfájlból jön, ezért azt mockolni kell):

```javascript
test("N. napi: szegmentált nap két blokkja (Reggeli + Esti), saját chippel", async ({ page }) => {
  const IDX = { napok: ["2026-08-31"] };
  await page.route(/kategoriak\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: [] }) }));
  await page.route(/legfrissebb\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: [], kulcsszavak: {}, kulcsszo_osszesites: [] }) }));
  await page.route(/napok\/index\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify(IDX) }));
  await page.route(/napok\/2026-08-31\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({
    nap: "2026-08-31",
    reggel: { trendek: [trend("reggeli-szo", "5000", ["Sports"])], frissitve: "2026-08-31T07:00:00+00:00" },
    este: { trendek: [trend("esti-szo", "9000", ["Politics"]), trend("esti-ketto", "8000", ["Politics"])], frissitve: "2026-08-31T19:00:00+00:00" },
  }) }));
  await page.goto("/");
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="reggel"]')).toBeVisible();
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="este"]')).toBeVisible();
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="reggel"] .trend-kartya')).toHaveCount(1);
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="este"] .trend-kartya')).toHaveCount(2);
  // per-szegmens szűrő: az esti "Politics (2)" chip csak az esti blokkban
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="este"] .kategoria-szuro button[data-kategoria="Politics"]')).toHaveAttribute("data-count", "2");
});

test("N+1. napi: régi (nem szegmentált) nap egyetlen blokk, cím nélkül", async ({ page }) => {
  await page.route(/kategoriak\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: [] }) }));
  await page.route(/legfrissebb\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: [], kulcsszavak: {}, kulcsszo_osszesites: [] }) }));
  await page.route(/napok\/index\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: ["2026-08-20"] }) }));
  await page.route(/napok\/2026-08-20\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({
    nap: "2026-08-20", trendek: [trend("regi-szo", "5000", ["Sports"])],
  }) }));
  await page.goto("/");
  await expect(page.locator('#trend-blokk .trend-szegmens')).toHaveCount(1);
  await expect(page.locator('#trend-blokk .trend-szegmens-cim')).toHaveCount(0);   // régi napon nincs címke
  await expect(page.locator('#trend-blokk .trend-kartya')).toHaveCount(1);
});
```

> Az attribútum-/osztálynevek (`.trend-kartya`, `.kategoria-szuro`, `data-kategoria`, `data-count`) az `OSZT_T`/`ATTR_T` konstansokból jönnek — a spec a tényleges rendered neveket használja (lásd `trend.spec.js` fejléc).

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test e2e/trend.spec.js --workers=1 -g "két blokkja|egyetlen blokk"`
Expected: FAIL (nincs `.trend-szegmens`; a legfrissebb nap a legfrissebb.json-ból üres).

- [ ] **Step 3: Implement**

In `docs/js/app.js`:

(a) `trend_szegmensek_nap` — a `trend_adat_nap` (1334-1341) MELLÉ (ne töröld a régit, ha más is hívja; a render átáll az újra):

```javascript
// az adott nap megjelenítendő szegmensei: [{szegmens, cimke, trendek}] (reggel elöl), VAGY null (a nap még tölt).
// Forrás MINDEN napra a napok/<nap>.json; ha az még nincs betöltve → null (a render betölti és újrahív).
// Legfrissebb-fallback: ha a napfájl hiányzik/legacy-üres és a legfrissebb.json-ban van top_trendek → egy cím nélküli blokk.
function trend_szegmensek_nap(nap) {
  const rel = "napok/" + nap + ".json";
  const napi = adat[rel];
  if (napi === undefined) return null;   // még nincs betöltve
  if (napi && (napi.reggel || napi.este)) {
    const ki = [];
    if (napi.reggel && Array.isArray(napi.reggel.trendek))
      ki.push({ szegmens: "reggel", cimke: "Reggeli · 9:00", trendek: napi.reggel.trendek });
    if (napi.este && Array.isArray(napi.este.trendek))
      ki.push({ szegmens: "este", cimke: "Esti · 21:00", trendek: napi.este.trendek });
    return ki;
  }
  if (napi && Array.isArray(napi.trendek))
    return [{ szegmens: "", cimke: "", trendek: napi.trendek }];   // régi nap: egy blokk, cím nélkül
  // fallback: legfrissebb nap, napfájl nélkül
  if (nap === trend_legfrissebb_nap()) {
    const lf = adat["legfrissebb.json"];
    if (lf && Array.isArray(lf.top_trendek)) return [{ szegmens: "", cimke: "", trendek: lf.top_trendek }];
  }
  return [{ szegmens: "", cimke: "", trendek: [] }];
}
```

(b) `trend_chart_epit` (1600-1620): a modul-globális `kategoria_chart` HELYETT a konténerre. Cseréld a `kategoria_chart = new Chart(...)`-ot `blokk._kchart = new Chart(...)`-ra, és a `kategoria_chart._eloszlas = eloszlas;`-t `blokk._kchart._eloszlas = eloszlas;`-ra.

(c) `trend_chart_szinez` (1623-1630): vegyen `blokk`-ot, olvassa a konténer-példányt:

```javascript
function trend_chart_szinez(blokk, aktiv) {
  const chart = blokk && blokk._kchart;
  if (!chart) return;
  const el = chart._eloszlas || [];
  chart.data.datasets[0].backgroundColor = el.map(function (e) {
    return trend_szin(e.kategoria, aktiv !== "" && e.kategoria !== aktiv);
  });
  chart.update();
}
```

(d) `trend_szinkron` (1731): a `trend_chart_szinez(aktiv)` hívást cseréld `trend_chart_szinez(blokk, aktiv)`-ra.

(e) `trend_chart_takarit` (~1593-1598): a szegmens-konténerek chartjait is destroy-olni kell. A meglévő `trend_chart_peldanyok.forEach(destroy)` MELLÉ:

```javascript
  const blokk = document.getElementById("trend-blokk");
  if (blokk) blokk.querySelectorAll("." + OSZT_T.szegmens).forEach(function (sz) {
    if (sz._kchart) { sz._kchart.destroy(); sz._kchart = null; }
  });
```

(f) A szegmens-építő helper + `trend_blokk_render` átírása. Cseréld a `trend_blokk_render`-t (1765-1827) erre (async, hogy a napfájlt betölthesse):

```javascript
// egy szegmens-blokk (cím + összefoglaló + lista) egy önálló section.trend-szegmens-be, PER-SZEGMENS szűrés-állapottal.
function trend_szegmens_epit(gazda, sz) {
  const sec = document.createElement("section");
  sec.className = OSZT_T.szegmens;
  if (sz.szegmens) sec.setAttribute("data-szegmens", sz.szegmens);
  if (sz.cimke) {
    const c = document.createElement("h3");
    c.className = OSZT_T.szegmens_cim;
    c.textContent = sz.cimke;
    sec.appendChild(c);
  }
  gazda.appendChild(sec);
  const trendek = sz.trendek;
  if (!trendek.length) {
    const u = document.createElement("p"); u.className = OSZT_T.ures; u.textContent = TREND_URES_SZOVEG;
    sec.appendChild(u); return;
  }
  const eloszlas = kategoria_eloszlas(trendek);
  if (eloszlas.length > 0) sec.appendChild(trend_osszefoglalo_epit(trendek, eloszlas, sec));
  const mind_ures = trendek.every(function (t) { return !Array.isArray(t.idosor) || t.idosor.length === 0; });
  if (mind_ures) {
    const bu = document.createElement("p"); bu.className = OSZT_T.idosor_ures_blokk; bu.textContent = TREND_IDOSOR_URES_BLOKK;
    sec.appendChild(bu);
  } else {
    const nm = document.createElement("p"); nm.className = OSZT_T.normalizalas_magyarazat; nm.textContent = TREND_NORMALIZALAS_SZOVEG;
    sec.appendChild(nm);
  }
  const lista = document.createElement("div"); lista.className = OSZT_T.lista;
  trendek.forEach(function (t) { lista.appendChild(trend_kartya_epit(t, mind_ures)); });
  sec.appendChild(lista);
  Array.prototype.slice.call(lista.querySelectorAll("." + OSZT_T.kartya + "[" + ATTR_T.idosor_allapot + "='van']"))
    .forEach(trend_sparkline_letrehoz);
  trend_szinkron(sec);   // per-szegmens kezdő szinkron
}

async function trend_blokk_render() {
  const blokk = document.getElementById("trend-blokk");
  if (!blokk) return;
  trend_esemeny_kot();
  const nap = trend_aktualis_nap(blokk);
  if (nap) blokk.setAttribute(ATTR_T.nap, nap);

  // a napfájl betöltése MINDEN napra (a legfrissebb is innen jön a szegmensekhez); legacy/hiányzó → fallback
  const rel = "napok/" + nap + ".json";
  if (nap && !(rel in adat)) {
    try { adat[rel] = await nap_betolt(nap); } catch (e) { adat[rel] = null; }
  }

  trend_chart_takarit();
  blokk.querySelectorAll("." + OSZT_T.szegmens + ", ." + OSZT_T.osszefoglalo + ", ." + OSZT_T.lista + ", ." + OSZT_T.ures
    + ", ." + OSZT_T.idosor_ures_blokk + ", ." + OSZT_T.normalizalas_magyarazat)
    .forEach(function (e) { e.remove(); });

  const szegmensek = trend_szegmensek_nap(nap);
  if (szegmensek === null) return;   // még tölt — a napváltás/await újrahív

  const van = szegmensek.some(function (s) { return s.trendek.length; });
  if (!van) {
    const u = document.createElement("p"); u.className = OSZT_T.ures; u.textContent = TREND_URES_SZOVEG;
    blokk.appendChild(u); return;
  }
  szegmensek.forEach(function (s) { trend_szegmens_epit(blokk, s); });
}
```

(g) `trend_nap_valt` (1851-1862): a napfájl-betöltés már a renderben van, de a régi ág maradhat; a lényeg, hogy `trend_blokk_render()` most async — a hívást `await trend_blokk_render();`-re állítsd (a fn async, a hívó `trend_nap_valt` már async).

(h) Az `OSZT_T` konstans-objektumhoz (a fájl elején, a trend OSZT_T blokkban) add: `szegmens: "trend-szegmens", szegmens_cim: "trend-szegmens-cim",`.

In `docs/css/app.css`, add:

```css
.trend-szegmens + .trend-szegmens { margin-top: 1.5rem; padding-top: 1.25rem; border-top: 2px solid #e0e0e0; }
.trend-szegmens-cim { margin: 0 0 .5rem; font-size: 1.05rem; color: #333; }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx playwright test e2e/trend.spec.js --workers=1`
Expected: PASS. A meglévő trend-tesztek: ahol a legfrissebb napot a `legfrissebb.json`-ból várták napfájl-mock nélkül, ott a fallback-ág egy cím nélküli blokkot ad (a `.trend-lista`/`.trend-kartya` szelektorok VÁLTOZATLANUL működnek, mert a kártyák a szegmens-konténeren belül is ugyanolyanok). Ha egy meglévő teszt `#trend-blokk > .trend-lista` KÖZVETLEN gyermeket feltételez, lazítsd `#trend-blokk .trend-lista`-ra (leszármazott).

> FONTOS regresszió-ellenőrzés: futtasd a TELJES trend/naptár/vezérlő e2e-t (`npx playwright test e2e/trend.spec.js e2e/naptar.spec.js e2e/vezerlok.spec.js e2e/dashboard.spec.js --workers=1`), mert a per-konténer chart-refaktor (`kategoria_chart` → `._kchart`) és az async render érinthet meglévő asserteket. A hibás asserteket a leszármazott-szelektorra/új DOM-ra igazítsd, a VISELKEDÉST ne változtasd.

- [ ] **Step 5: Commit**

```bash
git add docs/js/app.js docs/css/app.css e2e/trend.spec.js
git commit -m "$(cat <<'EOF'
feat(napi): reggeli/esti felkapott két blokk egymás alatt, per-szegmens szűrés

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 10: Teljes suite + leltár-invariáns

**Files:**
- Modify: a leltár-fájl (a repó leltár/invariáns tartója — keresd: `grep -rl "invariáns\|leltár" docs/ --include=*.md | head`), ha a felkapott-szekció számot tart.
- Test: teljes SOROS suite.

- [ ] **Step 1: Teljes Python suite**

Run: `.venv/bin/python -m pytest -p no:xdist -q`
Expected: PASS (mind).

- [ ] **Step 2: Teljes Playwright suite**

Run: `npx playwright test --workers=1`
Expected: PASS (mind).

- [ ] **Step 3: Leltár-invariáns fizikai mérése**

Ha a projekt leltárt tart a felkapott-tesztekről, mérd meg a tényleges teszt-számokat (`pytest --collect-only -q | wc -l`, e2e teszt-count) és frissítsd a leltár-számot a MÉRT értékre (ne becsülj). Az ops-tételek (workflow-k, szerver-cron) NEM a leltárban élnek — memóriába.

- [ ] **Step 4: Commit (ha volt leltár-változás)**

```bash
git add <leltár-fájl>
git commit -m "$(cat <<'EOF'
teszt(felkapott): leltár-invariáns a reggeli/esti szegmensekkel (mért)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

## FÁZIS 4 — Ops (kézi, szerver-oldali — a felhasználó futtatja)

### Task 11: Szerver-cron + memória (NEM kód-teszt)

**Files:** nincs repó-fájl; szerver-crontab + memória-frissítés.

- [ ] **Step 1: Push (KÜLÖN kapuzott kör)** — a Fázis 1-3 commitjai a szokásos sync-gate-tel (fetch → divergencia → rebase ha kell → push → rev-list 0 0), külön user-jóváhagyással. A GitHub Actions-ön futtatható a `reggeli.yml` egy kézi `workflow_dispatch`-csal (füst-teszt), és megnézhető a `napok/<ma>.json` `reggel` szegmense.

- [ ] **Step 2: Szerver-crontab (a felhasználó a Hetzner-en, `trendfigyelo` user).** A meglévő `10 19 UTC napi.yml` (CRON_TZ=UTC) trigger CSERÉJE Budapest-helyi triggerekre (a szerver TZ Europe/Budapest, a `CRON_TZ=UTC` sort ezekhez EL kell hagyni):
  ```
  0 9  * * *  bash /home/trendfigyelo/trendfigyelo/scripts/trigger_workflow.sh reggeli.yml >> ~/trigger.log 2>&1
  0 21 * * *  bash /home/trendfigyelo/trendfigyelo/scripts/trigger_workflow.sh napi.yml    >> ~/trigger.log 2>&1
  ```
  a youtube-trigger marad. (A parancsokat a felhasználó adja ki; én a pontos lépéseket megadom.)

- [ ] **Step 3: Memória-frissítés** — `napi-futas-megbizhatosag.md` + `oras-only-hosszu-ablak.md` szomszédja: új memória VAGY meglévő bővítés a reggeli/esti szétválasztásról (szegmentált napfájl, `--mode`, szegmens-őr, Budapest-helyi cron). A MEMORY.md indexsor frissítése. A korábbi „cron ~2h korán tüzel + napi 2× gyűjtés" megfigyelés részben rendeződik (a Budapest-helyi ütemezés a szándékolt időt adja).

---

## Önellenőrzés (a terv a spec ellen)

- **Spec §3 időzítés** → Task 6 (`reggeli.yml`/`napi.yml` cron) + Task 11 (szerver-cron Budapest-idő). ✓
- **Spec §4 B1 mód-kapcsoló** → Task 4 (`futtat mode` + `main --mode`). ✓
- **Spec §5 szegmentált napfájl + visszafelé kompat** → Task 1 (`napi_ir` + `_nap_szegmensek`). ✓
- **Spec §5.1 kategoriak szegmensek** → Task 2. ✓
- **Spec §6 legfrissebb kulcsszó-megőrzés** → Task 3 + Task 4 (d). ✓
- **Spec §7 szegmens-tudatos őr** → Task 5 + Task 6 (őr-lépések). ✓
- **Spec §8 frontend #1/#2/#3** → Task 9 / Task 8 / Task 7. ✓
- **Spec §9 tesztelés/kapuk** → minden task TDD + Task 10 teljes suite. ✓
- **Type-konzisztencia:** `_nap_szegmensek` (Task 1) → használja Task 2 (`kategoriak_ir`) és a JS-párja Task 7/9; `szegmens` kulcsok `"reggel"`/`"este"` végig; `frissitve_iso` a napfájl-szegmensben → olvassa a `szegmens_mar_gyujtottunk_ma` (Task 5). ✓
- **YAGNI:** nincs déli gyűjtés, nincs történelmi migráció, a #2 nem kap egyszerre-reggel+este vonalakat (váltó). ✓
