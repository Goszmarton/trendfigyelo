# Elemzés-fül — YouTube-szegmens (napi AI-elemzés a YouTube-adatokra) — tervdokumentum (spec)

**Dátum:** 2026-08-25
**Repó:** Goszmarton/trendfigyelo (publikus)
**Állapot:** jóváhagyott terv, implementáció előtt (Phase 4)
**Modell:** `claude-opus-4-8` (a meglévő elemzés-hívás bővítése)

## 1. Cél és kontextus

Az Elemzés fül **két nevesített szegmensre** bővül:
1. **„Google keresések napi elemzése"** — a MEGLÉVŐ elemzés (13 kulcsszó + felkapott + „mi változott ma"), VÁLTOZATLAN.
2. **„YouTube keresések napi elemzése"** — ÚJ: a 12 YouTube-szó (8 kosár) napi AI-elemzése, a Google-részhez hasonlóan **VALÓS számok dobozokban + AI-próza**, a `youtube_nyers.json` + `youtube_regresszio.json` adatból.

A meglévő ELEMZES-FUL alap (spec 2026-08-22) minden nem-alkudható elve ÖRÖKLŐDIK; ez a doc csak a YouTube-szegmens hozzáadását specifikálja.

## 2. Nem-alkudható követelmények (öröklött)

### 2.1 A számokat PYTHON számolja, nem az AI (MÉRJ, NE TIPPELJ)
A YouTube VALÓS réteg is determinisztikus Pythonból (irány, mai érték, csúcs, átlag, heti mozgás). A Claude **CSAK a YouTube-narratívát** írja, számot NEM talál ki. A jelölési fegyelem ([[naming-discipline]]): VALÓS = Python-számok; a próza mezőnevet/„payload"-ot/adatstruktúrát NEM szivárogtat (a meglévő `RENDSZER_PROMPT` tiltása kiterjed a YouTube-szekciókra is).

### 2.2 EGY hívás, EGY fail-soft, EGY archívum
A YouTube-szegmens **ugyanabba a napi `elemzes.json`-ba** kerül, **EGYETLEN, bővített Claude-hívással** (nem külön második hívás). Így a meglévő egyetlen `try/except` fail-soft (API-hibán a régi `elemzes.json`+archívum marad) automatikusan lefedi a YouTube-részt is; nincs részleges-siker elágazás. Egy napi archív-bejegyzés tartalmazza mindkét szegmenst; a naptár-visszalapozás változatlan.

## 3. Architektúra — (a) egy elemzes.json, „youtube" blokk

Az `epit_payload` egy új `"youtube"` kulccsal bővül; a `_valasz_sema` egy új `"youtube"` próza-szekció-csoporttal; a `valasz_to_artefakt` egy új `"youtube"` blokkot varr össze (VALÓS a payloadból + AI-próza a válaszból). A `futtat` betölti a `youtube_regresszio.json` + `youtube_nyers.json` fájlokat. A Google-blokkok (`valtozas`/`kulcsszavak`/`felkapott`) BÁJT-AZONOSAN változatlanok.

## 4. YouTube VALÓS réteg (Python, determinisztikus)

**Forrás:** `youtube_regresszio.json` (irány/meredekség/érvényesség/mai érték) + `youtube_nyers.json` (nyers sorozat → csúcs/átlag/heti mozgás). **NINCS** `tortenet`/`lanc` a YouTube-nál — a csúcs/átlag/heti-delta közvetlenül a nyers sorozatból számolódik.

- **`_youtube_szamok(youtube_regresszio, youtube_nyers)`** — szavanként (mind a 12):
  - `szo`, `domen` (a 8 kosár egyike);
  - `irany`, `meredekseg`, `ervenyes`, `mai_ertek` — a szó **leghosszabb ÉRVÉNYES** intervallumából (a frontend `teljes_valaszt` mintája; robusztus a napi/heti rács-eltérésre — a `1_het` a YouTube-nál gyakran érvénytelen, ezért NEM fix `1_het`, mint a Google-nél);
  - `csucs` (a nyers sorozat max-a), `atlag` (a nem-részleges pontok átlaga) — a `youtube_nyers` **heti (12-m) sorozatából** (a legteljesebb tartomány).
