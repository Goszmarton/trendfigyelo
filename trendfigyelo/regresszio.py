"""Kulcsszó-regresszió: a kulcsszo_regresszio.json SZÁRMAZTATOTT nézet előállítása.

A regresszió az exportban, Pythonban számolódik (spec 8.3); a frontend csak rajzol.
Bemenet a kulcsszo_nyers.json lezárt (nem részleges) órás pontjai + a halmozódó
tortenet.json + a mai config. Nulla extra Google-hívás.

KORSZAK: kizárólag a modszertan_valtas dönti el. A rekord-ALAKBÓL TILOS a korszakra
következtetni: a rekord-alak töréspontja (2026-07-29) egy nappal a marker (2026-07-30)
ELŐTT van (Task 2 lelet). A meres_kezdete ezért a markerre van vágva.

HORGONYOS-ONLY SZAVAK: a modszertan_valtas előtti kísérleti lista szavai (pl. MNB,
kamat), amelyek sosem jelennek meg a marker után és nincsenek a configban, ebből a
fájlból KIMARADNAK. Ez NEM adattörlés — a tortenet.json változatlanul tartalmazza
őket; a regresszió csak egy szóló-korszakra szűkített, származtatott nézet.

9b FIGYELEM — meres_kezdete null + 1_het ervenyes EGYÜTT lehetséges: egy ma felvett,
ma mért szó a kulcsszo_nyers-ben már van (1_het ervenyes lehet), de a tortenet csak
TELJES napokat tart (spec 1.3), ezért aznap még nem szerepel → meres_kezdete null.
Ez elsőre ellentmondásos, de helyes; a 9b-nek kezelnie kell (a meres_kezdete másnap
frissül, amikor a mai nap teljes napként bekerül a tortenet-be).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import json_export

INTERVALLUMOK = {"1_het": 7, "2_het": 14, "1_ho": 30, "3_ho": 90, "1_ev": 365}
MIN_PONT = 24
IRANY_KUSZOB = 1.0                          # relatív pont / nap
MEREDEKSEG_EGYSEG = "relatív pont / nap"
R2_MEGJEGYZES = ("Az R² autokorrelált órás soron számolt — MÁSODLAGOS; az elsődleges a "
                 "meredekség és az irány (spec 4.1). Az r2_masodlagos_autokorrelacio ezt jelzi. "
                 "A se_meredekseg (OLS standard hiba) UGYANEZEN autokorreláció miatt szintén "
                 "MÁSODLAGOS és torzított (lefelé) — a se_masodlagos_autokorrelacio jelzi; a "
                 "felület NEM írja ki konfidencia-sávként.")


def _dt(iso):
    return datetime.fromisoformat(iso)


def _illesztes(xs, ys):
    """Legkisebb négyzetek. Visszaad: (meredekseg, METSZET, r2, se_meredekseg).

    A metszet (a = my - b*mx) itt, EGY forrásból számolódik — a hívó NE számolja
    újra (divergencia-kockázat). Degenerált eset (nincs x-variancia, sxx == 0) →
    (None, None, None, None), hogy a hívó NE építsen belőle ervenyes:true rekordot.
    """
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None, None, None, None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    b = sxy / sxx
    a = my - b * mx                                        # metszet (y az x=0-nál)
    r2 = (sxy * sxy) / (sxx * syy) if syy > 0 else 0.0
    sse = max(syy - b * sxy, 0.0)                          # maradék négyzetösszeg
    se = (sse / ((n - 2) * sxx)) ** 0.5 if n > 2 else 0.0
    return b, a, r2, se


def _irany(meredekseg):
    if abs(meredekseg) < IRANY_KUSZOB:
        return "stagnal"
    return "novekszik" if meredekseg > 0 else "csokken"


def _hianyzo_orak(ablak_kezdet_utc, ablak_veg_utc, lezart_ts):
    """A hiányzó lezárt órás slotok száma AZ ABLAKHOZ mérve (nem csak a pontok közt).

    A [kezdet, veg) órás rács slotjai a várt lezárt pontok (a veg = részleges slot,
    kizárva). Így az eleji ÉS a végi csonkolás is látszik, nem csak a belső lyuk.
    """
    kezd = _dt(ablak_kezdet_utc)
    veg = _dt(ablak_veg_utc)
    vart = round((veg - kezd).total_seconds() / 3600)
    return max(vart - len(lezart_ts), 0)


def regresszio_egy_ablak(pontok, ablak_kezdet_utc, ablak_veg_utc, ablak_hossz_nap):
    """Egy intervallum mérőszámai EGY szó EGY ablakának órás pontjaiból.

    A reszleges:true pont(ok) kihagyva (spec 8.3). ervenyes = pontok_hasznalt >= MIN_PONT
    ÉS span >= ablak_hossz_nap/2. Ok-kódok: nincs_adat / keves_pont / degeneralt / rovid_span.
    """
    lezart = sorted((p for p in pontok if not p.get("reszleges")), key=lambda p: p["idopont_utc"])
    kihagyva = len(pontok) - len(lezart)
    if not lezart:
        return {"ervenyes": False, "ok": "nincs_adat"}
    n = len(lezart)
    nem_nulla = sum(1 for p in lezart if p["ertek"] != 0)   # a jel erőssége (§8.3): a nullák éjszakai artefaktumok
    if n < MIN_PONT:
        return {"ervenyes": False, "ok": "keves_pont",
                "pontok_hasznalt": n, "pontok_nem_nulla": nem_nulla,
                "pontok_kihagyva_reszleges": kihagyva}
    ts = [_dt(p["idopont_utc"]) for p in lezart]
    x0 = ts[0]
    xs = [(t - x0).total_seconds() / 86400 for t in ts]
    ys = [p["ertek"] for p in lezart]
    b, a, r2, se = _illesztes(xs, ys)
    if b is None:                                          # degenerált: nincs x-variancia
        return {"ervenyes": False, "ok": "degeneralt",
                "pontok_hasznalt": n, "pontok_nem_nulla": nem_nulla,
                "pontok_kihagyva_reszleges": kihagyva}
    span_nap = (ts[-1] - ts[0]).total_seconds() / 86400
    if span_nap < ablak_hossz_nap / 2:
        return {"ervenyes": False, "ok": "rovid_span",
                "pontok_hasznalt": n, "pontok_nem_nulla": nem_nulla,
                "pontok_kihagyva_reszleges": kihagyva}
    # A regressziós vonal két végpont-horgonya: az ELSŐ és UTOLSÓ LEZÁRT pont EREDETI
    # idopont_utc-jénél (a részleges záró NEM horgony → a vonal megáll előtte). Az ertek
    # TELJES float, adatréteg-kerekítés NÉLKÜL (szemben a meredekseg_nap/se/r2 kerekítéssel):
    # a horgony a görbe végpontjához illeszkedik, a MEGJELENÍTÉST a frontend kerekíti.
    illesztes_vonal = [
        {"idopont_utc": lezart[0]["idopont_utc"], "ertek": a + b * xs[0]},
        {"idopont_utc": lezart[-1]["idopont_utc"], "ertek": a + b * xs[-1]},
    ]
    return {
        "ervenyes": True,
        "meredekseg_nap": round(b, 3),
        "se_meredekseg": round(se, 4),
        "se_masodlagos_autokorrelacio": True,              # az se ugyanúgy autokorreláció-torzított, mint az R²
        "irany": _irany(b),
        "r2": round(r2, 3),
        "r2_masodlagos_autokorrelacio": True,
        "ablak_kezdet_utc": ablak_kezdet_utc,
        "ablak_veg_utc": ablak_veg_utc,
        "pontok_hasznalt": n,
        "pontok_nem_nulla": nem_nulla,
        "pontok_kihagyva_reszleges": kihagyva,
        "pontok_hianyzo": _hianyzo_orak(ablak_kezdet_utc, ablak_veg_utc, ts),
        "illesztes_vonal": illesztes_vonal,
    }


def _domen_tipus(szo, aktivak, napok):
    """domen/tipus: config ha aktív; különben az utolsó új-alakú tortenet-rekordból; különben null."""
    if szo in aktivak:
        t = aktivak[szo]
        return t.domen, t.tipus
    for _, rek in reversed(napok):
        if "domen" in rek and "tipus" in rek:
            return rek["domen"], rek["tipus"]
    return None, None


def _intervallumok(nyers_rekordok):
    ki = {}
    if nyers_rekordok:
        rek = max(nyers_rekordok, key=lambda r: r["ablak_veg_utc"])     # a legfrissebb pillanatkép
        ki["1_het"] = regresszio_egy_ablak(rek["pontok"], rek["ablak_kezdet_utc"],
                                           rek["ablak_veg_utc"], INTERVALLUMOK["1_het"])
    else:
        ki["1_het"] = {"ervenyes": False, "ok": "nincs_adat"}
    # 2_het+ : láncolás Phase 4 (spec 7.2/8.2). A napi tortenet-aggregátum NEM forrás (1.4):
    # a napi átlagok naponként külön normalizáltak, nem összemérhetők. A gomb a láncolástól
    # függ, NEM a naptártól — 14 szóló nap önmagában nem nyitja ki.
    for kulcs in ("2_het", "1_ho", "3_ho", "1_ev"):
        ki[kulcs] = {"ervenyes": False, "ok": "nincs_lancolas"}
    return ki


def regresszio_szamit(nyers, tortenet, config, szamitva_utc):
    """A teljes kulcsszo_regresszio.json szerkezet. Nulla extra Google-hívás.

    Szóhalmaz: a tortenet marker-utáni (>= modszertan_valtas) szavai ∪ a config szavai.
    A horgonyos-only szavak (csak marker előtt, nem config) KIMARADNAK.
    """
    marker = config.modszertan_valtas
    aktivak = {t.kifejezes: t for t in config.osszes_kulcsszo()}
    napok_szonkent = {}
    for nap in tortenet.get("napok", []):
        d = nap["nap"]
        if marker is not None and d < marker:      # kanonikus YYYY-MM-DD → lexikografikus = kronológiai
            continue
        for rek in nap["kulcsszavak"]:
            napok_szonkent.setdefault(rek["kulcsszo"], []).append((d, rek))

    ki = {}
    for szo in sorted(set(aktivak) | set(napok_szonkent)):
        napok = sorted(napok_szonkent.get(szo, []), key=lambda x: x[0])
        aktiv = szo in aktivak
        domen, tipus = _domen_tipus(szo, aktivak, napok)
        ki[szo] = {
            "meres_kezdete": napok[0][0] if napok else None,
            "meres_vege": None if aktiv else (napok[-1][0] if napok else None),
            "aktiv": aktiv,
            "domen": domen,
            "tipus": tipus,
            "intervallumok": _intervallumok(nyers.get("kulcsszavak", {}).get(szo)),
        }
    return {
        "szamitva_utc": szamitva_utc,
        "meredekseg_egyseg": MEREDEKSEG_EGYSEG,
        "irany_kuszob": IRANY_KUSZOB,
        "megjegyzes": R2_MEGJEGYZES,
        "kulcsszavak": ki,
    }


def regresszio_ir(docs_data, adat) -> Path:
    return json_export._ir_json(Path(docs_data) / "kulcsszo_regresszio.json", adat)
