# trendfigyelo/heti_ertekeles.py
"""Heti értékelés az előző (hétfő–vasárnap) hétről (magyar, LLM-alapú). A korpusz-építés és a
grounding tiszta/determinista; a Claude Opus hívás nem determinista (AI-jelölt). A havi_nlp.py
PÁRHUZAMOS mintája — a napi/havi elemzés érintetlen."""
import glob
import json
import logging
import os
import time
from datetime import date, timedelta
from pathlib import Path

from trendfigyelo import json_export

_log = logging.getLogger(__name__)


def _het_veg(het_kezdet_iso):
    return (date.fromisoformat(het_kezdet_iso) + timedelta(days=6)).isoformat()


def _iso_het(het_kezdet_iso):
    ev, het, _ = date.fromisoformat(het_kezdet_iso).isocalendar()
    return f"{ev}-W{het:02d}"


def _het_1het(regr_szo):
    iv = ((regr_szo or {}).get("intervallumok") or {}).get("1_het") or {}
    return iv if iv.get("ervenyes") else {}


def _kulcsszavak_het(docs_data):
    """A 28 követett szó heti jele a regresszió `1_het` (érvényes) ablakából: irány, illeszkedés a
    szokásos szinthez, eltérés (mai_reziduum − reziduum_szokasos), heti pálya (illesztes_vonal)."""
    fajl = Path(docs_data) / "kulcsszo_regresszio.json"
    try:
        d = json.loads(fajl.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for szo, w in (d.get("kulcsszavak") or {}).items():
        iv = _het_1het(w)
        mr, rsz = iv.get("mai_reziduum"), iv.get("reziduum_szokasos")
        elteres = (mr - rsz) if isinstance(mr, (int, float)) and isinstance(rsz, (int, float)) else None
        out.append({
            "szo": szo, "domen": w.get("domen"), "tipus": w.get("tipus"),
            "irany": iv.get("irany"), "illeszkedes": iv.get("illeszkedes"),
            "mai_ertek": iv.get("mai_ertek"), "meredekseg_nap": iv.get("meredekseg_nap"),
            "elteres_szokasostol": elteres,
            "palya": [{"idopont_utc": p.get("idopont_utc"), "ertek": p.get("ertek")}
                      for p in (iv.get("illesztes_vonal") or [])],
        })
    return out


def _youtube_het(docs_data):
    fajl = Path(docs_data) / "youtube_regresszio.json"
    try:
        d = json.loads(fajl.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for szo, w in (d.get("kulcsszavak") or {}).items():
        iv = _het_1het(w)
        van = bool(iv)
        out.append({"szo": szo, "domen": w.get("domen"), "tipus": w.get("tipus"),
                    "irany": iv.get("irany") if van else None,
                    "illeszkedes": iv.get("illeszkedes") if van else None,
                    "mai_ertek": iv.get("mai_ertek") if van else None,
                    "nincs_adat": not van})
    return out


def _felkapott_het(docs_data, het_kezdet_iso, het_veg_iso):
    """A hét (hétfő–vasárnap) napfájljaiból aggregált felkapott kifejezések: napok_szama (hány külön
    napon), max_volumen, témák, pár hír. A napfájl szegmentált (reggel/este) VAGY régi lapos — a
    havi_korpusz-szal azonos visszafelé-kompat szabály, de DÁTUM-ABLAKRA szűrve (nem hónap-prefixre)."""
    agg, beolvasott = {}, 0
    for f in sorted(glob.glob(os.path.join(docs_data, "napok", "*.json"))):
        nap = Path(f).stem
        if len(nap) != 10 or nap < het_kezdet_iso or nap > het_veg_iso:
            continue
        try:
            with open(f, encoding="utf-8") as fp:
                d = json.loads(fp.read())
        except (OSError, ValueError):
            continue
        beolvasott += 1
        trend_lista = []
        for szeg in ("reggel", "este"):
            trend_lista += (d.get(szeg) or {}).get("trendek", []) or []
        if not trend_lista:
            trend_lista = d.get("trendek") or []
        napi = set()
        for tr in trend_lista:
            kif = (tr.get("kifejezes") or "").strip()
            if not kif:
                continue
            napi.add(kif)
            a = agg.setdefault(kif, {"kifejezes": kif, "napok_szama": 0, "max_volumen": 0,
                                     "temak": set(), "hirek": []})
            try:
                a["max_volumen"] = max(a["max_volumen"], int(tr.get("volumen") or 0))
            except (TypeError, ValueError):
                pass
            a["temak"].update(tr.get("temak") or [])
            for h in (tr.get("hirek") or [])[:2]:
                cim = h.get("cim") if isinstance(h, dict) else h
                if cim and cim not in a["hirek"] and len(a["hirek"]) < 3:
                    a["hirek"].append(cim)
        for kif in napi:
            agg[kif]["napok_szama"] += 1
    szavak = sorted(agg.values(), key=lambda a: (-a["napok_szama"], -a["max_volumen"], a["kifejezes"]))
    for a in szavak:
        a["temak"] = sorted(a["temak"])
    return szavak, beolvasott


def heti_korpusz(docs_data, het_kezdet_iso):
    """Az előző hét (hétfő=het_kezdet_iso … vasárnap) DETERMINISTA aggregálása. Csak OLVAS."""
    het_veg = _het_veg(het_kezdet_iso)
    felkapott, napok = _felkapott_het(docs_data, het_kezdet_iso, het_veg)
    return {
        "het_kezdet": het_kezdet_iso, "het_veg": het_veg, "iso_het": _iso_het(het_kezdet_iso),
        "napok": napok,
        "kulcsszavak": _kulcsszavak_het(docs_data),
        "felkapott": felkapott,
        "youtube": _youtube_het(docs_data),
    }


def _valasz_sema():
    """A heti értékelés 6 részének strukturált sémája (spec §4). Minden mező kötelező (üres megengedett),
    additionalProperties:False."""
    str_lista = {"type": "array", "items": {"type": "string"}}
    return {
        "type": "object", "additionalProperties": False,
        "required": ["vezetoi_osszefoglalo", "figyelem_atrendezodes", "ugyek_eletutja",
                     "melyebb_temak", "google_youtube_osszefugges", "jovo_heti_figyelendok"],
        "properties": {
            "vezetoi_osszefoglalo": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
            "figyelem_atrendezodes": {
                "type": "object", "additionalProperties": False,
                "required": ["erosodo", "gyengulo"],
                "properties": {"erosodo": str_lista, "gyengulo": str_lista}},
            "ugyek_eletutja": {
                "type": "object", "additionalProperties": False,
                "required": ["rovid_kiugras", "hosszabb_kiugras", "visszatero"],
                "properties": {"rovid_kiugras": {"type": "string"},
                               "hosszabb_kiugras": {"type": "string"},
                               "visszatero": {"type": "string"}}},
            "melyebb_temak": {
                "type": "array", "maxItems": 3,
                "items": {"type": "object", "additionalProperties": False,
                          "required": ["tema", "keresesi_palya", "kapcsolodo_kifejezesek",
                                       "ellenorzott_esemenyek", "magyarazat"],
                          "properties": {"tema": {"type": "string"},
                                         "keresesi_palya": {"type": "string"},
                                         "kapcsolodo_kifejezesek": {"type": "string"},
                                         "ellenorzott_esemenyek": {"type": "string"},
                                         "magyarazat": {"type": "string"}}}},
            "google_youtube_osszefugges": {"type": "string"},
            "jovo_heti_figyelendok": {"type": "array", "items": {"type": "string"}},
        },
    }


RENDSZER_PROMPT_HETI = (
    "Heti értékelést készítő elemző vagy egy magyar Google Trends és YouTube figyelő oldalhoz. A "
    "bemeneted egy HETI korpusz az előző hétfő–vasárnap hétről: (1) a KÖVETETT keresőszavak heti "
    "iránya (nő/csökken/stagnál), a szokásos szintjükhöz mért helyzete (felette/alatta/illeszkedik) "
    "és a szokásostól való eltérésük; (2) a héten FELKAPOTT (trendelt) keresőszavak, szavanként azzal, "
    "hogy hány külön napon trendeltek, a legmagasabb volumennel, a Google-témacímkékkel és néhány "
    "hír-címmel; (3) a YouTube-keresőszavak heti iránya/szintje. A feladatod az ügyek tartósságának és "
    "ÖSSZEFÜGGÉSÉNEK értékelése — mi tartott ki, mi volt rövid kiugrás, mi tért vissza, és hol látszik "
    "kapcsolat a témák és a két adatforrás között. "
    "SZABÁLYOK, kivétel nélkül: "
    "(1) MINDEN kimenet magyar nyelven, LAIKUS olvasónak, folyó mondatokban — SOHA ne írj mezőnevet, "
    "JSON-t vagy technikai kulcsot a szövegbe. "
    "(2) GROUNDING: kizárólag a kapott korpusz számaiból/szavaiból/híreiből dolgozol; keresőszót, "
    "eseményt vagy okot SOHA nem találsz ki. Okot vagy eseményt CSAK akkor írsz, ha a korpuszban "
    "ténylegesen van hozzá hír — hír nélkül csak a megfigyelt mozgást írod le, magyarázat nélkül. "
    "(3) A hat rész: "
    "`vezetoi_osszefoglalo` = legfeljebb 5 megállapítás arról, mi változott a héten és miért érdemes "
    "vele foglalkozni (ha csendes volt a hét, ezt őszintén jelezd). "
    "`figyelem_atrendezodes` = mely témák ERŐSÖDTEK (`erosodo`) és mely GYENGÜLTEK (`gyengulo`) a "
    "szokásos szintjükhöz képest — az illeszkedés/irány/eltérés alapján. "
    "`ugyek_eletutja` = az ügyek tartóssága: `rovid_kiugras` (ami csak egy-két napig szökött fel), "
    "`hosszabb_kiugras` (ami több napon át kitartott), `visszatero` (ami a héten belül vagy korábbról "
    "vissza-visszatért). "
    "`melyebb_temak` = 2–3 kiemelt téma MÉLYEBB elemzése, mindegyikhez: `keresesi_palya` (hogyan "
    "mozgott a héten a keresés), `kapcsolodo_kifejezesek` (a korpuszból kapcsolódó szavak), "
    "`ellenorzott_esemenyek` (CSAK a korpusz hír-címeiből), `magyarazat` (grounded értelmezés). "
    "`google_youtube_osszefugges` = hol látszik közös vagy párhuzamos mozgás a követett Google-szavak "
    "és a YouTube-szavak között (téma- vagy iránybeli egybeesés) — ha nincs, ezt mondd ki. "
    "`jovo_heti_figyelendok` = mire érdemes figyelni a jövő héten, a heti pályából és a visszatérőkből "
    "levezetve, ÓVATOSAN (ez nem eseményjóslás, hanem figyelmeztetés, mit érdemes nézni). "
    "(4) Ahol a fogalmazás óvatosabb, azt a mondat maga hordozza; a rövid gondolatjel „–”."
)


MODELL = "claude-opus-4-8"
MAX_TOKENS_HETI = 64000   # gondolkodás + strukturált kimenet KÖZÖS kerete; a heti a napi (32000) és a
#  havi (128000) közt — 6 rész + 2–3 mély elemzés. Csonkolásnál (json.loads hiba) emelni (max 128000).


class _HetiKliens:
    """A heti Claude-kliens: az anthropic SDK-t STREAMELVE hívja strukturált kimenettel (a havi_nlp
    _NlpKliens mintája). Az `sdk` injektálható (teszt); None → anthropic.Anthropic() a kulccsal."""

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
            model=modell, max_tokens=MAX_TOKENS_HETI,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium",
                           "format": {"type": "json_schema", "schema": _valasz_sema()}},
            system=RENDSZER_PROMPT_HETI,
            messages=[{"role": "user", "content":
                       "Értékeld az alábbi heti korpuszt (JSON). Csak ebből dolgozz:\n"
                       + json.dumps(korpusz, ensure_ascii=False)}],
        ) as folyam:
            valasz = folyam.get_final_message()
        szoveg = next(b.text for b in valasz.content if b.type == "text")
        return json.loads(szoveg)


