from trendfigyelo import naplo


def test_uj_fajl_fejleccel(tmp_path):
    p = naplo.naplo_ir(tmp_path, "2021-01-01T12:00:00+00:00", [
        {"ag": "felkapott_api", "eredmeny": "siker", "hivasok_szama": 1, "hibakodok": ""},
    ])
    sorok = p.read_text(encoding="utf-8-sig").splitlines()
    assert sorok[0] == "futas_ido_utc;ag;eredmeny;hivasok_szama;hibakodok"
    assert sorok[1] == "2021-01-01T12:00:00+00:00;felkapott_api;siker;1;"
    assert p.name == "naplo.csv"


def test_masodik_futas_hozzafuz_fejlec_nelkul(tmp_path):
    naplo.naplo_ir(tmp_path, "2021-01-01T12:00:00+00:00",
                   [{"ag": "a", "eredmeny": "siker", "hivasok_szama": 1, "hibakodok": ""}])
    p = naplo.naplo_ir(tmp_path, "2021-01-02T12:00:00+00:00",
                       [{"ag": "b", "eredmeny": "hiba", "hivasok_szama": 4, "hibakodok": "429,429"}])
    sorok = p.read_text(encoding="utf-8-sig").splitlines()
    assert len(sorok) == 3  # 1 fejléc + 2 adatsor
    assert sorok[2] == "2021-01-02T12:00:00+00:00;b;hiba;4;429,429"
