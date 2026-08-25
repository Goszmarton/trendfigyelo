# YouTube-fül (társadalmi videó-igény-monitor) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Új „YouTube" fül a trendfigyelo-ban, ami 12 előre definiált szó napi/heti YouTube-keresési (videó-igény) görbéjét és trendjét mutatja HU-ra, a Google-kulcsszó-fül paritásában.

**Architecture:** A meglévő *másodlagos* gyűjtő-modellt tükrözzük `gprop='youtube'`-bal, külön kimenettel és külön (15:00 UTC) workflow-val. NINCS órás gyűjtés és NINCS lánc (mérésileg halott YouTube-on). A backend a `gyujt_egy_masodlagos` + `regresszio_masodlagos_szamit` függvényeket hasznosítja újra (utóbbit egy config-shimmel, a mag módosítása nélkül). A frontend egy új `youtube.html` + `youtube.js`, ami betölti az `app.js`-t és annak paraméter-vezérelt leaf-függvényeit (`nyers_ablak`, `racs_epit`, `kartya_letrehoz`, `chart_letrehoz`) újrahasználja — a Google-fül érintése nélkül.

**Tech Stack:** Python 3.12 + `trendspy` (backend), vanilla JS + Chart.js UMD (frontend), pytest + Playwright (teszt), GitHub Actions (ütemezés).

**Spec:** `docs/superpowers/specs/2026-08-25-youtube-ful-design.md`

## Global Constraints

- **SOROS suite:** pytest `.venv/bin/python -m pytest -p no:xdist -q`; Playwright `npx playwright test --workers=1`.
- **MUTÁCIÓ==1** fegyelem (a meglévő sentinel változatlan: `e2e/kulcsszo.spec.js:1230`).
- **KÜLÖN adat-commit**, `git add` NÉVVEL (sosem `-A`/`.`); a ROOT `ATADAS-2026-08-18.txt` SOHA nem add-elődik.
- **A pótolhatatlan órás ág CSAK OLVASVA** (`kulcsszo_nyers.json`, `kulcsszo_lanc.json` — a YouTube-ág SOHA nem indítja/írja).
- **Commit-üzenet magyar** + trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` és `Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN`.
- **Gyűjtési paraméterek (kőbe vésve):** geo=HU, `gprop='youtube'`, timeframe-ek `("today 3-m", "today 12-m")` — NINCS `now 7-d`. 12 szó, végleges mátrix.
- **Külön belépő:** a napi Google-pipeline (`python top_keresesek.py`) VÁLTOZATLAN; a YouTube-ág `python -m trendfigyelo.youtube`.
- **Meglévő zöld bázis (regresszió-őr):** 386 pytest + 130 Playwright; a Google-fül regressziómentes marad.

---

### Task 1: Config — `youtube:` szekció + 12 szó

**Files:**
- Modify: `trendfigyelo/config.py` (Config dataclass ~35-57, `betolt` ~153-199)
- Modify: `config.yaml` (új `youtube:` szekció a fájl végére)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Config.youtube_kulcsszavak: list[KulcsszoTetel]`, `Config.osszes_youtube_kulcsszo() -> list[KulcsszoTetel]`, `config._youtube_kulcsszavak_beolvas(nyers) -> list`.
- Consumes: meglévő `KulcsszoTetel = namedtuple("KulcsszoTetel", ["kifejezes","domen","tipus","racs"], defaults=("ora",))`, `TIPUSOK`, `RACSOK`, `KonfigHiba`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py  (a meglévő tesztek MELLÉ)
def test_youtube_szekcio_12_szo_es_racs():
    c = config.betolt("config.yaml")
    yt = c.osszes_youtube_kulcsszo()
    kifejezesek = [t.kifejezes for t in yt]
    assert len(yt) == 12
    assert kifejezesek == [
        "szorongás", "edzés", "meditáció", "befektetés", "bitcoin", "hírek",
        "magyar péter", "recept", "mese", "nyaralás", "tanulás", "klíma",
    ]
    racs = {t.kifejezes: t.racs for t in yt}
    assert racs["edzés"] == "nap" and racs["meditáció"] == "nap" and racs["recept"] == "nap"
    assert racs["mese"] == "nap" and racs["magyar péter"] == "nap"
    assert racs["szorongás"] == "het" and racs["bitcoin"] == "het" and racs["klíma"] == "het"
    # a Google-kulcsszavak ÉRINTETLENEK
    assert len(c.osszes_kulcsszo()) == 13

def test_youtube_szekcio_hianyzik_ures_lista():
    # ha nincs youtube: szekció, a betöltés NEM bukik, üres listát ad
    import yaml
    nyers = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    nyers.pop("youtube", None)
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        yaml.safe_dump(nyers, f, allow_unicode=True)
        utvonal = f.name
    try:
        c = config.betolt(utvonal)
        assert c.osszes_youtube_kulcsszo() == []
    finally:
        os.unlink(utvonal)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_config.py::test_youtube_szekcio_12_szo_es_racs -v`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'osszes_youtube_kulcsszo'`.

- [ ] **Step 3: Write minimal implementation**

`config.py` — a `Config` dataclass-hoz (a meglévő mezők után, a `trend_idosor_rekesz_max` mellé):

```python
    youtube_kulcsszavak: list = field(default_factory=list)  # [KulcsszoTetel, ...] a YouTube-fülhöz

    def osszes_youtube_kulcsszo(self):
        """A YouTube-fül követett szavai a beolvasás sorrendjében."""
        return list(self.youtube_kulcsszavak)
```

`config.py` — új parser a `_kulcsszavak_beolvas` mintájára, de OPCIONÁLIS (hiány → []):

```python
def _youtube_kulcsszavak_beolvas(nyers) -> list:
    tetelek = nyers.get("youtube")
    if tetelek is None:
        return []
    if not isinstance(tetelek, list) or not tetelek:
        raise KonfigHiba("A 'youtube' szekció (ha megadott) nem lehet üres — per-szó rekordok listája kell.")
    ki, latott = [], set()
    for i, t in enumerate(tetelek):
        if not isinstance(t, dict):
            raise KonfigHiba(f"youtube[{i}]: dict kell (kifejezes/domen/tipus/racs)")
        kifejezes = t.get("kifejezes")
        domen = t.get("domen")
        tipus = t.get("tipus")
        if not (isinstance(kifejezes, str) and kifejezes.strip()):
            raise KonfigHiba(f"youtube[{i}]: 'kifejezes' nem üres string kell")
        if tipus not in TIPUSOK:
            raise KonfigHiba(f"youtube[{i}] ({kifejezes!r}): 'tipus' ∈ {sorted(TIPUSOK)} kell")
        racs = t.get("racs", "ora")
        if racs not in RACSOK:
            raise KonfigHiba(f"youtube[{i}] ({kifejezes!r}): 'racs' ∈ {sorted(RACSOK)} kell")
        if kifejezes in latott:
            raise KonfigHiba(f"youtube: duplikált kifejezes: {kifejezes!r}")
        latott.add(kifejezes)
        ki.append(KulcsszoTetel(kifejezes, domen, tipus, racs))
    return ki
```

