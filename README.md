# Trendfigyelő

Napi rendszerességgel gyűjti a **magyarországi (geo=HU)** Google Trends adatokat az
elmúlt 24 órából, és CSV + JSON formában menti őket. Minden lekérdezés, adat és
kimenet **kizárólag Magyarországra** vonatkozik.

## Mit gyűjt

- **Felkapott keresések** (trending_now API + RSS-tartalék + kapcsolódó magyar hírek).
- **Trend-idősorok:** a legnagyobb trendek 24 órás keresleti görbéje (sparkline).
- **Saját kulcsszavak:** a `config.yaml`-ban felsorolt magyar kulcsszavak (per-kulcsszó
  `kifejezes`/`domen`/`tipus` rekordok) **szóló** `now 7-d` órás idősora, **nyers** értékkel.
  Minden szó a saját 0–100 tartományát kapja — nincs referenciaszó/normalizálás (lásd lent).

Kimenetek: CSV-k az `adatok/` mappában (`;` elválasztó, `utf-8-sig` — a magyar Excel
dupla kattintásra megnyitja), futásnapló az `adatok/naplo.csv`-ben, és a webes
felülethez JSON-ok a `docs/data/` mappában.

## Telepítés és futtatás (helyi gép)

```bash
pip install -r requirements.txt
python top_keresesek.py
```

Egy futás logikai Google-hívásainak száma `2 + trend_idosor_max + len(kulcsszavak)`
= felkapott_api (1) + felkapott_rss (1) + idosor (`min(15,#trend)`) + kulcsszo (szavanként 1)
≈ **30** (a jelenlegi configgal 2+15+13). A hívások közt véletlenített **6–10 mp**
késleltetés (`szoras_mp`), a trendspy `request_delay` **6.0** (`alap_keses_mp`) — IP-blokkolás
elleni védelem. Egy kliens-szintű **hívás-plafon** (`tervezett × max_probak`) leállítja a
futást, ha egy hiba miatt a hívásszám elszaladna.

## Kulcsszó hozzáadása

Csak a `config.yaml` `kulcsszavak:` szakaszát kell szerkeszteni — kód nem változik.
A lista **per-kulcsszó rekordokból** áll (`kifejezes`/`domen`/`tipus`):

```yaml
kulcsszavak:
  - {kifejezes: "állás",       domen: munkaeropiac, tipus: szintmero}
  - {kifejezes: "ÚJ_KULCSSZÓ", domen: valamely_domen, tipus: szintmero}
```

A `tipus` ∈ {`szintmero`, `esemenyjelzo`, `hibrid`}; a domének **ékezet nélküliek**
(a magyar megjelenítendő címke a frontendé). A geo, az időablak, a nyelv és a
kulcsszó-ablak (`kulcsszo_idokeret`) szintén itt, egy helyen állítható. A korábbi
horgony-mezők (`referenciaszo`, `referencia_min_atlag`) **elavultak, eltávolítva**.

## Kulcsszó-mérés: szóló, nyers, láncolás-előkészítés

A kulcsszavakat **szólóban** kérdezzük le (`interest_over_time([kif], geo="HU",
timeframe="now 7-d")`), kulcsszavanként külön — minden szó a **saját 0–100 tartományát**
kapja. (Korábban egy `időjárás` horgonyra normalizáltunk; elvetve, mert egy eseményvezérelt
horgony a saját ritmusát minden mért szóba beleírja.)

**Kétféle idősor, más célra:** a felkapott trendek `trend_idosorok`-ja **napi, önálló**
`now 1-d` sparkline (8 perces rács) — csak megjelenítés, **nem láncolódik**; a
`kulcsszo_nyers.json` a kulcsszavak **láncoláshoz** eltett **`now 7-d` órás** nyers sorozata.

### `kulcsszo_nyers.json` — gördülő, verziókövetett nyers kimenet

Kulcsszavanként a nyers órás értékeket őrzi a lekérdezés **pontos ablakhatáraival**
(`ablak_kezdet_utc`/`ablak_veg_utc`) és a **részleges-farok jelöléssel** (`reszleges` — a
Trends `isPartial` oszlopából; a legfrissebb, még nem végleges óra `true`). Gördülő retenció
(alap 14 nap) tartja karban. Ez a napok közti **láncolás** (későbbi fázis) bemenete: az
egymást követő napok 7 napos ablakai átfednek, az átfedésből visszaszámolható a napi skálázó
— de csak a **lezárt** (nem részleges) szakaszból.

### Módszertani töréspont — `modszertan_valtas`

A horgonyos → szóló váltás előtti és utáni napok **nem hasonlíthatók össze**. A váltás dátuma
az **adatba** kerül (`modszertan_valtas` kulcs a `tortenet.json` és `legfrissebb.json` tetején,
az első éles produkciós futás napja), hogy a későbbi felület tudja, hol **nem szabad**
összekötni a sorozatot.

