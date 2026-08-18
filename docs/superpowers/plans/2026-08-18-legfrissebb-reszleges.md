# Terv — LEGFRISSEBB-RESZLEGES: hiba-tudatos TELJES-fájl skip

Dátum: 2026-08-18. Fázis: Phase 3/4 (KUDARC-VAK rekord utolsó nyitott tagja).
Döntés: **(d) hiba-tudatos TELJES-fájl skip** (user-jóváhagyás 2026-08-18).

## 1. A HIBA (MÉRVE, nem elméleti)

**Kódhely:** `futtato.py:349-357` (guard) + `json_export.legfrissebb_ir` (TELJES újraírás, NINCS merge).
A `legfrissebb.json` három logikai blokkja: `top_trendek` / `trend_idosorok` / `kulcsszavak`(+`kulcsszo_osszesites`).

**A meglévő LEGFRISSEBB-GUARD (7e2ec4c) rése:** a guard CSAK a TELJES-üres esetet fedi
(`len(_lf_ures) == len(_lf_reszek)` → mind a 3 blokk üres). Ha az API sikerül (`top_trendek` nem üres),
de az idosor/kulcsszo ág 429-blokkot kap → 2 blokk üres, 1 nem → a guard NEM tüzel → **a részleges felülír**.

**MÉRT előfordulások (a git-történetből + naplo.csv):** 07-27, 07-28, **08-11 (e660f2ee)**.
A 08-11 naplója: `kulcsszo;blokkolva;5;429,429,429,429` és `idosor;kihagyva;0`. Következmény:

| | top_trendek | idosorral | kulcsszavak | trend_idosorok |
|---|---|---|---|---|
| 08-10 (előző, TELJES) | 20 | 15 | 12 | 2700 |
| **08-11 (részleges FELÜLÍRÁS)** | **15** | **0** | **0** | **0** |

A 08-10 teljes „ma"-nézete (20 trend sparkline-nal, 12 kulcsszó-chart) felülíródott csak-nevek snapshottal.
Ez **MÉRT** (nem elméleti, ellentétben a SUCCESS-VAK-kal). A guard (08-15) 08-11-et amúgy sem fogta volna
(`top_trendek` nem üres); post-guard eset még nincs, mert 08-15 óta nem volt 429-blokk (szerencse, nem védelem).

## 2. A DÖNTÉS: (d) — a diszkriminátor az ÁG-STÁTUSZ, NEM a darabszám

**(a) monotonitás-guard MEGCÁFOLVA méréssel:** `kulcsszavak` 22→13 (07-29→30, konfig/módszertan-váltás) és
13→12 (08-10, ritka esemenyjelzo szó) LEGITIM csökkenés — az (a) befagyasztaná.
**(b) merge MEGCÁFOLVA:** a 22→13 mutatja, szavak JOGGAL kilépnek; a merge a törölt szavakat bennragasztaná,
és a kevert frissesség hazudná a `frissitve`-bélyeget.

**A helyes szabály:** egy mag-blokk (`kulcsszavak` ↔ `kulcsszo` ág; `trend_idosorok` ↔ `idosor` ág) üres,
MERT az ága **bukott** (`eredmeny ∈ {blokkolva, kihagyva, plafon, hiba}`) → **NE írd felül** a jó teljes
fájlt + HANGOS FIGYELEM. A legitim csökkenés mindig `siker` ágon történik (a blokk nem-üres, csak kisebb) →
normálisan felülír. Blokk csak bukott ágon nullázódik → a darabszám-csökkenés SOHA nem nullázza a blokkot,
ezért freeze-veszély NINCS.

