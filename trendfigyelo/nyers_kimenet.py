"""Nyers órás kulcsszó-kimenet szerződése (Phase 2.5).

Ebben a taskban (Task 3) csak a **szerződés-validátor** él; a gördülő-ablakú
író (Task 6) később kerül ide. A validált rekord-alak — egy kulcsszó nyers órás
sorozata egy futásból:

    {
      "kulcsszo": str,               # nem üres
      "ablak_kezdet_utc": str,       # ISO, a lekérdezés ablakának kezdete
      "ablak_veg_utc": str,          # ISO, > ablak_kezdet_utc
      "pontok": [                    # nem üres
        {"idopont_utc": str, "ertek": int | "", "reszleges": bool},
        ...
      ],
    }

A `reszleges` a részleges-farok (Trends `isPartial`) véglegesség-jelölése
(spec 4.3) — pontonként kötelező bool.
"""

from datetime import datetime


def _iso(x) -> bool:
    """Igaz, ha x ISO-időbélyeg stringként értelmezhető."""
    try:
        datetime.fromisoformat(x)
        return True
    except (ValueError, TypeError):
        return False


def ervenyes_nyers_rekord(rek) -> list:
    """A rekord szerződés-hibáinak listája; ÜRES lista = érvényes."""
    if not isinstance(rek, dict):
        return ["a rekord nem dict"]
    hibak = []

    if not isinstance(rek.get("kulcsszo"), str) or not rek.get("kulcsszo"):
        hibak.append("kulcsszo: nem üres string kell")

    kezd, veg = rek.get("ablak_kezdet_utc"), rek.get("ablak_veg_utc")
    if not _iso(kezd):
        hibak.append("ablak_kezdet_utc: hiányzó vagy nem ISO időbélyeg")
    if not _iso(veg):
        hibak.append("ablak_veg_utc: hiányzó vagy nem ISO időbélyeg")
    if _iso(kezd) and _iso(veg):
        try:
            if datetime.fromisoformat(kezd) >= datetime.fromisoformat(veg):
                hibak.append("ablak_kezdet_utc < ablak_veg_utc kell")
        except TypeError:
            # tz-aware és tz-naiv határ keveréke — a guard reportálja, ne szálljon el
            hibak.append("ablak_kezdet_utc/veg: összehasonlíthatatlan időzóna (aware vs naiv)")

    pontok = rek.get("pontok")
    if not isinstance(pontok, list) or not pontok:
        hibak.append("pontok: nem üres lista kell")
    else:
        for i, p in enumerate(pontok):
            if not isinstance(p, dict):
                hibak.append(f"pontok[{i}]: nem dict")
                continue
            if not _iso(p.get("idopont_utc")):
                hibak.append(f"pontok[{i}].idopont_utc: hiányzó vagy nem ISO")
            ert = p.get("ertek", "___hiany___")
            # bool az int altípusa, de itt nem elfogadott érték
            if not ((isinstance(ert, int) and not isinstance(ert, bool)) or ert == ""):
                hibak.append(f"pontok[{i}].ertek: int vagy '' kell")
            if not isinstance(p.get("reszleges"), bool):
                hibak.append(f"pontok[{i}].reszleges: bool kell (véglegesség-jelölés)")
    return hibak
