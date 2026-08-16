# 6b / RAJZOLÁS — Szelet 2: másodlagos fogyasztás + routing + rács-tudatos üres-állapot

Dátum: 2026-08-16
Spec: docs/superpowers/phase4/phase4-spec.md §8 (a felület fogyassza a nap/het
másodlagos adatot); §8.2 (nap/het = egyetlen today 3-m/12-m, NEM láncolás).
Előzmény: Szelet 1 (racs_epit slot-rács) LESZÁLLT (a99c335). Ez a szelet köti be
a valós másodlagos adatot. ATOMI és >50 sor → subagent-review KÖTELEZŐ.

## Két mért lelet (a felderítésből)

1. A gomb-elérhetőség AGGREGÁLT és ÓRÁS-alapú (`intervallum_allapot`, app.js:135:
   „legalább egy szónál ervenyes", csak a kulcsszo_regresszio.json-ból). → a
   másodlagos görbe ELÉRHETETLEN, amíg a gomb tiltva marad. A routingnak a
   gomb-elérhetőséget is egyesítenie kell.
2. A `racs` PER-INTERVALLUM különbözik, nem per-szó. albérlet: 1_het = órás
   (racs „ora"), 1_ho = másodlagos (racs „nap"). → a RACS_EGYSEG jelenlegi
   szó-szintű `szoreg.racs` hívása (app.js:464) átáll INTERVALLUM-szintre.

## Megoldás: egyesített merge-réteg

Új `egyesitett_regresszio()`: az órás + másodlagos regresszióból EGYETLEN
egyesített `kulcsszavak` nézetet épít, amit a MEGLÉVŐ renderelők
(`intervallum_vezerlo_render`, `kartya_letrehoz`) VÁLTOZATLANUL fogyasztanak.
A logika a merge-ben; a renderelő alig változik.

Minden (szó W, intervallum X) párra:
- órás[W][X].ervenyes → iv = órás, `_racs="ora"`, `_forras="kulcsszo_nyers.json"`
- különben másodlagos[W] && másodlagos[W][X].ervenyes → iv = másodlagos,
  `_racs=másodlagos[W].racs`, `_forras="kulcsszo_masodlagos_nyers.json"`
- különben üres (ok = az elsődleges forrásból, lásd lent)

A `_racs`/`_forras` az iv-re kerül (nem a szóra). `kartya_letrehoz`: az
`iv._racs`-ot adja a `merteszamok_szoveg`/`racs_epit`-nek; `nyers_ablak` az
`iv._forras`-t olvassa (órás vs másodlagos nyers).

## Rács-tudatos ÜRES-ÁLLAPOT (KUDARC-VAK a felületen — kritikus)

Elsődleges forrás egy X-hez: X==1_het → órás; X∈{2_het,1_ho,3_ho,1_ev} →
másodlagos. Az üres `ok` az elsődleges forrásból:
- hosszú X, van másodlagos entry → a másodlagos `ok` (keves_pont / esemenyjelzo)
- hosszú X, NINCS másodlagos entry (a szó sosem forgott be; rotáció max 2/nap) →
  ÚJ `nincs_masodlagos`
- rövid X (1_het) → órás `ok`

GARANCIA: hosszú intervallum SOHA nem mutat „Ehhez több összefűzött nap kell"
(nincs_lancolas) — az az órás láncolásra (LANC-ORAS) utal, ami a nap/het ágon
irreleváns (§8.2). Új OK_MAGYAR:
- `nincs_masodlagos: "Ehhez még nem gyűjtöttünk napi/heti adatot"`
- `esemenyjelzo: "Eseményjelző — szint-nézet készül (nem trendvonal)"`
  (KIMONDVA: tüntetésnek VAN adata, csak eseményjelzőként nem rajzolunk
  trendvonalat; a szöveg NEM állít adathiányt. A 6c cseréli üres → szint-vonal.)

## Betöltés blokk-izolációval — részleges betöltés

A kulcsszo-blokk BLOKK bővül: +kulcsszo_masodlagos_regresszio.json,
+kulcsszo_masodlagos_nyers.json. A `blokk_betolt` fájlonként izolál
(Promise.allSettled). Részleges betöltés → LÁTHATÓ üres, SOHA csendes rossz görbe:
- regresszió megvan, nyers hiányzik → routing másodlagosra vált, de `nyers_ablak`
  null (nincs ablak) → `!ablak` guard → URES_NINCS_ABLAK (látható).
- nyers megvan, regresszió hiányzik → routing sosem választ másodlagost (a
  `.ervenyes`-re kulcsol) → `nincs_masodlagos` üres.
- mindkettő hiányzik → hosszú intervallumok `nincs_masodlagos`.

## KUDARC-VAK őrök — a routing RAJTUK KERESZTÜL megy

- `nyers_ablak` ablak_veg-EGYEZÉS (app.js:363): az egyesített iv ablak_veg_utc-
  jével egyező másodlagos nyers ablak; elavult/nem-egyező → null → .ures.
- `iv.ervenyes` + `!ablak` guardok (app.js:432) érintetlenek; a merge táplálja
  őket, nem kerüli meg.

## Alap-intervallum: SPEC-SZÁNDÉK (leghosszabb érvényes) — döntés + megkötés

A `intervallum_vezerlo_render` (app.js:174) a leghosszabb ÉRVÉNYES intervallumot
választja alapból (spec 7.2 „magától tolódik kifelé"). Szelet 2 után a 3_ho/1_ev
is érvényes → az alap-nézet a leghosszabb másodlagos intervallumra ugrik.
DÖNTÉS (jóváhagyva): követjük a spec-szándékot (a commitolt viselkedés; egy 90
napos napi görbe több információ, az órás egy kattintás).

MEGKÖTÉS (leltárba, megfigyelésként — NEM task): **ALAPNEZET-VEGYES** — ezzel a
kártyák KÜLÖNBÖZŐ alapnézeten nyílnak (a 4 másodlagos szó 3_ho/1_ev-en, a 9 többi
1_het-en). Nem hiba, de látható inkonzisztencia; a szemlénél kiemelten nézzük, és
ha zavaró, külön kis szeletben 1_het-re rögzíthető.

## TDD — RED-ek (névre, hibatípusra)

1. Elsődleges: mock másodlagos_regresszió (egy szó 1_ho érvényes, racs=nap) +
   másodlagos_nyers (napi ablak). Assert: az 1_ho gomb ENGEDÉLYEZETT
   (`toBeEnabled`). RED: ma a másodlagos nincs betöltve → intervallum_allapot(1_ho)
   aggregált-érvénytelen → gomb `disabled` → `toBeEnabled` bukik (AssertionError,
   „not enabled"); a gomb létezik (locator feloldódik).
2. Üres-label: egy szó másodlagos ENTRY NÉLKÜL, hosszú X → a tiltott gomb
   ok-szövege „…napi/heti adatot". RED: ma „…összefűzött nap" → toContainText bukik.
3. Rajzolás-integráció: az 1_ho kiválasztása után a másodlagos szó kártyája
   drawable, „nap nem-nulla", data-szakadas=0. RED: ma az 1_ho gomb tiltott →
   nem választható → a kártya nincs_lancolas üres.
SZÁNDÉKOS-ZÖLD (előre): (1) a meglévő órás 1_het tesztek (1–10., 2f) változatlan;
(2) explicit: másodlagos betöltve, de egy tisztán órás szó 1_het-je VÁLTOZATLANUL
órás görbe („óra nem-nulla").

## Diff + review + szemle

Production >50 sor (merge ~30–45 + OK_MAGYAR 2 + nyers_ablak forrás ~3 + kartya
_racs/_forras ~4 + BLOKK 1 + render-belépő ~3) → **subagent-review KÖTELEZŐ** a
commit előtt. Teszt ~70–90 sor.

Leltár lezáráskor: 6b Állapot frissül (Szelet 2 kész — a rajzolás teljes; ami hátra:
6c szint-vonal + a nagyobb LANC-ORAS órás-láncolás külön); ÚJ megfigyelés
ALAPNEZET-VEGYES (D-blokk, rekord); invariáns újraszámolva.

Vizuális szemle Szelet 2 UTÁN (6 pont): (1) alap-intervallum a leghosszabb
másodlagosra ugrik-e; (2) albérlet 1_ho napi görbe, dátumok, „nap nem-nulla",
vonal, tooltip dátum; (3) akciós újság 1_ev heti görbe, „hét nem-nulla"; (4)
benzin (nincs másodlagos) 2_het → „…napi/heti adatot" (NEM „összefűzött nap");
(5) tüntetés hosszú → „Eseményjelző — szint-nézet készül (nem trendvonal)"; (6)
bármely órás szó 1_het VÁLTOZATLAN. + KIEMELTEN: ALAPNEZET-VEGYES (vegyes kezdő).
