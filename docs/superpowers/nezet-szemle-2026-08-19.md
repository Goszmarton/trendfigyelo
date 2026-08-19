# NÉZET-SZEMLE — 2026-08-19

Állapot a szemle idején: `7dedcf5` (TELJES-NEZET lezárva).
Mind a 6 intervallum-nézet × 13 szó vizuálisan átnézve, lokális szerverről.

**Ezek MEGFIGYELÉSEK, nem tételek.** A §2 szűrő (adatvesztés / néma
meghibásodás) alkalmazva: egyik sem okoz adatvesztést. A leltárban egyetlen
parkolt sor hivatkozik erre a dokumentumra: `NEZET-SZEMLE-0819`.
A 3b (frontend per-interval rács) körnél elő kell venni.

---

## A) TELJES IDŐSZAK nézet (landing, alapértelmezett)

| szó | rács | ablak | jobb szél |
|---|---|---|---|
| állás | heti | 2025-08-17 → 2026-08-09 | 08-09 |
| kormányablak | heti | 2025-08-17 → 2026-08-09 | 08-09 |
| kórház | heti | 2025-08-17 → 2026-08-09 | 08-09 |
| akciós újság | heti | 2025-08-10 → 2026-08-02 | 08-02 |
| tüntetés | heti | 2025-08-10 → 2026-08-02 | 08-02 |
| albérlet | napi | 2026-05-15 → 08-12 | 08-12 |
| eladó lakás | napi | 2026-05-20 → 08-17 | 08-17 |
| nyaralás | napi | 2026-05-17 → 08-14 | 08-14 |
| betegség | napi | 2026-05-19 → 08-16 | 08-16 |
| benzin / nyugdíj / hitel / napelem | órás | 2026-08-11 → 08-18 | 08-18 |

**A1 — A magasság nem jelent semmit, és ez nem látszik.**
Minden kártya külön 0–100-ra húzva a SAJÁT ablakán belül. A `tüntetés`
100-asa valódi esemény; a `kormányablak` 100-asa csak „az év legmagasabb hete
egy egyenletes évben". Vizuálisan azonos.
*Javaslat (nem döntés):* a `tüntetés` medián-szintvonala MINDEN kártyára.
Plató-szónál a görbe rátapad, eseménynél messze fölé ugrik. Nem igényel új
gyűjtést, nem igényel rács-döntést. Lásd I1.

**A2 — Trendvonal ott is, ahol nincs trend.**
Hat kártyán R² = 0,00–0,01. `kormányablak`: a piros vonal tökéletesen
vízszintes, +0,00 pont/nap — a szöveg azt mondja „nincs", a kép azt mondja
„van illesztésem". A piros a görbe után a legerősebb vizuális elem.
**FIGYELEM:** egy R²-küszöb bevezetése RÁCS-VAK KONSTANS veszély — ez nem
„állítsunk be 0,05-öt", hanem külön, mért döntés.

**A3 — Az időtáv 52-szeresen szór azonos chart-szélességen.**
Legrosszabb pár: Fogyasztás szekció — `akciós újság` (1 év, heti) és `benzin`
(1 hét, órás) EGYMÁS MELLETT, azonos szélességen. Az időtáv ma csak a
lábjegyzetben van; a cím alatt kellene lennie, ahol a „Felbontás:" áll.

**A4 — A gomb felirata két ponton sem igaz.**
„a gyűjtés kezdetétől máig":
- a bal szél NEM a gyűjtés kezdete (a heti adat visszamenőleg jött a
  Google-tól 2025 augusztusából — akkor még nem gyűjtöttünk)
- a jobb szél NEM „máig": 08-02 és 08-18 között szór, **16 nap**.
  `kórház` 08-09-cel, `nyugdíj` 08-18-cal végződik, egymás alatt.
A jobb szél szórása a másodlagos rotáció közvetlen látképe — hasznos
információ, csak nincs kimondva.

