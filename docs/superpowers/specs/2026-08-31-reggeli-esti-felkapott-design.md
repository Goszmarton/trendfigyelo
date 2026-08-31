# Reggeli és esti felkapott-gyűjtés — tervdokumentum (spec)

**Dátum:** 2026-08-31
**Repó:** Goszmarton/trendfigyelo (publikus)
**Állapot:** jóváhagyott terv (brainstorming lezárva), implementáció előtt
**Érintett rétegek:** szerver-időzítés (Hetzner-cron), GitHub Actions, Python gyűjtő-pipeline, adatmodell, frontend (3 megjelenítő felület)

## 1. Cél

Ma a felkapott (napi trend-keresések) gyűjtése **naponta egyszer**, az esti teljes
futásban történik (felkapott + kulcsszavak együtt). A cél: **napi KÉT** felkapott-pillanatkép —
egy **reggeli** (9:00 Budapest, CSAK felkapott keresések, kulcsszó NÉLKÜL) és egy **esti**
(21:00 Budapest, felkapott + kulcsszó, ahogy MOST) — és **mindkettő megjelenítése** a
honlapon három felületen.

Fogalmi indok: a reggeli pillanatkép „mi pörög 9-kor" korai képe, az esti „a nap beállt
képe". A kettő külön érték; a felhasználó látni akarja mindkettőt (nem az esti felülírja a
reggelit, hanem egymás mellett élnek).

A determinisztikus helyesség és a pótolhatatlan Google-adat védelme elsődleges. A
programnyelv Python (gyűjtő) + vanília JS (frontend).

## 2. Jelenlegi állapot (feltárás, 2026-08-31)

### 2.1 Gyűjtés — mind-vagy-semmi, nincs „csak felkapott" út
- Belépő: `.github/workflows/napi.yml` → `python top_keresesek.py` → `trendfigyelo/futtato.py`
  `main()` (579) → `futtat()` (299). **Nincs argparse, nincs mód-kapcsoló** a napi
  belépőn (csak a `PLAFON_OVERRIDE` env-plafon).
- A `futtat()` **kötött ágsorrendet** futtat (futtato.py:321–343): `felkapott_api` (322) →
  `felkapott_rss` (324) → `kulcsszo` (328, KULCSSZÓ) → `idosor` (334, felkapott-származék) →
  `kulcsszo_masodlagos` (339, KULCSSZÓ) → `idosor_rekesz` (343, felkapott-származék).
- A meglévő „only" belépő (`trendfigyelo/masodlagos_only.py`, `masodlagos_only.yml`) az
  ELLENKEZŐJE: csak kulcsszó-cellákat gyűjt, felkapottat nem, és nem commitol. Mintát ad az
  argparse-hoz, de nem használható újra a reggeli felkapott-only futáshoz.

### 2.2 Felkapott adatmodell
- `top_trend_struktura()` (futtato.py:209–251) állítja elő a felkapott-listát; elem-mezők:
  `kifejezes, volumen, novekedes_pct, topics, temak, idosor ({idopont_utc, ertek}), hirek`.
- **`docs/data/legfrissebb.json`** — a legfrissebb TELJES pillanatkép (`json_export.legfrissebb_ir`,
  json_export.py:81–94). Kulcsok: `geo, frissitve, top_trendek` (felkapott), `trend_idosorok`,
  **`kulcsszavak`, `kulcsszo_osszesites`** (KULCSSZÓ-diagram adata), opcionális `modszertan_valtas`.
  **Minden futásnál teljesen felülíródik.**
- **`docs/data/napok/<YYYY-MM-DD>.json`** — a per-naptári-nap pillanatkép (`json_export.napi_ir`,
  json_export.py:136–148), **Budapest-naptári napra kulcsolva** (`nap_iso`, futtato.py:309).
  Alak: `{"nap": nap_iso, "trendek": [...]}` (ugyanaz az elem-alak, mint a `top_trendek`).
  Írás: futtato.py:407 `if top_trendek:`. **Azonos napon a második futás felülírja.**
  A `napi_ir` egyúttal upsertálja a napot a `napok/index.json` (`{napok:[ISO...]}`) halmazba.
