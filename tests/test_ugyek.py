import json
from pathlib import Path

from trendfigyelo import ugyek as u


def _nap(tmp_path, nap, kifejezesek):
    p = tmp_path / "napok" / f"{nap}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"este": {"trendek": [
        {"kifejezes": k, "volumen": v, "temak": tm, "hirek": hi} for (k, v, tm, hi) in kifejezesek]}},
        ensure_ascii=False), encoding="utf-8")


def test_korpusz_ablak_es_jelenlet(tmp_path):
    _nap(tmp_path, "2026-09-05", [("x", 50, [], [])])          # ablakon KÍVÜL (>30 nap a 10-07-től)
    _nap(tmp_path, "2026-09-20", [("tüntetés", 70, ["Politics"], [{"cim": "H1"}])])
    _nap(tmp_path, "2026-09-21", [("tüntetés", 90, [], [])])
    _nap(tmp_path, "2026-10-07", [("tüntetés", 40, [], [])])
    k = u.ugy_korpusz(str(tmp_path), "2026-10-07", ablak_nap=30)
    kif = {c["kifejezes"]: c for c in k["kifejezesek"]}
    assert "x" not in kif                                       # 2026-09-05 kiesett
    t = kif["tüntetés"]
    assert t["elso_nap"] == "2026-09-20" and t["utolso_nap"] == "2026-10-07"
    assert t["napok_szama"] == 3
    assert t["volumen_sor"][0] == {"nap": "2026-09-20", "max_volumen": 70}
    assert "Politics" in t["temak"] and "H1" in t["hirek"]
    assert k["ablak"]["nap"] == 30


def test_eletut_ujonnan_tartos_visszatero(tmp_path):
    veg = "2026-10-07"
    # újonnan: csak az utolsó pár napon, rövid span
    assert u._eletut({"elso_nap": "2026-10-05", "utolso_nap": "2026-10-07",
                      "napok": ["2026-10-05", "2026-10-06", "2026-10-07"]}, veg, 30) == "ujonnan_megfigyelt"
    # folyamatos: a napok nagy részén jelen
    sok = [f"2026-09-{d:02d}" for d in range(8, 31)] + ["2026-10-0%d" % d for d in range(1, 8)]
    assert u._eletut({"elso_nap": sok[0], "utolso_nap": "2026-10-07", "napok": sok}, veg, 30) == "folyamatosan_jelenlevo"
    # visszatérő: van hosszú szünet, majd újra
    assert u._eletut({"elso_nap": "2026-09-10", "utolso_nap": "2026-10-07",
                      "napok": ["2026-09-10", "2026-09-11", "2026-10-06", "2026-10-07"]}, veg, 30) == "visszatero"


def test_mozgas_iranya():
    assert u._mozgas([{"nap": "a", "max_volumen": 10}, {"nap": "b", "max_volumen": 20},
                      {"nap": "c", "max_volumen": 40}]) == "erosodo"
    assert u._mozgas([{"nap": "a", "max_volumen": 40}, {"nap": "b", "max_volumen": 20},
                      {"nap": "c", "max_volumen": 10}]) == "lecsengo"
    assert u._mozgas([{"nap": "a", "max_volumen": 30}, {"nap": "b", "max_volumen": 31},
                      {"nap": "c", "max_volumen": 29}]) == "stabil"
    assert u._mozgas([{"nap": "a", "max_volumen": 30}]) == "nem_megallapithato"


VEG = "2026-10-07"


def _el(napok):
    return u._eletut({"elso_nap": napok[0], "utolso_nap": napok[-1], "napok": napok}, VEG, 30)


def test_eletut_visszatero_szunet_hatar():
    assert _el(["2026-10-01", "2026-10-04"]) != "visszatero"   # rés pontosan 3
    assert _el(["2026-10-01", "2026-10-05"]) == "visszatero"   # rés 4
    assert u._eletut({"napok": []}, VEG, 30) == "egyeb"


def test_eletut_ujonnan_hatarok():
    assert _el(["2026-10-01", "2026-10-02"]) == "ujonnan_megfigyelt"      # 6 nappal veg elott
    assert _el(["2026-09-30", "2026-10-01"]) != "ujonnan_megfigyelt"      # 7 nappal veg elott
    # veghez kozel kezdodik, de a span > 7
    hosszu = [f"2026-10-0{d}" for d in range(1, 9)]
    assert _el(hosszu) != "ujonnan_megfigyelt"
    # regi rovid span
    assert _el(["2026-09-01", "2026-09-02"]) != "ujonnan_megfigyelt"
    # span pontosan 7 (6 nap elteres) -> meg ujonnan
    assert _el(["2026-10-01", "2026-10-04", "2026-10-07"]) == "ujonnan_megfigyelt"


