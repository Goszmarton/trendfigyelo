# GORBE-B — rekesz-idősor (a holtverseny-rekesz trendjei is kapjanak sparkline-t)

Dátum: 2026-08-17
Előzmény: 6b + 6c LESZÁLLÍTVA (a GORBE-B a leltárban a 6b UTÁNRA volt időzítve).
Terv JÓVÁHAGYVA 2026-08-17 (a három paraméter + a kétállapotú FIGYELEM).

## A probléma — MÉRVE (nem tippelve)

A napi TREND-blokkban a **D1 holtverseny-rekesz** trendjei megjelennek, de
**idősor (sparkline) NÉLKÜL** → „nincs idősor ezen a napon". Ok: a megjelenített
lista = top `trend_idosor_max` (15) + a küszöb-volumennel megegyező tie-bucket
(a `trend_megjelenites_max`=25 plafonig), DE idősort CSAK a top-15 prefix kap
(`idosorok.gyujt` `[:trend_idosor_max]`-ra vág; `top_trend_struktura` az
`idosor_map.get(kif, [])`-vel üreset ad a rekesznek).

MÉRT (élő + 5 nap): 08-16 17/15/**2 üres** (ufc 330, lionel messi, vol 2000);
08-15 16/15/1; 08-14 20/15/5; 08-13 15/15/0; 08-12 25/15/**10** (a 25-plafonig);
08-11 blokk-bukás (0 idősor, más hibaosztály). A küszöb-volumen mindig 2000 (a
legalsó Google-sáv) — a top-15 megtelik, a 2000-rekesz maradéka idősor nélkül marad.

## Döntés: (a) FORWARD-ONLY

A rekesz-szavak is kapjanak idősort a GYŰJTÉSKOR (akkor ismertek a pillanatképben);
visszamenőleges pótlás NEM (a régi napok sosem telnek fel, az üres-felirat marad).

## Kötelező kikötések (a törékeny idősor-ág védelme)

1. **Sorrend:** top-15 idősor (VÁLTOZATLAN) → másodlagos → **rekesz LEGUTOLSÓ**.
   Indok: a másodlagos rotáció a Task 5 bemenete; a rekesz elé téve egy nagy
   rekeszes nap kiéheztetné a rotáció hívás-keretét, a lefedettség-építés hetekre
   lassulna. A rekesz a legopcionálisabb.
2. **A rekesz-ág bukása NEM job-piros.** A top-15 tartalma ma garantált — ez a
   garancia nem gyengülhet. A rekesz-ág a `_masodlagos_ag`-mintát követi: saját
   try/except, csendes feladás 429/hibára, FIGYELEM a naplóba, se propagálás, se
   exit-kód. (NEM a `_ag`, ami `PlafonTullepve`→exit 2 / AgFeladva→block-stop.)
3. **Plafon:** `tervezett_hivasszam += trend_idosor_rekesz_max` → 2+15+5+13 = **35**
   → hívás-plafon = `(tervezett_hivasszam + MAX_MASODLAGOS_NAPI) × max_probak`
   = **(35+2)×4 = 148** (a régi (30+2)×4 = **128** helyett). **KORREKCIÓ (Szelet 3,
   MÉRT 08-18):** a plafon NEM `tervezett × max_probak` (az 140-et adna) — a `+
   MAX_MASODLAGOS_NAPI`(=2) fejtér is benne van (`_szamitott_plafon`,
   futtato.py:490-492). A doc korábbi 140-e ELÍRÁS volt. A 128 és a 148 is
   LEVEZETETT szám, NINCS beírt konstans. Lásd a PLAFON-128 konfliktus-elemzést lent.
4. **Konfigurálható felső korlát:** `trend_idosor_rekesz_max = 5` (NEM a 25-maradék).
   Indok (a saját mérésből): a napi többlet jellemzően +1..5; a 10 az elméleti max,
   ami épp a kiugró (08-12: 10) napokon engedne a legtöbbet — a legkockázatosabb
   pillanatban. Ötnél a jellemző nap teljesen fedett, a kiugró fékezett.
   NEM-MÉRT konstans, első közelítés.
5. **Régi napok:** a `TREND_IDOSOR_URES_ELEM = "nincs idősor ezen a napon"` MARAD
   (forward-only), nem ígér feltöltődést (ugyanaz a szabály, mint a rovid_masodlagos).

## Kétállapotú FIGYELEM (a rekesz-ág naplója) — KÖTELEZŐ

A rekesz-ág naplója KÜLÖNBÖZTESSE MEG (ne mossa össze, mint a MASODLAGOS-PLAFON
'kihagyva'-hibája):
- **(a) nincs rekesz** (üres tie-bucket, vagy D4 0-küszöb) → „nincs mit gyűjteni"
  (nem hiba, nem elmaradás).
- **(b) volt rekesz, de az 5-ös korlát VAGY 429 megfogta** → a napló írja ki,
  HÁNY szó maradt el ÉS MIÉRT (`korlát` vs `429`). Ez a különbség kell az
  L11/rotáció későbbi elemzéséhez.

## PLAFON-128 KONFLIKTUS — kimondva (a Task 5 előtt)

A `tervezett_hivasszam` ma `2 + trend_idosor_max + len(kulcsszavak)`. Két jövőbeli
módosító:
- **EZ (GORBE-B):** egy IDŐSOR-tagot ad: `+ trend_idosor_rekesz_max`.
- **Task 5:** a KULCSSZO-tagot írja át (a rotáció szerint melyik szó fut aznap).
A két tag KÜLÖNBÖZŐ és ADDITÍV → **nincs közvetlen konfliktus.** DE mindkettő
ugyanazt a függvényt módosítja → a **Task 5 tervénél a formulának MINDKÉT
módosítást tartalmaznia kell** (idősor-rekesz + rotáció-kulcsszó). Az L4 szelep
(`PlafonTullepve`→exit 2) érintetlen: a rekesz a MEGEMELT plafon (**148**) alatt fut,
a saját 429-csendes-feladása NEM plafon-túllépés. A PLAFON-128 leltár-tétel ezzel
ÚJRANYITVA (a plafon 128→**148**, LEVEZETETT: (35+2)×4); a frissítés a Szelet 1
commitjában (rule a), a szám EXPLICIT levezetése a Szelet 3 leltárában.

## Szeletek

### Szelet 1 — BACKEND (auto-teszttel őrizhető)
Érint: `config.yaml`+`config.py` (`trend_idosor_rekesz_max=5`), `futtato.py`
(`rekesz_kifejezesek` helper + `_rekesz_idosor_ag` szakasz LEGUTOLSÓ + kétállapotú
FIGYELEM + `tervezett_hivasszam` bővítés), `idosorok.py` (a `gyujt` vagy vékony
variáns, ami tetszőleges kifejezés-listát vesz, nem `[:trend_idosor_max]`-ra vág).

TDD RED (pytest, névre/hibatípusra):
1. `test_rekesz_kifejezesek_tie_bucket_5re_korlatozva` — a top-15 feletti tie-bucket,
   `trend_idosor_rekesz_max`(5)-re vágva → **AttributeError** (helper nem létezik).
2. `test_tervezett_hivasszam_rekesszel` — 2+idosor_max+rekesz_max+kulcsszavak = 35 →
   **AssertionError** (ma 30).
3. `test_rekesz_ag_429_csendes_nem_exit_top15_megmarad` — AgFeladva→csendes, exit≠2,
   a top-15 idősor megvan → **AssertionError** (naiv `_ag` propagálna/exitelne).
4. `test_rekesz_figyelem_ketallapotu` — (a) üres rekesz → „nincs mit gyűjteni";
   (b) korlát/429 → „elmaradt N szó (korlát|429)" → **AssertionError** (ma nincs ilyen).
   (+ a `test_rekesz_idosor_bekerul_a_trend_idosorokba` a szeletelt-adat oldalra.)

Ha kész és zöld → PUSH külön körben (ne halmozódjon pusholatlan commit).

### Szelet 2 — FRONTEND (VIZUÁLIS SZEMLE a záró kapu)
Érint: valószínűleg NULLA frontend kód — a rekesz-szó most `idosor`-t kap → a
MEGLÉVŐ `trend_sparkline_letrehoz` rajzol (KÜLÖN `trend_chart_peldanyok`, Task 8a).
- VIZUÁLIS SZEMLE: ÚJ napon a rekesz-szó (ufc 330) sparkline-t rajzol; RÉGI napon
  (dátumválasztó) marad „nincs idősor ezen a napon".
- E2e: régi-nap rekesz-kártya `data-idosor-allapot`=üres; új-nap sparkline jelen.

### Szelet 3 — leltár + spec záró (a szemle után)
GORBE-B FÉLRETETT→leszállítva (forward); PLAFON-128 frissítve; `trend_idosor_rekesz_max`
NEM-MÉRT + újramérési feltétel; a rekesz-ág nem-piros hibaosztálya. Invariáns méréssel.

## Újramérési feltétel (leltárba)
„14 nap után újramérendő: a rekesz-ág 429-aránya, és hányszor harapott az 5-ös
korlát (elmaradt többlet)." Indok: a másodlagos retenció is ~14 nap (ugyanaz az
ablak), és elég hosszú a rossz napokhoz (07-27/28, 08-11 → bukás 2-3 hetente).

## Mit NEM szabad elrontani (ma leszállított)
A trend-sparkline út KÜLÖN — a `racs_epit` szeletelés, az esemenyjelzo szint-nézet,
a `data-rajzolt-pont`, a `chart_takarit`/`chart_peldanyok` ÉRINTETLEN. GORBE-B csak:
`futtato.py` trend-ág + `idosorok.py` + config + a trend-sparkline frontend.

## Spec-eltérés → ez a DOC-COMMIT (a kód ELŐTT)
phase3-spec §7.3 (D1): az „idősor-lista változatlanul top `trend_idosor_max`, a
kiterjesztés a hívásköltséget nem érinti" REVÍZIÓ — az idősor-lista forward-only
kiterjed a rekeszre (`trend_idosor_rekesz_max`-ig, LEGUTOLSÓ csendes ág), a plafon
emelt. A prefix-invariáns (idősor ⊆ megjelenített) áll; a rekesz a prefix UTÁN jön.
