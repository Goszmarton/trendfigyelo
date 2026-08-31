# Esti AI-elemzés: külön reggeli / esti / teljes-napi felkapott bekezdés — tervdokumentum (spec)

**Dátum:** 2026-08-31
**Repó:** Goszmarton/trendfigyelo (publikus)
**Állapot:** jóváhagyott terv (brainstorming lezárva), implementáció előtt
**Érintett rétegek:** `trendfigyelo/elemzo.py` (payload/prompt/séma/artefakt), `docs/js/elemzes.js` (render)
**Előzmény:** [[reggeli-esti-felkapott]] — a napi felkapott mostantól szegmentált (`napok/<nap>.json` `{reggel,este}`); ez a kör az esti AI-elemzést bővíti, hogy külön elemezze a reggeli és az esti pillanatképet.

## 1. Cél

Az esti AI-elemzés (napi `elemzes.yml`, az esti `napi.yml` után láncolva) a felkapott (Google napi trend-keresések) részt **egy pillanatképből, egy „napi" prózában** elemzi. A cél: a felkapott elemzés **négy** próza-szekcióra bomlik:
1. **Reggeli** (9:00 pillanatkép — mi pörög reggel),
2. **Esti** (21:00 pillanatkép — mi pörög este),
3. **Teljes nap (a nap íve)** — mi lett estére ÚJ (reggel még nem volt), mi HALVÁNYULT el, mi TARTOTT KI egész nap; a gép egy valós **reggel↔este diffet** is kap ehhez,
4. **Heti összesítés** — a több napon vissza-visszatérő szavak (a MOSTANI viselkedés, változatlanul).

A kulcsszó- és a YouTube-elemzés-rész **bájt-azonos** marad. A determinisztikus helyesség elsődleges: minden SZÁM/lista a Python-kódból jön, az AI CSAK a prózát írja.

## 2. Jelenlegi állapot (feltárás, 2026-08-31)

- **`elemzo.futtat`** (elemzo.py:381–410): felépíti az `adatok` dictet, `epit_payload`-dal payloadot gyárt, `elemez`-zel hívja a Claude Opus-t (`MODELL="claude-opus-4-8"`, json_schema output), `valasz_to_artefakt`-tal artefaktot épít, kiírja `elemzesek/<nap>.json` + `elemzes.json`. Fail-soft (kivétel → `return 2`, régi fájl marad).
- **Felkapott payload** — `_felkapott(legfrissebb, napok_trendek)` (182–204) → `{top, het}`:
  - `top`: a mai trend-lista `legfrissebb.top_trendek`-ből (EGY pillanatkép; mezők: `kifejezes, volumen, novekedes_pct, temak, hirek`).
  - `het`: számolt heti aggregátum `{napok, visszateroek:[{kifejezes, napok_szama}]}` a `_utolso_napok_trendek` (350–360, utolsó ≤7 nap, szegmensenként EGY — `este||reggel`) alapján.
- **`nap_diff`** (207–231) → `payload["valtozas"]` a NAP-over-nap diffel (`felkapott_uj/eltunt`, ma vs tegnapi archivált) — ez KÜLÖN a „Mi változott ma?" szekcióé, NEM az intra-napi ív.
- **Séma** `_valasz_sema` felkapott blokk (267–269): `{napi, het}`, mind próza (`_szekcio_sema` = `{szoveg}`). (A `kulcsszavak`/`youtube` blokk 3-3 prózás: `napi, teljes_kep, het`.)
- **Prompt** `RENDSZER_PROMPT` (21–51): nincs felkapott-specifikus szekció; általános szabályok (számokból, folyó próza, hír-kitalálás tilos stb.). A napi/heti bontást KIZÁRÓLAG a séma kényszeríti.
- **Artefakt** `valasz_to_artefakt` felkapott (325–330): `{top (valós), napi (AI), het (AI), het_valos (valós)}`.
- **Frontend** `elemzes.js` `rajzol` (119–121): a Google-szegmensen belül 2 `<h3>` szekció — „Felkapott — napi" (`art.felkapott.napi`) + „Felkapott — heti összesítés" (`art.felkapott.het`), a `szekcio_elem(cim, szekcio)` (15–29) `\n\n` mentén bekezdésekre bont. A nyers csempéket 2026-08-23-án szándékosan elhagytuk.
- **Időzítés** `elemzes.yml`: `workflow_run` a **„Napi trendgyűjtés"** (`napi.yml`) sikeres futása után + `workflow_dispatch`. A `reggeli.yml` MÁS nevű workflow → NEM indít elemzést. **Ez helyes, nem változik.**

## 3. Adatmodell / payload

