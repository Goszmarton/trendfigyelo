from __future__ import annotations

import inspect
import json
import re
from datetime import date, datetime
from pathlib import Path

from trendfigyelo.nyers_kimenet import ervenyes_nyers_rekord, ir_gordulo

GYOKER = Path(__file__).resolve().parent.parent
DATA = GYOKER / "docs" / "data"

# a (kezdet,veg) perem-párok korlátja (I5) az ir_gordulo alapértelmezéséből ered — nem beégetett
MEGTARTOTT_NAP = inspect.signature(ir_gordulo).parameters["megtartott_nap"].default
ISO_NAP = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# felkapott.hir_sorok által garantált mezők (a sorszam/kifejezes-t a top_trend_struktura levágja)
_HIR_MEZOK = ("hir_cim", "hir_forras", "hir_url", "hir_ido_utc", "hir_kep", "hir_kivonat")

# atlag/csucs None is lehet (végig-nulla szó, vö. test_json_export.test_teljesen_nulla_*)
_OSSZESITES = {
    "kulcsszo": (str,), "domen": (str,), "tipus": (str,),
    "atlag": (int, float, type(None)), "csucs": (int, float, type(None)),
    "ervenyes_pontok": (int,), "nulla_pontok": (int,), "ossz_pontok": (int,),
}


def _json(*reszek) -> object:
    return json.loads(DATA.joinpath(*reszek).read_text(encoding="utf-8"))


def _tz_aware_utc(s) -> bool:
    """Igaz, ha s tz-aware ISO időbélyeg +00:00 eltolással."""
    if not isinstance(s, str):
        return False
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return False
    off = dt.utcoffset()
    return off is not None and off.total_seconds() == 0


def _kanonikus_nap(s) -> bool:
    if not (isinstance(s, str) and ISO_NAP.match(s)):
        return False
    try:
        return date.fromisoformat(s).isoformat() == s
    except ValueError:
        return False


def _sema_osszesites(rek, hol) -> list[str]:
    if not isinstance(rek, dict):
        return [f"{hol}: dict kell"]
    hibak = []
    for mezo, tipusok in _OSSZESITES.items():
        if mezo not in rek:
            hibak.append(f"{hol}: hiányzó '{mezo}'")
        elif not isinstance(rek[mezo], tipusok) or isinstance(rek[mezo], bool):
            hibak.append(f"{hol}.{mezo}: rossz típus")
    return hibak


# a tortenet.json halmozódó → a régi (horgonyos) napok ÖRÖKRE benne maradnak a
# régi aggregátum-alakban (insert-if-absent, sosem felülírva). Ezért két alakot
# kell elfogadni; a közös mezők (kulcsszo/atlag/csucs/ervenyes_pontok) mindkettőben
# kötelezők, az új-only mezők csak akkor, ha az új alak jelenléte látszik.
_OSSZ_KOZOS = {
    "kulcsszo": (str,), "atlag": (int, float, type(None)),
    "csucs": (int, float, type(None)), "ervenyes_pontok": (int,),
}
_OSSZ_UJ_ONLY = {
    "domen": (str,), "tipus": (str,), "nulla_pontok": (int,), "ossz_pontok": (int,),
}


def _tipus_ok(v, tipusok) -> bool:
    return isinstance(v, tipusok) and not isinstance(v, bool)


