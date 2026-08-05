import csv
from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd

from trendfigyelo import futtato, json_export, kliens
from trendfigyelo.config import Config, KulcsszoTetel


def _config(kulcsszavak=None):
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        alap_keses_mp=3.0, szoras_mp=(3, 7),
        max_probak=4, backoff_mp=[30, 120, 480], trend_idosor_max=2, proxy=None,
        kulcsszavak=kulcsszavak or [KulcsszoTetel("a", "g", "szintmero")],
    )


def _dummy_tr():
    """Olyan tr, amelynek megvannak a metódusnevei (a fake hivas nem hívja őket)."""
    return SimpleNamespace(trending_now=None, trending_now_by_rss=None,
                           interest_over_time=None)


def _naplo_soronkent(adatok_mappa):
    """A naplo.csv-t {ag: eredmeny} párokra bontja (utolsó futás sorai)."""
    fajl = adatok_mappa / "naplo.csv"
    with fajl.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def test_top_trend_struktura_parositja_az_idosort_es_hirt():
    api = [SimpleNamespace(keyword="infláció", volume=50000, volume_growth_pct=120)]
    idosorok = [{"kifejezes": "infláció", "idopont_utc": "2021-01-01T10:00:00+00:00", "ertek": 40}]
    hir = SimpleNamespace(title="Cím", source="Index", url="http://x", time=None,
                          picture="", snippet="")
    rss = [SimpleNamespace(keyword="infláció", news=[hir])]
    struktura = futtato.top_trend_struktura(api, idosorok, rss, _config())
    assert struktura[0]["kifejezes"] == "infláció"
    assert struktura[0]["idosor"] == [{"idopont_utc": "2021-01-01T10:00:00+00:00", "ertek": 40}]
    assert struktura[0]["hirek"][0]["hir_cim"] == "Cím"


class Mindig429Kliens:
    """Minden ág AgFeladva-t dob → teljes blokkolás szimulálása."""
    def __init__(self):
        self.tr = object()
    def hivas(self, ag, fn, *a, **k):
        raise kliens.AgFeladva(ag, ["429", "429", "429", "429"])
    def hivasszam(self, ag):
        return 4
    def osszes_hivas(self):
        return 8


