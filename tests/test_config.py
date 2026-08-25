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


# --- per-szó rács-mező (Phase 4 Task 1: séma, viselkedés-változás nélkül) ---

JO_RACS = JO.replace(
    '- {kifejezes: "infláció", domen: gazdasag, tipus: szintmero}',
    '- {kifejezes: "infláció", domen: gazdasag, tipus: szintmero, racs: nap}',
).replace(
    '- {kifejezes: "benzinár", domen: fogyasztas, tipus: szintmero}',
    '- {kifejezes: "benzinár", domen: fogyasztas, tipus: szintmero, racs: het}',
)


def test_racs_alapertelmezes_ora(tmp_path):
    # racs nélküli bejegyzés → "ora" (visszafelé kompatibilis default)
    c = config.betolt(_ir(tmp_path, JO))
    assert all(t.racs == "ora" for t in c.osszes_kulcsszo())


def test_racs_beolvas_nap_es_het(tmp_path):
    c = config.betolt(_ir(tmp_path, JO_RACS))
    racsok = {t.kifejezes: t.racs for t in c.osszes_kulcsszo()}
    assert racsok["infláció"] == "nap"
    assert racsok["benzinár"] == "het"
    assert racsok["tüntetés"] == "ora"      # racs nélkül maradt → default


def test_ervenytelen_racs_konfighibat_dob(tmp_path):
    rossz = JO.replace("tipus: szintmero}", "tipus: szintmero, racs: havi}", 1)
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_racs_idokeret_terkep():
    assert config.RACS_IDOKERET == {
        "ora": "now 7-d",
        "nap": "today 3-m",
        "het": "today 12-m",
    }


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


def test_eles_config_racs_besorolas():
    # a MÉRT (2026-08-13) rács-besorolás — regresszió-őr a config-adaton
    gyoker = Path(__file__).resolve().parent.parent
    c = config.betolt(gyoker / "config.yaml")
    racsok = {t.kifejezes: t.racs for t in c.osszes_kulcsszo()}
    assert racsok == {
        "benzin": "ora", "nyugdíj": "ora",
        "eladó lakás": "nap", "albérlet": "nap", "betegség": "nap",
        "napelem": "nap", "hitel": "nap", "nyaralás": "nap",
        "kormányablak": "het", "állás": "het", "kórház": "het",
        "akciós újság": "het", "tüntetés": "het",
    }
    assert all(t.racs in config.RACSOK for t in c.osszes_kulcsszo())


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


# --- KONFIG-VALIDALATLAN: numerikus kulcsok tartomány-őre (≥1 / ≥0 ADD-ON) ---

def test_trend_idosor_max_nulla_konfighibat_dob(tmp_path):
    # trend_idosor_max=0 EDDIG csendesen átment (int) → a RESZBEN-TELT-BLOKK leak config-elérhető.
    # A tartomány-őr ≥1-et követel. RED: ma NEM dob (0 átmegy).
    rossz = JO.replace("trend_idosor_max: 15", "trend_idosor_max: 0")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_trend_idosor_max_negativ_konfighibat_dob(tmp_path):
    rossz = JO.replace("trend_idosor_max: 15", "trend_idosor_max: -3")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_idoablak_orak_nulla_konfighibat_dob(tmp_path):
    rossz = JO.replace("idoablak_orak: 24", "idoablak_orak: 0")
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_trend_megjelenites_max_nulla_konfighibat_dob(tmp_path):
    rossz = JO + "trend_megjelenites_max: 0\n"
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_naplo_max_sor_nulla_konfighibat_dob(tmp_path):
    rossz = JO + "naplo_max_sor: 0\n"
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_trend_idosor_rekesz_max_nulla_engedett(tmp_path):
    # ADD-ON kulcs (≥0): a 0 LEGITIM (nincs rekesz-sparkline) — NEM dob. SZANDEKOS-ZOLD-VAK diszkriminátor:
    # ha a min tévesen 1 lenne, ez a teszt bukna.
    c = config.betolt(_ir(tmp_path, JO + "trend_idosor_rekesz_max: 0\n"))
    assert c.trend_idosor_rekesz_max == 0


