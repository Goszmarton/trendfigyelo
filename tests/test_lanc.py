"""LANC-ORAS (Phase 4, §8.2) — órás láncolás Szelet 1: lancol + marker-szűrő + perzisztens I/O + guard,
és a _intervallumok 2_het+ láncolt szeletelése."""

import json
import os
from datetime import datetime, timedelta, timezone

from trendfigyelo import lanc, regresszio


def test_frissit_lanc_megszakadt_iras_megorzi_a_regi_fajlt(tmp_path, monkeypatch):
    # ATOMI-IRAS (a pótolhatatlan kulcsszo_lanc.json bekötés fedése): megszakadt kommit (os.replace) →
    # a régi lánc-fájl bájtjai sértetlenek, nincs temp szemét.
    fajl = tmp_path / lanc.FAJL
    fajl.write_text("SENTINEL-REGI-LANC", encoding="utf-8")     # a betolt_lanc parse-hibán {}-t ad, a fájl marad

    def _crash(*a, **k):
        raise OSError("kommit crash")
    monkeypatch.setattr(os, "replace", _crash)

    try:
        lanc.frissit_lanc(tmp_path, {})
    except OSError:
        pass
    assert fajl.read_text(encoding="utf-8") == "SENTINEL-REGI-LANC", "a régi lánc-fájl megsérült a megszakadt írásnál"
    assert not list(tmp_path.glob("*.tmp")), "maradt szemét temp fájl"


def _ablak(kezdet_iso, napok=7, skala=1.0, csucs=100):
    """169-ish órás pont: `napok`×24+1 óra `kezdet`-től; érték = skala×(csucs·háromszög), az utolsó reszleges."""
    t0 = datetime.fromisoformat(kezdet_iso)
    n = napok * 24 + 1
    pontok = []
    for i in range(n):
        e = round(skala * (csucs * (0.3 + 0.7 * (i % 24) / 24)))   # nem-nulla, órán belül változó
        pontok.append({"idopont_utc": (t0 + timedelta(hours=i)).isoformat(),
                       "ertek": e, "reszleges": (i == n - 1)})
    return {"ablak_kezdet_utc": t0.isoformat(),
            "ablak_veg_utc": (t0 + timedelta(hours=n - 1)).isoformat(), "pontok": pontok}


# --- RED 2: átfedés-skálázó ---
def test_lancol_atfedes_skalazo():
    # két ablak, a 2. FÉL skálán (Trends átnormált, magasabb csúcs) → a láncnak a KÖZÖS skálára kell húznia.
    w1 = _ablak("2026-08-01T00:00:00+00:00", napok=7, skala=1.0)
    w2 = _ablak("2026-08-02T00:00:00+00:00", napok=7, skala=0.5)   # átfed w1-gyel, fél skálán
    l = lanc.lancol([w1, w2])
    # a w2 UTOLSÓ (nem-átfedő) pontja a w1 skálájára húzva ≈ a w1-beli megfelelő órai érték (2× vissza)
    utolso = l["pontok"][-1]["ertek"]
    assert utolso > 60, f"a skálázó nem húzta vissza (fél skálán ~35 lenne): {utolso}"   # ~100·(...)·1, nem 0.5×


# --- RED 3: hiányzó nap → szakaszra bomlik ---
def test_lancol_hianyzo_nap_szakaszra_bomlik():
    w1 = _ablak("2026-08-01T00:00:00+00:00", napok=7)
    w3 = _ablak("2026-08-20T00:00:00+00:00", napok=7)   # NEM fed át w1-gyel (>7 nap rés)
    l = lanc.lancol([w1, w3])
    # nincs érvényes átfedés → a lánc az ÚJ szakasztól indul (w3), a régi (w1) NEM ér bele
    assert l["szakasz_kezdet_utc"][:10] == "2026-08-20", l["szakasz_kezdet_utc"]
    assert l["ablak_kezdet_utc"][:10] == "2026-08-20"   # csak a friss szakasz


# --- RED 4: marker (modszertan_valtas) abszolút határ ---
def test_marker_szur_kizarja_a_marker_elottit():
    w = _ablak("2026-07-27T00:00:00+00:00", napok=7)   # 07-27 → 08-03, átível a 07-30 markeren
    szurt = lanc._marker_szur([w], "2026-07-30")
    datumok = {p["idopont_utc"][:10] for p in szurt[0]["pontok"]}
    assert min(datumok) == "2026-07-30", f"a marker előtti pont bent maradt: {min(datumok)}"
    assert "2026-07-27" not in datumok and "2026-07-29" not in datumok


# --- RED 1: órás 2_het a láncból ERVENYES (nem nincs_lancolas) ---
def _nyers_rek_ora():
    return [_ablak("2026-08-11T00:00:00+00:00", napok=7)]   # egy friss órás pillanatkép (1_het bázisa)


