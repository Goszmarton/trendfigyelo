# Trendfigyelő — Phase 4 spec: per-szó rács-bővítés

Állapot: a gyűjtő-oldal (Task 1–5) **leszállítva és pusholva**; a megjelenítés
(Task 6+) MÉG NINCS. Ez a dokumentum a leszállított gyűjtő-viselkedést rögzíti
(utólagos spec, DOC-COMMIT), plusz kimondja a nyitott megjelenítési adósságot.

Rokon dokumentumok: a mester-spec `docs/superpowers/phase3/phase3-spec.md`
(§1.4 normalizálás, §8.2 láncolás-előfeltételek, §8.3 regresszió). A mérési alap
`.atadas-archiv/meresek/racs_dontes_13_szo_2026-08-13.md` (gitignore-olt, tartós).

---

## 1. Cél és kontextus

A `now 7-d` ÓRÁS rács egy csomó kulcsszóhoz **eleve rossz felbontás**: aminek a
jele napi vagy heti ciklusú, azt az órás ablak vagy padlóra (0-kra) veri, vagy a
nap-órája/hét-napja ciklusa uralja, és a 7 napos ablak túl rövid a lassú
mozgáshoz. A Phase 4 ezért **per-szó rácsot** vezet be: minden kulcsszó ahhoz a
lekérdezési felbontáshoz kötődik, ami a **jeléhez** illik.

A rács MÉRÉSI EREDMÉNY, nem ízlés (lásd §3 mérőeszköz). Ezért a rács **adat**,
config-mező, újramérésre változhat — nem kódba drótozva.

---

## 2. A per-szó rács fogalma

- **`racs` ∈ {ora, nap, het}**, per kulcsszó, a `config.yaml`-ban (KulcsszoTetel
  4. mező, alapértelmezés `"ora"` → visszafelé kompatibilis, viselkedés-változás
  nélkül vezethető be).
- **`RACS_IDOKERET` térkép** (`config.py`): `ora → "now 7-d"` (órás, ~169 pont, 7
  nap), `nap → "today 3-m"` (napi, ~90 pont), `het → "today 12-m"` (heti, ~52
  pont, 1 év).
- **A globális `kulcsszo_idokeret` az ÓRÁS ág sajátja marad** (`"now 7-d"`). A
  másodlagos (nap/het) ág NEM ezt használja, hanem a per-szó `RACS_IDOKERET`-et.
  Az órás fogyasztók (`ir_gordulo`, `_hianyzo_orak`, `regresszio_egy_ablak`,
  `ervenyes_nyers_rekord`) érintetlenek — az órás rács szemantikája nem változik.

**KIMONDANDÓ:** az órás sorozat (`now 7-d`) **pótolhatatlan** — visszamenőleg NEM
kérhető le (a Google csak az aktuális 7 napot adja órás bontásban). A napi/heti
sorozat viszont retroaktívan újralekérdezhető. Ez az aszimmetria indokolja, hogy
az órás ág elöl fut, a másodlagos ág pedig legutolsó és feladható (§6).

---

## 3. A mérőeszköz — ami a besorolást adta

A besorolás enélkül önkényesnek látszana. Három mérőszám dönt, tárolt órás
adatból + webes Trends CSV-kből (nulla új Google-hívás a méréshez):

- **P = padló-hányad** — a pontok hány %-a **pontosan 0**. Magas P = az órás
  ablak a jelet padlóra veri (a valódi mozgás a nap/hét szintjén van).
- **C = ciklus-hányad** — a szórás mekkora részét magyarázza a **naptári
  pozíció**. `C_ora`: az **órás** soron a *nap órája* szerint. `C_nap`: a **napi**
  soron a *hét napja* szerint. FONTOS: `C_nap` CSAK napi soron mérhető — a 7 napos
  órás sor minden hétnap-szintet 1×-tel tartalmaz, így a hétnap-kategória felszívja
  a trendet (szintetikus ellenőrzés igazolta, hogy órás soron `C_nap` érvénytelen).
- **T = trend R²** — a lineáris tag inkrementális R²-e a ciklus figyelembevétele
  UTÁN (`T_ora`: 24 óra-hatás + 1 lineáris tag).

