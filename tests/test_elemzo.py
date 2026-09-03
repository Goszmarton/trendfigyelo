from trendfigyelo import elemzo


def _regresszio_egy_szo(irany, meredekseg, ervenyes, mai):
    return {
        "kulcsszavak": {
            "állás": {
                "domen": "munkaeropiac", "tipus": "szintmero", "racs": "ora",
                "intervallumok": {
                    "1_het": {
                        "ervenyes": ervenyes, "irany": irany,
                        "meredekseg_nap": meredekseg, "mai_ertek": mai,
                        "ablak_veg_utc": "2026-08-22T18:00:00+00:00",
                    }
                },
            }
        }
    }


def test_kulcsszo_szamok_a_regresszio_1_het_intervallumbol():
    adatok = {
        "regresszio": _regresszio_egy_szo("emelkedik", 1.23, True, 42.0),
        "tortenet": {"napok": [{"nap": "2026-08-22",
                                "kulcsszavak": [{"kulcsszo": "állás", "atlag": 25.0, "csucs": 100.0}]}]},
        "legfrissebb": {"top_trendek": []},
        "napok_trendek": {},
    }
    payload = elemzo.epit_payload(adatok)
    szamok = payload["kulcsszavak"]["szamok"]
    assert len(szamok) == 1
    szo = szamok[0]
    assert szo["szo"] == "állás"
    assert szo["irany"] == "emelkedik"
    assert szo["meredekseg"] == 1.23
    assert szo["ervenyes"] is True
    assert szo["mai_ertek"] == 42.0
    assert szo["csucs"] == 100.0
    assert szo["atlag"] == 25.0


def test_felkapott_top_es_gordulo_het():
    adatok = {
        "regresszio": {"kulcsszavak": {}},
        "tortenet": {"napok": []},
        "legfrissebb": {"top_trendek": [
            {"kifejezes": "viharos szél", "volumen": "50000", "novekedes_pct": "1000", "temak": ["Other"]},
        ]},
        "napok_trendek": {
            "2026-08-21": [{"kifejezes": "eső", "volumen": "20000", "temak": ["Weather"]},
                           {"kifejezes": "viharos szél", "volumen": "10000", "temak": ["Weather"]}],
            "2026-08-22": [{"kifejezes": "viharos szél", "volumen": "50000", "temak": ["Other"]}],
        },
    }
    payload = elemzo.epit_payload(adatok)
    felk = payload["felkapott"]
    assert felk["top"][0]["kifejezes"] == "viharos szél"
    assert felk["top"][0]["volumen"] == "50000"
    # gördülő hét: hányszor bukkant fel egy kifejezés az elmúlt napokban
    het = {e["kifejezes"]: e["napok_szama"] for e in felk["het"]["visszateroek"]}
    assert het["viharos szél"] == 2      # 08-21 és 08-22
    assert het["eső"] == 1


def test_felkapott_top_tovabbitja_a_hireket():
    # A RENDSZER_PROMPT megengedi az AI-nak a 'hirek' mező használatát — de csak akkor
    # jut el hozzá, ha a _felkapott ténylegesen továbbadja a legfrissebb.top_trendek 'hirek' listáját.
    adatok = {
        "regresszio": {"kulcsszavak": {}},
        "tortenet": {"napok": []},
        "legfrissebb": {"top_trendek": [
            {"kifejezes": "viharos szél", "volumen": "50000", "novekedes_pct": "1000",
             "temak": ["Other"], "hirek": [{"cim": "Vihar közeleg", "forras": "hvg.hu"}]},
        ]},
        "napok_trendek": {},
    }
    payload = elemzo.epit_payload(adatok)
    assert payload["felkapott"]["top"][0]["hirek"] == [{"cim": "Vihar közeleg", "forras": "hvg.hu"}]


def test_szekcio_sema_csak_szoveg():
    s = elemzo._szekcio_sema()
    assert s["required"] == ["szoveg"]
    assert set(s["properties"]) == {"szoveg"}
    assert "megfigyelesek" not in s["properties"]
    assert "elmeleti" not in s["properties"]


def test_modell_opus():
    assert elemzo.MODELL == "claude-opus-4-8"


def test_rendszer_prompt_folyo_proza_es_tiltas():
    p = elemzo.RENDSZER_PROMPT.lower()
    assert "bekezdés" in p          # folyó bekezdéseket kér
    assert "payload" in p           # explicit tiltja a „payload" szót
    assert "mező" in p              # tiltja a mezőnév-hivatkozást


def test_gordulo_het_napon_beluli_dedup():
    # Ha egy kifejezés EGY napon belül kétszer szerepel, az akkor is CSAK
    # egy nap (a "hány külön napon" szerződés — nem bejegyzés-számláló).
    adatok = {
        "regresszio": {"kulcsszavak": {}},
        "tortenet": {"napok": []},
        "legfrissebb": {"top_trendek": []},
        "napok_trendek": {
            "2026-08-22": [{"kifejezes": "eső", "volumen": "20000", "temak": ["Weather"]},
                           {"kifejezes": "eső", "volumen": "10000", "temak": ["Weather"]}],
        },
    }
    payload = elemzo.epit_payload(adatok)
    het = {e["kifejezes"]: e["napok_szama"] for e in payload["felkapott"]["het"]["visszateroek"]}
    assert het["eső"] == 1               # egy napon belüli duplikátum → 1 nap


