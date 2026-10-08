# Bővítés fül (elmozdulásfigyelő + ügy-életút + közpolitikai szűrő) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Új „Bővítés" fül 3 képességgel: (F1) determinista elmozdulásfigyelő + halvány szokásos-sáv a meglévő chartokon; (F2) LLM-csoportosított ügy-életút (gördülő 30 nap, naponta); (F3) új 8-kategóriás közpolitikai taxonómia + szűrők.

**Architecture:** F1 determinista az esti `futtato.py`-ban → `docs/data/elmozdulas.json` (nincs új workflow). F2 LLM-kör (a heti/havi mintája) → `docs/data/ugyek.json` új `bovites.yml`-ben (workflow_run a „Napi trendgyűjtés"-re, napi őr, fail-soft). F3 izolált `szakpolitika.py` (a `config.yaml` érintetlen). Frontend: új `bovites.html`+`bovites.js` + a szokásos-sáv az `app.js` meglévő chartjain, kapcsolóval.

**Tech Stack:** Python 3.12 (stdlib + meglévő anthropic/json_export), Chart.js (vendorelt), vanilla JS, GitHub Actions, pytest + Playwright.

**Spec:** `docs/superpowers/specs/2026-10-08-bovites-ful-design.md`

## Global Constraints

- NULLA új Python-dependency (stdlib + meglévő anthropic/json_export). Frontend: meglévő vendorelt Chart.js, nincs új vendor/külső betöltés.
- Grounding: a Python a VALÓS számok; az LLM CSAK csoportosít/nevez/sorol be a korpuszból; `grounding_validal` szűr. „A frontend NEM SZÁMOL" — a metrikák/sáv a backend JSON-ból.
- NINCS argless `datetime.now()` a modul-logikában (ablak-vég/keszult = PARAMÉTER; a belépő adja a `seged.most_utc()`-ot).
- `ugy_elemez`: `claude-opus-4-8`, adaptive thinking, STREAMING kötelező, nincs beta-header, bounded-retry (3×, 5/20/60mp) + fail-soft. `MAX_TOKENS_UGYEK = 128000`.
- Atomi írás (`json_export._ir_json`); irreplaceable adat (regresszió/nyers/napok) READ-ONLY. A `bovites.yml` commit CSAK `docs/data/ugyek.json`; az `elmozdulas.json`-t a főfutás `napi.yml` commitolja (`git add docs/data`).
- A plafon/`tervezett_hivasszam` (`futtato.py`) VÁLTOZATLAN — F1 determinista, F2 LLM; egyik sem hív Google-t.
- `config.yaml` (gyűjtés-kritikus) ÉRINTETLEN — a szakpolitika izolált modul.
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör. SOROS suite (pytest + Playwright) zöld.
- Nav 6→7 fül MINDEN HTML-oldalon, sorrend: Napi Elemzések · Heti értékelés · Havi elemzés · Google Trendek · YouTube Trendek · Bővítés · Infó. A nav-tesztek (`e2e/menu.spec.js`) frissítendők.
- Python-teszt futtatás: `.venv/bin/python -m pytest …` (a `python` NINCS PATH-on). e2e: `npx playwright test …` (auto-szerver).

---

### Task 1: `szakpolitika.py` — közpolitikai taxonómia + besorolás

**Files:**
- Create: `trendfigyelo/szakpolitika.py`
- Test: `tests/test_szakpolitika.py`

**Interfaces:**
- Produces: `SZAKPOLITIKAK` (list of (slug, címke)), `SZAKPOLITIKA_SLUGOK` (set), `szakpolitika_besorol(kifejezes=None, domen=None, temak=None) -> slug`. A Task 2 (elmozdulas) és Task 5-7 (ugyek) fogyasztja.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_szakpolitika.py
from trendfigyelo import szakpolitika as sp


def test_nyolc_kategoria_es_slugok():
    assert len(sp.SZAKPOLITIKAK) == 8
    assert sp.SZAKPOLITIKA_SLUGOK == {
        "szocialpolitika", "egeszsegpolitika", "oktataspolitika", "gazdasag_foglalkoztatas",
        "lakhatas", "energia_rezsi", "kozelet_kozigazgatas", "egyeb"}
    assert dict(sp.SZAKPOLITIKAK)["egeszsegpolitika"] == "Egészségpolitika"


def test_kulcsszo_terkep_mind_a_28():
    minta = {"nyugdíj": "szocialpolitika", "segély": "szocialpolitika",
             "kórház": "egeszsegpolitika", "sürgősségi": "egeszsegpolitika",
             "iskola": "oktataspolitika", "pedagógus": "oktataspolitika",
             "infláció": "gazdasag_foglalkoztatas", "állás": "gazdasag_foglalkoztatas",
             "fizetés": "gazdasag_foglalkoztatas", "munkanélküliség": "gazdasag_foglalkoztatas",
             "csőd": "gazdasag_foglalkoztatas", "albérlet": "lakhatas", "eladó lakás": "lakhatas",
             "hitel": "lakhatas", "kölcsön": "lakhatas", "benzin": "energia_rezsi",
             "rezsi": "energia_rezsi", "napelem": "energia_rezsi", "kormányablak": "kozelet_kozigazgatas",
             "tüntetés": "kozelet_kozigazgatas", "korrupció": "kozelet_kozigazgatas",
             "kormány": "kozelet_kozigazgatas", "akciós újság": "egyeb", "nyaralás": "egyeb"}
    for szo, vart in minta.items():
        assert sp.szakpolitika_besorol(kifejezes=szo) == vart, szo


def test_fallback_domen_majd_tema_majd_egyeb():
    assert sp.szakpolitika_besorol(domen="egeszsegugy") == "egeszsegpolitika"
    assert sp.szakpolitika_besorol(domen="oktatas") == "oktataspolitika"
    assert sp.szakpolitika_besorol(temak=["Politics"]) == "kozelet_kozigazgatas"
    assert sp.szakpolitika_besorol(temak=["Health"]) == "egeszsegpolitika"
    assert sp.szakpolitika_besorol(temak=["Ismeretlen"]) == "egyeb"
    assert sp.szakpolitika_besorol() == "egyeb"


def test_prioritas_kulcsszo_eros_a_domen_elott():
    # a kulcsszó-térkép erősebb a doménnél (nyugdíj domen=megelhetes, de szocialpolitika)
    assert sp.szakpolitika_besorol(kifejezes="nyugdíj", domen="megelhetes") == "szocialpolitika"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_szakpolitika.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

```python
# trendfigyelo/szakpolitika.py
"""Közpolitikai (szakpolitikai) taxonómia és determinista besorolás a Bővítés fülhöz. IZOLÁLT
modul — a config.yaml (gyűjtés-kritikus) ÉRINTETLEN. 3-szintű besorolás: kulcsszó-térkép →
domén-fallback → Google-témacímke-fallback → 'egyeb'."""

SZAKPOLITIKAK = [
    ("szocialpolitika", "Szociálpolitika"),
    ("egeszsegpolitika", "Egészségpolitika"),
    ("oktataspolitika", "Oktatáspolitika"),
    ("gazdasag_foglalkoztatas", "Gazdaság- és foglalkoztatáspolitika"),
    ("lakhatas", "Lakhatás"),
    ("energia_rezsi", "Energia és rezsi"),
    ("kozelet_kozigazgatas", "Közélet és közigazgatás"),
    ("egyeb", "Egyéb / nem közpolitikai"),
]
SZAKPOLITIKA_SLUGOK = {s for s, _ in SZAKPOLITIKAK}

KULCSSZO_SZAKPOLITIKA = {
    "állás": "gazdasag_foglalkoztatas", "kormányablak": "kozelet_kozigazgatas",
    "eladó lakás": "lakhatas", "albérlet": "lakhatas", "akciós újság": "egyeb",
    "benzin": "energia_rezsi", "nyaralás": "egyeb", "kórház": "egeszsegpolitika",
    "betegség": "egeszsegpolitika", "napelem": "energia_rezsi", "nyugdíj": "szocialpolitika",
    "hitel": "lakhatas", "tüntetés": "kozelet_kozigazgatas", "infláció": "gazdasag_foglalkoztatas",
    "rezsi": "energia_rezsi", "fizetés": "gazdasag_foglalkoztatas", "segély": "szocialpolitika",
    "várólista": "egeszsegpolitika", "háziorvos": "egeszsegpolitika", "műtét": "egeszsegpolitika",
    "iskola": "oktataspolitika", "munkanélküliség": "gazdasag_foglalkoztatas",
    "csőd": "gazdasag_foglalkoztatas", "kölcsön": "lakhatas", "sürgősségi": "egeszsegpolitika",
    "pedagógus": "oktataspolitika", "korrupció": "kozelet_kozigazgatas", "kormány": "kozelet_kozigazgatas",
}
DOMEN_SZAKPOLITIKA = {
    "megelhetes": "gazdasag_foglalkoztatas", "egeszsegugy": "egeszsegpolitika",
    "oktatas": "oktataspolitika", "gazdasag": "gazdasag_foglalkoztatas",
    "politika": "kozelet_kozigazgatas",
}
GOOGLE_TEMA_SZAKPOLITIKA = {
    "Politics": "kozelet_kozigazgatas", "Law and Government": "kozelet_kozigazgatas",
    "Health": "egeszsegpolitika", "Business and Finance": "gazdasag_foglalkoztatas",
    "Jobs and Education": "oktataspolitika", "Climate": "energia_rezsi",
    "Science": "egyeb", "Technology": "egyeb", "Sports": "egyeb", "Entertainment": "egyeb",
    "Hobbies and Leisure": "egyeb", "Other": "egyeb",
}


def szakpolitika_besorol(kifejezes=None, domen=None, temak=None):
    """3-szintű determinista besorolás: pontos kulcsszó → domén → Google-témacímke → 'egyeb'."""
    if kifejezes and kifejezes in KULCSSZO_SZAKPOLITIKA:
        return KULCSSZO_SZAKPOLITIKA[kifejezes]
    if domen and domen in DOMEN_SZAKPOLITIKA:
        return DOMEN_SZAKPOLITIKA[domen]
    for t in (temak or []):
        if t in GOOGLE_TEMA_SZAKPOLITIKA:
            return GOOGLE_TEMA_SZAKPOLITIKA[t]
    return "egyeb"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_szakpolitika.py -q`
Expected: PASS (4 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/szakpolitika.py tests/test_szakpolitika.py
git commit -m "feat(bovites): szakpolitika.py - 8-kategorias kozpolitikai taxonomia + determinista besorolas"
```

---

### Task 2: `elmozdulas.py` — determinista elmozdulás-metrikák + sáv

**Files:**
- Create: `trendfigyelo/elmozdulas.py`
- Test: `tests/test_elmozdulas.py`

**Interfaces:**
- Consumes: `kulcsszo_regresszio.json` + `kulcsszo_masodlagos_regresszio.json` (per-kulcsszó `intervallumok`), `kulcsszo_nyers.json` (`{kulcsszavak: {<szo>: [{ablak_veg_utc, pontok:[{idopont_utc, ertek, reszleges}]}, …]}}`), `szakpolitika.szakpolitika_besorol`.
- Produces: `elmozdulas_szamit(docs_data) -> dict`, `elmozdulas_ir(docs_data) -> Path` (a Task 3 hívja a `futtato.py`-ból).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_elmozdulas.py
import json
from pathlib import Path

from trendfigyelo import elmozdulas as em


def _ir(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _reg(tmp_path, kulcsszavak):
    _ir(tmp_path / "kulcsszo_regresszio.json", {"szamitva_utc": "2026-10-07T18:00:00+00:00",
                                                "kulcsszavak": kulcsszavak})
    _ir(tmp_path / "kulcsszo_masodlagos_regresszio.json", {"kulcsszavak": {}})


def _nyers(tmp_path, szo, pontok):
    _ir(tmp_path / "kulcsszo_nyers.json", {"kulcsszavak": {szo: [
        {"kulcsszo": szo, "ablak_kezdet_utc": pontok[0]["idopont_utc"],
         "ablak_veg_utc": pontok[-1]["idopont_utc"], "pontok": pontok}]}})


def _iv(**kw):
    alap = {"ervenyes": True, "irany": "novekszik", "meredekseg_nap": 1.0, "se_meredekseg": 0.2,
            "r2": 0.6, "pontok_hasznalt": 160, "reziduum_szokasos": 4.0, "mai_reziduum": 12.0,
            "illeszkedes": "felette",
            "illesztes_vonal": [{"idopont_utc": "2026-10-01T00:00:00+00:00", "ertek": 30.0},
                                {"idopont_utc": "2026-10-07T00:00:00+00:00", "ertek": 48.0}]}
    alap.update(kw)
    return alap


def test_szokatlan_es_irany_es_elteres(tmp_path):
    _reg(tmp_path, {"benzin": {"domen": "megelhetes", "tipus": "szintmero", "racs": "ora",
                               "intervallumok": {"1_het": _iv()}}})
    _nyers(tmp_path, "benzin", [{"idopont_utc": "2026-10-07T18:00:00+00:00", "ertek": 60, "reszleges": False}])
    ki = em.elmozdulas_szamit(str(tmp_path))
    b = ki["kulcsszavak"]["benzin"]
    assert b["szokatlan"] is True
    assert b["irany"] == "emelkedik"                 # illeszkedes felette → emelkedik
    assert round(b["elteres"], 2) == 3.0             # 12.0 / max(4.0, 3.0) = 3.0
    assert b["elteres_nyers"] == 12.0
    assert b["szakpolitika"] == "energia_rezsi"
    assert "1_het" in b["sav"] and b["sav"]["1_het"]["also"] and b["sav"]["1_het"]["felso"]


def test_illeszkedik_nem_szokatlan(tmp_path):
    _reg(tmp_path, {"iskola": {"domen": "oktatas", "tipus": "szintmero", "racs": "het",
                               "intervallumok": {"1_ho": _iv(illeszkedes="illeszkedik", mai_reziduum=1.0)}}})
    _nyers(tmp_path, "iskola", [{"idopont_utc": "2026-10-07T18:00:00+00:00", "ertek": 40, "reszleges": False}])
    ki = em.elmozdulas_szamit(str(tmp_path))
    assert ki["kulcsszavak"]["iskola"]["szokatlan"] is False
    assert "iskola" not in ki["szokatlan_lista"]      # csak a szokatlanok a listában


def test_megbizhatosag_label(tmp_path):
    _reg(tmp_path, {"a": {"domen": "x", "tipus": "szintmero", "racs": "ora",
                          "intervallumok": {"1_het": _iv(r2=0.7, pontok_hasznalt=150)}},
                    "b": {"domen": "x", "tipus": "szintmero", "racs": "ora",
                          "intervallumok": {"1_het": _iv(r2=0.05, pontok_hasznalt=20)}}})
    _nyers(tmp_path, "a", [{"idopont_utc": "2026-10-07T18:00:00+00:00", "ertek": 60, "reszleges": False}])
    ki = em.elmozdulas_szamit(str(tmp_path))
    assert ki["kulcsszavak"]["a"]["megbizhatosag"] == "magas"
    assert ki["kulcsszavak"]["b"]["megbizhatosag"] == "alacsony"


def test_idotartam_egymas_utani_savon_kivuli_pontok(tmp_path):
    # a trendvonal ~30→48 (10-01..10-07). Az utolsó 3 pont magasan a sáv fölött, előtte illesztő.
    _reg(tmp_path, {"benzin": {"domen": "megelhetes", "tipus": "szintmero", "racs": "ora",
                               "intervallumok": {"1_het": _iv()}}})
    pts = [{"idopont_utc": f"2026-10-07T{h:02d}:00:00+00:00", "ertek": e, "reszleges": False}
           for h, e in [(10, 48), (11, 49), (12, 90), (13, 92), (14, 95)]]  # utolsó 3 kiugró
    _nyers(tmp_path, "benzin", pts)
    ki = em.elmozdulas_szamit(str(tmp_path))
    assert ki["kulcsszavak"]["benzin"]["idotartam_pont"] == 3
    assert ki["kulcsszavak"]["benzin"]["idotartam_ota_utc"] == "2026-10-07T12:00:00+00:00"


def test_elmozdulas_ir(tmp_path):
    _reg(tmp_path, {"benzin": {"domen": "megelhetes", "tipus": "szintmero", "racs": "ora",
                               "intervallumok": {"1_het": _iv()}}})
    _nyers(tmp_path, "benzin", [{"idopont_utc": "2026-10-07T18:00:00+00:00", "ertek": 60, "reszleges": False}])
    p = em.elmozdulas_ir(str(tmp_path))
    assert Path(p).exists()
    mentve = json.loads(Path(p).read_text(encoding="utf-8"))
    assert "benzin" in mentve["kulcsszavak"] and "szamitva_utc" in mentve
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_elmozdulas.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

```python
# trendfigyelo/elmozdulas.py
"""Determinista elmozdulásfigyelő a Bővítés fülhöz: a kulcsszo_regresszio.json szokásos-szint /
eltérés / irány / megbízhatóság adataiból + a nyers sorból a 'mióta tart' (sávon kívüli egymás
utáni pontok). Zéró Google-hívás; az esti futtato.py-ban fut a regresszió után (mint a kategoriak_ir)."""
import json
from datetime import datetime
from pathlib import Path

from trendfigyelo import json_export, szakpolitika

SAV_SZORZO = 2.0     # a reziduum_szokasos (MAD) szorzója — a regresszio._illeszkedes_allapot-tal konzisztens
SAV_MIN = 3.0        # a sáv alsó korlátja
ELSODLEGES_IV = {"ora": "1_het", "nap": "1_ho", "het": "1_ho"}   # racs → melyik intervallumból


def _ts(s):
    return datetime.fromisoformat(s).timestamp()


def _vonal(iv):
    """A trendvonal (a+b*t) a két illesztes_vonal végpontból; (b_per_mp, t0, y0) vagy None."""
    v = iv.get("illesztes_vonal") or []
    if len(v) < 2:
        return None
    t0, y0 = _ts(v[0]["idopont_utc"]), float(v[0]["ertek"])
    t1, y1 = _ts(v[-1]["idopont_utc"]), float(v[-1]["ertek"])
    if t1 == t0:
        return None
    return ((y1 - y0) / (t1 - t0), t0, y0)


def _megbizhatosag(iv):
    r2 = iv.get("r2") or 0.0
    pont = iv.get("pontok_hasznalt") or 0
    if r2 >= 0.5 and pont >= 100:
        return "magas"
    if r2 >= 0.2 and pont >= 50:
        return "kozepes"
    return "alacsony"


def _idotartam(iv, pontok):
    """Hány egymást követő LEGUTÓBBI nyers pont van a szokásos sávon kívül (a trendvonalhoz mért
    reziduum > sáv), a mai eltérés irányában. (szam, elso_ilyen_idopont) vagy (0, None)."""
    vonal = _vonal(iv)
    if not vonal or not pontok:
        return 0, None
    b, t0, y0 = vonal
    mad = float(iv.get("reziduum_szokasos") or 0.0)
    sav = max(SAV_SZORZO * mad, SAV_MIN)
    elojel = 1 if (iv.get("mai_reziduum") or 0) >= 0 else -1
    szam, ota = 0, None
    for p in reversed(pontok):                      # a legfrissebbtől visszafelé
        if p.get("reszleges"):
            continue
        rez = float(p["ertek"]) - (y0 + b * (_ts(p["idopont_utc"]) - t0))
        if rez * elojel > sav:                      # a shift irányában, a sávon kívül
            szam += 1
            ota = p["idopont_utc"]
        else:
            break
    return szam, ota


def _sav_pontok(iv):
    vonal = _vonal(iv)
    v = iv.get("illesztes_vonal") or []
    if not vonal or len(v) < 2:
        return None
    mad = float(iv.get("reziduum_szokasos") or 0.0)
    d = max(SAV_SZORZO * mad, SAV_MIN)
    also = [{"idopont_utc": p["idopont_utc"], "ertek": round(float(p["ertek"]) - d, 2)} for p in v]
    felso = [{"idopont_utc": p["idopont_utc"], "ertek": round(float(p["ertek"]) + d, 2)} for p in v]
    return {"also": also, "felso": felso}


def _betolt(docs_data, nev):
    try:
        return json.loads((Path(docs_data) / nev).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def elmozdulas_szamit(docs_data):
    """Per követett kulcsszó az elsődleges intervallumból: szokatlan/irány/eltérés/mióta-tart/
    megbízhatóság/sáv + szakpolitika. Determinista, csak olvas."""
    reg = _betolt(docs_data, "kulcsszo_regresszio.json")
    reg2 = _betolt(docs_data, "kulcsszo_masodlagos_regresszio.json")
    nyers = _betolt(docs_data, "kulcsszo_nyers.json").get("kulcsszavak") or {}
    egyesitett = {}
    egyesitett.update((reg.get("kulcsszavak") or {}))
    for szo, w in (reg2.get("kulcsszavak") or {}).items():
        egyesitett.setdefault(szo, w)
    out = {}
    for szo, w in egyesitett.items():
        racs = w.get("racs") or "ora"
        ivn = ELSODLEGES_IV.get(racs, "1_het")
        iv = (w.get("intervallumok") or {}).get(ivn) or {}
        if not iv.get("ervenyes"):
            continue
        illeszkedes = iv.get("illeszkedes")
        szokatlan = illeszkedes in ("felette", "alatta")
        mad = float(iv.get("reziduum_szokasos") or 0.0)
        mai = float(iv.get("mai_reziduum") or 0.0)
        ablakok = nyers.get(szo) or []
        pontok = (ablakok[-1].get("pontok") if ablakok else []) or []
        tart, ota = _idotartam(iv, pontok)
        out[szo] = {
            "szokatlan": szokatlan,
            "irany": "emelkedik" if illeszkedes == "felette" else ("csokken" if illeszkedes == "alatta" else "stabil"),
            "elteres": round(mai / max(mad, SAV_MIN), 2),
            "elteres_nyers": round(mai, 2),
            "idotartam_pont": tart, "idotartam_ota_utc": ota,
            "megbizhatosag": _megbizhatosag(iv),
            "domen": w.get("domen"), "tipus": w.get("tipus"),
            "szakpolitika": szakpolitika.szakpolitika_besorol(kifejezes=szo, domen=w.get("domen")),
            "sav": {ivn: _sav_pontok(iv)} if _sav_pontok(iv) else {},
        }
    szokatlan_lista = sorted([s for s, v in out.items() if v["szokatlan"]],
                             key=lambda s: -abs(out[s]["elteres"]))
    return {"szamitva_utc": reg.get("szamitva_utc"), "kulcsszavak": out, "szokatlan_lista": szokatlan_lista}


def elmozdulas_ir(docs_data):
    """Az elmozdulas.json atomi írása (a json_export._ir_json mintája)."""
    return json_export._ir_json(Path(docs_data) / "elmozdulas.json", elmozdulas_szamit(docs_data))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_elmozdulas.py -q`
Expected: PASS (5 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/elmozdulas.py tests/test_elmozdulas.py
git commit -m "feat(bovites): elmozdulas.py - determinista szokatlan-elmozdulas metrikak + savpontok"
```

---

### Task 3: `elmozdulas_ir` bekötése a `futtato.py` esti futásába

**Files:**
- Modify: `trendfigyelo/futtato.py` (a `kategoriak.kategoriak_ir(...)` / `regresszio.regresszio_ir(...)` után)
- Test: `tests/test_futtato.py` (kiterjesztés)

**Interfaces:**
- Consumes: `elmozdulas.elmozdulas_ir(docs_data_mappa)` (Task 2). Google-hívás NÉLKÜL — a plafon/`tervezett_hivasszam` VÁLTOZATLAN.

- [ ] **Step 1: Write the failing test** (`tests/test_futtato.py`-hoz — a meglévő stílusban; a lényeg: az esti futás hívja az `elmozdulas_ir`-t)

```python
# tests/test_futtato.py  (hozzáadás)
def test_esti_futas_hivja_az_elmozdulas_irt(monkeypatch, tmp_path):
    # a meglévő futtató-tesztek mintájára: mockold a Google-ágakat, és figyeld, hogy az
    # elmozdulas.elmozdulas_ir meghívódik a docs/data mappára az esti futásban.
    from trendfigyelo import futtato, elmozdulas
    hivott = {}
    monkeypatch.setattr(elmozdulas, "elmozdulas_ir", lambda dd: hivott.setdefault("dd", dd))
    # ... a meglévő test_futtato minimál-konfig + mockolt kliens beállítása (lásd a fájl elejét),
    # futtato.futtat(...) / main(...) esti módban, majd:
    assert "dd" in hivott
```

*(Megjegyzés az implementernek: igazodj a `tests/test_futtato.py` meglévő fixture-mintájához — ugyanúgy mockold a `Kliens`-t és a Google-ágakat, ahogy a `kategoriak_ir`/`regresszio_ir` hívását ellenőrző meglévő tesztek. Ha nincs ilyen minta, a legegyszerűbb egy fókuszált teszt, amely a `futtato` esti ágán futtatja a származtatott-írás szakaszt és a mock `elmozdulas_ir` meghívódását állítja.)*

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_futtato.py -q -k elmozdulas`
Expected: FAIL (az `elmozdulas_ir` még nincs bekötve).

- [ ] **Step 3: Write minimal implementation**

A `trendfigyelo/futtato.py` tetején: `from trendfigyelo import elmozdulas` (a meglévő importokhoz). A `kategoriak.kategoriak_ir(docs_data_mappa)` (468. sor körül) és a `regresszio.regresszio_ir(...)` (501. sor) utáni származtatott-írás szakaszban, az ESTI ágon (ahol a `regresszio_ir` fut), tedd hozzá:

```python
            elmozdulas.elmozdulas_ir(docs_data_mappa)   # determinista szokatlan-elmozdulás (zéró Google-hívás)
```

Helyezd a `regresszio_ir` sikeres ága UTÁN (az `elmozdulas_szamit` a frissen kiírt `kulcsszo_regresszio.json`-t olvassa, ezért a `regresszio_ir` MÁR lefutott). Ha a regresszió kihagyódik/hibázik (üres sorozat), az `elmozdulas_ir` is kihagyható (a bemenet hiányában üres/parciális JSON-t ír — fail-soft: `try/except` köré, log + folytatás, a főfutás NE dőljön el emiatt).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_futtato.py -q`
Expected: PASS (a teljes futtató-suite + az új teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/futtato.py tests/test_futtato.py
git commit -m "feat(bovites): elmozdulas.json generalasa az esti futtato.py-ban (determinista, fail-soft)"
```

---

### Task 4: Halvány szokásos-sáv a meglévő kulcsszó-chartokon (`app.js`) + kapcsoló

**Files:**
- Modify: `docs/js/app.js` (band + `data-szokasos-sav` kapcsoló, a `data-nemlin` mintája)
- Modify: `docs/css/app.css` (ha a kapcsolóhoz kell)
- Test: `e2e/kulcsszo.spec.js` (kiterjesztés)

**Interfaces:**
- Consumes: `docs/data/elmozdulas.json` (`kulcsszavak.<szo>.sav.<intervallum>.{also,felso}`); a globális `egyesitett_reg`/kártya-infrastruktúra.
- Produces: a kártyákon egy halvány sáv dataset-pár (`fill:"-1"`), a `data-szokasos-sav` kapcsolóval BE/KI (default KI).

- [ ] **Step 1: Write the failing test** (`e2e/kulcsszo.spec.js` — a nemlin-kapcsoló tesztjének mintájára; mockold az `elmozdulas.json`-t, kapcsold be a sávot, és ellenőrizd, hogy a kártya megkapja a `data-szokasos-sav="true"`-t és rajzolódik a sáv-dataset)

```javascript
// e2e/kulcsszo.spec.js  (hozzáadás — igazodj a meglévő mock/route + vezérlő-kapcsoló mintához)
test("szokásos-sáv kapcsoló: BE → a kártyán data-szokasos-sav='true', a sáv-dataset rajzolódik", async ({ page }) => {
  // mock: a meglévő kulcsszó-mock mellé egy elmozdulas.json route a `sav` pontokkal egy kulcsszóra.
  // alap: a kapcsoló KI → nincs sáv; kattintás → BE → a kártya attribútuma true és +2 dataset (also/felso).
  // (A pontos selektorok a meglévő nemlin-kapcsoló teszt mintáját kövessék.)
});
```

*(Az implementer a `data-nemlin` kapcsoló meglévő e2e-tesztjét másolja mintának, `elmozdulas.json` route-tal.)*

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test e2e/kulcsszo.spec.js -g "szokásos-sáv"`
Expected: FAIL (nincs kapcsoló/sáv).

- [ ] **Step 3: Write minimal implementation**

A `data-nemlin` kapcsoló TELJES mintáját kövesd (az `app.js`-ben: `ATTR.nemlin`, a `vezerlok_render` kapcsolója, a kártyára tett attribútum, és a `chart_letrehoz` rajzolás). Konkrétan:

1. Új konstans a színekhez (a `PREDIKCIO_SAV_SZIN` közelébe):
```javascript
const SZOKASOS_SAV_SZIN = "rgba(120, 120, 120, 0.14)";   // halvány szürke „szokásos tartomány" sáv
```
2. Új `ATTR.szokasos_sav = "data-szokasos-sav"` + egy kapcsoló a `vezerlok_render`-ben (a nemlin-kapcsoló párjaként, default KI), amely a kártyákra teszi/leveszi a `data-szokasos-sav` attribútumot és újrarajzol.
3. Betöltés: az `elmozdulas.json`-t a kártya-infrastruktúra töltse be (a `BLOKKOK`/`json_betolt` mintájára), és a kártyához rendelje a szóhoz tartozó `sav` pontokat (az éppen mutatott intervallumhoz illesztve — a kártya `racs`/intervallum-választásával konzisztensen; ha az adott intervallumra nincs `sav`, a sáv kimarad — fail-soft).
4. A `chart_letrehoz` MINDKÉT ágában (teljes linear-x ÉS kompakt category-x), ha `kartya.getAttribute(ATTR.szokasos_sav) === "true"` és van a szóhoz `sav` az adott intervallumra, told be a predikció-sáv mintájára:
```javascript
      // szokásos-tartomány sáv (a szokatlan elmozdulás vizuális referenciája) — a predikció-sáv technikája
      ds.push({ data: sav_also, spanGaps: true, borderColor: "rgba(0,0,0,0)", borderWidth: 0, pointRadius: 0, fill: false });
      ds.push({ data: sav_felso, spanGaps: true, borderColor: "rgba(0,0,0,0)", borderWidth: 0, pointRadius: 0, fill: "-1", backgroundColor: SZOKASOS_SAV_SZIN });
```
ahol `sav_also`/`sav_felso` a `sav.also`/`sav.felso` pontjai a kártya x-tengelyéhez illesztve (a teljes ágban `{x:ms,y}`, a kompaktban a `racs.labels`-hez igazítva — a meglévő `horgony`/`vonal_xy` segédek mintájára). A tooltip változatlan (`datasetIndex===0` szűrő).

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test e2e/kulcsszo.spec.js` (a teljes fájl zöld, az új teszt is).
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/js/app.js docs/css/app.css e2e/kulcsszo.spec.js
git commit -m "feat(bovites): halvany szokasos-sav a kulcsszo-chartokon + data-szokasos-sav kapcsolo"
```

---

### Task 5: `ugyek.py` — korpusz + determinista életút-osztályozás

**Files:**
- Create: `trendfigyelo/ugyek.py`
- Test: `tests/test_ugyek.py`

**Interfaces:**
- Consumes: `docs/data/napok/<nap>.json` (szegmentált reggel/este `trendek[]` VAGY lapos `trendek[]`; trend: `kifejezes/volumen/temak/hirek`), `json_export`.
- Produces: `ugy_korpusz(docs_data, veg_nap, ablak_nap=30) -> dict`; `_eletut(kif) -> str`; `_mozgas(volumen_sor) -> str`. A Task 6-7 fogyasztja.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ugyek.py
import json
from pathlib import Path

from trendfigyelo import ugyek as u


def _nap(tmp_path, nap, kifejezesek):
    p = tmp_path / "napok" / f"{nap}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"este": {"trendek": [
        {"kifejezes": k, "volumen": v, "temak": tm, "hirek": hi} for (k, v, tm, hi) in kifejezesek]}},
        ensure_ascii=False), encoding="utf-8")