def test_trend_idosor_rekesz_max_negativ_konfighibat_dob(tmp_path):
    # a ≥0 nem „nincs ellenőrzés": a negatív TILOS.
    rossz = JO + "trend_idosor_rekesz_max: -1\n"
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_tortenet_visszapotlas_nap_nulla_engedett(tmp_path):
    # ADD-ON kulcs (≥0): a 0 LEGITIM (nincs visszapótlás) — NEM dob.
    c = config.betolt(_ir(tmp_path, JO + "tortenet_visszapotlas_nap: 0\n"))
    assert c.tortenet_visszapotlas_nap == 0


def test_naplo_max_sor_alapertelmezes(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.naplo_max_sor == 2000


def test_tortenet_visszapotlas_nap_alapertelmezes(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.tortenet_visszapotlas_nap == 3


# --- Task 7: modszertan_valtas (töréspont-jelölő) forrás + normalizálás ---

def test_modszertan_valtas_alapertelmezes_none(tmp_path):
    c = config.betolt(_ir(tmp_path, JO))
    assert c.modszertan_valtas is None          # merge előtt nincs töréspont


def test_modszertan_valtas_beolvasva_string(tmp_path):
    jo = JO + 'modszertan_valtas: "2026-08-01"\n'
    c = config.betolt(_ir(tmp_path, jo))
    assert c.modszertan_valtas == "2026-08-01"


def test_modszertan_valtas_idezojel_nelkul_datum_objektum(tmp_path):
    # a PyYAML az idézőjel nélküli dátumot datetime.date-té alakítja → stringgé normalizálva
    jo = JO + "modszertan_valtas: 2026-08-01\n"
    c = config.betolt(_ir(tmp_path, jo))
    assert c.modszertan_valtas == "2026-08-01"   # str, nem datetime.date


def test_modszertan_valtas_kanonikusra_normalizal(tmp_path):
    # alap-formátumú ISO ("20260801") → kanonikus "2026-08-01"
    jo = JO + 'modszertan_valtas: "20260801"\n'
    c = config.betolt(_ir(tmp_path, jo))
    assert c.modszertan_valtas == "2026-08-01"


def test_modszertan_valtas_nem_iso_konfighibat_dob(tmp_path):
    rossz = JO + 'modszertan_valtas: "not-a-date"\n'
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_modszertan_valtas_nem_datum_tipus_konfighibat_dob(tmp_path):
    # minden más bemenet (pl. int) → KonfigHiba
    rossz = JO + "modszertan_valtas: 12345\n"
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


def test_modszertan_valtas_datetime_konfighibat_dob(tmp_path):
    # datetime.datetime a date ALOSZTÁLYA — az idő-komponensű alakot (elgépelt
    # dátum) elutasítjuk, nem csonkoljuk .date()-re.
    rossz = JO + "modszertan_valtas: 2026-08-01 12:00:00\n"
    with pytest.raises(config.KonfigHiba):
        config.betolt(_ir(tmp_path, rossz))


# --- YouTube-fül (Phase 4, 2026-08-25): youtube: szekció, opcionális (hiány → []) ---

def test_youtube_szekcio_12_szo_es_racs():
    c = config.betolt("config.yaml")
    yt = c.osszes_youtube_kulcsszo()
    kifejezesek = [t.kifejezes for t in yt]
    assert len(yt) == 12
    assert kifejezesek == [
        "szorongás", "edzés", "meditáció", "befektetés", "bitcoin", "hírek",
        "magyar péter", "recept", "mese", "nyaralás", "tanulás", "klíma",
    ]
    racs = {t.kifejezes: t.racs for t in yt}
    assert racs["edzés"] == "nap" and racs["meditáció"] == "nap" and racs["recept"] == "nap"
    assert racs["mese"] == "nap" and racs["magyar péter"] == "nap"
    assert racs["szorongás"] == "het" and racs["bitcoin"] == "het" and racs["klíma"] == "het"
    # a Google-kulcsszavak ÉRINTETLENEK
    assert len(c.osszes_kulcsszo()) == 13


def test_youtube_szekcio_hianyzik_ures_lista():
    # ha nincs youtube: szekció, a betöltés NEM bukik, üres listát ad
    import yaml
    nyers = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    nyers.pop("youtube", None)
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        yaml.safe_dump(nyers, f, allow_unicode=True)
        utvonal = f.name
    try:
        c = config.betolt(utvonal)
        assert c.osszes_youtube_kulcsszo() == []
    finally:
        os.unlink(utvonal)