def test_teljes_blokkolas_nem_nulla_kilepesi_kod(tmp_path):
    most = datetime(2021, 1, 1, 12, 0, tzinfo=timezone.utc)
    kod = futtato.futtat(_config(), Mindig429Kliens(),
                         tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    assert kod == 1
    # a napló akkor is elkészül
    assert (tmp_path / "adatok" / "naplo.csv").exists()


class Szamlalo429Kliens:
    """Az ELSŐ hívás AgFeladva-t dob; számolja a hívásokat."""
    def __init__(self):
        self.tr = _dummy_tr()
        self.hivasok = 0
    def hivas(self, ag, fn, *a, **k):
        self.hivasok += 1
        raise kliens.AgFeladva(ag, ["429", "429", "429", "429"])
    def hivasszam(self, ag):
        return 4
    def osszes_hivas(self):
        return self.hivasok


def test_teljes_blokkolas_egyetlen_hivas_utan_leall(tmp_path):
    """(a) Az első ág blokkol → egyetlen hívás, a többi ág kimarad."""
    most = datetime(2021, 1, 1, 12, 0, tzinfo=timezone.utc)
    kli = Szamlalo429Kliens()
    kod = futtato.futtat(_config(), kli,
                         tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    assert kod == 1
    # pontosan egyszer hívtuk a Google-t: nem indult további ág
    assert kli.hivasok == 1
    sorok = _naplo_soronkent(tmp_path / "adatok")
    eredmenyek = {s["ag"]: s["eredmeny"] for s in sorok}
    assert eredmenyek["felkapott_api"] == "blokkolva"
    # a részleges adat és a napló ekkor is kiíródik
    assert (tmp_path / "adatok" / "naplo.csv").exists()
    assert (tmp_path / "docs" / "data" / "legfrissebb.json").exists()


class UresKulcsszoKliens:
    """felkapott_rss ad adatot; a kulcsszo-ág sima (nem 429) hibát dob szavanként.

    A kulcsszavak.gyujt ezt szavanként lenyeli → [] a kulcsszó-eredmény.
    """
    def __init__(self):
        self.tr = _dummy_tr()
        self.szamlalok = {}
    def hivas(self, ag, fn, *a, **k):
        self.szamlalok[ag] = self.szamlalok.get(ag, 0) + 1
        if ag == "felkapott_rss":
            hir = SimpleNamespace(title="Cím", source="Index", url="http://x",
                                  time=None, picture="", snippet="")
            return [SimpleNamespace(keyword="infláció", volume=1000, trend_keywords=[],
                                    started=None, picture="", picture_source="",
                                    news=[hir])]
        if ag == "kulcsszo":
            raise RuntimeError("váratlan kulcsszó-hiba")
        return []
    def hivasszam(self, ag):
        return self.szamlalok.get(ag, 0)
    def osszes_hivas(self):
        return sum(self.szamlalok.values())


def test_ures_kulcsszo_nem_irja_felul_a_tortenetet(tmp_path):
    """Üres kulcsszó-adat nem törölheti a nap meglévő tortenet-bejegyzését."""
    import json
    most = datetime(2021, 1, 1, 12, 0, tzinfo=timezone.utc)
    docs_data = tmp_path / "docs" / "data"
    nap_iso = "2021-01-01"
    # jó bejegyzés magvetése (új pont-alak: domen/nyers_ertek)
    jo_pontok = [{"kulcsszo": "a", "domen": "g", "tipus": "szintmero",
                  "idopont_utc": "2021-01-01T10:00:00+00:00", "nyers_ertek": 50}]
    json_export.tortenet_frissit(docs_data, nap_iso, jo_pontok)

    kod = futtato.futtat(_config(), UresKulcsszoKliens(),
                         tmp_path / "adatok", docs_data, most=most)
    assert kod == 0
    adat = json.loads((docs_data / "tortenet.json").read_text(encoding="utf-8"))
    nap = next(b for b in adat["napok"] if b["nap"] == nap_iso)
    assert nap["kulcsszavak"], "a nap kulcsszó-bejegyzése nem lehet üres"


class ReszlegesKliens:
    """felkapott_api sima (nem 429) hibát dob, a felkapott_rss adatot ad."""
    def __init__(self):
        self.tr = _dummy_tr()
        self.szamlalok = {}
    def hivas(self, ag, fn, *a, **k):
        self.szamlalok[ag] = self.szamlalok.get(ag, 0) + 1
        if ag == "felkapott_api":
            raise RuntimeError("váratlan API-hiba")
        if ag == "felkapott_rss":
            hir = SimpleNamespace(title="Cím", source="Index", url="http://x",
                                  time=None, picture="", snippet="")
            return [SimpleNamespace(keyword="infláció", volume=1000, trend_keywords=[],
                                    started=None, picture="", picture_source="",
                                    news=[hir])]
        return []
    def hivasszam(self, ag):
        return self.szamlalok.get(ag, 0)
    def osszes_hivas(self):
        return sum(self.szamlalok.values())


def test_reszleges_siker_nulla_kilepesi_kod(tmp_path):
    """(b) Egy ág sima hibát dob, más ág ad adatot → kilépési kód 0, 'hiba' a naplóban."""
    most = datetime(2021, 1, 1, 12, 0, tzinfo=timezone.utc)
    kod = futtato.futtat(_config(), ReszlegesKliens(),
                         tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    assert kod == 0
    sorok = _naplo_soronkent(tmp_path / "adatok")
    eredmenyek = {s["ag"]: s["eredmeny"] for s in sorok}
    # (c) ágsoronkénti napló-ellenőrzés
    assert eredmenyek["felkapott_api"] == "hiba"
    assert eredmenyek["felkapott_rss"] == "siker"
    assert eredmenyek["idosor"] == "siker"
    assert eredmenyek["kulcsszo"] == "siker"


def test_tervezett_hivasszam_szolo():
    c = _config()  # trend_idosor_max=2, 1 kulcsszó → SZÓLÓ: 1 hívás
    assert futtato.tervezett_hivasszam(c) == 2 + 2 + 1  # api+rss + idosor + 1 szó = 5


def test_tervezett_hivasszam_teljes_config():
    c = Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        alap_keses_mp=3.0, szoras_mp=(3, 7),
        max_probak=4, backoff_mp=[30, 120, 480], trend_idosor_max=15, proxy=None,
        kulcsszavak=[KulcsszoTetel(f"szo{i}", "d", "szintmero") for i in range(13)],
    )
    # szóló: szavankénti egy hívás → CONFIGBÓL származó elvárás (a lista változásakor nem törik)
    assert futtato.tervezett_hivasszam(c) == 2 + c.trend_idosor_max + len(c.osszes_kulcsszo())
    assert futtato.tervezett_hivasszam(c) == 2 + 15 + 13  # konkrét pin: 30


def _egy_szo_df(oszlop, ertekek, idopontok, reszleges):
    idx = pd.to_datetime(idopontok)
    return pd.DataFrame({oszlop: ertekek, "isPartial": reszleges}, index=idx)


class KulcsszoAdatKliens:
    """felkapott_rss ad egy trendet; a kulcsszo-ág egy-oszlopos 7-d DataFrame-et ad (horgony nélkül)."""
    def __init__(self):
        self.tr = _dummy_tr()
    def hivas(self, ag, fn, *a, **k):
        if ag == "felkapott_rss":
            return [SimpleNamespace(keyword="benzinár", news=[])]
        if ag == "kulcsszo":
            return _egy_szo_df("a", [30, 40], [
                datetime(2021, 1, 1, 10, tzinfo=timezone.utc),   # utolsó teljes nap
                datetime(2021, 1, 2, 10, tzinfo=timezone.utc),   # mai (részleges)
            ], [False, True])
        return []
    def hivasszam(self, ag):
        return 1
    def osszes_hivas(self):
        return 4


class KulcsszoHianyzoNapokKliens:
    """3 teljes nap (01-01,01-02,01-03) + csonka mai (01-04) egy 7-d ablakban;
    egy-oszlopos DataFrame (horgony nélkül). A 429-önjavítás teszteléséhez."""
    def __init__(self):
        self.tr = _dummy_tr()
    def hivas(self, ag, fn, *a, **k):
        if ag == "felkapott_rss":
            return [SimpleNamespace(keyword="benzinár", news=[])]
        if ag == "kulcsszo":
            return _egy_szo_df("a", [30, 40, 50, 60], [
                datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
                datetime(2021, 1, 2, 10, tzinfo=timezone.utc),
                datetime(2021, 1, 3, 10, tzinfo=timezone.utc),
                datetime(2021, 1, 4, 9, tzinfo=timezone.utc),   # mai (részleges)
            ], [False, False, False, True])
        return []
    def hivasszam(self, ag):
        return 1
    def osszes_hivas(self):
        return 4


def test_tortenet_a_valos_adatnapra_kerul(tmp_path):
    import json
    cfg = _config([KulcsszoTetel("a", "megelhetes", "szintmero")])
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)  # mai budapesti nap 2021-01-02
    futtato.futtat(cfg, KulcsszoAdatKliens(),
                   tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    tortenet = json.loads((tmp_path / "docs" / "data" / "tortenet.json").read_text(encoding="utf-8"))
    napok = [b["nap"] for b in tortenet["napok"]]
    assert napok == ["2021-01-01"]  # az utolsó teljes nap, NEM a futás napja (2021-01-02)


# --- Task 5: ágsorrend (kulcsszo az idosor ELŐTT) ---

class SorrendKemKliens:
    """Rögzíti az ágak hívási sorrendjét; áganként érvényes alakú adatot ad."""
    def __init__(self):
        self.tr = _dummy_tr()
        self.sorrend = []
    def hivas(self, ag, fn, *a, **k):
        self.sorrend.append(ag)
        if ag == "felkapott_api":
            return [SimpleNamespace(keyword="infláció", volume=50000, volume_growth_pct=10)]
        if ag == "felkapott_rss":
            return [SimpleNamespace(keyword="infláció", news=[])]
        if ag == "kulcsszo":
            return _egy_szo_df("a", [30, 40], [
                datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
                datetime(2021, 1, 2, 10, tzinfo=timezone.utc),
            ], [False, True])
        if ag == "idosor":
            return _egy_szo_df("infláció", [40], [
                datetime(2021, 1, 1, 10, tzinfo=timezone.utc)], [False])
        return []
    def hivasszam(self, ag):
        return self.sorrend.count(ag)
    def osszes_hivas(self):
        return len(self.sorrend)
    def elso_index(self, ag):
        return self.sorrend.index(ag)


def test_kulcsszo_az_idosor_elott_fut(tmp_path):
    """A kulcsszo-ág első hívása megelőzi az idosor-ág első hívását."""
    kem = SorrendKemKliens()
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)
    futtato.futtat(_config(), kem, tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    assert kem.elso_index("kulcsszo") < kem.elso_index("idosor")


def test_agak_konstans_a_vegrehajtasi_sorrenddel_egyezik():
    """Az AGAK block-stop kihagyás-jelölő sorrendje = a valós végrehajtási sorrend."""
    assert futtato.AGAK == ["felkapott_api", "felkapott_rss", "kulcsszo", "idosor"]


class IdosorBlokkolKliens:
    """Az 'idosor' ág 429-cel kimerül; a többi ág (a kulcsszo is) ad adatot."""
    def __init__(self):
        self.tr = _dummy_tr()
        self.szamlalok = {}
    def hivas(self, ag, fn, *a, **k):
        self.szamlalok[ag] = self.szamlalok.get(ag, 0) + 1
        if ag == "idosor":
            raise kliens.AgFeladva("idosor", ["429", "429", "429", "429"])
        if ag == "felkapott_api":
            return [SimpleNamespace(keyword="infláció", volume=50000, volume_growth_pct=10)]
        if ag == "felkapott_rss":
            return [SimpleNamespace(keyword="infláció", news=[])]
        if ag == "kulcsszo":
            return _egy_szo_df("a", [30, 40], [
                datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
                datetime(2021, 1, 2, 10, tzinfo=timezone.utc),
            ], [False, True])
        return []
    def hivasszam(self, ag):
        return self.szamlalok.get(ag, 0)
    def osszes_hivas(self):
        return sum(self.szamlalok.values())


def test_idosor_blokk_utan_a_kulcsszo_mar_megvan(tmp_path):
    """Block-napon az idosor blokkol, de a kulcsszo már lefutott (nem 'kihagyva')."""
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)
    futtato.futtat(_config(), IdosorBlokkolKliens(),
                   tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    eredmeny = {s["ag"]: s["eredmeny"] for s in _naplo_soronkent(tmp_path / "adatok")}
    assert eredmeny["kulcsszo"] == "siker"       # már lefutott az idosor előtt
    assert eredmeny["idosor"] == "blokkolva"     # a régi sorrenden a kulcsszo lenne "kihagyva"


def test_futtato_visszapotolja_a_kihagyott_kulcsszo_napot(tmp_path):
    """Két egymást követő kihagyott nap (01-01, 01-02) visszapótlása a 7-d ablakból;
    a tortenet-ben csak az utolsó teljes nap (01-03) volt meg. A visszapótlást a
    gyujt napi_pontok + tortenet_frissit_napok (insert-if-absent) végzi."""
    import json
    cfg = _config([KulcsszoTetel("a", "megelhetes", "szintmero")])
    docs_data = tmp_path / "docs" / "data"
    # magvetés: csak az utolsó teljes nap (01-03) van meg; 01-01 és 01-02 kimaradt
    json_export.tortenet_frissit(docs_data, "2021-01-03", [
        {"kulcsszo": "a", "domen": "megelhetes", "tipus": "szintmero", "nyers_ertek": 30}])
    most = datetime(2021, 1, 4, 12, 0, tzinfo=timezone.utc)  # mai=01-04 → utolsó teljes 01-03
    futtato.futtat(cfg, KulcsszoHianyzoNapokKliens(),
                   tmp_path / "adatok", docs_data, most=most)
    tortenet = json.loads((docs_data / "tortenet.json").read_text(encoding="utf-8"))
    napok = sorted(b["nap"] for b in tortenet["napok"])
    assert napok == ["2021-01-01", "2021-01-02", "2021-01-03"]


# --- Task 6: nyers gördülő kimenet bekötése ---

def test_futtato_kiirja_a_nyers_gordulo_fajlt(tmp_path):
    """A kulcsszo-ág nyers_sorozatait az ir_gordulo a kulcsszo_nyers.json-ba írja,
    minden rekord átmegy a Task 3 szerződésen."""
    import json
    from trendfigyelo.nyers_kimenet import ervenyes_nyers_rekord
    cfg = _config([KulcsszoTetel("a", "megelhetes", "szintmero")])
    docs_data = tmp_path / "docs" / "data"
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)
    futtato.futtat(cfg, KulcsszoAdatKliens(), tmp_path / "adatok", docs_data, most=most)
    fajl = docs_data / "kulcsszo_nyers.json"
    assert fajl.exists()
    adat = json.loads(fajl.read_text(encoding="utf-8"))
    assert "a" in adat["kulcsszavak"]
    for rek in adat["kulcsszavak"]["a"]:
        assert ervenyes_nyers_rekord(rek) == []


def test_futtato_ures_kulcsszo_nem_ir_nyers_fajlt(tmp_path):
    """Üres kulcsszó-eredmény (minden szó hibázott) NE hozzon létre üres nyers fájlt."""
    docs_data = tmp_path / "docs" / "data"
    most = datetime(2021, 1, 1, 12, 0, tzinfo=timezone.utc)
    futtato.futtat(_config(), UresKulcsszoKliens(), tmp_path / "adatok", docs_data, most=most)
    assert not (docs_data / "kulcsszo_nyers.json").exists()


# --- hívás-plafon drótozás (E): a main a Kliensnek tervezett_hivasszam*max_probak-ot ad ---

def test_main_beallitja_a_hivas_plafont(monkeypatch):
    """A main a kliens hívás-plafonját a config-jóslatra állítja: tervezett*max_probak (=120).
    A Kliens-t és a futtat-ot elfogjuk, hogy ne induljon éles futás/FS-írás."""
    from trendfigyelo.config import betolt
    rogzitett = {}

    def recorder(config, *a, **k):
        rogzitett["plafon"] = k.get("plafon")
        return object()

    monkeypatch.setattr(futtato, "Kliens", recorder)
    monkeypatch.setattr(futtato, "futtat", lambda *a, **k: 0)
    futtato.main()
    cfg = betolt()
    vart = futtato.tervezett_hivasszam(cfg) * cfg.max_probak
    # Csak a DRÓTOZÁST asszertáljuk (tervezett * max_probak), config-agnosztikusan: a
    # kulcsszólista a 6.2 szerint változhat, ezért NEM pinneljük a 120-at az élő confighoz.
    # (Az aritmetikai pin — 2+15+13=30 — a test_tervezett_hivasszam_teljes_config-ban él,
    # szintetikus configgal; a * max_probak szorzót ez a == vart fogja.)
    assert rogzitett["plafon"] == vart


# --- Task 9a wiring: a regresszió védett bekötése (nem blokkol, nem néma) ---

def _naplo_agonkent(adatok_mappa):
    return {s["ag"]: s for s in _naplo_soronkent(adatok_mappa)}


def test_futtato_kiirja_a_regressziot(tmp_path):
    """Normál futás: kulcsszo_regresszio.json kiírva, napló 'regresszio;siker;0;',
    és a szamitva_utc == a naplósor futas_ido_utc (ugyanaz a letoltve)."""
    import json
    cfg = _config([KulcsszoTetel("a", "megelhetes", "szintmero")])
    docs_data = tmp_path / "docs" / "data"
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)
    futtato.futtat(cfg, KulcsszoAdatKliens(), tmp_path / "adatok", docs_data, most=most)
    fajl = docs_data / "kulcsszo_regresszio.json"
    assert fajl.exists()
    adat = json.loads(fajl.read_text(encoding="utf-8"))
    assert "a" in adat["kulcsszavak"] and "intervallumok" in adat["kulcsszavak"]["a"]
    sorok = _naplo_agonkent(tmp_path / "adatok")
    assert "regresszio" in sorok
    assert sorok["regresszio"]["eredmeny"] == "siker" and sorok["regresszio"]["hivasok_szama"] == "0"
    assert adat["szamitva_utc"] == sorok["regresszio"]["futas_ido_utc"]


