"""Task 3 — a nyers órás kimenet szerződés-validátorának tesztjei.

RED-diszkriminátor: a validátornak EL KELL utasítania az ablakhatár nélküli
és a véglegesség-jelölés (`reszleges`) nélküli rekordot — egy „mindig []-t adó"
csonk-validátor ezen a két negatív teszten megbukik.
"""

from trendfigyelo.nyers_kimenet import ervenyes_nyers_rekord


def test_hianyzo_ablakhatar_elutasitva():
    rek = {"kulcsszo": "hitel", "ablak_veg_utc": "2026-07-27T21:00:00+00:00",
           "pontok": [{"idopont_utc": "2026-07-27T20:00:00+00:00", "ertek": 5, "reszleges": False}]}
    hibak = ervenyes_nyers_rekord(rek)
    assert any("ablak_kezdet_utc" in h for h in hibak)  # csonk-validátor ([]) itt bukik


def test_veglegesseg_jeloles_nelkul_elutasitva():
    rek = {"kulcsszo": "hitel", "ablak_kezdet_utc": "2026-07-20T21:00:00+00:00",
           "ablak_veg_utc": "2026-07-27T21:00:00+00:00",
           "pontok": [{"idopont_utc": "2026-07-27T20:00:00+00:00", "ertek": 5}]}  # nincs 'reszleges'
    hibak = ervenyes_nyers_rekord(rek)
    assert any("reszleges" in h for h in hibak)


def test_ervenyes_rekord_atmegy():
    rek = {"kulcsszo": "hitel", "ablak_kezdet_utc": "2026-07-20T21:00:00+00:00",
           "ablak_veg_utc": "2026-07-27T21:00:00+00:00",
           "pontok": [{"idopont_utc": "2026-07-27T20:00:00+00:00", "ertek": 5, "reszleges": True}]}
    assert ervenyes_nyers_rekord(rek) == []


def test_kevert_idozona_ablakhatar_nem_szall_el():
    # tz-aware kezdet + tz-naiv vég: a guard NEM szállhat el TypeError-ral,
    # hanem NÉV SZERINT jelentse a hibát (review-finding, Important).
    rek = {"kulcsszo": "hitel",
           "ablak_kezdet_utc": "2026-07-20T21:00:00+00:00",
           "ablak_veg_utc": "2026-07-27T21:00:00",  # nincs offset → naiv
           "pontok": [{"idopont_utc": "2026-07-27T20:00:00+00:00", "ertek": 5, "reszleges": True}]}
    hibak = ervenyes_nyers_rekord(rek)  # nem szabad kivételt dobnia
    assert any("időzón" in h for h in hibak)
