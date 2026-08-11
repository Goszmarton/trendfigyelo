# Task 3b — `kategoriak.json` kategória-aggregátum — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Új adatréteg-kimenet `docs/data/kategoriak.json`, amely a napi felkapott trendlista `temak` kategóriáit napi bontásban aggregálja, felület nélkül.

**Architecture:** Új `trendfigyelo/kategoriak.py` modul egy tiszta osztályozó/aggregáló függvénnyel (`kategoria_aggregatum`) és egy író függvénnyel (`kategoriak_ir`), amely a `napok/*.json` fájlok **determinisztikus tükreként** állítja elő a kimenetet (a `regresszio.py` származtatott-nézet mintája). Bekötés a `futtato.futtat`-ba a `napi_ir` után, a regresszió-ág **védelmi mintájával** (nem néma, nem blokkol, nulla Google-hívás).

**Tech Stack:** Python 3.14 (fejlesztői venv), pytest. Nincs új függőség.

## Global Constraints

- **Spec-horgony:** `docs/superpowers/phase3/phase3-spec.md` §8.1; design: `docs/superpowers/specs/2026-08-11-kategoriak-json-design.md`.
- **Nulla extra Google-hívás.** A `tervezett_hivasszam` és a hívás-plafon változatlan.
- **A származtatott kimenet VÉDETT és NEM néma:** hiba SOHA nem viheti el az adatmentést vagy az exit-kódot, de `FIGYELEM` a run.log-ba + `kategoriak` naplósor (finding 6 fegyelme).
- **A történet 3a élesítésétől (2026-08-05) épül;** a 13 régi mező-nélküli nap tudatosan kimarad.
- **Az `ok` mező MEGFIGYELÉST rögzít, nem OKOT:** egyetlen érték `"nincs_kategoria_adat"`; a valódi ág a `naplo.csv` `felkapott_api` sorából fejthető vissza.
- **Az „Other" valódi Google-kategória** (topic ID 11), saját kulcs a `kategoriak`-ban — NEM a `kategoria_nelkul` gyűjtő.
- **A napló `ag` neve az új ágra: `"kategoriak"`;** oszlopok: `ag;eredmeny;hivasok_szama;hibakodok`.
- **TDD kötelező:** minden lépés valódi RED → GREEN. A `.venv/bin/pytest -q` baseline **224 passed**.

---

## File Structure

- **Create** `trendfigyelo/kategoriak.py` — `kategoria_aggregatum(nap_iso, trendek)` (tiszta) + `kategoriak_ir(docs_data)` (tükör-író).
- **Create** `tests/test_kategoriak.py` — a 9 diszkriminátor (Task 1–2).
- **Modify** `trendfigyelo/futtato.py` — import kiegészítés (13. sor) + védett bekötés-blokk a 213. sor után.
- **Modify** `tests/test_futtato.py` — bekötés-tesztek (pozitív + védelem).
- **Create (adat)** `docs/data/kategoriak.json` — a valós backfill kimenete (Task 4).

---

### Task 1: `kategoria_aggregatum` — tiszta osztályozó/aggregáló függvény

**Files:**
- Create: `trendfigyelo/kategoriak.py`
- Test: `tests/test_kategoriak.py`

**Interfaces:**
- Consumes: semmit (tiszta függvény; bemenet egy napi fájl `trendek` listája).
- Produces: `kategoria_aggregatum(nap_iso: str, trendek: list[dict]) -> dict | None`
  - `None` → 3a előtti nap (kihagyandó).
  - `{"nap", "merve": False, "ok": "nincs_kategoria_adat", "lista_hossz"}` → nem-mért nap.
  - `{"nap", "merve": True, "lista_hossz", "lista_kategoriaval", "kategoria_nelkul", "kategoriak": {név: db}}` → mért nap.

- [ ] **Step 1: Írd meg a bukó teszteket (aggregálás — `merve:true`)**

`tests/test_kategoriak.py`:

```python
import json

from trendfigyelo import kategoriak


def _t(kifejezes, temak=None):
    """Trend-elem; temak=None → NINCS temak kulcs (3a előtti / vegyes eset)."""
    e = {"kifejezes": kifejezes}
    if temak is not None:
        e["temak"] = temak
    return e


def test_merve_true_alap_aggregalas():
    trendek = [_t("a", ["Sports"]), _t("b", ["Health"]), _t("c", ["Sports"])]
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["merve"] is True
    assert r["nap"] == "2026-08-10"
    assert r["lista_hossz"] == 3
    assert r["kategoriak"] == {"Sports": 2, "Health": 1}
    assert r["kategoria_nelkul"] == 0
    assert r["lista_kategoriaval"] == 3


def test_multi_kategoria_tobbszor_szamit():
    # egy elem két temak → mindkettőben +1; az összeg meghaladhatja a lista_hossz-t
    trendek = [_t("a", ["Business and Finance", "Health"])]
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["kategoriak"] == {"Business and Finance": 1, "Health": 1}
    assert sum(r["kategoriak"].values()) > r["lista_hossz"]
    assert r["lista_kategoriaval"] == 1


def test_kategoria_nelkul_ures_es_hianyzo():
    # temak=[] ÉS hiányzó temak kulcs is a kategoria_nelkul-ba esik
    trendek = [_t("a", ["Sports"]), _t("b", []), _t("c")]   # c: nincs temak kulcs
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["merve"] is True
    assert r["kategoria_nelkul"] == 2
    assert r["lista_kategoriaval"] == 1
    assert r["kategoriak"] == {"Sports": 1}


def test_other_valodi_kategoria_nem_gyujto():
    trendek = [_t("a", ["Other"]), _t("b", ["Sports"])]
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["kategoriak"]["Other"] == 1
    assert r["kategoria_nelkul"] == 0


def test_lista_hossz_invarians():
    trendek = [_t("a", ["Sports"]), _t("b", []), _t("c", ["Health", "Law"]), _t("d")]
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["lista_hossz"] == r["lista_kategoriaval"] + r["kategoria_nelkul"]
```

- [ ] **Step 2: Futtasd, hogy BUKJON**

Run: `.venv/bin/pytest tests/test_kategoriak.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'trendfigyelo.kategoriak'`

- [ ] **Step 3: Írd meg a minimális implementációt**

`trendfigyelo/kategoriak.py`:

```python
"""Kategória-aggregátum: a kategoriak.json SZÁRMAZTATOTT nézet előállítása (spec 8.1).

A napi felkapott trendlista `temak` kategóriáit napi bontásban aggregálja. A
kategoriak.json a napok/*.json determinisztikus tükre (mint a regresszio.json a
nyersből) — nulla Google-hívás, felület nélkül.

Az `ok` mező MEGFIGYELÉST rögzít, nem OKOT: a "nincs_kategoria_adat" nem állítja,
MIÉRT nincs adat (a valódi ág utólag a naplo.csv felkapott_api sorából fejthető
vissza). Az "Other" valódi Google-kategória (topic ID 11), nem a kategoria_nelkul gyűjtő.
"""
import json
from pathlib import Path

from . import json_export


def kategoria_aggregatum(nap_iso, trendek):
    """Egy nap trendlistája → kategória-rekord, VAGY None (3a előtti nap, kihagyandó).

    None: egyetlen elemnek sincs "temak" KULCSA (3a előtti korszak).
    merve:false: a kulcs jelen, de minden temak üres → ok="nincs_kategoria_adat".
    merve:true: van legalább egy nem-üres temak; a []/kulcs nélküli elemek a
                kategoria_nelkul-ba esnek (§8.1 gyűjtő), a nap egésze mért (vegyes nap).
    """
    tem_m = sum(1 for e in trendek if "temak" in e)
    if tem_m == 0:
        return None                                  # 3a előtti nap — kihagyva
    lista_hossz = len(trendek)
    if not any(e.get("temak") for e in trendek):     # a kulcs jelen, de mind üres
        return {"nap": nap_iso, "merve": False,
                "ok": "nincs_kategoria_adat", "lista_hossz": lista_hossz}
    kategoriak = {}
    kategoria_nelkul = 0
    lista_kategoriaval = 0
    for e in trendek:
        temak = e.get("temak") or []                 # hiányzó kulcs VAGY [] → []
        if not temak:
            kategoria_nelkul += 1
        else:
            lista_kategoriaval += 1
            for k in temak:
                kategoriak[k] = kategoriak.get(k, 0) + 1
    return {"nap": nap_iso, "merve": True, "lista_hossz": lista_hossz,
            "lista_kategoriaval": lista_kategoriaval,
            "kategoria_nelkul": kategoria_nelkul, "kategoriak": kategoriak}
```

