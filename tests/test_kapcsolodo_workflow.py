# tests/test_kapcsolodo_workflow.py
from pathlib import Path
import yaml


def _wf():
    return yaml.safe_load(Path(".github/workflows/kapcsolodo.yml").read_text(encoding="utf-8"))


def test_trigger_a_napi_gyujtesre():
    on = _wf()
    on = on[True] if True in on else on["on"]
    assert on["workflow_run"]["workflows"] == ["Napi trendgyűjtés"]
    assert "workflow_dispatch" in on


def test_or_a_pip_install_elott():
    sz = Path(".github/workflows/kapcsolodo.yml").read_text(encoding="utf-8")
    assert sz.index("trendfigyelo.kapcsolodo_orzo") < sz.index("pip install")
    assert "python kapcsolodo.py" in sz


def test_commit_csak_a_kapcsolodo_json_es_nincs_anthropic():
    sz = Path(".github/workflows/kapcsolodo.yml").read_text(encoding="utf-8")
    assert "git add docs/data/kapcsolodo.json" in sz
    assert "ANTHROPIC_API_KEY" not in sz       # nincs LLM
