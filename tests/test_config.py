import textwrap
from pathlib import Path

import pytest

from trendfigyelo import config
from trendfigyelo.config import KulcsszoTetel


def _ir(tmp_path, szoveg):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent(szoveg), encoding="utf-8")
    return p


JO = """
geo: HU
nyelv: hu
idoablak_orak: 24
idosor_idokeret: "now 1-d"
kerespont:
  alap_keses_mp: 3.0
  szoras_mp: [3, 7]
  max_probak: 4
  backoff_mp: [30, 120, 480]
trend_idosor_max: 15
proxy: null
kulcsszavak:
  - {kifejezes: "infláció", domen: gazdasag, tipus: szintmero}
  - {kifejezes: "benzinár", domen: fogyasztas, tipus: szintmero}
  - {kifejezes: "tüntetés", domen: kozelet, tipus: esemenyjelzo}
"""


def test_betolt_kiolvassa_a_mezoket(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.geo == "HU"
    assert c.szoras_mp == (3, 7)
    assert c.backoff_mp == [30, 120, 480]
    assert c.trend_idosor_max == 15
    assert c.proxy is None


def test_nincs_horgony_mezo():
    # a horgony-mezők elhagyva a sémából
    assert "referenciaszo" not in config.Config.__dataclass_fields__
    assert "referencia_min_atlag" not in config.Config.__dataclass_fields__


def test_osszes_kulcsszo_tetelekkel(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.osszes_kulcsszo() == [
        KulcsszoTetel("infláció", "gazdasag", "szintmero"),
        KulcsszoTetel("benzinár", "fogyasztas", "szintmero"),
        KulcsszoTetel("tüntetés", "kozelet", "esemenyjelzo"),
    ]


def test_hianyzo_kotelezo_mezo_konfighibat_dob(tmp_path):
    rossz = JO.replace("geo: HU", "")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_ures_kulcsszolista_konfighibat_dob(tmp_path):
    rossz = JO.split("kulcsszavak:")[0] + "kulcsszavak: []\n"
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_ervenytelen_tipus_konfighibat_dob(tmp_path):
    rossz = JO.replace("tipus: esemenyjelzo", "tipus: valamimas")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_hianyzo_domen_konfighibat_dob(tmp_path):
    rossz = JO.replace("- {kifejezes: \"infláció\", domen: gazdasag, tipus: szintmero}",
                       "- {kifejezes: \"infláció\", tipus: szintmero}")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_hianyzo_kifejezes_konfighibat_dob(tmp_path):
    rossz = JO.replace("- {kifejezes: \"infláció\", domen: gazdasag, tipus: szintmero}",
                       "- {domen: gazdasag, tipus: szintmero}")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_duplikalt_kifejezes_konfighibat_dob(tmp_path):
    rossz = JO + '  - {kifejezes: "infláció", domen: gazdasag, tipus: szintmero}\n'
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_betolt_kulcsszo_idokeret(tmp_path):
    jo = JO + 'kulcsszo_idokeret: "now 7-d"\n'
    c = config.betolt(_ir(tmp_path, jo))
    assert c.kulcsszo_idokeret == "now 7-d"


def test_kulcsszo_idokeret_alapertelmezes(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.kulcsszo_idokeret == "now 7-d"


def test_eles_config_lassitott_anti_block_utem():
    # A valódi projekt-config.yaml anti-block üteme (2. füst-teszt: azonnali 429 → lassítás)
    gyoker = Path(__file__).resolve().parent.parent
    c = config.betolt(gyoker / "config.yaml")
    assert c.alap_keses_mp == 6.0          # trendspy request_delay
    assert c.szoras_mp == (6.0, 10.0)      # saját véletlen késleltetés


def test_eles_config_13_kulcsszo():
    # a Task 2-ben jóváhagyott 13 szó, per-kulcsszó tipussal
    gyoker = Path(__file__).resolve().parent.parent
    c = config.betolt(gyoker / "config.yaml")
    tetelek = c.osszes_kulcsszo()
    assert len(tetelek) == 13
    assert all(t.tipus in {"szintmero", "esemenyjelzo", "hibrid"} for t in tetelek)
    assert any(t.kifejezes == "tüntetés" and t.tipus == "esemenyjelzo" for t in tetelek)


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


def test_tortenet_visszapotlas_nap_alapertelmezes(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.tortenet_visszapotlas_nap == 3
