# Elemzés-narratíva átalakítás (esti) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Az Elemzések oldal esti narratívája letisztultabb és tagoltabb legyen (csoport-címek, sorrend, törölt szekciók), az AI a felkapott szavak „miértjét" csak hír megléte esetén írja le, minden követett kulcsszó szóba kerüljön, és rövid gondolatjelet használjon.

**Architecture:** A VALÓS számokat továbbra is Python számolja, az AI csak narratívát ír. A séma (`_valasz_sema`) szűkül (kevesebb szekció), az artefakt (`valasz_to_artefakt`) ehhez igazodik, egy determinisztikus gondolatjel-csere fut az AI-válaszon, a prompt kap három új/módosított szabályt, a frontend render (`elemzes.js`) pedig átrendezi és átcímkézi a szekciókat. A payload adat-előkészítői (`_kulcsszo_het`, `_youtube_het`) VÁLTOZATLANOK maradnak.

**Tech Stack:** Python 3 (pytest, `-p no:xdist`), vanilla JS + Chart.js, Playwright (`--workers=1`).

**Spec:** `docs/superpowers/specs/2026-09-04-elemzes-narrativa-atalakitas-design.md`

## Global Constraints

- SOROS suite: `.venv/bin/python -m pytest -p no:xdist -q` és `npx playwright test --workers=1`.
- MUTÁCIÓ=1 per commit; TDD valódi RED→GREEN.
- `git add` KIZÁRÓLAG névvel; a gyökér `ATADAS-2026-08-18.txt` SOHA nem staged.
- Commit-trailerek MINDEN commitra:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN`
- Gondolatjel: rövid `–` (U+2013, en dash); a hosszú `—` (U+2014, em dash) tilos a KIMENETBEN (az AI-válaszban és a statikus címekben). A prompt-SZÖVEG maga tartalmazhat `—`-t (az utasítás, nem kimenet).
- Ág: `feat/elemzes-narrativa-atalakitas` (már létrehozva, a spec rajta van).
- Frontend: nincs `new Date()`/`Date.now()`. Backend tesztelt logikában nincs argnélküli `datetime.now()`.

---

### Task 1: Backend — séma + artefakt szűkítése

A `kulcsszavak` szekcióból kiesik a `teljes_kep` és `het`; a `youtube` szekcióból a `het`. Az artefakt ehhez igazodik (a `youtube` már `het_valos`-t sem visz). A payload-építő (`epit_payload`, `_kulcsszo_het`, `_youtube_het`) VÁLTOZATLAN.

**Files:**
- Modify: `trendfigyelo/elemzo.py` (`_valasz_sema` ~338–362; `valasz_to_artefakt` reggeli ág ~394–411, esti kulcsszavak ~434–439, youtube ~452–459)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Produces: `_valasz_sema(youtube, mode)` — esti `kulcsszavak.required == ["napi"]`, `youtube.required == ["napi","teljes_kep"]`; reggeli séma változatlan.
- Produces: `valasz_to_artefakt(...)` — esti `art["kulcsszavak"] == {szamok, napi}`; `art["youtube"] == {szamok, napi, teljes_kep}` (nincs `het`, nincs `het_valos`); reggeli `art["kulcsszavak"] == {szamok, napi}`.
- Consumes: a meglévő `_ai_valasz()` / `_ai_valasz_youtubebal()` fake-ek (kulcsszavak/youtube extra kulcsai inertek maradnak).

- [ ] **Step 1: Írd meg a bukó teszteket** — `tests/test_elemzo.py`

Cseréld le a meglévő `test_valasz_sema_youtube_szekcio_szigoru`-t, és add hozzá az új kulcsszavak-séma tesztet:

```python
def test_valasz_sema_youtube_szekcio_szigoru():
    s = elemzo._valasz_sema(youtube=True)
    assert "youtube" in s["required"]
    yt = s["properties"]["youtube"]
    assert yt["additionalProperties"] is False
    assert set(yt["required"]) == {"napi", "teljes_kep"}          # a 'het' KIESETT
    assert set(yt["properties"]) == {"napi", "teljes_kep"}
    assert set(yt["properties"]["napi"]["properties"]) == {"szoveg"}


