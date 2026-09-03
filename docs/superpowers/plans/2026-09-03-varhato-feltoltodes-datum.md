# Kulcsszó-chart „várható feltöltődés" dátum — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Minden kulcsszó-chart üres ablakához kiírni a *várható* dátumot: a még be nem gyűlt (`nincs_masodlagos`) szavaknál a becsült gyűjtési napot, a sosem-teljesülő (`rovid_masodlagos`) ablaknál pedig őszinte, dátum nélküli szöveget.

**Architecture:** Új tiszta backend modul (`varhato_gyujtes.py`) zárt képlettel becsli a reggeli másodlagos-rotáció következő gyűjtési napját minden soha-nem-gyűlt reggeli szóra; a `futtato` az esti regresszió-íráskor per-szó `varhato_gyujtes_datum` mezőt injektál a `kulcsszo_regresszio.json`-ba; a frontend ezt a `nincs_masodlagos` ághoz külön mondattal kiírja, és a `rovid_masodlagos` szöveget őszintére cseréli.

**Tech Stack:** Python 3.12 (stdlib: `datetime`, `zoneinfo` a `seged`-en át), vanilla JS (`docs/js/app.js`), pytest (SOROS, `-p no:xdist`), Playwright (`--workers=1`, testDir `e2e/`).

**Spec:** `docs/superpowers/specs/2026-09-03-varhato-feltoltodes-datum-design.md`

## Global Constraints

