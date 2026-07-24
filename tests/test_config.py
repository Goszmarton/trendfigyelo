import textwrap
from pathlib import Path

import pytest

from trendfigyelo import config


def _ir(tmp_path, szoveg):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent(szoveg), encoding="utf-8")
    return p


JO = """
geo: HU
nyelv: hu
idoablak_orak: 24
idosor_idokeret: "now 1-d"
referenciaszo: "időjárás"
kerespont:
  alap_keses_mp: 3.0
  szoras_mp: [3, 7]
  max_probak: 4
  backoff_mp: [30, 120, 480]
trend_idosor_max: 15
proxy: null
kulcsszavak:
  megelhetes: [infláció, benzinár]
  gazdaság: [forint árfolyam]
"""


def test_betolt_kiolvassa_a_mezoket(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.geo == "HU"
    assert c.referenciaszo == "időjárás"
    assert c.szoras_mp == (3, 7)
    assert c.backoff_mp == [30, 120, 480]
    assert c.trend_idosor_max == 15
    assert c.proxy is None


def test_osszes_kulcsszo_csoporttal(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.osszes_kulcsszo() == [
        ("infláció", "megelhetes"),
        ("benzinár", "megelhetes"),
        ("forint árfolyam", "gazdaság"),
    ]


def test_hianyzo_kotelezo_mezo_konfighibat_dob(tmp_path):
    rossz = JO.replace("geo: HU", "")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_ures_kulcsszolista_konfighibat_dob(tmp_path):
    rossz = JO.split("kulcsszavak:")[0] + "kulcsszavak: {}\n"
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_reszben_ures_csoport_konfighibat_dob(tmp_path):
    rossz = JO.split("kulcsszavak:")[0] + "kulcsszavak:\n  megelhetes: []\n  gazdaság: [forint árfolyam]\n"
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_betolt_kulcsszo_idokeret_es_referencia_kuszob(tmp_path):
    jo = JO + 'kulcsszo_idokeret: "now 7-d"\nreferencia_min_atlag: 1.0\n'
    c = config.betolt(_ir(tmp_path, jo))
    assert c.kulcsszo_idokeret == "now 7-d"
    assert c.referencia_min_atlag == 1.0


def test_referencia_min_atlag_alapertelmezes(tmp_path):
    # ha a config.yaml nem adja meg, az alap 1.0
    c = config.betolt(_ir(tmp_path, JO + 'kulcsszo_idokeret: "now 7-d"\n'))
    assert c.referencia_min_atlag == 1.0


def test_eles_config_lassitott_anti_block_utem():
    # A valódi projekt-config.yaml anti-block üteme (2. füst-teszt: azonnali 429 → lassítás)
    gyoker = Path(__file__).resolve().parent.parent
    c = config.betolt(gyoker / "config.yaml")
    assert c.alap_keses_mp == 6.0          # trendspy request_delay
    assert c.szoras_mp == (6.0, 10.0)      # saját véletlen késleltetés


def test_szoras_mp_skalar_konfighibat_dob(tmp_path):
    rossz = JO.replace("szoras_mp: [3, 7]", "szoras_mp: 5")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_szoras_mp_egy_elem_konfighibat_dob(tmp_path):
    rossz = JO.replace("szoras_mp: [3, 7]", "szoras_mp: [5]")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_szoras_mp_forditott_hatarok_konfighibat_dob(tmp_path):
    rossz = JO.replace("szoras_mp: [3, 7]", "szoras_mp: [7, 3]")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_backoff_ures_lista_konfighibat_dob(tmp_path):
    rossz = JO.replace("backoff_mp: [30, 120, 480]", "backoff_mp: []")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_max_probak_nulla_konfighibat_dob(tmp_path):
    rossz = JO.replace("max_probak: 4", "max_probak: 0")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_naplo_max_sor_alapertelmezes(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.naplo_max_sor == 2000
