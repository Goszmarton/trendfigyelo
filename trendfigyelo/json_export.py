"""JSON-export a statikus webnek: legfrissebb, tortenet, napi trendlista-történet."""

import json
from pathlib import Path

from . import seged


def _szam_e(x):
    try:
        float(x)
        return x != ""
    except (ValueError, TypeError):
        return False


def _nyers(pont):
    """A nyers érték számként, ha értelmezhető; különben None."""
    v = pont.get("nyers_ertek")
    return float(v) if _szam_e(v) else None


def kulcsszo_napi_osszesites(kulcsszo_pontok) -> list:
    """Kulcsszavanként átlag + csúcs a NEM-nulla NYERS értékből, + gyakoriság-jel.

    Phase 2.5: szóló lekérdezés, nincs normalizálás/horgony. A 0/üres értékek az
    átlagból kimaradnak (0 = a Google mérési küszöbe alatt), de a `nulla_pontok`/
    `ossz_pontok`-ban megjelennek; egy végig-nulla (mért-de-csendes) kulcsszó is
    kap sort (atlag=None). Csak a végig üres/NaN (nincs mérés) kulcsszó marad ki.
    """
    domenek = {}
    for p in kulcsszo_pontok:
        rek = domenek.setdefault(p["kulcsszo"], {
            "domen": p.get("domen", ""), "tipus": p.get("tipus", ""),
            "ertekek": [], "nulla": 0, "ossz": 0,
        })
        rek["ossz"] += 1                 # minden pont (nullákkal, üresekkel együtt)
        ert = _nyers(p)
        if ert is None:
            continue                     # üres/NaN: nem mérés, csak ossz-ba számít
        if ert == 0:
            rek["nulla"] += 1            # a 0 külön (gyakoriság-jel), az átlagból kimarad
        else:
            rek["ertekek"].append(ert)
    eredmeny = []
    for kulcsszo, rek in domenek.items():
        ek = rek["ertekek"]
        if not ek and rek["nulla"] == 0:
            continue                     # csak üres/NaN pont = nincs mérés → kihagyva (a végig-0 marad)
        eredmeny.append({
            "kulcsszo": kulcsszo,
            "domen": rek["domen"],
            "tipus": rek["tipus"],
            "atlag": round(sum(ek) / len(ek), 2) if ek else None,   # a 0-k nélkül; None, ha nincs nem-nulla mérés
            "csucs": round(max(ek), 2) if ek else None,
            "ervenyes_pontok": len(ek),                # nem-nulla pontok (az átlagban)
            "nulla_pontok": rek["nulla"],              # 0 értékű pontok (gyakoriság)
            "ossz_pontok": rek["ossz"],                # összes pont
        })
    return eredmeny


def _ir_json(fajl: Path, adat):
    seged.atomi_ir_szoveg(fajl, json.dumps(adat, ensure_ascii=False, indent=2))   # ATOMI-IRAS
    return fajl


def _kulcsszo_idosorok(kulcsszo_pontok) -> dict:
    """Kulcsszavanként [{idopont_utc, nyers_ertek}] a mai grafikonhoz (domen-nel)."""
    ki = {}
    for p in kulcsszo_pontok:
        ki.setdefault(p["kulcsszo"], {"domen": p.get("domen", ""),
                                      "tipus": p.get("tipus", ""), "pontok": []})
        ki[p["kulcsszo"]]["pontok"].append({
            "idopont_utc": p.get("idopont_utc", ""),
            "nyers_ertek": p.get("nyers_ertek", ""),
        })
    return ki


def legfrissebb_kulcsszo_megorzes(docs_data) -> dict:
    """A meglévő legfrissebb.json kulcsszó-részei (reggeli mód megőrzéséhez).

    Hiányzó fájl / hibás JSON / hiányzó mező → üres alap ({} / []).
    """
    fajl = Path(docs_data) / "legfrissebb.json"
    try:
        adat = json.loads(fajl.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"kulcsszavak": {}, "kulcsszo_osszesites": []}
    return {
        "kulcsszavak": adat.get("kulcsszavak", {}) or {},
        "kulcsszo_osszesites": adat.get("kulcsszo_osszesites", []) or [],
    }


