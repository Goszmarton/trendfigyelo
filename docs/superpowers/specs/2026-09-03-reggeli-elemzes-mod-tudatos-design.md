# Terv: mód-tudatos AI-elemzés (reggeli scoped + esti teljes) + flash-bug javítás

**Dátum:** 2026-09-03
**Állapot:** jóváhagyásra vár
**Kiváltó igény:** a felhasználó szerint „káosz" van az elemzésnél — reggel megjelenik egy új nap, de „flash amit elemez". A cél: reggel = csak az új/reggeli felkapott szavak elemzése („minden máshoz azt adja, h majd az esti futáskor frissül"), este = mindent összetesz.

## Motiváció — két összefonódó probléma

**A felderítés cáfolta a kiindulást:** jelenleg NINCS reggeli elemzés. Az AI-elemzés kizárólag az esti futás után generálódik (`elemzes.yml` a „Napi trendgyűjtés" workflow befejezésére láncolódik). A „flash/káosz" valójában egy dátum-hiba + újraindítási bug:

1. **Dátum-kulcs hiba:** `elemzo.main` a napot a nyers órajelből számolja (`bp_idobelyeg(most_utc())[:10]`, elemzo.py:485), a gyűjtés `esti_nap` hajnali-visszagörgetése NÉLKÜL. Az esti `napi.yml` 23:00 UTC backup cronja budapesti idő szerint éjfél után fut, „success"-szel zár → újraindítja az elemzést → az a KÖVETKEZŐ napra készít elemzést, aminek még nincs szegmens-adata → üres/„nem volt gyűjtés" fallback kerül a `elemzes.json`-ba (amit az oldal mutat) és az `elemzesek/index.json`-ba. (Bizonyíték: `elemzesek/2026-09-03.json` `frissitve 2026-09-03T00:58Z` = 02:58 budapesti, üres szegmensekkel.)
2. **Újraindítási flash:** `elemzes.yml` MINDEN őrzött backup-futás „success"-ére újratüzel (`if:` csak conclusion-t néz), és a modell nem-determinisztikus (`thinking=adaptive`) → ugyanaznap felülírja a 21:00-ás szöveget.

A megoldás egyszerre javítja a bugot ÉS bevezeti a mód-tudatos (reggel/este) elemzést.

## A viselkedés

| Futás | Nap-kulcs | Mit elemez az AI | Deferrált szekciók (helyőrző) |
|---|---|---|---|
| **reggel** (~09:00) | budapesti naptári nap | CSAK a felkapott REGGELI pillanatkép (1 bekezdés) | valtozas, kulcsszavak (napi/teljes_kep/het próza), felkapott este/nap íve/het, YouTube (kulcs kimarad) |
| **este** (~21:00) | `seged.esti_nap` (logikai esti nap) | a MOSTANI teljes elemzés (változatlan) | — |

- A deferrált **próza** szekciók determinisztikus helyőrzőt kapnak: **„Ez a rész az esti futáskor (21:00) frissül."** (a meglévő `van_reggel`/`van_este` fallback-minta kiterjesztése).
- A **VALÓS numerikus** rétegek (kulcsszó-csempék `szamok`, felkapott tops, `het_valos`) reggel is a jelenlegi on-disk értékeket mutatják — ezek tények, nem az elemzés; csak az AI-próza deferrálódik. (Ez a felhasználó „minden máshoz azt adja, h este frissül" kérésének őszinte olvasata: a szám tény, a narratíva jön este.)
- A YouTube-blokk reggel teljesen kimarad (a `youtube` kulcs hiányzik → a frontend eleve fail-soft rá, elemzes.js:132).

## Architektúra

### 1. Flash-bug: logikai nap + idempotencia-őr

**Új modul: `trendfigyelo/elemzes_orzo.py`** (a `futas_orzo.py` mintájára, hogy `elemzo.py` fókuszált maradjon):

```
elemzes_nap(mode, most) -> str            # reggel → BP naptári nap; este → seged.esti_nap(most)
elemzes_mar_kesz(docs_data, nap, mode) -> bool
main(argv)                                 # `--mode reggel|este docs/data` → "true"/"false"
```

- `elemzes_nap`: reggel = `most.astimezone(seged.BUDAPEST).date().isoformat()`; este = `seged.esti_nap(most)`. Pontosan a `futas_orzo.main` per-szegmens nap-logikája → az elemzés napja egyezik a gyűjtés napjával, nincs következő-napi elcsúszás.
- `elemzes_mar_kesz`: beolvassa `elemzesek/<nap>.json`-t. Ha nincs → False. Ha van, a benne tárolt `mode` mező alapján:
  - **reggel:** True, ha a mai fájl BÁRMILYEN móddal létezik (a reggeli idempotens, és sosem ír felül egy esti teljeset).
  - **este:** True CSAK ha a létező `mode == "este"` (teljes már kész ma). Ha a létező `reggel`, az este LEFUT (scoped → teljes upgrade).
  - Régi (mode nélküli) archívum → `mode` = None → este: `None == "este"` False → lefut (regenerál teljesként); reggel csak mára fut, ott nincs régi archív.
- Az éjfél-utáni esti backup az `esti_nap` miatt az ELŐZŐ napra néz → ott már `mode==este` → skip. **Nincs többé következő-napi üres flash.** A reggeli backup-újraindítás → ma már kész → skip. **Nincs többé ugyanaznapi próza-flash.**

### 2. Mód-tudatos generátor (`elemzo.py`)

- **`main` (483-487):** olvassa `ELEMZES_MODE` env-et (default `"este"` — workflow_dispatch / back-compat). Nap = `ELEMZES_NAP` override VAGY `elemzes_orzo.elemzes_nap(mode, most_utc())`. `futtat(docs_data, nap, mode=mode)`.
- **`futtat` (450):** új `mode="este"` param, továbbadva `epit_payload`-nak és `valasz_to_artefakt`-nak; `elemez` a mód-séma szerint hív.
- **`epit_payload` (285):** új `mode="este"` param. reggel módban a `youtube` blokk KIMARAD (már most is feltételes).
- **`_valasz_sema` (312):** új `mode` param. reggel → szűkített séma, csak `{felkapott: {required:[reggel], properties:{reggel: sz}}}`, top-level required `["felkapott"]`. este → a mostani teljes séma. Így az AI reggel CSAK a reggeli bekezdést írja (nem fizetünk eldobott, halandzsa szekciókért).
- **`RENDSZER_PROMPT` → `_rendszer_prompt(mode)` (21):** reggel → rövid, a reggeli pillanatképre fókuszáló prompt (nem a 4-bekezdéses szabály); este → a mostani prompt változatlanul.
- **`valasz_to_artefakt` (360):** új `mode="este"` param + KÜLÖN reggeli ág. Reggel: a VALÓS rétegeket a szokásos módon másolja (szamok, tops, het_valos), `felkapott.reggel`-t az AI-ból, minden más PRÓZA szekciót a `"Ez a rész az esti futáskor (21:00) frissül."` helyőrzővel, `youtube` kulcs nélkül. Este: a mostani ág. MINDKÉT ág beírja: `art["mode"] = mode` (az őr és a jövőbeli konzumensek számára).

A reggeli ág NEM olvas `ai_valasz["kulcsszavak"]`/`["youtube"]`/`["felkapott"]["este"]` stb. mezőket (a szűkített séma miatt nem is léteznek) — a helyőrzők determinisztikusak.

### 3. Trigger (`.github/workflows/elemzes.yml`)

- `on.workflow_run.workflows`: `["Napi trendgyűjtés", "Reggeli felkapott-gyűjtés"]` (mindkét gyűjtő-workflow).
- Új **mód-levezető** lépés: `github.event.workflow_run.name`-ből → `MODE` (`"Reggeli felkapott-gyűjtés"` → `reggel`, egyébként `este`; `workflow_dispatch` → default `este`). `echo "mode=$MODE" >> $GITHUB_OUTPUT`.
- Új **őr-lépés** (a gyűjtés mintájára): `skip=$(python -m trendfigyelo.elemzes_orzo --mode $MODE docs/data)`; a futtatás + commit lépések `if: skip != 'true'`.
- Az „Elemzés futtatása" lépés env-je bővül: `ELEMZES_MODE: ${{ steps.mode.outputs.mode }}`.
- `concurrency: group: napi-futtatas` változatlan (ne fusson a gyűjtéssel párban).

### 4. Frontend (`docs/js/elemzes.js`)

**Nincs kód-változás** — a helyőrzők sima `{szoveg}` objektumként a meglévő `szekcio_elem`-mel renderelődnek; minden PRÓZA-kulcs jelen van (a felkapott a 4-bekezdéses ágon marad, mert `art.felkapott.reggel` truthy), a `youtube` kulcs hiánya fail-soft. A tervhez tartozik egy e2e/DOM-ellenőrzés, hogy a reggeli artefakt helyesen renderel (helyőrző-próza + reggeli AI-bekezdés + nincs YouTube-blokk).

## Adatfolyam

```
reggeli.yml (mode=reggel) → napok/<nap>.json {reggel} commit
  → workflow_run "Reggeli felkapott-gyűjtés" completed → elemzes.yml
     mode=reggel; elemzes_orzo őr: ma kész? nem → elemzo (mode=reggel)
       AI: csak felkapott.reggel; többi próza = "…frissül este"; youtube kihagyva; art.mode="reggel"
       → elemzes.json + elemzesek/<nap>.json (mode=reggel) commit

napi.yml (mode=este) → napok/<nap>.json {este} commit
  → workflow_run "Napi trendgyűjtés" completed → elemzes.yml
     mode=este; őr: ma kész teljes? nem (reggel van) → elemzo (mode=este)
       teljes elemzés (változatlan); art.mode="este" → felülírja a reggeli scoped-ot

éjfél-utáni esti backup → esti_nap = ELŐZŐ nap → őr: ott mode==este → skip (nincs flash)
```

## Hibakezelés / élek

- **AI-hiba (fail-soft):** változatlan — `elemez` kivételkor a régi fájl marad (elemzo.py:470-472). Reggel is: ha az AI bukik, a reggeli scoped nem íródik, a tegnapi esti marad, míg az esti újra elkészíti. Nincs adatvesztés.
- **Olvashatatlan `elemzesek/<nap>.json` az őrben:** `elemzes_mar_kesz` → False (fail-open: inkább fut, mint tévesen kihagy) — a `szegmens_mar_gyujtottunk_ma` mintája.
- **`workflow_dispatch` kézi teszt:** `workflow_run` mezők üresek → default `mode=este`, `ELEMZES_NAP` override továbbra is működik.
- **Régi archívumok (mode nélkül):** az őr és a frontend is tolerálja (`mode` hiánya → None); a frontend nem olvassa a `mode`-ot.
- **Pótolhatatlan adat:** az elemzés csak OLVAS gyűjtés-adatot; csak a saját `elemzes.json`/`elemzesek/*` fájljait írja (változatlan).

## Tesztelés

- **`tests/test_elemzes_orzo.py` (ÚJ):** `elemzes_nap(reggel/este, most)` a helyes logikai napot adja (éjfél-utáni este → előző nap); `elemzes_mar_kesz` mátrix: nincs fájl→False; reggel+létező-reggel→True; reggel+létező-este→True; este+létező-reggel→False (upgrade); este+létező-este→True; mode nélküli archív→este False; olvashatatlan→False. CLI true/false.
- **`tests/test_elemzo.py` (bővítés):** `epit_payload(mode="reggel")` kihagyja a youtube-ot; `_valasz_sema("reggel")` csak `felkapott.reggel`-t követel; `_rendszer_prompt("reggel")` a reggeli pillanatképre szól; `valasz_to_artefakt(mode="reggel", ...)` a VALÓS rétegeket másolja, `felkapott.reggel`-t az AI-ból, a többi prózát a determinisztikus „…frissül este" helyőrzővel, `youtube` kulcs nélkül, `art["mode"]=="reggel"`; a `KamuKliens` szűkített választ ad reggel módban. `main` az `ELEMZES_MODE`-ot átvezeti. Az esti (default) ág tesztjei változatlanul zöldek (regresszió-védelem).
- **e2e/DOM (`e2e/elemzes.spec.js` bővítés):** reggeli artefakt-fixture → a reggeli AI-bekezdés látszik, a deferrált szekciók a helyőrző-prózát mutatják, nincs YouTube-blokk; esti artefakt változatlanul teljes.

## Amit NEM csinálunk (YAGNI)

- Reggel NINCS nap-diff / „mi változott" (a user döntése: csak a reggeli felkapott).
- Reggel az AI NEM kap teljes sémát „eldobandó" szekciókkal (szűkített séma → olcsóbb, tisztább).
- Nincs frontend-kód-változás (a helyőrzők a meglévő renderrel jelennek meg).
- Nincs külön elemzés-fájl reggelre — ugyanaz a `elemzes.json` + `elemzesek/<nap>.json`, az esti felülírja a reggelit (szándékos: scoped→teljes).
