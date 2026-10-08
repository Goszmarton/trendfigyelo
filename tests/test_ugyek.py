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


def test_valasz_sema_ugyek_enum_szakpolitika():
    s = u._valasz_sema()
    assert s["additionalProperties"] is False and s["required"] == ["ugyek"]
    item = s["properties"]["ugyek"]["items"]
    assert set(item["required"]) == {"nev", "kifejezesek", "szakpolitika", "osszefoglalo"}
    assert item["additionalProperties"] is False
    assert set(item["properties"]["szakpolitika"]["enum"]) == u.szakpolitika.SZAKPOLITIKA_SLUGOK


def test_rendszer_prompt_grounding():
    p = u.RENDSZER_PROMPT_UGYEK
    assert "ügy" in p.lower() and ("GROUNDING" in p or "nem talál" in p.lower())
    assert "csoportos" in p.lower()


class _Stream:
    def __init__(self, v): self._v = v
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self):
        import json as _j
        b = type("B", (), {"type": "text", "text": _j.dumps(self._v, ensure_ascii=False)})()
        return type("M", (), {"content": [b]})()


class _Sdk:
    def __init__(self, v): self.messages = self; self._v = v; self.n = 0
    def stream(self, **kw): self.n += 1; return _Stream(self._v)


def _valasz():
    return {"ugyek": [{"nev": "Üzemanyagárak", "kifejezesek": ["benzin ára", "gázolaj"],
                       "szakpolitika": "energia_rezsi", "osszefoglalo": "x"}]}


def test_ugy_elemez_mock():
    out = u.ugy_elemez({"kifejezesek": []}, kliens=u._UgyKliens(sdk=_Sdk(_valasz())))
    assert out["ugyek"][0]["nev"] == "Üzemanyagárak"


def test_ugy_elemez_bounded_retry():
    class _Buko:
        n = 0
        def uzenet(self, *a, **k):
            self.n += 1
            if self.n < 2:
                raise RuntimeError("int")
            return _valasz()
    assert u.ugy_elemez({}, kliens=_Buko(), alvo=lambda s: None)["ugyek"][0]["szakpolitika"] == "energia_rezsi"


def test_grounding_kiszuri_a_nem_korpuszbeli_kifejezest_es_enumot():
    korpusz = {"kifejezesek": [{"kifejezes": "benzin ára"}, {"kifejezes": "gázolaj"}]}
    eredmeny = {"ugyek": [
        {"nev": "Üzemanyag", "kifejezesek": ["benzin ára", "KITALÁLT"], "szakpolitika": "energia_rezsi", "osszefoglalo": "x"},
        {"nev": "Üres", "kifejezesek": ["NINCS"], "szakpolitika": "egyeb", "osszefoglalo": "y"},
        {"nev": "Rossz enum", "kifejezesek": ["gázolaj"], "szakpolitika": "HOLDbazis", "osszefoglalo": "z"}]}
    out = u.grounding_validal(eredmeny, korpusz)
    nevek = [x["nev"] for x in out["ugyek"]]
    assert "Üres" not in nevek                                  # üres taggé vált → kiesik
    uzem = next(x for x in out["ugyek"] if x["nev"] == "Üzemanyag")
    assert uzem["kifejezesek"] == ["benzin ára"]                # KITALÁLT kiesett
    rossz = next(x for x in out["ugyek"] if x["nev"] == "Rossz enum")
    assert rossz["szakpolitika"] in u.szakpolitika.SZAKPOLITIKA_SLUGOK   # érvénytelen enum → determinista fallback


def test_ugy_osszegez_a_tagokbol():
    korpusz = {"kifejezesek": [
        {"kifejezes": "a", "napok": ["2026-10-01", "2026-10-02"], "elso_nap": "2026-10-01",
         "utolso_nap": "2026-10-02", "volumen_sor": [{"nap": "2026-10-01", "max_volumen": 10}], "eletut": "egyeb", "mozgas": "stabil"},
        {"kifejezes": "b", "napok": ["2026-10-02", "2026-10-03"], "elso_nap": "2026-10-02",
         "utolso_nap": "2026-10-03", "volumen_sor": [{"nap": "2026-10-03", "max_volumen": 20}], "eletut": "egyeb", "mozgas": "erosodo"}]}
    eredmeny = {"ugyek": [{"nev": "Ü", "kifejezesek": ["a", "b"], "szakpolitika": "egyeb", "osszefoglalo": "s"}]}
    out = u.ugy_osszegez(eredmeny, korpusz)
    ugy = out["ugyek"][0]
    assert ugy["elso_nap"] == "2026-10-01" and ugy["utolso_nap"] == "2026-10-03"
    assert ugy["napok_szama"] == 3                               # a,b napjainak uniója: 01,02,03
    assert ugy["eletut"] in ("ujonnan_megfigyelt", "folyamatosan_jelenlevo", "visszatero", "egyeb")
    assert [p["nap"] for p in ugy["idovonal"]] == ["2026-10-01", "2026-10-02", "2026-10-03"]


def test_ugy_generalas_ir_es_meta(tmp_path):
    (tmp_path / "napok").mkdir(parents=True)
    (tmp_path / "napok" / "2026-10-07.json").write_text(
        json.dumps({"este": {"trendek": [{"kifejezes": "benzin ára", "volumen": 50, "temak": [], "hirek": []}]}}),
        encoding="utf-8")
    sdk = _Sdk({"ugyek": [{"nev": "Üzemanyag", "kifejezesek": ["benzin ára"],
                           "szakpolitika": "energia_rezsi", "osszefoglalo": "x"}]})
    out = u.ugy_generalas(str(tmp_path), "2026-10-07", "2026-10-08T07:00:00+00:00",
                          kliens=u._UgyKliens(sdk=sdk))
    assert out is not None
    mentve = json.loads((tmp_path / "ugyek.json").read_text(encoding="utf-8"))
    assert mentve["modell"] == "claude-opus-4-8" and mentve["ablak"]["veg"] == "2026-10-07"
    assert mentve["ugyek"][0]["nev"] == "Üzemanyag" and "idovonal" in mentve["ugyek"][0]


def test_ugy_generalas_fail_soft(tmp_path, monkeypatch):
    monkeypatch.setattr(u.time, "sleep", lambda s: None)        # a bounded retry ne aludjon valósan
    (tmp_path / "napok").mkdir(parents=True)
    (tmp_path / "napok" / "2026-10-07.json").write_text(json.dumps({"este": {"trendek": []}}), encoding="utf-8")
    class _Buko:
        def uzenet(self, *a, **k): raise RuntimeError("tartós")
    assert u.ugy_generalas(str(tmp_path), "2026-10-07", "2026-10-08T07:00:00+00:00", kliens=_Buko()) is None
    assert not (tmp_path / "ugyek.json").exists()
