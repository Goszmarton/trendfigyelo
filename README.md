# Trendfigyelő

Napi rendszerességgel gyűjti a **magyarországi (geo=HU)** Google Trends adatokat az
elmúlt 24 órából, és CSV + JSON formában menti őket. Minden lekérdezés, adat és
kimenet **kizárólag Magyarországra** vonatkozik.

## Mit gyűjt

- **Felkapott keresések** (trending_now API + RSS-tartalék + kapcsolódó magyar hírek).
- **Trend-idősorok:** a legnagyobb trendek 24 órás keresleti görbéje (sparkline).
- **Saját kulcsszavak:** a `config.yaml`-ban megadott, csoportokba rendezett magyar
  kulcsszavak napi 24 órás idősora, nyers és referenciaszóra normalizált értékkel.

Kimenetek: CSV-k az `adatok/` mappában (`;` elválasztó, `utf-8-sig` — a magyar Excel
dupla kattintásra megnyitja), futásnapló az `adatok/naplo.csv`-ben, és a webes
felülethez JSON-ok a `docs/data/` mappában.

## Telepítés és futtatás (helyi gép)

```bash
pip install -r requirements.txt
python top_keresesek.py
```

Egy futás összes Google-hívása **néhány tucat alatt** marad
(kb. `2 + trend_idosor_max + a kulcsszó-kötegek száma` ≈ 9–23), a hívások közt
véletlenített 3–7 mp késleltetéssel — ez az IP-blokkolás elleni védelem része.

## Kulcsszó hozzáadása

Csak a `config.yaml` `kulcsszavak:` szakaszát kell szerkeszteni — kód nem változik.
Vegyél fel egy szót egy meglévő csoporthoz, vagy hozz létre új csoportot:

```yaml
kulcsszavak:
  megelhetes: [infláció, benzinár, ..., ÚJ_KULCSSZÓ]
  új_csoport: [példa1, példa2]
```

A referenciaszó (`referenciaszo:`), a geo, az időablak és a nyelv szintén itt,
egy helyen állítható.

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

A `.github/workflows/napi.yml` a napi gyűjtést végzi — **kezdetben csak kézi
indítással** (`workflow_dispatch`: `Actions → Napi trendgyűjtés → Run workflow`);
a `schedule:` (ütemezés) egyelőre ki van kommentelve. Ez méri fel, kap-e
429-et a felhő-runner IP-je. Ha a kézi futások tiszták, a `schedule:` sort
(`cron: "7 19 * * *"`, azaz 19:07 UTC ≈ késő este Budapesten) élesítjük.

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
