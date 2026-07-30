# Trendfigyelő — Phase 2.5 (kulcsszó-mérés helyreállítása) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A kulcsszó-ág átállítása a horgony-normalizálásról **szóló (kulcsszavankénti) lekérdezésre**, hogy minden szó a saját 0–100 tartományát kapja; a nyers órás sorozat verziókövetett mentése a későbbi láncoláshoz; és a mérésre-épülő döntések (kulcsszólista, kérésszám) élesben rögzítése — a `felkapott`/`idosor` ágak érintése nélkül.

**Architecture:** A meglévő `trendfigyelo/` csomag pontszerű, de a kulcsszó-ágon **mély** átírása. A `config.yaml` `kulcsszavak` szerkezete csoport→lista dictből **per-kulcsszó rekordok listájává** válik (`kifejezes`/`domen`/`tipus`), a `referenciaszo`/`referencia_min_atlag` eltűnik. A `kulcsszavak.gyujt` kötegelés+horgony helyett szavanként egy `interest_over_time([kif], "now 7-d")`-t hív, nyers órás értékkel, normalizálás nélkül. Egy új, verziókövetett `docs/data/kulcsszo_nyers.json` gördülő ablakban őrzi a nyers órás sorozatot a lekérdezés ablakhatáraival és a részleges-farok (`isPartial`) jelöléssel. A `felkapott`/`idosor` ág és az anti-block `kliens` **nem változik**; a `futtato` ágsorrendje `…→kulcsszo→idosor`-ra fordul (a jó `idosor`-adat block-napon az olcsóbb veszteség).

**Tech Stack:** Python 3.12, trendspy==0.1.6, PyYAML, pandas, pytest. Nincs build-lépés. Kézi Google Trends mérés (Task 1, 8) — nem a repó kódja.

## Global Constraints

Ezek MINDEN taskra vonatkoznak (Phase 1/2-ből öröklött + Phase 2.5-specifikus):

- **geo="HU" mindenhol**, **nyelv="hu"**, **egyetlen konfigforrás a `config.yaml`**; minden CSV-sor és JSON-bejegyzés tartalmaz `geo` mezőt (a kulcsszó-CSV-nél is).
- **Idő:** nyers adat UTC-ben (ISO, `timespec="seconds"`); fájlnevek és megjelenítendő időbélyegek budapesti idő (Europe/Budapest, `seged.BUDAPEST`).
- **CSV formátum:** `;` elválasztó, `utf-8-sig`. A `felkapott` 3 CSV-je (api/rss/hirek) és a `top_trend_idosor` CSV **változatlan**. A `kulcsszo_idosor` CSV oszlopai viszont változnak (horgony-mezők kiesnek, `csoport`→`domen`, `tipus` bejön) — ez a törés része (Task 7).
- **Kulcsszó-ablak változatlan:** `kulcsszo_idokeret: "now 7-d"` (órás felbontás). A `felkapott` `hours=24` és az `idosor` `now 1-d` **nem változik**.
- **Anti-block:** a `kliens.Kliens` (véletlenített késleltetés, 429-backoff, `AgFeladva`, hívásszámlálás) **egyetlen sora sem változik**. Napi egy futás; nincs rövid ciklusú tömeges retry; részleges siker is siker; teljes blokk → nem-nulla kilépési kód.
- **AgFeladva a looping ágakban:** a szóló kulcsszó-ciklus `AgFeladva`-t NEM nyelhet el `continue`-val — az egész ágat fel kell adni (a kivétel a `futtato`-hoz megy block-detektálásra). Egyéb (nem-429) hiba csak az adott szót/szemet hagyja ki.
- **Horgony végleg elvetve:** `időjárás` referenciaszó, `referencia_min_atlag`, `skalazo`, `normalizalt_ertek`, `referencia_*` mezők eltűnnek. Szóló lekérdezésnél a méret nem számít (spec 2.5).
- **Nincs élő Google-teszt** a unit tesztekben — mock/fixtúra. Az egyetlen éles mérés a Task 1 és Task 8 (kézi/`workflow_dispatch`).
- **Munkamódszer:** friss implementer + külön review-agent taskonként; TDD (RED→GREEN) a fejlesztő-taskokra; **a RED nem lehet vacuous** (lásd taskonként a RED-diszkriminátort); commit **review után**; no-commit protokoll (implementer nem commitol); záró ledger `.superpowers/sdd/progress.md`.
- **Task 1 és Task 8 NEM TDD** — mérés. Nincs RED/GREEN ciklus; eldobható mérő-script megengedett, **repóba kerülő kód és commit nem**; a kimenet verziókövetett jegyzőkönyv.
- **Verziófloorok (requirements.txt) változatlanok:** `trendspy==0.1.6`, `PyYAML>=6.0`, `pandas>=2.0`, `pytest>=8.0`.
- **Kód magyarul** (kommentek, változónevek, kimenetek).
- **Gyűjtés ≠ megjelenítés:** 13 szót gyűjteni és később hatot megjeleníteni legitim (spec 6.2). A vágás CSAK a Task 1 vagy Task 8 eredménye alapján indokolt.

**Teszt-futtatás:** a repó gyökeréből `.venv/bin/python -m pytest -q` a teljes suite; egy fájlra `.venv/bin/python -m pytest tests/test_X.py -v`.

**Spec:** `docs/superpowers/phase2_5/phase2_5-spec.md` — a task↔fejezet hivatkozások arra mutatnak.

---

## File Structure

