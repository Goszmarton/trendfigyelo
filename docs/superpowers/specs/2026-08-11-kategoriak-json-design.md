# Task 3b — `kategoriak.json` kategória-aggregátum (design)

Dátum: 2026-08-11
Spec-horgony: `docs/superpowers/phase3/phase3-spec.md` §8.1 (+ §7.5 hivatkozva)
Hatókör: **adatréteg, felület nélkül.** A heti/havi eloszlás-görbe megjelenítése
NEM ennek a tasknak a hatóköre.

## 1. Cél

Új kimenet `docs/data/kategoriak.json`, amely a napi felkapott trendlista
`temak` kategóriáit **napi bontásban** aggregálja, hogy a történet a Task 3a
élesítésétől (2026-08-05) épüljön, és később heti/havi részesedés-görbe
építhető legyen belőle. A §8.1 két követelménye: tárolni a **kategóriánkénti
nyers darabszámot ÉS a napi trendlista teljes hosszát** (a puszta darabszám
félrevezet, mert rövid listán a részesedés ugrál).

## 2. Kiinduló mérés (2026-08-11, rögzítve)

18 napi fájl `docs/data/napok/`-ban, három csoport:

| Csoport | Napok | Db | Sors |
|---|---|---|---|
| Nincs `temak` kulcs (3a előtti) | 2026-07-23 … 08-04 | 13 | **Kihagyva** — kategória nem visszaszerezhető, és a §8.1 szerint a történet 3a-tól épül |
| `temak` kulcs jelen, van nem-üres | 2026-08-05, 07, 08, 09, 10 | 5 | **Backfill** (mind API-nap, mind trend kategorizált) |
| Nincs napi fájl | 2026-08-06 | 1 | **Nem reprezentálható** — kimaradt futás; a hiányt a `napok/index.json` hiánya jelöli |

**RSS-only nap (kulcs jelen, de mindenhol `[]`): a valós adatban ma 0 db.** A
sémának mégis kezelnie kell, mert jövőben előfordulhat, és a §8.1 „kategória
nélküli" gyűjtője különben egybemosná a hiányzó mezős és az üres-lista esetet.

## 3. A kulcsdöntés: az idősor explicit a nem-mért napról

A `kategoriak.json` **idősor**. Idősorban a hiányzó bejegyzés **kétértelmű** —
nem különbözteti meg a „futottunk, de nem mértünk kategóriát" esetet a „még
nem jutottunk el odáig / nem futottunk" esettől. A heti/havi görbénél pont ez
számít: egy **nem-mért nap kihagyandó a nevezőből**, egy **hiányzó nap** csak
annyit jelent, hogy nem tudjuk. Ugyanaz a minta, mint a
`data-idosor-allapot`-nál: **explicit jelölés > néma hiány.**

Ezért:

- **Mért nap** → `merve: true` + aggregátum.
- **Nem-mért nap, amelyről VAN napi fájl** (RSS-only) → `merve: false` + `ok`.
- **Hiányzó nap** (nincs napi fájl, pl. 08-06) → **NINCS bejegyzés.** A
  `merve: false` azt jelenti, „futottunk és nem mértünk"; a 08-06-on nem
  futottunk. A fájl **csak azokról a napokról nyilatkozik, amelyekről van napi
  fájl** — nem modellez olyan állapotot, amiről nincs adat.
- **3a előtti nap** (nincs `temak` kulcs sehol) → **NINCS bejegyzés** (más
  korszak; a történet 3a-tól épül, §8.1).

## 4. Fájl-alak

`tortenet.json` mintájára `{ "napok": [ ... ] }`, nap szerint rendezve.

```json
{
  "napok": [
    {
      "nap": "2026-08-10",
      "merve": true,
      "lista_hossz": 20,
      "lista_kategoriaval": 20,
      "kategoria_nelkul": 0,
      "kategoriak": { "Other": 6, "Sports": 3, "Health": 2 }
    },
    {
      "nap": "2026-08-12",
      "merve": false,
      "ok": "nincs_kategoria_adat",
      "lista_hossz": 15
    }
  ]
}
```

**`merve: true` mezők:**