def test_oras_2_het_lancolt_ervenyes(monkeypatch):
    # a láncolás LOGIKÁJA a GATE-en KÍVÜL (a Szelet 2 aktiválja élesben): gate OFF → 2_het ervenyes a láncból.
    monkeypatch.setattr(regresszio, "LANC_2HET_GATE", False)
    lanc_sorozat = lanc.lancol([_ablak("2026-08-01T00:00:00+00:00", napok=17)])   # 17 napos lánc (≥14)
    iv = regresszio._intervallumok(_nyers_rek_ora(), "ora", lanc=lanc_sorozat)
    assert iv["2_het"]["ervenyes"] is True, iv["2_het"]           # a láncból szeletelve ERVENYES
    assert iv["2_het"].get("ok") != "nincs_lancolas"


def test_oras_2het_gate_amig_frontend_nem_olvas():
    # IDEIGLENES GATE-SZERZŐDÉS — a Szelet 2 (frontend) TÖRLI EZT A TESZTET ÉS a regresszio.LANC_2HET_GATE-et.
    # Amíg a frontend nem olvassa a kulcsszo_lanc.json-t (a rajzolt pontokat a nyers 7-napos ablakából veszi,
    # a lánc-veg nem egyezik → kirajzolhatatlan), az órás 2_het MARADJON nincs_lancolas (08-17-i ismert-jó
    # megjelenítés). A lánc ADATA (frissit_lanc → kulcsszo_lanc.json) KÖZBEN tovább épül. Default GATE=True.
    lanc_sorozat = lanc.lancol([_ablak("2026-08-01T00:00:00+00:00", napok=17)])   # van lánc (≥14 nap)
    iv = regresszio._intervallumok(_nyers_rek_ora(), "ora", lanc=lanc_sorozat)
    assert iv["2_het"]["ervenyes"] is False            # GATE: a lánc ELLENÉRE nem ervenyes
    assert iv["2_het"]["ok"] == "nincs_lancolas"        # a 08-17-i megjelenítési szerződés


# --- SZÁNDÉKOS-ZÖLD: órás 1_het VÁLTOZATLAN (farokszelet, a lánc NEM érinti a ≤7 napot) ---
def test_oras_1_het_valtozatlan_SZANDEKOS_ZOLD():
    rek = _nyers_rek_ora()
    lanc_sorozat = lanc.lancol([_ablak("2026-08-01T00:00:00+00:00", napok=17)])
    iv_lanccal = regresszio._intervallumok(rek, "ora", lanc=lanc_sorozat)
    iv_lanc_nelkul = regresszio._intervallumok(rek, "ora", lanc=None)
    assert iv_lanccal["1_het"] == iv_lanc_nelkul["1_het"]        # az 1_het bájt-azonos lánccal és anélkül


# --- RED 5: sérült/nem-épülő bővítés NEM írja felül a tárolt láncot + FIGYELEM ---
def test_frissit_lanc_serult_nem_irja_felul(tmp_path, capsys):
    tarolt = lanc.lancol([_ablak("2026-08-01T00:00:00+00:00", napok=10)])   # tárolt lánc: 08-01 → 08-11
    (tmp_path / lanc.FAJL).write_text(json.dumps({"kulcsszavak": {"benzin": tarolt}}), encoding="utf-8")
    # friss ablak, ami NEM ér vissza a tárolt lánc végéig (>7 nap rés) → nem épül, guard
    friss = {"benzin": [_ablak("2026-08-25T00:00:00+00:00", napok=7)]}
    ki = lanc.frissit_lanc(tmp_path, friss)
    assert ki["benzin"]["ablak_kezdet_utc"] == tarolt["ablak_kezdet_utc"]   # a tárolt lánc ÉRINTETLEN
    assert ki["benzin"]["ablak_veg_utc"] == tarolt["ablak_veg_utc"]
    assert "ÉRINTETLEN" in capsys.readouterr().out                          # HANGOS FIGYELEM


# --- SZÁNDÉKOS-ZÖLD: perzisztens — a bővítés a TÁROLT láncra épül (retenció-független) ---
def test_frissit_lanc_perzisztens_bovit_SZANDEKOS_ZOLD(tmp_path):
    tarolt = lanc.lancol([_ablak("2026-08-01T00:00:00+00:00", napok=10)])   # 08-01 → 08-11
    (tmp_path / lanc.FAJL).write_text(json.dumps({"kulcsszavak": {"benzin": tarolt}}), encoding="utf-8")
    friss = {"benzin": [_ablak("2026-08-05T00:00:00+00:00", napok=7)]}       # 08-05 → 08-11T23 (lezárt), átfed
    lanc.frissit_lanc(tmp_path, friss)
    # a LEMEZRE ÍRT láncot olvassuk vissza (NEM a visszatérési értéket) — a gate mellett is ÍR (a lánc ADATA
    # nem áll le); egy write-kihagyó mutáció ezt PIROSÍTJA (a fájl a régi, nem-bővült marad).
    lemez = json.loads((tmp_path / lanc.FAJL).read_text(encoding="utf-8"))["kulcsszavak"]["benzin"]
    assert lemez["ablak_kezdet_utc"] == tarolt["ablak_kezdet_utc"]           # a kezdet MEGMARAD (retenció-független)
    assert lemez["ablak_veg_utc"] > tarolt["ablak_veg_utc"]                  # ÉS a FÁJL bővült a friss lezárt farkáig
    assert lemez["ablak_veg_utc"][:10] == "2026-08-11"                       # 08-10 → 08-11 (+1 nap)
