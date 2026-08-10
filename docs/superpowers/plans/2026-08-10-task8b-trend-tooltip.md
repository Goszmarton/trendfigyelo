# Task 8b — Trend napi görbe: interakció, tooltip, normalizálás-magyarázat

Státusz: TERV (jóváhagyásra vár). Untracked scratch — a munkamódszer szerint vagy
untracked marad, vagy egyetlen commitban a végén. Spec: §7.3 (08-08/09 patch), §1.4, §9 (Task 8b, dep 8a).

---

## 0. Kiindulás — MÉRT (2026-08-10, valós adat: `docs/data/legfrissebb.json`, 08-09 nap)

- **Adatalak:** 24 trend, **15 görbével** (mind 180 pont, **8 PERCES rács**, 23,9h span),
  9 üres idősor (D1-kiterjesztés). A rács NEM órás — ez a J3 kulcsszó-oldaltól (órás) ELTÉR.
- **LELET 2 igazolva a friss napon** — volumen-sávok a görbés (idosor van) trendek közt:
  `2000 → 6 trend`, `5000 → 5`, `10000 → 3`, `20000 → 1`. Egy sávon belül minden görbe a
  SAJÁT 100-jához skálázva (§1.4) → hasonló magasság, eltérő keresettség. Ez a magyarázat célpontja.
- **8a kód-állapot:** `trend_sparkline_letrehoz` (app.js:666): `tooltip:{enabled:false}`,
  `y:{display:false,min:0,max:100}`, `x:{display:false}`, `labels = idosor.map(idopont_utc)` (nyers ISO).
- **Kategória-magyarázat:** `trend_osszefoglalo_epit` (app.js:830) → `.kategoria-magyarazat` `<p>`,
  CSAK kategóriás napon (eloszlas.length>0). Tartalma a kategória-összegről szól, NEM a normalizálásról.
- **Elrendezés:** `#kulcsszo-blokk` (index.html:21) FENT, `#trend-blokk` (:33) LENT. Következmény: a
  trend doboz-magasság NEM tolja a kulcsszó-kártyákat → a lazy-render őr (kulcsszo.spec.js T11,
  rootMargin 400px IO) **strukturálisan érintetlen**. (Empirikusan is igazoljuk: suite zöld.)
- **Baseline (SOROS, mérvadó L12):** Playwright **56**, pytest **224**. Szinkron: `origin/main==HEAD`
  (b928794, éjszakai adat-commit rebase-elve).

## 0.1 Jóváhagyott rész-döntések (2026-08-10, felhasználó)

- **Q1** — normalizálás-magyarázat: BLOKK-SZINTŰ, a lista FÖLÉ; NE tapadjon a kategória-magyarázat alá
  (vizuális elválasztás); a szöveg KÉTFELŰ (mi nem / mi igen olvasható).
- **Q2** — 64px doboz: 8b-be, de mert a tooltip használhatósága a magasság függvénye → a magasság **MÉRT** érték.
- **Q3** — „több sparkline egy ábrán" (mikor csúcsosodtak): KIMARAD, külön kör.

---

## A. Tooltip a trend-sparkline-on

**Cél:** a 8a-ban szándékosan letiltott hover-tooltip bekapcsolása, a 8 perces rács adatához igazítva.

**A J3 kulcsszó-formátum NEM vehető át változtatás nélkül** (két mért ok): a J3 `labels` „dátum HH:MM"
formázott string ÉS a rács ÓRÁS; a trend `labels` nyers ISO ÉS a rács 8 PERCES. Külön formázás kell.

**Konfiguráció** (`trend_sparkline_letrehoz`):
- `plugins.tooltip.enabled: true` (a `false` helyett).
- `interaction: { mode: 'index', intersect: false }` — OSZLOPOS hover: bárhol a függőleges sávban a
  legközelebbi x-pont jelenik meg. Így a hover-célpont **x-alapú, a doboz-magasságtól FÜGGETLEN** →
  ez oldja fel a „közel lapos alapvonalon pontatlan a célzás" aggályt a hover x-tengelyén. (A magasság
  ezután a LÁTHATÓ olvashatóságot javítja, lásd C.)
