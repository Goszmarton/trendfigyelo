from datetime import date, datetime, timezone

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
    pontok = kulcsszavak.parse_koteg(df, koteg, date(2021, 1, 2), 1.0)
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
    pontok = kulcsszavak.parse_koteg(df, koteg, date(2021, 1, 2), 1.0)
    p = kulcsszavak.csv_ir(tmp_path, "2021-01-01_1200", "2021-01-01T12:00:00+00:00", "HU", pontok)
    fejlec = p.read_text(encoding="utf-8-sig").splitlines()[0]
    assert fejlec == ("kulcsszo;csoport;idopont_utc;nyers_ertek;normalizalt_ertek;"
                      "koteg_id;referenciaszo;referencia_atlag;letoltve_utc;geo")
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
    pontok = kulcsszavak.parse_koteg(df, koteg, date(2021, 1, 2), 1.0)
    assert pontok[0]["nyers_ertek"] == ""
    assert pontok[0]["normalizalt_ertek"] == ""


def _tobbnapos_df():
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 2, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 2, 12, tzinfo=timezone.utc),  # 2021-01-02 a mai (részleges) nap
    ])
    return pd.DataFrame({"a": [30, 40, 50], "időjárás": [0, 0, 0]}, index=idx)


def test_utolso_teljes_nap_kizarja_a_mait():
    df = _tobbnapos_df()
    # mai budapesti nap = 2021-01-02 → utolsó teljes = 2021-01-01
    assert kulcsszavak.utolso_teljes_nap(df, date(2021, 1, 2)) == date(2021, 1, 1)


def test_utolso_teljes_nap_nincs_korabbi():
    df = _tobbnapos_df()
    assert kulcsszavak.utolso_teljes_nap(df, date(2021, 1, 1)) is None


def test_parse_koteg_csak_az_utolso_teljes_napot():
    df = _tobbnapos_df()
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    pontok = kulcsszavak.parse_koteg(df, koteg, date(2021, 1, 2), 1.0)
    # csak 2021-01-01 marad (1 pont), a 2021-01-02-i kettő kizárva
    assert len(pontok) == 1
    assert pontok[0]["nyers_ertek"] == 30


def test_utolso_teljes_nap_tobb_teljes_nap_kozul_a_legutolso():
    # 3 teljes nap (01-01, 01-02, 01-03) + csonka mai (01-04) → 01-03
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 2, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 3, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 4, 9, tzinfo=timezone.utc),
    ])
    df = pd.DataFrame({"a": [10, 20, 30, 40], "időjárás": [50, 50, 50, 50]}, index=idx)
    assert kulcsszavak.utolso_teljes_nap(df, date(2021, 1, 4)) == date(2021, 1, 3)


def test_parse_koteg_tobb_teljes_nap_csak_a_legutolso():
    # élesben a 7-d ablakban több teljes nap van; a szűrésnek a LEGUTOLSÓT kell választania
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),  # teljes nap — KIZÁRVA
        datetime(2021, 1, 2, 10, tzinfo=timezone.utc),  # teljes nap — KIZÁRVA
        datetime(2021, 1, 3, 8, tzinfo=timezone.utc),   # legutolsó teljes nap — BENN
        datetime(2021, 1, 3, 12, tzinfo=timezone.utc),  # legutolsó teljes nap — BENN
        datetime(2021, 1, 4, 9, tzinfo=timezone.utc),   # mai (csonka) — KIZÁRVA
    ])
    df = pd.DataFrame({"a": [10, 20, 30, 35, 40], "időjárás": [50, 50, 50, 50, 50]}, index=idx)
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    pontok = kulcsszavak.parse_koteg(df, koteg, date(2021, 1, 4), 1.0)
    assert [p["nyers_ertek"] for p in pontok] == [30, 35]  # csak a 01-03 két pontja
    assert kulcsszavak.aggregalt_nap(pontok) == "2021-01-03"


def test_parse_koteg_ervenytelen_referencia_ures_normalizalt():
    df = _tobbnapos_df()  # időjárás végig 0 → referencia-átlag nincs → érvénytelen
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    p = kulcsszavak.parse_koteg(df, koteg, date(2021, 1, 2), 1.0)[0]
    assert p["referencia_ervenyes"] is False
    assert p["normalizalt_ertek"] == ""
    assert p["referencia_atlag"] == ""


