"""Ügy-életút a Bővítés fülhöz: gördülő 30-napos korpusz (determinista aggregálás) + LLM-csoportosítás
(Claude Opus) ügyekbe + determinista ügy-metrikák. A heti_ertekeles/havi_nlp mintája. Grounded:
a Python számol, az LLM csak csoportosít/nevez/sorol be a korpuszból."""
import glob
import json
import logging
import os
import time
from datetime import date, timedelta
from pathlib import Path

from trendfigyelo import json_export, szakpolitika

_log = logging.getLogger(__name__)

UJ_KUSZOB_NAP = 7          # 'újonnan megfigyelt': az első nap az ablak utolsó ennyi napján belül
FOLYAMATOS_ARANY = 0.5     # 'folyamatosan jelenlévő': a span napjainak legalább ennyi részén jelen
VISSZATERO_SZUNET = 3      # 'visszatérő': legalább ennyi napos szünet két jelenléti nap között


def _napok_kozott(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def _eletut(kif, veg_nap, ablak_nap):
    napok = sorted(kif.get("napok") or [])
    if not napok:
        return "egyeb"
    elso, utolso = napok[0], napok[-1]
    span = _napok_kozott(elso, utolso) + 1
    # visszatérő: van VISSZATERO_SZUNET-nél hosszabb rés két jelenléti nap között
    van_szunet = any(_napok_kozott(napok[i], napok[i + 1]) > VISSZATERO_SZUNET for i in range(len(napok) - 1))
    if van_szunet:
        return "visszatero"
    # újonnan: az első nap az ablak utolsó UJ_KUSZOB_NAP napján belül, és rövid span
    if _napok_kozott(elso, veg_nap) < UJ_KUSZOB_NAP and span <= UJ_KUSZOB_NAP:
        return "ujonnan_megfigyelt"
    # folyamatos: a span napjainak legalább FOLYAMATOS_ARANY részén jelen
    if span >= 2 and len(napok) / span >= FOLYAMATOS_ARANY:
        return "folyamatosan_jelenlevo"
    return "egyeb"


def _mozgas(volumen_sor):
    ertekek = [float(p.get("max_volumen") or 0) for p in (volumen_sor or [])]
    if len(ertekek) < 2:
        return "nem_megallapithato"
    elso_fel = ertekek[: len(ertekek) // 2] or ertekek[:1]
    masodik_fel = ertekek[len(ertekek) // 2:]
    d = (sum(masodik_fel) / len(masodik_fel)) - (sum(elso_fel) / len(elso_fel))
    bazis = max(1.0, sum(ertekek) / len(ertekek))
    if d / bazis > 0.2:
        return "erosodo"
    if d / bazis < -0.2:
        return "lecsengo"
    return "stabil"


def ugy_korpusz(docs_data, veg_nap, ablak_nap=30):
    """A [veg_nap-ablak_nap+1 .. veg_nap] ablak felkapott kifejezéseinek determinista aggregálása.
    Csak OLVAS (napok/*.json). Per kifejezés: jelenléti napok, első/utolsó nap, volumen-sor, témák, hírek."""
    kezdet = (date.fromisoformat(veg_nap) - timedelta(days=ablak_nap - 1)).isoformat()
    agg = {}
    for f in sorted(glob.glob(os.path.join(docs_data, "napok", "*.json"))):
        nap = Path(f).stem
        if len(nap) != 10 or nap < kezdet or nap > veg_nap:
            continue
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        trendek = []
        for szeg in ("reggel", "este"):
            trendek += (d.get(szeg) or {}).get("trendek", []) or []
        if not trendek:
            trendek = d.get("trendek") or []
        napi_max = {}
        for tr in trendek:
            kif = (tr.get("kifejezes") or "").strip()
            if not kif:
                continue
            a = agg.setdefault(kif, {"kifejezes": kif, "napok": set(), "volumen_map": {},
                                     "temak": set(), "hirek": []})
            a["napok"].add(nap)
            try:
                v = int(tr.get("volumen") or 0)
            except (TypeError, ValueError):
                v = 0
            napi_max[kif] = max(napi_max.get(kif, 0), v)
            a["temak"].update(tr.get("temak") or [])
            for h in (tr.get("hirek") or [])[:2]:
                cim = h.get("cim") if isinstance(h, dict) else h
                if cim and cim not in a["hirek"] and len(a["hirek"]) < 3:
                    a["hirek"].append(cim)
        for kif, v in napi_max.items():
            agg[kif]["volumen_map"][nap] = v
    kifejezesek = []
    for a in agg.values():
        napok = sorted(a["napok"])
        volumen_sor = [{"nap": n, "max_volumen": a["volumen_map"][n]} for n in napok]
        kif = {"kifejezes": a["kifejezes"], "elso_nap": napok[0], "utolso_nap": napok[-1],
               "napok": napok, "napok_szama": len(napok), "volumen_sor": volumen_sor,
               "temak": sorted(a["temak"]), "hirek": a["hirek"]}
        kif["eletut"] = _eletut(kif, veg_nap, ablak_nap)
        kif["mozgas"] = _mozgas(volumen_sor)
        kif["szakpolitika"] = szakpolitika.szakpolitika_besorol(kifejezes=a["kifejezes"], temak=kif["temak"])
        kifejezesek.append(kif)
    kifejezesek.sort(key=lambda c: (-c["napok_szama"], c["elso_nap"], c["kifejezes"]))
    return {"ablak": {"kezdet": kezdet, "veg": veg_nap, "nap": ablak_nap}, "kifejezesek": kifejezesek}


def _valasz_sema():
    """Az ügy-csoportosítás strukturált sémája: ügyenként név + a korpuszból csoportosított
    kifejezések + szakpolitika (enum) + rövid összefoglaló. additionalProperties:False."""
    return {
        "type": "object", "additionalProperties": False, "required": ["ugyek"],
        "properties": {"ugyek": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["nev", "kifejezesek", "szakpolitika", "osszefoglalo"],
            "properties": {
                "nev": {"type": "string"},
                "kifejezesek": {"type": "array", "items": {"type": "string"}},
                "szakpolitika": {"type": "string", "enum": sorted(szakpolitika.SZAKPOLITIKA_SLUGOK)},
                "osszefoglalo": {"type": "string"},
            }}}},
    }


RENDSZER_PROMPT_UGYEK = (
    "Közügy-elemző vagy egy magyar Google Trends figyelő oldalhoz. A bemeneted egy 30 napos korpusz: "
    "a felkapott (trendelt) magyar keresőkifejezések, mindegyikhez determinista metrikákkal (hány napon "
    "volt jelen, mikor tűnt fel, az életút-besorolása és a mozgása, a Google-témacímkék, pár hír-cím). "
    "A feladatod a kifejezéseket JELENTÉS szerint ÜGYEKbe CSOPORTOSÍTANI — egy ügy ugyanazon közügy/téma "
    "köré gyűlő kifejezések halmaza (például ugyanannak az árnak vagy intézkedésnek a különböző "
    "megfogalmazásai). "
    "SZABÁLYOK, kivétel nélkül: "
    "(1) GROUNDING: kizárólag a korpuszban SZEREPLŐ kifejezéseket csoportosítod; új kifejezést SOHA nem "
    "találsz ki, és egy kifejezés legfeljebb EGY ügybe kerül. "
    "(2) Minden ügynek adj rövid, beszédes magyar NEVET, 1-2 mondatos magyar ÖSSZEFOGLALÓT (grounded, a "
    "korpusz adataiból), és sorold be a megadott szakpolitikai kategóriák (enum) EGYIKÉBE a jelentése "
    "és a témacímkéi alapján. "
    "(3) A prózába SOHA ne írj mezőnevet, JSON-t vagy technikai kulcsot; magyar, laikus olvasónak. "
    "(4) Rövid „–” gondolatjel. Ne minden kifejezés legyen külön ügy — a valódi összetartozókat vond össze; "
    "az egyedi, társíthatatlan kifejezés maradhat önálló ügy."
)

MODELL = "claude-opus-4-8"
MAX_TOKENS_UGYEK = 128000     # a 30-napos korpusz nagy lehet; a havi (128000) mintája, streaming kötelező

RETRY_PROBAK = 3
RETRY_BACKOFF_MP = (5, 20, 60)


class _UgyKliens:
    """Streaming Claude-kliens strukturált kimenettel (a heti_ertekeles._HetiKliens mintája)."""

    def __init__(self, sdk=None):
        self._sdk = sdk

    def _kliens(self):
        if self._sdk is not None:
            return self._sdk
        import anthropic
        return anthropic.Anthropic()

    def uzenet(self, korpusz, modell):
        kliens = self._kliens()
        with kliens.messages.stream(
            model=modell, max_tokens=MAX_TOKENS_UGYEK,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium",
                           "format": {"type": "json_schema", "schema": _valasz_sema()}},
            system=RENDSZER_PROMPT_UGYEK,
            messages=[{"role": "user", "content":
                       "Csoportosítsd az alábbi korpusz kifejezéseit ügyekbe (JSON). Csak ebből dolgozz:\n"
                       + json.dumps(korpusz, ensure_ascii=False)}],
        ) as folyam:
            valasz = folyam.get_final_message()
        szoveg = next(b.text for b in valasz.content if b.type == "text")
        return json.loads(szoveg)


