"""Task 3 (Phase 4) — másodlagos (nap/het) gyűjtő-ág + hétnap-ütemezés.

Minden teszt HÉTNAP-BEMENETTEL (a `most` datetime hétnapja), nulla naptár-függés.
Az ütemezés a nem-órás szavak config-sorrend szerinti sorszáma % 7 — a konkrét
hozzárendelés config-sorrend-függő (szó beszúrása eltolja); a teszt CSAK a
szerkezeti invariánst őrzi (≤2/nap, mindet pontosan egyszer).
"""

import json
from datetime import datetime, timezone

import pandas as pd

from trendfigyelo import futtato, kulcsszavak, nyers_kimenet
from trendfigyelo.config import Config, KulcsszoTetel
import pytest

from trendfigyelo.kliens import AgFeladva, PlafonTullepve


def _config(kulcsszavak_lista):
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        alap_keses_mp=3.0, szoras_mp=(3, 7), max_probak=4, backoff_mp=[30, 120, 480],
        trend_idosor_max=15, proxy=None, kulcsszavak=kulcsszavak_lista,
    )


def _eles_config():
    # a valódi 13 szó rács-besorolása (2 ora / 6 nap / 5 het)
    return _config([
        KulcsszoTetel("állás", "m", "szintmero", "het"),
        KulcsszoTetel("kormányablak", "k", "szintmero", "het"),
        KulcsszoTetel("eladó lakás", "l", "szintmero", "nap"),
        KulcsszoTetel("albérlet", "l", "szintmero", "nap"),
        KulcsszoTetel("akciós újság", "f", "szintmero", "het"),
        KulcsszoTetel("benzin", "f", "szintmero", "ora"),
        KulcsszoTetel("nyaralás", "f", "szintmero", "nap"),
        KulcsszoTetel("kórház", "e", "szintmero", "het"),
        KulcsszoTetel("betegség", "e", "szintmero", "nap"),
        KulcsszoTetel("napelem", "e", "hibrid", "nap"),
        KulcsszoTetel("nyugdíj", "j", "hibrid", "ora"),
        KulcsszoTetel("hitel", "h", "szintmero", "nap"),
        KulcsszoTetel("tüntetés", "kz", "esemenyjelzo", "het"),
    ])


def _nap(hetnap):
    # 2021-01-04 hétfő (weekday 0); +hetnap adja a kívánt UTC hétnapot
    return datetime(2021, 1, 4 + hetnap, 12, tzinfo=timezone.utc)


# --- Ciklus A: ütemező ---

def test_masodlagos_szavak_ma_max_2_per_nap():
    c = _eles_config()
    for hetnap in range(7):
        szavak = futtato.masodlagos_szavak_ma(c, _nap(hetnap))
        assert len(szavak) <= 2, f"hétnap {hetnap}: {[t.kifejezes for t in szavak]}"


def test_masodlagos_szavak_ma_lefedi_mindet_egyszer():
    c = _eles_config()
    osszes = []
    for hetnap in range(7):
        osszes += [t.kifejezes for t in futtato.masodlagos_szavak_ma(c, _nap(hetnap))]
    nem_oras = {t.kifejezes for t in c.osszes_kulcsszo() if t.racs != "ora"}
    assert sorted(osszes) == sorted(nem_oras)          # mindet PONTOSAN egyszer, semmi extra
    assert all("benzin" != k and "nyugdíj" != k for k in osszes)   # az ora-szavak kimaradnak


# --- Ciklus B: egy szó másodlagos gyűjtése ---

def _df_masodlagos(kif):
    idx = pd.to_datetime([
        datetime(2026, 5, 16, tzinfo=timezone.utc),   # ablak-kezdet
        datetime(2026, 8, 12, tzinfo=timezone.utc),   # teljes
        datetime(2026, 8, 13, tzinfo=timezone.utc),   # részleges farok
    ])
    return pd.DataFrame({kif: [30, 40, 99], "isPartial": [False, False, True]}, index=idx)


class _RogzitoKliens:
    """A hivas() timeframe/ag argumentumát rögzíti, szavankénti df-et ad."""
    def __init__(self, df_gyar=_df_masodlagos):
        self.df_gyar = df_gyar
        self.timeframe = None
        self.ag = None
        self.tr = type("T", (), {"interest_over_time": None})()

    def hivas(self, ag, fn, szavak, geo=None, timeframe=None):
        self.ag = ag
        self.timeframe = timeframe
        return self.df_gyar(szavak[0])

    def hivasszam(self, ag):
        return 1


