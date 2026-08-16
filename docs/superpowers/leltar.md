# Trendfigyelő — állapot-leltár (nyitott tételek, stabil ID-kkal)

Ez a fájl a projekt **ÁLLAPOTA**: mi nyitott, mi kész, mi lezárt. A
`.superpowers/sdd/progress.md` ledger a **DÖNTÉSEK** (miért) kronológikus naplója
marad; ez a leltár a követett (commitolt) állapot-nézet, ami túléli a chatet.
Ezzel oldjuk fel a §3-ban rögzített ledger↔repó ellentmondást (a ledger a
döntéseket rögzítette, az állapotot nem).

Utolsó frissítés: 2026-08-16.

## Hogyan frissítsd

- **a)** A leltár állapot-frissítése **UGYANABBA A COMMITBA** megy, amelyik a
  tételt lezárja vagy módosítja — nem külön körben, nem utólag.
- **b)** Az ID-k **soha nem újrahasznosíthatók és nem átszámozhatók.** Új tétel =
  új ID. Lezárt tétel a **LEZÁRT / ELAVULT** szakaszba kerül, **nem törlődik**.
- **c) INVARIÁNS (frissítéskor ellenőrizd):**
  `aktív + kész + nem-task rekord + félretett = törzs-sorszám`.
  Most: **33 + 12 + 11 + 1 = 57**. A **LEZÁRT / ELAVULT** külön számolódik: most **11**.
  Ha ez az egyenlőség nem áll, a leltár driftel.
