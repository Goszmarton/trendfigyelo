# Mód-tudatos AI-elemzés (reggeli scoped + esti teljes) + flash-fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A napi AI-elemzés reggel csak a felkapott reggeli pillanatképet elemezze (minden más „…frissül este" helyőrző), este a teljeset; és szűnjön meg az éjfél-utáni backup okozta következő-napi üres/„flash" elemzés.

**Architecture:** Új `elemzes_orzo.py` ad mód-tudatos logikai napot (reggel=BP naptári nap, este=`esti_nap`) és per-(nap,mód) idempotencia-őrt (a `futas_orzo.py` mintájára). Az `elemzo.py` végigfűz egy `mode` paramétert (payload/séma/prompt/artefakt), reggel szűkített sémával csak a `felkapott.reggel` bekezdést kéri az AI-tól és a többi prózát determinisztikus helyőrzővel tölti. Az `elemzes.yml` mindkét gyűjtő-workflow-ra hallgat, a `workflow_run.name`-ből módot vezet le és az őrrel kihagyja a backup-újraindításokat.

**Tech Stack:** Python 3.12 (stdlib + `zoneinfo` a `seged`-en át; `anthropic` SDK a kliens-varrat mögött, tesztben NEM hívva), pytest (SOROS, `-p no:xdist`), Playwright (`--workers=1`, testDir `e2e/`), GitHub Actions (`workflow_run`).

**Spec:** `docs/superpowers/specs/2026-09-03-reggeli-elemzes-mod-tudatos-design.md`

## Global Constraints

- **SOROS suite:** `.venv/bin/python -m pytest -p no:xdist -q` és `npx playwright test --workers=1`. MUTÁCIÓ=1.
- **TDD valódi RED→GREEN:** minden implementáció előtt bukó teszt, futtatva, a bukás igazolva.
- **Az AI-t SOHA nem hívjuk tesztben:** a `kliens` varraton át `KamuKliens`/`HibasKliens` fake-ek; nincs hálózati hívás, nincs `ANTHROPIC_API_KEY` igény.
- **Nincs argless `datetime.now()`/`seged.most_utc()` a tesztelt logikában:** az időt paraméterként (`most`) adjuk; a CLI/`main` a belépési ponton hívhatja a `seged.most_utc()`-ot.
- **A deferrált helyőrző szöveg PONTOS értéke:** `"Ez a rész az esti futáskor (21:00) frissül."` (egyetlen forrás: `elemzo._ESTI_FRISSUL`).
- **`git add` KIZÁRÓLAG néven** (soha `-A`/`.`); a gyökér `ATADAS-2026-08-18.txt` SOHA nem staged.
- **Commit-trailerek** minden commitban:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN`
- **Push nincs** — külön, kapuzott kör, csak explicit user-engedéllyel.
- **Pótolhatatlan adat READ-ONLY:** az elemzés csak olvassa a gyűjtés-adatot; teszt-adat kizárólag `tmp_path`-ban. A `docs/data/elemzes*.json`-t élesben a workflow írja, kézzel NEM nyúlunk hozzá.
- **Test output pristine** (nincs warning).
- **Független `hirfigyelo` projekt** a közös szerveren — NE nyúlj hozzá.

---

### Task 1: `elemzes_orzo.py` — logikai nap + idempotencia-őr

Új tiszta modul: a mód szerinti logikai elemzés-nap és a per-(nap,mód) „már kész?" döntés, plusz CLI a workflow őr-lépéséhez. Ez a flash-fix magja.

**Files:**
- Create: `trendfigyelo/elemzes_orzo.py`
- Test: `tests/test_elemzes_orzo.py`

**Interfaces:**
- Consumes: `seged.esti_nap(most) -> str` (hajnali `<6:00` visszagörgetés az előző napra), `seged.BUDAPEST` (ZoneInfo), `seged.most_utc()`.
- Produces:
  - `elemzes_nap(mode, most) -> str` — reggel: `most` budapesti naptári napja; este: `seged.esti_nap(most)`.
  - `elemzes_mar_kesz(docs_data, nap, mode) -> bool` — reggel: True ha `elemzesek/<nap>.json` létezik (idempotens, sosem downgrade-el); este: True CSAK ha a fájl `mode` mezője `"este"`.
  - CLI: `python -m trendfigyelo.elemzes_orzo --mode <reggel|este> <docs_data>` → `"true"`/`"false"`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_elemzes_orzo.py
import json
from datetime import datetime, timezone

from trendfigyelo import elemzes_orzo


def _ir_artefakt(dd, nap, mode):
    d = dd / "elemzesek"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{nap}.json").write_text(json.dumps({"nap": nap, "mode": mode}), encoding="utf-8")


# ── elemzes_nap ──────────────────────────────────────────────
def test_elemzes_nap_reggel_budapesti_naptari_nap():
    most = datetime(2026, 9, 3, 7, 0, tzinfo=timezone.utc)   # 09:00 Budapest
    assert elemzes_orzo.elemzes_nap("reggel", most) == "2026-09-03"


def test_elemzes_nap_este_esti_nap():
    most = datetime(2026, 9, 3, 19, 0, tzinfo=timezone.utc)  # 21:00 Budapest
    assert elemzes_orzo.elemzes_nap("este", most) == "2026-09-03"


def test_elemzes_nap_este_hajnali_backup_elozo_nap():
    # 2026-09-03T23:30Z = budapesti 2026-09-04T01:30 (<6:00) → esti_nap az ELŐZŐ napot adja
    most = datetime(2026, 9, 3, 23, 30, tzinfo=timezone.utc)
    assert elemzes_orzo.elemzes_nap("este", most) == "2026-09-03"


# ── elemzes_mar_kesz + CLI ───────────────────────────────────
# ── elemzes_mar_kesz ─────────────────────────────────────────
def test_mar_kesz_nincs_fajl_false(tmp_path):
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "reggel") is False
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "este") is False


def test_mar_kesz_reggel_barmely_letezo_true(tmp_path):
    _ir_artefakt(tmp_path, "2026-09-03", "reggel")
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "reggel") is True


def test_mar_kesz_reggel_esti_letezo_true_nem_downgradel(tmp_path):
    _ir_artefakt(tmp_path, "2026-09-03", "este")
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "reggel") is True


def test_mar_kesz_este_reggeli_letezo_false_upgradel(tmp_path):
    _ir_artefakt(tmp_path, "2026-09-03", "reggel")
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "este") is False


def test_mar_kesz_este_esti_letezo_true(tmp_path):
    _ir_artefakt(tmp_path, "2026-09-03", "este")
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "este") is True


def test_mar_kesz_olvashatatlan_este_false(tmp_path):
    d = tmp_path / "elemzesek"; d.mkdir(parents=True)
    (d / "2026-09-03.json").write_text("{nem json", encoding="utf-8")
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "este") is False   # fail-open


# ── CLI ──────────────────────────────────────────────────────
def test_cli_este_kesz_true(tmp_path, capsys, monkeypatch):
    _ir_artefakt(tmp_path, "2026-09-03", "este")
    monkeypatch.setattr(elemzes_orzo.seged, "most_utc",
                        lambda: datetime(2026, 9, 3, 19, 0, tzinfo=timezone.utc))
    rc = elemzes_orzo.main(["--mode", "este", str(tmp_path)])
    assert rc == 0 and capsys.readouterr().out.strip() == "true"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -p no:xdist tests/test_elemzes_orzo.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'trendfigyelo.elemzes_orzo'`.