**A guard feltétele (kikötés 5 — a régi ág RÉSZHALMAZ, NEM veszik el):**
```
skip, HA:
  (A)  mind a 3 blokk üres                                      # RÉGI LEGFRISSEBB-GUARD, megőrizve (bármely okból)
  VAGY (B) van olyan mag-blokk, ami ÜRES ÉS az ága BUKOTT       # ÚJ (d) — a részleges-hiba eset
```
Az (A) a régi viselkedés (fedi az „mind üres, akár siker akár blokk" esetet is); a (B) az új réteg.
A commit KIMONDJA: a LEGFRISSEBB-GUARD viselkedése az új guard RÉSZHALMAZA, nem veszett el.

## 3. FIGYELEM üzenet (kikötés 1 — HANGOS, MEGNEVEZ; a napló-taxonómia folytatása)

Tartalma: MELYIK blokk ürült ki, MELYIK ág bukott és MIVEL, hogy a fájl NEM íródott felül, és MELYIK nap
teljes snapshotja marad (a meglévő fájl `frissitve`-jét beolvasva). Formátum:
```
FIGYELEM: legfrissebb.json felülírása KIHAGYVA — RÉSZLEGES futás (ág-hiba).
  üres blokk: 'kulcsszavak' (a 'kulcsszo' ág: blokkolva — 429,429,429,429)
  üres blokk: 'trend_idosorok' (az 'idosor' ág: kihagyva)
  a jó TELJES fájl ÉRINTETLEN — marad a(z) 2026-08-10 teljes snapshotja.
```
NEM mosódik össze a MASODLAGOS-PLAFON / total-guard címkéivel: ez EXPLICIT „RÉSZLEGES futás (ág-hiba)".

## 4. RED-ek + SZÁNDÉKOS-ZÖLD (kikötés 2) — névre / hibatípusra / tényleges üzenetre

Új test-dublőr: `ReszlegesBlokkKliens` — `felkapott_api` ad egy trendet (top_trendek nem üres),
`kulcsszo` `AgFeladva(["429"×4])`-t dob → `blokkolva` → block-stop → `idosor` = `kihagyva`.
(A 08-11 pontos reprodukciója. Meglévő minta: `Mindig429Kliens`, `IdosorBlokkolKliens`.)

- **RED 1 — `test_reszleges_agHiba_nem_uriti_a_legfrissebbet`** (a fix magja).
  Meglévő jó `legfrissebb.json` + `ReszlegesBlokkKliens` → a fájl VÁLTOZATLAN.
  RED (fix előtt): a részleges felülír → `AssertionError` (a fájl tartalma megváltozott, ≠ az eredeti).
- **RED 2 — `test_reszleges_agHiba_figyelem_megnevez`** (kikötés 1, capsys).
  Kimenet tartalmazza: `"KIHAGYVA"`, `"RÉSZLEGES"`, `"kulcsszavak"`, `"kulcsszo"`, `"blokkolva"`, és a
  megőrzött nap dátumát. RED (fix előtt): nincs ilyen sor (némán írt) → `AssertionError` (hiányzó substring).
- **SZÁNDÉKOS-ZÖLD 3 — `test_legit_kisebb_blokk_siker_agon_FELULIR`** (A LEGFONTOSABB — a user félelme, anti-freeze).
  Meglévő jó `legfrissebb.json` (13 szó) + kliens, ami 12 szót ad `siker` kulcsszo-ágon (blokk KISEBB, nem üres)
  → a fájl FELÜLÍRÓDIK (12 szó). Zöld a fix ELŐTT ÉS UTÁN — ŐRZI, hogy a javítás SOHA ne fagyassza a jogos
  csökkenést. Egy téves monotonitás-implementáció (12<13 → skip) ezt PIROSÍTANÁ → mutációs védelem.
- **SZÁNDÉKOS-ZÖLD 4 — a régi total-guard megmarad** (`test_nulla_adat_nem_uriti_a_legfrissebbet` VÁLTOZATLANUL zöld):
  a (B) ág nem ronthatja el az (A) részhalmazt. Ha kell, +1 explicit assert, hogy total-üres → skip.

## 5. Kikötés 3 — ARCHIVUM-RESZLEGES megfigyelés a leltárba (NE maradjon szóbeli)

A `napi_ir` (napok/<nap>.json, futtato.py:367) a részleges `top_trendek`-et KIÍRJA — SZÁNDÉKOS aszimmetria:
archívum = mi TÖRTÉNT (a részleges nap is történés), legfrissebb = a legjobb ismert TELJES állapot.
Ha egységes skip kell, az KÜLÖN tétel/scope. → új leltár-REKORD: **ARCHIVUM-RESZLEGES**.

## 6. Méret + spec

- **Production:** ~20-30 sor a `futtato.py` guard-blokkjában (blokk↔ág térkép + „üres ÉS ága bukott?" +
  a meglévő fájl `frissitve` beolvasása a FIGYELEM-hez). A `bejegyzesek` a guard pontján elérhető.
- **Egy commit**, backend, NINCS szemle-kapu. Méret: **S-M** (mérve, nem a címke alapján).
- **Spec:** NINCS eltérés — a 7e2ec4c guard sem érintett specet, és a §7.5 már „az utolsó SIKERES gyűjtésé"-t
  mondja (547-548) → a (d) ezzel ÖSSZHANGBAN. A DOC-COMMIT = EZ a terv-doc.

## 7. Leltár-terv (a záró commitban)

- LEGFRISSEBB-RESZLEGES → LESZÁLLÍTVA, **MÉRT** (07-27/28 + 08-11 e660f2ee; a 20/15/12/2700 → 15/0/0/0 táblázat).
  A KUDARC-VAK rekord BUG-tagjai így mind rendezve (L4/SUCCESS-VAK/LEGFRISSEBB-RESZLEGES). PONTOSÍTÁS: a **FOLYT**
  még NYITOTT, de az NEM bug — egy külön, egy körben zárandó DÖNTÉS-tétel (él-trigger elég-e); nem tartozik a
  „kudarc-jelzés" javításokhoz. A rekord tehát a hibák oldalán zár, a FOLYT-döntés külön marad.
- Új REKORD: **ARCHIVUM-RESZLEGES** (kikötés 3).
- Invariáns MÉRÉSSEL.
