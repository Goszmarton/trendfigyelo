"""Nyers órás kulcsszó-kimenet: szerződés-validátor + gördülő verziókövetett író.

A validált rekord-alak — egy kulcsszó nyers órás sorozata egy futásból:

    {
      "kulcsszo": str,               # nem üres
      "ablak_kezdet_utc": str,       # tz-aware UTC ISO, a lekérdezés ablakának kezdete
      "ablak_veg_utc": str,          # tz-aware UTC ISO, > ablak_kezdet_utc
      "pontok": [                    # nem üres; minden idopont az ablakon belül (inkluzív)
        {"idopont_utc": str, "ertek": int | "", "reszleges": bool},
        ...
      ],
    }

Szerződés-szigorítás (Task 6): minden időbélyeg KÖTELEZŐEN tz-aware UTC ISO
(naiv/date-only elutasítva) — a keresztfutásos láncoláshoz (spec 4.2) egyértelmű
UTC-szemantika kell; és minden `idopont_utc` az `[ablak_kezdet_utc, ablak_veg_utc]`
ablakon belül esik (inkluzív). A pontok sorrendjét a validátor NEM írja elő (a
gördülő író rendez); a `reszleges` a részleges-farok (Trends `isPartial`)
véglegesség-jelölése (spec 4.3) — pontonként kötelező bool.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import seged
from .config import RACS_IDOKERET, TIMEFRAME_RACS

# aware sentinel a rendezéshez: érvénytelen/hiányzó időbélyeg előre (a validátor jelzi)
_MIN_DT = datetime.min.replace(tzinfo=timezone.utc)


def _aware_dt(x):
    """Parse-olt tz-aware datetime, ha x tz-aware ISO string; különben None.

    A naiv és a date-only string elutasított (None) — a nyers kimenet
    keresztfutásos láncoláshoz készül, ott a naiv/kétértelmű időbélyeg latens bug.
    """
    if not isinstance(x, str):
        return None
    try:
        dt = datetime.fromisoformat(x)
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else None


# KARANTEN-LEGACY seam (2026-08-20): a jövőbeli KÖTELEZŐ mezőket IDE veszi fel a fejlesztő — EGY deklaratív hely.
# A FRISS-írás validátora megköveteli (hard-fail), a LEMEZ-örökség karanténja ELLENBEN NEM dob rá (a drop a
# `_strukturalis_hibak` zárt (iii) listája; hiányzó mező → MEGTARTÁS + FIGYELEM). Így egy új kötelező mező NEM
# üríti ki visszamenőleg a lemezt. A teszt EZEN a listán át injektál (nem monkeypatch a validátorra).
_TOVABBI_KOTELEZO_MEZOK: list = []          # mezőnevek; jelen-és-truthy kell


def ervenyes_nyers_rekord(rek) -> list:
    """A rekord szerződés-hibáinak listája; ÜRES lista = érvényes."""
    if not isinstance(rek, dict):
        return ["a rekord nem dict"]
    hibak = []

    if not isinstance(rek.get("kulcsszo"), str) or not rek.get("kulcsszo"):
        hibak.append("kulcsszo: nem üres string kell")

    kezd_dt = _aware_dt(rek.get("ablak_kezdet_utc"))
    veg_dt = _aware_dt(rek.get("ablak_veg_utc"))
    if kezd_dt is None:
        hibak.append("ablak_kezdet_utc: hiányzó vagy nem tz-aware UTC ISO")
    if veg_dt is None:
        hibak.append("ablak_veg_utc: hiányzó vagy nem tz-aware UTC ISO")
    if kezd_dt is not None and veg_dt is not None and kezd_dt >= veg_dt:
        hibak.append("ablak_kezdet_utc < ablak_veg_utc kell")

    pontok = rek.get("pontok")
    if not isinstance(pontok, list) or not pontok:
        hibak.append("pontok: nem üres lista kell")
    else:
        for i, p in enumerate(pontok):
            if not isinstance(p, dict):
                hibak.append(f"pontok[{i}]: nem dict")
                continue
            p_dt = _aware_dt(p.get("idopont_utc"))
            if p_dt is None:
                hibak.append(f"pontok[{i}].idopont_utc: hiányzó vagy nem tz-aware UTC ISO")
            elif kezd_dt is not None and veg_dt is not None and not (kezd_dt <= p_dt <= veg_dt):
                hibak.append(f"pontok[{i}].idopont_utc: az ablakon kívül esik")
            ert = p.get("ertek", "___hiany___")
            # bool az int altípusa, de itt nem elfogadott érték
            if not ((isinstance(ert, int) and not isinstance(ert, bool)) or ert == ""):
                hibak.append(f"pontok[{i}].ertek: int vagy '' kell")
            if not isinstance(p.get("reszleges"), bool):
                hibak.append(f"pontok[{i}].reszleges: bool kell (véglegesség-jelölés)")
    for mezo in _TOVABBI_KOTELEZO_MEZOK:            # seam: jövőbeli kötelező mezők (ma üres → no-op)
        if isinstance(rek, dict) and not rek.get(mezo):
            hibak.append(f"{mezo}: hiányzó (kötelező mező)")
    return hibak


def _rendezett(rek) -> dict:
    """A rekord másolata, a pontok idopont_utc szerint növekvő sorrendben (Q1: az író rendez).

    Parse-olt datetime szerint rendez (offset-agnosztikus, nem a nyers string),
    így tetszőleges tz-aware offsetnél is időrendi; a validátor sorrendet nem ír
    elő, de a lemez-artefakt a láncoláshoz mindig időrendben kerül ki.
    """
    r = dict(rek)
    pontok = r.get("pontok")
    if isinstance(pontok, list):
        r["pontok"] = sorted(
            pontok,
            key=lambda p: (_aware_dt(p.get("idopont_utc")) if isinstance(p, dict) else None) or _MIN_DT,
        )
    return r


# ---------- KARANTEN-LEGACY Szelet 1: fill-only migráció + zárt (iii) dobási lista ----------

def _strukturalis_hibak(rek) -> list:
    """A ZÁRT (iii) dobási lista — CSAK ez ürítheti a lemezt visszaolvasáskor: nincs egyetlen pont sem,
    vagy a pont elhelyezhetetlen (nem dict / hiányzó-érvénytelen `idopont_utc`). MINDEN MÁS hiányzó/rossz
    mező (az ISMERETLEN is) → MEGTARTÁS. A pontszintű finomítás (egy rossz pont ne dobja az egészet) = Szelet 2."""
    if not isinstance(rek, dict):
        return ["a rekord nem dict"]
    pontok = rek.get("pontok")
    if not isinstance(pontok, list) or not pontok:
        return ["pontok: nincs egyetlen pont sem"]
    for i, p in enumerate(pontok):
        if not isinstance(p, dict):
            return [f"pontok[{i}]: elhelyezhetetlen pont (nem dict)"]
        if _aware_dt(p.get("idopont_utc")) is None:
            return [f"pontok[{i}].idopont_utc: elhelyezhetetlen (hiányzó/érvénytelen)"]
    return []


def _migral_nyers_hianyzo(rek, kulcs):
    """Fill-only visszamenőleges migráció: CSAK HIÁNYZÓ mezőt tölt, meglévőt SOHA nem ír felül (a MINOR-2
    `ablak_veg_utc`-horgony védelme). Levezetés meglévő adatból/kulcsból, NEM beírt konstansból."""
    if not isinstance(rek, dict):
        return rek
    rek = dict(rek)
    if not rek.get("kulcsszo"):
        rek["kulcsszo"] = kulcs                              # a konténer-kulcs a szó identitása
    pontok = rek.get("pontok")
    if isinstance(pontok, list) and pontok:
        rek["pontok"] = [                                    # reszleges ← False (spec 4.3 véglegesség-default)
            ({**p, "reszleges": False} if isinstance(p, dict) and not isinstance(p.get("reszleges"), bool) else p)
            for p in pontok
        ]
        idok = sorted(d for p in pontok if isinstance(p, dict)
                      for d in (_aware_dt(p.get("idopont_utc")),) if d is not None)
        if idok:                                             # ablak ← a pontok tényleges min/max-a (tiszta levezetés)
            rek.setdefault("ablak_kezdet_utc", idok[0].isoformat())
            rek.setdefault("ablak_veg_utc", idok[-1].isoformat())
    return rek


def _migral_masodlagos_hianyzo(rek, kulcs):
    """A bázis migráció + a másodlagos racs↔timeframe kölcsönös levezetés. A 207–208 inline timeframe-ág
    BEOLVAD ide — EGY mechanizmus marad."""
    rek = _migral_nyers_hianyzo(rek, kulcs)
    if not isinstance(rek, dict):
        return rek
    rek = dict(rek)
    if not rek.get("timeframe") and RACS_IDOKERET.get(rek.get("racs")):
        rek["timeframe"] = RACS_IDOKERET[rek["racs"]]        # timeframe ← racs
    if not rek.get("racs") and TIMEFRAME_RACS.get(rek.get("timeframe")):
        rek["racs"] = TIMEFRAME_RACS[rek["timeframe"]]       # racs ← timeframe (csak ha HIÁNYZIK)
    return rek


def _tisztit_pontok(rek):
    """Szelet 2 — PONT-szintű zárt (iii) dobás: a visszaolvasott rekordból ELDOBJA az ELHELYEZHETETLEN pontokat
    (nem dict / hiányzó-érvénytelen `idopont_utc`), a TÖBBIT MEGTARTJA. `(rek, eldobott_szam)`. Ha MINDEN pont
    elhelyezhetetlen → a `pontok` üres lesz → a `_strukturalis_hibak` „nincs pont" ága ejti a rekordot."""
    if not isinstance(rek, dict) or not isinstance(rek.get("pontok"), list):
        return rek, 0
    jo = [p for p in rek["pontok"] if isinstance(p, dict) and _aware_dt(p.get("idopont_utc")) is not None]
    eldobott = len(rek["pontok"]) - len(jo)
    if eldobott:
        rek = dict(rek)
        rek["pontok"] = jo
    return rek, eldobott