- [ ] **Step 3: Write the module**

```python
# trendfigyelo/elemzes_orzo.py
"""Az AI-elemzés idempotencia-őre + mód-tudatos logikai nap (a futas_orzo.py mintájára).

A napi.yml/reggeli.yml backup-cronjai 'success'-szel zárnak akkor is, ha nem gyűjtöttek,
és mindegyik újraindítja az elemzes.yml-t. Enélkül az elemzés ugyanaznap többször
regenerálódik (nem-determinisztikus próza = flash), az éjfél-utáni esti backup pedig a
KÖVETKEZŐ napra írna üres elemzést (mert a nyers budapesti dátumot használná). Ez a modul
mód szerinti logikai napot ad (reggel = BP naptári nap, este = esti_nap) és eldönti,
kész-e már a mai (nap, mód) elemzés.
"""
import json
import sys
from pathlib import Path

from . import seged


def elemzes_nap(mode, most):
    """A (mode) logikai elemzés-napja. reggel: budapesti naptári nap; este: seged.esti_nap.

    Az esti ág a hajnali (<6:00 BP) futást az ELŐZŐ estére sorolja — nincs következő-napi
    elcsúszás, ezért az éjfél-utáni backup nem ír üres 'holnapi' elemzést."""
    if mode == "este":
        return seged.esti_nap(most)
    return most.astimezone(seged.BUDAPEST).date().isoformat()


def _artefakt_modja(docs_data, nap):
    """Az elemzesek/<nap>.json 'mode' mezője, vagy None (hiányzó/olvashatatlan/régi archív)."""
    fajl = Path(docs_data) / "elemzesek" / f"{nap}.json"
    try:
        art = json.loads(fajl.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return art.get("mode") if isinstance(art, dict) else None


def elemzes_mar_kesz(docs_data, nap, mode):
    """True, ha a mai (nap) elemzés ebben a módban már kész (a backup-újraindítás kihagyható).

    reggel: kész, ha a mai fájl LÉTEZIK (idempotens; sosem ír felül egy esti teljeset →
            nem downgrade-el). este: kész CSAK ha a létező 'mode' == 'este' (teljes) —
            'reggel' esetén az esti LEFUT (scoped → teljes upgrade).
    Hiányzó/olvashatatlan → False (fail-open: inkább fusson, mint tévesen kihagyja)."""
    if mode == "reggel":
        return (Path(docs_data) / "elemzesek" / f"{nap}.json").exists()
    return _artefakt_modja(docs_data, nap) == "este"


def main(argv=None):
    """CLI: `--mode <reggel|este> <docs_data>` → 'true' (ma kész, hagyd ki) / 'false' (fuss)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = "este"
    if "--mode" in argv:
        i = argv.index("--mode")
        mode = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    docs_data = argv[0] if argv else "docs/data"
    nap = elemzes_nap(mode, seged.most_utc())
    print("true" if elemzes_mar_kesz(docs_data, nap, mode) else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -p no:xdist tests/test_elemzes_orzo.py -q`
Expected: PASS (8 passing), pristine.

- [ ] **Step 5: Full suite + commit**

```bash
.venv/bin/python -m pytest -p no:xdist -q
git add trendfigyelo/elemzes_orzo.py tests/test_elemzes_orzo.py
git commit -m "feat(elemzes-orzo): mód-tudatos logikai nap + per-(nap,mód) idempotencia-őr

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN"
```

---

### Task 2: `elemzo.py` — mód-tudatos AI-hívás réteg (payload / séma / prompt / kliens)

