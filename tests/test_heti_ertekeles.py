# tests/test_heti_ertekeles.py
import json
from pathlib import Path

from trendfigyelo import heti_ertekeles as he


def _ir(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _regresszio_fajl(tmp_path):
    # két követett szó: egy „felette" (erősödő, pozitív eltérés) és egy „alatta" (gyengülő)
    _ir(tmp_path / "kulcsszo_regresszio.json", {
        "szamitva_utc": "2026-10-05T18:00:00+00:00",
        "kulcsszavak": {
            "benzinár": {"domen": "megelhetes", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": True, "irany": "nő", "illeszkedes": "felette",
                          "mai_ertek": 80, "mai_reziduum": 20.0, "reziduum_szokasos": 8.0,
                          "meredekseg_nap": 2.5,
                          "illesztes_vonal": [{"idopont_utc": "2026-09-29T00:00:00+00:00", "ertek": 60.0},
                                              {"idopont_utc": "2026-10-05T00:00:00+00:00", "ertek": 78.0}]}}},
            "nyugdíj": {"domen": "megelhetes", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": True, "irany": "csökken", "illeszkedes": "alatta",
                          "mai_ertek": 30, "mai_reziduum": 5.0, "reziduum_szokasos": 12.0,
                          "meredekseg_nap": -1.0, "illesztes_vonal": []}}},
        },
    })


def _youtube_fajl(tmp_path):
    _ir(tmp_path / "youtube_regresszio.json", {
        "szamitva_utc": "2026-10-05T18:00:00+00:00",
        "kulcsszavak": {
            "szorongás": {"domen": "egeszseg", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": True, "irany": "stagnál", "illeszkedes": "illeszkedik",
                          "mai_ertek": 14}}},
            "fejfájás": {"domen": "egeszseg", "tipus": "szintmero", "intervallumok": {
                "1_het": {"ervenyes": False, "ok": "kevés pont"}}},
        },
    })


def _nap(tmp_path, nap, kifejezesek):
    _ir(tmp_path / "napok" / f"{nap}.json",
        {"este": {"trendek": [{"kifejezes": k, "volumen": v, "temak": tm, "hirek": hi}
                               for (k, v, tm, hi) in kifejezesek]}})


