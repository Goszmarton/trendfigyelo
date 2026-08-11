import csv
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd

from trendfigyelo import felkapott, futtato, json_export, kliens
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


# --- Task 3a: kategória (topics + temak) átvezetése a top_trend_struktura-ban ---

def test_top_trend_struktura_atadja_topics_temak():
    # API TrendKeyword: .topics (list[int]) + .topic_names (list[str], a topics-ból derivált)
    api = [SimpleNamespace(keyword="infláció", volume=50000, volume_growth_pct=120,
                           topics=[1, 2], topic_names=["Autos", "Sport"])]
    s = futtato.top_trend_struktura(api, [], [], _config())
    assert s[0].get("topics") == [1, 2] and s[0].get("temak") == ["Autos", "Sport"]


def test_top_trend_struktura_ures_topics_ures_lista():
    # üres kategória → [] (nem null, nem hiányzó kulcs); nincs negyedik állapot (spec 7.3)
    api = [SimpleNamespace(keyword="x", volume=100, volume_growth_pct=1, topics=[], topic_names=[])]
    s = futtato.top_trend_struktura(api, [], [], _config())
    assert s[0].get("topics") == [] and s[0].get("temak") == []


def test_ures_topics_figyelem(capsys):
    # üres topics naplózása (spec 3a): aggregált FIGYELEM a run.log-ba, a kifejezéssel
    api = [SimpleNamespace(keyword="csendes", volume=100, volume_growth_pct=1, topics=[], topic_names=[])]
    futtato.top_trend_struktura(api, [], [], _config())
    out = capsys.readouterr().out
    assert "FIGYELEM" in out and "csendes" in out


def test_topics_kulcs_mindig_jelen():
    # "mindig jelen, soha hiányzó kulcs": üres kategóriánál is JELEN a kulcs (nem csak None-érték)
    api = [SimpleNamespace(keyword="x", volume=100, volume_growth_pct=1, topics=[], topic_names=[])]
    s = futtato.top_trend_struktura(api, [], [], _config())
    assert "topics" in s[0] and "temak" in s[0]


def test_topics_attributum_nelkul():
    # RSS-ág TrendKeywordLite: NINCS topics/topic_names attribútum → getattr(...,[]) fallback,
    # nem AttributeError; a kulcs jelen, értéke [].
    lite = SimpleNamespace(keyword="rss", volume=50, volume_growth_pct=1)
    s = futtato.top_trend_struktura([lite], [], [], _config())
    assert "topics" in s[0] and s[0]["topics"] == []
    assert "temak" in s[0] and s[0]["temak"] == []


# --- D1–D4: holtverseny-kiterjesztés + tie-break + felső korlát + 0-kapu (spec §7.3, 026231a) ---
# A mai top_trend_struktura = sorted(api, key=volumen_szam, reverse=True)[:trend_idosor_max]:
# nincs rekesz-kiterjesztés, nincs trend_megjelenites_max. A VALÓBAN új viselkedés csak a
# D1-kiterjesztés és a D3-korlát → csak T1/T6/T7 RED; a többi a MÁR MEGLÉVŐ viselkedést
# kodifikáló SZÁNDÉKOSAN ZÖLD őr/diszkriminátor (a kód e körben NEM változik, hogy a RED valódi legyen).

def _tr(keyword, volume):
    """API-trend teszt-dummy: string volumen (spec §1.4), topics-szal (nincs ures-topics FIGYELEM)."""
    return SimpleNamespace(keyword=keyword, volume=volume, volume_growth_pct="1000",
                           topics=[1], topic_names=["X"])


def _cfg_trend(idosor_max, megjelenites_max=None):
    """_config() a kért trend_idosor_max-szal; a trend_megjelenites_max PÉLDÁNY-ATTRIBÚTUMKÉNT
    (a Config nem frozen, a config.py e körben érintetlen — a majdani mező helyettese)."""
    cfg = _config()
    cfg.trend_idosor_max = idosor_max
    if megjelenites_max is not None:
        cfg.trend_megjelenites_max = megjelenites_max
    return cfg


