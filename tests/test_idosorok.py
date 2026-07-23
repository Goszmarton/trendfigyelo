from datetime import datetime, timezone

import pandas as pd

from trendfigyelo import idosorok


def _df():
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 1, 11, tzinfo=timezone.utc),
    ])
    return pd.DataFrame({"infláció": [40, 80], "isPartial": [False, True]}, index=idx)


def test_df_idosor_pontok_es_ispartial_kihagyva():
    pontok = idosorok.df_idosor(_df(), "infláció", "interest_over_time")
    assert len(pontok) == 2
    assert pontok[0]["idopont_utc"] == "2021-01-01T10:00:00+00:00"
    assert pontok[0]["ertek"] == 40
    assert pontok[1]["ertek"] == 80
    assert all(p["kifejezes"] == "infláció" for p in pontok)


def test_csv_ir_fejlec_es_geo(tmp_path):
    pontok = idosorok.df_idosor(_df(), "infláció", "interest_over_time")
    p = idosorok.csv_ir(tmp_path, "2021-01-01_1200", "2021-01-01T12:00:00+00:00", "HU", pontok)
    sorok = p.read_text(encoding="utf-8-sig").splitlines()
    assert sorok[0] == "kifejezes;idopont_utc;ertek;letoltve_utc;forras;geo"
    assert sorok[1].endswith(";HU")
    assert p.name == "top_trend_idosor_HU_2021-01-01_1200.csv"
