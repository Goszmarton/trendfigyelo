# tests/test_bovites_orzo.py
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from trendfigyelo import bovites_orzo as bo


def _bp(y, m, d, h):
    return datetime(y, m, d, h, tzinfo=ZoneInfo("Europe/Budapest")).astimezone(timezone.utc)


def test_kell_generalni_ha_meg_nincs(tmp_path):
    assert bo.kell_generalni(str(tmp_path), _bp(2026, 10, 7, 21)) == "2026-10-07"


def test_idempotencia_ma_mar_kesz(tmp_path):
    (tmp_path / "ugyek.json").write_text(json.dumps({"szamitva_utc": "2026-10-07T21:30:00+00:00"}), encoding="utf-8")
    assert bo.kell_generalni(str(tmp_path), _bp(2026, 10, 7, 22)) is None


def test_korabbi_keszult_ujra(tmp_path):
    (tmp_path / "ugyek.json").write_text(json.dumps({"szamitva_utc": "2026-10-06T21:30:00+00:00"}), encoding="utf-8")
    assert bo.kell_generalni(str(tmp_path), _bp(2026, 10, 7, 21)) == "2026-10-07"


def test_hajnali_az_elozo_naphoz(tmp_path):
    # 2026-10-08 02:00 BP → esti_nap = 2026-10-07 → azt generálja
    assert bo.kell_generalni(str(tmp_path), _bp(2026, 10, 8, 2)) == "2026-10-07"


def test_main_cli(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(bo.seged, "most_utc", lambda: _bp(2026, 10, 7, 21))
    assert bo.main([str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == "2026-10-07"
