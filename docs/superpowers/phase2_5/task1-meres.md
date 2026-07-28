# Task 1 — Szóló kulcsszó-mérés jegyzőkönyve

Fázis: Phase 2.5, Task 1 (MÉRÉS — nem TDD)
Plan: docs/superpowers/plans/2026-07-28-trendfigyelo-phase2_5-kulcsszo-meres.md (§ Task 1)
Spec: docs/superpowers/phase2_5/phase2_5-spec.md (§ 6.1 objektív kritérium)
Dátum: 2026-07-28

Cél: a spec 2.2 tizenhárom szavának szóló mérése (`geo=HU`, `now 7-d`, órás
felbontás), és a 6.1 objektív kritérium alapján szavankénti döntés
(mérhető / elbukott). A mérés **rostál** — ezért a küszöbök a lekérdezés
ELŐTT rögzülnek (lentebb), a nyers számok pedig szavanként megőrződnek, hogy
egy későbbi küszöb-korrekció **új Trends-lekérdezés nélkül** újraszámolható
legyen.

---

## 1. JELÖLT KÜSZÖBÖK — a mérés ELŐTT rögzítve

> Ezek a küszöbök **a lekérdezés előtt** kerültek ide. Ha a mérés után
> bármelyiken módosítani kell, a módosítás a 4. szakaszban jelenik meg
> **régi érték + új érték + indok** formában — a lenti számokat NEM írjuk át.

A ~168 pontos (7 nap × 24 óra) szóló órás sorozatra, 0–100 skálán:

### K1 — Különböző értékek száma (distinct értékek a ~168 pontból)
- **Mérhető:** ≥ **25** különböző érték. Gazdag, sok szintű görbe.
- **Gyanús (egyedi mérlegelés):** **9–24** különböző érték.
- **Elvetendő (kvantálás):** ≤ **8** különböző érték — néhány diszkrét szint
  (pl. 0/25/50/75/100), ez nem mérés.

### K2 — Nullák aránya és eloszlása
- **Mérhető:** a nullák aránya < **35%**, VAGY (ha ≥ 35%) a nullák **összefüggő
  éjszakai blokkokban** állnak — ez valódi napi ciklus (pl. `MNB` éjszaka),
  nem hiány.
- **Elvetendő:** a nullák aránya ≥ **35%** ÉS a nullák **szétszórtak** (nem
  összefüggő éjszakai blokkok) — órás felbontásban nem mérhető.
- *Blokk-definíció:* egy nulla „éjszakai blokkban" van, ha a szomszédai is
  nulla és a budapesti óra a 23:00–06:00 sávba esik. A „szétszórt" nullák
  aránya = a nem-blokk nullák / összes pont.

### K3 — Szomszédos pontok különbsége (folytonosság vs. zaj)
- **Nagy ugrás** definíciója: két szomszédos óra közt |Δ| > **25** (0–100
  skálán).
- **Mérhető (folytonos):** a nagy, **előjelet váltó** ugrások aránya < **20%**
  az összes szomszéd-lépésből.
- **Elvetendő (zaj):** a nagy, előjelváltó ugrások aránya ≥ **20%**.

### Együttes döntési szabály
- **Mérhető**, ha **mindhárom** (K1, K2, K3) teljesül.
- **Elvetendő**, ha **bármelyik** kettő elbukik. Egyetlen bukásnál egyedi
  mérlegelés a nyers számok alapján (a 4. szakaszban indokolva).

