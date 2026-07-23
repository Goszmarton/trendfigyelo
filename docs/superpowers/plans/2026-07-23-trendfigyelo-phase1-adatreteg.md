# Trendfigyelő — Phase 1 (adatréteg) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `trendfigyelo/` Python-csomag felépítése, amely napi egy futással geo="HU", 24 órás Google Trends adatokat gyűjt (felkapott keresések + trend-idősorok + fix kulcsszavak) IP-blokkolás ellen védett, kíméletes lekérdezéssel, és CSV + JSON kimeneteket ír, helyi gépről hibamentesen futtatva.

**Architecture:** Fókuszált modulok egy Python-csomagban. A `config.yaml` az egyetlen forrás geo/időablak/nyelv/referenciaszó/kulcsszavak számára. Minden Google-hívás a `kliens.Kliens.hivas()` wrapperen megy át, amely véletlenített késleltetést és 429-backoffot ad. A gyűjtő modulok (`felkapott`, `idosorok`, `kulcsszavak`) tiszta parse-függvényekre + I/O-ra bontottak, hogy hálózat nélkül, mock/fixtúra adatokkal tesztelhetők legyenek. A `futtato` ágakat sorban hív, részleges sikert kezel, és a kilépési kóddal jelez teljes blokkolást.

**Tech Stack:** Python 3, trendspy (Google Trends), PyYAML (config), pandas (interest_over_time DataFrame), pytest (teszt). Nincs build-lépés.

## Global Constraints

Ezek MINDEN taskra vonatkoznak, akkor is, ha a task nem ismétli meg:

- **geo="HU" mindenhol.** Minden Google-hívás a configból vett geót kapja; geo nélküli lekérdezés tilos. Minden CSV-sor és JSON-bejegyzés tartalmaz `geo` mezőt.
- **Időablak = elmúlt 24 óra.** Felkapott: `hours=24` (config `idoablak_orak`). Idősorok: `timeframe="now 1-d"` (config `idosor_idokeret`).
- **Nyelv = magyar.** `language="hu"` (config `nyelv`). A kód kommentjei, változónevei, kimenetei magyarul.
- **Egyetlen konfigforrás.** geo/időablak/nyelv/referenciaszó/anti-block paraméterek CSAK a `config.yaml`-ból; nincs a kódba égetve.
- **Idő:** nyers adat UTC-ben (ISO, `timespec="seconds"`); fájlnevek és megjelenítendő időbélyegek budapesti idő (Europe/Budapest).
- **CSV formátum:** `;` elválasztó, `utf-8-sig` kódolás. A meglévő 3 CSV (api/rss/hirek) oszlopszerkezete és névsémája VÁLTOZATLAN.
- **Anti-block:** hívások közt véletlen 3–7 mp; 429 → exponenciális+jitteres backoff (max 4 próba), utána ág feladása + naplózás; nincs rövid ciklusú tömeges retry.
- **AgFeladva a looping ágakban:** a trend/köteg ciklust futtató ágak (`idosorok.gyujt`, `kulcsszavak.gyujt`) az `AgFeladva` (429-kimerülés) kivételt NEM nyelhetik el `continue`-val — az egész ágat fel kell adni (a kivétel továbbmegy a `futtato`-hoz block-detektálásra), különben blokkolás alatt elemenként újra lefutna a teljes backoff. Egyéb (nem-429) hiba csak az adott elemet hagyja ki.
- **Részleges siker = siker:** egy ág bukása nem dönti a többit; teljes bukás (semmi adat) → nem-nulla kilépési kód.
- **Nincs élő Google-teszt** a unit tesztekben — mock/fixtúra. Egyetlen kézi éles füst-teszt a végén, helyi gépről.
- **requirements.txt:** rögzített vagy alsó-korlátos verziók.

**Verziófloorok (requirements.txt):**
```
trendspy>=0.1.3
PyYAML>=6.0
pandas>=2.0
pytest>=8.0
```
(A pontos trendspy-verzió a záró éles füst-teszten véglegesítendő.)

---

## Fájlszerkezet (Phase 1 után)

```
trendfigyelo/
├── __init__.py
├── seged.py          # közös segédek: idő, szöveggé alakítás, CSV-író (Task 1)
├── config.py         # config.yaml betöltés + validálás (Task 2)
├── kliens.py         # Trends-kliens + 429-backoff wrapper + hívásszámláló (Task 3)
├── felkapott.py      # trending_now API + RSS → 3 CSV (Task 4)
├── idosorok.py       # trend-sparkline-ok → CSV (Task 5)
├── kulcsszavak.py    # 4+1 kötegelt kulcsszó-idősorok → CSV (Task 6)
├── naplo.py          # adatok/naplo.csv (Task 7)
├── json_export.py    # docs/data/*.json (Task 8)
└── futtato.py        # orchestráció, kilépési kód (Task 9)
config.yaml           # (Task 2)
requirements.txt      # (Task 1)
.gitignore            # (Task 1)
top_keresesek.py      # vékony belépő (Task 9) — a régi tartalom lecserélve
README.md             # (Task 10)
tests/                # pytest tesztek taskonként
```

---

### Task 1: Projekt-váz + közös segédek (`seged.py`)

Megalapozza a csomagot és a mindenhol használt segédfüggvényeket (idő, szöveggé alakítás, CSV-író). Ezekre minden későbbi modul épít.

**Files:**
- Create: `trendfigyelo/__init__.py` (üres)
- Create: `trendfigyelo/seged.py`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `tests/__init__.py` (üres)
- Create: `tests/test_seged.py`

**Interfaces:**
- Produces:
  - `BUDAPEST: ZoneInfo` — az Europe/Budapest zóna.
  - `most_utc() -> datetime` — aktuális idő UTC-ben (tz-aware).
  - `szovegge(ertek) -> str` — None → "", lista/tuple → ", "-vel összefűzve, egyéb → str.
  - `idove(ts) -> str` — unix időbélyeg (vagy `(ts, ...)` páros) → UTC ISO `timespec="seconds"`; hibás bemenet → `str(ts)`; None/0/"" → "".
  - `idopont_iso(ts) -> str` — datetime/pandas Timestamp → UTC ISO `timespec="seconds"`. tz-naiv bemenetet UTC-nek vesz.
  - `bp_idobelyeg(dt: datetime) -> str` — budapesti `"%Y-%m-%d_%H%M"` (fájlnévhez).
  - `csv_iro(fajl: Path) -> tuple[TextIO, "csv.writer"]` — `utf-8-sig`, `;` elválasztó író.

- [ ] **Step 1: Failing teszt — `seged.py` segédek**

Create `tests/test_seged.py`:
```python
from datetime import datetime, timezone
from pathlib import Path

from trendfigyelo import seged


def test_szovegge_kezeli_a_none_es_lista_eseteket():
    assert seged.szovegge(None) == ""
    assert seged.szovegge(["a", "b"]) == "a, b"
    assert seged.szovegge(42) == "42"


def test_idove_unix_bol_utc_iso():
    # 2021-01-01T00:00:00Z == 1609459200
    assert seged.idove(1609459200) == "2021-01-01T00:00:00+00:00"
    assert seged.idove(None) == ""
    assert seged.idove((1609459200, 999)) == "2021-01-01T00:00:00+00:00"


def test_idopont_iso_tz_naiv_datetime_utcnek_veszi():
    assert seged.idopont_iso(datetime(2021, 1, 1, 0, 0, 0)) == "2021-01-01T00:00:00+00:00"


def test_bp_idobelyeg_budapesti_ido():
    # 2021-06-01T10:00:00Z nyáron Budapesten 12:00 (UTC+2)
    dt = datetime(2021, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert seged.bp_idobelyeg(dt) == "2021-06-01_1200"


def test_csv_iro_utf8_sig_es_pontosvesszo(tmp_path):
    fajl = tmp_path / "t.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow(["á", "b"])
    nyers = fajl.read_bytes()
    assert nyers.startswith(b"\xef\xbb\xbf")  # utf-8-sig BOM
    assert b";" in nyers
```

- [ ] **Step 2: Futtatás — bukjon**

Run: `python -m pytest tests/test_seged.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'trendfigyelo'` vagy hiányzó függvények.

- [ ] **Step 3: Csomag-váz + `seged.py`**

Create `trendfigyelo/__init__.py` (üres fájl).
Create `tests/__init__.py` (üres fájl).
Create `trendfigyelo/seged.py`:
```python
"""Közös segédfüggvények: idő, szöveggé alakítás, CSV-író."""

import csv
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BUDAPEST = ZoneInfo("Europe/Budapest")


def most_utc() -> datetime:
    """Aktuális idő UTC-ben, tz-aware."""
    return datetime.now(timezone.utc)


def szovegge(ertek) -> str:
    """None/lista biztonságos szöveggé alakítása egy CSV-cellába."""
    if ertek is None:
        return ""
    if isinstance(ertek, (list, tuple)):
        return ", ".join(str(e) for e in ertek)
    return str(ertek)


def idove(ts) -> str:
    """Unix-időbélyeg (vagy (ts, ...) páros) olvasható UTC-idővé."""
    if isinstance(ts, (list, tuple)):
        ts = ts[0] if ts else None
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat(timespec="seconds")
    except (ValueError, TypeError, OSError):
        return str(ts)


def idopont_iso(ts) -> str:
    """datetime/pandas Timestamp → UTC ISO. tz-naiv bemenetet UTC-nek vesz."""
    dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
    if not isinstance(dt, datetime):
        return str(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def bp_idobelyeg(dt: datetime) -> str:
    """Budapesti idő fájlnévhez: '%Y-%m-%d_%H%M'."""
    return f"{dt.astimezone(BUDAPEST):%Y-%m-%d_%H%M}"


def csv_iro(fajl: Path):
    """utf-8-sig, pontosvesszős CSV-író. Visszaad: (fájlobjektum, writer)."""
    f = fajl.open("w", newline="", encoding="utf-8-sig")
    return f, csv.writer(f, delimiter=";")
```

- [ ] **Step 4: Futtatás — menjen át**

Run: `python -m pytest tests/test_seged.py -v`
Expected: PASS (mind az 5 teszt).

