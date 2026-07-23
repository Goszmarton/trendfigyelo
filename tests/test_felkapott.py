from types import SimpleNamespace

from trendfigyelo import felkapott


def _api_trend():
    return SimpleNamespace(
        keyword="infláció", volume=50000, volume_growth_pct=120,
        started_timestamp=(1609459200, 0), ended_timestamp=None,
        is_trend_finished=False, trend_keywords=["ár", "MNB"],
        topic_names=["gazdaság"], normalized_keyword="inflacio",
    )


def _rss_trend():
    hir = SimpleNamespace(title="Címsor", source="Index", url="http://x",
                          time=1609459200, picture="http://k", snippet="kivonat")
    return SimpleNamespace(keyword="benzinár", volume="20000",
                           trend_keywords=["üzemanyag"], started=1609459200,
                           picture="http://p", picture_source="MTI", news=[hir])


def test_api_trend_dict_oszlopok():
    d = felkapott.api_trend_dict(_api_trend(), 1)
    assert d["kifejezes"] == "infláció"
    assert d["volumen"] == "50000"
    assert d["aktiv"] == "igen"  # is_trend_finished False → aktív
    assert d["trend_indult_utc"] == "2021-01-01T00:00:00+00:00"
    assert d["kapcsolodo_kifejezesek"] == "ár, MNB"


def test_volumen_szam_hibatur():
    assert felkapott.volumen_szam(_api_trend()) == 50000
    assert felkapott.volumen_szam(SimpleNamespace(volume=None)) == 0


def test_hir_sorok_soronkent_egy_hir():
    sorok = felkapott.hir_sorok([_rss_trend()])
    assert len(sorok) == 1
    assert sorok[0]["hir_cim"] == "Címsor"
    assert sorok[0]["kifejezes"] == "benzinár"


def test_csv_ir_api_fejlec_es_geo_oszlop(tmp_path):
    p = felkapott.csv_ir_api(tmp_path, "2021-01-01_1200", "2021-01-01T12:00:00+00:00",
                             "HU", [_api_trend()])
    tartalom = p.read_text(encoding="utf-8-sig")
    fejlec = tartalom.splitlines()[0]
    assert fejlec.split(";")[1] == "kifejezes"
    assert fejlec.strip().endswith("geo")
    assert "HU" in tartalom.splitlines()[1]
    assert p.name == "top_keresesek_api_HU_2021-01-01_1200.csv"


def test_api_trend_dict_hianyzo_keyword_nem_dobal():
    t = SimpleNamespace(volume=100)  # nincs keyword attribútum
    d = felkapott.api_trend_dict(t, 1)
    assert d["kifejezes"] == ""