### K-ESEMÉNY — eseményjelző kivétel (`tüntetés`)
A `tüntetés` alapvonala legitimen alacsony (spec 2.2: 3–7), így K2 (nullák/kis
értékek) és K1 (kevés distinct) **nem alkalmazandó** rá. Helyette:
- A **csúcs-szakaszok** folytonossága a kritérium: a sorozat maximumának
  ≥ 50%-át elérő pontok (a „csúcsablakok") **K3 szerint folytonosak**-e
  (nagy, előjelváltó ugrások aránya < 20% a csúcsablakon belül).
- Ha legalább egy jól kirajzolódó, folytonos csúcs van → **mérhető**.

---

## 2. Mért nyers számok — kulcsszavanként

**Mérés állapota: 13/13 szó megmérve.** A `nyugdíj` a 2. re-runban megjött
(17:14 BP, mérhető). Hiányzik még a `betegség`+`kórház` éves **pár**: a
re-runban a pár-hívás (17:30 BP) **429**-et kapott → megállás (kikötés: nincs
újrapróba). A nyers órás sorozatok a scratchpad
dumpban (`meres_eredmeny.json`) a recomputálhatósághoz. A K1/K2/K3 a §1
**mérés-előtti** küszöbök szerint (K1 distinct ≥25; K2 nulla <35% VAGY éjszakai-
blokk azaz szórt <35%; K3 oszcilláló nagy ugrás <20%). Minden szóló max=100
(a Trends a sorozat maximumára normalizál).

| Kulcsszó (domén, típus) | lekérd. (BP) | distinct | nulla% | szórt% | nagy% | oszc% | K1 | K2 | K3 | Döntés |
|---|---|---|---|---|---|---|---|---|---|---|
| állás (munkaerőpiac, szintmérő) | 13:49 | 43 | 0.0 | 0.0 | 0.012 | 0.006 | ✓ | ✓ | ✓ | **mérhető** |
| kormányablak (közigazgatás, szintmérő) | 14:05 | 65 | 0.213 | 0.006 | 0.048 | 0.0 | ✓ | ✓ | ✓ | **mérhető** |
| eladó lakás (lakhatás, szintmérő) | 14:20 | 44 | 0.16 | 0.0 | 0.125 | 0.024 | ✓ | ✓ | ✓ | **mérhető** |
| albérlet (lakhatás, szintmérő) | 14:35 | 45 | 0.178 | 0.0 | 0.101 | 0.012 | ✓ | ✓ | ✓ | **mérhető** |
| akciós újság (fogyasztás, szintmérő) | 14:50 | 59 | 0.101 | 0.018 | 0.06 | 0.012 | ✓ | ✓ | ✓ | **mérhető** |
| benzin (fogyasztás, szintmérő) | 15:05 | 65 | 0.024 | 0.006 | 0.03 | 0.0 | ✓ | ✓ | ✓ | **mérhető** |
| nyaralás (fogyasztás, szintmérő) | 13:34 | 48 | 0.219 | 0.0 | 0.137 | 0.006 | ✓ | ✓ | ✓ | **mérhető** |
| kórház (egészség, szintmérő) | 12:56 | 57 | 0.089 | 0.018 | 0.071 | 0.018 | ✓ | ✓ | ✓ | **mérhető** |
| betegség (egészség, szintmérő) | 13:19 | 26 | 0.243 | 0.0 | 0.065 | 0.006 | ✓ | ✓ | ✓ | **mérhető** |
| napelem (energia, hibrid) | 15:20 | 43 | 0.32 | 0.047 | 0.161 | 0.036 | ✓ | ✓ | ✓ | **mérhető** |
| nyugdíj (jövedelem, hibrid) | 17:14 | 56 | 0.083 | 0.006 | 0.024 | 0.0 | ✓ | ✓ | ✓ | **mérhető** |
| hitel (háztartási pénzügy, szintmérő) | 15:51 | 38 | 0.154 | 0.0 | 0.024 | 0.0 | ✓ | ✓ | ✓ | **mérhető** |
| tüntetés (közélet, eseményjelző) | 12:27 | 2 | 0.994 | 0.663 | 0.012 | 0.006 | ✗ | ✗ | ✓ | **inkonkluzív** (2.1) |

### 2.0 Szoros átmenetek (nem kizáró ok, de figyelendő)
Két szám a küszöb szélén ment át:
- **`betegség` distinct = 26** (küszöb ≥ 25) — épphogy a „gazdag sorozat" fölött.
- **`napelem` nulla = 32%** (küszöb < 35%) — a nulla-arány közel a határhoz.

Egyik sem kizáró ok, de **ha később ingadoznak, a vágást ezekkel kezdjük**.

### 2.1 `tüntetés` — a mért görbe olvasata (NEM végső döntés; az a Task 2-é)
A 169 órás pontból **egyetlen** nem-nulla: index 3 = **100** (2026-07-21 ~13:00
UTC), a többi 168 pont **0**. distinct = {0, 100}. Ablak: 2026-07-21T10:00 →
2026-07-28T10:00 UTC.

Ez **nem folytonos csúcs**, hanem egyetlen izolált óra — a K-ESEMÉNY (csúcs-
folytonosság) kritérium ezen a héten **nem dönthető el**: ezen a 7 napos ablakon
nem volt érdemi tüntetés-esemény. A spec 5. ezt előre jelezte (a `tüntetés` órás
viselkedése ismeretlen; alacsony alapvonal, ritka csúcsok). A tiszta döntéshez
egy **valódi eseményt tartalmazó ablak** kellene; ennek híján a spec 6.2
védettsége áll (`tüntetés` = az egyetlen eseményjelző, nem vágható), a
megjelenítési döntés fenntartásával. Megjegyzés: az egyetlen órás csúcs → 100
skálázás pontosan a „single-hour = 100" kvantálás, amit a spec 5. veszélyként
nevez meg.

---

## 3. `betegség` + `kórház` éves átfedés-mérés

> Task 1 / 5. lépés: egy közös éves lekérdezés
> `interest_over_time(["betegség","kórház"], geo="HU", timeframe="today 12-m")`,
> annak eldöntésére, ugyanazt a téli hullámot mérik-e (spec 6.2). Az eredmény
> ide kerül; a **döntés a Task 2-é**.

**Módszer (korrigálva): KÉT KÜLÖN SZÓLÓ éves lekérdezés**, nem közös hívás. Egy
közös `interest_over_time(["betegség","kórház"])` mindkét szót a KÖZÖS maximumhoz
normalizálná — ha a kórház nagyobb, a betegség a kvantálási padlóra kerülne, azaz
pont a horgony-hibát reprodukálnánk. Helyette `betegség` (today 12-m) és `kórház`
(today 12-m) **külön**, majd utólag **Pearson-r** + csúcs-hónap egybeesés (a
Pearson lineáris átskálázásra érzéketlen, tehát a két külön normalizált sorozat
együttmozgása kompresszió nélkül kiolvasható).

**Állapot: MÉG NINCS meg — 429 az esti sávban.** Próbák:
- közös hívás, 17:30 (16 perces köz) → 429;
- külön-szóló `betegség` (today 12-m), 18:12 (25 perces köz) → 429.

Az esti sáv (17:30–18:15, a 21:07-es cron felé közeledve) telített; 25 perc sem
volt elég. **Az átfedés-mérést elengedtük** (felhasználói döntés): **mindkét
szó — `betegség` és `kórház` — marad** a listában. Az éves átfedés (Pearson-r +
csúcs-hónap) **NYITOTT kérdés** — a Phase 3 vagy egy későbbi nappali sáv dönti
el; a Task 1-et nem blokkolja.

---

## 4. Küszöb-korrekciók (ha voltak)

> Ha a mérés után bármelyik jelölt küszöb módosult: régi érték + új érték +
> indok. Ha nem volt módosítás: „nincs korrekció".

*(kitöltés a mérés után)*

---

## 5. Összegzés

**Mérhető (12/12 szintmérő + hibrid):** `állás`, `kormányablak`, `eladó lakás`,
`albérlet`, `akciós újság`, `benzin`, `nyaralás`, `kórház`, `betegség`,
`napelem`, `nyugdíj`, `hitel` — mind a három kritérium (K1/K2/K3) teljesül;
distinct 26–65, nulla 0–32%, oszcilláló nagy ugrás ≤3.6%. Gazdag, tiszta,
folytonos görbék — a szóló mérés bizonyítottan **nem** termeli a régi kvantálási
padlót. **A horgony elvetése helyes volt.**

**Inkonkluzív (1):** `tüntetés` (eseményjelző) — ezen a héten egyetlen izolált
1-órás csúcs (100), a többi 0; a csúcs-folytonosság nem dönthető el esemény
híján. A spec 6.2 szerint **védett** (az egyetlen eseményjelző), nem vágható.

**Elbukott: 0.** A >4-es kapu **NEM aktiválódik** → a Task 2 a teljes listával
mehet tovább.

**Szoros átmenetek (figyelendő):** `betegség` distinct=26 (≥25), `napelem`
nulla=32% (<35%) — lásd §2.0.

**Task 2 döntés (jóváhagyva): mind a 13 szó marad.** A `betegség`/`kórház` éves
átfedés (§3) elengedve, mindkét szó a listában; az átfedés **nyitott kérdés** a
Phase 3-ra / későbbi nappali sávra — nem blokkolt semmit.

**Tempó (Task 8 bemenet):** 5 perc kevés (12–13h); 15 perc nappal jó (~11/12 OK);
az esti sávban (17:30–18:15) 16 és 25 perc is 429. A keret idősáv-függő.