def _karantenaz(kulcsszavak, migral, valid) -> None:
    """VISSZAOLVASÁS-elnéző karantén (helyben módosít): a rekordot előbb fill-only migrálja, majd PONT-szinten
    tisztítja (elhelyezhetetlen pont eldobva), végül DOBJA CSAK ha `_strukturalis_hibak` (iii — pl. nincs pont).
    Minden más szerződés-hibát MEGTART + FIGYELEM. Üres szó → törlés."""
    for kif in list(kulcsszavak):
        tiszta = []
        for r in kulcsszavak[kif]:
            r = migral(r, kif)
            r, eldobott_pont = _tisztit_pontok(r)
            if eldobott_pont:
                print(f"FIGYELEM: {eldobott_pont} elhelyezhetetlen pont ELDOBVA, a rekord MEGTARTVA ({kif})")
            strukt = _strukturalis_hibak(r)
            if strukt:
                print(f"FIGYELEM: strukturálisan sérült rekord karanténba ({kif}): {strukt}")
                continue
            maradek = valid(r)
            if maradek:                                      # megtartjuk, de HANGOSAN jelöljük a hiányt
                print(f"FIGYELEM: hiányos rekord MEGTARTVA + jelölve ({kif}): {maradek}")
            tiszta.append(r)
        if tiszta:
            kulcsszavak[kif] = tiszta
        else:
            del kulcsszavak[kif]


