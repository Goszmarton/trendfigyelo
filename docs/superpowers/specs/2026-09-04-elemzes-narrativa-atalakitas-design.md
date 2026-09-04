# Elemzés-narratíva átalakítás (esti) — terv

**Dátum:** 2026-09-04
**Érinti:** `docs/js/elemzes.js`, `docs/css/app.css`, `trendfigyelo/elemzo.py`,
`tests/test_elemzo.py`, `e2e/elemzes.spec.js`
**Előzmény:** a VALÓS csempe-réteg eltávolítása (origin/main `160a8d1`) — erre épül.

## 1. Cél

Az Elemzések oldal esti narratívája legyen letisztultabb és világosabban tagolt,
plusz az AI a felkapott szavak „miértjét" csak akkor mondja el, ha tényleg van rá
hír (a mai ChatGPT-féle találgatás megszüntetése). Hat felhasználói kérés (item 1–6).

## 2. Végleges szerkezet (esti render)

**GOOGLE szegmens** — `h2: „Google keresések napi elemzése"`

- **Csoport-cím: „Google kulcsszavak"**
  1. `Kulcsszavak – mit látunk ma`  ← **ez lesz az első** (item 4)
  2. `Mi változott ma?`
  - törölve: `Kulcsszavak – teljes kép`, `Kulcsszavak – 1 hét` (item 4)
