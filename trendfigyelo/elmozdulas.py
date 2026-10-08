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


def _ablak_pontok(ablakok, iv):
    """A nyers ablakok közül az intervallumot TARTALMAZÓ (legszűkebb), ennek híján a legközelebbi végű
    (>= az intervallum vége) pontjai, az intervallum ablakára szűrve. Ha az intervallumnak nincs ablaka:
    a legutolsó nyers ablak. Fail-soft: [] ."""
    try:
        ablakok = [a for a in (ablakok or []) if isinstance(a, dict)]
        if not ablakok:
            return []
        if not (iv.get("ablak_kezdet_utc") and iv.get("ablak_veg_utc")):
            return ablakok[-1].get("pontok") or []
        k, v = _ts(iv["ablak_kezdet_utc"]), _ts(iv["ablak_veg_utc"])
        ak = [(_ts(a["ablak_kezdet_utc"]), _ts(a["ablak_veg_utc"]), a) for a in ablakok
              if a.get("ablak_kezdet_utc") and a.get("ablak_veg_utc")]
        tart = [x for x in ak if x[0] <= k and x[1] >= v]
        if tart:
            ab = min(tart, key=lambda x: x[1] - x[0])[2]
        else:
            vegu = [x for x in ak if x[1] >= v]
            if not vegu:
                return []
            ab = max(vegu, key=lambda x: x[1])[2]
        return [p for p in (ab.get("pontok") or []) if k <= _ts(p["idopont_utc"]) <= v]
    except (AttributeError, TypeError, ValueError, KeyError):
        return []


def elmozdulas_szamit(docs_data):
    """Per követett kulcsszó az elsődleges intervallumból: szokatlan/irány/eltérés/mióta-tart/
    megbízhatóság/sáv + szakpolitika. Determinista, csak olvas."""
    reg = _betolt(docs_data, "kulcsszo_regresszio.json")
    reg2 = _betolt(docs_data, "kulcsszo_masodlagos_regresszio.json")
    nyers = _betolt(docs_data, "kulcsszo_nyers.json").get("kulcsszavak") or {}
    nyers2 = _betolt(docs_data, "kulcsszo_masodlagos_nyers.json").get("kulcsszavak") or {}
    elsod = reg.get("kulcsszavak") or {}
    masod = reg2.get("kulcsszavak") or {}
    out = {}
    # per-INTERVALLUM merge (mint a frontend egyesitett_reg): az elsődleges intervallum, ha érvényes,
    # különben a másodlagos azonos intervalluma. A metaadat az elsődleges entryből, ennek híján a másodlagosból.
    for szo in list(elsod) + [s for s in masod if s not in elsod]:
        o = elsod.get(szo) or {}
        m = masod.get(szo) or {}
        w = o or m
        racs = w.get("racs") or "ora"
        ivn = ELSODLEGES_IV.get(racs, "1_het")
        oiv = (o.get("intervallumok") or {}).get(ivn) or {}
        miv = (m.get("intervallumok") or {}).get(ivn) or {}
        if oiv.get("ervenyes"):
            iv, masodlagos_forras = oiv, False
        else:
            iv, masodlagos_forras = miv, True
        if not iv.get("ervenyes"):
            continue
        illeszkedes = iv.get("illeszkedes")
        szokatlan = illeszkedes in ("felette", "alatta")
        mad = float(iv.get("reziduum_szokasos") or 0.0)
        mai = float(iv.get("mai_reziduum") or 0.0)
        pontok = _ablak_pontok(nyers2.get(szo) if masodlagos_forras else nyers.get(szo), iv)
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