def ir_gordulo(docs_data, nyers_sorozatok: dict, megtartott_nap: int = 14) -> Path:
    """A friss nyers rekordokat kulcsszavanként a kulcsszo_nyers.json-ba upsertli.

    Gördülő retenció: a legkésőbbi ismert `ablak_veg_utc`-hez képest (adat-relatív,
    NEM falióra) a `megtartott_nap`-nál régebbi rekordokat eldobja. A pontok
    időrendbe rendezve kerülnek lemezre. Fájl-alak: {"kulcsszavak": {kifejezes: [rekord, ...]}}.

    Validálás forrás szerint kettéválasztva (Task 6 review):
    - a FRISS producer-rekord hibája a MI bugunk → ValueError (fail-loud);
    - a LEMEZRŐL visszaolvasott örökség sérült rekordja KARANTÉN (kihagyás +
      naplózás), hogy egyetlen romlott legacy-rekord ne bénítsa meg a napi írást.
    """
    fajl = Path(docs_data) / "kulcsszo_nyers.json"
    if fajl.exists():
        adat = json.loads(fajl.read_text(encoding="utf-8"))
    else:
        adat = {"kulcsszavak": {}}
    kulcsszavak = adat.setdefault("kulcsszavak", {})

    # 1) VISSZAOLVASOTT örökség: VISSZAOLVASÁS-elnéző karantén (drop CSAK strukturális; hiányzó mező MEGMARAD)
    _karantenaz(kulcsszavak, _migral_nyers_hianyzo, ervenyes_nyers_rekord)

    # 2) FRISS producer-kimenet: hibás rekord a MI bugunk → hard fail
    for kifejezes, rek in nyers_sorozatok.items():
        rendezett = _rendezett(rek)
        hibak = ervenyes_nyers_rekord(rendezett)
        if hibak:
            raise ValueError(f"{kifejezes}: érvénytelen friss nyers rekord: {hibak}")
        kulcsszavak.setdefault(kifejezes, []).append(rendezett)

    # 3) retenció (MINOR-2): a horizont a legfrissebb VALÓS adatpontra (max idopont_utc) áll — NEM a
    #    max(ablak_veg_utc)-ra. Egy sérült/jövőbeli ablak_veg (metaadat) így nem húzhatja a hatar-t a jövőbe
    #    és nem gördítheti ki a PÓTOLHATATLAN múltat; a future-veg rekord MEGMARAD (fail-open). Adat-relatív.
    pont_idok = [d for lst in kulcsszavak.values() for r in lst for p in (r.get("pontok") or [])
                 for d in (_aware_dt(p.get("idopont_utc")),) if d is not None]
    if pont_idok:
        hatar = max(pont_idok) - timedelta(days=megtartott_nap)
        for kif in list(kulcsszavak):
            kulcsszavak[kif] = [r for r in kulcsszavak[kif]
                                if _aware_dt(r["ablak_veg_utc"]) >= hatar]
            if not kulcsszavak[kif]:
                del kulcsszavak[kif]           # ne maradjon üres lista a kulcsszóra

    seged.atomi_ir_szoveg(fajl, json.dumps(adat, ensure_ascii=False, indent=2))   # ATOMI-IRAS (pótolhatatlan)
    return fajl


