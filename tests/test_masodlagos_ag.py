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

def _ir_masodlagos_nyers(docs, kif_tf_datum):
    """kulcsszo_masodlagos_nyers.json PER-CELLA (szó × timeframe) utolsó-lekerdezes-dátummal (staleness-beállítás).
    kif_tf_datum: {kif: {timeframe: datum}}."""
    docs.mkdir(parents=True, exist_ok=True)
    kk = {kif: [{"timeframe": tf, "racs": "nap", "lekerdezes_utc": f"{nap}T12:00:00+00:00"}
                for tf, nap in tf_datum.items()]
          for kif, tf_datum in kif_tf_datum.items()}
    (docs / "kulcsszo_masodlagos_nyers.json").write_text(
        json.dumps({"kulcsszavak": kk}, ensure_ascii=False), encoding="utf-8")


def _cellak(c, most, docs):
    """A scheduler kimenete (tetel, timeframe) párokból (szó, timeframe) párokra."""
    return [(t.kifejezes, tf) for t, tf in futtato.masodlagos_szavak_ma(c, most, docs)]


_MOST = datetime(2026, 8, 18, 12, tzinfo=timezone.utc)


def test_masodlagos_legelavultabb_elol(tmp_path):
    # fed: staleness-RENDEZÉS CELLA-szinten (szó × timeframe): a 2 LEGELAVULTABB CELLA.
    c = _config([KulcsszoTetel(k, "d", "szintmero", "nap") for k in ["a", "b"]])
    _ir_masodlagos_nyers(tmp_path, {
        "a": {"today 3-m": "2026-08-17", "today 12-m": "2026-08-01"},   # a/12-m = 17 nap (legelavultabb)
        "b": {"today 3-m": "2026-08-17", "today 12-m": "2026-08-10"}})   # b/12-m = 8 nap
    assert _cellak(c, _MOST, tmp_path) == [("a", "today 12-m"), ("b", "today 12-m")]   # a 2 legelavultabb cella


def test_masodlagos_never_collected_prioritas(tmp_path):
    # fed: never-collected CELLA (None=max-elavult) ELÖL — a 12-m cellák soha nem gyűltek.
    c = _config([KulcsszoTetel(k, "d", "szintmero", "nap") for k in ["a", "b"]])
    _ir_masodlagos_nyers(tmp_path, {"a": {"today 3-m": "2026-08-01"}, "b": {"today 3-m": "2026-08-02"}})   # 12-m SOHA
    assert _cellak(c, _MOST, tmp_path) == [("a", "today 12-m"), ("b", "today 12-m")]   # never-collected 12-m cellák elöl


def test_masodlagos_tie_break_config_index(tmp_path):
    # fed: TIE-BREAK config-index (NEM ábécé): azonos elavultság (mindkét 12-m never) → config-sorrend.
    c = _config([KulcsszoTetel(k, "d", "szintmero", "nap") for k in ["zebra", "alma", "medve"]])
    _ir_masodlagos_nyers(tmp_path, {"zebra": {"today 3-m": "2026-08-17"}, "alma": {"today 3-m": "2026-08-17"},
                                    "medve": {"today 3-m": "2026-08-17", "today 12-m": "2026-08-17"}})
    assert _cellak(c, _MOST, tmp_path) == [("zebra", "today 12-m"), ("alma", "today 12-m")]   # config-index; ábécé "alma" elöl LENNE


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
    # (a) fájl HIÁNYZIK → fallback: config-index+timeframe első 2 cellája = (a,3-m),(a,12-m)
    assert _cellak(c, _MOST, tmp_path) == [("a", "today 3-m"), ("a", "today 12-m")]   # NEM dob
    ki = capsys.readouterr().out
    assert "FALLBACK" in ki and "kulcsszo_masodlagos_nyers.json" in ki   # HANGOS, megnevezi a fájlt
    # (b) JSON-hibás fájl
    (tmp_path / "kulcsszo_masodlagos_nyers.json").write_text("{ROSSZ", encoding="utf-8")
    assert _cellak(c, _MOST, tmp_path) == [("a", "today 3-m"), ("a", "today 12-m")]   # JSON-hiba is fallback, NEM dob


def test_masodlagos_cella_szintu_utemezes(tmp_path):
    # RED (4. rész): a scheduler (szó, timeframe) PÁROKAT ad; mindkét timeframe KÜLÖN cella; a never-collected elöl.
    c = _config([KulcsszoTetel("a", "d", "szintmero", "nap")])   # 1 szó → 2 cella (today 3-m, today 12-m)
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "kulcsszo_masodlagos_nyers.json").write_text(json.dumps({"kulcsszavak": {   # 3-m friss, 12-m SOHA
        "a": [{"timeframe": "today 3-m", "racs": "nap", "lekerdezes_utc": "2026-08-18T12:00:00+00:00"}]}}),
        encoding="utf-8")
    cellak = futtato.masodlagos_szavak_ma(c, _MOST, tmp_path)
    elso = cellak[0]
    assert isinstance(elso, tuple) and len(elso) == 2          # (tetel, timeframe) pár — RED: ma KulcsszoTetel (len 4)
    tetel, tf = elso
    assert (tetel.kifejezes, tf) == ("a", "today 12-m")        # a never-collected 12-m cella az első
    assert len(cellak) == futtato.MAX_MASODLAGOS_NAPI == 2     # a cap változatlan (cellákra)


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

    def hivas(self, ag, fn, szavak, geo=None, timeframe=None, gprop=""):
        self.ag = ag
        self.timeframe = timeframe
        return self.df_gyar(szavak[0])

    def hivasszam(self, ag):
        return 1