RETRY_PROBAK = 3
RETRY_BACKOFF_MP = (5, 20, 60)


def heti_elemez(korpusz, kliens=None, modell=MODELL,
                probak=RETRY_PROBAK, backoff_mp=RETRY_BACKOFF_MP, alvo=None):
    """A heti Claude-hívás BOUNDED RETRY-vel (a havi_nlp_elemez mintája): intermittens API-hibánál
    `probak` próba, közöttük `backoff_mp` várakozás; csak az utolsó bukás propagál."""
    kliens = kliens or _HetiKliens()
    alvo = alvo if alvo is not None else time.sleep
    utolso = None
    for i in range(probak):
        try:
            return kliens.uzenet(korpusz, modell)
        except Exception as e:   # noqa: BLE001 — intermittens API-hiba: bounded retry, végül propagál
            utolso = e
            if i + 1 < probak:
                _log.warning("FIGYELEM: a heti elemzés elhasalt (%s); újrapróba %d/%d %d mp múlva.",
                             e, i + 2, probak, backoff_mp[i])
                alvo(backoff_mp[i])
    raise utolso


def grounding_validal(eredmeny, korpusz):
    """Hallucináció-védelem: az `erosodo`/`gyengulo` szó-listákat a korpusz kulcsszó-halmazára szűri
    (a nem-korpuszbeli kiesik). A prózai mezők (vezetoi_osszefoglalo, melyebb_temak, összefüggés,
    figyelendők) NEM szűrtek — ezek a modell értelmezései a grounded számok fölött. Determinista,
    nem mutálja a bemenetet."""
    kov = {s.get("szo") for s in (korpusz.get("kulcsszavak") or [])}
    kov |= {s.get("kifejezes") for s in (korpusz.get("felkapott") or [])}
    kov |= {s.get("szo") for s in (korpusz.get("youtube") or [])}
    fa = eredmeny.get("figyelem_atrendezodes") or {}
    tiszta = {
        "erosodo": [sz for sz in (fa.get("erosodo") or []) if sz in kov],
        "gyengulo": [sz for sz in (fa.get("gyengulo") or []) if sz in kov],
    }
    return {**eredmeny, "figyelem_atrendezodes": tiszta}


