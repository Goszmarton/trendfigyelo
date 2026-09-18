from pathlib import Path

import yaml


def _wf():
    p = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "havi.yml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def test_havi_workflow_letezik_es_parsol():
    assert _wf() is not None


def test_trigger_napi_trendgyujtes_es_dispatch():
    wf = _wf()
    on = wf[True] if True in wf else wf["on"]     # a PyYAML az 'on:'-t True kulcsként olvashatja
    assert "workflow_dispatch" in on
    assert on["workflow_run"]["workflows"] == ["Napi trendgyűjtés"]
    assert "completed" in on["workflow_run"]["types"]


def test_generalo_lepes_anthropic_kulccsal():
    wf = _wf()
    steps = wf["jobs"]["havi"]["steps"]
    szoveg = yaml.safe_dump(steps, allow_unicode=True)
    assert "ANTHROPIC_API_KEY" in szoveg
    assert "python -m trendfigyelo.havi_orzo" in szoveg
    assert "havi.py" in szoveg


def test_commit_csak_havi_nlp_es_rebase():
    wf = _wf()
    szoveg = yaml.safe_dump(wf["jobs"]["havi"]["steps"], allow_unicode=True)
    assert "docs/data/havi_nlp" in szoveg
    assert "git pull --rebase" in szoveg
    # NEM stage-eli a napi/trend adatot
    assert "docs/data/elemzes.json" not in szoveg