**Kapu:**
- **ÓRÁS**, ha `P ≤ 10%` **ÉS** `C_ora ≤ 0,30` **ÉS** `C_nap (napi soron) ≤ 0,30`;
- **NAPI**, ha `P_napi ≤ 10%` **ÉS** `C_nap ≤ 0,30`;
- különben **HETI**.

A küszöbök a mért természetes törésekbe esnek: a `P` 10%-a a 7,7 ↔ 14,9 közé, a
`C_nap` 0,30-a a 0,246 ↔ 0,416 szakadékba (robusztus, nem finomhangolt).

**KIMONDANDÓ — az alacsony T IGAZ EREDMÉNY:** ha egy rács átment MINDKÉT kapuján
(alacsony padló, gyenge ciklus), akkor az **alacsony trend-R² egy stabil szintet
jelent, NEM hibát és NEM rács-problémát.** A „szintmérő" szavaknál (pl. hitel,
betegség) épp ezt várjuk: lapos, stabil szint, értelmes irány nélkül. A rács
akkor rossz, ha a P vagy a C bukik — nem akkor, ha a T alacsony.

---

## 4. A mért besorolás (13 szó, 2026-08-13)

| rács | szavak |
|------|--------|
| **ora** (2) | benzin, nyugdíj |
| **nap** (6) | eladó lakás, albérlet, betegség, napelem, hitel, nyaralás |
| **het** (5) | kormányablak, állás, kórház, akciós újság, tüntetés |

Mérési alap (tartós, gitignore-olt): `.atadas-archiv/meresek/racs_dontes_13_szo_2026-08-13.md`
(a nyers baseline-okkal együtt). Ez az EGYETLEN tartós összehasonlítási alap: ha
később bármely szó rácsa mozdul, eldönthető marad, hogy a szó VISELKEDÉSE
változott-e, vagy csak az ablak renormált. Leletek: `kormányablak` C_nap=0,868 (a
legerősebb hétnap-ciklus); `tüntetés` arány 0,01 / szél 99% az órás rácson
(esemény-jellegű, nem ciklikus — lásd §7 nyitott: trendvonal nélkül).

---

## 5. A másodlagos fájl szerződése (`kulcsszo_masodlagos_nyers.json`)

Az órástól (`kulcsszo_nyers.json`) KÜLÖN fájl, hogy az órás rács tiszta maradjon.

- Alak: `{"kulcsszavak": {kifejezes: [rekord, ...]}}`.
- Per-rekord **`racs`** ∈ {nap, het} (az „ora" a másodlagos fájlban ÉRVÉNYTELEN —
  az órás a saját fájljában él).
- **Kötelező `lekerdezes_utc`** (tz-aware UTC ISO) — a pillanatképek rendezéséhez,
  mert a nap/het retroaktív, és ugyanahhoz a naphoz több lekérdezés is tartozhat.
- **Retenció: szavanként a `N=3` legutóbbi rekord**, `lekerdezes_utc` szerint,
  **ADAT-relatív** (nem falióra) — ha egy szó nem frissül, a története NEM ürül.
- Karantén / hard-fail kettéválasztás (az `ir_gordulo` mintájára): a LEMEZRŐL
  visszaolvasott sérült örökség karanténba (kihagyás + naplózás); a FRISS
  producer-rekord hibája a MI bugunk → `ValueError` (fail-loud).

**KIMONDANDÓ — idempotencia-teszt NEM írható rá:** az órás `ir_gordulo`-ra van
bájt-azonos újraszámolási teszt (ugyanabból a bemenetből ugyanaz jön ki). A
másodlagos író erre NEM tesztelhető, mert **3 pillanatképet tart**: egy második
lekérdezés új rekordot fűz hozzá, a fájl NEM lesz bájt-azonos. A szerződés-teszt
ezért CSAK a szerkezetet és az érvényességet őrizheti (mezők megléte, retenció
mérete, rendezés, karantén/hard-fail), NEM a bájt-azonosságot.

---

## 6. Az ütemezés és a másodlagos ág

- **Max 2 szó/nap** (`MAX_MASODLAGOS_NAPI = 2`) — szerkezeti konstans, a
  körbeforgó eloszlás csúcsa; ebből jön a hívás-plafon fejtere is.