A `mode` végigfűzése azon a rétegen, ami eldönti, MIT kérünk az AI-tól. Reggel: youtube-mentes payload, szűkített séma (csak `felkapott.reggel`), reggeli rendszer-prompt.

**Files:**
- Modify: `trendfigyelo/elemzo.py` (`RENDSZER_PROMPT` mellé `_RENDSZER_PROMPT_REGGEL` + `_rendszer_prompt`; `_valasz_sema` `:312`; `epit_payload` `:285`; `_AnthropicKliens.uzenet` `:336`; `elemez` `:355`)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: —
- Produces:
  - `_rendszer_prompt(mode="este") -> str` (reggel → `_RENDSZER_PROMPT_REGGEL`, egyébként `RENDSZER_PROMPT`).
  - `_valasz_sema(youtube=False, mode="este") -> dict` (reggel → csak `{felkapott:{required:[reggel]}}`).
  - `epit_payload(adatok, tegnapi_szamok=None, tegnapi_top=None, mode="este") -> dict` (reggel → nincs `youtube` kulcs).
  - `elemez(payload, kliens=None, modell=MODELL, mode="este")`; `_AnthropicKliens.uzenet(payload, modell, mode="este")`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_elemzo.py — új tesztek (a meglévő importok mellé)
def test_valasz_sema_reggel_csak_felkapott_reggel():
    sema = elemzo._valasz_sema(mode="reggel")
    assert sema["required"] == ["felkapott"]
    fk = sema["properties"]["felkapott"]
    assert fk["required"] == ["reggel"] and set(fk["properties"]) == {"reggel"}
    assert "kulcsszavak" not in sema["properties"] and "valtozas" not in sema["properties"]


def test_valasz_sema_este_valtozatlan_negy_felkapott():
    sema = elemzo._valasz_sema(mode="este")
    assert sema["properties"]["felkapott"]["required"] == ["reggel", "este", "teljes_nap", "het"]
    assert "valtozas" in sema["properties"] and "kulcsszavak" in sema["properties"]


def test_rendszer_prompt_reggel_csak_reggeli_pillanatkep():
    p = elemzo._rendszer_prompt("reggel")
    assert "reggeli" in p.lower()
    assert "NÉGY külön bekezdésben" not in p       # a 4-bekezdéses esti szabály NINCS benne
    assert elemzo._rendszer_prompt("este") == elemzo.RENDSZER_PROMPT


def test_epit_payload_reggel_kihagyja_a_youtube_ot():
    adatok = {"regresszio": {}, "tortenet": {}, "legfrissebb": {"top_trendek": []},
              "napok_trendek": {}, "ma_szegmensek": {"reggel": [{"kifejezes": "r"}]}, "lanc": {},
              "youtube_regresszio": {"kulcsszavak": {"foci": {"intervallumok": {}}}},
              "youtube_nyers": {"kulcsszavak": {"foci": []}}}
    assert "youtube" not in elemzo.epit_payload(adatok, mode="reggel")


def test_elemez_atadja_a_modot_a_kliensnek():
    kliens = KamuKliens(_ai_valasz())
    elemzo.elemez({"felkapott": {}}, kliens=kliens, mode="reggel")
    assert kliens.hivasok[0][2] == "reggel"      # (payload, modell, mode)
```

Frissítsd a `KamuKliens.uzenet` fake-et, hogy fogadja és rögzítse a `mode`-ot:
```python
class KamuKliens:
    def __init__(self, valasz):
        self._valasz = valasz
        self.hivasok = []

    def uzenet(self, payload, modell, mode="este"):
        self.hivasok.append((payload, modell, mode))
        return self._valasz
```
(A meglévő `test_elemez_a_varrat_mogott_nem_hiv_halozatot` assertje `kliens.hivasok[0][1] == "claude-opus-4-8"` VÁLTOZATLAN marad — a modell továbbra is az 1-es indexen.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -p no:xdist tests/test_elemzo.py -q -k "reggel or mod"`
Expected: FAIL — `_valasz_sema()`/`_rendszer_prompt`/`epit_payload` nem ismeri a `mode`/`_rendszer_prompt` nevet (TypeError/AttributeError).

- [ ] **Step 3: Implement the mode-aware AI-call layer**

3a. `RENDSZER_PROMPT` (elemzo.py:21-56) VÁLTOZATLAN marad. Alá vedd fel a reggeli variánst + a választót:
```python
_RENDSZER_PROMPT_REGGEL = (
    "Magyar nyelvű elemző vagy egy magyar Google Trends figyelő oldalhoz. A közönség "
    "laikus olvasó, aki NEM lát JSON-t, mezőneveket vagy technikai részleteket. Most a "
    "REGGELI (9:00 körüli) pillanatképet elemzed: mi pörög ma reggel a magyar Google-keresésben. "
    "SZABÁLYOK, kivétel nélkül: "
    "(1) KIZÁRÓLAG a kapott számokból dolgozol; számot SOHA nem találsz ki. "
    "(2) FOLYÓ, összefüggő magyar BEKEZDÉST (vagy több bekezdést, üres sorral elválasztva) írsz. "
    "SOHA nem használsz felsorolást, bullet-pontot, címkét, kulcs–érték párt vagy szakszót. "
    "(3) SOHA nem említesz mezőnevet, technikai kulcsot, sem a „payload\", „adatstruktúra\" szót. "
    "Ha valamiről nincs adatod, természetes magyar mondattal írod le, nem a hiányzó mezőt nevezed meg. "
    "(4) Ok-okozatot TÉNYKÉNT nem állítasz; ahol magyarázatot feltételezel, óvatosan jelzed "
    "(„feltehetően\", „elképzelhető\") — külön felirat nélkül, a fogalmazás hordozza az óvatosságot. "
    "(5) Hírt, forrást, eseményt nem találsz ki; csak a kapott témák és hírek alapján írsz. "
    "(6) Tömör, óvatos, DE ÉRDEMI: mondd el, mi pörög ma reggel és mit lehet ebből óvatosan leszűrni. "
    "CSAK a reggeli pillanatképről írsz — a nap többi részét (esti kép, heti összesítés, kulcsszavak) "
    "a mai esti futás fogja elemezni, azzal most nem foglalkozol."
)


def _rendszer_prompt(mode="este"):
    return _RENDSZER_PROMPT_REGGEL if mode == "reggel" else RENDSZER_PROMPT
```