def test_regresszio_hiba_nem_blokkol(tmp_path, monkeypatch, capsys):
    """A regresszió-hiba NEM viszi el az exit-kódot/adatmentést; 'regresszio;hiba;0;KeyError'
    a naplóba, FIGYELEM a run.log-ba."""
    def _dob(*a, **k):
        raise KeyError("bumm")
    monkeypatch.setattr("trendfigyelo.regresszio.regresszio_szamit", _dob)
    cfg = _config([KulcsszoTetel("a", "megelhetes", "szintmero")])
    docs_data = tmp_path / "docs" / "data"
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)
    kod = futtato.futtat(cfg, KulcsszoAdatKliens(), tmp_path / "adatok", docs_data, most=most)
    assert kod == 0                                              # van adat → 0, a hiba nem viszi el
    assert (docs_data / "kulcsszo_nyers.json").exists()          # az adatmentés megtörtént
    assert not (docs_data / "kulcsszo_regresszio.json").exists()  # a regresszió nem írt
    sorok = _naplo_agonkent(tmp_path / "adatok")
    assert "regresszio" in sorok
    assert sorok["regresszio"]["eredmeny"] == "hiba"
    assert sorok["regresszio"]["hibakodok"] == "KeyError"
    assert "FIGYELEM" in capsys.readouterr().out