- `lista_hossz`: a napi trendlista teljes hossza (§8.1 nevező).
- `lista_kategoriaval`: hány trendnek van legalább egy nem-üres `temak`.
- `kategoria_nelkul`: hány trend `temak`-ja `[]` **vagy** hiányzó kulcs (§8.1
  „kategória nélküli" gyűjtő). `lista_hossz = lista_kategoriaval + kategoria_nelkul`.
- `kategoriak`: `{ temak_név: darabszám }`. **Minden elem MINDEN `temak`-jában
  számít** (a többértékű trend többször), ezért a darabszámok összege
  **meghaladhatja** `lista_hossz`-t (§8.1). Az **„Other" valódi Google-kategória**
  (topic ID 11), saját kulcsként szerepel — **NEM** a `kategoria_nelkul` gyűjtő.
  A `kategoriak` **kulcs-sorrendje nem jelentőségteljes** (a fenti példa
  count-csökkenő, de a data-fájl fogyasztója maga rendez, mint a Task 7 frontend).

**`merve: false` mezők:**

- `ok`: **zárt, dokumentált értékkészlet.** Ma az egyetlen érték
  `"nincs_kategoria_adat"` (mező jelen, de minden `temak` üres). A mező
  **MEGFIGYELÉST rögzít** (nincs kategória-adat ezen a napon), **nem OKOT** — a
  kód nem tudja megállapítani, hogy azért nincs adat, mert az RSS-ág futott,
  vagy másért; ezért a név nem állít okot (ugyanaz a fegyelem, mint az L12
  párhuzamos-flake és a „fésű"-korrekció esetében: plauzibilis magyarázat ≠
  megállapított ok). A valódi ág **utólag a `naplo.csv`-ből állapítható meg** (a
  `felkapott_api` sor megléte) — az információ nem vész el, csak nem ebbe a
  mezőbe kerül. Az értékkészlet **bővíthető**: ha később más, ténylegesen
  megállapítható ok merül fel, az **ÚJ érték** legyen, nem ebbe söpörve. **Ma
  egyik `ok`-érték sem fordult elő valós adatban** — ez az ág egyelőre elméleti.
- `lista_hossz`: megtartva (a lista létezik, csak kategória nincs).
- **Nincs** `kategoriak` / `kategoria_nelkul` (nem mértünk).

## 5. Aggregálási + osztályozási logika

Egy napi fájl (`{ "nap", "trendek": [...] }`) → egy rekord **vagy** `None`
(kihagyás). A diszkriminátor a **nem-üres `temak` megléte**, NEM pusztán a
`tem_m > 0` (a kulcs jelenléte) — lásd az alábbi négy esetet, mindegyik mellett a
mai valós előfordulásával. `tem_m = azon elemek száma, ahol a "temak" KULCS jelen van`:

| Eset | Feltétel | Eredmény | Mai előfordulás |
|---|---|---|---|
| Nincs sehol `temak` kulcs | `tem_m == 0` | **`None`** (kihagyás) | **VALÓS: 13 nap** (07-23…08-04) |
| Van kulcs, van nem-üres | `van_kategoria` | **`merve: true`** + aggregálás | **VALÓS: 5 nap** (08-05…08-10) |
| Van kulcs, mind üres | `tem_m>0`, nincs nem-üres | **`merve: false`**, `nincs_kategoria_adat` | **ELMÉLETI: 0 nap** |
| Vegyes (némelyiken kulcs, némelyiken nem) | — | a nem-üresek szerint (lásd lent) | **ELMÉLETI: 0 nap** |

`van_kategoria = van legalább egy nem-üres temak`. A `merve:true` aggregálás:

```
for e in trendek:
    temak = e.get("temak") or []      # hiányzó kulcs VAGY [] → []
    if not temak:  kategoria_nelkul += 1
    else:          lista_kategoriaval += 1; minden k-ra kategoriak[k] += 1
```

**Miért a nem-üres megléte a diszkriminátor, nem a `tem_m > 0`:** ha a puszta
`tem_m > 0` döntene (`merve:true`), akkor a **valós RSS-only nap** — ahol a
`top_trend_struktura` MINDEN elemre ráteszi a `temak` kulcsot, mind `[]`, tehát
`tem_m = len > 0` — tévesen `merve:true` lenne. Ezzel **pont az az eset
semmisülne meg, amiért a `merve` mezőt bevezettük**: a `nincs_kategoria_adat`
jelölés célja tűnne el. Ezért a `merve:true` feltétele a **nem-üres `temak`
megléte**.

**Vegyes nap (ELMÉLETI — a pipeline nem állítja elő):** elvileg előállhat olyan
nap, ahol **néhány** elemen van `temak` kulcs, néhányon nincs. Ilyenkor a
besorolás a nem-üresek szerint dől el (`van_kategoria` → `merve:true`, különben
`merve:false`), és a kulcs nélküli / üres elemek a `kategoria_nelkul`-ba esnek
(§8.1 gyűjtő). **Ez az eset a valós adatban nem áll elő** — a
`top_trend_struktura` minden elemre ráteszi a `temak` kulcsot, vagy (3a előtt)
egyikre sem; sosem vegyesen. Ugyanaz a fegyelem, mint az `ok` értékkészleténél:
ami nem fordult elő valós adatban, azt **elméletiként** jelöljük. A
`test_vegyes_nap_merve_true` regressziós őr (a kulcs nélküli elem a gyűjtőbe
essen, ne dobjon hibát), de elméleti esetet őriz.

**Dokumentált korlát:** a `nincs_kategoria_adat` felismerés heurisztika
(mező-jelen + mind-üres). Elvi álpozitív: egy API-nap, ahol az API **egyetlen**
trendhez sem adott kategóriát, tévesen `merve:false`-nak jelölődne. **Empirikusan
nem fordult elő** — minden megfigyelt API-nap teljesen kategorizált (15/15 …
20/20). A napi fájl nem hordoz explicit ág-jelölőt, ezért ez a legjobb elérhető
megkülönböztetés; a valódi ág utólag a `naplo.csv`-ből fejthető vissza (lásd §4).

## 6. Modul + bekötés

**Új modul `trendfigyelo/kategoriak.py`** (a `regresszio.py` / `nyers_kimenet.py`
mintájára — önálló kimenet, egy felelősség):

- `kategoria_aggregatum(nap_iso, trendek) -> dict | None` — **tiszta függvény**,
  a §5 logikája. Ez a TDD gerince.
- `kategoriak_ir(docs_data) -> Path` — a `napok/index.json` szerinti összes
  napi fájlt beolvassa, minden napra `kategoria_aggregatum`-ot hív, a `None`-t
  kihagyja, a `merve:false`-t/`merve:true`-t felveszi, nap szerint rendez, kiír.

**Eltérés a spec §9-től (explicit jelölve):** a §9 3b-sora „aggregátum
**upserttel**"-t ír. Itt tudatosan **teljes újraépítésre** (determinisztikus
tükör) váltunk a forward-upsert helyett, mert (a) a mérés fő célja a **backfill**
volt — egy csak-előre upsert az 5 meglévő napot **nem** pótolná vissza
automatikusan, iterálni kellene rajtuk; a tükör ezt természetesen megteszi; (b)
idempotens és önjavító (nincs Minor 3-típusú elsodródás); (c) illeszkedik a
`regresszio.json` származtatott-nézet mintájához. A **kimeneti fájl
upsert-ekvivalens**, csak elsodródás-mentes.

