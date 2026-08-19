# Terv — Per-szó több-timeframe másodlagos + érkezés-ellenőrzés (jóváhagyva 2026-08-19)

## Döntés (user, mért alapon)
Minden **nem-ora** szó kapjon MINDKÉT hosszú sorozatot (`today 3-m` ÉS `today 12-m`). Indok: a nézet-szemle
MÉRTE, hogy ugyanaz az adat rövidebb/hosszabb ablakon MÁS irányt ad (kormányablak: 1 év R²=0,00 stagnáló vs
3 hó R²=0,66 növekvő). Ezért NEM választunk timeframe-et szavanként, hanem **mindkettőt tartjuk**, a felhasználó
gombbal vált. A config-rács MARAD (megjelenítési alapértelmezés), átsorolás NINCS. A **timeframe-sweep TÁRGYTALAN** (08-19
leltár-takarítás): mivel MINDKÉT hosszú timeframe-et gyűjtjük és tartjuk (nem választunk szavanként), nincs mit
„sweep"-elni — a RACS-PLATO mérés is ezt támasztja alá (ugyanaz a 12-m adat 3 hó ablakon jelet ad).

## Hatókör
- **11 nem-ora szó** (racs≠ora). benzin/nyugdíj **KIMARAD** — ott `RACS_IDOKERET`+`_intervallumok(racs="ora")`
  +`RACS_GRID_STEP/MIN_PONT/ABLAK_NAP`+frontend GATE is érintett (NEM lokális, 3/d válasz).
- Ebben a körben: az 1-4 rész (ellenőrzés → séma → olvasó → gyűjtés). **A 13 cella KÉZI feltöltése + a
  másodlagos-only belépő KÜLÖN kör**, csak miután az 1) érkezés-ellenőrzés zölden áll.
- NE nyúlj: nézet-szemle többi lelete (feliratok, tengelycímke, medián-vonal, 12/13 szöveg), LANC-ORAS Sz2, RACS-PLATO.

## MÉRT kalibráció (2026-08-19, a lemezről — a várt alak LEVEZETÉSÉHEZ, nem beírt konstans)
| timeframe | step | pont | span (nap) | veg→lek |
|---|---|---|---|---|
| today 3-m | 1 nap | 92 | 91 | 0 nap |
| today 12-m | 7 nap | 52-53 | 357-364 | 0-5 nap |

Levezetés: `today N-m` → várt span ≈ **N × 30,4 nap** (3-m→91, 12-m→365, mért arány 0,98-1,00); a **step MÉRT**
(a pontok közti egyenlő köz), a pont ≈ span/step+1. Csonka = a span jóval a várt alatt.

## Rekord-séma változás (a 2-4 rész alapja)
A másodlagos rekord két új invariánsa:
- **`timeframe`**: a kért string (pl. `"today 3-m"`) — a rekord ELtárolja (ma nem teszi; a racs-ból derül).
- **`racs`** = a timeframe RÁCSA (3-m→`nap`, 12-m→`het`), NEM a config-rács. Ma egybeesik (racs↔timeframe 1:1),
  a több-timeframe világban egy het-config szó 3-m rekordjának rácsa `nap`. A config-rács külön (megjelenítési default).

---

## 1) ÉRKEZÉS-ELLENŐRZÉS (ELSŐ — ma a csonka adat érvényesként elmentődik, 4/d)
**Hol:** a GYŰJTÉS pontján (`kulcsszavak.gyujt_egy_masodlagos`), NEM a `ervenyes_masodlagos_rekord`-ban — a csonka
GOOGLE-válasz NEM a mi bugunk → **ELDOBNI + naplóba FIGYELEM** (a `ervenyes_*` ValueError-je a MI hibánké, az crashelne).
- Új `masodlagos_alak_ok(pontok, timeframe, lekerdezes_utc) → (ok, indok)`:
  - **rács-szabályos:** a pontok közti köz EGYENLŐ (egyetlen step-érték) — különben eldob;
  - **span a timeframe-ből:** `N × 30,4 nap` várt span; a tényleges span ≥ 0,85× (csonka-guard) és ≤ 1,2× (rossz-tf);
  - **frissesség:** `veg` NEM jövő és a lekérdezéshez képest ≤ 2×step + puffer.
  Minden várt érték a `timeframe`-ből LEVEZETVE (rács-vak konstans veszély kerülve).
- `ervenyes_masodlagos_rekord` (`nyers_kimenet.py:164`): a **`timeframe` mező kötelező** (jelen + a kalibrációs
  készletben) — hogy a séma (2. rész) rá kulcsolhasson.