def test_parse_koteg_ervenyes_referencia_normalizal():
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
    df = pd.DataFrame({"a": [30], "időjárás": [50]}, index=idx)
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    p = kulcsszavak.parse_koteg(df, koteg, date(2021, 1, 2), 1.0)[0]
    assert p["referencia_ervenyes"] is True
    assert p["referencia_atlag"] == 50.0
    assert p["nyers_ertek"] == 30
    assert p["normalizalt_ertek"] == 60.0  # 30 * (100/50)


def test_parse_koteg_kuszob_alatti_de_mert_referencia_dokumentalt():
    # referencia mérhető (nem-nulla), de a küszöb (2.0) alatt → normalizált üres,
    # de a referencia_atlag a MÉRT számot mutatja (nem üres)
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
    df = pd.DataFrame({"a": [30], "időjárás": [1]}, index=idx)  # ref átlag = 1.0
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    p = kulcsszavak.parse_koteg(df, koteg, date(2021, 1, 2), 2.0)[0]  # min_atlag=2.0 → érvénytelen
    assert p["referencia_ervenyes"] is False
    assert p["normalizalt_ertek"] == ""
    assert p["referencia_atlag"] == 1.0   # a mért átlag látszik, nem ""


def test_aggregalt_nap_a_pontok_budapesti_napja():
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
    df = pd.DataFrame({"a": [30], "időjárás": [50]}, index=idx)
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    pontok = kulcsszavak.parse_koteg(df, koteg, date(2021, 1, 2), 1.0)
    assert kulcsszavak.aggregalt_nap(pontok) == "2021-01-01"
    assert kulcsszavak.aggregalt_nap([]) is None


def test_csv_ir_referencia_atlag_oszlop(tmp_path):
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
    df = pd.DataFrame({"a": [30], "időjárás": [50]}, index=idx)
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    pontok = kulcsszavak.parse_koteg(df, koteg, date(2021, 1, 2), 1.0)
    p = kulcsszavak.csv_ir(tmp_path, "2021-01-01_1200", "2021-01-01T12:00:00+00:00", "HU", pontok)
    fejlec = p.read_text(encoding="utf-8-sig").splitlines()[0]
    assert fejlec == ("kulcsszo;csoport;idopont_utc;nyers_ertek;normalizalt_ertek;"
                      "koteg_id;referenciaszo;referencia_atlag;letoltve_utc;geo")


def test_utolso_N_teljes_nap_utolso_harmat_adja():
    idx = pd.to_datetime(
        [datetime(2021, 1, d, 10, tzinfo=timezone.utc) for d in (1, 2, 3, 4)]
        + [datetime(2021, 1, 5, 9, tzinfo=timezone.utc)]  # mai (csonka)
    )
    df = pd.DataFrame({"a": [10, 20, 30, 40, 50], "időjárás": [50] * 5}, index=idx)
    # mai=01-05 → teljes: 01-01..01-04 → utolsó 3 = [01-02, 01-03, 01-04]
    assert kulcsszavak.utolso_N_teljes_nap(df, date(2021, 1, 5), 3) == [
        date(2021, 1, 2), date(2021, 1, 3), date(2021, 1, 4),
    ]


def test_utolso_N_teljes_nap_kevesebb_mint_n():
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 2, 9, tzinfo=timezone.utc),   # mai (csonka)
    ])
    df = pd.DataFrame({"a": [10, 20], "időjárás": [50, 50]}, index=idx)
    assert kulcsszavak.utolso_N_teljes_nap(df, date(2021, 1, 2), 3) == [date(2021, 1, 1)]


def test_parse_koteg_napok_tobb_napot_ad_naponkenti_normalizalassal():
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 2, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 3, 9, tzinfo=timezone.utc),   # mai (csonka)
    ])
    df = pd.DataFrame({"a": [30, 40, 99], "időjárás": [50, 50, 50]}, index=idx)
    koteg = {"id": 0, "tagok": [("a", "megelhetes")], "referenciaszo": "időjárás"}
    napi = kulcsszavak.parse_koteg_napok(df, koteg, date(2021, 1, 3), 1.0, 3)
    assert set(napi.keys()) == {"2021-01-01", "2021-01-02"}   # a mai (01-03) kizárva
    assert napi["2021-01-01"][0]["nyers_ertek"] == 30
    assert napi["2021-01-01"][0]["normalizalt_ertek"] == 60.0  # 30 * (100/50)
    assert napi["2021-01-02"][0]["nyers_ertek"] == 40
