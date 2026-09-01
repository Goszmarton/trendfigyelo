# Napi összesen idősor-nézet + hamis-esti forrás-javítás — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A kategória-idősorhoz egy harmadik „Napi összesen" nézet (reggel+este darabszám-összege) + állandó info-doboz, és a gyűjtés forrás-javítása, hogy egy hajnali backup-futás ne írjon hamis másnapi esti szegmenst.

**Architecture:** Közös `seged.esti_nap(most)` helper (a 6:00 budapesti óra ELŐTTI futás az előző nap estéjéhez tartozik); ezt használja a `futtat` (este `nap_iso`) és a `futas_orzo` őr is → egyezik a gyűjtés és a skip-döntés. A frontend `kategoria_idosor` egy új `"osszesen"` móddal naponként összeadja a MEGLÉVŐ szegmensek kategória-darabszámait. Egyszeri adat-takarítás a már beírt hamis 09-01 estire.

**Tech Stack:** Python 3.12 (pytest, zoneinfo), vanilla JS (Chart.js, DOM-tükör), Playwright e2e.

**Spec:** `docs/superpowers/specs/2026-09-01-napi-osszesen-esti-nap-fix-design.md`

## Global Constraints

- **git add CSAK név szerint** (soha `-A` / `.`); a gyökér `ATADAS-2026-08-18.txt` SOSEM kerül stagelésre.
- **Commit-trailerek** minden commitra:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN`
- **Push = KÜLÖN, kapuzott kör** (fetch → divergencia-ellenőrzés → rebase ha lemaradt → push → `rev-list 0 0` igazolás), csak explicit user-jóváhagyással. A terv NEM pushol.
- **SOROS suite** (a kész-ellenőrzésekhez): `.venv/bin/python -m pytest -p no:xdist -q` ÉS `npx playwright test --workers=1`. Task közben elég a célzott részhalmaz, de a task-jelentés a TELJES suite eredményét idézze.
- **TDD**: valós RED→GREEN, MUTÁCIÓ=1 (egy logikai változás/commit).
- **Frontend: NINCS `new Date()` / `Date.now()`** (csak `new Date(Date.UTC(...))` ha egyáltalán kell — itt nem kell, a szövegek statikusak).
- **Pótolhatatlan órás adat READ-ONLY**: `docs/data/kulcsszo_nyers.json`, `docs/data/kulcsszo_lanc.json` — NEM nyúlunk hozzá.
- **Adat-változás KÜLÖN commit** a kód-commitoktól (Task 4).
- **Időérzékenység:** a Task 4 (adat-takarítás) + a teljes ág legkésőbb MA 21:00 (budapesti) ELŐTT pusholva legyen, hogy a ma esti valódi futás be tudja írni a valós 09-01 estit. (A ma esti dispatch `workflow_dispatch` → az őr nem aktív → mindenképp gyűjt, de csak ha a hamis este már törölve van.)

---

## Fájlstruktúra

- `trendfigyelo/seged.py` — új `esti_nap()` + `ESTI_NAP_HAJNAL_KUSZOB` konstans (Task 1).
- `trendfigyelo/futtato.py` — `nap_iso` este-módban `esti_nap`-ból (Task 2, `:315`).
- `trendfigyelo/futas_orzo.py` — `main` este-ága `esti_nap`-ot néz (Task 3).
- `docs/data/napok/2026-09-01.json`, `docs/data/kategoriak.json` — egyszeri takarítás (Task 4).
- `docs/js/app.js` — `kategoria_idosor` „osszesen" mód (Task 5), `idosor_szegmens_valto_epit` 3 gomb + alap (Task 6), `idosor_blokk_render` info-doboz + takarítás (Task 7).
- `docs/css/app.css` — `.idosor-info` kék-callout (Task 7).
- `tests/test_seged.py`, `tests/test_futtato.py`, `tests/test_futas_orzo.py`, `e2e/trend.spec.js` — tesztek.
- `docs/superpowers/leltar.md` — invariáns + tétel (Task 8).

---

## Task 1: `seged.esti_nap` — a logikai esti nap helper

**Files:**
- Modify: `trendfigyelo/seged.py` (a `most_utc` köré, `:37` után)
- Test: `tests/test_seged.py`

**Interfaces:**
- Produces: `seged.esti_nap(most: datetime) -> str` (ISO `"YYYY-MM-DD"`); `seged.ESTI_NAP_HAJNAL_KUSZOB = 6` (int, budapesti óra). A `most` tz-aware UTC datetime.

- [ ] **Step 1: Write the failing tests**

`tests/test_seged.py` végére:

```python
# --- ESTI-NAP: a logikai esti nap (hajnali futás = az ELŐZŐ este pótlása) ---

def test_esti_nap_este_aznap():
    # 21:00 CEST (19:00 UTC nyáron) → aznap estéje
    assert seged.esti_nap(datetime(2026, 9, 1, 19, 0, tzinfo=timezone.utc)) == "2026-09-01"


