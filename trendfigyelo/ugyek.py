"""Ügy-életút a Bővítés fülhöz: gördülő 30-napos korpusz (determinista aggregálás) + LLM-csoportosítás
(Claude Opus) ügyekbe + determinista ügy-metrikák. A heti_ertekeles/havi_nlp mintája. Grounded:
a Python számol, az LLM csak csoportosít/nevez/sorol be a korpuszból."""
import glob
import json
import logging
import os
import time
from datetime import date, timedelta
from pathlib import Path

from trendfigyelo import json_export, szakpolitika

_log = logging.getLogger(__name__)

UJ_KUSZOB_NAP = 7          # 'újonnan megfigyelt': az első nap az ablak utolsó ennyi napján belül
FOLYAMATOS_ARANY = 0.5     # 'folyamatosan jelenlévő': a span napjainak legalább ennyi részén jelen
VISSZATERO_SZUNET = 3      # 'visszatérő': legalább ennyi napos szünet két jelenléti nap között


def _napok_kozott(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def _eletut(kif, veg_nap, ablak_nap):
    napok = sorted(kif.get("napok") or [])
    if not napok:
        return "egyeb"
    elso, utolso = napok[0], napok[-1]
    span = _napok_kozott(elso, utolso) + 1
    # visszatérő: van VISSZATERO_SZUNET-nél hosszabb rés két jelenléti nap között
    van_szunet = any(_napok_kozott(napok[i], napok[i + 1]) > VISSZATERO_SZUNET for i in range(len(napok) - 1))
    if van_szunet:
        return "visszatero"
    # újonnan: az első nap az ablak utolsó UJ_KUSZOB_NAP napján belül, és rövid span
    if _napok_kozott(elso, veg_nap) < UJ_KUSZOB_NAP and span <= UJ_KUSZOB_NAP:
        return "ujonnan_megfigyelt"
    # folyamatos: a span napjainak legalább FOLYAMATOS_ARANY részén jelen
    if span >= 2 and len(napok) / span >= FOLYAMATOS_ARANY:
        return "folyamatosan_jelenlevo"
    return "egyeb"


def _mozgas(volumen_sor):
    ertekek = [float(p.get("max_volumen") or 0) for p in (volumen_sor or [])]
    if len(ertekek) < 2:
        return "nem_megallapithato"
    elso_fel = ertekek[: len(ertekek) // 2] or ertekek[:1]
    masodik_fel = ertekek[len(ertekek) // 2:]
    d = (sum(masodik_fel) / len(masodik_fel)) - (sum(elso_fel) / len(elso_fel))
    bazis = max(1.0, sum(ertekek) / len(ertekek))
    if d / bazis > 0.2:
        return "erosodo"
    if d / bazis < -0.2:
        return "lecsengo"
    return "stabil"


def ugy_korpusz(docs_data, veg_nap, ablak_nap=30):
    """A [veg_nap-ablak_nap+1 .. veg_nap] ablak felkapott kifejezéseinek determinista aggregálása.
    Csak OLVAS (napok/*.json). Per kifejezés: jelenléti napok, első/utolsó nap, volumen-sor, témák, hírek."""
    kezdet = (date.fromisoformat(veg_nap) - timedelta(days=ablak_nap - 1)).isoformat()
    agg = {}
    for f in sorted(glob.glob(os.path.join(docs_data, "napok", "*.json"))):
        nap = Path(f).stem
        if len(nap) != 10 or nap < kezdet or nap > veg_nap:
            continue
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        trendek = []
        for szeg in ("reggel", "este"):
            trendek += (d.get(szeg) or {}).get("trendek", []) or []
        if not trendek:
            trendek = d.get("trendek") or []
        napi_max = {}
        for tr in trendek:
            kif = (tr.get("kifejezes") or "").strip()
            if not kif:
                continue
            a = agg.setdefault(kif, {"kifejezes": kif, "napok": set(), "volumen_map": {},
                                     "temak": set(), "hirek": []})
            a["napok"].add(nap)
            try:
                v = int(tr.get("volumen") or 0)
            except (TypeError, ValueError):
                v = 0
            napi_max[kif] = max(napi_max.get(kif, 0), v)
            a["temak"].update(tr.get("temak") or [])
            for h in (tr.get("hirek") or [])[:2]:
                cim = h.get("cim") if isinstance(h, dict) else h
                if cim and cim not in a["hirek"] and len(a["hirek"]) < 3:
                    a["hirek"].append(cim)
        for kif, v in napi_max.items():
            agg[kif]["volumen_map"][nap] = v
    kifejezesek = []
    for a in agg.values():
        napok = sorted(a["napok"])
        volumen_sor = [{"nap": n, "max_volumen": a["volumen_map"][n]} for n in napok]
        kif = {"kifejezes": a["kifejezes"], "elso_nap": napok[0], "utolso_nap": napok[-1],
               "napok": napok, "napok_szama": len(napok), "volumen_sor": volumen_sor,
               "temak": sorted(a["temak"]), "hirek": a["hirek"]}
        kif["eletut"] = _eletut(kif, veg_nap, ablak_nap)
        kif["mozgas"] = _mozgas(volumen_sor)
        kif["szakpolitika"] = szakpolitika.szakpolitika_besorol(kifejezes=a["kifejezes"], temak=kif["temak"])
        kifejezesek.append(kif)
    kifejezesek.sort(key=lambda c: (-c["napok_szama"], c["elso_nap"], c["kifejezes"]))
    return {"ablak": {"kezdet": kezdet, "veg": veg_nap, "nap": ablak_nap}, "kifejezesek": kifejezesek}