def test_gordulo_het_none_napok_trendek_guard():
    # Explicit None napok_trendek esetén ne AttributeError-özzön, adjon üres eredményt.
    adatok = {
        "regresszio": {"kulcsszavak": {}},
        "tortenet": {"napok": []},
        "legfrissebb": {"top_trendek": []},
        "napok_trendek": None,
    }
    payload = elemzo.epit_payload(adatok)
    het = payload["felkapott"]["het"]
    assert het["napok"] == 0
    assert het["visszateroek"] == []


def test_nap_diff_iranyvaltas_es_felkapott_valtozas():
    mai = [{"szo": "állás", "irany": "emelkedik", "meredekseg": 2.0},
           {"szo": "benzin", "irany": "stagnal", "meredekseg": 0.0}]
    tegnapi = [{"szo": "állás", "irany": "csokken", "meredekseg": -1.0},
               {"szo": "benzin", "irany": "stagnal", "meredekseg": 0.1}]
    mai_top = [{"kifejezes": "eső"}, {"kifejezes": "viharos szél"}]
    tegnapi_top = [{"kifejezes": "eső"}, {"kifejezes": "hőség"}]
    diff = elemzo.nap_diff(mai, tegnapi, mai_top, tegnapi_top)
    assert diff["van_elozo"] is True
    assert {"szo": "állás", "elozo": "csokken", "mai": "emelkedik"} in diff["irany_valtok"]
    assert all(v["szo"] != "benzin" for v in diff["irany_valtok"])   # benzin nem váltott irányt
    assert "viharos szél" in diff["felkapott_uj"]
    assert "hőség" in diff["felkapott_eltunt"]


def test_nap_diff_elso_futas_nincs_elozo():
    diff = elemzo.nap_diff([{"szo": "állás", "irany": "emelkedik", "meredekseg": 1.0}], None,
                           [{"kifejezes": "eső"}], None)
    assert diff["van_elozo"] is False
    assert diff["irany_valtok"] == []
    assert diff["felkapott_uj"] == []
    assert diff["felkapott_eltunt"] == []


def test_epit_payload_beepiti_a_valtozast_ha_van_tegnapi():
    adatok = {
        "regresszio": _regresszio_egy_szo("emelkedik", 1.0, True, 10.0),
        "tortenet": {"napok": []},
        "legfrissebb": {"top_trendek": [{"kifejezes": "eső"}]},
        "napok_trendek": {},
    }
    tegnapi_szamok = [{"szo": "állás", "irany": "csokken", "meredekseg": -1.0}]
    tegnapi_top = [{"kifejezes": "hőség"}]
    payload = elemzo.epit_payload(adatok, tegnapi_szamok=tegnapi_szamok, tegnapi_top=tegnapi_top)
    assert payload["valtozas"]["van_elozo"] is True
    assert payload["valtozas"]["irany_valtok"][0]["szo"] == "állás"
    assert "eső" in payload["valtozas"]["felkapott_uj"]


def test_epit_payload_kulcsszo_het_a_lancbol():
    adatok = {"regresszio": {}, "tortenet": {}, "legfrissebb": {}, "napok_trendek": {},
              "lanc": {"kulcsszavak": {"állás": {"pontok": [
                  {"idopont_utc": "2026-08-15T18:00:00+00:00", "ertek": 42},
                  {"idopont_utc": "2026-08-22T18:00:00+00:00", "ertek": 51}]}}}}
    p = elemzo.epit_payload(adatok)
    assert p["kulcsszo_het"]["szavak"], "a kulcsszo_het NEM lehet üres, ha van lánc"
    assert p["kulcsszo_het"]["szavak"][0]["szo"] == "állás"
    assert p["kulcsszo_het"]["szavak"][0]["valtozas"] == 9


def test_nap_diff_mozgok_rendezes_es_delta():
    # A mozgok listát az abszolút meredekség-változás szerint CSÖKKENŐEN rendezi,
    # és a valtozas mező a helyes delta (mai − tegnapi, kerekítve).
    mai = [{"szo": "állás", "irany": "emelkedik", "meredekseg": 3.0},
           {"szo": "benzin", "irany": "emelkedik", "meredekseg": 0.5}]
    tegnapi = [{"szo": "állás", "irany": "emelkedik", "meredekseg": 1.0},
               {"szo": "benzin", "irany": "emelkedik", "meredekseg": 0.4}]
    diff = elemzo.nap_diff(mai, tegnapi, [], [])
    assert diff["mozgok"][0]["szo"] == "állás"       # nagyobb abszolút változás elöl
    assert diff["mozgok"][0]["valtozas"] == 2.0      # 3.0 − 1.0
    assert diff["mozgok"][1]["szo"] == "benzin"
    assert diff["mozgok"][1]["valtozas"] == 0.1      # 0.5 − 0.4, kerekítve


def test_nap_diff_mai_only_szo_kihagyva():
    # Ha egy szó a maiban van, de a tegnapiban NINCS → kihagyva (nem dob, nem kerül be).
    mai = [{"szo": "állás", "irany": "emelkedik", "meredekseg": 2.0},
           {"szo": "új_szo", "irany": "emelkedik", "meredekseg": 5.0}]
    tegnapi = [{"szo": "állás", "irany": "csokken", "meredekseg": 1.0}]
    diff = elemzo.nap_diff(mai, tegnapi, [], [])
    assert all(v["szo"] != "új_szo" for v in diff["irany_valtok"])
    assert all(m["szo"] != "új_szo" for m in diff["mozgok"])