| Fájl | Művelet | Felelősség | Task |
|---|---|---|---|
| `docs/superpowers/phase2_5/task1-meres.md` | Create | Szóló mérés jegyzőkönyve: **kulcsszavanként nyers számok** + a 6.1 küszöbök | 1 |
| `config.yaml` | Modify | `kulcsszavak` dict→lista (`kifejezes`/`domen`/`tipus`); `referenciaszo`+`referencia_min_atlag` törölve | 4 (tartalom: 2) |
| `trendfigyelo/config.py` | Modify | `Config` mezők, validáció, `osszes_kulcsszo()` → `KulcsszoTetel` rekordok; horgony-mezők ki | 4 |
| `trendfigyelo/kulcsszavak.py` | Rewrite | Szóló `interest_over_time([kif])`; kötegelés/horgony/normalizálás ki; nyers órás sorozat kinyerése ablakhatárral + `isPartial` | 4 (nyers: 6) |
| `trendfigyelo/json_export.py` | Modify | Kulcsszó-aggregátum nyers értékből, `csoport`→`domen`; töréspont-mező | 4 (töréspont: 7) |
| `trendfigyelo/nyers_kimenet.py` | Create | Nyers órás rekord **szerződés-validátora** (Task 3), majd a **gördülő-ablakú író** (Task 6) | 3, 6 |
| `docs/data/kulcsszo_nyers.json` | Create (futásidő) | Verziókövetett nyers órás sorozat, ablakhatárral + véglegesség-jelöléssel, gördülő retenció | 6 |
| `trendfigyelo/futtato.py` | Modify | Ágsorrend `…→kulcsszo→idosor` + `AGAK`; új kimenetek bekötése | 5 (kimenetek: 6,7) |
| `tests/test_kulcsszavak.py`, `tests/test_config.py`, `tests/test_json_export.py`, `tests/test_futtato.py`, `tests/test_nyers_kimenet.py` (new) | Modify/Create | A fenti változások tesztjei | 3–7 |

### Dekompozíciós döntés (a spec Task 2 vs Task 4 zöld-határa)

A `config.yaml` séma, a `config.py` betöltő és a `kulcsszavak.py`/`json_export.py` fogyasztók **egyetlen atomi kontraktus**: a `kulcsszavak.py` a `config.osszes_kulcsszo()`/`referenciaszo` interfészt fogyasztja, így külön nem maradhatnak zöldben. Ezért:

- **Task 2 = tartalmi döntés + jóváhagyási kapu** (spec: „tartalmi döntés, külön jóváhagyással"). Nem ír build-törő fájlt: véglegesíti a kulcsszólistát (a 13 szó a Task 1 rostája után), és a plan/ledger rögzíti a pontos `config.yaml`-tartalmat jóváhagyásra. **Nincs RED — ez döntés.**
- **Task 4 = az atomi kód-váltás:** a jóváhagyott `config.yaml` + `config.py` + `kulcsszavak.py` + `json_export.py` együtt, egyetlen zöld-határig. A suite csak a Task 4 végén áll vissza teljesen zöldbe.

Ez a spec task-számozását megtartja (1..9, a 8 = kérésszám-mérés), csak a `config.yaml` **fájlírását** a Task 2 tartalmi döntéséből a Task 4 atomi lépésébe helyezi.

---

## Task 1: Szóló mérés (MÉRÉS — NEM TDD)

**Files:**
- Create: `docs/superpowers/phase2_5/task1-meres.md`

**Cél:** A spec 2.2 tizenhárom szavát **szólóban**, `now 7-d` órás felbontásban megmérni, és a 6.1 objektív kritérium (különböző értékek száma; nullák aránya és eloszlása; szomszédos pontok különbsége) alapján eldönteni, melyik szó mérhető. A mérés a Task 2 tartalmi döntésének bemenete.

**Nincs RED/GREEN.** Eldobható mérő-script megengedett (pl. helyi `trendspy` hívások), de **repóba kerülő kód és commit nem** — az egyetlen artefakt a jegyzőkönyv.

- [ ] **1. JELÖLT küszöbök beírása a jegyzőkönyvbe — a mérés ELŐTT.** A 6.1 három kritériumához (különböző értékek száma; nullák aránya és eloszlása; szomszéd-különbségek) jelölt számküszöbök rögzítése, **mielőtt** bármit lekérdezünk. Ez rostál; a fordítottja (küszöb a számok látványa után) igazolna — az a vacuous RED mérés-alakja.
- [ ] **2. Szóló lekérdezés** kulcsszavanként: `interest_over_time([kif], geo="HU", timeframe="now 7-d")`, mind a 13 szóra (spec 2.2).
- [ ] **3. Kulcsszavanként a nyers számok kiírása** a jegyzőkönyvbe — **ne csak a következtetést** (felhasználói kikötés): különböző értékek száma, nullák aránya, nulla-blokkok eloszlása (összefüggő éjszakai vs. szórt), szomszéd-különbségek eloszlása. Cél: ha a küszöb később rossznak bizonyul, **új Trends-lekérdezés nélkül újraszámolható** legyen.
- [ ] **4. Döntés szavanként** a **mérés-előtti** küszöbök alapján (mérhető / elbukott), számokkal indokolva. A `tüntetés`-nél a kritérium a **csúcsok** folytonossága, nem a sok kis érték (spec 6.1, eseményjelző-kivétel). Ha a mérés után a küszöbön módosítani kell, az megengedett, **de a jegyzőkönyvben ott a régi érték, az új és az indok.**
- [ ] **5. `betegség` + `kórház` közös éves lekérdezés** (egy hívás): `interest_over_time(["betegség", "kórház"], geo="HU", timeframe="today 12-m")` — annak eldöntésére, ugyanazt a téli hullámot mérik-e (6.2). **Most a legolcsóbb pillanat rá**; a szóló mérések után már nem derülne ki. Az eredmény a jegyzőkönyvbe, a döntés a Task 2-é.
- [ ] **6. A jegyzőkönyv mentése** `docs/superpowers/phase2_5/task1-meres.md`-be; a véglegesített küszöbök visszaírandók a spec 6.1-be (külön szerkesztés).
- [ ] **7. Commit a jegyzőkönyvről — a Task 2 jóváhagyása UTÁN** (hogy ne a Task 3 feature-commitjában utazzon): `docs(phase2_5): Task 1 szóló mérés jegyzőkönyve`. **Repóba kerülő script továbbra sincs.** *Ez a checkbox szándékosan nyitva marad, amikor a végrehajtó a Task 2-re lép — nem blokkoló; a Task 2 jóváhagyása után zárul.*

**DoD:**
- A jegyzőkönyv létezik, és **kulcsszavanként tartalmazza a nyers számokat** (nem csak a verdiktet).
- A jegyzőkönyv tartalmazza a **mérés előtti (jelölt) küszöböket** is; ha a küszöb módosult, a régi érték + új + indok szerepel.
- Minden „elbukott" döntés mellett ott a szám, ami alátámasztja (6.1).
- A `tüntetés` a csúcs-folytonosság szerint van megítélve, nem a kis alapvonal miatt kizárva.
- A `betegség`+`kórház` éves átfedés-mérés eredménye rögzítve.
- **Nincs repóba került script.** A jegyzőkönyv saját `docs(phase2_5): Task 1 szóló mérés jegyzőkönyve` commitot kap a Task 2 jóváhagyása után.

---

## Task 2: Kulcsszólista véglegesítése (TARTALMI DÖNTÉS — JÓVÁHAGYÁSI KAPU)

**Files:** nincs kód; a döntés a plan/ledgerbe kerül.

**Interfaces:**
- Consumes: Task 1 jegyzőkönyv (mérhető szavak listája + okok).
- Produces: a **jóváhagyott** `config.yaml` `kulcsszavak`-tartalom (a Task 4 ezt írja fájlba).

**Cél:** A Task 1 rostája alapján a végleges kulcsszólista + `domen` + `tipus` rögzítése, **külön felhasználói jóváhagyással**. A „ne húzzunk előre a listából" elv (6.2): a Task 1-en meg nem bukott szó nem esik ki.

**Nincs RED — ez döntés, nem kód.**

- [ ] **0. Fordított kapu — ha túl sok szó bukik.** Ha a Task 1-en **4-nél több** szó bukott el, a Task 2 **NEM a maradékkal megy tovább**: megáll, és visszatér **listaválasztásra** (felhasználói döntés — új szavak/megfogalmazások keresése). Indok: 13 szó / 9 domén mellett 5+ bukás több domént is lefedetlenül hagyna, és a lista alapfeltevése dőlne meg. *(A 4-es küszöbbel egyetértek; felhasználói finomításra nyitva.)*
- [ ] **1.** A spec 2.2 alaplistából a Task 1-en **elbukott** szavak elhagyása (ha ≤4 van); a `tüntetés` védett (6.2, egyetlen eseményjelző).
- [ ] **2.** Minden megmaradt szóhoz `domen` (ékezet nélkül, spec 7) és `tipus` ∈ {`szintmero`, `esemenyjelzo`, `hibrid`} (spec 2.3).
- [ ] **3.** A pontos `config.yaml kulcsszavak:` blokk kiírása a ledgerbe **jóváhagyásra**. Alapállapot (mind a 13 mérhető esetén, spec 7):

```yaml
kulcsszavak:
  - {kifejezes: "állás",        domen: munkaeropiac,       tipus: szintmero}
  - {kifejezes: "kormányablak", domen: kozigazgatas,       tipus: szintmero}
  - {kifejezes: "eladó lakás",  domen: lakhatas,           tipus: szintmero}
  - {kifejezes: "albérlet",     domen: lakhatas,           tipus: szintmero}
  - {kifejezes: "akciós újság", domen: fogyasztas,         tipus: szintmero}
  - {kifejezes: "benzin",       domen: fogyasztas,         tipus: szintmero}
  - {kifejezes: "nyaralás",     domen: fogyasztas,         tipus: szintmero}
  - {kifejezes: "kórház",       domen: egeszseg,           tipus: szintmero}
  - {kifejezes: "betegség",     domen: egeszseg,           tipus: szintmero}
  - {kifejezes: "napelem",      domen: energia,            tipus: hibrid}
  - {kifejezes: "nyugdíj",      domen: jovedelem,          tipus: hibrid}
  - {kifejezes: "hitel",        domen: haztartasi_penzugy, tipus: szintmero}
  - {kifejezes: "tüntetés",     domen: kozelet,            tipus: esemenyjelzo}
```

**DoD:**
- Ha a Task 1-en >4 szó bukott, a task **megállt és listaválasztásra tért vissza** (nem a maradékkal ment tovább).
- A felhasználó jóváhagyta a végleges listát (szavak, domének, típusok).
- Minden kihagyott szó mellett ott a Task 1-es szám-indok (a `betegség`/`kórház` átfedés-döntést is beleértve).
- A jóváhagyott blokk a ledgerben rögzítve, hogy a Task 4 verbatim beírhassa.

---

## Task 3: Nyers órás kimenet szerződés-validátora (TDD)

**Files:**
- Create: `trendfigyelo/nyers_kimenet.py` (csak a validátor ebben a taskban)
- Test: `tests/test_nyers_kimenet.py`

**Interfaces:**
- Produces: `ervenyes_nyers_rekord(rek: dict) -> list[str]` — a hibák listája; **üres lista = érvényes**. A rekord-alak, amit a Task 6 írónak elő kell állítania:

```python
# egy kulcsszó nyers órás sorozata egy futásból:
{
  "kulcsszo": str,               # nem üres
  "ablak_kezdet_utc": str,       # ISO, a lekérdezés ablakának kezdete
  "ablak_veg_utc": str,          # ISO, > ablak_kezdet_utc
  "pontok": [                    # nem üres, időrendben
    {"idopont_utc": str, "ertek": int | "", "reszleges": bool},
    ...
  ],
}
```

**Cél:** A nyers órás kimenet szerződésének **futtatható őre**: mezők jelenléte, ablakhatárok megléte és rendezettsége, típusok, és a **véglegesség-jelölés** (`reszleges` bool minden ponton, spec 4.3). A Task 6 író és annak integrációs tesztje ezt a validátort használja újra.

**RED-diszkriminátor:** a validátornak **el kell utasítania** az ablakhatár nélküli és a véglegesség-jelölés nélküli rekordot — egy „mindig `[]`-t adó" csonk-validátor ezen megbukik. A negatív fixtúrák ezt kényszerítik ki:

```python
def test_hianyzo_ablakhatar_elutasitva():
    rek = {"kulcsszo": "hitel", "ablak_veg_utc": "2026-07-27T21:00:00+00:00",
           "pontok": [{"idopont_utc": "2026-07-27T20:00:00+00:00", "ertek": 5, "reszleges": False}]}
    hibak = ervenyes_nyers_rekord(rek)
    assert any("ablak_kezdet_utc" in h for h in hibak)  # csonk-validátor ([]) itt bukik

def test_veglegesseg_jeloles_nelkul_elutasitva():
    rek = {"kulcsszo": "hitel", "ablak_kezdet_utc": "2026-07-20T21:00:00+00:00",
           "ablak_veg_utc": "2026-07-27T21:00:00+00:00",
           "pontok": [{"idopont_utc": "2026-07-27T20:00:00+00:00", "ertek": 5}]}  # nincs 'reszleges'
    hibak = ervenyes_nyers_rekord(rek)
    assert any("reszleges" in h for h in hibak)

def test_ervenyes_rekord_atmegy():
    rek = {"kulcsszo": "hitel", "ablak_kezdet_utc": "2026-07-20T21:00:00+00:00",
           "ablak_veg_utc": "2026-07-27T21:00:00+00:00",
           "pontok": [{"idopont_utc": "2026-07-27T20:00:00+00:00", "ertek": 5, "reszleges": True}]}
    assert ervenyes_nyers_rekord(rek) == []
```

- [ ] **1. Írd meg a fenti három tesztet** (`tests/test_nyers_kimenet.py`).
- [ ] **2. Futtasd — bukjon** (`ImportError`/`NameError`: `ervenyes_nyers_rekord` nincs).
- [ ] **3. Implementáld** `ervenyes_nyers_rekord`-ot: ellenőrzi a kötelező kulcsokat, az `ablak_kezdet_utc < ablak_veg_utc` ISO-relációt, a nem-üres `pontok`-at, és pontonként az `idopont_utc`(str)/`ertek`(int vagy `""`)/`reszleges`(bool) típusokat.
- [ ] **4. Futtasd — menjen át** mindhárom.
- [ ] **5. Commit** (review után): `feat(kulcsszo): nyers órás kimenet szerződés-validátora`.

**DoD:**
- `ervenyes_nyers_rekord` üres listát ad érvényes rekordra, és **név szerint jelzi** a hiányzó ablakhatárt / véglegesség-jelölést.
- A negatív tesztek egy `[]`-t adó csonkon bizonyítottan buknának (nem vacuous).
- Teljes suite zöld.

---

## Task 4: Szóló gyűjtő + config-séma (ATOMI, TDD)

**Files:**
- Modify: `config.yaml`, `trendfigyelo/config.py`, `trendfigyelo/kulcsszavak.py`, `trendfigyelo/json_export.py`
- Test: `tests/test_config.py`, `tests/test_kulcsszavak.py`, `tests/test_json_export.py`

**Interfaces:**
- Produces:
  - `config.KulcsszoTetel` = `namedtuple("KulcsszoTetel", ["kifejezes", "domen", "tipus"])`
  - `Config.osszes_kulcsszo() -> list[KulcsszoTetel]` (a `referenciaszo`/`referencia_min_atlag` mezők törölve)
  - `kulcsszavak.gyujt(kliens, config, most=None) -> (pontok, napi_pontok, nyers_sorozatok)` — háromelemű:
    - `pontok`: az utolsó teljes nap pontjai a CSV-hez/`legfrissebb.json`-hoz; pont-alak: `{"kulcsszo","domen","tipus","idopont_utc","nyers_ertek"}` (nincs `normalizalt_ertek`/`referencia_*`).
    - `napi_pontok`: `{nap_iso: [pont]}` az utolsó N teljes napra (a `tortenet` upserthez).
    - `nyers_sorozatok`: `{kifejezes: nyers_rekord}` a Task 3 séma szerint (a Task 6 írja ki; itt csak előáll).
- Consumes: `config` (új séma), `kliens.tr.interest_over_time`.

**Cél:** A kulcsszó-ág átállítása szólóra: szavanként **egy** `interest_over_time([kif], geo, "now 7-d")`, **referenciaszó és normalizálás nélkül**; a config-séma per-kulcsszó rekordokra; a `json_export` kulcsszó-aggregátuma a **nyers** értékből, `csoport`→`domen`. A `kliens`, `felkapott`, `idosor` érintetlen.

**RED-diszkriminátor (a lényegi teszt):** egy 3-szavas configgal a `kliens.tr.interest_over_time`-ot **3-szor, szavanként EGY-elemű listával**, referenciaszó nélkül kell hívni — a régi kötegelt kód (1 hívás, 5 szó a horgonnyal) ezen megbukik. Kém-kliens rögzíti a hívásonként átadott `szavak` argumentumot:

```python
def test_szolo_lekerdezes_szavanként_egy_hivas(harom_szavas_config):
    kem = KemKliens(df_gyar=egy_szo_df)   # rögzíti a hívott 'szavak' listákat
    kulcsszavak.gyujt(kem, harom_szavas_config, most=FIX_MOST)
    assert kem.hivott_szavak == [["állás"], ["hitel"], ["tüntetés"]]  # 3 hívás, 1-1 szó
    assert all("időjárás" not in sz for sz in kem.hivott_szavak)       # nincs horgony

def test_nincs_normalizalt_mezo_a_pontokban(harom_szavas_config):
    pontok, _, _ = kulcsszavak.gyujt(KemKliens(df_gyar=egy_szo_df), harom_szavas_config, most=FIX_MOST)
    assert pontok and all("normalizalt_ertek" not in p and "referenciaszo" not in p for p in pontok)
    assert all(p["domen"] and p["tipus"] for p in pontok)             # domen/tipus átmegy
```

- [ ] **1. Config-tesztek RED:** `test_config.py` — `osszes_kulcsszo()` `KulcsszoTetel` rekordokat ad; `referenciaszo`/`referencia_min_atlag` már nincs; hibás `tipus` → `KonfigHiba`. Futtasd, bukjon.
- [ ] **2. Config GREEN:** `config.py` — `Config` mezők (horgony ki, `kulcsszavak: list`), a `betolt()` a lista-of-dict `kulcsszavak`-ot parse-olja, validálja (`kifejezes` nem-üres; `domen` nem-üres; `tipus` a három érték egyike), `osszes_kulcsszo()` `KulcsszoTetel`-eket ad. Írd át a `config.yaml`-t a **Task 2-ben jóváhagyott** blokkra, `referenciaszo`/`referencia_min_atlag` törölve.
- [ ] **3. Gyűjtő-tesztek RED:** a fenti két diszkriminátor-teszt `test_kulcsszavak.py`-ba; a régi kötegelő tesztek (`kotegek`, `skalazo`, `referencia_*`) törlése/átírása. Futtasd, bukjon.
- [ ] **4. Gyűjtő GREEN:** `kulcsszavak.py` — `KOTEG_MERET`/`kotegek`/`koteg_lekerdezes_szavai`/`skalazo`/`_ref_atlag` **törlés**; `gyujt` szavanként hív, a df-et pontokká (nyers, `domen`/`tipus`) parse-olja, az utolsó teljes nap + utolsó N nap szűrése megmarad (a `_bp_datum`/`utolso_teljes_nap`/`utolso_N_teljes_nap` újrahasznosítható), és minden szóra összeállítja a `nyers_sorozatok` rekordját (ablakhatárok a df indexéből, `reszleges` az `isPartial` oszlopból — lásd 4.3). Futtasd, menjen át.
- [ ] **5. json_export GREEN:** `json_export.py` — `kulcsszo_napi_osszesites`/`_kulcsszo_idosorok`/`csv_ir` a **nyers** értékből dolgozik (`referencia_ervenyes`-szűrő és `normalizalt_ertek` ki), `csoport`→`domen`, a `tipus` átmegy. A `test_json_export.py` frissítése. Futtasd a teljes suite-ot — **zöld**.
- [ ] **6. Commit** (review után): `feat(kulcsszo): szóló lekérdezés + per-kulcsszó config, horgony elvetve`.

**DoD:**
- `interest_over_time` szavanként **egy** hívás, egy-elemű listával, horgony nélkül (diszkriminátor bizonyítja).
- A pontokban nincs `normalizalt_ertek`/`referencia_*`; van `domen`/`tipus`.
- `config.py` az új sémát tölti, hibás `tipus`/hiányzó `domen` → `KonfigHiba`.
- `gyujt` visszaad `nyers_sorozatok`-ot a Task 3 séma szerint (a Task 6 még nem írja ki).
- Teljes suite zöld; a `felkapott`/`idosor`/`kliens` fájlok **érintetlenek** (diff-ellenőrzés).

---

## Task 5: Ágsorrend csere (TDD) — dep 4

**Files:**
- Modify: `trendfigyelo/futtato.py` (ágsorrend + `AGAK`)
- Test: `tests/test_futtato.py`

**Interfaces:**
- Consumes: `kulcsszavak.gyujt` (3-tuple, Task 4), `idosorok.gyujt`.
- Az `AGAK` konstans új sorrendje: `["felkapott_api", "felkapott_rss", "kulcsszo", "idosor"]`.

**Cél:** A gyűjtő ágsorrendje `felkapott_api → felkapott_rss → kulcsszo → idosor` (ma a `kulcsszo` az utolsó). **Csak a Task 4 után** — előtte a `kulcsszo` a régi 22 szót gyűjti horgonnyal (használhatatlan), tehát a csere a jó `idosor`-adatot áldozná fel érte (spec 6, Task-lista indoklás).

**RED-diszkriminátor:** kém-kliens rögzíti az ágak **végrehajtási sorrendjét**; a `kulcsszo` első hívása előbb kell legyen, mint az `idosor` elsőé — a régi `futtato` (idosor előbb) ezen megbukik. Külön block-stop teszt: az `idosor`-ág blokkol → a `kulcsszo` **már lefutott** (van adata), az `idosor` „blokkolva", és a `kulcsszo` **nem** „kihagyva":

```python
def test_kulcsszo_az_idosor_elott_fut():
    kem = SorrendKemKliens()
    futtato.futtat(config, kem, adatok, docs)
    assert kem.elso_index("kulcsszo") < kem.elso_index("idosor")

def test_idosor_blokk_utan_a_kulcsszo_mar_megvan(tmp_path):
    kem = IdosorBlokkolKliens()   # az 'idosor' ágon merít ki 429-cel
    futtato.futtat(config, kem, tmp_path/"adatok", tmp_path/"docs")
    eredmeny = {s["ag"]: s["eredmeny"] for s in _naplo(tmp_path)}
    assert eredmeny["kulcsszo"] == "siker"       # már lefutott
    assert eredmeny["idosor"] == "blokkolva"
    # a régi sorrenden a kulcsszo lenne "kihagyva"
```

- [ ] **1.** A két teszt `test_futtato.py`-ba. Futtasd — bukjon (régi sorrenden a `kulcsszo` az `idosor` után van).
- [ ] **2.** `futtato.futtat`: a `kulcsszo` `_ag(...)` blokk az `idosor` blokk **elé** kerül (a `top_kifejezesek` számítása marad az `api` után, az `idosor` előtt). Az `AGAK` konstans átrendezése ugyanerre a sorrendre.
- [ ] **3.** Futtasd — menjen át; a meglévő block-stop teszt (`felkapott_api` az első) **továbbra is** zöld.
- [ ] **4. Commit** (review után): `refactor(futtato): kulcsszo ág az idosor elé (block-napon az idosor az olcsóbb veszteség)`.

**DoD:**
- A `kulcsszo` bizonyítottan az `idosor` előtt fut; `AGAK` egyezik a végrehajtási sorrenddel.
- Block-napon a `kulcsszo` adata megvan, mielőtt az `idosor` blokkolna.
- `tervezett_hivasszam` érték változatlan (sorrend-független összeg).
- Teljes suite zöld.

---

## Task 6: Nyers órás sorozat verziókövetett kimenete (TDD) — dep 3, 4

**Files:**
- Modify: `trendfigyelo/nyers_kimenet.py` (író hozzáadása a validátor mellé), `trendfigyelo/futtato.py` (bekötés)
- Create (futásidő): `docs/data/kulcsszo_nyers.json`
- Test: `tests/test_nyers_kimenet.py`

**Interfaces:**
- Produces: `nyers_kimenet.ir_gordulo(docs_data, nyers_sorozatok: dict, megtartott_nap: int = 14) -> Path` — a `docs/data/kulcsszo_nyers.json`-ba upsertli a friss nyers rekordokat kulcsszavanként, gördülő ablakban (a `megtartott_nap`-nál régebbi napok ablakait eldobja). A fájl-alak: `{"kulcsszavak": {kifejezes: [nyers_rekord, ...]}}`, minden rekord a Task 3 séma szerint és `ervenyes_nyers_rekord`-dal validált.
- Consumes: `kulcsszavak.gyujt` `nyers_sorozatok` (Task 4), `ervenyes_nyers_rekord` (Task 3).

**Cél:** A nyers órás sorozat verziókövetett mentése a lekérdezés **pontos ablakhatáraival** és a **részleges-farok jelöléssel**, gördülő retencióval — a későbbi láncolás bemenete (spec 4.2). Ablakhatárok nélkül a mentés értéktelen (4.2), a részleges farok bejelöletlen bevétele rendszeres torzítás (4.3).

**RED-diszkriminátor:** két egymást követő futás után a `kulcsszo_nyers.json` rekordjai **átmennek** a Task 3 validátoron ÉS a részleges farok `reszleges: true`-ként szerepel; a `megtartott_nap`-nál régebbi ablak **kiesik**. Egy ablakhatár nélküli vagy a farkat végleg­esként jelölő naiv író a validátoron bukik:

```python
def test_kimenet_atmegy_a_szerzodesen():
    ny = {"hitel": mintarekord(reszleges_farok=True)}
    p = nyers_kimenet.ir_gordulo(tmp/"docs", ny)
    adat = json.loads(p.read_text("utf-8"))
    for rekordok in adat["kulcsszavak"].values():
        for rek in rekordok:
            assert ervenyes_nyers_rekord(rek) == []
    assert adat["kulcsszavak"]["hitel"][-1]["pontok"][-1]["reszleges"] is True

def test_gordulo_ablak_eldobja_a_regit():
    nyers_kimenet.ir_gordulo(tmp/"docs", {"hitel": rekord_ablak("2026-06-01")}, megtartott_nap=14)
    nyers_kimenet.ir_gordulo(tmp/"docs", {"hitel": rekord_ablak("2026-07-27")}, megtartott_nap=14)
    ablakok = [r["ablak_veg_utc"][:10] for r in json.loads(...)["kulcsszavak"]["hitel"]]
    assert "2026-06-01" not in " ".join(ablakok)   # a régi ablak kiesett
```

- [ ] **1.** A két teszt `test_nyers_kimenet.py`-ba. Futtasd — bukjon (`ir_gordulo` nincs).
- [ ] **2.** `ir_gordulo` implementálása: beolvas (ha van), kulcsszavanként hozzáfűzi a friss rekordot, a `megtartott_nap`-nál régebbi `ablak_veg_utc`-jű rekordokat eldobja, és **mentés előtt** minden rekordot `ervenyes_nyers_rekord`-dal validál (hibás → `ValueError` a hibalistával). Futtasd — menjen át.
- [ ] **3.** `futtato.futtat`: a `kulcsszo` ág `nyers_sorozatok`-ját átadja `ir_gordulo`-nak (a CSV/JSON-export mellett). Üres sorozat NE írjon üres fájlt (a meglévő „részleges siker" mintát követve).
- [ ] **4.** Futtasd a teljes suite-ot — zöld.
- [ ] **5. Commit** (review után): `feat(kulcsszo): nyers órás sorozat verziókövetett gördülő kimenete`.

**DoD:**
- A `kulcsszo_nyers.json` minden rekordja átmegy a Task 3 szerződésen (ablakhatárok + `reszleges` jelölés).
- A részleges farok `reszleges: true`-ként szerepel (4.3), nem végleges.
- A `megtartott_nap`-nál régebbi ablak kiesik (gördülő retenció, 4.2).
- Teljes suite zöld.

---

## Task 7: Töréspont rögzítése az adatban (TDD) — dep 4

**Files:**
- Modify: `trendfigyelo/json_export.py` (töréspont-mező írása), `trendfigyelo/futtato.py` (átadás)
- Test: `tests/test_json_export.py`

**Interfaces:**
- Produces: a `tortenet.json` és `legfrissebb.json` top-szintű `modszertan_valtas` kulcsa (ISO dátum, **az első éles (merge utáni) produkciós futás napja**). `json_export.tortenet_frissit_napok(...)` és `legfrissebb_ir(...)` egy `valtas_datum` paramétert kap.

**Cél:** A javítás előtti és utáni napok összehasonlíthatatlanok (spec: „az idősor töréspontja"); a váltás dátuma az **adatba** kerüljön, ne csak commit-üzenetbe. A frontend (Phase 3) ebből tudja, hol nem szabad összekötni a sorozatot.

**A `valtas_datum` az ELSŐ ÉLES (merge utáni) produkciós futás napja — nem a Task 4 commit-napja.** Indok: a Task 4 nem mergelt ágon él; a merge-ig az esti cron a régi, horgonyos kóddal gyűjt tovább, így egy commit-napi töréspont után is jönnének még régi-módszertanú napok a `tortenet.json`-ba, és a Phase 3 pont ott kötné össze a sorozatot, ahol nem szabad. Ha az érték a Task 7 futásakor még nem ismert, **a merge után kerül be** (a `valtas_datum` forrás — config/konstans — egysoros frissítése). A Task 7 **tesztje ettől független és zöld**, mert `valtas_datum` **paraméterezett, nem hardkódolt dátum**.

**Szerződés-döntés (user, 2026-07-29) — a jelölő-írás aszimmetriája (SZÁNDÉKOS, nem bug):**
- A `tortenet.json` **halmozódó** (több futás upsertje), ezért a `modszertan_valtas`-t **`setdefault`**-tal írjuk:
  az **első beállított** (legkorábbi éles) érték marad, későbbi futás (más dátum vagy None) **nem írja felül / nem törli**.
- A `legfrissebb.json` **minden futásban teljesen újraíródik**, ott nincs megőrzendő korábbi állapot → a kulcs egyszerűen
  a friss `valtas_datum`-ot kapja.
- Mindkét helyen **`if valtas_datum is not None:`** — a None sosem ír `null`-t és nem nyúl a kulcshoz (a kulcs HIÁNYZIK, nem null).
- **Scope:** a `modszertan_valtas` **CSAK jelöl** — nulla szűrő/vágó/régi-adat-eldobó logika (az Phase 3 döntése).
- **YAML-típus + normalizálás:** a merge-utáni egysoros editet ember írja, jó eséllyel idézőjel nélkül
  (`modszertan_valtas: 2026-08-01`) → a PyYAML `datetime.date`-té alakítja. A `betolt` elfogad **str-t és
  `datetime.date`-et**, a validált dátum **`.isoformat()`**-ját (kanonikus `YYYY-MM-DD`) teszi a `Config`-ra;
  minden más bemenet → `KonfigHiba`.
- **Verzió-jegyzet:** a str-ág elutasító viselkedése (idézőjeles idő-tartalmú string, pl. `"2026-08-01T12:00:00"` /
  `"2026-08-01 12:00:00"` → `date.fromisoformat` ValueError → `KonfigHiba`) **Python 3.14.4-en igazolva** (fejlesztői
  venv). A CI és az átadó környezet **Python 3.12** (`.github/workflows/napi.yml`); a `date.fromisoformat` az idő-tartalmú
  stringet **3.11+ óta elutasítja** (a 3.11-es relaxáció csak dátum-formátumokat bővített — basic/hét/ordinális —, nem a
  záró időt), így a viselkedés verzió-konzisztens. A `datetime`-**objektum** útját amúgy is az explicit
  `isinstance(ertek, datetime)` fogja el a `fromisoformat` elérése ELŐTT.

**RED-diszkriminátor:** a `tortenet.json`-nak a váltás után **tartalmaznia kell** a `modszertan_valtas` ISO-dátumot; a régi `json_export` (ami nem írja) ezen megbukik. Külön: a töréspont **nem lehet** üres/ismeretlen, ha van szóló-adat.

```python
def test_tortenet_tartalmazza_a_torespontot(tmp_path):
    json_export.tortenet_frissit_napok(tmp_path, {"2026-07-28": pontok}, valtas_datum="2026-07-28")
    adat = json.loads((tmp_path/"tortenet.json").read_text("utf-8"))
    assert adat["modszertan_valtas"] == "2026-07-28"
    # a régi kód nem ír ilyen kulcsot → KeyError/None itt
```

- [ ] **1.** A teszt `test_json_export.py`-ba. Futtasd — bukjon (nincs `modszertan_valtas`).
- [ ] **2.** `tortenet_frissit_napok`/`legfrissebb_ir` kap `valtas_datum` paramétert, és a kimenet top-szintjére írja `modszertan_valtas`-ként (idempotens: meglévő értéket nem töröl, ha már be van állítva korábbi napra). `futtato` átadja a váltás dátumát a `valtas_datum` forrásból (config/konstans), amely az **első éles, merge utáni futás napjára** áll be — a merge-ig üres/None is lehet (ekkor a mező nem íródik, a régi napok érintetlenek). Futtasd — menjen át.
- [ ] **3.** Futtasd a teljes suite-ot — zöld.
- [ ] **4. Commit** (review után): `feat(adat): módszertani töréspont rögzítése a tortenet/legfrissebb JSON-ban`.

**DoD:**
- A `tortenet.json` és `legfrissebb.json` `modszertan_valtas` ISO-dátumot tartalmaz.
- A töréspont az adatban van (nem csak commit-üzenetben).
- A régi bejegyzéseket nem írja felül (idempotencia).
- Teljes suite zöld.

---

## Task 8: Első éles integráció + hívásszám-igazolás (MÉRÉS — NEM FEJLESZTÉS) — dep 4, 5

**Files:**
- Create: `docs/superpowers/phase2_5/task8-kerésszam.md` (jegyzőkönyv)

**Újrafogalmazva (2026-07-30, trigger-stratifikáció után).** Az eredeti „429-ráta + futásidő mérése dispatch-csel" cél **nem teljesíthető merge előtt**, mert a dispatch-populáció szisztematikusan torzított: az Actions-history szerint **3/3 `workflow_dispatch` tiszta, 0/3 `schedule` problémás** (2 kapu-blokk + 1 lágy), és a trigger a naptári nappal konfundál (a 3 dispatch = 07-24/25/26, a 3 schedule = 07-27/28/29). Egy dispatch tehát a **jó rezsimet** mintázza. Ráadásul a `schedule` **csak a default (main) ágon fut** → az új ágsorrend schedule-rezsimben **csak merge UTÁN** figyelhető meg.

**Cél — MERGE ELŐTT (ez a Task 8 valódi tartalma):**
1. **Első éles integráció.** A Task 4–7 kódja eddig **kizárólag fake/mock ellen** futott (108 zöld teszt). Egy dispatch az **első valódi trendspy-0.1.6 + Google Trends** integráció az **új kódon és az új `…→kulcsszo→idosor` ágsorrenden** — ezt a suite nem tudja igazolni (lásd alább).
2. **Ágankénti hívásszám igazolása a config-jóslat ellen:** `felkapott_api=1, felkapott_rss=1, kulcsszo=13, idosor=min(15,#trend)`, összesen ~30. Determinisztikus, **egyetlen tiszta futás elég**.

**MERGE UTÁNRA ÁTTOLVA (NEM Task 8 döntése):** a 429-ráta / futásidő / rezsim-jellemzés a mainre akkumulálódó `naplo.csv`-ből, ~2 hét megfigyeléssel (az a mechanizmus, ami a 07-27/28/29 adatot adta). A produkciós üzemeltetési döntések — cron perc/óra, kézi vs schedule, futás-szintű retry — **külön, merge utáni kör**, nem ez a task dönti el.

**Nincs RED/GREEN.** A jel a `kliens` hívásszámlálóiból (`hivasszam`/`osszes_hivas`) + a naplóból olvasandó; **repóba kerülő script-kód és commit nem** (a jegyzőkönyvön kívül). **Előfeltételek** (külön, engedélyhez kötött lépések, lásd ledger): ág push origin-ra; **ág-alapú feltételes commit-step** a `napi.yml`-ben — `if: always() && github.ref == 'refs/heads/main'` (dispatch a phase-2.5-ről → `false` → nem commitol az ágra; merge után a mainen → `true` → commitol, ahogy eddig; **nincs input** → megszűnik a dispatch input-schema- és boolean-coercion-kérdés, a main `napi.yml`-je bitre változatlan); **kliens-szintű hívás-plafon** (call-multiplying bug elleni védőkorlát, TDD-vel) — küszöb **`tervezett_hivasszam * max_probak`** (=120, a strukturális maximum, ráhagyás nélkül), az ellenőrzés **`> plafon`** (nem `>=`: a 120. legitim legrosszabb eset — minden logikai hívás mind a 4 próbát kimeríti — még átmegy, a 121. már csak bug), túllépéskor `RuntimeError`; a napló + a `docs/data` JSON-ok + a teljes stdout **kötelező** felszínre hozása commit nélkül (`actions/upload-artifact@v4`, `if: always()`; a stdout `set -o pipefail` + `tee run.log`-gal, hogy a kilépési kód ne vesszen).

**Jegyzőkönyv-jegyzet (2026-07-30) — NE olvassuk félre a mérőfutás kimenetét:** az ág `docs/data`-ja a `b12722e` pillanatkép, ~3 napja elavult (a 07-27/28/29 napi JSON-ok CSAK a mainen vannak, az ág egyetlen commitja sem nyúlt `docs/data`-hoz). A mérőfutás tehát **hiányos történetre upsertál** → az artefakt `tortenet.json`-ja hiányos történetet mutat — **ez NEM integrációs hiba**. A `kulcsszo_nyers.json` viszont az ágon **egyáltalán nem létezik** → az `ir_gordulo` nulláról hozza létre — **ez épp a jó eset a validátor-átmenet (tz-aware ISO, szerződés) valós adaton való igazolására**.

- [ ] **1.** Előfeltételek teljesítése (push + **ág-alapú feltételes commit-step** + hívás-plafon + kötelező napló/JSON/stdout-artefakt) — mind külön jóváhagyással.
- [ ] **2.** Egy `workflow_dispatch` futás a **Task 4 + Task 5 utáni** kóddal a phase-2.5 ágról (`github.ref` = `refs/heads/phase-2.5` ≠ `main` → az ág-alapú feltétel miatt **nem commitol az ágra**); a naplóból (artefaktból) ágankénti `hivasok_szama` + `eredmeny` kiolvasása.
- [ ] **3.** Az **ágankénti hívásszám** összevetése a config-jóslattal (api=1/rss=1/kulcsszo=13/idosor≤15). Eltérés (pl. 26 vagy 13+1) = integrációs hiba, kivizsgálandó. A hibaminta *helye* (kapu vs közepi, melyik ág) best-effort rögzítendő — de nem garantált, hogy egy dispatch egyáltalán reprodukál blokkot.
- [ ] **4.** Jegyzőkönyv mentése; a 429-ráta/rezsim explicit a **merge utáni** megfigyelésre utalva (nem itt).

**DoD:**
- A jegyzőkönyv tartalmazza az **ágankénti hívásszámot** egy valós futásból, és **igazolja a config-jóslatot** (vagy dokumentálja az eltérést + okát).
- Rögzíti, hogy az **első éles integráció** az új sorrenden lefutott (mit igazolt, amit a fake nem).
- A 429-ráta / rezsim / tartalék-döntés **explicit áttolva merge utánra** — ez a task NEM dönt tartalékról.
- Nincs repóba került script, nincs commit ebből a taskból; a mérési adat nem került az ágra.

---

## Task 9: README-frissítés + whole-branch review

**Files:**
- Modify: `README.md`
- Review: teljes ág (base `b12722e` … a Task 7 utolsó commitja)

**Cél:** A README átvezetése a szóló mérésre (horgony eltűnt, per-kulcsszó config, nyers órás kimenet, töréspont), és a teljes ág átfogó felülvizsgálata merge előtt.

**RED-diszkriminátor:** nincs új kód → nincs RED. Verifikáció: a README **ne** hivatkozzon a `referenciaszo`/horgony/normalizálás fogalmakra a kulcsszó-ágnál, és **hivatkozzon** a `kulcsszo_nyers.json`-ra + a töréspontra. Grep-ellenőrzés + whole-branch review.

- [ ] **1.** README: a kulcsszó-ág leírása szólóra; a `config.yaml kulcsszavak` új szerkezete; a `kulcsszo_nyers.json` és a `modszertan_valtas` dokumentálása; a horgony-szakasz törlése.
- [ ] **2.** Grep: `grep -niE "időjárás|referenciaszo|horgony|normaliz" README.md` a kulcsszó-kontextusban üres (vagy csak történeti/„elvetve" említés).
- [ ] **3.** Whole-branch review (Opus) a base…HEAD diffre: a `kliens`/`felkapott`/`idosor` érintetlensége, a suite zöldsége, a szerződés-tesztek nem-vacuous volta, a törés konzisztenciája kód/teszt/README között.
- [ ] **4. Commit** (review után): `docs: README a szóló kulcsszó-mérésre + whole-branch review`.

**DoD:**
- README a valós (szóló) viselkedést írja; nincs elárvult horgony-hivatkozás.
- Whole-branch review: nincs blokkoló; a `felkapott`/`idosor`/`kliens` bizonyítottan érintetlen.
- Teljes suite zöld; az ág merge-kész.

---

## Self-Review (spec-lefedettség)

| Spec elem | Task | 
|---|---|
| 1–1.4 (baj, skálaösszenyomás, horgony hibás) | Motiváció; a horgony elvetése **Task 4** |
| 2.1–2.5 (kulcsszólista, elv, karaktertípusok, méret) | **Task 2** (lista+domen+tipus), **Task 4** (config-mezők) |
| 3 (döntések: szóló, ablak 7-d, csoportok=domének, karaktertípus, láncolás-előkészítés) | **Task 4** (szóló, domének, tipus), **Task 6** (láncolás-előkészítés) |
| 4.1–4.4 (láncolás elve, nyers órás + ablakhatár, részleges farok, hibahalmozás) | **Task 3** (szerződés), **Task 6** (nyers kimenet, isPartial) |
| 5 (kockázatok: zaj, skálaugrás, kérésszám, töréspont) | **Task 1** (6.1 zaj-kritérium), **Task 7** (töréspont), **Task 8** (kérésszám) |
| 6/6.1/6.2 (task-lista, objektív kritérium, ne húzz előre) | mind; **Task 1** (6.1), **Task 2/8** (6.2 vágás) |
| 7 (config-szerkezet, config.py átírandó) | **Task 2** (tartalom), **Task 4** (config.py) |
| Ágsorrend (Task-lista 5) | **Task 5** |

Nincs lefedetlen spec-elem. A `kliens`/`felkapott`/`idosor` szándékosan érintetlen (Global Constraints).
