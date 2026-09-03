# Terv: kulcsszó-chartok „várható feltöltődés" dátuma

**Dátum:** 2026-09-03
**Állapot:** jóváhagyásra vár
**Kiváltó igény:** a felhasználó kérése — minden kulcsszó-charthoz jelenjen meg, hogy *várhatóan melyik napon* töltődik fel adattal, „mint a korábbi kulcsszavaknál" (az órás-only `oras_lanc_kell` szavaknál már ott a „Várhatóan …-től lesz elérhető").

## Motiváció

A frontend ma **egyetlen** üres-ablak esetnél ír ki várható dátumot: `oras_lanc_kell` (órás-only szó, pl. benzin/nyugdíj), a betöltött láncból (`ablak_kezdet + hossz nap`, `app.js:274-282` + `varhato_datum_szamit` `app.js:694-705`). A 2026-09-02-őn hozzáadott 15 új társadalmi-feszültség szó viszont nagyrészt **nem-órás (másodlagos)** szó; ezek üres ablakai jelenleg dátum nélkül csak annyit írnak: *„Magától feltöltődik."* A cél: ezekre is kiírni a várható dátumot, ahol az **őszintén** megtehető.

## Fogalmi modell — kétféle „váró" üres ablak

A `egyesitett_reg()` (`app.js:224-296`) szavanként/ablakonként dönt ok-kódot. A releváns üres esetek:

| ok-kód | jelentés | időbeli? | teendő |
|---|---|---|---|
| `oras_lanc_kell` | órás-only szó hosszú ablaka, épül a lánc | IGEN | **változatlan** (már van dátuma) |
| `nincs_masodlagos` | a szó a rotációból **még be sem gyűlt** | IGEN | **① becsült gyűjtési dátum** |
| `rovid_masodlagos` | van másodlagos, de a sorozat rövidebb az ablaknál | **NEM** (lásd lent) | **② nincs dátum + őszinte szöveg** |
| `rovid_het_ablak` | heti rácson strukturálisan túl rövid ablak | NEM (ELVI) | változatlan |

### ① `nincs_masodlagos` — becsült gyűjtési dátum

A másodlagos gyűjtés rotációja **determinisztikus** (`masodlagos_szavak_ma`, `futtato.py:52-83`):

- Egység = **cella** = (szó × timeframe). Reggeli szó = **1 cella** (`masodlagos_timeframek`, `config.py:34-44`).
- Jogosultság: `t.racs != "ora" and t.futas == "reggel"` → jelenleg **15 reggeli cella**.
- Rangsor: **elavultság DESC, majd config-index ASC, majd tf-index ASC** (`futtato.py:82`). Az elavultság = `(most - max(lekerdezes_utc)).days`; **soha-nem-gyűlt cella → `inf`** → a sor elejére, config-sorrendben.
- Cap: **`MAX_MASODLAGOS_REGGELI = 8`** cella/futás (`futtato.py:43`), **napi 1 reggeli futás**.

