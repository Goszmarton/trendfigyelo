# 6b / RAJZOLÁS — Szelet 3: rács-tudatos üres-ok + alapnézet (a vizuális szemle leletei)

Dátum: 2026-08-16
Előzmény: Szelet 2 (ca3a05d) — a másodlagos fogyasztás/routing. A VIZUÁLIS SZEMLE
két hibát talált, amit auto-teszt nem fogott (ezért van a szemle). A 6b csak a
MEGISMÉTELT szemle után LESZÁLLÍTVA.

## HIBA 1 (blokkoló) — gyökér-ok MÉRVE

A Szelet 2 szabálya: „hosszú intervallum SOHA nem mutat 'összefűzött nap'-ot"
(nincs_lancolas = órás-láncolás, §8.2 szerint a nap/het ágon irreleváns). ÉLESBEN
mégis megjelent a nyaralás 1_ev kártyán. Mérés (kulcsszo_masodlagos_regresszio.json):

  albérlet [nap] 1_ev: ok=nincs_lancolas
  nyaralás [nap] 1_ev: ok=nincs_lancolas

A MÁSODLAGOS regresszió MAGA hordoz `nincs_lancolas`-t. Az egyesitett_reg
üres-ága a `miv.ok`-ot NYERSEN átengedte (`hosszu ? (miv ? miv.ok : ...)`), így a
másodlagos nincs_lancolas → OK_MAGYAR → „Ehhez több összefűzött nap kell". A
`nincs_masodlagos`-t csak akkor adtam, ha NINCS másodlagos entry — de itt VAN
(a 90 napos napi sorozat nem fedi le az 1 évet). A tévedés: azt hittem, a
másodlagos sosem ad nincs_lancolas-t. Ad.

Szemantika: a nap/het `nincs_lancolas` NEM órás-láncolás — a napi/heti SOROZAT
rövidebb az ablaknál (nyaralás: 90 nap < 365). Ez SOHA nem tölt fel automatikusan
today 3-m-en; csak egy mélyebb (today 12-m) lekérdezés változtatná. A kód ezt nem
tudja eldönteni → SEMLEGES TÉNYKÖZLÉS, nem ígéret.

Javítás: az üres hosszú-intervallum ágon a `miv.ok`-ot rács-tudatosan fordítom:
- `miv.ok === "nincs_lancolas"` → `rovid_masodlagos`
  = „A napi/heti sorozat rövidebb ennél az ablaknál" (puszta tény, se „még", se ígéret)
- garancia: hosszú intervallum a másodlagos ágon SOHA nem ad nincs_lancolas-t.

## HIBA 2 (belefér) — het keves_pont

akciós újság [het] 2_het/1_ho: ok=keves_pont. Heti rácson egy rövid ablak
strukturálisan kevés pont (2 heti pont / 2 hét), NEM adathiány — de a „Túl kevés
mért pont" adathiányt sugall. Javítás rács-tudatosan:
- `miv.ok === "keves_pont" && m.racs === "het"` → `rovid_het_ablak`
  = „A heti rácson ez az ablak túl rövid"
- nap `keves_pont` hosszú intervallumon nem fordul elő (a nap-szavak 2_het/1_ho/3_ho
  érvényesek) → csak a het-ágat kondicionálom (mérve, nem tippelve).

## ALAPNEZET — default = 1 hét (a spec-szándék ELLEN, indokolva)

A `intervallum_vezerlo_render` a leghosszabb ÉRVÉNYES intervallumot választja
alapból (spec 7.2 „magától tolódik kifelé"). Szelet 2 után ez 1_ev (akciós újság
érvényes rajta) → betöltéskor 13-ból 1 kártya rajzol, a többi üres. Rossz élmény.

Az érv a spec-szándék ELLEN (nem csak „commitolt"): a „leghosszabb érvényes"
szabály arra épült, hogy az érvényesség MONOTON nő ÉS a leghosszabb egyben
minden-szó-érvényes (1_het, csak órás világban). A másodlagossal ez MEGTÖRT: a
hosszú intervallumokon az érvényesség RITKA (1_ev: 1/13). Így a „leghosszabb
érvényes globálisan" már nem korrelál a „legtöbb szónak jó nézettel".

Javítás: a default a legtöbb kártyát rajzoló intervallum = **1_het (13/13)**. Ha
1_het érvényes → azt választjuk; különben a leghosszabb érvényes (visszaesés). A
hosszabb nézetek kattintásra maradnak. Ezzel az ALAPNEZET-VEGYES megfigyelés
LEZÁRUL (a vegyes kezdő-nézet megszűnik).

## TDD (Playwright e2e, gomb/aria-alapú — közvetlenül assertálható)

- HIBA 1 RED: nap-szó 1_ev másodlagos nincs_lancolas → a tiltott 1_ev gomb ok-szövege
  „…rövidebb ennél az ablaknál", NEM „összefűzött". Hibatípus: toContainText AssertionError.
- HIBA 2 RED: het-szó 2_het keves_pont → „A heti rácson ez az ablak túl rövid", nem
  „Túl kevés mért pont". Hibatípus: toContainText AssertionError.
- ALAPNEZET RED: 1_het + egy hosszú érvényes → az aria-pressed gomb data-intervallum
  = „1_het", nem a leghosszabb. Hibatípus: toHaveAttribute AssertionError.
- SZÁNDÉKOS-ZÖLD (előre): (1) nincs_masodlagos út (nincs entry) VÁLTOZATLAN
  („napi/heti adatot"); (2) az órás görbe/„óra nem-nulla" változatlan.

## Lezárás

Production diff valószínűleg <50 (üres-ág rács-fordítás + 2 OK_MAGYAR + default 1 sor)
→ subagent-review nem kötelező; ha átlépi, jelzés. EGY commit (Szelet 3) + leltár
UGYANABBAN: 6b → LESZÁLLÍTVA a MEGISMÉTELT vizuális szemle után; ALAPNEZET-VEGYES
LEZÁRVA; invariáns újraszámolva. A 6b csak a 2. szemle után LESZÁLLÍTVA.