`config.py` — a `betolt`-ban (a `kulcsszavak = _kulcsszavak_beolvas(nyers)` után) add hozzá:

```python
    youtube_kulcsszavak = _youtube_kulcsszavak_beolvas(nyers)
```

és a `Config(...)` konstruktor-hívásba (a `kulcsszavak=kulcsszavak` mellé):

```python
        youtube_kulcsszavak=youtube_kulcsszavak,
```

`config.yaml` — a fájl végére:

```yaml
# YouTube-fül (Phase 4, 2026-08-25): társadalmi videó-igény-monitor, gprop=youtube, geo=HU.
# A racs a MEGJELENÍTÉSI alapértelmezés (napi/heti); a gyűjtés MINDKÉT timeframe-et (3-m + 12-m) bekéri.
# tipus mindenhol szintmero (a trend minden szóra számolódik). A domének ékezet nélküliek.
youtube:
  - {kifejezes: "szorongás",    domen: egeszseg,  tipus: szintmero, racs: het}
  - {kifejezes: "edzés",        domen: egeszseg,  tipus: szintmero, racs: nap}
  - {kifejezes: "meditáció",    domen: egeszseg,  tipus: szintmero, racs: nap}
  - {kifejezes: "befektetés",   domen: penzugy,   tipus: szintmero, racs: het}
  - {kifejezes: "bitcoin",      domen: penzugy,   tipus: szintmero, racs: het}
  - {kifejezes: "hírek",        domen: kozelet,   tipus: szintmero, racs: het}
  - {kifejezes: "magyar péter", domen: kozelet,   tipus: szintmero, racs: nap}
  - {kifejezes: "recept",       domen: haztartas, tipus: szintmero, racs: nap}
  - {kifejezes: "mese",         domen: csalad,    tipus: szintmero, racs: nap}
  - {kifejezes: "nyaralás",     domen: szabadido, tipus: szintmero, racs: het}
  - {kifejezes: "tanulás",      domen: tanulas,   tipus: szintmero, racs: het}
  - {kifejezes: "klíma",        domen: otthon,    tipus: szintmero, racs: het}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_config.py -v`
Expected: PASS (mindkét új teszt + a meglévők).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/config.py config.yaml tests/test_config.py
git commit  # üzenet: "feat(youtube-config): youtube: szekció (12 szó, 8 kosár) + osszes_youtube_kulcsszo (opcionális, hiány→[])"  + trailer
```

---

### Task 2: `gyujt_egy_masodlagos` — `gprop` + `ag` paraméter

**Files:**
- Modify: `trendfigyelo/kulcsszavak.py:215-241`
- Test: `tests/test_kulcsszavak.py`

**Interfaces:**
- Produces: `gyujt_egy_masodlagos(kliens, config, tetel, most, timeframe, gprop="", ag="kulcsszo_masodlagos") -> dict|None` — a `gprop` a `kliens.hivas`-nak továbbítva, az `ag` a Kliens-számláló/napló címkéje.
- Consumes: meglévő `kliens.hivas(ag, fn, *args, **kwargs)` (a kwargs `interest_over_time`-ba megy).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_kulcsszavak.py
from types import SimpleNamespace
from trendfigyelo import kulcsszavak

class _RogzitoKliens:
    """A hivas() argumentumait rögzíti; egy fabrikált df-et ad vissza."""
    def __init__(self, df):
        self._df = df
        self.hivasok = []
        self.tr = SimpleNamespace(interest_over_time="IOT_SENTINEL")
    def hivas(self, ag, fn, *args, **kwargs):
        self.hivasok.append({"ag": ag, "fn": fn, "args": args, "kwargs": kwargs})
        return self._df

def _napi_df():
    import pandas as pd
    from datetime import datetime, timezone, timedelta
    kezd = datetime(2026, 5, 20, tzinfo=timezone.utc)
    idx = [kezd + timedelta(days=i) for i in range(92)]
    return pd.DataFrame({"edzés": [40]*92, "isPartial": [False]*91 + [True]}, index=idx)

def test_gyujt_egy_masodlagos_gprop_es_ag_tovabbitas():
    cfg = SimpleNamespace(geo="HU")
    tetel = SimpleNamespace(kifejezes="edzés", domen="egeszseg", tipus="szintmero", racs="nap")
    most = __import__("datetime").datetime(2026, 8, 20, 9, tzinfo=__import__("datetime").timezone.utc)
    k = _RogzitoKliens(_napi_df())
    rek = kulcsszavak.gyujt_egy_masodlagos(k, cfg, tetel, most, "today 3-m",
                                           gprop="youtube", ag="youtube")
    assert rek is not None and rek["timeframe"] == "today 3-m"
    hiv = k.hivasok[0]
    assert hiv["ag"] == "youtube"
    assert hiv["kwargs"]["gprop"] == "youtube"
    assert hiv["kwargs"]["geo"] == "HU" and hiv["kwargs"]["timeframe"] == "today 3-m"

def test_gyujt_egy_masodlagos_alap_gprop_ures_es_ag_valtozatlan():
    # REGRESSZIÓ-ŐR: alapból a Google-viselkedés — ag="kulcsszo_masodlagos", gprop=""
    cfg = SimpleNamespace(geo="HU")
    tetel = SimpleNamespace(kifejezes="edzés", domen="egeszseg", tipus="szintmero", racs="nap")
    most = __import__("datetime").datetime(2026, 8, 20, 9, tzinfo=__import__("datetime").timezone.utc)
    k = _RogzitoKliens(_napi_df())
    kulcsszavak.gyujt_egy_masodlagos(k, cfg, tetel, most, "today 3-m")
    hiv = k.hivasok[0]
    assert hiv["ag"] == "kulcsszo_masodlagos"
    assert hiv["kwargs"]["gprop"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_kulcsszavak.py::test_gyujt_egy_masodlagos_gprop_es_ag_tovabbitas -v`
Expected: FAIL — `TypeError: gyujt_egy_masodlagos() got an unexpected keyword argument 'gprop'`.

- [ ] **Step 3: Write minimal implementation**

`kulcsszavak.py` — a `gyujt_egy_masodlagos` szignatúra + a `kliens.hivas` hívás:

```python
def gyujt_egy_masodlagos(kliens, config, tetel, most, timeframe, gprop="", ag="kulcsszo_masodlagos"):
    """EGY nap/het szó másodlagos (RACS_IDOKERET szerinti) lekérdezése → egy rekord vagy None.

    `gprop`: Google-tulajdon ('' = web [Google-viselkedés bájt-azonos], 'youtube' = YouTube).
    `ag`: a Kliens-számláló/napló ág-címkéje (külön a YouTube-nál).
    """
    from .config import TIMEFRAME_RACS
    df = kliens.hivas(
        ag, kliens.tr.interest_over_time,
        [tetel.kifejezes], geo=config.geo, timeframe=timeframe, gprop=gprop)
    if df is None or len(df) == 0:
        return None
    # ... a törzs VÁLTOZATLAN (oszlop, _nyers_sorozat, racs/timeframe/lekerdezes_utc, masodlagos_alak_ok) ...
```

