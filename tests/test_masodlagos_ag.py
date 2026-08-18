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


# --- Ciklus A: STALENESS-vezérelt ütemező (Task 5, a %7 helyett) ---

def _ir_masodlagos_nyers(docs, kif_datum):
    """kulcsszo_masodlagos_nyers.json a megadott szó→utolsó-lekerdezes-dátummal (staleness-beállítás)."""
    docs.mkdir(parents=True, exist_ok=True)
    kk = {kif: [{"lekerdezes_utc": f"{nap}T12:00:00+00:00", "racs": "nap"}] for kif, nap in kif_datum.items()}
    (docs / "kulcsszo_masodlagos_nyers.json").write_text(
        json.dumps({"kulcsszavak": kk}, ensure_ascii=False), encoding="utf-8")


_MOST = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)


def test_masodlagos_legelavultabb_elol(tmp_path):
    # RED 1 (fed: staleness-RENDEZÉS): a 2 LEGELAVULTABB szó, nem a hétnap-alapú lista.
    c = _config([KulcsszoTetel(k, "d", "szintmero", "nap") for k in ["a", "b", "c", "d"]])
    _ir_masodlagos_nyers(tmp_path, {"a": "2026-08-17", "b": "2026-08-01", "c": "2026-08-10", "d": "2026-08-16"})
    szavak = [t.kifejezes for t in futtato.masodlagos_szavak_ma(c, _MOST, tmp_path)]
    assert szavak == ["b", "c"]   # b (17 nap) > c (8 nap) > d (2) > a (1) → a 2 legelavultabb


def test_masodlagos_never_collected_prioritas(tmp_path):
    # RED 2 (fed: None=max-elavult KEZELÉS, külön a kortól): a soha-gyűjtött (fájlban NINCS) szavak ELÖL.
    c = _config([KulcsszoTetel(k, "d", "szintmero", "nap") for k in ["a", "b", "c", "d"]])
    _ir_masodlagos_nyers(tmp_path, {"a": "2026-08-01", "b": "2026-08-02"})   # c, d SOHA
    szavak = [t.kifejezes for t in futtato.masodlagos_szavak_ma(c, _MOST, tmp_path)]
    assert szavak == ["c", "d"]   # c, d never-collected (max elavult) → a régi a/b elé


def test_masodlagos_tie_break_config_index(tmp_path):
    # RED 3 (fed: TIE-BREAK config-index, NEM ábécé): azonos elavultság → config-sorrend.
    c = _config([KulcsszoTetel(k, "d", "szintmero", "nap") for k in ["zebra", "alma", "medve"]])
    _ir_masodlagos_nyers(tmp_path, {"zebra": "2026-08-01", "alma": "2026-08-01", "medve": "2026-08-17"})
    szavak = [t.kifejezes for t in futtato.masodlagos_szavak_ma(c, _MOST, tmp_path)]
    assert szavak == ["zebra", "alma"]   # azonos kor → config-index (zebra idx0, alma idx1); ábécé "alma" elöl LENNE


def test_masodlagos_cap_max_napi(tmp_path):
    # RED 4 (fed: EXPLICIT CAP, az 5. rejtett feltevés): >14 jogosult szó → a %7 egy hétnapon 3-at adna
    # (index 0,7,14), a no-cap mutáció 15-öt; a cap PONTOSAN MAX_MASODLAGOS_NAPI-t. Megkülönbözteti MINDKETTŐT.
    c = _config([KulcsszoTetel("w%02d" % i, "d", "szintmero", "nap") for i in range(15)])   # 15 jogosult (>14)
    _ir_masodlagos_nyers(tmp_path, {})   # üres → mind never-collected (max elavult) → cap nélkül 15 jönne
    szavak = futtato.masodlagos_szavak_ma(c, _nap(0), tmp_path)   # _nap(0) = hétfő (weekday 0): %7 index 0,7,14 = 3
    assert len(szavak) == futtato.MAX_MASODLAGOS_NAPI == 2   # a cap PONTOSAN vág (a %7 3-at, a no-cap 15-öt adna)


def test_masodlagos_sorozat_hiany_nem_all_le(tmp_path, capsys):
    # RED 5 (fed: I/O-ROBUSZTUSSÁG): hiányzó/hibás nyers → NEM dob, config-index fallback + HANGOS FIGYELEM.
    c = _config([KulcsszoTetel(k, "d", "szintmero", "nap") for k in ["a", "b", "c"]])
    # (a) fájl HIÁNYZIK
    szavak = [t.kifejezes for t in futtato.masodlagos_szavak_ma(c, _MOST, tmp_path)]
    assert szavak == ["a", "b"]   # config-index első 2 (fallback), NEM dob
    ki = capsys.readouterr().out
    assert "FALLBACK" in ki and "kulcsszo_masodlagos_nyers.json" in ki   # HANGOS, megnevezi a fájlt
    # (b) JSON-hibás fájl
    (tmp_path / "kulcsszo_masodlagos_nyers.json").write_text("{ROSSZ", encoding="utf-8")
    szavak2 = [t.kifejezes for t in futtato.masodlagos_szavak_ma(c, _MOST, tmp_path)]
    assert szavak2 == ["a", "b"]   # JSON-hiba is fallback, NEM dob


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
    """szo0 sikeres df; szo1 AgFeladva (a 2. ütemezett szó blokkol)."""
    def __init__(self):
        self.tr = type("T", (), {"interest_over_time": None})()
        self.hivott = []

    def hivas(self, ag, fn, szavak, geo=None, timeframe=None):
        self.hivott.append(szavak[0])
        if szavak[0] == "szo1":
            raise AgFeladva(ag, ["429", "429", "429", "429"])
        return _df_masodlagos(szavak[0])

    def hivasszam(self, ag):
        return len(self.hivott)


def test_masodlagos_ag_szavankent_ir_a_blokk_elott(tmp_path):
    # 8 nap-szó, MIND never-collected (nincs nyers) → fallback config-index első 2 = szo0, szo1; a 2. (szo1) blokkol.
    c = _config([KulcsszoTetel(f"szo{i}", "d", "szintmero", "nap") for i in range(8)])
    most = _nap(0)
    assert [t.kifejezes for t in futtato.masodlagos_szavak_ma(c, most, tmp_path)] == ["szo0", "szo1"]
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
