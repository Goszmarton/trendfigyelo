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