3b. `_valasz_sema` (elemzo.py:312) — új `mode` param, reggel szűkített:
```python
def _valasz_sema(youtube=False, mode="este"):
    sz = _szekcio_sema()
    if mode == "reggel":
        return {"type": "object", "additionalProperties": False,
                "required": ["felkapott"],
                "properties": {"felkapott": {"type": "object", "additionalProperties": False,
                                             "required": ["reggel"],
                                             "properties": {"reggel": sz}}}}
    props = {
        "valtozas": sz,
        "kulcsszavak": {"type": "object", "additionalProperties": False,
                        "required": ["napi", "teljes_kep", "het"],
                        "properties": {"napi": sz, "teljes_kep": sz, "het": sz}},
        "felkapott": {"type": "object", "additionalProperties": False,
                      "required": ["reggel", "este", "teljes_nap", "het"],
                      "properties": {"reggel": sz, "este": sz, "teljes_nap": sz, "het": sz}},
    }
    required = ["valtozas", "kulcsszavak", "felkapott"]
    if youtube:
        props["youtube"] = {"type": "object", "additionalProperties": False,
                            "required": ["napi", "teljes_kep", "het"],
                            "properties": {"napi": sz, "teljes_kep": sz, "het": sz}}
        required = required + ["youtube"]
    return {"type": "object", "additionalProperties": False,
            "required": required, "properties": props}
```

3c. `epit_payload` (elemzo.py:285) — új `mode` param, reggel kihagyja a youtube-ot:
```python
def epit_payload(adatok, tegnapi_szamok=None, tegnapi_top=None, mode="este"):
    regresszio = adatok.get("regresszio", {})
    tortenet = adatok.get("tortenet", {})
    szamok = _kulcsszo_szamok(regresszio, tortenet)
    felkapott = _felkapott(adatok.get("legfrissebb", {}), adatok.get("napok_trendek", {}))
    felkapott.update(_felkapott_szegmensek(adatok.get("ma_szegmensek", {}), adatok.get("legfrissebb", {})))
    valtozas = nap_diff(szamok, tegnapi_szamok, felkapott["top"], tegnapi_top)
    payload = {
        "kulcsszavak": {"szamok": szamok},
        "felkapott": felkapott,
        "valtozas": valtozas,
        "kulcsszo_het": _kulcsszo_het(adatok.get("lanc", {})),
    }
    if mode != "reggel":
        yt_szamok = _youtube_szamok(adatok.get("youtube_regresszio"), adatok.get("youtube_nyers"))
        if yt_szamok:
            payload["youtube"] = {"szamok": yt_szamok,
                                  "het_valos": _youtube_het(adatok.get("youtube_nyers"))["szavak"]}
    return payload
```

3d. `_AnthropicKliens.uzenet` (elemzo.py:336) + `elemez` (elemzo.py:355) — `mode` átvezetés:
```python
    def uzenet(self, payload, modell, mode="este"):
        import json
        import anthropic
        kliens = anthropic.Anthropic()   # ANTHROPIC_API_KEY a környezetből
        valasz = kliens.messages.create(
            model=modell, max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium",
                           "format": {"type": "json_schema",
                                      "schema": _valasz_sema(youtube="youtube" in payload, mode=mode)}},
            system=_rendszer_prompt(mode),
            messages=[{"role": "user", "content":
                       "Elemezd az alábbi VALÓS számokat (JSON). Csak ezekből dolgozz:\n"
                       + json.dumps(payload, ensure_ascii=False)}],
        )
        szoveg = next(b.text for b in valasz.content if b.type == "text")
        return json.loads(szoveg)


def elemez(payload, kliens=None, modell=MODELL, mode="este"):
    kliens = kliens or _AnthropicKliens()
    return kliens.uzenet(payload, modell, mode)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -p no:xdist tests/test_elemzo.py -q`
Expected: PASS (a meglévő + 5 új; a `KamuKliens` mode-signatúrája miatt az összes elemzo-teszt zöld).

- [ ] **Step 5: Full suite + commit**

```bash
.venv/bin/python -m pytest -p no:xdist -q
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "feat(elemzo): mód-tudatos AI-hívás réteg (reggel szűkített séma + prompt, youtube-mentes payload)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN"
```

---

### Task 3: `elemzo.py` — mód-tudatos artefakt + `futtat`/`main` bekötés