- [ ] **Step 5: `requirements.txt` és `.gitignore`**

Create `requirements.txt`:
```
trendspy>=0.1.3
PyYAML>=6.0
pandas>=2.0
pytest>=8.0
```

Create `.gitignore`:
```
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.DS_Store
```
(Megjegyzés: az `adatok/` és a `docs/data/` NEM ignorált — ezeket commitoljuk.)

- [ ] **Step 6: Commit**

```bash
git add trendfigyelo/__init__.py trendfigyelo/seged.py tests/__init__.py tests/test_seged.py requirements.txt .gitignore
git commit -m "feat(seged): közös segédek + projekt-váz (Phase 1 Task 1)"
```

---

### Task 2: Konfiguráció (`config.py` + `config.yaml`)

Az egyetlen konfigforrás betöltése és validálása. Minden későbbi modul innen kap geót/időablakot/nyelvet/referenciaszót/kulcsszavakat.

**Files:**
- Create: `trendfigyelo/config.py`
- Create: `config.yaml`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: —
- Produces:
  - `class KonfigHiba(Exception)` — hiányzó/hibás konfig esetén.
  - `@dataclass class Config` mezők: `geo: str`, `nyelv: str`, `idoablak_orak: int`, `idosor_idokeret: str`, `referenciaszo: str`, `alap_keses_mp: float`, `szoras_mp: tuple[float, float]`, `max_probak: int`, `backoff_mp: list[int]`, `trend_idosor_max: int`, `proxy: str | None`, `kulcsszavak: dict[str, list[str]]`.
  - `Config.osszes_kulcsszo(self) -> list[tuple[str, str]]` — `[(kulcsszo, csoport), ...]` a beolvasás sorrendjében.
  - `betolt(utvonal: str | Path = "config.yaml") -> Config`.

- [ ] **Step 1: Failing teszt — betöltés + validálás**

Create `tests/test_config.py`:
```python
import textwrap

import pytest

from trendfigyelo import config


def _ir(tmp_path, szoveg):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent(szoveg), encoding="utf-8")
    return p


JO = """
geo: HU
nyelv: hu
idoablak_orak: 24
idosor_idokeret: "now 1-d"
referenciaszo: "időjárás"
kerespont:
  alap_keses_mp: 3.0
  szoras_mp: [3, 7]
  max_probak: 4
  backoff_mp: [30, 120, 480]
trend_idosor_max: 15
proxy: null
kulcsszavak:
  megelhetes: [infláció, benzinár]
  gazdaság: [forint árfolyam]
"""


def test_betolt_kiolvassa_a_mezoket(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.geo == "HU"
    assert c.referenciaszo == "időjárás"
    assert c.szoras_mp == (3, 7)
    assert c.backoff_mp == [30, 120, 480]
    assert c.trend_idosor_max == 15
    assert c.proxy is None


def test_osszes_kulcsszo_csoporttal(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.osszes_kulcsszo() == [
        ("infláció", "megelhetes"),
        ("benzinár", "megelhetes"),
        ("forint árfolyam", "gazdaság"),
    ]


def test_hianyzo_kotelezo_mezo_konfighibat_dob(tmp_path):
    rossz = JO.replace("geo: HU", "")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_ures_kulcsszolista_konfighibat_dob(tmp_path):
    rossz = JO.split("kulcsszavak:")[0] + "kulcsszavak: {}\n"
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))
```

- [ ] **Step 2: Futtatás — bukjon**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — hiányzó `trendfigyelo.config`.

- [ ] **Step 3: `config.py`**

Create `trendfigyelo/config.py`:
```python
"""A config.yaml betöltése és validálása — az egyetlen konfigforrás."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class KonfigHiba(Exception):
    """Hiányzó vagy hibás konfigurációs érték."""


@dataclass
class Config:
    geo: str
    nyelv: str
    idoablak_orak: int
    idosor_idokeret: str
    referenciaszo: str
    alap_keses_mp: float
    szoras_mp: tuple
    max_probak: int
    backoff_mp: list
    trend_idosor_max: int
    proxy: object  # str | None
    kulcsszavak: dict = field(default_factory=dict)

    def osszes_kulcsszo(self):
        """[(kulcsszo, csoport), ...] a beolvasás sorrendjében."""
        parok = []
        for csoport, szavak in self.kulcsszavak.items():
            for szo in szavak:
                parok.append((szo, csoport))
        return parok


def _kell(d: dict, kulcs: str, hol: str):
    if kulcs not in d or d[kulcs] in (None, ""):
        raise KonfigHiba(f"Hiányzó konfigmező: {hol}{kulcs}")
    return d[kulcs]


def betolt(utvonal="config.yaml") -> Config:
    """A config.yaml beolvasása Config objektummá; hibás konfig → KonfigHiba."""
    p = Path(utvonal)
    if not p.exists():
        raise KonfigHiba(f"Nincs konfigfájl: {p}")
    try:
        nyers = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise KonfigHiba(f"Hibás YAML: {e}") from e

    kp = nyers.get("kerespont") or {}
    kulcsszavak = nyers.get("kulcsszavak") or {}
    if not any(kulcsszavak.values()):
        raise KonfigHiba("A 'kulcsszavak' üres — legalább egy csoport, egy szóval.")

    szoras = _kell(kp, "szoras_mp", "kerespont.")
    return Config(
        geo=_kell(nyers, "geo", ""),
        nyelv=_kell(nyers, "nyelv", ""),
        idoablak_orak=int(_kell(nyers, "idoablak_orak", "")),
        idosor_idokeret=_kell(nyers, "idosor_idokeret", ""),
        referenciaszo=_kell(nyers, "referenciaszo", ""),
        alap_keses_mp=float(_kell(kp, "alap_keses_mp", "kerespont.")),
        szoras_mp=(float(szoras[0]), float(szoras[1])),
        max_probak=int(_kell(kp, "max_probak", "kerespont.")),
        backoff_mp=list(_kell(kp, "backoff_mp", "kerespont.")),
        trend_idosor_max=int(_kell(nyers, "trend_idosor_max", "")),
        proxy=nyers.get("proxy"),
        kulcsszavak=kulcsszavak,
    )
```

- [ ] **Step 4: Futtatás — menjen át**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (mind a 4 teszt).

- [ ] **Step 5: `config.yaml` a teljes induló tartalommal**

Create `config.yaml`:
```yaml
# Trendfigyelő — az EGYETLEN konfigforrás. geo/időablak/nyelv/referenciaszó/kulcsszavak.
geo: HU
nyelv: hu
idoablak_orak: 24            # felkapott trendek: hours=24
idosor_idokeret: "now 1-d"   # interest_over_time timeframe (elmúlt 24 óra)
referenciaszo: "időjárás"    # stabil, magas volumenű HU kifejezés a kötegek normalizálásához
kerespont:                   # anti-block (IP-blokkolás elleni) paraméterek
  alap_keses_mp: 3.0
  szoras_mp: [3, 7]          # véletlen 3–7 mp két hívás közt
  max_probak: 4              # 429 esetén max ennyi próba, utána az ág feladva
  backoff_mp: [30, 120, 480] # exponenciális visszavárakozás (mp)
trend_idosor_max: 15         # hány top trend kapjon idősort (sparkline)
proxy: null                  # pl. "http://user:pass@host:port" — alap: nincs
kulcsszavak:
  megelhetes: [infláció, benzinár, rezsi, élelmiszerárak, albérlet, lakáshitel, minimálbér, nyugdíj]
  gazdaság:   [forint árfolyam, euró árfolyam, MNB, kamat, munkanélküliség, adóváltozás]
  közélet:    [választás, kormány, népszavazás, tüntetés, egészségügy, oktatás, pedagógus, kórház]
```

- [ ] **Step 6: Betöltés-ellenőrzés az éles configon**

Run: `python -c "from trendfigyelo import config; c=config.betolt(); print(len(c.osszes_kulcsszo()), 'kulcsszó,', c.geo)"`
Expected: `22 kulcsszó, HU`

- [ ] **Step 7: Commit**

```bash
git add trendfigyelo/config.py config.yaml tests/test_config.py
git commit -m "feat(config): config.yaml betöltés + validálás (Phase 1 Task 2)"
```

---

### Task 3: Trends-kliens + anti-block wrapper (`kliens.py`)

A rendszer legkockázatosabb pontja. Minden Google-hívás ezen a wrapperen megy át: véletlen késleltetés, 429-backoff, hívásszámlálás, ág-feladás.

**Files:**
- Create: `trendfigyelo/kliens.py`
- Create: `tests/test_kliens.py`

**Interfaces:**
- Consumes: `config.Config` (Task 2).
- Produces:
  - `class AgFeladva(Exception)` — attribútumok: `.ag: str`, `.hibakodok: list[str]`.
  - `rate_limit_hiba(exc: Exception) -> bool` — igaz, ha az kivétel 429/rate-limit.
  - `class Kliens`:
    - `__init__(self, config: Config, trends=None)` — ha `trends` None, `Trends(language=config.nyelv, request_delay=config.alap_keses_mp, proxy=config.proxy)`-t épít. A `trends` paraméter injektálható a teszthez.
    - `.tr` — az alatta lévő trendspy `Trends` példány.
    - `hivas(self, ag: str, fn, *args, **kwargs)` — meghívja `fn(*args, **kwargs)`-t; előtte véletlen alvás; 429 → backoff+újrapróba (max `config.max_probak`), kimerülve `AgFeladva`; nem-429 kivétel továbbdobva. Minden próbát számol.
    - `hivasszam(self, ag: str) -> int`, `osszes_hivas(self) -> int`.

**Fontos:** a `time.sleep` és `random.uniform` a `kliens` modul szintjén hívva, hogy a teszt patch-elhesse őket (ne aludjon valóban).

- [ ] **Step 1: Failing teszt — számlálás, backoff, ág-feladás, nem-429 továbbdobás**