- **`docs/data/kategoriak.json`** — SZÁRMAZTATOTT (nulla Google-hívás), `kategoriak.kategoriak_ir()`
  (kategoriak.py:50–70, hívás futtato.py:424) újraépíti minden futáskor a `napok/index.json` +
  az összes `napok/<nap>.json` fájlból. Alak: `{"napok":[{nap, merve, lista_hossz,
  lista_kategoriaval, kategoria_nelkul, kategoriak:{Kategória:count}}]}`.

### 2.3 Kulcsszó — amit a reggeli KIHAGY
Kulcsszó-ágak: `kulcsszo` (futtato.py:328) + `kulcsszo_masodlagos` (339). Származtatott
kulcsszó-lépések: `tortenet_frissit_napok` (403–405), `ir_gordulo`/`frissit_lanc` (409–417),
`regresszio` (437–460), `regresszio_masodlagos` (466–484). Kimenetek (mind kulcsszó-only, NEM
felkapott): `kulcsszo_nyers.json, kulcsszo_lanc.json, kulcsszo_masodlagos_nyers.json,
kulcsszo_regresszio.json, kulcsszo_masodlagos_regresszio.json, tortenet.json`, valamint a
`legfrissebb.json` `kulcsszavak`/`kulcsszo_osszesites` kulcsai.
**Az `idosor` és `idosor_rekesz` (ág 4/6) felkapott-származékok** (a trend-keresések
görbéi/rekesz-sparkline-jai) → a **reggeli futásban BENNE maradnak**.

### 2.4 Napló + idempotencia-őr
- `adatok/naplo.csv` (`naplo.naplo_ir`, naplo.py:9–23), APPEND, `;`-elválasztott. Fejléc:
  `futas_ido_utc;ag;eredmeny;hivasok_szama;hibakodok`. Egy futás ágakként egy-egy sort ír.
- Az idempotencia-őr (`trendfigyelo/futas_orzo.py`, napi.yml:39–53) a `legfrissebb.json`
  `frissitve` DÁTUMÁT veti a mai UTC-nappal; ütemezett futásnál ha ma már van adat → `skip`.

### 2.5 Frontend — 3 felület (mind `docs/js/app.js`, tárolók `docs/index.html`)
1. **„Ma felkapott keresések"** (`#trend-blokk`, index.html:68; nap-választó `#datum-valaszto`,
   64): `trend_blokk_render()` (1765–1827). Adat: legfrissebb nap → `legfrissebb.top_trendek`,
   régebbi → `napok/<nap>.json.trendek` (`trend_adat_nap`, 1334–1341). Oszlopdiagram
   `trend_chart_epit` (1600–1620) a `kategoria_eloszlas` (1355–1365) alapján; chip-sor
   `trend_osszefoglalo_epit` (1735–1762); kártyák `trend_kartya_epit` (1644–1700, mezők:
   `kifejezes`, `volumen`, `temak`, `idosor`-sparkline). Nap-választó `datum_valaszto_render`
   (516–540), események `trend_esemeny_kot` (1830–1848).
2. **„Napi keresési kategóriák idősora"** (`#idosor-blokk`, index.html:55; legenda
   `#idosor-legend`, 51): `idosor_blokk_render()` (1505–1542). Adat: **`kategoriak.json`**
   (nap-független aggregátum). Alakító `kategoria_idosor` (1372–1393); vonaldiagram
   `trend_idosor_chart_epit` (1448–1482); bal legenda `idosor_legend_epit` (1486–1501);
   kiemelés-váltó `idosor_aktiv_valt` (1441–1444).
3. **„Heti felkapott keresések"** (`#heti-blokk`, index.html:81; hét-választó `#heti-valaszto`,
   77): `heti_blokk_render()` (1940–1954) → `heti_tabla_render(hetfo_iso)` (1904–1938).
   Minden nap egy `<tr class="heti-nap-sor" data-nap>` két cellával: `td.heti-nap` =
   „Hétfő · 08-31", `td.heti-szavak` = `napi.trendek.map(kifejezes).join(", ")` (1932–1934).
   CSS: app.css:49–53.

## 3. Időzítés (szerver-oldali, Budapest-idő)

- **Reggeli** — 9:00 Budapest, `--mode reggel`, csak felkapott.
- **Esti** — 21:00 Budapest, `--mode este` (alap), teljes (felkapott + kulcsszó).
- A Hetzner-cron **helyi Budapest-időben** ütemez: `0 9 * * *` (reggeli) + `0 21 * * *` (esti).
  Ez **automatikusan kezeli a nyári/téli időt** (a szerver TZ = Europe/Budapest) ÉS megkerüli
  a 2026-08-31-i rutinban talált `CRON_TZ=UTC`-anomáliát (a cron eleve helyi időben fut).
  A `scripts/trigger_workflow.sh` bővül egy workflow-fájl paraméterrel (már ma is workflow-nevet vesz).
