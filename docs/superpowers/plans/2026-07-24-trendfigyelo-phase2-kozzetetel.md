# Trendfigyelő — Phase 2 (közzététel + automatizálás) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Phase 1 adatréteg közzététele és automatizálása: három adatminőségi Minor-fix, a kulcsszó-történet 429-önjavítása (0 extra hívás), napi egy GitHub Actions futás (előbb kézi, majd ütemezett), és a GitHub Pages infra bekapcsolása a `docs/`-ból.

**Architecture:** A meglévő `trendfigyelo/` csomag pontszerű bővítése (idosorok, config, naplo, kulcsszavak, json_export, futtato) + két új nem-Python artefakt (`.github/workflows/napi.yml`, `docs/index.html`). A 429-önjavítás a **már lekért** `now 7-d` ablakból az utolsó N teljes napot upsertli a `tortenet.json`-ba, miközben a CSV és a `legfrissebb.json` egynapos marad (kis blast-radius). A teljes Chart.js web külön Phase 3.

**Tech Stack:** Python 3.12, trendspy==0.1.6, PyYAML, pandas, pytest; GitHub Actions (YAML), statikus HTML. Nincs build-lépés.

## Global Constraints

Ezek MINDEN taskra vonatkoznak (a Phase 1-ből öröklött, verbatim):

- **geo="HU" mindenhol**, **nyelv="hu"**, **elmúlt 24 óra**; egyetlen konfigforrás a `config.yaml`; minden CSV-sor és JSON-bejegyzés tartalmaz `geo` mezőt.
- **Idő:** nyers adat UTC-ben (ISO, `timespec="seconds"`); fájlnevek és megjelenítendő időbélyegek budapesti idő (Europe/Budapest).
- **CSV formátum:** `;` elválasztó, `utf-8-sig`. A meglévő fájlok oszlopszerkezete VÁLTOZATLAN.
- **Anti-block:** napi egy futás; nincs rövid ciklusú tömeges retry; 429 → backoff → ág-feladás + naplózás; részleges siker is siker; teljes blokk → nem-nulla kilépési kód.
- **Nincs élő Google-teszt** a unit tesztekben — mock/fixtúra. Az egyetlen éles teszt Phase 2-ben a valós `workflow_dispatch` futás (merge után).
- **Munkamódszer:** friss implementer + külön review-agent taskonként; TDD (RED→GREEN); commit **review után**; záró ledger.
- **Verziófloorok (requirements.txt) változatlanok:** `trendspy==0.1.6`, `PyYAML>=6.0`, `pandas>=2.0`, `pytest>=8.0`.
- **Kód magyarul** (kommentek, változónevek, kimenetek).

**Teszt-futtatás:** a repó gyökeréből `python -m pytest -q` a teljes suite; egy fájlra `python -m pytest tests/test_X.py -v`.

---

## Előfeltétel (kódmentes, kifelé ható — KÜLÖN JÓVÁHAGYÁS)

A kódtaskok előtt, a felhasználó kézi jóváhagyásával:

1. **Phase 1 → `main`.** A `feature/phase1-adatreteg` (lezárt, zöld, éles füst-teszt átment) PR-rel a `main`-be. Ez a Phase 2 spec-commitját (`edc9f95`) is viszi.
2. **Phase 2 ág.** `git switch -c feature/phase2-kozzetetel` a friss `main`-ről.

> A merge és a branch-műveletek kifelé ható lépések — az implementer NE végezze el önállóan; a felhasználó indítja/hagyja jóvá. A Task 1–8 ezen az ágon készül; a mainre-emelés és az élesítés a „Merge + élesítés" szakaszban.

---

## Fájlszerkezet (Phase 2 után)

```
trendfigyelo/
├── idosorok.py        # MÓDOSUL: NaN → "" (Task 1)
├── config.py          # MÓDOSUL: lista-validáció + naplo_max_sor + tortenet_visszapotlas_nap (Task 2,3,4)
├── naplo.py           # MÓDOSUL: görgő sor-cap (Task 3)
├── kulcsszavak.py     # MÓDOSUL: utolso_N_teljes_nap, parse_koteg_napok, gyujt tuple (Task 4,5)
├── json_export.py     # MÓDOSUL: tortenet_frissit_napok (Task 5)
└── futtato.py         # MÓDOSUL: naplo cap + kulcsszó tuple + tortenet_frissit_napok bekötés (Task 3,5)
config.yaml            # MÓDOSUL: naplo_max_sor, tortenet_visszapotlas_nap (Task 3,4)
.github/workflows/napi.yml   # ÚJ (Task 6) — dispatch-only, majd schedule (Task 9)
docs/index.html        # ÚJ (Task 7) — statikus placeholder
README.md              # MÓDOSUL (Task 8) — workflow, Pages, escalation-függelék
tests/                 # új/bővített tesztek taskonként (+ tests/test_pages.py)
```

---

### Task 1: NaN → üres string (`idosorok.df_idosor`)

A `df_idosor` NaN-értéknél jelenleg a literál `"nan"` stringet írja ki (`_szam` False → `szovegge(NaN)` → `str(NaN)`). Fix: nem-szám/NaN → `""`, szimmetriában a kulcsszó-ág `parse_koteg`-jével.

**Files:**
- Modify: `trendfigyelo/idosorok.py` (a `df_idosor` `ertek` kifejezése)
- Test: `tests/test_idosorok.py`

**Interfaces:**
- Consumes: `idosorok.df_idosor(df, kifejezes: str, forras: str) -> list` (meglévő).
- Produces: változatlan szignatúra; NaN-értékű pont `ertek` mezője `""` (nem `"nan"`).

- [ ] **Step 1: Failing teszt — NaN üres stringet ad**

Add to `tests/test_idosorok.py`:
```python
def test_df_idosor_nan_ures_string_nem_nan():
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 1, 11, tzinfo=timezone.utc),
    ])
    df = pd.DataFrame({"infláció": [float("nan"), 80], "isPartial": [False, False]}, index=idx)
    pontok = idosorok.df_idosor(df, "infláció", "interest_over_time")
    assert pontok[0]["ertek"] == ""     # NEM a literál "nan"
    assert pontok[1]["ertek"] == 80
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_idosorok.py::test_df_idosor_nan_ures_string_nem_nan -v`
Expected: FAIL — `assert 'nan' == ''`.

- [ ] **Step 3: GREEN — az else ág üres stringet ad**