- **SOROS suite kötelező:** `.venv/bin/python -m pytest -p no:xdist -q` és `npx playwright test --workers=1`. MUTÁCIÓ=1 (egy koncepcionális változás/commit).
- **TDD valódi RED→GREEN:** minden implementáció előtt először bukó teszt, futtatva, a bukás igazolva.
- **`git add` KIZÁRÓLAG néven** (soha `-A`/`.`); a gyökér `ATADAS-2026-08-18.txt` SOHA nem staged.
- **Commit-trailerek** minden commitban:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN`
- **Push nincs** — külön, kapuzott kör, csak explicit user-engedéllyel.
- **Pótolhatatlan adat READ-ONLY:** `docs/data/kulcsszo_nyers.json`, `kulcsszo_lanc.json`, `kulcsszo_masodlagos_nyers.json` — a feature csak OLVASSA őket; teszt-adat kizárólag `tmp_path`-ban.
- **Nincs `Date.now()` / argless `datetime.now()` / argless `new Date()`** — az idő mindig paraméterként (`most`) érkezik; JS-ben csak `new Date(Date.UTC(...))`.
- **Idő-egység:** a becsült dátum `YYYY-MM-DD` (Budapest-helyi naptári nap), a frontend `YYYY.MM.DD` alakban jeleníti meg.
- **Független `hirfigyelo` projekt** a közös szerveren — NE nyúlj hozzá.

---

### Task 1: Backend modul — `varhato_gyujtes.py` (becsült gyűjtési dátum)

Tiszta, determinisztikus függvény, amely a reggeli másodlagos-rotáció zárt képletéből (`floor(rang/cap)`) minden **soha-nem-gyűlt** reggeli nem-órás szóra megadja a várható gyűjtési napot.

**Files:**
- Create: `trendfigyelo/varhato_gyujtes.py`
- Test: `tests/test_varhato_gyujtes.py`

**Interfaces:**
- Consumes: `config.osszes_kulcsszo()` → `[KulcsszoTetel(kifejezes, domen, tipus, racs, oras, futas), ...]`; `nyers_kimenet._aware_dt(x)`; `seged.BUDAPEST` (ZoneInfo).
- Produces:
  `varhato_gyujtes_datumok(config, masodlagos_nyers, most, cap=MAX_MASODLAGOS_REGGELI) -> dict[str, str]`
  ahol `masodlagos_nyers` a `kulcsszo_masodlagos_nyers.json` `"kulcsszavak"` blokkja (`{szó: [rekord,...]}`), `most` aware UTC `datetime`, a visszaadott érték `{szó: "YYYY-MM-DD"}` CSAK a soha-nem-gyűlt reggeli nem-órás szavakra. Modul-konstans: `MAX_MASODLAGOS_REGGELI = 8`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_varhato_gyujtes.py
from datetime import datetime, timezone

from trendfigyelo import varhato_gyujtes
from trendfigyelo.config import Config, KulcsszoTetel


def _config(kulcsszavak):
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        alap_keses_mp=3.0, szoras_mp=(3, 7), max_probak=4, backoff_mp=[30, 120, 480],
        trend_idosor_max=2, proxy=None, kulcsszavak=kulcsszavak,
    )


# egy esti (21:00 Budapest = 19:00 UTC) becslés → a következő reggeli nap MÁSNAP
MOST = datetime(2026, 9, 3, 19, 0, tzinfo=timezone.utc)


def _reggeli(kif, racs="het"):
    # nem-órás reggeli szó: racs != "ora", futas == "reggel"
    return KulcsszoTetel(kif, "gazdasag", "szintmero", racs, False, "reggel")


def _rekord(lekerdezes_utc):
    return {"timeframe": "today 12-m", "lekerdezes_utc": lekerdezes_utc,
            "ablak_kezdet_utc": "2026-08-01T00:00:00+00:00",
            "ablak_veg_utc": "2026-09-01T00:00:00+00:00", "pontok": []}


def test_soha_nem_gyult_reggeli_szo_masnapi_datumot_kap():
    cfg = _config([_reggeli("infláció")])
    ki = varhato_gyujtes.varhato_gyujtes_datumok(cfg, {}, MOST)
    assert ki == {"infláció": "2026-09-04"}   # 2026-09-03 (Budapest) + 1 nap


def test_rang_8_folott_egy_nappal_kesobb(cap=8):
    # 9 soha-nem-gyűlt reggeli szó config-sorrendben: az első 8 másnap, a 9. egy nappal később
    szavak = [_reggeli("szo%02d" % i) for i in range(9)]
    ki = varhato_gyujtes.varhato_gyujtes_datumok(_config(szavak), {}, MOST, cap=8)
    assert ki["szo00"] == "2026-09-04"
    assert ki["szo07"] == "2026-09-04"
    assert ki["szo08"] == "2026-09-05"   # floor(8/8)=1 → +1 nap


def test_mar_begyult_szo_nem_kap_datumot():
    cfg = _config([_reggeli("infláció")])
    mn = {"infláció": [_rekord("2026-09-03T07:00:00+00:00")]}   # van érvényes lekerdezes_utc
    assert varhato_gyujtes.varhato_gyujtes_datumok(cfg, mn, MOST) == {}


def test_ervenytelen_lekerdezes_utc_soha_nem_gyultnek_szamit():
    cfg = _config([_reggeli("infláció")])
    mn = {"infláció": [_rekord(None)]}   # rekord van, de nincs érvényes időbélyeg → inf elavultság
    assert varhato_gyujtes.varhato_gyujtes_datumok(cfg, mn, MOST) == {"infláció": "2026-09-04"}


def test_esti_es_oras_szavak_kizarva():
    esti = KulcsszoTetel("állás", "munka", "szintmero", "nap", False, "este")
    oras = KulcsszoTetel("benzin", "fogyasztas", "szintmero", "ora", True, "reggel")
    cfg = _config([esti, oras])
    assert varhato_gyujtes.varhato_gyujtes_datumok(cfg, {}, MOST) == {}


def test_ures_vagy_hianyzo_bemenet_ures_map():
    cfg = _config([_reggeli("infláció")])
    # None kulcsszavak-blokk (olvashatatlan/üres fájl esetén a hívó ezt adja)
    assert varhato_gyujtes.varhato_gyujtes_datumok(cfg, {}, MOST) == {"infláció": "2026-09-04"}
    assert varhato_gyujtes.varhato_gyujtes_datumok(_config([]), {}, MOST) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -p no:xdist tests/test_varhato_gyujtes.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'trendfigyelo.varhato_gyujtes'`.

- [ ] **Step 3: Write the module**

