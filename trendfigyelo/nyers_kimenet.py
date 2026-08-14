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

    # 1) VISSZAOLVASOTT örökség: sérült rekord KARANTÉN (kihagyás + naplózás)
    for kif in list(kulcsszavak):
        tiszta = []
        for r in kulcsszavak[kif]:
            hibak = ervenyes_nyers_rekord(r)
            if hibak:
                print(f"FIGYELEM: sérült nyers rekord karanténba ({kif}): {hibak}")
                continue
            tiszta.append(r)
        if tiszta:
            kulcsszavak[kif] = tiszta
        else:
            del kulcsszavak[kif]

    # 2) FRISS producer-kimenet: hibás rekord a MI bugunk → hard fail
    for kifejezes, rek in nyers_sorozatok.items():
        rendezett = _rendezett(rek)
        hibak = ervenyes_nyers_rekord(rendezett)
        if hibak:
            raise ValueError(f"{kifejezes}: érvénytelen friss nyers rekord: {hibak}")
        kulcsszavak.setdefault(kifejezes, []).append(rendezett)

    # 3) retenció: minden megmaradó vég már érvényes tz-aware → egyszerű összehasonlítás
    vegek = [_aware_dt(r["ablak_veg_utc"]) for lst in kulcsszavak.values() for r in lst]
    if vegek:
        hatar = max(vegek) - timedelta(days=megtartott_nap)
        for kif in list(kulcsszavak):
            kulcsszavak[kif] = [r for r in kulcsszavak[kif]
                                if _aware_dt(r["ablak_veg_utc"]) >= hatar]
            if not kulcsszavak[kif]:
                del kulcsszavak[kif]           # ne maradjon üres lista a kulcsszóra

    fajl.parent.mkdir(parents=True, exist_ok=True)
    fajl.write_text(json.dumps(adat, ensure_ascii=False, indent=2), encoding="utf-8")
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

    # 1) VISSZAOLVASOTT örökség: sérült rekord KARANTÉN
    for kif in list(kulcsszavak):
        tiszta = []
        for r in kulcsszavak[kif]:
            hibak = ervenyes_masodlagos_rekord(r)
            if hibak:
                print(f"FIGYELEM: sérült másodlagos rekord karanténba ({kif}): {hibak}")
                continue
            tiszta.append(r)
        if tiszta:
            kulcsszavak[kif] = tiszta
        else:
            del kulcsszavak[kif]

    # 2) FRISS producer-kimenet: hibás rekord a MI bugunk → hard fail
    for kifejezes, rek in sorozatok.items():
        rendezett = _rendezett(rek)
        hibak = ervenyes_masodlagos_rekord(rendezett)
        if hibak:
            raise ValueError(f"{kifejezes}: érvénytelen friss másodlagos rekord: {hibak}")
        kulcsszavak.setdefault(kifejezes, []).append(rendezett)

    # 3) retenció: szavanként a megtartott_db legutóbbi rekord lekerdezes_utc szerint (adat-relatív)
    for kif in list(kulcsszavak):
        kulcsszavak[kif] = sorted(
            kulcsszavak[kif],
            key=lambda r: _aware_dt(r.get("lekerdezes_utc")) or _MIN_DT,
            reverse=True,
        )[:megtartott_db]

    fajl.parent.mkdir(parents=True, exist_ok=True)
    fajl.write_text(json.dumps(adat, ensure_ascii=False, indent=2), encoding="utf-8")
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
