# Design — Reggeli kulcsszó-ág: társadalmi-feszültség monitor (15 új szó, 5 domén, per-szó időablak)

Dátum: 2026-09-01
Státusz: jóváhagyva (brainstorming), spec-review kész

## Cél

15 új „társadalmi feszültség" kulcsszót figyelünk, 5 beszédes nagy-kategóriába (domén)
sorolva, a **reggeli** futásban gyűjtve, **per-szó időablakkal** (a lassú strukturális
szavak csak egy másodlagos ablakot kapnak — nincs órás; a csúcs-hajlamosak órást is).
A meglévő 13 esti kulcsszót és a **pótolhatatlan órás láncot NEM bolygatjuk**.

## Taxonómia — 5 domén, 28 szó

A `domen` a backenden szabad szöveg (nincs validálás), a magyar címke a frontendé.
Az 5 új domén a régi szórt doméneket VÁLTJA (a meglévő 13 szót is átcímkézzük — ez
adat-biztos: az idősor-adat a szó nevéhez kötött, nem a doménhez).

| Domén (slug) | Magyar címke | Szavak |
|---|---|---|
| `megelhetes` | Megélhetési problémák | rezsi🆕, fizetés🆕, kölcsön🆕, segély🆕, albérlet, hitel, nyugdíj, eladó lakás, benzin, akciós újság, állás, napelem, nyaralás |
| `egeszsegugy` | Egészségügyi problémák | várólista🆕, sürgősségi🆕, háziorvos🆕, műtét🆕, kórház, betegség |
| `oktatas` | Oktatási problémák | pedagógus🆕, iskola🆕 |
| `gazdasag` | Gazdasági bizonytalanság | infláció🆕, munkanélküliség🆕, csőd🆕 |
| `politika` | Politikai elégedetlenség | korrupció🆕, kormány🆕, tüntetés, kormányablak |

(🆕 = új szó; a többi meglévő, csak átcímkézzük.)

## Per-szó gyűjtési profilok (a 15 ÚJ szó)

Időablak-rövidítések: **7d** = órás elsődleges (`now 7-d`); **3m** = napi másodlagos
(`today 3-m`); **12m** = heti másodlagos (`today 12-m`).

| Profil | Szavak | 7d órás | másodlagos ablak | config |
|---|---|---|---|---|
| 1 — lassú strukturális | infláció, rezsi, fizetés, segély, várólista, háziorvos, műtét, iskola, munkanélküliség, csőd | — | 12m (heti) | `oras:false, racs:het` |
| 2 — közepes momentum | kölcsön, sürgősségi | — | 3m (napi) | `oras:false, racs:nap` |
| 3 — esemény/csúcs | pedagógus, korrupció, kormány | ✓ | 12m (heti) | `oras:true, racs:het` |

Mind a 15: `futas: reggel`. **Egy-ablakos**: a reggel-szó másodlagosa CSAK a `racs`-hoz
tartozó egyetlen ablakot gyűjti (nem 3m+12m mindkettőt). A meglévő 13 esti szó
VÁLTOZATLAN (mindkét másodlagos ablak, `oras:true`, `futas:este`).

## Architektúra — komponensek és változások

### A. Config-séma (`trendfigyelo/config.py`)

- `KulcsszoTetel` namedtuple bővítése két új, ALAPÉRTELMEZETT mezővel:
  `KulcsszoTetel(kifejezes, domen, tipus, racs, oras=True, futas="este")`.
  Az alapértékek a meglévő 13 szót és minden pozicionális konstrukciót visszafelé
  kompatibilisen hagynak (de a pozicionális hívóhelyeket — tesztek, `masodlagos_only`
  — végig kell nézni; lásd Kockázatok).
- `_kulcsszavak_beolvas` parse+validáció (a `racs` mintájára):
  `oras` → bool (különben `KonfigHiba`); `futas` ∈ {`reggel`, `este`} (különben `KonfigHiba`).
- Új segéd: `masodlagos_timeframek(tetel)` — a szó másodlagos időablakai:
  - `futas == "este"` → `MASODLAGOS_TIMEFRAMEK` (mindkettő: 3m, 12m) — VÁLTOZATLAN a meglévőknek.
  - `futas == "reggel"` → `[RACS_IDOKERET[tetel.racs]]` (egyetlen ablak: nap→3m, het→12m).
  Ez az „egy-ablakos csak az újakra" viselkedés egyetlen igazságforrása; minden
  másodlagos-cellát számoló/gyűjtő kód ezen megy át.
- A `youtube` lista változatlan (nem kap `oras`/`futas`-t; a youtube-ág külön út).