- [ ] **Step 4: Futtasd, hogy ÁTMENJEN**

Run: `.venv/bin/pytest tests/test_kategoriak.py -q`
Expected: PASS (5 teszt)

- [ ] **Step 5: Írd meg a bukó teszteket (osztályozás — `None` / `merve:false` / vegyes)**

Add hozzá `tests/test_kategoriak.py`-hoz:

```python
def test_harom_a_elotti_nap_none():
    # egyetlen elemnek sincs "temak" kulcsa (3a előtti korszak) → None (kihagyás)
    trendek = [{"kifejezes": "a", "volumen": "1000"}, {"kifejezes": "b"}]
    assert kategoriak.kategoria_aggregatum("2026-07-28", trendek) is None


def test_nincs_kategoria_adat_merve_false():
    # a temak kulcs JELEN, de minden érték üres → merve:false, ok, nincs kategoriak
    trendek = [_t("a", []), _t("b", []), _t("c", [])]
    r = kategoriak.kategoria_aggregatum("2026-08-12", trendek)
    assert r["merve"] is False
    assert r["ok"] == "nincs_kategoria_adat"
    assert r["lista_hossz"] == 3
    assert "kategoriak" not in r


def test_vegyes_nap_merve_true():
    # néhány elemen van (nem-üres) temak kulcs, néhányon nincs → merve:true,
    # a kulcs nélküli elemek kategoria_nelkul-ban (nem None, nem merve:false)
    trendek = [_t("a", ["Sports"]), _t("b"), _t("c")]   # b,c: nincs temak kulcs
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["merve"] is True
    assert r["kategoria_nelkul"] == 2
    assert r["kategoriak"] == {"Sports": 1}
```

- [ ] **Step 6: Futtasd — az új 3 teszt ÁTMEGY (a logika már fedi őket)**

Run: `.venv/bin/pytest tests/test_kategoriak.py -q`
Expected: PASS (8 teszt)

> **Megjegyzés a RED-ről:** a Step 5 három tesztje a Step 3 logikáján már zöld — ezek a `None`/`merve:false`/vegyes ágakat **rögzítik** (regressziós őr). A valódi RED-diszkriminátort a Step 2 adta (a teljes modul hiánya). A mutáció-igazolás a Task 1 végén (Step 7).

- [ ] **Step 7: Mutáció-igazolás (a tesztek nem-vacuous)**

Ideiglenesen rontsd el a `tem_m == 0` ágat `return None` → `pass` (töröld a sort), futtasd:
Run: `.venv/bin/pytest tests/test_kategoriak.py::test_harom_a_elotti_nap_none -q`
Expected: FAIL. Állítsd vissza. Majd az `any(...)` ág `not any` → `any`:
Run: `.venv/bin/pytest tests/test_kategoriak.py::test_nincs_kategoria_adat_merve_false -q`
Expected: FAIL. Állítsd vissza. `grep -rn "MUTÁCIÓ" trendfigyelo/` üres, `git diff trendfigyelo/kategoriak.py` üres.

- [ ] **Step 8: Commit**

```bash
git add trendfigyelo/kategoriak.py tests/test_kategoriak.py
git commit -m "$(cat <<'MSG'
feat(phase3): Task 3b — kategoria_aggregatum tiszta osztályozó/aggregáló

A Step 5 három tesztje (None / merve:false / vegyes) a Step 3 logikáján
SZÁNDÉKOSAN ELŐRE JELÖLT ZÖLD: regressziós őr, nem RED-diszkriminátor. A
valódi RED a teljes modul hiánya volt (Step 2); a nem-vacuous voltot a
Step 7 mutáció-igazolás bizonyítja.
MSG
)"
```

