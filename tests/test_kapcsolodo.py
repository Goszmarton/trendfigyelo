import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from trendfigyelo import kapcsolodo as kp


def _nap(tmp_path, nap, trendek):
    p = tmp_path / "napok" / f"{nap}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"este": {"trendek": [
        {"kifejezes": k, "volumen": v} for (k, v) in trendek]}}, ensure_ascii=False), encoding="utf-8")


def test_jeloltek_top_volumen_es_cap(tmp_path):
    _nap(tmp_path, "2026-10-06", [("a", 10), ("b", 90)])
    _nap(tmp_path, "2026-10-07", [("b", 50), ("c", 70), ("d", 30)])
    most = datetime(2026, 10, 7, 21, tzinfo=timezone.utc)
    jel = kp.jeloltek(str(tmp_path), {}, most, cap=2, staleness_nap=7)
    assert jel == [("b", 90), ("c", 70)]            # max volumen a 2 napból, top 2


def test_jeloltek_staleness_kizar(tmp_path):
    _nap(tmp_path, "2026-10-07", [("b", 90), ("c", 70)])
    most = datetime(2026, 10, 7, 21, tzinfo=timezone.utc)
    meglevo = {"b": "2026-10-05T21:00:00+00:00"}     # 2 napja frissült → staleness 7-en belül → kizár
    jel = kp.jeloltek(str(tmp_path), meglevo, most, cap=5, staleness_nap=7)
    assert [k for k, _ in jel] == ["c"]


def test_jeloltek_regi_lekerdezes_ujra(tmp_path):
    _nap(tmp_path, "2026-10-07", [("b", 90)])
    most = datetime(2026, 10, 7, 21, tzinfo=timezone.utc)
    meglevo = {"b": "2026-09-01T21:00:00+00:00"}     # >7 napja → újra jelölt
    assert kp.jeloltek(str(tmp_path), meglevo, most, cap=5, staleness_nap=7) == [("b", 90)]


def test_parse_related_df_es_breakout():
    eredmeny = {
        "top": pd.DataFrame({"query": ["benzin ár", "mol benzin"], "value": [100, 19]}),
        "rising": pd.DataFrame({"query": ["benzin ársapka", "új"], "value": [8350, "Breakout"]}),
    }
    out = kp._parse_related(eredmeny, limit=15)
    assert out["top"] == [{"query": "benzin ár", "value": 100}, {"query": "mol benzin", "value": 19}]
    assert out["rising"][0] == {"query": "benzin ársapka", "value": 8350}
    assert out["rising"][1] == {"query": "új", "value": "Breakout"}    # string megőrizve


def test_parse_related_none_es_ures():
    assert kp._parse_related(None) == {"top": [], "rising": []}
    assert kp._parse_related({"top": None, "rising": pd.DataFrame({"query": [], "value": []})}) == {"top": [], "rising": []}


def test_parse_related_limit():
    df = pd.DataFrame({"query": [f"q{i}" for i in range(20)], "value": list(range(20))})
    out = kp._parse_related({"top": df, "rising": df}, limit=15)
    assert len(out["top"]) == 15 and len(out["rising"]) == 15


MOST = datetime(2026, 10, 7, 21, tzinfo=timezone.utc)


def test_jeloltek_napok_vissza_ablak(tmp_path):
    _nap(tmp_path, "2026-10-05", [("regi", 99)])
    _nap(tmp_path, "2026-10-06", [("kozep", 50)])
    _nap(tmp_path, "2026-10-07", [("uj", 40)])
    jel = kp.jeloltek(str(tmp_path), {}, MOST, cap=10, staleness_nap=7)
    assert sorted(k for k, _ in jel) == ["kozep", "uj"]


def test_jeloltek_staleness_hatar(tmp_path):
    _nap(tmp_path, "2026-10-07", [("b", 90)])
    het = {"b": "2026-09-30T21:00:00+00:00"}    # pontosan 7 nap
    assert kp.jeloltek(str(tmp_path), het, MOST, cap=5, staleness_nap=7) == [("b", 90)]
    hat = {"b": "2026-10-01T21:00:00+00:00"}    # 6 nap
    assert kp.jeloltek(str(tmp_path), hat, MOST, cap=5, staleness_nap=7) == []


def test_jeloltek_egyenlo_volumen_nev_szerint(tmp_path):
    _nap(tmp_path, "2026-10-07", [("z", 50), ("a", 50)])
    assert kp.jeloltek(str(tmp_path), {}, MOST, cap=1, staleness_nap=7) == [("a", 50)]


def test_jeloltek_reggel_es_lapos_formatum(tmp_path):
    n = tmp_path / "napok"
    n.mkdir()
    (n / "2026-10-06.json").write_text(json.dumps(
        {"trendek": [{"kifejezes": "lapos", "volumen": 10}]}), encoding="utf-8")
    (n / "2026-10-07.json").write_text(json.dumps(
        {"reggel": {"trendek": [{"kifejezes": "reggeli", "volumen": 20}]}}), encoding="utf-8")
    jel = kp.jeloltek(str(tmp_path), {}, MOST, cap=10, staleness_nap=7)
    assert jel == [("reggeli", 20), ("lapos", 10)]


def test_jeloltek_robusztussag(tmp_path):
    _nap(tmp_path, "2026-10-07", [("ok", 5), ("", 99), ("  ", 98)])
    p = tmp_path / "napok" / "2026-10-07.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["este"]["trendek"].append({"kifejezes": "nincsvol", "volumen": None})
    p.write_text(json.dumps(d), encoding="utf-8")
    (tmp_path / "napok" / "index.json").write_text("{\"trendek\": [{\"kifejezes\": \"idx\", \"volumen\": 1000}]}", encoding="utf-8")
    jel = kp.jeloltek(str(tmp_path), {}, MOST, cap=10, staleness_nap=7)
    assert jel == [("ok", 5), ("nincsvol", 0)]


def test_parse_related_ures_es_szokozos_query():
    df = pd.DataFrame({"query": ["", "  ", " x "], "value": [1, 2, 3]})
    out = kp._parse_related({"top": df, "rising": None}, limit=15)
    assert out["top"] == [{"query": "x", "value": 3}]
