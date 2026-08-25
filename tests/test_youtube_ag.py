import json
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
import pandas as pd
from trendfigyelo import youtube

_MOST = datetime(2026, 8, 20, 9, tzinfo=timezone.utc)

def _config():
    yt = [SimpleNamespace(kifejezes="edzés", domen="egeszseg", tipus="szintmero", racs="nap"),
          SimpleNamespace(kifejezes="klíma", domen="otthon", tipus="szintmero", racs="het")]
    return SimpleNamespace(geo="HU", max_probak=4, naplo_max_sor=2000, modszertan_valtas=None,
                           osszes_youtube_kulcsszo=lambda: list(yt),
                           osszes_kulcsszo=lambda: list(yt))

def _df(kif, tf):
    # a span a timeframe VÁRT spanjéhez illik (masodlagos_alak_ok: 0,85–1,2×), a vég _MOST előtt
    if tf == "today 3-m":                       # ~92 nap, napi rács, vége 2026-08-19
        veg = datetime(2026, 8, 19, tzinfo=timezone.utc)
        idx = [veg - timedelta(days=i) for i in range(92)][::-1]
    else:                                       # ~53 hét, heti rács, vége 2026-08-19
        veg = datetime(2026, 8, 19, tzinfo=timezone.utc)
        idx = [veg - timedelta(weeks=i) for i in range(53)][::-1]
    return pd.DataFrame({kif: [40]*len(idx), "isPartial": [False]*(len(idx)-1) + [True]}, index=idx)

class _FakeKliens:
    def __init__(self):
        self.szam = 0
        self.tr = SimpleNamespace(interest_over_time=None)
    def hivas(self, ag, fn, szavak, geo, timeframe, gprop):
        self.szam += 1
        assert gprop == "youtube" and ag == "youtube"
        return _df(szavak[0], timeframe)
    def osszes_hivas(self):
        return self.szam

def test_futtat_youtube_24_cella_ir_nyers_es_regressziot(tmp_path):
    k = _FakeKliens()
    ki = youtube.futtat_youtube(_config(), tmp_path, _MOST, kliens=k)
    # 2 szó × 2 timeframe = 4 cella (a teszt-configban 2 szó)
    assert len(ki["letoltve"]) == 4
    nyers = json.loads((tmp_path / "youtube_nyers.json").read_text(encoding="utf-8"))["kulcsszavak"]
    assert set(nyers) == {"edzés", "klíma"}
    reg = json.loads((tmp_path / "youtube_regresszio.json").read_text(encoding="utf-8"))["kulcsszavak"]
    assert "edzés" in reg and "klíma" in reg

def test_futtat_youtube_nem_indit_mas_agat(tmp_path, monkeypatch):
    from trendfigyelo import felkapott, idosorok, kulcsszavak, lanc, nyers_kimenet
    tiltott = []
    def tilt(nev):
        return lambda *a, **k: tiltott.append(nev) or (_ for _ in ()).throw(AssertionError(nev))
    monkeypatch.setattr(felkapott, "gyujt_api", tilt("felkapott.gyujt_api"), raising=False)
    monkeypatch.setattr(felkapott, "gyujt_rss", tilt("felkapott.gyujt_rss"), raising=False)
    monkeypatch.setattr(idosorok, "gyujt", tilt("idosorok.gyujt"), raising=False)
    monkeypatch.setattr(kulcsszavak, "gyujt", tilt("kulcsszavak.gyujt"), raising=False)
    monkeypatch.setattr(lanc, "frissit_lanc", tilt("lanc.frissit_lanc"), raising=False)
    monkeypatch.setattr(nyers_kimenet, "ir_gordulo", tilt("nyers_kimenet.ir_gordulo"), raising=False)
    youtube.futtat_youtube(_config(), tmp_path, _MOST, kliens=_FakeKliens())
    assert tiltott == []