(A függvény többi sora érintetlen.)

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_kulcsszavak.py -v`
Expected: PASS (mindkét új teszt + a meglévők).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/kulcsszavak.py tests/test_kulcsszavak.py
git commit  # "feat(youtube-gyujt): gyujt_egy_masodlagos gprop+ag paraméter (alap ''/'kulcsszo_masodlagos' → Google bájt-azonos)"  + trailer
```

---

### Task 3: `nyers_kimenet.ir_youtube` — a `youtube_nyers.json` írása

**Files:**
- Modify: `trendfigyelo/nyers_kimenet.py` (új `ir_youtube` az `ir_masodlagos` mellé)
- Test: `tests/test_youtube_kimenet.py` (ÚJ)

**Interfaces:**
- Produces: `ir_youtube(docs_data, sorozatok: dict, megtartott_db: int = 3) -> Path` — `docs/data/youtube_nyers.json`, `{"kulcsszavak": {kif: [rek,...]}}`, retenció szó×timeframe-enként; atomi írás.
- Consumes: meglévő `ervenyes_masodlagos_rekord`, `_rendezett`, `_aware_dt`, `_MIN_DT`, `seged.atomi_ir_szoveg`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_youtube_kimenet.py  (ÚJ)
import json
from trendfigyelo import nyers_kimenet
from trendfigyelo.nyers_kimenet import ervenyes_masodlagos_rekord

def _pont(iso, ertek=5, reszleges=False):
    return {"idopont_utc": iso, "ertek": ertek, "reszleges": reszleges}

def _rek(kulcsszo="edzés", racs="nap", timeframe="today 3-m",
         kezd="2026-05-16T00:00:00+00:00", veg="2026-08-13T00:00:00+00:00",
         lekerdezes="2026-08-13T09:00:00+00:00"):
    return {"kulcsszo": kulcsszo, "racs": racs, "timeframe": timeframe,
            "lekerdezes_utc": lekerdezes, "ablak_kezdet_utc": kezd, "ablak_veg_utc": veg,
            "pontok": [_pont(kezd, 5, False), _pont(veg, 6, True)]}

def _read(mappa):
    return json.loads((mappa / "youtube_nyers.json").read_text(encoding="utf-8"))["kulcsszavak"]

def test_ir_youtube_ir_es_megorzi_a_mezoket(tmp_path):
    p = nyers_kimenet.ir_youtube(tmp_path, {"edzés": _rek(racs="nap", timeframe="today 3-m")})
    assert p.name == "youtube_nyers.json"
    rekk = _read(tmp_path)["edzés"]
    assert len(rekk) == 1 and rekk[0]["timeframe"] == "today 3-m" and rekk[0]["racs"] == "nap"
    assert ervenyes_masodlagos_rekord(rekk[0]) == []

def test_ir_youtube_retencio_timeframe_kulon(tmp_path):
    for i in range(3):
        nyers_kimenet.ir_youtube(tmp_path, {"edzés": _rek(
            timeframe="today 3-m", racs="nap", lekerdezes=f"2026-08-1{i}T09:00:00+00:00")})
        nyers_kimenet.ir_youtube(tmp_path, {"edzés": _rek(
            timeframe="today 12-m", racs="het", lekerdezes=f"2026-08-1{i}T09:00:00+00:00")})
    rekk = _read(tmp_path)["edzés"]
    tf = {}
    for r in rekk:
        tf[r["timeframe"]] = tf.get(r["timeframe"], 0) + 1
    assert tf == {"today 3-m": 3, "today 12-m": 3}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_youtube_kimenet.py -v`
Expected: FAIL — `AttributeError: module 'trendfigyelo.nyers_kimenet' has no attribute 'ir_youtube'`.

- [ ] **Step 3: Write minimal implementation**

`nyers_kimenet.py` — az `ir_masodlagos` mintájára, de a karantén-örökség NÉLKÜL (YouTube-nak nincs visszaolvasott legacy-je):

```python
def ir_youtube(docs_data, sorozatok: dict, megtartott_db: int = 3) -> Path:
    """A youtube_nyers.json: szó × timeframe (3-m/12-m) YouTube-sorozatok, retencióval.
    Az ir_masodlagos rekord-sémáját és validációját (ervenyes_masodlagos_rekord) újrahasználja."""
    fajl = Path(docs_data) / "youtube_nyers.json"
    if fajl.exists():
        adat = json.loads(fajl.read_text(encoding="utf-8"))
    else:
        adat = {"kulcsszavak": {}}
    kulcsszavak = adat.setdefault("kulcsszavak", {})

    for kifejezes, rek in sorozatok.items():
        rendezett = _rendezett(rek)
        hibak = ervenyes_masodlagos_rekord(rendezett)
        if hibak:
            raise ValueError(f"{kifejezes}: érvénytelen friss YouTube-rekord: {hibak}")
        kulcsszavak.setdefault(kifejezes, []).append(rendezett)

    for kif in list(kulcsszavak):
        tf_csoport = {}
        for r in kulcsszavak[kif]:
            tf_csoport.setdefault(r.get("timeframe"), []).append(r)
        megtartott = []
        for rekk in tf_csoport.values():
            megtartott.extend(sorted(rekk, key=lambda r: _aware_dt(r.get("lekerdezes_utc")) or _MIN_DT,
                                     reverse=True)[:megtartott_db])
        kulcsszavak[kif] = megtartott

    seged.atomi_ir_szoveg(fajl, json.dumps(adat, ensure_ascii=False, indent=2))
    return fajl
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_youtube_kimenet.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/nyers_kimenet.py tests/test_youtube_kimenet.py
git commit  # "feat(youtube-kimenet): ir_youtube (youtube_nyers.json, szó×timeframe retenció, atomi)"  + trailer
```

---

### Task 4: `regresszio_ir_youtube` + shim-alapú újrahasznosítás

**Files:**
- Modify: `trendfigyelo/regresszio.py` (egyetlen új thin író)
- Test: `tests/test_youtube_regresszio.py` (ÚJ)

**Interfaces:**
- Produces: `regresszio_ir_youtube(docs_data, adat) -> Path` — `docs/data/youtube_regresszio.json`.
- Consumes: meglévő `regresszio_masodlagos_szamit(masodlagos_nyers, tortenet, config, szamitva_utc)` VÁLTOZATLANUL, egy `SimpleNamespace` config-shimmel (`osszes_kulcsszo` → YouTube-tételek, `modszertan_valtas=None`) és üres tortenet-tel (`{"napok": []}`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_youtube_regresszio.py  (ÚJ)
import json
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
from trendfigyelo import regresszio

def _het_pontok(n, ertek=40):
    kezd = datetime(2025, 8, 20, tzinfo=timezone.utc)
    return [{"idopont_utc": (kezd + timedelta(weeks=i)).isoformat(),
             "ertek": ertek, "reszleges": (i == n - 1)} for i in range(n)]

def _yt_shim():
    tetel = [SimpleNamespace(kifejezes="klíma", domen="otthon", tipus="szintmero", racs="het")]
    return SimpleNamespace(modszertan_valtas=None, osszes_kulcsszo=lambda: list(tetel))

def test_youtube_regresszio_szamit_es_ir(tmp_path):
    yt_nyers = {"kulcsszavak": {"klíma": [{
        "kulcsszo": "klíma", "racs": "het", "timeframe": "today 12-m",
        "lekerdezes_utc": "2026-08-13T09:00:00+00:00",
        "ablak_kezdet_utc": _het_pontok(53)[0]["idopont_utc"],
        "ablak_veg_utc": _het_pontok(53)[-1]["idopont_utc"],
        "pontok": _het_pontok(53)}]}}
    adat = regresszio.regresszio_masodlagos_szamit(yt_nyers, {"napok": []}, _yt_shim(), "T")
    sz = adat["kulcsszavak"]["klíma"]
    assert sz["racs"] == "het" and sz["domen"] == "otthon" and sz["aktiv"] is True
    iv = sz["intervallumok"]
    assert "irany" in iv["1_ev"] and iv["1_ev"]["ervenyes"] is True
    # heti szó rövid ablaka strukturálisan érvénytelen (kevés heti pont)
    assert iv["1_het"]["ervenyes"] is False
    p = regresszio.regresszio_ir_youtube(tmp_path, adat)
    assert p.name == "youtube_regresszio.json"
    vissza = json.loads(p.read_text(encoding="utf-8"))
    assert "klíma" in vissza["kulcsszavak"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_youtube_regresszio.py -v`
