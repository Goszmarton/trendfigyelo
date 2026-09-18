import json
from trendfigyelo import havi_nlp

def _napfajl(tmp, nap, reggel_szavak, este_szavak=None):
    d = {"nap": nap, "reggel": {"trendek": reggel_szavak}}
    if este_szavak is not None:
        d["este"] = {"trendek": este_szavak}
    (tmp / "napok").mkdir(exist_ok=True)
    (tmp / "napok" / f"{nap}.json").write_text(json.dumps(d), encoding="utf-8")

def _napfajl_regi(tmp, nap, szavak):
    """Régi (2026-08 eleji) lapos szerkezet: top-level `trendek`, NINCS reggel/este szegmens."""
    (tmp / "napok").mkdir(exist_ok=True)
    (tmp / "napok" / f"{nap}.json").write_text(
        json.dumps({"nap": nap, "trendek": szavak}), encoding="utf-8")

def _szo(kif, vol=100, temak=None, hirek=None):
    return {"kifejezes": kif, "volumen": str(vol), "novekedes_pct": "100",
            "temak": temak or ["Hírek"], "hirek": hirek or []}


def test_havi_korpusz_regi_lapos_trendek_visszafele_kompat(tmp_path):
    # 2026-08: régi lapos napok (top-level `trendek`, nincs reggel/este) + egy szegmentált este-only nap
    _napfajl_regi(tmp_path, "2026-08-01", [_szo("jég", 500), _szo("mvm zrt")])
    _napfajl_regi(tmp_path, "2026-08-02", [_szo("jég", 800)])
    _napfajl(tmp_path, "2026-08-31", [], [_szo("időjárás")])          # szegmentált, csak este
    kor = havi_nlp.havi_korpusz(str(tmp_path), "2026-08")
    assert kor["napok"] == 3
    szavak = {s["kifejezes"]: s for s in kor["szavak"]}
    # a régi LAPOS napok ÉS a szegmentált este-only nap szavai IS bekerülnek
    assert set(szavak) == {"jég", "mvm zrt", "időjárás"}
    assert szavak["jég"]["gyakorisag"] == 2                           # két külön lapos napon
    assert szavak["jég"]["max_volumen"] == 800
    assert szavak["időjárás"]["gyakorisag"] == 1                      # a szegmentált este-only napról


def test_havi_korpusz_szegmentalt_nap_nem_olvas_top_level_trendeket(tmp_path):
    # regresszió-őr: ha egy napnak VAN reggel/este szegmense, a top-level `trendek` NEM számít
    (tmp_path / "napok").mkdir(exist_ok=True)
    (tmp_path / "napok" / "2026-09-01.json").write_text(json.dumps({
        "nap": "2026-09-01", "reggel": {"trendek": [_szo("valós")]},
        "trendek": [_szo("kamu")],   # ezt figyelmen kívül kell hagyni
    }), encoding="utf-8")
    kor = havi_nlp.havi_korpusz(str(tmp_path), "2026-09")
    assert {s["kifejezes"] for s in kor["szavak"]} == {"valós"}

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
    # a token-keret elég nagy a havi kimenethez (több száz szó → sok ezer token; a 32000
    # levágta a JSON-t → csonka, json.loads bukott). Regresszió-őr: ne csússzon vissza.
    assert sdk._kw["max_tokens"] >= 64000


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


def test_havi_korpusz_napok_csak_a_beolvasottakat_szamolja(tmp_path):
    # egy ép nap + egy sérült (nem-JSON) fájl → a napok csak az épet számolja (nem a glob-találatot)
    _napfajl(tmp_path, "2026-09-01", [_szo("csalás")])
    (tmp_path / "napok" / "2026-09-02.json").write_text("{ ez nem JSON", encoding="utf-8")
    kor = havi_nlp.havi_korpusz(str(tmp_path), "2026-09")
    assert kor["napok"] == 1                                   # a sérült fájl NEM inflálja a napok-ot
    assert kor["egyedi_szo"] == 1


def test_havi_nlp_generalas_top_level_honapot_ir(tmp_path):
    # a fejléc (havi.js) az art.honap-ot olvassa → a generált artefaktnak top-level honap-ot KELL írnia
    _napfajl(tmp_path, "2026-09-01", [_szo("csalás")])
    valasz = json.dumps({"lemmak": [{"szo": "csalás", "lemma": "csalás"}],
                         "ner": {"orszagok": [], "telepulesek": [], "szemelyek": []},
                         "klaszterek": [{"cimke": "Bűnügy", "szavak": ["csalás"],
                                         "ertelmezes": "…", "uralkodo_temak": []}],
                         "osszegzes": "A hónap…"})
    kliens = havi_nlp._NlpKliens(sdk=_FakeSDK(valasz))
    er = havi_nlp.havi_nlp_generalas(str(tmp_path), "2026-09", "2026-09-30T21:00:00Z", kliens=kliens)
    assert er["honap"] == "2026-09"                            # visszatérési érték
    p = tmp_path / "havi_nlp" / "2026-09.json"
    assert json.loads(p.read_text(encoding="utf-8"))["honap"] == "2026-09"   # a fájlban is


def test_volumen_dusit_entitas_es_klaszter():
    korpusz = {"szavak": [{"kifejezes": "csalás", "max_volumen": 800},
                          {"kifejezes": "átverés", "max_volumen": 200},
                          {"kifejezes": "debrecen", "max_volumen": 500}]}
    er = {"ner": {"orszagok": [], "telepulesek": [{"nev": "Debrecen", "szavak": ["debrecen"]}], "szemelyek": []},
          "klaszterek": [{"cimke": "Bűnügy", "szavak": ["csalás", "átverés"]}], "osszegzes": "…"}
    v = havi_nlp.volumen_dusit(er, korpusz)
    assert v["klaszterek"][0]["volumen"] == 1000                 # 800 + 200
    assert v["ner"]["telepulesek"][0]["volumen"] == 500
    assert er["klaszterek"][0].get("volumen") is None            # NEM mutálja a bemenetet


def test_havi_nlp_index_ir(tmp_path):
    mappa = tmp_path / "havi_nlp"; mappa.mkdir()
    (mappa / "2026-08.json").write_text("{}", encoding="utf-8")
    (mappa / "2026-09.json").write_text("{}", encoding="utf-8")
    p = havi_nlp.havi_nlp_index_ir(str(tmp_path))
    idx = json.loads(p.read_text(encoding="utf-8"))
    assert idx["honapok"] == ["2026-08", "2026-09"] and idx["legutolso"] == "2026-09"


def test_havi_nlp_volumen_utodusit(tmp_path):
    _napfajl(tmp_path, "2026-09-01", [_szo("csalás", 800)])
    (tmp_path / "havi_nlp").mkdir()
    (tmp_path / "havi_nlp" / "2026-09.json").write_text(json.dumps(
        {"ner": {"orszagok": [], "telepulesek": [], "szemelyek": []},
         "klaszterek": [{"cimke": "B", "szavak": ["csalás"]}], "osszegzes": "x"}), encoding="utf-8")
    havi_nlp.havi_nlp_volumen_utodusit(str(tmp_path), "2026-09")
    art = json.loads((tmp_path / "havi_nlp" / "2026-09.json").read_text(encoding="utf-8"))
    assert art["klaszterek"][0]["volumen"] == 800
