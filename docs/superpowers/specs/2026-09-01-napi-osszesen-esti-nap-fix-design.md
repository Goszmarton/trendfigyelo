# Design — „Napi összesen" idősor-nézet + a hamis-esti forrás-javítás

Dátum: 2026-09-01
Státusz: jóváhagyva (brainstorming), spec-review kész

## Probléma

A kategória-idősor Reggel/Este váltója mellé a felhasználó egy harmadik,
**„Napi összesen"** nézetet kér, ahol egy nap reggeli és esti kategória-adata
össze van adva — de **mindig csak az adott nap tényleges lefutásaival**, sosem
áthúzva tegnapi estit. Legyen info-rész is, ami elmagyarázza a három nézetet,
hogy miért nincs még esti egy adott napnál, és mikor frissül.

A feature kidolgozása közben kiderült egy mögöttes **adat-helyességi hiba**: a
gyűjtés a futás **budapesti naptári napjához** rendel (`futtato.py:315`), ezért
egy **éjfél utáni (hajnali) esti backup-futás** hamis „másnapi esti" szegmenst ír.
Konkrétan 2026-09-01-en a 02:02 / 03:38 CEST-kor futott backup a `09-01` esti
szegmensbe írt, holott az valójában a 08-31 esti kép késői pótlása. Ráadásul az
idempotencia-őr emiatt a **mai valódi 21:00-s futást kihagyná** (látja, hogy
„09-01 este már megvan"), így a hamis esti egész nap bent ragadna. Ez nemcsak az
új nézetet, hanem a meglévő „Esti 21:00" idősort és a napi „Ma felkapott" blokkot
is rontja.

A felhasználó döntése: **a forrásnál javítunk** (adat + pipeline), nem csak a
megjelenítésnél — így minden nézet helyes lesz, a frontend triviális marad.

## A megközelítés (jóváhagyott)

Három rész: (A) backend „esti nap" fogalom a helyes nap-hozzárendeléshez,
(B) egyszeri adat-takarítás a már beírt hamis 09-01 estire, (C) frontend
„Napi összesen" mód + info-rész.

---

## A rész — Backend: „esti nap" fogalom

### Szabály

Új, tiszta, tesztelt segéd-függvény a `seged.py`-ben (az egyetlen igazságforrás,
hogy a gyűjtés és az őr egyezzen). Az **este-módra** kiszámítja a *logikai esti
napot* a futás budapesti idejéből:

```
esti_nap(most) = BP_dátum,           ha BP_óra >= 6
               = BP_dátum − 1 nap,   ha BP_óra < 6
```

- A **6:00 budapesti** küszöb elválasztja a valódi esti futást (21:00) és annak
  esti backup-jait (max ~01:00 CEST → ez már a *következő* naptári napé, de a
  6:00 előtti szabály visszasorolja az előző estéhez) a reggeli gyűjtéstől (09:00).
- DST automatikus: a küszöb budapesti helyi órában értendő (`astimezone(BUDAPEST)`).
- A `< 6` ág jelentése: „ez egy hajnali futás → az ELŐZŐ nap estéjének pótlása".

### Alkalmazás — két hely, ugyanaz a helper

1. **`futtato.futtat`** — este-módban a `nap_iso` (jelenleg `futtato.py:315`,
   `most.astimezone(seged.BUDAPEST).date().isoformat()`) helyett
   `esti_nap(most)`-ot használ a felkapott szegmens írásához. **Reggel-mód
   változatlan** (a 09:00-s reggelinek nincs hajnali esete; a
   `csak_felkapott`/`mode=="reggel"` ág a mostani BP-dátumot tartja).
   A `nap_iso` egyéb használatai (`futtato.py:419` napi_ir, `:504` index-hivatkozás)
   automatikusan a helyes napot kapják, mert ugyanabból a `nap_iso`-ból mennek.

2. **`futas_orzo` (idempotencia-őr)** — az este-szegmens ágán a `ma_bp`
   (jelenleg `seged.most_utc().astimezone(seged.BUDAPEST).date()`) helyett
   `esti_nap(most_utc())`-ot használ: azt vizsgálja, hogy *annak* az estének
   (esti_nap) van-e már szegmense a `napok/<esti_nap>.json`-ban. Ha van → **skip**
   (a hajnali backup nem gyűjt fölöslegesen és nem ír hamis estit). Ha nincs →
   gyűjt, és a `futtat` a `nap_iso = esti_nap(most)` révén az **előző napra**
   (a valóban kimaradt estére) írja be — a backup-védőháló megmarad.

### Az őr összehasonlítási szabálya

A jelenlegi őr a `<szegmens>.frissitve[:10]` (UTC-dátum) == `ma_bp` (BP-dátum)
egyenlőséget nézi. Az „esti nap" bevezetésével ez a **normál esetben helyes**:
a valódi esti futás (21:00 CEST = 19:00 UTC) `frissitve`-dátuma egybeesik a BP
esti napjával, tehát `napok/<esti_nap>.json` este.`frissitve[:10] == esti_nap`
→ skip. A `_szegmens_datuma` a helper által számolt `esti_nap`-ú fájlt olvassa.

Ritka, kettős-hiba eset (a valódi este KIMARADT ÉS több hajnali backup fut): a
bepótló hajnali futás `frissitve`-je a *következő* naptári nap UTC-dátuma, így
egy még későbbi backup `frissitve[:10] != esti_nap` miatt **fail-open** (újra
gyűjt/felülír). Ez elfogadott: a rosszabbik alternatíva a hamis kihagyás lenne,
és a felülírás ugyanannak az estének a pótlása. Ezt kommenttel jelöljük.

### Tudatos revízió

Ez **felülírja** az őr eddigi szándékos döntését („budapesti-éjfél-utáni
backup-futás FAIL-OPEN, ne javítsd UTC-összehasonlításra" komment). A felhasználó
irányítása alapján a hamis-esti szegmens rosszabb, mint egy elméleti kihagyás; a
miss-védelmet a bepótló-ág (előző napra írás, ha hiányzik) megőrzi. A régi
kommentet erre a döntésre frissítjük, nem töröljük szó nélkül.

### Mellékhatás (elfogadható, nincs adatvesztés)

Eddig a hajnali fail-open backup másodszor is gyűjtött kulcsszó-láncot; ezután
nem. De a lánc terv szerint is **napi 1×** (az esti teljes futásban) épül — a
`masodlagos_only.yml` kézi-only, a hajnali dupla-gyűjtés nem szándékos kadencia
volt. A pótolhatatlan órás adathoz (`kulcsszo_nyers.json`, `kulcsszo_lanc.json`)
NEM nyúlunk.

---

## B rész — Egyszeri adat-takarítás (KÜLÖN data-commit)

A már beírt hamis `09-01` estit el kell venni, hogy a **ma esti 21:00 valódi
futás** be tudja írni a valós estit (különben az őr — a javítással együtt is —
látná a meglévő 09-01 estit és skippelne, mert az esti_nap(21:00) = 09-01, aminek
már van szegmense).

- `docs/data/napok/2026-09-01.json` → az `este` kulcs törlése; marad `{nap, reggel}`.
- `docs/data/kategoriak.json` → a `2026-09-01` rekord `este` al-kulcsának törlése;
  marad `{nap, reggel:{...}}`.
- `legfrissebb.json` **érintetlen**: a `frissitve` már a reggeli `07:00` (a legfrissebb
  legit pillanatkép, `top_trendek` = 24), a kulcsszó-mezők megvannak.
- `index.json` **érintetlen**: 09-01 a reggeli szegmenssel bent marad.
- **NEM nyúlunk** a `kulcsszo_nyers.json` / `kulcsszo_lanc.json`-hoz.

A takarítás a hamis `01:43` esti pillanatképet tudatosan eldobja (a felhasználó
kérése: ne jelenjen meg 09-01 estijeként); a valós estit ma 21:00-kor gyűjtjük.

Ez a data-commit **külön** megy az implementációs (kód) commitoktól.

---

## C rész — Frontend: „Napi összesen" mód

### Shaper

`kategoria_idosor(kj, szegmens)` (`docs/js/app.js`) új `"osszesen"` szegmens-móddal:
a `kat(n)` belső függvény `osszesen` esetén naponként **összeadja a jelenlévő
szegmensek kategória-darabszámait**:

- reggel + este, ha mindkettő megvan;
- csak reggel, ha az este aznap még nincs (nincs kitalált/áthúzott érték);
- régi lapos rekord (`n.kategoriak`, nincs reggel/este) → **egyszer** számít
  (visszafelé kompat);
- ha egy naphoz semelyik szegmens sincs → `null` (a nap kimarad, ahogy most is).

A meglévő invariánsok változatlanok: a tengelyen CSAK a mért napok; a kategória
első megjelenése előtt `null`; jelen-nap-0 → valós `0`; vonal-készlet adat-vezérelt;
sorrend első-megjelenés majd név.

### Váltó és alapértelmezés

`idosor_szegmens_valto_epit()`: 3 gomb, sorrend
**`Napi összesen · Reggeli 9:00 · Esti 21:00`**. Az alap `idosor_szegmens`
kezdőértéke **`"osszesen"`** (belépéskor a teljes napi kép fogad). A váltó
mindig látszik (üres szegmensen is → nincs zsákutca).

### Info-rész

A váltó alatt **állandó, mindig látszó kék infó-doboz** (a főoldali
`trend-gyujtes-info` callout stílusában), determinisztikus statikus szöveggel
(NINCS `new Date()`/`Date.now()`):

- mit jelent a három nézet (Napi összesen = a nap reggeli + esti adata összeadva;
  Reggeli 9:00 / Esti 21:00 = az adott pillanatkép);
- ha egy napnál még csak reggeli adat van (az aznapi 21:00 esti még nem futott le),
  a Napi összesen arra a napra egyelőre **csak a reggelit** tartalmazza;
- frissülés: reggeli ~9:00, esti ~21:00 (a honlap kevéssel utána frissül).

A meglévő „Esti 21:00" nézet és a napi „Ma felkapott" blokk a forrás-javítás
után automatikusan helyes adatot mutat — nincs rájuk külön frontend-változás.

---

## D rész — Tesztelés (TDD, valós RED→GREEN)

- **Backend unit** (`tests/test_seged.py`): `esti_nap` — hajnal (`< 6`) → előző
  nap; este (`>= 6`, 21:00) → aznap; 6:00 határ (05:59 vs 06:00); DST (nyári/téli
  ugyanaz a helyi 6:00 küszöb).
- **Backend integráció** (`tests/test_futtato.py`): este-módú hajnali `most` →
  a felkapott szegmens az ELŐZŐ napra íródik; 21:00-s `most` → aznapra. Reggel-mód
  változatlan.
- **Őr** (`tests/test_futas_orzo.py`): este-szegmens — hajnali futás az esti_nap
  (előző) szegmensét nézi → meglévőnél skip; hiányzó előző esténél gyűjt; 21:00-s
  futás az aznapit nézi.
- **Frontend shaper**: `kategoria_idosor` „osszesen" — összeg (reggel+este),
  régi-lapos egyszer, csak-reggel nap, null-rés/valós-0 megőrzése; a rejtett
  DOM-tükrön keresztül assertálva.
- **Playwright e2e** (`e2e/trend.spec.js`): 3-gombos váltó; alap `osszesen`;
  info-doboz jelenléte + tartalma; a régi `{reggel,este}` adat visszafelé-kompat.

## Nem-cél (YAGNI)

- NEM egyedi-trend unió (dedup nyers szó szerint) — a felhasználó „össze vannak
  adva" = darabszám-összeg; az unió más adatforrást igényelne, külön kör.
- NEM változtatjuk a reggeli nap-hozzárendelését (nincs hajnali reggeli).
- NEM nyúlunk a cron-ütemezéshez ebben a körben (a szerver-trigger + backupok
  maradnak; csak a nap-attribúció + őr logikája változik).

## Kockázatok

- A `nap_iso` átállítása a felkapott szegmens írását (`napi_ir`, `:419`) és az
  index-hivatkozást (`:504`) táplálja — gondos integráció-teszt kell, hogy
  este-módban ezek a helyes napra menjenek és reggel-mód ne változzon. (A
  `tortenet` a valós adat-napokra megy, NEM a `nap_iso`-ra — nem érinti.)
- Az őr revíziója a backup-védőhálót érinti — a hiányzó-este bepótló ágat
  explicit teszt fedi.
- A data-takarítás pótolhatatlan-adat-szomszédos (`napok/<nap>.json`), de csak a
  felkapott esti szegmenst érinti (ma este újragyűjtött), az órás láncot nem.
