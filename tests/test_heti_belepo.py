import importlib
import sys

import heti as heti_belepo


def test_ures_argv_nincs_teendo(capsys):
    assert heti_belepo.main([]) == 0
    assert "Nincs" in capsys.readouterr().out


def test_siker_generalas_es_index(monkeypatch, tmp_path):
    hivott = {}
    monkeypatch.setattr(heti_belepo.heti_ertekeles, "heti_generalas",
                        lambda dd, het, ki, kliens=None: hivott.setdefault("gen", (dd, het, ki)) or {"ok": 1})
    monkeypatch.setattr(heti_belepo.heti_ertekeles, "heti_index_ir",
                        lambda dd: hivott.setdefault("idx", dd))
    assert heti_belepo.main(["2026-09-28"]) == 0
    assert hivott["gen"][1] == "2026-09-28"
    assert "idx" in hivott


def test_fail_soft_nincs_index(monkeypatch):
    monkeypatch.setattr(heti_belepo.heti_ertekeles, "heti_generalas",
                        lambda *a, **k: None)
    hivott = {}
    monkeypatch.setattr(heti_belepo.heti_ertekeles, "heti_index_ir",
                        lambda dd: hivott.setdefault("idx", True))
    assert heti_belepo.main(["2026-09-28"]) == 1
    assert "idx" not in hivott        # bukott generálás → NINCS index-frissítés
