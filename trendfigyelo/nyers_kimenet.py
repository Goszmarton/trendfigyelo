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