### B. Elsődleges (órás) gyűjtés `oras`-szűréssel (`trendfigyelo/kulcsszavak.py`)

- `gyujt(kliens, config, most)` a főloopban (`:168`) CSAK azokra a szavakra kér órás
  `now 7-d`-t, amelyekre `tetel.oras` igaz ÉS a szó a futás módjához tartozik (lásd C).
  A profil-1/2 szavak (oras:false) KIMARADNAK az órás ágból (nincs `kulcsszo_nyers`/lánc
  bejegyzésük — ez szándékos).
- A `gyujt` részleges-mentés szerződése (`e.reszleges` a `pontok/napi_pontok/nyers_sorozatok`-on)
  a szűrt listával konzisztens marad.

### C. Futtatás — reggel a reggel-részhalmazt gyűjti (`trendfigyelo/futtato.py`)

A 6 bináris `csak_felkapott` kapu KULCSSZÓ-RÉSZHALMAZ-tudatossá válik. A futás
kulcsszó-részhalmaza:
`futas_szavak = [t for t in config.osszes_kulcsszo() if t.futas == ("reggel" if csak_felkapott else "este")]`.

- **Elsődleges ág (`:337-342`)**: reggel-módban NEM ürít nullára, hanem meghívja a
  `gyujt`-öt a reggel-részhalmaz `oras:true` szavaira (profil 3). Este-módban a
  meglévő 13-ra (mind oras:true), változatlanul.
- **Másodlagos ág (`:351-352`)**: reggel-módban is FUT, a reggel-részhalmazra, DEDIKÁLT
  budgettel (lásd E) — a `_masodlagos_ag` és a `masodlagos_szavak_ma` a részhalmazon
  + a `masodlagos_timeframek(tetel)` egy-ablakán operál.
- **`kulcsszo_nyers.json` / `kulcsszo_lanc.json` (`:426-434`)**: reggel a profil-3
  szavak órás sorozatát írja — **PER-SZÓ UPSERT-tel a meglévő fájlba** (SOHA nem
  csonkolja/klobborálja az esti 13 szó pótolhatatlan sorozatát). Ez a legkritikusabb
  pont — külön teszt igazolja (lásd Tesztelés). (A `nyers_kimenet.ir_gordulo` /
  `lanc.frissit_lanc` per-szó merge-viselkedését igazolni/biztosítani kell.)
- **`tortenet.json` (`:418`)** + regresszió (`:449-504`): a reggel-részhalmazra is
  lefut (a profil-3 szavak napi pontjaira), a részhalmazon.

### D. `legfrissebb.json` kulcsszó-blokk: MERGE-tudatos (`trendfigyelo/json_export.py`)

Ma: reggel „megőrzi a teljes régi blokkot", este „teljesen felülír". Mostantól MINDKÉT
futás a SAJÁT részhalmaza szavait írja a kulcsszó-blokkba, a MÁSIK futás szavait
megőrizve (per-szó merge, nem teljes csere). Így a reggel+este együtt teljes blokkot
ad; egyik sem törli a másik szavait.

### E. Reggeli másodlagos budget + mód-tudatos plafon (`trendfigyelo/futtato.py`)

- Új konstans `MAX_MASODLAGOS_REGGELI` (javaslat: **8**, tunable) — a reggeli futás
  másodlagos-cella cap-je, KÜLÖN az esti `MAX_MASODLAGOS_NAPI=2`-től. A reggel-részhalmaz
  ~15 szavának egy-ablakos másodlagosát ~2 reggel alatt körbejárja (staleness szerint).
- **Mód-tudatos plafon**: `tervezett_hivasszam(config, mode)` és `_szamitott_plafon(config, mode)`
  a futás részhalmazát számolja:
  - reggel: `2 (felkapott+rss) + trend_idosor_max + trend_idosor_rekesz_max + len(reggel oras:true szavak) + MAX_MASODLAGOS_REGGELI`.
  - este: a mai formula (13 szó), VÁLTOZATLAN.
  A `main()` (`:607-616`) a `mode`-ot átadja a plafon-számításnak (ma nem teszi — ez a rés).

### F. Frontend — 5 új domén (`docs/js/app.js`)