def test_nap_diff_nem_szam_meredekseg_kihagyva():
    # Ha egy szó meredeksége None (vagy hiányzik) → ne dobjon, ne kerüljön mozgok-ba.
    mai = [{"szo": "állás", "irany": "emelkedik", "meredekseg": None}]
    tegnapi = [{"szo": "állás", "irany": "emelkedik", "meredekseg": 1.0}]
    diff = elemzo.nap_diff(mai, tegnapi, [], [])
    assert all(m["szo"] != "állás" for m in diff["mozgok"])


class KamuKliens:
    def __init__(self, valasz):
        self._valasz = valasz
        self.hivasok = []

    def uzenet(self, payload, modell, mode="este"):
        self.hivasok.append((payload, modell, mode))
        return self._valasz


def _ai_valasz():
    szekcio = {"szoveg": "sz"}
    sz = lambda s: {"szoveg": s}
    return {"valtozas": szekcio, "kulcsszavak": {"napi": szekcio, "teljes_kep": szekcio, "het": szekcio},
            "felkapott": {"reggel": sz("f-reggel"), "este": sz("f-este"),
                          "teljes_nap": sz("f- iv"), "het": sz("f-het")}}


def _payload_szegmensekkel(van_reggel=True, van_este=True):
    reggel = [{"kifejezes": "r"}] if van_reggel else []
    este = [{"kifejezes": "e"}] if van_este else []
    ms = {}
    if van_reggel: ms["reggel"] = reggel
    if van_este: ms["este"] = este
    adatok = {"regresszio": {}, "tortenet": {},
              "legfrissebb": {"top_trendek": este}, "napok_trendek": {},
              "ma_szegmensek": ms, "lanc": {}}
    return elemzo.epit_payload(adatok)


def test_artefakt_felkapott_negy_szekcio():
    payload = _payload_szegmensekkel(van_reggel=True, van_este=True)
    art = elemzo.valasz_to_artefakt(_ai_valasz(), payload, nap="2026-08-31", modell="m")
    fk = art["felkapott"]
    assert fk["reggel"]["szoveg"] == "f-reggel"
    assert fk["este"]["szoveg"] == "f-este"
    assert fk["teljes_nap"]["szoveg"] == "f- iv"
    assert fk["het"]["szoveg"] == "f-het"
    assert "reggel_top" in fk and "este_top" in fk and "reggel_este_diff" in fk
    assert "het_valos" in fk


def test_artefakt_fail_soft_csak_este():
    payload = _payload_szegmensekkel(van_reggel=False, van_este=True)
    art = elemzo.valasz_to_artefakt(_ai_valasz(), payload, nap="2026-08-31", modell="m")
    fk = art["felkapott"]
    assert "nem volt reggeli" in fk["reggel"]["szoveg"].lower()      # DETERMINISZTIKUS, nem az AI
    assert "nem rajzolható" in fk["teljes_nap"]["szoveg"].lower()
    assert fk["este"]["szoveg"] == "f-este"                          # az esti marad AI-próza


def test_elemez_a_varrat_mogott_nem_hiv_halozatot():
    kliens = KamuKliens(_ai_valasz())
    payload = {"kulcsszavak": {"szamok": []}, "felkapott": {"top": []}, "valtozas": {}}
    valasz = elemzo.elemez(payload, kliens=kliens)
    assert kliens.hivasok[0][1] == "claude-opus-4-8"      # a modell átment
    assert valasz["kulcsszavak"]["napi"]["szoveg"] == "sz"
    assert valasz["valtozas"]["szoveg"] == "sz"


def test_valasz_sema_reggel_csak_felkapott_reggel():
    sema = elemzo._valasz_sema(mode="reggel")
    assert sema["required"] == ["felkapott"]
    fk = sema["properties"]["felkapott"]
    assert fk["required"] == ["reggel"] and set(fk["properties"]) == {"reggel"}
    assert "kulcsszavak" not in sema["properties"] and "valtozas" not in sema["properties"]


def test_valasz_sema_este_valtozatlan_negy_felkapott():
    sema = elemzo._valasz_sema(mode="este")
    assert sema["properties"]["felkapott"]["required"] == ["reggel", "este", "teljes_nap", "het"]
    assert "valtozas" in sema["properties"] and "kulcsszavak" in sema["properties"]


def test_rendszer_prompt_reggel_csak_reggeli_pillanatkep():
    p = elemzo._rendszer_prompt("reggel")
    assert "reggeli" in p.lower()
    assert "NÉGY külön bekezdésben" not in p       # a 4-bekezdéses esti szabály NINCS benne
    assert elemzo._rendszer_prompt("este") == elemzo.RENDSZER_PROMPT


def test_epit_payload_reggel_kihagyja_a_youtube_ot():
    adatok = {"regresszio": {}, "tortenet": {}, "legfrissebb": {"top_trendek": []},
              "napok_trendek": {}, "ma_szegmensek": {"reggel": [{"kifejezes": "r"}]}, "lanc": {},
              "youtube_regresszio": {"kulcsszavak": {"foci": {"intervallumok": {}}}},
              "youtube_nyers": {"kulcsszavak": {"foci": []}}}
    assert "youtube" not in elemzo.epit_payload(adatok, mode="reggel")


def test_elemez_atadja_a_modot_a_kliensnek():
    kliens = KamuKliens(_ai_valasz())
    elemzo.elemez({"felkapott": {}}, kliens=kliens, mode="reggel")
    assert kliens.hivasok[0][2] == "reggel"      # (payload, modell, mode)


