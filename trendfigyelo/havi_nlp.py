"""Havi NLP-elemzés a felkapott keresőszavakról (magyar, LLM-alapú). A korpusz-építés és a
grounding-validáció tiszta/determinista; az NLP-hívás a Claude Opus (nem determinista, AI-jelölt)."""
import glob
import json
import os

def havi_korpusz(docs_data, honap):
    """A hónap (YYYY-MM) felkapott szavai aggregálva: egyedi kifejezés + gyakoriság (hány külön nap),
    max volumen, témák-halmaz, pár hír-cím. Csak OLVAS (napok/*.json READ-ONLY)."""
    minta = os.path.join(docs_data, "napok", honap + "-*.json")
    fajlok = sorted(glob.glob(minta))
    agg = {}
    for f in fajlok:
        try:
            nap = json.loads(open(f, encoding="utf-8").read())
        except (OSError, ValueError):
            continue
        napi_kif = set()
        for szeg in ("reggel", "este"):
            for tr in (nap.get(szeg) or {}).get("trendek", []) or []:
                kif = (tr.get("kifejezes") or "").strip()
                if not kif:
                    continue
                napi_kif.add(kif)
                a = agg.setdefault(kif, {"kifejezes": kif, "gyakorisag": 0, "max_volumen": 0,
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
        for kif in napi_kif:
            agg[kif]["gyakorisag"] += 1                       # naponta EGYSZER számít
    szavak = sorted(agg.values(), key=lambda a: (-a["gyakorisag"], -a["max_volumen"], a["kifejezes"]))
    for a in szavak:
        a["temak"] = sorted(a["temak"])
    return {"honap": honap, "napok": len(fajlok), "egyedi_szo": len(szavak), "szavak": szavak}
