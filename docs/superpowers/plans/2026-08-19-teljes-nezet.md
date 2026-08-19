# Terv — TELJES-NEZET: közös dátum-tengely, per-szó vágás (jóváhagyva 2026-08-19)

Új intervallum-gomb (**„Teljes időszak"**), ami minden szót a saját **leghosszabb ÉRVÉNYES**
intervallumán rajzol, **egy KÖZÖS dátum-tengelyre** vetítve (közös bal szél minden kártyán).
A később kezdődő szó görbéje **később indul** a tengelyen — ez NEM hiba, ez a látni-akart jel
(mennyi adat van egy-egy szóból). **VÁGÁS, nem összefűzés**; nincs kitalált érték, nincs balra
nyújtás, nincs kártyák-közti átskálázás (§1.4: minden szó a saját 0–100 skáláján marad).

**BACKEND 0 kód** — a szükséges adat (primary + másodlagos regresszió + nyers) már megvan.
Tiszta frontend, de **ERVENYES-ROUTING-osztály** (egy per-szó választás vezérli a kártya rajzolását)
ÉS canvas-érintő (új rendering-mód) → **SZEMLE KÖTELEZŐ push előtt**, a köztes állapot NEM pusholható.

## MÉRT alapok (2026-08-18 éles adat)

A per-szó **legkorábbi HASZNÁLHATÓ adatpont** = a szó leghosszabb érvényes intervallumának kezdete
(egyesített primary+másodlagos, `ervenyes:true`):

| szó | rács | leghosszabb érvényes | legkorábbi | pont | span (nap) |
|---|---|---|---|---|---|
| akciós újság | het | 1_ev (M) | **2025-08-10** | 52 | 373 |
| tüntetés | het | 1_ev (M) | **2025-08-10** | 52 | 373 |
| kórház | het | 1_ev (M) | 2025-08-16 | 52 | 367 |
| kormányablak | het | 1_ev (M) | 2025-08-17 | 52 | 366 |
| állás | het | 1_ev (M) | 2025-08-17 | 52 | 366 |
| albérlet | nap | 3_ho (M) | 2026-05-15 | 90 | 95 |
| nyaralás | nap | 3_ho (M) | 2026-05-17 | 90 | 93 |
| betegség | nap | 3_ho (M) | 2026-05-19 | 90 | 91 |
| eladó lakás | nap | 3_ho (M) | 2026-05-20 | 90 | 90 |
| benzin | ora | 1_het (P) | 2026-08-11 | 168 | **7** (GATE) |
| nyugdíj | ora | 1_het (P) | 2026-08-11 | 168 | **7** (GATE) |
| hitel | nap | 1_het (P) | 2026-08-11 | 168 | **7** (még nincs másodlagos) |
| napelem | nap | 1_het (P) | 2026-08-11 | 168 | **7** (még nincs másodlagos) |

- **(a)** A legkorábbi dátumok **2025-08-10 … 2026-08-11** között szórnak (egy teljes év).
- **(b) 0/1 pontú szó: NINCS.** A minimum 1_het = 168 órás pont (7 nap). Minden szó rajzolható.
- **(c) Közös vágás tarthatatlan** — per-szó kezdet kötelező. (A leltár TELJES-NEZET sorának
  „NEVESÍTETT config-konstans dátumtól rajzol" keretezése **MÉRÉSSEL téves**: nincs közös konstans;
  a másodlagos nem növekvő lánc egy genezistől, hanem MAI-relatív fix ablak egyetlen normalizálásban →
  visszamenőleg nem lehet többet előhúzni, csak a meglévő ablakokat közös tengelyre VÁGNI.)

**Rendering-tények (MÉRT):**
- A vendor Chart.js-ben **nincs idő-adapter** (`TimeScale`+`_adapters` regisztrálva, de nincs
  date-fns/luxon/moment) → `type:"time"` DOBNA. Ezért a közös tengely = **`type:"linear"`** numerikus
  x (epoch-ms) + tick-callback dátumra. Adapter-függőség nélkül ad pontos kártyák-közti igazítást
  bármely rácson.
- A **másodlagos nyers** (`kulcsszo_masodlagos_nyers.json`) hordoz per-pont időbélyeget
  (`pontok:[{idopont_utc,ertek,reszleges}]`, nyaralás 93 pont 2026-05-15-től) → minden szó
  `{x:ms, y:ertek}` pontokként rajzolható a saját natív rácsán.

## Döntések (a user rögzítette)

1. **Közös tengely, közös bal szél** minden kártyán; a később kezdődő görbe később indul (üres bal = jel).
2. Minden szó a **leghosszabb ÉRVÉNYES** intervallumát adja (het→1_ev, nap→3_ho, ora→1_het/lánc),
   erre a közös tengelyre vetítve.
3. **Nincs rács-összefűzés, nincs átskálázás** kártyák között (§1.4: saját 0–100).
4. A **közös kezdet ADATBÓL SZÁMÍTVA** (ma 2025-08-10), NEM config-konstans, NEM beégetve →
   holnap magától tágul, ha valamelyik sorozat hosszabb lesz.
5. Vállalt következmény (nem kérdés): a nap-szavak a tengely ~75%-án, az órások ~99%-án üresek.
   Ez a lényeg — látni, melyik szóból mennyi van.
6. A benzin/nyugdíj 7 napja a **GATE** miatt van (`LANC_2HET_GATE`) → az a **2. kör** (LANC-ORAS
   Szelet 2), NEM itt oldjuk; a teljes nézet a lánc javítása után magától bővül.

## Rendering-modell (a mag)

- **x-tengely:** `type:"linear"`, **közös** `min = kozos_kezdet_ms`, `max = most_ms` MINDEN kártyán →
  a bal (és jobb) szél garantáltan egy helyen. Tick-callback: ms → dátum-string (nincs adapter, nincs Date-aritmetika a tickben a formázáson túl).
  - **`kozos_kezdet_ms`** = a per-szó választott intervallum ELSŐ LEZÁRT nyers pontjának
    legkorábbika (adatból; a „legkorábbi PONT", nem a nominális `ablak_kezdet_utc` — a kettő eltérhet,
    lásd 6c/RESZLEGES-RAJZOL perem). Ma: 2025-08-10.
  - **`most_ms`** = a választott intervallumok utolsó lezárt pontjának LEGKÉSŐBBIKE (**adatból, NEM
    böngésző-óra** — a kódbázis óra-tilalma, „nincs Date/rendszeróra"). Ma ~2026-08-18.
- **adat:** `{x: idopont_ms, y: ertek}` pontok a szó választott intervallumának nyers ablakából
  (`nyers_ablak(szo, iv.ablak_veg_utc, iv._forras)`), natív rács MEGMARAD. Hiányzó pont → a sorozat
  megszakad (`spanGaps:false`, mint ma — §7.5 nincs interpoláció).
- **y-tengely:** VÁLTOZATLAN `min:0 max:100` per szó.
- **regressziós/szint-vonal:** a meglévő `illesztes_vonal` (2 végpont, `idopont_utc`+`ertek`) és az
  esemenyjelzo `szint_vonal` a linear tengelyen is `{x,y}`-ként rajzolható (a végpontok dátumból).
  A meglévő guard marad (vonal CSAK ha mindkét végpont a rajzolt sorozaton). **tüntetés (esemenyjelzo)**
  a teljes nézeten is a szint-vonalat mutatja (szint != null) — SZEMLE-pont.
- A `chart_letrehoz` egy **elágazás**: teljes-mód → linear + `{x,y}`; egyébként a mai category-út
  **bájt-azonos** (a fix intervallumok viselkedése nem változik).

## Routing + közös kezdet (DOM-assertálható)

- **`teljes` ál-intervallum** a 6. gomb; felirat **„Teljes időszak"**, sub-szöveg
  **„a gyűjtés kezdetétől máig, szavanként eltérő indulással"** (a `GOMB_MAGYARAZAT` mintában).
  Elérhető, ha ≥1 szónak van ≥1 érvényes intervalluma (a fix-gombok elérhetőségének OR-ja).
  Az ALAPNÉZET VÁLTOZATLAN (1_het); a teljes nézet opt-in kattintással.
- **`teljes_valaszt(szoreg)`** (ÚJ, app.js): a szó `egyesitett_reg`-beli intervallumai közül a
  leghosszabb ÉRVÉNYES (= legkorábbi `ablak_kezdet_utc`) iv-t adja, vagy `null`-t, ha egy sincs.
  **Itt dől el a per-szó választás — ez a routing-mag.**
- **`teljes_kozos_kezdet(reg)`** (ÚJ): a fenti `kozos_kezdet_ms` számítása; a `#kulcsszo-blokk`
  `data-teljes-kezdet` attribútumába (YYYY-MM-DD).
- **per-kártya forrás-felirat** (ÚJ DOM-szöveg + `data-teljes-forras`): pl.
  *„adat forrása: heti sorozat (1 év), 2025-08-10-től"* — a választott iv `_racs` + kulcs + első pont
  dátumából. Assertálható.
- **ÚJ, KÜLÖN ok-kód:** `teljes_nincs_sorozat` → *„Ehhez a szóhoz még nincs rajzolható sorozat a
  teljes nézetben."* Csak akkor tüzel, ha `teljes_valaszt` `null` (egy érvényes intervallum sincs).
  Ma nulla ilyen szó → guard; szintetikus mind-érvénytelen szóval RED-elt. **Nem mosódik** a
  `nincs_masodlagos`/`oras_lanc_kell`/`nincs_lancolas`/`nincs_adat` kódokkal.
- **blokk-szintű felirat** (`frissesseg_szoveg` analóg): teljes-módban külön mondat
  („Teljes időszak — szavanként eltérő kezdet, közös tengely {kezdet}-től; a skálák szavanként 0–100,
  nem összemérhetők"), mert az `INTERVALLUMOK.find("teljes")` undefined lenne.

## Szeletek

### Szelet 1 — routing-mag (DOM-only, RED→GREEN)
- `teljes` gomb + sub-szöveg; `teljes_valaszt`; `teljes_kozos_kezdet` + `data-teljes-kezdet`;
  per-kártya `data-teljes-forras` + forrás-felirat; `teljes_nincs_sorozat` ok-kód; blokk-felirat.
- **RED-ek (valódi AssertionError névre/hibatípusra):**
  - `test_teljes_gomb_es_felirat` — „Teljes időszak" gomb + sub-szöveg jelen.
  - `test_teljes_per_szo_valasztas` — `data-teljes-forras` = várt intervallum (het→1_ev, nap→3_ho,
    ora→1_het) legalább 3 mintaszón (kórház/nyaralás/benzin).
  - `test_teljes_kozos_kezdet` — `data-teljes-kezdet` == 2025-08-10 (a min).
    **SZÁNDÉKOS-ZÖLD fedés MÉRVE:** min→max mutáció (vagy a min-loop kikapcsolása) PIROSÍT.
  - `test_teljes_ures_ok_kod` — szintetikus mind-érvénytelen szó → `data-ok="teljes_nincs_sorozat"`.
    Fedés MÉRVE: a régi kód valamelyikére cserélve a teszt piros.

### Szelet 2 — CANVAS (linear dátum-tengely)
- `{x,y}` shaper (párhuzamos a `racs_epit`-tel; teljes-módban a nyers ablak pontjait ms-x-re képezi,
  natív rács, `spanGaps:false`); `chart_letrehoz` elágazás (linear x, közös min/max, tick-callback);
  regressziós/szint-vonal `{x,y}`-ként.
- **Nem DOM-assertálható → SZEMLE (L9).** DOM-oldali horog, ami MÉRHETŐ: a teljes-mód aktív jelzése
  (`data-aktiv-intervallum="teljes"`) + a `data-teljes-kezdet`/`data-teljes-forras` (Szelet 1), és
  hogy a kártya rajzolható-e (`data-drawable`). A tengely-igazítás/relatív hossz **canvas-belső → SZEMLE**.

### Push
- **EGYETLEN push** Szelet 1+2 után, **SZEMLE UTÁN**. Szelet 1 önmagában a broken category-tengelyre
  route-olna → NEM pusholható (ZOLD-NEM-SZALLIT / GATE-tanulság). Csak fejlesztés, push nincs Szelet 1-nél.

## SZEMLE-terv (kötelező, push előtt; SZEMLE-SZABÁLY: két szó egy tengelyen)
Helyi `http.server`, váltás „Teljes időszak"-ra, majd:
1. **Bal szél egy helyen** 2025-08-10-nél (mindegyik kártya x-tengelye ott kezdődik).
2. **het szó** (kórház) teljes szélesség; **nap szó** (nyaralás) ~2026-05-tól (~75% üres bal);
   **ora szó** (benzin) a jobb szélen (~99% üres) — a relatív hosszak a MÉRT táblát tükrözik.
3. **Forrás-felirat** helyes szavanként (heti/napi/órás + kezdő dátum).
4. **tüntetés (esemenyjelzo)** a teljes nézeten is a **szint-vonalat** mutatja.
5. **benzin/nyugdíj 7 nap** (GATE — VÁRT; a 2. kör bővíti). Nincs hamis „nem érhető el".
6. **Konzol tiszta**; visszaváltás fix intervallumra → category-tengely visszaáll (nincs leak,
   `chart_takarit` mindkét módra jó).

## Leltár-jegyzet (a lezáró commitban)
- TELJES-NEZET (C) → LESZÁLLÍTVA (kész +1, törzs +1), önhivatkozó hash nélkül.
- A leltár TELJES-NEZET sorának „config-konstans dátum" keretezése **MÉRÉSSEL cáfolva** → a sor
  szövege a valós modellre (közös tengely, per-szó vágás, adatból számított kezdet) frissül.
- Invariáns MÉRÉSSEL újraszámolva.
- Ha SZEMLE-lelet PARKOLT sorként (egy mondat), nem külön kör.