**A `kategoriak.json` a `napok/*.json` determinisztikus tükre** — a
`regresszio.json` mintájára származtatott nézet. Előny:

- **Az első futás magától backfilleli** az 5 meglévő napot (nincs külön script).
- **Önjavító és idempotens** — nincs Minor 3-típusú duplikálódás; a fájl mindig
  a napi fájlok függvénye.
- Olcsó: ma ~18–30 kis JSON beolvasása futásonként.

**Skálázási nagyságrend (hogy egy év múlva ne kelljen újramérni):** a `napok/`
halmozódik (nincs retenció), a tükör futásonként beolvassa az összeset. A napi
fájlok kicsik (~10–50 KB), a teljes beolvasás **~500 nap felett válik
érezhetővé** (nagyságrendileg 10–25 MB napi I/O). Ekkor a `naplo_max_sor`
mintájára a megoldás **retenció** (a tükör csak az utolsó N napot építi) **vagy
inkrementális upsert** (a mai nap hozzáírása a meglévő fájlhoz, a többi
érintetlen). Phase 3-ban egyik sem kell — a küszöb ~1,5 évnyi napi futás.

**Bekötés a `futtato.main`-ben**, közvetlenül a `napi_ir` (210. sor) UTÁN (hogy a
mai napi fájl már elérhető legyen), a **regresszió-ág védelmi mintájával**
(215–242): `try/except`, hiba → `FIGYELEM` a run.log-ba + `kategoriak` naplósor
(`eredmeny=hiba/siker`), **sosem blokkolja az adatmentést vagy az exit-kódot**,
és **nem néma** (finding 6). Nulla Google-hívás.

## 7. TDD-diszkriminátorok (a plan részletezi)

`tests/test_kategoriak.py`, valódi RED-ekkel:

1. **Multi-kategória számlálás:** egy elem `temak=["A","B"]` → mindkettőben +1;
   `sum(kategoriak) > lista_hossz` lehetséges.
2. **`kategoria_nelkul`:** `temak=[]` ÉS hiányzó `temak` kulcs is ide számít.
3. **„Other" nem gyűjtő:** `temak=["Other"]` → `kategoriak["Other"]`, nem
   `kategoria_nelkul`.
4. **`nincs_kategoria_adat`:** minden elem `temak=[]` (kulcs jelen) →
   `merve:false`, `ok:"nincs_kategoria_adat"`, nincs `kategoriak`.
5. **3a előtti nap:** egyik elemnek sincs `temak` kulcsa → `None` (kihagyás).
6. **`lista_hossz = lista_kategoriaval + kategoria_nelkul`** invariáns.
7. **`kategoriak_ir` integráció a valós 5 napi fájlon:** 5 `merve:true` rekord,
   0 `merve:false`, a 13 régi nap kihagyva, nap szerint rendezve.
8. **Determinisztikus tükör:** kétszeri `kategoriak_ir` azonos kimenet (idempotencia).
9. **Vegyes nap:** néhány elemen van `temak` kulcs, néhányon nincs → `merve:true`,
   és a kulcs nélküli elemek a `kategoria_nelkul`-ban (nem `None`, nem `merve:false`).

## 8. Amit ez a task NEM csinál

- **Nincs felület** — heti/havi görbe a megjelenítési körben (más nap).
- **Nincs `napok/*.json` visszapótlása** kategóriával (a 13 régi nap kimarad;
  ezt a commit-üzenet is rögzíti, hogy később ne tűnjön hibának).
- **Nincs új Google-hívás** — a `tervezett_hivasszam` és a hívás-plafon
  változatlan.
- A 08-06 hiányzó nap nem kap bejegyzést (nincs napi fájl).