import json
from pathlib import Path


def _minimal_docs_data(tmp_path):
    dd = tmp_path / "data"
    (dd / "napok").mkdir(parents=True)
    (dd / "kulcsszo_regresszio.json").write_text(json.dumps(
        _regresszio_egy_szo("emelkedik", 1.0, True, 10.0)), encoding="utf-8")
    (dd / "tortenet.json").write_text(json.dumps(
        {"napok": [{"nap": "2026-08-22", "kulcsszavak": [{"kulcsszo": "állás", "atlag": 25.0, "csucs": 100.0}]}]}),
        encoding="utf-8")
    (dd / "legfrissebb.json").write_text(json.dumps({"top_trendek": [{"kifejezes": "eső"}]}), encoding="utf-8")
    (dd / "napok" / "index.json").write_text(json.dumps({"napok": ["2026-08-22"]}), encoding="utf-8")
    (dd / "napok" / "2026-08-22.json").write_text(json.dumps({"nap": "2026-08-22", "trendek": [{"kifejezes": "eső"}]}),
                                                  encoding="utf-8")
    return dd


def test_futtat_sikeres_ut_ir_artefaktot_archivumot_indexet(tmp_path):
    dd = _minimal_docs_data(tmp_path)
    kod = elemzo.futtat(dd, nap="2026-08-22", kliens=KamuKliens(_ai_valasz()))
    assert kod == 0
    art = json.loads((dd / "elemzes.json").read_text(encoding="utf-8"))
    assert art["nap"] == "2026-08-22"
    assert art["kulcsszavak"]["napi"]["szoveg"] == "sz"
    # archívum + index
    assert (dd / "elemzesek" / "2026-08-22.json").exists()
    idx = json.loads((dd / "elemzesek" / "index.json").read_text(encoding="utf-8"))
    assert idx["napok"] == ["2026-08-22"]


class HibasKliens:
    def uzenet(self, payload, modell, mode="este"):
        raise RuntimeError("429 szimulált")


def test_futtat_fail_soft_megorzi_az_elozo_elemzest(tmp_path):
    dd = _minimal_docs_data(tmp_path)
    regi = json.dumps({"nap": "2026-08-21", "modell": "regi"}, ensure_ascii=False)
    (dd / "elemzes.json").write_text(regi, encoding="utf-8")
    kod = elemzo.futtat(dd, nap="2026-08-22", kliens=HibasKliens())
    assert kod == 2
    # a LEMEZEN a régi maradt (SZANDEKOS-ZOLD-VAK: a lemezt nézzük, nem a visszatérést)
    a_lemezen = json.loads((dd / "elemzes.json").read_text(encoding="utf-8"))
    assert a_lemezen["nap"] == "2026-08-21"
    assert not (dd / "elemzesek" / "2026-08-22.json").exists()


def test_main_env_nappal_fut(tmp_path, monkeypatch):
    # a main a docs/data-t a repo gyökérből veszi; itt csak azt igazoljuk, hogy az env-nap átmegy
    hivott = {}
    monkeypatch.setattr(elemzo, "futtat", lambda docs_data, nap, kliens=None: hivott.setdefault("nap", nap) and 0)
    monkeypatch.setenv("ELEMZES_NAP", "2026-08-22")
    assert elemzo.main() == 0
    assert hivott["nap"] == "2026-08-22"


def test_valasz_to_artefakt_valos_reteg_es_ai_narrativa():
    payload = {
        "kulcsszavak": {"szamok": [{"szo": "állás", "irany": "emelkedik", "meredekseg": 1.0,
                                    "ervenyes": True, "mai_ertek": 10.0, "csucs": 100.0, "atlag": 25.0}]},
        "felkapott": {"top": [{"kifejezes": "eső", "volumen": "20000", "novekedes_pct": "500", "temak": ["W"]}],
                      "reggel_top": [], "este_top": [],
                      "reggel_este_diff": {"uj_estere": [], "eltunt_estere": [], "megmaradt": []},
                      "het": {"napok": 2, "visszateroek": []}},
        "valtozas": {"irany_valtok": [], "mozgok": [], "felkapott_uj": [], "felkapott_eltunt": [], "van_elozo": False},
    }
    art = elemzo.valasz_to_artefakt(_ai_valasz(), payload, nap="2026-08-22", modell="claude-sonnet-5")
    assert art["nap"] == "2026-08-22"
    assert art["modell"] == "claude-sonnet-5"
    # VALÓS réteg átvéve a payloadból (nem az AI-tól):
    assert art["kulcsszavak"]["szamok"][0]["csucs"] == 100.0
    assert art["felkapott"]["top"][0]["kifejezes"] == "eső"
    assert art["valtozas"]["diff"]["van_elozo"] is False
    # AI-narratíva a helyén:
    assert art["kulcsszavak"]["napi"]["szoveg"] == "sz"
    assert art["felkapott"]["het"]["szoveg"] == "f-het"


