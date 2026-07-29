import json

from trendfigyelo import json_export


def _kpontok():
    return [
        {"kulcsszo": "infláció", "domen": "gazdasag", "tipus": "szintmero", "nyers_ertek": 40},
        {"kulcsszo": "infláció", "domen": "gazdasag", "tipus": "szintmero", "nyers_ertek": 80},
        {"kulcsszo": "MNB", "domen": "gazdasag", "tipus": "szintmero", "nyers_ertek": ""},
    ]


def test_kulcsszo_napi_osszesites_atlag_es_csucs():
    o = json_export.kulcsszo_napi_osszesites(_kpontok())
    inflacio = next(x for x in o if x["kulcsszo"] == "infláció")
    assert inflacio["atlag"] == 60.0
    assert inflacio["csucs"] == 80.0
    assert inflacio["domen"] == "gazdasag"
    assert inflacio["tipus"] == "szintmero"          # a tipus nem eshet ki némán
    assert inflacio["ossz_pontok"] == 2
    assert inflacio["nulla_pontok"] == 0
    # MNB-nek nincs érvényes (nem-üres) nyers értéke → kihagyva
    assert all(x["kulcsszo"] != "MNB" for x in o)


def test_kulcsszo_napi_osszesites_ervenyes_pontok():
    o = json_export.kulcsszo_napi_osszesites(_kpontok())
    inflacio = next(x for x in o if x["kulcsszo"] == "infláció")
    assert inflacio["atlag"] == 60.0
    assert inflacio["csucs"] == 80.0
    assert inflacio["ervenyes_pontok"] == 2


def test_nulla_ertekek_kihagyva_az_atlagbol():
    # SZÁNDÉKOS (a) szemantika: a 0 kimarad az átlagból, de külön jelként megjelenik.
    pontok = [
        {"kulcsszo": "x", "domen": "g", "tipus": "szintmero", "nyers_ertek": 0},
        {"kulcsszo": "x", "domen": "g", "tipus": "szintmero", "nyers_ertek": 60},
    ]
    x = json_export.kulcsszo_napi_osszesites(pontok)[0]
    assert x["atlag"] == 60.0         # a 0 nem húzza le 30-ra (szint)
    assert x["ervenyes_pontok"] == 1  # nem-nulla pont az átlagban
    assert x["nulla_pontok"] == 1     # a 0 külön (gyakoriság-jel)
    assert x["ossz_pontok"] == 2


def test_esemenyjelzo_szint_es_gyakorisag_kulon():
    # tüntetés-szerű: sok 0 + egy 100 → a szint (atlag) és a gyakoriság (nulla) külön jel.
    pontok = [{"kulcsszo": "tüntetés", "domen": "kozelet", "tipus": "esemenyjelzo", "nyers_ertek": 0}
              for _ in range(168)]
    pontok.append({"kulcsszo": "tüntetés", "domen": "kozelet", "tipus": "esemenyjelzo", "nyers_ertek": 100})
    t = json_export.kulcsszo_napi_osszesites(pontok)[0]
    assert t["tipus"] == "esemenyjelzo"
    assert t["atlag"] == 100.0
    assert t["csucs"] == 100.0
    assert t["ervenyes_pontok"] == 1
    assert t["nulla_pontok"] == 168
    assert t["ossz_pontok"] == 169


def test_ures_nyers_ertek_kimarad():
    pontok = [
        {"kulcsszo": "infláció", "domen": "gazdasag", "tipus": "szintmero", "nyers_ertek": 40},
        {"kulcsszo": "infláció", "domen": "gazdasag", "tipus": "szintmero", "nyers_ertek": 80},
        {"kulcsszo": "infláció", "domen": "gazdasag", "tipus": "szintmero", "nyers_ertek": ""},
    ]
    inflacio = json_export.kulcsszo_napi_osszesites(pontok)[0]
    assert inflacio["ervenyes_pontok"] == 2   # az üres nem számít az átlagba
    assert inflacio["atlag"] == 60.0
    assert inflacio["ossz_pontok"] == 3       # de az összbe igen


def test_legfrissebb_ir_tipus_atmegy_mindket_uton(tmp_path):
    p = json_export.legfrissebb_ir(tmp_path, [], [], _kpontok(), "2021-01-01T12:00:00+00:00", "HU")
    adat = json.loads(p.read_text(encoding="utf-8"))
    assert adat["geo"] == "HU"
    assert adat["frissitve"] == "2021-01-01T12:00:00+00:00"
    assert p.name == "legfrissebb.json"
    # tipus az idősorban ÉS az összesítésben is
    assert adat["kulcsszavak"]["infláció"]["tipus"] == "szintmero"
    o = next(x for x in adat["kulcsszo_osszesites"] if x["kulcsszo"] == "infláció")
    assert o["tipus"] == "szintmero"


def test_tortenet_frissit_ugyanazt_a_napot_felulirja(tmp_path):
    json_export.tortenet_frissit(tmp_path, "2021-01-01", _kpontok())
    p = json_export.tortenet_frissit(tmp_path, "2021-01-01", _kpontok())  # ugyanaz a nap újra
    adat = json.loads(p.read_text(encoding="utf-8"))
    napok = [b["nap"] for b in adat["napok"]]
    assert napok == ["2021-01-01"]  # nem duplikálódik


def _kp(nap_ertek):
    return [{"kulcsszo": "a", "domen": "g", "tipus": "szintmero", "nyers_ertek": nap_ertek}]