- **Csoport-cím: „Google napi friss keresőszavak"**
  3. `Reggeli (9:00)` · `Esti (21:00)` · `A nap íve` · `Heti összesítés`
     (a régi „Felkapott — …" prefix helyett; régi artefakt-alaknál: `Napi` · `Heti összesítés`)

**YOUTUBE szegmens** — `h2: „YouTube keresések napi elemzése"`
  1. `YouTube – mai videós érdeklődés`  ← átnevezve (item 5; volt „YouTube — mit néznek ma")
  2. `YouTube – teljes kép`  *(marad)*
  - törölve: `YouTube – heti mozgás` (item 5)

Minden gondolatjel a rövid `–` (item 3).

## 3. Részletes változások

### A) Frontend render — `docs/js/elemzes.js`

- Új segéd `csoport_cim(szoveg)` → `<h3 class="elemzes-csoport-cim">`.
- `rajzol` Google-rész: sorrend a fenti (2.) szerint; `Kulcsszavak – mit látunk ma`
  a `Mi változott ma?` **elé**; a `teljes_kep`/`het` szekció-render **törölve**;
  a két csoport-cím beszúrva.
- A felkapott szekció-címek prefix nélkül: `Reggeli (9:00)` / `Esti (21:00)` /
  `A nap íve` / `Heti összesítés` (régi ág: `Napi` / `Heti összesítés`).
- `youtube_szegmens`: az első szekció címe `YouTube – mai videós érdeklődés`;
  a `het` (heti mozgás) render **törölve**; `teljes kép` marad.
- A statikus címekben `—` → `–`.

### B) Backend séma — `elemzo.py::_valasz_sema` (esti ág)

- `kulcsszavak.properties`: csak `{napi}`; `required: ["napi"]`
  (a `teljes_kep`, `het` kikerül).
- `youtube.properties`: `{napi, teljes_kep}`; `required: ["napi","teljes_kep"]`
  (a `het` kikerül).
- `felkapott` és `valtozas`: változatlan. A **reggeli** séma: változatlan
  (csak `felkapott.reggel`).

### C) Backend artefakt — `elemzo.py::valasz_to_artefakt`

- Esti ág: `kulcsszavak` = `{szamok, napi}` (nincs `teljes_kep`/`het`);
  `youtube` = `{szamok, napi, teljes_kep}` (nincs `het`, és `het_valos` sem).
- Reggeli ág: a `teljes_kep`/`het` helyőrző mezők **kikerülnek** a `kulcsszavak`-ból
  (konzisztencia; a render úgyis csak `napi`-t olvas).
- **Determinisztikus gondolatjel-csere (item 3):** az AI-válasz minden szöveg-mezőjében
  `—` (U+2014) → `–` (U+2013), egy rekurzív segéddel (`_gondolatjel_rovidit`), a
  `valasz_to_artefakt` elején, MINDKÉT módban. Ez a promptszabály mellett garancia.

### D) Prompt — `elemzo.py`

- `RENDSZER_PROMPT` (esti):
  - **(5) item 6 — grounded-only „miért":** a felkapott szó mögötti OKOT csak akkor
    írd le, ha ahhoz a szóhoz **konkrét hír** érkezett; a hír tartalmát a forrásra
    utalva, természetesen foglald össze. Ha egy szóhoz nincs hír, csak annyit írj,
    hogy felkapott — okot akkor **SE** találj ki, óvatosan sem.
  - **(8) item 2 — teljesebb lefedettség:** törekedj rá, hogy **minden** követett
    kulcsszó legalább egyszer szóba kerüljön; a szembetűnő „önmagához képest"
    eltéréseket emeld ki, a nyugodt szinten állókat néhány szóval csoportosítva is
    összefoglalhatod.
  - **(10) item 3 — gondolatjel:** mindig a rövid `–`, SOHA a hosszú `—`.
- `_RENDSZER_PROMPT_REGGEL`: ugyanaz a grounded-only „miért" (5) és a gondolatjel-szabály.
  (A lefedettség/kulcsszó-rész reggel nem releváns — reggel csak felkapott.reggel.)

### E) CSS — `docs/css/app.css`

- `.elemzes-csoport-cim`: a szegmens-`h2` és a szekció-dobozok közötti csoport-fejléc
  (nagyobb térköz felül, vastag, semleges szín) — a többi szekciótól elkülönítve.

## 4. Visszafelé kompatibilitás

A **régi archivált artefaktok** (a change előttiek) tartalmazzák a `kulcsszavak.teljes_kep`,
`kulcsszavak.het`, `youtube.het` mezőket. Az új render ezeket **egyszerűen nem olvassa**,
így csendben nem jelennek meg — nincs hibás mezőhivatkozás, nincs összeomlás. A
`kulcsszavak.napi`, `valtozas`, `felkapott` minden régi alakban jelen van.

## 5. Tesztek

**`e2e/elemzes.spec.js`:**
- Új sorrend-őr: `Kulcsszavak – mit látunk ma` a `Mi változott ma?` **előtt**.
- Csoport-cím-őr: `.elemzes-csoport-cim` „Google kulcsszavak" és „Google napi friss keresőszavak".
- Törölt szekciók: `Kulcsszavak – teljes kép`, `Kulcsszavak – 1 hét`, `YouTube – heti mozgás`
  → `toHaveCount(0)`.
- YouTube átnevezés: `YouTube – mai videós érdeklődés` jelen; YouTube szekciók száma **2**.
- Felkapott címek: `Reggeli (9:00)` stb. (a „Felkapott — …" helyett) — a 4-szekciós,
  a régi-alak és a reggeli-scoped teszt is frissül.
- Gondolatjel-őr: `#elemzes-tartalom` szövege nem tartalmaz `—` (U+2014) karaktert.

**`tests/test_elemzo.py`:**
- `_valasz_sema` esti: `kulcsszavak` már nem követeli a `teljes_kep`/`het`-et;
  `youtube` már nem a `het`-et.
- `valasz_to_artefakt`: a kimenet `kulcsszavak`-ja `{szamok,napi}`; a `youtube`
  `{szamok,napi,teljes_kep}` — a fixture-kliensek (fake) az új, szűkebb alakot adják.
- Új teszt: gondolatjel-csere end-to-end (AI-válaszban `—` → artefaktban `–`).

## 6. Ruling-ök (hatókör-döntések)

- **A payload adat-előkészítő függvényeit NEM távolítjuk el** (`_kulcsszo_het`,
  `_youtube_het`) és a payload `kulcsszo_het` / youtube `het_valos` mezői **maradnak**.
  Miért: a séma vezérli a kimenetet, az extra bemeneti adat inert és olcsó; az
  eltávolításuk szélesíti a blast radius-t (saját tesztjeik) valós haszon nélkül.
  Ha rossz: néhány kbájt fölösleges payload — elhanyagolható.
- **A „miért" nem kap külön UI-elemet / forrás-megjelenítést** (item 6 = prózában marad).
- **Csak az Elemzések oldal változik**; a Google/YouTube trend-fülek (index.html,
  youtube.html) érintetlenek.

## 7. Hatókörön kívül (YAGNI)

- Hír-scraping vagy új adatforrás a „miérthez" — nem kell, a hír már a payloadban van.
- Heading-szintek átszervezése a csoport-`h3` hozzáadásán túl.
- A reggeli narratíva tartalmi bővítése (a reggeli „teljesen jó" — user).
