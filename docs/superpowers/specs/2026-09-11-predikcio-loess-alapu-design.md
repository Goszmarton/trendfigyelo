# Predikció (LOESS-alapú, csillapított-trend) a kulcsszó-chartokon — design

**Állapot:** jóváhagyott terv, implementáció előtt (Phase 4).
**Dátum:** 2026-09-11.
**Előzmény:** a [nemlineáris LOESS-trend](2026-09-10-nemlinearis-ml-trend-design.md) feature — a
predikció ANNAK a LOESS-görbének a folytatása a jövőbe.

## 1. Cél

Minden kulcsszóra **rövid-/középtávú előrejelzés** a chart jobb szélétől a jövőbe, a meglévő
**LOESS-görbe alapján**, **5 külön horizont-gombbal** (1 nap / 1 hét / 1 hónap / 3 hónap / 1 év),
egymást kizárva. Az előrejelzés MINDIG **bizonytalansági sávval** (a hibát jelöljük), ami a
horizonttal szélesedik. A hosszú horizontokat őszintén kezeljük: nem rejtjük el, de a széles sáv +
figyelmeztetés kimondja, hogy pontbecslésként bizonytalanok. A predikciónak **saját vezérlő-szekciója**
van, a LOESS-kapcsolótól függetlenül.

## 2. Az adat és a statisztikai valóság (ez indokolja a döntéseket)

- A Google Trends 0–100-ra normált, szavanként külön skálázott, **zajos, gyakran szezonális és
  átlaghoz visszahúzó** sorozat. Felbontásonként más a múlt: órás (~1 hó, lánccal nő), napi (3 hó,
  ~92 pont), heti (1 év, 52 pont).
- **A LOESS simító, nem előrejelző.** Extrapolálni a görbét a szélén túl statisztikailag ingatag: a
  szélső szomszédság egyoldalú, a lokális meredekség kifelé húzva a zajt felnagyítja. → **csillapítás**
  kell (a trend ellaposodjon), és a hosszú távú pontbecslés **csak széles, empirikus sávval** őszinte.
- **Horizont-védhetőség (a döntés alapja):** 1 nap / 1 hét reális rövid extrapoláció; 1 hónap gyenge
  pont, de őszinte sávval megáll; 3 hónap / 1 év pontbecslésként ~értéktelen → **a sáv (nem a vonal)
  hordozza az üzenetet**, és figyelmeztetést kap.
- **A nem-alkukérdés:** a hibát MINDIG mutatjuk, és a horizonttal szélesednie kell. Sáv nélküli
  előrejelző vonal = hazugság; ezt a feature nem csinálja.

## 3. A modell — csillapított trend + szezon + EMPIRIKUS hibasáv

Szavanként, felbontásonként (a lezárt pont-sorozat `y` [0–100] és a rá illesztett LOESS `sim`).

### 3.1 Szint és trend a LOESS széléről (zajtalanítva)
- **Szint** `L = sim[-1]` (a LOESS utolsó, zajtalanított értéke).
- **Trend** `b` = a `sim` utolsó `w` pontjára illesztett egyenes meredeksége (per lépés; `w` kicsi,
  felbontás-arányos, pl. `w = clip(n//10, 3, 24)`), robusztus él-becslés.

### 3.2 Csillapított extrapoláció (damped trend)
- `ŷ(h) = L + b · Σ_{i=1..h} φ^i = L + b · φ·(1 − φ^h)/(1 − φ)`, `0<φ<1` (alap **φ=0,95**).
- A trend hozzájárulása `h→∞`-nél `b·φ/(1−φ)`-hoz telít → a görbe **ellaposodik**, nem szalad el.
- Minden `ŷ(h)` **[0,100]-ra vágva**.

### 3.3 Szezon — CSAK ahol becsülhető (≥2 teljes ciklus)
- Additív szezon-profil `s_k` (k=0..m−1) = a `(y − sim)` átlagos eltérése az adott fázison,
  **nulla-átlagúra centrálva** (a szint kétszeres beszámítása ellen).
- Periódus a felbontás szerint: **órás → m=24** (napszak), **napi → m=7** (hét). **Heti → NINCS
  szezon** (52 pont = 1 éves ciklus, ≥2 ciklus kell a becsléshez → tisztességtelen lenne).
- Feltétel: `n ≥ 2m`. Ha nem teljesül, nincs szezon-tag (a `szezon:false` a blokkban).
- Előrejelzés: `ŷ(h) += s_{(utolsó_fázis + h) mod m}` (majd [0,100]-vágás).