def test_esti_nap_hajnal_az_elozo_nap():
    # 03:38 CEST (01:38 UTC) → hajnal → az ELŐZŐ nap estéje (a hamis-esti forrása)
    assert seged.esti_nap(datetime(2026, 9, 1, 1, 38, tzinfo=timezone.utc)) == "2026-08-31"


def test_esti_nap_hatar_kuszob_alatt_elozo():
    # 05:59 CEST (03:59 UTC) → még hajnal → előző nap
    assert seged.esti_nap(datetime(2026, 9, 1, 3, 59, tzinfo=timezone.utc)) == "2026-08-31"


def test_esti_nap_hatar_kuszobon_aznap():
    # 06:00 CEST (04:00 UTC) → már aznap
    assert seged.esti_nap(datetime(2026, 9, 1, 4, 0, tzinfo=timezone.utc)) == "2026-09-01"


def test_esti_nap_teli_ido_DST_hatar():
    # télen CET (+1): 06:00 CET = 05:00 UTC → aznap; 05:00 CET = 04:00 UTC → előző
    assert seged.esti_nap(datetime(2026, 1, 15, 5, 0, tzinfo=timezone.utc)) == "2026-01-15"
    assert seged.esti_nap(datetime(2026, 1, 15, 4, 0, tzinfo=timezone.utc)) == "2026-01-14"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_seged.py -k esti_nap`
Expected: FAIL — `AttributeError: module 'trendfigyelo.seged' has no attribute 'esti_nap'`

- [ ] **Step 3: Write minimal implementation**

`trendfigyelo/seged.py`, a `most_utc()` függvény után (a `timedelta` már importált a fejlécben):

```python
ESTI_NAP_HAJNAL_KUSZOB = 6   # budapesti óra: e küszöb ALATT a futás az ELŐZŐ nap estéjéhez tartozik


def esti_nap(most: datetime) -> str:
    """Az este-módú futás LOGIKAI esti napja (ISO 'YYYY-MM-DD').

    A budapesti naptári nap, KIVÉVE a hajnali (ESTI_NAP_HAJNAL_KUSZOB budapesti óra
    előtti) futást: az egy éjfél-átfordulós backup, ami az ELŐZŐ nap estéjének pótlása,
    ezért az előző napra sorolódik. Így egy hajnali backup nem hoz létre hamis másnapi
    esti szegmenst; a valóban kimaradt estét viszont bepótolja. DST automatikus
    (budapesti helyi órából számol)."""
    bp = most.astimezone(BUDAPEST)
    if bp.hour < ESTI_NAP_HAJNAL_KUSZOB:
        return (bp.date() - timedelta(days=1)).isoformat()
    return bp.date().isoformat()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_seged.py -k esti_nap`
Expected: PASS (5 teszt)

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/seged.py tests/test_seged.py
git commit   # üzenet: "feat(seged): esti_nap — logikai esti nap (hajnali futás = előző este)"  + trailerek
```

---

## Task 2: `futtat` — este-mód a logikai esti napra ír

**Files:**
- Modify: `trendfigyelo/futtato.py:315` (a `nap_iso` értékadás)
- Test: `tests/test_futtato.py`

**Interfaces:**
- Consumes: `seged.esti_nap` (Task 1). A `futtat(config, kliens, adatok, docs_data, most=..., mode="este"|"reggel")` már létező, `most`-injektálható; `AdatKliens` (a fájlban) felkapott trendet ad → `top_trendek` nem üres → `napi_ir` ír szegmenst.

- [ ] **Step 1: Write the failing tests**

`tests/test_futtato.py` végére (a `json`, `datetime`, `timezone`, `AdatKliens`, `_config` már a fájlban):

```python
def test_este_hajnali_futas_az_elozo_napra_ir(tmp_path):
    # 03:38 CEST (01:38 UTC) esti futás = az ELŐZŐ nap (08-31) esti pótlása, NEM 09-01 este
    most = datetime(2026, 9, 1, 1, 38, tzinfo=timezone.utc)
    ddir = tmp_path / "docs" / "data"
    futtato.futtat(_config(), AdatKliens(), tmp_path / "adatok", ddir, most=most, mode="este")
    elozo = json.loads((ddir / "napok" / "2026-08-31.json").read_text(encoding="utf-8"))
    assert "este" in elozo
    assert not (ddir / "napok" / "2026-09-01.json").exists()


def test_este_esti_futas_aznapra_ir(tmp_path):
    # 21:00 CEST (19:00 UTC) → aznap (09-01) este
    most = datetime(2026, 9, 1, 19, 0, tzinfo=timezone.utc)
    ddir = tmp_path / "docs" / "data"
    futtato.futtat(_config(), AdatKliens(), tmp_path / "adatok", ddir, most=most, mode="este")
    mai = json.loads((ddir / "napok" / "2026-09-01.json").read_text(encoding="utf-8"))
    assert "este" in mai


def test_reggel_mod_valtozatlan_nincs_hajnali_eltolas(tmp_path):
    # reggel-mód: a 09:00 CEST (07:00 UTC) a MAI reggelbe ír (nincs esti_nap-eltolás)
    most = datetime(2026, 9, 1, 7, 0, tzinfo=timezone.utc)
    ddir = tmp_path / "docs" / "data"
    futtato.futtat(_config(), AdatKliens(), tmp_path / "adatok", ddir, most=most, mode="reggel")
    mai = json.loads((ddir / "napok" / "2026-09-01.json").read_text(encoding="utf-8"))
    assert "reggel" in mai
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_futtato.py -k "hajnali or esti_futas or reggel_mod_valtozatlan"`
Expected: FAIL — a `test_este_hajnali_futas_az_elozo_napra_ir` bukik: `napok/2026-09-01.json` létezik (a jelenlegi kód a naptári napra ír), `2026-08-31.json` hiányzik.