- `DOMEN_MAGYAR` (`:577-581`): az 5 új slug→címke felvétele
  (`megelhetes`→„Megélhetési problémák", `egeszsegugy`→„Egészségügyi problémák",
  `oktatas`→„Oktatási problémák", `gazdasag`→„Gazdasági bizonytalanság",
  `politika`→„Politikai elégedetlenség"). A régi, már nem használt slugok elhagyhatók.
- `DOMEN_SORREND` (`:583-584`): az 5 új slug beillesztése a kívánt megjelenítési
  sorrendbe (a `null`→„Egyéb" vödör a végén marad, biztonsági defaultként).
- A youtube-tab `YT_DOMEN_MAGYAR` (`youtube.js`) KÜLÖN, ÉRINTETLEN.

### G. Config-adat (`config.yaml`)

- A 15 új szó felvétele a fenti profilokkal (`oras`/`futas`/`racs`/`tipus`/`domen`).
- A meglévő 13 szó `domen`-jének átírása az 5 új doménre (a Taxonómia tábla szerint);
  `oras`/`futas` NÁLUK nem szükséges (a defaultok: `oras:true, futas:este`).

## Tesztelés (TDD, valós RED→GREEN)

- **Config**: `oras`/`futas` parse+validáció (jó/rossz érték), default (`oras:true, futas:este`);
  `masodlagos_timeframek` (este→mindkettő, reggel→egy ablak a racs szerint).
- **gyujt**: `oras:false` szó KIMARAD az órás ágból; `oras:true` benne van.
- **futtat reggel**: a reggel-részhalmaz profil-3 szavaira órás gyűjtés; a
  reggel-részhalmazra másodlagos; az esti 13 NEM gyűjtődik reggel; **`kulcsszo_nyers`/`lanc`
  PER-SZÓ UPSERT** — egy reggeli profil-3 írás NEM törli az esti szó sorozatát (kritikus,
  pótolhatatlan-adat védelme).
- **legfrissebb merge**: reggel a saját szavait írja, az esti szavakat megőrzi és fordítva;
  a kettő együtt teljes blokk.
- **plafon mód-tudatos**: reggel plafon a reggel-részhalmazt tükrözi; este változatlan;
  a `main` a `mode`-ot átadja.
- **másodlagos reggeli budget**: reggel `MAX_MASODLAGOS_REGGELI` cap, az esti `2` cap
  ÉRINTETLEN; a reggel-szó másodlagosa az egy-ablakot gyűjti.
- **Frontend (Playwright)**: az 5 domén magyar címkével + sorrendben jelenik meg; egy új
  szó a helyes doménbe kerül; ismeretlen domén továbbra is „Egyéb".

## Nem-cél (YAGNI)

- A meglévő 13 esti szó gyűjtése/időablakai VÁLTOZATLANOK (csak a `domen`-címke).
- A youtube-ág érintetlen.
- Nincs cron/ütemezés-változás: a reggeli futás már `--mode reggel`-lel fut, a
  kulcsszó-munka ezen belül történik (a `reggeli.yml` YAML valószínűleg nem változik;
  a plafon/hívásszám a kódból jön).
- Nincs egyedi-trend unió, nincs új adatfájl (a meglévő `kulcsszo_*` fájlokba merge-elünk).

## Kockázatok

- **Pótolhatatlan lánc (LEGNAGYOBB):** a reggeli profil-3 órás írásának PER-SZÓ
  upsertnek kell lennie a `kulcsszo_nyers.json`/`kulcsszo_lanc.json`-ba — bármilyen
  teljes-fájl felülírás az esti 13 szó pótolhatatlan sorozatát törölné. A
  `nyers_kimenet.ir_gordulo`/`lanc.frissit_lanc` merge-viselkedését a terv első
  backend-taskja IGAZOLJA (olvasás), és ha nem per-szó, akkor per-szó merge-t vezet be.
- **6 kapu + merge szemantika:** a `csak_felkapott` kapuk és a `legfrissebb`/`nyers`
  „mind vagy semmi" logikája részhalmaz-/merge-tudatossá válik — sok mozgó rész, gondos
  integráció-teszt kell (reggel-részhalmaz vs este-részhalmaz izoláció).
- **`KulcsszoTetel` pozicionális namedtuple:** a 2 új mező előtt `grep 'KulcsszoTetel('`
  minden konstrukcióra (tesztek, `masodlagos_only.py`) — a defaultok segítenek, de a
  pozicionális hívások ellenőrzendők.
- **Reggeli futásidő/429:** a reggel +3 órás + ~8 másodlagos hívást kap (backoff-fal);
  a meglévő 429-kezelés fedi, de az első éles reggeli futás FIGYELENDŐ.
- **Elemzés (`elemzo.py`):** a napi AI-elemzés kulcsszó-része az új domének/szavak
  adatát is látja — valószínűleg adat-vezérelt, de a terv IGAZOLJA, hogy nincs
  bedrótozott régi-domén feltevés.