Create `tests/test_kliens.py`:
```python
import pytest

from trendfigyelo import kliens
from trendfigyelo.config import Config


def _config():
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        referenciaszo="időjárás", alap_keses_mp=3.0, szoras_mp=(3, 7),
        max_probak=4, backoff_mp=[30, 120, 480], trend_idosor_max=15,
        proxy=None, kulcsszavak={"g": ["x"]},
    )


class HibaKoddal(Exception):
    def __init__(self, kod):
        super().__init__(f"HTTP {kod}")
        self.status_code = kod


@pytest.fixture(autouse=True)
def ne_aludj(monkeypatch):
    monkeypatch.setattr(kliens.time, "sleep", lambda *_: None)
    monkeypatch.setattr(kliens.random, "uniform", lambda a, b: a)


def test_rate_limit_hiba_felismeri_a_429et():
    assert kliens.rate_limit_hiba(HibaKoddal(429)) is True
    assert kliens.rate_limit_hiba(Exception("valami 429 Too Many Requests")) is True
    assert kliens.rate_limit_hiba(Exception("hálózati hiba")) is False


def test_sikeres_hivas_szamol_es_visszaad():
    k = kliens.Kliens(_config(), trends=object())
    eredmeny = k.hivas("teszt", lambda x: x * 2, 21)
    assert eredmeny == 42
    assert k.hivasszam("teszt") == 1
    assert k.osszes_hivas() == 1


def test_429_utan_feladja_az_agat_es_minden_probat_szamol():
    k = kliens.Kliens(_config(), trends=object())

    def mindig_429():
        raise HibaKoddal(429)

    with pytest.raises(kliens.AgFeladva) as info:
        k.hivas("idosor", mindig_429)
    assert info.value.ag == "idosor"
    assert k.hivasszam("idosor") == 4  # max_probak próbálkozás


def test_nem_429_kivetel_tovabbdobva_retry_nelkul():
    k = kliens.Kliens(_config(), trends=object())

    def halozati():
        raise RuntimeError("hálózati hiba")

    with pytest.raises(RuntimeError):
        k.hivas("api", halozati)
    assert k.hivasszam("api") == 1  # nincs újrapróba nem-429-re
```

- [ ] **Step 2: Futtatás — bukjon**

Run: `python -m pytest tests/test_kliens.py -v`
Expected: FAIL — hiányzó `trendfigyelo.kliens`.

- [ ] **Step 3: `kliens.py`**

Create `trendfigyelo/kliens.py`:
```python
"""Trends-kliens véletlenített késleltetéssel és 429-backoffal (IP-blokkolás elleni védelem)."""

import random
import time


class AgFeladva(Exception):
    """Egy lekérdezési ág feladva ismételt 429 (rate limit) miatt."""

    def __init__(self, ag: str, hibakodok):
        super().__init__(f"'{ag}' ág feladva {len(hibakodok)} próba után: {hibakodok}")
        self.ag = ag
        self.hibakodok = hibakodok


def rate_limit_hiba(exc: Exception) -> bool:
    """Igaz, ha a kivétel HTTP 429 / rate limit."""
    kod = getattr(exc, "status_code", None)
    if kod is None:
        valasz = getattr(exc, "response", None)
        kod = getattr(valasz, "status_code", None)
    if kod == 429:
        return True
    szoveg = str(exc).lower()
    return "429" in szoveg or "too many requests" in szoveg


class Kliens:
    """Minden Google-hívás ezen megy át: késleltetés, 429-backoff, hívásszámlálás."""

    def __init__(self, config, trends=None):
        self.config = config
        if trends is None:
            from trendspy import Trends
            trends = Trends(
                language=config.nyelv,
                request_delay=config.alap_keses_mp,
                proxy=config.proxy,
            )
        self.tr = trends
        self._szamlalok = {}

    def _var(self):
        also, felso = self.config.szoras_mp
        time.sleep(random.uniform(also, felso))

    def _backoff(self, proba: int):
        bo = self.config.backoff_mp
        alap = bo[min(proba, len(bo) - 1)]
        time.sleep(alap + random.uniform(0, alap * 0.25))

    def hivas(self, ag: str, fn, *args, **kwargs):
        """fn meghívása anti-block védelemmel; 429 kimerülésnél AgFeladva."""
        self._szamlalok.setdefault(ag, 0)
        hibakodok = []
        for proba in range(self.config.max_probak):
            self._var()
            self._szamlalok[ag] += 1
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if not rate_limit_hiba(e):
                    raise
                hibakodok.append("429")
                if proba < self.config.max_probak - 1:
                    self._backoff(proba)
        raise AgFeladva(ag, hibakodok)

    def hivasszam(self, ag: str) -> int:
        return self._szamlalok.get(ag, 0)

    def osszes_hivas(self) -> int:
        return sum(self._szamlalok.values())
```

- [ ] **Step 4: Futtatás — menjen át**

Run: `python -m pytest tests/test_kliens.py -v`
Expected: PASS (mind a 4 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/kliens.py tests/test_kliens.py
git commit -m "feat(kliens): anti-block Trends-wrapper 429-backoffal (Phase 1 Task 3)"
```

---

### Task 4: Felkapott keresések ág (`felkapott.py`)

A meglévő két forrás (trending_now API + RSS) parse-olása és a **változatlan szerkezetű** 3 CSV kiírása. A parse tiszta függvényekben, mock trend-objektumokkal tesztelve.

**Files:**
- Create: `trendfigyelo/felkapott.py`
- Create: `tests/test_felkapott.py`

**Interfaces:**
- Consumes: `kliens.Kliens` (Task 3), `config.Config` (Task 2), `seged` (Task 1).
- Produces:
  - `api_trend_dict(t, sorszam: int) -> dict` — kulcsok: `sorszam, kifejezes, volumen, novekedes_pct, trend_indult_utc, trend_veget_ert_utc, aktiv, kapcsolodo_kifejezesek, temak, normalizalt_kifejezes`.
  - `rss_trend_dict(t, sorszam: int) -> dict` — kulcsok: `sorszam, kifejezes, volumen, kapcsolodo_kifejezesek, trend_indult_utc, kep_url, kep_forras, hirek_szama`.
  - `hir_sorok(rss_trendek: list) -> list[dict]` — kulcsok: `sorszam, kifejezes, hir_cim, hir_forras, hir_url, hir_ido_utc, hir_kep, hir_kivonat`.
  - `volumen_szam(t) -> int` — a trend numerikus volumene rendezéshez (hiba → 0).
  - `gyujt_api(kliens, config) -> list` — nyers trending_now trend-objektumok (a `kliens.hivas("felkapott_api", ...)`-on át).
  - `gyujt_rss(kliens, config) -> list` — nyers RSS trend-objektumok.
  - `csv_ir_api(mappa, idobelyeg, letoltve, geo, api_trendek) -> Path | None`
  - `csv_ir_rss(mappa, idobelyeg, letoltve, geo, rss_trendek) -> Path | None`
  - `csv_ir_hirek(mappa, idobelyeg, geo, rss_trendek) -> Path | None`

- [ ] **Step 1: Failing teszt — parse + CSV**

Create `tests/test_felkapott.py`:
```python
from types import SimpleNamespace

from trendfigyelo import felkapott


def _api_trend():
    return SimpleNamespace(
        keyword="infláció", volume=50000, volume_growth_pct=120,
        started_timestamp=(1609459200, 0), ended_timestamp=None,
        is_trend_finished=False, trend_keywords=["ár", "MNB"],
        topic_names=["gazdaság"], normalized_keyword="inflacio",
    )


def _rss_trend():
    hir = SimpleNamespace(title="Címsor", source="Index", url="http://x",
                          time=1609459200, picture="http://k", snippet="kivonat")
    return SimpleNamespace(keyword="benzinár", volume="20000",
                           trend_keywords=["üzemanyag"], started=1609459200,
                           picture="http://p", picture_source="MTI", news=[hir])


def test_api_trend_dict_oszlopok():
    d = felkapott.api_trend_dict(_api_trend(), 1)
    assert d["kifejezes"] == "infláció"
    assert d["volumen"] == "50000"
    assert d["aktiv"] == "igen"  # is_trend_finished False → aktív
    assert d["trend_indult_utc"] == "2021-01-01T00:00:00+00:00"
    assert d["kapcsolodo_kifejezesek"] == "ár, MNB"


def test_volumen_szam_hibatur():
    assert felkapott.volumen_szam(_api_trend()) == 50000
    assert felkapott.volumen_szam(SimpleNamespace(volume=None)) == 0


def test_hir_sorok_soronkent_egy_hir():
    sorok = felkapott.hir_sorok([_rss_trend()])
    assert len(sorok) == 1
    assert sorok[0]["hir_cim"] == "Címsor"
    assert sorok[0]["kifejezes"] == "benzinár"


def test_csv_ir_api_fejlec_es_geo_oszlop(tmp_path):
    p = felkapott.csv_ir_api(tmp_path, "2021-01-01_1200", "2021-01-01T12:00:00+00:00",
                             "HU", [_api_trend()])
    tartalom = p.read_text(encoding="utf-8-sig")
    fejlec = tartalom.splitlines()[0]
    assert fejlec.split(";")[1] == "kifejezes"
    assert fejlec.strip().endswith("geo")
    assert "HU" in tartalom.splitlines()[1]
    assert p.name == "top_keresesek_api_HU_2021-01-01_1200.csv"
```

- [ ] **Step 2: Futtatás — bukjon**

Run: `python -m pytest tests/test_felkapott.py -v`
Expected: FAIL — hiányzó `trendfigyelo.felkapott`.

- [ ] **Step 3: `felkapott.py`**

Create `trendfigyelo/felkapott.py`:
```python
"""Felkapott keresések ág: trending_now API + RSS → a meglévő 3 CSV (változatlan séma)."""

from pathlib import Path

from . import seged


def volumen_szam(t) -> int:
    """A trend numerikus volumene rendezéshez; hibás/hiányzó → 0."""
    try:
        return int(getattr(t, "volume", 0) or 0)
    except (ValueError, TypeError):
        return 0


def api_trend_dict(t, sorszam: int) -> dict:
    return {
        "sorszam": sorszam,
        "kifejezes": t.keyword,
        "volumen": seged.szovegge(getattr(t, "volume", None)),
        "novekedes_pct": seged.szovegge(getattr(t, "volume_growth_pct", None)),
        "trend_indult_utc": seged.idove(getattr(t, "started_timestamp", None)),
        "trend_veget_ert_utc": seged.idove(getattr(t, "ended_timestamp", None)),
        "aktiv": "nem" if getattr(t, "is_trend_finished", False) else "igen",
        "kapcsolodo_kifejezesek": seged.szovegge(getattr(t, "trend_keywords", None)),
        "temak": seged.szovegge(getattr(t, "topic_names", None)),
        "normalizalt_kifejezes": seged.szovegge(getattr(t, "normalized_keyword", None)),
    }


def rss_trend_dict(t, sorszam: int) -> dict:
    return {
        "sorszam": sorszam,
        "kifejezes": t.keyword,
        "volumen": seged.szovegge(getattr(t, "volume", None)),
        "kapcsolodo_kifejezesek": seged.szovegge(getattr(t, "trend_keywords", None)),
        "trend_indult_utc": seged.idove(getattr(t, "started", None)),
        "kep_url": seged.szovegge(getattr(t, "picture", None)),
        "kep_forras": seged.szovegge(getattr(t, "picture_source", None)),
        "hirek_szama": len(getattr(t, "news", None) or []),
    }


def hir_sorok(rss_trendek) -> list:
    sorok = []
    for i, t in enumerate(rss_trendek, 1):
        for hir in getattr(t, "news", None) or []:
            sorok.append({
                "sorszam": i,
                "kifejezes": t.keyword,
                "hir_cim": seged.szovegge(getattr(hir, "title", None)),
                "hir_forras": seged.szovegge(getattr(hir, "source", None)),
                "hir_url": seged.szovegge(getattr(hir, "url", None)),
                "hir_ido_utc": seged.idove(getattr(hir, "time", None)),
                "hir_kep": seged.szovegge(getattr(hir, "picture", None)),
                "hir_kivonat": seged.szovegge(getattr(hir, "snippet", None)),
            })
    return sorok


def gyujt_api(kliens, config) -> list:
    """trending_now API — a teljes 24 órás HU lista."""
    return kliens.hivas("felkapott_api", kliens.tr.trending_now,
                        geo=config.geo, hours=config.idoablak_orak) or []


def gyujt_rss(kliens, config) -> list:
    """RSS — tartalék + hírek."""
    return kliens.hivas("felkapott_rss", kliens.tr.trending_now_by_rss,
                        geo=config.geo) or []


def csv_ir_api(mappa, idobelyeg, letoltve, geo, api_trendek):
    if not api_trendek:
        return None
    fajl = Path(mappa) / f"top_keresesek_api_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow([
            "sorszam", "kifejezes", "volumen", "novekedes_pct",
            "trend_indult_utc", "trend_veget_ert_utc", "aktiv",
            "kapcsolodo_kifejezesek", "temak", "normalizalt_kifejezes",
            "letoltve_utc", "forras", "geo",
        ])
        for i, t in enumerate(api_trendek, 1):
            d = api_trend_dict(t, i)
            iro.writerow([
                d["sorszam"], d["kifejezes"], d["volumen"], d["novekedes_pct"],
                d["trend_indult_utc"], d["trend_veget_ert_utc"], d["aktiv"],
                d["kapcsolodo_kifejezesek"], d["temak"], d["normalizalt_kifejezes"],
                letoltve, "trending_now", geo,
            ])
    return fajl


