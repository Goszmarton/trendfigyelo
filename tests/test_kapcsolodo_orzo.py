import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from trendfigyelo import kapcsolodo_orzo as ko


def _bp(y, m, d, h):
    return datetime(y, m, d, h, tzinfo=ZoneInfo("Europe/Budapest")).astimezone(timezone.utc)


def test_kell_ha_meg_nincs(tmp_path):
    assert ko.kell(str(tmp_path), _bp(2026, 10, 7, 21)) == "2026-10-07"


def test_skip_ha_ma_mar(tmp_path):
    (tmp_path / "kapcsolodo.json").write_text(json.dumps({"frissitve": "2026-10-07T21:30:00+00:00"}), encoding="utf-8")
    assert ko.kell(str(tmp_path), _bp(2026, 10, 7, 22)) == ""


def test_korabbi_ujra(tmp_path):
    (tmp_path / "kapcsolodo.json").write_text(json.dumps({"frissitve": "2026-10-06T21:30:00+00:00"}), encoding="utf-8")
    assert ko.kell(str(tmp_path), _bp(2026, 10, 7, 21)) == "2026-10-07"


def test_hajnali_elozo_nap(tmp_path):
    assert ko.kell(str(tmp_path), _bp(2026, 10, 8, 2)) == "2026-10-07"


def test_main_cli(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(ko.seged, "most_utc", lambda: _bp(2026, 10, 7, 21))
    assert ko.main([str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == "2026-10-07"
