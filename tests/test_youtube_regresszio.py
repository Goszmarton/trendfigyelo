import json
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
from trendfigyelo import regresszio

def _het_pontok(n, ertek=40):
    kezd = datetime(2025, 8, 20, tzinfo=timezone.utc)
    return [{"idopont_utc": (kezd + timedelta(weeks=i)).isoformat(),
             "ertek": ertek, "reszleges": (i == n - 1)} for i in range(n)]

def _yt_shim():
    tetel = [SimpleNamespace(kifejezes="klíma", domen="otthon", tipus="szintmero", racs="het")]
    return SimpleNamespace(modszertan_valtas=None, osszes_kulcsszo=lambda: list(tetel))

def test_youtube_regresszio_szamit_es_ir(tmp_path):
    yt_nyers = {"kulcsszavak": {"klíma": [{
        "kulcsszo": "klíma", "racs": "het", "timeframe": "today 12-m",
        "lekerdezes_utc": "2026-08-13T09:00:00+00:00",
        "ablak_kezdet_utc": _het_pontok(53)[0]["idopont_utc"],
        "ablak_veg_utc": _het_pontok(53)[-1]["idopont_utc"],
        "pontok": _het_pontok(53)}]}}
    adat = regresszio.regresszio_masodlagos_szamit(yt_nyers, {"napok": []}, _yt_shim(), "T")
    sz = adat["kulcsszavak"]["klíma"]
    assert sz["racs"] == "het" and sz["domen"] == "otthon" and sz["aktiv"] is True
    iv = sz["intervallumok"]
    assert "irany" in iv["1_ev"] and iv["1_ev"]["ervenyes"] is True
    # heti szó rövid ablaka strukturálisan érvénytelen (kevés heti pont)
    assert iv["1_het"]["ervenyes"] is False
    p = regresszio.regresszio_ir_youtube(tmp_path, adat)
    assert p.name == "youtube_regresszio.json"
    vissza = json.loads(p.read_text(encoding="utf-8"))
    assert "klíma" in vissza["kulcsszavak"]
