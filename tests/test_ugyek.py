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