- **`_youtube_het(youtube_nyers)`** — a heti mozgás: szavanként a legutóbbi hét változása (utolsó lezárt heti pont vs. ~1 héttel korábbi), `abs`-szerint rendezve; a `_kulcsszo_het` mintája, de a `youtube_nyers` heti sorozatából (nincs lánc). Ez táplálja a „heti mozgás" prózát ÉS megőrződik VALÓS-ként az artefaktban (`het_valos`).

**Óvatosság:** a 0–100 RELATÍV skála a YouTube-nál is szavanként külön; a szavak egymással nem összemérhetők — ezt a próza-fegyelem (nem az AI dönti el, mi „jelentős") tartja.

## 5. YouTube AI-próza (3 szekció — Google-paritás)

A Claude a YouTube VALÓS payloadból **három** próza-szekciót ír (mind `{"szoveg": string}`, folyó bekezdések, mezőnév-szivárgás nélkül):
- **`youtube.napi`** — mit néznek ma (a mai értékek + irányok olvasata a 12 szón / 8 kosáron).
- **`youtube.teljes_kep`** — a hosszabb kép: mely témák tartósan erősek/gyengülnek (a trend-irányok + csúcs/átlag alapján).
- **`youtube.het`** — a heti mozgás: a legnagyobb heti mozgók (a `_youtube_het` VALÓS deltáiból).

**NINCS** YouTube „mi változott ma?" (napi diff) — a heti rácsú szavak napi mozgása zajos lenne (user-döntés, 2026-08-25). **NINCS** YouTube „felkapott" — az fogalmilag Google-only (nincs YouTube trending-réteg).

## 6. `elemzes.json` séma-bővítés

Új top-level `youtube` blokk (a Google-blokkok mellé):
```
youtube: {
  szamok:     [ {szo, domen, irany, meredekseg, ervenyes, mai_ertek, csucs, atlag}, ... ],  // VALÓS, 12 szó
  het_valos:  [ {szo, valtozas, ...}, ... ],   // VALÓS, heti mozgók (megőrizve)
  napi:       "…",   // AI-próza
  teljes_kep: "…",   // AI-próza
  het:        "…",   // AI-próza
}
```
A séma (`_valasz_sema`) `required`-je bővül a `youtube` szekcióval; `additionalProperties: False` megtartva.

## 7. Backend beavatkozási pontok (`trendfigyelo/elemzo.py`)

1. `futtat`: betölti `youtube_regresszio.json` + `youtube_nyers.json`-t (fail-soft: ha hiányoznak, a YouTube-szegmens üres/kihagyott — a Google-elemzés akkor is fut; lásd §10).
2. Új `_youtube_szamok(...)` + `_youtube_het(...)` (§4) — tiszta, tesztelhető, AI nélkül.
3. `epit_payload`: `"youtube": {"szamok": …, "het_valos": …}` hozzáadva.
4. `_valasz_sema`: új `"youtube"` szekció-csoport (`napi`/`teljes_kep`/`het`).
5. `RENDSZER_PROMPT`: rövid kiegészítés a YouTube-szegmens fogalmi keretével (videó-igény ≠ webes keresés; a szavak nem összemérhetők) — a tiltó szabályok (mezőnév/payload) változatlanul érvényesek rá.
6. `valasz_to_artefakt`: új `"youtube"` blokk (VALÓS a payloadból + AI a válaszból).

## 8. Frontend (`docs/js/elemzes.js` + `docs/elemzes.html`)

- A `rajzol(art)` **két nevesített szegmensre** tagolódik:
  - `<h2>Google keresések napi elemzése</h2>` fölé/köré a MEGLÉVŐ render (valtozas + kulcsszavak + felkapott) — változatlan tartalommal.
  - `<h2>YouTube keresések napi elemzése</h2>` + ÚJ render a `art.youtube` blokkra: VALÓS csempék (a `valos_kulcsszo_csempek` újrahasznosításával — a `csucs` hiánya már `?? "–"`-ként kezelt; kosár/domén szerinti csoportosítás opció) + a három AI-szekció (napi / teljes kép / heti mozgás).
- Fail-soft a frontenden: ha `art.youtube` hiányzik (régi archív-bejegyzés), a YouTube-szegmens NEM renderel (a Google-rész változatlan) — a visszalapozott régi napokon nincs YouTube-szegmens, ez VÁRT.

## 9. Workflow (`.github/workflows/elemzes.yml`)

VÁLTOZATLAN: a `workflow_run` a napi.yml (19:07 UTC) után fut, friss `main`-t checkoutol. A YouTube-adat (`youtube_nyers/regresszio`) a **külön youtube.yml (15:00 UTC) commitjából** már a main-en van 19:07-kor → az elemzés bevonja. Ha a 15:00-as youtube-futás aznap kimaradt, a YouTube-szegmens az előző napi (lassan mozgó) adatból dolgozik — elfogadható (a heti rács miatt egy nap csúszás jelentéktelen), a próza a `frissitve`/adat-korból nem következtet félre.

## 10. Fail-soft és jelölési fegyelem (a YouTube-részre)

- **Hiányzó YouTube-adat:** ha `youtube_regresszio.json`/`youtube_nyers.json` hiányzik (pl. a fül élesítése előtti nap), a `_youtube_szamok` üres listát ad → a YouTube-szegmens kimarad, a Google-elemzés ZAVARTALAN. (A YouTube-szekció a sémában `required`, de üres `szamok`-nál a prompt jelezheti „nincs YouTube-adat ma" — VAGY a séma a youtube-blokkot feltételesen kéri; a writing-plans dönti el a legkisebb-kockázatú megoldást.)
- **API-hiba:** a meglévő egyetlen fail-soft (a teljes `elemzes.json` régi marad) fedi.
- **Üres/hallucináció-védelem:** a YouTube-prózára is áll a mezőnév/payload-tiltás; a próza NEM állít ok-okozatot tényként.

## 11. Tesztelés (`tests/test_elemzo.py` bővítés)

- `_youtube_szamok`: a leghosszabb érvényes intervallumból irány/mai_ertek; csúcs/átlag a nyers sorozatból; a 8 kosár domén-mezője helyes; érvénytelen szó kezelése.
- `_youtube_het`: heti delta a nyers heti sorozatból, rendezés.
- `epit_payload`: tartalmazza a `youtube` kulcsot; a Google-kulcsok VÁLTOZATLANOK.
- `_valasz_sema`: a `youtube` szekció szigorúan `{szoveg}`, nincs `elmeleti`/`megfigyelesek` mező.
- `valasz_to_artefakt`: a `youtube.szamok` VALÓS a payloadból, a `youtube.napi/teljes_kep/het` az AI-ból.
- Tiltott-token: a YouTube-próza sem tartalmaz mezőnevet/„payload"-ot.
- Hiányzó YouTube-adat: a Google-elemzés akkor is előáll (fail-soft).
- Frontend (Playwright): a két szegmens-cím renderel; a YouTube-csempék + 3 szekció megjelennek; régi archív-nap (nincs `youtube`) → nincs YouTube-szegmens, a Google-rész ép.
- A meglévő elemzés-tesztek VÁLTOZATLANUL zöldek (a Google-rész regressziómentes).

## 12. Nem-cél (YAGNI)

- **NINCS** YouTube „mi változott ma?" (napi archív-diff) — user-döntés.
- **NINCS** YouTube „felkapott" — Google-only fogalom.
- **NINCS** külön második Claude-hívás — egy bővített hívás.
- **NINCS** új workflow — az elemzes.yml változatlan.
- **NINCS** YouTube tortenet/lanc bevezetése — a csúcs/átlag/heti a nyers sorozatból.

## 13. Nyitott / a writing-plans dönti el

- A hiányzó-YouTube-adat séma-kezelése: feltételes `youtube` szekció vs. mindig-kért, üres-payload-jelzéssel (§10) — a legkisebb-kockázatú út.
- A YouTube VALÓS csempék pontos elrendezése (kosár-csoportosítás igen/nem) — a Google-csempe-render újrahasznosításának mértéke.
- A `_youtube_szamok` intervallum-választás pontos szabálya (leghosszabb érvényes vs. rács-alapú default) — mérni a valós youtube_regresszio-n.
