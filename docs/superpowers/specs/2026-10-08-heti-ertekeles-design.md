# Heti értékelés — új fül (hétfőnkénti heti riport) — design

**Állapot:** jóváhagyott terv (chat), implementáció előtt.
**Dátum:** 2026-10-08.
**Előzmény:** [[havi-nlp-elemzes]] (a havi alrendszer: korpusz→Claude→grounding→ir + orzo + yml + fül — a HETI PÁRHUZAMOS mintája), [[elemzes-ful-fast-follow]] (napi elemzés: VALÓS számok Python + Claude narratíva, grounded), [[napi-futas-megbizhatosag]] (workflow_run-lánc + szerver-trigger), [[reggeli-kulcsszo-feszultseg]] (28 követett kulcsszó).

## 1. Cél

Egy **teljesen új fül** egy **heti értékeléssel**, amely **hétfőnként** készül el az **előző (hétfő–vasárnap) hétről**. A fókusz az **ügyek tartóssága és összefüggése**: mi tartott ki, mi volt rövid kiugrás, mi tért vissza, és hol látszik kapcsolat a témák és a Google–YouTube adatok között. Magyar nyelvű, LLM-alapú (Claude Opus 4.8, strukturált JSON, adaptive thinking, streaming — a `havi_nlp` mintája), grounded (VALÓS számok Python, ok csak hír esetén, nincs kitalálás).