- [ ] **Step 3: Write minimal implementation**

`trendfigyelo/futtato.py:315` — a jelenlegi sort:

```python
    nap_iso = most.astimezone(seged.BUDAPEST).date().isoformat()
```

cseréld erre:

```python
    # este-mód: a LOGIKAI esti nap (hajnali backup = az ELŐZŐ este pótlása, nincs hamis
    # másnapi esti szegmens); reggel-mód: a budapesti naptári nap (nincs hajnali eset).
    nap_iso = (most.astimezone(seged.BUDAPEST).date().isoformat()
               if csak_felkapott else seged.esti_nap(most))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_futtato.py`
Expected: PASS (a régi futtato-tesztek is zöldek — azok `most=...12:00`-t használnak, ami >= 6:00 → aznap, változatlan viselkedés)

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/futtato.py tests/test_futtato.py
git commit   # "fix(futtato): este-mód a logikai esti napra ír (esti_nap) — nincs hamis másnapi este"  + trailerek
```

---

## Task 3: `futas_orzo` őr — este-ág a logikai esti napot nézi

**Files:**
- Modify: `trendfigyelo/futas_orzo.py` (`main`, a `--szegmens` ág)
- Test: `tests/test_futas_orzo.py`

**Interfaces:**
- Consumes: `seged.esti_nap` (Task 1). A `main` a `--szegmens este docs/data` hívásra `true`/`false`-t nyomtat. A `szegmens_mar_gyujtottunk_ma(docs_data, szegmens, nap)` VÁLTOZATLAN (a `nap` paramétert a `main` számolja). A `_ir_nap_szegmens(tmp_path, nap, szegmens, frissitve)` helper már a tesztfájlban van.

- [ ] **Step 1: Write the failing tests**

`tests/test_futas_orzo.py` — a fejlécbe (ha nincs) vedd fel:
`from datetime import datetime, timezone`
majd a szegmens-tesztek mellé:

```python
def test_cli_este_hajnali_az_elozo_estet_nezi_skip(tmp_path, capsys, monkeypatch):
    # 03:38 CEST (01:38 UTC) → esti_nap = 08-31; a 08-31 este MEGVAN → skip (true)
    _ir_nap_szegmens(tmp_path, "2026-08-31", "este", "2026-08-31T19:06:00+00:00")
    monkeypatch.setattr(futas_orzo.seged, "most_utc",
                        lambda: datetime(2026, 9, 1, 1, 38, tzinfo=timezone.utc))
    futas_orzo.main(["--szegmens", "este", str(tmp_path)])
    assert capsys.readouterr().out.strip() == "true"


def test_cli_este_hajnali_hianyzo_elozo_este_gyujt(tmp_path, capsys, monkeypatch):
    # a 08-31 este HIÁNYZIK → a hajnali backup bepótolja (false = gyűjts)
    monkeypatch.setattr(futas_orzo.seged, "most_utc",
                        lambda: datetime(2026, 9, 1, 1, 38, tzinfo=timezone.utc))
    futas_orzo.main(["--szegmens", "este", str(tmp_path)])
    assert capsys.readouterr().out.strip() == "false"


def test_cli_este_esti_futas_aznapot_nezi_gyujt(tmp_path, capsys, monkeypatch):
    # 21:00 CEST (19:00 UTC) → esti_nap = 09-01; a 09-01 este MÉG NINCS → false (gyűjts),
    # a tegnapi (08-31) este megléte nem befolyásol
    _ir_nap_szegmens(tmp_path, "2026-08-31", "este", "2026-08-31T19:06:00+00:00")
    monkeypatch.setattr(futas_orzo.seged, "most_utc",
                        lambda: datetime(2026, 9, 1, 19, 0, tzinfo=timezone.utc))
    futas_orzo.main(["--szegmens", "este", str(tmp_path)])
    assert capsys.readouterr().out.strip() == "false"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_futas_orzo.py -k "cli_este"`
Expected: FAIL — `test_cli_este_hajnali_az_elozo_estet_nezi_skip` `false`-t kap (a jelenlegi kód a 09-01-et nézi, ott nincs este), várt `true`.

- [ ] **Step 3: Write minimal implementation**

`trendfigyelo/futas_orzo.py`, a `main`-ben a `--szegmens` ág — a jelenlegi:

```python
        docs_data = maradek[0] if maradek else "docs/data"
        ma_bp = seged.most_utc().astimezone(seged.BUDAPEST).date().isoformat()
        print("true" if szegmens_mar_gyujtottunk_ma(docs_data, szegmens, ma_bp) else "false")
        return 0