def test_valasz_to_artefakt_megorzi_a_heti_valos_reteget():
    # A payload felkapott.het (VALÓS, determinisztikus heti visszatérés) NE vesszen el —
    # az AI narratíva felülírja a felkapott.het-et, de a VALÓS számoknak sibling het_valos
    # mezőben meg kell maradniuk (nem-törő bővítés).
    payload = {
        "kulcsszavak": {"szamok": []},
        "felkapott": {"top": [],
                      "reggel_top": [], "este_top": [],
                      "reggel_este_diff": {"uj_estere": [], "eltunt_estere": [], "megmaradt": []},
                      "het": {"napok": 3, "visszateroek": [{"kifejezes": "eső", "napok_szama": 2}]}},
        "valtozas": {"irany_valtok": [], "mozgok": [], "felkapott_uj": [], "felkapott_eltunt": [], "van_elozo": False},
    }
    art = elemzo.valasz_to_artefakt(_ai_valasz(), payload, nap="2026-08-22", modell="claude-sonnet-5")
    assert art["felkapott"]["het_valos"]["visszateroek"] == [{"kifejezes": "eső", "napok_szama": 2}]
    assert art["felkapott"]["het_valos"]["napok"] == 3
    # az AI-narratíva a het mezőben marad, változatlanul:
    assert art["felkapott"]["het"]["szoveg"] == "f-het"


def _mini_payload(van_elozo):
    return {"kulcsszavak": {"szamok": []},
            "felkapott": {"top": [], "reggel_top": [], "este_top": [],
                          "reggel_este_diff": {"uj_estere": [], "eltunt_estere": [], "megmaradt": []},
                          "het": {"napok": 0, "visszateroek": []}},
            "valtozas": {"van_elozo": van_elozo, "irany_valtok": [], "mozgok": [],
                         "felkapott_uj": [], "felkapott_eltunt": []},
            "kulcsszo_het": {"ablak_napok": 7, "szavak": []}}


def _mini_ai(valtozas_szoveg):
    sz = {"szoveg": "sz"}
    return {"valtozas": {"szoveg": valtozas_szoveg},
            "kulcsszavak": {"napi": sz, "teljes_kep": sz, "het": sz},
            "felkapott": {"reggel": sz, "este": sz, "teljes_nap": sz, "het": sz}}


def test_artefakt_ures_nap_python_szoveg():
    art = elemzo.valasz_to_artefakt(_mini_ai("AI-SZÖVEG-NE-JELENJEN-MEG"),
                                    _mini_payload(van_elozo=False),
                                    nap="2026-08-22", modell="claude-opus-4-8")
    assert "nincs korábbi nap" in art["valtozas"]["szoveg"].lower()
    assert "AI-SZÖVEG-NE-JELENJEN-MEG" not in art["valtozas"]["szoveg"]
    assert art["valtozas"]["diff"]["van_elozo"] is False


def test_artefakt_van_elozo_ai_szoveg_marad():
    art = elemzo.valasz_to_artefakt(_mini_ai("Az AI napi összefoglalója."),
                                    _mini_payload(van_elozo=True),
                                    nap="2026-08-22", modell="claude-opus-4-8")
    assert art["valtozas"]["szoveg"] == "Az AI napi összefoglalója."


def test_kulcsszo_het_valos_palya():
    lanc = {"kulcsszavak": {
        "állás": {"ablak_kezdet_utc": "2026-08-01T00:00:00+00:00",
                   "ablak_veg_utc": "2026-08-22T18:00:00+00:00",
                   "pontok": [
                       {"idopont_utc": "2026-08-14T18:00:00+00:00", "ertek": 40},  # ablakon KÍVÜL (< 08-15T18:00)
                       {"idopont_utc": "2026-08-15T18:00:00+00:00", "ertek": 42},  # ablak eleje = kezdo
                       {"idopont_utc": "2026-08-18T18:00:00+00:00", "ertek": 55},  # max
                       {"idopont_utc": "2026-08-22T18:00:00+00:00", "ertek": 51},  # veg
                   ]},
        "tüntetés": {"ablak_kezdet_utc": "2026-08-01T00:00:00+00:00",
                      "ablak_veg_utc": "2026-08-17T18:00:00+00:00",
                      "pontok": [
                          {"idopont_utc": "2026-08-16T18:00:00+00:00", "ertek": 5},
                          {"idopont_utc": "2026-08-17T18:00:00+00:00", "ertek": 0},  # elavult vég → KIMARAD
                      ]},
    }}
    ki = elemzo._kulcsszo_het(lanc)
    assert ki["ablak_napok"] == 7
    assert [s["szo"] for s in ki["szavak"]] == ["állás"]   # a szakasz-törött tüntetés kimaradt
    allas = ki["szavak"][0]
    assert allas["kezdo"] == 42     # az ablak első pontja (08-15); a 08-14 KÍVÜL van
    assert allas["veg"] == 51
    assert allas["valtozas"] == 9   # 51 - 42
    assert allas["min"] == 42
    assert allas["max"] == 55


def test_kulcsszo_het_ures_lanc():
    assert elemzo._kulcsszo_het({}) == {"ablak_napok": 7, "szavak": []}
    assert elemzo._kulcsszo_het({"kulcsszavak": {}}) == {"ablak_napok": 7, "szavak": []}


def _yt_reg_egy_szo():
    # 1_het érvénytelen (mint az éles youtube_regresszio-ban), 2_het és 1_ev érvényes;
    # a leghosszabb érvényes = 1_ev (legkorábbi ablak_kezdet_utc).
    return {"kulcsszavak": {"szorongás": {
        "domen": "egeszseg", "racs": "nap", "aktiv": True, "tipus": "szintmero",
        "intervallumok": {
            "1_het": {"ervenyes": False, "ok": "keves_pont"},
            "2_het": {"ervenyes": True, "irany": "csokken", "meredekseg_nap": -0.97,
                       "mai_ertek": 78, "ablak_kezdet_utc": "2026-08-11T00:00:00+00:00"},
            "1_ev": {"ervenyes": True, "irany": "novekszik", "meredekseg_nap": 0.05,
                      "mai_ertek": 43, "ablak_kezdet_utc": "2025-08-24T00:00:00+00:00"},
        }}}}


