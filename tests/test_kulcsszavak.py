from datetime import datetime, timezone

import pandas as pd
import pytest

from trendfigyelo import kulcsszavak
from trendfigyelo.config import Config
from trendfigyelo.kliens import AgFeladva


def _config():
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        referenciaszo="időjárás", alap_keses_mp=3.0, szoras_mp=(3, 7),
        max_probak=4, backoff_mp=[30, 120, 480], trend_idosor_max=15, proxy=None,
        kulcsszavak={"megelhetes": ["a", "b", "c", "d", "e"], "gazdaság": ["f"]},
    )


def test_kotegek_4es_bontas_referenciaszoval():
    kot = kulcsszavak.kotegek(_config())
    # 6 kulcsszó → 2 köteg (4 + 2)
    assert len(kot) == 2
    assert len(kot[0]["tagok"]) == 4
    assert kot[0]["referenciaszo"] == "időjárás"
    assert kulcsszavak.koteg_lekerdezes_szavai(kot[0])[-1] == "időjárás"
    assert len(kulcsszavak.koteg_lekerdezes_szavai(kot[0])) == 5


def test_skalazo_atlagra_szamol():
    assert kulcsszavak.skalazo([50, 50]) == 2.0   # 100 / 50
    assert kulcsszavak.skalazo([0, 0]) is None


def test_parse_koteg_nyers_es_normalizalt():
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
    df = pd.DataFrame({"a": [30], "b": [60], "időjárás": [50]}, index=idx)
    koteg = {"id": 0, "tagok": [("a", "megelhetes"), ("b", "megelhetes")],
             "referenciaszo": "időjárás"}
    pontok = kulcsszavak.parse_koteg(df, koteg)
    a_pont = next(p for p in pontok if p["kulcsszo"] == "a")
    assert a_pont["nyers_ertek"] == 30
    # skálázó = 100/50 = 2.0 → normalizált = 30*2 = 60.0
    assert a_pont["normalizalt_ertek"] == 60.0
    assert a_pont["csoport"] == "megelhetes"
    assert a_pont["koteg_id"] == 0


def test_csv_ir_fejlec(tmp_path):
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
    df = pd.DataFrame({"a": [30], "időjárás": [50]}, index=idx)
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    pontok = kulcsszavak.parse_koteg(df, koteg)
    p = kulcsszavak.csv_ir(tmp_path, "2021-01-01_1200", "2021-01-01T12:00:00+00:00", "HU", pontok)
    fejlec = p.read_text(encoding="utf-8-sig").splitlines()[0]
    assert fejlec == ("kulcsszo;csoport;idopont_utc;nyers_ertek;normalizalt_ertek;"
                      "koteg_id;referenciaszo;letoltve_utc;geo")
    assert p.name == "kulcsszo_idosor_HU_2021-01-01_1200.csv"


def _config_2koteg():
    return Config(geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
                  referenciaszo="időjárás", alap_keses_mp=3.0, szoras_mp=(3, 7),
                  max_probak=4, backoff_mp=[30, 120, 480], trend_idosor_max=15,
                  proxy=None, kulcsszavak={"g": ["a", "b", "c", "d", "e", "f", "g2", "h"]})


def _koteg_df(szavak, ref):
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
    adat = {sz: [50] for sz in szavak}
    adat[ref] = [50]
    return pd.DataFrame(adat, index=idx)


class _FakeKliens:
    """A hivas a viselkodes lista (hívási sorrend) szerint ad df-et vagy dob kivételt."""
    def __init__(self, viselkedes):
        self.viselkedes = viselkedes
        self.hivasszamlalo = 0
        self.tr = type('obj', (object,), {'interest_over_time': None})()

    def hivas(self, ag, fn, szavak, **kw):
        i = self.hivasszamlalo
        self.hivasszamlalo += 1
        v = self.viselkedes[i]
        if isinstance(v, Exception):
            raise v
        return v


def test_gyujt_agfeladva_feladja_az_egesz_agat():
    # 8 kulcsszó → 2 köteg; az 1. köteg 429-kimerülést dob → egész ág feladva
    k = _FakeKliens([AgFeladva("kulcsszo", ["429", "429", "429", "429"]),
                     _koteg_df(["e", "f", "g2", "h"], "időjárás")])
    with pytest.raises(AgFeladva):
        kulcsszavak.gyujt(k, _config_2koteg())
    assert k.hivasszamlalo == 1  # a 2. köteget meg sem hívja


def test_gyujt_egyeb_hiba_csak_azt_a_koteget_hagyja_ki():
    df2 = _koteg_df(["e", "f", "g2", "h"], "időjárás")
    k = _FakeKliens([RuntimeError("hálózat"), df2])
    pontok = kulcsszavak.gyujt(k, _config_2koteg())
    assert k.hivasszamlalo == 2                     # mindkét köteget meghívja
    assert {p["koteg_id"] for p in pontok} == {1}   # csak a 2. köteg pontjai jönnek át


def test_parse_koteg_nan_nem_dobal():
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
    df = pd.DataFrame({"a": [float("nan")], "időjárás": [50]}, index=idx)
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    pontok = kulcsszavak.parse_koteg(df, koteg)
    assert pontok[0]["nyers_ertek"] == ""
    assert pontok[0]["normalizalt_ertek"] == ""
