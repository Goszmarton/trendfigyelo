import json

from trendfigyelo import kategoriak


def _t(kifejezes, temak=None):
    """Trend-elem; temak=None → NINCS temak kulcs (3a előtti / vegyes eset)."""
    e = {"kifejezes": kifejezes}
    if temak is not None:
        e["temak"] = temak
    return e


def test_merve_true_alap_aggregalas():
    trendek = [_t("a", ["Sports"]), _t("b", ["Health"]), _t("c", ["Sports"])]
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["merve"] is True
    assert r["nap"] == "2026-08-10"
    assert r["lista_hossz"] == 3
    assert r["kategoriak"] == {"Sports": 2, "Health": 1}
    assert r["kategoria_nelkul"] == 0
    assert r["lista_kategoriaval"] == 3


def test_multi_kategoria_tobbszor_szamit():
    # egy elem két temak → mindkettőben +1; az összeg meghaladhatja a lista_hossz-t
    trendek = [_t("a", ["Business and Finance", "Health"])]
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["kategoriak"] == {"Business and Finance": 1, "Health": 1}
    assert sum(r["kategoriak"].values()) > r["lista_hossz"]
    assert r["lista_kategoriaval"] == 1


def test_kategoria_nelkul_ures_es_hianyzo():
    # temak=[] ÉS hiányzó temak kulcs is a kategoria_nelkul-ba esik
    trendek = [_t("a", ["Sports"]), _t("b", []), _t("c")]   # c: nincs temak kulcs
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["merve"] is True
    assert r["kategoria_nelkul"] == 2
    assert r["lista_kategoriaval"] == 1
    assert r["kategoriak"] == {"Sports": 1}


def test_other_valodi_kategoria_nem_gyujto():
    trendek = [_t("a", ["Other"]), _t("b", ["Sports"])]
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["kategoriak"]["Other"] == 1
    assert r["kategoria_nelkul"] == 0


def test_lista_hossz_invarians():
    trendek = [_t("a", ["Sports"]), _t("b", []), _t("c", ["Health", "Law"]), _t("d")]
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["lista_hossz"] == r["lista_kategoriaval"] + r["kategoria_nelkul"]


def test_harom_a_elotti_nap_none():
    # egyetlen elemnek sincs "temak" kulcsa (3a előtti korszak) → None (kihagyás)
    trendek = [{"kifejezes": "a", "volumen": "1000"}, {"kifejezes": "b"}]
    assert kategoriak.kategoria_aggregatum("2026-07-28", trendek) is None


def test_nincs_kategoria_adat_merve_false():
    # a temak kulcs JELEN, de minden érték üres → merve:false, ok, nincs kategoriak
    trendek = [_t("a", []), _t("b", []), _t("c", [])]
    r = kategoriak.kategoria_aggregatum("2026-08-12", trendek)
    assert r["merve"] is False
    assert r["ok"] == "nincs_kategoria_adat"
    assert r["lista_hossz"] == 3
    assert "kategoriak" not in r


def test_vegyes_nap_merve_true():
    # néhány elemen van (nem-üres) temak kulcs, néhányon nincs → merve:true,
    # a kulcs nélküli elemek kategoria_nelkul-ban (nem None, nem merve:false)
    # MEGJEGYZÉS: ez ELMÉLETI eset — a valós pipeline sosem állít elő "vegyes"
    # temak-jelenlétet egy napon belül: a top_trend_struktura minden elemre
    # ráteszi a temak kulcsot, vagy (3a előtti napon) egyikre sem; a teszt itt
    # a függvény defenzív viselkedését dokumentálja, nem egy valós bemenetet.
    trendek = [_t("a", ["Sports"]), _t("b"), _t("c")]   # b,c: nincs temak kulcs
    r = kategoriak.kategoria_aggregatum("2026-08-10", trendek)
    assert r["merve"] is True
    assert r["kategoria_nelkul"] == 2
    assert r["kategoriak"] == {"Sports": 1}


def _napi_fajl(napok_mappa, nap_iso, trendek):
    napok_mappa.mkdir(parents=True, exist_ok=True)
    (napok_mappa / f"{nap_iso}.json").write_text(
        json.dumps({"nap": nap_iso, "trendek": trendek}, ensure_ascii=False), encoding="utf-8")


def _index(napok_mappa, napok):
    napok_mappa.mkdir(parents=True, exist_ok=True)
    (napok_mappa / "index.json").write_text(json.dumps({"napok": napok}), encoding="utf-8")


def test_kategoriak_ir_tukor_harom_csoport(tmp_path):
    docs_data = tmp_path / "docs" / "data"
    napok = docs_data / "napok"
    _napi_fajl(napok, "2026-07-28", [_t("regi")])                     # 3a előtti: nincs temak
    _napi_fajl(napok, "2026-08-10", [_t("a", ["Sports"]), _t("b", ["Health"])])
    _napi_fajl(napok, "2026-08-12", [_t("x", []), _t("y", [])])       # RSS-only: mind []
    _index(napok, ["2026-07-28", "2026-08-10", "2026-08-12"])
    kategoriak.kategoriak_ir(docs_data)
    adat = json.loads((docs_data / "kategoriak.json").read_text(encoding="utf-8"))
    napok_ki = adat["napok"]
    assert [n["nap"] for n in napok_ki] == ["2026-08-10", "2026-08-12"]   # 07-28 kihagyva, rendezett
    assert napok_ki[0]["merve"] is True
    assert napok_ki[0]["kategoriak"] == {"Sports": 1, "Health": 1}
    assert napok_ki[1]["merve"] is False and napok_ki[1]["ok"] == "nincs_kategoria_adat"


def test_kategoriak_ir_hianyzo_napi_fajl_kihagyva(tmp_path):
    # index-ben szereplő, de hiányzó fájlú nap (mint 2026-08-06) NEM kap bejegyzést
    docs_data = tmp_path / "docs" / "data"
    napok = docs_data / "napok"
    _napi_fajl(napok, "2026-08-10", [_t("a", ["Sports"])])
    _index(napok, ["2026-08-06", "2026-08-10"])                       # 08-06 fájl nincs
    kategoriak.kategoriak_ir(docs_data)
    adat = json.loads((docs_data / "kategoriak.json").read_text(encoding="utf-8"))
    assert [n["nap"] for n in adat["napok"]] == ["2026-08-10"]


def test_kategoriak_ir_idempotens(tmp_path):
    docs_data = tmp_path / "docs" / "data"
    napok = docs_data / "napok"
    _napi_fajl(napok, "2026-08-10", [_t("a", ["Sports"])])
    _index(napok, ["2026-08-10"])
    kategoriak.kategoriak_ir(docs_data)
    elso = (docs_data / "kategoriak.json").read_text(encoding="utf-8")
    kategoriak.kategoriak_ir(docs_data)
    masodik = (docs_data / "kategoriak.json").read_text(encoding="utf-8")
    assert elso == masodik
