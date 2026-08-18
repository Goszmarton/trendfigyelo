# Terv — Task 5: staleness-vezérelt másodlagos ütemező (Szelet 2)

Dátum: 2026-08-18. Fázis: Phase 4. Előzmény: RETROSPEKTÍV MÉRÉS (nem n=1-2 élő megfigyelés — a valós adat már a
lemezen: naplo.csv ~333 nap, kulcsszo_masodlagos_nyers.json).

## 0. MÉRT ALAPOK (retrospektív, a meglévő adatból)

- **Jogosult készlet:** a `masodlagos_szavak_ma` bemenete `racs≠"ora"` = **11 szó** (csak benzin+nyugdíj órás).
  → a másodlagos lefedettség PLAFONJA **11, NEM 13**; benzin/nyugdíj órás-only, JOGOSULATLAN a másodlagosra
  (de a napi órás ágban gyűlnek). Task 5 önmagában **11-re visz, nem 13-ra**.
- **%7 ma is 2/nap:** 11 szó → 2-2-2-2-1-1-1 (Hét-Csüt 2, Pén-Vas 1). Egy szó a saját `nem_oras-index % 7`
  hétnapján fut, HETENTE EGYSZER.
- **Lefedettség (08-18):** 7 gyűjtve (albérlet/tüntetés 08-13, akciós újság 08-14, nyaralás 08-15, kórház 08-16,
  állás/betegség 08-17), 4 SOHA (kormányablak/napelem → 08-19 Kedd; eladó lakás/hitel → 08-20 Szerda).
- **429-történet:** a masodlagos ág 5/5 nap (08-13..17) SIKER, 0×429 → van fejtér a 2/nap-hoz (napi ~33 hívás ≪ 148 plafon).
- **Adatmennyiség (MÉRT):** %7 = **11 gyűjtés/hét**, max-kor 7 nap, kimaradt szó → **14 nap** büntetés.
  staleness+cap2 = **14 gyűjtés/hét** (+27%), refresh-ciklus 6 nap, kimaradt szó → **1 nap** recovery.

## 1. A TASK 5 VALÓDI HASZNA (a korábbi „lefedettség" indoklás HAMIS)

A %7 EGY TELJES HÉT alatt körbeér → ~08-20-ra mind a 11 szó gyűlik **Task 5 NÉLKÜL is**. Tehát a haszon NEM a
lefedettség, hanem:
- **(a) kimaradt nap recovery:** ma egy kimaradt szó 7 NAPOS büntetést kap (a következő hétnapjáig); a staleness a
  legelavultabbat választja → a kimaradt szó MÁSNAP behozódik (14 nap → 1 nap).
- **(b) never-collected prioritás/latencia:** egy ÚJ szó (KULCS-LISTA bővülés) ma akár 7 napot vár a hétnapjára;
  staleness-szel a None=max-elavult → MÁSNAP gyűlik.
- **(c) az 5. rejtett kalibráció-feltevés megszüntetése (CÉL, nem mellékhatás):** a %7 IMPLICIT ≤14 nem-órás szót
  feltételez (afölött egy hétnap 3 szót adna → túllépné a MAX_MASODLAGOS_NAPI=2 fejteret → plafon-kockázat a
  KULCS-LISTA bővülésekor). Az explicit `[:MAX_MASODLAGOS_NAPI]` cap ezt CÉLZOTTAN kiiktatja. (MIN_PONT /
  IRANY-KUSZOB / ALAPNEZET-KONSTANS / trend_idosor_max után az ÖTÖDIK.)

**LELTÁR-KÖVETKEZMÉNY:** az ALAPNEZET-KONSTANS / SZINT-VONAL-VAK / IRANY-KUSZOB NEM a Task 5 leszállásától
oldódik fel, hanem NAPTÁRI IDŐTŐL / config-tól — tételenként a valós feltétel (a leltárban javítva).

## 2. A CSERE (Szelet 2, backend, TDD)

`masodlagos_szavak_ma(config, most)` %7-logikája → staleness-rangsor:
- újrahasznosítja a MEGLÉVŐ `nyers_kimenet.elavult_masodlagos_szavak(sorozatok, most)`-ot (a
  `kulcsszo_masodlagos_nyers.json`-ból, mint a `_jelez_elavult_masodlagos` ma), **config-index tie-break**-kel
  (NEM ábécé — TIE-BREAK), **EXPLICIT `[:MAX_MASODLAGOS_NAPI]` cap**-pel;