def test_korpusz_ablak_es_jelenlet(tmp_path):
    _nap(tmp_path, "2026-09-05", [("x", 50, [], [])])          # ablakon KÍVÜL (>30 nap a 10-07-től)
    _nap(tmp_path, "2026-09-20", [("tüntetés", 70, ["Politics"], [{"cim": "H1"}])])
    _nap(tmp_path, "2026-09-21", [("tüntetés", 90, [], [])])
    _nap(tmp_path, "2026-10-07", [("tüntetés", 40, [], [])])
    k = u.ugy_korpusz(str(tmp_path), "2026-10-07", ablak_nap=30)
    kif = {c["kifejezes"]: c for c in k["kifejezesek"]}
    assert "x" not in kif                                       # 2026-09-05 kiesett
    t = kif["tüntetés"]
    assert t["elso_nap"] == "2026-09-20" and t["utolso_nap"] == "2026-10-07"
    assert t["napok_szama"] == 3
    assert t["volumen_sor"][0] == {"nap": "2026-09-20", "max_volumen": 70}
    assert "Politics" in t["temak"] and "H1" in t["hirek"]
    assert k["ablak"]["nap"] == 30


def test_eletut_ujonnan_tartos_visszatero(tmp_path):
    veg = "2026-10-07"
    # újonnan: csak az utolsó pár napon, rövid span
    assert u._eletut({"elso_nap": "2026-10-05", "utolso_nap": "2026-10-07",
                      "napok": ["2026-10-05", "2026-10-06", "2026-10-07"]}, veg, 30) == "ujonnan_megfigyelt"
    # folyamatos: a napok nagy részén jelen
    sok = [f"2026-09-{d:02d}" for d in range(8, 31)] + ["2026-10-0%d" % d for d in range(1, 8)]
    assert u._eletut({"elso_nap": sok[0], "utolso_nap": "2026-10-07", "napok": sok}, veg, 30) == "folyamatosan_jelenlevo"
    # visszatérő: van hosszú szünet, majd újra
    assert u._eletut({"elso_nap": "2026-09-10", "utolso_nap": "2026-10-07",
                      "napok": ["2026-09-10", "2026-09-11", "2026-10-06", "2026-10-07"]}, veg, 30) == "visszatero"