### A pontszámok kulcsszavak közt NEM összemérhetők

**Minden kulcsszó a SAJÁT maximumára normalizált (0–100), ezért a kulcsszavak pontszámai
egymással nem összemérhetők; közös horgony nélkül rangsort (pl. „legnépszerűbb kulcsszó")
nem képezünk.** A Trends „Átlagos érdeklődés"-e mindig a lekérdezésen belüli maximumhoz
viszonyít; két különböző szó szóló sorozata más skálán él. A `kulcsszo_osszesites`
`atlag`/`csucs` értékei **szón belül** értelmesek, szavak közt nem.

## B terv — mi van, ha a Google blokkol?

A Google Trends nem hivatalos API-t használ, és az adatközponti IP-ket (amilyenekről
egy felhő-futó dolgozik) szigorúbban szűri. Ha a lekérdezések 429 (rate limit) hibát
kapnak:

1. A szkript magától exponenciálisan visszavár (30 mp → 2 perc → 8 perc), majd az adott
   ágat feladja az napra és naplózza — nem próbálkozik makacsul (az hosszabb blokkot
   válthatna ki).
2. **Futtasd helyi gépről.** Lakossági IP-ről a blokkolás esélye sokkal kisebb. A fenti
   `python top_keresesek.py` parancs módosítás nélkül fut helyben; utána a keletkezett
   `adatok/` és `docs/data/` fájlokat commitolhatod és pusholhatod kézzel.
3. Opcionálisan a `config.yaml` `proxy:` mezőjében megadható egy HTTP(S) proxy.

## Automatikus napi futás (GitHub Actions)

A `.github/workflows/napi.yml` a napi gyűjtést végzi. Az **ütemezés él**: `schedule:`
`cron: "7 19 * * *"` = **19:07 UTC** (≈ késő este Budapesten), plusz kézi indítás
(`workflow_dispatch`: `Actions → Napi trendgyűjtés → Run workflow`). A 19:07 UTC a
**legkorábbi** időpont, nem garancia: a GitHub-oldali ütemezett indítás rendszeresen
késik — a megfigyelt futások 68–92 perccel a cron után indultak.

A futás **csak** a `docs/data/*.json` fájlokat és az `adatok/naplo.csv`-t
commitolja (a web ezekből dolgozik); a per-futás nyers CSV-ket felhőben nem
őrizzük. Teljes blokk (429 minden ágon) → a job pirosan bukik → GitHub e-mail.

## GitHub Pages bekapcsolása

A **Settings → Pages** alatt: *Source* = `Deploy from a branch`, *Branch* =
`main` / `/docs`. Mentés után az oldal a `https://<felhasználó>.github.io/trendfigyelo/`
címen él, a `docs/index.html` placeholderrel (a teljes felület Phase 3).

## Robusztusság röviden

- **Napló-cap:** a `naplo.csv` a `config.yaml` `naplo_max_sor` (alap 2000)
  fölött a fejlécre + a legutóbbi N sorra korlátozódik — nem hízik korlátlanul.
- **429-önjavítás:** a kulcsszó-ág a már lekért `now 7-d` ablakból az utolsó
  `tortenet_visszapotlas_nap` (alap 3) teljes napot upsertli a `tortenet.json`-ba
  (0 extra Google-hívás). Egy kimaradt nap a **következő** futásból visszapótlódik;
  a top-trend napi lista viszont az adott napra hiányos marad.
  A `legfrissebb.json` és a napi CSV mindig csak az utolsó teljes napot tükrözi
  (egynapos); a többnapos visszapótlás kizárólag a `tortenet.json`-t érinti.

## Escalation-függelék — proxy (csak ha minden más kevés)

A `config.yaml` `proxy:` mezője kész (alap `null`). Csak akkor nyúlj hozzá, ha a
szelídebb megoldások mind kevésnek bizonyulnak:

1. Napi egy futás + részleges siker → **elég?** Ha igen, kész.
2. Ha a runner-IP tartósan 429-et kap: **futtass helyi gépről** (lakossági IP) —
   a `python top_keresesek.py` módosítás nélkül fut, a kimenet kézzel commitolható.
3. Csak ha 1–2 sem elég: adj meg egy HTTP(S)-proxyt a `config.yaml`
   `proxy:` mezőjében (`"http://user:pass@host:port"`). A `kliens.py` már átadja
   a trendspy-nak; új kód nem kell.

> **Figyelem:** a `config.yaml` a nyilvános repóban verziózott — valódi
> proxy-hitelesítőt (jelszót) NE commitolj bele; használj környezeti változót
> vagy hitelesítő nélküli proxyt.
