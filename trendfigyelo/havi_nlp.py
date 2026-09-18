"""Havi NLP-elemzés a felkapott keresőszavakról (magyar, LLM-alapú). A korpusz-építés és a
grounding-validáció tiszta/determinista; az NLP-hívás a Claude Opus (nem determinista, AI-jelölt)."""
import glob
import json
import logging
import os
import time
from pathlib import Path

from trendfigyelo import json_export

_log = logging.getLogger(__name__)

def havi_korpusz(docs_data, honap):
    """A hónap (YYYY-MM) felkapott szavai aggregálva: egyedi kifejezés + gyakoriság (hány külön nap),
    max volumen, témák-halmaz, pár hír-cím. Csak OLVAS (napok/*.json READ-ONLY)."""
    minta = os.path.join(docs_data, "napok", honap + "-*.json")
    fajlok = sorted(glob.glob(minta))
    agg = {}
    beolvasott = 0                                            # csak a sikeresen parse-olt napokat számoljuk
    for f in fajlok:
        try:
            with open(f, encoding="utf-8") as fp:
                nap = json.loads(fp.read())
        except (OSError, ValueError):
            continue
        beolvasott += 1
        napi_kif = set()
        # szegmentált (reggel/este) VAGY régi lapos (top-level `trendek`) napszerkezet: a
        # 2026-08 eleji napokon nincs reggel/este szegmens, csak közvetlen `trendek` — ilyenkor
        # arra esünk vissza (visszafelé-kompatibilitás, hogy a régi hónapok is teljes korpuszt
        # adjanak). Ha VAN szegmens-adat, a top-level `trendek` NEM számít.
        trend_lista = []
        for szeg in ("reggel", "este"):
            trend_lista += (nap.get(szeg) or {}).get("trendek", []) or []
        if not trend_lista:
            trend_lista = nap.get("trendek") or []
        for tr in trend_lista:
            kif = (tr.get("kifejezes") or "").strip()
            if not kif:
                continue
            napi_kif.add(kif)
            a = agg.setdefault(kif, {"kifejezes": kif, "gyakorisag": 0, "max_volumen": 0,
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
        for kif in napi_kif:
            agg[kif]["gyakorisag"] += 1                       # naponta EGYSZER számít
    szavak = sorted(agg.values(), key=lambda a: (-a["gyakorisag"], -a["max_volumen"], a["kifejezes"]))
    for a in szavak:
        a["temak"] = sorted(a["temak"])
    return {"honap": honap, "napok": beolvasott, "egyedi_szo": len(szavak), "szavak": szavak}


def _nlp_sema():
    """A havi NLP strukturált válasz sémája (spec §3.2): lemma-térkép, NER (3 csoport),
    tematikus klaszterek, összegzés. Minden mező kötelező, extra kulcs tiltva (additionalProperties:False)."""
    entitas_lista = {
        "type": "array",
        "items": {
            "type": "object", "additionalProperties": False,
            "required": ["nev", "szavak"],
            "properties": {
                "nev": {"type": "string"},
                "szavak": {"type": "array", "items": {"type": "string"}},
            },
        },
    }
    return {
        "type": "object", "additionalProperties": False,
        "required": ["lemmak", "ner", "klaszterek", "osszegzes"],
        "properties": {
            "lemmak": {
                "type": "array",
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["szo", "lemma"],
                    "properties": {"szo": {"type": "string"}, "lemma": {"type": "string"}},
                },
            },
            "ner": {
                "type": "object", "additionalProperties": False,
                "required": ["orszagok", "telepulesek", "szemelyek"],
                "properties": {
                    "orszagok": entitas_lista,
                    "telepulesek": entitas_lista,
                    "szemelyek": entitas_lista,
                },
            },
            "klaszterek": {
                "type": "array",
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["cimke", "szavak", "ertelmezes", "uralkodo_temak"],
                    "properties": {
                        "cimke": {"type": "string"},
                        "szavak": {"type": "array", "items": {"type": "string"}},
                        "ertelmezes": {"type": "string"},
                        "uralkodo_temak": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "osszegzes": {"type": "string"},
        },
    }


RENDSZER_PROMPT_NLP = (
    "Magyar nyelvi (NLP) elemző vagy egy magyar Google Trends figyelő oldalhoz. A bemeneted egy "
    "HAVI korpusz: az adott hónapban felkapott (trendelt) magyar keresőszavak, szavanként a "
    "gyakorisággal (hány külön napon trendelt), a legmagasabb megfigyelt kereső-volumennel, a "
    "Google-témacímkékkel és néhány kapcsolódó hír-címmel. A feladatod MÉLY, alapos, PONTOS magyar "
    "NLP-feldolgozás — nem felületes összefoglaló. "
    "SZABÁLYOK, kivétel nélkül: "
    "(1) MINDEN kimenet magyar nyelven íródik (lemmák, entitásnevek, klaszter-címkék, értelmezések, "
    "összegzés). "
    "(2) GROUNDING: kizárólag a kapott korpusz szavaiból/azok tartalmából dolgozol. NER-entitást, "
    "klaszter-tagszót vagy bármilyen kifejezést SOHA nem találsz ki — ha egy szó nem szerepel a "
    "korpuszban, nem veheted fel semmilyen listába. "
    "(3) TELJES LEFEDETTSÉG: minden egyes korpusz-szóra pontosan egy lemma-bejegyzést adsz (szo→lemma), "
    "és minden egyes korpusz-szó pontosan EGY klaszterbe kerül — egyetlen szó sem maradhat klaszter "
    "nélkül, és egyetlen szó sem szerepelhet két klaszterben. "
    "(4) MAGYAR LEMMATIZÁLÁS: minden szóhoz a helyes magyar tő/szótári alakot add meg (ragozott, "
    "toldalékolt vagy összetett kifejezésekre is a jelentés szerinti alapalakot). "
    "(5) MAGYAR NER: azonosítsd a korpusz-szavakban megjelenő ORSZÁGOKAT, (magyar és külföldi) "
    "TELEPÜLÉSEKET és SZEMÉLYNEVEKET; minden felismert entitáshoz sorold fel, mely korpusz-szavakban "
    "jelenik meg. Ha egy kategóriában nincs felismerhető entitás, üres listát adsz — nem találsz ki. "
    "(6) JELENTÉS-ALAPÚ KLASZTEREK: a csoportosítás a TÉMA/JELENTÉS szerint történjen, NEM felszíni "
    "szó-egyezés vagy karakteres hasonlóság alapján (pl. két teljesen más témájú szó ne kerüljön egy "
    "klaszterbe csak azért, mert közös szótöredéket tartalmaznak). Minden klaszterhez adj magyar "
    "CÍMKÉT, rövid magyar ÉRTELMEZÉST (mit jelent ez a csoportosulás a havi keresési érdeklődésben), "
    "és a domináns Google-témákat (a tagszavak témacímkéiből, ha vannak). "
    "(7) MÉLYSÉG: használd a gyakoriságot, a volument, a témacímkéket és a hír-címeket is a "
    "klaszterezés és az értelmezés megalapozásához — ne csak a szó szövegét nézd. Törekedj arra, hogy "
    "a klaszterek száma és mérete arányos legyen a korpusz méretével és sokszínűségével (se néhány "
    "óriás gyűjtő-kategória, se egy-egy szavas apró klaszterek tömkelege, hacsak a tartalom ezt nem "
    "indokolja). "
    "(8) ÖSSZEGZÉS: az `osszegzes` mező folyó magyar prózai szöveg, amely a hónap keresési "
    "érdeklődésének egészét értelmezi — miről szólt a hónap a magyar közönség keresései alapján, "
    "milyen témák domináltak, mik voltak a visszatérő vagy kiugró minták. Kizárólag a kapott adatokból "
    "vonj le következtetést; ahol óvatosabban fogalmazol, azt a fogalmazás maga hordozza."
)


MODELL_NLP = "claude-opus-4-8"
MAX_TOKENS_NLP = 64000   # a gondolkodás (adaptive thinking) ÉS a strukturált kimenet KÖZÖS kerete
#  A havi kimenet nagyságrenddel nagyobb a napinál: MINDEN korpusz-szóra lemma + klaszter-tagság + NER
#  + prózai összegzés (több száz szónál sok ezer token). 32000-nél a mély gondolkodás elhasználta a
#  keretet és a JSON levágódott (json.loads „Expecting ',' delimiter") → 64000, hogy a gondolkodásnak
#  ÉS a teljes strukturált kimenetnek is legyen helye. STREAMING kötelező (nincs HTTP-időtúllépés).


class _NlpKliens:
    """A havi NLP kliens-varrat: az anthropic SDK-t STREAMELVE hívja strukturált kimenettel
    (az elemzo._AnthropicKliens mintája, saját séma+prompt). Az `sdk` injektálható (teszt);
    None → az anthropic.Anthropic() a környezeti kulccsal."""

    def __init__(self, sdk=None):
        self._sdk = sdk

    def _kliens(self):
        if self._sdk is not None:
            return self._sdk
        import anthropic
        return anthropic.Anthropic()   # ANTHROPIC_API_KEY a környezetből

    def uzenet(self, korpusz, modell):
        kliens = self._kliens()
        with kliens.messages.stream(   # STREAM: a nagy max_tokens nem üt HTTP-időtúllépésbe
            model=modell, max_tokens=MAX_TOKENS_NLP,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium",
                           "format": {"type": "json_schema", "schema": _nlp_sema()}},
            system=RENDSZER_PROMPT_NLP,
            messages=[{"role": "user", "content":
                       "Dolgozd fel az alábbi havi felkapott keresőszó-korpuszt (JSON). Csak ebből "
                       "dolgozz:\n" + json.dumps(korpusz, ensure_ascii=False)}],
        ) as folyam:
            valasz = folyam.get_final_message()
        szoveg = next(b.text for b in valasz.content if b.type == "text")
        return json.loads(szoveg)


RETRY_PROBAK_NLP = 3                 # a Claude-hívás max ennyi próbája
RETRY_BACKOFF_MP_NLP = (5, 20, 60)   # növekvő várakozás a próbák közt (mp)


def havi_nlp_elemez(korpusz, kliens=None, modell=MODELL_NLP,
                     probak=RETRY_PROBAK_NLP, backoff_mp=RETRY_BACKOFF_MP_NLP, alvo=None):
    """A havi NLP Claude-hívás BOUNDED RETRY-vel (az elemzo.elemez mintája): az Anthropic API néha
    intermittens hibát ad egy egyébként érvényes, determinista kérésre; `probak` próba, közöttük
    `backoff_mp` várakozás — csak az utolsó bukás propagál (a hívón kívüli fail-soft ott lép be).
    `alvo` = a várakozó (default time.sleep; tesztben no-op)."""
    kliens = kliens or _NlpKliens()
    alvo = alvo if alvo is not None else time.sleep
    utolso = None
    for i in range(probak):
        try:
            return kliens.uzenet(korpusz, modell)
        except Exception as e:   # noqa: BLE001 — intermittens API-hiba: bounded retry, végül propagál
            utolso = e
            if i + 1 < probak:
                _log.warning("FIGYELEM: a havi NLP-hívás elhasalt (%s); újrapróba %d/%d %d mp múlva.",
                             e, i + 2, probak, backoff_mp[i])
                alvo(backoff_mp[i])
    raise utolso


def grounding_validal(eredmeny, korpusz):
    """A hallucináció-védelem (spec §3.1/3): a korpusz kifejezés-halmaza az egyetlen igazságforrás —
    minden NER-entitás és klaszter `szavak` listája erre a halmazra szűrve (a nem-korpuszbeli tag
    kiesik); az emiatt ÜRESSÉ vált NER-entitás egészében kiesik (egy 0 szavas entitás nem auditálható).
    A `lemmak` a korpusz-szavakra korlátozva (a nem-korpuszbeli `szo`-jú bejegyzés kiesik).
    Tiszta/determinista — nem módosítja a bemenetet."""
    # A `szavak`/`szo` listákat szűrjük a korpuszra; a klaszter `uralkodo_temak`-ja és az entitás `nev`-e
    # NEM szűrt — ezek a modell értelmezései a MÁR grounded `szavak` fölött, és a látható `szavak` oszlop
    # tartja auditálhatóan ellenőrizhetőnek (a kitalálás-védelem a tag-szavakon fog).
    korpusz_szavak = {s["kifejezes"] for s in korpusz.get("szavak", [])}

    lemmak = [l for l in eredmeny.get("lemmak", []) if l.get("szo") in korpusz_szavak]

    ner = {}
    for csoport, entitasok in (eredmeny.get("ner") or {}).items():
        szurt = []
        for e in entitasok or []:
            szavak = [sz for sz in (e.get("szavak") or []) if sz in korpusz_szavak]
            if szavak:   # az üressé vált entitás kiesik
                szurt.append({**e, "szavak": szavak})
        ner[csoport] = szurt

    klaszterek = []
    for k in eredmeny.get("klaszterek", []):
        szavak = [sz for sz in (k.get("szavak") or []) if sz in korpusz_szavak]
        klaszterek.append({**k, "szavak": szavak})

    return {**eredmeny, "lemmak": lemmak, "ner": ner, "klaszterek": klaszterek}


def _volumen_terkep(korpusz):
    return {s["kifejezes"]: int(s.get("max_volumen") or 0) for s in (korpusz.get("szavak") or [])}


def _entitas_volumen(szavak, vol_map):
    return sum(int(vol_map.get(sz, 0)) for sz in (szavak or []))


def volumen_dusit(eredmeny, korpusz):
    """Minden NER-entitáshoz és klaszterhez `volumen` = a kötött korpusz-szavak max_volumen-összege.
    Determinista; NEM mutálja a bemenetet (a barchartok magassága + a Fázis-B térkép-színezés forrása)."""
    vol = _volumen_terkep(korpusz)
    ner = {}
    for csoport, entitasok in (eredmeny.get("ner") or {}).items():
        ner[csoport] = [{**e, "volumen": _entitas_volumen(e.get("szavak"), vol)} for e in (entitasok or [])]
    klaszterek = [{**k, "volumen": _entitas_volumen(k.get("szavak"), vol)}
                  for k in (eredmeny.get("klaszterek") or [])]
    return {**eredmeny, "ner": ner, "klaszterek": klaszterek}


def havi_nlp_index_ir(docs_data):
    """A havi_nlp mappa hónapjainak index-e a frontend hónap-választójához (az index.json-t kihagyva)."""
    mappa = Path(docs_data) / "havi_nlp"
    honapok = sorted(p.stem for p in mappa.glob("*.json") if p.stem != "index")
    return json_export._ir_json(mappa / "index.json",
                                {"honapok": honapok, "legutolso": honapok[-1] if honapok else None})


def havi_nlp_volumen_utodusit(docs_data, honap):
    """A meglévő artefaktot a korpuszból volumen-dúsítja és visszaírja (determinista, LLM/kulcs NÉLKÜL)."""
    p = Path(docs_data) / "havi_nlp" / (honap + ".json")
    eredmeny = json.loads(p.read_text(encoding="utf-8"))
    return havi_nlp_ir(docs_data, honap, volumen_dusit(eredmeny, havi_korpusz(docs_data, honap)))


def havi_nlp_ir(docs_data, honap, eredmeny):
    """A havi NLP-eredmény külön `havi_nlp/<honap>.json` fájlba, atomi írással (a meglévő
    json_export._ir_json mintája — nincs a fő json_export.py-t érintő duplikáció)."""
    mappa = Path(docs_data) / "havi_nlp"
    mappa.mkdir(parents=True, exist_ok=True)
    return json_export._ir_json(mappa / (honap + ".json"), eredmeny)


def havi_nlp_generalas(docs_data, honap, keszult_iso, kliens=None):
    """A havi NLP-elemzés generáló belépési pontja: korpusz → Claude-hívás (fail-soft: tartós
    hibán None, NEM dob) → grounding-validáció → keszult/modell/korpusz-meta hozzáadva → írás.
    A `keszult_iso` PARAMÉTER (nincs argless datetime.now() a determinizmus miatt)."""
    korpusz = havi_korpusz(docs_data, honap)
    try:
        eredmeny = havi_nlp_elemez(korpusz, kliens=kliens)
    except Exception as e:   # noqa: BLE001 — tartós API-hiba a bounded retry után: fail-soft
        _log.error("HIBA: a havi NLP-elemzés tartósan elhasalt (%s hónap): %s", honap, e)
        return None

    eredmeny = grounding_validal(eredmeny, korpusz)
    eredmeny = volumen_dusit(eredmeny, korpusz)
    eredmeny["honap"] = honap                     # top-level honap: a fejlécet (havi.js) ez táplálja
    eredmeny["keszult"] = keszult_iso
    eredmeny["modell"] = MODELL_NLP
    eredmeny["korpusz"] = {"honap": korpusz["honap"], "napok": korpusz["napok"],
                            "egyedi_szo": korpusz["egyedi_szo"]}
    havi_nlp_ir(docs_data, honap, eredmeny)
    return eredmeny