def _rss_trend(keyword, hirrel):
    """RSS-trend teszt-dummy (TrendKeywordLite-szerű): keyword + opcionális EGY hír."""
    news = [SimpleNamespace(title="c", source="f", url="u", time=None, picture="", snippet="s")] if hirrel else []
    return SimpleNamespace(keyword=keyword, news=news)


class TrendListaKliens:
    """Integrációhoz: konfigurálható api-trendlista + testreszabott rss-halmaz + idosor-df minden
    kért kifejezéshez; a kulcsszo a SorrendKemKliens érvényes alakját követi. Ági hívásszámot számol.
    rss=None → a régi viselkedés (az api első keyword-je, hír nélkül); rss=[(kw, hirrel_bool), ...] → testreszabott."""
    def __init__(self, trendek, rss=None):
        self.tr = _dummy_tr()
        self._trendek = trendek          # [(keyword, volume), ...]
        self._rss = rss                  # None → régi; [(keyword, hirrel_bool), ...] → testreszabott
        self._szam = {}
    def hivas(self, ag, fn, *a, **k):
        self._szam[ag] = self._szam.get(ag, 0) + 1
        if ag == "felkapott_api":
            return [_tr(kw, vol) for kw, vol in self._trendek]
        if ag == "felkapott_rss":
            if self._rss is None:
                return [SimpleNamespace(keyword=self._trendek[0][0], news=[])]
            return [_rss_trend(kw, hirrel) for kw, hirrel in self._rss]
        if ag == "kulcsszo":
            return _egy_szo_df("a", [30, 40], [
                datetime(2021, 1, 1, 10, tzinfo=timezone.utc),
                datetime(2021, 1, 2, 10, tzinfo=timezone.utc)], [False, True])
        if ag == "idosor":
            kif = a[0][0]                # gyujt: kliens.hivas("idosor", fn, [kif], ...)
            return _egy_szo_df(kif, [40], [datetime(2021, 1, 1, 10, tzinfo=timezone.utc)], [False])
        return []
    def hivasszam(self, ag):
        return self._szam.get(ag, 0)
    def osszes_hivas(self):
        return sum(self._szam.values())


# ── D1 — holtverseny-kiterjesztés ──────────────────────────────────────────────

def test_megjelenites_kiterjed_a_kuszob_rekeszre():
    # RED: a 2000-es küszöb-rekeszt TELJESEN beveszi → A,B,C,D,E (5), nem a mai [:3]=A,B,C.
    cfg = _cfg_trend(3)
    api = [_tr("A", "10000"), _tr("B", "5000"), _tr("C", "2000"),
           _tr("D", "2000"), _tr("E", "2000"), _tr("F", "1000")]
    s = futtato.top_trend_struktura(api, [], [], cfg)
    assert [d["kifejezes"] for d in s] == ["A", "B", "C", "D", "E"]


def test_nincs_holtverseny_pontos_hossz():
    # SZÁNDÉKOSAN ZÖLD (D1 regr.-őr): a küszöbön (2000) nincs holtverseny → pontosan
    # trend_idosor_max hosszú; a mai [:3] is ezt adja. A kiterjesztés NE aktiválódjon feleslegesen.
    cfg = _cfg_trend(3)
    api = [_tr("A", "10000"), _tr("B", "5000"), _tr("C", "2000"),
           _tr("D", "1000"), _tr("E", "500")]
    s = futtato.top_trend_struktura(api, [], [], cfg)
    assert [d["kifejezes"] for d in s] == ["A", "B", "C"]


# ── D2 — tie-break és prefix-invariáns ─────────────────────────────────────────

def test_azonos_bemenet_azonos_kimenet():
    # SZÁNDÉKOSAN ZÖLD (D2 determinizmus): a mai sorted determinisztikus. Őrzi, hogy
    # egy jövőbeli refaktor se hozzon be bemenet-függő sorrendet.
    cfg = _cfg_trend(3)
    api = [_tr("A", "2000"), _tr("B", "5000"), _tr("C", "2000"), _tr("D", "1000")]
    s1 = futtato.top_trend_struktura(api, [], [], cfg)
    s2 = futtato.top_trend_struktura(api, [], [], cfg)
    assert [d["kifejezes"] for d in s1] == [d["kifejezes"] for d in s2]