In `trendfigyelo/idosorok.py`, a `df_idosor` ciklusában cseréld:
```python
            "ertek": int(sor[oszlop]) if _szam(sor[oszlop]) else seged.szovegge(sor[oszlop]),
```
erre:
```python
            "ertek": int(sor[oszlop]) if _szam(sor[oszlop]) else "",
```

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_idosorok.py -v`
Expected: PASS (az új teszt + a meglévő `test_df_idosor_pontok_es_ispartial_kihagyva` zöld).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/idosorok.py tests/test_idosorok.py
git commit -m "fix(idosorok): NaN érték üres string, nem literál 'nan' (Phase 2 Task 1)"
```

---

### Task 2: `config.betolt` lista-aritás validáció

Skalár/hiányos `szoras_mp` most nyers `IndexError`-t dob; a `backoff_mp`/`max_probak` nincs ellenőrizve. Fix: minden hiba érthető `KonfigHiba`, a mezőt megnevezve. A **kimeneti értékek változatlanok** (a validáció nem konvertál, csak ellenőriz).

**Files:**
- Modify: `trendfigyelo/config.py` (új `_ellenoriz_szamlista` helper + validáció a `betolt`-ben)
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `config.betolt(utvonal) -> Config`, `config.KonfigHiba` (meglévő).
- Produces: `_ellenoriz_szamlista(ertek, hol: str, hossz: int | None = None) -> None` — `KonfigHiba`-t dob, ha `ertek` nem lista/tuple, ha `hossz` megadva és a hossz nem stimmel, ha üres (amikor `hossz is None`), vagy ha bármely elem nem szám. A `Config` mezők típusai VÁLTOZATLANOK.

- [ ] **Step 1: Failing tesztek — érthető hibák hibás listákra**

Add to `tests/test_config.py`:
```python
def test_szoras_mp_skalar_konfighibat_dob(tmp_path):
    rossz = JO.replace("szoras_mp: [3, 7]", "szoras_mp: 5")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_szoras_mp_egy_elem_konfighibat_dob(tmp_path):
    rossz = JO.replace("szoras_mp: [3, 7]", "szoras_mp: [5]")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_szoras_mp_forditott_hatarok_konfighibat_dob(tmp_path):
    rossz = JO.replace("szoras_mp: [3, 7]", "szoras_mp: [7, 3]")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_backoff_ures_lista_konfighibat_dob(tmp_path):
    rossz = JO.replace("backoff_mp: [30, 120, 480]", "backoff_mp: []")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_max_probak_nulla_konfighibat_dob(tmp_path):
    rossz = JO.replace("max_probak: 4", "max_probak: 0")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_config.py -v -k "szoras_mp or backoff_ures or max_probak_nulla"`
Expected: FAIL — a skalár/1-elem eset `IndexError`/`TypeError`, a fordított/üres/nulla esetek NEM dobnak (rossz adat átcsúszik).

- [ ] **Step 3: GREEN — validáló helper + beépítés**

In `trendfigyelo/config.py`, a `_kell` függvény után add:
```python
def _ellenoriz_szamlista(ertek, hol: str, hossz=None):
    """KonfigHiba, ha ertek nem szám-lista (adott hosszal / nem-üresen)."""
    if not isinstance(ertek, (list, tuple)):
        raise KonfigHiba(f"{hol}: listát vártam, nem {type(ertek).__name__}-t")
    if hossz is not None and len(ertek) != hossz:
        raise KonfigHiba(f"{hol}: pontosan {hossz} elem kell, kaptam {len(ertek)}-t")
    if hossz is None and not ertek:
        raise KonfigHiba(f"{hol}: nem lehet üres lista")
    for x in ertek:
        try:
            float(x)
        except (ValueError, TypeError):
            raise KonfigHiba(f"{hol}: nem-szám elem: {x!r}")
```

Ezután a `betolt`-ben cseréld a jelenlegi
```python
    szoras = _kell(kp, "szoras_mp", "kerespont.")
    return Config(
```
blokkot erre (a `return Config(` elé kerül a validáció; a `Config(...)` argumentumai VÁLTOZATLANOK maradnak):
```python
    szoras = _kell(kp, "szoras_mp", "kerespont.")
    _ellenoriz_szamlista(szoras, "kerespont.szoras_mp", 2)
    if float(szoras[0]) < 0:
        raise KonfigHiba("kerespont.szoras_mp: nem lehet negatív")
    if float(szoras[0]) > float(szoras[1]):
        raise KonfigHiba("kerespont.szoras_mp: az alsó határ nem lehet nagyobb a felsőnél")

    backoff = _kell(kp, "backoff_mp", "kerespont.")
    _ellenoriz_szamlista(backoff, "kerespont.backoff_mp")

    if float(_kell(kp, "alap_keses_mp", "kerespont.")) < 0:
        raise KonfigHiba("kerespont.alap_keses_mp: nem lehet negatív")
    if int(_kell(kp, "max_probak", "kerespont.")) < 1:
        raise KonfigHiba("kerespont.max_probak: legalább 1 kell legyen")

    return Config(
```

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS — az új tesztek zöldek, a meglévők (`test_betolt_kiolvassa_a_mezoket` a `szoras_mp == (3, 7)` és `backoff_mp == [30, 120, 480]` egyenlőségekkel) továbbra is zöldek.

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/config.py tests/test_config.py
git commit -m "fix(config): lista-aritás validáció érthető KonfigHibával (Phase 2 Task 2)"
```

---

### Task 3: `naplo.csv` görgő sor-cap + `naplo_max_sor` config

A `naplo_ir` korlátlanul hozzáfűz. Fix: íráskor, ha a fájl túllépi a `max_sor` adatsort, fejléc + utolsó `max_sor` sorra korlátozzuk (CSV-formátumot megőrizve). A `config.yaml` új `naplo_max_sor` mezője adja az értéket; a `futtato` átadja.

**Files:**
- Modify: `trendfigyelo/naplo.py` (`naplo_ir` új `max_sor` param + `_cap` helper)
- Modify: `trendfigyelo/config.py` (`Config.naplo_max_sor` mező + betöltés)
- Modify: `trendfigyelo/futtato.py` (a `naplo.naplo_ir` hívás átadja `config.naplo_max_sor`-t)
- Modify: `config.yaml` (`naplo_max_sor: 2000`)
- Test: `tests/test_naplo.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `naplo.naplo_ir(mappa, futas_ido_utc, bejegyzesek)` (meglévő).
- Produces: `naplo.naplo_ir(mappa, futas_ido_utc, bejegyzesek, max_sor: int = 2000) -> Path` — cap után a fájl legfeljebb `max_sor` adatsor + 1 fejléc, sorrend-tartón (a legrégebbiek esnek ki). `Config.naplo_max_sor: int` (alap 2000).

- [ ] **Step 1: Failing teszt — a cap az utolsó N sort tartja**