### 3.4 Empirikus hibasáv (gördülő-origó visszatesztelés)
- **K origó** a sorozat vége felé (alap **K = clip(n//4, 5, 20)**). Minden `o` origóra a 3.1–3.3
  recept fut `y[:o]`-n, előrejelez `Hmax` lépést, és a hibát `e_o(h) = y[o+h−1] − ŷ_o(h)` gyűjti,
  ahol a valós pont létezik.
- `RMSE(h) = sqrt(mean_o( e_o(h)² ))`. Nem csökkenőre simítva (kumulatív max, hogy a sáv monoton
  táguljon — a zaj ne szűkítse vissza egy távolabbi horizonton).
- **Sáv** `h`-ra: `ŷ(h) ± z·RMSE(h)`, **z=1,28 (80%)**, [0,100]-ra vágva.
- **Fallback** (kevés origó egy `h`-ra): reziduális alapú tágítás `RMSE(h) ≈ σ_reziduum·√h` (ahol
  `σ_reziduum = std(y − sim)`), és a `megbizhatosag` alacsonyabb. Ha egyáltalán nincs elég adat a
  horizonthoz (nincs megfelelő felbontású sorozat), az a horizont a szóra **nincs** (őszinte).
- **Kompromisszum (kimondva):** a backteszt `K × (LOESS O(o²))` — drága. Csökkentés: a backteszt-
  ágban a szint/trend a `y[:o]` OLCSÓBB simítójából jön (pl. mozgóátlag-alapú él, NEM teljes LOESS
  minden origón), a teljes LOESS csak a végső `sim`-hez. A napi futás idejét MÉRNI kell (lásd 9.).

### 3.5 Horizont ↔ felbontás leképezés
A legfinomabb sorozat, ami kényelmesen fedi a horizontot (≥ elég múlttal):
| Gomb | Sorozat | Lépés | h (lépésben) |
|---|---|---|---|
| 1 nap | órás | óra | 24 |
| 1 hét | órás | óra | 168 (ha az órás rövid: napi, 7) |
| 1 hónap | napi | nap | 30 |
| 3 hónap | napi | nap | 90 (vagy heti, 13) |
| 1 év | heti | hét | 52 |
Ha a szónak nincs meg a kellő felbontású sorozata (pl. még nincs heti lánc), az a horizont **nincs**
kiszámolva (a gomb a kártyán jelzi: „nincs elég adat ehhez a horizonthoz").

## 4. Architektúra

### 4.1 Backend — új modul `trendfigyelo/predikcio.py`
- Tiszta **numpy** (semmi új dep). Determinista (nincs random/`datetime.now()` a tesztelt logikában;
  a jövő-időbélyegek az adat utolsó pontjából + `h·lépés`-ből számolódnak).
- Fő függvények: `elorejelzes(y, sim, lepes_perc, m, horizontok, phi, z)` → horizontonkénti blokk;
  `_szezon_profil(y, sim, m)`, `_damped(L, b, h, phi)`, `_backteszt_rmse(y, ...)`.
- A `regresszio_szamit` / `regresszio_masodlagos_szamit` a **szó szintjén** (nem intervallumonként)
  hívja: a szó megfelelő felbontású sorozataiból számol, és egy **`predikcio`** blokkot ad a szó-
  rekordhoz. Nulla Google-hívás; a LOESS-t/nemlin-t nem bántja (additív).

### 4.2 Adat-séma (a regresszió-fájlokban, szó-szinten)
```json
"predikcio": {
  "1_nap": { "pont": [{"idopont_utc":"…","ertek":41.2}, …],
             "also": [{"idopont_utc":"…","ertek":33.1}, …],
             "felso":[{"idopont_utc":"…","ertek":49.3}, …],
             "rmse_veg": 8.1, "szezon": true, "modszer": "damped-LOESS",
             "megbizhatosag": 0.8, "figyelmeztetes": false },
  "1_het": { … }, "1_ho": { … }, "3_ho": { …, "figyelmeztetes": true },
  "1_ev":  { …, "figyelmeztetes": true }
}
```
Hiányzó horizont → a kulcs elhagyva (a frontend „nincs elég adat"-ot ír).

### 4.3 Frontend (`docs/js/app.js` + `docs/css/app.css`)
- Külön **„Predikció" sáv** (a mltrend-sáv mintájára), 5 **egymást kizáró** gombbal (1 nap / 1 hét /
  1 hó / 3 hó / 1 év) + alatta info-callout. Alapból egyik sincs kiválasztva (nincs predikció).
  `#kulcsszo-blokk[data-predikcio="1_nap|1_het|1_ho|3_ho|1_ev|ki"]`.
- Kiválasztott horizont: a chart jobb széléről a jövőbe húzódó **előrejelző vonal** (szaggatott,
  külön szín, pl. `PREDIKCIO_SZIN = "#16a085"`) + **árnyékolt sáv** (a `also`/`felso` közti kitöltés).
  A jövő-időbélyegek az x-tengelyt jobbra nyújtják.
- **Figyelmeztetés** a 3 hó / 1 év horizontnál: a charton + a gomb mellett „szemléltető — nagy
  bizonytalanság" jelölés.
- A kártya kiírja a horizont mért hibáját: „80%-os sáv: ±18 pont (1 hónapra)".
- A predikció **független** a LOESS-görbe kapcsolótól (belül a LOESS-ből számol, de saját vezérlő).
- Nincs `new Date()`/`Date.now()` — a jövő-időbélyegek a backendből jönnek.
- **Tengely/nézet:** az előrejelzés folytonos **idő-tengelyt** kíván (a jövő-pontok abszolút
  időbélyeggel jobbra nyújtják az x-tengelyt). Ezért a predikció a **teljes (idő-tengelyű / xy)
  nézeten** jelenik meg; a horizont a saját natív felbontásából rajzol (1 nap → órás pontok, 1 év →
  heti pontok — mind ugyanazon az idő-tengelyen, a chart jobb szélén túl). A **kategória-tengelyes fix
  nézeteken** (1_het/1_ho/… gombok, label-indexelt) a predikció-gombra kattintás a **teljes nézetre
  vált** (ott rajzol), mert a jövő nem mappelhető label-indexre. A predikció-sáv csak akkor látszik,
  ha van kiválasztott horizont ÉS a szónak van rá számolt blokkja.

### 4.4 Pipeline
A napi futásban a regresszió-ág UTÁN (vagy abba integrálva), nulla Google-hívás, determinista. A
pótolhatatlan órás lánc + a lineáris/nemlin változatlan. Minden szóra fut (esemenyjelző is — ott a
sáv nagyon széles lesz, ami őszinte).

## 5. Bizonytalanság + őszinteség (összefoglalva)
- A sáv MINDIG látszik (a vonal soha nem áll sáv nélkül).
- A sáv **empirikus** (visszatesztelt valós hiba), nem elméleti feltevés.
- A hosszú horizont **ellaposodó** ponttal + **széles** sávval + **figyelmeztetéssel** jelenik meg.
- A megjelenített szám a horizont valós hibája (nem kitalált pontosság).

## 6. Az „Az adatokról" oldal
Új doboz: **„Előrejelzés — hogyan és meddig?"** — a módszer (LOESS-szint + csillapított trend +
szezon), miért csillapított (nem szalad el), mit jelent a sáv (80%-os empirikus, visszatesztelt), és
**miért óvatos a hosszú táv** (a Google Trends nem hordoz 1 év előre jelezhető jelet; a sáv szélessége
maga a figyelmeztetés). A képletek dióhéjban, a nemlin-doboz mintájára.

## 7. Tesztelés (TDD)
- **Backend:** fabrikált lineáris+szezonos sorozat → a pont az elvárt közelébe esik; a `RMSE(h)`
  horizonttal NŐ (monoton sáv); a csillapítás nem lép ki [0,100]-ból; determinizmus (kétszeri futás
  bájt-azonos); szezon csak `n≥2m`-nél; kevés adatnál tág/fallback sáv; hiányzó felbontás → nincs
  horizont.
- **Frontend (e2e):** a gombok kizárólagossága (egyszerre egy); a kiválasztott horizont sávot+vonalat
  rajzol a jövőbe; a 3 hó/1 év figyelmeztetés megjelenik; kikapcsolás (nincs predikció-dataset);
  hiányzó horizont-gomb „nincs elég adat" jelzése.

## 8. Hatókörön kívül (v1)
- ARIMA/Prophet/állapottér auto-modellezés (nem determinista/nehéz numpyban, robusztus auto-fit 28
  heterogén szóra kockázatos). A LOESS+damped+empirikus-sáv a pragmatikus, átlátható választás; a
  backteszt validálja (ha a hiba nagy, a sáv őszintén mutatja).
- Heti (1 év) sorozaton szezon (nincs ≥2 ciklus).
- A napi AI-elemzés predikció-összefoglalója (a metrikák a payloadba) — külön, későbbi kör.

## 9. Kockázatok / megjegyzések
- **Számítási költség:** a backteszt (`K` origó × recept) a fő tétel — a nemlin már ~6,5 s. A 3.4
  olcsóbb backteszt-simítója enyhít, de a napi futás idejét **mérni kell**; ha sok, `K` csökkenthető /
  a hosszú-táv backteszt ritkítható (USER-döntésre a cap).
- **Determinizmus-kapu:** semmi véletlen; a jövő-időbélyegek az adat utolsó pontjából számolódnak.
- **[0,100]-vágás mindenütt** (pont ÉS sáv) — a becslés nem hazudik skálán kívüli értéket.
- **Adatméret:** a `predikcio` blokk 5 horizont × ~3×N_pont — a regresszió-JSON nő; ritkított pont-
  sorozat (horizontonként ~20–40 pont) tartja kordában.
