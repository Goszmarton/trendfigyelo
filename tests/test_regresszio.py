from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from trendfigyelo import regresszio

KEZD = datetime(2026, 7, 24, 21, tzinfo=timezone.utc)


def _pont(t, ertek, reszleges=False):
    return {"idopont_utc": t.isoformat(), "ertek": ertek, "reszleges": reszleges}


def _oras(n_lezart, meredekseg=0.1, kezd=KEZD, partial=False):
    """n_lezart lezárt órás pont T+0..T+(n-1); partial=True esetén +1 részleges a végén."""
    pts = [_pont(kezd + timedelta(hours=i), 50 + meredekseg * i) for i in range(n_lezart)]
    if partial:
        pts.append(_pont(kezd + timedelta(hours=n_lezart), 50 + meredekseg * n_lezart, reszleges=True))
    return pts


# ── _illesztes ──────────────────────────────────────────────────────────────
def test_illesztes_pontos_egyenes():
    # mini-9a: az _illesztes 4-tuple-t ad → (meredekseg, METSZET, r2, se). y=2x → metszet 0.
    b, a, r2, se = regresszio._illesztes([0, 1, 2, 3], [0, 2, 4, 6])
    assert round(b, 6) == 2.0 and round(a, 6) == 0.0 and round(r2, 6) == 1.0 and se == 0.0


def test_illesztes_lapos():
    b, a, r2, _ = regresszio._illesztes([0, 1, 2], [5, 5, 5])
    assert b == 0.0 and a == 5.0 and r2 == 0.0


def test_illesztes_degeneralt_none():
    # nincs x-variancia (minden x azonos) → degeneráltság-jelzés (4-tuple None, a metszet is None)
    assert regresszio._illesztes([3, 3, 3], [1, 2, 3]) == (None, None, None, None)


# ── _irany (fix 1.0 küszöb, ASCII enum) ──────────────────────────────────────
def test_irany_kuszob():
    assert regresszio._irany(0.5) == "stagnal"
    assert regresszio._irany(-0.99) == "stagnal"
    assert regresszio._irany(2.0) == "novekszik"
    assert regresszio._irany(-2.0) == "csokken"


# ── regresszio_egy_ablak ─────────────────────────────────────────────────────
def test_reszleges_zaropont_kihagyva():
    pts = _oras(168, partial=True)
    veg = KEZD + timedelta(hours=168)
    r = regresszio.regresszio_egy_ablak(pts, KEZD.isoformat(), veg.isoformat(), 7)
    assert r["ervenyes"] is True
    assert r["pontok_kihagyva_reszleges"] == 1 and r["pontok_hasznalt"] == 168


def test_keves_pont():
    pts = _oras(10)
    r = regresszio.regresszio_egy_ablak(pts, KEZD.isoformat(), (KEZD + timedelta(hours=10)).isoformat(), 7)
    assert r["ervenyes"] is False and r["ok"] == "keves_pont"
    assert r["pontok_hasznalt"] == 10


def test_rovid_span():
    pts = _oras(30)   # 30 pont, ~29h span < 3.5 nap
    r = regresszio.regresszio_egy_ablak(pts, KEZD.isoformat(), (KEZD + timedelta(hours=29)).isoformat(), 7)
    assert r["ervenyes"] is False and r["ok"] == "rovid_span"
    assert r["pontok_hasznalt"] == 30


def test_degeneralt():
    pts = [_pont(KEZD, 50 + i) for i in range(24)]   # 24 pont AZONOS időbélyeggel
    r = regresszio.regresszio_egy_ablak(pts, KEZD.isoformat(), (KEZD + timedelta(hours=168)).isoformat(), 7)
    assert r["ervenyes"] is False and r["ok"] == "degeneralt"


def test_ervenyes_teljes_ablak():
    pts = _oras(168, meredekseg=-0.2, partial=True)
    veg = KEZD + timedelta(hours=168)
    r = regresszio.regresszio_egy_ablak(pts, KEZD.isoformat(), veg.isoformat(), 7)
    assert r["ervenyes"] and r["pontok_hianyzo"] == 0
    assert "se_meredekseg" in r and r["r2_masodlagos_autokorrelacio"] is True
    assert r["irany"] == "csokken"