def test_valasz_sema_kulcsszavak_csak_napi():
    s = elemzo._valasz_sema(mode="este")
    ks = s["properties"]["kulcsszavak"]
    assert ks["required"] == ["napi"]                             # teljes_kep/het KIESETT
    assert set(ks["properties"]) == {"napi"}
```

Cseréld le a `test_valasz_to_artefakt_youtube_blokk_valos_es_ai` végét (a `het`/`het_valos` már NINCS az artefaktban):

```python
def test_valasz_to_artefakt_youtube_blokk_valos_es_ai():
    payload = {
        "kulcsszavak": {"szamok": []},
        "felkapott": {"top": [], "reggel_top": [], "este_top": [],
                      "reggel_este_diff": {"uj_estere": [], "eltunt_estere": [], "megmaradt": []},
                      "het": {"napok": 0, "visszateroek": []}},
        "valtozas": {"irany_valtok": [], "mozgok": [], "felkapott_uj": [], "felkapott_eltunt": [], "van_elozo": False},
        "youtube": {"szamok": [{"szo": "szorongás", "domen": "egeszseg", "irany": "novekszik",
                                "meredekseg": 0.05, "ervenyes": True, "mai_ertek": 43, "csucs": 50, "atlag": 45.0}],
                    "het_valos": [{"szo": "bitcoin", "kezdo": 30, "veg": 57, "valtozas": 27}]},
    }
    art = elemzo.valasz_to_artefakt(_ai_valasz_youtubebal(), payload, nap="2026-08-26", modell="claude-opus-4-8")
    assert art["youtube"]["szamok"][0]["csucs"] == 50             # VALÓS a payloadból
    assert art["youtube"]["napi"]["szoveg"] == "yt-napi"          # AI-próza
    assert art["youtube"]["teljes_kep"]["szoveg"] == "yt-teljes"
    assert "het" not in art["youtube"]                            # a heti mozgás KIESETT
    assert "het_valos" not in art["youtube"]
```

Add hozzá egy artefakt-alak tesztet a kulcsszavakra:

```python
def test_valasz_to_artefakt_kulcsszavak_csak_szamok_es_napi():
    payload = _mini_payload(van_elozo=True)
    art = elemzo.valasz_to_artefakt(_mini_ai("napi"), payload, nap="2026-08-26", modell="m")
    assert set(art["kulcsszavak"]) == {"szamok", "napi"}          # teljes_kep/het KIESETT
    assert art["kulcsszavak"]["napi"]["szoveg"] == "sz"
```

- [ ] **Step 2: Futtasd — RED**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_elemzo.py -k "youtube_szekcio_szigoru or kulcsszavak_csak_napi or youtube_blokk_valos or kulcsszavak_csak_szamok"`
Expected: FAIL (a séma még tartalmazza a `het`/`teljes_kep`-et; az artefakt még beírja őket).

- [ ] **Step 3: Szűkítsd a sémát** — `elemzo.py::_valasz_sema` esti ág

Cseréld:

```python
    props = {
        "valtozas": sz,
        "kulcsszavak": {"type": "object", "additionalProperties": False,
                        "required": ["napi"],
                        "properties": {"napi": sz}},
        "felkapott": {"type": "object", "additionalProperties": False,
                      "required": ["reggel", "este", "teljes_nap", "het"],
                      "properties": {"reggel": sz, "este": sz, "teljes_nap": sz, "het": sz}},
    }
    required = ["valtozas", "kulcsszavak", "felkapott"]
    if youtube:
        props["youtube"] = {"type": "object", "additionalProperties": False,
                            "required": ["napi", "teljes_kep"],
                            "properties": {"napi": sz, "teljes_kep": sz}}
        required = required + ["youtube"]
```