def test_gyujt_egy_masodlagos_rekord_racs_lekerdezes_idokeret():
    from trendfigyelo.nyers_kimenet import ervenyes_masodlagos_rekord
    tetel = KulcsszoTetel("hitel", "h", "szintmero", "nap")
    k = _RogzitoKliens()
    most = datetime(2026, 8, 13, 9, 0, tzinfo=timezone.utc)
    rek = kulcsszavak.gyujt_egy_masodlagos(k, _config([tetel]), tetel, most, "today 3-m")
    assert k.timeframe == "today 3-m"                           # a PARAMÉTER timeframe ment ki
    assert k.ag == "kulcsszo_masodlagos"                        # külön Kliens-számláló / napló-ág
    assert rek["racs"] == "nap"                                 # a timeframe RÁCSA (today 3-m → nap)
    assert rek["timeframe"] == "today 3-m"
    assert rek["lekerdezes_utc"] == "2026-08-13T09:00:00+00:00"
    assert ervenyes_masodlagos_rekord(rek) == []               # a séma-szerződést teljesíti


# --- Ciklus B2: ÉRKEZÉS-ELLENŐRZÉS (per-szó több-timeframe, 1. rész) ---

def _df_racs(kif, n, step_nap, veg=_MOST):
    """n szabályos LEZÁRT pont step_nap közönként, az utolsó (veg−step) napon; részleges farok a veg-en.
    A `veg`-re végződés → frissesség-OK; a span/step a timeframe-ellenőrzés bemenete."""
    from datetime import timedelta
    utolso = veg - timedelta(days=step_nap)
    napok = [utolso - timedelta(days=i * step_nap) for i in range(n)][::-1]
    ertek = [50] * n
    ip = [False] * n
    napok.append(veg); ertek.append(0); ip.append(True)
    return pd.DataFrame({kif: ertek, "isPartial": ip}, index=pd.to_datetime(napok))


def test_masodlagos_csonka_eldobva():
    # RED (1. rész): nap-szó (today 3-m, ~91 nap várt) DE csak 10 napi pont (span 9 nap) → ELDOBVA (None), nem mentve.
    tetel = KulcsszoTetel("hitel", "h", "szintmero", "nap")
    k = _RogzitoKliens(df_gyar=lambda kif: _df_racs(kif, 10, 1))   # span 9 nap << 0,85×91
    rek = kulcsszavak.gyujt_egy_masodlagos(k, _config([tetel]), tetel, _MOST, "today 3-m")
    assert rek is None   # csonka → eldobva


def test_masodlagos_alak_timeframe_fuggo():
    # RED (1. rész, SZÁNDÉKOS-ZÖLD fedés): UGYANAZ a 92 napi pont (span 91 nap) — nap-szónak (3-m) ÉRVÉNYES,
    # het-szónak (12-m, ~365 nap várt) ELDOBVA. A verdikt a timeframe-ből LEVEZETVE (nem beírt konstans).
    df92 = lambda kif: _df_racs(kif, 92, 1)
    nap = KulcsszoTetel("hitel", "h", "szintmero", "nap")
    het = KulcsszoTetel("kórház", "e", "szintmero", "het")
    assert kulcsszavak.gyujt_egy_masodlagos(_RogzitoKliens(df92), _config([nap]), nap, _MOST, "today 3-m") is not None   # 3-m OK
    assert kulcsszavak.gyujt_egy_masodlagos(_RogzitoKliens(df92), _config([het]), het, _MOST, "today 12-m") is None      # 12-m csonka


def test_masodlagos_timeframe_mezo_kotelezo():
    # RED (1. rész): a séma (2. rész) timeframe-re kulcsol → a rekordnak KÖTELEZŐ timeframe mezője.
    from trendfigyelo.nyers_kimenet import ervenyes_masodlagos_rekord
    rek = {"kulcsszo": "hitel", "ablak_kezdet_utc": "2026-05-18T00:00:00+00:00",
           "ablak_veg_utc": "2026-08-18T00:00:00+00:00",
           "pontok": [{"idopont_utc": "2026-05-18T00:00:00+00:00", "ertek": 50, "reszleges": False}],
           "racs": "nap", "lekerdezes_utc": "2026-08-18T12:00:00+00:00"}   # NINCS timeframe
    hibak = ervenyes_masodlagos_rekord(rek)
    assert any("timeframe" in h for h in hibak)   # a hiányzó timeframe hibát ad (ma: nincs ilyen ellenőrzés → RED)