- **d)** **Önhivatkozó hash TILOS:** a leltár nem tartalmazhatja a SAJÁT lezáró commitja
  hash-ét (nincs „(ez a commit)" placeholder sem, ami bent ragad). A lezáró sor állapota
  „LESZÁLLÍTVA (lásd git log)"; a tényleges hash-t a push után a KÖVETKEZŐ ATADAS pinneli
  (mint a hat eredeti LESZÁLLÍTVA-tételnél). MÁS, MÁR LÉTEZŐ commit hash-ére hivatkozni szabad.

Mezők: **ID | Név | Fázis | Állapot | MÉRT/BECS | Futásra hat | Méret | Függ**.
Méret: S (<20 sor) / M (20–80) / L (80+) / XL (több task).

---

## LESZÁLLÍTVA — a ledger nem jelölte késznek, itt rögzítve (12)

| ID | Név | Fázis | Állapot | M/B | Futásra hat | Méret | Függ |
|---|---|---|---|---|---|---|---|
| LEGFRISSEBB-GUARD | nulla-adatos futás NE írja felül üressel a jó legfrissebb.json-t (az EGYETLEN feltétel nélküli kanonikus felülíró; tortenet/napi/nyers már guardolt); feltétel: not(top_trendek or trend_idosorok or kulcsszavak); hangos FIGYELEM + megnevezi az üreseket; kapcsolódik: SUCCESS-VAK (bemeneti testvér); ÉLESBEN IGAZOLVA (run 31888919931) | Ph3 | LESZÁLLÍTVA (lásd git log) | MÉRT | igen (kimenet) | S | — |
| L4 | Kliens-plafon HANGOS szelep: PlafonTullepve(RuntimeError) propagál (3 elnyelő hely szűrve) + részleg-mentés (.reszleges / másodlagos per-szavas upsert) + KILEPES_PLAFON=2 exit; PLAFON_OVERRIDE env CSAK csökkenthet (min, hangos); a KUDARC-VAK plafon-tagját zárja (SUCCESS-VAK/FOLYT NYITVA). **CI-piros-út MÉRT IGAZOLVA** (run 31888919931, bot-commit e73299e: job PIROS + always()-adat-commit + legfrissebb védve, 0 valódi hívás) | Ph3 | LESZÁLLÍTVA (lásd git log) | MÉRT | igen (viselkedés) | M | — |
| PIPEFAIL | napi.yml explicit `set -o pipefail` — az L4 exit 2 NE vesszen el a `| tee run.log` mögött (helyben igazolva: pipefail nélkül exit=0, vele 2; élesben: exit code 2 → job PIROS) | Ph3 | LESZÁLLÍTVA (504103c) | MÉRT | igen (CI-jelzés) | S | — |
| PLAFON-OVERRIDE | PLAFON_OVERRIDE env (CSAK csökkent, min; hangos) + napi.yml dispatch-input (cron-BIZTOS: schedule → '' → némán None) — a (c) CI-piros-út igazolás előfeltétele; env-hook c60ae76, plumbing 7fab4db | Ph3 | LESZÁLLÍTVA (7fab4db) | MÉRT | igen (CI-teszt) | S | — |
| LEDGER-HIG | állapot-leltár követett fájlba + a 6 hash rögzítése | fázis-függ. | LESZÁLLÍTVA (6f4091d) | MÉRT | nem | S-M | — |
| PH4-T1 | config racs-mező (viselkedés-változás nélkül) | Ph4 | LESZÁLLÍTVA (486b3c7) | MÉRT | nem | — | — |
| PH4-T2 | másodlagos nyers kimenet (N=3 adat-relatív retenció) | Ph4 | LESZÁLLÍTVA (9279f35) | MÉRT | igen | — | — |
| PH4-T3 | másodlagos gyűjtő-ág + %7 hétnap-ütemezés | Ph4 | LESZÁLLÍTVA (71c2a95) | MÉRT | igen | — | — |
| PH4-T4 | elavultság-jelzés (A — backend + run.log) | Ph4 | LESZÁLLÍTVA (a16e5e9) | MÉRT | igen | — | — |
| PH4-SPEC | phase4-spec + phase3 §1.4.1/§8.2 bővítés | Ph4 | LESZÁLLÍTVA (d2fe35b) | MÉRT | nem | — | — |
| PH4-T6a | rács-tudatos regresszió (nap/het + esemenyjelzo szint) | Ph4 | LESZÁLLÍTVA (75839d0) | MÉRT | igen (ma este 1. éles) | — | — |
| RACS-EGYSEG | rács-tudatos jel-erősség felirat (a 6b ELSŐ szelet): a merteszamok_szoveg rács-SZAVA (óra/nap/hét) a szó `racs`-ából, `"ora"` default (az órás JSON nem hordoz racs-ot → órás felirat bájt-azonos, nulla séma-változás); ismeretlen rács → LÁTHATÓ `"? <érték>"` (nem undefined, nem néma „óra" — KUDARC-VAK-elhárítás); a mértékegység („/nap") mérve rács-INVARIÁNS, kimarad; a RAJZOLÁS (racs_epit/ora_index/x-tengely/tooltip) a KÖVETKEZŐ, nagyobb 6b-szelet (lásd 6b sor) | Ph4 | LESZÁLLÍTVA (lásd git log) | MÉRT | nem (frontend felirat) | S | — |

## META / FOLYAMATBAN (0)

— (üres — a LEDGER-HIG leszállt: 6f4091d, lásd LESZÁLLÍTVA)

## (B) Phase 3 / korábbról örökölt (24 — 23 nyitott + 1 félretett)

| ID | Név | Fázis | Állapot | M/B | Futásra hat | Méret | Függ |
|---|---|---|---|---|---|---|---|
| L1 | B2 elavultság-jelzés a FRONTENDEN (a felület mutassa a szó elavultságát) — a PH4-T4 backend/run.log párjának UI-oldala | Ph3 | NYITOTT | MÉRT/BECS | igen (megjel.) | M | PH4-T4 |
| L6 | nulla-arány középső sáv (12–90%) őrizetlen (7 szó, a 9b csak a szélsőket) | Ph3 §11.2 | NYITOTT | MÉRT | igen (megjel.) | M | részben: rács-bővítés |
| L7 | parositas bemenet-perzisztálás / a WHY nem auditálható | Ph3 | NYITOTT (irány kész) | MÉRT | nem (diagnoszt.) | M | — |
| L8 | RSS↔trend párosítás hirrel=0 (3 adatpont, mind 0) | Ph3 | NYITOTT | MÉRT | nem | M | L7; blokkolja Task 7 |
| L9 | „chart csak színez" invariáns nem őrizhető (canvas-belső) → kézi szemle | Ph3 | RÉSZBEN (auto-teszt elvetve) | MÉRT | nem | — | — |
| L11 | legfrissebb.json ~44–46% redundáns (trend_idosorok dup, 337KB) | Ph3 | NYITOTT | MÉRT | igen (kimenet) | M-L | — |
| L12 | párhuzamos Playwright flaky (soros a mérvadó) | Ph3 | NYITOTT | MÉRT | nem (teszt) | M | gyökér-ok nem mérve |
| MINOR-2 | retenció-horgony robusztusság (befagyás / jövőbeli ablak_veg kivág) | Ph2.5 §11.7 | NYITOTT | BECS | igen (adatvesztés) | M | láncolás tervezés |
| §11.8 | betegség/kórház éves átfedés | Ph2.5 | NYITOTT (kutatás) | BECS | nem (felület nem) | S-M | — |
| VENV | venv 3.14 vs CI/átadó 3.12 | Ph2.5 | NYITOTT (nem blokkoló) | MÉRT | nem | S | — |
| SEMA | sema_legfrissebb topics/temak szigorítás (megengedő→kötelező) | Ph3 (3a) | RÉSZBEN (indítható, nem lezárt) | MÉRT | nem | S | — |
| MIN-BC | borderColor #3366cc magic literal (app.js) | Ph3 (8a) | NYITOTT (minor) | MÉRT | nem | S | — |
| MIN-TCP | trend_chart_peldanyok kulcs-kollízió (árva Chart, memória) | Ph3 (8a) | NYITOTT (minor) | MÉRT | nem (memória) | S | — |
| T21 | kategória-chart jelenlétének explicit assert-erősítése | Ph3 (8a) | NYITOTT (minor) | MÉRT | nem (teszt) | S | — |
| MIN-CSS | CSS-sorrend app.css:40-41 (date-select szabály a vezérlő közé ékelődött) | Ph3 (T10) | NYITOTT (minor, csak ATADAS-08-11:184) | MÉRT | nem | S | — |
| SUCCESS-VAK | success-vakság — elveszett kulcsszó-nap = ZÖLD workflow (exit 0) | Ph3 §10 | NYITOTT | MÉRT (08-11) | igen (diagnoszt.) | M | — |
| 429-RATA | 429-ráta jellemzése (n=1, több nap napló kell) | Ph3 | NYITOTT (mérés) | MÉRT | nem | S / folyamatos | több nap napló |
| GORBE-B | „minden kártyán legyen görbe" (B) | Ph3 | FÉLRETETT | MÉRT | igen (megjel.) | L | 429-RATA |
| FOLYT | folytonossag él-trigger vs állapot-check | Ph3 | NYITOTT (eldöntendő) | MÉRT | nem (napló) | S-M | SUCCESS-VAK |
| NAPLO-MENTETT | naplo.csv „mentett-szám" 6. oszlop (a részleges-mentés fixből) | Ph3 | NYITOTT | MÉRT | igen (napló-séma) | S-M | — |
| NAPTAR | naptáras (tól–ig) intervallumválasztó (elég-e az 5 fix ablak) | Ph3 | NYITOTT (9b után) | BECS | nem | M-L | — |
| KAT-GORBE | kategória heti/havi görbe | Ph3/4-jelölt | NYITOTT (felvetés, nincs terv) | BECS | igen (új kimenet) | L | — |
| KAT-TABLA | kategória heti táblázat | Ph3/4-jelölt | NYITOTT (felvetés) | BECS | igen | M-L | — |
| KULCS-LISTA | kulcsszó-lista bővítés (nincs diszkrét repó-nyom, csak ambient) | Ph3 | NYITOTT (ambient) | BECS | igen (config) | S-M | — |

## (C) Phase 4 hátralévő (4)

| ID | Név | Fázis | Állapot | M/B | Futásra hat | Méret | Függ |
|---|---|---|---|---|---|---|---|
| TASK5 | staleness-vezérelt ütemező (tie-break=config-index) | Ph4 | NYITOTT | BECS (terv kész) | igen | L | 6a megfigyelés (1-2 futás) |
| 6b | nem-órás (nap/het) megjelenítés a felületen | Ph4 | RÉSZBEN (LESZÁLLT: RACS-EGYSEG felirat + Szelet1 [racs_epit slot-index] + Szelet2 [másodlagos fogyasztás + egyesitett_reg routing + rács-tudatos üres-állapot + guardok] + Szelet3 [SZEMLE-JAVÍTÁS: a másodlagos MAGA adta nincs_lancolas/keves_pont rács-tudatosan fordítva → rovid_masodlagos/rovid_het_ablak, hosszú intervallum SOHA nem 'összefűzött nap'; default→1_het — ALAPNEZET-VEGYES lezárva]; kód-kész és tesztelt [78 e2e], Szelet2 subagent-review; a ZÁRÓ KAPU a MEGISMÉTELT VIZUÁLIS SZEMLE — utána LESZÁLLÍTVA; HÁTRA külön tétel: 6c szint-vonal) | BECS | nem (frontend) | L | 6a valós adat |
| 6c | tüntetés szint-vonal (medián, „stabil szint", nincs trendvonal) | Ph4 | NYITOTT (döntés kész) | MÉRT | nem | M | 6b |
| LANC-ORAS | órás láncolás (2_het+; kumulált skálázó tartós tárolása) | Ph4 §8.2 | NYITOTT | BECS | igen (új kimenet) | XL | §8.2-INV |

## (D) Ma (2026-08-13..16) nyitott új tételek (17 — 6 nyitott + 11 rekord)

| ID | Név | Fázis | Állapot | M/B | Futásra hat | Méret | Függ |
|---|---|---|---|---|---|---|---|
| IRANY-KUSZOB | irány-küszöb rács-tudatossá: a nap/het ág ABLAK-RELATÍV (\|meredekseg×span\| < 7 pont = a skála %-a), az órás per-nap 1.0 VÁLTOZATLAN (0 címke-eltérés valós nyers adaton); a másodlagos metaadat is javítva (elmozdulas_kuszob a félrevezető irany_kuszob helyett). A 7,0 az órás kalibráció átvitele, ELSŐ közelítés (5 intervallum mintája). LEZÁRHATÓ, ha ≥15 nap/het intervallumon újramérve a 7,0 továbbra is TERMÉSZETES HÉZAGBA esik ÉS elválasztja a stagnal/nem-stagnal halmazt (most a 2,89↔13,10 közti ~10 pontos hézagban ül); ha a tömeg a küszöb köré csúszik → újrakalibrálás | Ph4 | RÉSZBEN | MÉRT (08-15) | igen (címke) | M | ADD-SWAP |
| KUDARC-VAK | „nem tud kudarcot jelezni" hibaosztály — ma NÉGY tag került elő: **L4** (plafon, LESZÁLLT + élesben igazolt) + **SUCCESS-VAK** (bemenet: néma üres-sorozat skip) + **FOLYT** (él-trigger) + **LEGFRISSEBB-RESZLEGES** (kimenet: részleges felülírás). Közös minta: van_adat=True / exit0 / néma skip elfedi a rossz állapotot. SUCCESS-VAK/FOLYT/LEGFRISSEBB-RESZLEGES NYITVA | Ph3/4 | REKORD (lelet) | MÉRT (08-14..15) | igen (diagnoszt.) | — | SUCCESS-VAK, FOLYT, LEGFRISSEBB-RESZLEGES |
| VEZERLO-MAGAS | a rács-tudatos üres-feliratok (Szelet 2) 234px-re növelik az intervallum-vezérlőt, ha egy szónak SINCS másodlagos adata (mind a 4 hosszú gomb tiltott, hosszú felirattal) → mobilon az első kártyát a hajtás alá tolja (MÉRT: vezérlő 234px, első kártya top=787px 380×320-on). MA nem jelentkezik (4 szónak van másodlagosa → az aggregált hosszú gombok ENGEDÉLYEZETTEK → nincs feliratszöveg → rövid vezérlő), DE friss telepítésen (0 másodlagos) vagy a kulcsszó-lista bővülésekor a szintetikus eset lesz a valóság | Ph4 | REKORD (megfigyelés) | MÉRT (08-16) | nem (megjel.) | S | KULCS-LISTA |
| MASODLAGOS-RACS-HIANY | ELMÉLETI (subagent-review 08-16): ha egy másodlagos szó `racs` NÉLKÜL érkezne (generátor-hiba), az egyesitett_reg `_racs=undefined`-et adna → slot_index az „ora" ágra esik (napi pontok 24-slotos ritka rácson = megszakadozó görbe) + „óra nem-nulla" címke napi adatra. Nem hamis ÉRTÉK, csak félrevezető címke+rács; kivétel nincs. VALÓS adaton nem fordul elő (a backend minden másodlagos szóhoz ír racs-ot — mérve 4/4). Aszimmetria: az órás ág védekező `o.racs || "ora"`-t használ, a másodlagos ág nyers `m.racs`-ot. Keményítés opcionális (explicit hiány-jelzés, NEM néma default) | Ph4 | REKORD (ELMÉLETI) | ELMÉLETI | nem (megjel.) | S | — |
| ALAPNEZET-KONSTANS | a default `1_het` BEÉGETETT konstans (nem futásidőben számított „legtöbb-kártya" intervallum). Ma helyes (13/13 rajzol), mert csak 4 szónak van másodlagos adata. ÚJRAMÉRENDŐ a Task 5 utáni lefedettségnél: ha több szó kap másodlagost, a legtöbb kártyát rajzoló intervallum eltolódhat → a beégetett 1_het rács-vakká válhat (a MIN_PONT és irany_kuszob után a HARMADIK ilyen konstans). Spec: phase3 §7.2 REVÍZIÓ (c1cd784) | Ph4 | REKORD (megfigyelés) | MÉRT (n=4, 08-16) | nem (megjel.) | S | TASK5 |
| MASODLAGOS-OK-NEV | a másodlagos regresszió `nincs_lancolas`/`keves_pont` ok-ot ad nap/het rácson (§9: a nap/het ágon nincs láncolás), a frontend STRING-ILLESZTÉSSEL fordítja (egyesitett_reg: nincs_lancolas→rovid_masodlagos; keves_pont+het→rovid_het_ablak). Egy backend ok-ÁTNEVEZÉS NÉMÁN elrontaná (a régi „összefűzött nap" visszatérne). Diszkriminátor: a másodlagos ENTRY (miv) léte + miv.ok + m.racs az ÜRES-ágon (az üres iv NEM hordoz _racs-ot → miv/m.racs a helyes kulcs, nem _racs). A het-szűkítés STRUKTURÁLIS (nem n=4): het 2_het/1_ho = 2/4 hét < RACS_MIN_PONT[het]=7 → mindig keves_pont (rács-durva a rövid ablakhoz); nap keves_pont ellenben valódi ritkulás (14 nap ≥ MIN_PONT 12, csak lyukaknál). Backend-javítás (nap/het saját ok-kód) külön kör | Ph4/backend | REKORD (megfigyelés) | MÉRT+STRUKT (08-16) | nem (megjel.) | S-M | — |
| PLAFON-128 | a Task 5 átírja a `tervezett_hivasszam` jelentését → a 128-as hívás-plafon ÚJRANÉZENDŐ a Task5 tervénél (L4 backstopként MOST ráépült — a plafon hard-abortot okoz) | Ph4 (új) | REKORD/MEGKÖTÉS | MÉRT | igen | — | TASK5, L4 |
| MASODLAGOS-PLAFON | a plafon a másodlagos ágban (utolsó ág) is üthet → propagál + exit 2, DE a napló 'kihagyva'-t ír (nem 'plafon'), és a másodlagos-propagáció+címke NINCS külön tesztelve; külön 'plafon'-jelölő + teszt = külön TDD-kör | Ph4 (új) | NYITOTT (kis) | MÉRT (08-15) | nem (napló-címke) | S | L4 |
| LEGFRISSEBB-RESZLEGES | RÉSZLEGES adatnál a legfrissebb_ir a jó TELJES fájlt hiányossal írja felül (pl. kulcsszó-ág 429 → kulcsszavak üresen kiíródik, van_adat=True → a total-empty guard NEM szól). IGAZOLT: ReszlegesKliens kod=0, de a payload mind 0. Külön kör: komponens-szintű merge/guard + partial-FIGYELEM. Testvér: SUCCESS-VAK (bemenet) / LEGFRISSEBB-GUARD (total) | Ph3/4 (új) | NYITOTT | MÉRT (08-15) | igen (kimenet) | M | — |
| NEVER-COLL | never-collected nem-ora szavak láthatósága | Ph4 (új) | NYITOTT (Task5 után) | MÉRT | igen | S-M | TASK5 |
| ADD-SWAP | „hozzáadás vs csere" rács-váltásnál (előbb mérünk) | Ph4 (új) | NYITOTT | BECS | igen (config) | M | több nap mérés |
| §8.2-INV | „a lezárt szakasz sem invariáns" csúcs-váltásnál (csak órás lánc) | Ph4/spec (új) | NYITOTT | MÉRT (§1.4.1) | nem | M-L | LANC-ORAS |
| TIE-BREAK | Task5 tie-break = config-index (nem ábécé) | Ph4 (új) | REKORD/MEGKÖTÉS | MÉRT | — | — | TASK5 |
| PC-RACS | P/C mérőszámok rács-specifikusak (nem vihetők át) | Ph4 (új) | REKORD/MEGKÖTÉS | MÉRT | nem | — | — |
| API-CSV | API vs webes CSV: napi 93 vs 90 pont (webes export 3 nappal rövidebb) | Ph4 (új) | REKORD (lelet) | MÉRT | nem | — | — |
| §1.4.1 | ablak-relatív újranormálás (69/71 bájt-azonos, harmadik mechanizmus) | Ph4/spec | REKORD (megfigyelés) | MÉRT | nem | — | táplálja §8.2-INV |
| HET-MINPONT | het MIN_PONT=7 önmagában gyenge; a védelmet a rács-szűrés adja | Ph4 (új) | REKORD/MEGKÖTÉS | MÉRT | nem | — | — |

## LEZÁRT / ELAVULT (11 — külön, nem a törzsben)

| ID | Név | Fázis | Állapot / miért nincs a nyitottak közt |
|---|---|---|---|
| ALAPNEZET-VEGYES | vegyes kezdő-nézet (a leghosszabb-érvényes default miatt) | Ph4 | LEZÁRVA — 2026-08-16, 6b Szelet 3: a default 1_het-re állt (a legtöbb kártyát rajzolja), a vegyes kezdő-nézet megszűnt. A régi „leghosszabb érvényes" (spec 7.2) feltevése a másodlagossal megtört (1_ev: 1/13) |
| L2 | trend_megjelenites_max nincs config.yaml-ban (csak config.py default 25) | Ph3 | LEZÁRVA — 2026-08-15 user-döntés: a default (25) áll; kommentelt config.yaml-sor a következő érdemi commit mellékleteként |
| L3 | naplo_max_sor komment elavult (~500 nap → ~333) | Ph3 | LEZÁRVA — átkeresve (naplo.py, config.py, phase3-spec.md), elavult komment NEM TALÁLHATÓ (2026-08-15) |
| L5 | parositas nem_egyezok determinista sorrend nem őrzött | Ph3 | LEZÁRVA — output determinista, HASHSEED=0 mellett is zöld (mért 2026-08-14, 278 passed); a történeti „bukik" pre-fix kódon készült, a `futtato.py` determinista-by-design javítás (RSS-sorrendű lista) óta zöld |
| L10 | mobil-geometria / rootMargin | LEZÁRT — Task 10 kész (ATADAS-08-12: „L10 LEZÁRVA") |
| PERIODICITÁS | periodicitás-diszkriminátor | LEZÁRT — 2026-08-13 user-döntés, 4 indokkal |
| §8.2-nap/het | láncolás a nap/het rácson | FELOLDVA — nem-órásnál nincs láncolás (2026-08-14 lelet) |
| MIN_PONT~168 | „MIN_PONT ~168-ra hangolt" | ELAVULT/JAVÍTVA — valójában rács-arányos ⌊ablak/7⌋ (ora 24 / nap 12 / het 7); a RACS_MIN_PONT konstans tartja, a `_intervallumok` választja ki rácsonként, a `regresszio_egy_ablak` érvényesíti; IMPLEMENTÁLVA (75839d0) |
| RACS-KERDES | per-szó rács kérdése | LEZÁRT — PH4-T1..T3 + PH4-T6a |
| SESSION-UUID | Claude-Session trailer séma | LEZÁRT — a UUID a hiteles azonosító (konvenció rögzítve) |
| AGSORREND | ágsorrend n=3 kapu-blokk a pótolhatatlan órás ágra | LEZÁRT-DÖNTÉS — nem javítjuk, nem módosítunk sorrendet (USER-DÖNTÉS, progress.md:1472-73). MÉRT (n=3); futásra hat, de tudott és elfogadott |