Add to `tests/test_naplo.py`:
```python
def test_naplo_cap_megtartja_az_utolso_n_sort(tmp_path):
    for i in range(5):
        naplo.naplo_ir(tmp_path, f"2021-01-{i + 1:02d}T12:00:00+00:00",
                       [{"ag": "a", "eredmeny": "siker", "hivasok_szama": 1, "hibakodok": ""}],
                       max_sor=3)
    sorok = (tmp_path / "naplo.csv").read_text(encoding="utf-8-sig").splitlines()
    assert len(sorok) == 4                          # 1 fejléc + 3 adatsor
    assert sorok[0] == "futas_ido_utc;ag;eredmeny;hivasok_szama;hibakodok"
    assert sorok[1].startswith("2021-01-03")        # a 01-01 és 01-02 kiesett
    assert sorok[3].startswith("2021-01-05")
```

And to `tests/test_config.py`:
```python
def test_naplo_max_sor_alapertelmezes(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.naplo_max_sor == 2000
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_naplo.py::test_naplo_cap_megtartja_az_utolso_n_sort tests/test_config.py::test_naplo_max_sor_alapertelmezes -v`
Expected: FAIL — `naplo_ir() got an unexpected keyword argument 'max_sor'`, illetve `AttributeError: ... 'naplo_max_sor'`.

- [ ] **Step 3: GREEN — cap-logika + config mező + futtato bekötés**

In `trendfigyelo/naplo.py` cseréld a `naplo_ir` szignatúrát és a `return` előtt add a cap-hívást, plusz az új helper:
```python
def naplo_ir(mappa, futas_ido_utc: str, bejegyzesek, max_sor: int = 2000) -> Path:
    """Ágsoronkénti napló hozzáfűzése; fejléc csak új fájlnál. Görgő cap: max_sor adatsor."""
    fajl = Path(mappa) / "naplo.csv"
    uj = not fajl.exists()
    with fajl.open("a", newline="", encoding="utf-8-sig") as f:
        iro = csv.writer(f, delimiter=";")
        if uj:
            iro.writerow(FEJLEC)
        for b in bejegyzesek:
            iro.writerow([
                futas_ido_utc, b["ag"], b["eredmeny"],
                b["hivasok_szama"], b["hibakodok"],
            ])
    _cap(fajl, max_sor)
    return fajl


def _cap(fajl: Path, max_sor: int):
    """Ha a fájl > max_sor adatsor, fejléc + utolsó max_sor sorra írja újra."""
    with fajl.open(encoding="utf-8-sig", newline="") as f:
        sorok = list(csv.reader(f, delimiter=";"))
    if len(sorok) <= max_sor + 1:      # +1 a fejléc
        return
    fejlec, adat = sorok[0], sorok[1:]
    with fajl.open("w", newline="", encoding="utf-8-sig") as f:
        iro = csv.writer(f, delimiter=";")
        iro.writerow(fejlec)
        iro.writerows(adat[-max_sor:])
```

In `trendfigyelo/config.py`, a `Config` dataclass végére (a defaultolt mezők közé) add:
```python
    naplo_max_sor: int = 2000
```
és a `betolt` `Config(...)` hívásában, a `referencia_min_atlag=...` sor után:
```python
        naplo_max_sor=int(nyers.get("naplo_max_sor", 2000)),
```

In `trendfigyelo/futtato.py` cseréld:
```python
    naplo.naplo_ir(adatok_mappa, letoltve, bejegyzesek)
```
erre:
```python
    naplo.naplo_ir(adatok_mappa, letoltve, bejegyzesek, config.naplo_max_sor)
```

In `config.yaml`, a `referencia_min_atlag: 1.0` sor után add:
```yaml
naplo_max_sor: 2000            # a naplo.csv görgő sor-cap-je (~500 nap napi ~4 sornál)
```

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_naplo.py tests/test_config.py tests/test_futtato.py -v`
Expected: PASS — az új tesztek + a meglévő napló-/config-/futtato-tesztek (default `max_sor=2000` mellett érintetlenül).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/naplo.py trendfigyelo/config.py trendfigyelo/futtato.py config.yaml tests/test_naplo.py tests/test_config.py
git commit -m "fix(naplo): görgő sor-cap + naplo_max_sor config (Phase 2 Task 3)"
```

---

### Task 4: `utolso_N_teljes_nap` + `parse_koteg_napok` + `tortenet_visszapotlas_nap`

A 429-önjavítás adat-alapja: a már lekért `now 7-d` DataFrame-ből az utolsó N teljes budapesti nap pontjai, naponkénti referencia-normalizálással. A `parse_koteg` belső egynap-parse-ját közös helperbe emeljük (viselkedés-őrző refaktor), és rá építjük a többnapos változatot.

**Files:**
- Modify: `trendfigyelo/kulcsszavak.py` (`_parse_egy_nap` helper kiemelése, `utolso_N_teljes_nap`, `parse_koteg_napok`)
- Modify: `trendfigyelo/config.py` (`Config.tortenet_visszapotlas_nap` mező + betöltés)
- Modify: `config.yaml` (`tortenet_visszapotlas_nap: 3`)
- Test: `tests/test_kulcsszavak.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `kulcsszavak.parse_koteg(df, koteg, mai_datum, min_atlag)`, `kulcsszavak.utolso_teljes_nap(df, mai_datum)`, `kulcsszavak._bp_datum(idx)`, `kulcsszavak._ref_atlag`, `kulcsszavak.skalazo` (meglévők); `seged` (meglévő).
- Produces:
  - `utolso_N_teljes_nap(df, mai_datum, n: int) -> list[date]` — a `mai_datum`-nál korábbi budapesti dátumok közül az utolsó `n`, növekvő sorrendben (kevesebb is lehet).
  - `_parse_egy_nap(napi_df, koteg, min_atlag) -> list` — egy nap (már leszűrt) DataFrame-je → pontlista (a `parse_koteg` eddigi belső logikája, változatlan mezőkkel).
  - `parse_koteg_napok(df, koteg, mai_datum, min_atlag, n: int) -> dict[str, list]` — `{nap_iso: [pontok]}` az utolsó `n` teljes napra (üres napokat kihagyva).
  - `Config.tortenet_visszapotlas_nap: int` (alap 3).

- [ ] **Step 1: Failing tesztek — N-napos kiválasztás és parse**

Add to `tests/test_kulcsszavak.py`:
```python
def test_utolso_N_teljes_nap_utolso_harmat_adja():
    idx = pd.to_datetime(
        [datetime(2021, 1, d, 10, tzinfo=timezone.utc) for d in (1, 2, 3, 4)]
        + [datetime(2021, 1, 5, 9, tzinfo=timezone.utc)]  # mai (csonka)
    )
    df = pd.DataFrame({"a": [10, 20, 30, 40, 50], "időjárás": [50] * 5}, index=idx)
    # mai=01-05 → teljes: 01-01..01-04 → utolsó 3 = [01-02, 01-03, 01-04]
    assert kulcsszavak.utolso_N_teljes_nap(df, date(2021, 1, 5), 3) == [
        date(2021, 1, 2), date(2021, 1, 3), date(2021, 1, 4),
    ]