def _sema_osszesites_barmelyik(rek, hol) -> list[str]:
    """A tortenet.json aggregátum-rekordja RÉGI VAGY ÚJ alakban is érvényes.

    RÉGI: {kulcsszo, csoport, atlag, csucs, ervenyes_pontok}
    ÚJ:   {kulcsszo, domen, tipus, atlag, csucs, ervenyes_pontok, nulla_pontok, ossz_pontok}
    A közös mezők (kulcsszo, atlag, csucs, ervenyes_pontok) mindkettőben kötelezők;
    ha bármely új-only mező (domen/tipus/nulla_pontok/ossz_pontok) jelen van, akkor a
    TELJES új mezőkészletet megköveteljük (a fél-új rekord is hiba).

    FONTOS: a rekord-alak töréspontja (2026-07-29) NEM esik egybe a modszertan_valtas
    markerrel (2026-07-30). A 07-29 már új alakú, de még a horgonyos korszakhoz tartozik.
    A rekord ALAKJÁBÓL ezért TILOS a korszakra következtetni — a korszakot kizárólag a
    modszertan_valtas dönti el.
    """
    if not isinstance(rek, dict):
        return [f"{hol}: dict kell"]
    hibak = []
    for mezo, tipusok in _OSSZ_KOZOS.items():
        if mezo not in rek:
            hibak.append(f"{hol}: hiányzó '{mezo}'")
        elif not _tipus_ok(rek[mezo], tipusok):
            hibak.append(f"{hol}.{mezo}: rossz típus")
    if any(m in rek for m in _OSSZ_UJ_ONLY):   # új alak → a teljes új mezőkészlet kötelező
        for mezo, tipusok in _OSSZ_UJ_ONLY.items():
            if mezo not in rek:
                hibak.append(f"{hol}: hiányzó '{mezo}' (új alak)")
            elif not _tipus_ok(rek[mezo], tipusok):
                hibak.append(f"{hol}.{mezo}: rossz típus")
    return hibak


# ═════════════════════════════════════════════════════════════════════════════
# SÉMA-SZINT — kulcsok, típusok, kötelező mezők (fájlonként egy validátor)
# ═════════════════════════════════════════════════════════════════════════════

def sema_legfrissebb(obj) -> list[str]:
    if not isinstance(obj, dict):
        return ["legfrissebb: dict kell"]
    hibak = []
    for mezo, tip in (("geo", str), ("frissitve", str), ("top_trendek", list),
                      ("trend_idosorok", list), ("kulcsszavak", dict),
                      ("kulcsszo_osszesites", list)):
        if mezo not in obj:
            hibak.append(f"legfrissebb: hiányzó '{mezo}'")
        elif not isinstance(obj[mezo], tip):
            hibak.append(f"legfrissebb.{mezo}: rossz típus")
    if "modszertan_valtas" in obj and not isinstance(obj["modszertan_valtas"], str):
        hibak.append("legfrissebb.modszertan_valtas: str kell, ha jelen")
    for i, tr in enumerate(obj.get("top_trendek", []) if isinstance(obj.get("top_trendek"), list) else []):
        if not isinstance(tr, dict):
            hibak.append(f"top_trendek[{i}]: dict kell")
            continue
        for m in ("kifejezes", "volumen", "novekedes_pct", "idosor", "hirek"):
            if m not in tr:
                hibak.append(f"top_trendek[{i}]: hiányzó '{m}'")
        for j, pt in enumerate(tr.get("idosor", []) if isinstance(tr.get("idosor"), list) else []):
            if not (isinstance(pt, dict) and "idopont_utc" in pt and "ertek" in pt):
                hibak.append(f"top_trendek[{i}].idosor[{j}]: {{idopont_utc, ertek}} kell")
        for j, hr in enumerate(tr.get("hirek", []) if isinstance(tr.get("hirek"), list) else []):
            if not isinstance(hr, dict):
                hibak.append(f"top_trendek[{i}].hirek[{j}]: dict kell")
                continue
            for m in _HIR_MEZOK:
                if m not in hr:
                    hibak.append(f"top_trendek[{i}].hirek[{j}]: hiányzó '{m}'")
        # Task 3a — kategória JELEN-ESETÉN-típusos (a mai legfrissebb.json még nem hordozza;
        # ledger nyitott elem a szigorításról). Ha jelen: topics list[int], temak list[str],
        # és len(topics) == len(temak) (a temak a topics-ból derivált, trendspy garantálja).
        if "topics" in tr or "temak" in tr:
            topics, temak = tr.get("topics"), tr.get("temak")
            if not (isinstance(topics, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in topics)):
                hibak.append(f"top_trendek[{i}].topics: list[int] kell")
            if not (isinstance(temak, list) and all(isinstance(x, str) for x in temak)):
                hibak.append(f"top_trendek[{i}].temak: list[str] kell")
            if isinstance(topics, list) and isinstance(temak, list) and len(topics) != len(temak):
                hibak.append(f"top_trendek[{i}].topics/temak: eltérő hossz")
    for i, pt in enumerate(obj.get("trend_idosorok", []) if isinstance(obj.get("trend_idosorok"), list) else []):
        if not (isinstance(pt, dict) and {"kifejezes", "idopont_utc", "ertek", "forras"} <= set(pt)):
            hibak.append(f"trend_idosorok[{i}]: {{kifejezes, idopont_utc, ertek, forras}} kell")
    # kulcsszavak: a pont mezője NYERS_ERTEK (nem 'ertek' — vö. kulcsszo_nyers!)
    kk = obj.get("kulcsszavak", {})
    for kif, v in (kk.items() if isinstance(kk, dict) else []):
        if not isinstance(v, dict):
            hibak.append(f"kulcsszavak[{kif!r}]: dict kell")
            continue
        for m in ("domen", "tipus", "pontok"):
            if m not in v:
                hibak.append(f"kulcsszavak[{kif!r}]: hiányzó '{m}'")
        for j, pt in enumerate(v.get("pontok", []) if isinstance(v.get("pontok"), list) else []):
            if not (isinstance(pt, dict) and "idopont_utc" in pt and "nyers_ertek" in pt):
                hibak.append(f"kulcsszavak[{kif!r}].pontok[{j}]: {{idopont_utc, nyers_ertek}} kell")
    for i, rek in enumerate(obj.get("kulcsszo_osszesites", []) if isinstance(obj.get("kulcsszo_osszesites"), list) else []):
        hibak += _sema_osszesites(rek, f"kulcsszo_osszesites[{i}]")
    return hibak


