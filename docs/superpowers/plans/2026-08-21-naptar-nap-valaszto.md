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
