"""LANC-ORAS (Phase 4, spec §8.2) — órás láncolás: átfedő 7-napos ablakokból egy közös skálájú,
retenciótól FÜGGETLEN, PERZISZTENS sorozat (`kulcsszo_lanc.json`).

A `kulcsszo_nyers.json` 14 nap után kigördül; a lánc-történet CSAK ebben a fájlban él → POTÓLHATATLAN:
- git adat-commit = a backup (a fájl a docs/data/-ban keletkezik);
- NINCS csendes önfelülírás: ha a napi bővítés nem tud LEZÁRT átfedésre épülni → NE írd felül, HANGOS FIGYELEM.
"""

import json
from pathlib import Path

FAJL = "kulcsszo_lanc.json"


def _median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def lancol(rekordok):
    """Átfedő ablakok láncolása egy közös skálájú sorozattá. A LEGRÉGEBBI a referencia (skála=1);
    minden újabb ablakot a KÖZÖS lezárt, NEM-NULLA átfedő pontokból számolt (robusztus, medián) skálázó
    húz a referencia-skálára. Csak a nem-átfedő (új) pontok fűződnek hozzá. Nincs érvényes átfedés (nincs
    közös nem-nulla lezárt pont) → a lánc ott SZAKASZRA bomlik (az új ablaktól újraindul, skála=1).

    Bemenet: rekordok listája (mindegyik {ablak_kezdet_utc, ablak_veg_utc, pontok:[{idopont_utc,ertek,reszleges}]}).
    Visszaad: {ablak_kezdet_utc, ablak_veg_utc, pontok:[{idopont_utc,ertek}], szakasz_kezdet_utc} vagy None.
    A `reszleges: true` záró pont KIMARAD (spec §8.2: csak a lezárt szakaszból).
    """
    rendezett = sorted([r for r in rekordok if r and r.get("pontok")], key=lambda r: r["ablak_veg_utc"])
    if not rendezett:
        return None
    lanc = {p["idopont_utc"]: p["ertek"] for p in rendezett[0]["pontok"] if not p.get("reszleges")}
    szakasz_kezdet = min(lanc) if lanc else rendezett[0]["ablak_kezdet_utc"]
    for rek in rendezett[1:]:
        pontok = {p["idopont_utc"]: p["ertek"] for p in rek["pontok"] if not p.get("reszleges")}
        kozos = [(lanc[t], pontok[t]) for t in pontok if t in lanc and lanc[t] > 0 and pontok[t] > 0]
        if not kozos:                                  # nincs érvényes átfedés → SZAKASZ-törés
            lanc = dict(pontok)
            szakasz_kezdet = min(pontok) if pontok else rek["ablak_kezdet_utc"]
            continue
        skalazo = _median([r / u for r, u in kozos])   # az új ablakot a referencia-skálára húzza
        for t, e in pontok.items():
            if t not in lanc:
                lanc[t] = e * skalazo                   # csak az ÚJ (nem-átfedő) pontok
    sorok = sorted(lanc.items())
    return {"ablak_kezdet_utc": sorok[0][0], "ablak_veg_utc": sorok[-1][0],
            "szakasz_kezdet_utc": szakasz_kezdet,
            "pontok": [{"idopont_utc": t, "ertek": round(e, 4)} for t, e in sorok]}


def _marker_szur(ablakok, marker):
    """A `modszertan_valtas` (marker) ELŐTTI órás pontok kizárása — a lánc a marker előtt NEM folytatható
    (spec §8.2, abszolút határ). marker=None → nincs szűrés. A pont-dátum (idopont_utc[:10]) < marker → kizárva.
    """
    if marker is None:
        return ablakok
    ki = []
    for r in ablakok:
        pontok = [p for p in r["pontok"] if p["idopont_utc"][:10] >= marker]
        if pontok:
            ki.append({**r, "pontok": pontok, "ablak_kezdet_utc": min(p["idopont_utc"] for p in pontok)})
    return ki


def _lanc_rekord(lanc):
    """A tárolt láncot `lancol` bemeneti-rekord alakúra hozza (a bővítés első, referencia eleme)."""
    return {"ablak_kezdet_utc": lanc["ablak_kezdet_utc"], "ablak_veg_utc": lanc["ablak_veg_utc"],
            "pontok": lanc["pontok"]}


def betolt_lanc(docs_data):
    """A tárolt kulcsszo_lanc.json (szó→lánc). Hiányzó/hibás fájl → {} (a bootstrap-ág kezeli)."""
    try:
        return json.loads((Path(docs_data) / FAJL).read_text(encoding="utf-8")).get("kulcsszavak", {})
    except (OSError, ValueError):
        return {}


def frissit_lanc(docs_data, nyers_sorozatok, marker=None):
    """Bootstrap (nincs tárolt lánc) VAGY napi bővítés (a friss ablakot a tárolt lánchoz igazítva).

    GUARD (a POTÓLHATATLANSÁG-őr): ha a bővítés nem tud a tárolt lánc LEZÁRT átfedésére épülni (a friss ablak
    NEM ér vissza a tárolt lánc végéig → szakasz-törés) → a tárolt láncot MEGŐRZI, HANGOS FIGYELEM (megnevezi a
    szót, a megőrzött lánc-véget) — a jó lánc NEM íródik felül üressel/rövidebbel. Csak órás (ora-rács) szavak.
    """
    tarolt = betolt_lanc(docs_data)
    ki = dict(tarolt)                                   # a nem érintett szavak megmaradnak
    for kif, ablakok in nyers_sorozatok.items():
        ablakok = _marker_szur(ablakok, marker)         # §8.2: a marker előtti pont NEM kerül a láncba
        if not ablakok:
            continue
        if kif not in tarolt:
            uj = lancol(ablakok)                        # BOOTSTRAP: az összes retenált ablak
            if uj:
                ki[kif] = uj
            continue
        legujabb = max(ablakok, key=lambda r: r["ablak_veg_utc"])
        uj = lancol([_lanc_rekord(tarolt[kif]), legujabb])   # a tárolt lánc a referencia
        # GUARD: a bővült lánc kezdete NEM csúszhat előre a tároltéhoz képest (szakasz-törés = a friss ablak
        # nem ért vissza) → őrizzük meg a tároltat
        if uj is None or uj["szakasz_kezdet_utc"] > tarolt[kif]["ablak_kezdet_utc"]:
            print(f"FIGYELEM: órás lánc — a(z) {kif!r} bővítése nem tud lezárt átfedésre épülni "
                  f"(a tárolt lánc végét nem éri el a friss ablak); a lánc ÉRINTETLEN "
                  f"(megőrzött vég: {tarolt[kif]['ablak_veg_utc'][:16]}).")
            ki[kif] = tarolt[kif]
        else:
            uj.pop("szakasz_kezdet_utc", None)          # a tárolt alakban nincs szükség rá (1 szakasz)
            ki[kif] = uj
    (Path(docs_data) / FAJL).write_text(
        json.dumps({"kulcsszavak": ki}, ensure_ascii=False), encoding="utf-8")
    return ki