- A ma ütemezett szavakat a **nem-ora szavak config-sorrend szerinti sorszáma %
  7 == UTC-hétnap** választja ki (körbeforgó, konstrukcióból kiegyensúlyozott: 11
  szó → 2-2-2-2-1-1-1). A konkrét szó→nap hozzárendelés config-sorrend-FÜGGŐ (nem
  szerződés; a nap/het pótolható). *(Task 5 tervezett: ezt elavultság-vezérelt
  kiválasztás váltja fel — lásd §8.)*
- A másodlagos ág az **`AGAK` LEGUTOLSÓ eleme**, az órás gyűjtés UTÁN fut. Indok:
  az órás (`now 7-d`) pótolhatatlan, ezért védve, elöl; a másodlagos pótolható.
- **429 → CSENDES FELADÁS** (saját try/except, NEM block-stop): a futás tisztán
  folytatódik. **SZAVANKÉNTI írás** → a blokk ELŐTT lemért szavak megmaradnak.
- **Külön naplócímke** (`kulcsszo_masodlagos`) — a `naplo.csv`-ben elkülönül az
  órás `kulcsszo` blokktól. A másodlagos blokk BENIGN, az órás blokk SÚLYOS.
- Hívás-plafon: `(tervezett_hivasszam + MAX_MASODLAGOS_NAPI) * max_probak`.

---

## 7. Elavultság-jelzés (a másodlagos ág success-vaksága ellen)

A másodlagos ág némán elavulhat: blokknál a szó kimarad és csak később kerül újra
sorra; senki nem veszi észre. Ellenszer:

- **`elavult_masodlagos_szavak(sorozatok, most, kuszob_nap=10)`** — tiszta
  függvény: azok a szavak, amelyek legfrissebb `lekerdezes_utc`-je kora `> 10`
  nap. CSAK a `sorozatok` jelenlévő kulcsain iterál → az ora-szavak (sosem
  másodlagos-kulcs) SOSEM jelennek meg; a never-collected nem-ora szó SEM (a
  rotációba még be nem került — Task 5 dolga). Kor-csökkenő, tie-break ábécé.
- **`_jelez_elavult_masodlagos`** — a `futat` farkában (a napló ELŐTT):
  `FIGYELEM: elavult másodlagos: <szó> (<N> napja), ...` a run.log-ba; **néma, ha
  nincs elavult** (a néma siker itt helyes).
- A küszöb 10: a `%7` alatt minden szó hetente frissül (normál kor max ~7), egy
  kimaradt kör után ~14 → a 10 a kettő közé esik.

**KIMONDANDÓ — nem az L7-korlát:** a FIGYELEM sor efemer (run.log, 14 nap
artefakt-retenció), DE a forrás-tény (`lekerdezes_utc` szavanként) a **commitolt**
másodlagos fájlban van, és a jelzés IDEMPOTENS napi (tartós elavulásnál minden
futás újra kiírja) → nincs szükség tartós nyomra.

---

## 8. Nyitott — a megjelenítés és a regresszió (Task 6+, NEM leszállítva)

A felület **MÉG NEM fogyasztja** a `kulcsszo_masodlagos_nyers.json`-t. Ez a fázis
valódi következő lépése és a legnagyobb ismeretlen. Röviden, hogy a szerkezet ne
nyíljon újra (a részletes terv külön készül):

- A regressziós számítás ma **kizárólag órás rácsot feltételez** (`_hianyzo_orak`
  a 3600 mp-es slotra, a `MIN_PONT = 24` padló, az `INTERVALLUMOK` nap-készlet, az
  `app.js` „óra"-feliratai és órarács-rajzolása). Ezek a nem-órás rácsokra
  általánosítandók — a `MIN_PONT = 24` a napi/heti soron a KÖTŐ korlát, nem az
  órás 168-pont.
- A `tüntetés`-nél (esemény-jelző) **trendvonal NEM készül** — a döntés helye és a
  helyette rajzolt tartalom Task 6-ban dől el.
- A **Task 5** (elavultság-vezérelt ütemezés) a `%7`-et váltja fel; a tie-break ott
  **config-index** (NEM ábécé, mint a §7 láthatóságnál), mert az ütemezőben azt
  dönti el, MELYIK szó kerül lekérdezésre azonos `lekerdezes_utc` esetén.
- A never-collected nem-ora szavak láthatósága Task 5 UTÁN újranyitandó (ha akkor
  egy szó MÉGIS kimarad a rotációból, az valódi hiba).