- **Két workflow:** ÚJ `reggeli.yml` (`--mode reggel`) + a meglévő `napi.yml` (esti teljes,
  `--mode este`). A szerver mindkettőt `workflow_dispatch`-el indítja a saját időpontjában.
- **Az esti teljes futás ezzel ~19:10 UTC-ről 21:00 Budapestre csúszik** (JÓVÁHAGYVA).
- **AI-elemzés** (`elemzes.yml`) csak az **estihez** marad láncolva; a reggeli NEM indít elemzést.
- **GitHub backup-cronok MEGMARADNAK** (biztonsági háló), de az őrök szegmens-tudatosak (§7),
  hogy a reggeli az estit ne blokkolja és fordítva. A backup-cronok időben a szerver-trigger
  MÖGÉ tolva (a szerver ér elsőnek, a backup dedupol).

## 4. Backend gyűjtő-mechanizmus (B1 — mód-kapcsoló a meglévő úton)

- A `top_keresesek.py` kap **argparse**-t: `--mode {reggel,este}`, alap `este` (a mostani
  teljes viselkedés → **visszafelé kompatibilis**, a `masodlagos_only.yml` és minden más
  változatlan). A mód átadódik `main()` → `futtat()`-nak.
- **Esti mód (`este`):** a `futtat()` a MOSTANI teljes viselkedést futtatja, egy különbséggel:
  a napfájl-írás az `este` SZEGMENSBE megy (§5), és a `legfrissebb.json` a mostani módon teljesen
  frissül.
- **Reggeli mód (`reggel`):** a `futtat()`
  - **futtatja:** `felkapott_api`, `felkapott_rss`, `idosor`, `idosor_rekesz`, `kategoriak`
    (származtatott újraépítés), `folytonossag`, `parositas` (nulla-hívásos diagnosztikák);
  - **kihagyja:** `kulcsszo`, `kulcsszo_masodlagos`, `tortenet_frissit_napok`,
    `ir_gordulo`/`frissit_lanc`, `regresszio`, `regresszio_masodlagos`;
  - a napfájlt a `reggel` SZEGMENSBE írja (§5);
  - a `legfrissebb.json`-t **kulcsszó-megőrzéssel** frissíti (§6): a `top_trendek`/`trend_idosorok`
    a reggeli felkapottra cserélődik, de a `kulcsszavak`/`kulcsszo_osszesites` a fájlban lévő
    (utolsó esti) értékét MEGTARTJA.
- A mechanizmus egy **kihagy-halmaz** a `futtat()`-ban (mód szerint), NEM külön kódút — egy
  helyen marad a felkapott-írás intricate logikája (legfrissebb-merge, napok-szegmens,
  kategoriak-újraépítés, napló).

## 5. Adatmodell — szegmentált napfájl

`docs/data/napok/<YYYY-MM-DD>.json` új alak:
```json
{ "nap": "2026-08-31",
  "reggel": { "trendek": [ ... ], "frissitve": "2026-08-31T07:00:12+00:00" },
  "este":   { "trendek": [ ... ], "frissitve": "2026-08-31T19:00:20+00:00" } }
```
- **`napi_ir` szegmens-tudatos:** beolvassa a napfájlt, ha van; a `mode` szerinti szegmenst
  (`reggel`/`este`) frissíti, a MÁSIKAT érintetlenül hagyja; atomi visszaír. Az `index.json`
  upsert változatlan.
- **Visszafelé kompatibilitás (KRITIKUS):** a régi fájlok `{nap, trendek}` alakúak.
  - Az olvasók (frontend §8, `kategoriak.py` §5.1) egy **normalizáló segéddel** kezelik:
    ha van `reggel`/`este` → azt használják; ha csak `trendek` (régi) → azt **`este`-ként**
    (a nap beállt képe) értelmezik, reggeli nincs.
  - **A régi fájlokat NEM írjuk át** (nincs migráció; nincs kockázatos tömeges rewrite).