```

cseréld erre:

```python
        docs_data = maradek[0] if maradek else "docs/data"
        # este: a LOGIKAI esti napot nézzük (hajnali backup az ELŐZŐ estét ellenőrzi → nem gyűjt
        # hamis másnapi estit, de a tényleg kimaradt estét bepótolja). reggel: a budapesti naptári nap.
        if szegmens == "este":
            nap = seged.esti_nap(seged.most_utc())
        else:
            nap = seged.most_utc().astimezone(seged.BUDAPEST).date().isoformat()
        print("true" if szegmens_mar_gyujtottunk_ma(docs_data, szegmens, nap) else "false")
        return 0
```

Frissítsd a `szegmens_mar_gyujtottunk_ma` fölötti kommentet is: a „budapesti-éjfél-utáni backup FAIL-OPEN, ne javítsd" megjegyzést cseréld egy rövid sorra, hogy az este-ág mostantól a `seged.esti_nap`-ot használja (a hajnali backup az előző estét nézi), a reggel-ág változatlan.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_futas_orzo.py`
Expected: PASS (a régi `test_cli_szegmens` füst-teszt is zöld: hiányzó fájl → `false`)

- [ ] **Step 5: Commit**

```bash
git add trendfigyelo/futas_orzo.py tests/test_futas_orzo.py
git commit   # "fix(futas_orzo): este-őr a logikai esti napot nézi (esti_nap) — hajnali backup nem dedupál hamisat"  + trailerek
```

---

## Task 4: Egyszeri adat-takarítás — a hamis 09-01 esti szegmens törlése

**Files:**
- Modify: `docs/data/napok/2026-09-01.json`, `docs/data/kategoriak.json`
- NINCS teszt (egyszeri adat-korrekció); a lépés VERIFIKÁL a végén.

**Interfaces:** —

**FONTOS:** ez KÜLÖN, adat-commit. NEM nyúlunk `kulcsszo_nyers.json`/`kulcsszo_lanc.json`/`legfrissebb.json`/`index.json`-hoz.

- [ ] **Step 1: Ellenőrizd az aktuális állapotot**

Run:
```bash
.venv/bin/python -c "import json; d=json.load(open('docs/data/napok/2026-09-01.json')); print('napfájl szegmensek:', [k for k in d if k in ('reggel','este')])"
.venv/bin/python -c "import json; kj=json.load(open('docs/data/kategoriak.json')); r=[n for n in kj['napok'] if n['nap']=='2026-09-01'][0]; print('kategoriak 09-01 szegmensek:', [k for k in r if k in ('reggel','este')])"
```
Expected: mindkettő `['reggel', 'este']`. Ha az `este` MÁR NINCS ott (pl. a valós esti futás közben átírta), a task NO-OP → jelezd és ugord át a törlést.

- [ ] **Step 2: Töröld az `este` szegmenst mindkét fájlból (érték-megőrző, formázás-tisztelő edit)**

Run:
```bash
.venv/bin/python - <<'PY'
import json

# napok/2026-09-01.json — az 'este' kulcs törlése, a 'reggel' marad
p = "docs/data/napok/2026-09-01.json"
d = json.load(open(p, encoding="utf-8"))
d.pop("este", None)
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(p, "a", encoding="utf-8").write("\n")

# kategoriak.json — a 2026-09-01 rekord 'este' al-kulcsának törlése
p = "docs/data/kategoriak.json"
kj = json.load(open(p, encoding="utf-8"))
for n in kj["napok"]:
    if n.get("nap") == "2026-09-01":
        n.pop("este", None)
json.dump(kj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(p, "a", encoding="utf-8").write("\n")
print("kész")
PY
```

**MEGJEGYZÉS a formázásról:** a fenti `indent=1` a projekt adatfájl-konvencióját követi (a `kategoriak.json`-t is így láttuk). A `git diff` az edit ELŐTT ellenőrizd: HA a diff a teljes fájlt átformázza (az eredeti nem `indent=1` volt), akkor `git checkout` a fájlokra, és inkább kézi, minimális JSON-edittel (csak az `este` blokk kivágása) csináld, hogy a diff kicsi maradjon.

- [ ] **Step 3: Verifikáld**