def sema_tortenet(obj) -> list[str]:
    if not isinstance(obj, dict):
        return ["tortenet: dict kell"]
    hibak = []
    if not isinstance(obj.get("napok"), list):
        hibak.append("tortenet.napok: list kell")
    if "modszertan_valtas" in obj and not isinstance(obj["modszertan_valtas"], str):
        hibak.append("tortenet.modszertan_valtas: str kell, ha jelen")
    for i, nap in enumerate(obj.get("napok", []) if isinstance(obj.get("napok"), list) else []):
        if not isinstance(nap, dict):
            hibak.append(f"napok[{i}]: dict kell")
            continue
        if not (isinstance(nap.get("nap"), str) and ISO_NAP.match(nap.get("nap", ""))):
            hibak.append(f"napok[{i}].nap: YYYY-MM-DD kell")
        if not isinstance(nap.get("kulcsszavak"), list):
            hibak.append(f"napok[{i}].kulcsszavak: list kell")
            continue
        for j, rek in enumerate(nap["kulcsszavak"]):
            hibak += _sema_osszesites_barmelyik(rek, f"napok[{i}].kulcsszavak[{j}]")
    return hibak


def sema_napok_index(obj) -> list[str]:
    if not isinstance(obj, dict) or not isinstance(obj.get("napok"), list):
        return ["napok/index: {napok: [...]} kell"]
    return [f"napok/index.napok[{i}]: YYYY-MM-DD kell"
            for i, x in enumerate(obj["napok"])
            if not (isinstance(x, str) and ISO_NAP.match(x))]


def sema_kulcsszo_nyers(obj) -> list[str]:
    """Fájl-váz + rekordonként az ÚJRAHASZNOSÍTOTT ervenyes_nyers_rekord (Task 3)."""
    if not isinstance(obj, dict) or not isinstance(obj.get("kulcsszavak"), dict):
        return ["kulcsszo_nyers: {kulcsszavak: {...}} kell"]
    hibak = []
    for kif, recs in obj["kulcsszavak"].items():
        if not isinstance(recs, list) or not recs:
            hibak.append(f"kulcsszavak[{kif!r}]: nem üres rekordlista kell")
            continue
        for i, rek in enumerate(recs):
            hibak += [f"kulcsszavak[{kif!r}][{i}]: {h}" for h in ervenyes_nyers_rekord(rek)]
    return hibak


# ═════════════════════════════════════════════════════════════════════════════
# INVARIÁNS-SZINT — kereszt-metsző igazságok
# ═════════════════════════════════════════════════════════════════════════════

