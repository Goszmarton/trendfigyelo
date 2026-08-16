# 6b / RACS_EGYSEG — terv (rács-tudatos felirat, az első 6b-szelet)

Dátum: 2026-08-16
Spec: docs/superpowers/phase4/phase4-spec.md §8 (a felület MÉG NEM fogyasztja a
nap/het másodlagos adatot; a §8:168 nevesíti az `app.js` „óra"-feliratait és
órarács-rajzolását mint általánosítandót).
Leltár: RACS-EGYSEG (C-blokk), a 6b (nem-órás megjelenítés) első RED-szelete.

## Cél és szűk hatókör

A `merteszamok_szoveg` (docs/js/app.js) rács-VAK: a jel-erősség feliratban a
rács-szót („óra") hardkódolja. Ez a szelet CSAK a rács-SZÓ-t teszi rács-tudatossá,
hogy a későbbi nap/het megjelenítés helyes feliratot kapjon. NEM érinti:
- a **rajzolást** (racs_epit / ora_index / x-tengely „ HH:MM" / tooltip) — ez a
  KÖVETKEZŐ, nagyobb 6b-szelet, saját RED-del;
- a **mértékegységet** — mérve rács-INVARIÁNS (lásd lentebb).

## Mért lelet — a mértékegység NEM rács-függő

Mindkét JSON ugyanazt deklarálja: `meredekseg_egyseg: "relatív pont / nap"`
(kulcsszo_regresszio.json ÉS kulcsszo_masodlagos_regresszio.json), mert a
másodlagos meredekség is per-NAP (`meredekseg_nap`). Ezért a „relatív pont/nap"
(app.js:311) a napi és heti rácson is helyes → NEM cél. Csak a rács-szó az.

## A rács-vak feliratok TELJES leltára (hogy ne szeletenként derüljön ki)

| # | Hely | Felirat | Rács-függő? | Ebben a szeletben? |
|---|------|---------|-------------|--------------------|
| a | app.js:313 `merteszamok_szoveg` | „N/M **óra** nem-nulla (M/nevező lezárt, K részleges kihagyva)" | IGEN (óra/nap/hét) | **IGEN — ez a cél** |
| b | app.js:311 `merteszamok_szoveg` | „relatív pont/nap" (egység) | NEM (mérve invariáns) | nem |
| c | app.js:83 `TENGELY_FELIRAT` | „relatív keresési szint (0–100)" | NEM (0–100 közös) | nem |
| d | app.js:322 `frissesseg_szoveg` | cimke az INTERVALLUMOK-ból | NEM (már rács-független) | nem |
| e | app.js:381/506 x-tengely + tick | dátum + „ HH:MM" | IGEN, de **rajzolás** | nem — következő szelet |
| f | app.js:505 tooltip | az x-label formátumát követi | (rajzolás) | nem — következő szelet |

## Leképezés és forrás — frontend, „ora" default, ismeretlen-fallback

- Frontend `RACS_SZO = {ora:"óra", nap:"nap", het:"hét"}` (a magyar UI-szó
  prezentáció, mint IRANY_MAGYAR/DOMEN_CIMKE/TENGELY_FELIRAT — nem adat).
- A `racs` a másodlagos JSON-ban **szó-szinten** él (`ks[szó].racs`); az órás
  JSON-ban NINCS → a hívó a szó `racs`-át adja át, **default „ora"**. Így az órás
  út bájt-azonos, nulla JSON-séma-változás, nulla backend-commit.
- Szignatúra: `merteszamok_szoveg(iv, racs)`; hívó (app.js:464) `szoreg.racs`-ot ad.
- **Ismeretlen érték NEM csendes** (KUDARC-VAK-elhárítás): egy `racs_szo(racs)`
  helper `RACS_SZO[racs || "ora"] || ("? " + (racs || "ora"))` — ismeretlen rács
  (config-elgépelés / jövőbeli negyedik rács) → LÁTHATÓ nyers érték, NEM undefined,
  NEM néma „óra".

### A „hét" kétértelműsége — megnézve, MARAD

Kontextus: „… · 3/4 **hét** nem-nulla (4/4 lezárt, 1 részleges kihagyva)". A keret
`N/M <egység> nem-nulla (M/nevező lezárt, …)`; a tört (3/4) UTÁN álló egységet a
zárójel M-ismétlése (4/4) slot-számlálásként rögzíti, magyarul szám után az egység
egyes számban áll („4 hét" = négy hét). A „hét = hetes szám" olvasat itt lehetetlen.
Párhuzamos az óra/nap alakkal; a „heti pont" megtörné a párhuzamot. → tudatos: `hét`.

## TDD

- Infra: Playwright e2e (§8.3: nincs JS-unit). `e2e/kulcsszo.spec.js` `page.route`
  + `reg()`/`regSzo()` helper; a 144./206. sor MÁR „óra nem-nulla"-t assertál.
- **RED (névre, hibatípusra):** új `Xa. nap-rácsú szó → 'nap nem-nulla'` teszt egy
  `racs:"nap"` fixture-szóval → `toContainText("nap nem-nulla")`. A jelenlegi kód
  mindig „óra"-t ír → **AssertionError (szöveg-eltérés), viselkedésbeli RED** (nem
  Import/timeout).
- **Ismeretlen-rács teszt:** `racs:"negyedev"` → a felirat NEM „óra" ÉS NEM
  „undefined" (a látható nyers érték jelenik meg).
- **SZÁNDÉKOS-ZÖLD (ELŐRE jelölve):** (1) a meglévő 144./206. (racs nélkül → „óra")
  változatlan; (2) explicit `..._racs_nelkul_ora_SZANDEKOS_ZOLD`.

## Diff és lezárás

Becslés: app.js ~4–6 sor (RACS_SZO konstans + racs_szo helper + 1 argumentum +
hívás) + e2e ~2–3 teszt + helper 1 sor. Cél: <50 sor kód → subagent-review nem
kötelező; ha az ismeretlen-ág 50 fölé viszi, jelzés.

Lezáráskor (UGYANABBA a commitba): RACS-EGYSEG → LESZÁLLÍTVA („lásd git log",
d-szabály); a 6b Állapota frissül (első szelet kész, rajzolás hátra); invariáns
33 + 12 + 7 + 1 = 53 (aktív −1, LESZÁLLÍTVA +1); (C) 5→4; git add névvel; push.