Run:
```bash
.venv/bin/python -c "import json; d=json.load(open('docs/data/napok/2026-09-01.json')); assert 'este' not in d and 'reggel' in d, d.keys(); print('napfájl OK:', list(d))"
.venv/bin/python -c "import json; kj=json.load(open('docs/data/kategoriak.json')); r=[n for n in kj['napok'] if n['nap']=='2026-09-01'][0]; assert 'este' not in r and 'reggel' in r; print('kategoriak OK:', [k for k in r])"
git --no-pager diff --stat docs/data/napok/2026-09-01.json docs/data/kategoriak.json
```
Expected: napfájl csak `nap`+`reggel`; kategoriak 09-01 csak `nap`+`reggel`; a diff KIS (csak az `este` blokk eltűnt).

- [ ] **Step 4: Commit (KÜLÖN adat-commit)**

```bash
git add docs/data/napok/2026-09-01.json docs/data/kategoriak.json
git commit   # "adat: 09-01 hamis esti szegmens eltávolítása (esti-nap javítás; ma 21:00 gyűjti a valósat)"  + trailerek
```

---

## Task 5: Frontend shaper — `kategoria_idosor` „osszesen" mód

**Files:**
- Modify: `docs/js/app.js` (`kategoria_idosor` `kat()` belső fn, `:1394-1400`)
- Test: `e2e/trend.spec.js`

**Interfaces:**
- Consumes: `mock(page, {kategoriak})` (e2e helper); a DOM-tükör `#idosor-blokk .idosor-adat .idosor-vonal[data-kategoria="X"]` → `data-ertekek` (JSON-tömb).
- Produces: `kategoria_idosor(kj, "osszesen")` — naponként a MEGLÉVŐ szegmensek darabszám-összege.

- [ ] **Step 1: Write the failing tests**

`e2e/trend.spec.js` — a #2 váltó tesztjei mellé:

```javascript
// ── Napi összesen mód — a nap MEGLÉVŐ szegmenseinek darabszám-összege ──
test("N. idősor: Napi összesen — reggel+este darabszám-összeg", async ({ page }) => {
  await mock(page, { kategoriak: { napok: [
    { nap: "2026-09-01", reggel: { kategoriak: { Sports: 3, Other: 8 } },
                          este:   { kategoriak: { Sports: 1, Politics: 2, Other: 12 } } } ] } });
  await page.goto("/");
  const tukor = page.locator("#idosor-blokk .idosor-adat");
  await expect(tukor.locator('.idosor-vonal[data-kategoria="Sports"]')).toHaveAttribute("data-ertekek", "[4]");
  await expect(tukor.locator('.idosor-vonal[data-kategoria="Politics"]')).toHaveAttribute("data-ertekek", "[2]");
  await expect(tukor.locator('.idosor-vonal[data-kategoria="Other"]')).toHaveAttribute("data-ertekek", "[20]");
});

test("N. idősor: Napi összesen — csak reggeli nap → csak a reggeli számít (nincs áthúzott este)", async ({ page }) => {
  await mock(page, { kategoriak: { napok: [
    { nap: "2026-09-01", reggel: { kategoriak: { Sports: 3 } } } ] } });   // NINCS este
  await page.goto("/");
  await expect(page.locator('#idosor-blokk .idosor-adat .idosor-vonal[data-kategoria="Sports"]'))
    .toHaveAttribute("data-ertekek", "[3]");
});

test("N. idősor: Napi összesen — régi lapos rekord EGYSZER számít", async ({ page }) => {
  await mock(page, { kategoriak: { napok: [
    { nap: "2026-08-05", kategoriak: { A: 2 } } ] } });   // legacy (nincs reggel/este)
  await page.goto("/");
  await expect(page.locator('#idosor-blokk .idosor-adat .idosor-vonal[data-kategoria="A"]'))
    .toHaveAttribute("data-ertekek", "[2]");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx playwright test --workers=1 -g "Napi összesen"`