- None (never-collected) = max elavult → legelöl.

## 3. BLOKKOLÓ (kiegészítés 1) — az ÚJ I/O-FÜGGŐSÉG kezelése KÖTELEZŐ

Ma `masodlagos_szavak_ma` TISZTA. A Szelet 2 után I/O-függő lesz (olvassa a másodlagos nyers fájlt) → egy
ütemező-finomítás miatt az EGÉSZ napi gyűjtés elbukhatna. Ez a FRISS-RESZLEGES-URES mintázat ugyanazon a helyen.
**SZERZŐDÉS:** ha a `kulcsszo_masodlagos_nyers.json` HIÁNYZIK / ÜRES / JSON-hibás → az ütemező NE dobjon, NE
állítsa meg a napi futást; **FALLBACK: a config-index sorrend első ≤MAX_MASODLAGOS_NAPI nem-órás szava** +
HANGOS FIGYELEM (nevezze meg: melyik fájl, mi a hiba, mi a fallback). (Ez egyben a friss telepítés esete is:
nincs másodlagos nyers → fallback a config-index elejére.)

## 4. RED-EK (5 db, test-oldali dublőr → AssertionError; kiegészítés 2: MEGKÜLÖNBÖZTETHETŐK)

Mind a 4+1 a régi %7-en pirosodik, DE KÜLÖNBÖZŐ viselkedést fed — a RED-jelentésben mind az 5 TÉNYLEGES
hibaüzenetét mutatom, és melyik állítás milyen KÜLÖNBÖZŐ okból bukik. Ha kettő szó szerint ugyanazt írja → jelzem.
1. `test_masodlagos_legelavultabb_elol` — a legelavultabb ≤2 szó (nem a hétnap). Fed: staleness-RENDEZÉS.
2. `test_masodlagos_never_collected_prioritas` — a None (soha) szavak ELÖL. Fed: None=max-elavult KEZELÉS (külön a kortól).
3. `test_masodlagos_tie_break_config_index` — azonos elavultság → config-index (NEM ábécé). Fed: TIE-BREAK szabály.
4. `test_masodlagos_cap_max_napi` — >2 elavult esetén is PONTOSAN ≤MAX_MASODLAGOS_NAPI. Fed: az EXPLICIT CAP (5. feltevés).
5. `test_masodlagos_sorozat_hiany_nem_all_le` — hiányzó/üres/hibás nyers → NEM dob, fallback config-index + FIGYELEM.
   Fed: az I/O-ROBUSZTUSSÁG (kiegészítés 1). RED (a naiv csere-implementáción): a fájl-olvasás dobna → a futás elszáll.

**SZÁNDÉKOS-ZÖLD (SZANDEKOS-ZOLD-VAK: a fedést MÉREM):** `test_plafon_invariáns_task5_utan` — `tervezett_hivasszam`=35
és a plafon=148 VÁLTOZATLAN. A fedést mutációval igazolom (pl. a cap elhagyása / MAX_MASODLAGOS_NAPI 2→3 pirosítja-e);
ha 0 fedés → cserélem.

## 5. MÉRET + SZELET 3

- **Szelet 2:** ~20-30 sor (`elavult_masodlagos_szavak` újrahasznosítás + config-index tie-break + cap + I/O-fallback);
  `masodlagos_szavak_ma` új `sorozatok`/fájl-olvasás bekötése. Backend, nincs szemle-kapu. A plafon NEM változik.
- **Szelet 3 (záró):** NEVER-COLL zárása a Szelet 2 futásának fényében (priorizálta-e a soha-gyűjtötteket) +
  TIE-BREAK LESZÁLLÍTVA + a „11 nem 13" plafon + az 5. rejtett feltevés + a leltár-függőség-javítások megerősítése.
  **MELLÉKHATÁS (előjegyezve, most NEM javítva):** a `_jelez_elavult_masodlagos` UGYANAZT a rangsort használja,
  mint mostantól a KIVÁLASZTÁS → a figyelmeztetés valószínűleg ÖRÖKRE elnémul (a kiválasztott szó már nem elavult).
  Szelet 3-ban eldöntendő: elnémul-e, és ha igen, marad-e értelme (pl. a NEM-kiválasztott, de küszöb feletti szóra).
