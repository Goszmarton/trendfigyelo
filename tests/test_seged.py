import os
from datetime import datetime, timezone
from pathlib import Path

from trendfigyelo import seged


# --- ATOMI-IRAS: seged.atomi_ir_szoveg ---

def test_atomi_ir_szoveg_kiirja_a_tartalmat_es_nem_hagy_temp_szemetet(tmp_path):
    fajl = tmp_path / "adat.json"
    seged.atomi_ir_szoveg(fajl, '{"x": 1}')
    assert fajl.read_text(encoding="utf-8") == '{"x": 1}'
    assert not list(tmp_path.glob("*.tmp"))          # nincs temp maradék siker után


def test_atomi_ir_szoveg_megszakadt_kommit_megorzi_a_regit_es_nem_hagy_tempet(tmp_path, monkeypatch):
    # ha az os.replace (a KOMMIT) elhasal, a MEGLÉVŐ fájl bájtjai sértetlenek, és a temp törlődik
    fajl = tmp_path / "adat.json"
    fajl.write_text("REGI", encoding="utf-8")

    def _crash(*a, **k):
        raise OSError("kommit crash")
    monkeypatch.setattr(os, "replace", _crash)

    try:
        seged.atomi_ir_szoveg(fajl, "UJ")
    except OSError:
        pass
    assert fajl.read_text(encoding="utf-8") == "REGI", "a régi fájl megsérült a megszakadt kommitnál"
    assert not list(tmp_path.glob("*.tmp")), "maradt szemét temp fájl"


def test_szovegge_kezeli_a_none_es_lista_eseteket():
    assert seged.szovegge(None) == ""
    assert seged.szovegge(["a", "b"]) == "a, b"
    assert seged.szovegge(42) == "42"


def test_idove_unix_bol_utc_iso():
    # 2021-01-01T00:00:00Z == 1609459200
    assert seged.idove(1609459200) == "2021-01-01T00:00:00+00:00"
    assert seged.idove(None) == ""
    assert seged.idove((1609459200, 999)) == "2021-01-01T00:00:00+00:00"


def test_idopont_iso_tz_naiv_datetime_utcnek_veszi():
    assert seged.idopont_iso(datetime(2021, 1, 1, 0, 0, 0)) == "2021-01-01T00:00:00+00:00"


def test_bp_idobelyeg_budapesti_ido():
    # 2021-06-01T10:00:00Z nyáron Budapesten 12:00 (UTC+2)
    dt = datetime(2021, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert seged.bp_idobelyeg(dt) == "2021-06-01_1200"


def test_csv_iro_utf8_sig_es_pontosvesszo(tmp_path):
    fajl = tmp_path / "t.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow(["á", "b"])
    nyers = fajl.read_bytes()
    assert nyers.startswith(b"\xef\xbb\xbf")  # utf-8-sig BOM
    assert b";" in nyers


# --- B2: utolso_res — kimaradt napi futás észlelése (belső folytonosság, utolsó két dátum) ---

def test_utolso_res_nincs():
    """Az utolsó két dátum folytonos (1 nap köz) → nincs rés."""
    assert seged.utolso_res(["2026-08-03", "2026-08-05", "2026-08-06"]) == []


def test_utolso_res_egy_nap():
    """08-05 után rögtön 08-07 (a mai 08-06-kimaradás esete) → a hiányzó 08-06."""
    assert seged.utolso_res(["2026-08-05", "2026-08-07"]) == ["2026-08-06"]


def test_utolso_res_tobb_nap():
    """08-05 után 08-08 → két hiányzó nap, sorrendben (off-by-one őr)."""
    assert seged.utolso_res(["2026-08-05", "2026-08-08"]) == ["2026-08-06", "2026-08-07"]


def test_utolso_res_ures_es_egyelemu():
    """Nincs összevethető pár (üres/egyelemű index, első futás) → [], nem IndexError."""
    assert seged.utolso_res([]) == []
    assert seged.utolso_res(["2026-08-05"]) == []


def test_utolso_res_ev_hatar():
    """Év-/hónaphatár: valódi dátum-aritmetikát kényszerít (naiv string-/int-kivonás őre)."""
    assert seged.utolso_res(["2026-12-31", "2027-01-02"]) == ["2027-01-01"]
