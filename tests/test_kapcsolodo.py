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