def figyelem_adat(korpusz):
    """A divergáló sávdiagram DETERMINISTA adata: a nem-None eltérésű követett szavak, az eltérés
    szerint CSÖKKENŐ sorrendben (erősödő = pozitív felül, gyengülő = negatív alul)."""
    sorok = [{"szo": s.get("szo"), "elteres": s.get("elteres_szokasostol"),
              "irany": s.get("irany"), "illeszkedes": s.get("illeszkedes"), "domen": s.get("domen")}
             for s in (korpusz.get("kulcsszavak") or []) if s.get("elteres_szokasostol") is not None]
    return sorted(sorok, key=lambda x: x["elteres"], reverse=True)


def heti_ir(docs_data, het_kezdet, eredmeny):
    """A heti eredmény külön `heti/<het_kezdet>.json`-ba, atomi írással (a havi_nlp_ir mintája)."""
    mappa = Path(docs_data) / "heti"
    mappa.mkdir(parents=True, exist_ok=True)
    return json_export._ir_json(mappa / (het_kezdet + ".json"), eredmeny)


def heti_index_ir(docs_data):
    """A heti mappa hetei a frontend hét-választójához (az index.json-t kihagyva)."""
    mappa = Path(docs_data) / "heti"
    hetek = sorted(p.stem for p in mappa.glob("*.json") if p.stem != "index")
    return json_export._ir_json(mappa / "index.json",
                                {"hetek": hetek, "legutolso": hetek[-1] if hetek else None})


