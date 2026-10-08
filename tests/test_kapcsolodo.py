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


class _FakeTr:
    def __init__(self, map_):
        self._map = map_          # kif -> {top, rising} dict VAGY Exception-példány
        self.hivott = []

    def related_queries(self, keyword, geo=None, timeframe=None, headers=None):
        self.hivott.append((keyword, geo, timeframe, headers))
        r = self._map.get(keyword)
        if isinstance(r, Exception):
            raise r
        return r


class _FakeKliens:
    def __init__(self, tr): self.tr = tr
    def hivas(self, ag, fn, *a, **k): return fn(*a, **k)   # throttle nélkül (teszt)


class _Cfg:
    geo = "HU"; max_probak = 4


def _df(rows):
    import pandas as pd
    return pd.DataFrame({"query": [q for q, _ in rows], "value": [v for _, v in rows]})


def test_related_egy_referer_es_parse():
    tr = _FakeTr({"benzin": {"top": _df([("benzin ár", 100)]), "rising": _df([("ársapka", "Breakout")])}})
    out = kp.related_egy(_FakeKliens(tr), "benzin", _Cfg(), timeframe="today 3-m")
    assert out["top"] == [{"query": "benzin ár", "value": 100}]
    assert tr.hivott[0][3] == {"referer": "https://www.google.com/"}   # referer-header átadva
    assert tr.hivott[0][1] == "HU" and tr.hivott[0][2] == "today 3-m"


def test_related_egy_soft_fail():
    tr = _FakeTr({"x": RuntimeError("kvóta")})
    assert kp.related_egy(_FakeKliens(tr), "x", _Cfg()) is None     # nem dob, None


def test_gyujt_merge_lekerdezve_es_retencio(tmp_path):
    _nap(tmp_path, "2026-10-07", [("benzin", 90), ("rezsi", 50)])
    tr = _FakeTr({"benzin": {"top": _df([("benzin ár", 100)]), "rising": _df([])},
                  "rezsi": {"top": _df([("rezsi csökkentés", 80)]), "rising": _df([])}})
    most = datetime(2026, 10, 7, 21, tzinfo=timezone.utc)
    out = kp.gyujt(str(tmp_path), _FakeKliens(tr), _Cfg(), most, cap=5, retencio=30)
    kif = {k["kifejezes"]: k for k in out["kifejezesek"]}
    assert "benzin" in kif and kif["benzin"]["lekerdezve"] == most.isoformat()
    assert kif["benzin"]["volumen"] == 90 and kif["benzin"]["top"][0]["query"] == "benzin ár"
    assert out["frissitve"] == most.isoformat()


def test_gyujt_soft_fail_kihagy(tmp_path):
    _nap(tmp_path, "2026-10-07", [("benzin", 90)])
    tr = _FakeTr({"benzin": RuntimeError("kvóta")})
    out = kp.gyujt(str(tmp_path), _FakeKliens(tr), _Cfg(), datetime(2026, 10, 7, 21, tzinfo=timezone.utc))
    assert out["kifejezesek"] == []     # soft-fail → nincs bejegyzés, de nem dob


def test_kapcsolodo_ir(tmp_path):
    p = kp.kapcsolodo_ir(str(tmp_path), {"frissitve": "x", "kifejezesek": []})
    assert Path(p).exists() and json.loads(Path(p).read_text(encoding="utf-8"))["frissitve"] == "x"


def _bej(kif, lek):
    return {"kifejezes": kif, "lekerdezve": lek, "volumen": 1,
            "top": [{"query": "t", "value": 1}], "rising": [{"query": "r", "value": 2}]}


def _ir_kapcs(tmp_path, bejegyzesek):
    (tmp_path / "kapcsolodo.json").write_text(
        json.dumps({"frissitve": "x", "kifejezesek": bejegyzesek}, ensure_ascii=False), encoding="utf-8")


def test_gyujt_merge_sort_retencio(tmp_path):
    regi = [_bej("old1", "2026-09-01T00:00:00+00:00"), _bej("old2", "2026-09-10T00:00:00+00:00"),
            _bej("old3", "2026-09-20T00:00:00+00:00")]
    _ir_kapcs(tmp_path, regi)
    _nap(tmp_path, "2026-10-07", [("uj", 80)])
    tr = _FakeTr({"uj": {"top": _df([("uj ar", 5)]), "rising": _df([])}})
    most = datetime(2026, 10, 7, 21, tzinfo=timezone.utc)
    out = kp.gyujt(str(tmp_path), _FakeKliens(tr), _Cfg(), most, retencio=3)
    nevek = [k["kifejezes"] for k in out["kifejezesek"]]
    assert nevek == ["uj", "old3", "old2"]
    assert out["kifejezesek"][1] == regi[2] and out["kifejezesek"][2] == regi[1]
    tr2 = _FakeTr({"uj": {"top": _df([("uj ar", 5)]), "rising": _df([])}})
    out2 = kp.gyujt(str(tmp_path), _FakeKliens(tr2), _Cfg(), most, retencio=30)
    assert [k["kifejezes"] for k in out2["kifejezesek"]] == ["uj", "old3", "old2", "old1"]


def test_gyujt_friss_kizar_es_cap(tmp_path):
    most = datetime(2026, 10, 7, 21, tzinfo=timezone.utc)
    friss = _bej("benzin", "2026-10-06T21:00:00+00:00")
    _ir_kapcs(tmp_path, [friss])
    _nap(tmp_path, "2026-10-07", [("benzin", 99), ("a", 50), ("b", 40), ("c", 30)])
    ures = {"top": _df([]), "rising": _df([])}
    tr = _FakeTr({"benzin": ures, "a": ures, "b": ures, "c": ures})
    out = kp.gyujt(str(tmp_path), _FakeKliens(tr), _Cfg(), most, cap=2)
    hivott = [h[0] for h in tr.hivott]
    assert "benzin" not in hivott
    assert len(hivott) == 2
    assert friss in out["kifejezesek"]


def test_gyujt_rising_tarolva(tmp_path):
    _nap(tmp_path, "2026-10-07", [("benzin", 90)])
    tr = _FakeTr({"benzin": {"top": _df([]), "rising": _df([("arsapka", 250)])}})
    out = kp.gyujt(str(tmp_path), _FakeKliens(tr), _Cfg(), datetime(2026, 10, 7, 21, tzinfo=timezone.utc))
    assert out["kifejezesek"][0]["rising"] == [{"query": "arsapka", "value": 250}]


def test_gyujt_serult_json_nem_dob(tmp_path):
    (tmp_path / "kapcsolodo.json").write_text("{nemjson", encoding="utf-8")
    _nap(tmp_path, "2026-10-07", [("benzin", 90)])
    tr = _FakeTr({"benzin": {"top": _df([]), "rising": _df([])}})
    out = kp.gyujt(str(tmp_path), _FakeKliens(tr), _Cfg(), datetime(2026, 10, 7, 21, tzinfo=timezone.utc))
    assert isinstance(out, dict) and out["kifejezesek"][0]["kifejezes"] == "benzin"
