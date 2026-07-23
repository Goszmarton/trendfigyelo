# Trendfigyelő — tervdokumentum (spec)

**Dátum:** 2026-07-23
**Repó:** Goszmarton/trendfigyelo (publikus)
**Állapot:** jóváhagyott terv, implementáció előtt

## 1. Cél és kontextus

Napi rendszerességgel gyűjtő + megjelenítő rendszer a **magyarországi** Google
Trends adatokra. A meglévő `top_keresesek.py` (trendspy alapú, geo=HU, 24 órás
felkapott keresések két forrásból) kibővítése:

1. Felkapott HU keresések gyűjtése (megvan, marad).
2. **ÚJ:** a felkapott trendek 24 órás idősorai (sparkline-ok).
3. **ÚJ:** fix, konfigból szerkeszthető kulcsszólista napi 24 órás követése.
4. Automatizálás GitHub Actions-szel (napi egy futás).
5. Statikus webes megjelenítő GitHub Pages-en (`docs/`).

**A programnyelv Python** (a gyűjtő is az); a megbízhatóság az elsődleges.

## 2. Két kiemelt, nem-alkudható követelmény

### 2.1 Magyarország-fókusz mindenhol
- **Minden** Google-hívásban `geo="HU"`: felkapott lista, RSS, trend-idősorok
  ÉS a saját kulcsszavas `interest_over_time` is (utóbbinál geo nélkül a Trends
  világadatot ad — az itt hiba).
- Időablak mindenhol az **elmúlt 24 óra** (`hours=24` ill. `timeframe="now 1-d"`).
- Nyelv magyar (`language="hu"`).
- `geo` / időablak / nyelv **egyetlen helyen** (config), minden modul onnan veszi.
- Minden CSV-sor és JSON-bejegyzés tartalmazza a `geo` mezőt.
- A weben cím/fejléc szinten egyértelmű a HU-fókusz.
- Megjelenítés és fájlnevek **budapesti idő** (Europe/Budapest); nyers adat UTC.

### 2.2 IP-blokkolás elleni védelem (a legnagyobb kockázat)
- Kíméletes ütem: hívások közt véletlenített **3–7 mp** késleltetés.
- Minimális hívásszám: semmit kétszer; kulcsszavak 4+1 kötegben; a futás
  kiírja a tervezett és tényleges hívásszámot (cél: néhány tucat alatt).
- **Napi egy futás**; nincs rövid ciklusú tömeges retry.
- **429 → exponenciális, jitteres visszavárakozás** (3–5 próba, kb.
  30 mp → 2 perc → 8 perc), utána az **ág feladása** az adott napra + naplózás.
- **Részleges siker is siker:** egy ág bukása nem dönti a többit; a workflow
  csak akkor bukik, ha **semmilyen** adat nem jött.
- **Blokkolás-észlelés:** `adatok/naplo.csv` rögzíti időpont/ág/eredmény/
  hívásszám/hibakódok. Ha minden ág 429-et kap → nem-nulla kilépési kód
  (GitHub e-mail értesítés).
- **B terv:** módosítás nélkül futtatható helyi gépről (lakossági IP); README
  lépésről lépésre. Opcionális HTTP(S) proxy a configból (alap: proxy nélkül).
- Böngészős user-agent + magyar nyelvi fejlécek, ahol a trendspy engedi.

## 3. Architektúra — Python-csomag

A `top_keresesek.py` egyben túl nagy lenne. Fókuszált modulok a `trendfigyelo/`
csomagban; a régi belépési pont vékony wrapperként marad.

```
trendfigyelo/
├── __init__.py
├── config.py        # config.yaml betöltés + validálás; egyetlen forrás
├── kliens.py        # Trends-gyártás (UA, request_delay, opcionális proxy) + 429 backoff wrapper + hívásszámláló
├── felkapott.py     # trending_now API + RSS → a meglévő 3 CSV (változatlan)
├── idosorok.py      # trend-sparkline-ok (showcase_timeline, fallback top-N iot) → új CSV
├── kulcsszavak.py   # 4+1 kötegelt interest_over_time, nyers+normalizált → új CSV
├── naplo.py         # adatok/naplo.csv
├── json_export.py   # docs/data/*.json építés/frissítés
└── futtato.py       # main: ágak sorban, részleges siker, kilépési kód
top_keresesek.py     # vékony belépő: from trendfigyelo.futtato import main
```

**Modul-elvek:** minden modulnak egy dolga van, jól definiált be/kimenettel,
külön tesztelhető. A lekérdező modulok a `kliens.hivas(...)` wrappert használják;
nem hívják közvetlenül a trendspy-t, így a geo/időablak/backoff nem maradhat le.