**USER-döntés:** a generálás **hétfő reggel** fut (a „Reggeli felkapott-gyűjtés" után), hogy a hét elején ott legyen az összefoglaló. A hét: **hétfő–vasárnap** (ISO-hét); a riport a VÉGZETT előző hetet összegzi.

## 2. A riport 6 része (strukturált)

1. **Vezetői összefoglaló:** 5 megállapítás arról, mi változott a héten és miért érdemes vele foglalkozni.
2. **A figyelem átrendeződése:** mely témák ERŐSÖDTEK, mely GYENGÜLTEK a szokásos szintjükhöz képest (a követett kulcsszavak heti szintje vs a saját szokásos szintje — `1_het.illeszkedes`/`irany`). **+ 1 DETERMINISTA divergáló sávdiagram** (nem az AI-narratívából): a követett szavak a szokásos szinttől való eltérésük szerint rendezve (erősödő = pozitív / gyengülő = negatív), a VALÓS `mai_reziduum − reziduum_szokasos` különbségből. USER-döntés: a heti fül „szöveges + egy kis vizualizáció".
3. **Ügyek életútja:** mi volt kiugró RÖVID ideig, mi volt HOSSZABBAN tartó kiugrás, mi TÉRT VISSZA (a felkapott Mon-Sun: `napok_szama`/gyakoriság + a napok íve).
4. **2–3 mélyebb témaelemzés:** témánként keresési pálya, kapcsolódó kifejezések, **ellenőrzött események** (a hírekből), magyarázatok (grounded).
5. **Google–YouTube összefüggés:** hol látszik kapcsolat a két adatforrás között (közös/párhuzamos téma a követett szavak és a YouTube-szavak heti mozgásában).
6. **Jövő heti figyelendők:** javaslatok, mire érdemes figyelni a jövő héten (grounded, a heti pályából/visszatérőkből).

## 3. Architektúra — PÁRHUZAMOS heti alrendszer (a havi mintájára)

- **`trendfigyelo/heti_ertekeles.py`** (a `havi_nlp.py` mintája):
  - `heti_korpusz(docs_data, het_kezdet_iso)`: az előző hét DETERMINISTA aggregálása (csak olvas):
    - **követett kulcsszavak (28):** per-szó a `1_het` intervallumból az `irany` + `illeszkedes` (szokásoshoz képest) + **`elteres_szokasostol`** (a `mai_reziduum − reziduum_szokasos` különbség, a divergáló sávdiagramhoz; `None`, ha hiányzik) + a heti pálya (a `kulcsszo_lanc`/regresszió `illesztes_vonal`/`pontok` a Mon-Sun ablakban) + `domen`/`tipus`; a figyelem-átrendeződéshez (erősödő/gyengülő).
    - **felkapott (Mon-Sun):** a hét `napok/<nap>.json` reggel/este szegmenseiből aggregált kifejezés-lista: `napok_szama` (hány külön napon), max_volumen, témák, hírek (a `havi_korpusz` mintája, 7 napra) — az ügyek életútjához + eseményekhez.
    - **YouTube (heti):** a 12 YT-szó heti iránya/szintje a `youtube_regresszio` `1_het` intervallumából, ha `ervenyes` (`irany`/`illeszkedes`/`mai_ertek`, + `domen`/`tipus`); érvénytelen ablaknál a szó „nincs elég heti adat" jelzéssel marad — a Google–YT összefüggéshez.

  **A `1_het` szemantika:** a `kulcsszo_regresszio.json`/`youtube_regresszio.json` a legfrissebb (a vasárnap esti futáskor számított) pillanatkép; a `1_het` egy ~7 napos GÖRDÜLŐ ablak, amely hétfő reggel ≈ a most lezárult hét. Ez a heti irány/szint grounded jele. A PONTOS hétfő–vasárnap határt a felkapott (`napok/<nap>.json`) aggregálás tartja (a napfájlok dátum szerint szűrve a hét 7 napjára).
    - Kimenet: `{het_kezdet, het_veg, iso_het, kulcsszavak:[...], felkapott:[...], youtube:[...], napok}` — csak VALÓS számok.
  - `heti_elemez(korpusz, kliens=None)`: Claude-hívás strukturált JSON-nal (a 6 rész sémája), bounded retry (3×), fail-soft (tartós hibán None).
  - `grounding_validal(eredmeny, korpusz)`: a korpuszban nem szereplő kulcsszó/téma kiesik (anti-hallucináció, a havi mintája — a prózai mezők nem szűrtek, a hivatkozott szó-listák igen).
  - `heti_ir` (atomi írás `docs/data/heti/<het_kezdet>.json`), `heti_index_ir` (a hónap-választóhoz hasonló hét-index), `heti_generalas(docs_data, het_kezdet, keszult_iso, kliens=None)` (korpusz→elemez→grounding→meta→írás).
- **`heti.py`** (a `havi.py` mintája): belépő — az őr adta hetet generálja (fail-soft) → `heti_index_ir`.
- **`.github/workflows/heti.yml`** (a `havi.yml` mintája): `workflow_run` a **„Reggeli felkapott-gyűjtés"** befejezésére + kézi `workflow_dispatch` (opcionális `het` input). `ANTHROPIC_API_KEY`-vel, külön commit CSAK `docs/data/heti/**`-ra, `git pull --rebase --autostash`. Az őr a `pip install` ELŐTT (stdlib).
- **`trendfigyelo/heti_orzo.py`** (a `havi_orzo.py` mintája): **hétfő-e** (a `seged.esti_nap`/budapesti nap hétfő) + idempotencia (`keszult` LOGIKAI napja == ma → skip, a hajnali dedup; a hét-kezdet a LEZÁRULT előző hét hétfője). Kimenet: a generálandó hét-kezdet (`YYYY-MM-DD`) vagy üres (skip).
- **Frontend:** ÚJ `docs/heti.html` + `docs/js/heti.js` (a `havi.html`/`havi.js` mintája): a 6 rész renderelése + **hét-választó** (a havi hónap-naptár mintája: `index.json` + `?het=YYYY-MM-DD`, hét-lista) + a 2. résznél **divergáló sávdiagram** (SVG/HTML, a havi barchart mintája, dataviz-validált divergáló pár + semleges közép, legenda; csak a nem-`None` eltérésű szavakból, rendezve). Fail-soft üres adaton. **Nav: 6. fül** („Heti értékelés") MINDEN oldal `#fomenu`-jében.
- **Adat:** `docs/data/heti/<het_kezdet>.json` (a hét hétfőjének dátuma a kulcs) + `docs/data/heti/index.json`.

## 4. Séma (`heti_ertekeles._valasz_sema`)

```
{
  vezetoi_osszefoglalo: [string] (maxItems 5),
  figyelem_atrendezodes: { erosodo: [string], gyengulo: [string] },
  ugyek_eletutja: { rovid_kiugras: string, hosszabb_kiugras: string, visszatero: string },
  melyebb_temak: [ { tema: string, keresesi_palya: string,
                     kapcsolodo_kifejezesek: string, ellenorzott_esemenyek: string,
                     magyarazat: string } ] (maxItems 3),
  google_youtube_osszefugges: string,
  jovo_heti_figyelendok: [string],
}
```
`additionalProperties: false`, minden mező kötelező (üres megengedett). A `korpusz`/`keszult`/`modell`/`het_kezdet`/`het_veg`/`iso_het` meta a generáláskor hozzáadva.

## 5. Prompt

A `havi_nlp` rendszer-prompt mintája, heti kontextusra: magyar, laikus olvasó, NINCS mezőnév/JSON, folyó mondatok a prózai mezőkben; VALÓS számok a korpuszból, ok/esemény CSAK hír esetén (anti-hallucináció), semmit nem talál ki; rövid „–" gondolatjel. A 6 rész pontos leírása (lásd §2); a „tartósság" = a heti pálya, az „összefüggés" = kereszt-téma/kereszt-forrás; a „figyelem átrendeződése" a szokásos-szinthez (`illeszkedes`) mérve; az „ellenőrzött események" a megadott hírekből; a „jövő heti figyelendők" a pályából/visszatérőkből, óvatosan (nem eseményjóslat).

## 6. „Ha nincs változás, ne generáljon semmit" — ÉRTELMEZÉS

A havi/heti riport a hét RENDSZERES összegzése (nem napi jelzés). A heti futás **mindig generál** egy heti riportot (a hét lezárult, van mit összegezni) — a „ne generáljon semmit magától" a NAPI TL;DR-re vonatkozott, NEM a heti/havi összegzőre. (A heti riport a vezetői összefoglalóban őszintén jelzi, ha csendes hét volt.) MEGJEGYZÉS: ha a USER a heti riportnál is a „csendes hét → nincs riport" viselkedést akarja, az egy `van_heti` flag + frontend-elhagyás — EZ A SPEC NEM tartalmazza (a heti a rendszeres összegző). *(Ruling: a heti MINDIG generál; a csendes hetet a szöveg jelzi.)*

## 7. Hatókörön KÍVÜL
- A napi/havi elemzés (séma/prompt/fül) VÁLTOZATLAN.
- A backend VALÓS-szám-számítás (regresszió/lánc) VÁLTOZATLAN — a heti_korpusz csak OLVAS és aggregál.
- Interaktív térkép a heti fülön NEM (a havi Leaflet-térképek nem kerülnek át). A heti elsősorban narratív/strukturált + EGY determinista divergáló sávdiagram (§2). Több diagram/térkép jövőbeli bővítés.

## 8. Tesztelés (TDD)
- **`tests/test_heti_ertekeles.py`**: `heti_korpusz` determinista aggregálása (28 kulcsszó irány/illeszkedés + `elteres_szokasostol` a `mai_reziduum−reziduum_szokasos`-ból, `None` ha hiányzik; felkapott Mon-Sun `napok_szama`, YT heti; befőttes napfájlok/regresszió tmp_path-ban); a `_valasz_sema` a 6 részt tartalmazza a megadott alakkal; `grounding_validal` kiszűri a nem-korpuszbeli hivatkozott szót; `heti_generalas` mock SDK-val (korpusz→elemez→meta→írás); `heti_index_ir`.
- **`tests/test_heti_orzo.py`**: hétfő igaz/hamis (más napokon skip); az előző hét hétfőjének helyes számítása; idempotencia (mai `keszult` → skip; korábbi → generál); hajnali él; CLI.
- **`tests/test_heti_belepo.py`** + **`tests/test_heti_workflow.py`**: a `heti.py` (mock), a `heti.yml` (yaml: trigger a „Reggeli felkapott-gyűjtés"-re, ANTHROPIC_API_KEY, commit csak `docs/data/heti`, őr a pip install előtt).
- **`e2e/heti.spec.js`**: a 6 rész renderelése `van`/`nincs` adaton; a hét-választó (korábbi hét betöltése); a 2. rész divergáló sávdiagramja (erősödő pozitív / gyengülő negatív, legenda); fail-soft; a nav 6. füle.
- **`tests/test_pages.py` / `e2e/menu.spec.js`**: a nav 6 fület tartalmaz, a „Heti értékelés" link minden oldalon.

## 9. Global Constraints
- NULLA új Python-dependency (`calendar`/`datetime`/`json` stdlib; az aggregálás numpy nélkül). A frontend a meglévő mintákból (nincs új vendor).
- Grounding: VALÓS számok, ok csak hír esetén, nincs kitalálás. Irreplaceable adat READ-ONLY; a heti írás atomi.
- `git add` NÉVRE; `ATADAS-2026-08-18.txt` SOSEM staged; push külön kapuzott kör USER-jóváhagyással. SOROS suite (pytest + Playwright) zöld.
- A workflow a meglévő `ANTHROPIC_API_KEY` secretet használja; a commit CSAK `docs/data/heti`-t érinti. NINCS argless `datetime.now()` a modul-logikában.
- MAX_TOKENS: a heti kimenet nagy (6 rész + 2-3 mély elemzés) → a `heti_elemez` MAX_TOKENS-e a havi 64000-hez igazodik (streaming kötelező); nagy hétnél emelés — ÉLES-figyelés.
- A nav bővítése 5→6 fül MINDEN HTML-oldalon (konzisztens sorrend).
