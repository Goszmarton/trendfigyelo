from datetime import date, datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from trendfigyelo import kulcsszavak
from trendfigyelo.config import Config, KulcsszoTetel
from trendfigyelo.kliens import AgFeladva
from trendfigyelo.nyers_kimenet import ervenyes_nyers_rekord

FIX_MOST = datetime(2021, 1, 3, 12, tzinfo=timezone.utc)  # mai budapesti nap = 2021-01-03


def _config():
    """3 szó: állás, hitel, tüntetés (a hívási sorrend ellenőrzéséhez)."""
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        alap_keses_mp=3.0, szoras_mp=(3, 7), max_probak=4, backoff_mp=[30, 120, 480],
        trend_idosor_max=15, proxy=None,
        kulcsszavak=[
            KulcsszoTetel("állás", "munkaeropiac", "szintmero"),
            KulcsszoTetel("hitel", "haztartasi_penzugy", "szintmero"),
            KulcsszoTetel("tüntetés", "kozelet", "esemenyjelzo"),
        ],
    )


def egy_szo_df(kif):
    """Egy-oszlopos órás DataFrame egy kulcsszóra + isPartial oszlop (a farok részleges)."""
    idx = pd.to_datetime([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),  # teljes nap
        datetime(2021, 1, 2, 10, tzinfo=timezone.utc),  # teljes nap
        datetime(2021, 1, 3, 9, tzinfo=timezone.utc),   # mai (részleges)
    ])
    return pd.DataFrame({kif: [30, 40, 99], "isPartial": [False, False, True]}, index=idx)


class KemKliens:
    """Rögzíti a hívásonként átadott 'szavak' listát; szavankénti df-et ad."""
    def __init__(self, df_gyar):
        self.df_gyar = df_gyar
        self.hivott_szavak = []
        self.tr = type("T", (), {"interest_over_time": None})()

    def hivas(self, ag, fn, szavak, **kw):
        self.hivott_szavak.append(list(szavak))
        return self.df_gyar(szavak[0])

    def hivasszam(self, ag):
        return len(self.hivott_szavak)

    def osszes_hivas(self):
        return len(self.hivott_szavak)


def test_szolo_lekerdezes_szavankent_egy_hivas():
    # A LÉNYEGI RED: szavankénti EGY hívás, egy-elemű listával, horgony NÉLKÜL.
    kem = KemKliens(df_gyar=egy_szo_df)
    kulcsszavak.gyujt(kem, _config(), most=FIX_MOST)
    assert kem.hivott_szavak == [["állás"], ["hitel"], ["tüntetés"]]  # 3 hívás, 1-1 szó
    assert all("időjárás" not in sz for sz in kem.hivott_szavak)      # nincs horgony


def test_nincs_normalizalt_mezo_a_pontokban():
    pontok, _, _ = kulcsszavak.gyujt(KemKliens(df_gyar=egy_szo_df), _config(), most=FIX_MOST)
    assert pontok and all("normalizalt_ertek" not in p and "referenciaszo" not in p for p in pontok)
    assert all(p["domen"] and p["tipus"] for p in pontok)


def test_nyers_sorozatok_atmegy_a_szerzodesen():
    _, _, nyers = kulcsszavak.gyujt(KemKliens(df_gyar=egy_szo_df), _config(), most=FIX_MOST)
    assert set(nyers.keys()) == {"állás", "hitel", "tüntetés"}
    # a Task 3-as validátor: minden nyers rekord érvényes (ablakhatárok + reszleges)
    assert all(ervenyes_nyers_rekord(r) == [] for r in nyers.values())
    assert nyers["állás"]["pontok"][-1]["reszleges"] is True   # a farok részleges


def _config_egy():
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        alap_keses_mp=3.0, szoras_mp=(3, 7), max_probak=4, backoff_mp=[30, 120, 480],
        trend_idosor_max=15, proxy=None,
        kulcsszavak=[KulcsszoTetel("állás", "munkaeropiac", "szintmero")],
    )


