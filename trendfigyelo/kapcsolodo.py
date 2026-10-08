"""Kapcsolódó keresések (F4): a napi felkapott témák mögé nézünk be a Google Trends related_queries-szel
(top + rising). IZOLÁLT gyűjtő-job saját, szűk plafonnal (a masodlagos_only mintája) — a fő órás gyűjtés
kvótáját NEM viheti el; soft-fail; a related endpoint referer-headert igényel (lásd spike)."""
import glob
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from trendfigyelo import json_export

_log = logging.getLogger(__name__)

CAP = 6                 # kifejezés / futás (kvóta-biztos)
TIMEFRAME = "today 3-m"
STALENESS_NAP = 7       # egy kifejezés ennyi naponként frissül újra
RETENCIO = 30           # az utolsó ennyi lekérdezett kifejezés megtartva
TOP_LIMIT = 15          # a top/rising lista max hossza
REFERER = {"referer": "https://www.google.com/"}   # KÖTELEZŐ a related endpointhoz
AG = "kapcsolodo"


def _ertek(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return str(v)   # pl. "Breakout"


def _lista(df, limit):
    if df is None:
        return []
    try:
        sorok = df.to_dict("records")       # pandas DataFrame
    except AttributeError:
        sorok = list(df)                    # lista-szerű (teszt-kompat)
    ki = []
    for s in sorok[:limit]:
        q = (s.get("query") or "").strip() if isinstance(s, dict) else ""
        if q:
            ki.append({"query": q, "value": _ertek(s.get("value"))})
    return ki


def _parse_related(eredmeny, limit=TOP_LIMIT):
    e = eredmeny or {}
    return {"top": _lista(e.get("top"), limit), "rising": _lista(e.get("rising"), limit)}


def jeloltek(docs_data, meglevo, most, cap=CAP, staleness_nap=STALENESS_NAP, napok_vissza=2):
    """A legutóbbi `napok_vissza` napfájl felkapottjai max-volumen szerint; a `staleness_nap`-on
    belül frissített kifejezések kizárva; volumen szerint csökkenőben a top `cap`. Csak OLVAS."""
    fajlok = [f for f in sorted(glob.glob(os.path.join(docs_data, "napok", "*.json")))
              if len(Path(f).stem) == 10]
    vol = {}
    for f in fajlok[-napok_vissza:]:
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        trendek = []
        for szeg in ("reggel", "este"):
            trendek += (d.get(szeg) or {}).get("trendek", []) or []
        if not trendek:
            trendek = d.get("trendek") or []
        for tr in trendek:
            kif = (tr.get("kifejezes") or "").strip()
            if not kif:
                continue
            try:
                v = int(tr.get("volumen") or 0)
            except (TypeError, ValueError):
                v = 0
            vol[kif] = max(vol.get(kif, 0), v)
    friss = set()
    for kif, lek in (meglevo or {}).items():
        try:
            if (most - datetime.fromisoformat(lek)).days < staleness_nap:
                friss.add(kif)
        except (TypeError, ValueError):
            pass
    jel = [(k, v) for k, v in vol.items() if k not in friss]
    jel.sort(key=lambda kv: (-kv[1], kv[0]))
    return jel[:cap]


def related_egy(kliens, kif, config, timeframe=TIMEFRAME):
    """Egy kifejezés related_queries-e a Kliens throttle-jén, KÖTELEZŐ referer-headerrel.
    SOFT-FAIL: kvóta/429/parszolási hiba → None (kihagyva + FIGYELEM), a job NEM dől el."""
    try:
        r = kliens.hivas(AG, kliens.tr.related_queries, kif,
                         geo=config.geo, timeframe=timeframe, headers=REFERER)
    except Exception as e:   # noqa: BLE001 — soft-fail: szigorú related-kvóta/429/egyéb
        _log.warning("FIGYELEM: a kapcsolódó keresések kimaradtak (%s): %s", kif, e)
        return None
    return _parse_related(r)


def _betolt(docs_data):
    try:
        return json.loads((Path(docs_data) / "kapcsolodo.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def gyujt(docs_data, kliens, config, most, cap=CAP, timeframe=TIMEFRAME,
          staleness_nap=STALENESS_NAP, retencio=RETENCIO):
    """A felkapott jelöltekre (jeloltek) related_queries-t gyűjt (soft-fail per szó), bemergeli a
    meglévő kapcsolodo.json-ba (lekerdezve=most), lekerdezve szerint rendez + retencio-ra vág."""
    adat = _betolt(docs_data)
    bejegyzesek = {k["kifejezes"]: k for k in (adat.get("kifejezesek") or [])}
    meglevo_lek = {k: v.get("lekerdezve") for k, v in bejegyzesek.items()}
    for kif, vol in jeloltek(docs_data, meglevo_lek, most, cap, staleness_nap):
        res = related_egy(kliens, kif, config, timeframe)
        if res is None:
            continue
        bejegyzesek[kif] = {"kifejezes": kif, "lekerdezve": most.isoformat(),
                            "volumen": vol, "top": res["top"], "rising": res["rising"]}
    lista = sorted(bejegyzesek.values(), key=lambda k: k.get("lekerdezve") or "", reverse=True)[:retencio]
    return {"frissitve": most.isoformat(), "kifejezesek": lista}


def kapcsolodo_ir(docs_data, adat):
    return json_export._ir_json(Path(docs_data) / "kapcsolodo.json", adat)