- **RED-előrejelzés (viselkedés):**
  - `test_masodlagos_csonka_eldobva`: 12-m kérés, de csak 10 heti pont (span ~63 nap) → `gyujt_egy_masodlagos`
    **None**-t ad (eldob), NEM ment. RED: ma rekordot ad → `assert rek is None` bukik (rek egy dict).
  - `test_masodlagos_alak_levezetett` (SZÁNDÉKOS-ZÖLD, fedés mérve): 3-m 92 napi pont OK; ugyanez 12-m-ként kérve
    ELUTASÍT (91 nap << 0,85×365). A várt span a timeframe-ből (N csere → más határ).
  - `test_masodlagos_timeframe_kotelezo`: `ervenyes_masodlagos_rekord` timeframe nélküli rekordra hibát ad.

## 2) SÉMA — retenció (szó × timeframe)
Ma a retenció a 3 legfrissebbet tartja timeframe-től FÜGGETLENÜL (`nyers_kimenet.py:218-223`) → a két timeframe
versenyezne 3 helyért. Kell: **timeframe-enként külön** `megtartott_db`.
- `ir_masodlagos` retenció: szavanként csoportosít `timeframe` szerint, mindegyikből a `megtartott_db` legfrissebb.
- **RED:** `test_masodlagos_retencio_timeframe_kulon`: egy szó 3× 3-m + 3× 12-m rekorddal → MIND a 6 megmarad
  (3/timeframe). RED: ma 3-ra vágja (össz) → `assert len == 6` bukik (len 3).

## 3) OLVASÓ — timeframe-tudatos rekord-választás (regresszió)
Ma `regresszio_masodlagos_szamit` (`regresszio.py:327-328`) `max(rekordok, key=ablak_veg_utc)` — a 3-m ablakvége
MINDIG frissebb (napi vs heti lezárás) → a 12-m SOHA nem jut képernyőre.
- Kell: szavanként MINDKÉT rekord (3-m és 12-m) feldolgozása, az intervallumok a rekord rácsából (3-m→napi:
  2_het/1_ho/3_ho; 12-m→heti: 1_ev [+3_ho]) — **egyesítve**. Ütközés a `3_ho`-n: a **finomabb (napi, 3-m) nyer**
  (a heti 12-m a saját egyedi `1_ev`-ét adja). Így a user a példája szerinti 3_ho (napi) ÉS 1_ev (heti) verdiktet is látja.
- Minden interval `ablak_veg_utc`-je a FORRÁS-rekordjáé → a frontend `nyers_ablak` (ablak_veg-egyezés) magától a jó
  nyers ablakot húzza. **FELTÉTELEZÉS, IMPLEMENTÁCIÓNÁL IGAZOLANDÓ:** ez backend-only (a frontend már per-interval
  ablak_veg-re olvas). **HA a frontend canvast érint → KÜLÖN SZELET + SZEMLE ELŐTTED** (a user kikötése).
- **RED:** `test_masodlagos_mindket_timeframe_intervallumot_ad`: egy szó 3-m + 12-m rekorddal → a regresszió-kimenet
  intervallumaiban VAN heti-forrású `1_ev` ÉS napi-forrású `3_ho`. RED: ma csak az egyik (max ablak_veg) rekord jön.

## 4) GYŰJTÉS — timeframe-paraméter + cella-szintű staleness
- `gyujt_egy_masodlagos(..., timeframe)`: paraméterből (nem `RACS_IDOKERET[racs]`); a rekordba `timeframe` + a
  timeframe rácsa (`racs`).
- `masodlagos_szavak_ma` (`futtato.py:42`): **cella-szintű** (szó × timeframe) staleness — 22 cella (11×2), a
  never-collected/legelavultabb elöl, config-index+timeframe tie-break; első `MAX_MASODLAGOS_NAPI` cellát adja.
  A `_masodlagos_ag` (futtato.py:70) a (tetel, timeframe) párokat kéri le. **MAX_MASODLAGOS_NAPI marad 2** (a kvótát
  KÜLÖN döntjük).
- **RED:** `test_masodlagos_cella_szintu_utemezes`: a scheduler (szó, timeframe) PÁROKAT ad, mindkét timeframe cella
  jogosult, never-collected elöl. RED: ma szavakat (egy timeframe) ad → a visszatérési alak/tartalom eltér.

---

## Folyamat
- TDD, valódi RED (névre + viselkedésre), a tényleges hibaüzenetet mutatom; eltérés → STOP.
- Mutáció egyenként; kör végén `grep MUTÁCIÓ == 1`. Commit CSAK jóváhagyott üzenettel, `git add` NÉVVEL.
- **EZUTÁN ÁLLJ MEG.** A kézi feltöltő kör + a másodlagos-only belépő KÜLÖN kör (csak az 1) zöld után).
- Leltár §11a a lezáró commitban, invariáns méréssel.