def test_utolso_N_teljes_nap_kevesebb_mint_n():
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 2, 9, tzinfo=timezone.utc),   # mai (csonka)
    ])
    df = pd.DataFrame({"a": [10, 20], "időjárás": [50, 50]}, index=idx)
    assert kulcsszavak.utolso_N_teljes_nap(df, date(2021, 1, 2), 3) == [date(2021, 1, 1)]


def test_parse_koteg_napok_tobb_napot_ad_naponkenti_normalizalassal():
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 2, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 3, 9, tzinfo=timezone.utc),   # mai (csonka)
    ])
    df = pd.DataFrame({"a": [30, 40, 99], "időjárás": [50, 50, 50]}, index=idx)
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    napi = kulcsszavak.parse_koteg_napok(df, koteg, date(2021, 1, 3), 1.0, 3)
    assert set(napi.keys()) == {"2021-01-01", "2021-01-02"}   # a mai (01-03) kizárva
    assert napi["2021-01-01"][0]["nyers_ertek"] == 30
    assert napi["2021-01-01"][0]["normalizalt_ertek"] == 60.0  # 30 * (100/50)
    assert napi["2021-01-02"][0]["nyers_ertek"] == 40
```

And to `tests/test_config.py`:
```python
def test_tortenet_visszapotlas_nap_alapertelmezes(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.tortenet_visszapotlas_nap == 3
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_kulcsszavak.py -v -k "utolso_N or parse_koteg_napok" tests/test_config.py::test_tortenet_visszapotlas_nap_alapertelmezes`
Expected: FAIL — `AttributeError: module ... has no attribute 'utolso_N_teljes_nap'` / `parse_koteg_napok`, illetve hiányzó `tortenet_visszapotlas_nap`.

- [ ] **Step 3: GREEN — helper-kiemelés + új függvények + config mező**

In `trendfigyelo/kulcsszavak.py` cseréld a jelenlegi `parse_koteg` teljes törzsét úgy, hogy a napi-parse közös helperbe kerül (a mezők VÁLTOZATLANOK):
```python
def _parse_egy_nap(napi, koteg, min_atlag) -> list:
    """Egy nap (már leszűrt) DataFrame-je → pontok, nyers + (érvényes ref-nél) normalizált."""
    pontok = []
    ref = koteg["referenciaszo"]
    ref_atlag = _ref_atlag(napi, ref)
    ervenyes = ref_atlag is not None and ref_atlag >= min_atlag
    sk = skalazo([ref_atlag]) if ervenyes else None  # 100 / ref_atlag
    for kulcsszo, csoport in koteg["tagok"]:
        if kulcsszo not in napi.columns:
            continue
        for idx, sor in napi.iterrows():
            nyers = sor[kulcsszo]
            if _szam(nyers):
                nyers_ert = int(nyers)
                norm = round(float(nyers) * sk, 2) if sk is not None else ""
            else:
                nyers_ert = ""
                norm = ""
            pontok.append({
                "kulcsszo": kulcsszo,
                "csoport": csoport,
                "idopont_utc": seged.idopont_iso(idx),
                "nyers_ertek": nyers_ert,
                "normalizalt_ertek": norm,
                "koteg_id": koteg["id"],
                "referenciaszo": ref,
                "referencia_atlag": round(ref_atlag, 2) if ref_atlag is not None else "",
                "referencia_ervenyes": ervenyes,
            })
    return pontok


def parse_koteg(df, koteg, mai_datum, min_atlag) -> list:
    """Köteg DataFrame → pontok az UTOLSÓ TELJES napra szűrve."""
    if df is None or len(df) == 0:
        return []
    nap = utolso_teljes_nap(df, mai_datum)
    if nap is None:
        return []
    napi = df[[_bp_datum(idx) == nap for idx in df.index]]
    return _parse_egy_nap(napi, koteg, min_atlag)
```

Az `utolso_teljes_nap` függvény után add:
```python
def utolso_N_teljes_nap(df, mai_datum, n: int) -> list:
    """A df budapesti dátumai közül az utolsó n, amely < mai_datum; növekvő sorrendben."""
    if df is None or len(df) == 0:
        return []
    korabbi = sorted({_bp_datum(idx) for idx in df.index if _bp_datum(idx) < mai_datum})
    return korabbi[-n:]


def parse_koteg_napok(df, koteg, mai_datum, min_atlag, n: int) -> dict:
    """Köteg DataFrame → {nap_iso: [pontok]} az utolsó n teljes napra (üres napok nélkül)."""
    if df is None or len(df) == 0:
        return {}
    ki = {}
    for nap in utolso_N_teljes_nap(df, mai_datum, n):
        napi = df[[_bp_datum(idx) == nap for idx in df.index]]
        pontok = _parse_egy_nap(napi, koteg, min_atlag)
        if pontok:
            ki[nap.isoformat()] = pontok
    return ki
```

In `trendfigyelo/config.py`, a `Config` dataclass végére add:
```python
    tortenet_visszapotlas_nap: int = 3
```
és a `betolt` `Config(...)` hívásában, a `naplo_max_sor=...` sor után:
```python
        tortenet_visszapotlas_nap=int(nyers.get("tortenet_visszapotlas_nap", 3)),
```

In `config.yaml`, a `naplo_max_sor: 2000` sor után add:
```yaml
tortenet_visszapotlas_nap: 3   # a kulcsszó-tortenet utolsó N teljes napjának upsertje (429-önjavítás)
```

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_kulcsszavak.py tests/test_config.py -v`
Expected: PASS — az új tesztek zöldek, ÉS a meglévő `parse_koteg`-tesztek (`test_parse_koteg_*`, `test_parse_koteg_csak_az_utolso_teljes_napot`, `test_parse_koteg_tobb_teljes_nap_csak_a_legutolso`, stb.) változatlanul zöldek (viselkedés-őrző refaktor).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/kulcsszavak.py trendfigyelo/config.py config.yaml tests/test_kulcsszavak.py tests/test_config.py
git commit -m "feat(kulcsszavak): utolso_N_teljes_nap + parse_koteg_napok + config N (Phase 2 Task 4)"
```

---

### Task 5: 429-önjavítás bekötése — `gyujt` tuple + `tortenet_frissit_napok` + `futtato`

A kulcsszó-ág egyetlen 7-d lekérésből ad **egynapos** pontokat (CSV/legfrissebb) ÉS az utolsó N nap `{nap_iso: [pontok]}` dict-jét (tortenet). A `tortenet.json` többnapos upsertje: a **legfrissebb nap felülír**, a régebbiek **insert-if-absent** (a csúszó-ablak-churn ellen).

**Files:**
- Modify: `trendfigyelo/kulcsszavak.py` (`gyujt` → `(pontok, napi_pontok)`)
- Modify: `trendfigyelo/json_export.py` (`tortenet_frissit_napok`)
- Modify: `trendfigyelo/futtato.py` (a kulcsszó-eredmény kicsomagolása + tortenet bekötés)
- Test: `tests/test_kulcsszavak.py`, `tests/test_json_export.py`, `tests/test_futtato.py`

**Interfaces:**
- Consumes: `kulcsszavak.parse_koteg`, `kulcsszavak.parse_koteg_napok` (Task 4), `json_export.kulcsszo_napi_osszesites`, `json_export._ir_json` (meglévők).
- Produces:
  - `kulcsszavak.gyujt(kliens, config, most=None) -> tuple[list, dict]` — `(egynapos_pontok, napi_pontok)`, ahol `napi_pontok = {nap_iso: [pontok]}` az utolsó `config.tortenet_visszapotlas_nap` napra. `AgFeladva` továbbra is propagál; nem-429 hiba köteget hagy ki.
  - `json_export.tortenet_frissit_napok(docs_data, napi_pontok: dict) -> Path` — minden napra upsert; `max(napi_pontok)` (legfrissebb ISO) felülír, a többi csak akkor íródik, ha még nincs a `tortenet.json`-ban. A `napok` lista dátum szerint rendezve marad.

- [ ] **Step 1: Failing tesztek — tuple-return, upsert-szemantika, önjavítás**

In `tests/test_kulcsszavak.py`, a meglévő `test_gyujt_egyeb_hiba_csak_azt_a_koteget_hagyja_ki` első sorát cseréld (a `gyujt` mostantól tuple-t ad):
```python
    pontok, _ = kulcsszavak.gyujt(k, _config_2koteg())
```
és add új tesztet:
```python
def test_gyujt_tuple_egynapos_es_napi_pontok():
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 2, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 3, 9, tzinfo=timezone.utc),   # mai (csonka)
    ])
    df = pd.DataFrame({"a": [30, 40, 99], "b": [30, 40, 99], "c": [30, 40, 99],
                       "d": [30, 40, 99], "időjárás": [50, 50, 50]}, index=idx)
    k = _FakeKliens([df])
    cfg = _config()  # 1 köteg (a..d) + referencia; tortenet_visszapotlas_nap alap 3
    most = datetime(2021, 1, 3, 12, tzinfo=timezone.utc)  # mai budapesti nap = 01-03
    pontok, napi = kulcsszavak.gyujt(k, cfg, most)
    assert {p["idopont_utc"][:10] for p in pontok} == {"2021-01-02"}   # egynapos: utolsó teljes
    assert set(napi.keys()) == {"2021-01-01", "2021-01-02"}            # napi: utolsó 2 teljes