def test_vegi_lyuk_latszik():
    # 144 lezárt pont, majd a végén 24h HIÁNYZIK — az ablakhoz mérve látszik
    pts = _oras(144)
    veg = KEZD + timedelta(hours=168)   # az EREDETI ablakvég, nem a csonkolt utolsó pont
    r = regresszio.regresszio_egy_ablak(pts, KEZD.isoformat(), veg.isoformat(), 7)
    assert r["ervenyes"] is True
    assert r["pontok_hianyzo"] == 24


# ── pontok_nem_nulla (a jel erőssége; a nullák éjszakai mintavételi artefaktumok, §8.3) ──
def test_pontok_nem_nulla_ervenyes():
    # 168 lezárt pont, ebből 163 NULLA + 5 nem-nulla (tüntetés-szerű eseményjelző);
    # ervenyes marad (168 >= MIN_PONT), de a jel erőssége csak 5.
    pts = [_pont(KEZD + timedelta(hours=i), 0) for i in range(168)]
    for i in (10, 40, 80, 120, 160):
        pts[i]["ertek"] = 100
    veg = KEZD + timedelta(hours=168)
    r = regresszio.regresszio_egy_ablak(pts, KEZD.isoformat(), veg.isoformat(), 7)
    assert r["ervenyes"] is True and r["pontok_hasznalt"] == 168
    assert r.get("pontok_nem_nulla") == 5


def test_pontok_nem_nulla_hibaagon_is():
    # szerződés-regularitás (§8.3): a mező ott van, ahol a pontok_hasznalt is — pl. a keves_pont ágon.
    pts = [_pont(KEZD + timedelta(hours=i), 0) for i in range(10)]
    for i in (2, 5, 8):
        pts[i]["ertek"] = 42
    r = regresszio.regresszio_egy_ablak(pts, KEZD.isoformat(), (KEZD + timedelta(hours=10)).isoformat(), 7)
    assert r["ervenyes"] is False and r["ok"] == "keves_pont"
    assert r.get("pontok_nem_nulla") == 3


# ── mini-9a: illesztes_vonal (két végpont-horgony) + se-flag ──────────────────
def test_illesztes_vonal_ket_vegpont():
    # ervenyes ág: két végpont-horgony {idopont_utc, ertek}, az első és UTOLSÓ LEZÁRT pontnál.
    # meredekseg=-0.07 SZÁNDÉKOS: y_veg = 50 - 0.07*167 = 38.31, azaz 2-tizedes végpont.
    # A korábbi -0.2 véletlenül 1-tizedes végpontot ad (16.6), azon egy adatréteg-kerekítés
    # LÁTHATATLAN marad (M2-mutációval igazolva) — a 2-tizedes végpont teszi élessé a
    # "nincs adatréteg-kerekítés, teljes float" szerződést.
    pts = _oras(168, meredekseg=-0.07, partial=True)
    veg = KEZD + timedelta(hours=168)
    r = regresszio.regresszio_egy_ablak(pts, KEZD.isoformat(), veg.isoformat(), 7)
    assert "illesztes_vonal" in r
    v = r["illesztes_vonal"]
    assert len(v) == 2
    assert set(v[0]) == {"idopont_utc", "ertek"} and set(v[1]) == {"idopont_utc", "ertek"}
    assert round(v[0]["ertek"], 6) == 50.0
    assert round(v[1]["ertek"], 6) == 38.31
    # explicit tiltás: az adatréteg NEM kerekíthet 1 tizedesre (38.31 != 38.3)
    assert round(v[1]["ertek"], 6) != round(v[1]["ertek"], 1)


def test_illesztes_vonal_zaropont_lezart():
    # a vonal UTOLSÓ pontja az utolsó LEZÁRT pont (T+167h), NEM a részleges záró (T+168h)
    pts = _oras(168, meredekseg=-0.2, partial=True)
    veg = KEZD + timedelta(hours=168)
    r = regresszio.regresszio_egy_ablak(pts, KEZD.isoformat(), veg.isoformat(), 7)
    v = r["illesztes_vonal"]
    assert v[0]["idopont_utc"] == KEZD.isoformat()
    assert v[1]["idopont_utc"] == (KEZD + timedelta(hours=167)).isoformat()
    assert v[1]["idopont_utc"] != (KEZD + timedelta(hours=168)).isoformat()


def test_se_masodlagos_flag():
    # a se_meredekseg ugyanúgy autokorreláció-torzított, mint az R² → önleíró flag, true
    pts = _oras(168, meredekseg=-0.2, partial=True)
    veg = KEZD + timedelta(hours=168)
    r = regresszio.regresszio_egy_ablak(pts, KEZD.isoformat(), veg.isoformat(), 7)
    assert r["se_masodlagos_autokorrelacio"] is True