```python
# trendfigyelo/varhato_gyujtes.py
"""Reggeli másodlagos gyűjtés VÁRHATÓ dátuma a még-be-nem-gyűlt szavakhoz.

A rotáció determinisztikus (lásd futtato.masodlagos_szavak_ma): a soha-nem-gyűlt
cellák `inf` elavultsággal a sor elejére kerülnek, config-sorrendben; futásonként
MAX_MASODLAGOS_REGGELI cella gyűl be, napi 1 reggeli futással. Ezért egy `r` rangú
(0-alapú, a soha-nem-gyűlt reggeli szavak config-sorrendjében) váró szó a
floor(r / cap) + 1 -edik jövőbeli reggeli futáson gyűl be → a következő reggeli
naptól számítva floor(r / cap) nappal később.

Tiszta függvény: nincs I/O és nincs órajel-olvasás — a `most`-ot a hívó adja.
"""
from datetime import timedelta

from . import nyers_kimenet, seged

MAX_MASODLAGOS_REGGELI = 8   # tükrözi futtato.MAX_MASODLAGOS_REGGELI (a hívó a sajátját adja át)


def varhato_gyujtes_datumok(config, masodlagos_nyers, most, cap=MAX_MASODLAGOS_REGGELI):
    """szó -> 'YYYY-MM-DD' (Budapest) a soha-nem-gyűlt reggeli nem-órás szavakhoz."""
    masodlagos_nyers = masodlagos_nyers or {}
    reggeli = [t for t in config.osszes_kulcsszo()
               if t.racs != "ora" and t.futas == "reggel"]
    varok = [t for t in reggeli if not _van_rekord(masodlagos_nyers, t.kifejezes)]
    kov_reggeli = most.astimezone(seged.BUDAPEST).date() + timedelta(days=1)
    return {t.kifejezes: (kov_reggeli + timedelta(days=r // cap)).isoformat()
            for r, t in enumerate(varok)}


def _van_rekord(masodlagos_nyers, kifejezes):
    """Igaz, ha a szónak van érvényes lekerdezes_utc-jű másodlagos rekordja
    (különben soha-nem-gyűlt = inf elavultság a rotációban)."""
    rekordok = masodlagos_nyers.get(kifejezes) or []
    return any(nyers_kimenet._aware_dt(r.get("lekerdezes_utc")) is not None
               for r in rekordok)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -p no:xdist tests/test_varhato_gyujtes.py -q`
Expected: PASS (6 passing), kimenet pristine (nincs warning).

- [ ] **Step 5: Full suite + commit**

```bash
.venv/bin/python -m pytest -p no:xdist -q
git add trendfigyelo/varhato_gyujtes.py tests/test_varhato_gyujtes.py
git commit -m "feat(varhato): reggeli másodlagos gyűjtés becsült dátuma (zárt képlet)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN"
```

---

### Task 2: `futtato` integráció — a mező injektálása az esti regresszióba

Az esti (`csak_felkapott == False`) regresszió-írás elé egy helper beolvassa a másodlagos nyers fájlt, meghívja a Task 1 függvényét, és a per-szó `varhato_gyujtes_datum` mezőt beírja a regresszió-struktúrába. A `regresszio.py` tiszta marad; a scheduler-matek a futtatóban él.

**Files:**
- Modify: `trendfigyelo/futtato.py` (import a 15. sor környékén; új helper; hívás a 481-484 blokkban)
- Test: `tests/test_futtato.py` (új teszt a helperre)

**Interfaces:**
- Consumes: `varhato_gyujtes.varhato_gyujtes_datumok(...)` (Task 1); `MAX_MASODLAGOS_REGGELI` (futtato meglévő konstans, 43. sor).
- Produces: `_injektal_varhato_gyujtes(reg, config, docs_data_mappa, most) -> None` — helyben mutálja `reg["kulcsszavak"][szó]["varhato_gyujtes_datum"]`-ot minden olyan szóra, amely a Task 1 map-jében szerepel ÉS jelen van a `reg`-ben. Olvashatatlan másodlagos fájl → nincs mutáció (kivétel nélkül).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_futtato.py — a meglévő importokhoz add hozzá, ha hiányzik:
#   import json
#   from datetime import datetime, timezone
#   from trendfigyelo.config import KulcsszoTetel

def test_injektal_varhato_gyujtes_csak_soha_nem_gyultre(tmp_path):
    ddir = tmp_path / "docs" / "data"
    ddir.mkdir(parents=True)
    # két reggeli nem-órás szó; egyik már begyűlt (van rekordja), a másik nem
    (ddir / "kulcsszo_masodlagos_nyers.json").write_text(json.dumps({"kulcsszavak": {
        "rezsi": [{"timeframe": "today 12-m", "lekerdezes_utc": "2026-09-03T07:00:00+00:00",
                   "ablak_kezdet_utc": "2026-08-01T00:00:00+00:00",
                   "ablak_veg_utc": "2026-09-01T00:00:00+00:00", "pontok": []}],
    }}), encoding="utf-8")
    cfg = _config([
        KulcsszoTetel("infláció", "gazdasag", "szintmero", "het", False, "reggel"),
        KulcsszoTetel("rezsi", "megelhetes", "szintmero", "het", False, "reggel"),
    ])
    reg = {"kulcsszavak": {"infláció": {"racs": "het"}, "rezsi": {"racs": "het"}}}
    most = datetime(2026, 9, 3, 19, 0, tzinfo=timezone.utc)

    futtato._injektal_varhato_gyujtes(reg, cfg, ddir, most)

    assert reg["kulcsszavak"]["infláció"]["varhato_gyujtes_datum"] == "2026-09-04"
    assert "varhato_gyujtes_datum" not in reg["kulcsszavak"]["rezsi"]   # már begyűlt