def test_tie_break_eredeti_api_pozicio():
    # SZÁNDÉKOSAN ZÖLD (D2): azonos volumennél az EREDETI API-sorrend marad (stabil sorted),
    # NEM ábécé. Az input-sorrend (zebra,alma,medve) KÜLÖNBÖZIK az ábécétől (alma,medve,zebra)
    # → diszkriminál egy jövőbeli ábécé-tie-break ellen; a mai kóddal zöld.
    cfg = _cfg_trend(3)
    api = [_tr("zebra", "2000"), _tr("alma", "2000"), _tr("medve", "2000")]
    s = futtato.top_trend_struktura(api, [], [], cfg)
    assert [d["kifejezes"] for d in s] == ["zebra", "alma", "medve"]


def test_idosor_lista_a_megjelenites_prefixe(tmp_path):
    # SZÁNDÉKOSAN ZÖLD (D2 prefix-invariáns, integrációs): a megjelenített lista azon elemei,
    # amelyeknek van idősora, a lista első trend_idosor_max eleme (PREFIX). A TÉNYLEGES
    # kimenetből (legfrissebb.json), nem mellékszámlálóból.
    # ADAT (T14-alak): a 2000-es holtverseny ÁTNYÚLIK a vágáson — base top-2 = A,Z (küszöb 2000),
    # és Y,X is 2000, tehát a GREEN után a megjelenített lista A,Z,Y,X, az idősoros A,Z (prefix).
    # MA azért zöld, mert NINCS kiterjesztés (a mai kód [:2]=A,Z-t ad, mindkettő kap idősort) —
    # NEM azért, mert az invariáns triviális. Diszkrimináció: ha egy hibás impl a két rendezést
    # szétcsúsztatná (pl. az idosor-lista ábécé szerint → A,X), az `idosorral` [A,X] lenne a
    # `megjelenitett[:2]` = [A,Z] helyett → a teszt BUKNA.
    import json
    cfg = _cfg_trend(2)
    kli = TrendListaKliens([("A", "10000"), ("Z", "2000"), ("Y", "2000"), ("X", "2000")])
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)
    futtato.futtat(cfg, kli, tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    top = json.loads((tmp_path / "docs" / "data" / "legfrissebb.json").read_text(encoding="utf-8"))["top_trendek"]
    megjelenitett = [d["kifejezes"] for d in top]
    idosorral = [d["kifejezes"] for d in top if d["idosor"]]
    assert idosorral == megjelenitett[: cfg.trend_idosor_max]


# ── D3 — felső korlát ──────────────────────────────────────────────────────────

def test_felso_korlat_vag():
    # RED: 22 trend, óriási 2000-rekesz; a korlát max(5,3)=5 → 5 elem. A mai [:3] → 3.
    cfg = _cfg_trend(3, 5)
    api = [_tr("A", "10000"), _tr("B", "5000")] + [_tr(f"C{i}", "2000") for i in range(20)]
    s = futtato.top_trend_struktura(api, [], [], cfg)
    assert [d["kifejezes"] for d in s] == ["A", "B", "C0", "C1", "C2"]


def test_felso_korlat_tie_break_dont():
    # RED: base top-2=[A,Z]; küszöb 2000; a rekeszből a korlátig (max(3,2)=3) az API-pozíció
    # szerint Z,Y marad → [A,Z,Y]. Input (Z,Y,X,W) ≠ ábécé (W,X,Y,Z) → a tie-break diszkriminál.
    # A mai [:2] → [A,Z].
    cfg = _cfg_trend(2, 3)
    api = [_tr("A", "10000"), _tr("Z", "2000"), _tr("Y", "2000"),
           _tr("X", "2000"), _tr("W", "2000")]
    s = futtato.top_trend_struktura(api, [], [], cfg)
    assert [d["kifejezes"] for d in s] == ["A", "Z", "Y"]


def test_max_korlat_nem_rovidebb_mint_idosor():
    # SZÁNDÉKOSAN ZÖLD (D3 max()): trend_idosor_max=4 > trend_megjelenites_max=2 → a tényleges
    # korlát max(2,4)=4, a lista NEM rövidül 2-re. Ma [:4]=4. Diszkriminál egy hibás impl ellen,
    # ami trend_megjelenites_max-ra (2-re) vágna.
    cfg = _cfg_trend(4, 2)
    api = [_tr("A", "10000"), _tr("B", "5000"), _tr("C", "2000"),
           _tr("D", "1000"), _tr("E", "500"), _tr("F", "200")]
    s = futtato.top_trend_struktura(api, [], [], cfg)
    assert [d["kifejezes"] for d in s] == ["A", "B", "C", "D"]


# ── D4 — 0-volumenű sáv kapuja ─────────────────────────────────────────────────

def test_nulla_kuszob_nincs_kiterjesztes():
    # SZÁNDÉKOSAN ZÖLD (D4 kapu): a küszöb-volumen 0 → a kiterjesztés ELMARAD, len marad 3.
    # Ma [:3]=3. Diszkriminál egy 0-sávba kiterjesztő hibás impl ellen (az 5-öt adna).
    cfg = _cfg_trend(3)
    api = [_tr("A", "10000"), _tr("B", "5000"),
           _tr("C", "0"), _tr("D", "0"), _tr("E", "0")]
    s = futtato.top_trend_struktura(api, [], [], cfg)
    assert [d["kifejezes"] for d in s] == ["A", "B", "C"]


def test_alap_top_n_valtozatlan_nulla_bejut():
    # SZÁNDÉKOSAN ZÖLD (D4): kevesebb nem-nulla trend, mint trend_idosor_max → a 0-volumenű
    # trendek BEJUTNAK az alap top-N-be (ma is). A D4-kapu CSAK a kiterjesztésre vonatkozik;
    # az alap top-N-t NEM módosítjuk (különben viselkedésváltozás lenne).
    cfg = _cfg_trend(5)
    api = [_tr("A", "10000"), _tr("B", "5000"), _tr("C", "2000"),
           _tr("D", "0"), _tr("E", "0")]
    s = futtato.top_trend_struktura(api, [], [], cfg)
    assert [d["kifejezes"] for d in s] == ["A", "B", "C", "D", "E"]


def test_volumen_szam_5000plus_es_hianyzo_nulla():
    # SZÁNDÉKOSAN ZÖLD (D4 premisz): a volumen_szam 0-t ad "5000+"-ra (ValueError-ág), None-ra
    # és hiányzó volume-ra; a "2000" valódi 2000 (nem-tautológ horgony). Ma is így viselkedik.
    assert felkapott.volumen_szam(SimpleNamespace(volume="5000+")) == 0
    assert felkapott.volumen_szam(SimpleNamespace(volume=None)) == 0
    assert felkapott.volumen_szam(SimpleNamespace()) == 0
    assert felkapott.volumen_szam(SimpleNamespace(volume="2000")) == 2000


# ── él-esetek: üres / rövid lista, idosor-hívásszám ────────────────────────────

def test_ures_api_lista_nem_omlik_ossze():
    # SZÁNDÉKOSAN ZÖLD (§7.5 él): üres api → üres lista, NINCS kivétel. A jövőbeli impl
    # küszöbe (a levágott lista utolsó eleme) üres listán IndexError-t dobhatna — ezt őrzi.
    cfg = _cfg_trend(3)
    s = futtato.top_trend_struktura([], [], [], cfg)
    assert s == []


def test_rovidebb_lista_mint_idosor_max():
    # SZÁNDÉKOSAN ZÖLD (off-by-one csapda): rövidebb lista, mint trend_idosor_max → a lista a
    # TÉNYLEGES hosszú. A küszöb a LEVÁGOTT lista utolsó eleme, NEM a [trend_idosor_max-1] index
    # (az egy rövid listán IndexError-t adna a jövőbeli implnél).
    cfg = _cfg_trend(3)
    api = [_tr("A", "10000"), _tr("B", "5000")]
    s = futtato.top_trend_struktura(api, [], [], cfg)
    assert [d["kifejezes"] for d in s] == ["A", "B"]
    # rövid lista VÉGÉN holtverseny → mind bent, len 3
    cfg2 = _cfg_trend(5)
    api2 = [_tr("A", "10000"), _tr("B", "2000"), _tr("C", "2000")]
    s2 = futtato.top_trend_struktura(api2, [], [], cfg2)
    assert [d["kifejezes"] for d in s2] == ["A", "B", "C"]


def test_idosor_hivasszam_nem_no_a_kiterjesztessel(tmp_path):
    # SZÁNDÉKOSAN ZÖLD (integrációs, a T5 mellé): az idosor-ág hívásszáma <= trend_idosor_max,
    # mert a gyujt a top_kifejezesek[:trend_idosor_max]-ra vág (idosorok.py:50). A megjelenítés-
    # kiterjesztés ezt NEM növelheti — közvetlen őr a plafon-ütközés ellen.
    cfg = _cfg_trend(2)
    kli = TrendListaKliens([("A", "10000"), ("B", "2000"), ("C", "2000"), ("D", "2000")])
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)
    futtato.futtat(cfg, kli, tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    assert kli.hivasszam("idosor") <= cfg.trend_idosor_max


# --- B2: folytonosság-diagnosztika a naplóban (kimaradt napi futás észlelése) ---

def _seed_index(docs_data, napok):
    import json
    napok_mappa = docs_data / "napok"
    napok_mappa.mkdir(parents=True, exist_ok=True)
    (napok_mappa / "index.json").write_text(json.dumps({"napok": napok}), encoding="utf-8")


def test_futtat_folytonossag_hiany_naploz(tmp_path):
    """Előírt index [2020-12-31], a mai nap 2021-01-02 → a napi_ir után az utolsó két dátum
    köze 2 nap → 'folytonossag;hiany;0;2021-01-01' naplósor."""
    docs_data = tmp_path / "docs" / "data"
    _seed_index(docs_data, ["2020-12-31"])
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)   # budapesti nap 2021-01-02
    futtato.futtat(_config(), SorrendKemKliens(), tmp_path / "adatok", docs_data, most=most)
    sorok = {s["ag"]: s for s in _naplo_soronkent(tmp_path / "adatok")}
    assert "folytonossag" in sorok
    assert sorok["folytonossag"]["eredmeny"] == "hiany"
    assert sorok["folytonossag"]["hivasok_szama"] == "0"
    assert sorok["folytonossag"]["hibakodok"] == "2021-01-01"