def test_gyujt_nan_ures_ertek_nem_dobal():
    # A Task 3 szerződés megengedi az ertek: "" alakot; a NaN/hiányzó érték várt eset.
    def nan_df(kif):
        idx = pd.to_datetime([
            datetime(2021, 1, 2, 10, tzinfo=timezone.utc),   # utolsó teljes nap, NaN érték
            datetime(2021, 1, 3, 9, tzinfo=timezone.utc),    # mai (részleges)
        ])
        return pd.DataFrame({kif: [float("nan"), 40], "isPartial": [False, True]}, index=idx)
    pontok, _, nyers = kulcsszavak.gyujt(KemKliens(df_gyar=nan_df), _config_egy(), most=FIX_MOST)
    p = next(p for p in pontok if p["idopont_utc"][:10] == "2021-01-02")
    assert p["nyers_ertek"] == ""                       # NaN → "" (nem int()-eli el)
    assert nyers["állás"]["pontok"][0]["ertek"] == ""   # a nyers sorozatban is ""


def test_gyujt_3_tuple_egynapos_es_napi_pontok():
    pontok, napi, nyers = kulcsszavak.gyujt(KemKliens(df_gyar=egy_szo_df), _config(), most=FIX_MOST)
    assert {p["idopont_utc"][:10] for p in pontok} == {"2021-01-02"}   # egynapos: utolsó teljes
    assert set(napi.keys()) == {"2021-01-01", "2021-01-02"}            # napi: utolsó 2 teljes
    assert set(nyers.keys()) == {"állás", "hitel", "tüntetés"}


class _FeladoKliens:
    def __init__(self):
        self.hivasszamlalo = 0
        self.tr = type("T", (), {"interest_over_time": None})()

    def hivas(self, ag, fn, szavak, **kw):
        self.hivasszamlalo += 1
        raise AgFeladva("kulcsszo", ["429", "429", "429", "429"])

    def hivasszam(self, ag):
        return self.hivasszamlalo

    def osszes_hivas(self):
        return self.hivasszamlalo


def test_gyujt_agfeladva_feladja_az_egesz_agat():
    k = _FeladoKliens()
    with pytest.raises(AgFeladva):
        kulcsszavak.gyujt(k, _config(), most=FIX_MOST)
    assert k.hivasszamlalo == 1   # az első szó után feladja, a többit meg sem hívja


class _EgySzoBukoKliens:
    """Az 'állás' RuntimeError-t dob (kihagyva), a többi df-et ad."""
    def __init__(self):
        self.hivott = []
        self.tr = type("T", (), {"interest_over_time": None})()

    def hivas(self, ag, fn, szavak, **kw):
        self.hivott.append(szavak[0])
        if szavak[0] == "állás":
            raise RuntimeError("hálózat")
        return egy_szo_df(szavak[0])

    def hivasszam(self, ag):
        return len(self.hivott)

    def osszes_hivas(self):
        return len(self.hivott)


def test_gyujt_egyeb_hiba_csak_azt_a_szot_hagyja_ki():
    k = _EgySzoBukoKliens()
    pontok, _, nyers = kulcsszavak.gyujt(k, _config(), most=FIX_MOST)
    assert k.hivott == ["állás", "hitel", "tüntetés"]        # mindet meghívja
    assert "állás" not in {p["kulcsszo"] for p in pontok}    # a bukott szó kimaradt
    assert "állás" not in nyers


def test_csv_ir_fejlec(tmp_path):
    pontok = [{"kulcsszo": "állás", "domen": "munkaeropiac", "tipus": "szintmero",
               "idopont_utc": "2021-01-01T10:00:00+00:00", "nyers_ertek": 30}]
    p = kulcsszavak.csv_ir(tmp_path, "2021-01-01_1200", "2021-01-01T12:00:00+00:00", "HU", pontok)
    fejlec = p.read_text(encoding="utf-8-sig").splitlines()[0]
    assert fejlec == "kulcsszo;domen;tipus;idopont_utc;nyers_ertek;letoltve_utc;geo"
    assert p.name == "kulcsszo_idosor_HU_2021-01-01_1200.csv"


# --- nap-szűrő segédfüggvények (horgony-független, megtartva) ---

def _napok_df(datetimes, ertekek):
    return pd.DataFrame({"a": ertekek}, index=pd.to_datetime(datetimes))


