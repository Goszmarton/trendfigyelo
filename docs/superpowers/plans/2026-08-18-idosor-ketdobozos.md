# Terv — Kategória-idősor kétdobozos elrendezés (legend bal, chart jobb) (jóváhagyva 2026-08-18)

CSAK ELRENDEZÉS-átszabás: a meglévő „Napi keresési kategóriák idősora" chart a `heti-felkapott` blokk mintájába
kerül — önálló `.szekcio`, **bal** dobozban (sticky `vezerlo-sav`) a legend, **jobb** dobozban a chart (cím fönt,
canvas, alatta a magyarázat). Az adat-shaper (`kategoria_idosor`), a szürke→kék kiemelés-logika és a rejtett
DOM-tükör VÁLTOZATLAN — csak a Chart.js belső (jobb oldali) legendje költözik ki HTML-legendbe a bal dobozba.

## MÉRT alapok (2026-08-18)
- **Jelenlegi hely:** az idősor a `trend_blokk_render`-ben épül, a `#trend-blokk`-on BELÜL, a „Ma felkapott
  keresések" h2 ELÉ beszúrva (`blokk.insertBefore(trend_idosor_epit(idosor), cim_h2)`). A legend a Chart.js
  beépített legendje, `position:"right"`, `generateLabels`-szel (szürke pötty / kék aktív).
- **Elrendezés-minta:** `#dashboard > .szekcio > (aside.vezerlo-sav[sticky] + section#…)` — ugyanaz, mint a
  `datum-valaszto`+`trend-blokk` és a `heti-valaszto`+`heti-blokk` szekció.
- **Adat:** `kategoriak.json` (nap-független, az init `trend-blokk` BLOKK-ja tölti be) → a shaper VÁLTOZATLAN.
  **BACKEND 0 kód.**
- **Kiemelés-modell (MARAD):** alap = MIND szürke; egy kategóriára kattintva az kék + felül, a többi tompított;
  ugyanarra újrakatt = reset (`idosor_aktiv_valt` toggle). Canvas-belső → **SZEMLE-köteles**; a legend AKTÍV
  állapota viszont HTML → **DOM-assertálható** (`.kiemelt` osztály a `[data-kategoria]`-n).

## Döntések (a user rögzítette)
1. Elhelyezés: önálló `.szekcio` a `#trend-blokk` szekció **FÖLÉ** (oda, ahol most is vizuálisan van).
2. Bal doboz = legend (kattintható), jobb doboz = chart. A Chart.js saját legendje **kikapcsolva**.
3. Legend viselkedés **VÁLTOZATLAN**: szürke→kék kiemelés, toggle-reset. Egyszerre EGY kiemelt.
4. Legend **kinézet VÁLTOZATLAN**: kerek szürke pötty + név; aktív = kék pötty + kék szöveg (a mostani Chart.js
   legend reprodukciója HTML-ben).
5. Cím + magyarázat a **jobb** dobozba (cím fönt → chart → magyarázat, a mostani sorrend); a bal doboz csak legend.
6. A bal doboz kerete/sticky-je a `vezerlo-sav` kártya (mint a hét-/dátum-választó).

## Backend: NINCS változás
Tiszta frontend elrendezés-átszabás. Az adat (`kategoriak.json`) megvan, auto-generált, auto-committed.

## Szelet 1 — kétdobozos elrendezés + HTML-legend (DOM-assertálható, RED→GREEN)
- `index.html`: ÚJ `.szekcio` a `#trend-blokk` szekció ELŐTT: `aside.vezerlo-sav > #idosor-legend` (bal),
  `section#idosor-blokk` statikus `<h2>Napi keresési kategóriák idősora</h2>` (jobb).
- `app.js`:
  - `trend_blokk_render`: a `trend_idosor_epit` beszúrás **törölve**; a takarító-szelektorból a `.idosor-blokk`
    **kivéve** (az idősor már nem él a `#trend-blokk`-ban).
  - ÚJ `idosor_blokk_render()` (RENDEREK-be, a `trend-blokk` ELÉ): `kategoria_idosor(adat["kategoriak.json"])` →
    ha van vonal: a `#idosor-blokk`-ba chart-doboz+canvas+rejtett tükör+`.idosor-magyarazat`, a `#idosor-legend`-be
    a HTML-legend; ha nincs vonal: a korábbi chart/legend/caption törlése (üres állapot, csak a h2 marad).
  - ÚJ `idosor_legend_epit(idosor)`: kategóriánként `<button.idosor-legend-elem[data-kategoria]>` (pötty `<span>` +
    név); katt → `idosor_aktiv_valt(nev)`.
  - `trend_idosor_chart_epit`: `plugins.legend.display = false` (a `generateLabels`/legend-`onClick` blokk törölve);
    a chart-`onClick` (vonalra/üresre kattintás) MARAD.
  - `idosor_szinez()`: a chart-frissítés után a HTML-legend elemeit is szinkronizálja (`.kiemelt` az aktívra,
    törlés a többiről); a `data-idosor-aktiv` DOM-tükör a `#trend-blokk` HELYETT a `#idosor-blokk`-ra kerül.
- `app.css`: `#idosor-blokk` a szekció-doboz szabályba (`#kulcsszo-blokk, #trend-blokk, #heti-blokk` mellé); a
  `.idosor-*` szabályok `#trend-blokk` helyett `#idosor-blokk` alá; ÚJ `#idosor-legend` pöttyös-lista stílus
  (kerek szürke pötty 14px, `.kiemelt` → kék pötty + kék szöveg), a Chart.js legend reprodukciója.

**Szelet 1 RED (AssertionError, valós üzenetekkel):**
- `idősor-elrendezés: az idősor SAJÁT #idosor-blokk szekció, a DOM-ban a #trend-blokk ELŐTT` → RED: ma a
  `#trend-blokk`-on belül van.
- `idősor-legend: a bal #idosor-legend N kattintható elemet tartalmaz (data-kategoria), a Chart.js belső legend NINCS`
  → RED: ma nincs HTML-legend, a canvas-legend a jobb oldalon.
- `idősor-legend: kattintásra az elem .kiemelt lesz, a többi nem; újrakatt törli (toggle)` → RED: nincs HTML-legend.
- `idősor-chart: canvas + data-idosor-chart-rendered a JOBB #idosor-blokk-ban` → RED: rossz konténer.
- `idősor-chart: a cím + magyarázat a jobb #idosor-blokk-ban (cím a canvas ELŐTT, magyarázat UTÁN)` → RED.
- A meglévő shaper-tesztek (4) VÁLTOZATLAN adatot mérnek, csak a KONTÉNER-szelektor `#trend-blokk`→`#idosor-blokk`.
- A régi „idősor a »Ma felkapott keresések« cím ELŐTT (a #trend-blokk-ban)" teszt CSERÉLVE az új szekció-sorrend
  tesztre (a szekció a trend-szekció ELŐTT).

## SZEMLE (push előtt, lokális szerver)
Bal legend látvány = a mostani (pöttyök, kék aktív); kattintás → a chart vonala kékül; sticky együttmozgás a
jobb charttal (mint a hét-választó); arányok mobil-nézetben (a `.szekcio` oszlopba tördel).

## Leltár
Elrendezés-átszabás, nincs adat-vesztés/néma-bukás → valószínűleg PARKOLT sor (nem új tétel); a mérés dönt (§11a).