- [ ] **Step 4: Igazítsd az artefaktot** — `elemzo.py::valasz_to_artefakt`

Esti ág `kulcsszavak`:

```python
        "kulcsszavak": {
            "szamok": payload["kulcsszavak"]["szamok"],
            "napi": ai_valasz["kulcsszavak"]["napi"],
        },
```

Esti ág `youtube` blokk (a `het_valos` és `het` kiesik):

```python
    if "youtube" in payload:
        art["youtube"] = {
            "szamok": payload["youtube"]["szamok"],
            "napi": ai_valasz["youtube"]["napi"],
            "teljes_kep": ai_valasz["youtube"]["teljes_kep"],
        }
```

Reggeli ág `kulcsszavak` (a helyőrző `teljes_kep`/`het` kiesik):

```python
            "kulcsszavak": {"szamok": payload["kulcsszavak"]["szamok"], "napi": d},
```

- [ ] **Step 5: Futtasd — GREEN (célzott)**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_elemzo.py -k "youtube_szekcio_szigoru or kulcsszavak_csak_napi or youtube_blokk_valos or kulcsszavak_csak_szamok"`
Expected: PASS.

- [ ] **Step 6: Teljes SOROS pytest**

Run: `.venv/bin/python -m pytest -p no:xdist -q`
Expected: PASS (a `_kulcsszo_het`/`_youtube_het`/payload-tesztek érintetlenek maradnak, mert a payload-építő nem változott).

- [ ] **Step 7: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "$(cat <<'EOF'
feat(elemzo): a kulcsszó teljes_kép/1_hét és a YouTube heti mozgás szekció kivezetése

A _valasz_sema esti ága a kulcsszavaknál már csak `napi`-t kér, a youtube-nál
`napi`+`teljes_kep`-et (a `het` kiesik). A valasz_to_artefakt ehhez igazodik: a
youtube artefakt nem visz `het`/`het_valos`-t, a kulcsszavak `{szamok,napi}`.
A payload-építő (epit_payload/_kulcsszo_het/_youtube_het) VÁLTOZATLAN.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 2: Backend — determinisztikus gondolatjel-csere

Az AI-válasz minden szöveg-mezőjében a hosszú `—` (U+2014) → rövid `–` (U+2013). Ez a promptszabály (Task 3) melletti garancia.

**Files:**
- Modify: `trendfigyelo/elemzo.py` (új `_gondolatjel_rovidit`; hívás a `valasz_to_artefakt` elején)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Produces: `_gondolatjel_rovidit(x)` — rekurzívan bejár dict/list/str szerkezetet, minden `str`-ben `"—"` → `"–"`, minden mást változatlanul ad vissza.
- Módosítja: `valasz_to_artefakt` — az első sorban `ai_valasz = _gondolatjel_rovidit(ai_valasz)`.

- [ ] **Step 1: Írd meg a bukó tesztet** — `tests/test_elemzo.py`

```python
def test_gondolatjel_rovidit_rekurziv():
    be = {"a": "egy — kettő", "b": {"c": "x—y"}, "d": ["p—q", 3, None]}
    ki = elemzo._gondolatjel_rovidit(be)
    assert ki == {"a": "egy – kettő", "b": {"c": "x–y"}, "d": ["p–q", 3, None]}


def test_artefakt_hosszu_gondolatjel_rovidre_valt():
    payload = _mini_payload(van_elozo=True)
    ai = _mini_ai("Ma — röviden — ez történt.")
    art = elemzo.valasz_to_artefakt(ai, payload, nap="2026-08-26", modell="m")
    assert "—" not in art["valtozas"]["szoveg"]
    assert art["valtozas"]["szoveg"] == "Ma – röviden – ez történt."
```

- [ ] **Step 2: Futtasd — RED**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_elemzo.py -k "gondolatjel or hosszu_gondolatjel"`
Expected: FAIL (`_gondolatjel_rovidit` nincs definiálva; az artefakt-szöveg még `—`-t tartalmaz).

