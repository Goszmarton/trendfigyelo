import json
from trendfigyelo import havi_nlp

def _napfajl(tmp, nap, reggel_szavak, este_szavak=None):
    d = {"nap": nap, "reggel": {"trendek": reggel_szavak}}
    if este_szavak is not None:
        d["este"] = {"trendek": este_szavak}
    (tmp / "napok").mkdir(exist_ok=True)
    (tmp / "napok" / f"{nap}.json").write_text(json.dumps(d), encoding="utf-8")

def _szo(kif, vol=100, temak=None, hirek=None):
    return {"kifejezes": kif, "volumen": str(vol), "novekedes_pct": "100",
            "temak": temak or ["Hírek"], "hirek": hirek or []}

def test_havi_korpusz_aggregal_dedup_gyakorisag(tmp_path):
    _napfajl(tmp_path, "2026-09-01", [_szo("csalás", 500), _szo("albérlet")])
    _napfajl(tmp_path, "2026-09-02", [_szo("csalás", 800)], [_szo("időjárás")])
    kor = havi_nlp.havi_korpusz(str(tmp_path), "2026-09")
    assert kor["honap"] == "2026-09" and kor["napok"] == 2
    szavak = {s["kifejezes"]: s for s in kor["szavak"]}
    assert szavak["csalás"]["gyakorisag"] == 2                 # két külön napon
    assert szavak["csalás"]["max_volumen"] == 800             # a max
    assert set(szavak) == {"csalás", "albérlet", "időjárás"}  # egyedi, reggel+este
    assert kor["egyedi_szo"] == 3
    # gyakoriság szerint rendezve (csalás elöl)
    assert kor["szavak"][0]["kifejezes"] == "csalás"


class _FakeStream:
    def __init__(self, valasz): self._v = valasz
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self):
        class M:
            content = [type("B", (), {"type": "text", "text": None})()]
        M.content[0].text = self._v
        return M

class _FakeSDK:
    def __init__(self, valasz): self.messages = self; self._v = valasz; self.hivva = 0
    def stream(self, **kw): self.hivva += 1; self._kw = kw; return _FakeStream(self._v)

def test_havi_nlp_elemez_strukturalt_JSON_mockolt_sdkval():
    korpusz = {"honap": "2026-09", "napok": 2, "egyedi_szo": 2,
               "szavak": [{"kifejezes": "csalás", "gyakorisag": 2, "max_volumen": 800, "temak": [], "hirek": []},
                          {"kifejezes": "debrecen időjárás", "gyakorisag": 1, "max_volumen": 100, "temak": [], "hirek": []}]}
    valasz = json.dumps({"lemmak": [{"szo": "csalás", "lemma": "csalás"},
                                    {"szo": "debrecen időjárás", "lemma": "debrecen időjárás"}],
                         "ner": {"orszagok": [], "telepulesek": [{"nev": "Debrecen", "szavak": ["debrecen időjárás"]}],
                                 "szemelyek": []},
                         "klaszterek": [{"cimke": "Bűnügy", "szavak": ["csalás"], "ertelmezes": "…", "uralkodo_temak": []},
                                        {"cimke": "Időjárás", "szavak": ["debrecen időjárás"], "ertelmezes": "…", "uralkodo_temak": []}],
                         "osszegzes": "A hónap…"})
    sdk = _FakeSDK(valasz)
    kliens = havi_nlp._NlpKliens(sdk=sdk)
    er = havi_nlp.havi_nlp_elemez(korpusz, kliens=kliens)
    assert sdk.hivva == 1
    assert er["ner"]["telepulesek"][0]["nev"] == "Debrecen"
    assert {k["cimke"] for k in er["klaszterek"]} == {"Bűnügy", "Időjárás"}
    # a séma-hívás strukturált JSON-t kért:
    assert sdk._kw["output_config"]["format"]["type"] == "json_schema"


def test_grounding_validal_kiszuri_a_nem_korpuszbeli_entitast():
    korpusz = {"szavak": [{"kifejezes": "csalás"}, {"kifejezes": "albérlet"}]}
    er = {"lemmak": [{"szo": "csalás", "lemma": "csalás"}],
          "ner": {"orszagok": [{"nev": "Kitalált", "szavak": ["nincs ilyen szó"]}], "telepulesek": [], "szemelyek": []},
          "klaszterek": [{"cimke": "A", "szavak": ["csalás", "kamu szó"], "ertelmezes": "…"}],
          "osszegzes": "…"}
    v = havi_nlp.grounding_validal(er, korpusz)
    # a nem-korpuszbeli entitás/tag KIESIK
    assert v["ner"]["orszagok"] == []                                  # a "nincs ilyen szó" nem korpusz-szó
    assert "kamu szó" not in v["klaszterek"][0]["szavak"]              # a lógó tag kiesik
    assert "csalás" in v["klaszterek"][0]["szavak"]


def test_havi_nlp_ir_kulon_fajlba(tmp_path):
    p = havi_nlp.havi_nlp_ir(str(tmp_path), "2026-09", {"honap": "2026-09", "klaszterek": []})
    assert p.name == "2026-09.json" and p.parent.name == "havi_nlp"
    assert json.loads(p.read_text(encoding="utf-8"))["honap"] == "2026-09"