- **ÚJ `_ma_szegmensek(docs_data, nap)`** — a `napok/<nap>.json`-ból (`json_export._nap_szegmensek`-kel) visszaadja a mai nap MINDKÉT szegmensének trend-listáját: `{"reggel": [...], "este": [...]}` (teljes mezőkkel: `kifejezes, volumen, novekedes_pct, temak, hirek`). Hiányzó szegmens → nincs kulcs (üres). Az esti elemzés-futáskor MINDKÉT szegmens megvan (a 9:00 + 21:00 futás után).
- **ÚJ reggel↔este diff** — a `kifejezes`-halmazokon: `uj_estere` (este-ben van, reggel-ben nincs), `eltunt_estere` (reggel-ben van, este-ben nincs), `megmaradt` (mindkettőben). Ez a „teljes nap / ív" bekezdés jele.
- **`_felkapott` bővül** (vagy új `_felkapott_szegmentalt`): a `legfrissebb.top_trendek` helyett/mellett a `_ma_szegmensek`-ből épít; visszaad `{reggel_top, este_top, reggel_este_diff, het}`. A `het` (heti aggregátum) VÁLTOZATLAN (`_utolso_napok_trendek`-ből). Az `este_top` ≡ `legfrissebb.top_trendek` (ugyanaz a pillanatkép) — a `legfrissebb` marad fallbacknek, ha a napfájl hiányos.
- **`nap_diff` VÁLTOZATLAN** (a nap-over-nap „Mi változott ma?"-hoz).
- **`epit_payload`** `payload["felkapott"]` az új alakot kapja; a `kulcsszavak`/`valtozas`/`kulcsszo_het`/`youtube` VÁLTOZATLAN.

## 4. Séma (`_valasz_sema`, felkapott blokk)

A `{napi, het}` helyett:
```python
"felkapott": {"type": "object", "additionalProperties": False,
              "required": ["reggel", "este", "teljes_nap", "het"],
              "properties": {"reggel": sz, "este": sz, "teljes_nap": sz, "het": sz}},
```
(mind `_szekcio_sema` = `{szoveg}`). A `kulcsszavak`/`youtube` blokk VÁLTOZATLAN.

## 5. Prompt (`RENDSZER_PROMPT`)

Új felkapott-keret (a meglévő szabály-stílusban, folyó próza, számokból):
- **reggel**: mit mutat a reggeli (9:00) pillanatkép — mi pörög, milyen témák.
- **este**: mit mutat az esti (21:00) pillanatkép.
- **teljes_nap (a nap íve)**: a reggel→este elmozdulás — mi lett estére ÚJ (`uj_estere`), mi HALVÁNYULT (`eltunt_estere`), mi TARTOTT KI (`megmaradt`); a nap dinamikája, nem a két lista újramondása.
- **het**: a több napon visszatérő szavak (mint eddig).
- **Fail-soft a promptban:** ha egy szegmens listája ÜRES (aznap nem volt az a gyűjtés), írj egy rövid tényszerű mondatot róla, NE találj ki adatot; ha nincs reggeli alap, a „nap íve" mondja ki, hogy az ív nem rajzolható. Számot/hírt továbbra sem talál ki.

## 6. Artefakt (`valasz_to_artefakt`)

```python
"felkapott": {
    "reggel_top": payload["felkapott"]["reggel_top"],       # valós lista
    "este_top": payload["felkapott"]["este_top"],           # valós lista
    "reggel_este_diff": payload["felkapott"]["reggel_este_diff"],  # valós
    "reggel": ai_valasz["felkapott"]["reggel"],             # AI próza
    "este": ai_valasz["felkapott"]["este"],                 # AI próza
    "teljes_nap": ai_valasz["felkapott"]["teljes_nap"],     # AI próza
    "het": ai_valasz["felkapott"]["het"],                   # AI próza
    "het_valos": payload["felkapott"]["het"],               # valós (heti aggregátum)
},
```
**Fail-soft (DETERMINISZTIKUS felülírás, az üres-nap `valtozas`-mintára):** a payload `van_reggel`/`van_este` jelzőt visz (a `_ma_szegmensek` alapján). A séma mindig mind a 4 prózát kéri (az AI mindig visszaad 4 mezőt), DE a `valasz_to_artefakt` a HIÁNYZÓ szegmens bekezdéseit **Python-canned tényszöveggel felülírja** (az AI prózáját ELDOBJA arra a mezőre) — így nincs hallucináció egy nem-létező pillanatképről:
- `van_reggel=False` → `felkapott.reggel` és `felkapott.teljes_nap` = fix magyar jelzés (pl. „Ma nem volt reggeli gyűjtés, ezért a reggeli kép és a nap íve nem elemezhető."). `reggel_top` üres lista.
- `van_este=False` (szimmetrikus, ritka) → `felkapott.este` (+ `teljes_nap`) fix jelzés.
- Mindkét szegmens megvan (a normál eset előre) → mind a 4 valós AI-próza.

## 7. Frontend (`elemzes.js`)

- A `rajzol` felkapott-blokkja (119–121) a Google-szegmensen belül **4 `<h3>` szekció**:
  „Felkapott — reggeli (9:00)" (`art.felkapott.reggel`) · „Felkapott — esti (21:00)" (`art.felkapott.este`) · „Felkapott — a nap íve" (`art.felkapott.teljes_nap`) · „Felkapott — heti összesítés" (`art.felkapott.het`), a `szekcio_elem`-mel.
- **Visszafelé kompatibilitás (KRITIKUS):** a régi archivált `elemzesek/<nap>.json` felkapott-ja `{napi, het}` alakú. A render detektál: ha `art.felkapott.reggel` VAN → új, 4-szekciós render; különben ha `art.felkapott.napi` (régi) → a MOSTANI egy-szekciós render (`Felkapott — napi` + `Felkapott — heti`). Így a régi elemzések is megjelennek. Üres/hiányzó próza-szekció → kihagyva (nem üres `<h3>`).
- A „Mi változott ma?" (nap-over-nap) render VÁLTOZATLAN.

## 8. Időzítés (NEM változik)

Az elemzés az esti `napi.yml` sikere után fut (`workflow_run`), amikor a `napok/<ma>.json`-ban MINDKÉT szegmens megvan. A `reggeli.yml` NEM indít elemzést (más workflow-név). Csak megerősítve; nem nyúlunk hozzá.

## 9. Fail-soft / degradáció

- **Csak esti szegmens** (régi nap visszamenőleg, vagy kimaradt reggeli): `van_reggel=False` → a `valasz_to_artefakt` a `reggel` és `teljes_nap` bekezdést DETERMINISZTIKUS canned jelzéssel írja felül (nem az AI prózájával, §6); az „esti" + „heti" normál AI-próza.
- **Csak reggeli szegmens** (szimmetrikus, ritka): `van_este=False` → fordítva.
- **Egyik sincs** (nem várt — a `legfrissebb`-ből az este mindig van valami): a felkapott-rész a `legfrissebb`-re esik vissza, mint eddig.
- A fail-soft NEM dobhatja el az egész elemzést (a meglévő `try/except` a `elemez` körül marad, `return 2` a régi fájllal).

## 10. Tesztelés (SDD, [[working-style-gates]])

SOROS suite: `.venv/bin/python -m pytest -p no:xdist -q` + `npx playwright test --workers=1`. TDD valódi RED→GREEN, MUTÁCIÓ=1.
- **Backend:** `_ma_szegmensek` (mindkét szegmens / csak-este / régi-lapos); reggel↔este diff (uj/eltunt/megmaradt); `_felkapott` új alak; `epit_payload` felkapott-kulcs; a séma `{reggel,este,teljes_nap,het}` illeszkedik; `valasz_to_artefakt` új szekciók + fail-soft (csak-este / csak-reggel); a Google/YouTube/kulcsszó-út érintetlensége.
- **Frontend (Playwright):** új artefakt (`felkapott.reggel/este/teljes_nap/het`) → 4 szekció; régi artefakt (`felkapott.napi/het`) → a mostani 1(napi)+1(heti) szekció (visszafelé kompat); hiányzó szegmens-szekció kihagyva.
- **Leltár-invariáns** fizikailag mérve (az implementáció méri).

## 11. Kockázatok / nyitott

- **Séma-migráció:** a régi artefaktok `{napi,het}`-ek; a frontend detektálja az alakot (7. §). A backend az ÚJ alakot termeli; a régi archívumot NEM írjuk át.
- **Prompt-minőség:** a négy bekezdés hangneme/hossza az első éles Opus-kimenetek után finomítható (fast-follow, nem ma).
- **Adat-valóság:** az első szegmentált napfájl az első éles reggeli+esti páros után áll elő; addig az elemzés a csak-este ágon degradál (helyes).

## 12. Nem-cél (YAGNI)

- Nincs nyers felkapott-csempe visszahozva (2026-08-23-i döntés áll).
- A kulcsszó- és YouTube-elemzés VÁLTOZATLAN.
- Nincs új workflow/időzítés; az elemzés esti marad.
- Nincs történelmi elemzés-újraszámolás (a régi `{napi,het}` artefaktok maradnak, a frontend visszafelé kompatibilis).
