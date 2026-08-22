"""Napi AI-elemzés ág: a commitolt adatokból VALÓS számok (Python) → Claude narratíva.

A számokat MINDIG ez a modul számolja; az AI (elemez) SOHA nem talál ki számot,
kizárólag a payloadban kapott számokból ír (spec §2.1). Ok-okozat tényként tilos;
hipotézis = külön ELMÉLETI mező (spec §2.2).
"""

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