def ugy_elemez(korpusz, kliens=None, modell=MODELL, probak=RETRY_PROBAK,
               backoff_mp=RETRY_BACKOFF_MP, alvo=None):
    """Bounded-retry Claude-hívás (a heti_elemez mintája); csak az utolsó bukás propagál."""
    kliens = kliens or _UgyKliens()
    alvo = alvo if alvo is not None else time.sleep
    utolso = None
    for i in range(probak):
        try:
            return kliens.uzenet(korpusz, modell)
        except Exception as e:   # noqa: BLE001 — intermittens API-hiba: bounded retry
            utolso = e
            if i + 1 < probak:
                _log.warning("FIGYELEM: az ügy-elemzés elhasalt (%s); újrapróba %d/%d %d mp múlva.",
                             e, i + 2, probak, backoff_mp[i])
                alvo(backoff_mp[i])
    raise utolso


def grounding_validal(eredmeny, korpusz):
    """Minden ügy `kifejezesek`-je a korpusz kifejezés-halmazára szűrve; üres taggé vált ügy kiesik;
    érvénytelen `szakpolitika` → determinista fallback a tagokból. Nem mutálja a bemenetet."""
    korp = {c.get("kifejezes") for c in (korpusz.get("kifejezesek") or [])}
    tema_map = {c.get("kifejezes"): (c.get("temak") or []) for c in (korpusz.get("kifejezesek") or [])}
    ugyek = []
    for ugy in (eredmeny.get("ugyek") or []):
        kif = [k for k in (ugy.get("kifejezesek") or []) if k in korp]
        if not kif:
            continue
        sp = ugy.get("szakpolitika")
        if sp not in szakpolitika.SZAKPOLITIKA_SLUGOK:
            temak = []
            for k in kif:
                temak += tema_map.get(k, [])
            sp = szakpolitika.szakpolitika_besorol(kifejezes=kif[0], temak=temak)
        ugyek.append({**ugy, "kifejezesek": kif, "szakpolitika": sp})
    return {**eredmeny, "ugyek": ugyek}