def heti_generalas(docs_data, het_kezdet, keszult_iso, kliens=None):
    """A heti értékelés generáló belépési pontja: korpusz → Claude (fail-soft: tartós hibán None) →
    grounding → figyelem-diagramadat + het/keszult/modell/korpusz-meta → atomi írás. A keszult_iso
    PARAMÉTER (nincs argless datetime.now())."""
    korpusz = heti_korpusz(docs_data, het_kezdet)
    try:
        eredmeny = heti_elemez(korpusz, kliens=kliens)
    except Exception as e:   # noqa: BLE001 — tartós API-hiba a bounded retry után: fail-soft
        _log.error("HIBA: a heti értékelés tartósan elhasalt (%s hét): %s", het_kezdet, e)
        return None
    eredmeny = grounding_validal(eredmeny, korpusz)
    eredmeny["het_kezdet"] = korpusz["het_kezdet"]
    eredmeny["het_veg"] = korpusz["het_veg"]
    eredmeny["iso_het"] = korpusz["iso_het"]
    eredmeny["figyelem"] = figyelem_adat(korpusz)
    eredmeny["keszult"] = keszult_iso
    eredmeny["modell"] = MODELL
    eredmeny["korpusz"] = {"het_kezdet": korpusz["het_kezdet"], "het_veg": korpusz["het_veg"],
                           "iso_het": korpusz["iso_het"], "napok": korpusz["napok"],
                           "egyedi_felkapott": len(korpusz["felkapott"])}
    heti_ir(docs_data, het_kezdet, eredmeny)
    return eredmeny