Expected: FAIL — `AttributeError: module 'trendfigyelo.regresszio' has no attribute 'regresszio_ir_youtube'`.

- [ ] **Step 3: Write minimal implementation**

`regresszio.py` — a `regresszio_ir_masodlagos` mellé:

```python
def regresszio_ir_youtube(docs_data, adat) -> Path:
    return json_export._ir_json(Path(docs_data) / "youtube_regresszio.json", adat)
```

(A számoló `regresszio_masodlagos_szamit` VÁLTOZATLAN — a YouTube-modul [Task 5] hívja a shimmel.)

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_youtube_regresszio.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/regresszio.py tests/test_youtube_regresszio.py
git commit  # "feat(youtube-reg): regresszio_ir_youtube + a másodlagos-számoló shim-újrahasznosítása (mag változatlan)"  + trailer
```

---

### Task 5: `trendfigyelo/youtube.py` — a gyűjtő-modul (belépő)

**Files:**
- Create: `trendfigyelo/youtube.py`
- Test: `tests/test_youtube_ag.py` (ÚJ)

**Interfaces:**
- Produces: `futtat_youtube(config, docs_data, most, kliens=None) -> dict` (`{"letoltve": [(szó,tf,pont)], "eldobva": [(szó,tf)]}`), `main(argv=None)`, `python -m trendfigyelo.youtube`.
- Consumes: `kulcsszavak.gyujt_egy_masodlagos(..., gprop="youtube", ag="youtube")` (Task 2), `nyers_kimenet.ir_youtube` (Task 3), `regresszio.regresszio_masodlagos_szamit`+`regresszio.regresszio_ir_youtube` (Task 4), `naplo.naplo_ir`, `config.MASODLAGOS_TIMEFRAMEK`, `Kliens`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_youtube_ag.py  (ÚJ)
import json
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
import pandas as pd
from trendfigyelo import youtube

_MOST = datetime(2026, 8, 20, 9, tzinfo=timezone.utc)

def _config():
    yt = [SimpleNamespace(kifejezes="edzés", domen="egeszseg", tipus="szintmero", racs="nap"),
          SimpleNamespace(kifejezes="klíma", domen="otthon", tipus="szintmero", racs="het")]
    return SimpleNamespace(geo="HU", max_probak=4, naplo_max_sor=2000, modszertan_valtas=None,
                           osszes_youtube_kulcsszo=lambda: list(yt),
                           osszes_kulcsszo=lambda: list(yt))

def _df(kif, tf):
    # a span a timeframe VÁRT spanjéhez illik (masodlagos_alak_ok: 0,85–1,2×), a vég _MOST előtt
    if tf == "today 3-m":                       # ~92 nap, napi rács, vége 2026-08-19
        veg = datetime(2026, 8, 19, tzinfo=timezone.utc)
        idx = [veg - timedelta(days=i) for i in range(92)][::-1]
    else:                                       # ~53 hét, heti rács, vége 2026-08-19
        veg = datetime(2026, 8, 19, tzinfo=timezone.utc)
        idx = [veg - timedelta(weeks=i) for i in range(53)][::-1]
    return pd.DataFrame({kif: [40]*len(idx), "isPartial": [False]*(len(idx)-1) + [True]}, index=idx)

class _FakeKliens:
    def __init__(self):
        self.szam = 0
        self.tr = SimpleNamespace(interest_over_time=None)
    def hivas(self, ag, fn, szavak, geo, timeframe, gprop):
        self.szam += 1
        assert gprop == "youtube" and ag == "youtube"
        return _df(szavak[0], timeframe)
    def osszes_hivas(self):
        return self.szam

def test_futtat_youtube_24_cella_ir_nyers_es_regressziot(tmp_path):
    k = _FakeKliens()
    ki = youtube.futtat_youtube(_config(), tmp_path, _MOST, kliens=k)
    # 2 szó × 2 timeframe = 4 cella (a teszt-configban 2 szó)
    assert len(ki["letoltve"]) == 4
    nyers = json.loads((tmp_path / "youtube_nyers.json").read_text(encoding="utf-8"))["kulcsszavak"]
    assert set(nyers) == {"edzés", "klíma"}
    reg = json.loads((tmp_path / "youtube_regresszio.json").read_text(encoding="utf-8"))["kulcsszavak"]
    assert "edzés" in reg and "klíma" in reg

def test_futtat_youtube_nem_indit_mas_agat(tmp_path, monkeypatch):
    from trendfigyelo import felkapott, idosorok, kulcsszavak, lanc, nyers_kimenet
    tiltott = []
    def tilt(nev):
        return lambda *a, **k: tiltott.append(nev) or (_ for _ in ()).throw(AssertionError(nev))
    monkeypatch.setattr(felkapott, "gyujt_api", tilt("felkapott.gyujt_api"), raising=False)
    monkeypatch.setattr(felkapott, "gyujt_rss", tilt("felkapott.gyujt_rss"), raising=False)
    monkeypatch.setattr(idosorok, "gyujt", tilt("idosorok.gyujt"), raising=False)
    monkeypatch.setattr(kulcsszavak, "gyujt", tilt("kulcsszavak.gyujt"), raising=False)
    monkeypatch.setattr(lanc, "frissit_lanc", tilt("lanc.frissit_lanc"), raising=False)
    monkeypatch.setattr(nyers_kimenet, "ir_gordulo", tilt("nyers_kimenet.ir_gordulo"), raising=False)
    youtube.futtat_youtube(_config(), tmp_path, _MOST, kliens=_FakeKliens())
    assert tiltott == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_youtube_ag.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'trendfigyelo.youtube'`.

- [ ] **Step 3: Write minimal implementation**

`trendfigyelo/youtube.py` (ÚJ) — a `masodlagos_only.py` mintájára:

```python
"""YouTube-ág belépő — CSAK a YouTube-szavak (gprop=youtube) 3-m+12-m gyűjtése + regresszió.

KRITIKUS INVARIÁNS: SEMMILYEN más ágat NEM indít (se primer órás, se idosor/felkapott/rss,
se lánc, se ir_gordulo). A pótolhatatlan Google-órás adat érintetlen. Saját, SZŰK plafon.
Használat: python -m trendfigyelo.youtube   (a .github/workflows/youtube.yml futtatja).
"""
import argparse
from pathlib import Path
from types import SimpleNamespace

from . import kulcsszavak, nyers_kimenet, regresszio, naplo, seged
from .config import MASODLAGOS_TIMEFRAMEK, betolt
from .kliens import Kliens, AgFeladva, PlafonTullepve

GPROP = "youtube"
AG = "youtube"


def _reg_shim(config):
    """Config-nézet a regresszio_masodlagos_szamit-hoz: a YouTube-szavak + nincs módszertan-marker."""
    return SimpleNamespace(modszertan_valtas=None,
                           osszes_kulcsszo=lambda: config.osszes_youtube_kulcsszo())


def futtat_youtube(config, docs_data, most, kliens=None):
    szavak = config.osszes_youtube_kulcsszo()
    cellak = len(szavak) * len(MASODLAGOS_TIMEFRAMEK)
    if kliens is None:
        kliens = Kliens(config, plafon=cellak * config.max_probak + 1)  # SZŰK plafon (kvóta-védelem)
    letoltve, eldobva = [], []
    for tetel in szavak:
        for timeframe in MASODLAGOS_TIMEFRAMEK:
            try:
                rek = kulcsszavak.gyujt_egy_masodlagos(kliens, config, tetel, most, timeframe,
                                                       gprop=GPROP, ag=AG)
            except (AgFeladva, PlafonTullepve) as e:
                print(f"FIGYELEM: a YouTube-ág feladva ({tetel.kifejezes!r} {timeframe}): {e}")
                rek = None
                break_all = True
            else:
                break_all = False
            if rek:
                nyers_kimenet.ir_youtube(docs_data, {tetel.kifejezes: rek})
                n = len([p for p in rek["pontok"] if not p.get("reszleges")])
                letoltve.append((tetel.kifejezes, timeframe, n))
                print(f"LETÖLTVE (yt): {tetel.kifejezes!r} {timeframe} ({n} pont)")
            else:
                eldobva.append((tetel.kifejezes, timeframe))
            if break_all:
                break
        else:
            continue
        break  # 429/plafon → az egész ág feladva, az addigi cellák megmaradnak

    # Regresszió a frissen kiírt youtube_nyers.json-ból (nulla Google-hívás)
    import json
    yt_fajl = Path(docs_data) / "youtube_nyers.json"
    if yt_fajl.exists():
        yt_nyers = json.loads(yt_fajl.read_text(encoding="utf-8"))
        adat = regresszio.regresszio_masodlagos_szamit(yt_nyers, {"napok": []}, _reg_shim(config),
                                                       most.isoformat())
        regresszio.regresszio_ir_youtube(docs_data, adat)

    print(f"ÖSSZEGZÉS (youtube): {len(letoltve)} letöltve, {len(eldobva)} eldobva/üres, "
          f"{kliens.osszes_hivas()} hívás. NEM indult primer/idosor/felkapott/lánc ág.")
    return {"letoltve": letoltve, "eldobva": eldobva}


def main(argv=None):
    p = argparse.ArgumentParser(description="YouTube-ág — gprop=youtube gyűjtés + regresszió, más ág NÉLKÜL.")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--docs-data", default="docs/data")
    p.add_argument("--adatok", default="adatok")
    a = p.parse_args(argv)
    config = betolt(a.config)
    most = seged.most_utc()
    ki = futtat_youtube(config, Path(a.docs_data), most)
    # napló: egy 'youtube' ág-sor
    naplo.naplo_ir(Path(a.adatok), most.isoformat(), [{
        "ag": "youtube", "eredmeny": "siker" if ki["letoltve"] else "hiany",
        "hivasok_szama": len(ki["letoltve"]), "hibakodok": "",
    }], config.naplo_max_sor)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_youtube_ag.py -v`
Expected: PASS (24-cella/4-cella loop, nyers+regresszió kiírva, nem indít más ágat).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/youtube.py tests/test_youtube_ag.py
git commit  # "feat(youtube-ag): trendfigyelo.youtube belépő (12 szó × 3-m+12-m, szűk plafon, regresszió, más ág NÉLKÜL)"  + trailer
```

---

### Task 6: `.github/workflows/youtube.yml` — külön 15:00 UTC ütemezés

**Files:**
- Create: `.github/workflows/youtube.yml`
- Test: YAML-érvényesség smoke (`.venv/bin/python -c "import yaml; yaml.safe_load(open('.github/workflows/youtube.yml'))"`)

**Interfaces:**
- Consumes: `python -m trendfigyelo.youtube`; a `masodlagos_only.yml`/`napi.yml` szerkezetét tükrözi.

- [ ] **Step 1: Írd meg a workflow-t**

`.github/workflows/youtube.yml` (ÚJ):

```yaml
name: YouTube-gyűjtés (napi)
on:
  workflow_dispatch:
  schedule:
    - cron: "0 15 * * *"   # 15:00 UTC — 17:00 nyár / 16:00 tél budapesti idő (a Google-futás 19:07 UTC ELŐTT)
permissions:
  contents: write
jobs:
  youtube:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Függőségek
        run: pip install -r requirements.txt
      - name: YouTube-gyűjtés
        run: |
          set -o pipefail
          python -m trendfigyelo.youtube 2>&1 | tee youtube.log
      - name: Commit (külön adat-commit)
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/data/youtube_nyers.json docs/data/youtube_regresszio.json adatok/naplo.csv
          if git diff --cached --quiet; then
            echo "Nincs változás — nincs commit."
          else
            git commit -m "adat: napi YouTube-gyűjtés ($(date -u +%Y-%m-%dT%H:%MZ))"
            git push
          fi
```

- [ ] **Step 2: YAML-érvényesség**

Run: `.venv/bin/python -c "import yaml; yaml.safe_load(open('.github/workflows/youtube.yml')); print('OK')"`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/youtube.yml
git commit  # "ci(youtube): külön napi workflow, cron 0 15 UTC (17:00/16:00 budapesti), külön adat-commit"  + trailer
```

---

### Task 7: `youtube.html` + a 4. menüpont (minden lapon)

**Files:**
- Create: `docs/youtube.html`
- Modify: `docs/index.html:10-14`, `docs/elemzes.html:10-14`, `docs/adatokrol.html` (`#fomenu`)
- Modify: `e2e/menu.spec.js`
- Test: `e2e/menu.spec.js`

**Interfaces:**
- Produces: `#youtube-intervallum-vezerlo`, `#youtube-blokk[data-aktiv-intervallum]`, `#youtube-attekinto` DOM-horgonyok (a Google-id-któl KÜLÖNBÖZŐK, hogy az `app.js` auto-init NE nyúljon hozzájuk); a `youtube.html` betölti `vendor/chartjs/chart.umd.js` + `js/app.js` + `js/youtube.js`.

- [ ] **Step 1: Frissítsd a menü-tesztet (RED)**

`e2e/menu.spec.js` — a count 3→4 és az új link minden lapon:

```js
test("menüsor: 4 fül, aktív = Trendek; a linkek helyesek", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#fomenu a")).toHaveCount(4);
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Trendek");
  await expect(page.locator('#fomenu a[href="elemzes.html"]')).toHaveText("Elemzés");
  await expect(page.locator('#fomenu a[href="youtube.html"]')).toHaveText("YouTube");
  await expect(page.locator('#fomenu a[href="adatokrol.html"]')).toHaveText("Infó");
});

test("youtube.html: a fül betölt, a YouTube menüpont aktív", async ({ page }) => {
  await page.goto("/youtube.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("YouTube");
  await expect(page.locator("#youtube-blokk")).toBeAttached();
});
```

- [ ] **Step 2: Futtasd — FAIL**

Run: `npx playwright test e2e/menu.spec.js --workers=1`
Expected: FAIL (count 3, nincs youtube.html).

- [ ] **Step 3: Add a 4. linket mindhárom meglévő lapon**

Mindegyik `#fomenu`-be (index.html, elemzes.html, adatokrol.html), az `elemzes.html` link UTÁN:

```html
    <a href="youtube.html">YouTube</a>
```

- [ ] **Step 4: Hozd létre `docs/youtube.html`-t**

A `docs/index.html` fej/láb-szerkezetét tükrözi; a `#fomenu`-ben a YouTube aktív; a törzs a YouTube-blokk vázát adja:

```html
  <nav id="fomenu" aria-label="Fő menü">
    <a href="index.html">Trendek</a>
    <a href="elemzes.html">Elemzés</a>
    <a href="youtube.html" class="aktiv" aria-current="page">YouTube</a>
    <a href="adatokrol.html">Infó</a>
  </nav>
  <header class="fejlec-doboz">
    <h1>YouTube — mit néznek Magyarországon</h1>
    <p class="fogalmi-keret">A YouTube-keresés VIDEÓ-IGÉNYT mér (meg akarom nézni / megtanulni /
      kikapcsolni) — nem információs keresést, mint a Trendek fül. Örökzöld kategória-szavakat
      követünk; minden szó a SAJÁT 0–100 skáláján. Napi frissítés.</p>
  </header>
  <main>
    <section class="szekcio">
      <div class="vezerlo-sav"><span class="vezerlo-cim">Idő-ablak</span>
        <div id="youtube-intervallum-vezerlo"></div></div>
      <div id="youtube-blokk" data-aktiv-intervallum="teljes"></div>
    </section>
    <section id="youtube-attekinto"></section>
  </main>
  <footer id="labresz"></footer>
  <script src="vendor/chartjs/chart.umd.js"></script>
  <script src="js/app.js"></script>
  <script src="js/youtube.js"></script>
```

(A `<head>`/`<link rel="stylesheet" href="css/app.css">` a `docs/index.html`-ből bájt-azonosan másolva.)

- [ ] **Step 5: Futtasd — PASS (menü)**

Run: `npx playwright test e2e/menu.spec.js --workers=1`
Expected: PASS (a youtube.js még üres lehet; a `#youtube-blokk` attached).

- [ ] **Step 6: Commit**

```bash
git add docs/youtube.html docs/index.html docs/elemzes.html docs/adatokrol.html e2e/menu.spec.js
git commit  # "feat(youtube-ui): youtube.html váz + 4. menüpont minden lapon; menu.spec 3→4"  + trailer
```

---

### Task 8: `youtube.js` — adatbetöltés, reg-egyesítés, render + e2e

**Files:**
- Create: `docs/js/youtube.js`
- Test: `e2e/youtube.spec.js` (ÚJ)

**Interfaces:**
- Consumes az `app.js` GLOBÁLIS leaf-jeit (classic script, közös scope): `json_betolt(rel)`, `adat` (fájlnév-kulcsú cache), `nyers_ablak(szo, veg, forras)`, `racs_epit(...)`, `kartya_letrehoz(...)`, `chart_letrehoz(kartya)`, `teljes_valaszt(szoreg)`, `INTERVALLUMOK`, `TELJES_KULCS`, `OK_MAGYAR`, `TREND_SZOVEG`, `DOMEN_MAGYAR`.
- Produces: a `#youtube-intervallum-vezerlo` gombsort + `#youtube-blokk` kosár-csoportosított kártyákat + `#youtube-attekinto` trend-panelt; a `_forras:"youtube_nyers.json"` beállításával a rajzoló leaf-ek YouTube-adatot rajzolnak.

- [ ] **Step 1: Írd meg az e2e-t (RED)** — a `kulcsszo.spec.js` `mock`-mintája YouTube-ra:

```js
// e2e/youtube.spec.js  (ÚJ)
const { test, expect } = require("@playwright/test");
const Y = "#youtube-blokk";

function iso(d) { return new Date(d).toISOString(); }
function napiPontok(n) {
  const ki = []; const kezd = Date.UTC(2026, 4, 22);
  for (let i = 0; i < n; i++) ki.push({ idopont_utc: iso(kezd + i*86400000), ertek: 40, reszleges: i === n-1 });
  return ki;
}
function ivErvenyes() {
  return { ervenyes: true, meredekseg_nap: 0.5, irany: "novekszik", r2: 0.4,
           ablak_kezdet_utc: iso(Date.UTC(2026,4,22)), ablak_veg_utc: iso(Date.UTC(2026,7,20)),
           illesztes_vonal: [{idopont_utc: iso(Date.UTC(2026,4,22)), ertek: 30},
                             {idopont_utc: iso(Date.UTC(2026,7,20)), ertek: 50}],
           se_masodlagos_autokorrelacio: true, r2_masodlagos_autokorrelacio: true,
           pontok_hasznalt: 90, mai_ertek: 50, illeszkedes: "illeszkedik" };
}
function ivRovidHet() { return { ervenyes: false, ok: "keves_pont" }; }

async function mock(page, { reg, nyers }) {
  const rou = async (rel, obj) =>
    page.route(u => u.pathname.endsWith(rel), r => r.fulfill({ json: obj }));
  await rou("youtube_regresszio.json", reg);
  await rou("youtube_nyers.json", nyers);
  // a Google-blokkok üresek maradjanak (ne szivárogjon a teszt-szerver adata)
  for (const f of ["kulcsszo_regresszio.json","kulcsszo_nyers.json","kulcsszo_masodlagos_nyers.json",
                   "kulcsszo_masodlagos_regresszio.json","kulcsszo_lanc.json"])
    await rou(f, { kulcsszavak: {} });
}

test("YouTube-fül: kosár-csoportok + napi szó rajzol + trend", async ({ page }) => {
  await mock(page, {
    reg: { kulcsszavak: {
      "edzés": { racs: "nap", aktiv: true, domen: "egeszseg", tipus: "szintmero",
                 intervallumok: { "1_het": ivErvenyes(), "2_het": ivErvenyes(),
                                  "1_ho": ivErvenyes(), "3_ho": ivErvenyes(), "1_ev": ivErvenyes() } },
      "klíma": { racs: "het", aktiv: true, domen: "otthon", tipus: "szintmero",
                 intervallumok: { "1_het": ivRovidHet(), "2_het": ivRovidHet(),
                                  "1_ho": ivErvenyes(), "3_ho": ivErvenyes(), "1_ev": ivErvenyes() } },
    }},
    nyers: { kulcsszavak: {
      "edzés": [{ kulcsszo:"edzés", racs:"nap", timeframe:"today 3-m",
                  ablak_kezdet_utc: iso(Date.UTC(2026,4,22)), ablak_veg_utc: iso(Date.UTC(2026,7,20)),
                  pontok: napiPontok(90) }],
      "klíma": [{ kulcsszo:"klíma", racs:"het", timeframe:"today 12-m",
                  ablak_kezdet_utc: iso(Date.UTC(2025,7,20)), ablak_veg_utc: iso(Date.UTC(2026,7,20)),
                  pontok: napiPontok(53) }],
    }},
  });
  await page.goto("/youtube.html");
  await expect(page.locator(`${Y} .domen-csoport`)).toHaveCount(2);       // 2 kosár
  await expect(page.locator(`${Y} .kulcsszo-chart`)).toHaveCount(2);
  // váltás 1 hét ablakra: az edzés (napi) rajzol, a klíma (heti) a "túl rövid" üzenetet hozza
  await page.locator('#youtube-intervallum-vezerlo button', { hasText: "1 hét" }).click();
  await expect(page.locator(`${Y} .kulcsszo-chart[data-drawable="true"]`)).toHaveCount(1);
  await expect(page.locator(`${Y} .kulcsszo-chart .ok`)).toContainText("túl rövid");
});
```