def test_futtat_folytonossag_siker_naploz(tmp_path):
    """Előírt index [2021-01-01], a mai nap 2021-01-02 → folytonos → 'folytonossag;siker;0;'
    (üres hibakodok); a heartbeat-sor MINDEN futáson ott van."""
    docs_data = tmp_path / "docs" / "data"
    _seed_index(docs_data, ["2021-01-01"])
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)
    futtato.futtat(_config(), SorrendKemKliens(), tmp_path / "adatok", docs_data, most=most)
    sorok = {s["ag"]: s for s in _naplo_soronkent(tmp_path / "adatok")}
    assert "folytonossag" in sorok
    assert sorok["folytonossag"]["eredmeny"] == "siker"
    assert sorok["folytonossag"]["hibakodok"] == ""


def test_futtat_folytonossag_serult_index_naplo_keszul(tmp_path):
    """C1: sérült index.json ('{') → a folytonosság-blokk NEM viszi el az EGÉSZ futás naplóját.
    A hat ág + folytonossag;hiba;0;JSONDecodeError kiíródik, a kód változatlan (0, mert van adat).
    (Nincs api-trend → top_trendek üres → napi_ir kimarad → a sérült index a blokkig él.)"""
    cfg = _config([KulcsszoTetel("a", "megelhetes", "szintmero")])
    docs_data = tmp_path / "docs" / "data"
    napok_mappa = docs_data / "napok"
    napok_mappa.mkdir(parents=True, exist_ok=True)
    (napok_mappa / "index.json").write_text("{", encoding="utf-8")   # sérült JSON
    most = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)
    kod = futtato.futtat(cfg, KulcsszoAdatKliens(), tmp_path / "adatok", docs_data, most=most)
    sorok = {s["ag"]: s for s in _naplo_soronkent(tmp_path / "adatok")}
    assert kod == 0                                                  # a futás NEM szállt el
    assert {"felkapott_api", "felkapott_rss", "kulcsszo", "idosor",
            "regresszio", "folytonossag"} <= set(sorok)              # mind a hat ág megvan
    assert sorok["folytonossag"]["eredmeny"] == "hiba"
    assert sorok["folytonossag"]["hibakodok"] == "JSONDecodeError"


