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
