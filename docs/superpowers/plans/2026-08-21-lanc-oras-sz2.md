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