def tortenet_nem_fogy(elozo, uj) -> list[str]:
    """I1 — KÉT PILLANATKÉP közti halmozódás: ∀ régi nap ∈ új, és a napszám nem csökken.
    Tiszta halmaz-összevetés; NEM hívja az exportert. Az exporter két egymást
    követő hívásának viselkedését a test_json_export.py párja fedi (más hatókör)."""
    regi = {b["nap"] for b in elozo.get("napok", [])}
    uj_ = {b["nap"] for b in uj.get("napok", [])}
    hibak = [f"eltűnt nap: {n}" for n in sorted(regi - uj_)]
    if len(uj.get("napok", [])) < len(elozo.get("napok", [])):
        hibak.append("napok száma csökkent")
    return hibak


def modszertan_valtas_egyezik(legfrissebb, tortenet) -> list[str]:
    """I2 — mindkét fájlban jelen, kanonikus YYYY-MM-DD, és megegyeznek."""
    a, b = legfrissebb.get("modszertan_valtas"), tortenet.get("modszertan_valtas")
    hibak = []
    for nev, v in (("legfrissebb", a), ("tortenet", b)):
        if v is None:
            hibak.append(f"{nev}.modszertan_valtas: hiányzik")
        elif not _kanonikus_nap(v):
            hibak.append(f"{nev}.modszertan_valtas: nem kanonikus YYYY-MM-DD: {v!r}")
    if a is not None and b is not None and a != b:
        hibak.append(f"modszertan_valtas eltér: {a!r} vs {b!r}")
    return hibak


def forward_perem_eltolas_napokban(napok_index, tortenet) -> int:
    """I3 — napok/index legfrissebb napja MÍNUSZ tortenet legfrissebb napja (nap).
    Az EXPORTER szerződése szerint PONTOSAN 1 (a tortenet csak teljes budapesti
    napokat tart → előre egy napot lemarad). Szintetikus adaton mindig +1; a
    VALÓS fájlok integrációja engedékenyebb (kimaradt gyűjtési nap ≠ kód-hiba)."""
    imax = max(date.fromisoformat(x) for x in napok_index["napok"])
    tmax = max(date.fromisoformat(b["nap"]) for b in tortenet["napok"])
    return (imax - tmax).days


def reszleges_csak_zaropont(nyers) -> list[str]:
    """I4 — reszleges:true KIZÁRÓLAG a záró ponton, sehol máshol; a záró MINDIG részleges.
    Kiterjeszti az ervenyes_nyers_rekord farok-ellenőrzését a 'sehol máshol' záradékkal."""
    hibak = []
    for kif, recs in nyers.get("kulcsszavak", {}).items():
        for i, rek in enumerate(recs):
            pts = rek.get("pontok", [])
            if not pts:
                continue
            for j, p in enumerate(pts[:-1]):
                if p.get("reszleges"):
                    hibak.append(f"{kif}[{i}].pontok[{j}]: reszleges igaz, de nem záró")
            if not pts[-1].get("reszleges"):
                hibak.append(f"{kif}[{i}]: záró pont nem részleges")
    return hibak


def kozos_perem_futasonkent(nyers) -> list[str]:
    """I5 — futásonkénti közös perem, bukásra képes megfogalmazásban:
      - minden ablak_veg_utc-hez PONTOSAN EGY ablak_kezdet_utc (együtt mozognak);
      - egy szónak egy peremhez ≤ 1 rekordja;
      - a (kezdet, veg) párok száma ≤ megtartott_nap+1, NEM szó×nap nagyságrendű.
    Ez fogja meg a 'minden szó saját peremet kapott' romlást."""
    hibak = []
    veg_kezdetek: dict = {}
    parok = set()
    for kif, recs in nyers.get("kulcsszavak", {}).items():
        latott = set()
        for rek in recs:
            k, v = rek.get("ablak_kezdet_utc"), rek.get("ablak_veg_utc")
            veg_kezdetek.setdefault(v, set()).add(k)
            parok.add((k, v))
            if v in latott:
                hibak.append(f"{kif}: két rekord ugyanahhoz a peremhez ({v})")
            latott.add(v)
    for v, kezdetek in veg_kezdetek.items():
        if len(kezdetek) != 1:
            hibak.append(f"perem {v}: több ablak_kezdet_utc tartozik hozzá: {sorted(kezdetek)}")
    if len(parok) > MEGTARTOTT_NAP + 1:
        hibak.append(f"(kezdet,veg) párok száma {len(parok)} > {MEGTARTOTT_NAP + 1} — szó×nap romlás gyanúja")
    return hibak