# --- Párosítás-diagnosztika (parositas naplósor): RSS ⊆ API? — a B2-minta szerint ---
# A kód e körben ÉRINTETLEN → a `parositas` sor NEM létezik → P1-P6 és P8 mind ugyanazért RED:
# a sor hiányzik (`.get("parositas")` = None). A tartalmi diszkriminációt (küszöb-forrás, szeparátor,
# eredmeny-logika, except-ág) NEM a RED bizonyítja, hanem a KÉSŐBBI mutációs kör. A helper, amit a
# GREEN bevezet és a P8/P9 patchel: futtato.parositas_szamit (tiszta függvény).
_PAR_MOST = datetime(2021, 1, 2, 12, 0, tzinfo=timezone.utc)


def test_parositas_sor_megjelenik_heartbeat(tmp_path):
    # RED: heartbeat — a sornak MINDEN futáson meg kell jelennie. Mivel a naplo.csv-ből olvassuk,
    # a jelenléte egyben igazolja, hogy a bejegyzés a naplo_ir ELŐTT került be.
    kli = TrendListaKliens([("A", "10000"), ("B", "5000")], rss=[("A", True)])
    futtato.futtat(_cfg_trend(2), kli, tmp_path / "adatok", tmp_path / "docs" / "data", most=_PAR_MOST)
    sorok = {s["ag"]: s for s in _naplo_soronkent(tmp_path / "adatok")}
    assert "parositas" in sorok