**Zárt képlet (nincs szükség szimulációra).** A soha-nem-gyűlt cellák `inf`-fel a backlog elejére kerülnek; a backlog szigorúan rang-sorrendben ürül, futásonként 8. Egy épp begyűlt cella elavultsága 0-ra nullázódik, így a következő futáson a még váró (nagy/`inf` elavultságú) cellák elé nem kerül. Ezért egy `r` 0-alapú rangú (a **soha-nem-gyűlt** reggeli cellák config-sorrendjében vett) váró szó a
```
runs_ahead = floor(r / 8) + 1
```
sorszámú jövőbeli reggeli futáson gyűl be. A következő reggeli futás dátuma = a becslést számoló esti futás Budapest-helyi dátuma + 1 nap (a regresszió csak esti módban íródik, lásd „Integráció"). Így:
```
varhato_gyujtes_datum = kovetkezo_reggeli_datum + floor(r / 8)   [nap]
```
15 cellánál `floor(r/8) ∈ {0,1}` → a becslés legfeljebb ~2 nap. Ha a config nő, a képlet gracefully skálázódik; nincs külön horizont-korlát (a cellaszám határolja).

**Kiket kap dátumot:** csak azok a reggeli nem-órás szavak, amelyeknek **nincs rekordjuk** a `kulcsszo_masodlagos_nyers.json`-ban (soha-nem-gyűlt = `nincs_masodlagos` a frontenden). A már begyűlt szavak nem kapnak (ablakuk érvényes, a frontend úgysem mutatná). Az arrival-check (`masodlagos_alak_ok`) által elutasított válasz sem ír rekordot → az a szó továbbra is „soha-nem-gyűlt" → helyesen kap dátumot.

### ② `rovid_masodlagos` — nincs dátum, őszinte szöveg

A jelenlegi confignál `rovid_masodlagos` **kizárólag** a napi rácsú szavak (kölcsön, sürgősségi) **1-év** nézetét érinti: a napi sorozat 3 hó (~90 nap), és a másodlagos **nem láncolja** a napi adatot 365 napra → ez az ablak **soha nem töltődik fel** magától. Ezért:

- **NEM** kap kitalált dátumot (a `kezdet+365` hamis ígéret lenne).
- A `OK_MAGYAR.rovid_masodlagos` szövege (`app.js:171`) az időbeli („Magától feltöltődik.") helyett **őszinte, strukturális** megfogalmazásra vált, pl.:
  `"A napi/heti sorozat ehhez az ablakhoz túl rövid."`

## Architektúra

### Backend

**Új modul: `trendfigyelo/varhato_gyujtes.py`** — egyetlen tiszta, determinisztikus függvény:

```
varhato_gyujtes_datumok(config, masodlagos_nyers, most) -> dict[str, str]
```

- Bemenet: `config` (kulcsszavak + rács + futás), a betöltött `kulcsszo_masodlagos_nyers.json` `kulcsszavak` blokkja, és `most` (aware UTC datetime — a hívó adja, **nincs** `Date.now()`/argless `datetime.now()`).
- Kiszámolja a reggeli nem-órás cellákat, kiválasztja a **soha-nem-gyűlt** cellákat (nincs rekord / nincs érvényes `lekerdezes_utc`), config-sorrendben rangsorolja, és minden ilyen szóhoz visszaad egy `YYYY-MM-DD` (Budapest-helyi) dátumot a fenti képlettel.
- A `kovetkezo_reggeli_datum` = `most` Budapest-helyi dátuma + 1 nap (a becslést az esti futás írja; a következő reggeli gyűjtés másnap 09:00). A Budapest-tz konverzió a meglévő `seged` segédekkel.
- Tiszta függvény: nincs I/O, nincs órajel-olvasás — teljesen tesztelhető rögzített `most`-tal és beadott sorozatokkal.

**Integráció: `trendfigyelo/futtato.py`** — az **esti** (`csak_felkapott == False`) ág regresszió-írásakor, miután a `kulcsszo_regresszio.json` struktúra elkészült:

- Beolvassa a `kulcsszo_masodlagos_nyers.json`-t (már elérhető útvonal a futtatóban), meghívja `varhato_gyujtes_datumok(config, masodlagos_nyers, most)`-ot.
- Szavanként beinjektálja a regresszió-struktúrába: `kulcsszavak[szo]["varhato_gyujtes_datum"] = "YYYY-MM-DD"` — **csak** azoknál a szavaknál, amelyek a map-ben szerepelnek (soha-nem-gyűlt reggeli szavak). A `regresszio.py` **tiszta marad** (a scheduler-matek a futtatóban él, nem a regresszió-számításban).
- A reggeli módban (regresszió kihagyva) a fájl nem íródik újra → a becslés naponta, esti futáskor frissül. Ez elfogadható (nap-granularitás).

### Frontend (`docs/js/app.js`)

- **`egyesitett_reg()` `nincs_masodlagos` ág (`app.js:265` körül):** amikor `ok === "nincs_masodlagos"`, és `o.varhato_gyujtes_datum` létezik, tegye `ures.varhato_gyujtes_datum = o.varhato_gyujtes_datum`. (Ugyanaz a mező-átvezetési minta, mint az `oras_lanc_kell` `varhato_datum`.)
- **`ok_szoveg(iv)` (`app.js:699-705`):** kiegészül a `nincs_masodlagos` ághoz tartozó dátum-toldalékkal:
  `alap + " Várhatóan " + datum.replace(/-/g,".") + "-től gyűlik."`
  (Az `oras_lanc_kell` meglévő „…-től lesz elérhető." mondata változatlan; a két eset külön záró-mondatot kap, hogy a jelentés pontos legyen.)
- **`OK_MAGYAR.rovid_masodlagos` (`app.js:171`):** szöveg-csere az őszinte, dátum nélküli megfogalmazásra (② szerint).

## Adatfolyam

```
esti futás (mode=este):
  gyujt / masodlagos_ag  →  kulcsszo_masodlagos_nyers.json (lekerdezes_utc/cellák)
  regresszió számít       →  kulcsszo_regresszio.json (per-szó)
  varhato_gyujtes_datumok(config, masodlagos_nyers, most)
        →  inject o.varhato_gyujtes_datum a soha-nem-gyűlt reggeli szavakhoz
  írás: kulcsszo_regresszio.json

frontend:
  egyesitett_reg(): o.varhato_gyujtes_datum → ures.varhato_gyujtes_datum (nincs_masodlagos ág)
  ok_szoveg(): "Várhatóan YYYY.MM.DD-től gyűlik."
```

## Hibakezelés / élek

- **Olvashatatlan másodlagos JSON:** `varhato_gyujtes_datumok` üres map-et ad (nincs becslés, a frontend a dátum nélküli szövegre esik vissza). Nincs kivétel a futtatóba.
- **Minden reggeli szó begyűlt:** a map üres → nincs változás a regresszióban. Helyes.
- **Config nő 8 cella fölé:** `floor(r/8)` több napot ad; nincs külön korlát.
- **`most` időzóna:** Budapest-helyi dátum a következő 09:00-ás futáshoz; nap-granularitás → nincs off-by-one az esti (UTC ~19:00 = Budapest 21:00) számításnál.
- **Pótolhatatlan adat:** ez a feature **csak olvassa** a `kulcsszo_masodlagos_nyers.json`-t és a `kulcsszo_regresszio.json` per-szó blokkját bővíti egy mezővel; a nyers/lánc fájlokat **nem** írja.

## Tesztelés

- **Backend egység (`tests/test_varhato_gyujtes.py`, új):**
  - Soha-nem-gyűlt reggeli cellák config-sorrendben → `floor(r/8)` napos eltolás (rang 0-7 → +0 nap, rang 8-14 → +1 nap).
  - Már begyűlt (friss `lekerdezes_utc`) szó **nem** kap dátumot.
  - Arrival-check-elutasított (rekord nélküli) szó **kap** dátumot.
  - Csak `futas==reggel` és `racs!=ora` szavak; esti szavak kizárva.
  - Olvashatatlan/üres bemenet → üres map.
  - Budapest-helyi következő-reggeli dátum rögzített `most`-ból (nincs órajel-olvasás).
- **Backend integráció (`test_futtato*`):** az esti ág a regresszió-struktúrába injektálja a mezőt a soha-nem-gyűlt reggeli szavakhoz; reggeli ág nem írja újra a fájlt.
- **Frontend e2e (`e2e/kulcsszo.spec.js`):**
  - `nincs_masodlagos` szó, `varhato_gyujtes_datum` fixture → kártya tartalmazza „Várhatóan YYYY.MM.DD-től gyűlik."
  - `rovid_masodlagos` → az új őszinte szöveg, **nincs** „Várhatóan".
  - `oras_lanc_kell` meglévő teszt (Várhatóan …-től lesz elérhető.) **változatlanul zöld**.

## Amit NEM csinálunk (YAGNI)

- Nincs teljes rotáció-szimuláció (zárt képlet elég a backlogra).
- Nincs napi-adat-láncolás 365 napra (a `rovid_masodlagos` strukturálisan üres marad — csak a szöveget javítjuk).
- Nincs új frontend fájl/fetch (a meglévő `kulcsszo_regresszio.json`-ba injektálunk).
- Nincs becslés a már begyűlt szavak *következő* frissítésére (a frontend úgysem mutatná).