def test_heti_korpusz_het_hatarok_es_iso(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")   # hétfő
    assert k["het_kezdet"] == "2026-09-29"
    assert k["het_veg"] == "2026-10-05"                # vasárnap
    assert k["iso_het"] == "2026-W40"


def test_heti_korpusz_kulcsszavak_elteres_es_irany(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    szavak = {s["szo"]: s for s in k["kulcsszavak"]}
    assert szavak["benzinár"]["irany"] == "nő"
    assert szavak["benzinár"]["illeszkedes"] == "felette"
    assert round(szavak["benzinár"]["elteres_szokasostol"], 2) == 12.0   # 20.0 - 8.0
    assert round(szavak["nyugdíj"]["elteres_szokasostol"], 2) == -7.0    # 5.0 - 12.0
    assert szavak["benzinár"]["domen"] == "megelhetes"
    assert szavak["benzinár"]["palya"][0]["ertek"] == 60.0


def test_heti_korpusz_elteres_none_ha_ervenytelen_vagy_hianyzik(tmp_path):
    _ir(tmp_path / "kulcsszo_regresszio.json", {"kulcsszavak": {
        "x": {"domen": "d", "tipus": "t", "intervallumok": {"1_het": {"ervenyes": False}}}}})
    _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    assert k["kulcsszavak"][0]["elteres_szokasostol"] is None
    assert k["kulcsszavak"][0]["irany"] is None


def test_heti_korpusz_felkapott_csak_a_het_napjaibol_napok_szama(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    _nap(tmp_path, "2026-09-28", [("héten kívül", 90, [], [])])        # előző vasárnap — KIMARAD
    _nap(tmp_path, "2026-09-29", [("tüntetés", 70, ["Politika"], [{"cim": "H1"}])])
    _nap(tmp_path, "2026-09-30", [("tüntetés", 90, ["Politika"], [{"cim": "H2"}])])
    _nap(tmp_path, "2026-10-05", [("tüntetés", 50, [], [])])
    _nap(tmp_path, "2026-10-06", [("héten kívül2", 10, [], [])])       # köv. hétfő — KIMARAD
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    fel = {f["kifejezes"]: f for f in k["felkapott"]}
    assert "héten kívül" not in fel and "héten kívül2" not in fel
    assert fel["tüntetés"]["napok_szama"] == 3
    assert fel["tüntetés"]["max_volumen"] == 90
    assert "Politika" in fel["tüntetés"]["temak"]
    assert "H1" in fel["tüntetés"]["hirek"] and len(fel["tüntetés"]["hirek"]) <= 3
    assert k["napok"] == 3        # a 3 héten-belüli nap


def test_heti_korpusz_youtube_ervenyes_es_ervenytelen(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    k = he.heti_korpusz(str(tmp_path), "2026-09-29")
    yt = {y["szo"]: y for y in k["youtube"]}
    assert yt["szorongás"]["irany"] == "stagnál" and yt["szorongás"]["nincs_adat"] is False
    assert yt["fejfájás"]["nincs_adat"] is True and yt["fejfájás"]["irany"] is None


def test_valasz_sema_hat_resz():
    s = he._valasz_sema()
    assert s["additionalProperties"] is False
    props = s["properties"]
    assert set(s["required"]) == {
        "vezetoi_osszefoglalo", "figyelem_atrendezodes", "ugyek_eletutja",
        "melyebb_temak", "google_youtube_osszefugges", "jovo_heti_figyelendok"}
    # Darabszám-korlát a PROMPTban, NEM a sémában (az output_config.format.schema a maxItems-t tömbön 400-zal
    # elutasítja). Regresszió-őr: maxItems NE kerüljön vissza.
    assert props["vezetoi_osszefoglalo"]["type"] == "array" and "maxItems" not in props["vezetoi_osszefoglalo"]
    assert set(props["figyelem_atrendezodes"]["required"]) == {"erosodo", "gyengulo"}
    assert set(props["ugyek_eletutja"]["required"]) == {"rovid_kiugras", "hosszabb_kiugras", "visszatero"}
    assert props["melyebb_temak"]["type"] == "array" and "maxItems" not in props["melyebb_temak"]
    tema = props["melyebb_temak"]["items"]
    assert set(tema["required"]) == {
        "tema", "keresesi_palya", "kapcsolodo_kifejezesek", "ellenorzott_esemenyek", "magyarazat"}
    assert tema["additionalProperties"] is False


def test_rendszer_prompt_grounding_es_hat_resz():
    p = he.RENDSZER_PROMPT_HETI
    assert "hétfő" in p and "vasárnap" in p
    assert "GROUNDING" in p or "nem találsz ki" in p
    assert "tartóssság" in p or "tartóss" in p or "tartós" in p   # az ügyek tartóssága
    assert "ellenőrzött" in p or "hír" in p                       # események csak hírből


class _HamisStream:
    def __init__(self, valasz): self._v = valasz
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self):
        class _B:
            type = "text"
            text = None
        b = _B(); b.text = json.dumps(self._v, ensure_ascii=False)
        return type("M", (), {"content": [b]})


class _HamisSdk:
    def __init__(self, valasz): self.messages = self; self._v = valasz; self.hivasok = 0
    def stream(self, **kw): self.hivasok += 1; return _HamisStream(self._v)


def _teljes_valasz():
    return {"vezetoi_osszefoglalo": ["a", "b"],
            "figyelem_atrendezodes": {"erosodo": ["benzinár"], "gyengulo": ["nyugdíj"]},
            "ugyek_eletutja": {"rovid_kiugras": "x", "hosszabb_kiugras": "y", "visszatero": "z"},
            "melyebb_temak": [{"tema": "T", "keresesi_palya": "p", "kapcsolodo_kifejezesek": "k",
                               "ellenorzott_esemenyek": "e", "magyarazat": "m"}],
            "google_youtube_osszefugges": "gy",
            "jovo_heti_figyelendok": ["f1"]}


def test_heti_elemez_mock_sdk_atveszi_a_valaszt():
    sdk = _HamisSdk(_teljes_valasz())
    out = he.heti_elemez({"het_kezdet": "2026-09-29", "kulcsszavak": [], "felkapott": [], "youtube": []},
                         kliens=he._HetiKliens(sdk=sdk))
    assert out["vezetoi_osszefoglalo"] == ["a", "b"]
    assert sdk.hivasok == 1


def test_heti_elemez_bounded_retry(monkeypatch):
    class _Buko:
        def uzenet(self, *a, **k):
            self.n = getattr(self, "n", 0) + 1
            if self.n < 2:
                raise RuntimeError("intermittens")
            return _teljes_valasz()
    out = he.heti_elemez({}, kliens=_Buko(), alvo=lambda s: None)
    assert out["google_youtube_osszefugges"] == "gy"


def test_grounding_kiszuri_a_nem_korpuszbeli_hivatkozast():
    korpusz = {"kulcsszavak": [{"szo": "benzinár"}, {"szo": "nyugdíj"}],
               "felkapott": [{"kifejezes": "tüntetés"}], "youtube": [{"szo": "szorongás"}]}
    eredmeny = {"figyelem_atrendezodes": {"erosodo": ["benzinár", "KITALÁLT"], "gyengulo": ["nyugdíj"]},
                "vezetoi_osszefoglalo": ["x"], "ugyek_eletutja": {},
                "melyebb_temak": [], "google_youtube_osszefugges": "", "jovo_heti_figyelendok": []}
    out = he.grounding_validal(eredmeny, korpusz)
    assert "benzinár" in out["figyelem_atrendezodes"]["erosodo"]
    assert "KITALÁLT" not in out["figyelem_atrendezodes"]["erosodo"]   # nem korpuszbeli → kiesik


def test_figyelem_adat_rendezett_nem_none():
    korpusz = {"kulcsszavak": [
        {"szo": "a", "elteres_szokasostol": 12.0, "irany": "nő", "illeszkedes": "felette", "domen": "d"},
        {"szo": "b", "elteres_szokasostol": None, "irany": None, "illeszkedes": None, "domen": "d"},
        {"szo": "c", "elteres_szokasostol": -7.0, "irany": "csökken", "illeszkedes": "alatta", "domen": "d"}]}
    adat = he.figyelem_adat(korpusz)
    assert [x["szo"] for x in adat] == ["a", "c"]            # None kiesik, eltérés szerint csökkenő
    assert adat[0]["elteres"] == 12.0 and adat[1]["elteres"] == -7.0


def test_heti_generalas_ir_es_meta(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    sdk = _HamisSdk(_teljes_valasz())
    out = he.heti_generalas(str(tmp_path), "2026-09-29", "2026-10-06T07:00:00+00:00",
                            kliens=he._HetiKliens(sdk=sdk))
    assert out is not None
    p = tmp_path / "heti" / "2026-09-29.json"
    assert p.exists()
    mentve = json.loads(p.read_text(encoding="utf-8"))
    assert mentve["het_kezdet"] == "2026-09-29" and mentve["het_veg"] == "2026-10-05"
    assert mentve["iso_het"] == "2026-W40"
    assert mentve["keszult"] == "2026-10-06T07:00:00+00:00"
    assert mentve["modell"] == "claude-opus-4-8"
    assert mentve["vezetoi_osszefoglalo"] == ["a", "b"]
    assert any(x["szo"] == "benzinár" for x in mentve["figyelem"])
    assert mentve["korpusz"]["napok"] == 0


def test_heti_generalas_fail_soft_none(tmp_path):
    _regresszio_fajl(tmp_path); _youtube_fajl(tmp_path)
    class _Buko:
        def uzenet(self, *a, **k): raise RuntimeError("tartós")
    out = he.heti_generalas(str(tmp_path), "2026-09-29", "2026-10-06T07:00:00+00:00",
                            kliens=_Buko())
    assert out is None
    assert not (tmp_path / "heti" / "2026-09-29.json").exists()


def test_heti_index_ir(tmp_path):
    for h in ("2026-09-22", "2026-09-29"):
        (tmp_path / "heti").mkdir(parents=True, exist_ok=True)
        (tmp_path / "heti" / f"{h}.json").write_text("{}", encoding="utf-8")
    he.heti_index_ir(str(tmp_path))
    idx = json.loads((tmp_path / "heti" / "index.json").read_text(encoding="utf-8"))
    assert idx["hetek"] == ["2026-09-22", "2026-09-29"]
    assert idx["legutolso"] == "2026-09-29"