def test_utolso_teljes_nap_kizarja_a_mait():
    df = _napok_df([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 2, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 2, 12, tzinfo=timezone.utc),
    ], [30, 40, 50])
    assert kulcsszavak.utolso_teljes_nap(df, date(2021, 1, 2)) == date(2021, 1, 1)


def test_utolso_teljes_nap_nincs_korabbi():
    df = _napok_df([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 1, 12, tzinfo=timezone.utc),
    ], [30, 40])
    assert kulcsszavak.utolso_teljes_nap(df, date(2021, 1, 1)) is None


def test_utolso_N_teljes_nap_utolso_harmat_adja():
    idx = [datetime(2021, 1, d, 10, tzinfo=timezone.utc) for d in (1, 2, 3, 4)]
    idx.append(datetime(2021, 1, 5, 9, tzinfo=timezone.utc))  # mai (csonka)
    df = _napok_df(idx, [10, 20, 30, 40, 50])
    assert kulcsszavak.utolso_N_teljes_nap(df, date(2021, 1, 5), 3) == [
        date(2021, 1, 2), date(2021, 1, 3), date(2021, 1, 4),
    ]


def test_utolso_N_teljes_nap_kevesebb_mint_n():
    df = _napok_df([
        datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
        datetime(2021, 1, 2, 9, tzinfo=timezone.utc),   # mai (csonka)
    ], [10, 20])
    assert kulcsszavak.utolso_N_teljes_nap(df, date(2021, 1, 2), 3) == [date(2021, 1, 1)]


# --- review-fixek: M1 (rendezetlen index), M2 (NaN isPartial) ---

def test_nyers_sorozat_rendezetlen_index_helyes_ablakhatar():
    # M1: az ablakhatár df.index.min()/max()-ból, nem pozicionális [0]/[-1]-ből;
    # rendezetlen indexnél a pozicionális kezdet > veg lenne → validátor-bukás.
    def fordit_df(kif):
        idx = pd.to_datetime([
            datetime(2021, 1, 3, 9, tzinfo=timezone.utc),   # később (index eleje)
            datetime(2021, 1, 1, 10, tzinfo=timezone.utc),  # korábbi (index vége)
        ])
        return pd.DataFrame({kif: [40, 30], "isPartial": [True, False]}, index=idx)
    _, _, nyers = kulcsszavak.gyujt(KemKliens(df_gyar=fordit_df), _config_egy(), most=FIX_MOST)
    r = nyers["állás"]
    assert r["ablak_kezdet_utc"] < r["ablak_veg_utc"]
    assert ervenyes_nyers_rekord(r) == []


def test_nyers_sorozat_nan_ispartial_nem_reszleges():
    # M2: NaN isPartial cellát ne olvasson részlegesnek (bool(NaN) True lenne).
    def nan_ip_df(kif):
        idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc)])
        return pd.DataFrame({kif: [30], "isPartial": [float("nan")]}, index=idx)
    _, _, nyers = kulcsszavak.gyujt(KemKliens(df_gyar=nan_ip_df), _config_egy(), most=FIX_MOST)
    assert nyers["állás"]["pontok"][0]["reszleges"] is False


# ── SUCCESS-VAK: a néma üres-skip hangos a VÁRATLAN (nem-esemenyjelzo) esetben ────
def _ures_ket_skiput(kif, mi):
    """Teszt-df: 'mi'='ures' → üres df (Google semmit); 'mi'='nincs_oszlop' → csak isPartial (nincs érték-oszlop)."""
    if mi == "ures":
        return pd.DataFrame()
    idx = pd.to_datetime([datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
                          datetime(2021, 1, 2, 10, tzinfo=timezone.utc)])
    return pd.DataFrame({"isPartial": [False, True]}, index=idx)


def test_ures_df_szintmero_FIGYELEM(capsys):
    # SUCCESS-VAK: szintmero szó ÜRES df-je (Google semmit) = VÁRATLAN → FIGYELEM, NEM néma
    gyar = lambda kif: _ures_ket_skiput(kif, "ures") if kif == "állás" else egy_szo_df(kif)
    kulcsszavak.gyujt(KemKliens(df_gyar=gyar), _config(), most=FIX_MOST)
    ki = capsys.readouterr().out
    assert "állás" in ki and "üres" in ki.lower()   # a váratlan üres df HANGOS