def test_parositas_teljes_egyezes_siker(tmp_path):
    # RED: minden RSS-keyword az api-halmazban → siker, üres nem_egyezok-rész (nincs lógó pipe).
    kli = TrendListaKliens([("A", "10000"), ("B", "5000"), ("C", "2000")],
                           rss=[("A", True), ("B", True), ("C", True)])
    futtato.futtat(_cfg_trend(3), kli, tmp_path / "adatok", tmp_path / "docs" / "data", most=_PAR_MOST)
    sorok = {s["ag"]: s for s in _naplo_soronkent(tmp_path / "adatok")}
    assert sorok.get("parositas", {}).get("eredmeny") == "siker"
    assert sorok.get("parositas", {}).get("hibakodok") == "3/3/3"


def test_parositas_reszleges_hiany_pipe(tmp_path):
    # RED: két RSS-trend nincs az api-ban → hiany, a nevek PIPE-pal (a rss_trendek sorrendjében).
    kli = TrendListaKliens([("A", "10000"), ("B", "5000")],
                           rss=[("A", True), ("napelem", True), ("kórház", True)])
    futtato.futtat(_cfg_trend(2), kli, tmp_path / "adatok", tmp_path / "docs" / "data", most=_PAR_MOST)
    sorok = {s["ag"]: s for s in _naplo_soronkent(tmp_path / "adatok")}
    assert sorok.get("parositas", {}).get("eredmeny") == "hiany"
    assert sorok.get("parositas", {}).get("hibakodok") == "3/1/1|napelem|kórház"


def test_parositas_hir_nelkuli_rss_beleszamit_rss_db(tmp_path):
    # RED + a hir_sorok-CSAPDA diszkriminátora: B benne van az RSS-ben, de NINCS híre. Az rss_db-nek
    # 2-nek kell lennie (a rss_trendek-ből), NEM 1-nek (amit a hir_sorok adna). megjelenitett_hirrel=1
    # (B-nek nincs híre) → a két szám KÜLÖNBÖZIK, tehát nem esik véletlenül egybe.
    kli = TrendListaKliens([("A", "10000"), ("B", "5000")], rss=[("A", True), ("B", False)])
    futtato.futtat(_cfg_trend(2), kli, tmp_path / "adatok", tmp_path / "docs" / "data", most=_PAR_MOST)
    sorok = {s["ag"]: s for s in _naplo_soronkent(tmp_path / "adatok")}
    assert sorok.get("parositas", {}).get("hibakodok") == "2/2/1"