# ---------- Task 2 (Phase 4): másodlagos (nap/het) nyers kimenet ----------

_MASODLAGOS_RACSOK = {"nap", "het"}


def ervenyes_masodlagos_rekord(rek) -> list:
    """A másodlagos rekord szerződés-hibái; ÜRES lista = érvényes.

    A bázis `ervenyes_nyers_rekord`-ot ÚJRAHASZNÁLJA (ablak/pontok/ertek/reszleges),
    és hozzáadja a másodlagos-specifikus mezőket: `racs` ∈ {nap, het} és a
    kötelező `lekerdezes_utc` (tz-aware UTC ISO — a 3 pillanatkép rendezéséhez).
    """
    hibak = ervenyes_nyers_rekord(rek)
    if not isinstance(rek, dict):
        return hibak
    if rek.get("racs") not in _MASODLAGOS_RACSOK:
        hibak.append('racs: "nap" vagy "het" kell')
    if _aware_dt(rek.get("lekerdezes_utc")) is None:
        hibak.append("lekerdezes_utc: hiányzó vagy nem tz-aware UTC ISO")
    if not rek.get("timeframe"):
        hibak.append("timeframe: hiányzó (a szó × timeframe séma kulcsa)")
    return hibak


def ir_masodlagos(docs_data, sorozatok: dict, megtartott_db: int = 3) -> Path:
    """A friss nap/het rekordokat a kulcsszo_masodlagos_nyers.json-ba upsertli.

    Retenció ADAT-relatív: szavanként a `megtartott_db` legutóbbi rekord marad,
    `lekerdezes_utc` szerint (NEM falióra) — ha egy szó nem frissül, a története
    NEM ürül. A karantén/hard-fail kettéválasztás az ir_gordulo mintájára:
    - LEMEZRŐL visszaolvasott sérült örökség → karantén (kihagyás + naplózás);
    - FRISS producer-rekord hibája a MI bugunk → ValueError (fail-loud).
    """
    fajl = Path(docs_data) / "kulcsszo_masodlagos_nyers.json"
    if fajl.exists():
        adat = json.loads(fajl.read_text(encoding="utf-8"))
    else:
        adat = {"kulcsszavak": {}}
    kulcsszavak = adat.setdefault("kulcsszavak", {})

    # 1) VISSZAOLVASOTT örökség: VISSZAOLVASÁS-elnéző karantén (a 207–208 timeframe-migráció BEOLVAD a rétegbe)
    _karantenaz(kulcsszavak, _migral_masodlagos_hianyzo, ervenyes_masodlagos_rekord)

    # 2) FRISS producer-kimenet: hibás rekord a MI bugunk → hard fail
    for kifejezes, rek in sorozatok.items():
        rendezett = _rendezett(rek)
        hibak = ervenyes_masodlagos_rekord(rendezett)
        if hibak:
            raise ValueError(f"{kifejezes}: érvénytelen friss másodlagos rekord: {hibak}")
        kulcsszavak.setdefault(kifejezes, []).append(rendezett)

    # 3) retenció: szavanként ÉS TIMEFRAME-enként a megtartott_db legutóbbi rekord (adat-relatív, lekerdezes_utc
    #    szerint). A per-szó több-timeframe világban a két timeframe NEM verseng egy közös 3 helyért.
    for kif in list(kulcsszavak):
        tf_csoport = {}
        for r in kulcsszavak[kif]:
            tf_csoport.setdefault(r.get("timeframe"), []).append(r)
        megtartott = []
        for rekk in tf_csoport.values():
            megtartott.extend(sorted(rekk, key=lambda r: _aware_dt(r.get("lekerdezes_utc")) or _MIN_DT,
                                     reverse=True)[:megtartott_db])
        kulcsszavak[kif] = megtartott

    seged.atomi_ir_szoveg(fajl, json.dumps(adat, ensure_ascii=False, indent=2))   # ATOMI-IRAS
    return fajl


