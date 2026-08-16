# 6b / RAJZOLÁS — Szelet 1: racs_epit rács-általánosítás (óra bájt-azonos)

Dátum: 2026-08-16
Spec: docs/superpowers/phase4/phase4-spec.md §8 (a §8:168 nevesíti az `app.js`
órarács-rajzolását mint általánosítandót a nem-órás rácsokra).
Előzmény: RACS_EGYSEG (felirat-szelet) LESZÁLLT (d00727b). Ez a rajzolás első,
legkockázatosabb, IZOLÁLT szelete — valós adat még NEM folyik rajta (Szelet 2).

## Cél

A `racs_epit` (docs/js/app.js) ma végig `ora_index`-re épül (óránkénti slot).
Ez a szelet a slot-pozicionálást és a label-formátumot rács-tudatossá teszi, hogy
a napi/heti pontok helyes rácson rajzolódjanak — MIELŐTT a másodlagos JSON-t
bekötnénk (Szelet 2). Az órás út bájt-azonos marad.

## Mért adatmodell (a szeletelés alapja)

- Minden szó az ÓRÁS fájlban van; a 4 másodlagos szó annak részhalmaza. A routing
  PER-INTERVALLUM: 1_het = órás (óránkénti); 2_het/1_ho/3_ho/1_ev = másodlagos
  (napi/heti), ha a szónak van másodlagos adata. (A routing maga a Szelet 2.)
- A másodlagos nyers séma AZONOS az órással: `{ablak_kezdet/veg_utc,
  pontok:[{idopont_utc,ertek,reszleges}], racs}`. Ütem: nap = napi, het = heti.

## het-geometria — MÉRVE (nem tipp)

akciós újság 1_ev, 53 heti pont, `floor(nap-index/7)` (globális epoch nullpont):
- **53 pont → 53 distinct slot**; szomszéd slot-különbség mind 1 (52×);
  collision (dif=0) = 0; hamis hézag (dif>1) = 0.
- nap-index mod 7 = {3} (mind vasárnap → fázis-stabil).
- albérlet nap: 93 pont → 93 distinct nap-index, mind 1-köz.

Következtetés: `floor(nap-index/7)` VÁLTOZATLAN mehet. Bármely pontosan 7-naponként
lépő sorozat összefüggő, distinct floor-értékeket ad (a +7 mindig egy határt lép
át), fázistól függetlenül. Tudatos függés: a heti pontok 7-nap-köze (a backend
heti rácsa garantálja); egy elcsúszott het-pont valós hézagot adna = HELYES
(kimaradt hét = valódi szakadás). A het-teszt a folytonosságot (szakadás=0) pinneli.

## A változás

- `slot_index(iso, racs)`:
  - óra → `napok_civil(...)*24 + óra` (= a jelenlegi `ora_index`, KARAKTERRE azonos)
  - nap → `napok_civil(...)` (nap-index)
  - het → `floor(napok_civil(...) / 7)` (hét-index)
- `racs_epit(ablak, iv, racs)`: az `ora_index` hívások → `slot_index(..., racs)`;
  a ciklus `i++` marad (a slot-egység a rácstól függ). A label-formátum:
  - óra → „dátum HH:MM" (VÁLTOZATLAN)
  - nap/het → „dátum" (nincs óra-rész)
- A tick-callback (x-tengely) és a tooltip NEM változik: a „ HH:MM"-vágó regex
  dátum-only labelnél nem illeszkedik → a dátumot érintetlenül mutatja.

## Az órás út védelme

- `slot_index("ora")` ≡ a jelenlegi `ora_index` teste, karakterre; a racs
  hiánya/„ora" a JELENLEGI kódút, a nap/het ÚJ ág MELLÉ kerül.
- Bizonyíték: a MEGLÉVŐ órás kártya-attribútum e2e-k (data-szakadas / data-vonal /
  data-adat-veg / data-pontok / .csupa-nulla / canvas) zöldek maradnak +
  explicit `..._oras_valtozatlan_SZANDEKOS_ZOLD`.
- ŐSZINTE KORLÁT: a canvas-BELSŐ x-tengely-tick és tooltip NEM DOM-assertálható
  (§8.3/L9). Az „ora" ág label-tömbje konstrukció szerint változatlan, de ezt
  auto-teszt NEM őrzi → KÉZI vizuális szemle (órás szó, 1_het) a szelet után.

## TDD — Szelet 1

- Fixture: `racs:"nap"` szó NAPI nyers pontokkal (1-nap köz, folytonos) + azonos
  ablakú érvényes regresszió-intervallum, a MEGLÉVŐ kulcsszo_regresszio/nyers
  mockon át (másodlagos JSON bekötés NÉLKÜL — az Szelet 2).
- RED: `data-szakadas` === "0" (napi rács folytonos). A jelenlegi `ora_index` a
  napi bélyegeket 24-óránként ugró slotokra teszi → sok null-köz → data-szakadas
  NAGY szám. Hibatípus: Playwright `toHaveAttribute` AssertionError (Expected "0",
  Received nagy szám), viselkedésbeli; a locator feloldódik (kártya renderel).
- het-teszt: `racs:"het"` heti pontokkal → data-szakadas === "0" (folytonosság).
- SZÁNDÉKOS-ZÖLD (előre): a meglévő órás szakadás/vonal attribútum-tesztek +
  explicit `..._oras_szakadas_valtozatlan_SZANDEKOS_ZOLD`.

## Lezárás

Diff: app.js ~10–15 sor (slot_index + racs_epit 3 hívás + label-elágazás + a hívó
racs átadása) + e2e ~2–3 teszt. Cél <50 sor kód; ha fölé megy, jelzés (subagent-
review). Leltár: a 6b sor Állapota változatlan RÉSZBEN (a rajzolás első alszelete
kész, a fogyasztás/routing — Szelet 2 — hátravan); ha külön ID kell a rajzolásnak,
a lezáró commit dönt. Vizuális szemle a szelet után (órás VÁLTOZATLAN), MIELŐTT
Szelet 2 indul.
