# tests/test_szakpolitika.py
from trendfigyelo import szakpolitika as sp


def test_nyolc_kategoria_es_slugok():
    assert len(sp.SZAKPOLITIKAK) == 8
    assert sp.SZAKPOLITIKA_SLUGOK == {
        "szocialpolitika", "egeszsegpolitika", "oktataspolitika", "gazdasag_foglalkoztatas",
        "lakhatas", "energia_rezsi", "kozelet_kozigazgatas", "egyeb"}
    assert dict(sp.SZAKPOLITIKAK)["egeszsegpolitika"] == "Egészségpolitika"


def test_kulcsszo_terkep_mind_a_28():
    minta = {"nyugdíj": "szocialpolitika", "segély": "szocialpolitika",
             "kórház": "egeszsegpolitika", "sürgősségi": "egeszsegpolitika",
             "iskola": "oktataspolitika", "pedagógus": "oktataspolitika",
             "infláció": "gazdasag_foglalkoztatas", "állás": "gazdasag_foglalkoztatas",
             "fizetés": "gazdasag_foglalkoztatas", "munkanélküliség": "gazdasag_foglalkoztatas",
             "csőd": "gazdasag_foglalkoztatas", "albérlet": "lakhatas", "eladó lakás": "lakhatas",
             "hitel": "lakhatas", "kölcsön": "lakhatas", "benzin": "energia_rezsi",
             "rezsi": "energia_rezsi", "napelem": "energia_rezsi", "kormányablak": "kozelet_kozigazgatas",
             "tüntetés": "kozelet_kozigazgatas", "korrupció": "kozelet_kozigazgatas",
             "kormány": "kozelet_kozigazgatas", "akciós újság": "egyeb", "nyaralás": "egyeb"}
    for szo, vart in minta.items():
        assert sp.szakpolitika_besorol(kifejezes=szo) == vart, szo


def test_fallback_domen_majd_tema_majd_egyeb():
    assert sp.szakpolitika_besorol(domen="egeszsegugy") == "egeszsegpolitika"
    assert sp.szakpolitika_besorol(domen="oktatas") == "oktataspolitika"
    assert sp.szakpolitika_besorol(temak=["Politics"]) == "kozelet_kozigazgatas"
    assert sp.szakpolitika_besorol(temak=["Health"]) == "egeszsegpolitika"
    assert sp.szakpolitika_besorol(temak=["Ismeretlen"]) == "egyeb"
    assert sp.szakpolitika_besorol() == "egyeb"


def test_prioritas_kulcsszo_eros_a_domen_elott():
    # a kulcsszó-térkép erősebb a doménnél (nyugdíj domen=megelhetes, de szocialpolitika)
    assert sp.szakpolitika_besorol(kifejezes="nyugdíj", domen="megelhetes") == "szocialpolitika"
