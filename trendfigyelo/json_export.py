"""JSON-export a statikus webnek: legfrissebb, tortenet, napi trendlista-történet."""

import json
from pathlib import Path


def _szam_e(x):
    try:
        float(x)
        return x != ""
    except (ValueError, TypeError):
        return False


def _ertek(pont):
    """A normalizált érték, ha érvényes; különben a nyers; különben None."""
    for kulcs in ("normalizalt_ertek", "nyers_ertek"):
        if kulcs in pont and _szam_e(pont[kulcs]):
            return float(pont[kulcs])
    return None


def kulcsszo_napi_osszesites(kulcsszo_pontok) -> list:
    """Kulcsszavanként átlag + csúcs + érvényes-pontszám a NEM-nulla normalizált értékből.

    Kihagyva: a referencia-érvénytelen kötegek pontjai (referencia_ervenyes False),
    és a 0/üres értékek (0 = a Google mérési küszöbe alatt = nem mérhető).
    """
    csoportok = {}
    for p in kulcsszo_pontok:
        if not p.get("referencia_ervenyes", True):
            continue
        ert = _ertek(p)
        if ert is None or ert == 0:
            continue
        rek = csoportok.setdefault(p["kulcsszo"], {"csoport": p.get("csoport", ""), "ertekek": []})
        rek["ertekek"].append(ert)
    eredmeny = []
    for kulcsszo, rek in csoportok.items():
        ek = rek["ertekek"]
        eredmeny.append({
            "kulcsszo": kulcsszo,
            "csoport": rek["csoport"],
            "atlag": round(sum(ek) / len(ek), 2),
            "csucs": round(max(ek), 2),
            "ervenyes_pontok": len(ek),
        })
    return eredmeny


def _ir_json(fajl: Path, adat):
    fajl.parent.mkdir(parents=True, exist_ok=True)
    fajl.write_text(json.dumps(adat, ensure_ascii=False, indent=2), encoding="utf-8")
    return fajl


def _kulcsszo_idosorok(kulcsszo_pontok) -> dict:
    """Kulcsszavanként [{idopont_utc, nyers_ertek, normalizalt_ertek}] a mai grafikonhoz."""
    ki = {}
    for p in kulcsszo_pontok:
        ki.setdefault(p["kulcsszo"], {"csoport": p.get("csoport", ""), "pontok": []})
        ki[p["kulcsszo"]]["pontok"].append({
            "idopont_utc": p.get("idopont_utc", ""),
            "nyers_ertek": p.get("nyers_ertek", ""),
            "normalizalt_ertek": p.get("normalizalt_ertek", ""),
        })
    return ki


def legfrissebb_ir(docs_data, top_trendek, trend_idosorok, kulcsszo_pontok,
                   frissitve_iso, geo) -> Path:
    adat = {
        "geo": geo,
        "frissitve": frissitve_iso,
        "top_trendek": top_trendek,
        "trend_idosorok": trend_idosorok,
        "kulcsszavak": _kulcsszo_idosorok(kulcsszo_pontok),
        "kulcsszo_osszesites": kulcsszo_napi_osszesites(kulcsszo_pontok),
    }
    return _ir_json(Path(docs_data) / "legfrissebb.json", adat)


def tortenet_frissit(docs_data, nap_iso, kulcsszo_pontok) -> Path:
    fajl = Path(docs_data) / "tortenet.json"
    if fajl.exists():
        adat = json.loads(fajl.read_text(encoding="utf-8"))
    else:
        adat = {"napok": []}
    uj_bejegyzes = {"nap": nap_iso, "kulcsszavak": kulcsszo_napi_osszesites(kulcsszo_pontok)}
    adat["napok"] = [b for b in adat["napok"] if b.get("nap") != nap_iso]
    adat["napok"].append(uj_bejegyzes)
    adat["napok"].sort(key=lambda b: b["nap"])
    return _ir_json(fajl, adat)


def tortenet_frissit_napok(docs_data, napi_pontok) -> Path:
    """Több nap upsertje: a legfrissebb nap felülír, a régebbiek insert-if-absent."""
    fajl = Path(docs_data) / "tortenet.json"
    if fajl.exists():
        adat = json.loads(fajl.read_text(encoding="utf-8"))
    else:
        adat = {"napok": []}
    if napi_pontok:
        friss = max(napi_pontok)          # a legfrissebb nap ISO-ja
        meglevo = {b.get("nap") for b in adat["napok"]}
        for nap_iso in sorted(napi_pontok):
            if nap_iso != friss and nap_iso in meglevo:
                continue                  # insert-if-absent: régi napot nem írunk felül
            osszesites = kulcsszo_napi_osszesites(napi_pontok[nap_iso])
            if not osszesites:
                continue
            adat["napok"] = [b for b in adat["napok"] if b.get("nap") != nap_iso]
            adat["napok"].append({"nap": nap_iso, "kulcsszavak": osszesites})
        adat["napok"].sort(key=lambda b: b["nap"])
    return _ir_json(fajl, adat)


def napi_ir(docs_data, nap_iso, top_trendek) -> Path:
    napok_mappa = Path(docs_data) / "napok"
    fajl = napok_mappa / f"{nap_iso}.json"
    _ir_json(fajl, {"nap": nap_iso, "trendek": top_trendek})

    index_fajl = napok_mappa / "index.json"
    if index_fajl.exists():
        index = json.loads(index_fajl.read_text(encoding="utf-8"))
    else:
        index = {"napok": []}
    napok = sorted(set(index.get("napok", [])) | {nap_iso})
    _ir_json(index_fajl, {"napok": napok})
    return fajl