- **Az `este` mindig legyen jelen új napokon** (az esti a teljes futás). Reggeli-only nap
  (ma 21:00 előtt) → csak `reggel`. Ha egy este kimarad → a nap `reggel`-only marad (őszinte).

### 5.1 kategoriak.json — szegmensenkénti kategória-számok
A `#2` felület Reggel/Este váltójához a `kategoriak.py` mindkét szegmens kategória-számait
viszi naponta. Új alak per nap:
```json
{ "nap": "2026-08-31",
  "reggel": { "merve": true, "lista_hossz": N, "lista_kategoriaval": N, "kategoria_nelkul": M, "kategoriak": {"Sports": 6, ...} },
  "este":   { "merve": true, "lista_hossz": ..., "kategoriak": {...} } }
```
- Ugyanaz a normalizálás: régi napfájl → `este` szegmensként számolva, `reggel` hiányzik
  (`merve:false`/nincs). A `kategoriak_ir` a normalizált szegmensekből számol.
- A frontend `kategoria_idosor` (1372–1393) egy szegmens-paramétert kap (alap `este`), és a
  megfelelő szegmens `kategoriak`-jából építi a vonalakat; hiányzó szegmens → `null` az adott napon.

## 6. legfrissebb.json — kulcsszó-megőrzés a reggeli módban

- `legfrissebb_ir` (json_export.py:81–94) reggeli módban: a **felkapott-részt** (`top_trendek`,
  `trend_idosorok`, `frissitve`, `geo`) a reggeli adatra írja, de a **`kulcsszavak` és
  `kulcsszo_osszesites`** kulcsokat a **meglévő fájlból olvassa vissza és megtartja** (ha nincs
  meglévő fájl vagy nincs benne kulcsszó → üres/hiányzó, a mostani üres-viselkedés szerint).
- Az esti mód változatlanul teljes `legfrissebb`-et ír (felkapott + friss kulcsszó).
- A meglévő üres-őr (futtato.py:376–396: csak akkor skip, ha top_trendek/idosorok/kulcsszavak
  MIND üres) reggeli módban a kulcsszó-megőrzés miatt nem üríti a kulcsszó-diagramot.

## 7. Őrök, backup, idempotencia (szegmens-tudatos)

- **Két őr-jel** a `futas_orzo.py`-ban:
  - **reggeli őr:** a `napok/<ma-budapest>.json` `reggel.frissitve` dátuma == mai Budapest-nap?
    → ha igen, a reggeli backup-cron `skip`. (Hiányzó fájl/mező → gyűjts; biztonságos default.)
  - **esti őr:** a `napok/<ma-budapest>.json` `este.frissitve` dátuma == mai Budapest-nap?
    → ha igen, az esti backup-cron `skip`. (A jelenlegi `legfrissebb.frissitve`-alapú UTC-őr
    helyett Budapest-nap + szegmens — így nem keveredik a reggelivel, és a nap-kulcs egységes.)
- A `reggeli.yml` a reggeli őrt hívja, a `napi.yml` az estit → a két futás **nem blokkolja
  egymást** (különböző jel), de a saját típusán belül nincs dupla.
- `workflow_dispatch` (szerver-trigger) MINDIG gyűjt (mint ma); a `schedule` (GitHub backup)
  az őrrel dedupol. A backup-cronok időzítése a szerver mögé tolva.
- **Napi-nap-átfordulás:** a Budapest-nap a kulcs (nem UTC), ezért a Budapest-helyi
  szerver-cron 9:00/21:00 stabilan a helyes naptári napra bélyegez; a §2.4-beli UTC-átfordulós
  lyuk kockázata csökken. (A backup-cronok UTC-ütemezésűek maradnak, de csak hálóként.)

## 8. Frontend (a jóváhagyott megjelenítés)

- **#1 Napi „Ma felkapott" — egymás alatt két blokk.** A `trend_blokk_render` a kiválasztott
  nap fájljából mindkét szegmenst kirajzolja: egy „Reggeli 9:00" blokk + egy „Esti 21:00"
  blokk, MINDEGYIK a meglévő oszlopdiagram + chip-sor + kártyarács rendert újrahasznosítva
  (a render-belső paraméterezve szegmensre; a DOM-azonosítók/`data-` attribútumok szegmens-
  prefixet kapnak az ütközés elkerülésére és az e2e-horgokhoz). Szabályok:
  - szegmentált nap → két blokk (ha az egyik szegmens hiányzik, csak a meglévő blokk);
  - régi (nem szegmentált) nap → EGYETLEN blokk (mint most), „Esti" felirat nélkül vagy
    semleges címmel;
  - a nap-választó (`#datum-valaszto`) és a napi blokk „ma"-forrása a `napok/<ma>.json`-ra
    vált (mindkét szegmens elérhető), a `legfrissebb.json` marad a kulcsszó-diagram forrása.