def trend_idosor_nincs_reszleges(legfrissebb) -> list[str]:
    """I7 — a trend-útvonal pontjain NINCS 'reszleges' (tudatos aszimmetria, nem láncolódik)."""
    hibak = [f"trend_idosorok[{i}]: nem lehet 'reszleges'"
             for i, p in enumerate(legfrissebb.get("trend_idosorok", [])) if "reszleges" in p]
    for ti, tr in enumerate(legfrissebb.get("top_trendek", [])):
        for j, p in enumerate(tr.get("idosor", [])):
            if "reszleges" in p:
                hibak.append(f"top_trendek[{ti}].idosor[{j}]: nem lehet 'reszleges'")
    return hibak


def napok_index_szinkron(napok_dir: Path) -> list[str]:
    """I9 — kétirányú: minden indexelt dátumhoz van napi fájl, és fordítva."""
    idx_ut = napok_dir / "index.json"
    if not idx_ut.is_file():
        return ["nincs index.json"]
    idx = set(json.loads(idx_ut.read_text(encoding="utf-8")).get("napok", []))
    fajlok = {p.stem for p in napok_dir.glob("*.json") if p.name != "index.json"}
    return ([f"indexben van, fájl nincs: {n}" for n in sorted(idx - fajlok)]
            + [f"fájl van, indexben nincs: {n}" for n in sorted(fajlok - idx)])


# ─────────────────────────────────────────────────────────────────────────────
# Szintetikus fixtúra-építők
# ─────────────────────────────────────────────────────────────────────────────

def _ossz(kulcsszo="a", **f):
    r = {"kulcsszo": kulcsszo, "domen": "g", "tipus": "szintmero",
         "atlag": 5.0, "csucs": 10.0, "ervenyes_pontok": 2, "nulla_pontok": 0, "ossz_pontok": 2}
    r.update(f)
    return r


def _nyers_rek(kulcsszo, kezd, veg, pontok):
    return {"kulcsszo": kulcsszo, "ablak_kezdet_utc": kezd, "ablak_veg_utc": veg, "pontok": pontok}


def _pont(iso, ertek=5, reszleges=False):
    return {"idopont_utc": iso, "ertek": ertek, "reszleges": reszleges}


def _valid_legfrissebb(n=3):
    kifs = [f"szo{i}" for i in range(n)]
    return {
        "geo": "HU", "frissitve": "2026-08-04T20:00:00+00:00",
        "top_trendek": [{"kifejezes": "t", "volumen": "1", "novekedes_pct": "1",
                         # temak a topics-ból derivált (trendspy trend_keyword.py:46) → len egyezik
                         "topics": [1], "temak": ["Autos and Vehicles"],
                         "idosor": [{"idopont_utc": "2026-08-04T20:00:00+00:00", "ertek": 1}],
                         "hirek": [{"hir_cim": "Cím", "hir_forras": "Index",
                                    "hir_url": "https://index.hu/x",
                                    "hir_ido_utc": "2026-08-04T18:00:00+00:00",
                                    "hir_kep": "", "hir_kivonat": ""}]}],
        "trend_idosorok": [{"kifejezes": "t", "idopont_utc": "2026-08-04T20:00:00+00:00", "ertek": 1, "forras": "api"}],
        "kulcsszavak": {k: {"domen": "g", "tipus": "szintmero",
                            "pontok": [{"idopont_utc": "2026-08-04T20:00:00+00:00", "nyers_ertek": 5}]} for k in kifs},
        "kulcsszo_osszesites": [_ossz(k) for k in kifs],
        "modszertan_valtas": "2026-07-30",
    }