- [ ] **Step 3: Implementáld** — `elemzo.py`

Add hozzá a segédet (pl. a `valasz_to_artefakt` fölé):

```python
def _gondolatjel_rovidit(x):
    """Az AI-szövegben a hosszú gondolatjelet (—, U+2014) rövidre (–, U+2013) cseréli
    (item 3, 2026-09-04). Rekurzívan bejárja a válasz-struktúrát; csak string-leveleket érint."""
    if isinstance(x, str):
        return x.replace("—", "–")
    if isinstance(x, dict):
        return {k: _gondolatjel_rovidit(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_gondolatjel_rovidit(v) for v in x]
    return x
```

A `valasz_to_artefakt` első sora:

```python
def valasz_to_artefakt(ai_valasz, payload, nap, modell, mode="este"):
    ai_valasz = _gondolatjel_rovidit(ai_valasz)
    fk = payload["felkapott"]
```

- [ ] **Step 4: Futtasd — GREEN (célzott)**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_elemzo.py -k "gondolatjel or hosszu_gondolatjel"`
Expected: PASS.

- [ ] **Step 5: Teljes SOROS pytest**

Run: `.venv/bin/python -m pytest -p no:xdist -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "$(cat <<'EOF'
feat(elemzo): determinisztikus hosszú→rövid gondolatjel-csere az AI-válaszban

A valasz_to_artefakt a válasz minden szöveg-mezőjében a — (U+2014) jelet – (U+2013)
jelre cseréli (item 3) — a promptszabály melletti garancia.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 3: Backend — prompt-szabályok (item 6, 2, 3)

A `RENDSZER_PROMPT` (5) grounded-only „miért", (8) teljesebb lefedettség, új (10) gondolatjel; a `_RENDSZER_PROMPT_REGGEL` grounded-only „miért" + gondolatjel-szabály.

**Files:**
- Modify: `trendfigyelo/elemzo.py` (`RENDSZER_PROMPT` ~23–58; `_RENDSZER_PROMPT_REGGEL` ~60–76)
- Test: `tests/test_elemzo.py`

**Interfaces:**
- Produces: `RENDSZER_PROMPT` tartalmazza: `"tényleg érkezett hír"`, `"okot, magyarázatot, hátteret akkor SEM találsz ki"`, `"MINDEN követett kulcsszó legalább egyszer"`, `"SOHA nem a hosszú"`.
- Produces: `_RENDSZER_PROMPT_REGGEL` tartalmazza: `"tényleg érkezett hír"`, `"soha nem a hosszú"`.
- A meglévő invariánsok (folyó bekezdés, payload/mező-tiltás, 4 felkapott-bekezdés) VÁLTOZATLANOK.

- [ ] **Step 1: Írd meg a bukó teszteket** — `tests/test_elemzo.py`

```python
def test_rendszer_prompt_grounded_miert():
    p = elemzo.RENDSZER_PROMPT
    assert "tényleg érkezett hír" in p
    assert "okot, magyarázatot, hátteret akkor SEM találsz ki" in p


def test_rendszer_prompt_teljesebb_lefedettseg():
    assert "MINDEN követett kulcsszó legalább egyszer" in elemzo.RENDSZER_PROMPT


def test_rendszer_prompt_rovid_gondolatjel_szabaly():
    assert "SOHA nem a hosszú" in elemzo.RENDSZER_PROMPT


def test_rendszer_prompt_reggel_grounded_es_gondolatjel():
    r = elemzo._RENDSZER_PROMPT_REGGEL
    assert "tényleg érkezett hír" in r
    assert "soha nem a hosszú" in r
```