A reggeli artefakt-ág (VALÓS rétegek + reggeli AI-bekezdés + „…frissül este" helyőrzők, youtube nélkül), az `art["mode"]` mező, és a `main` mód-bekötése (`ELEMZES_MODE` + `elemzes_orzo.elemzes_nap`).

**Files:**
- Modify: `trendfigyelo/elemzo.py` (import `elemzes_orzo`; `_ESTI_FRISSUL` konstans; `valasz_to_artefakt` `:360`; `futtat` `:450`; `main` `:483`)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Consumes: `elemzes_orzo.elemzes_nap(mode, most)` (Task 1); `epit_payload(..., mode=...)`, `elemez(..., mode=...)` (Task 2).
- Produces:
  - `valasz_to_artefakt(ai_valasz, payload, nap, modell, mode="este") -> dict` — mindig `art["mode"]=mode`; reggel: külön ág.
  - `futtat(docs_data, nap, mode="este", kliens=None) -> int`.
  - `main()` — `ELEMZES_MODE` env + `elemzes_orzo.elemzes_nap`.
  - Konstans `_ESTI_FRISSUL = "Ez a rész az esti futáskor (21:00) frissül."`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_elemzo.py — új tesztek

def _ai_valasz_reggel():
    return {"felkapott": {"reggel": {"szoveg": "reggeli-elemzes"}}}


def test_artefakt_reggel_scoped_helyorzokkel():
    payload = _payload_szegmensekkel(van_reggel=True, van_este=True)
    art = elemzo.valasz_to_artefakt(_ai_valasz_reggel(), payload, nap="2026-09-03", modell="m", mode="reggel")
    assert art["mode"] == "reggel"
    assert art["felkapott"]["reggel"]["szoveg"] == "reggeli-elemzes"        # az AI reggeli bekezdése
    assert art["felkapott"]["este"]["szoveg"] == elemzo._ESTI_FRISSUL       # deferrált
    assert art["felkapott"]["teljes_nap"]["szoveg"] == elemzo._ESTI_FRISSUL
    assert art["felkapott"]["het"]["szoveg"] == elemzo._ESTI_FRISSUL
    assert art["kulcsszavak"]["napi"]["szoveg"] == elemzo._ESTI_FRISSUL
    assert art["valtozas"]["szoveg"] == elemzo._ESTI_FRISSUL
    assert art["kulcsszavak"]["szamok"] == payload["kulcsszavak"]["szamok"] # VALÓS réteg megmarad
    assert "reggel_top" in art["felkapott"] and "het_valos" in art["felkapott"]
    assert "youtube" not in art


def test_artefakt_este_kap_mode_mezot():
    payload = _payload_szegmensekkel(van_reggel=True, van_este=True)
    art = elemzo.valasz_to_artefakt(_ai_valasz(), payload, nap="2026-08-31", modell="m")   # default este
    assert art["mode"] == "este"
    assert art["felkapott"]["este"]["szoveg"] == "f-este"                   # esti ág változatlan


def test_futtat_reggel_ir_scoped_artefaktot(tmp_path):
    dd = _minimal_docs_data(tmp_path)
    kod = elemzo.futtat(dd, nap="2026-08-22", mode="reggel", kliens=KamuKliens(_ai_valasz_reggel()))
    assert kod == 0
    art = json.loads((dd / "elemzes.json").read_text(encoding="utf-8"))
    assert art["mode"] == "reggel"
    assert art["felkapott"]["reggel"]["szoveg"] == "reggeli-elemzes"
    assert art["felkapott"]["het"]["szoveg"] == elemzo._ESTI_FRISSUL
    assert "youtube" not in art


def test_main_atveszi_az_elemzes_mode_ot(monkeypatch):
    kapott = {}
    monkeypatch.setenv("ELEMZES_MODE", "reggel")
    monkeypatch.setenv("ELEMZES_NAP", "2026-09-03")
    monkeypatch.setattr(elemzo, "futtat", lambda dd, nap, mode="este", kliens=None: kapott.update(nap=nap, mode=mode) or 0)
    elemzo.main()
    assert kapott == {"nap": "2026-09-03", "mode": "reggel"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest -p no:xdist tests/test_elemzo.py -q -k "reggel_scoped or mode_mezot or futtat_reggel or elemzes_mode"`
Expected: FAIL — `valasz_to_artefakt()` nem ismer `mode`-ot / nincs `_ESTI_FRISSUL` / `main` nem olvas `ELEMZES_MODE`-ot.

- [ ] **Step 3: Implement the mode-aware artefakt + wiring**

3a. Az `elemzo.py` tetején az importhoz add hozzá az `elemzes_orzo`-t (nincs körkörös import — `elemzes_orzo` csak `seged`-et importál):
```python
from trendfigyelo import seged
from trendfigyelo import elemzes_orzo
```
És a `MODELL = "claude-opus-4-8"` közelébe a konstans:
```python
_ESTI_FRISSUL = "Ez a rész az esti futáskor (21:00) frissül."
```

3b. `valasz_to_artefakt` (elemzo.py:360) — új `mode="este"` param, reggeli ág a függvény ELEJÉN, majd az esti ág `art["mode"]`-ot kap:
```python
def valasz_to_artefakt(ai_valasz, payload, nap, modell, mode="este"):
    fk = payload["felkapott"]
    if mode == "reggel":
        d = {"szoveg": _ESTI_FRISSUL}
        return {
            "frissitve": seged.idopont_iso(seged.most_utc()),
            "modell": modell,
            "nap": nap,
            "mode": "reggel",
            "valtozas": {"diff": payload["valtozas"], "szoveg": _ESTI_FRISSUL},
            "kulcsszavak": {"szamok": payload["kulcsszavak"]["szamok"],
                            "napi": d, "teljes_kep": d, "het": d},
            "felkapott": {
                "top": fk["top"], "reggel_top": fk["reggel_top"], "este_top": fk["este_top"],
                "reggel_este_diff": fk["reggel_este_diff"],
                "reggel": ai_valasz["felkapott"]["reggel"],
                "este": d, "teljes_nap": d, "het": d,
                "het_valos": fk["het"],
            },
        }
    valtozas_szoveg = ai_valasz["valtozas"]["szoveg"]
    if not payload["valtozas"].get("van_elozo"):
        valtozas_szoveg = ("Ma nincs korábbi nap, amivel összevethetnénk, így a napi "
                           "elmozdulás egyelőre nem értékelhető. A friss kép a lenti "
                           "szekciókban olvasható.")
    van_reggel = fk.get("van_reggel", True)
    van_este = fk.get("van_este", True)
    reggel_szoveg = ai_valasz["felkapott"]["reggel"]
    este_szoveg = ai_valasz["felkapott"]["este"]
    teljes_nap_szoveg = ai_valasz["felkapott"]["teljes_nap"]
    if not van_reggel:
        reggel_szoveg = {"szoveg": "Ma nem volt reggeli gyűjtés, ezért a reggeli kép nem elemezhető."}
        teljes_nap_szoveg = {"szoveg": "Reggeli pillanatkép híján a nap íve (a reggeltől estig tartó elmozdulás) nem rajzolható."}
    elif not van_este:
        este_szoveg = {"szoveg": "Ma nem volt esti gyűjtés, ezért az esti kép nem elemezhető."}
        teljes_nap_szoveg = {"szoveg": "Esti pillanatkép híján a nap íve nem rajzolható."}
    art = {
        "frissitve": seged.idopont_iso(seged.most_utc()),
        "modell": modell,
        "nap": nap,
        "mode": "este",
        "valtozas": {"diff": payload["valtozas"], "szoveg": valtozas_szoveg},
        "kulcsszavak": {
            "szamok": payload["kulcsszavak"]["szamok"],
            "napi": ai_valasz["kulcsszavak"]["napi"],
            "teljes_kep": ai_valasz["kulcsszavak"]["teljes_kep"],
            "het": ai_valasz["kulcsszavak"]["het"],
        },
        "felkapott": {
            "top": fk["top"],
            "reggel_top": fk["reggel_top"],
            "este_top": fk["este_top"],
            "reggel_este_diff": fk["reggel_este_diff"],
            "reggel": reggel_szoveg,
            "este": este_szoveg,
            "teljes_nap": teljes_nap_szoveg,
            "het": ai_valasz["felkapott"]["het"],
            "het_valos": fk["het"],
        },
    }
    if "youtube" in payload:
        art["youtube"] = {
            "szamok": payload["youtube"]["szamok"],
            "het_valos": payload["youtube"]["het_valos"],
            "napi": ai_valasz["youtube"]["napi"],
            "teljes_kep": ai_valasz["youtube"]["teljes_kep"],
            "het": ai_valasz["youtube"]["het"],
        }
    return art
```

3c. `futtat` (elemzo.py:450) — `mode` param + átvezetés `epit_payload`/`elemez`/`valasz_to_artefakt`-ba:
```python
def futtat(docs_data, nap, mode="este", kliens=None):
    docs_data = Path(docs_data)
    adatok = {
        "regresszio": _betolt(docs_data / "kulcsszo_regresszio.json") or {},
        "tortenet": _betolt(docs_data / "tortenet.json") or {},
        "legfrissebb": _betolt(docs_data / "legfrissebb.json") or {},
        "napok_trendek": _utolso_napok_trendek(docs_data),
        "ma_szegmensek": _ma_szegmensek(docs_data, nap),
        "lanc": _betolt(docs_data / "kulcsszo_lanc.json") or {},
        "youtube_regresszio": _betolt(docs_data / "youtube_regresszio.json"),
        "youtube_nyers": _betolt(docs_data / "youtube_nyers.json"),
    }
    tegnapi = _elozo_archivum(docs_data, nap)
    payload = epit_payload(
        adatok,
        tegnapi_szamok=(tegnapi or {}).get("kulcsszavak", {}).get("szamok") if tegnapi else None,
        tegnapi_top=(tegnapi or {}).get("felkapott", {}).get("top") if tegnapi else None,
        mode=mode,
    )
    try:
        ai_valasz = elemez(payload, kliens=kliens, mode=mode)
    except Exception as e:                       # noqa: BLE001 — fail-soft: az elemzés nem pótolhatatlan
        _log.warning("FIGYELEM: az AI-elemzés elhasalt (%s) — az előző elemzes.json marad.", e)
        return 2
    art = valasz_to_artefakt(ai_valasz, payload, nap=nap, modell=MODELL, mode=mode)
    szoveg = json.dumps(art, ensure_ascii=False, indent=0)
    elemzesek_dir = docs_data / "elemzesek"
    elemzesek_dir.mkdir(exist_ok=True)
    seged.atomi_ir_szoveg(elemzesek_dir / f"{nap}.json", szoveg)
    seged.atomi_ir_szoveg(docs_data / "elemzes.json", szoveg)
    _index_frissit(elemzesek_dir, nap)
    return 0
```

3d. `main` (elemzo.py:483) — `ELEMZES_MODE` + `elemzes_orzo.elemzes_nap`:
```python
def main():
    import os
    mode = os.environ.get("ELEMZES_MODE", "este")
    nap = os.environ.get("ELEMZES_NAP") or elemzes_orzo.elemzes_nap(mode, seged.most_utc())
    docs_data = Path(__file__).resolve().parent.parent / "docs" / "data"
    return futtat(docs_data, nap=nap, mode=mode)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest -p no:xdist tests/test_elemzo.py -q`
Expected: PASS (a 4 új + minden meglévő; a meglévő `test_artefakt_*` az esti ágra érvényes, most `mode` default "este" → változatlan viselkedés + új `mode` mező).

- [ ] **Step 5: Full suite + commit**

```bash
.venv/bin/python -m pytest -p no:xdist -q
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "feat(elemzo): reggeli scoped artefakt (helyőrzők + mode mező) + futtat/main mód-bekötés

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN"
```

---

### Task 4: `.github/workflows/elemzes.yml` — kettős trigger + mód-levezetés + őr

Az elemzés mindkét gyűjtő-workflow-ra fusson, a `workflow_run.name`-ből módot vezessen le, és az idempotencia-őr hagyja ki a backup-újraindításokat.

**Files:**
- Modify: `.github/workflows/elemzes.yml`

**Interfaces:**
- Consumes: `python -m trendfigyelo.elemzes_orzo --mode <reggel|este> docs/data` (Task 1); `ELEMZES_MODE` env (Task 3 `main` olvassa).
- Produces: —

- [ ] **Step 1: Módosítsd a triggert (a fájl `on:` blokkja)**

Cseréld a `workflows:` sort mindkét gyűjtő-workflow nevére:
```yaml
on:
  workflow_run:
    workflows: ["Napi trendgyűjtés", "Reggeli felkapott-gyűjtés"]   # esti (teljes) + reggeli (scoped)
    types: [completed]
  workflow_dispatch: {}                # kézi teszt (default mód: este)
```

- [ ] **Step 2: Adj hozzá egy mód+őr lépést a „Függőségek telepítése" UTÁN, az „Elemzés futtatása" ELÉ**

```yaml
      - name: "Mód + idempotencia-őr (reggel scoped / este teljes; backup-újraindítás kihagyása)"
        id: guard
        shell: bash
        run: |
          NEV="${{ github.event.workflow_run.name }}"
          if [ "$NEV" = "Reggeli felkapott-gyűjtés" ]; then MODE=reggel; else MODE=este; fi
          echo "mode=$MODE" >> "$GITHUB_OUTPUT"
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            echo "Kézi (workflow_dispatch) futás — az őr nem aktív, elemzünk."
            echo "skip=false" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          skip="$(python -m trendfigyelo.elemzes_orzo --mode $MODE docs/data)"
          echo "Elemzés mód=$MODE — ma már kész? skip=$skip"
          echo "skip=$skip" >> "$GITHUB_OUTPUT"
```

- [ ] **Step 3: Kösd be a módot + az őrt az „Elemzés futtatása" és a commit lépésbe**

Az „Elemzés futtatása" lépés kapjon `if`-et és `ELEMZES_MODE` env-et:
```yaml
      - name: Elemzés futtatása
        if: steps.guard.outputs.skip != 'true'
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          ELEMZES_MODE: ${{ steps.guard.outputs.mode }}
        run: |
          set -o pipefail
          python elemzes.py 2>&1 | tee elemzes.log
```
A commit lépés `if`-jét bővítsd az őrrel:
```yaml
      - name: Változások commitolása (CSAK az elemzés-fájlok, KÜLÖN commit)
        if: always() && github.ref == 'refs/heads/main' && steps.guard.outputs.skip != 'true'
```
(Az „Artefakt" lépés `if: always()` marad — a logot skip esetén is töltse fel.)

- [ ] **Step 4: Validáld a YAML-t**

Run: `.venv/bin/python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/elemzes.yml')); print('YAML OK')"`
Expected: `YAML OK`. Emellett szemrevételezd: az őr-lépés a `pip install` UTÁN van (a `trendfigyelo` importálható), a `guard` id egyedi, a `steps.guard.outputs.{mode,skip}` hivatkozások helyesek.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/elemzes.yml
git commit -m "feat(elemzes-wf): kettős trigger (reggeli+esti) + mód-levezetés + idempotencia-őr

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN"
```

---

### Task 5: `e2e/elemzes.spec.js` — reggeli artefakt renderelése (frontend-változás NÉLKÜL)

Karakterizációs e2e: a reggeli (scoped) artefakt helyesen renderel a MEGLÉVŐ frontenddel — a reggeli AI-bekezdés látszik, a deferrált szekciók a helyőrző-prózát mutatják, nincs YouTube-blokk, a kulcsszó VALÓS csempék megmaradnak. Ha zöld első futásra, az igazolja: nem kell frontend-kód.

**Files:**
- Modify: `e2e/elemzes.spec.js`

**Interfaces:**
- Consumes: a reggeli artefakt alakja (Task 3): `mode:"reggel"`, `felkapott.reggel` valós, a többi próza `_ESTI_FRISSUL`, nincs `youtube` kulcs.
- Produces: —

- [ ] **Step 1: Write the test (a fájl végére)**

```javascript
const REGGELI_FIXTURE = {
  frissitve: "2026-09-03T07:10:00+00:00", modell: "claude-opus-4-8", nap: "2026-09-03", mode: "reggel",
  valtozas: { diff: { van_elozo: true, irany_valtok: [], mozgok: [], felkapott_uj: [], felkapott_eltunt: [] },
              szoveg: "Ez a rész az esti futáskor (21:00) frissül." },
  kulcsszavak: { szamok: [{ szo: "állás", irany: "emelkedik", mai_ertek: 10, csucs: 100 }],
                 napi: { szoveg: "Ez a rész az esti futáskor (21:00) frissül." },
                 teljes_kep: { szoveg: "Ez a rész az esti futáskor (21:00) frissül." },
                 het: { szoveg: "Ez a rész az esti futáskor (21:00) frissül." } },
  felkapott: { top: [{ kifejezes: "eső", volumen: "20000" }],
               reggel_top: [{ kifejezes: "eső" }], este_top: [], reggel_este_diff: { uj_estere: [], eltunt_estere: [], megmaradt: [] },
               reggel: { szoveg: "Reggel a legpörgőbb keresés az eső." },
               este: { szoveg: "Ez a rész az esti futáskor (21:00) frissül." },
               teljes_nap: { szoveg: "Ez a rész az esti futáskor (21:00) frissül." },
               het: { szoveg: "Ez a rész az esti futáskor (21:00) frissül." },
               het_valos: { napok: 3, visszateroek: [] } },
};

test("Elemzés — reggeli scoped artefakt: reggeli bekezdés + „frissül este" helyőrzők + nincs YouTube", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: REGGELI_FIXTURE }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  // a reggeli felkapott bekezdés valós AI-szöveget mutat
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — reggeli (9:00)")) .elemzes-szoveg'))
    .toContainText("a legpörgőbb keresés az eső");
  // a deferrált esti felkapott a helyőrzőt mutatja
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — esti (21:00)")) .elemzes-szoveg'))
    .toContainText("az esti futáskor (21:00) frissül");
  // a kulcsszó-próza is deferrált
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Kulcsszavak — mit látunk ma")) .elemzes-szoveg'))
    .toContainText("az esti futáskor (21:00) frissül");
  // a kulcsszó VALÓS csempe megmarad (tény, nem elemzés)
  await expect(page.locator(".elemzes-csempe")).toContainText("állás");
  // reggel NINCS YouTube-blokk
  await expect(page.locator("#youtube-szegmens")).toHaveCount(0);
});
```

- [ ] **Step 2: Run the test**

Run: `npx playwright test --workers=1 elemzes.spec.js -g "reggeli scoped"`
Expected: PASS első futásra (a frontend a helyőrzőket a meglévő `szekcio_elem`-mel rendereli, a `youtube` kulcs hiánya fail-soft). Ha BÁRMELYIK assert bukik, az a meglévő frontend hiányos kezelése — akkor STOP és jelezd (a spec szerint nem várt frontend-változás); ne módosíts vakon.

- [ ] **Step 3: Full Playwright + pytest, majd commit**

```bash
npx playwright test --workers=1
.venv/bin/python -m pytest -p no:xdist -q
git add e2e/elemzes.spec.js
git commit -m "test(e2e): reggeli scoped elemzés-artefakt renderelése (helyőrzők + nincs YouTube)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN"
```

---

## Önellenőrzés (terv ↔ spec)

- **Spec-lefedettség:** flash-fix logikai nap + idempotencia → Task 1; mód-tudatos AI-hívás (payload/séma/prompt) → Task 2; reggeli scoped artefakt + helyőrzők + `mode` mező + `main` bekötés → Task 3; kettős trigger + mód-levezetés + őr → Task 4; frontend graceful render (nincs kód-változás) igazolása → Task 5. A „primary esti bukott → éjfél-utáni backup az előző napot teljessé upgrade-eli" eset a `elemzes_mar_kesz` este-ágából (mode!="este" → fut) következik, Task 1 tesztje (`este_reggeli_letezo_false_upgradel`) fedi.
- **Placeholder-scan:** a Task 1 első teszt-blokkjában egy szándékos „placeholder replaced below" sor van, amit a rá következő végleges kódblokk VÁLT KI — az implementer a végleges assertet írja (`== "2026-09-03"`); minden más lépés konkrét kód.
- **Típus-konzisztencia:** `mode` string („reggel"/„este") végig; `elemzes_nap(mode, most)`/`elemzes_mar_kesz(docs_data, nap, mode)` (Task 1) ↔ CLI (Task 4) ↔ `main` (Task 3); `epit_payload(...,mode=)`/`_valasz_sema(...,mode=)`/`_rendszer_prompt(mode)`/`elemez(...,mode=)`/`uzenet(...,mode=)` (Task 2) ↔ `futtat(...,mode=)`/`valasz_to_artefakt(...,mode=)` (Task 3); `_ESTI_FRISSUL` egyetlen forrás (Task 3) ↔ a pontos string a Task 5 fixture-ben és a Global Constraintsban azonos. A `KamuKliens.uzenet(payload, modell, mode="este")` a Task 2-ben frissül, a Task 3 `futtat` ezen át hívja.

## Amit NEM csinálunk (YAGNI)

- Reggel NINCS nap-diff / „mi változott" próza (user-döntés: csak a reggeli felkapott; a `valtozas.szoveg` deferrált).
- Reggel az AI NEM kap teljes sémát „eldobandó" szekciókkal (szűkített séma → olcsóbb, tisztább).
- Nincs `docs/js/elemzes.js` kód-változás (a helyőrzők a meglévő renderrel jelennek meg; Task 5 igazolja).
- Nincs külön reggeli elemzés-fájl — ugyanaz a `elemzes.json` + `elemzesek/<nap>.json`, az esti felülírja a reggelit (szándékos scoped→teljes).