# FIGYELEM: ez a teszt SZÁNDÉKOSAN NEM RED — regressziós őr a 4. tervdöntésre.
# Azt betonozza be, hogy az ÉRVÉNYTELEN ágra (ervenyes:false) NEM kerül illesztes_vonal
# (nincs vonal, amit rajzolni), és se-flag sem. Ne törölje senki "feleslegesként": ha valaki
# később a horgonyt/flaget az érvénytelen ágra is ráteszi, ennek a tesztnek EL KELL buknia.
def test_illesztes_vonal_csak_ervenyes():
    r = regresszio.regresszio_egy_ablak(_oras(10), KEZD.isoformat(),
                                        (KEZD + timedelta(hours=10)).isoformat(), 7)
    assert r["ervenyes"] is False and r["ok"] == "keves_pont"
    assert "illesztes_vonal" not in r
    assert "se_masodlagos_autokorrelacio" not in r


def test_nincs_adat():
    r = regresszio.regresszio_egy_ablak([], KEZD.isoformat(), (KEZD + timedelta(hours=168)).isoformat(), 7)
    assert r["ervenyes"] is False and r["ok"] == "nincs_adat"


# ── élettartam + összeállítás ────────────────────────────────────────────────
def _config(kifejezesek):
    tetel = [SimpleNamespace(kifejezes=k, domen="g", tipus="szintmero") for k in kifejezesek]
    return SimpleNamespace(modszertan_valtas="2026-07-30", osszes_kulcsszo=lambda: list(tetel))


def _uj_rek(kulcsszo, atlag=1.0):
    return {"kulcsszo": kulcsszo, "domen": "d", "tipus": "t", "atlag": atlag, "csucs": atlag,
            "ervenyes_pontok": 1, "nulla_pontok": 0, "ossz_pontok": 1}


def _tortenet(napok):
    return {"napok": [{"nap": d, "kulcsszavak": r} for d, r in sorted(napok.items())],
            "modszertan_valtas": "2026-07-30"}


def test_meres_kezdete_markerre_vagva():
    # 07-29 (pre-marker, új-alak) ÉS 07-30 → meres_kezdete = 07-30, NEM 07-29
    tort = _tortenet({"2026-07-29": [_uj_rek("állás")], "2026-07-30": [_uj_rek("állás")]})
    out = regresszio.regresszio_szamit({"kulcsszavak": {}}, tort, _config(["állás"]), "T")
    assert out["kulcsszavak"]["állás"]["meres_kezdete"] == "2026-07-30"


def test_horgonyos_only_szo_kimarad():
    tort = _tortenet({"2026-07-21": [{"kulcsszo": "MNB", "csoport": "gazd",
                                      "atlag": 3.0, "csucs": 3.0, "ervenyes_pontok": 1}]})
    out = regresszio.regresszio_szamit({"kulcsszavak": {}}, tort, _config(["állás"]), "T")
    assert "MNB" not in out["kulcsszavak"]


def test_eltavolitott_szo_aktiv_es_meres_vege():
    tort = _tortenet({"2026-07-30": [_uj_rek("régi")]})
    out = regresszio.regresszio_szamit({"kulcsszavak": {}}, tort, _config(["állás"]), "T")
    r = out["kulcsszavak"]["régi"]
    assert r["aktiv"] is False and r["meres_vege"] == "2026-07-30"
    assert r["domen"] == "d" and r["tipus"] == "t"


def test_2_het_nincs_lancolas_es_top_mezok():
    nyers = {"kulcsszavak": {"állás": [{"ablak_kezdet_utc": KEZD.isoformat(),
                                        "ablak_veg_utc": (KEZD + timedelta(hours=168)).isoformat(),
                                        "pontok": _oras(168, meredekseg=-0.2, partial=True)}]}}
    out = regresszio.regresszio_szamit(nyers, _tortenet({}), _config(["állás"]), "T")
    assert out["irany_kuszob"] == 1.0 and out["meredekseg_egyseg"] == "relatív pont / nap"
    iv = out["kulcsszavak"]["állás"]["intervallumok"]
    assert iv["2_het"] == {"ervenyes": False, "ok": "nincs_lancolas"}
    assert iv["1_het"]["ervenyes"] is True
    # mini-9a: az érvényes 1_het a teljes szerkezetben is hordozza a horgonyt + se-flaget
    assert "illesztes_vonal" in iv["1_het"]
    assert iv["1_het"]["se_masodlagos_autokorrelacio"] is True