def test_parositas_vesszos_kifejezes_ep_es_pipe_visszabonthato(tmp_path):
    # RED: vesszőt tartalmazó nem-egyező név → a CSV cella ép (a , nem elválasztó), és a pipe-bontás
    # egyértelmű (a vessző a néven belül marad).
    kli = TrendListaKliens([("A", "10000")], rss=[("A", True), ("eladó lakás, olcsón", True)])
    futtato.futtat(_cfg_trend(1), kli, tmp_path / "adatok", tmp_path / "docs" / "data", most=_PAR_MOST)
    sorok = {s["ag"]: s for s in _naplo_soronkent(tmp_path / "adatok")}
    hk = sorok.get("parositas", {}).get("hibakodok")
    assert hk == "2/1/1|eladó lakás, olcsón"
    assert (hk.split("|")[1:] if hk else None) == ["eladó lakás, olcsón"]


def test_parositas_ures_rss_nulla_per_nulla(tmp_path):
    # RED: üres rss (az ág üreset ad) → 0/0/0, siker (0==0), nem omlik össze.
    kli = TrendListaKliens([("A", "10000"), ("B", "5000")], rss=[])
    futtato.futtat(_cfg_trend(2), kli, tmp_path / "adatok", tmp_path / "docs" / "data", most=_PAR_MOST)
    sorok = {s["ag"]: s for s in _naplo_soronkent(tmp_path / "adatok")}
    assert sorok.get("parositas", {}).get("eredmeny") == "siker"
    assert sorok.get("parositas", {}).get("hibakodok") == "0/0/0"


def test_naplo_pipe_es_vesszos_hibakodok_ep_csv(tmp_path):
    # SZÁNDÉKOSAN ZÖLD: a napló-réteg (csv, ;-delimiter, QUOTE_MINIMAL) a |+, tartalmú cellát ÉPEN
    # körbejárja — ez a D1-premissza (pipe-szeparátor + vessző-biztos név), a parositas-blokktól
    # függetlenül igaz ma is (mint a B2 volumen_szam-karakterizáció).
    from trendfigyelo import naplo
    adatok = tmp_path / "adatok"
    adatok.mkdir()
    naplo.naplo_ir(adatok, "2021-01-02T00:00:00+00:00", [
        {"ag": "parositas", "eredmeny": "hiany", "hivasok_szama": 0,
         "hibakodok": "2/1/1|eladó lakás, olcsón|benzin ár"}], 2000)
    sorok = {s["ag"]: s for s in _naplo_soronkent(adatok)}
    hk = sorok["parositas"]["hibakodok"]
    assert hk == "2/1/1|eladó lakás, olcsón|benzin ár"          # egy ép cella (a , nem törte szét)
    assert hk.split("|")[1:] == ["eladó lakás, olcsón", "benzin ár"]   # pipe-bontás egyértelmű


def test_parositas_hiba_ag_naplo_keszul(tmp_path, monkeypatch):
    # RED: a parositas dedikált helperét kivétel-dobásra patcheljük (a védett except-et NEM kerüli meg).
    # raising=False: stub-RED-ben a helper még nincs, a futtat nem hívja → a patch inert → nincs
    # parositas sor → RED (mint P1-P6). GREEN után: a helper bukik → 'parositas;hiba;0;ValueError'.
    def _dob(*a, **k):
        raise ValueError("teszt")
    monkeypatch.setattr(futtato, "parositas_szamit", _dob, raising=False)
    kli = TrendListaKliens([("A", "10000")], rss=[("A", True)])
    futtato.futtat(_cfg_trend(1), kli, tmp_path / "adatok", tmp_path / "docs" / "data", most=_PAR_MOST)
    sorok = {s["ag"]: s for s in _naplo_soronkent(tmp_path / "adatok")}
    assert sorok.get("parositas", {}).get("eredmeny") == "hiba"
    assert sorok.get("parositas", {}).get("hibakodok") == "ValueError"