def _nap(nap):
    return {"nap": nap, "kulcsszavak": [_ossz()]}


# ═════════════════════════════════════════════════════════════════════════════
# SÉMA-SZINT tesztek
# ═════════════════════════════════════════════════════════════════════════════

def test_megtartott_nap_a_kodbol_szarmazik():
    assert isinstance(MEGTARTOTT_NAP, int) and MEGTARTOTT_NAP > 0


def test_sema_legfrissebb_valid():
    assert sema_legfrissebb(_valid_legfrissebb()) == []


def test_sema_legfrissebb_hibak():
    hi = _valid_legfrissebb()
    del hi["geo"]
    assert any("geo" in h for h in sema_legfrissebb(hi))
    # a kulcsszavak-pont mezője 'nyers_ertek' — az 'ertek' NEM elég
    rossz = _valid_legfrissebb()
    p = rossz["kulcsszavak"]["szo0"]["pontok"][0]
    p.pop("nyers_ertek"); p["ertek"] = 5
    assert any("nyers_ertek" in h for h in sema_legfrissebb(rossz))


def test_sema_legfrissebb_hir_hianyzo_mezo():
    rossz = _valid_legfrissebb()
    rossz["top_trendek"][0]["hirek"][0].pop("hir_url")   # Task 7 a linkhez ezt rajzolja
    assert any("hir_url" in h for h in sema_legfrissebb(rossz))


def test_sema_legfrissebb_topics_es_temak():
    # Task 3a: topics list[int] + temak list[str], JELEN-ESETÉN-típusos, párosított hossz.
    assert sema_legfrissebb(_valid_legfrissebb()) == []                     # topics=[1], temak=["..."] paired
    rossz_t = _valid_legfrissebb(); rossz_t["top_trendek"][0]["topics"] = ["x"]    # int helyett str
    assert any("topics" in h for h in sema_legfrissebb(rossz_t))
    rossz_te = _valid_legfrissebb(); rossz_te["top_trendek"][0]["temak"] = [1]      # str helyett int
    assert any("temak" in h for h in sema_legfrissebb(rossz_te))
    rossz_len = _valid_legfrissebb(); rossz_len["top_trendek"][0]["topics"] = [1, 2]  # len eltér a temak-tól
    assert any("hossz" in h for h in sema_legfrissebb(rossz_len))
    # hiányzó mezők MEGENGEDETTEK (mai legfrissebb.json még nem hordozza) — ledger nyitott elem
    hiany = _valid_legfrissebb()
    hiany["top_trendek"][0].pop("topics"); hiany["top_trendek"][0].pop("temak")
    assert sema_legfrissebb(hiany) == []


def test_sema_tortenet_valid_es_hibas():
    jo = {"napok": [{"nap": "2026-07-30", "kulcsszavak": [_ossz()]}], "modszertan_valtas": "2026-07-30"}
    assert sema_tortenet(jo) == []
    assert any("YYYY-MM-DD" in h for h in sema_tortenet({"napok": [{"nap": "30/07", "kulcsszavak": []}]}))


def test_sema_tortenet_regi_semas_nap():
    # A halmozódó fájl RÉGI (horgonyos) napjai a régi aggregátum-alakban maradnak.
    ujra = {"nap": "2026-07-30", "kulcsszavak": [_ossz()]}                      # új alak
    regi = {"nap": "2026-07-21", "kulcsszavak": [
        {"kulcsszo": "albérlet", "csoport": "megelhetes", "atlag": 3.72, "csucs": 3.72, "ervenyes_pontok": 1}]}
    assert sema_tortenet({"napok": [regi, ujra], "modszertan_valtas": "2026-07-30"}) == []
    # egyik alakra sem illő rekord (hiányzik a kulcsszo) → hiba a régi napon is
    rossz = {"napok": [{"nap": "2026-07-21", "kulcsszavak": [
        {"csoport": "x", "atlag": 1.0, "csucs": 1.0, "ervenyes_pontok": 1}]}]}
    assert any("kulcsszo" in h for h in sema_tortenet(rossz))