def test_len_agnosztikus_3_es_20():
    for n in (3, 20):
        out = regresszio.regresszio_szamit({"kulcsszavak": {}}, _tortenet({}),
                                           _config([f"szo{i}" for i in range(n)]), "T")
        assert len(out["kulcsszavak"]) == n


# ── writer + valós integráció ────────────────────────────────────────────────
def test_regresszio_ir_visszaolvas(tmp_path):
    import json
    p = regresszio.regresszio_ir(tmp_path, {"szamitva_utc": "T", "kulcsszavak": {}})
    assert json.loads(p.read_text(encoding="utf-8"))["szamitva_utc"] == "T"


def test_valos_adatbol():
    import json
    from pathlib import Path
    from trendfigyelo import config as cfgmod
    DATA = Path(__file__).resolve().parent.parent / "docs" / "data"
    nyers = json.loads((DATA / "kulcsszo_nyers.json").read_text(encoding="utf-8"))
    tort = json.loads((DATA / "tortenet.json").read_text(encoding="utf-8"))
    cfg = cfgmod.betolt()
    out = regresszio.regresszio_szamit(nyers, tort, cfg, "2026-08-04T20:39:28+00:00")
    kk = out["kulcsszavak"]
    assert len(kk) == len(cfg.osszes_kulcsszo())
    for szo, v in kk.items():
        assert v["meres_kezdete"] == "2026-07-30" and v["aktiv"] is True
        assert v["intervallumok"]["1_het"]["ervenyes"] is True
        assert v["intervallumok"]["2_het"]["ok"] == "nincs_lancolas"


# ── Task 6a-1: _hianyzo_pontok(grid_step) ─────────────────────────────────────
# A 3600-hardkód helyett rács-paraméter. Az órás (grid_step=3600) bitre a régi.

def test_hianyzo_pontok_oras_azonos_a_regivel():
    # 160 lezárt órás pont egy 168 órás ablakban → 8 hiányzó, mint a _hianyzo_orak
    veg = KEZD + timedelta(hours=168)
    ts = [KEZD + timedelta(hours=i) for i in range(160)]
    assert regresszio._hianyzo_pontok(KEZD.isoformat(), veg.isoformat(), ts, 3600) == 8


def test_hianyzo_pontok_napi_5_hianyzo():
    # 85 lezárt NAPI pont egy 90 napos ablakban → 5 hiányzó (grid_step=86400)
    veg = KEZD + timedelta(days=90)
    ts = [KEZD + timedelta(days=i) for i in range(85)]
    assert regresszio._hianyzo_pontok(KEZD.isoformat(), veg.isoformat(), ts, 86400) == 5


def test_hianyzo_orak_wrapper_valtozatlan_SZANDEKOS_ZOLD():
    # SZÁNDÉKOS-ZÖLD: a _hianyzo_orak a refaktor UTÁN is 8-at ad (golden, guard)
    veg = KEZD + timedelta(hours=168)
    ts = [KEZD + timedelta(hours=i) for i in range(160)]
    assert regresszio._hianyzo_orak(KEZD.isoformat(), veg.isoformat(), ts) == 8


# ── Task 6a-2: _intervallumok(rekordok, racs) — rács-szűrés + farokszeletelés ──
def _rekord(kezd, veg, pontok):
    return {"ablak_kezdet_utc": kezd.isoformat(), "ablak_veg_utc": veg.isoformat(), "pontok": pontok}


def test_intervallumok_napi_szeleteles():
    # 90 lezárt NAPI pont (napok 0..89) + részleges a 90. napon; nominal=90, MIN_PONT=12
    veg = KEZD + timedelta(days=90)
    pontok = [_pont(KEZD + timedelta(days=i), 10 + 0.5 * i) for i in range(90)]
    pontok.append(_pont(veg, 60, reszleges=True))
    iv = regresszio._intervallumok([_rekord(KEZD, veg, pontok)], "nap")
    assert iv["1_het"]["ok"] == "keves_pont"          # ~7 pt < 12
    assert iv["2_het"]["ervenyes"] is True            # ~14 pt
    assert iv["1_ho"]["ervenyes"] is True             # ~30 pt
    assert iv["3_ho"]["ervenyes"] is True             # teljes 90 napos ablak
    assert iv["1_ev"]["ok"] == "nincs_lancolas"       # 365 > 90 → láncolás kellene