def test_hianyzo_oszlop_szintmero_FIGYELEM(capsys):
    # SUCCESS-VAK: szintmero szó df-jében NINCS érték-oszlop (query/parse-gyanú) = MÁSIK skip-út → FIGYELEM
    gyar = lambda kif: _ures_ket_skiput(kif, "nincs_oszlop") if kif == "hitel" else egy_szo_df(kif)
    kulcsszavak.gyujt(KemKliens(df_gyar=gyar), _config(), most=FIX_MOST)
    ki = capsys.readouterr().out
    assert "hitel" in ki and "oszlop" in ki.lower()   # a hiányzó oszlop KÜLÖN hibaosztály


def test_ures_esemenyjelzo_NEM_pirosit(capsys):
    # SZÁNDÉKOS-ZÖLD (előre): esemenyjelzo (tüntetés) üres = VÁRT (sparse-by-design, spec 6.2) → TELJESEN NÉMA
    gyar = lambda kif: _ures_ket_skiput(kif, "ures") if kif == "tüntetés" else egy_szo_df(kif)
    kulcsszavak.gyujt(KemKliens(df_gyar=gyar), _config(), most=FIX_MOST)
    ki = capsys.readouterr().out
    assert "tüntetés" not in ki   # NINCS FIGYELEM az esemenyjelzo üresre


# ── gyujt_egy_masodlagos: gprop + ag paraméter (YouTube-fül, Task 2) ─────────────
class _RogzitoKliens:
    """A hivas() argumentumait rögzíti; egy fabrikált df-et ad vissza."""
    def __init__(self, df):
        self._df = df
        self.hivasok = []
        self.tr = SimpleNamespace(interest_over_time="IOT_SENTINEL")
    def hivas(self, ag, fn, *args, **kwargs):
        self.hivasok.append({"ag": ag, "fn": fn, "args": args, "kwargs": kwargs})
        return self._df

def _napi_df():
    import pandas as pd
    from datetime import datetime, timezone, timedelta
    kezd = datetime(2026, 5, 20, tzinfo=timezone.utc)
    idx = [kezd + timedelta(days=i) for i in range(92)]
    return pd.DataFrame({"edzés": [40]*92, "isPartial": [False]*91 + [True]}, index=idx)

def test_gyujt_egy_masodlagos_gprop_es_ag_tovabbitas():
    cfg = SimpleNamespace(geo="HU")
    tetel = SimpleNamespace(kifejezes="edzés", domen="egeszseg", tipus="szintmero", racs="nap")
    most = __import__("datetime").datetime(2026, 8, 20, 9, tzinfo=__import__("datetime").timezone.utc)
    k = _RogzitoKliens(_napi_df())
    rek = kulcsszavak.gyujt_egy_masodlagos(k, cfg, tetel, most, "today 3-m",
                                           gprop="youtube", ag="youtube")
    assert rek is not None and rek["timeframe"] == "today 3-m"
    hiv = k.hivasok[0]
    assert hiv["ag"] == "youtube"
    assert hiv["kwargs"]["gprop"] == "youtube"
    assert hiv["kwargs"]["geo"] == "HU" and hiv["kwargs"]["timeframe"] == "today 3-m"

def test_gyujt_egy_masodlagos_alap_gprop_ures_es_ag_valtozatlan():
    # REGRESSZIÓ-ŐR: alapból a Google-viselkedés — ag="kulcsszo_masodlagos", gprop=""
    cfg = SimpleNamespace(geo="HU")
    tetel = SimpleNamespace(kifejezes="edzés", domen="egeszseg", tipus="szintmero", racs="nap")
    most = __import__("datetime").datetime(2026, 8, 20, 9, tzinfo=__import__("datetime").timezone.utc)
    k = _RogzitoKliens(_napi_df())
    kulcsszavak.gyujt_egy_masodlagos(k, cfg, tetel, most, "today 3-m")
    hiv = k.hivasok[0]
    assert hiv["ag"] == "kulcsszo_masodlagos"
    assert hiv["kwargs"]["gprop"] == ""
