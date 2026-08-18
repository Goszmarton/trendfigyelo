# Terv — Heti felkapott keresések blokk (jóváhagyva 2026-08-18)

Új blokk a trend-kártyák ALÁ (a „Nyers adat" footer fölé), a meglévő `[sticky keskeny vezérlő-sáv] + [széles
tartalom]` mintában (mint a `datum-valaszto` + `trend-blokk` szekció). Bal: hét-választó legördülő; jobb: a
kiválasztott hét napi táblázata (nap · dátum → aznapi felkapott szavak). Frontend/DOM, **nincs canvas** → a logika
DOM-assertálható; a végén EGY SZEMLE a látványra (sticky, arányok), push előtt.

## MÉRT alapok (2026-08-18)
- **Elrendezés-minta:** `#dashboard > .szekcio > (aside.vezerlo-sav[sticky] + section#…)`. Az új blokk egy ÚJ
  `.szekcio` a trend-szekció UTÁN: `aside.vezerlo-sav` (hét-választó) + `section#heti-blokk` (táblázat).
- **Adat:** `napok/index.json` (elérhető napok, most 2026-07-23 … 2026-08-17, 25 nap) + `napok/<nap>.json`
  (`trendek[].kifejezes`, tárolt volumen-sorrend, minden szó = egy kártya aznap). **BACKEND 0 kód** — a napi futás
  írja + committolja (mint az idősornál).
- **Mai nap:** 2026-08-18 MÉG NINCS az indexben (a futás archiválja) → a legfrissebb hét csak a legutolsó ELÉRHETŐ
  napig mutat (user elfogadta: „a mai nap a futás után jelenik meg").
- **ISO-hét KORREKCIÓ (a jóváhagyott példa hibás volt):** 2026-08-11 = **ISO 33. hét** (hétfő-index 2), 2026-08-17
  = **ISO 34. hét** (hétfő), 2026-08-18 = ISO 34. A hét = **hétfő–vasárnap**; a helyes határok pl. `33. hét
  (aug. 10–16)`, `34. hét (aug. 17–23)`. A címke-formátum `{ISO hétszám}. hét ({kezdet}–{vég})`, magyar hónap-
  rövidítéssel (jan./feb./márc./ápr./máj./jún./júl./aug./szept./okt./nov./dec.); két hónapot átívelő hét →
  „aug. 31 – szept. 6".

## Döntések (a user rögzítette)
1. Hét = hétfő–vasárnap naptári (ISO) hét; címke `34. hét (aug. 17–23)`.
2. Napi szavak: MINDEN aznapi felkapott szó (amiről kártya van), tárolt (volumen-csökkenő) sorrendben.
3. Jobb doboz: **táblázat**, soronként egy nap (nap neve · dátum → vesszős szólista). Csak a szó (nincs volumen/kategória).
4. Elrendezés: **bal keskeny sticky választó + jobb széles táblázat** (a `datum-valaszto` + `trend-blokk` arány).
5. **Független** a `#datum-valaszto`-tól: a hét-választó csak ezt a blokkot vezérli, a fenti chartok napját NEM.
6. Alapból a **legfrissebb hét**; részleges hét = csak a Mon..(legfrissebb elérhető nap) napok.
7. Hiányzó nap a héten (pl. 08-06) → **„nincs adat"** sor (nem marad ki).

## Nap-tartomány szabály (determinisztikus, NINCS böngésző-óra)
A kiválasztott hét megjelenített napjai = a hét hétfő..vasárnap napjai, DE **csak a `max(napok/index)` napig** (a jövőbeli/
nem-archivált napok kimaradnak). A tartományon belül: napok/index-ben van → szavak; nincs → „nincs adat". Ez tükrözi a
„részleges hét = eltelt napok" kérést böngésző-óra nélkül (a legfrissebb ELÉRHETŐ nap a vágás), és tesztelhető.

## Backend: NINCS változás
Az adat (`napok/*.json` + index) megvan, auto-generált, auto-committed. Tiszta frontend blokk.

## Szelet 1 — hét-csoportosító + `<select>` + táblázat (DOM-assertálható, RED→GREEN)
- `index.html`: új `.szekcio` shell a trend-szekció után (`aside.vezerlo-sav > #heti-valaszto`, `section#heti-blokk`).
- Loader: `napok/index.json` már betöltött; a kiválasztott hét napi fájljait (`napok/<nap>.json`) ON-DEMAND tölti
  (a meglévő `json_betolt` mintája), mint a napváltás.
- Tiszta függvények: (a) `hetek_index(napok)` → ISO-hetenkénti csoport [{ho_kezdet, hetszam, cimke, napok:[ISO]}],
  legfrissebb elöl; (b) `heti_cimke(iso_hetfo)` → „34. hét (aug. 17–23)"; (c) a táblázat-sorok a hét napjaira.
- Render: a `<select>` opciói a hetekből (alap = legfrissebb); váltásra a `#heti-blokk` táblázat újraépül. A szavak
  DOM-tükörben is assertálhatók (soronként `data-nap` + a szólista szövege / „nincs adat").

**Szelet 1 RED (AssertionError, valós üzenetekkel):**
- `heti: a hét-választó ISO-heteket sorol, legfrissebb elöl, alap = legfrissebb` → RED: rossz opciók/alap.
- `heti: a 2026-08-17 a "34. hét (aug. 17–23)" alá esik (hétfő–vasárnap, ISO)` → RED: rossz határ/címke (a hibás
  „aug 11–17" ellen élesítve).
- `heti: a kiválasztott hét napi sorai hétfő..a legfrissebb elérhető napig; a mai/jövő nap NEM jelenik meg` → RED.
- `heti: egy nap sora az aznapi ÖSSZES felkapott szót tartalmazza, tárolt sorrendben` → RED.
- `heti: hiányzó nap a héten → "nincs adat" sor (nem marad ki)` → RED.
- `heti: a hét-váltás FÜGGETLEN — a #datum-valaszto értéke és a trend-blokk napja VÁLTOZATLAN` → RED.

**Szándékos-zöld (SZANDEKOS-ZOLD-VAK, előre jelölve):**
- `a meglévő dátumválasztó/trend-blokk VÁLTOZATLAN` — szándékos-zöld; fedése a Szelet 1 végén diszkriminátorral
  MÉRVE (a heti-render elrontása ne boríthassa; 0 fedés → élesített asszertre cserélem).

## Szelet 2 — elrendezés/stílus (CSS) + SZEMLE
A `.szekcio`/`.vezerlo-sav` sticky+arány CSS-t ÖRÖKLI (0 új elrendezés-kód); csak a táblázat stílusa (nap-oszlop,
szólista, „nincs adat" halvány). **NINCS canvas** → a logika DOM-teszttel fedve; a végén EGY SZEMLE a látványra:
sticky bal + széles jobb arány, táblázat olvashatóság, a blokk a kártyák alatt / a footer felett.

## Zárás
grep MUTÁCIÓ==1 → `git status docs/data` tiszta → commit (kód+teszt+leltár §11a) → push KÜLÖN körben, rev-list 0 0.
Új tétel csak adatvesztésre/néma hibára; egyéb lelet → PARKOLT sor, egy mondat.