def test_mozgas_iranya():
    assert u._mozgas([{"nap": "a", "max_volumen": 10}, {"nap": "b", "max_volumen": 20},
                      {"nap": "c", "max_volumen": 40}]) == "erosodo"
    assert u._mozgas([{"nap": "a", "max_volumen": 40}, {"nap": "b", "max_volumen": 20},
                      {"nap": "c", "max_volumen": 10}]) == "lecsengo"
    assert u._mozgas([{"nap": "a", "max_volumen": 30}, {"nap": "b", "max_volumen": 31},
                      {"nap": "c", "max_volumen": 29}]) == "stabil"
    assert u._mozgas([{"nap": "a", "max_volumen": 30}]) == "nem_megallapithato"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ugyek.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

```python
# trendfigyelo/ugyek.py
"""Ügy-életút a Bővítés fülhöz: gördülő 30-napos korpusz (determinista aggregálás) + LLM-csoportosítás
(Claude Opus) ügyekbe + determinista ügy-metrikák. A heti_ertekeles/havi_nlp mintája. Grounded:
a Python számol, az LLM csak csoportosít/nevez/sorol be a korpuszból."""
import glob
import json
import logging
import os
import time
from datetime import date, timedelta
from pathlib import Path

from trendfigyelo import json_export, szakpolitika

_log = logging.getLogger(__name__)

UJ_KUSZOB_NAP = 7          # 'újonnan megfigyelt': az első nap az ablak utolsó ennyi napján belül
FOLYAMATOS_ARANY = 0.5     # 'folyamatosan jelenlévő': a span napjainak legalább ennyi részén jelen
VISSZATERO_SZUNET = 3      # 'visszatérő': legalább ennyi napos szünet két jelenléti nap között


def _napok_kozott(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def _eletut(kif, veg_nap, ablak_nap):
    napok = sorted(kif.get("napok") or [])
    if not napok:
        return "egyeb"
    elso, utolso = napok[0], napok[-1]
    span = _napok_kozott(elso, utolso) + 1
    # visszatérő: van VISSZATERO_SZUNET-nél hosszabb rés két jelenléti nap között
    van_szunet = any(_napok_kozott(napok[i], napok[i + 1]) > VISSZATERO_SZUNET for i in range(len(napok) - 1))
    if van_szunet:
        return "visszatero"
    # újonnan: az első nap az ablak utolsó UJ_KUSZOB_NAP napján belül, és rövid span
    if _napok_kozott(elso, veg_nap) < UJ_KUSZOB_NAP and span <= UJ_KUSZOB_NAP:
        return "ujonnan_megfigyelt"
    # folyamatos: a span napjainak legalább FOLYAMATOS_ARANY részén jelen
    if span >= 2 and len(napok) / span >= FOLYAMATOS_ARANY:
        return "folyamatosan_jelenlevo"
    return "egyeb"


def _mozgas(volumen_sor):
    ertekek = [float(p.get("max_volumen") or 0) for p in (volumen_sor or [])]
    if len(ertekek) < 2:
        return "nem_megallapithato"
    elso_fel = ertekek[: len(ertekek) // 2] or ertekek[:1]
    masodik_fel = ertekek[len(ertekek) // 2:]
    d = (sum(masodik_fel) / len(masodik_fel)) - (sum(elso_fel) / len(elso_fel))
    bazis = max(1.0, sum(ertekek) / len(ertekek))
    if d / bazis > 0.2:
        return "erosodo"
    if d / bazis < -0.2:
        return "lecsengo"
    return "stabil"


def ugy_korpusz(docs_data, veg_nap, ablak_nap=30):
    """A [veg_nap-ablak_nap+1 .. veg_nap] ablak felkapott kifejezéseinek determinista aggregálása.
    Csak OLVAS (napok/*.json). Per kifejezés: jelenléti napok, első/utolsó nap, volumen-sor, témák, hírek."""
    kezdet = (date.fromisoformat(veg_nap) - timedelta(days=ablak_nap - 1)).isoformat()
    agg = {}
    for f in sorted(glob.glob(os.path.join(docs_data, "napok", "*.json"))):
        nap = Path(f).stem
        if len(nap) != 10 or nap < kezdet or nap > veg_nap:
            continue
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        trendek = []
        for szeg in ("reggel", "este"):
            trendek += (d.get(szeg) or {}).get("trendek", []) or []
        if not trendek:
            trendek = d.get("trendek") or []
        napi_max = {}
        for tr in trendek:
            kif = (tr.get("kifejezes") or "").strip()
            if not kif:
                continue
            a = agg.setdefault(kif, {"kifejezes": kif, "napok": set(), "volumen_map": {},
                                     "temak": set(), "hirek": []})
            a["napok"].add(nap)
            try:
                v = int(tr.get("volumen") or 0)
            except (TypeError, ValueError):
                v = 0
            napi_max[kif] = max(napi_max.get(kif, 0), v)
            a["temak"].update(tr.get("temak") or [])
            for h in (tr.get("hirek") or [])[:2]:
                cim = h.get("cim") if isinstance(h, dict) else h
                if cim and cim not in a["hirek"] and len(a["hirek"]) < 3:
                    a["hirek"].append(cim)
        for kif, v in napi_max.items():
            agg[kif]["volumen_map"][nap] = v
    kifejezesek = []
    for a in agg.values():
        napok = sorted(a["napok"])
        volumen_sor = [{"nap": n, "max_volumen": a["volumen_map"][n]} for n in napok]
        kif = {"kifejezes": a["kifejezes"], "elso_nap": napok[0], "utolso_nap": napok[-1],
               "napok": napok, "napok_szama": len(napok), "volumen_sor": volumen_sor,
               "temak": sorted(a["temak"]), "hirek": a["hirek"]}
        kif["eletut"] = _eletut(kif, veg_nap, ablak_nap)
        kif["mozgas"] = _mozgas(volumen_sor)
        kif["szakpolitika"] = szakpolitika.szakpolitika_besorol(kifejezes=a["kifejezes"], temak=kif["temak"])
        kifejezesek.append(kif)
    kifejezesek.sort(key=lambda c: (-c["napok_szama"], c["elso_nap"], c["kifejezes"]))
    return {"ablak": {"kezdet": kezdet, "veg": veg_nap, "nap": ablak_nap}, "kifejezesek": kifejezesek}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ugyek.py -q`
