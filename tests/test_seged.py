from datetime import datetime, timezone
from pathlib import Path

from trendfigyelo import seged


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
