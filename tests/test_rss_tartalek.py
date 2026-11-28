"""RSS-tartalék a felkapott-listához (2026-11-05 óta a Google trending_now / i0OFE végpont [7]-es hibát ad,
így az API-ág üres → nem íródott napfájl). Ha az API üres, az RSS-lista lesz a rangsor- és napfájl-forrás,
API-kompatibilis (egész) volumennel — a downstream modulok `int(tr["volumen"])`-nel olvasnak."""
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from trendfigyelo import felkapott, futtato
from tests.test_futtato import _config, _dummy_tr


@pytest.mark.parametrize("nyers,vart", [
    ("500+", 500), ("1000+", 1000), ("20 000+", 20000), ("20 000+", 20000), ("1,000+", 1000),
    ("2K+", 2000), ("1M+", 1000000), (300, 300), ("", 0), (None, 0), ("sok", 0),
])
def test_rss_volumen_szam(nyers, vart):
    assert felkapott.rss_volumen_szam(nyers) == vart


def _hir(cim):
    return SimpleNamespace(title=cim, source="Index", url="http://x", time=None, picture="", snippet="")


def _rss(kw, vol):
    return SimpleNamespace(keyword=kw, volume=vol, trend_keywords=[], link="", started=None,
                           picture="", picture_source="", news=[_hir(f"{kw} hír")])


def test_rss_tartalek_api_kompatibilis():
    ki = felkapott.rss_tartalek([_rss("föld", "1000+")])
    assert ki[0].keyword == "föld" and ki[0].volume == 1000
    assert ki[0].news[0].title == "föld hír"
    assert felkapott.volumen_szam(ki[0]) == 1000          # a meglévő rangsorolás numerikusan olvassa


def test_rss_tartalek_ures():
    assert felkapott.rss_tartalek([]) == []
    assert felkapott.rss_tartalek(None) == []


class ApiHalottKliens:
    """A 2026-11-05 óta élő helyzet: felkapott_api TypeError, az RSS ad 3 trendet szöveges volumennel."""
    def __init__(self, api=None):
        self.tr = _dummy_tr()
        self.hivasok = {}
        self.idosor_kifejezesek = None
        self.api = api
    def hivas(self, ag, fn, *a, **k):
        self.hivasok[ag] = self.hivasok.get(ag, 0) + 1
        if ag == "felkapott_api":
            if self.api is None:
                raise TypeError("the JSON object must be str, bytes or bytearray, not NoneType")
            return self.api
        if ag == "felkapott_rss":
            return [_rss("m1", "500+"), _rss("föld", "1000+"), _rss("vasút", "200+")]
        return []
    def hivasszam(self, ag):
        return self.hivasok.get(ag, 0)
    def osszes_hivas(self):
        return sum(self.hivasok.values())


def _futtat(tmp_path, kliens, monkeypatch=None):
    most = datetime(2021, 1, 1, 19, 0, tzinfo=timezone.utc)
    ddir = tmp_path / "docs" / "data"
    kod = futtato.futtat(_config(), kliens, tmp_path / "adatok", ddir, most=most)
    return kod, ddir


def test_api_halott_rss_bol_irodik_napfajl(tmp_path, capsys):
    kod, ddir = _futtat(tmp_path, ApiHalottKliens())
    assert kod == 0
    napfajlok = [p for p in (ddir / "napok").glob("*.json") if p.name != "index.json"]
    assert len(napfajlok) == 1
    szeg = json.loads(napfajlok[0].read_text(encoding="utf-8"))["este"]
    assert szeg["forras"] == "rss"
    trendek = szeg["trendek"]
    assert [t["kifejezes"] for t in trendek] == ["föld", "m1"]        # volumen szerint, trend_idosor_max=2
    assert [t["volumen"] for t in trendek] == ["1000", "500"]         # API-kompatibilis egész-szöveg
    assert all(int(t["volumen"]) > 0 for t in trendek)                # downstream int() nem bukik
    assert trendek[0]["hirek"][0]["hir_cim"] == "föld hír"
    assert "RSS-tartalék" in capsys.readouterr().out                  # nem néma


def test_api_halott_idosor_az_rss_kifejezesekre_fut(tmp_path, monkeypatch):
    kapott = {}
    def fake_gyujt(kliens, config, kifejezesek):
        kapott["kif"] = list(kifejezesek)
        return []
    monkeypatch.setattr(futtato.idosorok, "gyujt", fake_gyujt)
    _futtat(tmp_path, ApiHalottKliens())
    assert kapott["kif"][:2] == ["föld", "m1"]


def test_mukodo_api_eseten_nincs_forras_jeloles_SZANDEKOS_ZOLD(tmp_path):
    api = [SimpleNamespace(keyword="infláció", volume=50000, volume_growth_pct=120, trend_keywords=[],
                           started=None, picture="", picture_source="", news=[])]
    _, ddir = _futtat(tmp_path, ApiHalottKliens(api=api))
    napfajl = next(p for p in (ddir / "napok").glob("*.json") if p.name != "index.json")
    szeg = json.loads(napfajl.read_text(encoding="utf-8"))["este"]
    assert "forras" not in szeg
    assert [t["kifejezes"] for t in szeg["trendek"]] == ["infláció"]


def test_masik_szegmens_irasa_megorzi_a_forras_jelolest(tmp_path):
    """Élő eset (11-27): a reggeli RSS-szegmens `forras` jelölését az esti napi_ir eldobta."""
    from trendfigyelo import json_export
    json_export.napi_ir(tmp_path, "2026-11-27", [{"kifejezes": "föld"}], szegmens="reggel",
                        frissitve_iso="2026-11-27T09:42:00+00:00", forras="rss")
    json_export.napi_ir(tmp_path, "2026-11-27", [{"kifejezes": "m1"}], szegmens="este",
                        frissitve_iso="2026-11-27T20:00:00+00:00")
    d = json.loads((tmp_path / "napok" / "2026-11-27.json").read_text(encoding="utf-8"))
    assert d["reggel"]["forras"] == "rss"
    assert "forras" not in d["este"]
