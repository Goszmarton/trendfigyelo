import json

from trendfigyelo import json_export


def _kpontok():
    return [
        {"kulcsszo": "infláció", "csoport": "megelhetes", "normalizalt_ertek": 40.0,
         "referencia_ervenyes": True},
        {"kulcsszo": "infláció", "csoport": "megelhetes", "normalizalt_ertek": 80.0,
         "referencia_ervenyes": True},
        {"kulcsszo": "MNB", "csoport": "gazdaság", "normalizalt_ertek": "",
         "referencia_ervenyes": True},
    ]


def test_kulcsszo_napi_osszesites_atlag_es_csucs():
    o = json_export.kulcsszo_napi_osszesites(_kpontok())
    inflacio = next(x for x in o if x["kulcsszo"] == "infláció")
    assert inflacio["atlag"] == 60.0
    assert inflacio["csucs"] == 80.0
    # MNB-nek nincs érvényes normalizált értéke → kihagyva
    assert all(x["kulcsszo"] != "MNB" for x in o)


def test_kulcsszo_napi_osszesites_ervenyes_pontok():
    o = json_export.kulcsszo_napi_osszesites(_kpontok())
    inflacio = next(x for x in o if x["kulcsszo"] == "infláció")
    assert inflacio["atlag"] == 60.0
    assert inflacio["csucs"] == 80.0
    assert inflacio["ervenyes_pontok"] == 2


def test_nulla_ertekek_kihagyva_az_atlagbol():
    pontok = [
        {"kulcsszo": "x", "csoport": "g", "normalizalt_ertek": 0, "referencia_ervenyes": True},
        {"kulcsszo": "x", "csoport": "g", "normalizalt_ertek": 60, "referencia_ervenyes": True},
    ]
    x = json_export.kulcsszo_napi_osszesites(pontok)[0]
    assert x["atlag"] == 60.0        # a 0 nem húzza le 30-ra
    assert x["ervenyes_pontok"] == 1


def test_ref_ervenytelen_koteg_kimarad_es_ervenyes_pontok_csokken():
    pontok = [
        {"kulcsszo": "infláció", "csoport": "megelhetes", "normalizalt_ertek": 40.0,
         "referencia_ervenyes": True},
        {"kulcsszo": "infláció", "csoport": "megelhetes", "normalizalt_ertek": 80.0,
         "referencia_ervenyes": True},
        # ref-érvénytelen köteg: normalizált üres, nyers 30 — NEM számíthat be
        {"kulcsszo": "infláció", "csoport": "megelhetes", "normalizalt_ertek": "",
         "nyers_ertek": 30, "referencia_ervenyes": False},
    ]
    inflacio = json_export.kulcsszo_napi_osszesites(pontok)[0]
    assert inflacio["ervenyes_pontok"] == 2      # 3 helyett — a ref-érvénytelen kimaradt
    assert inflacio["atlag"] == 60.0             # a nyers 30 nem szivárgott be


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


def test_tortenet_frissit_napok_visszapotol_es_nem_ir_felul(tmp_path):
    # meglévő 01-02 (régi 99.0 érték)
    json_export.tortenet_frissit(tmp_path, "2021-01-02", [
        {"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 99.0, "referencia_ervenyes": True}])
    napi = {
        "2021-01-01": [{"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 10.0, "referencia_ervenyes": True}],
        "2021-01-02": [{"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 20.0, "referencia_ervenyes": True}],
        "2021-01-03": [{"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 30.0, "referencia_ervenyes": True}],
    }
    p = json_export.tortenet_frissit_napok(tmp_path, napi)
    adat = json.loads(p.read_text(encoding="utf-8"))
    atlagok = {b["nap"]: b["kulcsszavak"][0]["atlag"] for b in adat["napok"]}
    assert [b["nap"] for b in adat["napok"]] == ["2021-01-01", "2021-01-02", "2021-01-03"]  # rendezett
    assert atlagok["2021-01-01"] == 10.0   # visszapótolva (hiányzott)
    assert atlagok["2021-01-02"] == 99.0   # insert-if-absent: a meglévő NEM íródott felül
    assert atlagok["2021-01-03"] == 30.0   # a legfrissebb nap beírva


def test_tortenet_frissit_napok_friss_nap_felulir(tmp_path):
    json_export.tortenet_frissit(tmp_path, "2021-01-03", [
        {"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 99.0, "referencia_ervenyes": True}])
    napi = {"2021-01-03": [{"kulcsszo": "a", "csoport": "g", "normalizalt_ertek": 30.0, "referencia_ervenyes": True}]}
    p = json_export.tortenet_frissit_napok(tmp_path, napi)
    adat = json.loads(p.read_text(encoding="utf-8"))
    b = next(x for x in adat["napok"] if x["nap"] == "2021-01-03")
    assert b["kulcsszavak"][0]["atlag"] == 30.0   # a legfrissebb nap FELÜLÍR


def test_napi_ir_es_index(tmp_path):
    json_export.napi_ir(tmp_path, "2021-01-02", [{"kifejezes": "infláció", "volumen": "50000"}])
    json_export.napi_ir(tmp_path, "2021-01-01", [{"kifejezes": "benzinár", "volumen": "20000"}])
    napi = json.loads((tmp_path / "napok" / "2021-01-02.json").read_text(encoding="utf-8"))
    assert napi["trendek"][0]["kifejezes"] == "infláció"
    index = json.loads((tmp_path / "napok" / "index.json").read_text(encoding="utf-8"))
    assert index["napok"] == ["2021-01-01", "2021-01-02"]  # rendezett, egyedi