def test_injektal_varhato_gyujtes_hianyzo_fajl_nem_dob(tmp_path):
    ddir = tmp_path / "docs" / "data"
    ddir.mkdir(parents=True)   # NINCS kulcsszo_masodlagos_nyers.json
    cfg = _config([KulcsszoTetel("infláció", "gazdasag", "szintmero", "het", False, "reggel")])
    reg = {"kulcsszavak": {"infláció": {"racs": "het"}}}
    most = datetime(2026, 9, 3, 19, 0, tzinfo=timezone.utc)
    futtato._injektal_varhato_gyujtes(reg, cfg, ddir, most)   # nem dob
    assert "varhato_gyujtes_datum" not in reg["kulcsszavak"]["infláció"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -p no:xdist tests/test_futtato.py::test_injektal_varhato_gyujtes_csak_soha_nem_gyultre -v`
Expected: FAIL — `AttributeError: module 'trendfigyelo.futtato' has no attribute '_injektal_varhato_gyujtes'`.

- [ ] **Step 3: Add the import, helper, and wiring in `futtato.py`**

3a. A 15. sor környéki import-sorhoz add hozzá a `varhato_gyujtes` modult (a meglévő `from . import ... nyers_kimenet, regresszio, seged` csoporthoz):

```python
from . import (..., nyers_kimenet, regresszio, seged, varhato_gyujtes)
```

3b. Új helper (tedd a `masodlagos_szavak_ma` közelébe, a modul-szintű helperek közé):

```python
def _injektal_varhato_gyujtes(reg, config, docs_data_mappa, most):
    """A soha-nem-gyűlt reggeli szavakhoz beírja a becsült gyűjtési dátumot a
    regresszió-struktúrába (kulcsszo_regresszio.json). Olvashatatlan másodlagos
    fájl → nincs mutáció (a becslés SOHA nem viheti el a regressziót)."""
    fajl = Path(docs_data_mappa) / "kulcsszo_masodlagos_nyers.json"
    try:
        masodlagos = json.loads(fajl.read_text(encoding="utf-8")).get("kulcsszavak", {})
    except (OSError, ValueError):
        return
    datumok = varhato_gyujtes.varhato_gyujtes_datumok(
        config, masodlagos, most, cap=MAX_MASODLAGOS_REGGELI)
    kulcsszavak = reg.get("kulcsszavak", {})
    for szo, datum in datumok.items():
        if szo in kulcsszavak:
            kulcsszavak[szo]["varhato_gyujtes_datum"] = datum
```

3c. A 481-484 blokkban válaszd külön a számítást és az írást, és tedd közé az injektálást (a `try`-on BELÜL, hogy a védettséget örökölje):

```python
                reg = regresszio.regresszio_szamit(nyers, tortenet, config, letoltve,
                                                   lanc_map=lanc.betolt_lanc(docs_data_mappa))
                _injektal_varhato_gyujtes(reg, config, docs_data_mappa, most)   # `most` a datetime (NEM letoltve, ami string!)
                regresszio.regresszio_ir(docs_data_mappa, reg)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -p no:xdist "tests/test_futtato.py::test_injektal_varhato_gyujtes_csak_soha_nem_gyultre" "tests/test_futtato.py::test_injektal_varhato_gyujtes_hianyzo_fajl_nem_dob" -v`
Expected: PASS (2 passing).

- [ ] **Step 5: Full suite + commit**

```bash
.venv/bin/python -m pytest -p no:xdist -q
git add trendfigyelo/futtato.py tests/test_futtato.py
git commit -m "feat(futtato): esti regresszió injektálja a becsült gyűjtési dátumot

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN"
```

---

### Task 3: Frontend — dátum a `nincs_masodlagos` ághoz + őszinte `rovid_masodlagos` szöveg

A `nincs_masodlagos` üres ablak megkapja a backend `varhato_gyujtes_datum` mezőjét („Várhatóan …-től gyűlik."); a `rovid_masodlagos` szöveg őszinte, dátum nélküli megfogalmazásra vált.

**Files:**
- Modify: `docs/js/app.js` (`OK_MAGYAR` 171. sor; `egyesitett_reg` üres-ág 273-283. sor; `ok_szoveg` 701-705. sor)
- Test: `e2e/kulcsszo.spec.js` (új „2h-c" teszt; a meglévő „2k" teszt szöveg-frissítése; a `regSzo` helper `varhato_gyujtes_datum` átvezetése)

**Interfaces:**
- Consumes: `o.varhato_gyujtes_datum` (Task 2 által a `kulcsszo_regresszio.json` per-szó blokkjába injektált `YYYY-MM-DD`).
- Produces: az üres kártya `.ures` szövege `nincs_masodlagos`-nál „… Várhatóan YYYY.MM.DD-től gyűlik.".

- [ ] **Step 1: Write / update the failing e2e tests**

1a. A `regSzo` helper visszaadott objektumába (kb. 137-145. sor) vezesd át a mezőt — a `racs:` sor mellé:

```javascript
    racs: over.racs,
    varhato_gyujtes_datum: over.varhato_gyujtes_datum,   // Task 2: nincs_masodlagos várható gyűjtési nap
    intervallumok: iv,
```

1b. Új teszt a 2h-b (409. sor) UTÁN:

```javascript
// ── 2h-c. nincs_masodlagos + becsült gyűjtési dátum → „Várhatóan <dátum>-től gyűlik" ──────────
test("2h-c. nem-órás szó másodlagos nélkül → nincs_masodlagos + 'Várhatóan <dátum>-től gyűlik'", async ({ page }) => {
  await mock(page, {
    regObj: reg({
      "infláció": regSzo({ domen: "gazdasag", racs: "het", varhato_gyujtes_datum: "2026-09-04" }),
      "albérlet": regSzo({ domen: "lakhatas" }),                     // hogy az 1_ho gomb ENGEDÉLYEZETT legyen
    }),
    nyersObj: nyers({ "infláció": [nyersRekord("infláció")], "albérlet": [nyersRekord("albérlet")] }),
    mpRegObj: mpReg({ "albérlet": mpSzo("nap", { "1_ho": racs_iv(30, 1) }) }),   // albérlet 1_ho érvényes
    mpNyersObj: mpNyers({ "albérlet": [racs_nyersRekord("albérlet", 30, 1)] }),
    // infláció: NINCS másodlagos → 1_ho nincs_masodlagos
  });
  await page.goto("/");
  await page.click('#intervallum-vezerlo button[data-intervallum="1_ho"]');
  const u = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="infláció"] .ures`);
  await expect(u).toContainText("még gyűlik a napi/heti adat");
  await expect(u).toContainText("Várhatóan 2026.09.04-től gyűlik.");
});
```

1c. A meglévő „2k" teszt (442. sor) assertjeit cseréld az új őszinte szövegre. FONTOS: a `#intervallum-vezerlo` MINDEN intervallum ok-szövegét kirakja (a `.ok` span közvetlenül `OK_MAGYAR`-ból, NEM `ok_szoveg`-ből → sosem dátum), ezért az 1_ho/3_ho `nincs_masodlagos` „Magától feltöltődik."-je beszivárogna egy konténer-szintű assertba. Az 1_ev intervallum-tételre szűkítünk:

```javascript
  await page.goto("/");
  const iv1ev = page.locator(".intervallum-tetel", { has: page.locator('button[data-intervallum="1_ev"]') });
  await expect(iv1ev).toContainText("A napi/heti sorozat ehhez az ablakhoz túl rövid.");   // rovid_masodlagos — ELVI, őszinte
  await expect(iv1ev).not.toContainText("Magától feltöltődik");   // a régi félrevezető IDŐBELI szöveg NEM
  await expect(iv1ev).not.toContainText("összefűzött");           // a félrevezető órás-láncolás felirat NEM
```
(A „Várhatóan …-től gyűlik." pozitív ellenőrzést a kártyán a 2h-c fedi; a vezérlőben nincs dátum.)

- [ ] **Step 2: Run e2e to verify the new/updated tests fail**

Run: `npx playwright test --workers=1 kulcsszo.spec.js -g "2h-c|2k"`
Expected: FAIL — „2h-c" nem találja a „Várhatóan …-től gyűlik." szöveget (a frontend még nem írja ki); „2k" nem találja az új „…túl rövid." szöveget (még a régi „Magától feltöltődik." van).

- [ ] **Step 3: Frontend — a három edit `docs/js/app.js`-ben**

3a. `OK_MAGYAR.rovid_masodlagos` (171. sor) — őszinte, dátum nélküli szöveg:

```javascript
  rovid_masodlagos: "A napi/heti sorozat ehhez az ablakhoz túl rövid.",   // ELVI: a másodlagos nem láncol hosszabb sorozattá
```

3b. `egyesitett_reg` üres-ág — az `oras_lanc_kell` `varhato_datum` injektálás (276-282. sor) UTÁN, ugyanabban a blokkban:

```javascript
        if (ok === "nincs_masodlagos" && o.varhato_gyujtes_datum) {
          ures.varhato_gyujtes_datum = o.varhato_gyujtes_datum;   // backend becslés: mikor gyűl be a szó
        }
```

3c. `ok_szoveg` (701-705. sor) — a `nincs_masodlagos` külön záró-mondatot kap (a meglévő `oras_lanc_kell` mondat változatlan):

```javascript
function ok_szoveg(iv) {
  const alap = OK_MAGYAR[iv.ok] || iv.ok;
  if (iv.varhato_datum) return alap + " Várhatóan " + iv.varhato_datum.replace(/-/g, ".") + "-től lesz elérhető.";
  if (iv.varhato_gyujtes_datum) return alap + " Várhatóan " + iv.varhato_gyujtes_datum.replace(/-/g, ".") + "-től gyűlik.";
  return alap;
}
```

- [ ] **Step 4: Run e2e to verify pass (and no regression on 2h-b / rovid_het_ablak)**

Run: `npx playwright test --workers=1 kulcsszo.spec.js -g "2h-b|2h-c|2k|rovid_het_ablak"`
Expected: PASS — 2h-c kiírja a gyűjtési dátumot; 2k az új őszinte szöveget; a meglévő 2h-b („…-től lesz elérhető.") és a `rovid_het_ablak` tesztek zöldek.

- [ ] **Step 5: Full suites + commit**

```bash
.venv/bin/python -m pytest -p no:xdist -q
npx playwright test --workers=1
git add docs/js/app.js e2e/kulcsszo.spec.js
git commit -m "feat(frontend): nincs_masodlagos becsült gyűjtési dátum + őszinte rovid_masodlagos szöveg

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN"
```

---

## Önellenőrzés (terv ↔ spec)

- **Spec-lefedettség:** ① `nincs_masodlagos` becsült dátum → Task 1 (számítás) + Task 2 (injektálás) + Task 3b/3c (megjelenítés). ② `rovid_masodlagos` nincs dátum + őszinte szöveg → Task 3a + a „2k" teszt frissítése. Az `oras_lanc_kell` változatlanul marad → a 2h-b teszt zöldben tartja. Hibakezelés (olvashatatlan JSON) → Task 2 helper `try/except` + teszt. Pótolhatatlan adat csak olvasva → minden fájl-hozzáférés read-only, teszt-adat `tmp_path`-ban. `regresszio.py` tiszta marad → a matek Task 1-ben és a futtatóban.
- **Placeholder-scan:** nincs TBD/„handle edge cases"; minden lépés konkrét kódot ad.
- **Típus-konzisztencia:** `varhato_gyujtes_datumok(config, masodlagos_nyers, most, cap)` → `dict[str,str]`; a futtato ezt `cap=MAX_MASODLAGOS_REGGELI`-vel hívja; a frontend `o.varhato_gyujtes_datum` (string `YYYY-MM-DD`) → `iv.varhato_gyujtes_datum` → `ok_szoveg`. A mezőnév (`varhato_gyujtes_datum`) mindhárom rétegben azonos. A meglévő `varhato_datum` (oras_lanc_kell) külön mező, külön mondat — nincs ütközés.

## Amit NEM csinálunk (YAGNI)

- Nincs teljes rotáció-szimuláció (a zárt `floor(rang/cap)` képlet elég a backlogra).
- Nincs napi-adat-láncolás (a `rovid_masodlagos` strukturálisan üres marad — csak a szöveg őszintébb).
- Nincs új frontend fájl/fetch (a meglévő `kulcsszo_regresszio.json`-ba injektálunk).
- Nincs becslés a már begyűlt szavak következő frissítésére.