- `pointHoverRadius: 3` (a `pointRadius:0` mellett) — a hoverelt pont láthatóvá válik.
- `tooltip.callbacks`:
  - `title`: az adott pont `idopont_utc`-jából `datum_formaz(iso.slice(0,10)) + " " + iso.slice(11,16)`
    → pl. `2026. 08. 09. 14:24`. **UTC**, konzisztensen a kulcsszó-oldallal (az is UTC-t mutat, nem
    konvertál helyi időre). Tudatos döntés, nem tz-bug.
  - `label`: `"érték: " + y + " / 100"` — a `/ 100` finoman jelzi az önnormalizálást (a részletes
    magyarázatot a B. blokk viszi, nem a tooltip — a tooltip tömör marad).

**Assertálhatóság (L9/J3-osztály, ELŐRE kimondva):** a tooltip canvas-belső, DOM-ból NEM assertálható.
A smoke NEM tudja ellenőrizni a tooltip helyességét — csak a data-* szerződést és a DOM-elemeket őrzi.
A tooltip helyessége **KÉZI szemle** (localhost:8000, valós 08-09 adat, több görbén). A terv ezt előre rögzíti.

## B. Normalizálás-magyarázat (LELET 2)

**Hely és feltétel:** `trend_blokk_render`-ben, KÜLÖN elem (`.trend-normalizalas-magyarazat`), a
`!mind_ures` ágon (= van legalább egy görbe), az összefoglaló UTÁN és a lista ELŐTT appendelve.
- Feltétele `!mind_ures` (van görbe), NEM `eloszlas.length>0` (van kategória) — a kettő KÜLÖNBÖZIK:
  archív napon van görbe, de nincs kategória → a magyarázat AKKOR IS kell. Mind-üres napon nincs görbe
  → nincs mit magyarázni, elmarad (a blokk-üres jelzés viszi a szót). Ezért a `mind_ures` predikátum
  (app.js:892) ÚJRAFELHASZNÁLVA, nem új számítás.
- Felveendő a `trend_blokk_render` takarító `querySelectorAll` listájába (app.js:869), hogy napváltáskor eltűnjön.