def test_gyujt_egy_masodlagos_rekord_racs_lekerdezes_idokeret():
    from trendfigyelo.config import RACS_IDOKERET
    from trendfigyelo.nyers_kimenet import ervenyes_masodlagos_rekord
    tetel = KulcsszoTetel("hitel", "h", "szintmero", "nap")
    k = _RogzitoKliens()
    most = datetime(2026, 8, 13, 9, 0, tzinfo=timezone.utc)
    rek = kulcsszavak.gyujt_egy_masodlagos(k, _config([tetel]), tetel, most)
    assert k.timeframe == RACS_IDOKERET["nap"] == "today 3-m"   # a racs szerinti timeframe ment ki
    assert k.ag == "kulcsszo_masodlagos"                        # külön Kliens-számláló / napló-ág
    assert rek["racs"] == "nap"
    assert rek["lekerdezes_utc"] == "2026-08-13T09:00:00+00:00"
    assert ervenyes_masodlagos_rekord(rek) == []               # a Task 2 szerződését teljesíti


# --- Ciklus C: a másodlagos ág (szavankénti írás + csendes feladás) ---

class _MasodlagosBukoKliens:
    """szo0 sikeres df; szo7 AgFeladva (a 2. ütemezett szó blokkol)."""
    def __init__(self):
        self.tr = type("T", (), {"interest_over_time": None})()
        self.hivott = []

    def hivas(self, ag, fn, szavak, geo=None, timeframe=None):
        self.hivott.append(szavak[0])
        if szavak[0] == "szo7":
            raise AgFeladva(ag, ["429", "429", "429", "429"])
        return _df_masodlagos(szavak[0])

    def hivasszam(self, ag):
        return len(self.hivott)


def test_masodlagos_ag_szavankent_ir_a_blokk_elott(tmp_path):
    # 8 nap-szó → weekday 0 az index 0 és 7 szót ütemezi; a 2. (szo7) blokkol.
    c = _config([KulcsszoTetel(f"szo{i}", "d", "szintmero", "nap") for i in range(8)])
    most = _nap(0)
    assert [t.kifejezes for t in futtato.masodlagos_szavak_ma(c, most)] == ["szo0", "szo7"]
    bejegyzesek = []
    futtato._masodlagos_ag(bejegyzesek, _MasodlagosBukoKliens(), c, tmp_path, most)  # NEM dob (csendes)
    fajl = tmp_path / "kulcsszo_masodlagos_nyers.json"
    adat = json.loads(fajl.read_text(encoding="utf-8")) if fajl.exists() else {"kulcsszavak": {}}
    assert "szo0" in adat["kulcsszavak"]        # az első szó a blokk ELŐTT kiíródott (szavankénti írás)
    assert "szo7" not in adat["kulcsszavak"]     # a blokkolt szó nincs
    naplo = {b["ag"]: b["eredmeny"] for b in bejegyzesek}
    assert naplo["kulcsszo_masodlagos"] == "blokkolva"    # külön napló-címke, csendes blokk


# ── MASODLAGOS-PLAFON: a plafon HARD (exit 2), de a napló EXPLICIT 'plafon'-t írjon (nem 'kihagyva') ──
class _MasodlagosPlafonKliens:
    """Minden másodlagos hívás PlafonTullepve (a hívás-plafon)."""
    def __init__(self):
        self.tr = type("T", (), {"interest_over_time": None})()
        self.n = 0
    def hivas(self, ag, fn, szavak, geo=None, timeframe=None):
        self.n += 1
        raise PlafonTullepve(ag, 121, 120)
    def hivasszam(self, ag):
        return self.n


def test_masodlagos_ag_plafon_naploz_plafont_es_propagal(tmp_path):
    c = _config([KulcsszoTetel(f"szo{i}", "d", "szintmero", "nap") for i in range(8)])
    bejegyzesek = []
    with pytest.raises(PlafonTullepve):                       # a plafon HARD marad (propagál → exit 2)
        futtato._masodlagos_ag(bejegyzesek, _MasodlagosPlafonKliens(), c, tmp_path, _nap(0))
    naplo = {b["ag"]: b["eredmeny"] for b in bejegyzesek}
    assert naplo.get("kulcsszo_masodlagos") == "plafon"       # NEM 'kihagyva' — külön 'plafon'-címke