- [ ] **Step 2: Futtasd — RED**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_elemzo.py -k "grounded or teljesebb_lefedettseg or rovid_gondolatjel or reggel_grounded"`
Expected: FAIL.

- [ ] **Step 3: Szerkeszd a promptot** — `elemzo.py`

A `RENDSZER_PROMPT`-ban cseréld az (5) szabályt:

```python
    "(5) A felkapott (napi trend) szó mögötti OKOT vagy hátteret KIZÁRÓLAG akkor írod le, ha "
    "ahhoz a konkrét szóhoz tényleg érkezett hír a bemenetben; ilyenkor a hír tartalmát természetes "
    "mondattal, a forrásra utalva foglalod össze. Ha egy felkapott szóhoz NINCS hír, csak azt írod le, "
    "hogy felkapott — okot, magyarázatot, hátteret akkor SEM találsz ki, még óvatos formában sem. "
    "Hírt, forrást, eseményt sosem találsz ki. "
```

cseréld a (8) szabályt:

```python
    "(8) Ahol egy szó MAI értéke érdemben eltér a saját szokásos (átlagos) szintjétől, azt "
    "emeld ki természetes szavakkal (pl. „a szokásosnál jóval élénkebb\", „a megszokott "
    "szintje alatt van\") — ez a lényegi „önmagához képest\" olvasat. TÖREKEDJ rá, hogy MINDEN "
    "követett kulcsszó legalább egyszer szóba kerüljön: a szembetűnő eltéréseket külön kiemeled, "
    "a szokásos szintjükön állókat néhány szóval, akár csoportosítva összefoglalod — de egyetlen "
    "követett szó se maradjon ki teljesen. A „szokásos szint\" a szó SAJÁT átlaga, NEM a szavak "
    "közötti összevetés; ez a Google- és a YouTube-szavakra egyaránt vonatkozik. "
```

és a (9) szabály UTÁN, a záró `)` ELŐTT told be a (10)-et (a (9) utolsó szövegdarabja `"...nem találsz ki."`-re végződik — utána új literál):

```python
    "(10) Gondolatjelként MINDIG a rövid „–\" jelet használod, SOHA nem a hosszú „—\" jelet."
```

A `_RENDSZER_PROMPT_REGGEL`-ben cseréld az (5) szabályt:

```python
    "(5) A felkapott szó mögötti OKOT kizárólag akkor írod le, ha ahhoz a konkrét szóhoz tényleg "
    "érkezett hír; ilyenkor a hír tartalmát a forrásra utalva foglalod össze. Ha nincs hír egy szóhoz, "
    "csak annyit írsz, hogy felkapott — okot akkor SEM találsz ki. Hírt, forrást, eseményt sosem találsz ki. "
```

és a záró `)` ELŐTT (a `"...azzal most nem foglalkozol."` után) told be a gondolatjel-szabályt — figyelj, a `foglalkozol.` végére kell egy szóköz, majd az új literál:

```python
    "a mai esti futás fogja elemezni, azzal most nem foglalkozol. "
    "(7) Gondolatjelként mindig a rövid „–\", soha nem a hosszú „—\"."
```

- [ ] **Step 4: Futtasd — GREEN (célzott)**

Run: `.venv/bin/python -m pytest -p no:xdist -q tests/test_elemzo.py -k "grounded or teljesebb_lefedettseg or rovid_gondolatjel or reggel_grounded"`
Expected: PASS.

- [ ] **Step 5: Teljes SOROS pytest**

Run: `.venv/bin/python -m pytest -p no:xdist -q`
Expected: PASS (a `test_rendszer_prompt_reggel_csak_reggeli_pillanatkep`, a folyó-próza és a youtube-keret invariáns-tesztek is zöldek maradnak).

- [ ] **Step 6: Commit**

```bash
git add trendfigyelo/elemzo.py tests/test_elemzo.py
git commit -m "$(cat <<'EOF'
feat(elemzo): grounded-only „miért" + teljesebb kulcsszó-lefedettség + rövid gondolatjel a promptban

(5) a felkapott szó okát csak akkor írja le az AI, ha ahhoz a szóhoz tényleg
érkezett hír (item 6); (8) minden követett kulcsszó legalább egyszer szóba
kerül (item 2); (10) rövid gondolatjel (item 3). A reggeli prompt is kapja a
grounded-only és a gondolatjel-szabályt.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