- [ ] **Step 2: Futtasd — FAIL**

Run: `npx playwright test e2e/youtube.spec.js --workers=1`
Expected: FAIL (üres `#youtube-blokk`, nincs render).

- [ ] **Step 3: Írd meg `docs/js/youtube.js`-t**

A Google-fül egyszerűsített mása (CSAK másodlagos, se órás, se lánc). A rajzoló leaf-eket az `app.js`-ből hívja; a saját `#youtube-*` id-kre renderel. A `_forras`-t `"youtube_nyers.json"`-ra állítja, `_racs`-ot az intervallum rácsából. A gombsor és a kártya-render az `app.js` `intervallum_vezerlo_render`/`kulcsszo_blokk_render` logikájának lehatárolt átvétele a YouTube-blokkra (a `#youtube-blokk[data-aktiv-intervallum]` az egyetlen igazságforrás; kattintás → `data-aktiv-intervallum` átírás + újrarender). A `nincs órás/lánc` miatt az egyesítés csak a másodlagos regresszió intervallumaiból dolgozik:

```js
"use strict";
(function () {
  const YT_REG = "youtube_regresszio.json", YT_NYERS = "youtube_nyers.json";
  const BLOKK = "youtube-blokk", VEZ = "youtube-intervallum-vezerlo", ATT = "youtube-attekinto";

  async function yt_init() {
    await Promise.allSettled([json_betolt(YT_REG), json_betolt(YT_NYERS)]
      .map(p => p.then(() => {}, () => {})));
    // json_betolt az app.js globális `adat`-jába tölt (fájlnév-kulcs); ha nem, itt cache-eljük:
    if (!adat[YT_REG]) { try { adat[YT_REG] = await json_betolt(YT_REG); } catch (e) {} }
    if (!adat[YT_NYERS]) { try { adat[YT_NYERS] = await json_betolt(YT_NYERS); } catch (e) {} }
    yt_render();
  }

  // egyesített reg: per (szó, intervallum) a MÁSODLAGOS regresszióból, _forras/_racs beállítva
  function yt_egyesitett_reg() {
    const reg = (adat[YT_REG] && adat[YT_REG].kulcsszavak) || {};
    const ki = {};
    for (const [szo, szoreg] of Object.entries(reg)) {
      const iv = {};
      for (const [k, cella] of Object.entries(szoreg.intervallumok || {})) {
        iv[k] = Object.assign({}, cella, { _forras: YT_NYERS, _racs: cella.racs || szoreg.racs });
      }
      ki[szo] = Object.assign({}, szoreg, { intervallumok: iv });
    }
    return ki;
  }

  function yt_render() {
    const egyesitett = yt_egyesitett_reg();
    // 1) gombsor a #youtube-intervallum-vezerlo-ba (az app.js intervallum-gomb mintája:
    //    TELJES ál-gomb + INTERVALLUMOK; érvénytelen intervallum → disabled + OK_MAGYAR[ok]),
    //    kattintás → document.getElementById(BLOKK).dataset.aktivIntervallum = kulcs; yt_blokk_render()
    yt_vezerlo_render(egyesitett);
    // 2) kosár-csoportosított kártyák a #youtube-blokk-ba (DOMEN_MAGYAR címkékkel),
    //    a kártyát az app.js kartya_letrehoz + chart_letrehoz építi (nyers_ablak a _forras-ból rajzol);
    //    érvénytelen intervallumnál .ures + OK_MAGYAR[ok] (heti szó rövid ablaka → "túl rövid ...")
    yt_blokk_render(egyesitett);
    // 3) trend-panel a #youtube-attekinto-ba: teljes_valaszt(szoreg).iv.irany → TREND_SZOVEG[irany]
    yt_attekinto_render(egyesitett);
  }

  // yt_vezerlo_render / yt_blokk_render / yt_attekinto_render: az app.js megfelelő
  // render-függvényeinek lehatárolt átvétele a #youtube-* id-kre, az egyesitett bemenettel.
  // (A rajzoló/formázó leaf-ek — nyers_ablak, racs_epit, kartya_letrehoz, chart_letrehoz,
  //  teljes_valaszt, INTERVALLUMOK, OK_MAGYAR, TREND_SZOVEG, DOMEN_MAGYAR — az app.js-ből.)

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", yt_init);
  else yt_init();
})();
```

**Végrehajtói jegyzet (ÉLŐ ITERÁCIÓ, a projekt bevett módja):** a `yt_vezerlo_render` / `yt_blokk_render` / `yt_attekinto_render` a `js/app.js` `intervallum_vezerlo_render` (313-403), `kulcsszo_blokk_render` (1173-1241) és `attekinto_blokk_render` (1071-1086) függvényeinek **átvétele** a `#youtube-*` id-kre és a `yt_egyesitett_reg()` bemenetre — a `data-drawable` / `.domen-csoport` / `.kulcsszo-chart` / `.ok` DOM-szerződések VÁLTOZATLANOK (ezekre megy az e2e). Az élő előnézet a memória „Élő-UI előnézet workflow" szerint (regen + localhost:8000), a `docs/data` szennyezése nélkül. A vizuális finomítás iteratív; a KÉSZ-kritérium a zöld `e2e/youtube.spec.js`.

- [ ] **Step 4: Futtasd — PASS**

