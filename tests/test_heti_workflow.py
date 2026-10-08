from pathlib import Path

import yaml


def _wf():
    return yaml.safe_load(Path(".github/workflows/heti.yml").read_text(encoding="utf-8"))


def test_trigger_a_reggeli_gyujtesre():
    wf = _wf()
    on = wf[True] if True in wf else wf["on"]           # a yaml az `on`-t True-ra oldhatja
    assert on["workflow_run"]["workflows"] == ["Reggeli felkapott-gyűjtés"]
    assert "workflow_dispatch" in on


def test_or_a_pip_install_elott_es_anthropic_secret():
    szoveg = Path(".github/workflows/heti.yml").read_text(encoding="utf-8")
    i_or = szoveg.index("trendfigyelo.heti_orzo")
    i_pip = szoveg.index("pip install")
    assert i_or < i_pip                                  # az őr a pip install ELŐTT
    assert "ANTHROPIC_API_KEY" in szoveg
    assert "secrets.ANTHROPIC_API_KEY" in szoveg


def test_commit_csak_a_heti_mappat():
    szoveg = Path(".github/workflows/heti.yml").read_text(encoding="utf-8")
    assert "git add docs/data/heti" in szoveg
    assert "python heti.py" in szoveg