### Task 4: Frontend — render átrendezése + csoport-címek + YouTube átnevezés

Az `elemzes.js` render: Google szegmens csoport-címekkel, `mit látunk ma` → `Mi változott ma?` sorrend, a `teljes kép`/`1 hét` és a YouTube `heti mozgás` szekció render nélkül, a YouTube nyítóblokk átnevezve, minden statikus címben és a fejlécben rövid gondolatjel.

**Files:**
- Modify: `docs/js/elemzes.js` (`rajzol` ~82–133; `youtube_szegmens` ~71–79; `elemzes_indit` hibaág fejléc)
- Modify: `docs/css/app.css` (új `.elemzes-csoport-cim`)
- Test: `e2e/elemzes.spec.js`

**Interfaces:**
- Produces: `csoport_cim(szoveg)` → `<h3 class="elemzes-csoport-cim">` (nem `.elemzes-szekcio`-n belül).
- A szekció-h3 címek: `Kulcsszavak – mit látunk ma`, `Reggeli (9:00)`, `Esti (21:00)`, `A nap íve`, `Heti összesítés`, `Napi` (régi ág), `YouTube – mai videós érdeklődés`, `YouTube – teljes kép` — mind rövid `–`.

- [ ] **Step 1: Írd meg / frissítsd a bukó teszteket** — `e2e/elemzes.spec.js`

**(a)** Az első teszt (`folyó próza … VALÓS csempe/diff-réteg NEM jelenik meg`) — cseréld az em-dashes címet en-dashre, és told be a sorrend + csoport-cím + törölt-szekció + gondolatjel őröket. A meglévő csempe-hiány asszertek maradnak. A `Kulcsszavak — mit látunk ma` locator legyen `Kulcsszavak – mit látunk ma`. Add hozzá a teszt VÉGÉHEZ:

```javascript
  // ÚJ szerkezet (2026-09-04): sorrend, csoport-címek, törölt szekciók, rövid gondolatjel
  await expect(page.locator(".elemzes-csoport-cim")).toHaveText([
    "Google kulcsszavak", "Google napi friss keresőszavak"]);
  // „mit látunk ma" a „Mi változott ma?" ELŐTT
  const cimek = await page.locator("#elemzes-tartalom h3").allTextContents();
  expect(cimek.indexOf("Kulcsszavak – mit látunk ma")).toBeLessThan(cimek.indexOf("Mi változott ma?"));
  // törölt kulcsszó-szekciók
  await expect(page.locator('h3:text-is("Kulcsszavak – teljes kép")')).toHaveCount(0);
  await expect(page.locator('h3:text-is("Kulcsszavak – 1 hét")')).toHaveCount(0);
  // rövid gondolatjel: sehol nincs hosszú „—"
  await expect(page.locator("#elemzes-tartalom")).not.toContainText("—");
```

**(b)** A `két nevesített szegmens + 3 YouTube-szekció …` teszt — a YouTube most 2 szekció, új nyítócím, nincs heti mozgás:

```javascript
test("Elemzés: két nevesített szegmens + 2 YouTube-szekció, ha van youtube blokk (heti mozgás nélkül)", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: FIXTURE_YT }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator("h2.elemzes-szegmens")).toHaveText([
    "Google keresések napi elemzése", "YouTube keresések napi elemzése"]);
  await expect(page.locator("#youtube-szegmens .elemzes-csempe")).toHaveCount(0);
  // ÚJ: nyítóblokk átnevezve, teljes kép marad, heti mozgás KIESETT → 2 szekció
  await expect(page.locator("#youtube-szegmens .elemzes-szekcio")).toHaveCount(2);
  await expect(page.locator('#youtube-szegmens h3:text-is("YouTube – mai videós érdeklődés")')).toHaveCount(1);
  await expect(page.locator('#youtube-szegmens h3:text-is("YouTube – teljes kép")')).toHaveCount(1);
  await expect(page.locator('#youtube-szegmens h3:text-is("YouTube – heti mozgás")')).toHaveCount(0);
  await expect(page.locator("#youtube-szegmens")).toContainText("YouTube napi próza.");
});
```