def csv_ir_rss(mappa, idobelyeg, letoltve, geo, rss_trendek):
    if not rss_trendek:
        return None
    fajl = Path(mappa) / f"top_keresesek_rss_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow([
            "sorszam", "kifejezes", "volumen", "kapcsolodo_kifejezesek",
            "trend_indult_utc", "kep_url", "kep_forras", "hirek_szama",
            "letoltve_utc", "forras", "geo",
        ])
        for i, t in enumerate(rss_trendek, 1):
            d = rss_trend_dict(t, i)
            iro.writerow([
                d["sorszam"], d["kifejezes"], d["volumen"], d["kapcsolodo_kifejezesek"],
                d["trend_indult_utc"], d["kep_url"], d["kep_forras"], d["hirek_szama"],
                letoltve, "rss", geo,
            ])
    return fajl


def csv_ir_hirek(mappa, idobelyeg, geo, rss_trendek):
    if not rss_trendek:
        return None
    fajl = Path(mappa) / f"top_keresesek_hirek_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow([
            "sorszam", "kifejezes", "hir_cim", "hir_forras", "hir_url",
            "hir_ido_utc", "hir_kep", "hir_kivonat",
        ])
        for s in hir_sorok(rss_trendek):
            iro.writerow([
                s["sorszam"], s["kifejezes"], s["hir_cim"], s["hir_forras"],
                s["hir_url"], s["hir_ido_utc"], s["hir_kep"], s["hir_kivonat"],
            ])
    return fajl
```

- [ ] **Step 4: Futtatás — menjen át**

Run: `python -m pytest tests/test_felkapott.py -v`
Expected: PASS (mind a 4 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/felkapott.py tests/test_felkapott.py
git commit -m "feat(felkapott): trending_now + RSS ág, 3 CSV változatlan sémával (Phase 1 Task 4)"
```

---

### Task 5: Trend-idősorok ág (`idosorok.py`)

A top-N trendhez egyenkénti `interest_over_time` hívás (geo="HU", "now 1-d") — így minden trend saját 0–100 sparkline-t kap (a shape megmarad). Egy trend bukása kihagyja azt az egyet, a többi megy tovább.

**Files:**
- Create: `trendfigyelo/idosorok.py`
- Create: `tests/test_idosorok.py`

**Interfaces:**
- Consumes: `kliens.Kliens`, `config.Config`, `seged`.
- Produces:
  - `df_idosor(df, kifejezes: str, forras: str) -> list[dict]` — egy oszlopos DataFrame → pontok. Kulcsok: `kifejezes, idopont_utc, ertek, forras`. Az `isPartial` oszlopot kihagyja.
  - `gyujt(kliens, config, top_kifejezesek: list[str]) -> list[dict]` — top-N kifejezésre egyenként `interest_over_time`; bukott kifejezés kihagyva.
  - `csv_ir(mappa, idobelyeg, letoltve, geo, pontok) -> Path | None` — fejléc: `kifejezes; idopont_utc; ertek; letoltve_utc; forras; geo`.

- [ ] **Step 1: Failing teszt — DataFrame parse + CSV**

Create `tests/test_idosorok.py`:
```python
from datetime import datetime, timezone

import pandas as pd

from trendfigyelo import idosorok


def _df():
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 1, 11, tzinfo=timezone.utc),
    ])
    return pd.DataFrame({"infláció": [40, 80], "isPartial": [False, True]}, index=idx)


def test_df_idosor_pontok_es_ispartial_kihagyva():
    pontok = idosorok.df_idosor(_df(), "infláció", "interest_over_time")
    assert len(pontok) == 2
    assert pontok[0]["idopont_utc"] == "2021-01-01T10:00:00+00:00"
    assert pontok[0]["ertek"] == 40
    assert pontok[1]["ertek"] == 80
    assert all(p["kifejezes"] == "infláció" for p in pontok)


def test_csv_ir_fejlec_es_geo(tmp_path):
    pontok = idosorok.df_idosor(_df(), "infláció", "interest_over_time")
    p = idosorok.csv_ir(tmp_path, "2021-01-01_1200", "2021-01-01T12:00:00+00:00", "HU", pontok)
    sorok = p.read_text(encoding="utf-8-sig").splitlines()
    assert sorok[0] == "kifejezes;idopont_utc;ertek;letoltve_utc;forras;geo"
    assert sorok[1].endswith(";HU")
    assert p.name == "top_trend_idosor_HU_2021-01-01_1200.csv"
```

- [ ] **Step 2: Futtatás — bukjon**

Run: `python -m pytest tests/test_idosorok.py -v`
Expected: FAIL — hiányzó `trendfigyelo.idosorok`.

- [ ] **Step 3: `idosorok.py`**

Create `trendfigyelo/idosorok.py`:
```python
"""Trend-idősorok ág: top-N trend 24 órás sparkline-ja (geo=HU, now 1-d)."""

from pathlib import Path

from . import seged
from .kliens import AgFeladva


def df_idosor(df, kifejezes: str, forras: str) -> list:
    """Egy oszlopos interest_over_time DataFrame → idősor-pontok."""
    pontok = []
    if df is None or len(df) == 0:
        return pontok
    oszlop = kifejezes if kifejezes in df.columns else _elso_ertek_oszlop(df, kifejezes)
    if oszlop is None:
        return pontok
    for idx, sor in df.iterrows():
        pontok.append({
            "kifejezes": kifejezes,
            "idopont_utc": seged.idopont_iso(idx),
            "ertek": int(sor[oszlop]) if _szam(sor[oszlop]) else seged.szovegge(sor[oszlop]),
            "forras": forras,
        })
    return pontok


def _elso_ertek_oszlop(df, kifejezes):
    for c in df.columns:
        if str(c).lower() != "ispartial":
            return c
    return None


def _szam(x) -> bool:
    try:
        int(x)
        return True
    except (ValueError, TypeError):
        return False


def gyujt(kliens, config, top_kifejezesek) -> list:
    """Top-N kifejezés egyenkénti idősora.

    AgFeladva (429-kimerülés) esetén az EGÉSZ ágat feladjuk (a kivétel
    továbbmegy a futtato-hoz block-detektálásra) — nem hammereljük tovább a
    Google-t trendenként. Egyéb hiba csak az adott trendet hagyja ki.
    """
    pontok = []
    for kif in top_kifejezesek[: config.trend_idosor_max]:
        try:
            df = kliens.hivas(
                "idosor", kliens.tr.interest_over_time,
                [kif], geo=config.geo, timeframe=config.idosor_idokeret,
            )
        except AgFeladva:  # 429-kimerülés → az egész ág feladva
            print(f"FIGYELEM: az idősor-ág feladva (429) a(z) '{kif}' kifejezésnél.")
            raise
        except Exception as e:  # egyetlen trend egyéb hibája nem dönti a többit
            print(f"FIGYELEM: '{kif}' idősora kimaradt ({e}).")
            continue
        pontok.extend(df_idosor(df, kif, "interest_over_time"))
    return pontok


def csv_ir(mappa, idobelyeg, letoltve, geo, pontok):
    if not pontok:
        return None
    fajl = Path(mappa) / f"top_trend_idosor_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow(["kifejezes", "idopont_utc", "ertek", "letoltve_utc", "forras", "geo"])
        for p in pontok:
            iro.writerow([p["kifejezes"], p["idopont_utc"], p["ertek"], letoltve, p["forras"], geo])
    return fajl
```

