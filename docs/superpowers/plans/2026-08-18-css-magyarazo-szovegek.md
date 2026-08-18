# Terv — CSS blokk-elkülönítés + magyarázó szövegek (jóváhagyva 2026-08-18, 3 módosítással)

Frontend/CSS kör, SZEMLE-KÖTELES. A „teljes/összes adat" nézet NEM ebbe a körbe tartozik (ERVENYES-ROUTING-osztály,
a LANC-ORAS Szelet 2 UTÁN, külön kör — két routing-változás egyszerre a mai hiba receptje). Canvast EGYIK szelet SEM
érint → NINCS szeletenkénti szemle: mindhárom szeletet végigfejlesztem, EGY szemle a végén, push ELŐTT.

## MÉRT alapok
- Szürkézés: `.vezerlo-sav { background:#fafafa; border; border-radius }` (commit `d86af56`, §7.1) → FELÜLÍRJUK (nem revert).
- Tartalom-blokkok `#kulcsszo-blokk`/`#trend-blokk`: nincs keret.
- „nincs görbe" ok-kódok (egyesitett_reg app.js:194-206): ELVI = `rovid_het_ablak`/het `keves_pont`; IDŐBELI =
  `nincs_masodlagos`/`rovid_masodlagos`. A benzin/nyugdíj (órás-only, `!miv`) → `nincs_masodlagos` (JOGOSULATLAN-URES-UZENET).
- A frontend NEM olvassa a `kulcsszo_lanc.json`-t (BLOKKOK:35) → a lánc-hossz (N) most nem elérhető olcsón.

## Szelet 1 — CSS blokk-elkülönítés (item 1)
`.vezerlo-sav` háttér #fafafa → **#fff**; `#kulcsszo-blokk` és `#trend-blokk` kap `border:1px solid #e3e3e3;
border-radius:6px; padding` (a 2 vezerlo-sav kerete már megvan). Fehér marad, finom keret+sarok, se szín, se árnyék.
RED (DOM): a vezerlo-sav háttér NEM #fafafa; a 2 tartalom-blokk számított kerete jelen. SZEMLE: a 4 blokk elkülönül.

## Szelet 2 — kártya-szövegek: felbontás + ELVI/IDŐBELI + benzin-fix (items 3, 4, 5)
- **Felbontás (item 3):** minden kártyán kiírva a felbontás (óránkénti/napi/heti), az ÜRES kártyán is. Forrás: az
  intervallum `_racs`-a; üresnél a szó config-rácsa (o.racs). Javasolt: „Felbontás: heti".
- **Üzenetek (item 4 + 5), jóváhagyva (a benzin MÓDOSÍTVA — nincs „Készül" ígéret):**

| eset | ok-kód / feltétel | szöveg |
|---|---|---|
| ELVI (heti rács, rövid ablak) | rovid_het_ablak / het keves_pont | „Heti felbontású szó — ez az ablak túl rövid a heti rácshoz. **Ez nem fog feltöltődni.**" |
| IDŐBELI (nap/het, még nincs) | nincs_masodlagos | „Ehhez az ablakhoz még gyűlik a napi/heti adat. **Magától feltöltődik.**" |
| IDŐBELI (másodlagos rövid) | rovid_masodlagos | „A napi/heti sorozat még rövidebb ennél az ablaknál. **Magától feltöltődik.**" |
| **benzin/nyugdíj (órás-only)** | ÚJ ág: `o.racs==="ora" && !miv` | „Órás felbontású szó — ehhez az ablakhoz az órás sorozat **láncolása** kell." (TÉNY, se ígéret, se szám) |

  A DINAMIKUS N („az órás lánc N napra nyúlik vissza") SZÁNDÉKOSAN kimarad: a frontend nem olvassa a láncot →
  drága, VAGY backend-mező kellene (scope). Az N természetesen jön a LANC-ORAS Szelet 2- vel. NE írjunk magától
  elavuló szöveget.
- RED (DOM): a 4 eset szövege KÜLÖNBÖZŐ + tartalmazza a helyes kulcsszót („nem fog feltöltődni" vs „magától
  feltöltődik" vs „láncolása"); benzin 2_het szövege NEM tartalmazza a „napi/heti adatot"-ot. SZEMLE: ránézésre eltér.

## Szelet 3 — gomb-magyarázatok, (A) sub-szöveg (item 2)
Minden intervallum-gomb ALÁ rövid időtartam-leírás (a divben LÁTSZÓDIK, nem tooltip): „mától visszafelé 1 hét /
2 hét / 1 hónap / 3 hónap / 1 év". RED (DOM): a magyarázat-szöveg jelen a gombhoz.
**⚠ VEZERLO-MAGAS — KÖTELEZŐ MÉRÉS:** a `scripts/vezerlo_meres.js` harnesszel, a KONTEXTUST rögzítve (viewport-magasság,
gomb-szám, szövegek). A VEZERLO-MAGAS lelet 320px MAGAS viewporton készült → OTT is mérni (VP=…x320), nem csak a
390×844 alapértelmezetten. Ha a vezérlő kilóg → **STOP, jelezni, NEM fércelni** (nem rövidítjük a szöveget értelmetlenre).

## SZEMLE (a végén, push ELŐTT) — amit a user néz
(1) a 4 blokk elkülönül-e (fehér, visszafogott); (2) a 4 üzenet-eset ránézésre eltér-e; (3) a gomb-magyarázatok
olvashatók-e; (4) a vezérlő nem lóg-e ki. Konzol-hiba nincs. ZOLD-NEM-SZALLIT: a köztes állapot szemle nélkül nem push.

## RED-fegyelem + PARKOLT
Minden RED DOM-assertálható (osztály/keret jelenlét, szöveg-tartalom); a canvas-belső NEM (SZEMLE őrzi). A
szándékos-zöldek fedése MÉRVE (SZANDEKOS-ZOLD-VAK, 0 fedés → csere). MUTÁCIÓ==1. JOGOSULATLAN-URES-UZENET a Szelet
2-ben feloldva (PARKOLT jel törlendő). Új leletet PARKOLT-ként.