**(c)** A `ÚJ felkapott 4 szekció` teszt — a felkapott címek prefix nélkül, rövid gondolatjel:

```javascript
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Reggeli (9:00)")) .elemzes-szoveg')).toHaveText("reggeli próza");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Esti (21:00)")) .elemzes-szoveg')).toHaveText("esti próza");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("A nap íve")) .elemzes-szoveg')).toHaveText("a nap íve próza");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Heti összesítés")) .elemzes-szoveg')).toHaveText("heti próza");
  await expect(page.locator('h3:text-is("Napi")')).toHaveCount(0);
```

**(d)** A `RÉGI felkapott {napi,het}` teszt:

```javascript
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Napi")) .elemzes-szoveg')).toHaveText("régi napi");
  await expect(page.locator('h3:text-is("Reggeli (9:00)")')).toHaveCount(0);
```

**(e)** A `reggeli scoped artefakt` teszt — a felkapott címek prefix nélkül:

```javascript
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Reggeli (9:00)")) .elemzes-szoveg'))
    .toContainText("a legpörgőbb keresés az eső");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Esti (21:00)")) .elemzes-szoveg'))
    .toContainText("az esti futáskor (21:00) frissül");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Kulcsszavak – mit látunk ma")) .elemzes-szoveg'))
    .toContainText("az esti futáskor (21:00) frissül");
```

(Az első teszt `Kulcsszavak — mit látunk ma` → `Kulcsszavak – mit látunk ma` locatorját is cseréld a 26. sor körül.)

- [ ] **Step 2: Futtasd — RED**

Run: `npx playwright test e2e/elemzes.spec.js --workers=1`
Expected: FAIL (a régi render em-dashos címeket és a törölt szekciókat adja; nincs csoport-cím).

- [ ] **Step 3: Írd át a rendert** — `docs/js/elemzes.js`

Új segéd (a `szegmens_cim` mellé):

```javascript
// csoport-fejléc a szegmensen belül (a szegmens-h2 és a szekció-h3-ak között)
function csoport_cim(szoveg) {
  const h = document.createElement("h3");
  h.className = "elemzes-csoport-cim";
  h.textContent = szoveg;
  return h;
}
```

`youtube_szegmens`:

```javascript
function youtube_szegmens(yt) {
  const box = document.createElement("section");
  box.id = "youtube-szegmens";
  box.appendChild(szegmens_cim("YouTube keresések napi elemzése"));
  box.appendChild(szekcio_elem("YouTube – mai videós érdeklődés", yt.napi));
  box.appendChild(szekcio_elem("YouTube – teljes kép", yt.teljes_kep));
  return box;
}
```

`rajzol` (a fejléctől lefelé):

```javascript
function rajzol(art) {
  const t = document.getElementById("elemzes-tartalom");
  t.textContent = "";
  document.getElementById("elemzes-fejlec").textContent =
    `Elemzés – ${art.nap} (${art.modell})`;

  t.appendChild(szegmens_cim("Google keresések napi elemzése"));

  // „Google kulcsszavak" — a mi választott szavaink (napi kép, majd napi változás)
  t.appendChild(csoport_cim("Google kulcsszavak"));
  t.appendChild(szekcio_elem("Kulcsszavak – mit látunk ma", art.kulcsszavak.napi));
  t.appendChild(szekcio_elem("Mi változott ma?", art.valtozas));

  // „Google napi friss keresőszavak" — a napi felkapott keresések
  t.appendChild(csoport_cim("Google napi friss keresőszavak"));
  if (art.felkapott.reggel) {
    t.appendChild(szekcio_elem("Reggeli (9:00)", art.felkapott.reggel));
    t.appendChild(szekcio_elem("Esti (21:00)", art.felkapott.este));
    t.appendChild(szekcio_elem("A nap íve", art.felkapott.teljes_nap));
    t.appendChild(szekcio_elem("Heti összesítés", art.felkapott.het));
  } else {
    t.appendChild(szekcio_elem("Napi", art.felkapott.napi));
    t.appendChild(szekcio_elem("Heti összesítés", art.felkapott.het));
  }

  // YouTube-szegmens — fail-soft: régi archív-nap (nincs art.youtube) → nincs YouTube-rész
  if (art.youtube) t.appendChild(youtube_szegmens(art.youtube));
}
```