def _yt_nyers_egy_szo():
    # két sorozat: napi (3-m) + heti (12-m, legkorábbi kezdet) — a csúcs/átlag a hetiből jön
    return {"kulcsszavak": {"szorongás": [
        {"ablak_kezdet_utc": "2026-05-25T00:00:00+00:00", "ablak_veg_utc": "2026-08-25T00:00:00+00:00",
         "pontok": [{"idopont_utc": "2026-08-24T00:00:00+00:00", "ertek": 90, "reszleges": False}]},
        {"ablak_kezdet_utc": "2025-08-24T00:00:00+00:00", "ablak_veg_utc": "2026-08-23T00:00:00+00:00",
         "pontok": [{"idopont_utc": "2025-08-24T00:00:00+00:00", "ertek": 40, "reszleges": False},
                    {"idopont_utc": "2026-08-16T00:00:00+00:00", "ertek": 50, "reszleges": False},
                    {"idopont_utc": "2026-08-23T00:00:00+00:00", "ertek": 88, "reszleges": True}]},
    ]}}


def test_youtube_szamok_leghosszabb_ervenyes_intervallum_es_nyers_csucs_atlag():
    szamok = elemzo._youtube_szamok(_yt_reg_egy_szo(), _yt_nyers_egy_szo())
    assert len(szamok) == 1
    s = szamok[0]
    assert s["szo"] == "szorongás"
    assert s["domen"] == "egeszseg"
    # a leghosszabb ÉRVÉNYES = 1_ev (2025-08-24 a legkorábbi kezdet), NEM a 2_het
    assert s["irany"] == "novekszik"
    assert s["meredekseg"] == 0.05
    assert s["mai_ertek"] == 43
    assert s["ervenyes"] is True
    # csúcs/átlag a HETI nyers sorozatból, csak a nem-részleges pontok (40, 50; a 88 részleges kimarad)
    assert s["csucs"] == 50
    assert s["atlag"] == 45.0


def test_youtube_szamok_nincs_ervenyes_intervallum_fail_soft():
    reg = {"kulcsszavak": {"klíma": {"domen": "otthon", "intervallumok": {
        "1_het": {"ervenyes": False, "ok": "keves_pont"}}}}}
    szamok = elemzo._youtube_szamok(reg, {"kulcsszavak": {}})
    assert szamok[0]["szo"] == "klíma"
    assert szamok[0]["irany"] is None
    assert szamok[0]["ervenyes"] is False
    assert szamok[0]["csucs"] is None
    assert szamok[0]["atlag"] is None


def test_youtube_szamok_hianyzo_adat_ures_lista():
    assert elemzo._youtube_szamok(None, None) == []
    assert elemzo._youtube_szamok({}, {}) == []


def test_youtube_het_utolso_ket_nem_reszleges_heti_pont():
    nyers = {"kulcsszavak": {
        "bitcoin": [
            {"ablak_kezdet_utc": "2025-08-24T00:00:00+00:00", "ablak_veg_utc": "2026-08-23T00:00:00+00:00",
             "pontok": [{"idopont_utc": "2026-08-09T00:00:00+00:00", "ertek": 30, "reszleges": False},
                        {"idopont_utc": "2026-08-16T00:00:00+00:00", "ertek": 57, "reszleges": False},
                        {"idopont_utc": "2026-08-23T00:00:00+00:00", "ertek": 99, "reszleges": True}]}],
        "mese": [
            {"ablak_kezdet_utc": "2025-08-24T00:00:00+00:00", "ablak_veg_utc": "2026-08-23T00:00:00+00:00",
             "pontok": [{"idopont_utc": "2026-08-09T00:00:00+00:00", "ertek": 90, "reszleges": False},
                        {"idopont_utc": "2026-08-16T00:00:00+00:00", "ertek": 95, "reszleges": False}]}],
    }}
    het = elemzo._youtube_het(nyers)
    szavak = {s["szo"]: s for s in het["szavak"]}
    # a részleges (2026-08-23) pont kimarad → az utolsó két lezárt: 30 → 57
    assert szavak["bitcoin"]["kezdo"] == 30
    assert szavak["bitcoin"]["veg"] == 57
    assert szavak["bitcoin"]["valtozas"] == 27
    assert szavak["mese"]["valtozas"] == 5
    # rendezés: a nagyobb abszolút mozgó elöl
    assert het["szavak"][0]["szo"] == "bitcoin"


def test_youtube_het_keves_pont_kimarad():
    nyers = {"kulcsszavak": {"klíma": [
        {"ablak_kezdet_utc": "2025-08-24T00:00:00+00:00", "ablak_veg_utc": "2026-08-23T00:00:00+00:00",
         "pontok": [{"idopont_utc": "2026-08-16T00:00:00+00:00", "ertek": 7, "reszleges": False}]}]}}
    assert elemzo._youtube_het(nyers)["szavak"] == []


def test_youtube_het_hianyzo_adat():
    assert elemzo._youtube_het(None) == {"szavak": []}
    assert elemzo._youtube_het({}) == {"szavak": []}


