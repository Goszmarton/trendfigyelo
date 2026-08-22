"""Napi AI-elemzés ág: a commitolt adatokból VALÓS számok (Python) → Claude narratíva.

A számokat MINDIG ez a modul számolja; az AI (elemez) SOHA nem talál ki számot,
kizárólag a payloadban kapott számokból ír (spec §2.1). Ok-okozat tényként tilos;
hipotézis = külön ELMÉLETI mező (spec §2.2).
"""

import json
import logging
from pathlib import Path

from trendfigyelo import seged


_log = logging.getLogger(__name__)

MODELL = "claude-sonnet-5"

RENDSZER_PROMPT = (
    "Magyar nyelvű elemző vagy egy magyar Google Trends figyelő oldalhoz. "
    "SZABÁLYOK, kivétel nélkül: (1) SOHA nem találsz ki számot — kizárólag a kapott "
    "payload számaiból dolgozol. (2) Ok-okozatot TÉNYKÉNT SOHA nem állítasz; a "
    "megfigyelés (mit mutatnak a számok) és a magyarázat (miért) külön mezőben van. "
    "(3) Minden feltételezést az 'elmeleti' mezőbe teszel, 'feltételezés' megfogalmazással; "
    "a tényszerű leolvasásokat a 'megfigyelesek' mezőbe. (4) A felkapott hírekről csak a "
    "kapott 'temak'/'hirek' alapján írsz, hírt/forrást/eseményt nem találsz ki. "
    "Tömör, óvatos, magyar mondatok."
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


def _felkapott(legfrissebb, napok_trendek):
    top = []
    for t in (legfrissebb.get("top_trendek", []) if isinstance(legfrissebb, dict) else []):
        top.append({
            "kifejezes": t.get("kifejezes"), "volumen": t.get("volumen"),
            "novekedes_pct": t.get("novekedes_pct"), "temak": t.get("temak", []),
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
        "kulcsszo_het": {},
    }


# Az AI válaszának sémája (szekciónként szöveg + megfigyelések + elméleti).
def _szekcio_sema():
    return {"type": "object", "additionalProperties": False,
            "required": ["szoveg", "megfigyelesek", "elmeleti"],
            "properties": {"szoveg": {"type": "string"},
                           "megfigyelesek": {"type": "array", "items": {"type": "string"}},
                           "elmeleti": {"type": "array", "items": {"type": "string"}}}}


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
    return {
        "frissitve": seged.idopont_iso(seged.most_utc()),
        "modell": modell,
        "nap": nap,
        "valtozas": {"diff": payload["valtozas"], **ai_valasz["valtozas"]},
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