def elavult_masodlagos_szavak(sorozatok, most, kuszob_nap=10):
    """A `sorozatok` (szó→rekordlista) azon szavai, amelyek legfrissebb `lekerdezes_utc`-je
    kora `> kuszob_nap` nap — kor szerint CSÖKKENŐ, tie-break ábécé. Alak: [(kif, napok), ...].

    CSAK a jelenlévő kulcsokon iterál → az ora-szavak (sosem másodlagos-kulcs) SOSEM jelennek
    meg, a never-collected (kulcs nélküli) nem-ora szó SEM elavult (a rotációba még be nem
    került → a Task 5 ütemező dolga). Kulcs jelen, de nincs érvényes `lekerdezes_utc` →
    "nincs adat = elavult" (napok=None, legelöl). A `>` határ: 10 nap OK, 11 naptól riaszt.
    """
    elavultak = []
    for kif, rekordok in sorozatok.items():
        korok = [_aware_dt(r.get("lekerdezes_utc")) for r in rekordok]
        legfrissebb = max((d for d in korok if d is not None), default=None)
        if legfrissebb is None:
            elavultak.append((kif, None))          # nincs érvényes adat = elavult
            continue
        napok = (most - legfrissebb).days
        if napok > kuszob_nap:
            elavultak.append((kif, napok))
    # None (nincs adat) = maximálisan elavult → legelöl; azonos kor → ábécé
    elavultak.sort(key=lambda t: (-(t[1] if t[1] is not None else 10**9), t[0]))
    return elavultak
