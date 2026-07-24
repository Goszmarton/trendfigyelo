from datetime import datetime, timezone

import pandas as pd
import pytest

from trendfigyelo import idosorok
from trendfigyelo.config import Config
from trendfigyelo.kliens import AgFeladva


def _df():
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 1, 11, tzinfo=timezone.utc),
    ])
    return pd.DataFrame({"infláció": [40, 80], "isPartial": [False, True]}, index=idx)


def test_df_idosor_nan_ures_string_nem_nan():
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 1, 11, tzinfo=timezone.utc),
    ])
    df = pd.DataFrame({"infláció": [float("nan"), 80], "isPartial": [False, False]}, index=idx)
    pontok = idosorok.df_idosor(df, "infláció", "interest_over_time")
    assert pontok[0]["ertek"] == ""     # NEM a literál "nan"
    assert pontok[1]["ertek"] == 80


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


def _config(maxn=5):
    return Config(geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
                  referenciaszo="időjárás", alap_keses_mp=3.0, szoras_mp=(3, 7),
                  max_probak=4, backoff_mp=[30, 120, 480], trend_idosor_max=maxn,
                  proxy=None, kulcsszavak={"g": ["x"]})


def _df_named(name):
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
    return pd.DataFrame({name: [50], "isPartial": [False]}, index=idx)


class _FakeKliens:
    """A hivas a viselkedes szótár szerint ad vissza df-et vagy dob kivételt."""
    def __init__(self, viselkedes):
        self.viselkedes = viselkedes
        self.hivasok = []
        self.tr = type('obj', (object,), {'interest_over_time': None})()

    def hivas(self, ag, fn, kifs, **kw):
        kif = kifs[0]
        self.hivasok.append(kif)
        v = self.viselkedes[kif]
        if isinstance(v, Exception):
            raise v
        return v


def test_gyujt_agfeladva_feladja_az_egesz_agat():
    # az első kifejezés 429-kimerülést dob → az egész ág feladva, 'b'-t meg sem hívja
    k = _FakeKliens({"a": AgFeladva("idosor", ["429", "429", "429", "429"]),
                     "b": _df_named("b")})
    with pytest.raises(AgFeladva):
        idosorok.gyujt(k, _config(), ["a", "b"])
    assert k.hivasok == ["a"]


def test_gyujt_egyeb_hiba_csak_azt_a_trendet_hagyja_ki():
    k = _FakeKliens({"a": RuntimeError("hálózat"), "b": _df_named("b")})
    pontok = idosorok.gyujt(k, _config(), ["a", "b"])
    assert k.hivasok == ["a", "b"]  # 'a' kimarad, 'b' lefut
    assert [p["kifejezes"] for p in pontok] == ["b"]
