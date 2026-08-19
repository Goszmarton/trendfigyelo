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

import statistics
from datetime import datetime, timedelta
from pathlib import Path

from . import json_export

INTERVALLUMOK = {"1_het": 7, "2_het": 14, "1_ho": 30, "3_ho": 90, "1_ev": 365}

# LANC-ORAS GATE (IDEIGLENES — a Szelet 2 [frontend] TÖRLI). A lánc ADATA (kulcsszo_lanc.json) tovább épül a
# frissit_lanc-ban; CSAK a MEGJELENÍTÉSI szerződést tartjuk vissza: amíg a frontend nem olvassa a láncot (a
# rajzolt pontokat a kulcsszo_nyers.json 7-napos ablakából veszi, a lánc-veg NEM egyezik), az órás 2_het+ NE
# legyen ervenyes → maradjon "nincs_lancolas", a 08-17-i ismert-jó megjelenítés. ERVENYES-ROUTING: az ervenyes
# flag a frontend elágazását vezérli (egyesitett_reg), ezért ez FRONTEND-szerződés, nem tiszta backend-állapot.
LANC_2HET_GATE = True
MIN_PONT = 24                               # ora: 168/7 (a 7 napos ablak 1/7-e)
# rács-tudatos regresszió (Task 6a): a rács szerinti slot-hossz és a rács-arányos
# MIN_PONT = ⌊ablak_pontszám/7⌋ (ora 24 VÁLTOZATLAN / nap 12 / het 7); a RACS_ABLAK_NAP
# a rács természetes ablaka (a "nincs_lancolas" határa üres adatnál).
RACS_GRID_STEP = {"ora": 3600, "nap": 86400, "het": 604800}
RACS_ABLAK_NAP = {"ora": 7, "nap": 90, "het": 365}
RACS_MIN_PONT = {"ora": 24, "nap": 12, "het": 7}
IRANY_KUSZOB = 1.0                          # relatív pont / nap — ÓRÁS ág (kalibrálva: 875ea1a)
# IRANY-KUSZOB: a per-nap küszöb a hosszú nap/het ablakon degenerál (365 nap × 1.0/nap = 365
# pont kellene, a skála max 100 → az 1_ev matematikailag holt irány-ág). A nap/het ág ezért
# ABLAK-RELATÍV: a címke a TELJES elmozduláson (|meredekseg × span_nap| pont = % a 0-100
# skálán) dől el. A ~7 pont az órás kalibráció átvitele (1.0/nap × 7 napos ablak); ELSŐ
# közelítés, nem lezárt kalibráció (kis nap/het minta — több-napos adat után újranyílik).
ELMOZDULAS_KUSZOB = 7.0                      # relatív pont (a 0-100 skála %-a), nap/het ág
RACS_ELMOZDULAS_KUSZOB = {"nap": ELMOZDULAS_KUSZOB, "het": ELMOZDULAS_KUSZOB}  # ora hiányzik → None
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


def _irany_elmozdulas(meredekseg, span_nap, kuszob):
    """Ablak-relatív iránycímke: a TELJES illesztett elmozduláson dönt (nap/het ág)."""
    elmozdulas = meredekseg * span_nap
    if abs(elmozdulas) < kuszob:
        return "stagnal"
    return "novekszik" if elmozdulas > 0 else "csokken"


def _hianyzo_pontok(ablak_kezdet_utc, ablak_veg_utc, lezart_ts, grid_step):
    """A hiányzó lezárt slotok száma AZ ABLAKHOZ mérve (nem csak a pontok közt).

    A [kezdet, veg) rács slotjai (grid_step mp) a várt lezárt pontok (a veg = részleges
    slot, kizárva). Így az eleji ÉS a végi csonkolás is látszik. A grid_step a rácstól
    függ (ora 3600 / nap 86400 / het 604800) → rács-független számlálás.
    """
    kezd = _dt(ablak_kezdet_utc)
    veg = _dt(ablak_veg_utc)
    vart = round((veg - kezd).total_seconds() / grid_step)
    return max(vart - len(lezart_ts), 0)


def _hianyzo_orak(ablak_kezdet_utc, ablak_veg_utc, lezart_ts):
    """Órás wrapper a _hianyzo_pontok fölött (grid_step=3600) — bitre a régi viselkedés."""
    return _hianyzo_pontok(ablak_kezdet_utc, ablak_veg_utc, lezart_ts, 3600)


