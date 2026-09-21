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


def test_guard_a_pip_install_elott_es_pip_install_gate_elt():
    steps = _wf()["jobs"]["havi"]["steps"]
    def idx(pred):
        return next(i for i, s in enumerate(steps) if pred(s))
    guard_i = idx(lambda s: s.get("id") == "guard")
    pip_i = idx(lambda s: "pip install -r requirements.txt" in (s.get("run") or ""))
    # az őr a pip install ELŐTT fut (csak stdlib kell hozzá) → nem-utolsó-napon NINCS telepítés
    assert guard_i < pip_i
    # a pip install CSAK generáláskor fut (az őr honap-outputja nem üres)
    assert steps[pip_i].get("if") == "steps.guard.outputs.honap != ''"


def test_commit_csak_havi_nlp_es_rebase():
    wf = _wf()
    szoveg = yaml.safe_dump(wf["jobs"]["havi"]["steps"], allow_unicode=True)
    # PONTOSAN a havi_nlp mappát stage-eli (nem véletlenül a napok/elemzesek/trend adatot)
    assert "git add docs/data/havi_nlp" in szoveg
    assert "git pull --rebase" in szoveg
    # NEM stage-el semmilyen más adat-utat
    assert "docs/data/elemzes.json" not in szoveg
    assert "docs/data/napok" not in szoveg
    assert "docs/data/elemzesek" not in szoveg