- [ ] **Step 4: Futtatás — menjen át**

Run: `python -m pytest tests/test_idosorok.py -v`
Expected: PASS (mind a 2 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/idosorok.py tests/test_idosorok.py
git commit -m "feat(idosorok): top-N trend sparkline interest_over_time-ból (Phase 1 Task 5)"
```

---

### Task 6: Kulcsszó-idősorok ág (`kulcsszavak.py`)

A fix kulcsszólista 4+1 kötegelt lekérdezése egy közös referenciaszóval; nyers ÉS normalizált érték mentése. A kötegelés és normalizálás tiszta függvényben, DataFrame-fixtúrával tesztelve.

**Files:**
- Create: `trendfigyelo/kulcsszavak.py`
- Create: `tests/test_kulcsszavak.py`

**Interfaces:**
- Consumes: `kliens.Kliens`, `config.Config`, `seged`.
- Produces:
  - `kotegek(config) -> list[dict]` — minden köteg: `{"id": int, "tagok": [(kulcsszo, csoport), ...], "referenciaszo": str}`, kötegenként max 4 tag.
  - `koteg_lekerdezes_szavai(koteg) -> list[str]` — a 4 kulcsszó + a referenciaszó (utolsóként).
  - `skalazo(ref_ertekek: list) -> float | None` — `100 / ref_átlag`, ha az átlag > 0, különben `None`.
  - `parse_koteg(df, koteg) -> list[dict]` — kulcsok: `kulcsszo, csoport, idopont_utc, nyers_ertek, normalizalt_ertek, koteg_id, referenciaszo`.
  - `gyujt(kliens, config) -> list[dict]` — minden köteget lekér és parse-ol; bukott köteg kihagyva.
  - `csv_ir(mappa, idobelyeg, letoltve, geo, pontok) -> Path | None` — fejléc: `kulcsszo; csoport; idopont_utc; nyers_ertek; normalizalt_ertek; koteg_id; referenciaszo; letoltve_utc; geo`.

- [ ] **Step 1: Failing teszt — kötegelés, skálázás, parse**

Create `tests/test_kulcsszavak.py`:
```python
from datetime import datetime, timezone

import pandas as pd

from trendfigyelo import kulcsszavak
from trendfigyelo.config import Config


def _config():
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        referenciaszo="időjárás", alap_keses_mp=3.0, szoras_mp=(3, 7),
        max_probak=4, backoff_mp=[30, 120, 480], trend_idosor_max=15, proxy=None,
        kulcsszavak={"megelhetes": ["a", "b", "c", "d", "e"], "gazdaság": ["f"]},
    )


def test_kotegek_4es_bontas_referenciaszoval():
    kot = kulcsszavak.kotegek(_config())
    # 6 kulcsszó → 2 köteg (4 + 2)
    assert len(kot) == 2
    assert len(kot[0]["tagok"]) == 4
    assert kot[0]["referenciaszo"] == "időjárás"
    assert kulcsszavak.koteg_lekerdezes_szavai(kot[0])[-1] == "időjárás"
    assert len(kulcsszavak.koteg_lekerdezes_szavai(kot[0])) == 5


def test_skalazo_atlagra_szamol():
    assert kulcsszavak.skalazo([50, 50]) == 2.0   # 100 / 50
    assert kulcsszavak.skalazo([0, 0]) is None


def test_parse_koteg_nyers_es_normalizalt():
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
    df = pd.DataFrame({"a": [30], "b": [60], "időjárás": [50]}, index=idx)
    koteg = {"id": 0, "tagok": [("a", "megelhetes"), ("b", "megelhetes")],
             "referenciaszo": "időjárás"}
    pontok = kulcsszavak.parse_koteg(df, koteg)
    a_pont = next(p for p in pontok if p["kulcsszo"] == "a")
    assert a_pont["nyers_ertek"] == 30
    # skálázó = 100/50 = 2.0 → normalizált = 30*2 = 60.0
    assert a_pont["normalizalt_ertek"] == 60.0
    assert a_pont["csoport"] == "megelhetes"
    assert a_pont["koteg_id"] == 0


def test_csv_ir_fejlec(tmp_path):
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
    df = pd.DataFrame({"a": [30], "időjárás": [50]}, index=idx)
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    pontok = kulcsszavak.parse_koteg(df, koteg)
    p = kulcsszavak.csv_ir(tmp_path, "2021-01-01_1200", "2021-01-01T12:00:00+00:00", "HU", pontok)
    fejlec = p.read_text(encoding="utf-8-sig").splitlines()[0]
    assert fejlec == ("kulcsszo;csoport;idopont_utc;nyers_ertek;normalizalt_ertek;"
                      "koteg_id;referenciaszo;letoltve_utc;geo")
    assert p.name == "kulcsszo_idosor_HU_2021-01-01_1200.csv"
```

- [ ] **Step 2: Futtatás — bukjon**

Run: `python -m pytest tests/test_kulcsszavak.py -v`
Expected: FAIL — hiányzó `trendfigyelo.kulcsszavak`.

- [ ] **Step 3: `kulcsszavak.py`**

Create `trendfigyelo/kulcsszavak.py`:
```python
"""Kulcsszó-idősorok ág: 4+1 kötegelt interest_over_time, nyers + normalizált érték."""

from pathlib import Path

from . import seged
from .kliens import AgFeladva

KOTEG_MERET = 4  # 4 kulcsszó + 1 referenciaszó = 5 (a Trends max 5-öt hasonlít össze)


def kotegek(config) -> list:
    """A kulcsszavakat 4-es kötegekre bontja, mindegyikbe a referenciaszóval."""
    parok = config.osszes_kulcsszo()
    kotek = []
    for i in range(0, len(parok), KOTEG_MERET):
        kotek.append({
            "id": i // KOTEG_MERET,
            "tagok": parok[i : i + KOTEG_MERET],
            "referenciaszo": config.referenciaszo,
        })
    return kotek


def koteg_lekerdezes_szavai(koteg) -> list:
    """A köteg 4 kulcsszava + a referenciaszó (utolsóként)."""
    return [kulcsszo for kulcsszo, _ in koteg["tagok"]] + [koteg["referenciaszo"]]


def skalazo(ref_ertekek):
    """100 / referenciaszó-átlag, ha az átlag > 0, különben None."""
    ervenyes = [float(x) for x in ref_ertekek if _szam(x)]
    if not ervenyes:
        return None
    atlag = sum(ervenyes) / len(ervenyes)
    return 100.0 / atlag if atlag > 0 else None


def _szam(x) -> bool:
    try:
        f = float(x)
    except (ValueError, TypeError):
        return False
    return f == f  # NaN esetén False (NaN != NaN) — különben int(NaN) elhasalna


def parse_koteg(df, koteg) -> list:
    """Köteg DataFrame → pontok nyers és normalizált értékkel (NaN-biztos)."""
    pontok = []
    if df is None or len(df) == 0:
        return pontok
    ref = koteg["referenciaszo"]
    sk = skalazo(list(df[ref])) if ref in df.columns else None
    for kulcsszo, csoport in koteg["tagok"]:
        if kulcsszo not in df.columns:
            continue
        for idx, sor in df.iterrows():
            nyers = sor[kulcsszo]
            if _szam(nyers):
                nyers_ert = int(nyers)
                norm = round(float(nyers) * sk, 2) if sk is not None else ""
            else:  # NaN / nem-szám → üres, nem dobunk kivételt
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
            })
    return pontok


def gyujt(kliens, config) -> list:
    """Minden köteget lekér és parse-ol.

    AgFeladva (429-kimerülés) esetén az EGÉSZ ágat feladjuk (a kivétel
    továbbmegy a futtato-hoz block-detektálásra) — nem hammereljük tovább a
    Google-t kötegenként. Egyéb hiba csak az adott köteget hagyja ki.
    """
    pontok = []
    for koteg in kotegek(config):
        szavak = koteg_lekerdezes_szavai(koteg)
        try:
            df = kliens.hivas(
                "kulcsszo", kliens.tr.interest_over_time,
                szavak, geo=config.geo, timeframe=config.idosor_idokeret,
            )
        except AgFeladva:  # 429-kimerülés → az egész ág feladva
            print(f"FIGYELEM: a kulcsszó-ág feladva (429) a(z) {koteg['id']}. kötegnél.")
            raise
        except Exception as e:  # egyetlen köteg egyéb hibája nem dönti a többit
            print(f"FIGYELEM: a(z) {koteg['id']}. köteg kimaradt ({e}).")
            continue
        pontok.extend(parse_koteg(df, koteg))
    return pontok


def csv_ir(mappa, idobelyeg, letoltve, geo, pontok):
    if not pontok:
        return None
    fajl = Path(mappa) / f"kulcsszo_idosor_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow([
            "kulcsszo", "csoport", "idopont_utc", "nyers_ertek", "normalizalt_ertek",
            "koteg_id", "referenciaszo", "letoltve_utc", "geo",
        ])
        for p in pontok:
            iro.writerow([
                p["kulcsszo"], p["csoport"], p["idopont_utc"], p["nyers_ertek"],
                p["normalizalt_ertek"], p["koteg_id"], p["referenciaszo"], letoltve, geo,
            ])
    return fajl
```

- [ ] **Step 4: Futtatás — menjen át**

Run: `python -m pytest tests/test_kulcsszavak.py -v`
Expected: PASS (mind a 4 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/kulcsszavak.py tests/test_kulcsszavak.py
git commit -m "feat(kulcsszavak): 4+1 kötegelt idősorok, nyers+normalizált érték (Phase 1 Task 6)"
```