Az `elemzes_indit` hibaágában a fejléc em-dashát is cseréld:

```javascript
    document.getElementById("elemzes-fejlec").textContent = "Elemzés – nem érhető el";
```

- [ ] **Step 4: Add hozzá a CSS-t** — `docs/css/app.css`

Az „Elemzés" fül blokkjához (a `.elemzes-szekcio` szabályok mellé):

```css
.elemzes-csoport-cim { font-size: 1.25rem; font-weight: 700; color: #111; margin: 1.75rem 0 .75rem; }
```

- [ ] **Step 5: Futtasd — GREEN (elemzés spec)**

Run: `npx playwright test e2e/elemzes.spec.js --workers=1`
Expected: PASS.

- [ ] **Step 6: Teljes SOROS suite (mindkettő)**

Run: `.venv/bin/python -m pytest -p no:xdist -q` és `npx playwright test --workers=1`
Expected: PASS (a többi e2e — kulcsszo/mobil/attekinto — érintetlen; azok a Google/YouTube trend-fülre vonatkoznak).

- [ ] **Step 7: Commit**

```bash
git add docs/js/elemzes.js docs/css/app.css e2e/elemzes.spec.js
git commit -m "$(cat <<'EOF'
feat(elemzes-ful): esti narratíva átrendezése — csoport-címek, sorrend, YouTube átnevezés

Google szegmens: „Google kulcsszavak" (mit látunk ma → Mi változott ma?) és
„Google napi friss keresőszavak" (Reggeli/Esti/A nap íve/Heti) csoport-címek;
a teljes kép / 1 hét szekció kikerül. YouTube: „mai videós érdeklődés" + teljes
kép (heti mozgás nélkül). Minden statikus címben és a fejlécben rövid gondolatjel.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016pfLzktJiw3byeG3ng5bWN
EOF
)"
```

---

## Önellenőrzés (spec-lefedettség)

- **item 1 (elkülönítés címekkel):** Task 4 — `csoport_cim` + „Google kulcsszavak" / „Google napi friss keresőszavak".
- **item 2 (minden kulcsszó):** Task 3 — (8) szabály „MINDEN követett kulcsszó legalább egyszer".
- **item 3 (rövid gondolatjel):** Task 2 (determinisztikus csere) + Task 3 (prompt (10)/(7)) + Task 4 (statikus címek + fejléc + e2e őr).
- **item 4 (Google sorrend + törlés):** Task 1 (séma/artefakt) + Task 4 (render sorrend, törölt szekciók).
- **item 5 (YouTube átnevezés + heti törlés):** Task 1 (youtube séma/artefakt) + Task 4 (átnevezés, heti mozgás törlés).
- **item 6 (grounded „miért"):** Task 3 — (5) szabály mindkét promptban.

## Ruling-ök

- A payload adat-előkészítői (`_kulcsszo_het`, `_youtube_het`) és a payload `kulcsszo_het` / youtube `het_valos` mezői **maradnak** — a séma úgyis levágja a kimenetet, az extra bemenet inert; az eltávolítás fölöslegesen szélesítené a teszt-blast-radiust. Ha rossz: pár kbájt fölös payload — elhanyagolható.
- A törölt szekciók a régi archív artefaktokban maradnak; az új render nem olvassa őket → csendben nem jelennek meg (nincs törő hivatkozás).