def test_sema_napok_index_valid_es_hibas():
    assert sema_napok_index({"napok": ["2026-07-30", "2026-07-31"]}) == []
    assert any("YYYY-MM-DD" in h for h in sema_napok_index({"napok": ["2026-7-3"]}))
    assert any("{napok" in h for h in sema_napok_index(["2026-07-30"]))  # nem {napok:[...]}


def test_sema_kulcsszo_nyers_valid_es_hibas():
    veg = "2026-07-30T20:00:00+00:00"
    kezd = "2026-07-23T20:00:00+00:00"
    jo = {"kulcsszavak": {"a": [_nyers_rek("a", kezd, veg, [_pont("2026-07-30T20:00:00+00:00", reszleges=True)])]}}
    assert sema_kulcsszo_nyers(jo) == []
    # a per-rekord hiba (nincs 'reszleges') propagál az ervenyes_nyers_rekord-ból
    rossz = {"kulcsszavak": {"a": [_nyers_rek("a", kezd, veg, [{"idopont_utc": "2026-07-30T20:00:00+00:00", "ertek": 5}])]}}
    assert any("reszleges" in h for h in sema_kulcsszo_nyers(rossz))
    assert any("nem üres rekordlista" in h for h in sema_kulcsszo_nyers({"kulcsszavak": {"a": []}}))


def test_valos_fajlok_sema():
    assert sema_legfrissebb(_json("legfrissebb.json")) == []
    assert sema_tortenet(_json("tortenet.json")) == []
    assert sema_napok_index(_json("napok", "index.json")) == []
    assert sema_kulcsszo_nyers(_json("kulcsszo_nyers.json")) == []


def test_sema_len_agnosztikus():  # I8 — sehol == 13
    assert sema_legfrissebb(_valid_legfrissebb(3)) == []
    assert sema_legfrissebb(_valid_legfrissebb(20)) == []


# ═════════════════════════════════════════════════════════════════════════════
# INVARIÁNS-SZINT tesztek
# ═════════════════════════════════════════════════════════════════════════════

def test_i1_tortenet_nem_fogy():
    a = {"napok": [_nap("2026-07-21"), _nap("2026-07-22")]}
    b = {"napok": [_nap("2026-07-21"), _nap("2026-07-22"), _nap("2026-07-23")]}
    assert tortenet_nem_fogy(a, b) == []          # bővül
    assert tortenet_nem_fogy(a, a) == []          # változatlan
    assert any("eltűnt" in h for h in tortenet_nem_fogy(b, a))  # 07-23 eltűnt


def test_i2_modszertan_valtas():
    ok = {"modszertan_valtas": "2026-07-30"}
    assert modszertan_valtas_egyezik(ok, ok) == []
    assert any("hiányzik" in h for h in modszertan_valtas_egyezik({}, ok))
    assert any("eltér" in h for h in modszertan_valtas_egyezik(ok, {"modszertan_valtas": "2026-07-31"}))
    assert any("kanonikus" in h for h in modszertan_valtas_egyezik({"modszertan_valtas": "2026-7-30"}, ok))


def test_i3_forward_perem_pontos_egy():
    idx = {"napok": ["2026-07-23", "2026-08-04"]}
    tort = {"napok": [_nap("2026-07-21"), _nap("2026-08-03")]}
    assert forward_perem_eltolas_napokban(idx, tort) == 1
    tort2 = {"napok": [_nap("2026-08-04")]}
    assert forward_perem_eltolas_napokban(idx, tort2) == 0  # nem +1 → a hívó teszt bünteti


def test_i3_valos_engedekeny_korlatos():
    idx = _json("napok", "index.json")
    tort = _json("tortenet.json")
    diff = forward_perem_eltolas_napokban(idx, tort)
    assert 0 <= diff <= 2, diff   # napok.max >= tortenet.max ÉS <= 2 nap