---

### Task 2: `kategoriak_ir` — a `napok/*.json` determinisztikus tükre

**Files:**
- Modify: `trendfigyelo/kategoriak.py`
- Test: `tests/test_kategoriak.py`

**Interfaces:**
- Consumes: `kategoria_aggregatum(nap_iso, trendek)` (Task 1); `json_export._ir_json(fajl, adat)`.
- Produces: `kategoriak_ir(docs_data) -> Path` — beolvassa a `napok/index.json` szerinti napi fájlokat, `{"napok": [rekord, ...]}`-t ír `docs_data/kategoriak.json`-ba, nap szerint rendezve, a `None`-okat kihagyva.

**Skálázási megjegyzés (design §6):** a tükör futásonként a teljes `napok/`
könyvtárat beolvassa — O(napok). ~500 nap felett ez érezhetővé válik; akkor a
`naplo_max_sor` mintájára retenció vagy inkrementális upsert a megoldás. Phase
3-ban egyik sem kell (~1,5 évnyi futás a küszöb).

- [ ] **Step 1: Írd meg a bukó teszteket (tükör + hiányzó nap + idempotencia)**

Add hozzá `tests/test_kategoriak.py`-hoz:

```python
def _napi_fajl(napok_mappa, nap_iso, trendek):
    napok_mappa.mkdir(parents=True, exist_ok=True)
    (napok_mappa / f"{nap_iso}.json").write_text(
        json.dumps({"nap": nap_iso, "trendek": trendek}, ensure_ascii=False), encoding="utf-8")


def _index(napok_mappa, napok):
    napok_mappa.mkdir(parents=True, exist_ok=True)
    (napok_mappa / "index.json").write_text(json.dumps({"napok": napok}), encoding="utf-8")


def test_kategoriak_ir_tukor_harom_csoport(tmp_path):
    docs_data = tmp_path / "docs" / "data"
    napok = docs_data / "napok"
    _napi_fajl(napok, "2026-07-28", [_t("regi")])                     # 3a előtti: nincs temak
    _napi_fajl(napok, "2026-08-10", [_t("a", ["Sports"]), _t("b", ["Health"])])
    _napi_fajl(napok, "2026-08-12", [_t("x", []), _t("y", [])])       # RSS-only: mind []
    _index(napok, ["2026-07-28", "2026-08-10", "2026-08-12"])
    kategoriak.kategoriak_ir(docs_data)
    adat = json.loads((docs_data / "kategoriak.json").read_text(encoding="utf-8"))
    napok_ki = adat["napok"]
    assert [n["nap"] for n in napok_ki] == ["2026-08-10", "2026-08-12"]   # 07-28 kihagyva, rendezett
    assert napok_ki[0]["merve"] is True
    assert napok_ki[0]["kategoriak"] == {"Sports": 1, "Health": 1}
    assert napok_ki[1]["merve"] is False and napok_ki[1]["ok"] == "nincs_kategoria_adat"


def test_kategoriak_ir_hianyzo_napi_fajl_kihagyva(tmp_path):
    # index-ben szereplő, de hiányzó fájlú nap (mint 2026-08-06) NEM kap bejegyzést
    docs_data = tmp_path / "docs" / "data"
    napok = docs_data / "napok"
    _napi_fajl(napok, "2026-08-10", [_t("a", ["Sports"])])
    _index(napok, ["2026-08-06", "2026-08-10"])                       # 08-06 fájl nincs
    kategoriak.kategoriak_ir(docs_data)
    adat = json.loads((docs_data / "kategoriak.json").read_text(encoding="utf-8"))
    assert [n["nap"] for n in adat["napok"]] == ["2026-08-10"]


def test_kategoriak_ir_idempotens(tmp_path):
    docs_data = tmp_path / "docs" / "data"
    napok = docs_data / "napok"
    _napi_fajl(napok, "2026-08-10", [_t("a", ["Sports"])])
    _index(napok, ["2026-08-10"])
    kategoriak.kategoriak_ir(docs_data)
    elso = (docs_data / "kategoriak.json").read_text(encoding="utf-8")
    kategoriak.kategoriak_ir(docs_data)
    masodik = (docs_data / "kategoriak.json").read_text(encoding="utf-8")
    assert elso == masodik
```