def legfrissebb_ir(docs_data, top_trendek, trend_idosorok, kulcsszo_pontok,
                   frissitve_iso, geo, valtas_datum=None, kulcsszo_megorzes=None) -> Path:
    if kulcsszo_megorzes is not None:
        kulcsszavak = kulcsszo_megorzes.get("kulcsszavak", {})
        osszesites = kulcsszo_megorzes.get("kulcsszo_osszesites", [])
    else:
        kulcsszavak = _kulcsszo_idosorok(kulcsszo_pontok)
        osszesites = kulcsszo_napi_osszesites(kulcsszo_pontok)
    adat = {
        "geo": geo,
        "frissitve": frissitve_iso,
        "top_trendek": top_trendek,
        "trend_idosorok": trend_idosorok,
        "kulcsszavak": kulcsszavak,
        "kulcsszo_osszesites": osszesites,
    }
    if valtas_datum is not None:
        adat["modszertan_valtas"] = valtas_datum
    return _ir_json(Path(docs_data) / "legfrissebb.json", adat)


def tortenet_frissit(docs_data, nap_iso, kulcsszo_pontok) -> Path:
    """Egy nap upsertje a tortenet.json-ba — production-ban a tortenet_frissit_napok váltotta le (Task 5), szándékosan megtartva teszt-seed/fixture helperként."""
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


def tortenet_frissit_napok(docs_data, napi_pontok, valtas_datum=None) -> Path:
    """Több nap upsertje: a legfrissebb nap felülír, a régebbiek insert-if-absent."""
    fajl = Path(docs_data) / "tortenet.json"
    if fajl.exists():
        adat = json.loads(fajl.read_text(encoding="utf-8"))
    else:
        adat = {"napok": []}
    # töréspont-jelölő: halmozódó fájl → setdefault (first-wins), a None/más dátum nem írja felül/nem törli
    if valtas_datum is not None:
        adat.setdefault("modszertan_valtas", valtas_datum)
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


def _nap_szegmensek(adat) -> dict:
    """Meglévő napfájl dict → {szegmens: {trendek, frissitve}} normalizált alak.

    Csak a jelenlévő (reggel/este) szegmenseket adja vissza. A régi {nap, trendek}
    alakot 'este' szegmensként értelmezi (a nap beállt képe). Hibás/hiányos input → {}.
    """
    if not isinstance(adat, dict):
        return {}
    szeg = {}
    for s in ("reggel", "este"):
        v = adat.get(s)
        if isinstance(v, dict) and isinstance(v.get("trendek"), list):
            szeg[s] = {"trendek": v["trendek"], "frissitve": v.get("frissitve")}
    if not szeg and isinstance(adat.get("trendek"), list):
        szeg["este"] = {"trendek": adat["trendek"], "frissitve": adat.get("frissitve")}
    return szeg


def napi_ir(docs_data, nap_iso, top_trendek, szegmens="este", frissitve_iso=None) -> Path:
    napok_mappa = Path(docs_data) / "napok"
    fajl = napok_mappa / f"{nap_iso}.json"
    meglevo = {}
    if fajl.exists():
        try:
            meglevo = json.loads(fajl.read_text(encoding="utf-8"))
        except ValueError:
            meglevo = {}
    szeg = _nap_szegmensek(meglevo)
    szeg[szegmens] = {"trendek": top_trendek, "frissitve": frissitve_iso}
    ki = {"nap": nap_iso}
    for s in ("reggel", "este"):
        if s in szeg:
            ki[s] = szeg[s]
    _ir_json(fajl, ki)

    index_fajl = napok_mappa / "index.json"
    if index_fajl.exists():
        index = json.loads(index_fajl.read_text(encoding="utf-8"))
    else:
        index = {"napok": []}
    napok = sorted(set(index.get("napok", [])) | {nap_iso})
    _ir_json(index_fajl, {"napok": napok})
    return fajl
