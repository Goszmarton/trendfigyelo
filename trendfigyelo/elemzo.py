"""Napi AI-elemzés ág: a commitolt adatokból VALÓS számok (Python) → Claude narratíva.

A számokat MINDIG ez a modul számolja; az AI (elemez) SOHA nem talál ki számot,
kizárólag a payloadban kapott számokból ír (spec §2.1). Ok-okozat tényként tilos;
a hipotézist az AI a folyó szövegbe ágyazva, óvatosan jelezve írja le — nincs
külön ELMÉLETI mező (spec §2.2).
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from trendfigyelo import seged


_log = logging.getLogger(__name__)

MODELL = "claude-opus-4-8"

RENDSZER_PROMPT = (
    "Magyar nyelvű elemző vagy egy magyar Google Trends figyelő oldalhoz. A közönség "
    "laikus olvasó, aki NEM lát JSON-t, mezőneveket vagy technikai részleteket. "
    "SZABÁLYOK, kivétel nélkül: "
    "(1) KIZÁRÓLAG a kapott számokból dolgozol; számot SOHA nem találsz ki. "
    "(2) FOLYÓ, összefüggő magyar BEKEZDÉSEKET írsz. SOHA nem használsz felsorolást, "
    "bullet-pontot, címkét, kulcs–érték párt vagy szakszót. Ha egy szekcióhoz több "
    "gondolat tartozik, azokat külön BEKEZDÉSBE (üres sorral elválasztva) fűzöd. "
    "(3) SOHA nem említesz mezőnevet, technikai kulcsot, sem a „payload\", „adatstruktúra\" "
    "vagy hasonló szót. A felhasználó nem tudja, milyen mezőkből dolgozol. Ha valamiről "
    "nincs adatod, azt természetes magyar mondattal írod le (pl. „ma még nincs mihez "
    "hasonlítani\"), NEM a hiányzó mezőt nevezed meg. "
    "(4) Ok-okozatot TÉNYKÉNT nem állítasz. Ahol magyarázatot feltételezel, a mondatban "
    "óvatosan jelzed („feltehetően\", „elképzelhető\", „ezt az adat önmagában nem igazolja\") "
    "— külön „feltételezés\" felirat NÉLKÜL, a fogalmazás maga hordozza az óvatosságot. "
    "(5) Hírt, forrást vagy eseményt nem találsz ki; a felkapott témákról csak a kapott "
    "témák és hírek alapján írsz. "
    "(6) Tömör, óvatos, DE ÉRDEMI: mondd el, mit látunk ma, milyen irányba mozdul a kép, "
    "és mit lehet ebből óvatosan leszűrni."
)

# A kulcsszó VALÓS iránya/meredeksége az 1_het (órás, napi frissülő) intervallumból jön.
KULCSSZO_IV = "1_het"


def _tortenet_utolso_nap_szavak(tortenet):
    napok = tortenet.get("napok", []) if isinstance(tortenet, dict) else []
    if not napok:
        return {}
    utolso = napok[-1]
    return {k["kulcsszo"]: k for k in utolso.get("kulcsszavak", [])}


def _kulcsszo_szamok(regresszio, tortenet):
    szavak = regresszio.get("kulcsszavak", {}) if isinstance(regresszio, dict) else {}
    tort = _tortenet_utolso_nap_szavak(tortenet)
    ki = []
    for szo, rec in szavak.items():
        iv = rec.get("intervallumok", {}).get(KULCSSZO_IV, {})
        t = tort.get(szo, {})
        ki.append({
            "szo": szo,
            "irany": iv.get("irany"),
            "meredekseg": iv.get("meredekseg_nap"),
            "ervenyes": iv.get("ervenyes"),
            "mai_ertek": iv.get("mai_ertek"),
            "csucs": t.get("csucs"),
            "atlag": t.get("atlag"),
        })
    return ki


HET_ABLAK_NAPOK = 7


def _kulcsszo_het(lanc):
    """A lánc utolsó HET_ABLAK_NAPOK napos ablakából valós heti pálya szavanként.
    A szakasz-törött (elavult végű) szavak kimaradnak — így a ~12 egészséges szó marad."""
    szavak_dict = (lanc or {}).get("kulcsszavak", {}) if isinstance(lanc, dict) else {}

    def _veg(rec):
        p = (rec or {}).get("pontok") or []
        return p[-1]["idopont_utc"] if p else None

    vegek = [v for v in (_veg(r) for r in szavak_dict.values()) if v]
    if not vegek:
        return {"ablak_napok": HET_ABLAK_NAPOK, "szavak": []}
    anchor = max(datetime.fromisoformat(v) for v in vegek)
    ablak_kezdet = anchor - timedelta(days=HET_ABLAK_NAPOK)
    frissessegi_kuszob = anchor - timedelta(days=1)   # ennél régebbi vég = szakasz-törött → kimarad
    szavak = []
    for szo, rec in szavak_dict.items():
        pontok = (rec or {}).get("pontok") or []
        if not pontok:
            continue
        if datetime.fromisoformat(pontok[-1]["idopont_utc"]) < frissessegi_kuszob:
            continue
        ablakban = [pt for pt in pontok
                    if datetime.fromisoformat(pt["idopont_utc"]) >= ablak_kezdet]
        if not ablakban:
            continue
        ertekek = [pt["ertek"] for pt in ablakban]
        kezdo, veg = round(ertekek[0], 1), round(ertekek[-1], 1)
        szavak.append({"szo": szo, "kezdo": kezdo, "veg": veg,
                       "valtozas": round(veg - kezdo, 1),
                       "min": round(min(ertekek), 1), "max": round(max(ertekek), 1)})
    szavak.sort(key=lambda s: -abs(s["valtozas"]))
    return {"ablak_napok": HET_ABLAK_NAPOK, "szavak": szavak}


def _nyers_heti_sorozat(youtube_nyers, szo):
    """A szó LEGKORÁBBI ablak_kezdetű nyers sorozata = a 12-m heti sáv (a legteljesebb tartomány)."""
    kw = (youtube_nyers or {}).get("kulcsszavak", {}) if isinstance(youtube_nyers, dict) else {}
    lista = kw.get(szo) or []
    if not lista:
        return None
    return min(lista, key=lambda s: s.get("ablak_kezdet_utc", ""))


def _csucs_atlag(series):
    pontok = (series or {}).get("pontok") or []
    ertekek = [p["ertek"] for p in pontok if not p.get("reszleges")]
    if not ertekek:
        return None, None
    return max(ertekek), round(sum(ertekek) / len(ertekek), 1)


def _yt_teljes_intervallum(rec):
    """A regressziós rekord leghosszabb ÉRVÉNYES intervalluma = legkorábbi ablak_kezdet_utc
    (a frontend teljes_valaszt mintája, app.js:290)."""
    ivk = (rec or {}).get("intervallumok", {})
    ervenyesek = [iv for iv in ivk.values() if iv.get("ervenyes") and iv.get("ablak_kezdet_utc")]
    if not ervenyesek:
        return None
    return min(ervenyesek, key=lambda iv: iv["ablak_kezdet_utc"])


def _youtube_szamok(youtube_regresszio, youtube_nyers):
    szavak = (youtube_regresszio or {}).get("kulcsszavak", {}) if isinstance(youtube_regresszio, dict) else {}
    ki = []
    for szo, rec in szavak.items():
        iv = _yt_teljes_intervallum(rec) or {}
        csucs, atlag = _csucs_atlag(_nyers_heti_sorozat(youtube_nyers, szo))
        ki.append({
            "szo": szo,
            "domen": rec.get("domen"),
            "irany": iv.get("irany"),
            "meredekseg": iv.get("meredekseg_nap"),
            "ervenyes": bool(iv.get("ervenyes")),
            "mai_ertek": iv.get("mai_ertek"),
            "csucs": csucs,
            "atlag": atlag,
        })
    return ki


def _felkapott(legfrissebb, napok_trendek):
    top = []
    for t in (legfrissebb.get("top_trendek", []) if isinstance(legfrissebb, dict) else []):
        top.append({
            "kifejezes": t.get("kifejezes"), "volumen": t.get("volumen"),
            "novekedes_pct": t.get("novekedes_pct"), "temak": t.get("temak", []),
            "hirek": t.get("hirek", []),
        })
    # gördülő hét: hány KÜLÖN NAPON szerepelt egy kifejezés (napok_trendek = utolsó ≤7 nap).
    # Napon belül minden kifejezés LEGFELJEBB egyszer számít (dedup) — a szerződés
    # a "hány külön nap", nem a bejegyzés-szám.
    napok_trendek = napok_trendek if isinstance(napok_trendek, dict) else {}
    szamlalo = {}
    for _datum, trendek in sorted(napok_trendek.items()):
        napi_kifejezesek = {t.get("kifejezes") for t in trendek}
        napi_kifejezesek.discard(None)
        for kif in napi_kifejezesek:
            szamlalo[kif] = szamlalo.get(kif, 0) + 1
    visszateroek = sorted(
        ({"kifejezes": k, "napok_szama": n} for k, n in szamlalo.items()),
        key=lambda e: (-e["napok_szama"], e["kifejezes"]),
    )
    return {"top": top, "het": {"napok": len(napok_trendek), "visszateroek": visszateroek}}


def nap_diff(mai_szamok, tegnapi_szamok, mai_top, tegnapi_top):
    if not tegnapi_szamok and not tegnapi_top:
        return {"irany_valtok": [], "mozgok": [], "felkapott_uj": [],
                "felkapott_eltunt": [], "van_elozo": False}
    tegnap = {s["szo"]: s for s in (tegnapi_szamok or [])}
    irany_valtok, mozgok = [], []
    for s in mai_szamok:
        elozo = tegnap.get(s["szo"])
        if not elozo:
            continue
        if elozo.get("irany") != s.get("irany"):
            irany_valtok.append({"szo": s["szo"], "elozo": elozo.get("irany"), "mai": s.get("irany")})
        m_mai, m_teg = s.get("meredekseg"), elozo.get("meredekseg")
        if isinstance(m_mai, (int, float)) and isinstance(m_teg, (int, float)):
            mozgok.append({"szo": s["szo"], "valtozas": round(m_mai - m_teg, 3)})
    mozgok.sort(key=lambda e: -abs(e["valtozas"]))
    mai_kif = {t.get("kifejezes") for t in (mai_top or [])}
    teg_kif = {t.get("kifejezes") for t in (tegnapi_top or [])}
    return {
        "irany_valtok": irany_valtok,
        "mozgok": mozgok[:5],
        "felkapott_uj": sorted(mai_kif - teg_kif),
        "felkapott_eltunt": sorted(teg_kif - mai_kif),
        "van_elozo": True,
    }


def epit_payload(adatok, tegnapi_szamok=None, tegnapi_top=None):
    regresszio = adatok.get("regresszio", {})
    tortenet = adatok.get("tortenet", {})
    szamok = _kulcsszo_szamok(regresszio, tortenet)
    felkapott = _felkapott(adatok.get("legfrissebb", {}), adatok.get("napok_trendek", {}))
    valtozas = nap_diff(szamok, tegnapi_szamok, felkapott["top"], tegnapi_top)
    return {
        "kulcsszavak": {"szamok": szamok},
        "felkapott": felkapott,
        "valtozas": valtozas,
        "kulcsszo_het": _kulcsszo_het(adatok.get("lanc", {})),
    }


# Az AI válaszának sémája (szekciónként csak folyó szöveg).
def _szekcio_sema():
    return {"type": "object", "additionalProperties": False,
            "required": ["szoveg"],
            "properties": {"szoveg": {"type": "string"}}}


def _valasz_sema():
    sz = _szekcio_sema()
    return {"type": "object", "additionalProperties": False,
            "required": ["valtozas", "kulcsszavak", "felkapott"],
            "properties": {
                "valtozas": sz,
                "kulcsszavak": {"type": "object", "additionalProperties": False,
                                "required": ["napi", "teljes_kep", "het"],
                                "properties": {"napi": sz, "teljes_kep": sz, "het": sz}},
                "felkapott": {"type": "object", "additionalProperties": False,
                              "required": ["napi", "het"],
                              "properties": {"napi": sz, "het": sz}}}}


class _AnthropicKliens:
    """Alap kliens-varrat: az anthropic SDK-t hívja strukturált kimenettel."""

    def uzenet(self, payload, modell):
        import json
        import anthropic
        kliens = anthropic.Anthropic()   # ANTHROPIC_API_KEY a környezetből
        valasz = kliens.messages.create(
            model=modell, max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium",
                           "format": {"type": "json_schema", "schema": _valasz_sema()}},
            system=RENDSZER_PROMPT,
            messages=[{"role": "user", "content":
                       "Elemezd az alábbi VALÓS számokat (JSON). Csak ezekből dolgozz:\n"
                       + json.dumps(payload, ensure_ascii=False)}],
        )
        szoveg = next(b.text for b in valasz.content if b.type == "text")
        return json.loads(szoveg)


def elemez(payload, kliens=None, modell=MODELL):
    kliens = kliens or _AnthropicKliens()
    return kliens.uzenet(payload, modell)


def valasz_to_artefakt(ai_valasz, payload, nap, modell):
    valtozas_szoveg = ai_valasz["valtozas"]["szoveg"]
    if not payload["valtozas"].get("van_elozo"):
        valtozas_szoveg = ("Ma nincs korábbi nap, amivel összevethetnénk, így a napi "
                           "elmozdulás egyelőre nem értékelhető. A friss kép a lenti "
                           "szekciókban olvasható.")
    return {
        "frissitve": seged.idopont_iso(seged.most_utc()),
        "modell": modell,
        "nap": nap,
        "valtozas": {"diff": payload["valtozas"], "szoveg": valtozas_szoveg},
        "kulcsszavak": {
            "szamok": payload["kulcsszavak"]["szamok"],
            "napi": ai_valasz["kulcsszavak"]["napi"],
            "teljes_kep": ai_valasz["kulcsszavak"]["teljes_kep"],
            "het": ai_valasz["kulcsszavak"]["het"],
        },
        "felkapott": {
            "top": payload["felkapott"]["top"],
            "napi": ai_valasz["felkapott"]["napi"],
            "het": ai_valasz["felkapott"]["het"],
            "het_valos": payload["felkapott"]["het"],
        },
    }


def _betolt(fajl):
    p = Path(fajl)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _utolso_napok_trendek(docs_data, hany=7):
    idx = _betolt(Path(docs_data) / "napok" / "index.json") or {"napok": []}
    ki = {}
    for datum in idx["napok"][-hany:]:
        nap_adat = _betolt(Path(docs_data) / "napok" / f"{datum}.json")
        if nap_adat:
            ki[datum] = nap_adat.get("trendek", [])
    return ki


def _index_frissit(elemzesek_dir, nap):
    idx_fajl = elemzesek_dir / "index.json"
    idx = _betolt(idx_fajl) or {"napok": []}
    if nap not in idx["napok"]:
        idx["napok"].append(nap)
        idx["napok"].sort()
    seged.atomi_ir_szoveg(idx_fajl, json.dumps(idx, ensure_ascii=False, indent=0))


def _elozo_archivum(docs_data, nap):
    """A legutolsó, `nap`-nál korábbi archivált elemzés (a nap-diffhez)."""
    idx = _betolt(Path(docs_data) / "elemzesek" / "index.json") or {"napok": []}
    korabbi = [d for d in idx["napok"] if d < nap]
    if not korabbi:
        return None
    return _betolt(Path(docs_data) / "elemzesek" / f"{max(korabbi)}.json")


def futtat(docs_data, nap, kliens=None):
    docs_data = Path(docs_data)
    adatok = {
        "regresszio": _betolt(docs_data / "kulcsszo_regresszio.json") or {},
        "tortenet": _betolt(docs_data / "tortenet.json") or {},
        "legfrissebb": _betolt(docs_data / "legfrissebb.json") or {},
        "napok_trendek": _utolso_napok_trendek(docs_data),
        "lanc": _betolt(docs_data / "kulcsszo_lanc.json") or {},
    }
    tegnapi = _elozo_archivum(docs_data, nap)
    payload = epit_payload(
        adatok,
        tegnapi_szamok=(tegnapi or {}).get("kulcsszavak", {}).get("szamok") if tegnapi else None,
        tegnapi_top=(tegnapi or {}).get("felkapott", {}).get("top") if tegnapi else None,
    )
    try:
        ai_valasz = elemez(payload, kliens=kliens)
    except Exception as e:                       # noqa: BLE001 — fail-soft: az elemzés nem pótolhatatlan
        _log.warning("FIGYELEM: az AI-elemzés elhasalt (%s) — az előző elemzes.json marad.", e)
        return 2
    art = valasz_to_artefakt(ai_valasz, payload, nap=nap, modell=MODELL)
    szoveg = json.dumps(art, ensure_ascii=False, indent=0)
    elemzesek_dir = docs_data / "elemzesek"
    elemzesek_dir.mkdir(exist_ok=True)
    seged.atomi_ir_szoveg(elemzesek_dir / f"{nap}.json", szoveg)
    seged.atomi_ir_szoveg(docs_data / "elemzes.json", szoveg)
    _index_frissit(elemzesek_dir, nap)
    return 0


def main():
    import os
    nap = os.environ.get("ELEMZES_NAP") or seged.bp_idobelyeg(seged.most_utc())[:10]
    docs_data = Path(__file__).resolve().parent.parent / "docs" / "data"
    return futtat(docs_data, nap=nap)
