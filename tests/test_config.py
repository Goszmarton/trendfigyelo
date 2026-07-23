import textwrap

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