def regresszio_egy_ablak(pontok, ablak_kezdet_utc, ablak_veg_utc, ablak_hossz_nap,
                         grid_step=3600, min_pont=MIN_PONT, elmozdulas_kuszob=None):
    """Egy intervallum mérőszámai EGY szó EGY ablakának pontjaiból.

    A reszleges:true pont(ok) kihagyva (spec 8.3). ervenyes = pontok_hasznalt >= min_pont
    ÉS span >= ablak_hossz_nap/2. Ok-kódok: nincs_adat / keves_pont / degeneralt / rovid_span.
    A grid_step/min_pont a RÁCSTÓL függ (Task 6a); a defaultok (3600, 24) = az órás viselkedés,
    bitre változatlan. A hiányzó-slot számlálás a grid_step szerint (nap/het is helyes).
    """
    lezart = sorted((p for p in pontok if not p.get("reszleges")), key=lambda p: p["idopont_utc"])
    kihagyva = len(pontok) - len(lezart)
    if not lezart:
        return {"ervenyes": False, "ok": "nincs_adat"}
    n = len(lezart)
    nem_nulla = sum(1 for p in lezart if p["ertek"] != 0)   # a jel erőssége (§8.3): a nullák éjszakai artefaktumok
    if n < min_pont:
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
        "irany": _irany(b) if elmozdulas_kuszob is None     # None (órás default) → per-nap küszöb, bitre változatlan
                 else _irany_elmozdulas(b, span_nap, elmozdulas_kuszob),  # nap/het → ablak-relatív
        "r2": round(r2, 3),
        "r2_masodlagos_autokorrelacio": True,
        "ablak_kezdet_utc": ablak_kezdet_utc,
        "ablak_veg_utc": ablak_veg_utc,
        "pontok_hasznalt": n,
        "pontok_nem_nulla": nem_nulla,
        "pontok_kihagyva_reszleges": kihagyva,
        "pontok_hianyzo": _hianyzo_pontok(ablak_kezdet_utc, ablak_veg_utc, ts, grid_step),
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


def _intervallumok(nyers_rekordok, racs="ora", lanc=None):
    """A rács intervallumai a LEGFRISSEBB pillanatképből, farokszeleteléssel.

    A rács természetes ablakán (RACS_ABLAK_NAP) TÚLNYÚLÓ intervallum → nincs_lancolas
    (egyetlen pillanatkép nem fedi; órásnál a 2_het+ ide esik, spec 8.2). Az ablakon
    BELÜLI intervallumot a pillanatkép farkából szeleteljük (nincs láncolás, nincs új
    hívás); a teljes ablakot lefedő intervallum a rekord eredeti határaival megy (ora
    1_het bitre változatlan). A rács adja a grid_step-et és a MIN_PONT-ot (Task 6a).
    """
    grid_step = RACS_GRID_STEP.get(racs, 3600)
    min_pont = RACS_MIN_PONT.get(racs, MIN_PONT)
    elmozdulas_kuszob = RACS_ELMOZDULAS_KUSZOB.get(racs)     # ora → None (per-nap, változatlan)
    nominal = RACS_ABLAK_NAP.get(racs, 7)
    rek = max(nyers_rekordok, key=lambda r: r["ablak_veg_utc"]) if nyers_rekordok else None
    if rek is not None:
        veg_dt = _dt(rek["ablak_veg_utc"])
        ablak_nap = round((veg_dt - _dt(rek["ablak_kezdet_utc"])).total_seconds() / 86400)
    ki = {}
    for kulcs, hossz in INTERVALLUMOK.items():
        if hossz > nominal:                          # túlnyúlik a rács ablakán → LÁNCOLÁS (LANC-ORAS, §8.2)
            if lanc and not LANC_2HET_GATE and lanc.get("pontok") and \
                    (_dt(lanc["ablak_veg_utc"]) - _dt(lanc["ablak_kezdet_utc"])).days >= hossz:
                lveg = _dt(lanc["ablak_veg_utc"])
                lkezd = lveg - timedelta(days=hossz)   # a LÁNCOLT sorozat farkából `hossz` nap
                szelet = [p for p in lanc["pontok"] if _dt(p["idopont_utc"]) >= lkezd]
                ki[kulcs] = regresszio_egy_ablak(szelet, lkezd.isoformat(), lanc["ablak_veg_utc"], hossz,
                                                 grid_step=grid_step, min_pont=min_pont,
                                                 elmozdulas_kuszob=elmozdulas_kuszob)
            else:                                      # nincs lánc VAGY túl rövid → nincs_lancolas
                ki[kulcs] = {"ervenyes": False, "ok": "nincs_lancolas"}
        elif rek is None:
            ki[kulcs] = {"ervenyes": False, "ok": "nincs_adat"}
        elif hossz >= ablak_nap:                      # a teljes pillanatkép — eredeti határok
            ki[kulcs] = regresszio_egy_ablak(rek["pontok"], rek["ablak_kezdet_utc"],
                                             rek["ablak_veg_utc"], hossz,
                                             grid_step=grid_step, min_pont=min_pont,
                                             elmozdulas_kuszob=elmozdulas_kuszob)
        else:                                         # farokszelet: az utolsó `hossz` nap
            kezdet_dt = veg_dt - timedelta(days=hossz)
            szelet = [p for p in rek["pontok"] if _dt(p["idopont_utc"]) >= kezdet_dt]
            ki[kulcs] = regresszio_egy_ablak(szelet, kezdet_dt.isoformat(),
                                             rek["ablak_veg_utc"], hossz,
                                             grid_step=grid_step, min_pont=min_pont,
                                             elmozdulas_kuszob=elmozdulas_kuszob)
    return ki


