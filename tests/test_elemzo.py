from trendfigyelo import elemzo


def _regresszio_egy_szo(irany, meredekseg, ervenyes, mai):
    return {
        "kulcsszavak": {
            "állás": {
                "domen": "munkaeropiac", "tipus": "szintmero", "racs": "ora",
                "intervallumok": {
                    "1_het": {
                        "ervenyes": ervenyes, "irany": irany,
                        "meredekseg_nap": meredekseg, "mai_ertek": mai,
                        "ablak_veg_utc": "2026-08-22T18:00:00+00:00",
                    }
                },
            }
        }
    }


def test_kulcsszo_szamok_a_regresszio_1_het_intervallumbol():
    adatok = {
        "regresszio": _regresszio_egy_szo("emelkedik", 1.23, True, 42.0),
        "tortenet": {"napok": [{"nap": "2026-08-22",
                                "kulcsszavak": [{"kulcsszo": "állás", "atlag": 25.0, "csucs": 100.0}]}]},
        "legfrissebb": {"top_trendek": []},
        "napok_trendek": {},
    }
    payload = elemzo.epit_payload(adatok)
    szamok = payload["kulcsszavak"]["szamok"]
    assert len(szamok) == 1
    szo = szamok[0]
    assert szo["szo"] == "állás"
    assert szo["irany"] == "emelkedik"
    assert szo["meredekseg"] == 1.23
    assert szo["ervenyes"] is True
    assert szo["mai_ertek"] == 42.0
    assert szo["csucs"] == 100.0
    assert szo["atlag"] == 25.0


def test_felkapott_top_es_gordulo_het():
    adatok = {
        "regresszio": {"kulcsszavak": {}},
        "tortenet": {"napok": []},
        "legfrissebb": {"top_trendek": [
            {"kifejezes": "viharos szél", "volumen": "50000", "novekedes_pct": "1000", "temak": ["Other"]},
        ]},
        "napok_trendek": {
            "2026-08-21": [{"kifejezes": "eső", "volumen": "20000", "temak": ["Weather"]},
                           {"kifejezes": "viharos szél", "volumen": "10000", "temak": ["Weather"]}],
            "2026-08-22": [{"kifejezes": "viharos szél", "volumen": "50000", "temak": ["Other"]}],
        },
    }
    payload = elemzo.epit_payload(adatok)
    felk = payload["felkapott"]
    assert felk["top"][0]["kifejezes"] == "viharos szél"
    assert felk["top"][0]["volumen"] == "50000"
    # gördülő hét: hányszor bukkant fel egy kifejezés az elmúlt napokban
    het = {e["kifejezes"]: e["napok_szama"] for e in felk["het"]["visszateroek"]}
    assert het["viharos szél"] == 2      # 08-21 és 08-22
    assert het["eső"] == 1


def test_gordulo_het_napon_beluli_dedup():
    # Ha egy kifejezés EGY napon belül kétszer szerepel, az akkor is CSAK
    # egy nap (a "hány külön napon" szerződés — nem bejegyzés-számláló).
    adatok = {
        "regresszio": {"kulcsszavak": {}},
        "tortenet": {"napok": []},
        "legfrissebb": {"top_trendek": []},
        "napok_trendek": {
            "2026-08-22": [{"kifejezes": "eső", "volumen": "20000", "temak": ["Weather"]},
                           {"kifejezes": "eső", "volumen": "10000", "temak": ["Weather"]}],
        },
    }
    payload = elemzo.epit_payload(adatok)
    het = {e["kifejezes"]: e["napok_szama"] for e in payload["felkapott"]["het"]["visszateroek"]}
    assert het["eső"] == 1               # egy napon belüli duplikátum → 1 nap


def test_gordulo_het_none_napok_trendek_guard():
    # Explicit None napok_trendek esetén ne AttributeError-özzön, adjon üres eredményt.
    adatok = {
        "regresszio": {"kulcsszavak": {}},
        "tortenet": {"napok": []},
        "legfrissebb": {"top_trendek": []},
        "napok_trendek": None,
    }
    payload = elemzo.epit_payload(adatok)
    het = payload["felkapott"]["het"]
    assert het["napok"] == 0
    assert het["visszateroek"] == []