def test_parositas_hiba_nem_blokkolja_az_adatmentest(tmp_path, monkeypatch):
    # SZÁNDÉKOSAN ZÖLD (§0.1/9): ugyanaz a bukó patch, mint P8. A parositas hibája NEM viheti el az
    # adatot: exit-kód változatlan, CSV/JSON kiírva, a hat meglévő ág naplózva. A parositas sort NEM
    # assertáljuk (azt P8). Ma trivi (nincs blokk, ami bukna); GREEN után éles.
    def _dob(*a, **k):
        raise ValueError("teszt")
    monkeypatch.setattr(futtato, "parositas_szamit", _dob, raising=False)
    docs_data = tmp_path / "docs" / "data"
    kli = TrendListaKliens([("A", "10000"), ("B", "5000")], rss=[("A", True)])
    kod = futtato.futtat(_cfg_trend(2), kli, tmp_path / "adatok", docs_data, most=_PAR_MOST)
    sorok = {s["ag"]: s for s in _naplo_soronkent(tmp_path / "adatok")}
    assert kod == 0
    assert (docs_data / "legfrissebb.json").exists()
    assert (tmp_path / "adatok" / "naplo.csv").exists()
    for ag in ("felkapott_api", "felkapott_rss", "kulcsszo", "idosor", "regresszio", "folytonossag"):
        assert ag in sorok


# --- Task 3b: kategoriak.json bekötése a futtatóba (védett, nem néma) ---

class KategoriaKliens:
    """felkapott_api ad EGY trendet topics+topic_names-szel → top_trend_struktura valódi
    temak-os trendet gyárt → napi_ir kiírja a mai napok/*.json-t → kategoriak_ir tükrözi.
    A kategória CSAK az API-ág TrendKeyword-jén van (a felkapott_rss nem ad kategóriát)."""
    def __init__(self):
        self.tr = _dummy_tr()
    def hivas(self, ag, fn, *a, **k):
        if ag == "felkapott_api":
            return [SimpleNamespace(keyword="infláció", volume=50000, volume_growth_pct=120,
                                    topics=[1], topic_names=["Sports"])]
        return []
    def hivasszam(self, ag):
        return 1
    def osszes_hivas(self):
        return 4


def test_kategoriak_json_letrejon_a_futasban(tmp_path):
    # a felkapott_api egy trendet ad topics+topic_names-szel → top_trend_struktura temak-os
    # trendet gyárt → napi_ir ír napok/*.json fájlt → kategoriak_ir azt tükrözi
    most = datetime(2021, 1, 4, 12, 0, tzinfo=timezone.utc)
    futtato.futtat(_config(), KategoriaKliens(),
                   tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    kat = tmp_path / "docs" / "data" / "kategoriak.json"
    assert kat.exists()
    adat = json.loads(kat.read_text(encoding="utf-8"))
    # valódi diszkriminátor: a tükör a mai napi adatot fogja meg (napi_ir UTÁN)
    assert adat["napok"], "a napok lista nem lehet üres — a tükör a napi adatot fogja meg"
    nap = next(n for n in adat["napok"] if n["nap"] == "2021-01-04")
    assert nap["merve"] is True
    assert nap["kategoriak"]["Sports"] == 1
    sorok = _naplo_soronkent(tmp_path / "adatok")
    assert {s["ag"]: s["eredmeny"] for s in sorok}["kategoriak"] == "siker"


def test_kategoriak_hiba_nem_blokkol(tmp_path, monkeypatch):
    # a származtatott ág hibája SOHA nem viheti el az adatmentést vagy az exit-kódot (finding 6)
    def _dob(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(futtato.kategoriak, "kategoriak_ir", _dob)
    most = datetime(2021, 1, 4, 12, 0, tzinfo=timezone.utc)
    kod = futtato.futtat(_config(), KulcsszoAdatKliens(),
                         tmp_path / "adatok", tmp_path / "docs" / "data", most=most)
    assert kod == 0                                                        # exit-kód érintetlen
    assert (tmp_path / "docs" / "data" / "legfrissebb.json").exists()      # adatmentés megvan
    sorok = _naplo_soronkent(tmp_path / "adatok")
    assert {s["ag"]: s["eredmeny"] for s in sorok}["kategoriak"] == "hiba"
