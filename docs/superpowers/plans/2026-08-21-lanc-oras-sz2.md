# LANC-ORAS Szelet 2 — a 2_het+ órás nézet a LÁNCBÓL rajzol (a GATE feloldása)

Dátum: 2026-08-21
Hatókör: **backend GATE-off + frontend lánc-pont-forrás.** A canvas köztes állapotánál
**VIZUÁLIS SZEMLE KÖTELEZŐ** (SZEMLE-SZABÁLY, ZOLD-NEM-SZALLIT) — a zöld suite NEM elég.
NEM hatókör: a tüntetés csonka láncának javítása (LANC-SZAKASZ-TORES, külön), 3b (per-interval
rács canvas), IRANY-KUSZOB, ADD-SWAP, TASK5, a H4/I3 felirat-lelet.

## 1. Cél

A `LANC_2HET_GATE` feloldása: az órás 2_het+ ne maradjon `nincs_lancolas`, hanem a
perzisztens `kulcsszo_lanc.json`-ból (LANC-ORAS Sz1) szeletelt, átskálázott sorozatból
rajzoljon. A backend (`regresszio._intervallumok`) a gate mögött MÁR képes rá; a Sz2
feloldja a gate-et ÉS a frontendet a láncból-rajzolásra hangolja.

## 2. Vezérelvek

- **A frontend NEM SZÁMOL.** A 2_het+ pontjait és illesztes-vonalát a backend a láncból
  adja; a frontend csak a helyes forrás-fájlból (`kulcsszo_lanc.json`) veszi a rajzolt pontokat.
- **A canvas EGYETLEN őre a vizuális szemle** (SZEMLE-SZABÁLY). A zöld suite nem elég.
- **Látható, nem néma.** Ahol a lánc rövid (tüntetés / 1_ho+), a nézet üres marad a
  meglévő ok-felirattal — nem kitalált görbe.

## 3. Hatókör — fájl:függvény:sor

Backend:
- `regresszio.py:37` — `LANC_2HET_GATE = True` konstans TÖRLÉSE.
- `regresszio.py:242` — a `if lanc and not LANC_2HET_GATE and …` feltételből a `not LANC_2HET_GATE and` kivétele.
- `regresszio.py:32-36` — a GATE-magyarázó komment frissítése/törlése.

Tesztek:
- `tests/test_lanc.py:86-94` (`test_oras_2het_gate_amig_frontend_nem_olvas`) — TÖRLÉS (a gate-szerződés megszűnik).
- `tests/test_lanc.py:77-83` (`test_oras_2_het_lancolt_ervenyes`) — FRISSÍTÉS: a `monkeypatch.setattr(…LANC_2HET_GATE,False)`
  törlendő (a törölt attr-ra a monkeypatch raise-elne); a teszt ezután FELTÉTEL NÉLKÜL őrzi a
  „2_het ervenyes a láncból" backend-viselkedést.

Frontend (`docs/js/app.js`):
- `:35` (loader) — `"kulcsszo_lanc.json"` felvétele a `kulcsszo-blokk` fájllistájába.
- `:236-243` (`egyesitett_reg`) — az érvényes órás intervallumnál, ahol `X !== "1_het"`,
  `_forras: "kulcsszo_lanc.json"` (a láncból rajzol); az 1_het marad `kulcsszo_nyers.json`.
- `:653` (`nyers_ablak`) — a lánc-forrás alakja EGY rekord (nem lista): külön ág, ablak_veg-egyezés
  + van-pont → visszaadja a rekordot (a `racs_epit` slot-logikája változatlanul kezeli az órás pontokat).

## 4. ERVENYES-ROUTING — a routing-vágás (a 3× tévesnek bizonyult besorolás)

- MEGLÉVŐ backend→frontend: az órás intervallum `ervenyes` flagje (backend) vezérli az
  `egyesitett_reg` órás-címkézését. A gate törlése után a 2_het `ervenyes` → órásként routolódik.
- ÚJ, TUDATOSAN FRONTEND-OLDALI: a forrás-fájl választása (`X !== "1_het"` → lánc) a FRONTENDBEN
  dől el, **NEM új backend mező** — hogy ne nőjön a backend→frontend routing-felület.