Run: `npx playwright test e2e/youtube.spec.js --workers=1`
Expected: PASS (2 kosár, napi szó rajzol, heti szó „túl rövid").

- [ ] **Step 5: Commit**

```bash
git add docs/js/youtube.js e2e/youtube.spec.js
git commit  # "feat(youtube-ui): youtube.js — reg-egyesítés (csak másodlagos) + gombsor/kosár/trend render; e2e"  + trailer
```

---

### Task 9: CSS — a `#youtube-*` blokkok stílusa

**Files:**
- Modify: `docs/css/app.css`
- Test: `e2e/youtube.spec.js` (a meglévő DOM-assertek + egy geometria-smoke)

**Interfaces:**
- A `#kulcsszo-blokk` / `#intervallum-vezerlo` ID-horgonyú szabályokat kiterjeszti a `#youtube-blokk` / `#youtube-intervallum-vezerlo`-ra (szelektor-lista bővítés, NEM duplikálás).

- [ ] **Step 1: Bővítsd a szelektorokat**

Az érintett szabályoknál (pl. `#kulcsszo-blokk .domen-csoport`, `#intervallum-vezerlo`, `#kulcsszo-blokk .kulcsszo-chart`, `.chart-doboz`) add hozzá a `#youtube-*` megfelelőt vesszős szelektor-listaként, pl.:

```css
#kulcsszo-blokk .domen-csoport,
#youtube-blokk .domen-csoport { /* ... a meglévő szabály ... */ }

#intervallum-vezerlo,
#youtube-intervallum-vezerlo { /* ... */ }
```

- [ ] **Step 2: Futtasd — a fül konzisztensen renderel**

Run: `npx playwright test e2e/youtube.spec.js --workers=1`
Expected: PASS (a DOM-assertek zöldek; a layout a Google-füllel egyező).

- [ ] **Step 3: Commit**

```bash
git add docs/css/app.css
git commit  # "style(youtube-ui): a #youtube-* blokkok a kulcsszó-fül CSS-ét öröklik (szelektor-bővítés)"  + trailer
```

---

### Task 10: Infó-oldal + fogalmi keret szöveg

**Files:**
- Modify: `docs/adatokrol.html` (új YouTube-doboz)
- Test: `e2e/menu.spec.js` (smoke: a doboz jelen van)

- [ ] **Step 1: Adj egy YouTube-magyarázó dobozt az `adatokrol.html`-hez**

A meglévő tematikus dobozok mintájában, óvatos fogalmazással: mit mér a YouTube-fül (videó-igény ≠ információs keresés), a 12 szó/8 kosár, a napi/heti rács, a 0–100 relatív skála, hogy nincs órás/lánc (heti szavaknál a rövid ablak strukturálisan üres), és hogy a trend Pythonból számolt (VALÓS, nem AI). Külön gyűjtés 15:00 UTC-kor.

- [ ] **Step 2: Smoke-teszt**

`e2e/menu.spec.js`-hez egy assert: `await expect(page.locator("#adatokrol-youtube")).toBeAttached();` (a doboznak adj `id="adatokrol-youtube"`-t).
Run: `npx playwright test e2e/menu.spec.js --workers=1`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add docs/adatokrol.html e2e/menu.spec.js
git commit  # "docs(youtube-ui): Infó-oldal YouTube-doboz (videó-igény, rács, 0–100, VALÓS trend)"  + trailer
```

---

### Task 11: Teljes SOROS suite + leltár + átadó

**Files:**
- Modify: `docs/superpowers/leltar.md`
- Create: `docs/superpowers/ATADAS-2026-08-25.txt`

- [ ] **Step 1: Teljes SOROS suite ZÖLD**

Run:
```
.venv/bin/python -m pytest -p no:xdist -q
npx playwright test --workers=1
```
Expected: pytest (386 + az új youtube-tesztek) ZÖLD; Playwright (130 + youtube.spec + a menü 4-es frissítés) ZÖLD; MUTÁCIÓ==1 változatlan.

- [ ] **Step 2: Leltár — a YouTube-fül LESZÁLLÍTVA (kész+1)**

`docs/superpowers/leltar.md`: új LESZÁLLÍTVA tétel (YOUTUBE-FUL), delta-log jegyzettel. Fejléc: **kész 40→41, törzs 72→73**; aktív 3 / rekord 29 / LEZÁRT 18 VÁLTOZATLAN. Invariáns: **3+41+29=73 ✓**. (Új adatfájlok: youtube_nyers.json, youtube_regresszio.json; új workflow; a pótolhatatlan órás ág érintetlen.)

- [ ] **Step 3: Átadó**

`docs/superpowers/ATADAS-2026-08-25.txt`: a YouTube-fül leszállítása (mérés-alap, 12 szó × 3-m+12-m, nincs órás/lánc, trend Google-paritásban, külön 15:00 UTC workflow), a nyitott pontok (>1 év akkumuláció; meres_kezdete kezdetben None; első éles 15:00 UTC futás FIGYELME), MUNKAMÓDSZER-lábléc.

- [ ] **Step 4: Commit (DOC + leltár)**

```bash
git add docs/superpowers/leltar.md docs/superpowers/ATADAS-2026-08-25.txt
git commit  # "doc(leltar+atado): YOUTUBE-FUL LESZÁLLÍTVA — kész 40→41, törzs 72→73 (invariáns 3+41+29=73), első éles 15:00 UTC futás figyelme"  + trailer
```

- [ ] **Step 5: Push — KÜLÖN kör, JÓVÁHAGYÁSSAL**

A sync-gate: `git fetch` → `HEAD..origin/main` → ha nem üres: `pull --rebase` + TELJES SOROS suite ÚJRA → `git push` → `git rev-list --left-right --count HEAD...origin/main` == `0 0`. **A push a felhasználó explicit jóváhagyásával.**

---

## Self-Review (spec-lefedettség)

- **Spec §3 (12 szó):** Task 1 (config.yaml) ✓
- **Spec §4 (24 hívás, 3-m+12-m, nincs órás):** Task 2 (gprop) + Task 5 (loop MASODLAGOS_TIMEFRAMEK, nincs `now 7-d`) ✓
- **Spec §5 (külön 15:00 UTC workflow, külön commit):** Task 6 ✓
- **Spec §6 (backend + youtube_nyers + youtube_regresszio + trend KÖTELEZŐ):** Task 3 + Task 4 + Task 5 ✓
- **Spec §7 (új fül, gombsor, kosár, trend-panel, fogalmi keret):** Task 7 + Task 8 + Task 9 + Task 10 ✓
- **Spec §8 (429/kvóta, órás ág védelme):** Task 5 (szűk plafon, nem indít más ágat — teszt) ✓
- **Spec §9 (tesztek, Google regressziómentes):** minden backend task TDD + Task 8 e2e + Task 11 teljes suite ✓
- **Spec §10 (YAGNI: nincs rising/AI/órás):** a terv egyiket sem építi ✓
- **Type-konzisztencia:** `gyujt_egy_masodlagos(..., gprop="", ag=...)` (Task 2) ← Task 5 hívja `gprop="youtube", ag="youtube"`; `ir_youtube` (Task 3) ← Task 5; `regresszio_masodlagos_szamit(...)` + `regresszio_ir_youtube` (Task 4) ← Task 5; `_forras="youtube_nyers.json"` (Task 8) ↔ `nyers_ablak(szo,veg,forras)` (app.js). ✓
- **Nyitott (writing-plans → execution):** `meres_kezdete` kezdetben None (üres tortenet-shim); a >1 év „Teljes időszak" akkumuláció későbbi kör (spec §11).