def test_eletut_folyamatos_arany():
    assert _el(["2026-09-01", "2026-09-04"]) == "folyamatosan_jelenlevo"   # 2/4 = 0.5
    assert _el(["2026-09-01", "2026-09-04", "2026-09-07"]) == "egyeb"      # 3/7 < 0.5
    assert _el(["2026-09-01"]) == "egyeb"                                  # span 1


def test_mozgas_kuszobok():
    m = lambda *v: u._mozgas([{"nap": str(i), "max_volumen": x} for i, x in enumerate(v)])
    assert m(89, 111) == "erosodo"
    assert m(90, 110) == "stabil"      # pontosan +0.2
    assert m(91, 109) == "stabil"
    assert m(111, 89) == "lecsengo"
    assert m(110, 90) == "stabil"      # pontosan -0.2
    assert m(109, 91) == "stabil"
    assert m(0, 0, 0) == "stabil"
    assert m(0, 0.1) == "stabil"       # bazis-padlo 1.0
    assert m(10, 40) == "erosodo"      # 2 pont is eleg
    assert m() == "nem_megallapithato"


def _nap_raw(tmp_path, nap, tartalom):
    p = tmp_path / "napok" / f"{nap}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(tartalom, ensure_ascii=False), encoding="utf-8")


def test_korpusz_ablak_hatarok(tmp_path):
    for nap in ("2026-09-07", "2026-09-08", "2026-10-07", "2026-10-08"):
        _nap(tmp_path, nap, [(f"k{nap}", 10, [], [])])
    k = u.ugy_korpusz(str(tmp_path), "2026-10-07", ablak_nap=30)
    nevek = {c["kifejezes"] for c in k["kifejezesek"]}
    assert nevek == {"k2026-09-08", "k2026-10-07"}
    assert k["ablak"]["kezdet"] == "2026-09-08"


def test_korpusz_reggel_este_max_es_lapos(tmp_path):
    _nap_raw(tmp_path, "2026-10-05", {
        "reggel": {"trendek": [{"kifejezes": "a", "volumen": 80}]},
        "este": {"trendek": [{"kifejezes": "a", "volumen": 30}]}})
    _nap_raw(tmp_path, "2026-10-06", {
        "reggel": {"trendek": [{"kifejezes": "a", "volumen": 20}]},
        "este": {"trendek": [{"kifejezes": "a", "volumen": 60}]}})
    _nap_raw(tmp_path, "2026-10-07", {"trendek": [{"kifejezes": "lapos", "volumen": 5}]})
    k = u.ugy_korpusz(str(tmp_path), VEG)
    kif = {c["kifejezes"]: c for c in k["kifejezesek"]}
    assert kif["a"]["volumen_sor"] == [{"nap": "2026-10-05", "max_volumen": 80},
                                       {"nap": "2026-10-06", "max_volumen": 60}]
    assert kif["lapos"]["napok_szama"] == 1


def test_korpusz_rendezes_es_hirek_plafon(tmp_path):
    hirek = [{"cim": f"H{i}"} for i in range(6)]
    _nap(tmp_path, "2026-10-05", [("ritka", 1, [], []), ("gyakori", 1, [], hirek[:2])])
    _nap(tmp_path, "2026-10-06", [("gyakori", 1, [], hirek[2:4])])
    _nap(tmp_path, "2026-10-07", [("gyakori", 1, [], hirek[4:])])
    k = u.ugy_korpusz(str(tmp_path), VEG)
    assert [c["kifejezes"] for c in k["kifejezesek"]] == ["gyakori", "ritka"]
    assert k["kifejezesek"][0]["hirek"] == ["H0", "H1", "H2"]


def test_korpusz_rendezes_napok_szama_elsodleges(tmp_path):
    _nap(tmp_path, "2026-10-01", [("B", 1, [], []), ("D", 1, [], []), ("C", 1, [], [])])
    for nap in ("2026-10-05", "2026-10-06", "2026-10-07"):
        _nap(tmp_path, nap, [("A", 1, [], [])])
    _nap(tmp_path, "2026-10-02", [("E", 1, [], [])])
    k = u.ugy_korpusz(str(tmp_path), VEG, ablak_nap=30)
    # A (3 nap) elol; utana 1 napos: elso_nap szerint (10-01: B,C,D kifejezes szerint), majd E
    assert [c["kifejezes"] for c in k["kifejezesek"]] == ["A", "B", "C", "D", "E"]
