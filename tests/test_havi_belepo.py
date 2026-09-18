import havi
from trendfigyelo import havi_nlp


def test_siker_index_ir_hivodik_es_0(monkeypatch):
    hivott = {"gen": 0, "idx": 0}
    monkeypatch.setattr(havi_nlp, "havi_nlp_generalas",
                        lambda dd, h, k, kliens=None: (hivott.__setitem__("gen", 1) or {"honap": h}))
    monkeypatch.setattr(havi_nlp, "havi_nlp_index_ir",
                        lambda dd: hivott.__setitem__("idx", 1))
    rc = havi.main(["2026-09"])
    assert rc == 0
    assert hivott == {"gen": 1, "idx": 1}


def test_fail_soft_none_nincs_index_es_1(monkeypatch):
    hivott = {"idx": 0}
    monkeypatch.setattr(havi_nlp, "havi_nlp_generalas", lambda dd, h, k, kliens=None: None)
    monkeypatch.setattr(havi_nlp, "havi_nlp_index_ir", lambda dd: hivott.__setitem__("idx", 1))
    rc = havi.main(["2026-09"])
    assert rc == 1
    assert hivott["idx"] == 0


def test_ures_arg_nincs_teendo_0(monkeypatch):
    monkeypatch.setattr(havi_nlp, "havi_nlp_generalas",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("nem hívható")))
    assert havi.main([""]) == 0
    assert havi.main([]) == 0