- **#2 Kategória-idősor — Reggel/Este váltó az egészre.** A `#idosor-blokk` fölé egy
  szegmens-váltó (Reggel/Este) kerül; `kategoria_idosor(kj, szegmens)` a kiválasztott szegmens
  `kategoriak`-jából építi a vonalakat, alap **Este**. A kiemelés-logika (`idosor_aktiv`)
  változatlan; a váltó a diagramot + legendát újraszínezi/újraépíti. Hiányzó szegmens az adott
  napon → `null` pont.
- **#3 Heti — elválasztó, reggel/este külön.** A `heti_tabla_render` szó-cellája (1932–1934)
  a napfájl mindkét szegmenséből épít: „Reggel: <szavak>" új sor/elválasztó „Este: <szavak>".
  Régi nap → egyetlen (esti) lista, mint most. A `td.heti-szavak` DOM bővül; CSS (app.css:49–53)
  kap egy elválasztó-stílust.

## 9. Tesztelés és kapuk (SDD, [[working-style-gates]])

SOROS suite: `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`.
Valódi TDD RED→GREEN, MUTÁCIÓ=1 fegyelem. Fő tesztterületek:
- **Backend:** `--mode reggel` argparse; a reggeli kihagy-halmaz (kulcsszó-ágak NEM futnak,
  felkapott + idosor IGEN); `napi_ir` szegmens-írás (a másik szegmens érintetlen); régi→új
  visszafelé olvasás; `legfrissebb` kulcsszó-megőrzés reggeli módban; `kategoriak_ir`
  szegmensenkénti számok + régi-nap normalizálás; szegmens-tudatos `futas_orzo` (reggeli és
  esti jel függetlensége).
- **Frontend (Playwright, route-mock JSON):** #1 két blokk szegmentált napon / egy blokk régi
  napon / csak-reggeli nap; #2 Reggel/Este váltó (vonalak a helyes szegmensből, alap Este,
  hiányzó szegmens null); #3 heti elválasztó reggel/este külön + régi nap egyetlen lista.
- **Leltár-invariáns fizikailag mérve** (a végleges számot az implementáció méri, nem a spec).
- Ops (szerver-cron, `reggeli.yml`, backup-eltolás, token) → **memóriába**, nem a leltárba
  ([[napi-futas-megbizhatosag]], [[trendfigyelo-onhost-deploy]]).

## 10. Kockázatok és nyitott pontok

- **legfrissebb kulcsszó-megőrzés:** ha valaha üresen indul a fájl, a reggeli futás után a
  kulcsszó-diagram üres marad az első esti futásig — elfogadható, self-heal.
- **Kvóta:** a reggeli +2 felkapott-hívás (api+rss) + az `idosor`/`idosor_rekesz` görbék napi
  plafon alatt; a reggeli a plafon egy részét viszi, az esti a maradékot — az implementáció
  ellenőrzi, hogy a plafon-logika (`PLAFON_OVERRIDE`, kliens hívásszám) a reggeli-esti
  bontásban is helyes (nem duplázódik a napi plafon két futásra kártékonyan).
- **Régi napfájlok** változatlanok maradnak; minden olvasó a normalizálón megy át — ezt
  minden fogyasztónál (frontend #1/#3, `kategoriak.py`, `folytonossag`) egységesen kell alkalmazni.
- **A `legfrissebb`-alapú „ma" forrás a #1-ben** a napfájlra vált — ellenőrizni, hogy nincs
  regresszió a mostani „ma" viselkedésben (sparkline-ok, kategória-eloszlás).

## 11. Nem-cél (YAGNI)

- Nincs déli/harmadik gyűjtés; pontosan reggel+este.
- A #2 nem kap külön reggel+este EGYÜTTES vonalakat (a váltó a döntés).
- Nincs történelmi napfájl-migráció (a régi napok esti-ként olvasódnak).
- A YouTube-fül és a kulcsszó-lánc NEM változik.
