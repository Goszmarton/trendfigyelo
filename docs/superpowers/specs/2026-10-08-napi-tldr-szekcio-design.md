# Napi riport — TL;DR („Lényeg") szekció az elején — design

**Állapot:** jóváhagyott terv (chat), implementáció előtt.
**Dátum:** 2026-10-08.
**Előzmény:** [[elemzes-ful-fast-follow]] (napi AI-elemzés: VALÓS számok Python + Claude narratíva, grounded-only „miért", 4-bekezdéses felkapott, predikció-szekció), `trendfigyelo/elemzo.py` séma+prompt+payload, `docs/js/elemzes.js` render.

## 1. Cél

A napi riport (esti, teljes AI-elemzés) LEGELEJÉRE egy kiemelt **„Lényeg (TL;DR)"** szekció, amely gyors, adatokkal alátámasztott vezetői összefoglalót ad. **USER-döntés: CSAK az esti (teljes) futásban** (a reggeli kép részleges → ott nincs TL;DR). A reggeli séma/prompt VÁLTOZATLAN.

## 2. A TL;DR tartalma (strukturált, 5 rész)

1. **Fő változások (≤3):** a 3 legfontosabb, **adatokkal alátámasztott** változás, egy-egy mondatban (szám/irány a lementett adatból — a `valtozas`-diff, a kulcsszó-mozgások, a felkapott nap íve).
2. **Kiemelt ügyek (≤5):** mi történik a keresésekben, **mihez képest** (a szó saját szokásos szintje / az előző nap), **mióta tart** (a felkapott heti/visszatérő adatból, ill. a kulcsszó-trend ablakból). Egy-egy tömör mondat.
3. **Visszatérő témák:** a több napon vissza-visszatérő témák rövid összefoglalója (a felkapott `het.visszateroek` adatból).
4. **Intenzívebb keresésbe veendő ügyek:** mely FELKAPOTT ügyeket/témákat lenne érdemes felvenni a KÖVETETT kulcsszavak közé (grounded javaslat a mai/visszatérő felkapottakból; NEM a meglévő 28 követett szó). Óvatos, indokolt.
5. **Információhiány / vizsgálandó kérdés:** mit nem tudunk az adatból (pl. „felkapott, de nem érkezett hír"), milyen kérdést érdemes külön megnézni — a jelzés nyers értelmezési pereme.

## 3. „Ha nincs változás, ne generáljon semmit"

Ha a napból **nincs érdemi, kiemelésre méltó változás** (csendes nap: a felkapottak a szokásos zaj, a követett szavak a saját szintjükön, nincs visszatérő kiugrás), az AI a TL;DR-t **ÜRESEN hagyja** (`van_tldr: false`, a többi mező üres), és a frontend a szekciót **NEM rendereli**. „Ne generáljon semmit magától" = nincs kitalált/erőltetett összefoglaló csendes napon. A döntést az AI hozza a grounded adatból; a riport TÖBBI (narratíva) szekciója változatlanul generálódik.

## 4. Séma (`elemzo._valasz_sema`, csak `mode="este"`)

ÚJ `tldr` mező (a többi szekció VÁLTOZATLAN):
```
tldr: {                      # kötelező a válaszban (este), de üres is lehet
  van_tldr: boolean,         # false → csendes nap, a frontend nem rendereli
  fo_valtozasok: [string],   # ≤3 (maxItems 3)
  kiemelt_ugyek: [string],   # ≤5 (maxItems 5)
  visszatero_temak: string,  # prózai (üres, ha nincs)
  intenzivebb_keresesbe: string,
  informaciohiany: string,
}
```
`additionalProperties: false`, minden mező `required` (üres string/`[]`/`false` megengedett). A `tldr` a `mode="este"` séma `required`-jéhez adódik; a reggeli séma érintetlen.

## 5. Prompt (RENDSZER_PROMPT, csak este)

ÚJ szabály a TL;DR-ről: az esti elemzés ELSŐ része egy TL;DR; a fenti 5 rész; a számok a lementett adatból (grounded, az ok csak hír esetén, nincs kitalálás); a „mihez képest/mióta" a szokásos-szint + heti/visszatérő adatból; az „intenzívebb keresés" a mai/visszatérő FELKAPOTTAKBÓL (nem a 28 követettből), óvatos indoklással; az „információhiány" a jelzés nyers értelmezési pereme. **Csendes napon `van_tldr: false` + üres mezők** (nincs erőltetett összefoglaló). A rövid „–" gondolatjel-szabály a TL;DR-re is.

## 6. Payload (`elemzo` payload-építés)

A meglévő adat ELÉG: `valtozas` (diff: mi változott a tegnapihoz), `kulcsszavak` számok (mai-vs-szokásos), `felkapott` reggel/este/teljes_nap/het (a `het.visszateroek` a visszatérőkhöz), `predikcio` közeltáv. Nincs kötelező új adat; ha a „mióta tart"-hoz hasznos, a payloadhoz adható a felkapott szavak `napok_szama` (már a `het.visszateroek`-ben van). A payload a TL;DR-hez NEM kap új backend-számítást (a Python a VALÓS számokat már szállítja).

## 7. Frontend (`docs/js/elemzes.js`)

A TL;DR szekció a riport LEGELEJÉN (az első szegmens-cím ELŐTT), kiemelt dobozban (az app kék akcentusa), CSAK ha `tldr && tldr.van_tldr`. Tartalom: cím „Lényeg"; „Fő változások" (a ≤3, rövid listaként vagy mondatonként); „Kiemelt ügyek" (≤5); „Visszatérő témák"; „Érdemes figyelni (intenzívebb keresés)"; „Információhiány / vizsgálandó". Üres részt (üres string / `[]`) kihagy. A TL;DR strukturált (NEM a folyó-próza szabály alá esik — ez egy szándékosan tagolt összefoglaló). Fail-soft: hiányzó/rossz `tldr` → nincs szekció (a riport többi része változatlan). A reggeli riportban nincs `tldr` → nincs szekció.

## 8. Tesztelés (TDD)

- **`tests/test_elemzo.py`**: a `_valasz_sema("este")` tartalmazza a `tldr`-t a megadott mezőkkel (van_tldr bool, fo_valtozasok/kiemelt_ugyek array maxItems 3/5, 3 string); a `reggel` séma NEM tartalmazza; a RENDSZER_PROMPT tartalmazza a TL;DR-szabályt + a „csendes nap → van_tldr false" elvet; az `elemez` a mock-válasz `tldr`-jét átvezeti az eredménybe.
- **`e2e/elemzes.spec.js`**: `van_tldr: true` → a „Lényeg" doboz a riport ELEJÉN rendereli a részeket; `van_tldr: false` → NINCS „Lényeg" doboz; a reggeli (mode reggel) riportban nincs TL;DR; üres rész-mező kimarad.

## 9. Hatókörön KÍVÜL
- A reggeli elemzés (séma/prompt/render) VÁLTOZATLAN.
- A backend VALÓS-szám-számítás (Python) VÁLTOZATLAN — nincs új metrika.
- A YouTube/predikció/narratíva szekciók VÁLTOZATLANOK.

## 10. Global Constraints
- NULLA új Python-dependency. A séma/prompt/payload az `elemzo.py`-ban; a render az `elemzes.js`-ben.
- Grounding: VALÓS számok, ok csak hír esetén, nincs kitalálás; a TL;DR a meglévő grounded adatból.
- MAX_TOKENS: a `tldr` kismértékben növeli a kimenetet — ha a szekciók rövidülnek/csonkolnak, a `MAX_TOKENS`-t emelni kell (jelenleg 32000; lásd [[elemzes-ful-fast-follow]] csonkolás-tanulság). ÉLES-figyelés az első esti futásnál.
- SOROS suite (pytest + Playwright) zöld. `git add` NÉVRE; push külön kapuzott kör USER-jóváhagyással.
- „Ne generáljon semmit" = csendes napon a TL;DR elmarad (nem placeholder).
