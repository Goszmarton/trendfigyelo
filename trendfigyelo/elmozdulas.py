# trendfigyelo/elmozdulas.py
"""Determinista elmozdulásfigyelő a Bővítés fülhöz: a kulcsszo_regresszio.json szokásos-szint /
eltérés / irány / megbízhatóság adataiból + a nyers sorból a 'mióta tart' (sávon kívüli egymás
utáni pontok). Zéró Google-hívás; az esti futtato.py-ban fut a regresszió után (mint a kategoriak_ir)."""
import json
from datetime import datetime
from pathlib import Path

from trendfigyelo import json_export, szakpolitika

SAV_SZORZO = 2.0     # a reziduum_szokasos (MAD) szorzója — a regresszio._illeszkedes_allapot-tal konzisztens
SAV_MIN = 3.0        # a sáv alsó korlátja
ELSODLEGES_IV = {"ora": "1_het", "nap": "1_ho", "het": "1_ho"}   # racs → melyik intervallumból


def _ts(s):
    return datetime.fromisoformat(s).timestamp()


def _vonal(iv):
    """A trendvonal (a+b*t) a két illesztes_vonal végpontból; (b_per_mp, t0, y0) vagy None."""
    v = iv.get("illesztes_vonal") or []
    if len(v) < 2:
        return None
    t0, y0 = _ts(v[0]["idopont_utc"]), float(v[0]["ertek"])
    t1, y1 = _ts(v[-1]["idopont_utc"]), float(v[-1]["ertek"])
    if t1 == t0:
        return None
    return ((y1 - y0) / (t1 - t0), t0, y0)


def _megbizhatosag(iv):
    r2 = iv.get("r2") or 0.0
    pont = iv.get("pontok_hasznalt") or 0
    if r2 >= 0.5 and pont >= 100:
        return "magas"
    if r2 >= 0.2 and pont >= 50:
        return "kozepes"
    return "alacsony"


def _idotartam(iv, pontok):
    """Hány egymást követő LEGUTÓBBI nyers pont van a szokásos sávon kívül (a trendvonalhoz mért
    reziduum > sáv), a mai eltérés irányában. (szam, elso_ilyen_idopont) vagy (0, None)."""
    vonal = _vonal(iv)
    if not vonal or not pontok:
        return 0, None
    b, t0, y0 = vonal
    mad = float(iv.get("reziduum_szokasos") or 0.0)
    sav = max(SAV_SZORZO * mad, SAV_MIN)
    elojel = 1 if (iv.get("mai_reziduum") or 0) >= 0 else -1
    szam, ota = 0, None
    for p in reversed(pontok):                      # a legfrissebbtől visszafelé
        if p.get("reszleges"):
            continue
        rez = float(p["ertek"]) - (y0 + b * (_ts(p["idopont_utc"]) - t0))
        if rez * elojel > sav:                      # a shift irányában, a sávon kívül
            szam += 1
            ota = p["idopont_utc"]
        else:
            break
    return szam, ota


def _sav_pontok(iv):
    vonal = _vonal(iv)
    v = iv.get("illesztes_vonal") or []
    if not vonal or len(v) < 2:
        return None
    mad = float(iv.get("reziduum_szokasos") or 0.0)
    d = max(SAV_SZORZO * mad, SAV_MIN)
    also = [{"idopont_utc": p["idopont_utc"], "ertek": round(float(p["ertek"]) - d, 2)} for p in v]
    felso = [{"idopont_utc": p["idopont_utc"], "ertek": round(float(p["ertek"]) + d, 2)} for p in v]
    return {"also": also, "felso": felso}


def _betolt(docs_data, nev):
    try:
        return json.loads((Path(docs_data) / nev).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def elmozdulas_szamit(docs_data):
    """Per követett kulcsszó az elsődleges intervallumból: szokatlan/irány/eltérés/mióta-tart/
    megbízhatóság/sáv + szakpolitika. Determinista, csak olvas."""
    reg = _betolt(docs_data, "kulcsszo_regresszio.json")
    reg2 = _betolt(docs_data, "kulcsszo_masodlagos_regresszio.json")
    nyers = _betolt(docs_data, "kulcsszo_nyers.json").get("kulcsszavak") or {}
    egyesitett = {}
    egyesitett.update((reg.get("kulcsszavak") or {}))
    for szo, w in (reg2.get("kulcsszavak") or {}).items():
        egyesitett.setdefault(szo, w)
    out = {}
    for szo, w in egyesitett.items():
        racs = w.get("racs") or "ora"
        ivn = ELSODLEGES_IV.get(racs, "1_het")
        iv = (w.get("intervallumok") or {}).get(ivn) or {}
        if not iv.get("ervenyes"):
            continue
        illeszkedes = iv.get("illeszkedes")
        szokatlan = illeszkedes in ("felette", "alatta")
        mad = float(iv.get("reziduum_szokasos") or 0.0)
        mai = float(iv.get("mai_reziduum") or 0.0)
        ablakok = nyers.get(szo) or []
        pontok = (ablakok[-1].get("pontok") if ablakok else []) or []
        tart, ota = _idotartam(iv, pontok)
        out[szo] = {
            "szokatlan": szokatlan,
            "irany": "emelkedik" if illeszkedes == "felette" else ("csokken" if illeszkedes == "alatta" else "stabil"),
            "elteres": round(mai / max(mad, SAV_MIN), 2),
            "elteres_nyers": round(mai, 2),
            "idotartam_pont": tart, "idotartam_ota_utc": ota,
            "megbizhatosag": _megbizhatosag(iv),
            "domen": w.get("domen"), "tipus": w.get("tipus"),
            "szakpolitika": szakpolitika.szakpolitika_besorol(kifejezes=szo, domen=w.get("domen")),
            "sav": {ivn: _sav_pontok(iv)} if _sav_pontok(iv) else {},
        }
    szokatlan_lista = sorted([s for s, v in out.items() if v["szokatlan"]],
                             key=lambda s: -abs(out[s]["elteres"]))
    return {"szamitva_utc": reg.get("szamitva_utc"), "kulcsszavak": out, "szokatlan_lista": szokatlan_lista}


def elmozdulas_ir(docs_data):
    """Az elmozdulas.json atomi írása (a json_export._ir_json mintája)."""
    return json_export._ir_json(Path(docs_data) / "elmozdulas.json", elmozdulas_szamit(docs_data))
