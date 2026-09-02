# Reggeli kulcsszó-ág: társadalmi-feszültség monitor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 15 új „társadalmi feszültség" kulcsszót gyűjtünk a REGGELI futásban, 5 új doménbe sorolva, per-szó időablakkal (lassú szó → csak másodlagos ablak; csúcs-szó → órás is), a meglévő 13 esti szó és a pótolhatatlan órás lánc bolygatása nélkül.

**Architecture:** Per-szó config-mezők (`oras`, `futas`) vezérlik, hogy egy szó melyik futásban (reggel/este) és milyen ablakokkal gyűlik. A futtatás a mód futás-részhalmazán operál (órás gyűjtés, másodlagos ütemezés, hívás-plafon mind mód-tudatos). A pótolhatatlan `kulcsszo_nyers.json`/`kulcsszo_lanc.json` írása MÁR per-szó upsert (read-modify-write) — a reggeli szubhalmaz nem csonkolja az estit. A frontend 5 új domén-címkét kap; minden derivált nézet (regresszió, elemzés) adat-vezérelt, a domén szabad szöveg.

**Tech Stack:** Python 3 (namedtuple config, pandas Trends-adat), pytest (SOROS, `-p no:xdist`), vanilla JS frontend, Playwright (`--workers=1`).

**Spec:** `docs/superpowers/specs/2026-09-01-reggeli-kulcsszavak-tarsadalmi-feszultseg-design.md`

## Kód-vizsgálat által feloldott spec-kockázatok (a terv ELŐTT igazolva)

A spec két legnagyobb kockázatát a kód beolvasása FELOLDOTTA — ezek a terv előfeltevései:

- **R1 — nyers/lánc merge MÁR per-szó (a #1 „pótolhatatlan" kockázat feloldva).** `nyers_kimenet.ir_gordulo`, `ir_masodlagos` és `lanc.frissit_lanc` MIND read-modify-write per-szó upsert: a fájlt beolvassák, CSAK a kapott dict szavait fűzik/frissítik, a többit érintetlenül hagyják (`frissit_lanc`: `ki = dict(tarolt)`). A reggeli profil-3 részhalmaz átadása tehát szerkezetileg NEM törölheti az esti 13 szó sorozatát. **Nincs új merge-kód**; a Task 2 karakterizációs teszttel LEZÁRJA ezt az invariánst a rá építő taskok előtt.
- **R3 — a `legfrissebb.json` kulcsszó-blokkja HALOTT a megjelenítéshez (a spec §D merge feleslegessé vált).** A frontend kulcsszó-blokkja (`docs/js/app.js:35`) a `kulcsszo_regresszio.json` + `kulcsszo_nyers.json` + `kulcsszo_masodlagos_*` + `kulcsszo_lanc.json` fájlokból rajzol; a `legfrissebb.json`-t CSAK a trend-blokk olvassa (`top_trendek`). A `legfrissebb.kulcsszavak`/`kulcsszo_osszesites` blokkot a jelenlegi frontend NEM olvassa kulcsszó-adatként. Ezért a spec §D („merge-tudatos legfrissebb") NEM szükséges: a reggeli szavak a `kulcsszo_nyers.json`-on (per-szó merge, mindig teljes) + az esti regresszió-passzon (a teljes fájlt olvassa) keresztül jelennek meg. **A `json_export.legfrissebb_ir`-t NEM módosítjuk.**
- **R2 — a `tortenet.json` reggeli írását ELKERÜLJÜK (a nap-clobber veszély miatt).** A `tortenet_frissit_napok` egy napot TELJESEN cserél (a nap kulcsszó-listáját felülírja). Reggel a profil-3, este a 13 szó UGYANARRA a `nap_iso`-ra írna → az egyik törölné a másikat. Megoldás: a reggeli mód NEM ír tortenetet (a meglévő `and not csak_felkapott` őr marad). A profil-3 szavak órás regresszióját az ESTI passz számolja a teljes `kulcsszo_nyers.json`-ból; a hiányzó tortenet-nap → `meres_kezdete=null` kecses degradáció (a 9b már kezeli, minden tortenet nélküli szónál). YAGNI: nincs per-szó tortenet-merge ebben az iterációban.
- **R4 — az esti regresszió-passz MÁR fedi a reggeli szavakat.** A `regresszio_szamit` a TELJES `kulcsszo_nyers.json`-t olvassa (nem csak az adott futás szavait), így a reggel beírt profil-3 szavak órás regressziója az esti futásban elkészül. A Task 9 igazolja, hogy egy tortenet nélküli nyers-szó nem hasal.

## Global Constraints

Minden task implicit követelménye. Pontos értékek a projekt munkamódszeréből:

- **Git `add` CSAK névvel.** SOHA `git add -A` / `git add .`. A gyökér `ATADAS-2026-08-18.txt` SOHA nem staged.
- **Commit-trailerek** (minden commit végén, üres sor után):
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
  ```
- **A push KÜLÖN, kapuzott kör** (nem a taskok része): fetch → divergencia-ellenőrzés → rebase ha lemaradt → push → `git rev-list --count`-tal 0/0 igazolás + explicit user-jóváhagyás.
- **SOROS suite** (MUTÁCIÓ=1, valós RED→GREEN): `.venv/bin/python -m pytest -p no:xdist -q` ÉS `npx playwright test --workers=1`. NINCS párhuzamos futtatás.
- **Pótolhatatlan adat OLVASHATÓ-CSAK szerkesztéskor:** `docs/data/kulcsszo_nyers.json`, `kulcsszo_lanc.json` — a kódot módosítjuk, az éles adatfájlokat kézzel SOHA. A tesztek `tmp_path`-ban dolgoznak.
- **Frontend időkezelés:** SOHA `new Date()` / `Date.now()`; kizárólag `new Date(Date.UTC(...))`.
- **A `hirfigyelo` projekt (közös Hetzner) érintetlen.** A youtube-ág (`youtube.py`, `youtube.js`, `YT_DOMEN_MAGYAR`) érintetlen.
- **Adat-commit KÜLÖN a kód-committól.** Ez a terv CSAK kódot/tesztet/configot/dokumentumot ír; nem generál éles adatot.

## Taxonómia (a Task 7 config-adatához — kanonikus forrás)

| Domén (slug) | Magyar címke | Szavak (🆕 = új, 15 db) |
|---|---|---|
| `megelhetes` | Megélhetési problémák | rezsi🆕, fizetés🆕, kölcsön🆕, segély🆕, albérlet, hitel, nyugdíj, eladó lakás, benzin, akciós újság, állás, napelem, nyaralás |
| `egeszsegugy` | Egészségügyi problémák | várólista🆕, sürgősségi🆕, háziorvos🆕, műtét🆕, kórház, betegség |
| `oktatas` | Oktatási problémák | pedagógus🆕, iskola🆕 |
| `gazdasag` | Gazdasági bizonytalanság | infláció🆕, munkanélküliség🆕, csőd🆕 |
| `politika` | Politikai elégedetlenség | korrupció🆕, kormány🆕, tüntetés, kormányablak |

**15 új szó profiljai (mind `futas: reggel`, egy-ablakos):**

| Profil | Szavak | `oras` | `racs` | Gyűjtött ablak(ok) |
|---|---|---|---|---|
| 1 — lassú strukturális | infláció, rezsi, fizetés, segély, várólista, háziorvos, műtét, iskola, munkanélküliség, csőd (10) | `false` | `het` | csak 12m (heti) |
| 2 — közepes momentum | kölcsön, sürgősségi (2) | `false` | `nap` | csak 3m (napi) |
| 3 — esemény/csúcs | pedagógus, korrupció, kormány (3) | `true` | `het` | 7d órás + 12m |

A meglévő 13 szó `oras`/`futas` mezője HIÁNYZIK a configból → default (`oras: true`, `futas: este`); csak a `domen`-jüket írjuk át.

---

### Task 1: Config-séma — `oras`/`futas` mezők + `masodlagos_timeframek` helper

**Files:**
- Modify: `trendfigyelo/config.py:14-15` (KulcsszoTetel namedtuple), `:101-131` (`_kulcsszavak_beolvas`), új helper a modul-szintre
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `KulcsszoTetel(kifejezes, domen, tipus, racs="ora", oras=True, futas="este")` — 6-mezős namedtuple, a 2 új mező alapértelmezett (visszafelé kompatibilis minden pozicionális hívóhellyel).
  - `config.masodlagos_timeframek(tetel) -> list[str]` — `futas=="este"` → `["today 3-m", "today 12-m"]`; `futas=="reggel"` → `[RACS_IDOKERET[tetel.racs]]` (egyetlen ablak: `nap`→`"today 3-m"`, `het`→`"today 12-m"`).
- Consumes: semmi (foundation task).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py` (a fájl végére; `import`-ok között már ott van `KulcsszoTetel`, `config`):

```python
def test_kulcsszotetel_uj_mezok_default(tmp_path):
    # a régi 3-mezős konstrukció defaultot kap: racs="ora", oras=True, futas="este"
    t = KulcsszoTetel("infláció", "gazdasag", "szintmero")
    assert (t.racs, t.oras, t.futas) == ("ora", True, "este")


def test_kulcsszavak_beolvas_oras_futas(tmp_path):
    yaml = (
        "geo: HU\nnyelv: hu\nidoablak_orak: 24\nidosor_idokeret: \"now 1-d\"\n"
        "trend_idosor_max: 15\n"
        "kerespont:\n  alap_keses_mp: 6.0\n  szoras_mp: [6, 10]\n  max_probak: 4\n  backoff_mp: [30]\n"
        "kulcsszavak:\n"
        "  - {kifejezes: \"infláció\", domen: gazdasag, tipus: szintmero, racs: het, oras: false, futas: reggel}\n"
        "  - {kifejezes: \"benzin\", domen: megelhetes, tipus: szintmero, racs: ora}\n"
    )
    p = tmp_path / "c.yaml"
    p.write_text(yaml, encoding="utf-8")
    c = config.betolt(str(p))
    infl, benzin = c.osszes_kulcsszo()
    assert (infl.oras, infl.futas) == (False, "reggel")
    assert (benzin.oras, benzin.futas) == (True, "este")   # hiányzó mezők → default


def test_kulcsszavak_beolvas_rossz_oras(tmp_path):
    yaml = (
        "geo: HU\nnyelv: hu\nidoablak_orak: 24\nidosor_idokeret: \"now 1-d\"\n"
        "trend_idosor_max: 15\n"
        "kerespont:\n  alap_keses_mp: 6.0\n  szoras_mp: [6, 10]\n  max_probak: 4\n  backoff_mp: [30]\n"
        "kulcsszavak:\n"
        "  - {kifejezes: \"infláció\", domen: gazdasag, tipus: szintmero, oras: talan}\n"
    )
    p = tmp_path / "c.yaml"
    p.write_text(yaml, encoding="utf-8")
    with pytest.raises(config.KonfigHiba):
        config.betolt(str(p))


def test_kulcsszavak_beolvas_rossz_futas(tmp_path):
    yaml = (
        "geo: HU\nnyelv: hu\nidoablak_orak: 24\nidosor_idokeret: \"now 1-d\"\n"
        "trend_idosor_max: 15\n"
        "kerespont:\n  alap_keses_mp: 6.0\n  szoras_mp: [6, 10]\n  max_probak: 4\n  backoff_mp: [30]\n"
        "kulcsszavak:\n"
        "  - {kifejezes: \"infláció\", domen: gazdasag, tipus: szintmero, futas: delben}\n"
    )
    p = tmp_path / "c.yaml"
    p.write_text(yaml, encoding="utf-8")
    with pytest.raises(config.KonfigHiba):
        config.betolt(str(p))


def test_masodlagos_timeframek_este_mindketto():
    t = KulcsszoTetel("hitel", "megelhetes", "szintmero", "nap")   # futas default este
    assert config.masodlagos_timeframek(t) == ["today 3-m", "today 12-m"]


def test_masodlagos_timeframek_reggel_egy_ablak():
    het = KulcsszoTetel("infláció", "gazdasag", "szintmero", "het", False, "reggel")
    nap = KulcsszoTetel("kölcsön", "megelhetes", "szintmero", "nap", False, "reggel")
    assert config.masodlagos_timeframek(het) == ["today 12-m"]
    assert config.masodlagos_timeframek(nap) == ["today 3-m"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_config.py -p no:xdist -q -k "uj_mezok or oras_futas or rossz_oras or rossz_futas or masodlagos_timeframek"`
Expected: FAIL — `TypeError` (namedtuple nem fogad 5-6 mezőt / nincs `oras` attribútum) és `AttributeError: module 'trendfigyelo.config' has no attribute 'masodlagos_timeframek'`.

- [ ] **Step 3: Extend the namedtuple**

`trendfigyelo/config.py:14-15` — cseréld:

```python
KulcsszoTetel = namedtuple(
    "KulcsszoTetel", ["kifejezes", "domen", "tipus", "racs", "oras", "futas"],
    defaults=("ora", True, "este"))
```

- [ ] **Step 4: Add the `masodlagos_timeframek` helper**

`trendfigyelo/config.py` — a `TIMEFRAME_RACS = {...}` sor (`:28`) UTÁN:

```python
FUTASOK = {"reggel", "este"}


def masodlagos_timeframek(tetel) -> list:
    """A szó másodlagos (nap/het) időablakai a `futas` szerint.

    este → MINDKÉT hosszú ablak (3-m napi + 12-m heti), a meglévő viselkedés.
    reggel → EGY ablak, a szó `racs`-a szerint (nap→3-m, het→12-m) — az „egy-ablakos
    csak az újakra" viselkedés EGYETLEN igazságforrása; minden másodlagos-cellát
    számoló/gyűjtő kód ezen megy át.
    """
    if tetel.futas == "reggel":
        return [RACS_IDOKERET[tetel.racs]]
    return list(MASODLAGOS_TIMEFRAMEK)
```

- [ ] **Step 5: Parse + validate `oras`/`futas` in `_kulcsszavak_beolvas`**

`trendfigyelo/config.py:120-124` — a `racs` validáció UTÁN, az `ki.append(...)` ELŐTT szúrd be az `oras`/`futas` beolvasást, és bővítsd az append-et:

```python
        racs = t.get("racs", "ora")   # hiány → "ora" (visszafelé kompatibilis: mai órás viselkedés)
        if racs not in RACSOK:
            raise KonfigHiba(
                f"kulcsszavak[{i}].racs: {racs!r} — a megengedett: {sorted(RACSOK)} ({kifejezes!r})")
        oras = t.get("oras", True)    # hiány → True (a mai órás elsődleges gyűjtés)
        if not isinstance(oras, bool):
            raise KonfigHiba(
                f"kulcsszavak[{i}].oras: {oras!r} — true/false kell ({kifejezes!r})")
        futas = t.get("futas", "este")  # hiány → "este" (a mai napi/esti futás)
        if futas not in FUTASOK:
            raise KonfigHiba(
                f"kulcsszavak[{i}].futas: {futas!r} — a megengedett: {sorted(FUTASOK)} ({kifejezes!r})")
        ki.append(KulcsszoTetel(kifejezes, domen, tipus, racs, oras, futas))
```

(A `_youtube_kulcsszavak_beolvas` `:158` `KulcsszoTetel(kifejezes, domen, tipus, racs)` hívása VÁLTOZATLAN — a youtube nem kap `oras`/`futas`-t, a default `oras=True, futas="este"` ártalmatlan, a youtube-ág külön út.)

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_config.py -p no:xdist -q`
Expected: PASS (az összes config-teszt, a `test_osszes_kulcsszo_tetelekkel` is — a 3-mezős literál most is `("ora", True, "este")` defaultot kap, egyezik a parse-olttal).

- [ ] **Step 7: Commit**

```bash
git add trendfigyelo/config.py tests/test_config.py
git commit
```
Üzenet: `feat(config): kulcsszó per-szó oras/futas mezők + masodlagos_timeframek helper` + a trailerek.

---

### Task 2: Per-szó merge biztonság — karakterizációs regresszió (R1 lezárása)

**Files:**
- Test: `tests/test_reszhalmaz_merge.py` (ÚJ)
- (Nincs produkciós változás — ez a task IGAZOLJA a meglévő per-szó upsert viselkedést, amire a Task 6 épül.)

**Interfaces:**
- Consumes: `nyers_kimenet.ir_gordulo`, `nyers_kimenet.ir_masodlagos`, `lanc.frissit_lanc` (meglévő).
- Produces: egy lezárt invariáns — „részhalmaz-írás megőrzi a többi szót" —, amit a Task 6 wiring nem törhet meg észrevétlenül.

- [ ] **Step 1: Write the characterization tests**

Új fájl `tests/test_reszhalmaz_merge.py`:

```python
"""R1 karakterizáció: a nyers/lánc írók PER-SZÓ upsertek — egy részhalmaz-írás
NEM törli a fájlban lévő MÁSIK szó (pótolhatatlan) sorozatát. Ez az invariáns a
reggeli szubhalmaz-gyűjtés (Task 6) előfeltevése."""

import json
from datetime import datetime, timezone
from pathlib import Path

from trendfigyelo import nyers_kimenet, lanc


def _rekord(kif, orak, ertekek):
    idok = [datetime(2026, 8, d, 10, tzinfo=timezone.utc) for d in orak]
    return {
        "kulcsszo": kif,
        "ablak_kezdet_utc": idok[0].isoformat(),
        "ablak_veg_utc": idok[-1].isoformat(),
        "pontok": [{"idopont_utc": t.isoformat(), "ertek": e, "reszleges": False}
                   for t, e in zip(idok, ertekek)],
    }


def test_ir_gordulo_reszhalmaz_megorzi_esti_szot(tmp_path):
    # seed: 2 "esti" szó a fájlban
    nyers_kimenet.ir_gordulo(tmp_path, {"benzin": _rekord("benzin", [1, 2, 3], [10, 20, 30])})
    nyers_kimenet.ir_gordulo(tmp_path, {"hitel": _rekord("hitel", [1, 2, 3], [5, 6, 7])})
    # reggeli profil-3 szó írása CSAK önmagát
    nyers_kimenet.ir_gordulo(tmp_path, {"korrupció": _rekord("korrupció", [2, 3, 4], [40, 50, 60])})
    adat = json.loads((tmp_path / "kulcsszo_nyers.json").read_text(encoding="utf-8"))["kulcsszavak"]
    assert set(adat) == {"benzin", "hitel", "korrupció"}         # az esti szavak MEGMARADTAK
    assert adat["benzin"][0]["pontok"][0]["ertek"] == 10          # érintetlen


def test_frissit_lanc_reszhalmaz_megorzi_esti_lancot(tmp_path):
    # seed: két szó lánca
    lanc.frissit_lanc(tmp_path, {"benzin": [_rekord("benzin", [1, 2, 3], [10, 20, 30])]})
    lanc.frissit_lanc(tmp_path, {"hitel": [_rekord("hitel", [1, 2, 3], [5, 6, 7])]})
    tarolt_elott = json.loads((tmp_path / lanc.FAJL).read_text(encoding="utf-8"))["kulcsszavak"]
    assert set(tarolt_elott) == {"benzin", "hitel"}
    # reggeli szó bővítése CSAK önmagát érinti
    lanc.frissit_lanc(tmp_path, {"korrupció": [_rekord("korrupció", [2, 3, 4], [40, 50, 60])]})
    utana = json.loads((tmp_path / lanc.FAJL).read_text(encoding="utf-8"))["kulcsszavak"]
    assert set(utana) == {"benzin", "hitel", "korrupció"}         # esti láncok MEGMARADTAK
    assert utana["benzin"] == tarolt_elott["benzin"]             # bájt-azonos (dict(tarolt) megőrzés)
```

- [ ] **Step 2: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_reszhalmaz_merge.py -p no:xdist -q`
Expected: PASS azonnal (a meglévő kód MÁR per-szó upsert). Ha BÁRMELYIK bukik, ÁLLJ MEG — az R1 előfeltevés téves, a tervet felül kell vizsgálni a Task 6 előtt.

- [ ] **Step 3: Commit**

```bash
git add tests/test_reszhalmaz_merge.py
git commit
```
Üzenet: `test(merge): per-szó nyers/lánc upsert megőrzi a többi szót (R1 lezárás)` + trailerek.

---

### Task 3: `kulcsszavak.gyujt` explicit részhalmaz-paraméter

**Files:**
- Modify: `trendfigyelo/kulcsszavak.py:153-168` (`gyujt` szignatúra + a főloop forrása)
- Test: `tests/test_kulcsszavak.py`

**Interfaces:**
- Produces: `gyujt(kliens, config, most=None, tetelek=None)` — `tetelek=None` → `config.osszes_kulcsszo()` (mai viselkedés); egyébként a MEGADOTT lista szavait gyűjti (a mód órás részhalmaza).
- Consumes: semmi új.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_kulcsszavak.py` (a fájl végére). A `KemKliens` (szavankénti df, rögzíti a hívott szavakat) már létezik a fájlban — használd a meglévő mintát; ha a rögzítő attribútum neve más, igazítsd:

```python
def test_gyujt_tetelek_reszhalmaz(monkeypatch):
    from trendfigyelo.config import Config, KulcsszoTetel
    c = _config()   # 3 szó: állás, hitel, tüntetés
    reszhalmaz = [KulcsszoTetel("hitel", "megelhetes", "szintmero", "het", True, "reggel")]

    hivott = []

    class _K:
        def __init__(self):
            self.tr = SimpleNamespace(interest_over_time=None)
        def hivas(self, ag, fn, szavak, **kw):
            hivott.append(szavak[0])
            return egy_szo_df(szavak[0])

    kulcsszavak.gyujt(_K(), c, most=FIX_MOST, tetelek=reszhalmaz)
    assert hivott == ["hitel"]   # CSAK a megadott részhalmazt kérte le, nem mind a 3-at
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_kulcsszavak.py::test_gyujt_tetelek_reszhalmaz -p no:xdist -q`
Expected: FAIL — `TypeError: gyujt() got an unexpected keyword argument 'tetelek'`.

- [ ] **Step 3: Add the `tetelek` parameter**

`trendfigyelo/kulcsszavak.py:153` — a szignatúra:

```python
def gyujt(kliens, config, most=None, tetelek=None):
```

Majd `:162-168` — a `most = most or ...` UTÁN, a főloop ELŐTT állítsd be a forrást, és cseréld a loop-fejet:

```python
    most = most or seged.most_utc()
    mai_datum = most.astimezone(seged.BUDAPEST).date()
    n = config.tortenet_visszapotlas_nap
    if tetelek is None:
        tetelek = config.osszes_kulcsszo()
    pontok = []
    napi_pontok = {}
    nyers_sorozatok = {}
    for tetel in tetelek:
```

(A docstring `:154` első sorát is pontosítsd: „Minden MEGADOTT (alap: összes) kulcsszót SZÓLÓBAN lekér (now 7-d).")

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_kulcsszavak.py -p no:xdist -q`
Expected: PASS (a meglévő tesztek is — `tetelek=None` → mai viselkedés).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/kulcsszavak.py tests/test_kulcsszavak.py
git commit
```
Üzenet: `feat(kulcsszavak): gyujt explicit tetelek-részhalmaz paraméter (mód órás alhalmaza)` + trailerek.

---

### Task 4: Mód-tudatos + per-szó-ablakos másodlagos ütemezés

**Files:**
- Modify: `trendfigyelo/futtato.py:39` (`MAX_MASODLAGOS_REGGELI` konstans), `:42-76` (`masodlagos_szavak_ma`), `:79-105` (`_masodlagos_ag`), új `_oras_szavak` helper
- Test: `tests/test_masodlagos_ag.py`

**Interfaces:**
- Produces:
  - `futtato.MAX_MASODLAGOS_REGGELI = 8`
  - `futtato._oras_szavak(config, mode) -> list` — a mód órás szavai (`t.oras and t.futas == ("reggel" if mode=="reggel" else "este")`).
  - `masodlagos_szavak_ma(config, most, docs_data_mappa, limit=None, mode="este")` — a mód `futas`-részhalmazának nem-ora szavai, per-szó `masodlagos_timeframek(t)` ablakokkal; `limit` default a mód cap-je (reggel 8 / este 2).
  - `_masodlagos_ag(bejegyzesek, kliens, config, docs_data_mappa, most, mode="este")`.
- Consumes: `config.masodlagos_timeframek` (Task 1).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_masodlagos_ag.py` (a fájl végére). Az `_config`, `_nap`, `_cellak` helperek már léteznek a fájlban:

```python
def test_masodlagos_szavak_reggel_egy_ablak_es_futas_szures(tmp_path):
    from trendfigyelo.config import KulcsszoTetel
    docs = tmp_path / "d"
    docs.mkdir()
    c = _config([
        KulcsszoTetel("infláció", "gazdasag", "szintmero", "het", False, "reggel"),
        KulcsszoTetel("kölcsön", "megelhetes", "szintmero", "nap", False, "reggel"),
        KulcsszoTetel("hitel", "megelhetes", "szintmero", "nap", True, "este"),   # esti → NEM reggel
    ])
    most = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)
    cellak = [(t.kifejezes, tf) for t, tf in
              futtato.masodlagos_szavak_ma(c, most, docs, mode="reggel")]
    # reggeli szavak, EGY ablak/szó (het→12-m, nap→3-m), az esti "hitel" KIMARAD
    assert ("infláció", "today 12-m") in cellak
    assert ("kölcsön", "today 3-m") in cellak
    assert all(kif != "hitel" for kif, _ in cellak)
    assert all(kif != "infláció" or tf == "today 12-m" for kif, tf in cellak)  # nincs 3-m az inflációra


def test_masodlagos_szavak_reggel_cap_8(tmp_path):
    from trendfigyelo.config import KulcsszoTetel
    docs = tmp_path / "d"
    docs.mkdir()
    c = _config([KulcsszoTetel(f"szo{i}", "megelhetes", "szintmero", "het", False, "reggel")
                 for i in range(12)])   # 12 reggeli szó, egy-ablakos → 12 cella jogosult
    most = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)
    cellak = futtato.masodlagos_szavak_ma(c, most, docs, mode="reggel")
    assert len(cellak) == futtato.MAX_MASODLAGOS_REGGELI == 8   # a reggeli cap, NEM a napi 2


def test_masodlagos_szavak_este_valtozatlan(tmp_path):
    # az esti út: nem-ora szó MINDKÉT ablakot kapja, cap 2 (mai viselkedés)
    docs = tmp_path / "d"
    docs.mkdir()
    c = _eles_config()   # 13 valódi szó, mind esti-default
    most = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)
    cellak = futtato.masodlagos_szavak_ma(c, most, docs)   # mode default este
    assert len(cellak) == futtato.MAX_MASODLAGOS_NAPI == 2


def test_oras_szavak_mod_szures():
    from trendfigyelo.config import KulcsszoTetel
    c = _config([
        KulcsszoTetel("korrupció", "politika", "szintmero", "het", True, "reggel"),
        KulcsszoTetel("infláció", "gazdasag", "szintmero", "het", False, "reggel"),  # oras:false → KIMARAD
        KulcsszoTetel("benzin", "megelhetes", "szintmero", "ora", True, "este"),
    ])
    assert [t.kifejezes for t in futtato._oras_szavak(c, "reggel")] == ["korrupció"]
    assert [t.kifejezes for t in futtato._oras_szavak(c, "este")] == ["benzin"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_masodlagos_ag.py -p no:xdist -q -k "reggel or oras_szavak or este_valtozatlan"`
Expected: FAIL — `AttributeError: ... has no attribute 'MAX_MASODLAGOS_REGGELI'` / `_oras_szavak`; a `mode=` kwarg ismeretlen.

- [ ] **Step 3: Add the constant + `_oras_szavak` helper**

`trendfigyelo/futtato.py:39` — a `MAX_MASODLAGOS_NAPI = 2` UTÁN:

```python
MAX_MASODLAGOS_NAPI = 2

# a REGGELI másodlagos ág napi cap-je — KÜLÖN az esti 2-től. A reggeli futásnak szabad
# kapacitása van (nem verseng az esti órás gyűjtéssel), ezért a ~15 reggeli szó egy-ablakos
# másodlagosát ~2 reggel alatt körbejárja (staleness szerint).
MAX_MASODLAGOS_REGGELI = 8


def _oras_szavak(config, mode) -> list:
    """A futás órás (elsődleges now 7-d) szavai: `oras` igaz ÉS a mód `futas`-részhalmaza."""
    futas = "reggel" if mode == "reggel" else "este"
    return [t for t in config.osszes_kulcsszo() if t.oras and t.futas == futas]
```

- [ ] **Step 4: Make `masodlagos_szavak_ma` mode-aware + per-word timeframes**

`trendfigyelo/futtato.py:42-76` — cseréld a szignatúrát és a cella-építést. A `from .config import MASODLAGOS_TIMEFRAMEK` sort cseréld `masodlagos_timeframek`-re, a `limit` és `nem_oras` és `cellak` sorokat igazítsd:

```python
def masodlagos_szavak_ma(config, most, docs_data_mappa, limit=None, mode="este"):
    """A ma ütemezett (szó × timeframe) cellák — STALENESS-vezérelt, a mód `futas`-részhalmazán.

    `limit` = hány cellát adjon vissza; None → a mód cap-je (reggel MAX_MASODLAGOS_REGGELI / este
    MAX_MASODLAGOS_NAPI). A cellák a mód `futas`-részhalmazának nem-ora szavaiból épülnek, per-szó
    `masodlagos_timeframek(t)` ablakokkal (este mindkettő, reggel egy). A rangsor/fallback/IO-robusztusság
    változatlan.
    """
    from .config import masodlagos_timeframek
    futas = "reggel" if mode == "reggel" else "este"
    limit = limit or (MAX_MASODLAGOS_REGGELI if mode == "reggel" else MAX_MASODLAGOS_NAPI)
    nem_oras = [t for t in config.osszes_kulcsszo() if t.racs != "ora" and t.futas == futas]
    # CELLA = (config-index, tetel, timeframe-index, timeframe) — per-szó ablak(ok) a masodlagos_timeframek-ből
    cellak = [(i, t, tf_i, tf) for i, t in enumerate(nem_oras)
              for tf_i, tf in enumerate(masodlagos_timeframek(t))]
    fajl = Path(docs_data_mappa) / "kulcsszo_masodlagos_nyers.json"
    try:
        sorozatok = json.loads(fajl.read_text(encoding="utf-8")).get("kulcsszavak", {})
    except (OSError, ValueError) as e:
        print(f"FIGYELEM: másodlagos ütemező — a(z) {fajl.name!r} nem olvasható ({type(e).__name__}); "
              f"FALLBACK: config-index+timeframe sorrend első {limit} cellája.")
        return [(t, tf) for _, t, _, tf in cellak[:limit]]

    def _elavultsag(kif, tf):
        rekk = [r for r in (sorozatok.get(kif, []) or []) if r.get("timeframe") == tf]
        korok = [nyers_kimenet._aware_dt(r.get("lekerdezes_utc")) for r in rekk]
        legfrissebb = max((d for d in korok if d is not None), default=None)
        return float("inf") if legfrissebb is None else (most - legfrissebb).days

    rangsor = sorted(cellak, key=lambda c: (-_elavultsag(c[1].kifejezes, c[3]), c[0], c[2]))
    return [(t, tf) for _, t, _, tf in rangsor[:limit]]
```

(Megjegyzés: a fallback-üzenetben a hardcode-olt `MAX_MASODLAGOS_NAPI`-t `limit`-re cseréltük, hogy a reggeli cap is helyesen jelenjen meg.)

- [ ] **Step 5: Thread `mode` through `_masodlagos_ag`**

`trendfigyelo/futtato.py:79` és a benti `masodlagos_szavak_ma` hívás (`:90`):

```python
def _masodlagos_ag(bejegyzesek, kliens, config, docs_data_mappa, most, mode="este"):
```
```python
        for tetel, timeframe in masodlagos_szavak_ma(config, most, docs_data_mappa, mode=mode):
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_masodlagos_ag.py tests/test_masodlagos_only.py -p no:xdist -q`
Expected: PASS (az esti/meglévő tesztek is — a `mode` default `"este"`, minden meglévő szó `futas=="este"`, `masodlagos_timeframek(este)` = mindkét ablak → azonos cella-halmaz).

- [ ] **Step 7: Commit**

```bash
git add trendfigyelo/futtato.py tests/test_masodlagos_ag.py
git commit
```
Üzenet: `feat(masodlagos): mód-tudatos ütemezés + per-szó ablak + reggeli budget (8)` + trailerek.

---

### Task 5: Mód-tudatos hívás-plafon

**Files:**
- Modify: `trendfigyelo/futtato.py:26-34` (`tervezett_hivasszam`), `:568-570` (`_szamitott_plafon`), `:586-596` (`_plafon`), `:607-616` (`main`)
- Test: `tests/test_futtato.py`

**Interfaces:**
- Produces:
  - `tervezett_hivasszam(config, mode="este") -> int` = `2 + trend_idosor_max + trend_idosor_rekesz_max + len(_oras_szavak(config, mode))`.
  - `_szamitott_plafon(config, mode="este")` = `(tervezett_hivasszam(config, mode) + <mód másodlagos cap>) * max_probak`.
  - `_plafon(config, mode="este", override=None)`.
- Consumes: `_oras_szavak`, `MAX_MASODLAGOS_REGGELI` (Task 4).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_futtato.py` (a fájl végére):

```python
def test_tervezett_hivasszam_mod_tudatos():
    from trendfigyelo.config import KulcsszoTetel
    c = _config([
        KulcsszoTetel("korrupció", "politika", "szintmero", "het", True, "reggel"),  # reggeli órás
        KulcsszoTetel("infláció", "gazdasag", "szintmero", "het", False, "reggel"),  # reggeli, NEM órás
        KulcsszoTetel("benzin", "megelhetes", "szintmero", "ora", True, "este"),     # esti órás
        KulcsszoTetel("hitel", "megelhetes", "szintmero", "nap", True, "este"),      # esti órás
    ])
    # este: 2 esti órás szó; reggel: 1 reggeli órás szó (infláció oras:false kimarad)
    assert futtato.tervezett_hivasszam(c, "este") == 2 + c.trend_idosor_max + c.trend_idosor_rekesz_max + 2
    assert futtato.tervezett_hivasszam(c, "reggel") == 2 + c.trend_idosor_max + c.trend_idosor_rekesz_max + 1


def test_szamitott_plafon_reggel_a_reggeli_budgettel():
    from trendfigyelo.config import KulcsszoTetel
    c = _config([KulcsszoTetel("korrupció", "politika", "szintmero", "het", True, "reggel")])
    vart = (futtato.tervezett_hivasszam(c, "reggel") + futtato.MAX_MASODLAGOS_REGGELI) * c.max_probak
    assert futtato._szamitott_plafon(c, "reggel") == vart
    # este a napi cap-pel, VÁLTOZATLAN
    vart_este = (futtato.tervezett_hivasszam(c, "este") + futtato.MAX_MASODLAGOS_NAPI) * c.max_probak
    assert futtato._szamitott_plafon(c, "este") == vart_este
```

(Megjegyzés: a meglévő `test_tervezett_hivasszam_szolo`/`_teljes_config` a `mode` default `"este"`-n fut; a szavaik `oras=True, futas="este"` → `_oras_szavak(este)` = mind → változatlan érték. Ha egy meglévő assert szó szerint `len(config.osszes_kulcsszo())`-t vár, az is egyezik, mert minden szó esti-órás.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_futtato.py -p no:xdist -q -k "mod_tudatos or reggeli_budgettel"`
Expected: FAIL — `tervezett_hivasszam()` / `_szamitott_plafon()` nem fogad `mode` argumentumot.

- [ ] **Step 3: Make `tervezett_hivasszam` mode-aware**

`trendfigyelo/futtato.py:26-34` — cseréld:

```python
def tervezett_hivasszam(config, mode="este") -> int:
    """A hibamentes (429 nélküli) futás várható Google-hívásszáma az ágstruktúrából, a MÓD szerint.

    felkapott_api (1) + felkapott_rss (1) + idosor (≤ trend_idosor_max) + idosor_rekesz
    (≤ trend_idosor_rekesz_max) + kulcsszo (SZÓLÓ: a mód órás szavai, szavankénti egy hívás).
    """
    return (2 + config.trend_idosor_max + config.trend_idosor_rekesz_max
            + len(_oras_szavak(config, mode)))
```

- [ ] **Step 4: Make `_szamitott_plafon` + `_plafon` mode-aware**

`trendfigyelo/futtato.py:568-570`:

```python
def _szamitott_plafon(config, mode="este"):
    """A strukturális maximum: minden logikai hívás mind a max_probak próbát kimeríti (a mód szerint)."""
    masodlagos_cap = MAX_MASODLAGOS_REGGELI if mode == "reggel" else MAX_MASODLAGOS_NAPI
    return (tervezett_hivasszam(config, mode) + masodlagos_cap) * config.max_probak
```

`trendfigyelo/futtato.py:586-596` — `_plafon` kapjon `mode`-ot és adja tovább:

```python
def _plafon(config, mode="este", override=None):
    """A tényleges hívás-plafon (a mód szerint). Az override CSAK CSÖKKENTHET (min) — a biztonsági
    szelepet egy bent felejtett/magas env NE kapcsolhassa ki csendben. Ha az env be van állítva, HANGOS
    FIGYELEM (akkor is, ha no-op), hogy ne lehessen véletlenül bent felejteni."""
    szamitott = _szamitott_plafon(config, mode)
    if override is None:
        return szamitott
    eff = min(szamitott, override)
    jelzo = "CSÖKKENTVE" if eff < szamitott else f"NO-OP (a számított {szamitott} marad)"
    print(f"FIGYELEM: PLAFON_OVERRIDE={override} beállítva — effektív hívás-plafon {eff} ({jelzo}).")
    return eff
```

- [ ] **Step 5: Thread `mode` in `main`**

`trendfigyelo/futtato.py:614-615`:

```python
    kliens = Kliens(config, plafon=_plafon(config, mode, _plafon_override_env()))
    print(f"Mód: {mode} · Várható Google-hívásszám (429 nélkül): ~{tervezett_hivasszam(config, mode)}")
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_futtato.py -p no:xdist -q`
Expected: PASS (a plafon/hívásszám meglévő tesztjei is).

- [ ] **Step 7: Commit**

```bash
git add trendfigyelo/futtato.py tests/test_futtato.py
git commit
```
Üzenet: `feat(plafon): mód-tudatos hívás-plafon (reggeli budget + órás részhalmaz)` + trailerek.

---

### Task 6: `futtat()` reggeli kulcsszó-integráció

**Files:**
- Modify: `trendfigyelo/futtato.py:337-342` (elsődleges ág), `:351-352` (másodlagos ág hívás), `:426-434` (nyers/lánc írás)
- Test: `tests/test_futtato.py`

**Interfaces:**
- Consumes: `_oras_szavak` (Task 4), `kulcsszavak.gyujt(..., tetelek=)` (Task 3), `_masodlagos_ag(..., mode=)` (Task 4), a per-szó nyers/lánc upsert (R1/Task 2).
- Produces: a `futtat(config, kliens, ...ok, mode)` reggeli módban a reggeli órás részhalmazt gyűjti, a reggeli másodlagost futtatja, és a reggeli szavakat PER-SZÓ upsertli a nyers/lánc fájlokba az esti szavak érintetlenül hagyásával. `tortenet`/`regresszió` reggel VÁLTOZATLANUL kimarad (R2).

- [ ] **Step 1: Write the failing integration tests**

Add to `tests/test_futtato.py` (a fájl végére). Használd a fájl meglévő `KulcsszoAdatKliens`/df-gyártó mintáit; ha a fake-kliens neve/alakja más, igazítsd. A cél a MEGFIGYELHETŐ végállapot (lemez), nem a belső hívások:

```python
def test_futtat_reggel_ir_profil3_nyerset_esti_szo_megmarad(tmp_path):
    """Reggeli futás: a profil-3 (reggeli órás) szó bekerül a kulcsszo_nyers.json-ba PER-SZÓ upserttel,
    az előzőleg beírt esti szó sorozata ÉRINTETLEN marad."""
    from trendfigyelo import nyers_kimenet
    from trendfigyelo.config import KulcsszoTetel
    from datetime import datetime, timezone

    ddir = tmp_path / "docs" / "data"
    ddir.mkdir(parents=True)
    # seed: egy esti szó pótolhatatlan órás sorozata már a fájlban
    def _rek(kif, napok, ert):
        idok = [datetime(2026, 8, d, 10, tzinfo=timezone.utc) for d in napok]
        return {"kulcsszo": kif, "ablak_kezdet_utc": idok[0].isoformat(),
                "ablak_veg_utc": idok[-1].isoformat(),
                "pontok": [{"idopont_utc": t.isoformat(), "ertek": e, "reszleges": False}
                           for t, e in zip(idok, ert)]}
    nyers_kimenet.ir_gordulo(ddir, {"benzin": _rek("benzin", [1, 2, 3], [10, 20, 30])})

    c = _config([
        KulcsszoTetel("korrupció", "politika", "szintmero", "het", True, "reggel"),  # reggeli órás (profil-3)
        KulcsszoTetel("benzin", "megelhetes", "szintmero", "ora", True, "este"),     # esti órás
    ])
    most = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)
    futtato.futtat(c, KulcsszoAdatKliens(), tmp_path / "adatok", ddir, most=most, mode="reggel")

    adat = json.loads((ddir / "kulcsszo_nyers.json").read_text(encoding="utf-8"))["kulcsszavak"]
    assert "benzin" in adat                              # az esti szó ÉRINTETLEN (nem csonkolt)
    assert adat["benzin"][0]["pontok"][0]["ertek"] == 10
    assert "korrupció" in adat                           # a reggeli profil-3 szó BEKERÜLT


def test_futtat_reggel_nem_ir_tortenetet(tmp_path):
    """R2: a reggeli mód NEM ír tortenet.json-t (a nap-clobber elkerülése)."""
    from trendfigyelo.config import KulcsszoTetel
    from datetime import datetime, timezone
    ddir = tmp_path / "docs" / "data"
    ddir.mkdir(parents=True)
    c = _config([KulcsszoTetel("korrupció", "politika", "szintmero", "het", True, "reggel")])
    most = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)
    futtato.futtat(c, KulcsszoAdatKliens(), tmp_path / "adatok", ddir, most=most, mode="reggel")
    assert not (ddir / "tortenet.json").exists()
```

Ha a `KulcsszoAdatKliens` fake nem ad órás df-et minden kért szóra, bővítsd, hogy a `_oras_szavak(c,"reggel")` szavaira nem-üres, ablakon-belüli órás df-et adjon (legalább 2 lezárt nap, hogy a `utolso_teljes_nap`/`_nyers_sorozat` érvényes rekordot gyártson).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_futtato.py -p no:xdist -q -k "reggel_ir_profil3 or reggel_nem_ir_tortenetet"`
Expected: FAIL — a jelenlegi reggeli ág üríti a kulcsszó-adatot (`kulcsszo_nyers` nem íródik), így `"korrupció"` hiányzik.

- [ ] **Step 3: Wire the primary (hourly) branch for both modes**

`trendfigyelo/futtato.py:337-342` — cseréld a `csak_felkapott` elágazást a mód órás részhalmazának gyűjtésére:

```python
        # elsődleges (órás now 7-d) ág — a MÓD órás részhalmazára (reggel: profil-3; este: a 13 szó)
        oras_szavak = _oras_szavak(config, mode)
        if oras_szavak:
            kulcsszo_eredmeny = _ag(bejegyzesek, kliens, "kulcsszo",
                                lambda: kulcsszavak.gyujt(kliens, config, most, tetelek=oras_szavak))
            kulcsszo_pontok, kulcsszo_napi_pontok, kulcsszo_nyers = kulcsszo_eredmeny or ([], {}, {})
        else:
            kulcsszo_pontok, kulcsszo_napi_pontok, kulcsszo_nyers = [], {}, {}
```

- [ ] **Step 4: Run the secondary branch in both modes**

`trendfigyelo/futtato.py:351-352` — cseréld a `if not csak_felkapott:` őrt feltétlen, mód-átadó hívásra:

```python
        # másodlagos (nap/het) ág — MINDKÉT mód a saját futás-részhalmazára, mód-specifikus budgettel
        _masodlagos_ag(bejegyzesek, kliens, config, docs_data_mappa, most, mode=mode)
```

- [ ] **Step 5: Write nyers/lánc for both modes, per-word, chaining only the fresh subset**

`trendfigyelo/futtato.py:426-434` — cseréld az `if kulcsszo_nyers and not csak_felkapott:` blokkot úgy, hogy MINDKÉT módban fusson, és a lánc CSAK a friss (e futás) szavakat bővítse:

```python
    # nyers órás sorozat — MINDKÉT mód a SAJÁT órás részhalmazát írja PER-SZÓ upserttel (a másik mód
    # szavai érintetlenek: ir_gordulo/frissit_lanc read-modify-write). Üres sorozat NE írjon fájlt.
    if kulcsszo_nyers:
        nyers_kimenet.ir_gordulo(docs_data_mappa, kulcsszo_nyers)
        # LANC-ORAS (§8.2): CSAK a FRISS (e futás) szavak láncát bővítjük a RETENÁLT ablakaikból; a másik
        # mód szavainak lánca érintetlen (frissit_lanc: ki=dict(tarolt)). Származtatott, VÉDETT.
        try:
            _retenalt = json.loads((docs_data_mappa / "kulcsszo_nyers.json").read_text(encoding="utf-8")).get("kulcsszavak", {})
            _friss = {k: v for k, v in _retenalt.items() if k in kulcsszo_nyers}
            lanc.frissit_lanc(docs_data_mappa, _friss, marker=config.modszertan_valtas)
        except Exception as e:
            print(f"FIGYELEM: az órás lánc frissítése kimaradt — nem blokkolja az adatmentést ({e}).")
```

(A `tortenet` őre `:418` `if kulcsszo_napi_pontok and not csak_felkapott:` VÁLTOZATLAN — R2. A `regresszió` `:449` `if csak_felkapott: pass` VÁLTOZATLAN — R4, az esti passz fedi a reggeli szavakat. A `napi_ir` `:421-424` VÁLTOZATLAN. A `legfrissebb` `:406-411` VÁLTOZATLAN — R3.)

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_futtato.py -p no:xdist -q`
Expected: PASS. Ha egy meglévő reggel-módú teszt azt állította, hogy a reggeli futás NEM logol `kulcsszo`/`kulcsszo_masodlagos` ág-sort, az MOST már logol (viselkedésváltozás): frissítsd az adott tesztet, hogy a reggeli futás órás+másodlagos ág-sorokat vár (a naplóban `siker`/`blokkolva` a fake-kliens szerint). Grep: `grep -rn "reggel" tests/test_futtato.py`.

- [ ] **Step 7: Full backend suite (integration guard)**

Run: `.venv/bin/python -m pytest -p no:xdist -q`
Expected: PASS az egész backend-suite (a Task 1–6 együtt).

- [ ] **Step 8: Commit**

```bash
git add trendfigyelo/futtato.py tests/test_futtato.py
git commit
```
Üzenet: `feat(futtato): reggeli kulcsszó-integráció — órás részhalmaz + másodlagos + per-szó nyers/lánc` + trailerek.

---

### Task 7: `config.yaml` — 15 új szó + a 13 meglévő átcímkézése

**Files:**
- Modify: `config.yaml:22-35` (a `kulcsszavak:` blokk)
- Test: `tests/test_config.py` (éles config betöltés-igazolás)

**Interfaces:**
- Consumes: a Task 1 séma (`oras`/`futas` parse).
- Produces: a 28-szavas éles config (13 átcímkézve + 15 új a profilokkal).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py` (a fájl végére) — az ÉLES `config.yaml`-t tölti (a repo gyökeréből):

```python
def test_eles_config_28_szo_profilokkal():
    c = config.betolt("config.yaml")
    szavak = {t.kifejezes: t for t in c.osszes_kulcsszo()}
    assert len(szavak) == 28
    # 5 új domén jelen van, a régi szórt domének eltűntek
    domenek = {t.domen for t in c.osszes_kulcsszo()}
    assert domenek == {"megelhetes", "egeszsegugy", "oktatas", "gazdasag", "politika"}
    # profil 1 (lassú): oras:false, racs:het, futas:reggel
    assert (szavak["infláció"].oras, szavak["infláció"].racs, szavak["infláció"].futas) == (False, "het", "reggel")
    # profil 2 (közepes): oras:false, racs:nap
    assert (szavak["kölcsön"].oras, szavak["kölcsön"].racs, szavak["kölcsön"].futas) == (False, "nap", "reggel")
    # profil 3 (csúcs): oras:true, racs:het
    assert (szavak["korrupció"].oras, szavak["korrupció"].racs, szavak["korrupció"].futas) == (True, "het", "reggel")
    # a meglévő esti szó: default oras:true, futas:este, új domén-címke
    assert (szavak["benzin"].oras, szavak["benzin"].futas, szavak["benzin"].domen) == (True, "este", "megelhetes")
    assert szavak["tüntetés"].domen == "politika"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_config.py::test_eles_config_28_szo_profilokkal -p no:xdist -q`
Expected: FAIL — 13 szó, régi domének.

- [ ] **Step 3: Rewrite the `kulcsszavak:` block in `config.yaml`**

`config.yaml:22-35` — cseréld a teljes `kulcsszavak:` listát (a fölötte lévő megjegyzéseket hagyd, a `youtube:` blokkot NE érintsd):

```yaml
kulcsszavak:
  # — Meglévő 13 szó: CSAK a domen-címke változik az 5 új doménre (oras/futas default: true/este) —
  - {kifejezes: "állás",        domen: megelhetes,  tipus: szintmero,    racs: het}
  - {kifejezes: "kormányablak", domen: politika,    tipus: szintmero,    racs: het}
  - {kifejezes: "eladó lakás",  domen: megelhetes,  tipus: szintmero,    racs: nap}
  - {kifejezes: "albérlet",     domen: megelhetes,  tipus: szintmero,    racs: nap}
  - {kifejezes: "akciós újság", domen: megelhetes,  tipus: szintmero,    racs: het}
  - {kifejezes: "benzin",       domen: megelhetes,  tipus: szintmero,    racs: ora}
  - {kifejezes: "nyaralás",     domen: megelhetes,  tipus: szintmero,    racs: nap}
  - {kifejezes: "kórház",       domen: egeszsegugy, tipus: szintmero,    racs: het}
  - {kifejezes: "betegség",     domen: egeszsegugy, tipus: szintmero,    racs: nap}
  - {kifejezes: "napelem",      domen: megelhetes,  tipus: hibrid,       racs: nap}
  - {kifejezes: "nyugdíj",      domen: megelhetes,  tipus: hibrid,       racs: ora}
  - {kifejezes: "hitel",        domen: megelhetes,  tipus: szintmero,    racs: nap}
  - {kifejezes: "tüntetés",     domen: politika,    tipus: esemenyjelzo, racs: het}
  # — 15 új „társadalmi feszültség" szó, REGGELI gyűjtésben, egy-ablakos profilokkal —
  # Profil 1 (lassú strukturális): oras:false, racs:het → csak 12-m heti
  - {kifejezes: "infláció",       domen: gazdasag,    tipus: szintmero,    racs: het, oras: false, futas: reggel}
  - {kifejezes: "rezsi",          domen: megelhetes,  tipus: szintmero,    racs: het, oras: false, futas: reggel}
  - {kifejezes: "fizetés",        domen: megelhetes,  tipus: szintmero,    racs: het, oras: false, futas: reggel}
  - {kifejezes: "segély",         domen: megelhetes,  tipus: szintmero,    racs: het, oras: false, futas: reggel}
  - {kifejezes: "várólista",      domen: egeszsegugy, tipus: szintmero,    racs: het, oras: false, futas: reggel}
  - {kifejezes: "háziorvos",      domen: egeszsegugy, tipus: szintmero,    racs: het, oras: false, futas: reggel}
  - {kifejezes: "műtét",          domen: egeszsegugy, tipus: szintmero,    racs: het, oras: false, futas: reggel}
  - {kifejezes: "iskola",         domen: oktatas,     tipus: szintmero,    racs: het, oras: false, futas: reggel}
  - {kifejezes: "munkanélküliség", domen: gazdasag,   tipus: szintmero,    racs: het, oras: false, futas: reggel}
  - {kifejezes: "csőd",           domen: gazdasag,    tipus: szintmero,    racs: het, oras: false, futas: reggel}
  # Profil 2 (közepes momentum): oras:false, racs:nap → csak 3-m napi
  - {kifejezes: "kölcsön",        domen: megelhetes,  tipus: szintmero,    racs: nap, oras: false, futas: reggel}
  - {kifejezes: "sürgősségi",     domen: egeszsegugy, tipus: szintmero,    racs: nap, oras: false, futas: reggel}
  # Profil 3 (esemény/csúcs): oras:true, racs:het → 7-d órás + 12-m
  - {kifejezes: "pedagógus",      domen: oktatas,     tipus: szintmero,    racs: het, oras: true,  futas: reggel}
  - {kifejezes: "korrupció",      domen: politika,    tipus: szintmero,    racs: het, oras: true,  futas: reggel}
  - {kifejezes: "kormány",        domen: politika,    tipus: szintmero,    racs: het, oras: true,  futas: reggel}
```

- [ ] **Step 3b: Fix the two existing real-config tests that the 13→28 change breaks**

A `config.yaml` 28-szavassá tétele két MEGLÉVŐ, éles-configot olvasó tesztet elront — ezeket UGYANEBBEN a taskban javítsd:

1. `tests/test_config.py:338` (`test_youtube_szekcio_12_szo_es_racs` vége): `assert len(c.osszes_kulcsszo()) == 13` → `assert len(c.osszes_kulcsszo()) == 28`.
2. `tests/test_regresszio.py:240` környéki teszt (real `docs/data/kulcsszo_nyers.json` + `tortenet.json` + `betolt()`): a `regresszio_szamit` a config ÉS a tortenet szavainak UNIÓJÁN iterál (`regresszio.py:302`), így a 15 új config-szó is bekerül a `kk`-ba, DE nincs éles adatuk (`meres_kezdete=None`). A per-szó adat-állítások (`v["meres_kezdete"] == "2026-07-30"`, `v["aktiv"] is True`, intervallum-állítások) CSAK az on-disk fixture-adattal rendelkező szavakra igazak. Szűkítsd a per-szó ciklust az on-disk `nyers["kulcsszavak"]` kulcsaira (a 13 valós szó), pl. a ciklus elején `if szo not in nyers["kulcsszavak"]: continue`. A `len(kk) == len(cfg.osszes_kulcsszo())` állítás VÁLTOZATLAN marad (28 == 28, mert a `regresszio_szamit` minden config-szóra ad rekordot). NE lazítsd fel a 13 valós szó ellenőrzését.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_config.py tests/test_regresszio.py -p no:xdist -q`
Expected: PASS (az új `test_eles_config_28_szo_profilokkal` ÉS a két javított meglévő teszt is).

- [ ] **Step 5: Verify the plafon/hívásszám sanity for both modes**

Run:
```bash
.venv/bin/python -c "from trendfigyelo import futtato; from trendfigyelo.config import betolt; c=betolt('config.yaml'); print('reggel', futtato.tervezett_hivasszam(c,'reggel'), futtato._szamitott_plafon(c,'reggel')); print('este', futtato.tervezett_hivasszam(c,'este'), futtato._szamitott_plafon(c,'este'))"
```
Expected: `reggel 25 132` (2 + 15 + 5 + 3 profil-3 órás = 25; (25+8)×4 = 132) és `este 35 148` (2 + 15 + 5 + 13 esti-órás = 35; (35+2)×4 = 148 — az esti plafon VÁLTOZATLAN a mai értékhez képest). Ha az órás-szó-szám eltér, ellenőrizd az `oras` mezőket a configban. (A pontos számok tájékoztatók; a lényeg, hogy mindkét mód VÉGES, az esti változatlan, és a reggeli a kisebb.)

- [ ] **Step 6: Commit**

```bash
git add config.yaml tests/test_config.py
git commit
```
Üzenet: `feat(config): 15 új reggeli társadalmi-feszültség szó + 13 átcímkézés (5 domén)` + trailerek.

---

### Task 8: Frontend — 5 új domén

**Files:**
- Modify: `docs/js/app.js:577-584` (`DOMEN_MAGYAR`, `DOMEN_SORREND`)
- Test: `e2e/kulcsszo.spec.js` (Playwright — a testDir `e2e/`, NEM `tests/e2e/`)

**Interfaces:**
- Consumes: a backend `domen` szabad szövege (a config-slugok).
- Produces: az 5 új domén magyar címkével + megjelenítési sorrendben; ismeretlen domén továbbra is „Egyéb".

**RULING PF-3 — MERGE, ne CSERÉLD (kritikus, plan-defektus javítás):** A meglévő `e2e/kulcsszo.spec.js` (~57 hivatkozás) és `e2e/attekinto.spec.js` (~17) a RÉGI domén-slugokat (`munkaeropiac`, `lakhatas`, `fogyasztas`, `egeszseg`, `kozelet`, …) használja fixture-ként, és a magyar címkéiket (`"Lakhatás"`, „Munkaerőpiac") állítja (pl. `e2e/kulcsszo.spec.js:205-206`). Ha a régi slugokat KIVESSZÜK a `DOMEN_MAGYAR`/`DOMEN_SORREND`-ből, ezek a tesztek eltörnek (a szavak az „Egyéb"-be esnének). Ezért az 5 újat HOZZÁADJUK a régi 9-hez (nem cseréljük le): a régi slugok a configban már holtak (a Task 7 után egy config-szó sem használja őket), de a frontend-térképben MEGMARADNAK, hogy az e2e mechanizmus-tesztek zöldek maradjanak. A produkcióban csak az 5 új domén jelenik meg (a config csak azokat használja); a régi slot-ok szó híján kimaradnak a renderből. A `null`→„Egyéb" vödör a lista VÉGÉN marad.

- [ ] **Step 1: Write the failing Playwright test**

A `e2e/kulcsszo.spec.js` `page.route`-mockolást használ a `mock(page, {regObj, nyersObj, ...})` helperrel; a `reg({...})` és `regSzo({domen})` fixture-építők egy szó regresszió-rekordját adják (default valid `1_het` → rajzolható), a `nyers({...})`/`nyersRekord(szó)` a nyers ablakot. A domén-csoport DOM: `#kulcsszo-blokk .domen-csoport[data-domen="<slug>"] h3.domen-fejlec` a magyar címkét adja. Adj egy ÚJ tesztet a fájl végére (a meglévő 1. teszt mintájára), egy ÚJ-domén szóval:

```javascript
// ── ÚJ: társadalmi-feszültség domén magyar címke (megelhetes/politika) ──────────────────────────
test("N. új társadalmi-feszültség domének magyar címkével jelennek meg", async ({ page }) => {
  await mock(page, {
    regObj: reg({
      "korrupció": regSzo({ domen: "politika" }),
      "hitel": regSzo({ domen: "megelhetes" }),
    }),
    nyersObj: nyers({ "korrupció": [nyersRekord("korrupció")], "hitel": [nyersRekord("hitel")] }),
  });
  await page.goto("/");
  await expect(page.locator(`${K} .domen-csoport[data-domen="politika"] h3.domen-fejlec`))
    .toHaveText("Politikai elégedetlenség");
  await expect(page.locator(`${K} .domen-csoport[data-domen="megelhetes"] h3.domen-fejlec`))
    .toHaveText("Megélhetési problémák");
});
```

(A `K` konstans (`"#kulcsszo-blokk"`) és a `mock`/`reg`/`regSzo`/`nyers`/`nyersRekord` helperek már a fájlban vannak. A pontos `test("N. ...")` sorszámot igazítsd a fájl számozásához.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx playwright test --workers=1 e2e/kulcsszo.spec.js -g "társadalmi-feszültség"`
Expected: FAIL — a `politika`/`megelhetes` slug nincs a `DOMEN_MAGYAR`-ban, a szavak az „Egyéb" (`__egyeb__`) csoportba esnek, így nincs `.domen-csoport[data-domen="politika"]` a helyes címkével.

- [ ] **Step 3: MERGE the 5 new domains INTO `DOMEN_MAGYAR` + `DOMEN_SORREND` (keep the old 9)**

`docs/js/app.js:577-584` — cseréld a két konstanst úgy, hogy az 5 ÚJ ELÖL kerül be, a régi 9 MEGMARAD utána (a `null` a `SORREND` végén marad):

```javascript
const DOMEN_MAGYAR = {
  // 5 aktív társadalmi-feszültség domén — a config (Task 7 óta) EZEKET használja
  megelhetes: "Megélhetési problémák", egeszsegugy: "Egészségügyi problémák",
  oktatas: "Oktatási problémák", gazdasag: "Gazdasági bizonytalanság",
  politika: "Politikai elégedetlenség",
  // régi slugok — a config már NEM használja őket, de az e2e domén-fixture-ök igen → MEGTARTVA
  munkaeropiac: "Munkaerőpiac", kozigazgatas: "Közigazgatás", lakhatas: "Lakhatás",
  fogyasztas: "Fogyasztás", egeszseg: "Egészség", energia: "Energia",
  jovedelem: "Jövedelem", haztartasi_penzugy: "Háztartási pénzügy", kozelet: "Közélet",
};
// megjelenítési sorrend; a null (besorolatlan/eltávolított szó) az "Egyéb" csoportba, a lista VÉGÉRE
const DOMEN_SORREND = ["megelhetes", "egeszsegugy", "oktatas", "gazdasag", "politika",
  "munkaeropiac", "kozigazgatas", "lakhatas", "fogyasztas", "egeszseg",
  "energia", "jovedelem", "haztartasi_penzugy", "kozelet", null];
```

- [ ] **Step 4: Run the tests to verify they pass (new test AND the whole kulcsszo/attekinto suites)**

Run: `npx playwright test --workers=1 e2e/kulcsszo.spec.js e2e/attekinto.spec.js`
Expected: PASS — az új teszt zöld, ÉS a régi-slug domén-fixture-öket használó meglévő tesztek (pl. `kulcsszo.spec.js` 1. teszt: „Lakhatás"/„Munkaerőpiac") változatlanul zöldek (a merge miatt). Ha bármelyik meglévő e2e piros, az a merge hibája — ellenőrizd, hogy MINDEN régi slug bent maradt.

- [ ] **Step 5: Commit**

```bash
git add docs/js/app.js e2e/kulcsszo.spec.js
git commit
```
Üzenet: `feat(frontend): 5 új társadalmi-feszültség domén (címke + sorrend, régi slugok megtartva)` + trailerek.

---

### Task 9: `elemzo`/regresszió domén-agnoszticitás igazolása (R4)

**Files:**
- Test: `tests/test_regresszio.py` VAGY `tests/test_elemzo.py` (a meglévő regresszió/elemzés teszt-fájl; keresd: `grep -rln "regresszio_szamit\|elemzo" tests/`)
- (Nincs produkciós változás elvárva — ha a teszt HIBÁT talál, az önálló bugfix-taskot igényel.)

**Interfaces:**
- Consumes: `regresszio.regresszio_szamit` (a teljes nyers fájlt olvassa), `elemzo` (domén-vezérelt).
- Produces: igazolás, hogy egy tortenet NÉLKÜLI, új-domén nyers-szó (reggeli profil-3) regresszió-rekordot kap crash nélkül, `meres_kezdete=null` kecses degradációval.

- [ ] **Step 1: Write the characterization test**

Add a meglévő regresszió-teszt-fájlhoz. Építs egy minimális `nyers` map-et egy új-domén szóval (`korrupció`/`politika`), ÜRES `tortenet`-tel, és hívd a `regresszio_szamit`-ot; állítsd, hogy a szó bekerül a kimenetbe, és nem dob:

```python
def test_regresszio_uj_domen_szo_tortenet_nelkul(tmp_path):
    from trendfigyelo import regresszio, lanc
    from trendfigyelo.config import Config, KulcsszoTetel
    from datetime import datetime, timezone
    c = Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        alap_keses_mp=3.0, szoras_mp=(3, 7), max_probak=4, backoff_mp=[30],
        trend_idosor_max=15, proxy=None,
        kulcsszavak=[KulcsszoTetel("korrupció", "politika", "szintmero", "het", True, "reggel")],
    )
    idok = [datetime(2026, 8, d, 10, tzinfo=timezone.utc) for d in range(1, 8)]
    nyers = {"kulcsszavak": {"korrupció": [{
        "kulcsszo": "korrupció", "ablak_kezdet_utc": idok[0].isoformat(),
        "ablak_veg_utc": idok[-1].isoformat(),
        "pontok": [{"idopont_utc": t.isoformat(), "ertek": 40 + i, "reszleges": False}
                   for i, t in enumerate(idok)]}]}}
    ki = regresszio.regresszio_szamit(nyers, {}, c, idok[-1].isoformat(), lanc_map={})
    # a szó bekerül; a domén szabad szöveg, nincs bedrótozott régi-domén feltevés
    assert "korrupció" in ki.get("kulcsszavak", {})
    assert ki["kulcsszavak"]["korrupció"].get("domen") == "politika"
```

(Igazítsd a `regresszio_szamit` tényleges szignatúrájához / visszatérési alakjához — olvasd be a `trendfigyelo/regresszio.py`-t a pontos kulcsokért, mielőtt a tesztet írod. A lényegi állítás: új-domén + tortenet-hiány → nincs crash, a szó megjelenik, a domén átmegy.)

- [ ] **Step 2: Run the test**

Run: `.venv/bin/python -m pytest tests/test_regresszio.py -p no:xdist -q -k "uj_domen"`
Expected: PASS azonnal (R4 igaz). Ha bukik/dob, az VALÓDI bug — állj meg, jelentsd a review-nak, és nyiss önálló bugfix-lépést a `regresszio.py`-ban a terv folytatása előtt.

- [ ] **Step 3: Commit**

```bash
git add tests/test_regresszio.py
git commit
```
Üzenet: `test(regresszio): új-domén nyers-szó tortenet nélkül regresszió-rekordot kap (R4)` + trailerek.

---

### Task 10: Leltár + invariáns frissítés

**Files:**
- Modify: `docs/superpowers/leltar.md` (a krónika-sor + invariáns)

**Interfaces:**
- Consumes: a Task 1–9 leszállított egységei.
- Produces: a leltár krónika-bejegyzés a reggeli kulcsszó-ágról + a frissített törzs/kész invariáns.

- [ ] **Step 1: Read the current invariant**

Run: `grep -nE "invariáns|törzs|kész" docs/superpowers/leltar.md | tail -5`
Olvasd ki a LEGUTOLSÓ krónika-sor élő invariánsát (a fejléc-összegzés `:19-24` elavult 08-26-os pillanatkép — NE azt használd).

- [ ] **Step 2: Append a chronicle entry**

Adj egy új krónika-sort a `leltar.md`-hez a reggeli kulcsszó-ág leszállításáról: mit épített (per-szó `oras`/`futas`, mód-tudatos gyűjtés/plafon, 15 új szó / 5 domén, frontend-domének), a kulcs-invariáns (a per-szó nyers/lánc upsert megőrzi az esti szavakat), a suite-eredmény (a Task 6/8 utáni zöld pytest + Playwright darabszám), és a frissített kész/törzs/invariáns számláló (a Step 1 értékéből levezetve).

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/leltar.md
git commit
```
Üzenet: `doc(leltar): reggeli kulcsszó-feszültség-ág kész + invariáns` + trailerek.

---

## Self-Review

**1. Spec coverage:**
- §A Config-séma (KulcsszoTetel + parse + `masodlagos_timeframek`) → Task 1. ✓
- §B Elsődleges órás `oras`-szűrés → Task 3 (`gyujt` részhalmaz) + Task 6 (`_oras_szavak` wiring). ✓
- §C Futtatás reggel-részhalmaz (elsődleges/másodlagos/nyers-lánc) → Task 6; a `csak_felkapott` kapuk kezelve (elsődleges/másodlagos/nyers-lánc módosítva, tortenet/regresszió/legfrissebb TUDATOSAN érintetlen R2/R3/R4 alapján). ✓
- §D `legfrissebb` merge → **feloldva (R3): a blokk halott a megjelenítéshez, nincs teendő** — dokumentálva a kockázat-szekcióban. ✓
- §E Reggeli budget + mód-tudatos plafon → Task 4 (budget/ütemezés) + Task 5 (plafon/main). ✓
- §F Frontend 5 domén → Task 8. ✓
- §G Config-adat → Task 7. ✓
- Tesztelés (config/gyujt/futtat-reggel/plafon/másodlagos/frontend) → Task 1,3,4,5,6,7,8. ✓
- Kockázatok: pótolhatatlan lánc (R1 → Task 2 lezárja), 6 kapu/merge (Task 6), namedtuple pozicionális (Task 1 default + a Task 1 grep igazolta: minden meglévő hívóhely ≤4 pozicionális arg → default-kompatibilis), elemzo/regresszió (R4 → Task 9). ✓

**2. Placeholder scan:** Minden kód-lépés valós, futtatható kódot ad; a Task 8 (Playwright fixture) és Task 9 (regresszió szignatúra) explicit „olvasd be a tényleges alakot" utasítást tartalmaz, mert a projekt e2e-fixture-konvenciója és a `regresszio_szamit` pontos alakja a fájlból derül ki — ez nem placeholder, hanem lokalizált beolvasási lépés a task elején.

**3. Type consistency:** `KulcsszoTetel(kifejezes, domen, tipus, racs, oras, futas)` egységes minden taskban; `masodlagos_timeframek` visszatérése `list[str]`; `_oras_szavak(config, mode) -> list[KulcsszoTetel]`; `tervezett_hivasszam(config, mode)` / `_szamitott_plafon(config, mode)` / `_plafon(config, mode, override)` konzisztens; `gyujt(..., tetelek=)` és `masodlagos_szavak_ma(..., mode=)` / `_masodlagos_ag(..., mode=)` egyeznek a hívóhelyekkel (Task 6).

**Ismert korlát (dokumentálva):** a profil-3 reggeli szavak órás regressziója az esti passzban készül, tortenet nélkül → `meres_kezdete=null` (kecses, létező viselkedés). Ha később teljes reggeli history kell, az egy külön iteráció (per-szó tortenet-merge) — YAGNI most.
