# Inline naptár nap-választó (a `<select>` helyett)

Dátum: 2026-08-21
Hatókör: **frontend-only** (app.js `datum_valaszto_render` + `valasztott_nap` + esemény-kötés,
docs/css/app.css). Az adat-contract VÁLTOZATLAN (`napok/index.json`). Canvas/UI → **VIZUÁLIS SZEMLE
KÖTELEZŐ**. NEM hatókör: backend, más blokkok, hét-választó.

## 1. Cél

A `#datum-valaszto` `<select>`-jét egy **inline naptár-rács** váltja (mindig látszik). A nem-választható
napokat (nincs rájuk adat / szomszéd-hónap) KICSIT SZÜRKÍTJÜK és nem-kattinthatóvá tesszük; a kiválasztott
nap kék kiemelést kap. A ‹ › hónap-navigáció az ADAT-TARTOMÁNYRA korlátozott.

## 2. Szerkezet

- Fejléc: hónap-év felirat + `‹`/`›` gomb (hónap-lépés).
- Hétfő-kezdő fejsor: H K Sz Cs P Sz V.
- 6×7 nap-rács. Cellánként:
  - a megjelenített hónap napja, amire VAN adat (`napok/index.json`) → `<button class="nap-cella">` (kattintható);
  - adat NÉLKÜLI nap VAGY szomszéd-hónap napja → `.nap-cella.nem-valaszthato` (halvány, `disabled`/nem-gomb);
  - a kiválasztott nap → `.nap-cella.valasztott` (kék kiemelés) + `aria-current="date"`.

## 3. Állapot + adatfolyam (contract változatlan)

- Elérhető napok: `napok/index.json` → Set (O(1) lookup). Tartomány = min…max nap.
- Megjelenített hónap: a `#datum-valaszto` `data-honap` attribútumában (UI-állapot); induláskor a
  LEGFRISSEBB nap hónapja. A ‹ › ezt lépteti (a kiválasztás VÁLTOZATLAN), a rácsot újrarajzolja.
  A ‹ letiltva, ha a hónap ≤ a tartomány első hónapja; a › letiltva, ha ≥ az utolsó.
- Kiválasztott nap: a `#datum-valaszto` `data-valasztott-nap` attribútumában. Alap = legfrissebb.
  A `valasztott_nap()` és az esemény-kötés INNEN olvas (a mai `select.value` helyett).
- Nap-kattintás: `data-valasztott-nap` = a nap → a meglévő nap-váltás hatás (a `#trend-blokk` napja
  frissül, a trend/idősor újrarajzol). Az esemény továbbra is a KONTÉNEREN delegált (túléli az újrarajzolást).

## 4. Tesztek

**Újramérendő (a widget változik, NEM termék-regresszió):**
- `vezerlok.spec.js`: „select feltöltve / alap legfrissebb" + „csökkenő sorrend" → naptárra (a rács a
  legfrissebb hónapot rajzolja, a legfrissebb nap `.valasztott`; a „sorrend"-teszt tárgytalan → a naptár
  természetes rács-rendje, helyette: az adat-napok kattinthatók, a többi szürke).
- `heti.spec.js` #6: a `#datum-valaszto select` érték → `data-valasztott-nap` olvasás (a függetlenség marad).
- `mobil.spec.js` G2 (WCAG 2.5.8 érintési célméret): a select-magasság → a **nap-cella gomb ≥44×44px**
  (`pointer: coarse`), a kalendárium célmérete.

**Új (TDD, RED→GREEN, NÉVRE+VISELKEDÉSRE):**
- a rács a legfrissebb hónapot rajzolja, a legfrissebb nap `.valasztott` (+ `data-valasztott-nap`);
- az adat-napok `<button>` (kattintható), az adat-nélküli + szomszéd-hónap napok `.nem-valaszthato` (disabled);
- nap-kattintás → `data-valasztott-nap` frissül + a `#trend-blokk data-nap` követi;
- ‹ › a tartomány-széleken `disabled`.

## 5. SZEMLE (KÖTELEZŐ a köztes állapotnál)
A kód zöldre kerülése UTÁN ÁLLJ MEG. Szemle: a naptár a legfrissebb hónapot mutatja, a legfrissebb nap kék;
az adat-napok kattinthatók (nap-váltás működik), a többi halvány; a ‹ › a széleken letiltva.

## 6. Kapuk
DOC-COMMIT (ez) a kód ELŐTT; teljes SOROS suite zöld; docs/data TISZTA; MUTÁCIÓ=1; leltár a záró commitban.

## 7. HETI naptár (Szelet 2, USER-jóváhagyva: „hét-kiemelő naptár")

A `#heti-valaszto` `<select>`-jét is naptár váltja, DE hét-granularitással: kattintáskor a nap EGÉSZ HETE
(hétfő–vasárnap sor) kiemelődik, és az adott hét kerül kiválasztásra.

- **Közös rács:** a `naptar_epit(honap, elso_ho, utolso_ho, cellaAllapot)` helper (a napi naptárból kiemelve,
  DRY) építi a fej + ‹ › + rács szerkezetet; a `cellaAllapot(iso, szomszed)` dönt a választhatóságról/kiemelésről.
- **Heti logika:** egy HÉT választható, ha van benne adat-nap (`het_hetfo(iso)` a data-hét-hétfők közt). A
  kiválasztott hét MIND a 7 cellája `.valasztott-het` (világoskék sor, a szomszéd-hónap cellái is). Kattintható
  csak a nem-szomszéd, adat-hét nap.
- **Hétfő-számítás Date nélkül:** `het_hetfo(iso)` = iso − (Sakamoto hétfő-index) nap, `iso_nap_lep`-pel
  (nap ±delta hónap/év átfordulással, tiszta egész-aritmetika).
- **Állapot:** a kiválasztott hét hétfője a `#heti-valaszto` `data-valasztott-het`-ben, a hónap `data-honap`-ban.
  Alap = a LEGFRISSEBB hét. Nap-kattintás → `data-valasztott-het` = a hét hétfője → `heti_tabla_render(hétfő)`.
- **Cím:** „Melyik hét felkapottjai?" (a napi „Melyik nap felkapottjai?" párja).

### Tesztek
- Újramérendő: `heti.spec.js` a `#heti-valaszto select`-re épülő tesztjei (a widget naptár lett).
- Új (TDD): a heti naptár a legfrissebb hét sorát emeli ki; nap-kattintás → az egész hét kiemelve + a heti tábla követi;
  adat-nélküli hét szürke.

## 8. Kísérő kis tweak-ek (USER, live-iteráció, ugyanebben a körben)
- Napi cím „Nap" → „Melyik nap felkapottjai?"; heti cím „Hét" → „Melyik hét felkapottjai?".
- Kategória-idősor y-felirat „trendek száma" → „kategóriába eső trendek".
- Kategória-idősor ALAP: az ELSŐ kategória kiemelve (nem „mind szürke") — `idosor_aktiv` az első vonalra,
  `idosor_szinez()` a build után a DOM-mirror + legend szinkronhoz.
