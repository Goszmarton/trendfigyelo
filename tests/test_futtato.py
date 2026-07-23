import csv
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from trendfigyelo import futtato, json_export, kliens
from trendfigyelo.config import Config


def _config():
    return Config(
        geo="HU", nyelv="hu", idoablak_orak=24, idosor_idokeret="now 1-d",
        referenciaszo="időjárás", alap_keses_mp=3.0, szoras_mp=(3, 7),
        max_probak=4, backoff_mp=[30, 120, 480], trend_idosor_max=2, proxy=None,
        kulcsszavak={"g": ["a"]},
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
    """felkapott_rss ad adatot; a kulcsszo-ág sima (nem 429) hibát dob köteget.

    A kulcsszavak.gyujt ezt kötegenként lenyeli → [] a kulcsszó-eredmény.
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
    # jó bejegyzés magvetése
    jo_pontok = [{"kulcsszo": "a", "csoport": "g", "idopont_utc": "2021-01-01T10:00:00+00:00",
                  "nyers_ertek": 50, "normalizalt_ertek": 50}]
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
