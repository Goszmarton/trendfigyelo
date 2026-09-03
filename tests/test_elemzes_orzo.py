import json
from datetime import datetime, timezone

from trendfigyelo import elemzes_orzo


def _ir_artefakt(dd, nap, mode):
    d = dd / "elemzesek"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{nap}.json").write_text(json.dumps({"nap": nap, "mode": mode}), encoding="utf-8")


# ── elemzes_nap ──────────────────────────────────────────────
def test_elemzes_nap_reggel_budapesti_naptari_nap():
    most = datetime(2026, 9, 3, 7, 0, tzinfo=timezone.utc)   # 09:00 Budapest
    assert elemzes_orzo.elemzes_nap("reggel", most) == "2026-09-03"


def test_elemzes_nap_este_esti_nap():
    most = datetime(2026, 9, 3, 19, 0, tzinfo=timezone.utc)  # 21:00 Budapest
    assert elemzes_orzo.elemzes_nap("este", most) == "2026-09-03"


def test_elemzes_nap_este_hajnali_backup_elozo_nap():
    # 2026-09-03T23:30Z = budapesti 2026-09-04T01:30 (<6:00) → esti_nap az ELŐZŐ napot adja
    most = datetime(2026, 9, 3, 23, 30, tzinfo=timezone.utc)
    assert elemzes_orzo.elemzes_nap("este", most) == "2026-09-03"


# ── elemzes_mar_kesz + CLI ───────────────────────────────────
# ── elemzes_mar_kesz ─────────────────────────────────────────
def test_mar_kesz_nincs_fajl_false(tmp_path):
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "reggel") is False
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "este") is False


def test_mar_kesz_reggel_barmely_letezo_true(tmp_path):
    _ir_artefakt(tmp_path, "2026-09-03", "reggel")
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "reggel") is True


def test_mar_kesz_reggel_esti_letezo_true_nem_downgradel(tmp_path):
    _ir_artefakt(tmp_path, "2026-09-03", "este")
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "reggel") is True


def test_mar_kesz_este_reggeli_letezo_false_upgradel(tmp_path):
    _ir_artefakt(tmp_path, "2026-09-03", "reggel")
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "este") is False


def test_mar_kesz_este_esti_letezo_true(tmp_path):
    _ir_artefakt(tmp_path, "2026-09-03", "este")
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "este") is True


def test_mar_kesz_olvashatatlan_este_false(tmp_path):
    d = tmp_path / "elemzesek"; d.mkdir(parents=True)
    (d / "2026-09-03.json").write_text("{nem json", encoding="utf-8")
    assert elemzes_orzo.elemzes_mar_kesz(tmp_path, "2026-09-03", "este") is False   # fail-open


# ── CLI ──────────────────────────────────────────────────────
def test_cli_este_kesz_true(tmp_path, capsys, monkeypatch):
    _ir_artefakt(tmp_path, "2026-09-03", "este")
    monkeypatch.setattr(elemzes_orzo.seged, "most_utc",
                        lambda: datetime(2026, 9, 3, 19, 0, tzinfo=timezone.utc))
    rc = elemzes_orzo.main(["--mode", "este", str(tmp_path)])
    assert rc == 0 and capsys.readouterr().out.strip() == "true"