## 4. Konfiguráció — `config.yaml`

Egyetlen forrás; a `config.py` betölti és validálja (hiányzó/rossz mező →
érthető hiba). PyYAML függőség.

```yaml
geo: HU
nyelv: hu
idoablak_orak: 24
idosor_idokeret: "now 1-d"
referenciaszo: "időjárás"
kerespont:
  alap_keses_mp: 3.0
  szoras_mp: [3, 7]        # véletlen 3–7 mp két hívás közt
  max_probak: 4
  backoff_mp: [30, 120, 480]
trend_idosor_max: 15       # hány top trend kap sparkline-t fallback esetén
proxy: null                # pl. "http://user:pass@host:port" — alap: nincs
kulcsszavak:
  megelhetes: [infláció, benzinár, rezsi, élelmiszerárak, albérlet, lakáshitel, minimálbér, nyugdíj]
  gazdaság:   [forint árfolyam, euró árfolyam, MNB, kamat, munkanélküliség, adóváltozás]
  közélet:    [választás, kormány, népszavazás, tüntetés, egészségügy, oktatás, pedagógus, kórház]
```

Új kulcsszó felvétele **kizárólag** e fájl szerkesztésével működik.

## 5. Anti-block motor (`kliens.py`)

- `Trends(language=hu, request_delay=alap_keses_mp, proxy=...)` böngészős
  user-agenttel (ha a trendspy engedi a headerek felülírását).
- `hivas(fn, ag_nev, *args, **kwargs)` wrapper:
  - minden hívás előtt véletlen 3–7 mp alvás;
  - 429 (ill. rate-limit jelzés) elkapása → backoff `[30,120,480]` mp + jitter,
    max `max_probak` próba;
  - kimerülés után `AgFeladva` kivétel + naplóbejegyzés (nincs további retry);
  - ágankénti és összesített hívásszámláló.
- A `futtato.py` a futás elején kiírja a tervezett hívásszámot, végén a
  ténylegeset.

## 6. Adatkimenetek — CSV (`adatok/`)

### 6.1 Meglévő három CSV — VÁLTOZATLAN
`top_keresesek_api_HU_...csv`, `..._rss_...`, `..._hirek_...`: jelenlegi
oszlopszerkezet, budapesti időbélyeg a névben, `;` elválasztó, utf-8-sig, geo
oszloppal. Nem írjuk felül ok nélkül.

### 6.2 Új: trend-idősorok CSV
`top_trend_idosor_HU_<bp_idobelyeg>.csv`
Oszlopok: `kifejezes; idopont_utc; ertek; letoltve_utc; forras; geo`
Forrás elsődlegesen `trending_now_showcase_timeline` (1 hívás, minden
sparkline); ha nem elérhető, a top-`trend_idosor_max` trendre egyenkénti
`interest_over_time(geo=HU, timeframe="now 1-d")`. A `forras` oszlop jelzi,
melyik ág adta.

### 6.3 Új: kulcsszó-idősorok CSV
`kulcsszo_idosor_HU_<bp_idobelyeg>.csv`
Oszlopok: `kulcsszo; csoport; idopont_utc; nyers_ertek; normalizalt_ertek;
koteg_id; referenciaszo; letoltve_utc; geo`
- 4 kulcsszó + 1 referenciaszó kötegenként (24 szó ≈ 6 hívás).
- **Nyers** (0–100 a kötegben) és **normalizált** (referenciaszóra átskálázott)
  érték is mentődik — a normalizálási logika utólag javítható adatvesztés nélkül.
- Normalizálás: a köteg értékeit a köteg referenciaszó-idősorával skálázzuk,
  hogy a kötegek egymással összemérhetők legyenek.

### 6.4 Futásnapló
`adatok/naplo.csv` — soronként: `futas_ido_utc; ag; eredmeny(siker/reszleges/
hiba); hivasok_szama; hibakodok`. Új futás hozzáfűz.

## 7. Adatkimenetek — JSON a webhez (`docs/data/`)

- **`legfrissebb.json`** (mindig felülírva): a legutóbbi futás összesítése —
  top HU trendek (volumen, növekedés, idősor), saját kulcsszavak aznapi
  idősorai (csoportonként), frissítés időpontja, geo.
- **`tortenet.json`** (növekvő): naponta egy bejegyzés kulcsszavanként, a napi
  **átlag ÉS csúcs** normalizált értékkel (mindkettőt tároljuk; a UI választ).
  Túl nagy méret esetén évenkénti darabolás.
