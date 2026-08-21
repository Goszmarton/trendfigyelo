# 3b — a masodlagos intervallum PER-INTERVALLUM rácsán rajzol (nem a szó-config rácsán)

Dátum: 2026-08-21
Hatókör: **frontend `egyesitett_reg`, 1 sor.** Canvas → **VIZUÁLIS SZEMLE KÖTELEZŐ** (SZEMLE-SZABÁLY,
ZOLD-NEM-SZALLIT). NEM hatókör: backend (a regresszió MÁR helyesen adja a per-interval `racs`-ot),
LANC-SZAKASZ-TORES, IRANY-KUSZOB, ADD-SWAP, TASK5.

## 1. A lelet (szemlén elkapva, 2026-08-21)

A TELJES nézeten a nap-config szavaknál (állás, kormányablak, eladó lakás, akciós újság) a kék
adat-görbe NEM rajzolódik (a trendvonal igen). Ok: a `egyesitett_reg` (app.js:251) a masodlagos
intervallumra a **SZÓ-szintű** rácsot teszi (`_racs: m.racs`), a **per-intervallum** `miv.racs` helyett.
A backend a masodlagos regresszióban HELYESEN adja: az 1_ev `racs='het'` (heti, 7 naponta), a 3_ho
`racs='nap'`. De egy nap-config szónál (`m.racs='nap'`) a het-forrású 1_ev `_racs='nap'`-ot kap → a
heti pontok NAPI slot-rácsra kerülnek → minden heti pont közé 6 napi NULL ékelődik → `spanGaps:false`
mellett a kék vonal 52 izolált 1-pontos szakaszra esik → LÁTHATATLAN. A `_racs` a felbontás-feliratot
(app.js:779) ÉS a rajzoló rácsot (`racs_epit(ablak, iv, iv._racs)`, app.js:799) is vezérli.

Ez a MASODLAGOS-TF-nél TUDATOSAN DEFERRED „3b" tétel („both-timeframe ADAT UTÁN"). Most jelenik meg,
mert a both-timeframe masodlagos adat feltöltődött. PRE-EXISTING, NEM a mai LANC-ORAS Sz2 okozta
(a Sz2 az órás láncot érintette; a masodlagos regresszió commitolt/érintetlen).

## 2. Fix (1 sor, forrás-hűség)

`docs/js/app.js:251` — `egyesitett_reg` masodlagos-valid ág:
  `_racs: m.racs` → `_racs: miv.racs || m.racs`
A per-intervallum `racs`-ot használjuk (a backend adja), szó-szintű fallback-kel (ha egy interval
nem hordozna racs-ot). Az órás ág (`_racs: "ora"`, app.js:249) és az ÜRES ág ok-kód `o.racs`/`m.racs`
(app.js:262/265) VÁLTOZATLAN — azok a szó config-rácsát nézik, ami ott HELYES.

## 3. TDD (valódi RED, NÉVRE+VISELKEDÉSRE)

- 22. RED: nap-config szó, HET-forrású 1_ev intervallum (`iv.racs='het'`) → `data-felbontas="het"` +
  `data-szakadas="0"` (folytonos heti rács). RED: ma `data-felbontas="nap"` (a szó-racs) → a heti
  pontok szétszórva, sok szakadás. A tényleges RED-üzenetet mutatjuk.
- Meglévő őrzők: a 2e (het-config szó → het) és a napi tesztek TOVÁBBRA IS zöldek (a fix a
  per-interval racs-ot használja, ami het-config szónál ugyanaz mint m.racs).

## 4. SZEMLE — KÖTELEZŐ a köztes állapotnál
A kód zöldre kerülése UTÁN ÁLLJ MEG. A szemlén: a nap-config szavak (állás/kormányablak/eladó
lakás/akciós újság) TELJES nézetén a kék görbe MOST rajzol (heti rács); az albérlet (het-config)
és a napi 3_ho nézetek VÁLTOZATLANOK.

## 5. Kapuk
Teljes SOROS suite zöld; docs/data TISZTA; MUTÁCIÓ=1; leltár a záró commitban; DOC-COMMIT a kód ELŐTT.