def test_regresszio_siker_naplo_sor(tmp_path):
    """Sikeres futásnál is van naplósor — a HIÁNYZÓ sor önmagában diagnosztikai jel."""
    cfg = _config([KulcsszoTetel("a", "megelhetes", "szintmero")])
    docs_data = tmp_path / "docs" / "data"
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)
    futtato.futtat(cfg, KulcsszoAdatKliens(), tmp_path / "adatok", docs_data, most=most)
    sorok = _naplo_agonkent(tmp_path / "adatok")
    assert "regresszio" in sorok and sorok["regresszio"]["eredmeny"] == "siker"


def test_regresszio_kihagyva_ha_nincs_nyers(tmp_path):
    """Nincs kulcsszo_nyers.json (nincs bemenet) → 'kihagyva', NEM 'hiba'; nincs crash."""
    docs_data = tmp_path / "docs" / "data"
    most = datetime(2021, 1, 1, 12, 0, tzinfo=timezone.utc)
    kod = futtato.futtat(_config(), UresKulcsszoKliens(), tmp_path / "adatok", docs_data, most=most)
    assert not (docs_data / "kulcsszo_regresszio.json").exists()
    sorok = _naplo_agonkent(tmp_path / "adatok")
    assert "regresszio" in sorok and sorok["regresszio"]["eredmeny"] == "kihagyva"