- **REJTETT FELTEVÉS NEVESÍTVE:** ez `RACS_ABLAK_NAP["ora"] == 7`-re támaszkodik — az órás nominál
  ablak 7 nap (=1_het), ezért MINDEN hosszabb érvényes órás intervallum a láncból jön. Ha ez a
  konstans valaha változik, a `X !== "1_het"` heurisztika törik. A MIN_PONT / IRANY-KUSZOB /
  ALAPNEZET-KONSTANS / RESZBEN-TELT-BLOKK család ÖTÖDIK/HATODIK rejtett rács-csatolt feltevése —
  tudatos, dokumentált; ha a nominál ablak változna, ez a routing újranézendő.
- **REJTETT FELTEVÉS NEVESÍTVE #2 (LANC-2HET-VONAL, szemle-lelet, ugyanide):** a rajzoló `veg_idx`
  kizárólagos felső határa a NYERS konvencióra épült — a nyers `ablak_veg_utc` egy RÉSZLEGES záró
  slot (kizárandó), a LÁNC `ablak_veg_utc`-je viszont az UTOLSÓ VALÓS pont. „A mező nem azonos azzal,
  amire használjuk." A fix a FORRÁS konvencióját teszi EXPLICITTÉ: a rekord `_veg_valos` jelzője mondja
  meg (a `nyers_ablak` lánc-ága állítja), és a `racs_epit` ebből dönt INKLUZÍV(+1)/kizáró(+0) között —
  NEM a hurok-határt tolja vakon (a naiv „utolsó lezárt +1" a nyers hátsó-lyukat is elrontaná). Lásd §11.

## 5. VÁRT ÁLLAPOT a szemlén — szavanként (MÉRVE 2026-08-21 a kulcsszo_lanc.json-ból)

| Szó(k) | Lánc pont / span | 2_het a gate után | 1_ho+ |
|---|---|---|---|
| 12 szó (állás, kormányablak, eladó lakás, albérlet, akciós újság, benzin, nyaralás, kórház, betegség, napelem, nyugdíj, hitel) | 523 pont / 21 nap (07-30→08-20) | ÚJ ERVENYES — láncból, átskálázott | marad `nincs_lancolas` (21<30) — VÁRT |
| benzin / nyugdíj (órás-only) | 21 nap | eddig „oras_lanc_kell" → MOST 2_het rajzol a láncból | 1_ho+ marad „oras_lanc_kell" |
| tüntetés | 168 pont / 6 nap (08-10→08-17, ragadt) | MARAD `nincs_lancolas` (6<14) — a gate NEM javítja (LANC-SZAKASZ-TORES) | marad `nincs_lancolas` |

### 5.a VÁRT viselkedés — a nézet-ablak vág, NEM hiányzik adat (08-19 tanulság)
A lánc ~21 napos, de a 2_het nézet ebből **~14 napot rajzol**. A különbség (~7 nap) **NEM
hiányzó adat** — a nézet ablakhossza (2_het=14 nap) vágja a farokból. Ez a szemlén a
legkönnyebben félreérthető dolog: a metrika a NÉZETET mérheti a TÁRGY helyett
(NEZET-SZEMLE-0819 tanulság). A rajzolt ~14 nap átskálázott görbe a ~21-napos láncból, NEM
az 1_het (7 nap) nyújtása.

### 5.b VÁRT — két felirat UGYANARRA a helyzetre (H4/I3 leletcsalád, NEM ebben a körben)
A 12 szó 1_ho+ ága `nincs_lancolas`-t, a benzin/nyugdíj (órás-only) 1_ho+ ága
`oras_lanc_kell`-t ír — de a helyzet UGYANAZ: a lánc 21 nap < a kért 30 nap. Ez a
NEZET-SZEMLE-0819 **H4/I3** felirat-leletcsaládja: két különböző felirat egy helyzetre.
VÁRT, a szemlén LÁTHATÓ lesz, de **NEM ebben a körben javítjuk** (nem új lelet).

## 6. VÁRT megjelenés a teljes nézeten
A teljes-nézet a leghosszabb érvényes intervallumot választja szavanként. A 12 szónál most a
2_het lesz a leghosszabb érvényes (~14 nap rajzolt, ~21-napos láncból átskálázva) — hosszabb,
mint az eddigi 1_het (7 nap). tüntetésnél változatlan. Az 1_ho+ üresen marad (21<30) — VÁRT.

## 7. TDD

- A gate-teszt TÖRLÉSE önmagában NEM TDD. Kell egy VALÓDI RED, ami a FRONTEND viselkedést méri:
  **a 2_het+ nézet a LÁNCBÓL rajzol** (Playwright, mock kulcsszo_lanc.json + a 2_het interval
  chain-sliced ervenyes → a kártya rajzol, a pontok a lánc ~14-napos farkából, nem üres/nyers).
  Előrejelzés NÉVRE és VISELKEDÉSRE; a tényleges RED-üzenetet mutatom. KICSIBEN (órás ág először).
- A backend viselkedést a frissített `test_oras_2_het_lancolt_ervenyes` őrzi (2_het ervenyes a
  láncból, feltétel nélkül) — ez a törölt gate-teszt HELYE.

## 8. SZEMLE — KÖTELEZŐ a köztes állapotnál
A kód zöldre kerülése UTÁN **ÁLLJ MEG**, ne commitolj. A canvas köztes állapotát a felhasználó
vizuálisan átnézi (SZEMLE-SZABÁLY: azonos szón 1_het vs 2_het — HA azonos görbe → szeletelési
hiba). Csak a szemle OK után jöhet a lezáró commit + push (külön kör).

## 9. Kapuk
Teljes SOROS suite zöld; `git status --short docs/data/` TISZTA; MUTÁCIÓ=1; leltár a záró
commitban; DOC-COMMIT (ez) a kód ELŐTT.

## 10. Teszt-újramérés (kód közben derült ki, USER-jóváhagyva 2026-08-21)

A `kulcsszo.spec.js` „10." és „13." teszt a Sz2 után PIROS lett. **ÚJRAMÉRVE, NEM
törölve** — és MIÉRT: mindkettő egy **órás 1_ho-t** rajzoltatott egy **FIKTÍV 720-pontos
NYERS ablakból**; a Sz2 routing (órás X≠1_het → LÁNC) **legitim módon megváltoztatta a
forrást** (a fiktív nyers-ablak már nem éri el). A tesztek VALÓDI tárgya (a váltás frissíti
a kártyát / a frissesseg követi az aktív intervallumot) generikus — a VALÓS Sz2-viselkedésre
mérve újra: `1_het` (nyers) → `2_het` (LÁNCBÓL), lanc-fixture-rel.

**Osztályozás: fabrikált-forrás ÚJRAMÉRÉS, NEM termék-regresszió. 4 pontos bizonyíték:**
1. A tesztek maga bevallja: az órás 1_ho „fiktív, mock-vezérelt".
2. A valóságban NINCS 720-pontos órás nyers ablak (a nyers 7 nap / 168 pont); a valós órás
   1_ho `nincs_lancolas` (a lánc 21 nap < 30) → a tesztelt jelenet SOSEM volt valós. **(döntő)**
3. A TELJES suite-ból CSAK ez a 2, azonos-fabrikált teszt bukott — minden VALÓS rajzolás zöld
   → nincs termék-regresszió.
4. A tesztek generikus tárgya (váltás-mechanizmus / frissesseg-követés) ép, csak a „hosszú
   intervallum" forrását kell a helyes helyről (lánc) etetni.

**Ez a Task-3 geometria-tesztek analógiája** (a panel eltolta a pixeleket → a load-idejű
geometria-tesztek újramérése; ott is a változás legitim módon módosította a mért állapotot).

**ORAS-1HO-FEDES megőrizve (USER-kikötés):** az órás 1_ho ágat NEM hagytuk el — a VALÓS
jelenlegi állapotra mérve (`nincs_lancolas` → tiltott gomb). Ez az assert MEGSZÓLAL, amikor a
lánc eléri a 30 napot és az 1_ho drawable lesz — pont ez a fedés értéke (időben változó helyzet).

## 11. LANC-2HET-VONAL — a szemle-lelet FIXE (USER-döntés: fix most, nem parkolt)

**Ez a mai kör regressziója — a valódi okot javítjuk, nem parkoljuk.** A szemle elkapta: a
lánc-forrású 2_het-en az UTOLSÓ PONT és a REGRESSZIÓS VONAL nem rajzolódott. Gyökér-ok: a
rajzoló `veg_idx = slot_index(ablak.ablak_veg_utc)` kizárólagos felső határa a NYERS konvencióra
épült (a nyers `ablak_veg_utc` RÉSZLEGES záró slot → kizárandó), DE a lánc `ablak_veg_utc`-je az
UTOLSÓ VALÓS pont → a `[rajz_kezd, veg_idx)` kihagyta, és a vonal-végpont (`i1 == ertekek.length`)
a `rajta()` guardon kívülre esett. „A mező nem azonos azzal, amire használjuk."

**Fix (forrás-konvenció explicit, NYERS ág VÁLTOZATLAN):**
- `app.js nyers_ablak` (lánc-ág): a visszaadott rekord `_veg_valos: true` (a `ablak_veg_utc` VALÓS pont).
- `app.js racs_epit`: `veg_idx = slot_index(ablak.ablak_veg_utc, racs) + (ablak._veg_valos ? 1 : 0)`.
  A nyers `_veg_valos` undefined → +0 → BÁJT-AZONOS a régivel; a lánc +1 → inkluzív (utolsó pont + vonal).

**Hatókör (MÉRVE 2026-08-21): jelenleg CSAK a 2_het chain-forrású (12 szó); az 1_ho/3_ho/1_ev mind
`nincs_lancolas` (lánc 21 nap < 30/90/365).** A fix mégis ÁLTALÁNOS (forrás-konvenció alapú, nem
2_het-specifikus) → amikor a lánc eléri a 30 napot és az 1_ho chain-forrású lesz, AUTOMATIKUSAN helyes.

**TDD (3 teszt, valódi RED, NÉVRE+VISELKEDÉSRE):**
- 19. RED: lánc 2_het → `data-vonal="true"` (RED: „false" — a vonal-végpont a tartományon kívül).
- 20. RED: lánc 2_het → `data-rajzolt-pont="337"` (RED: „336" — az utolsó pont kiesik; ez ADAT, nem dísz).
- 21. ŐRZŐ (SZÁNDÉKOS-ZÖLD, fogak MÉRVE): nyers HÁTSÓ-LYUK változatlan (`data-rajzolt-pont="168"`, a 3
  hátsó null bennmarad). FOGAK IGAZOLVA: a tiltott naiv fix (utolsó lezárt+1) alatt e teszt PIROS (165≠168),
  a helyes forrás-konvenciós fix alatt zöld (168).

## 12. Szemle-mérés eredményei (2026-08-21, a szemle UTÁN rögzítve)

### napelem 2_het „~26 plafon" — VÁRT (nem lelet)
MÉRVE a kulcsszo_lanc.json-ból: a napelem lánc GLOBÁLIS maximuma **100.00 @ 2026-08-02T11** — a
2 hét nézeten KÍVÜL (a [08-06,08-20] ablakon belül a max csak **26.05 @ 08-09**). A skálázó faktorok
SIMÁK/MAGYARÁZOTTAK: a 0.97→0.42 lépés 08-09-nél a 08-02-i csúcs kigördülése a 7-napos ablakból
(legitim újranormálás), nincs egyedi kiugró faktor. Kontroll (kormányablak: max 100 @ 08-03, 2 hét 93;
nyaralás: max 100 @ 08-02, 2 hét 87) UGYANEZ a minta → a napelem csak SZÉLSŐSÉGESEBB eset, nem külön
jelenség. **A 2 hét nézeten a lánc globális maximuma kívül eshet, ezért a görbe alacsonyan futhat — nem hiba.**
(Megjegyzés: ez megerősíti a §8.2-INV parkolást — a skálázás a GATE törlésével láthatóvá vált, de sima.)

### Két apróság a jegyzőkönyvbe (VÁRT, nem javítjuk most)
- **A tüntetés 1_het ELŐREJELZÉSEM TÉVES volt** (a szemle-táblában „rajzol (rövid)"): a valóságban a
  heti-rács üzenet jön MINDKÉT nézeten. Az ELŐREJELZÉS volt téves, NEM a termék — itt rögzítve, hogy a
  doc ne tartson fenn hamis várt állapotot.
- **A 2 hét x-tengely utolsó tick 08-19, az adat vége 08-20** (a tick-osztás miatt) — a NEZET-SZEMLE-0819
  **B4/E2** családja, VÁRT, nem ebben a körben javítjuk.
