import bovites as be


def test_ures_argv(capsys):
    assert be.main([]) == 0
    assert "Nincs" in capsys.readouterr().out


def test_siker(monkeypatch):
    hiv = {}
    monkeypatch.setattr(be.ugyek, "ugy_generalas",
                        lambda dd, veg, ki, **kw: hiv.setdefault("v", (dd, veg, ki)) and {"ugyek": []})
    assert be.main(["2026-10-07"]) == 0
    assert hiv["v"][1] == "2026-10-07"


def test_fail_soft(monkeypatch):
    monkeypatch.setattr(be.ugyek, "ugy_generalas", lambda *a, **k: None)
    assert be.main(["2026-10-07"]) == 1
