import pytest

from trendfigyelo import kliens
from trendfigyelo.config import Config


def _config():
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        referenciaszo="időjárás", alap_keses_mp=3.0, szoras_mp=(3, 7),
        max_probak=4, backoff_mp=[30, 120, 480], trend_idosor_max=15,
        proxy=None, kulcsszavak={"g": ["x"]},
    )


class HibaKoddal(Exception):
    def __init__(self, kod):
        super().__init__(f"HTTP {kod}")
        self.status_code = kod


@pytest.fixture(autouse=True)
def ne_aludj(monkeypatch):
    monkeypatch.setattr(kliens.time, "sleep", lambda *_: None)
    monkeypatch.setattr(kliens.random, "uniform", lambda a, b: a)


def test_rate_limit_hiba_felismeri_a_429et():
    assert kliens.rate_limit_hiba(HibaKoddal(429)) is True
    assert kliens.rate_limit_hiba(Exception("valami 429 Too Many Requests")) is True
    assert kliens.rate_limit_hiba(Exception("hálózati hiba")) is False


def test_sikeres_hivas_szamol_es_visszaad():
    k = kliens.Kliens(_config(), trends=object())
    eredmeny = k.hivas("teszt", lambda x: x * 2, 21)
    assert eredmeny == 42
    assert k.hivasszam("teszt") == 1
    assert k.osszes_hivas() == 1


def test_429_utan_feladja_az_agat_es_minden_probat_szamol():
    k = kliens.Kliens(_config(), trends=object())

    def mindig_429():
        raise HibaKoddal(429)

    with pytest.raises(kliens.AgFeladva) as info:
        k.hivas("idosor", mindig_429)
    assert info.value.ag == "idosor"
    assert k.hivasszam("idosor") == 4  # max_probak próbálkozás


def test_trends_a_configbol_kapja_a_request_delayt():
    rogzitett = {}

    def spy_gyar(**kwargs):
        rogzitett.update(kwargs)
        return object()

    cfg = _config()  # alap_keses_mp=3.0 a fixtúrában
    kliens.Kliens(cfg, trends_gyar=spy_gyar)
    assert rogzitett["request_delay"] == cfg.alap_keses_mp
    assert rogzitett["language"] == cfg.nyelv
    assert rogzitett["proxy"] == cfg.proxy


def test_nem_429_kivetel_tovabbdobva_retry_nelkul():
    k = kliens.Kliens(_config(), trends=object())

    def halozati():
        raise RuntimeError("hálózati hiba")

    with pytest.raises(RuntimeError):
        k.hivas("api", halozati)
    assert k.hivasszam("api") == 1  # nincs újrapróba nem-429-re