def test_epit_payload_youtube_kulcs_ha_van_adat():
    adatok = {
        "regresszio": _regresszio_egy_szo("emelkedik", 1.0, True, 10.0),
        "tortenet": {"napok": []}, "legfrissebb": {"top_trendek": []}, "napok_trendek": {},
        "youtube_regresszio": _yt_reg_egy_szo(), "youtube_nyers": _yt_nyers_egy_szo(),
    }
    payload = elemzo.epit_payload(adatok)
    assert "youtube" in payload
    assert payload["youtube"]["szamok"][0]["szo"] == "szorongás"
    assert "het_valos" in payload["youtube"]
    # a Google-kulcsok VÁLTOZATLANOK
    assert payload["kulcsszavak"]["szamok"][0]["szo"] == "állás"


def test_epit_payload_nincs_youtube_kulcs_ha_nincs_adat():
    adatok = {"regresszio": _regresszio_egy_szo("emelkedik", 1.0, True, 10.0),
              "tortenet": {"napok": []}, "legfrissebb": {"top_trendek": []}, "napok_trendek": {}}
    payload = elemzo.epit_payload(adatok)
    assert "youtube" not in payload


def test_valasz_sema_google_alap_valtozatlan():
    s = elemzo._valasz_sema()
    assert set(s["required"]) == {"valtozas", "kulcsszavak", "felkapott"}
    assert "youtube" not in s["properties"]


def test_valasz_sema_youtube_szekcio_szigoru():
    s = elemzo._valasz_sema(youtube=True)
    assert "youtube" in s["required"]
    yt = s["properties"]["youtube"]
    assert yt["additionalProperties"] is False
    assert set(yt["required"]) == {"napi", "teljes_kep", "het"}
    assert set(yt["properties"]["napi"]["properties"]) == {"szoveg"}


def test_rendszer_prompt_youtube_keret():
    p = elemzo.RENDSZER_PROMPT.lower()
    assert "youtube" in p                 # a YouTube-keret jelen van
    assert "payload" in p and "mező" in p  # a meglévő tiltások VÁLTOZATLANUL érvényben


def _ai_valasz_youtubebal():
    sz = {"szoveg": "sz"}
    return {"valtozas": sz, "kulcsszavak": {"napi": sz, "teljes_kep": sz, "het": sz},
            "felkapott": {"reggel": sz, "este": sz, "teljes_nap": sz, "het": sz},
            "youtube": {"napi": {"szoveg": "yt-napi"}, "teljes_kep": {"szoveg": "yt-teljes"},
                        "het": {"szoveg": "yt-het"}}}


def test_valasz_to_artefakt_youtube_blokk_valos_es_ai():
    payload = {
        "kulcsszavak": {"szamok": []},
        "felkapott": {"top": [], "reggel_top": [], "este_top": [],
                      "reggel_este_diff": {"uj_estere": [], "eltunt_estere": [], "megmaradt": []},
                      "het": {"napok": 0, "visszateroek": []}},
        "valtozas": {"irany_valtok": [], "mozgok": [], "felkapott_uj": [], "felkapott_eltunt": [], "van_elozo": False},
        "youtube": {"szamok": [{"szo": "szorongás", "domen": "egeszseg", "irany": "novekszik",
                                "meredekseg": 0.05, "ervenyes": True, "mai_ertek": 43, "csucs": 50, "atlag": 45.0}],
                    "het_valos": [{"szo": "bitcoin", "kezdo": 30, "veg": 57, "valtozas": 27}]},
    }
    art = elemzo.valasz_to_artefakt(_ai_valasz_youtubebal(), payload, nap="2026-08-26", modell="claude-opus-4-8")
    # VALÓS a payloadból
    assert art["youtube"]["szamok"][0]["csucs"] == 50
    assert art["youtube"]["het_valos"][0]["valtozas"] == 27
    # AI-próza a válaszból
    assert art["youtube"]["napi"]["szoveg"] == "yt-napi"
    assert art["youtube"]["teljes_kep"]["szoveg"] == "yt-teljes"
    assert art["youtube"]["het"]["szoveg"] == "yt-het"


def test_valasz_to_artefakt_nincs_youtube_ha_nincs_payloadban():
    payload = _mini_payload(van_elozo=True)   # nincs "youtube" kulcs
    art = elemzo.valasz_to_artefakt(_mini_ai("napi"), payload, nap="2026-08-26", modell="claude-opus-4-8")
    assert "youtube" not in art


def test_utolso_napok_trendek_szegmentalt_estit_ad(tmp_path):
    napok = tmp_path / "napok"; napok.mkdir(parents=True)
    (napok / "index.json").write_text(json.dumps({"napok": ["2026-08-31"]}), encoding="utf-8")
    (napok / "2026-08-31.json").write_text(json.dumps({
        "nap": "2026-08-31",
        "reggel": {"trendek": [{"kifejezes": "reggeli"}], "frissitve": "2026-08-31T07:00:00+00:00"},
        "este": {"trendek": [{"kifejezes": "esti"}], "frissitve": "2026-08-31T19:00:00+00:00"},
    }), encoding="utf-8")
    ki = elemzo._utolso_napok_trendek(tmp_path)
    assert ki["2026-08-31"] == [{"kifejezes": "esti"}]   # az ESTI (beállt) kép