**Vizuális elválasztás (Q1-megkötés):** kategóriás napon a sorrend `összefoglaló (benne
kategória-magyarázat) → normalizálás-magyarázat → lista`. Hogy NE olvassa két egymás alatti bekezdésnek:
a `.trend-normalizalas-magyarazat` MÁS stílust kap (bal oldali akcentus-border + halványabb/dőlt szedés
+ „ⓘ" jelölés) — így külön blokként olvasható, nem a kategória-magyarázat második bekezdéseként.

**Szöveg (KÉTFELŰ):**
> ⓘ A görbék magassága nem összemérhető: mindegyik a SAJÁT aznapi csúcsához (100) van skálázva, ezért
> két hasonló magasságú görbe eltérő keresettséget takarhat — azt a „volumen" mutatja. Amit a görbe
> megbízhatóan mutat: egy trend saját napi lefutásának ALAKJÁT és a CSÚCS IDŐZÍTÉSÉT.

(Az első fél = mi NEM olvasható ki [§1.4 tiltás]; a második fél = mi IGEN [§7.3: egy görbén belül az alak
és időzítés érvényes; a 08-09 vizuális szemle igazolta].)

## C. Doboz-geometria (LELET 3) — KÉT külön probléma

**C1 — Levágott csúcs = y-FEJTÉR, nem magasság.** A `y.max=100` miatt a 100-értékű pont a rajzterület
FELSŐ PEREMÉN renderel, a doboz magasságától FÜGGETLENÜL — ezt a magasítás önmagában NEM oldja.
Megoldás: `y: { min: 0, max: 110 }` (~9% fejtér; a 100 a rajzterület ~91%-án ül, a `pointHoverRadius:3`
körnek is jut hely). Fix vizuális konstans; az adat továbbra is 0–100 (csak a tengely-skála kap fejteret).

**C2 — Tooltip-olvashatóság + görbe-részletesség = doboz-MAGASSÁG, MÉRT.**
Mérési protokoll (eldobható `e2e/_diag.spec.js`, a 8a `_diag`-mintára, **futtatás után törölve, NEM commit**):
- Szélességek: **380×320** (mobil) és **1280×800** (asztali).
- Jelöltek: **64** (mai), 88, 96, 112 px.
- Mért mennyiségek: `.trend-kartya` boundingBox magasság; az ELSŐ trend-kártya viewport-pozíciója; a
  görbe rajzterület-magassága; szemre: a 8 perces pontok vizuális elkülönülése és a csúcs (C1-fejtérrel) nem vág-e.
- **Választás:** a LEGKISEBB magasság, ahol a csúcs nem vág, a lefutás olvasható, és a kártya mobilon nem
  lóg ki abszurd módon. A magasság a jegyzőkönyvbe (commit-üzenet + ledger) MÉRT értékként kerül.
- **Őr:** a teljes SOROS suite fusson; `kulcsszo.spec.js` T11 (lusta-render) MARADJON zöld. (Strukturálisan
  biztonságos — a kulcsszó-blokk a trend fölött van; empirikusan is igazoljuk.)
- **Ütközés-szabály:** ha a használható magasság megtörné a Task 10 rootMargin-zónát / T11-et → az a
  **Task 10 hatóköre, JELZÉS** a felhasználónak, NEM csendes áttolás.

CSS: `#trend-blokk .trend-sparkline-doboz { height: <MÉRT>px; }` (app.css:75, ma 64px).

---

## D. Tesztek (smoke, DOM-szerződés — a canvas-belső NEM)

Új `e2e/trend.spec.js` tesztek (a T22 után, 23-tól):
- **T23** — van-görbe napon `.trend-normalizalas-magyarazat` JELEN + kétfelű szöveg-horgony
  (tartalmazza a „volumen" ÉS az „időzítés" szót).
- **T24** — mind-üres napon (idosor-ág bukása) `.trend-normalizalas-magyarazat` NINCS (diszkriminátor:
  van blokk-üres jelzés, de nincs normalizálás-magyarázat).
- **T25** — DOM-sorrend: a `.trend-normalizalas-magyarazat` a `.trend-lista` ELŐTT áll (a magyarázat
  „előbb érkezik", Q1). Kategóriás napon a `.kategoria-magyarazat` és a `.trend-normalizalas-magyarazat`
  KÜLÖN elem (nem összeragadt bekezdés).
- **(T26 opc.)** — archív napon (görbe van, kategória nincs) a normalizálás-magyarázat JELEN, az
  összefoglaló NINCS (a feltétel-szétválasztás igazolása: `!mind_ures` ≠ `eloszlas>0`).
- A **tooltip config NEM assertálható** → nincs rá smoke; kézi szemle (A.).
- A magasság-mérő `_diag` spec NEM marad a suite-ban.

## E. Verifikáció

1. SOROS Playwright + pytest zöld — várt: **56 + új (≈60)**, **224**.
2. **KÉZI vizuális szemle** localhost:8000, valós 08-09 adat: tooltip hover 3–4 görbén (nagy/kicsi
   volumen, lapos/csúcsos alak — pl. `liverpool–monaco` 20000 vs `halpusztulás` 2000); a
   normalizálás-magyarázat helye/olvashatósága; a csúcs nem vág (C1); a magyarázat a lista fölött.
3. **Subagent-review** — CSAK 50+ soros kódváltozásnál (munkamódszer). A várható diff (tooltip-callback
   + magyarázat-elem + CSS) a határ közelében lehet → a végső diff-méret dönt.

## F. Végrehajtási sorrend (kis atomi lépések, a 8a mintájára)

1. **Mérés** — `_diag` spec → doboz-magasság megállapítása (C2), jegyzőkönyv. (Kód előtt, L10.)
2. **Kód** — `trend_sparkline_letrehoz` tooltip (A) + y-fejtér (C1); `trend_blokk_render`
   normalizálás-magyarázat (B) + takarító-lista; CSS doboz-magasság (C2) + `.trend-normalizalas-magyarazat` stílus.
3. **Tesztek** — T23–T25(+T26); RED→GREEN a magyarázat-elemre (a tooltipre nincs RED, kézi).
4. **Verifikáció** (E) + kézi szemle.
5. **Zárás** — commit(ek), ledger-frissítés, ATADAS.

---

## Nyitott / kockázat

- A tooltip UTC-t mutat (nem helyi idő) — tudatos konzisztencia a kulcsszó-oldallal; ha helyi idő kell,
  az KÜLÖN döntés mindkét oldalra (nem 8b-scope).
- A magasság MÉRT; ha a mobil-geometria (Task 10) később újrahangol, a VÉGLEGES magasságon teszi (egyszer).
- 50+ soros diffnél subagent-review a munkamódszer szerint.