def test_i4_reszleges_csak_zaropont():
    veg = "2026-07-30T20:00:00+00:00"; kezd = "2026-07-23T20:00:00+00:00"
    jo = {"kulcsszavak": {"a": [_nyers_rek("a", kezd, veg,
          [_pont("2026-07-30T18:00:00+00:00"), _pont("2026-07-30T20:00:00+00:00", reszleges=True)])]}}
    assert reszleges_csak_zaropont(jo) == []
    kozbulso = {"kulcsszavak": {"a": [_nyers_rek("a", kezd, veg,
          [_pont("2026-07-30T18:00:00+00:00", reszleges=True), _pont("2026-07-30T20:00:00+00:00", reszleges=True)])]}}
    assert any("nem záró" in h for h in reszleges_csak_zaropont(kozbulso))
    zaro_nem = {"kulcsszavak": {"a": [_nyers_rek("a", kezd, veg, [_pont("2026-07-30T20:00:00+00:00", reszleges=False)])]}}
    assert any("nem részleges" in h for h in reszleges_csak_zaropont(zaro_nem))


def test_i5_kozos_perem_futasonkent():
    v1, k1 = "2026-07-30T20:00:00+00:00", "2026-07-23T20:00:00+00:00"
    jo = {"kulcsszavak": {"a": [_nyers_rek("a", k1, v1, [])], "b": [_nyers_rek("b", k1, v1, [])]}}
    assert kozos_perem_futasonkent(jo) == []
    # két szó AZONOS veg, ELTÉRŐ kezdet → hiba (a perem nem koherens)
    rossz = {"kulcsszavak": {"a": [_nyers_rek("a", k1, v1, [])],
                             "b": [_nyers_rek("b", "2026-07-24T20:00:00+00:00", v1, [])]}}
    assert any("több ablak_kezdet_utc" in h for h in kozos_perem_futasonkent(rossz))
    # egy szó két rekordja ugyanahhoz a peremhez → hiba
    dup = {"kulcsszavak": {"a": [_nyers_rek("a", k1, v1, []), _nyers_rek("a", k1, v1, [])]}}
    assert any("két rekord ugyanahhoz a peremhez" in h for h in kozos_perem_futasonkent(dup))


def test_i6_tz_aware_utc():
    assert _tz_aware_utc("2026-07-30T20:00:00+00:00")
    assert not _tz_aware_utc("2026-07-30T20:00:00")          # naiv
    assert not _tz_aware_utc("2026-07-30")                   # csak dátum
    assert not _tz_aware_utc("2026-07-30T20:00:00+02:00")    # nem UTC


def test_i6_valos_idobelyegek_tz_aware():
    ny = _json("kulcsszo_nyers.json")
    for kif, recs in ny["kulcsszavak"].items():
        for rek in recs:
            assert _tz_aware_utc(rek["ablak_kezdet_utc"]) and _tz_aware_utc(rek["ablak_veg_utc"]), kif
            for p in rek["pontok"]:
                assert _tz_aware_utc(p["idopont_utc"]), kif
    for p in _json("legfrissebb.json")["trend_idosorok"]:
        assert _tz_aware_utc(p["idopont_utc"])


def test_i7_trend_idosor_nincs_reszleges():
    assert trend_idosor_nincs_reszleges(_valid_legfrissebb()) == []
    rossz = _valid_legfrissebb()
    rossz["trend_idosorok"][0]["reszleges"] = False
    assert any("reszleges" in h for h in trend_idosor_nincs_reszleges(rossz))
    assert trend_idosor_nincs_reszleges(_json("legfrissebb.json")) == []


def test_i9_napok_index_szinkron(tmp_path):
    (tmp_path / "2026-07-30.json").write_text("{}", encoding="utf-8")
    (tmp_path / "index.json").write_text('{"napok": ["2026-07-30"]}', encoding="utf-8")
    assert napok_index_szinkron(tmp_path) == []                                      # (a)
    (tmp_path / "index.json").write_text('{"napok": ["2026-07-30", "2026-07-31"]}', encoding="utf-8")
    assert any("fájl nincs" in h for h in napok_index_szinkron(tmp_path))            # (b)
    (tmp_path / "index.json").write_text('{"napok": []}', encoding="utf-8")
    assert any("indexben nincs" in h for h in napok_index_szinkron(tmp_path))        # (c)


def test_i9_valos_napok_szinkron():
    assert napok_index_szinkron(DATA / "napok") == []
