import json
from datetime import datetime, timezone

from trendfigyelo import havi_orzo


def _ir_havi(dd, honap, keszult=None):
    d = dd / "havi_nlp"
    d.mkdir(parents=True, exist_ok=True)
    art = {"honap": honap}
    if keszult is not None:
        art["keszult"] = keszult
    (d / f"{honap}.json").write_text(json.dumps(art), encoding="utf-8")


# ── utolso_nap_e ─────────────────────────────────────────────
def test_utolso_nap_szeptember_30_igaz():
    most = datetime(2026, 9, 30, 19, 0, tzinfo=timezone.utc)   # 21:00 BP, szept. 30
    assert havi_orzo.utolso_nap_e(most) is True


def test_utolso_nap_szeptember_15_hamis():
    most = datetime(2026, 9, 15, 19, 0, tzinfo=timezone.utc)
    assert havi_orzo.utolso_nap_e(most) is False


def test_utolso_nap_februar_nem_szokoev_28_igaz():
    most = datetime(2026, 2, 28, 19, 0, tzinfo=timezone.utc)   # 2026 nem szökőév
    assert havi_orzo.utolso_nap_e(most) is True


def test_utolso_nap_februar_szokoev_29_igaz_28_hamis():
    assert havi_orzo.utolso_nap_e(datetime(2028, 2, 29, 19, 0, tzinfo=timezone.utc)) is True
    assert havi_orzo.utolso_nap_e(datetime(2028, 2, 28, 19, 0, tzinfo=timezone.utc)) is False


def test_utolso_nap_30_es_31_napos_honap():
    assert havi_orzo.utolso_nap_e(datetime(2026, 4, 30, 19, 0, tzinfo=timezone.utc)) is True
    assert havi_orzo.utolso_nap_e(datetime(2026, 1, 31, 19, 0, tzinfo=timezone.utc)) is True


def test_utolso_nap_hajnali_backup_ho_fordulo_utan_elozo_ho_utolso_napja():
    # 2026-09-30T23:30Z = budapesti 2026-10-01T01:30 (<6:00) → esti_nap = 2026-09-30 (előző este)
    most = datetime(2026, 9, 30, 23, 30, tzinfo=timezone.utc)
    assert havi_orzo.utolso_nap_e(most) is True
    assert havi_orzo.havi_logikai_honap(most) == "2026-09"


# ── havi_logikai_honap ───────────────────────────────────────
def test_logikai_honap_esti():
    assert havi_orzo.havi_logikai_honap(datetime(2026, 9, 30, 19, 0, tzinfo=timezone.utc)) == "2026-09"


# ── mar_kesz ─────────────────────────────────────────────────
def test_mar_kesz_nincs_fajl_false(tmp_path):
    assert havi_orzo.mar_kesz(tmp_path, "2026-09", "2026-09-30") is False


def test_mar_kesz_mai_keszult_true(tmp_path):
    _ir_havi(tmp_path, "2026-09", keszult="2026-09-30T21:05:00+00:00")
    assert havi_orzo.mar_kesz(tmp_path, "2026-09", "2026-09-30") is True


def test_mar_kesz_ho_kozbeni_keszult_false(tmp_path):
    _ir_havi(tmp_path, "2026-09", keszult="2026-09-17T14:58:00+00:00")   # kézzel, hó közben
    assert havi_orzo.mar_kesz(tmp_path, "2026-09", "2026-09-30") is False


def test_mar_kesz_keszult_nelkul_false(tmp_path):
    _ir_havi(tmp_path, "2026-09", keszult=None)
    assert havi_orzo.mar_kesz(tmp_path, "2026-09", "2026-09-30") is False


# ── kell_generalni ───────────────────────────────────────────
def test_kell_generalni_nem_utolso_nap_none(tmp_path):
    most = datetime(2026, 9, 15, 19, 0, tzinfo=timezone.utc)
    assert havi_orzo.kell_generalni(tmp_path, most) is None


def test_kell_generalni_utolso_nap_nincs_fajl_honap(tmp_path):
    most = datetime(2026, 9, 30, 19, 0, tzinfo=timezone.utc)
    assert havi_orzo.kell_generalni(tmp_path, most) == "2026-09"


def test_kell_generalni_utolso_nap_ho_kozbeni_fajl_ujragenerál(tmp_path):
    _ir_havi(tmp_path, "2026-09", keszult="2026-09-17T14:58:00+00:00")
    most = datetime(2026, 9, 30, 19, 0, tzinfo=timezone.utc)
    assert havi_orzo.kell_generalni(tmp_path, most) == "2026-09"


def test_kell_generalni_utolso_nap_mai_fajl_none(tmp_path):
    _ir_havi(tmp_path, "2026-09", keszult="2026-09-30T21:05:00+00:00")
    most = datetime(2026, 9, 30, 19, 0, tzinfo=timezone.utc)
    assert havi_orzo.kell_generalni(tmp_path, most) is None


# ── CLI ──────────────────────────────────────────────────────
def test_cli_kiirja_a_honapot(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(havi_orzo.seged, "most_utc",
                        lambda: datetime(2026, 9, 30, 19, 0, tzinfo=timezone.utc))
    havi_orzo.main([str(tmp_path)])
    assert capsys.readouterr().out.strip() == "2026-09"


def test_cli_ures_sor_ha_nem_kell(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(havi_orzo.seged, "most_utc",
                        lambda: datetime(2026, 9, 15, 19, 0, tzinfo=timezone.utc))
    havi_orzo.main([str(tmp_path)])
    assert capsys.readouterr().out.strip() == ""