Expected: FAIL — az alap `idosor_szegmens` még `"este"`, a fixture reggel-only napján/az összegen nem a várt értékek jönnek (pl. a Sports `[3]` az este-only olvasat helyett `[4]` várt, vagy a tükör hiányzik). (Megjegyzés: a Task 6 állítja majd az alapot `osszesen`-re; itt a shaper `kat()` „osszesen" ágának hiánya a RED. Ha a Task 6 még nincs kész, ideiglenesen a teszt hívhatja explicit a `osszesen` váltógombot — de mivel a gomb sem létezik még, a RED egyértelmű: nincs `data-szegmens="osszesen"`. A GREEN-t a Task 5 shaper + a Task 6 alap/gomb együtt adja; a helyes RED→GREEN sorrendhez a Task 5 és Task 6 kódját EGY körben is beviheted, de KÜLÖN committal — lásd lent.)

**FONTOS sorrend-megjegyzés:** a shaper (Task 5) és a gomb/alap (Task 6) együtt teszi zölddé ezeket a teszteket. Ezért:
- Task 5 Step 3: írd meg a shaper „osszesen" ágát.
- Task 5 Step 4: a tesztek MÉG bukhatnak (nincs gomb/alap) — ez rendben, jelezd.
- Task 6 zárja zöldre őket. Alternatíva (tisztább RED→GREEN): a Task 5 tesztjei ideiglenesen `await page.evaluate(() => { /* nincs API */ })` helyett a Task 6 után ellenőrződnek. A KÖNNYEBB út: Task 5-ben a shaper-egységet közvetlenül ne e2e-vel, hanem a Task 6-tal együtt zöldítsd, és a Task 5 commit csak a shaper-kódot + a 3 tesztet tartalmazza (piros marad a gomb hiánya miatt), a Task 6 commit teszi zöldre. **A subagent-executor számára: Task 5 és Task 6 egymás után, a GREEN-gate a Task 6 végén közös.**

- [ ] **Step 3: Write minimal implementation**

`docs/js/app.js`, `kategoria_idosor` `kat()` — a jelenlegi:

```javascript
  function kat(n) {   // a rekord kategoriak-ja a kért szegmensre; régi lapos rekord 'este'-ként
    if (n[szeg] && n[szeg].kategoriak) return n[szeg].kategoriak;
    if (szeg === "este" && n.kategoriak) return n.kategoriak;   // visszafelé kompat
    return null;
  }
```

cseréld erre:

```javascript
  function kat(n) {   // a rekord kategoriak-ja a kért szegmensre; régi lapos rekord 'este'-ként
    if (szeg === "osszesen") {                       // a nap MEGLÉVŐ szegmenseinek darabszám-összege
      const ossz = {}; let van = false;
      ["reggel", "este"].forEach(function (s) {
        if (n[s] && n[s].kategoriak) {
          van = true;
          Object.keys(n[s].kategoriak).forEach(function (c) { ossz[c] = (ossz[c] || 0) + n[s].kategoriak[c]; });
        }
      });
      if (!van && n.kategoriak) {                    // régi lapos rekord → EGYSZER számít (visszafelé kompat)
        van = true;
        Object.keys(n.kategoriak).forEach(function (c) { ossz[c] = (ossz[c] || 0) + n.kategoriak[c]; });
      }
      return van ? ossz : null;
    }
    if (n[szeg] && n[szeg].kategoriak) return n[szeg].kategoriak;
    if (szeg === "este" && n.kategoriak) return n.kategoriak;   // visszafelé kompat
    return null;
  }
```

- [ ] **Step 4: Run tests (várható: még piros a gomb/alap hiánya miatt → Task 6 zárja)**

Run: `npx playwright test --workers=1 -g "Napi összesen"`
Expected: a Task 6 ELŐTT még FAIL (nincs `osszesen` gomb/alap). Jelezd, és folytasd a Task 6-tal.

- [ ] **Step 5: Commit (csak a shaper + a 3 teszt)**

```bash
git add docs/js/app.js e2e/trend.spec.js
git commit   # "feat(idosor): kategoria_idosor 'osszesen' mód — szegmensek darabszám-összege"  + trailerek
```

---

## Task 6: Frontend váltó — 3 gomb + alap „Napi összesen"

**Files:**
- Modify: `docs/js/app.js` — `idosor_szegmens_valto_epit` (`:1535`), az `idosor_szegmens` alapérték (`:1323`)
- Test: `e2e/trend.spec.js` (új gomb-sorrend teszt + a MEGLÉVŐ „N. idősor: Reggel/Este váltó" teszt frissítése)

**Interfaces:**
- Consumes: a Task 5 shaper „osszesen" ága.
- Produces: `.idosor-szegmens-valto` 3 gombbal, sorrend `osszesen · reggel · este`, alap `osszesen` (`aria-pressed`).

- [ ] **Step 1: Write / update the tests**

Új teszt `e2e/trend.spec.js`-be:

```javascript
test("N. idősor: három szegmens-gomb, sorrend Napi összesen · Reggeli · Esti, alap az összesen", async ({ page }) => {
  await mock(page, { kategoriak: { napok: [
    { nap: "2026-09-01", reggel: { kategoriak: { Sports: 3 } }, este: { kategoriak: { Politics: 2 } } } ] } });
  await page.goto("/");
  const gombok = page.locator(".idosor-szegmens-valto button");
  await expect(gombok).toHaveCount(3);
  await expect(gombok.nth(0)).toHaveAttribute("data-szegmens", "osszesen");
  await expect(gombok.nth(1)).toHaveAttribute("data-szegmens", "reggel");
  await expect(gombok.nth(2)).toHaveAttribute("data-szegmens", "este");
  await expect(gombok.nth(0)).toHaveText("Napi összesen");
  await expect(gombok.nth(0)).toHaveAttribute("aria-pressed", "true");
});
```

A MEGLÉVŐ teszt (`"N. idősor: Reggel/Este váltó — alap Este, váltásra a reggeli számok"`, ~`:708`) alap-állítását igazítsd az új alaphoz. A fixture `reggel {Sports:3}` + `este {Sports:1, Politics:2}` → `osszesen` = Sports 4 + Politics 2 = 2 vonal (a `data-vonal-szam` „2" MARAD). Cseréld:
- a címet: `"N. idősor: szegmens-váltó — alap Napi összesen, váltásra a reggeli számok"`;
- az `[data-szegmens="este"]` aria-pressed=true állítást → `[data-szegmens="osszesen"]` aria-pressed=true;
- a reggelre kattintás utáni `data-vonal-szam == "1"` (csak Sports) MARAD.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx playwright test --workers=1 -g "szegmens-gomb|szegmens-váltó"`
Expected: FAIL — 2 gomb van (nincs `osszesen`), az alap `este`.

- [ ] **Step 3: Write minimal implementation**

`docs/js/app.js:1323` — az alapérték:

```javascript
let idosor_szegmens = "este";   // #2 Reggel/Este váltó — alap az esti (teljes) pillanatkép
```
→
```javascript
let idosor_szegmens = "osszesen";   // #2 szegmens-váltó — alap a Napi összesen (reggel+este a napra)
```

`docs/js/app.js:1535` — a gomb-lista:

```javascript
  [["reggel", "Reggeli 9:00"], ["este", "Esti 21:00"]].forEach(function (par) {
```
→
```javascript
  [["osszesen", "Napi összesen"], ["reggel", "Reggeli 9:00"], ["este", "Esti 21:00"]].forEach(function (par) {
```

Frissítsd a függvény fölötti kommentet is (`:1531`, „a #2 Reggel/Este váltó … alap Este") → „3-gombos szegmens-váltó (Napi összesen / Reggeli / Esti), alap a Napi összesen".

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test --workers=1 -g "Napi összesen|szegmens-gomb|szegmens-váltó"`
Expected: PASS — a Task 5 „Napi összesen" tesztek is ZÖLDEK (most van gomb+alap). Futtasd a teljes trend-spec-et is: `npx playwright test --workers=1 e2e/trend.spec.js` — a régi „üres szegmensen a váltó" teszt is zöld (este-only napon az `osszesen` = az este → `data-vonal-szam` 1 változatlan).

- [ ] **Step 5: Commit**

```bash
git add docs/js/app.js e2e/trend.spec.js
git commit   # "feat(idosor): 3-gombos szegmens-váltó + alap Napi összesen"  + trailerek
```

---

## Task 7: Frontend info-doboz — állandó kék callout a három nézetről

**Files:**
- Modify: `docs/js/app.js` — `idosor_blokk_render` (`:1553`): info-doboz beszúrása + a takarító-lista bővítése
- Modify: `docs/css/app.css` (`:242`, `:250`, `:255` selector-csoportok)
- Test: `e2e/trend.spec.js`

**Interfaces:**
- Produces: `#idosor-blokk .idosor-info` (mindig látszó `<p>`, kék bal-border + ⓘ).

- [ ] **Step 1: Write the failing test**

`e2e/trend.spec.js`-be:

```javascript
test("N. idősor: állandó info-doboz a három nézetről + frissülési időkről, nincs duplikáció", async ({ page }) => {
  await mock(page, { kategoriak: { napok: [
    { nap: "2026-09-01", reggel: { kategoriak: { Sports: 3 } }, este: { kategoriak: { Politics: 2 } } } ] } });
  await page.goto("/");
  const info = page.locator("#idosor-blokk .idosor-info");
  await expect(info).toHaveCount(1);
  await expect(info).toBeVisible();
  await expect(info).toContainText("Napi összesen");
  await expect(info).toContainText("21:00");
  // váltás után is PONTOSAN EGY info-doboz (a re-render ne duplikálja)
  await page.locator('.idosor-szegmens-valto [data-szegmens="reggel"]').click();
  await expect(page.locator("#idosor-blokk .idosor-info")).toHaveCount(1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx playwright test --workers=1 -g "info-doboz a három nézetről"`
Expected: FAIL — nincs `.idosor-info` elem.

- [ ] **Step 3: Write minimal implementation**

`docs/js/app.js`, `idosor_blokk_render` — (a) a takarító `querySelectorAll(...)` listába vedd fel a `.idosor-info`-t, hogy a re-render ne duplikáljon. A jelenlegi (`:1561-1563`):

```javascript
  blokk.querySelectorAll("." + OSZT_T.idosor_chart_doboz + ", ." + OSZT_T.idosor_adat + ", ." + OSZT_T.idosor_magyarazat
    + ", .idosor-szegmens-valto")
    .forEach(function (e) { e.remove(); });
```
→ told a listához a `, .idosor-info`-t:
```javascript
  blokk.querySelectorAll("." + OSZT_T.idosor_chart_doboz + ", ." + OSZT_T.idosor_adat + ", ." + OSZT_T.idosor_magyarazat
    + ", .idosor-szegmens-valto, .idosor-info")
    .forEach(function (e) { e.remove(); });
```

(b) a váltó `appendChild` UTÁN (`:1567` után) szúrd be az info-dobozt:

```javascript
  blokk.appendChild(idosor_szegmens_valto_epit());   // a váltó MINDIG látszik (üres szegmensnél is → vissza lehet váltani)

  const info = document.createElement("p");
  info.className = "idosor-info";
  info.textContent = "Három nézet: a Napi összesen egy nap reggeli és esti adatát adja össze; a Reggeli 9:00 "
    + "és az Esti 21:00 a két külön pillanatkép. Ha egy napnál még csak reggeli adat van (az aznapi 21:00 esti "
    + "lekérdezés még nem futott le), a Napi összesen arra a napra egyelőre csak a reggelit tartalmazza, és este "
    + "21:00 után egészül ki. Frissülés: reggel ~9:00, este ~21:00 (budapesti idő; a honlap kevéssel utána frissül).";
  blokk.appendChild(info);
```

- [ ] **Step 4: CSS — `.idosor-info` a kék-callout csoportokba**

`docs/css/app.css`:
- a `:242` sor (`#idosor-blokk .idosor-magyarazat,`) MELLÉ, ugyanabba a selector-listába vedd fel:
  `#idosor-blokk .idosor-info,`
- a `:250` margó-szabály mintájára adj egy sort:
  `#idosor-blokk .idosor-info { margin: .3rem 0 .8rem; max-width: 40rem; }`
- a `::before` csoportba (`:255` `#idosor-blokk .idosor-magyarazat::before,` mellé):
  `#idosor-blokk .idosor-info::before,`

- [ ] **Step 5: Run test to verify it passes**

Run: `npx playwright test --workers=1 -g "info-doboz a három nézetről"`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add docs/js/app.js docs/css/app.css e2e/trend.spec.js
git commit   # "feat(idosor): állandó info-doboz a három nézetről + frissülési időkről"  + trailerek
```

---

## Task 8: Leltár — invariáns + tétel

**Files:**
- Modify: `docs/superpowers/leltar.md`

**Interfaces:** —

- [ ] **Step 1: Olvasd ki az aktuális invariánst**

Run: `grep -n "aktív\|kész\|törzs\|= *[0-9]" docs/superpowers/leltar.md | grep -i "invari\|törzs\|aktív.*kész" | head`
Keresd meg az AKTUÁLIS `aktív + kész + rekord + félretett = törzs` összeget (a memória szerint ~`3 + 44 + 29 = 76`, de a FÁJL a mérvadó).

- [ ] **Step 2: Adj hozzá egy KÉSZ tételt** (`NAPI-OSSZESEN-ESTI-NAP`) a kész-szekcióba: rövid leírás (Napi összesen idősor-nézet + `esti_nap` forrás-javítás a hamis másnapi este ellen + egyszeri 09-01 adat-takarítás), spec+terv útvonalak, „LESZÁLLÍTVA 2026-09-01" jelöléssel. Növeld a `kész` számot 1-gyel és a `törzs`-sorszámot 1-gyel; ellenőrizd, hogy az invariáns egyenlet STIMMEL.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/leltar.md
git commit   # "doc(leltar): NAPI-OSSZESEN-ESTI-NAP kész + invariáns"  + trailerek
```

---

## Végső ellenőrzés (a push-kör ELŐTT, a finishing skillben)

- [ ] TELJES SOROS suite zöld: `.venv/bin/python -m pytest -p no:xdist -q` ÉS `npx playwright test --workers=1`.
- [ ] `git status` — csak a szándékolt fájlok; `ATADAS-2026-08-18.txt` UNTRACKED marad.
- [ ] Az élő-UI előnézeten (regen-script + localhost) nézd meg: 3 gomb, alap Napi összesen, info-doboz, a 09-01 nap a takarítás után reggel-only.
- [ ] Push: KÜLÖN kapuzott kör, user-jóváhagyással; a Task 4 adat-commit + a kód-commitok együtt mennek fel MA 21:00 (budapesti) ELŐTT.

## Self-Review jegyzet (terv-készítéskor futtatva)

- **Spec-lefedettség:** A rész → Task 1-3; B rész → Task 4; C rész shaper → Task 5, váltó/alap → Task 6, info → Task 7; D rész tesztek minden taskban; leltár → Task 8. Nincs fedetlen spec-elem.
- **Placeholder-scan:** nincs TBD/„handle edge cases"; minden lépés konkrét kóddal.
- **Típus-konzisztencia:** `esti_nap(most)->str` és `ESTI_NAP_HAJNAL_KUSZOB` egységes T1/T2/T3-ban; a frontend `"osszesen"` szegmens-kulcs egységes T5/T6/T7-ben; a DOM-tükör attribútumok (`data-ertekek`, `data-vonal-szam`, `.idosor-vonal[data-kategoria]`, `.idosor-szegmens-valto [data-szegmens]`) a meglévő tesztekkel egyeznek.
- **Ismert sorrend-csapda:** a Task 5 e2e-tesztjei a Task 6 gomb/alap nélkül pirosak — ez dokumentálva; a közös GREEN-gate a Task 6 végén.
