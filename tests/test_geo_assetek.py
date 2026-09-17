import json
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / "docs" / "vendor"


def test_leaflet_vendorelt():
    assert (VENDOR / "leaflet" / "leaflet.js").stat().st_size > 100000     # ~140KB
    assert (VENDOR / "leaflet" / "leaflet.css").stat().st_size > 10000


def test_vilag_orszagok_geojson():
    gj = json.loads((VENDOR / "geo" / "vilag-orszagok.geojson").read_text(encoding="utf-8"))
    assert gj.get("type") == "FeatureCollection"
    feats = gj["features"]
    assert len(feats) > 150                                                # ~177 ország
    assert all("id" in f for f in feats[:5])                               # ISO-kód a feature-ön


def test_orszag_nev_iso_magyar():
    m = json.loads((VENDOR / "geo" / "orszag-nev-iso.json").read_text(encoding="utf-8"))
    assert m.get("magyarország") == "HUN" and m.get("németország") == "DEU"
    assert len(m) > 150


def test_hu_telepules_koord():
    t = json.loads((VENDOR / "geo" / "hu-telepules-koord.json").read_text(encoding="utf-8"))
    assert len(t) > 1000                                                   # sok magyar település
    assert "debrecen" in t and abs(t["debrecen"][0] - 47.53) < 0.3         # ~Debrecen szélesség


def test_varos_koord_magyar_exonimak():
    v = json.loads((VENDOR / "geo" / "varos-koord.json").read_text(encoding="utf-8"))
    for varos in ("moszkva", "kijev", "brüsszel", "porto"):
        assert varos in v and len(v[varos]) == 2                          # a felmerülő városok
