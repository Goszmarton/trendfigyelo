from pathlib import Path
import yaml


def _wf():
    return yaml.safe_load(Path(".github/workflows/bovites.yml").read_text(encoding="utf-8"))


def test_trigger_a_napi_gyujtesre():
    wf = _wf()
    on = wf[True] if True in wf else wf["on"]
    assert on["workflow_run"]["workflows"] == ["Napi trendgyűjtés"]
    assert "workflow_dispatch" in on


def test_or_a_pip_install_elott_es_secret():
    sz = Path(".github/workflows/bovites.yml").read_text(encoding="utf-8")
    assert sz.index("trendfigyelo.bovites_orzo") < sz.index("pip install")
    assert "secrets.ANTHROPIC_API_KEY" in sz
    assert "python bovites.py" in sz


def test_commit_csak_az_ugyek_json():
    sz = Path(".github/workflows/bovites.yml").read_text(encoding="utf-8")
    assert "git add docs/data/ugyek.json" in sz