---

### Task 7: Futásnapló (`naplo.py`)

Ágsoronkénti napló `adatok/naplo.csv`-be (időpont, ág, eredmény, hívásszám, hibakódok). Új futás hozzáfűz; a fejléc csak új fájlnál kerül ki.

**Files:**
- Create: `trendfigyelo/naplo.py`
- Create: `tests/test_naplo.py`

**Interfaces:**
- Consumes: `seged`.
- Produces:
  - `naplo_ir(mappa, futas_ido_utc: str, bejegyzesek: list[dict]) -> Path` — minden bejegyzés kulcsai: `ag, eredmeny, hivasok_szama, hibakodok`. Fejléc: `futas_ido_utc; ag; eredmeny; hivasok_szama; hibakodok`. Létező fájlhoz hozzáfűz, fejléc nélkül.

- [ ] **Step 1: Failing teszt — új fájl fejléccel, hozzáfűzés fejléc nélkül**

Create `tests/test_naplo.py`:
```python
from trendfigyelo import naplo


def test_uj_fajl_fejleccel(tmp_path):
    p = naplo.naplo_ir(tmp_path, "2021-01-01T12:00:00+00:00", [
        {"ag": "felkapott_api", "eredmeny": "siker", "hivasok_szama": 1, "hibakodok": ""},
    ])
    sorok = p.read_text(encoding="utf-8-sig").splitlines()
    assert sorok[0] == "futas_ido_utc;ag;eredmeny;hivasok_szama;hibakodok"
    assert sorok[1] == "2021-01-01T12:00:00+00:00;felkapott_api;siker;1;"
    assert p.name == "naplo.csv"


def test_masodik_futas_hozzafuz_fejlec_nelkul(tmp_path):
    naplo.naplo_ir(tmp_path, "2021-01-01T12:00:00+00:00",
                   [{"ag": "a", "eredmeny": "siker", "hivasok_szama": 1, "hibakodok": ""}])
    p = naplo.naplo_ir(tmp_path, "2021-01-02T12:00:00+00:00",
                       [{"ag": "b", "eredmeny": "hiba", "hivasok_szama": 4, "hibakodok": "429,429"}])
    sorok = p.read_text(encoding="utf-8-sig").splitlines()
    assert len(sorok) == 3  # 1 fejléc + 2 adatsor
    assert sorok[2] == "2021-01-02T12:00:00+00:00;b;hiba;4;429,429"
```

- [ ] **Step 2: Futtatás — bukjon**

Run: `python -m pytest tests/test_naplo.py -v`
Expected: FAIL — hiányzó `trendfigyelo.naplo`.

- [ ] **Step 3: `naplo.py`**

Create `trendfigyelo/naplo.py`:
```python
"""Futásnapló: adatok/naplo.csv — időpont, ág, eredmény, hívásszám, hibakódok."""

import csv
from pathlib import Path

FEJLEC = ["futas_ido_utc", "ag", "eredmeny", "hivasok_szama", "hibakodok"]


def naplo_ir(mappa, futas_ido_utc: str, bejegyzesek) -> Path:
    """Ágsoronkénti napló hozzáfűzése; fejléc csak új fájlnál."""
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
    return fajl
```

- [ ] **Step 4: Futtatás — menjen át**

