import pytest

from trendfigyelo import kliens
from trendfigyelo.config import Config


def _config():
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        alap_keses_mp=3.0, szoras_mp=(3, 7),
        max_probak=4, backoff_mp=[30, 120, 480], trend_idosor_max=15,
        proxy=None, kulcsszavak=[],
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


# --- hívás-plafon (call-multiplying bug elleni védőkorlát) ---
# Szerződés: a check a próba-ciklus LEGELEJÉN, a _var()+inkrementálás ELŐTT, `>= plafon`.
# Kis plafonnal tesztelünk (a 120 = tervezett*max_probak külön, a test_futtato E-tesztje).


def test_plafonon_a_kuszobig_atmegy_a_felette_dob():
    # plafon=3: pontosan 3 próba átmegy, a 4. RuntimeError.
    # Diszkriminátor: `>=` a ciklus elején → 3 átmegy; egy `>`-et használó VAGY
    # plafon nélküli impl a 4.-en nem itt/nem így viselkedne (a plafon nélküli sosem dob).
    k = kliens.Kliens(_config(), trends=object(), plafon=3)
    for _ in range(3):
        assert k.hivas("teszt", lambda: "ok") == "ok"
    with pytest.raises(RuntimeError):
        k.hivas("teszt", lambda: "ok")


def test_a_cap_tuzelese_nem_inflalja_a_szamlalot():
    # plafon=3: a 4. hivas dob, de a számláló 3 marad (nem 4).
    # Diszkriminátor: az inkrementálás UTÁNi check `>`-tel 4-et adna (előbb növel, majd dob);
    # a ciklus-eleji `>=` a _var()+inkrementálás ELŐTT dob → 3 marad, és nincs felesleges alvás.
    k = kliens.Kliens(_config(), trends=object(), plafon=3)
    for _ in range(3):
        k.hivas("teszt", lambda: "ok")
    with pytest.raises(RuntimeError):
        k.hivas("teszt", lambda: "ok")
    assert k.osszes_hivas() == 3


def test_a_plafon_a_probakat_szamolja_nem_a_logikai_hivasokat():
    # Egyetlen logikai hívás, csupa 429-retry → a PRÓBÁK érik el a plafont, a cap tüzel
    # az AgFeladva ELŐTT. Diszkriminátor: egy "logikai hívásokat számoló" impl 1-nél
    # tartana, sosem érné el a plafon=2-t → AgFeladva jönne (max_probak=4), nem RuntimeError.
    k = kliens.Kliens(_config(), trends=object(), plafon=2)

    def mindig_429():
        raise HibaKoddal(429)

    with pytest.raises(RuntimeError):   # NEM AgFeladva
        k.hivas("idosor", mindig_429)
    assert k.osszes_hivas() == 2        # proba0→1, proba1→2, proba2: 2>=2 → dob


def test_plafon_nelkul_soha_nem_dob():
    # Default (nincs plafon) → a meglévő (plafon nélküli) hívók viselkedése változatlan.
    # Diszkriminátor: egy configból AUTO-számoló default (pl. 120) a 121.-en dobna → itt bukna.
    k = kliens.Kliens(_config(), trends=object())
    for _ in range(200):
        k.hivas("teszt", lambda: "ok")
    assert k.osszes_hivas() == 200


def test_a_plafon_hiba_uzenete_kozli_a_kuszobot_es_az_allast():
    # Üzenet-szerződés: "hívás-plafon túllépve a(z) '<ag>' ágon: osszes_hivas=<N> >= plafon=<P>".
    # A loop-top `>=` miatt N==P a raise pillanatában (a számláló sosem lépi túl a plafont),
    # ezért a küszöböt ÉS a tényleges állást KÜLÖN MEZŐKÉNT közöljük — így a naplóból/artefaktból
    # látszik, hol álltunk le. Diszkriminátor: egy csupasz RuntimeError() vagy egy csak-küszöböt
    # közlő üzenet ("plafon: 3") itt bukik, mert hiányzik az 'osszes_hivas=' mező és/vagy az ág.
    k = kliens.Kliens(_config(), trends=object(), plafon=3)
    for _ in range(3):
        k.hivas("teszt", lambda: "ok")
    with pytest.raises(RuntimeError) as info:
        k.hivas("teszt", lambda: "ok")
    uzenet = str(info.value)
    assert "plafon=3" in uzenet          # a küszöb, névvel + értékkel
    assert "osszes_hivas=3" in uzenet    # a tényleges számlálóállás, névvel + értékkel
    assert "teszt" in uzenet             # melyik ágon állt le


def test_a_plafon_az_osszes_hivast_nezi_nem_a_per_ag_szamlalot():
    # A call-multiplying bug bárhol lehet → a plafon az ÖSSZES próbára vonatkozik, nem egy
    # ág saját számlálójára. plafon=3: három KÜLÖN ágon egy-egy hívás (per-ág=1), a negyedik
    # (idosor, per-ág=0) a TOTÁL miatt dob — pedig egyetlen ág sem érte el a 3-at.
    # Diszkriminátor: egy per-ág (_szamlalok[ag]) check itt NEM dobna (mind 0/1).
    k = kliens.Kliens(_config(), trends=object(), plafon=3)
    k.hivas("felkapott_api", lambda: "ok")
    k.hivas("felkapott_rss", lambda: "ok")
    k.hivas("kulcsszo", lambda: "ok")
    assert k.osszes_hivas() == 3
    with pytest.raises(RuntimeError):
        k.hivas("idosor", lambda: "ok")   # totál=3 → dob, bár idosor per-ág=0