- [ ] **Step 2: Futtasd, hogy BUKJON**

Run: `.venv/bin/pytest tests/test_kategoriak.py -k ir -q`
Expected: FAIL — `AttributeError: module 'trendfigyelo.kategoriak' has no attribute 'kategoriak_ir'`

- [ ] **Step 3: Írd meg a minimális implementációt**

Add hozzá `trendfigyelo/kategoriak.py` végéhez:

```python
def kategoriak_ir(docs_data):
    """A napok/*.json determinisztikus tükre → kategoriak.json (spec 8.1).

    A napok/index.json szerinti összes napi fájlt beolvassa, minden napra
    kategoria_aggregatum-ot hív, a None-t (3a előtti nap) kihagyja, nap szerint
    rendez, kiír. Idempotens: a kimenet a napi fájlok determinisztikus függvénye.
    """
    napok_mappa = Path(docs_data) / "napok"
    index_fajl = napok_mappa / "index.json"
    napok_index = (json.loads(index_fajl.read_text(encoding="utf-8")).get("napok", [])
                   if index_fajl.exists() else [])
    rekordok = []
    for nap_iso in sorted(napok_index):
        nap_fajl = napok_mappa / f"{nap_iso}.json"
        if not nap_fajl.exists():
            continue                                 # index-ben van, fájl nincs → nem reprezentáljuk
        nap = json.loads(nap_fajl.read_text(encoding="utf-8"))
        rek = kategoria_aggregatum(nap_iso, nap.get("trendek", []))
        if rek is not None:
            rekordok.append(rek)
    return json_export._ir_json(Path(docs_data) / "kategoriak.json", {"napok": rekordok})
```

- [ ] **Step 4: Futtasd, hogy ÁTMENJEN**