Run: `python -m pytest tests/test_naplo.py -v`
Expected: PASS (mind a 2 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/naplo.py tests/test_naplo.py
git commit -m "feat(naplo): ágsoronkénti futásnapló naplo.csv-be (Phase 1 Task 7)"
```

---

### Task 8: JSON-export a webnek (`json_export.py`)

A web kizárólag ezekből dolgozik: `legfrissebb.json` (aktuális futás), `tortenet.json` (napi kulcsszó-átlag+csúcs), `napok/<dátum>.json` + `napok/index.json` (napi trendlista-történet, visszalapozáshoz).

**Files:**
- Create: `trendfigyelo/json_export.py`
- Create: `tests/test_json_export.py`

**Interfaces:**
- Consumes: `seged`.
- Produces:
  - `kulcsszo_napi_osszesites(kulcsszo_pontok: list[dict]) -> list[dict]` — kulcsszavanként: `{"kulcsszo", "csoport", "atlag", "csucs"}` a normalizált értékből (ha van, különben nyersből); üres/nem-szám kihagyva.
  - `legfrissebb_ir(docs_data, top_trendek: list[dict], trend_idosorok: list[dict], kulcsszo_pontok: list[dict], frissitve_iso: str, geo: str) -> Path` — `docs/data/legfrissebb.json`.
  - `tortenet_frissit(docs_data, nap_iso: str, kulcsszo_pontok: list[dict]) -> Path` — `docs/data/tortenet.json`; a `nap_iso` napi bejegyzését beírja/felülírja (kulcsszavanként átlag+csúcs).
  - `napi_ir(docs_data, nap_iso: str, top_trendek: list[dict]) -> Path` — `docs/data/napok/<nap_iso>.json`; és frissíti a `napok/index.json` dátumlistáját (rendezett, egyedi).

  `top_trendek` elem-alak: `{"kifejezes", "volumen", "novekedes_pct", "idosor": [{"idopont_utc","ertek"}], "hirek": [...]}` (a `futtato` állítja elő).

- [ ] **Step 1: Failing teszt — összesítés, tortenet upsert, napi + index**

Create `tests/test_json_export.py`:
```python
import json

from trendfigyelo import json_export


def _kpontok():
    return [
        {"kulcsszo": "infláció", "csoport": "megelhetes", "normalizalt_ertek": 40.0},
        {"kulcsszo": "infláció", "csoport": "megelhetes", "normalizalt_ertek": 80.0},
        {"kulcsszo": "MNB", "csoport": "gazdaság", "normalizalt_ertek": ""},
    ]


def test_kulcsszo_napi_osszesites_atlag_es_csucs():
    o = json_export.kulcsszo_napi_osszesites(_kpontok())
    inflacio = next(x for x in o if x["kulcsszo"] == "infláció")
    assert inflacio["atlag"] == 60.0
    assert inflacio["csucs"] == 80.0
    # MNB-nek nincs érvényes normalizált értéke → kihagyva
    assert all(x["kulcsszo"] != "MNB" for x in o)


def test_legfrissebb_ir_geo_es_frissites(tmp_path):
    p = json_export.legfrissebb_ir(tmp_path, [], [], _kpontok(), "2021-01-01T12:00:00+00:00", "HU")
    adat = json.loads(p.read_text(encoding="utf-8"))
    assert adat["geo"] == "HU"
    assert adat["frissitve"] == "2021-01-01T12:00:00+00:00"
    assert p.name == "legfrissebb.json"


def test_tortenet_frissit_ugyanazt_a_napot_felulirja(tmp_path):
    json_export.tortenet_frissit(tmp_path, "2021-01-01", _kpontok())
    p = json_export.tortenet_frissit(tmp_path, "2021-01-01", _kpontok())  # ugyanaz a nap újra
    adat = json.loads(p.read_text(encoding="utf-8"))
    napok = [b["nap"] for b in adat["napok"]]
    assert napok == ["2021-01-01"]  # nem duplikálódik


def test_napi_ir_es_index(tmp_path):
    json_export.napi_ir(tmp_path, "2021-01-02", [{"kifejezes": "infláció", "volumen": "50000"}])
    json_export.napi_ir(tmp_path, "2021-01-01", [{"kifejezes": "benzinár", "volumen": "20000"}])
    napi = json.loads((tmp_path / "napok" / "2021-01-02.json").read_text(encoding="utf-8"))
    assert napi["trendek"][0]["kifejezes"] == "infláció"
    index = json.loads((tmp_path / "napok" / "index.json").read_text(encoding="utf-8"))
    assert index["napok"] == ["2021-01-01", "2021-01-02"]  # rendezett, egyedi
```

- [ ] **Step 2: Futtatás — bukjon**

Run: `python -m pytest tests/test_json_export.py -v`
Expected: FAIL — hiányzó `trendfigyelo.json_export`.

- [ ] **Step 3: `json_export.py`**

Create `trendfigyelo/json_export.py`:
```python
"""JSON-export a statikus webnek: legfrissebb, tortenet, napi trendlista-történet."""

import json
from pathlib import Path


def _szam_e(x):
    try:
        float(x)
        return x != ""
    except (ValueError, TypeError):
        return False


def _ertek(pont):
    """A normalizált érték, ha érvényes; különben a nyers; különben None."""
    for kulcs in ("normalizalt_ertek", "nyers_ertek"):
        if kulcs in pont and _szam_e(pont[kulcs]):
            return float(pont[kulcs])
    return None


def kulcsszo_napi_osszesites(kulcsszo_pontok) -> list:
    """Kulcsszavanként átlag + csúcs; érvényes érték nélküli kulcsszó kihagyva."""
    csoportok = {}
    for p in kulcsszo_pontok:
        ert = _ertek(p)
        if ert is None:
            continue
        rek = csoportok.setdefault(p["kulcsszo"], {"csoport": p.get("csoport", ""), "ertekek": []})
        rek["ertekek"].append(ert)
    eredmeny = []
    for kulcsszo, rek in csoportok.items():
        ek = rek["ertekek"]
        eredmeny.append({
            "kulcsszo": kulcsszo,
            "csoport": rek["csoport"],
            "atlag": round(sum(ek) / len(ek), 2),
            "csucs": round(max(ek), 2),
        })
    return eredmeny


def _ir_json(fajl: Path, adat):
    fajl.parent.mkdir(parents=True, exist_ok=True)
    fajl.write_text(json.dumps(adat, ensure_ascii=False, indent=2), encoding="utf-8")
    return fajl


def _kulcsszo_idosorok(kulcsszo_pontok) -> dict:
    """Kulcsszavanként [{idopont_utc, nyers_ertek, normalizalt_ertek}] a mai grafikonhoz."""
    ki = {}
    for p in kulcsszo_pontok:
        ki.setdefault(p["kulcsszo"], {"csoport": p.get("csoport", ""), "pontok": []})
        ki[p["kulcsszo"]]["pontok"].append({
            "idopont_utc": p.get("idopont_utc", ""),
            "nyers_ertek": p.get("nyers_ertek", ""),
            "normalizalt_ertek": p.get("normalizalt_ertek", ""),
        })
    return ki


def legfrissebb_ir(docs_data, top_trendek, trend_idosorok, kulcsszo_pontok,
                   frissitve_iso, geo) -> Path:
    adat = {
        "geo": geo,
        "frissitve": frissitve_iso,
        "top_trendek": top_trendek,
        "trend_idosorok": trend_idosorok,
        "kulcsszavak": _kulcsszo_idosorok(kulcsszo_pontok),
        "kulcsszo_osszesites": kulcsszo_napi_osszesites(kulcsszo_pontok),
    }
    return _ir_json(Path(docs_data) / "legfrissebb.json", adat)


def tortenet_frissit(docs_data, nap_iso, kulcsszo_pontok) -> Path:
    fajl = Path(docs_data) / "tortenet.json"
    if fajl.exists():
        adat = json.loads(fajl.read_text(encoding="utf-8"))
    else:
        adat = {"napok": []}
    uj_bejegyzes = {"nap": nap_iso, "kulcsszavak": kulcsszo_napi_osszesites(kulcsszo_pontok)}
    adat["napok"] = [b for b in adat["napok"] if b.get("nap") != nap_iso]
    adat["napok"].append(uj_bejegyzes)
    adat["napok"].sort(key=lambda b: b["nap"])
    return _ir_json(fajl, adat)


def napi_ir(docs_data, nap_iso, top_trendek) -> Path:
    napok_mappa = Path(docs_data) / "napok"
    fajl = napok_mappa / f"{nap_iso}.json"
    _ir_json(fajl, {"nap": nap_iso, "trendek": top_trendek})

    index_fajl = napok_mappa / "index.json"
    if index_fajl.exists():
        index = json.loads(index_fajl.read_text(encoding="utf-8"))
    else:
        index = {"napok": []}
    napok = sorted(set(index.get("napok", [])) | {nap_iso})
    _ir_json(index_fajl, {"napok": napok})
    return fajl
```

- [ ] **Step 4: Futtatás — menjen át**

Run: `python -m pytest tests/test_json_export.py -v`
Expected: PASS (mind a 4 teszt).

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/json_export.py tests/test_json_export.py
git commit -m "feat(json): legfrissebb + tortenet + napi trendlista JSON-export (Phase 1 Task 8)"
```

---

### Task 9: Orchestráció (`futtato.py`) + vékony belépő (`top_keresesek.py`)

Az ágakat sorban futtatja külön try-ágakban (részleges siker), naplóz, kiírja a hívásszámot, összeállítja a JSON-okhoz a top-trend struktúrát, és a kilépési kóddal jelzi a teljes blokkolást. A tesztek mockolt ág-függvényekkel dolgoznak (nincs hálózat).

**Files:**
- Create: `trendfigyelo/futtato.py`
- Modify: `top_keresesek.py` (a régi tartalom lecserélve vékony belépőre)
- Create: `tests/test_futtato.py`

**Interfaces:**
- Consumes: minden korábbi modul.
- Produces:
  - `top_trend_struktura(api_trendek, trend_idosorok, rss_trendek, config) -> list[dict]` — a legnagyobb `trend_idosor_max` API-trend `{"kifejezes","volumen","novekedes_pct","idosor":[...],"hirek":[...]}` alakban; az idősort a `trend_idosorok`-ból, a híreket az RSS-ből kulcsszó szerint párosítva.
  - `futtat(config, kliens, adatok_mappa, docs_data_mappa, most=None) -> int` — lefuttat minden ágat, ír CSV+JSON+napló, visszaad kilépési kódot (0 = van adat; 1 = minden ág elbukott).
  - `main() -> int` — betölti a configot, felépíti a klienst, meghívja `futtat`-ot. A `top_keresesek.py` ezt hívja `sys.exit(main())`-nel.

- [ ] **Step 1: Failing teszt — top-trend párosítás + teljes-bukás kilépési kód**

Create `tests/test_futtato.py`:
```python
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from trendfigyelo import futtato, kliens
from trendfigyelo.config import Config


def _config():
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        referenciaszo="időjárás", alap_keses_mp=3.0, szoras_mp=(3, 7),
        max_probak=4, backoff_mp=[30, 120, 480], trend_idosor_max=2, proxy=None,
        kulcsszavak={"g": ["a"]},
    )


def test_top_trend_struktura_parositja_az_idosort_es_hirt():
    api = [SimpleNamespace(keyword="infláció", volume=50000, volume_growth_pct=120)]
    idosorok = [{"kifejezes": "infláció", "idopont_utc": "2021-01-01T10:00:00+00:00", "ertek": 40}]
    hir = SimpleNamespace(title="Cím", source="Index", url="http://x", time=None,
                          picture="", snippet="")
    rss = [SimpleNamespace(keyword="infláció", news=[hir])]
    struktura = futtato.top_trend_struktura(api, idosorok, rss, _config())
    assert struktura[0]["kifejezes"] == "infláció"
    assert struktura[0]["idosor"] == [{"idopont_utc": "2021-01-01T10:00:00+00:00", "ertek": 40}]
    assert struktura[0]["hirek"][0]["hir_cim"] == "Cím"


class Mindig429Kliens:
    """Minden ág AgFeladva-t dob → teljes blokkolás szimulálása."""
    def __init__(self):
        self.tr = object()
    def hivas(self, ag, fn, *a, **k):
        raise kliens.AgFeladva(ag, ["429", "429", "429", "429"])
    def hivasszam(self, ag):
        return 4
    def osszes_hivas(self):
        return 8


def test_teljes_blokkolas_nem_nulla_kilepesi_kod(tmp_path):
    most = datetime(2021, 1, 1, 12, 0, tzinfo=timezone.utc)
    kod = futtato.futtat(_config(), Mindig429Kliens(),
                         tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    assert kod == 1
    # a napló akkor is elkészül
    assert (tmp_path / "adatok" / "naplo.csv").exists()
```

- [ ] **Step 2: Futtatás — bukjon**

Run: `python -m pytest tests/test_futtato.py -v`
Expected: FAIL — hiányzó `trendfigyelo.futtato`.

- [ ] **Step 3: `futtato.py`**

Create `trendfigyelo/futtato.py`:
```python
"""Orchestráció: ágakat sorban futtat (részleges siker), naplóz, JSON-t ír, kilépési kódot ad."""

import sys
from pathlib import Path

from . import config as config_modul
from . import felkapott, idosorok, json_export, kulcsszavak, naplo, seged
from .kliens import Kliens


def _ag(bejegyzesek, kliens, ag: str, fn):
    """Egy ág lefuttatása külön try-ágban; naplóbejegyzés; kivétel elnyelve."""
    try:
        eredmeny = fn()
        bejegyzesek.append({"ag": ag, "eredmeny": "siker",
                            "hivasok_szama": kliens.hivasszam(ag), "hibakodok": ""})
        return eredmeny
    except Exception as e:
        hibakodok = ",".join(getattr(e, "hibakodok", []) or [type(e).__name__])
        bejegyzesek.append({"ag": ag, "eredmeny": "hiba",
                            "hivasok_szama": kliens.hivasszam(ag), "hibakodok": hibakodok})
        print(f"FIGYELEM: a(z) '{ag}' ág elbukott ({e}).")
        return None


def top_trend_struktura(api_trendek, trend_idosorok, rss_trendek, config) -> list:
    """A legnagyobb N API-trend a JSON-hoz: idősorral és hírekkel párosítva."""
    idosor_map = {}
    for p in trend_idosorok:
        idosor_map.setdefault(p["kifejezes"], []).append(
            {"idopont_utc": p["idopont_utc"], "ertek": p["ertek"]})
    hir_map = {}
    for t in rss_trendek or []:
        hir_map[t.keyword] = felkapott.hir_sorok([t])

    rendezett = sorted(api_trendek, key=felkapott.volumen_szam, reverse=True)
    struktura = []
    for t in rendezett[: config.trend_idosor_max]:
        struktura.append({
            "kifejezes": t.keyword,
            "volumen": seged.szovegge(getattr(t, "volume", None)),
            "novekedes_pct": seged.szovegge(getattr(t, "volume_growth_pct", None)),
            "idosor": idosor_map.get(t.keyword, []),
            "hirek": hir_map.get(t.keyword, []),
        })
    return struktura


def futtat(config, kliens, adatok_mappa, docs_data_mappa, most=None) -> int:
    most = most or seged.most_utc()
    adatok_mappa = Path(adatok_mappa)
    docs_data_mappa = Path(docs_data_mappa)
    adatok_mappa.mkdir(parents=True, exist_ok=True)
    idobelyeg = seged.bp_idobelyeg(most)
    letoltve = most.isoformat(timespec="seconds")
    nap_iso = f"{most.astimezone(seged.BUDAPEST):%Y-%m-%d}"
    bejegyzesek = []

    # --- ágak (részleges siker: mindegyik külön try-ágban) ---
    api_trendek = _ag(bejegyzesek, kliens, "felkapott_api",
                      lambda: felkapott.gyujt_api(kliens, config)) or []
    rss_trendek = _ag(bejegyzesek, kliens, "felkapott_rss",
                      lambda: felkapott.gyujt_rss(kliens, config)) or []

    top_kifejezesek = [t.keyword for t in
                       sorted(api_trendek, key=felkapott.volumen_szam, reverse=True)]
    trend_idosorok = _ag(bejegyzesek, kliens, "idosor",
                         lambda: idosorok.gyujt(kliens, config, top_kifejezesek)) or []
    kulcsszo_pontok = _ag(bejegyzesek, kliens, "kulcsszo",
                          lambda: kulcsszavak.gyujt(kliens, config)) or []

    # --- CSV-k ---
    felkapott.csv_ir_api(adatok_mappa, idobelyeg, letoltve, config.geo, api_trendek)
    felkapott.csv_ir_rss(adatok_mappa, idobelyeg, letoltve, config.geo, rss_trendek)
    felkapott.csv_ir_hirek(adatok_mappa, idobelyeg, config.geo, rss_trendek)
    idosorok.csv_ir(adatok_mappa, idobelyeg, letoltve, config.geo, trend_idosorok)
    kulcsszavak.csv_ir(adatok_mappa, idobelyeg, letoltve, config.geo, kulcsszo_pontok)

    # --- JSON a webnek ---
    top_struktura = top_trend_struktura(api_trendek, trend_idosorok, rss_trendek, config)
    json_export.legfrissebb_ir(docs_data_mappa, top_struktura, trend_idosorok,
                               kulcsszo_pontok, letoltve, config.geo)
    if kulcsszo_pontok:
        json_export.tortenet_frissit(docs_data_mappa, nap_iso, kulcsszo_pontok)
    if top_struktura:
        json_export.napi_ir(docs_data_mappa, nap_iso, top_struktura)

    # --- napló + összegzés ---
    naplo.naplo_ir(adatok_mappa, letoltve, bejegyzesek)
    van_adat = any([api_trendek, rss_trendek, trend_idosorok, kulcsszo_pontok])
    print(f"Összes Google-hívás: {kliens.osszes_hivas()}. Van adat: {van_adat}.")
    return 0 if van_adat else 1


def main() -> int:
    config = config_modul.betolt()
    kliens = Kliens(config)
    tervezett = (2 + config.trend_idosor_max
                 + -(-len(config.osszes_kulcsszo()) // kulcsszavak.KOTEG_MERET))
    print(f"Tervezett Google-hívások (max): ~{tervezett}")
    return futtat(config, kliens, Path("adatok"), Path("docs") / "data")


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Futtatás — menjen át**

Run: `python -m pytest tests/test_futtato.py -v`
Expected: PASS (mind a 2 teszt).

- [ ] **Step 5: Vékony belépő — `top_keresesek.py`**

Replace `top_keresesek.py` teljes tartalmát:
```python
"""Trendfigyelő — belépő. A gyűjtő logika a `trendfigyelo` csomagban van.

Használat:
    pip install -r requirements.txt
    python top_keresesek.py
"""

import sys

from trendfigyelo.futtato import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Teljes teszt-svít**

Run: `python -m pytest -v`
Expected: PASS (minden task tesztje zöld).

- [ ] **Step 7: Commit**

```bash
git add trendfigyelo/futtato.py top_keresesek.py tests/test_futtato.py
git commit -m "feat(futtato): orchestráció, részleges siker, kilépési kód + vékony belépő (Phase 1 Task 9)"
```

---

### Task 10: README (Phase 1 hatókör) + éles füst-teszt

A README a Phase 1 hatóköréig: mit gyűjt (HU-fókusz), helyi telepítés/futtatás, kulcsszó-hozzáadás, hívásszám, B terv (helyi futtatás blokkolás esetén). A Pages-bekapcsolás és a workflow a Phase 2/3-ban egészül ki. Végén az első éles füst-teszt.

**Files:**
- Create: `README.md`

**Interfaces:** —

- [ ] **Step 1: `README.md`**

Create `README.md`:
```markdown
# Trendfigyelő

Napi rendszerességgel gyűjti a **magyarországi (geo=HU)** Google Trends adatokat az
elmúlt 24 órából, és CSV + JSON formában menti őket. Minden lekérdezés, adat és
kimenet **kizárólag Magyarországra** vonatkozik.

## Mit gyűjt

- **Felkapott keresések** (trending_now API + RSS-tartalék + kapcsolódó magyar hírek).
- **Trend-idősorok:** a legnagyobb trendek 24 órás keresleti görbéje (sparkline).
- **Saját kulcsszavak:** a `config.yaml`-ban megadott, csoportokba rendezett magyar
  kulcsszavak napi 24 órás idősora, nyers és referenciaszóra normalizált értékkel.

Kimenetek: CSV-k az `adatok/` mappában (`;` elválasztó, `utf-8-sig` — a magyar Excel
dupla kattintásra megnyitja), futásnapló az `adatok/naplo.csv`-ben, és a webes
felülethez JSON-ok a `docs/data/` mappában.

## Telepítés és futtatás (helyi gép)

```bash
pip install -r requirements.txt
python top_keresesek.py
```

Egy futás összes Google-hívása **néhány tucat alatt** marad
(kb. `2 + trend_idosor_max + a kulcsszó-kötegek száma` ≈ 9–23), a hívások közt
véletlenített 3–7 mp késleltetéssel — ez az IP-blokkolás elleni védelem része.

## Kulcsszó hozzáadása

Csak a `config.yaml` `kulcsszavak:` szakaszát kell szerkeszteni — kód nem változik.
Vegyél fel egy szót egy meglévő csoporthoz, vagy hozz létre új csoportot:

```yaml
kulcsszavak:
  megelhetes: [infláció, benzinár, ..., ÚJ_KULCSSZÓ]
  új_csoport: [példa1, példa2]
```

A referenciaszó (`referenciaszo:`), a geo, az időablak és a nyelv szintén itt,
egy helyen állítható.

## B terv — mi van, ha a Google blokkol?

A Google Trends nem hivatalos API-t használ, és az adatközponti IP-ket (amilyenekről
egy felhő-futó dolgozik) szigorúbban szűri. Ha a lekérdezések 429 (rate limit) hibát
kapnak:

1. A szkript magától exponenciálisan visszavár (30 mp → 2 perc → 8 perc), majd az adott
   ágat feladja az napra és naplózza — nem próbálkozik makacsul (az hosszabb blokkot
   válthatna ki).
2. **Futtasd helyi gépről.** Lakossági IP-ről a blokkolás esélye sokkal kisebb. A fenti
   `python top_keresesek.py` parancs módosítás nélkül fut helyben; utána a keletkezett
   `adatok/` és `docs/data/` fájlokat commitolhatod és pusholhatod kézzel.
3. Opcionálisan a `config.yaml` `proxy:` mezőjében megadható egy HTTP(S) proxy.

> A GitHub Actions-ütemezés és a GitHub Pages weboldal a következő fázisokban kerül a
> projektbe; ez a README azokat majd kiegészíti (Settings → Pages → `docs/`).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README Phase 1 hatókörrel (HU-fókusz, futtatás, B terv) (Phase 1 Task 10)"
```

- [ ] **Step 3: Éles füst-teszt (helyi gép, valós Google-hívás)**

> Ez az EGYETLEN élő hívásos lépés. Helyi gépről futtatandó (lakossági IP).

```bash
pip install -r requirements.txt
python top_keresesek.py
```

Ellenőrizd:
- Nincs kivétel; a végén `Van adat: True`.
- `adatok/` tartalmaz: `top_keresesek_api_HU_*.csv`, `..._rss_...`, `..._hirek_...`,
  `top_trend_idosor_HU_*.csv`, `kulcsszo_idosor_HU_*.csv`, `naplo.csv`.
- `docs/data/` tartalmaz: `legfrissebb.json`, `tortenet.json`,
  `napok/<mai-dátum>.json`, `napok/index.json`.
- Minden CSV-ben és JSON-ban a `geo` értéke `HU`.
- A `naplo.csv` ágsoronként mutatja a sikert és a hívásszámot.

Ha itt trendspy-hiba jön a valós API alakja miatt, a parse-függvények (`api_trend_dict`,
`df_idosor`, `parse_koteg`) igazítandók a tényleges attribútum-/oszlopnevekhez — a
tesztek fixtúráit is frissítve. Ha minden zöld, a `requirements.txt` trendspy-verziója
rögzíthető a ténylegesen telepítettre (`pip freeze | grep trendspy`).

- [ ] **Step 4: Az éles adatok commitolása**

```bash
git add adatok/ docs/data/
git commit -m "chore: első éles HU adatgyűjtés (Phase 1 füst-teszt)"
```

---

## Self-Review (a terv ellenőrzése a spec ellen)

**Spec-lefedettség:**
- HU-fókusz mindenhol → Global Constraints + minden ág configból veszi a geót/időablakot/nyelvet ✔
- Anti-block (3–7 mp, 429-backoff, ág-feladás, részleges siker) → Task 3 + Task 9 ✔
- Minimális hívásszám, hívásszám kiírása → Task 9 (`main` tervezett, `futtat` tényleges) ✔
- Meglévő 3 CSV változatlan → Task 4 ✔
- Trend-idősorok CSV → Task 5 ✔
- Kulcsszó-idősorok CSV (nyers+normalizált, 4+1 köteg, referenciaszó configból) → Task 6 ✔
- Futásnapló → Task 7 ✔
- JSON: legfrissebb + tortenet (átlag+csúcs) + napi trendlista-történet + index → Task 8 ✔
- Új kulcsszó csak configból → Task 2 + README (Task 10) ✔
- B terv, hívásszám, HU-fókusz a README-ben → Task 10 ✔
- Nincs élő teszt a unitokban, egy éles füst-teszt → mindenhol mock + Task 10 Step 3 ✔
- **Phase 2 (GitHub Actions) és Phase 3 (web) NEM ebben a tervben** — külön tervek, a jóváhagyott fázisolás szerint.

**Placeholder-ellenőrzés:** nincs TBD/„később" — minden lépés tartalmazza a tényleges kódot. ✔

**Típus-/névkonzisztencia:** `Config` mezőnevek egységesek (Task 2 ↔ minden teszt-fixtúra); `kliens.hivas(ag, fn, ...)` aláírás egységes (Task 3 ↔ 4/5/6/9); `AgFeladva.hibakodok` (Task 3 ↔ 9 `_ag`); CSV-fejlécek a spec 6. szakaszával egyeznek; JSON-kulcsok (Task 8 ↔ 9 `top_trend_struktura`) egyeznek. ✔

**Megjegyzés a hívásszámról:** a trend-idősor ág egyenkénti hívása miatt egy futás ~9–23 hívás (a `trend_idosor_max`-tól függően) — a spec „néhány tucat" korlátja alatt. A showcase-timeline egyhívásos optimalizáció a Phase 1-ben szándékosan kimarad (bizonytalan trendspy-API, nem tesztelhető hálózat nélkül); későbbi fázisban hozzáadható a meglévő `idosorok.gyujt` mögé, a CSV-séma változása nélkül.