def test_intervallumok_heti_szeleteles():
    # 53 lezárt HETI pont (hét 0..52, nap 0..364) + részleges a 365. napon; nominal=365, MIN_PONT=7
    veg = KEZD + timedelta(days=365)
    pontok = [_pont(KEZD + timedelta(days=7 * i), 20 + 0.3 * i) for i in range(53)]
    pontok.append(_pont(veg, 30, reszleges=True))
    iv = regresszio._intervallumok([_rekord(KEZD, veg, pontok)], "het")
    assert iv["1_het"]["ok"] == "keves_pont"          # ~1 pt
    assert iv["2_het"]["ok"] == "keves_pont"          # ~2 pt
    assert iv["1_ho"]["ok"] == "keves_pont"           # ~4 pt < 7
    assert iv["3_ho"]["ervenyes"] is True             # ~13 heti pt
    assert iv["1_ev"]["ervenyes"] is True             # teljes 365 napos ablak, ~53 pt


def test_intervallumok_ora_valtozatlan_SZANDEKOS_ZOLD():
    # SZÁNDÉKOS-ZÖLD: ora rácson a régi viselkedés — 1_het érvényes, a többi nincs_lancolas
    veg = KEZD + timedelta(hours=168)
    iv = regresszio._intervallumok([_rekord(KEZD, veg, _oras(168, partial=True))], "ora")
    assert iv["1_het"]["ervenyes"] is True
    assert iv["2_het"]["ok"] == "nincs_lancolas" and iv["1_ev"]["ok"] == "nincs_lancolas"


# ── Task 6a-3: regresszio_masodlagos_szamit — a nap/het szavak regressziója ────
def test_masodlagos_szamit_racs_es_intervallumok():
    veg = KEZD + timedelta(days=90)
    pontok = [_pont(KEZD + timedelta(days=i), 10 + 0.5 * i) for i in range(90)]
    pontok.append(_pont(veg, 60, reszleges=True))
    masodlagos = {"kulcsszavak": {"albérlet": [{
        "racs": "nap", "lekerdezes_utc": veg.isoformat(),
        "ablak_kezdet_utc": KEZD.isoformat(), "ablak_veg_utc": veg.isoformat(), "pontok": pontok}]}}
    out = regresszio.regresszio_masodlagos_szamit(masodlagos, _tortenet({}), _config(["albérlet"]), "T")
    w = out["kulcsszavak"]["albérlet"]
    assert w["racs"] == "nap"                                  # a rács a rekordból
    assert w["intervallumok"]["3_ho"]["ervenyes"] is True       # a nap rács szerint számol
    assert w["intervallumok"]["1_ev"]["ok"] == "nincs_lancolas"


# ── Task 6a-4: esemenyjelzo → nincs illesztés, van szint (medián) ─────────────
def test_esemenyjelzo_skip_ok_es_szint():
    # tüntetés-szerű: tipus=esemenyjelzo → minden intervallum ok:"esemenyjelzo",
    # a szint a MEGJELENÍTETT sor nem-részleges értékeinek MEDIÁNJA (a backendben).
    veg = KEZD + timedelta(days=365)
    vals = [2, 4, 6, 8, 10]                                    # medián 6; a 99-es részleges kizárva
    pontok = [_pont(KEZD + timedelta(days=7 * i), vals[i]) for i in range(5)]
    pontok.append(_pont(veg, 99, reszleges=True))
    masodlagos = {"kulcsszavak": {"tüntetés": [{
        "racs": "het", "lekerdezes_utc": veg.isoformat(),
        "ablak_kezdet_utc": KEZD.isoformat(), "ablak_veg_utc": veg.isoformat(), "pontok": pontok}]}}
    cfg = SimpleNamespace(modszertan_valtas="2026-07-30",
                          osszes_kulcsszo=lambda: [SimpleNamespace(
                              kifejezes="tüntetés", domen="kz", tipus="esemenyjelzo")])
    out = regresszio.regresszio_masodlagos_szamit(masodlagos, _tortenet({}), cfg, "T")
    w = out["kulcsszavak"]["tüntetés"]
    assert w["szint"] == 6 and w["szint_modszer"] == "median"   # backend számolja
    assert w["intervallumok"]["1_ev"]["ok"] == "esemenyjelzo"   # nincs illesztés
    assert w["intervallumok"]["3_ho"]["ok"] == "esemenyjelzo"
    assert all(iv["ok"] == "esemenyjelzo" for iv in w["intervallumok"].values())