Run: `.venv/bin/pytest tests/test_kategoriak.py -q`
Expected: PASS (11 teszt)

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/kategoriak.py tests/test_kategoriak.py
git commit -m "feat(phase3): Task 3b — kategoriak_ir (napok/*.json determinisztikus tükre)"
```

---

### Task 3: Bekötés a `futtato.futtat`-ba (védett, nem néma)

**Files:**
- Modify: `trendfigyelo/futtato.py:13` (import) és `:213` után (bekötés-blokk)
- Test: `tests/test_futtato.py`

**Interfaces:**
- Consumes: `kategoriak.kategoriak_ir(docs_data_mappa)` (Task 2).
- Produces: a `futtat` minden futáskor kiírja a `docs_data/kategoriak.json`-t, és egy `{"ag": "kategoriak", "eredmeny": "siker"|"hiba", ...}` naplósort.

- [ ] **Step 1: Írd meg a bukó bekötés-teszteket**

Add hozzá `tests/test_futtato.py`-hoz (a `KulcsszoAdatKliens` már létezik a fájlban):

```python
def test_kategoriak_json_letrejon_a_futasban(tmp_path):
    # a felkapott_rss egy trendet ad → napi_ir ír napok fájlt → kategoriak_ir tükrözi
    most = datetime(2021, 1, 4, 12, 0, tzinfo=timezone.utc)
    futtato.futtat(_config(), KulcsszoAdatKliens(),
                   tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    kat = tmp_path / "docs" / "data" / "kategoriak.json"
    assert kat.exists()
    adat = json.loads(kat.read_text(encoding="utf-8"))
    assert "napok" in adat
    sorok = _naplo_soronkent(tmp_path / "adatok")
    assert {s["ag"]: s["eredmeny"] for s in sorok}["kategoriak"] == "siker"


def test_kategoriak_hiba_nem_blokkol(tmp_path, monkeypatch):
    # a származtatott ág hibája SOHA nem viheti el az adatmentést vagy az exit-kódot (finding 6)
    def _dob(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(futtato.kategoriak, "kategoriak_ir", _dob)
    most = datetime(2021, 1, 4, 12, 0, tzinfo=timezone.utc)
    kod = futtato.futtat(_config(), KulcsszoAdatKliens(),
                         tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    assert kod == 0                                                        # exit-kód érintetlen
    assert (tmp_path / "docs" / "data" / "legfrissebb.json").exists()      # adatmentés megvan
    sorok = _naplo_soronkent(tmp_path / "adatok")
    assert {s["ag"]: s["eredmeny"] for s in sorok}["kategoriak"] == "hiba"
```

- [ ] **Step 2: Futtasd, hogy BUKJON**

Run: `.venv/bin/pytest tests/test_futtato.py -k kategoriak -q`
Expected: FAIL — `test_kategoriak_json_letrejon...`: `kategoriak.json` nem jön létre; `test_kategoriak_hiba...`: `AttributeError: module 'trendfigyelo.futtato' has no attribute 'kategoriak'` (a monkeypatch a nem-létező attribútumon bukik).

- [ ] **Step 3: Add hozzá az importot**

`trendfigyelo/futtato.py:13` — vedd fel a `kategoriak`-ot a tuple-be (`json_export` után):

```python
from . import (felkapott, idosorok, json_export, kategoriak, kulcsszavak, naplo,
               nyers_kimenet, regresszio, seged)
```

- [ ] **Step 4: Írd meg a védett bekötés-blokkot**

`trendfigyelo/futtato.py` — a `nyers_kimenet.ir_gordulo` blokk UTÁN (a 213. sor), a `# ---------- regresszió ...` (215. sor) ELÉ szúrd be:

```python
    # ---------- kategória-aggregátum (származtatott, VÉDETTEN; CSAK naplóz) ----------
    # A napok/*.json determinisztikus tükre → kategoriak.json (spec 8.1). Nulla Google-hívás.
    # A regresszió-ág védelmi mintája: hiba SOHA nem viheti el az adatmentést/exit-kódot,
    # de NEM néma (finding 6) — FIGYELEM a run.log-ba + kategoriak naplósor.
    try:
        kategoriak.kategoriak_ir(docs_data_mappa)
        bejegyzesek.append({"ag": "kategoriak", "eredmeny": "siker",
                            "hivasok_szama": 0, "hibakodok": ""})
    except Exception as e:
        bejegyzesek.append({"ag": "kategoriak", "eredmeny": "hiba",
                            "hivasok_szama": 0, "hibakodok": type(e).__name__})
        print(f"FIGYELEM: a kategória-aggregátum kimaradt — nem blokkolja az adatmentést ({e}).")
```

- [ ] **Step 5: Futtasd, hogy ÁTMENJEN**

Run: `.venv/bin/pytest tests/test_futtato.py -k kategoriak -q`
Expected: PASS (2 teszt)

- [ ] **Step 6: Teljes suite — nincs regresszió**

Run: `.venv/bin/pytest -q`
Expected: PASS (**237 passed** — 224 baseline + 13 új: 8 Task 1 + 3 Task 2 + 2 Task 3). Ha eltér, STOP és vizsgáld.

- [ ] **Step 7: Commit**

```bash
git add trendfigyelo/futtato.py tests/test_futtato.py
git commit -m "feat(phase3): Task 3b — kategoriak.json bekötése a futtatóba (védett, nem néma)"
```

---

### Task 4: Valós backfill + a `kategoriak.json` adat-commit

**Files:**
- Create (adat): `docs/data/kategoriak.json`

**Interfaces:**
- Consumes: `kategoriak.kategoriak_ir` (Task 2) a valós `docs/data`-n.

> **FIGYELEM — ez az EGYETLEN lépés, ami adatfájlt ír a repóba, és az éjszakai
> adat-commit ugyanide nyúl.** A kód (Task 1–3) és az adat (Task 4) commitja
> KÜLÖN marad, hogy egy esetleges rebase ne ragassza össze őket.

- [ ] **Step 0: Szinkron-kapu (adatfájl-írás előtt kötelező)**

Run:
```bash
git fetch && git rev-list --left-right --count origin/main...HEAD
```
Expected: `0	0`. Ha `origin/main` előrébb van (éjszakai adat-commit), `git pull --rebase` ELŐBB, majd ismételd a rev-listet, és csak `0 0` után tovább.

- [ ] **Step 1: Generáld a valós `kategoriak.json`-t a meglévő 18 napból**

Run:
```bash
.venv/bin/python -c "from trendfigyelo import kategoriak; kategoriak.kategoriak_ir('docs/data')"
```

- [ ] **Step 2: Ellenőrizd a backfill hatókörét (5 merve:true, 0 merve:false, 13 kihagyva)**

Run:
```bash
.venv/bin/python -c "
import json
d = json.load(open('docs/data/kategoriak.json'))
napok = d['napok']
mt = [n['nap'] for n in napok if n['merve']]
mf = [n['nap'] for n in napok if not n['merve']]
print('merve:true:', mt)
print('merve:false:', mf)
assert mt == ['2026-08-05','2026-08-07','2026-08-08','2026-08-09','2026-08-10'], mt
assert mf == [], mf
print('OK — 5 mért nap, 0 nem-mért, a 13 régi + 08-06 kihagyva')
"
```
Expected: `OK — 5 mért nap, 0 nem-mért, a 13 régi + 08-06 kihagyva`

- [ ] **Step 3: Commit (a tudatos kimaradás rögzítve az üzenetben)**

```bash
git add docs/data/kategoriak.json
git commit -m "$(cat <<'MSG'
adat(phase3): kategoriak.json backfill — 5 API-nap (08-05..08-10)

TUDATOS KIMARADÁSOK (nem hiba, ne tűnjön annak később):
- a 13 régi, 3a előtti nap (2026-07-23..08-04): kategória-mező nem létezik
  a napi fájlokban, visszamenőleg nem szerezhető meg — a történet a 3a
  élesítésétől (2026-08-05) épül (§8.1).
- a 2026-08-06 HIÁNYZÓ nap: nincs napi fájl → NEM kap bejegyzést (a merve
  megfigyelés, nem futott nap). A hiányt a napok/index.json hiánya jelöli.
MSG
)"
```

---

## Self-Review

**1. Spec coverage (design §7 diszkriminátorai → tesztek):**
- §7.1 multi-kategória → `test_multi_kategoria_tobbszor_szamit` ✓
- §7.2 kategoria_nelkul ([] és hiányzó) → `test_kategoria_nelkul_ures_es_hianyzo` ✓
- §7.3 Other nem gyűjtő → `test_other_valodi_kategoria_nem_gyujto` ✓
- §7.4 nincs_kategoria_adat → `test_nincs_kategoria_adat_merve_false` ✓
- §7.5 3a előtti → None → `test_harom_a_elotti_nap_none` ✓
- §7.6 lista_hossz invariáns → `test_lista_hossz_invarians` ✓
- §7.7 integráció valós 5 napon → `test_kategoriak_ir_tukor_harom_csoport` (tmp_path szintetikus) + Task 4 (valós 5 nap) ✓
- §7.8 idempotencia → `test_kategoriak_ir_idempotens` ✓
- §7.9 vegyes nap → `test_vegyes_nap_merve_true` ✓
- §6 védett bekötés (nem néma, nem blokkol) → `test_kategoriak_hiba_nem_blokkol` ✓
- §3 hiányzó nap nem kap bejegyzést → `test_kategoriak_ir_hianyzo_napi_fajl_kihagyva` ✓

**2. Placeholder scan:** nincs TBD/TODO; minden lépés konkrét kóddal. ✓

**3. Type consistency:** `kategoria_aggregatum(nap_iso, trendek) -> dict|None` és `kategoriak_ir(docs_data) -> Path` egységes minden taskban; a `felkapott_api`/`kategoriak` napló-nevek és a `_ir_json` aláírás a valós kódból ellenőrizve. ✓

**Megjegyzés a teszt-számról:** a Step 6 elvárt `237 passed` (224 + 13). A számot a végrehajtó igazolja; eltérés → STOP.
