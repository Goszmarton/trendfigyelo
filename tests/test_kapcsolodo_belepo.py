# tests/test_kapcsolodo_belepo.py
import kapcsolodo as be


def test_siker_sajat_plafon(monkeypatch):
    hiv = {}
    class _Cfg: max_probak = 4
    monkeypatch.setattr(be, "betolt", lambda: _Cfg())
    monkeypatch.setattr(be, "Kliens", lambda cfg, plafon=None: (hiv.setdefault("plafon", plafon), "KLIENS")[1])
    monkeypatch.setattr(be.kapcsolodo, "gyujt",
                        lambda dd, kl, cfg, most, **kw: (hiv.setdefault("gyujt", (dd, kl)), {"frissitve": "x", "kifejezesek": []})[1])
    monkeypatch.setattr(be.kapcsolodo, "kapcsolodo_ir", lambda dd, adat: hiv.setdefault("ir", adat))
    assert be.main([]) == 0
    assert hiv["plafon"] == be.kapcsolodo.CAP * 4 + 1      # saját, szűk plafon
    assert hiv["gyujt"][1] == "KLIENS" and "ir" in hiv


def test_cap_argumentum(monkeypatch):
    hiv = {}
    class _Cfg: max_probak = 4
    monkeypatch.setattr(be, "betolt", lambda: _Cfg())
    monkeypatch.setattr(be, "Kliens", lambda cfg, plafon=None: hiv.setdefault("plafon", plafon))
    monkeypatch.setattr(be.kapcsolodo, "gyujt", lambda dd, kl, cfg, most, cap=None, **kw: (hiv.setdefault("cap", cap), {"frissitve": "x", "kifejezesek": []})[1])
    monkeypatch.setattr(be.kapcsolodo, "kapcsolodo_ir", lambda dd, adat: None)
    assert be.main(["--cap", "3"]) == 0
    assert hiv["cap"] == 3 and hiv["plafon"] == 3 * 4 + 1
