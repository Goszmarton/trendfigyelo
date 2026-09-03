from datetime import datetime, timezone

from trendfigyelo import varhato_gyujtes
from trendfigyelo.config import Config, KulcsszoTetel


def _config(kulcsszavak):
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        alap_keses_mp=3.0, szoras_mp=(3, 7), max_probak=4, backoff_mp=[30, 120, 480],
        trend_idosor_max=2, proxy=None, kulcsszavak=kulcsszavak,
    )


# egy esti (21:00 Budapest = 19:00 UTC) becslés → a következő reggeli nap MÁSNAP
MOST = datetime(2026, 9, 3, 19, 0, tzinfo=timezone.utc)


def _reggeli(kif, racs="het"):
    # nem-órás reggeli szó: racs != "ora", futas == "reggel"
    return KulcsszoTetel(kif, "gazdasag", "szintmero", racs, False, "reggel")


def _rekord(lekerdezes_utc):
    return {"timeframe": "today 12-m", "lekerdezes_utc": lekerdezes_utc,
            "ablak_kezdet_utc": "2026-08-01T00:00:00+00:00",
            "ablak_veg_utc": "2026-09-01T00:00:00+00:00", "pontok": []}


def test_soha_nem_gyult_reggeli_szo_masnapi_datumot_kap():
    cfg = _config([_reggeli("infláció")])
    ki = varhato_gyujtes.varhato_gyujtes_datumok(cfg, {}, MOST)
    assert ki == {"infláció": "2026-09-04"}   # 2026-09-03 (Budapest) + 1 nap


def test_rang_8_folott_egy_nappal_kesobb(cap=8):
    # 9 soha-nem-gyűlt reggeli szó config-sorrendben: az első 8 másnap, a 9. egy nappal később
    szavak = [_reggeli("szo%02d" % i) for i in range(9)]
    ki = varhato_gyujtes.varhato_gyujtes_datumok(_config(szavak), {}, MOST, cap=8)
    assert ki["szo00"] == "2026-09-04"
    assert ki["szo07"] == "2026-09-04"
    assert ki["szo08"] == "2026-09-05"   # floor(8/8)=1 → +1 nap


def test_mar_begyult_szo_nem_kap_datumot():
    cfg = _config([_reggeli("infláció")])
    mn = {"infláció": [_rekord("2026-09-03T07:00:00+00:00")]}   # van érvényes lekerdezes_utc
    assert varhato_gyujtes.varhato_gyujtes_datumok(cfg, mn, MOST) == {}


def test_ervenytelen_lekerdezes_utc_soha_nem_gyultnek_szamit():
    cfg = _config([_reggeli("infláció")])
    mn = {"infláció": [_rekord(None)]}   # rekord van, de nincs érvényes időbélyeg → inf elavultság
    assert varhato_gyujtes.varhato_gyujtes_datumok(cfg, mn, MOST) == {"infláció": "2026-09-04"}


def test_esti_es_oras_szavak_kizarva():
    esti = KulcsszoTetel("állás", "munka", "szintmero", "nap", False, "este")
    oras = KulcsszoTetel("benzin", "fogyasztas", "szintmero", "ora", True, "reggel")
    cfg = _config([esti, oras])
    assert varhato_gyujtes.varhato_gyujtes_datumok(cfg, {}, MOST) == {}


def test_ures_vagy_hianyzo_bemenet_ures_map():
    cfg = _config([_reggeli("infláció")])
    # None kulcsszavak-blokk (olvashatatlan/üres fájl esetén a hívó ezt adja)
    assert varhato_gyujtes.varhato_gyujtes_datumok(cfg, {}, MOST) == {"infláció": "2026-09-04"}
    assert varhato_gyujtes.varhato_gyujtes_datumok(_config([]), {}, MOST) == {}


def test_nem_egyezo_timeframe_rekord_soha_nem_gyultnek_szamit():
    # "het" rácsú reggeli szó saját timeframe-je "today 12-m" (RACS_IDOKERET["het"]);
    # a rekord viszont "today 3-m" alatt van — ez NEM a szó saját cellája (pl. este→reggel
    # átállás vagy racs-váltás után ottmaradt régi rekord), ezért a schedulerrel (futtato.
    # masodlagos_szavak_ma) azonosan soha-nem-gyűltnek kell számítania.
    cfg = _config([_reggeli("infláció", racs="het")])
    mn = {"infláció": [{"timeframe": "today 3-m", "lekerdezes_utc": "2026-09-03T07:00:00+00:00",
                         "ablak_kezdet_utc": "2026-06-01T00:00:00+00:00",
                         "ablak_veg_utc": "2026-09-01T00:00:00+00:00", "pontok": []}]}
    assert varhato_gyujtes.varhato_gyujtes_datumok(cfg, mn, MOST) == {"infláció": "2026-09-04"}