**A5 — Az `esemenyjelzo` besorolás ugyanabban a betegségben szenved, mint a rács.**
A `betegség` szerkezetileg UGYANAZ, mint a `tüntetés`: alacsony alapvonal
(~25) + két 100-ig érő kiugrás. Mégis trendvonalat kap R²=0,00-val, a
`tüntetés` meg szint-vonalat. A különbség nem mérésből jött, hanem abból, hogy
annak idején a `tüntetés`-re figyeltünk fel. Ugyanaz a gyökérok (EMLÉKEN áll,
nem mérésen), csak a másik flagen.

**A6 — `kórház`: három különböző dátum ugyanarra a szóra. LELET.**
tengely bal széle 2025-08-17 · lábfelirat 2025-08-16 · nyers első pont
2025-08-10, 53 lezárt ponttal (a többi het-szónál 52).
A többi kártyán a tengely és a felirat EGYEZIK.

---

## B) 1 HÉT nézet

Rács: mind a 12 rajzolt szó órás, azonos ablak (08-11 → 08-18), 168 pont.
**Rácsot egyetlen szónál sem cserélnék** — egy hetes ablakon az órás az
egyetlen felbontás, ami pontot ad. Ez az egyetlen nézet, ahol a szavak
FORMÁJA valóban összehasonlítható.

Megfigyelt formák: `kormányablak` tiszta hivatali napi ciklus (hétvégén padló,
a legolvashatóbb kártya az oldalon); `akciós újság` / `benzin` / `nyaralás`
napi ritmus éjszakai lezuhanással; `nyugdíj` napi ciklus + hét közbeni
lecsengés; `állás` / `betegség` / `hitel` kevésbé ciklikus, tüskés.

**B1 — A nézet és a metrika mást kérdez.**
A kártya alatti szöveg mindegyiknél TRENDET mond. Egy 24 órás periodicitású
jelre húzott egyenes iránya nagyrészt attól függ, hol vág az ablak a ciklusba.
- `kormányablak`: a görbe naponta 0→100 jár, a piros vízszintes ~33-on,
  „stagnáló, R²=0,00"
- `nyugdíj`: -4,18 pont/nap (R²=0,22) = hét eleje→hét vége lejtő. Lehet valós,
  lehet hétvége-hatás — **egyetlen hétből nem eldönthető, n=1**

Amit ez a nézet valóban tud: mikor keresnek rá NAPON BELÜL, hétköznap vs
hétvége, mennyire ciklikus. Ezekre ma egy szám sincs a kártyán.

**B2 — A nulla ezen a nézeten mást jelent.**
Padlót verő szavak: `nyaralás` 123/168, `napelem` 126, `betegség` 134,
`eladó lakás` 136, `kormányablak` 136 nem-nulla óra.
A 0 itt NEM „senki nem kereste", hanem „a Google kerekítési küszöbe alá esett".
A grafikonon viszont ugyanaz a padló, mint egy valódi nulla. `albérlet` /
`eladó lakás` kártyája emiatt vonalkód-hatású: a függőleges zuhanások uralják
a képet, a napi mintázat elveszik mögöttük.
NEM rács-csere kérdése (napi rácson nem-nulla lenne, de akkor nincs napon
belüli mintázat) — jelölés kérdése.

**B3 — A `tüntetés` kártyája üresen áll. LELET, javítható.**
Felirat: „Heti felbontású szó — ez az ablak túl rövid a heti rácshoz."
DE: a `tüntetés`-nek VAN órás nyers adata (`now 7-d`, mind a 13 szóra). A
másik 12 szó ugyanezt az órás adatot rajzolja, config-rácstól FÜGGETLENÜL.
Nem hiányzik az adat — a `tüntetés` a heti ágra van irányítva. Ugyanaz az
osztály, mint az `ERVENYES-ROUTING`: egy flag (`esemenyjelzo`) vezérli a
rajzolást.

**B4 — A dátumtengely napokat duplázva ír ki. LELET.**
Címkék: 08.11, 08.12, 08.13, **08.13**, 08.14, 08.15, 08.16, **08.16**, 08.17,
08.18. Két tick esik ugyanarra a napra, ÓRA NÉLKÜL — így nem látszik, hol a
napváltás, és a napi ciklus leolvasása pont ezen múlna. Mind a 12 kártyán.