Expected: PASS (4 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/ugyek.py tests/test_ugyek.py
git commit -m "feat(bovites): ugyek.py korpusz + determinista eletut/mozgas osztalyozas (30 nap)"
```

---

### Task 6: `ugyek.py` — séma + prompt + streaming kliens + `ugy_elemez`

**Files:**
- Modify: `trendfigyelo/ugyek.py`
- Test: `tests/test_ugyek.py`

**Interfaces:**
- Consumes: `ugy_korpusz` (Task 5), `szakpolitika.SZAKPOLITIKA_SLUGOK`.
- Produces: `_valasz_sema()`, `RENDSZER_PROMPT_UGYEK`, `MODELL`, `MAX_TOKENS_UGYEK`, `_UgyKliens(sdk=None)`, `ugy_elemez(korpusz, kliens=None, ...)`. A Task 7 fogyasztja.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ugyek.py  (hozzáadás)
def test_valasz_sema_ugyek_enum_szakpolitika():
    s = u._valasz_sema()
    assert s["additionalProperties"] is False and s["required"] == ["ugyek"]
    item = s["properties"]["ugyek"]["items"]
    assert set(item["required"]) == {"nev", "kifejezesek", "szakpolitika", "osszefoglalo"}
    assert item["additionalProperties"] is False
    assert set(item["properties"]["szakpolitika"]["enum"]) == u.szakpolitika.SZAKPOLITIKA_SLUGOK


def test_rendszer_prompt_grounding():
    p = u.RENDSZER_PROMPT_UGYEK
    assert "ügy" in p.lower() and ("GROUNDING" in p or "nem talál" in p.lower())
    assert "csoportos" in p.lower()


class _Stream:
    def __init__(self, v): self._v = v
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self):
        import json as _j
        b = type("B", (), {"type": "text", "text": _j.dumps(self._v, ensure_ascii=False)})()
        return type("M", (), {"content": [b]})()


class _Sdk:
    def __init__(self, v): self.messages = self; self._v = v; self.n = 0
    def stream(self, **kw): self.n += 1; return _Stream(self._v)


def _valasz():
    return {"ugyek": [{"nev": "Üzemanyagárak", "kifejezesek": ["benzin ára", "gázolaj"],
                       "szakpolitika": "energia_rezsi", "osszefoglalo": "x"}]}


def test_ugy_elemez_mock():
    out = u.ugy_elemez({"kifejezesek": []}, kliens=u._UgyKliens(sdk=_Sdk(_valasz())))
    assert out["ugyek"][0]["nev"] == "Üzemanyagárak"


def test_ugy_elemez_bounded_retry():
    class _Buko:
        n = 0
        def uzenet(self, *a, **k):
            self.n += 1
            if self.n < 2:
                raise RuntimeError("int")
            return _valasz()
    assert u.ugy_elemez({}, kliens=_Buko(), alvo=lambda s: None)["ugyek"][0]["szakpolitika"] == "energia_rezsi"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ugyek.py -q -k "sema or prompt or elemez"`
Expected: FAIL (`AttributeError`).

- [ ] **Step 3: Write minimal implementation** (a `ugyek.py` végére — a `heti_ertekeles` `_HetiKliens`/`heti_elemez` mintája)

```python
def _valasz_sema():
    """Az ügy-csoportosítás strukturált sémája: ügyenként név + a korpuszból csoportosított
    kifejezések + szakpolitika (enum) + rövid összefoglaló. additionalProperties:False."""
    return {
        "type": "object", "additionalProperties": False, "required": ["ugyek"],
        "properties": {"ugyek": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["nev", "kifejezesek", "szakpolitika", "osszefoglalo"],
            "properties": {
                "nev": {"type": "string"},
                "kifejezesek": {"type": "array", "items": {"type": "string"}},
                "szakpolitika": {"type": "string", "enum": sorted(szakpolitika.SZAKPOLITIKA_SLUGOK)},
                "osszefoglalo": {"type": "string"},
            }}}},
    }


RENDSZER_PROMPT_UGYEK = (
    "Közügy-elemző vagy egy magyar Google Trends figyelő oldalhoz. A bemeneted egy 30 napos korpusz: "
    "a felkapott (trendelt) magyar keresőkifejezések, mindegyikhez determinista metrikákkal (hány napon "
    "volt jelen, mikor tűnt fel, az életút-besorolása és a mozgása, a Google-témacímkék, pár hír-cím). "
    "A feladatod a kifejezéseket JELENTÉS szerint ÜGYEKbe CSOPORTOSÍTANI — egy ügy ugyanazon közügy/téma "
    "köré gyűlő kifejezések halmaza (például ugyanannak az árnak vagy intézkedésnek a különböző "
    "megfogalmazásai). "
    "SZABÁLYOK, kivétel nélkül: "
    "(1) GROUNDING: kizárólag a korpuszban SZEREPLŐ kifejezéseket csoportosítod; új kifejezést SOHA nem "
    "találsz ki, és egy kifejezés legfeljebb EGY ügybe kerül. "
    "(2) Minden ügynek adj rövid, beszédes magyar NEVET, 1-2 mondatos magyar ÖSSZEFOGLALÓT (grounded, a "
    "korpusz adataiból), és sorold be a megadott szakpolitikai kategóriák (enum) EGYIKÉBE a jelentése "
    "és a témacímkéi alapján. "
    "(3) A prózába SOHA ne írj mezőnevet, JSON-t vagy technikai kulcsot; magyar, laikus olvasónak. "
    "(4) Rövid „–" gondolatjel. Ne minden kifejezés legyen külön ügy — a valódi összetartozókat vond össze; "
    "az egyedi, társíthatatlan kifejezés maradhat önálló ügy."
)

MODELL = "claude-opus-4-8"
MAX_TOKENS_UGYEK = 128000     # a 30-napos korpusz nagy lehet; a havi (128000) mintája, streaming kötelező

RETRY_PROBAK = 3
RETRY_BACKOFF_MP = (5, 20, 60)


class _UgyKliens:
    """Streaming Claude-kliens strukturált kimenettel (a heti_ertekeles._HetiKliens mintája)."""

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
            model=modell, max_tokens=MAX_TOKENS_UGYEK,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium",
                           "format": {"type": "json_schema", "schema": _valasz_sema()}},
            system=RENDSZER_PROMPT_UGYEK,
            messages=[{"role": "user", "content":
                       "Csoportosítsd az alábbi korpusz kifejezéseit ügyekbe (JSON). Csak ebből dolgozz:\n"
                       + json.dumps(korpusz, ensure_ascii=False)}],
        ) as folyam:
            valasz = folyam.get_final_message()
        szoveg = next(b.text for b in valasz.content if b.type == "text")
        return json.loads(szoveg)


def ugy_elemez(korpusz, kliens=None, modell=MODELL, probak=RETRY_PROBAK,
               backoff_mp=RETRY_BACKOFF_MP, alvo=None):
    """Bounded-retry Claude-hívás (a heti_elemez mintája); csak az utolsó bukás propagál."""
    kliens = kliens or _UgyKliens()
    alvo = alvo if alvo is not None else time.sleep
    utolso = None
    for i in range(probak):
        try:
            return kliens.uzenet(korpusz, modell)
        except Exception as e:   # noqa: BLE001 — intermittens API-hiba: bounded retry
            utolso = e
            if i + 1 < probak:
                _log.warning("FIGYELEM: az ügy-elemzés elhasalt (%s); újrapróba %d/%d %d mp múlva.",
                             e, i + 2, probak, backoff_mp[i])
                alvo(backoff_mp[i])
    raise utolso
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ugyek.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/ugyek.py tests/test_ugyek.py
git commit -m "feat(bovites): ugyek sema (enum szakpolitika) + prompt + streaming kliens + bounded-retry"
```

---

### Task 7: `ugyek.py` — grounding + ügy-összegzés + írás + `ugy_generalas`

**Files:**
- Modify: `trendfigyelo/ugyek.py`
- Test: `tests/test_ugyek.py`

**Interfaces:**
- Consumes: `ugy_korpusz` (Task 5), `ugy_elemez` (Task 6), `szakpolitika`, `json_export`.
- Produces: `grounding_validal(eredmeny, korpusz)`, `ugy_osszegez(eredmeny, korpusz)`, `ugy_ir`, `ugy_generalas(docs_data, veg_nap, keszult_iso, ablak_nap=30, kliens=None)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ugyek.py  (hozzáadás)
def test_grounding_kiszuri_a_nem_korpuszbeli_kifejezest_es_enumot():
    korpusz = {"kifejezesek": [{"kifejezes": "benzin ára"}, {"kifejezes": "gázolaj"}]}
    eredmeny = {"ugyek": [
        {"nev": "Üzemanyag", "kifejezesek": ["benzin ára", "KITALÁLT"], "szakpolitika": "energia_rezsi", "osszefoglalo": "x"},
        {"nev": "Üres", "kifejezesek": ["NINCS"], "szakpolitika": "egyeb", "osszefoglalo": "y"},
        {"nev": "Rossz enum", "kifejezesek": ["gázolaj"], "szakpolitika": "HOLDbazis", "osszefoglalo": "z"}]}
    out = u.grounding_validal(eredmeny, korpusz)
    nevek = [x["nev"] for x in out["ugyek"]]
    assert "Üres" not in nevek                                  # üres taggé vált → kiesik
    uzem = next(x for x in out["ugyek"] if x["nev"] == "Üzemanyag")
    assert uzem["kifejezesek"] == ["benzin ára"]                # KITALÁLT kiesett
    rossz = next(x for x in out["ugyek"] if x["nev"] == "Rossz enum")
    assert rossz["szakpolitika"] in u.szakpolitika.SZAKPOLITIKA_SLUGOK   # érvénytelen enum → determinista fallback


def test_ugy_osszegez_a_tagokbol():
    korpusz = {"kifejezesek": [
        {"kifejezes": "a", "napok": ["2026-10-01", "2026-10-02"], "elso_nap": "2026-10-01",
         "utolso_nap": "2026-10-02", "volumen_sor": [{"nap": "2026-10-01", "max_volumen": 10}], "eletut": "egyeb", "mozgas": "stabil"},
        {"kifejezes": "b", "napok": ["2026-10-02", "2026-10-03"], "elso_nap": "2026-10-02",
         "utolso_nap": "2026-10-03", "volumen_sor": [{"nap": "2026-10-03", "max_volumen": 20}], "eletut": "egyeb", "mozgas": "erosodo"}]}
    eredmeny = {"ugyek": [{"nev": "Ü", "kifejezesek": ["a", "b"], "szakpolitika": "egyeb", "osszefoglalo": "s"}]}
    out = u.ugy_osszegez(eredmeny, korpusz)
    ugy = out["ugyek"][0]
    assert ugy["elso_nap"] == "2026-10-01" and ugy["utolso_nap"] == "2026-10-03"
    assert ugy["napok_szama"] == 3                               # a,b napjainak uniója: 01,02,03
    assert ugy["eletut"] in ("ujonnan_megfigyelt", "folyamatosan_jelenlevo", "visszatero", "egyeb")
    assert [p["nap"] for p in ugy["idovonal"]] == ["2026-10-01", "2026-10-02", "2026-10-03"]


def test_ugy_generalas_ir_es_meta(tmp_path, monkeypatch):
    (tmp_path / "napok").mkdir(parents=True)
    (tmp_path / "napok" / "2026-10-07.json").write_text(
        json.dumps({"este": {"trendek": [{"kifejezes": "benzin ára", "volumen": 50, "temak": [], "hirek": []}]}}),
        encoding="utf-8")
    sdk = _Sdk({"ugyek": [{"nev": "Üzemanyag", "kifejezesek": ["benzin ára"],
                           "szakpolitika": "energia_rezsi", "osszefoglalo": "x"}]})
    out = u.ugy_generalas(str(tmp_path), "2026-10-07", "2026-10-08T07:00:00+00:00",
                          kliens=u._UgyKliens(sdk=sdk))
    assert out is not None
    mentve = json.loads((tmp_path / "ugyek.json").read_text(encoding="utf-8"))
    assert mentve["modell"] == "claude-opus-4-8" and mentve["ablak"]["veg"] == "2026-10-07"
    assert mentve["ugyek"][0]["nev"] == "Üzemanyag" and "idovonal" in mentve["ugyek"][0]


def test_ugy_generalas_fail_soft(tmp_path):
    (tmp_path / "napok").mkdir(parents=True)
    (tmp_path / "napok" / "2026-10-07.json").write_text(json.dumps({"este": {"trendek": []}}), encoding="utf-8")
    class _Buko:
        def uzenet(self, *a, **k): raise RuntimeError("tartós")
    assert u.ugy_generalas(str(tmp_path), "2026-10-07", "2026-10-08T07:00:00+00:00", kliens=_Buko()) is None
    assert not (tmp_path / "ugyek.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ugyek.py -q -k "grounding or osszegez or generalas"`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation** (a `ugyek.py` végére)

```python
def grounding_validal(eredmeny, korpusz):
    """Minden ügy `kifejezesek`-je a korpusz kifejezés-halmazára szűrve; üres taggé vált ügy kiesik;
    érvénytelen `szakpolitika` → determinista fallback a tagokból. Nem mutálja a bemenetet."""
    korp = {c.get("kifejezes") for c in (korpusz.get("kifejezesek") or [])}
    tema_map = {c.get("kifejezes"): (c.get("temak") or []) for c in (korpusz.get("kifejezesek") or [])}
    ugyek = []
    for ugy in (eredmeny.get("ugyek") or []):
        kif = [k for k in (ugy.get("kifejezesek") or []) if k in korp]
        if not kif:
            continue
        sp = ugy.get("szakpolitika")
        if sp not in szakpolitika.SZAKPOLITIKA_SLUGOK:
            temak = []
            for k in kif:
                temak += tema_map.get(k, [])
            sp = szakpolitika.szakpolitika_besorol(kifejezes=kif[0], temak=temak)
        ugyek.append({**ugy, "kifejezesek": kif, "szakpolitika": sp})
    return {**eredmeny, "ugyek": ugyek}


def ugy_osszegez(eredmeny, korpusz):
    """Minden ügy ÉLETÚT-metrikáját a TAGJAI (kifejezései) metrikáiból aggregálja (determinista):
    napok uniója, első/utolsó nap, napok_szama, életút/mozgás, idővonal (napi jelenlét)."""
    kmap = {c["kifejezes"]: c for c in (korpusz.get("kifejezesek") or [])}
    veg = (korpusz.get("ablak") or {}).get("veg")
    ablak_nap = (korpusz.get("ablak") or {}).get("nap") or 30
    ugyek = []
    for ugy in (eredmeny.get("ugyek") or []):
        tagok = [kmap[k] for k in ugy.get("kifejezesek", []) if k in kmap]
        napok = sorted({n for t in tagok for n in (t.get("napok") or [])})
        vol = {}
        for t in tagok:
            for p in (t.get("volumen_sor") or []):
                vol[p["nap"]] = vol.get(p["nap"], 0) + int(p.get("max_volumen") or 0)
        idovonal = [{"nap": n, "jelen": True, "ossz_volumen": vol.get(n, 0)} for n in napok]
        kif_agg = {"napok": napok, "elso_nap": napok[0] if napok else None,
                   "utolso_nap": napok[-1] if napok else None}
        ugyek.append({**ugy,
                      "elso_nap": kif_agg["elso_nap"], "utolso_nap": kif_agg["utolso_nap"],
                      "napok_szama": len(napok),
                      "eletut": _eletut(kif_agg, veg, ablak_nap) if napok else "egyeb",
                      "mozgas": _mozgas([{"max_volumen": p["ossz_volumen"]} for p in idovonal]),
                      "idovonal": idovonal})
    return {**eredmeny, "ugyek": ugyek}


def ugy_ir(docs_data, eredmeny):
    return json_export._ir_json(Path(docs_data) / "ugyek.json", eredmeny)


def ugy_generalas(docs_data, veg_nap, keszult_iso, ablak_nap=30, kliens=None):
    """Belépési pont: korpusz → Claude (fail-soft: tartós hibán None, NEM ír) → grounding →
    ügy-összegzés → meta → atomi írás. A keszult_iso/veg_nap PARAMÉTER (nincs argless now())."""
    korpusz = ugy_korpusz(docs_data, veg_nap, ablak_nap=ablak_nap)
    try:
        eredmeny = ugy_elemez(korpusz, kliens=kliens)
    except Exception as e:   # noqa: BLE001 — tartós API-hiba a bounded retry után: fail-soft
        _log.error("HIBA: az ügy-elemzés tartósan elhasalt (%s): %s", veg_nap, e)
        return None
    eredmeny = grounding_validal(eredmeny, korpusz)
    eredmeny = ugy_osszegez(eredmeny, korpusz)
    eredmeny["ablak"] = korpusz["ablak"]
    eredmeny["keszult"] = keszult_iso
    eredmeny["szamitva_utc"] = keszult_iso
    eredmeny["modell"] = MODELL
    ugy_ir(docs_data, eredmeny)
    return eredmeny
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ugyek.py -q`
Expected: PASS (az összes).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/ugyek.py tests/test_ugyek.py
git commit -m "feat(bovites): ugyek grounding + ugy-osszegzes (tagokbol) + atomi iras + generalas (fail-soft)"
```

---

### Task 8: `bovites_orzo.py` — napi őr

**Files:**
- Create: `trendfigyelo/bovites_orzo.py`
- Test: `tests/test_bovites_orzo.py`

**Interfaces:**
- Consumes: `seged.esti_nap`, `seged.most_utc`; az `ugyek.json` `szamitva_utc` mezője.
- Produces: `kell_generalni(docs_data, most) -> str|None` (a generálandó vég-nap = a logikai nap, vagy None, ha ma már kész), `main(argv)`.

Minta: `trendfigyelo/elemzes_orzo.py` / `heti_orzo.py` (NAPI idempotencia a `seged.esti_nap` logikai napon).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bovites_orzo.py
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from trendfigyelo import bovites_orzo as bo


def _bp(y, m, d, h):
    return datetime(y, m, d, h, tzinfo=ZoneInfo("Europe/Budapest")).astimezone(timezone.utc)


def test_kell_generalni_ha_meg_nincs(tmp_path):
    assert bo.kell_generalni(str(tmp_path), _bp(2026, 10, 7, 21)) == "2026-10-07"


def test_idempotencia_ma_mar_kesz(tmp_path):
    (tmp_path / "ugyek.json").write_text(json.dumps({"szamitva_utc": "2026-10-07T21:30:00+00:00"}), encoding="utf-8")
    assert bo.kell_generalni(str(tmp_path), _bp(2026, 10, 7, 22)) is None


def test_korabbi_keszult_ujra(tmp_path):
    (tmp_path / "ugyek.json").write_text(json.dumps({"szamitva_utc": "2026-10-06T21:30:00+00:00"}), encoding="utf-8")
    assert bo.kell_generalni(str(tmp_path), _bp(2026, 10, 7, 21)) == "2026-10-07"


def test_hajnali_az_elozo_naphoz(tmp_path):
    # 2026-10-08 02:00 BP → esti_nap = 2026-10-07 → azt generálja
    assert bo.kell_generalni(str(tmp_path), _bp(2026, 10, 8, 2)) == "2026-10-07"


def test_main_cli(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(bo.seged, "most_utc", lambda: _bp(2026, 10, 7, 21))
    assert bo.main([str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == "2026-10-07"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_bovites_orzo.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation**

```python
# trendfigyelo/bovites_orzo.py
"""A Bővítés (ügy-életút) NAPI idempotencia-őre (az elemzes_orzo/heti_orzo mintája). A bovites.yml
a 'Napi trendgyűjtés' (esti) befejezésére fut; a backupok ugyanazon a napon többször indíthatnak.
Egyszer/logikai nap (seged.esti_nap). Kimenet: a generálandó vég-nap (YYYY-MM-DD) vagy üres sor (skip)."""
import json
import sys
from datetime import datetime
from pathlib import Path

from . import seged


def _keszult_logikai_nap(docs_data):
    try:
        art = json.loads((Path(docs_data) / "ugyek.json").read_text(encoding="utf-8"))
        k = art.get("szamitva_utc") if isinstance(art, dict) else None
        return seged.esti_nap(datetime.fromisoformat(k)) if isinstance(k, str) else None
    except (OSError, ValueError, TypeError):
        return None


def kell_generalni(docs_data, most):
    """A generálandó vég-nap (a logikai nap), vagy None, ha ma (a logikai napon) már kész."""
    logikai = seged.esti_nap(most)
    if _keszult_logikai_nap(docs_data) == logikai:
        return None
    return logikai


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    docs_data = argv[0] if argv else "docs/data"
    nap = kell_generalni(docs_data, seged.most_utc())
    print(nap or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_bovites_orzo.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/bovites_orzo.py tests/test_bovites_orzo.py
git commit -m "feat(bovites): bovites_orzo.py - napi idempotencia-or (egyszer/logikai nap)"
```

---

### Task 9: `bovites.py` belépő

**Files:**
- Create: `bovites.py` (repo gyökér)
- Test: `tests/test_bovites_belepo.py`

**Interfaces:**
- Consumes: `ugyek.ugy_generalas`, `bovites_orzo` (nem kötelező itt), `seged.most_utc`.
- Produces: `main(argv) -> int` (0 siker / nincs teendő, 1 bukás).

Minta: `heti.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bovites_belepo.py
import bovites as be


def test_ures_argv(capsys):
    assert be.main([]) == 0
    assert "Nincs" in capsys.readouterr().out


def test_siker(monkeypatch):
    hiv = {}
    monkeypatch.setattr(be.ugyek, "ugy_generalas",
                        lambda dd, veg, ki, **kw: hiv.setdefault("v", (dd, veg, ki)) or {"ok": 1})
    assert be.main(["2026-10-07"]) == 0
    assert hiv["v"][1] == "2026-10-07"


def test_fail_soft(monkeypatch):
    monkeypatch.setattr(be.ugyek, "ugy_generalas", lambda *a, **k: None)
    assert be.main(["2026-10-07"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_bovites_belepo.py -q`
Expected: FAIL (`ModuleNotFoundError: bovites`).

- [ ] **Step 3: Write minimal implementation**

```python
# bovites.py  (repo gyökér — a heti.py mintája)
"""A Bővítés ügy-életút generáló belépője (a bovites.yml ezt hívja): a megadott vég-napra generál
(gördülő 30 nap, fail-soft). A kulcsot az ugyek._UgyKliens az ANTHROPIC_API_KEY env-ből olvassa."""
import sys

from trendfigyelo import seged, ugyek


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or not argv[0]:
        print("Nincs megadott vég-nap — nincs teendő.")
        return 0
    veg_nap = argv[0]
    keszult_iso = seged.most_utc().isoformat()
    eredmeny = ugyek.ugy_generalas("docs/data", veg_nap, keszult_iso)
    if eredmeny is None:
        print(f"Az ügy-elemzés generálása elhasalt ({veg_nap}).")
        return 1
    print(f"Ügy-elemzés kész: {veg_nap} ({len(eredmeny.get('ugyek', []))} ügy)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_bovites_belepo.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add bovites.py tests/test_bovites_belepo.py
git commit -m "feat(bovites): bovites.py belepo (fail-soft ugy-generalas)"
```

---

### Task 10: `.github/workflows/bovites.yml`

**Files:**
- Create: `.github/workflows/bovites.yml`
- Test: `tests/test_bovites_workflow.py`

**Interfaces:**
- Consumes: `trendfigyelo.bovites_orzo` (őr, stdlib, pip install előtt), `bovites.py`, `ANTHROPIC_API_KEY`.

Minta: `.github/workflows/heti.yml`, de a trigger a **„Napi trendgyűjtés"** (esti), és a commit CSAK `docs/data/ugyek.json`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bovites_workflow.py
from pathlib import Path
import yaml


def _wf():
    return yaml.safe_load(Path(".github/workflows/bovites.yml").read_text(encoding="utf-8"))


def test_trigger_a_napi_gyujtesre():
    wf = _wf()
    on = wf[True] if True in wf else wf["on"]
    assert on["workflow_run"]["workflows"] == ["Napi trendgyűjtés"]
    assert "workflow_dispatch" in on


def test_or_a_pip_install_elott_es_secret():
    sz = Path(".github/workflows/bovites.yml").read_text(encoding="utf-8")
    assert sz.index("trendfigyelo.bovites_orzo") < sz.index("pip install")
    assert "secrets.ANTHROPIC_API_KEY" in sz
    assert "python bovites.py" in sz


def test_commit_csak_az_ugyek_json():
    sz = Path(".github/workflows/bovites.yml").read_text(encoding="utf-8")
    assert "git add docs/data/ugyek.json" in sz
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_bovites_workflow.py -q`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation** (a `heti.yml` mintája; a kulcs-deltákkal)

```yaml
# .github/workflows/bovites.yml
name: Bővítés ügy-elemzés

on:
  workflow_run:
    workflows: ["Napi trendgyűjtés"]   # az esti teljes gyűjtés után
    types: [completed]
  workflow_dispatch:
    inputs:
      veg_nap:
        description: "Kézi teszt: vég-nap (YYYY-MM-DD) újragenerálása; üres = az őr dönt"
        required: false
        default: ""

permissions:
  contents: write

concurrency:
  group: bovites-futtatas
  cancel-in-progress: false

jobs:
  bovites:
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

      # Az őr a függőség-telepítés ELŐTT: CSAK stdlib (bovites_orzo/seged).
      - name: "Napi idempotencia-őr (a generálandó vég-nap, vagy üres = skip)"
        id: guard
        shell: bash
        env:
          KEZI_INPUT: ${{ github.event.inputs.veg_nap }}
        run: |
          KEZI="$KEZI_INPUT"
          if [ -n "$KEZI" ]; then
            echo "Kézi felülbírálás: $KEZI"
            echo "veg_nap=$KEZI" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          VEG="$(python -m trendfigyelo.bovites_orzo docs/data)"
          echo "Őr szerint generálandó vég-nap: '$VEG' (üres = ma nincs teendő)"
          echo "veg_nap=$VEG" >> "$GITHUB_OUTPUT"

      - name: Függőségek telepítése (csak generáláskor)
        if: steps.guard.outputs.veg_nap != ''
        run: pip install -r requirements.txt

      - name: Ügy-elemzés generálása
        if: steps.guard.outputs.veg_nap != ''
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          VEG_NAP: ${{ steps.guard.outputs.veg_nap }}
        run: |
          set -o pipefail
          python bovites.py "$VEG_NAP" 2>&1 | tee bovites.log

      - name: Változások commitolása (CSAK az ugyek.json, KÜLÖN commit)
        if: always() && github.ref == 'refs/heads/main' && steps.guard.outputs.veg_nap != ''
        env:
          VEG_NAP: ${{ steps.guard.outputs.veg_nap }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git pull --rebase --autostash || true
          git add docs/data/ugyek.json
          if git diff --staged --quiet; then
            echo "Nincs ügy-elemzés-változás — nincs commit."
          else
            git commit -m "adat: ügy-elemzés ($VEG_NAP, $(date -u +%Y-%m-%dT%H:%MZ))"
            git push
          fi

      - name: Artefakt (a log + az ugyek.json — mindig)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: bovites-${{ github.run_id }}
          retention-days: 14
          path: |
            bovites.log
            docs/data/ugyek.json
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_bovites_workflow.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/bovites.yml tests/test_bovites_workflow.py
git commit -m "feat(bovites): bovites.yml workflow (Napi gyujtesre, or a pip install elott, csak ugyek.json commit)"
```

---

### Task 11: `bovites.html` váz + nav 7. fül minden oldalon

**Files:**
- Create: `docs/bovites.html`
- Modify: `docs/elemzes.html`, `docs/heti.html`, `docs/havi.html`, `docs/trendek.html`, `docs/youtube.html`, `docs/adatokrol.html` (nav 7. fül)
- Modify: `e2e/menu.spec.js`

**Interfaces:**
- Produces: `docs/bovites.html` a `#bovites` main-nel (`#bovites-szuro` + `#bovites-elmozdulas` + `#bovites-ugyek` szekciók), `js/app.js` + `vendor/chartjs/chart.umd.js` + `js/bovites.js` betöltve. Nav 7 fül minden oldalon.

A nav sorrend MINDEN oldalon: `Napi Elemzések · Heti értékelés · Havi elemzés · Google Trendek · YouTube Trendek · Bővítés · Infó`. A `<a href="bovites.html">Bővítés</a>` a YouTube és az Infó KÖZÉ kerül; a `bovites.html`-en `class="aktiv" aria-current="page"`, máshol nem.

- [ ] **Step 1: Write the failing test** (`e2e/menu.spec.js`)

```javascript
// az első menü-teszt: 6 → 7, sorrend + Bővítés link; cím "7 fül"
test("menüsor: 7 fül, aktív = Google Trendek; a linkek helyesek + sorrend", async ({ page }) => {
  await page.goto("/trendek.html");
  await expect(page.locator("#fomenu a")).toHaveCount(7);
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Google Trendek");
  await expect(page.locator('#fomenu a[href="bovites.html"]')).toHaveText("Bővítés");
  await expect(page.locator("#fomenu a")).toHaveText(
    ["Napi Elemzések", "Heti értékelés", "Havi elemzés", "Google Trendek", "YouTube Trendek", "Bővítés", "Infó"]);
  await expect(page.locator("#labresz")).toBeAttached();
  await expect(page.locator("#adatokrol")).toHaveCount(0);
});

// a heti.html és havi.html meglévő toHaveText([...]) tömbjei → a 7-elemű lista.
// ÚJ teszt:
test("bovites.html: a fül betölt, a Bővítés menüpont aktív", async ({ page }) => {
  await page.goto("/bovites.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Bővítés");
  await expect(page.locator("#fomenu a")).toHaveText(
    ["Napi Elemzések", "Heti értékelés", "Havi elemzés", "Google Trendek", "YouTube Trendek", "Bővítés", "Infó"]);
  await expect(page.locator("#bovites")).toBeAttached();
});
```

(A meglévő `heti.html`/`havi.html`/`youtube.html` menü-tesztek `toHaveCount(6)` és a 6-elemű `toHaveText([...])` tömbjeit is frissítsd 7-re/7-eleműre — mindet, ahol a nav sorrendjét ellenőrzik.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx playwright test e2e/menu.spec.js`
Expected: FAIL (6 fül, nincs bovites.html).

- [ ] **Step 3: Write minimal implementation**

`docs/bovites.html` (a `heti.html` mintája):

```html
<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bővítés – Trendfigyelő</title>
  <link rel="stylesheet" href="css/app.css">
</head>
<body>
  <nav id="fomenu" aria-label="Fő menü">
    <a href="elemzes.html">Napi Elemzések</a>
    <a href="heti.html">Heti értékelés</a>
    <a href="havi.html">Havi elemzés</a>
    <a href="trendek.html">Google Trendek</a>
    <a href="youtube.html">YouTube Trendek</a>
    <a href="bovites.html" class="aktiv" aria-current="page">Bővítés</a>
    <a href="adatokrol.html">Infó</a>
  </nav>

  <header class="fejlec-doboz">
    <h1>Bővítés</h1>
    <p class="halvany" id="bovites-fejlec">Betöltés…</p>
  </header>

  <main id="bovites">
    <section id="bovites-szuro" aria-label="Szűrők"></section>
    <section id="bovites-elmozdulas" aria-label="Szokatlan változások" aria-live="polite"></section>
    <section id="bovites-ugyek" aria-label="Ügyek életútja" aria-live="polite"></section>
  </main>

  <footer id="labresz" aria-label="Lábléc"></footer>

  <script src="js/app.js"></script>
  <script src="vendor/chartjs/chart.umd.js"></script>
  <script src="js/bovites.js"></script>
</body>
</html>
```

A többi 6 oldalon a `#fomenu`-be a `<a href="youtube.html">YouTube Trendek</a>` UTÁN told be: `<a href="bovites.html">Bővítés</a>` (a saját oldalán kívül aktiv/aria-current NÉLKÜL).

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test e2e/menu.spec.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/bovites.html docs/elemzes.html docs/heti.html docs/havi.html docs/trendek.html docs/youtube.html docs/adatokrol.html e2e/menu.spec.js
git commit -m "feat(bovites): bovites.html vaz + nav 7. ful (Bovites) minden oldalon"
```

---

### Task 12: `bovites.js` — szokatlan-változások blokk + ügy-lista + idővonal

**Files:**
- Create: `docs/js/bovites.js`
- Modify: `docs/css/app.css` (`.bovites-*`)
- Create: `e2e/bovites.spec.js`

**Interfaces:**
- Consumes: `data/elmozdulas.json` (`kulcsszavak.<szo>.{szokatlan,irany,elteres,idotartam_pont,megbizhatosag,szakpolitika}`, `szokatlan_lista`), `data/ugyek.json` (`ugyek[].{nev,szakpolitika,eletut,mozgas,kifejezesek,elso_nap,utolso_nap,napok_szama,idovonal,osszefoglalo}`); a globális `Chart`.
- Produces: a `#bovites-elmozdulas` (F1 blokk) + `#bovites-ugyek` (F2 lista + idővonal) renderelése. (A `#bovites-szuro` szűrők a Task 13.)

- [ ] **Step 1: Write the failing test** (`e2e/bovites.spec.js`)

```javascript
const { test, expect } = require("@playwright/test");

const ELM = { szamitva_utc: "2026-10-07T18:00:00+00:00",
  kulcsszavak: { "benzin": { szokatlan: true, irany: "emelkedik", elteres: 3.0, elteres_nyers: 12.0,
      idotartam_pont: 5, idotartam_ota_utc: "2026-10-07T12:00:00+00:00", megbizhatosag: "magas",
      domen: "megelhetes", tipus: "szintmero", szakpolitika: "energia_rezsi", sav: {} } },
  szokatlan_lista: ["benzin"] };
const UGY = { szamitva_utc: "2026-10-07T21:00:00+00:00", ablak: { kezdet: "2026-09-08", veg: "2026-10-07", nap: 30 },
  modell: "claude-opus-4-8", ugyek: [
    { nev: "Üzemanyagárak", szakpolitika: "energia_rezsi", eletut: "folyamatosan_jelenlevo", mozgas: "erosodo",
      kifejezesek: ["benzin ára", "gázolaj"], elso_nap: "2026-09-10", utolso_nap: "2026-10-07", napok_szama: 12,
      idovonal: [{ nap: "2026-09-10", jelen: true, ossz_volumen: 40 }, { nap: "2026-10-07", jelen: true, ossz_volumen: 70 }],
      osszefoglalo: "Az üzemanyagárak tartósan foglalkoztatják a keresőket." }] };

async function mock(page) {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ json: ELM }));
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ json: UGY }));
}

test("bővítés: szokatlan-változások blokk + ügy-lista renderel", async ({ page }) => {
  await mock(page);
  await page.goto("/bovites.html");
  await expect(page.locator("#bovites-elmozdulas")).toContainText("benzin");
  await expect(page.locator("#bovites-elmozdulas")).toContainText("emelkedik");
  await expect(page.locator("#bovites-ugyek")).toContainText("Üzemanyagárak");
  await expect(page.locator("#bovites-ugyek")).toContainText("benzin ára");
  await expect(page.locator(".bovites-ugy")).toHaveCount(1);
});

test("bővítés: fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/bovites.html");
  await expect(page.locator("#bovites")).toContainText("nem érhető el");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx playwright test e2e/bovites.spec.js`
Expected: FAIL (nincs bovites.js).

- [ ] **Step 3: Write minimal implementation**

`docs/js/bovites.js` — a `heti.js` szerkezeti mintája. Töltse be a `data/elmozdulas.json`-t és a `data/ugyek.json`-t (fail-soft: ha mindkettő hiányzik → `#bovites` „nem érhető el"). Render:
- **`#bovites-elmozdulas`** (F1): a `szokatlan_lista` sorrendjében kártyák/sorok: kulcsszó, irány (emelkedik/csökken), eltérés (×szokásos), „mióta tart" (`idotartam_pont` pont), megbízhatóság, szakpolitika-címke. Üres lista → „Nincs szokatlan elmozdulás."
- **`#bovites-ugyek`** (F2): `.bovites-ugy` kártyák ügyenként: név, szakpolitika-címke, életút-címke (újonnan/folyamatos/visszatérő/egyéb → magyar), mozgás-címke (erősödő/stabil/lecsengő/nem megállapítható → magyar), a `kifejezesek` chipek, az `osszefoglalo`, és egy **idővonal** (a `idovonal` napi jelenlét-sávja — egyszerű HTML/CSS sáv vagy mini Chart.js). Rendezés default: `napok_szama` csökkenő (a Task 13 ad rendezés-váltót).

A magyar címkék (konstans map a fájlban): `eletut`: {ujonnan_megfigyelt:"Újonnan megfigyelt", folyamatosan_jelenlevo:"Folyamatosan jelen", visszatero:"Visszatérő", egyeb:"Egyéb"}; `mozgas`: {erosodo:"Erősödő", stabil:"Stabil", lecsengo:"Lecsengő", nem_megallapithato:"Nem megállapítható"}; `szakpolitika`: a 8 címke (a `szakpolitika.py` SZAKPOLITIKAK-jával egyező magyar nevek, JS-konstansként).

Fail-soft, NINCS `new Date()`. Az idővonal/mini-chart a vendorelt Chart.js-sel VAGY tiszta HTML/CSS sávval (az implementer választ; ha Chart.js, a `heti.js` chart-kezelésének mintája).

`docs/css/app.css`: `.bovites-*` stílusok (a `.heti-*` mintájára — kártyák, címkék, idővonal-sáv).

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test e2e/bovites.spec.js e2e/menu.spec.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/js/bovites.js docs/css/app.css e2e/bovites.spec.js
git commit -m "feat(bovites): bovites.js - szokatlan-valtozasok blokk + ugy-lista + idovonal + CSS + e2e"
```

---

### Task 13: Szűrők (szakpolitika / kategória / téma) + rendezés

**Files:**
- Modify: `docs/js/bovites.js`
- Modify: `docs/css/app.css`
- Modify: `e2e/bovites.spec.js`

**Interfaces:**
- Consumes: a Task 12 render + a betöltött `elmozdulas.json`/`ugyek.json`.
- Produces: a `#bovites-szuro` vezérlősor (szakpolitika-chipek + rendezés) ami szűri/rendezi MINDKÉT blokkot.

- [ ] **Step 1: Write the failing test** (`e2e/bovites.spec.js` — hozzáadás)

```javascript
test("bővítés: szakpolitika-szűrő szűkíti az ügy-listát", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ json: ELM }));
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ json: {
    ...UGY, ugyek: [UGY.ugyek[0],
      { nev: "Iskolakezdés", szakpolitika: "oktataspolitika", eletut: "visszatero", mozgas: "stabil",
        kifejezesek: ["iskola"], elso_nap: "2026-09-10", utolso_nap: "2026-10-01", napok_szama: 4,
        idovonal: [{ nap: "2026-09-10", jelen: true, ossz_volumen: 20 }], osszefoglalo: "y" }] } }));
  await page.goto("/bovites.html");
  await expect(page.locator(".bovites-ugy")).toHaveCount(2);
  await page.locator('.bovites-szuro-chip[data-szakpolitika="energia_rezsi"]').click();
  await expect(page.locator(".bovites-ugy")).toHaveCount(1);
  await expect(page.locator("#bovites-ugyek")).toContainText("Üzemanyagárak");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test e2e/bovites.spec.js -g "szakpolitika-szűrő"`
Expected: FAIL (nincs szűrő).

- [ ] **Step 3: Write minimal implementation**

A `#bovites-szuro`-ba egy vezérlősor: a 8 szakpolitika-chip (`.bovites-szuro-chip[data-szakpolitika=...]`, az „összes" alap) + egy rendezés-váltó az ügy-listához (frissesség / időtartam=napok_szama / mozgás). A chip-kattintás szűri a `#bovites-elmozdulas` sorokat (a `kulcsszavak.<szo>.szakpolitika` szerint) ÉS a `#bovites-ugyek` kártyákat (az `ugy.szakpolitika` szerint); az „összes" mindent mutat. (A legfelkapott-lista `app.js`-beli kategória-chip-szűrőjének mintája.) A rendezés a `.bovites-ugy` kártyákat rendezi újra. Opcionálisan Google-kategória/téma szűrő, ha az adat tartalmazza (a `temak`-ból) — ha nem triviális, elég a szakpolitika + rendezés ebben a taskban.

`docs/css/app.css`: `.bovites-szuro-chip` aktív/inaktív állapot.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test e2e/bovites.spec.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/js/bovites.js docs/css/app.css e2e/bovites.spec.js
git commit -m "feat(bovites): szakpolitika-szuro + rendezes a Bovites fulon"
```

---

### Task 14: Infó-oldal „A Bővítés fül" csoport

**Files:**
- Modify: `docs/adatokrol.html`
- Modify: `e2e/menu.spec.js`

**Interfaces:**
- Produces: egy új `.adat-csoport` „A Bővítés fül" leírással (elmozdulásfigyelő / ügy-életút / közpolitikai szűrő), a meglévő markup-mintát követve.

- [ ] **Step 1: Write the failing test** (`e2e/menu.spec.js` Infó-teszt)

```javascript
// az "Infó oldal" tesztben:
await expect(page.locator("#adatokrol .adat-doboz")).toHaveCount(31);  // +3 bővítés doboz (28→31)
await expect(page.locator("#adatokrol .adat-csoport")).toHaveCount(6); // +1 „A Bővítés fül"
await expect(page.locator("#adatokrol .adat-csoport")).toHaveText([
  "Google Trend adatok", "YouTube Trend adatok", "Az elemzés (napi AI-összefoglaló)",
  "A heti elemzés (heti AI-összefoglaló)", "A havi elemzés (havi AI-összefoglaló)", "A Bővítés fül"]);
await expect(page.locator("#adatokrol")).toContainText("szokatlan");
await expect(page.locator("#adatokrol")).toContainText("ügyek életútja");
```

(A pontos jelenlegi doboz/csoport-számot az implementer ellenőrizze a `docs/adatokrol.html`-ben a teszt írásakor — a heti-kör 28 dobozt / 5 csoportot hagyott; a +3/+1 ebből indul. Ha eltér, a VALÓS aktuális számból +3/+1.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx playwright test e2e/menu.spec.js -g "Infó"`
Expected: FAIL (a régi számok).

- [ ] **Step 3: Write minimal implementation**

A `docs/adatokrol.html`-ben az UTOLSÓ `.adat-csoport` (A havi elemzés) UTÁN egy új csoport, a MEGLÉVŐ markup-mintát követve (`h2.adat-csoport` + `section.adat-doboz` belső `h2`-vel — ahogy a havi csoport):

```html
<section class="adat-doboz"><h2>A Bővítés fül</h2></section>
<!-- FIGYELEM: a tényleges markup-mintát a docs/adatokrol.html meglévő csoportjaiból másold (h2.adat-csoport
     cím + 3 db section.adat-doboz). 3 doboz: -->
```
3 doboz tartalma:
- **Szokatlan változások (elmozdulásfigyelő):** egy keresőkifejezés a megszokotthoz képest emelkedik/csökken-e, mekkora az eltérés, **mióta tart**, és mennyire megbízható; a megszokott tartomány a Google Trendek fül chartjain halvány sávként kapcsolható be. A számokat Python számolja a meglévő mérésekből.
- **Ügyek életútja:** a felkapott keresések ügyekbe csoportosítva (a `claude-opus-4-8` modell kapcsolja össze a kifejezéseket); minden ügy besorolva: **egyszeri / folyamatosan jelen / visszatérő**, a mozgása **erősödő / stabil / lecsengő**. Gördülő 30 nap, naponta frissül.
- **Közpolitikai szűrő:** minden ügy és kulcsszó egy szakpolitikai területbe sorolva (8 kategória: szociál-, egészség-, oktatás-, gazdaság- és foglalkoztatás-, lakhatás-, energia/rezsi, közélet/közigazgatás, egyéb); a fülön szakpolitika szerint szűrhető.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test e2e/menu.spec.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/adatokrol.html e2e/menu.spec.js
git commit -m "feat(bovites): Info-oldal 'A Bovites ful' csoport (elmozdulas/ugy-eletut/szakpolitika)"
```

---

## Self-Review

**Spec coverage:** F1 → Task 2 (metrikák+sáv), Task 3 (futtato), Task 4 (chart-sáv), Task 12 (blokk). F2 → Task 5 (korpusz+osztályozás), Task 6 (séma+prompt+kliens), Task 7 (grounding+összegzés+generálás), Task 8/9/10 (őr/belépő/workflow), Task 12/13 (lista+idővonal). F3 → Task 1 (taxonómia), beépítve Task 2/7-be, Task 13 (szűrő). Fül+nav → Task 11; Infó → Task 14. ✓

**Placeholder scan:** a backend-taskok (1,2,5,6,7,8,9,10) teljes kóddal; a frontend-integrációs taskok (3,4,12,13,14) konkrét minta-referenciával + kulcs-kóddal (az app.js/bovites.js a meglévő fájlokat olvasva implementálandó — a teljes verbatim kód a 2500-soros app.js-hez találgatás lenne). A Task 3/4 teszt-vázának az implementer igazodik a meglévő fixture-mintához — ez tudatos (a `test_futtato`/`kulcsszo.spec` meglévő mintája a hiteles).

**Type consistency:** `elmozdulas.json` mezői (Task 2) ↔ app.js sáv (Task 4) ↔ bovites.js blokk (Task 12). `ugyek.json` mezői (Task 7 `ugy_osszegez` kimenet) ↔ bovites.js (Task 12/13). `szakpolitika` slug-ok (Task 1) ↔ enum (Task 6) ↔ besorolás (Task 2/7) ↔ frontend címkék (Task 12) — mind a 8 azonos slug. `veg_nap`/`ablak` végig egyezik. ✓

**Ordering ruling:** Task 1 (szakpolitika) ELŐBB, mert Task 2 és 5/7 importálja. Task 2 előbb mint Task 3 (a futtato az elmozdulas_ir-t hívja). Task 5→6→7 sorrend (ugyek.py épül). Task 11 (html) előbb mint Task 12/13 (bovites.js a vázra épül). Task 4 (app.js sáv) függ Task 2-től (elmozdulas.json alakja). — A pre-flight a végrehajtás előtt ezt megerősíti.

**Fájlnév-ütközés (heti-tanulság):** mind a tervezett ÚJ fájlnév (`bovites.html/js`, `elmozdulas.py`, `ugyek.py`, `szakpolitika.py`, `bovites_orzo.py`, `bovites.py`, `bovites.yml`, `test_*`, `e2e/bovites.spec.js`) ÜTKÖZÉSMENTES (ellenőrizve a spec-fázisban). Az `e2e/bovites.spec.js` ÚJ (nem létezett).
