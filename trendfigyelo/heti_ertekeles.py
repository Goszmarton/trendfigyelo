# trendfigyelo/heti_ertekeles.py
"""Heti értékelés az előző (hétfő–vasárnap) hétről (magyar, LLM-alapú). A korpusz-építés és a
grounding tiszta/determinista; a Claude Opus hívás nem determinista (AI-jelölt). A havi_nlp.py
PÁRHUZAMOS mintája — a napi/havi elemzés érintetlen."""
import glob
import json
import logging
import os
import time
from datetime import date, timedelta
from pathlib import Path

from trendfigyelo import json_export

_log = logging.getLogger(__name__)


def _het_veg(het_kezdet_iso):
    return (date.fromisoformat(het_kezdet_iso) + timedelta(days=6)).isoformat()


def _iso_het(het_kezdet_iso):
    ev, het, _ = date.fromisoformat(het_kezdet_iso).isocalendar()
    return f"{ev}-W{het:02d}"


def _het_1het(regr_szo):
    iv = ((regr_szo or {}).get("intervallumok") or {}).get("1_het") or {}
    return iv if iv.get("ervenyes") else {}


def _kulcsszavak_het(docs_data):
    """A 28 követett szó heti jele a regresszió `1_het` (érvényes) ablakából: irány, illeszkedés a
    szokásos szinthez, eltérés (mai_reziduum − reziduum_szokasos), heti pálya (illesztes_vonal)."""
    fajl = Path(docs_data) / "kulcsszo_regresszio.json"
    try:
        d = json.loads(fajl.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for szo, w in (d.get("kulcsszavak") or {}).items():
        iv = _het_1het(w)
        mr, rsz = iv.get("mai_reziduum"), iv.get("reziduum_szokasos")
        elteres = (mr - rsz) if isinstance(mr, (int, float)) and isinstance(rsz, (int, float)) else None
        out.append({
            "szo": szo, "domen": w.get("domen"), "tipus": w.get("tipus"),
            "irany": iv.get("irany"), "illeszkedes": iv.get("illeszkedes"),
            "mai_ertek": iv.get("mai_ertek"), "meredekseg_nap": iv.get("meredekseg_nap"),
            "elteres_szokasostol": elteres,
            "palya": [{"idopont_utc": p.get("idopont_utc"), "ertek": p.get("ertek")}
                      for p in (iv.get("illesztes_vonal") or [])],
        })
    return out


def _youtube_het(docs_data):
    fajl = Path(docs_data) / "youtube_regresszio.json"
    try:
        d = json.loads(fajl.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for szo, w in (d.get("kulcsszavak") or {}).items():
        iv = _het_1het(w)
        van = bool(iv)
        out.append({"szo": szo, "domen": w.get("domen"), "tipus": w.get("tipus"),
                    "irany": iv.get("irany") if van else None,
                    "illeszkedes": iv.get("illeszkedes") if van else None,
                    "mai_ertek": iv.get("mai_ertek") if van else None,
                    "nincs_adat": not van})
    return out


def _felkapott_het(docs_data, het_kezdet_iso, het_veg_iso):
    """A hét (hétfő–vasárnap) napfájljaiból aggregált felkapott kifejezések: napok_szama (hány külön
    napon), max_volumen, témák, pár hír. A napfájl szegmentált (reggel/este) VAGY régi lapos — a
    havi_korpusz-szal azonos visszafelé-kompat szabály, de DÁTUM-ABLAKRA szűrve (nem hónap-prefixre)."""
    agg, beolvasott = {}, 0
    for f in sorted(glob.glob(os.path.join(docs_data, "napok", "*.json"))):
        nap = Path(f).stem
        if len(nap) != 10 or nap < het_kezdet_iso or nap > het_veg_iso:
            continue
        try:
            with open(f, encoding="utf-8") as fp:
                d = json.loads(fp.read())
        except (OSError, ValueError):
            continue
        beolvasott += 1
        trend_lista = []
        for szeg in ("reggel", "este"):
            trend_lista += (d.get(szeg) or {}).get("trendek", []) or []
        if not trend_lista:
            trend_lista = d.get("trendek") or []
        napi = set()
        for tr in trend_lista:
            kif = (tr.get("kifejezes") or "").strip()
            if not kif:
                continue
            napi.add(kif)
            a = agg.setdefault(kif, {"kifejezes": kif, "napok_szama": 0, "max_volumen": 0,
                                     "temak": set(), "hirek": []})
            try:
                a["max_volumen"] = max(a["max_volumen"], int(tr.get("volumen") or 0))
            except (TypeError, ValueError):
                pass
            a["temak"].update(tr.get("temak") or [])
            for h in (tr.get("hirek") or [])[:2]:
                cim = h.get("cim") if isinstance(h, dict) else h
                if cim and cim not in a["hirek"] and len(a["hirek"]) < 3:
                    a["hirek"].append(cim)
        for kif in napi:
            agg[kif]["napok_szama"] += 1
    szavak = sorted(agg.values(), key=lambda a: (-a["napok_szama"], -a["max_volumen"], a["kifejezes"]))
    for a in szavak:
        a["temak"] = sorted(a["temak"])
    return szavak, beolvasott


def heti_korpusz(docs_data, het_kezdet_iso):
    """Az előző hét (hétfő=het_kezdet_iso … vasárnap) DETERMINISTA aggregálása. Csak OLVAS."""
    het_veg = _het_veg(het_kezdet_iso)
    felkapott, napok = _felkapott_het(docs_data, het_kezdet_iso, het_veg)
    return {
        "het_kezdet": het_kezdet_iso, "het_veg": het_veg, "iso_het": _iso_het(het_kezdet_iso),
        "napok": napok,
        "kulcsszavak": _kulcsszavak_het(docs_data),
        "felkapott": felkapott,
        "youtube": _youtube_het(docs_data),
    }