_ESEMENYJELZO_TREND_MEZOK = (
    "meredekseg_nap", "se_meredekseg", "se_masodlagos_autokorrelacio",
    "irany", "r2", "r2_masodlagos_autokorrelacio", "illesztes_vonal",
)


def _szint_intervallum(iv):
    """esemenyjelzo szeletelt intervallum: a TREND-mezők (illesztés/irány/meredekség/R²)
    strippelve. A het sorozat rács-tudatosan szeletelve marad (ablak-/pont-mezők), de a
    frontend a szint-VONALAT a szó-szintű szint-ből rajzolja, NEM ebből az intervallumból
    (különben egy második, trend-jellegű vonal jelenne meg). Hibás ág (keves_pont/…) változatlan.
    """
    if not iv.get("ervenyes"):
        return iv
    return {k: v for k, v in iv.items() if k not in _ESEMENYJELZO_TREND_MEZOK}


def regresszio_szamit(nyers, tortenet, config, szamitva_utc, lanc_map=None):
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
        # esemenyjelzo (pl. tüntetés): az ÓRÁS ág NEM számol trendvonalat (§8 + 6c) — a friss
        # szakasz kerekítési zaja nem trend; a helyette rajzolt szint-nézet a másodlagos (het)
        # ágon dől el. Minden órás intervallum ervenyes:False, ok:"esemenyjelzo" (nincs halott
        # irany/meredekseg/R² — a korábbi stagnal-illesztés §8-sértő volt).
        if tipus == "esemenyjelzo":
            intervallumok = {k: {"ervenyes": False, "ok": "esemenyjelzo"} for k in INTERVALLUMOK}
        else:
            intervallumok = _intervallumok(nyers.get("kulcsszavak", {}).get(szo),
                                           lanc=(lanc_map or {}).get(szo))
        ki[szo] = {
            "meres_kezdete": napok[0][0] if napok else None,
            "meres_vege": None if aktiv else (napok[-1][0] if napok else None),
            "aktiv": aktiv,
            "domen": domen,
            "tipus": tipus,
            # a szó config-RÁCSA (óra/nap/het) — a frontend felbontás-feliratához (item 3) és az órás-only
            # szó (benzin/nyugdíj) megkülönböztetéséhez (item 5); a horgonyos-only (nem-config) szó → "ora".
            "racs": getattr(aktivak.get(szo), "racs", "ora") or "ora",
            "intervallumok": intervallumok,
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


_RACS_FINOMSAG = {"ora": 0, "nap": 1, "het": 2}   # kisebb = finomabb (ütközésnél a finomabb rács nyer)


def _masodlagos_intervallumok_egyesit(rekordok, alap_racs):
    """PER-SZÓ TÖBB-TIMEFRAME: a szó minden timeframe-rekordjából (rács-csoportonként) számol intervallumokat,
    majd EGYESÍTI — intervallumonként az ÉRVÉNYES nyer, azon belül a FINOMABB rács (nap > het), és minden interval
    a forrás-rácsával címkézve (per-interval `racs`, a frontend ezt olvassa). Egyetlen rács esetén a régi viselkedés."""
    per_racs = {}
    for r in rekordok:
        per_racs.setdefault(r.get("racs") or alap_racs, []).append(r)
    if not per_racs:
        per_racs = {alap_racs: []}
    szamolt = {racs: _intervallumok(recs, racs) for racs, recs in per_racs.items()}
    egyesitett = {}
    for kulcs in INTERVALLUMOK:
        jeloltek = [(_RACS_FINOMSAG.get(racs, 9), racs, ivs[kulcs]) for racs, ivs in szamolt.items() if kulcs in ivs]
        jeloltek.sort(key=lambda t: (not t[2].get("ervenyes"), t[0]))   # érvényes elöl; azon belül finomabb rács elöl
        if jeloltek:
            _, racs, iv = jeloltek[0]
            egyesitett[kulcs] = {**iv, "racs": racs}
    return egyesitett


def regresszio_masodlagos_szamit(masodlagos_nyers, tortenet, config, szamitva_utc):
    """A kulcsszo_masodlagos_regresszio.json: a nap/het szavak RÁCS-tudatos regressziója.

    A racs a rekordból jön (per-szó nap/het), az intervallumok a rács szerint (Task 6a-2).
    Külön fájl, hogy az órás kulcsszo_regresszio.json ÉRINTETLEN maradjon. Nulla Google-hívás.
    Szóhalmaz: a másodlagos nyers fájl szavai (amiknek van nap/het adatuk).
    """
    marker = config.modszertan_valtas
    aktivak = {t.kifejezes: t for t in config.osszes_kulcsszo()}
    napok_szonkent = {}
    for nap in tortenet.get("napok", []):
        d = nap["nap"]
        if marker is not None and d < marker:
            continue
        for rek in nap["kulcsszavak"]:
            napok_szonkent.setdefault(rek["kulcsszo"], []).append((d, rek))

    ki = {}
    for szo, rekordok in masodlagos_nyers.get("kulcsszavak", {}).items():
        rek = max(rekordok, key=lambda r: r["ablak_veg_utc"]) if rekordok else None
        racs = rek.get("racs") if rek else None
        napok = sorted(napok_szonkent.get(szo, []), key=lambda x: x[0])
        domen, tipus = _domen_tipus(szo, aktivak, napok)
        ki[szo] = {
            "racs": racs,
            "aktiv": szo in aktivak,
            "domen": domen,
            "tipus": tipus,
        }
        if tipus == "esemenyjelzo":
            # esemény-jelző (pl. tüntetés): NINCS trendvonal — a friss szakasz kerekítési
            # padló-zaja nem trend (§4). HELYETTE szint = a nem-részleges értékek MEDIÁNJA
            # (robusztus az esemény-csúcsokra, ellentétben az átlaggal). A het sorozatot a
            # _intervallumok UGYANÚGY szeleteli (rács-tudatos ablak; rövidnél keves_pont →
            # a frontend rovid_het_ablak), de a TREND-mezők strippelve — a felülírás minden
            # ablakot ugyanarra a görbére húzna (no-op intervallum-választó), a szeletelés nem.
            lezart = [p["ertek"] for p in rek["pontok"] if not p.get("reszleges")] if rek else []
            ki[szo]["szint"] = statistics.median(lezart) if lezart else None
            ki[szo]["szint_modszer"] = "median"
            ki[szo]["intervallumok"] = {k: _szint_intervallum(iv)
                                        for k, iv in _masodlagos_intervallumok_egyesit(rekordok, racs or "het").items()}
        else:
            ki[szo]["intervallumok"] = _masodlagos_intervallumok_egyesit(rekordok, racs or "ora")
    return {
        "szamitva_utc": szamitva_utc,
        "meredekseg_egyseg": MEREDEKSEG_EGYSEG,
        "elmozdulas_kuszob": ELMOZDULAS_KUSZOB,      # a nap/het iránycímke ABLAK-RELATÍV (nem per-nap)
        "megjegyzes": R2_MEGJEGYZES,
        "kulcsszavak": ki,
    }


def regresszio_ir_masodlagos(docs_data, adat) -> Path:
    return json_export._ir_json(Path(docs_data) / "kulcsszo_masodlagos_regresszio.json", adat)