---

## E) 2 HÉT nézet

**13-ból 9 kártya ÜRES. A nézet 69%-a szöveg.**
- rajzol (napi, 14 pont): albérlet, eladó lakás, nyaralás, betegség
- üres „túl rövid a heti rácshoz": állás, kormányablak, akciós újság, kórház, tüntetés
- üres „az órás sorozat láncolása kell" (GATE, VÁRT): benzin, nyugdíj
- üres „még gyűlik a napi/heti adat" (never-collected): napelem, hitel

**E1 — Az üresség EGY RÉSZE nem adathiány, hanem routing.**
Mind a 13 szónak van `now 7-d` órás nyers adata. Az 1 hét nézet ezt rajzolja
mind a 12 szónál. A 2 hét nézeten senki nem rajzolja. Az öt heti szó felirata
igaz a HETI sorozatra, de elrejti, hogy létezik használható órás adat. A
`benzin` felirata legalább őszinte („láncolás kell"). → ugyanaz az osztály,
mint B3.

**E2 — A fejléc EGY dátumot állít, a kártyák jobb széle 5 napot szór. LELET.**
Fejléc: „az adat vége: 2026. 08. 12."
Valóság: albérlet 08-12 · nyaralás 08-14 · betegség 08-16 · eladó lakás 08-17
Ugyanaz a mechanizmus, amit a `(b)` leletnél javítottnak jelentettünk (a
fejléc az ELSŐ kártya `adat_veg`-ét mondja). A javítás a TELJES nézetre ment
be; itt FENNÁLL, és élesebb, mert a fejléc konkrét dátumot ígér.

**E3 — Rövid ablakon a trend-metrika a legmegbízhatóbbnak LÁTSZIK, miközben a
legkevésbé az.**
`nyaralás` R²=0,58 (a lap legmagasabbja) 14 pontból — ugyanez a szó a teljes
nézeten R²=0,01, „stagnáló". Nyár végi szezonális lecsengés, nem trend.
Ugyanez: `eladó lakás` 0,11 és `betegség` 0,18.

**E4 — A 2 hét ablak a két meglévő rács KÖZÉ esik.**
Órás: 7 napig ér (láncolás nélkül). Napi másodlagos: 3 hónapos ablakból. Heti:
egyéves. KÉT HÉTRE EGYIK SEM KÉSZÜLT — a napi véletlenül jó rá.

**E5 — MEGFONTOLANDÓ: a 2 hét nézet ma többet árt, mint használ.**
Kilenc üres kártya közé szúrva négy görbe, amiből a legmeggyőzőbb (`nyaralás`)
a legfélrevezetőbb.

---

## F) 1 HÓ nézet

**MEGEGYEZIK a 2 hét nézettel** — ugyanaz a 4 szó rajzol, ugyanaz a 9 üres,
szó szerint ugyanazokkal a feliratokkal. Csak a pontszám 14 → 30.
A fejléc itt is egy dátumot állít → E2 megismétlődik.

**F1 — Két gomb, azonos tartalom; a heti szavaknál VÉGLEGESEN.**
A `LANC-ORAS` Szelet 2 után benzin/nyugdíj feltöltődik, a rotáció
hitel/napelem-et behozza. DE az öt heti szó MINDKÉT nézeten örökre üres marad
a heti rácson — a felirat ezt őszintén ki is mondja: „Ez nem fog feltöltődni".

**F2 — AZ IRÁNY NEM A SZÓ TULAJDONSÁGA, HANEM AZ ABLAKÉ. (MÉRT, a lapról)**
`nyaralás`, ugyanaz a napi adat, csak az ablak hossza változik:

| ablak | pont | irány | R² |
|---|---|---|---|
| 2 hét | 14 | csökkenő -1,09 | 0,58 |
| 1 hó | 30 | csökkenő -0,39 | 0,06 |
| teljes | 90 | stagnáló -0,06 | 0,01 |

A meredekség 18-szorosára nő, ahogy rövidül az ablak.
Ugyanez `eladó lakás`: 2 hét 0,11 → 1 hó 0,17 → teljes 0,00.

**KÖVETKEZMÉNY:** ha a „melyik timeframe ad jelet" mérőszáma az R² /
meredekség, akkor a RÖVIDEBB ABLAK SZINTE MINDIG NYER — nem mert több jel van
benne, hanem mert kevesebb pontra könnyebb egyenest húzni. A PLATÓ-mérték
(medián ±10 sávba eső pontok aránya) és a kiugrás/medián arány ablak-hosszra
sokkal kevésbé érzékeny.

---

## G) MIÉRT ÜRES? — a származtatás kérdése

**G1 — SZŰKÍTÉS (hosszabb sorozatból rövidebb ablak): TRIVIÁLISAN MŰKÖDIK,**
és a nap-szavaknál MA IS MŰKÖDIK. A `today 3-m` egy 92 pontos NAPI sorozat; az
1 hó nézet ennek az utolsó 30 pontja — ugyanaz a lekérés, ugyanaz a skála.
A het-szavaknál a szűkítés elve NEM rossz, csak a felbontás durva: a `today
12-m` HETI pontokat ad → 1 hónapra 4 pont.

**G2 — DE: a het-szavaknak IS van napi alatti adata.**
A `now 7-d` órás sorozat MIND A 13 SZÓRA megvan. 2 hétre a 7 napos ablak nem
elég — hacsak nem láncolunk.

**G3 — LÁNCOLÁS: MŰKÖDIK, de nem ingyen.**
- két FELBONTÁS nem fűzhető össze; 3 hónapos nézetre az órás lánc soha nem ér el
- minden 7 napos ablak a SAJÁT 0–100 skáláján jön → van átfedés-alapú skálázás
  (`lanc.py:21`, medián-arány a referenciára), de átfedés nélkül a lánc
  SZAKASZRA BOMLIK (lásd `LANC-SZAKASZ-TORES`)

**G4 — KÖVETKEZTETÉS: TÖBB ADATUNK VAN, MINT AMENNYIT MEGJELENÍTÜNK.**
Az üresség egy része nem adathiány, hanem routing (E1, B3).

---

## H) 3 HÓ nézet

Rajzol: 5 heti szó (12 pont) + 4 napi szó (90 pont). Üres: benzin, nyugdíj
(GATE), hitel, napelem (never-collected).

**H1 — AZ F2 IGAZOLÁSA, ÉLESEN: az irány ELŐJELE fordul az ablakhossztól.**
Ugyanabból a `today 12-m` sorozatból szűkítve:

| szó | ablak | pont | irány | R² |
|---|---|---|---|---|
| kormányablak | teljes | 52 | stagnáló +0,00 | 0,00 |
| kormányablak | 3 hó | 12 | **NÖVEKVŐ +0,26** | **0,66** |
| állás | teljes | 52 | CSÖKKENŐ -0,04 | 0,13 |
| állás | 3 hó | 12 | **NÖVEKVŐ +0,09** | **0,52** |

→ A trend-metrika ebben a rendszerben AZ ABLAKOT MÉRI, NEM A SZÓT.

**H2 — A `RACS-PLATO` DIAGNÓZISA PONTATLAN. MÉRT.**
A korábbi megfogalmazás szerint a `kormányablak` plató, „nincs jel, csak zaj",
a `today 12-m` kilapítja. DE ugyanabból az adatból a 3 hó nézet TISZTA,
MONOTON EMELKEDŐ görbét rajzol, R²=0,66.
→ A „nincs jel" AZ ABLAKRÓL szólt, NEM A SZÓRÓL. A `12-m` lekérés jó; egyben
nézve az 52 hetet a szűk ingadozás beleolvad, rövidebb szeleten látszik.
**KÖVETKEZMÉNY: a megoldás NEM átsorolás, hanem MEGJELENÍTÉS — ugyanaz az
adat, rövidebb ablakon. NULLA Google-hívás.**

**H3 — LELET: a „12/12 hét nem-nulla (12/13 lezárt, 1 részleges kihagyva)"
felirat önellentmondó.**
Mind az öt heti szónál. A többi nézeten 52/52, 90/90, 168/168 — itt a mondat
első fele 12/12-t mond, a második 12/13-at, UGYANARRA a halmazra. A viselkedés
valószínűleg helyes; a megfogalmazás nem.

**H4 — LELET: napelem/hitel felirata ezen a nézeten HIBÁS.**
„Ehhez az ablakhoz még gyűlik a napi/heti adat. Magától feltöltődik."
De a `today 3-m` PONT 3 hónapos ablak. Nem gyűlik: soha nem lett lekérve
(never-collected). A felirat türelemre int, miközben a rotáción múlik.

---

## I) 1 ÉV nézet

A 2 hét TÜKÖRKÉPE. Csak az öt HETI szó rajzol (52 pont); 5 rajzol, 8 üres.

**I1 — A `tüntetés` itt van a helyén.**
Az EGYETLEN kártya az egész lapon, ami saját magától olvasható: alacsony
alapvonal, medián-vonal 8-on, három tiszta esemény (szept, dec, máj–júl). Nem
kell hozzá metrika, a forma beszél.
→ Ez méri le, mennyit ér az A1: a `kormányablak` ugyanezen a nézeten 37–100
közt zajong, a piros trendvonal vízszintesen 74-en. Ha az MEDIÁN lenne,
azonnal látszana, hogy a görbe végig rátapad — szemben a `tüntetés`-sel, ahol
messze fölé ugrik. Ugyanaz a vizuális elem, két teljesen más jelentés.

**I2 — A H2 MEGERŐSÍTÉSE, HARMADIK független nézetből.**
A grafikon jobb harmadán szemmel is látszik az emelkedés (júniustól 75 → 88);
az egész éves illesztést a decemberi zuhanás kioltja.
→ A négy „plató-szó" közül legalább kettőnél (állás, kormányablak) VAN JEL AZ
ADATBAN — csak az egyéves illesztés nem látja.

**I3 — LELET: a napi szavak felirata itt HAMIS ÍGÉRET.**
„A napi/heti sorozat még rövidebb ennél az ablaknál. Magától feltöltődik."
NEM IGAZ. A `today 3-m` MINDIG 3 hónapot ad, a lekérdezéstől visszafelé.
**Ez soha nem fog feltöltődni egy évre.** Ugyanaz az osztály, mint H4, de
súlyosabb: VÉGLEGES állapotra ígér türelmet.

---

## J) A HAT NÉZET EGYÜTT — a lefedettség képe

|  | 1 hét | 2 hét | 1 hó | 3 hó | 1 év | teljes |
|---|---|---|---|---|---|---|
| ora (2) | ✓ | — | — | — | — | ✓ (7 nap) |
| nap (6) | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| het (5) | — | — | — | ✓ | ✓ | ✓ |

- Az EGYETLEN nézet, ahol mind a 13 megjelenik: **TELJES** — de ott mindenki
  MÁS ablakon (A3, A4).
- A második legjobb: **3 HÓ** — 9 szó, UGYANAZON az ablakon.
- **2 hét** és **1 hó**: azonos tartalom, 4 szó (E5, F1).
- **1 hét**: 12 szó, azonos ablakon — a legjobb FORMA-összehasonlítás (B).
- **1 év**: 5 szó.

---

## Ami ebből a szemléből DÖNTÉSSÉ vált (2026-08-19)

A H2/I2/F2 mérés alapján: **nem timeframe-et választunk szavanként, hanem
mindkét hosszú sorozatot gyűjtjük** (`today 3-m` + `today 12-m`), és a
felhasználó választ ablakot gombbal. A config-rács megjelenítési
alapértelmezéssé válik, átsorolás nincs, a tervezett timeframe-sweep
tárgytalan. Leszállítva: `MASODLAGOS-TF` (`bde421d`).