```

In `tests/test_json_export.py` add:
```python
def test_tortenet_frissit_napok_visszapotol_es_nem_ir_felul(tmp_path):
    # meglévő 01-02 (régi 99.0 érték)
    json_export.tortenet_frissit(tmp_path, "2021-01-02", [
        {"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 99.0, "referencia_ervenyes": True}])
    napi = {
        "2021-01-01": [{"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 10.0, "referencia_ervenyes": True}],
        "2021-01-02": [{"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 20.0, "referencia_ervenyes": True}],
        "2021-01-03": [{"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 30.0, "referencia_ervenyes": True}],
    }
    p = json_export.tortenet_frissit_napok(tmp_path, napi)
    adat = json.loads(p.read_text(encoding="utf-8"))
    atlagok = {b["nap"]: b["kulcsszavak"][0]["atlag"] for b in adat["napok"]}
    assert [b["nap"] for b in adat["napok"]] == ["2021-01-01", "2021-01-02", "2021-01-03"]  # rendezett
    assert atlagok["2021-01-01"] == 10.0   # visszapótolva (hiányzott)
    assert atlagok["2021-01-02"] == 99.0   # insert-if-absent: a meglévő NEM íródott felül
    assert atlagok["2021-01-03"] == 30.0   # a legfrissebb nap beírva


def test_tortenet_frissit_napok_friss_nap_felulir(tmp_path):
    json_export.tortenet_frissit(tmp_path, "2021-01-03", [
        {"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 99.0, "referencia_ervenyes": True}])
    napi = {"2021-01-03": [{"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 30.0, "referencia_ervenyes": True}]}
    p = json_export.tortenet_frissit_napok(tmp_path, napi)
    adat = json.loads(p.read_text(encoding="utf-8"))
    b = next(x for x in adat["napok"] if x["nap"] == "2021-01-03")
    assert b["kulcsszavak"][0]["atlag"] == 30.0   # a legfrissebb nap FELÜLÍR
```

In `tests/test_futtato.py` add (a `KulcsszoAdatKliens` már ad többnapos df-et; itt önjavítást ellenőrzünk):
```python
def test_futtato_visszapotolja_a_kihagyott_kulcsszo_napot(tmp_path):
    import json
    cfg = _config()
    cfg.kulcsszavak = {"megelhetes": ["a"]}
    docs_data = tmp_path / "docs" / "data"
    # magvetés: csak 01-02 létezik a tortenet-ben (01-01 "kihagyott" nap)
    json_export.tortenet_frissit(docs_data, "2021-01-02", [
        {"kulcsszo": "a", "csoport": "megelhetes", "normalizalt_ertek": 20.0, "referencia_ervenyes": True}])
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)  # mai=01-02 → utolsó teljes 01-01
    futtato.futtat(cfg, KulcsszoAdatKliens(), tmp_path / "adatok", docs_data, most=most)
    tortenet = json.loads((docs_data / "tortenet.json").read_text(encoding="utf-8"))
    napok = sorted(b["nap"] for b in tortenet["napok"])
    assert napok == ["2021-01-01", "2021-01-02"]   # a 01-01 visszapótolva a 7-d ablakból
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_kulcsszavak.py tests/test_json_export.py tests/test_futtato.py -v -k "gyujt_tuple or tortenet_frissit_napok or visszapotolja"`
Expected: FAIL — `gyujt` listát ad (nem tuple → unpack hiba), `tortenet_frissit_napok` nem létezik, az önjavítás-teszt csak 01-02-t lát.

- [ ] **Step 3: GREEN — gyujt tuple + json_export upsert + futtato bekötés**

In `trendfigyelo/kulcsszavak.py` cseréld a `gyujt` törzsét:
```python
def gyujt(kliens, config, most=None):
    """Minden köteget lekér (now 7-d). Visszaad: (egynapos_pontok, {nap_iso: [pontok]}).

    Az egynapos_pontok a CSV-hez és legfrissebb.json-hoz (utolsó teljes nap); a napi
    dict a tortenet többnapos upsertjéhez (utolsó N teljes nap, 0 extra hívásból).
    AgFeladva (429) → az EGÉSZ ág feladva; egyéb hiba csak az adott köteget hagyja ki.
    """
    most = most or seged.most_utc()
    mai_datum = most.astimezone(seged.BUDAPEST).date()
    n = config.tortenet_visszapotlas_nap
    pontok = []
    napi_pontok = {}
    for koteg in kotegek(config):
        szavak = koteg_lekerdezes_szavai(koteg)
        try:
            df = kliens.hivas(
                "kulcsszo", kliens.tr.interest_over_time,
                szavak, geo=config.geo, timeframe=config.kulcsszo_idokeret,
            )
        except AgFeladva:
            print(f"FIGYELEM: a kulcsszó-ág feladva (429) a(z) {koteg['id']}. kötegnél.")
            raise
        except Exception as e:
            print(f"FIGYELEM: a(z) {koteg['id']}. köteg kimaradt ({e}).")
            continue
        pontok.extend(parse_koteg(df, koteg, mai_datum, config.referencia_min_atlag))
        for nap_iso, nap_pontok in parse_koteg_napok(
                df, koteg, mai_datum, config.referencia_min_atlag, n).items():
            napi_pontok.setdefault(nap_iso, []).extend(nap_pontok)
    return pontok, napi_pontok
```

In `trendfigyelo/json_export.py`, a `tortenet_frissit` után add:
```python
def tortenet_frissit_napok(docs_data, napi_pontok) -> Path:
    """Több nap upsertje: a legfrissebb nap felülír, a régebbiek insert-if-absent."""
    fajl = Path(docs_data) / "tortenet.json"
    if fajl.exists():
        adat = json.loads(fajl.read_text(encoding="utf-8"))
    else:
        adat = {"napok": []}
    if napi_pontok:
        friss = max(napi_pontok)          # a legfrissebb nap ISO-ja
        meglevo = {b.get("nap") for b in adat["napok"]}
        for nap_iso in sorted(napi_pontok):
            if nap_iso != friss and nap_iso in meglevo:
                continue                  # insert-if-absent: régi napot nem írunk felül
            osszesites = kulcsszo_napi_osszesites(napi_pontok[nap_iso])
            if not osszesites:
                continue
            adat["napok"] = [b for b in adat["napok"] if b.get("nap") != nap_iso]
            adat["napok"].append({"nap": nap_iso, "kulcsszavak": osszesites})
        adat["napok"].sort(key=lambda b: b["nap"])
    return _ir_json(fajl, adat)
```

In `trendfigyelo/futtato.py` cseréld a kulcsszó-ág sorát:
```python
        kulcsszo_pontok = _ag(bejegyzesek, kliens, "kulcsszo",
                            lambda: kulcsszavak.gyujt(kliens, config, most)) or []
```
erre:
```python
        kulcsszo_eredmeny = _ag(bejegyzesek, kliens, "kulcsszo",
                            lambda: kulcsszavak.gyujt(kliens, config, most))
        kulcsszo_pontok, kulcsszo_napi_pontok = kulcsszo_eredmeny or ([], {})
```
és a `kulcsszo_pontok = []` iniciálást (a négy-lista blokkban) egészítsd ki:
```python
    kulcsszo_pontok = []
    kulcsszo_napi_pontok = {}
```
majd cseréld a tortenet-frissítő blokkot:
```python
    kulcsszo_nap = kulcsszavak.aggregalt_nap(kulcsszo_pontok)
    if kulcsszo_pontok and kulcsszo_nap:
        json_export.tortenet_frissit(docs_data_mappa, kulcsszo_nap, kulcsszo_pontok)
```
erre:
```python
    if kulcsszo_napi_pontok:
        json_export.tortenet_frissit_napok(docs_data_mappa, kulcsszo_napi_pontok)
```

> Megjegyzés: az `AgFeladva`-ág (a `try/except AgFeladva` blokk `for ag in AGAK` naplózása) változatlan; `kulcsszo_napi_pontok` az iniciálásból `{}` marad, ha a kulcsszó-ág kimarad, így a tortenet érintetlen — az „üres kulcsszó nem írja felül" garancia áll.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest -q`
Expected: PASS — a teljes suite. Kiemelten zöld: az új Task 5-tesztek, ÉS a meglévő `test_ures_kulcsszo_nem_irja_felul_a_tortenetet` és `test_tortenet_a_valos_adatnapra_kerul` (a wiring-váltás után is helyes viselkedés).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/kulcsszavak.py trendfigyelo/json_export.py trendfigyelo/futtato.py tests/test_kulcsszavak.py tests/test_json_export.py tests/test_futtato.py
git commit -m "feat(429): kulcsszó-tortenet N-napos önjavítás a 7-d ablakból (Phase 2 Task 5)"
```

---

### Task 6: GitHub Actions workflow — `napi.yml` (dispatch-only)

Napi futás-workflow, **először csak `workflow_dispatch`-csal** (a `schedule:` bekommentelve, Task 9 élesíti). Szelektív commit: csak `docs/data` + `adatok/naplo.csv`; a per-futás CSV-k sosem stage-elődnek. A workflow valódi tesztje a merge utáni kézi indítás.

**Files:**
- Create: `.github/workflows/napi.yml`
- Test: nincs unit-teszt (YAML-validáció lentebb); az éles teszt a merge utáni dispatch.

**Interfaces:**
- Consumes: `top_keresesek.py` (belépő), `requirements.txt` (meglévők).
- Produces: `.github/workflows/napi.yml` — `workflow_dispatch` trigger, `contents: write`, `concurrency` guard, szelektív add + commit-ha-diff.

- [ ] **Step 1: A workflow-fájl létrehozása**

Create `.github/workflows/napi.yml`:
```yaml
name: Napi trendgyűjtés

on:
  workflow_dispatch:
  # A napi ütemezés KÜLÖN, későbbi committal élesedik (Task 9), miután a kézi
  # futások megerősítették, hogy a runner-IP nem kap azonnali 429-et:
  # schedule:
  #   - cron: "7 19 * * *"   # 19:07 UTC — 21:07 nyár / 20:07 tél budapesti idő

permissions:
  contents: write

concurrency:
  group: napi-futtatas
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

      - name: Függőségek telepítése
        run: pip install -r requirements.txt

      - name: Trendfigyelő futtatása
        run: python top_keresesek.py

      - name: Változások commitolása (csak JSON + napló)
        if: always()
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add docs/data adatok/naplo.csv
          if git diff --staged --quiet; then
            echo "Nincs változás — nincs commit."
          else
            git commit -m "adat: napi HU trendgyűjtés ($(date -u +%Y-%m-%dT%H:%MZ))"
            git push
          fi
```

> A `Trendfigyelő futtatása` lépés nem-nulla kóddal bukik teljes blokknál → a job piros → GitHub e-mail. A commit-lépés `if: always()`, így a blokkot dokumentáló `naplo.csv` ekkor is bekerül. A `git add docs/data adatok/naplo.csv` sosem stage-eli a per-futás `adatok/*.csv`-ket → a CI csak JSON+napló, `.gitignore`-változás nélkül.

- [ ] **Step 2: YAML-validáció (lokálisan)**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/napi.yml')); print('YAML OK')"`
Expected: `YAML OK` (nincs kivétel).

- [ ] **Step 3: A teljes suite még zöld (nincs Python-változás)**

Run: `python -m pytest -q`
Expected: PASS (a workflow-fájl nem érinti a kódot).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/napi.yml
git commit -m "ci(workflow): napi trendgyűjtés dispatch-only (Phase 2 Task 6)"
```

---

### Task 7: GitHub Pages placeholder — `docs/index.html`

Statikus, JS- és build-mentes landing: cím, HU-fókusz, „Phase 3" jegyzet, linkek a data-JSON-okra. Bizonyítja, hogy a Pages él; Phase 3 lecseréli.

**Files:**
- Create: `docs/index.html`
- Test: `tests/test_pages.py`

**Interfaces:**
- Consumes: a napi futás által írt `docs/data/*.json` (relatív linkek).
- Produces: `docs/index.html` — tartalmazza a `"Trendfigyelő"` címet, a `data/legfrissebb.json` linket és a Phase 3-jegyzetet.

- [ ] **Step 1: Failing teszt — az oldal létezik és a data-ra hivatkozik**

Create `tests/test_pages.py`:
```python
from pathlib import Path


def test_index_html_letezik_es_hivatkozik_az_adatra():
    gyoker = Path(__file__).resolve().parent.parent
    html = (gyoker / "docs" / "index.html").read_text(encoding="utf-8")
    assert "Trendfigyelő" in html
    assert "data/legfrissebb.json" in html
    assert "data/tortenet.json" in html
    assert "Phase 3" in html
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_pages.py -v`
Expected: FAIL — `FileNotFoundError: ... docs/index.html`.

- [ ] **Step 3: GREEN — a placeholder oldal**

Create `docs/index.html`:
```html
<!DOCTYPE html>
<html lang="hu">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Trendfigyelő — magyarországi keresési trendek</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 42rem; margin: 3rem auto;
           padding: 0 1rem; line-height: 1.6; color: #222; }
    h1 { margin-bottom: .25rem; }
    .halvany { color: #666; }
    ul { padding-left: 1.2rem; }
    code { background: #f2f2f2; padding: .1rem .3rem; border-radius: 3px; }
  </style>
</head>
<body>
  <h1>Trendfigyelő</h1>
  <p class="halvany">Magyarországi (geo=HU) Google Trends adatok, napi frissítéssel.</p>

  <p>Ez az oldal jelenleg <strong>placeholder</strong>: az interaktív grafikonok
  (kulcsszó-idősorok, napi top trendek, dátumválasztó) a <strong>Phase 3</strong>-ban
  érkeznek. Addig a nyers adat közvetlenül elérhető:</p>

  <ul>
    <li><a href="data/legfrissebb.json"><code>data/legfrissebb.json</code></a> — a legutóbbi futás összesítése</li>
    <li><a href="data/tortenet.json"><code>data/tortenet.json</code></a> — kulcsszó-történet (napi átlag + csúcs)</li>
    <li><a href="data/napok/index.json"><code>data/napok/index.json</code></a> — az elérhető napi trendlisták dátumai</li>
  </ul>

  <p class="halvany">Minden adat kizárólag Magyarországra (geo=HU), az elmúlt 24 órára vonatkozik.</p>
</body>
</html>
```

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_pages.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/index.html tests/test_pages.py
git commit -m "feat(pages): statikus placeholder landing a docs/-ban (Phase 2 Task 7)"
```

---

### Task 8: README — workflow, Pages-bekapcsolás, escalation-függelék

A README kiegészítése a Phase 2 valóságával: az automatikus futás, a Pages manuális bekapcsolása, a napló-cap és a 429-önjavítás rövid leírása, és az escalation-döntésfa (proxy — csak dokumentum).

**Files:**
- Modify: `README.md` (a „B terv" szakasz kibővítése / új szakaszok a végén)
- Test: nincs (dokumentáció); tartalmi ellenőrzés a Step 3-ban.

**Interfaces:**
- Consumes: a Task 6 workflow és a Task 7 oldal (a leírás rájuk hivatkozik).
- Produces: a `README.md` tartalmazza a Pages-bekapcsolás lépéseit és az escalation-függeléket.

- [ ] **Step 1: A README kiegészítése**

In `README.md`, a jelenlegi záró blockquote
```markdown
> A GitHub Actions-ütemezés és a GitHub Pages weboldal a következő fázisokban kerül a
> projektbe; ez a README azokat majd kiegészíti (Settings → Pages → `docs/`).
```
helyére illeszd:
```markdown
## Automatikus napi futás (GitHub Actions)

A `.github/workflows/napi.yml` napi egy futást végez. Kezdetben **csak kézi
indítással** (`Actions → Napi trendgyűjtés → Run workflow`) — ez méri fel, kap-e
429-et a felhő-runner IP-je. Ha a kézi futások tiszták, a `schedule:` sort
(`cron: "7 19 * * *"`, azaz 19:07 UTC ≈ késő este Budapesten) élesítjük.

A futás **csak** a `docs/data/*.json` fájlokat és az `adatok/naplo.csv`-t
commitolja (a web ezekből dolgozik); a per-futás nyers CSV-ket felhőben nem
őrizzük. Teljes blokk (429 minden ágon) → a job pirosan bukik → GitHub e-mail.

## GitHub Pages bekapcsolása

A **Settings → Pages** alatt: *Source* = `Deploy from a branch`, *Branch* =
`main` / `/docs`. Mentés után az oldal a `https://<felhasználó>.github.io/trendfigyelo/`
címen él, a `docs/index.html` placeholderrel (a teljes felület Phase 3).

## Robusztusság röviden

- **Napló-cap:** a `naplo.csv` a `config.yaml` `naplo_max_sor` (alap 2000)
  fölött a legutóbbi N sorra korlátozódik — nem hízik korlátlanul.
- **429-önjavítás:** a kulcsszó-ág a már lekért `now 7-d` ablakból az utolsó
  `tortenet_visszapotlas_nap` (alap 3) teljes napot upsertli a `tortenet.json`-ba
  (0 extra Google-hívás). Egy kimaradt nap a **következő** futásból visszapótlódik;
  a top-trend napi lista viszont az adott napra hiányos marad.

## Escalation-függelék — proxy (csak ha minden más kevés)

A `config.yaml` `proxy:` mezője kész (alap `null`). Csak akkor nyúlj hozzá, ha a
szelídebb megoldások mind kevésnek bizonyulnak:

1. Napi egy futás + részleges siker → **elég?** Ha igen, kész.
2. Ha a runner-IP tartósan 429-et kap: **futtass helyi gépről** (lakossági IP) —
   a `python top_keresesek.py` módosítás nélkül fut, a kimenet kézzel commitolható.
3. Csak ha 1–2 sem elég: adj meg egy HTTP(S)-proxyt a `config.yaml`
   `proxy:` mezőjében (`"http://user:pass@host:port"`). A `kliens.py` már átadja
   a trendspy-nak; új kód nem kell.
```

- [ ] **Step 2: A teljes suite zöld (nincs kódváltozás)**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 3: Tartalmi ellenőrzés**

Run: `grep -c "GitHub Pages\|Escalation\|429-önjavítás\|naplo_max_sor" README.md`
Expected: `>= 1` minden mintára (a szakaszok jelen vannak).

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): workflow, Pages-bekapcsolás, escalation-függelék (Phase 2 Task 8)"
```

---

## Merge + élesítés (kifelé ható — KÜLÖN, EGYENKÉNTI JÓVÁHAGYÁS)

A Task 1–8 után, a felhasználó vezérlésével (az implementer NE önállóan):

1. **Teljes zöld ellenőrzés:** `python -m pytest -q` a repó gyökeréből → mind zöld.
2. **Phase 2 → `main`:** a `feature/phase2-kozzetetel` PR-rel a `main`-be.
3. **GitHub Pages bekapcsolása:** Settings → Pages → `main` /docs (manuális kattintás).
   Ellenőrzés: a `…github.io/trendfigyelo/` betölti a placeholdert, a `data/…json`
   linkek elérhetők.
4. **A runner-IP első tesztje:** `Actions → Napi trendgyűjtés → Run workflow`
   (kézi). Figyeld: kilépési kód, a commitolt `adatok/naplo.csv` sorai (429?),
   a `docs/data/*.json` frissült-e. Ismételd néhány napon át.

---

### Task 9: A napi ütemezés élesítése (idő-kapuzott — a megfigyelés UTÁN)

Csak akkor, ha a kézi `workflow_dispatch` futások **stabilan tiszták** (nincs
azonnali 429 a runner-IP-ről a `naplo.csv`/Actions-logok szerint).

**Files:**
- Modify: `.github/workflows/napi.yml` (a `schedule:` bekommentelt blokk élesítése)

- [ ] **Step 1: A `schedule:` élesítése**

In `.github/workflows/napi.yml` cseréld:
```yaml
  # A napi ütemezés KÜLÖN, későbbi committal élesedik (Task 9), miután a kézi
  # futások megerősítették, hogy a runner-IP nem kap azonnali 429-et:
  # schedule:
  #   - cron: "7 19 * * *"   # 19:07 UTC — 21:07 nyár / 20:07 tél budapesti idő
```
erre:
```yaml
  schedule:
    - cron: "7 19 * * *"   # 19:07 UTC — 21:07 nyár / 20:07 tél budapesti idő
```

- [ ] **Step 2: YAML-validáció**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/napi.yml')); print('YAML OK')"`
Expected: `YAML OK`.

- [ ] **Step 3: Commit (a `main`-en / PR-rel)**

```bash
git add .github/workflows/napi.yml
git commit -m "ci(workflow): napi schedule 19:07 UTC élesítése (Phase 2 Task 9)"
```

- [ ] **Step 4: Ellenőrzés a következő ütemezett futáskor**

A cron a `main`-en él. Az első ütemezett futás után ellenőrizd az `Actions` logot
és a friss commitot; ha 429 jön, tér vissza a dispatch-only állapothoz (revert)
és fontold az escalation-függelék 2–3. lépését.

---

## Ledger (a plan végén, a Phase 1 mintája szerint — az implementer tölti)

A Phase 2 lezárásakor ide kerül: a teljes suite zöld állapota; az első éles
`workflow_dispatch` megfigyelt kimenete (kilépési kód, hívásszám, 429?); a Pages
URL; a `schedule` élesítésének dátuma és az első ütemezett futás eredménye.

---

## Self-Review (a terv ellenőrzése a spec ellen)

**Spec-lefedettség:**
- Spec 4.1 NaN → Task 1. ✓
- Spec 4.2 config-validáció → Task 2. ✓
- Spec 4.3 naplo-cap → Task 3. ✓
- Spec 5 (429-önjavítás, Option B N=3, insert-if-absent, CSV/legfrissebb egynapos) → Task 4–5. ✓
- Spec 6 (workflow, dispatch-first, szelektív add, permissions, concurrency, blokk→email) → Task 6 + Task 9. ✓
- Spec 7.1–7.2 (Pages bekapcsolás + placeholder) → Task 7 + „Merge + élesítés" 3. ✓
- Spec 7.3 (escalation-függelék) → Task 8. ✓
- Spec „Előfeltétel" (Phase 1 → main, phase2 ág) → Előfeltétel-szakasz. ✓

**Placeholder-scan:** nincs TBD/TODO; a Ledger szándékosan az implementer által kitöltendő futásadat, nem terv-placeholder. ✓

**Típus-konzisztencia:** `gyujt` új visszatérése `(list, dict)` — a `futtato` kicsomagolja, a két gyujt-teszt frissítve; `tortenet_frissit_napok(docs_data, napi_pontok: dict)` a `{nap_iso: [pontok]}` alakot fogyasztja, amit a `parse_koteg_napok`/`gyujt` termel; `utolso_N_teljes_nap` `list[date]`-et ad, a `parse_koteg_napok` `.isoformat()`-tal kulcsol. `naplo_ir` új `max_sor` paramétere defaultolt (meglévő hívók zöldek). A `Config` új mezői (`naplo_max_sor`, `tortenet_visszapotlas_nap`) defaultoltak. Konzisztens. ✓
