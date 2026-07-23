import json

from trendfigyelo import json_export


def _kpontok():
    return [
        {"kulcsszo": "infláció", "csoport": "megelhetes", "normalizalt_ertek": 40.0},
        {"kulcsszo": "infláció", "csoport": "megelhetes", "normalizalt_ertek": 80.0},
        {"kulcsszo": "MNB", "csoport": "gazdaság", "normalizalt_ertek": ""},
    ]


def test_kulcsszo_napi_osszesites_atlag_es_csucs():
    o = json_export.kulcsszo_napi_osszesites(_kpontok())
    inflacio = next(x for x in o if x["kulcsszo"] == "infláció")
    assert inflacio["atlag"] == 60.0
    assert inflacio["csucs"] == 80.0
    # MNB-nek nincs érvényes normalizált értéke → kihagyva
    assert all(x["kulcsszo"] != "MNB" for x in o)


def test_legfrissebb_ir_geo_es_frissites(tmp_path):
    p = json_export.legfrissebb_ir(tmp_path, [], [], _kpontok(), "2021-01-01T12:00:00+00:00", "HU")
    adat = json.loads(p.read_text(encoding="utf-8"))
    assert adat["geo"] == "HU"
    assert adat["frissitve"] == "2021-01-01T12:00:00+00:00"
    assert p.name == "legfrissebb.json"


def test_tortenet_frissit_ugyanazt_a_napot_felulirja(tmp_path):
    json_export.tortenet_frissit(tmp_path, "2021-01-01", _kpontok())
    p = json_export.tortenet_frissit(tmp_path, "2021-01-01", _kpontok())  # ugyanaz a nap újra
    adat = json.loads(p.read_text(encoding="utf-8"))
    napok = [b["nap"] for b in adat["napok"]]
    assert napok == ["2021-01-01"]  # nem duplikálódik


def test_napi_ir_es_index(tmp_path):
    json_export.napi_ir(tmp_path, "2021-01-02", [{"kifejezes": "infláció", "volumen": "50000"}])
    json_export.napi_ir(tmp_path, "2021-01-01", [{"kifejezes": "benzinár", "volumen": "20000"}])
    napi = json.loads((tmp_path / "napok" / "2021-01-02.json").read_text(encoding="utf-8"))
    assert napi["trendek"][0]["kifejezes"] == "infláció"
    index = json.loads((tmp_path / "napok" / "index.json").read_text(encoding="utf-8"))
    assert index["napok"] == ["2021-01-01", "2021-01-02"]  # rendezett, egyedi
