import json
from trendfigyelo import nyers_kimenet
from trendfigyelo.nyers_kimenet import ervenyes_masodlagos_rekord

def _pont(iso, ertek=5, reszleges=False):
    return {"idopont_utc": iso, "ertek": ertek, "reszleges": reszleges}

def _rek(kulcsszo="edzés", racs="nap", timeframe="today 3-m",
         kezd="2026-05-16T00:00:00+00:00", veg="2026-08-13T00:00:00+00:00",
         lekerdezes="2026-08-13T09:00:00+00:00"):
    return {"kulcsszo": kulcsszo, "racs": racs, "timeframe": timeframe,
            "lekerdezes_utc": lekerdezes, "ablak_kezdet_utc": kezd, "ablak_veg_utc": veg,
            "pontok": [_pont(kezd, 5, False), _pont(veg, 6, True)]}

def _read(mappa):
    return json.loads((mappa / "youtube_nyers.json").read_text(encoding="utf-8"))["kulcsszavak"]

def test_ir_youtube_ir_es_megorzi_a_mezoket(tmp_path):
    p = nyers_kimenet.ir_youtube(tmp_path, {"edzés": _rek(racs="nap", timeframe="today 3-m")})
    assert p.name == "youtube_nyers.json"
    rekk = _read(tmp_path)["edzés"]
    assert len(rekk) == 1 and rekk[0]["timeframe"] == "today 3-m" and rekk[0]["racs"] == "nap"
    assert ervenyes_masodlagos_rekord(rekk[0]) == []

def test_ir_youtube_retencio_timeframe_kulon(tmp_path):
    for i in range(3):
        nyers_kimenet.ir_youtube(tmp_path, {"edzés": _rek(
            timeframe="today 3-m", racs="nap", lekerdezes=f"2026-08-1{i}T09:00:00+00:00")})
        nyers_kimenet.ir_youtube(tmp_path, {"edzés": _rek(
            timeframe="today 12-m", racs="het", lekerdezes=f"2026-08-1{i}T09:00:00+00:00")})
    rekk = _read(tmp_path)["edzés"]
    tf = {}
    for r in rekk:
        tf[r["timeframe"]] = tf.get(r["timeframe"], 0) + 1
    assert tf == {"today 3-m": 3, "today 12-m": 3}