- **`napok/<ÉÉÉÉ-HH-NN>.json`** (napi egy fájl): az adott nap top trendjei
  teljes részletességgel (kifejezés, volumen, növekedés, idősor, kapcsolódó
  hírek). Így a napi trendlista visszalapozható a fájl elhízása nélkül.
- **`napok/index.json`**: az elérhető napi fájlok dátumlistája (a
  dátumválasztóhoz).
- Minden futás frissíti a JSON-okat; a web kizárólag ezekből dolgozik
  (statikus, nincs backend).

## 8. GitHub Actions — `.github/workflows/napi.yml` (Phase 2)

- Ütemezés: naponta **egyszer** cron (19:00 UTC) + `workflow_dispatch`.
  Nincs sűrűbb ütemezés (IP-védelem).
- Lépések: checkout → Python → `pip install -r requirements.txt` → szkript →
  változások commit + push (csak ha van változás; `GITHUB_TOKEN`,
  `permissions: contents: write`).
- A 2.2 megbízhatósági/blokk-kezelési szabályok a workflow-ra is vonatkoznak
  (teljes blokk → nem-nulla kód → e-mail).

## 9. Webes felület (`docs/`, Phase 3)

- Sima HTML + CSS + JS, Chart.js CDN-ről; **nincs build-lépés**.
- Tartalom, végig **magyarul**:
  1. Fejléc: „Trendfigyelő — magyarországi keresési trendek", utolsó frissítés
     budapesti idő szerint.
  2. Saját kulcsszavak: vonaldiagram(ok) 24 óra; csoportonként (megélhetés /
     gazdaság / közélet) szűrhető/kapcsolható; + hosszú távú nézet a
     `tortenet.json`-ból.
  3. Napi top trendek: kártyák/táblázat (kifejezés, volumen, növekedés %,
     kezdés), mindegyik mellett sparkline a mentett idősorból; **dátumválasztó**
     a korábbi napok trendlistáihoz (`napok/index.json` + `napok/<dátum>.json`).
  4. Kapcsolódó hírek linkjei a top trendeknél.
- Hibatűrés: hiányzó/hiányos JSON → „az adat nem elérhető", az oldal nem omlik.
- Reszponzív (mobilon is használható).

## 10. Tesztelés

- **Nincs élő Google-teszt** (hívásokat égetne, blokkot kockáztat).
- Rögzített trendspy-válasz **fixtúrákkal (mock)** teszteljük: parszolás,
  4+1 kötegelés, normalizálás, JSON-építés, 429-backoff, részleges-siker
  logika, kilépési kódok.
- Egy kézi **füst-teszt élesben, helyi gépről** (a felhasználó választása
  szerint az első éles futás lokálisan).

## 11. Fázisok (jóváhagyott sorrend)

- **Phase 1 — adatréteg:** `config.yaml`, `trendfigyelo/` csomag minden gyűjtő
  modullal, CSV + JSON kimenetek, tesztek, `requirements.txt`. Helyi éles
  füst-teszt valós HU adaton.
- **Phase 2 — automatizálás:** `.github/workflows/napi.yml`, commit/push.
- **Phase 3 — web:** `docs/` statikus oldal a JSON-okból.

## 12. Repó-szerkezet (cél)

```
trendfigyelo/
├── top_keresesek.py           # vékony belépő
├── trendfigyelo/              # csomag (ld. 3. pont)
├── config.yaml
├── requirements.txt           # rögzített/alsó-korlátos verziók
├── README.md                  # magyarul: mit gyűjt (HU-fókusz), beüzemelés, Pages bekapcsolás, kulcsszó-hozzáadás, hívásszám, B terv
├── .gitignore
├── .github/workflows/napi.yml
├── adatok/                    # CSV-k + naplo.csv
└── docs/                      # web + data/*.json
```

## 13. Elfogadási feltételek

1. Helyi futtatásra hibamentesen legenerálódik minden CSV és JSON (kulcsszavakkal
   együtt); minden adat `geo="HU"`, elmúlt 24 órás.
2. Egy futás Google-hívása néhány tucat alatt, véletlenített késleltetéssel;
   429 → exponenciális backoff, majd ág-feladás + naplózás.
3. A workflow kézi indításra lefut és commitol; blokk esetén részleges adat +
   értelmes napló; teljes blokknál nem-nulla kód (e-mail).
4. A Pages-oldal betölti a JSON-okat, kirajzolja a grafikonokat friss HU
   adattal, és a dátumválasztóval visszalapozhatók a korábbi napi trendlisták.
5. Új kulcsszó felvétele kizárólag a `config.yaml` szerkesztésével működik.
