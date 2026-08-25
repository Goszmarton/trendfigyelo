"""MÁSODLAGOS-ONLY belépő (S) — CSAK a másodlagos cellák feltöltése.

A LEGFONTOSABB invariáns (külön teszt): a belépő SEMMILYEN más ágat nem indít
(primer órás/idosor/felkapott/rss/lánc/ir_gordulo) — a primer órás az EGYETLEN
pótolhatatlan adat (§10)."""

from datetime import datetime, timedelta, timezone

import json
import pandas as pd

from trendfigyelo import masodlagos_only
from trendfigyelo.config import Config, KulcsszoTetel

_MOST = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)


def _config(szavak):
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        alap_keses_mp=3.0, szoras_mp=(3, 7), max_probak=4, backoff_mp=[30, 120, 480],
        trend_idosor_max=15, proxy=None, kulcsszavak=szavak,
    )


def _eles_config():
    return _config([
        KulcsszoTetel("albérlet", "l", "szintmero", "nap"),
        KulcsszoTetel("kórház", "e", "szintmero", "het"),
        KulcsszoTetel("hitel", "h", "szintmero", "nap"),
        KulcsszoTetel("benzin", "f", "szintmero", "ora"),   # ora → nem jogosult
    ])


def _df_for_tf(kif, timeframe, most, csonka=False):
    """A timeframe-nek MEGFELELŐ (vagy csonka) szabályos df, a most-ra végződve (frissesség-OK)."""
    step = 1 if "3-m" in timeframe else 7
    n = (10 if csonka else 92) if step == 1 else (8 if csonka else 53)
    utolso = most - timedelta(days=step)
    napok = [utolso - timedelta(days=i * step) for i in range(n)][::-1] + [most]
    ertek = [50] * n + [0]
    ip = [False] * n + [True]
    return pd.DataFrame({kif: ertek, "isPartial": ip}, index=pd.to_datetime(napok))


class _FakeKliens:
    """A timeframe-nek megfelelő df-et ad; SOHA nem alszik/hív hálózatot."""
    def __init__(self, most=_MOST, csonka=False):
        self.most = most
        self.csonka = csonka
        self.hivott = []
        self.tr = type("T", (), {"interest_over_time": None})()

    def hivas(self, ag, fn, szavak, geo=None, timeframe=None, gprop=""):
        self.hivott.append((ag, szavak[0], timeframe))
        return _df_for_tf(szavak[0], timeframe, self.most, self.csonka)

    def hivasszam(self, ag):
        return len(self.hivott)


def _read(docs):
    f = docs / "kulcsszo_masodlagos_nyers.json"
    return json.loads(f.read_text(encoding="utf-8"))["kulcsszavak"] if f.exists() else {}


def test_masodlagos_only_feltolti_a_cellakat(tmp_path):
    # RED: a belépő a megadott (szó, timeframe) cellát letölti + ELMENTI, és visszaadja a letöltöttet.
    c = _eles_config()
    k = _FakeKliens()
    ki = masodlagos_only.futtat_masodlagos_only(c, tmp_path, _MOST, max_cella=1,
                                                cellak=[("hitel", "today 3-m")], kliens=k)
    assert [(sz, tf) for sz, tf, _ in ki["letoltve"]] == [("hitel", "today 3-m")]
    rekk = _read(tmp_path).get("hitel", [])
    assert any(r["timeframe"] == "today 3-m" for r in rekk)   # ténylegesen elmentve


def test_masodlagos_only_csonka_eldobva(tmp_path):
    # RED: a mai érkezés-ellenőrzés ÉLES → csonka cella ELDOBVA (nem mentve), az eldobva listában.
    c = _eles_config()
    k = _FakeKliens(csonka=True)
    ki = masodlagos_only.futtat_masodlagos_only(c, tmp_path, _MOST, max_cella=1,
                                                cellak=[("hitel", "today 12-m")], kliens=k)
    assert ki["letoltve"] == []
    assert ("hitel", "today 12-m") in ki["eldobva"]
    assert _read(tmp_path) == {}   # semmi nem mentődött


def test_masodlagos_only_sajat_limit_nem_a_napi_cap(tmp_path):
    # RED: a belépő SAJÁT limitje (max_cella), NEM a napi MAX_MASODLAGOS_NAPI(=2). max_cella=5 → 5 cella.
    c = _config([KulcsszoTetel(k, "d", "szintmero", "nap") for k in ["a", "b", "c"]])   # 3 szó × 2 tf = 6 cella
    k = _FakeKliens()
    ki = masodlagos_only.futtat_masodlagos_only(c, tmp_path, _MOST, max_cella=5, kliens=k)
    assert len(ki["letoltve"]) + len(ki["eldobva"]) == 5   # 5 cella (nem 2)


def test_masodlagos_only_NEM_INDITJA_a_primer_agat(tmp_path, monkeypatch):
    # A LEGFONTOSABB invariáns: a belépő SEMMILYEN más ágat nem indít — a primer órás pótolhatatlan (§10).
    from trendfigyelo import felkapott, idosorok, kulcsszavak, lanc, nyers_kimenet
    tiltott = []

    def _tilos(nev):
        def _f(*a, **k):
            tiltott.append(nev)
            raise AssertionError(f"TILTOTT ág indult a másodlagos-only belépőből: {nev}")
        return _f

    monkeypatch.setattr(felkapott, "gyujt_api", _tilos("felkapott.gyujt_api"))
    monkeypatch.setattr(felkapott, "gyujt_rss", _tilos("felkapott.gyujt_rss"))
    monkeypatch.setattr(idosorok, "gyujt", _tilos("idosorok.gyujt"))
    monkeypatch.setattr(kulcsszavak, "gyujt", _tilos("kulcsszavak.gyujt"))   # a PRIMER órás
    monkeypatch.setattr(lanc, "frissit_lanc", _tilos("lanc.frissit_lanc"))
    monkeypatch.setattr(nyers_kimenet, "ir_gordulo", _tilos("nyers_kimenet.ir_gordulo"))

    c = _eles_config()
    masodlagos_only.futtat_masodlagos_only(c, tmp_path, _MOST, max_cella=2,
                                           cellak=[("hitel", "today 3-m"), ("kórház", "today 12-m")],
                                           kliens=_FakeKliens())
    assert tiltott == []   # EGYIK tiltott ág sem indult
