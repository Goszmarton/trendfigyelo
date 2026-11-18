import json
from pathlib import Path

import pytest
import yaml

from trendfigyelo import ai_szunet


def _ir(tmp_path, tartalom):
    (tmp_path / "ai_szunet.json").write_text(tartalom, encoding="utf-8")


def test_hianyzo_fajl_nincs_szunet(tmp_path):
    assert ai_szunet.szunetel("napi", tmp_path) is False


def test_tipusonkent_olvas(tmp_path):
    _ir(tmp_path, json.dumps({"szunetel": {"napi": True, "heti": False}}))
    assert ai_szunet.szunetel("napi", tmp_path) is True
    assert ai_szunet.szunetel("heti", tmp_path) is False
    assert ai_szunet.szunetel("havi", tmp_path) is False


@pytest.mark.parametrize("tartalom", ["{nem json", "[]", '{"szunetel": "igen"}', '{"szunetel": {"napi": "true"}}'])
def test_hibas_fajl_fail_open(tmp_path, tartalom):
    _ir(tmp_path, tartalom)
    assert ai_szunet.szunetel("napi", tmp_path) is False


def test_ismeretlen_tipus():
    with pytest.raises(ValueError):
        ai_szunet.szunetel("eves")


def test_cli(tmp_path, capsys):
    _ir(tmp_path, json.dumps({"szunetel": {"havi": True}}))
    ai_szunet.main(["x", "havi", str(tmp_path)])
    assert capsys.readouterr().out.strip() == "true"


def test_eles_fajl_ervenyes_es_mindharom_szunetel():
    d = json.loads(Path("docs/data/ai_szunet.json").read_text(encoding="utf-8"))
    assert d["szunetel"] == {"napi": True, "heti": True, "havi": True, "ugyek": True}
    assert d["uzenet"]


@pytest.mark.parametrize("wf,tipus,or_modul", [
    ("elemzes", "napi", "trendfigyelo.elemzes_orzo"),
    ("heti", "heti", "trendfigyelo.heti_orzo"),
    ("havi", "havi", "trendfigyelo.havi_orzo"),
    ("bovites", "ugyek", "trendfigyelo.bovites_orzo"),
])
def test_workflow_a_szunet_ort_a_generalas_elott_nezi(wf, tipus, or_modul):
    szoveg = Path(f".github/workflows/{wf}.yml").read_text(encoding="utf-8")
    hivas = f"python -m trendfigyelo.ai_szunet {tipus} docs/data"
    assert hivas in szoveg
    # a szünet-ellenőrzés a kézi felülbírálás és az idempotencia-őr ELŐTT van (a dispatch sem kerüli meg)
    assert szoveg.index(hivas) < szoveg.index(or_modul)
    kezi = 'if [ -n "$KEZI" ]' if wf != "elemzes" else 'if [ "${{ github.event_name }}" = "workflow_dispatch" ]'
    assert szoveg.index(hivas) < szoveg.index(kezi)
    yaml.safe_load(szoveg)


def test_minden_anthropic_kulcsot_hasznalo_workflow_szuneteltetheto():
    """A token-költség teljes leállításához MINDEN API-kulcsot kapó workflow-nak a szünet-őr mögött kell lennie."""
    for wf in Path(".github/workflows").glob("*.yml"):
        szoveg = wf.read_text(encoding="utf-8")
        if "ANTHROPIC_API_KEY" in szoveg:
            assert "python -m trendfigyelo.ai_szunet " in szoveg, wf.name