def test_tortenet_frissit_napok_visszapotol_es_nem_ir_felul(tmp_path):
    json_export.tortenet_frissit(tmp_path, "2021-01-02", _kp(99))  # meglévő 01-02 (régi 99)
    napi = {"2021-01-01": _kp(10), "2021-01-02": _kp(20), "2021-01-03": _kp(30)}
    p = json_export.tortenet_frissit_napok(tmp_path, napi)
    adat = json.loads(p.read_text(encoding="utf-8"))
    atlagok = {b["nap"]: b["kulcsszavak"][0]["atlag"] for b in adat["napok"]}
    assert [b["nap"] for b in adat["napok"]] == ["2021-01-01", "2021-01-02", "2021-01-03"]  # rendezett
    assert atlagok["2021-01-01"] == 10.0   # visszapótolva (hiányzott)
    assert atlagok["2021-01-02"] == 99.0   # insert-if-absent: a meglévő NEM íródott felül
    assert atlagok["2021-01-03"] == 30.0   # a legfrissebb nap beírva


def test_tortenet_frissit_napok_friss_nap_felulir(tmp_path):
    json_export.tortenet_frissit(tmp_path, "2021-01-03", _kp(99))
    napi = {"2021-01-03": _kp(30)}
    p = json_export.tortenet_frissit_napok(tmp_path, napi)
    adat = json.loads(p.read_text(encoding="utf-8"))
    b = next(x for x in adat["napok"] if x["nap"] == "2021-01-03")
    assert b["kulcsszavak"][0]["atlag"] == 30.0   # a legfrissebb nap FELÜLÍR


def test_teljesen_nulla_kulcsszo_is_kap_sort():
    # M3(b): egy végig-nulla (esemény nélküli) kulcsszó is kapjon sort — atlag=None,
    # de a nulla_pontok/ossz_pontok gyakoriság-jel megmarad (ne tűnjön el a listából).
    pontok = [
        {"kulcsszo": "tüntetés", "domen": "kozelet", "tipus": "esemenyjelzo", "nyers_ertek": 0},
        {"kulcsszo": "tüntetés", "domen": "kozelet", "tipus": "esemenyjelzo", "nyers_ertek": 0},
    ]
    sor = json_export.kulcsszo_napi_osszesites(pontok)[0]
    assert sor["kulcsszo"] == "tüntetés"
    assert sor["atlag"] is None
    assert sor["csucs"] is None
    assert sor["ervenyes_pontok"] == 0
    assert sor["nulla_pontok"] == 2
    assert sor["ossz_pontok"] == 2


# --- Task 7: módszertani töréspont (modszertan_valtas) — CSAK jelölő ---

def test_tortenet_tartalmazza_a_torespontot(tmp_path):
    json_export.tortenet_frissit_napok(tmp_path, {"2026-07-28": _kp(40)}, valtas_datum="2026-07-28")
    adat = json.loads((tmp_path / "tortenet.json").read_text(encoding="utf-8"))
    assert adat["modszertan_valtas"] == "2026-07-28"


def test_legfrissebb_tartalmazza_a_torespontot(tmp_path):
    p = json_export.legfrissebb_ir(tmp_path, [], [], _kpontok(),
                                   "2021-01-01T12:00:00+00:00", "HU", valtas_datum="2026-07-28")
    adat = json.loads(p.read_text(encoding="utf-8"))
    assert adat["modszertan_valtas"] == "2026-07-28"


def test_none_valtas_datum_nem_ir_kulcsot(tmp_path):
    # None → a kulcs HIÁNYZIK (nem null értékkel szerepel).
    json_export.tortenet_frissit_napok(tmp_path, {"2026-07-28": _kp(40)}, valtas_datum=None)
    t = json.loads((tmp_path / "tortenet.json").read_text(encoding="utf-8"))
    assert "modszertan_valtas" not in t
    p = json_export.legfrissebb_ir(tmp_path, [], [], _kpontok(),
                                   "2021-01-01T12:00:00+00:00", "HU", valtas_datum=None)
    l = json.loads(p.read_text(encoding="utf-8"))
    assert "modszertan_valtas" not in l


def test_torespont_idempotens_nem_ir_felul(tmp_path):
    # setdefault (first-wins): a MÁSODIK futás MÁS dátummal NEM írja felül a meglévőt.
    json_export.tortenet_frissit_napok(tmp_path, {"2026-07-28": _kp(40)}, valtas_datum="2026-07-28")
    json_export.tortenet_frissit_napok(tmp_path, {"2026-07-29": _kp(50)}, valtas_datum="2026-08-01")
    adat = json.loads((tmp_path / "tortenet.json").read_text(encoding="utf-8"))
    assert adat["modszertan_valtas"] == "2026-07-28"   # az ELSŐ marad


def test_none_nem_torli_a_meglevo_torespontot(tmp_path):
    # a merge előtti None-futás nem törölheti a már beállított jelölőt.
    json_export.tortenet_frissit_napok(tmp_path, {"2026-07-28": _kp(40)}, valtas_datum="2026-07-28")
    json_export.tortenet_frissit_napok(tmp_path, {"2026-07-29": _kp(50)}, valtas_datum=None)
    adat = json.loads((tmp_path / "tortenet.json").read_text(encoding="utf-8"))
    assert adat["modszertan_valtas"] == "2026-07-28"


def test_napi_ir_es_index(tmp_path):
    json_export.napi_ir(tmp_path, "2021-01-02", [{"kifejezes": "infláció", "volumen": "50000"}])
    json_export.napi_ir(tmp_path, "2021-01-01", [{"kifejezes": "benzinár", "volumen": "20000"}])
    napi = json.loads((tmp_path / "napok" / "2021-01-02.json").read_text(encoding="utf-8"))
    assert napi["trendek"][0]["kifejezes"] == "infláció"
    index = json.loads((tmp_path / "napok" / "index.json").read_text(encoding="utf-8"))
    assert index["napok"] == ["2021-01-01", "2021-01-02"]  # rendezett, egyedi