# --- Ciklus C: a másodlagos ág (szavankénti írás + csendes feladás) ---

class _MasodlagosBukoKliens:
    """szo0 sikeres df; szo1 AgFeladva (a 2. ütemezett szó blokkol)."""
    def __init__(self):
        self.tr = type("T", (), {"interest_over_time": None})()
        self.hivott = []

    def hivas(self, ag, fn, szavak, geo=None, timeframe=None, gprop=""):
        self.hivott.append(szavak[0])
        if szavak[0] == "szo1":
            raise AgFeladva(ag, ["429", "429", "429", "429"])
        return _df_masodlagos(szavak[0])

    def hivasszam(self, ag):
        return len(self.hivott)


def test_masodlagos_ag_szavankent_ir_a_blokk_elott(tmp_path):
    # 8 nap-szó, MIND never-collected (nincs nyers) → fallback config-index első 2 = szo0, szo1; a 2. (szo1) blokkol.
    c = _config([KulcsszoTetel(f"szo{i}", "d", "szintmero", "nap") for i in range(8)])
    most = _MOST   # 2026 — a df-fel kortárs (az érkezés-ellenőrzésnek nem jövőbeli)
    # minden szó 12-m gyűjtött (stale 0) → a top cellák a NEVER-collected 3-m cellák (szo0, szo1); a _df 3-m-re érvényes
    _ir_masodlagos_nyers(tmp_path, {f"szo{i}": {"today 12-m": "2026-08-18"} for i in range(8)})
    assert _cellak(c, most, tmp_path) == [("szo0", "today 3-m"), ("szo1", "today 3-m")]
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
    def hivas(self, ag, fn, szavak, geo=None, timeframe=None, gprop=""):
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


# ── esemenyjelzo (tüntetés) SZÓ-SZINTŰ mediántól-eltérés + illeszkedés (Task 2) ──

def _mp_nyers_esemeny(ertekek):
    # egy heti esemenyjelzo rekord növekvő idővel; az utolsó érték = a legfrissebb szint
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    pts = [{"idopont_utc": (t0 + timedelta(weeks=i)).isoformat(),
            "ertek": e, "reszleges": False} for i, e in enumerate(ertekek)]
    return {"kulcsszavak": {"tüntetés": [{
        "racs": "het", "timeframe": "today 12-m",
        "ablak_kezdet_utc": pts[0]["idopont_utc"],
        "ablak_veg_utc": pts[-1]["idopont_utc"], "pontok": pts}]}}


def test_masodlagos_esemenyjelzo_median_elteres():
    from trendfigyelo import regresszio
    from trendfigyelo.config import KulcsszoTetel
    # a `_config` helper (a fájl tetején) — a tüntetést esemenyjelzo-ként ismeri → _domen_tipus
    # a config-ból adja a tipus="esemenyjelzo"-t (nincs szükség tortenet-re)
    config = _config([KulcsszoTetel("tüntetés", "kozelet", "esemenyjelzo", "het")])
    nyers = _mp_nyers_esemeny([8, 8, 8, 8, 9, 8, 8, 30])   # medián 8; az utolsó (30) messze
    out = regresszio.regresszio_masodlagos_szamit(
        nyers, {"napok": []}, config, "2026-08-20T19:00:00+00:00")
    t = out["kulcsszavak"]["tüntetés"]
    assert t["szint"] == 8
    assert t["mai_szint"] == 30
    assert t["mai_elteres"] == 22.0
    assert t["szint_szokasos"] is not None
    assert t["illeszkedes"] == "felette"   # a mediántól POZITÍV irányban, a sáv fölött


def test_masodlagos_esemenyjelzo_intervallum_nem_szivargat_task1_mezoket():
    # controller-döntés: a Task-1 4 új intervallum-mezője (mai_ertek/mai_reziduum/
    # reziduum_szokasos/illeszkedes) NE szivárogjon a tüntetés MASODLAGOS *ervenyes*
    # intervallumaiba — az esemenyjelzo-nak nincs trend-mezője (§ szándékos terv).
    from trendfigyelo import regresszio
    from trendfigyelo.config import KulcsszoTetel
    config = _config([KulcsszoTetel("tüntetés", "kozelet", "esemenyjelzo", "het")])
    nyers = _mp_nyers_esemeny([8, 8, 8, 8, 9, 8, 8, 30])
    out = regresszio.regresszio_masodlagos_szamit(
        nyers, {"napok": []}, config, "2026-08-20T19:00:00+00:00")
    t = out["kulcsszavak"]["tüntetés"]
    ervenyesek = [iv for iv in t["intervallumok"].values() if iv.get("ervenyes")]
    assert ervenyesek, "a fixture-nek legalább egy ervenyes intervallumot kell adnia"
    for iv in ervenyesek:
        assert "mai_reziduum" not in iv