def test_nap_diff_iranyvaltas_es_felkapott_valtozas():
    mai = [{"szo": "állás", "irany": "emelkedik", "meredekseg": 2.0},
           {"szo": "benzin", "irany": "stagnal", "meredekseg": 0.0}]
    tegnapi = [{"szo": "állás", "irany": "csokken", "meredekseg": -1.0},
               {"szo": "benzin", "irany": "stagnal", "meredekseg": 0.1}]
    mai_top = [{"kifejezes": "eső"}, {"kifejezes": "viharos szél"}]
    tegnapi_top = [{"kifejezes": "eső"}, {"kifejezes": "hőség"}]
    diff = elemzo.nap_diff(mai, tegnapi, mai_top, tegnapi_top)
    assert diff["van_elozo"] is True
    assert {"szo": "állás", "elozo": "csokken", "mai": "emelkedik"} in diff["irany_valtok"]
    assert all(v["szo"] != "benzin" for v in diff["irany_valtok"])   # benzin nem váltott irányt
    assert "viharos szél" in diff["felkapott_uj"]
    assert "hőség" in diff["felkapott_eltunt"]


def test_nap_diff_elso_futas_nincs_elozo():
    diff = elemzo.nap_diff([{"szo": "állás", "irany": "emelkedik", "meredekseg": 1.0}], None,
                           [{"kifejezes": "eső"}], None)
    assert diff["van_elozo"] is False
    assert diff["irany_valtok"] == []
    assert diff["felkapott_uj"] == []
    assert diff["felkapott_eltunt"] == []


def test_epit_payload_beepiti_a_valtozast_ha_van_tegnapi():
    adatok = {
        "regresszio": _regresszio_egy_szo("emelkedik", 1.0, True, 10.0),
        "tortenet": {"napok": []},
        "legfrissebb": {"top_trendek": [{"kifejezes": "eső"}]},
        "napok_trendek": {},
    }
    tegnapi_szamok = [{"szo": "állás", "irany": "csokken", "meredekseg": -1.0}]
    tegnapi_top = [{"kifejezes": "hőség"}]
    payload = elemzo.epit_payload(adatok, tegnapi_szamok=tegnapi_szamok, tegnapi_top=tegnapi_top)
    assert payload["valtozas"]["van_elozo"] is True
    assert payload["valtozas"]["irany_valtok"][0]["szo"] == "állás"
    assert "eső" in payload["valtozas"]["felkapott_uj"]


def test_nap_diff_mozgok_rendezes_es_delta():
    # A mozgok listát az abszolút meredekség-változás szerint CSÖKKENŐEN rendezi,
    # és a valtozas mező a helyes delta (mai − tegnapi, kerekítve).
    mai = [{"szo": "állás", "irany": "emelkedik", "meredekseg": 3.0},
           {"szo": "benzin", "irany": "emelkedik", "meredekseg": 0.5}]
    tegnapi = [{"szo": "állás", "irany": "emelkedik", "meredekseg": 1.0},
               {"szo": "benzin", "irany": "emelkedik", "meredekseg": 0.4}]
    diff = elemzo.nap_diff(mai, tegnapi, [], [])
    assert diff["mozgok"][0]["szo"] == "állás"       # nagyobb abszolút változás elöl
    assert diff["mozgok"][0]["valtozas"] == 2.0      # 3.0 − 1.0
    assert diff["mozgok"][1]["szo"] == "benzin"
    assert diff["mozgok"][1]["valtozas"] == 0.1      # 0.5 − 0.4, kerekítve


def test_nap_diff_mai_only_szo_kihagyva():
    # Ha egy szó a maiban van, de a tegnapiban NINCS → kihagyva (nem dob, nem kerül be).
    mai = [{"szo": "állás", "irany": "emelkedik", "meredekseg": 2.0},
           {"szo": "új_szo", "irany": "emelkedik", "meredekseg": 5.0}]
    tegnapi = [{"szo": "állás", "irany": "csokken", "meredekseg": 1.0}]
    diff = elemzo.nap_diff(mai, tegnapi, [], [])
    assert all(v["szo"] != "új_szo" for v in diff["irany_valtok"])
    assert all(m["szo"] != "új_szo" for m in diff["mozgok"])


def test_nap_diff_nem_szam_meredekseg_kihagyva():
    # Ha egy szó meredeksége None (vagy hiányzik) → ne dobjon, ne kerüljön mozgok-ba.
    mai = [{"szo": "állás", "irany": "emelkedik", "meredekseg": None}]
    tegnapi = [{"szo": "állás", "irany": "emelkedik", "meredekseg": 1.0}]
    diff = elemzo.nap_diff(mai, tegnapi, [], [])
    assert all(m["szo"] != "állás" for m in diff["mozgok"])