def ugy_osszegez(eredmeny, korpusz):
    """Minden ügy ÉLETÚT-metrikáját a TAGJAI (kifejezései) metrikáiból aggregálja (determinista):
    napok uniója, első/utolsó nap, napok_szama, életút/mozgás, idővonal (napi jelenlét)."""
    kmap = {c["kifejezes"]: c for c in (korpusz.get("kifejezesek") or [])}
    veg = (korpusz.get("ablak") or {}).get("veg")
    ablak_nap = (korpusz.get("ablak") or {}).get("nap") or 30
    ugyek = []
    for ugy in (eredmeny.get("ugyek") or []):
        tagok = [kmap[k] for k in ugy.get("kifejezesek", []) if k in kmap]
        napok = sorted({n for t in tagok for n in (t.get("napok") or [])})
        vol = {}
        for t in tagok:
            for p in (t.get("volumen_sor") or []):
                vol[p["nap"]] = vol.get(p["nap"], 0) + int(p.get("max_volumen") or 0)
        idovonal = [{"nap": n, "jelen": True, "ossz_volumen": vol.get(n, 0)} for n in napok]
        kif_agg = {"napok": napok, "elso_nap": napok[0] if napok else None,
                   "utolso_nap": napok[-1] if napok else None}
        ugyek.append({**ugy,
                      "elso_nap": kif_agg["elso_nap"], "utolso_nap": kif_agg["utolso_nap"],
                      "napok_szama": len(napok),
                      "eletut": _eletut(kif_agg, veg or napok[-1], ablak_nap) if napok else "egyeb",
                      "mozgas": _mozgas([{"max_volumen": p["ossz_volumen"]} for p in idovonal]),
                      "idovonal": idovonal})
    return {**eredmeny, "ugyek": ugyek}


def ugy_ir(docs_data, eredmeny):
    return json_export._ir_json(Path(docs_data) / "ugyek.json", eredmeny)


def ugy_generalas(docs_data, veg_nap, keszult_iso, ablak_nap=30, kliens=None):
    """Belépési pont: korpusz → Claude (fail-soft: tartós hibán None, NEM ír) → grounding →
    ügy-összegzés → meta → atomi írás. A keszult_iso/veg_nap PARAMÉTER (nincs argless now())."""
    korpusz = ugy_korpusz(docs_data, veg_nap, ablak_nap=ablak_nap)
    try:
        eredmeny = ugy_elemez(korpusz, kliens=kliens)
    except Exception as e:   # noqa: BLE001 — tartós API-hiba a bounded retry után: fail-soft
        _log.error("HIBA: az ügy-elemzés tartósan elhasalt (%s): %s", veg_nap, e)
        return None
    eredmeny = grounding_validal(eredmeny, korpusz)
    eredmeny = ugy_osszegez(eredmeny, korpusz)
    eredmeny["ablak"] = korpusz["ablak"]
    eredmeny["keszult"] = keszult_iso
    eredmeny["szamitva_utc"] = keszult_iso
    eredmeny["modell"] = MODELL
    ugy_ir(docs_data, eredmeny)
    return eredmeny
