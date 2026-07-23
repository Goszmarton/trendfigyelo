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

> A GitHub Actions-ütemezés és a GitHub Pages weboldal a következő fázisokban kerül a
> projektbe; ez a README azokat majd kiegészíti (Settings → Pages → `docs/`).