def test_utolso_napok_trendek_csak_reggel_fallback(tmp_path):
    napok = tmp_path / "napok"; napok.mkdir(parents=True)
    (napok / "index.json").write_text(json.dumps({"napok": ["2026-08-31"]}), encoding="utf-8")
    (napok / "2026-08-31.json").write_text(json.dumps({
        "nap": "2026-08-31",
        "reggel": {"trendek": [{"kifejezes": "reggeli"}], "frissitve": "2026-08-31T07:00:00+00:00"},
    }), encoding="utf-8")
    ki = elemzo._utolso_napok_trendek(tmp_path)
    assert ki["2026-08-31"] == [{"kifejezes": "reggeli"}]   # nincs este → reggel fallback


def test_utolso_napok_trendek_regi_alak(tmp_path):
    napok = tmp_path / "napok"; napok.mkdir(parents=True)
    (napok / "index.json").write_text(json.dumps({"napok": ["2026-08-20"]}), encoding="utf-8")
    (napok / "2026-08-20.json").write_text(json.dumps({
        "nap": "2026-08-20", "trendek": [{"kifejezes": "regi"}],
    }), encoding="utf-8")
    ki = elemzo._utolso_napok_trendek(tmp_path)
    assert ki["2026-08-20"] == [{"kifejezes": "regi"}]   # régi = este-ként normalizálva


def test_ma_szegmensek_reggel_este(tmp_path):
    napok = tmp_path / "napok"; napok.mkdir()
    (napok / "2026-08-31.json").write_text(json.dumps({
        "nap": "2026-08-31",
        "reggel": {"trendek": [{"kifejezes": "r1"}], "frissitve": "x"},
        "este": {"trendek": [{"kifejezes": "e1"}, {"kifejezes": "e2"}], "frissitve": "y"},
    }), encoding="utf-8")
    ms = elemzo._ma_szegmensek(tmp_path, "2026-08-31")
    assert [t["kifejezes"] for t in ms["reggel"]] == ["r1"]
    assert [t["kifejezes"] for t in ms["este"]] == ["e1", "e2"]


def test_ma_szegmensek_regi_lapos_este(tmp_path):
    napok = tmp_path / "napok"; napok.mkdir()
    (napok / "2026-08-20.json").write_text(json.dumps({"nap": "2026-08-20", "trendek": [{"kifejezes": "x"}]}), encoding="utf-8")
    ms = elemzo._ma_szegmensek(tmp_path, "2026-08-20")
    assert "reggel" not in ms
    assert [t["kifejezes"] for t in ms["este"]] == ["x"]


def test_ma_szegmensek_hianyzo_fajl(tmp_path):
    assert elemzo._ma_szegmensek(tmp_path, "2026-08-31") == {}


def test_felkapott_szegmensek_diff():
    ms = {"reggel": [{"kifejezes": "a", "volumen": "5"}, {"kifejezes": "b"}],
          "este": [{"kifejezes": "b"}, {"kifejezes": "c"}]}
    r = elemzo._felkapott_szegmensek(ms, {})
    assert [t["kifejezes"] for t in r["reggel_top"]] == ["a", "b"]
    assert [t["kifejezes"] for t in r["este_top"]] == ["b", "c"]
    assert r["reggel_este_diff"] == {"uj_estere": ["c"], "eltunt_estere": ["a"], "megmaradt": ["b"]}
    assert r["van_reggel"] is True and r["van_este"] is True


def test_felkapott_szegmensek_este_fallback_legfrissebb():
    # nincs napfájl-este → a legfrissebb.top_trendek a settled esti kép
    r = elemzo._felkapott_szegmensek({"reggel": [{"kifejezes": "a"}]},
                                     {"top_trendek": [{"kifejezes": "z"}]})
    assert [t["kifejezes"] for t in r["este_top"]] == ["z"]
    assert r["van_reggel"] is True and r["van_este"] is True


def test_felkapott_szegmensek_csak_este():
    r = elemzo._felkapott_szegmensek({"este": [{"kifejezes": "e"}]}, {})
    assert r["van_reggel"] is False and r["van_este"] is True
    assert r["reggel_top"] == []
    assert r["reggel_este_diff"]["uj_estere"] == ["e"]


def test_epit_payload_felkapott_szegmensek(tmp_path):
    # a ma_szegmensek az adatok-ból jön (futtat tölti); itt közvetlenül adjuk
    adatok = {
        "regresszio": {}, "tortenet": {},
        "legfrissebb": {"top_trendek": [{"kifejezes": "e1"}]},
        "napok_trendek": {},
        "ma_szegmensek": {"reggel": [{"kifejezes": "r1"}], "este": [{"kifejezes": "e1"}]},
        "lanc": {},
    }
    p = elemzo.epit_payload(adatok)
    fk = p["felkapott"]
    assert "top" in fk and "het" in fk                    # a régi kulcsok maradnak
    assert [t["kifejezes"] for t in fk["reggel_top"]] == ["r1"]
    assert [t["kifejezes"] for t in fk["este_top"]] == ["e1"]
    assert fk["van_reggel"] is True and fk["van_este"] is True
    assert fk["reggel_este_diff"]["uj_estere"] == ["e1"]  # e1 este-ben, reggel-ben nincs


def test_valasz_sema_felkapott_negy_mezo():
    sema = elemzo._valasz_sema()
    fk = sema["properties"]["felkapott"]
    assert set(fk["required"]) == {"reggel", "este", "teljes_nap", "het"}
    assert set(fk["properties"]) == {"reggel", "este", "teljes_nap", "het"}


def test_rendszer_prompt_felkapott_negy_bekezdes():
    p = elemzo.RENDSZER_PROMPT.lower()
    assert "reggeli" in p and "esti" in p and "nap íve" in p
