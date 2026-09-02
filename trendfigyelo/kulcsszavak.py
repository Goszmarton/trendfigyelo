"""Kulcsszó-idősorok ág (Phase 2.5): SZÓLÓ interest_over_time kulcsszavanként.

Horgony/kötegelés/normalizálás elvetve — minden szó a saját 0–100 tartományát
kapja. A gyujt visszaad: (egynapos_pontok, {nap_iso: [pontok]}, {kifejezes: nyers_rekord}).
A nyers_rekord a Task 3 szerződése szerint (ablakhatárok + isPartial-jelölés).
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from . import seged
from .kliens import AgFeladva, PlafonTullepve

# egy hónap ~ napokban (a `today N-m` ablak várt span-jének LEVEZETÉSÉHEZ — nem beírt pontszám-konstans)
_HONAP_NAP = 30.4


def varhato_span_nap(timeframe):
    """A `today N-m` / `now N-d` timeframe VÁRT span-je napokban (a csonka-ellenőrzéshez, a stringből levezetve).
    Ismeretlen alak → None. Egység: d=nap, m=hónap(~30,4), y=év(365), H=óra."""
    m = re.match(r"(?:today|now)\s+(\d+)\s*-\s*([dmyH])", timeframe or "")
    if not m:
        return None
    n, egyseg = int(m.group(1)), m.group(2)
    return {"d": n, "m": n * _HONAP_NAP, "y": n * 365.0, "H": n / 24.0}.get(egyseg)


def masodlagos_alak_ok(pontok, timeframe, lekerdezes_utc):
    """ÉRKEZÉS-ELLENŐRZÉS: a KAPOTT sorozat megfelel-e a KÉRT timeframe-nek → (ok: bool, indok: str).
    - szabályos rács: a lezárt pontok közti köz EGYENLŐ (a step MÉRT, nem beírt);
    - span: a timeframe-ből levezetve, ≥ 0,85× (csonka-guard) és ≤ 1,2× (rossz-timeframe-guard);
    - frissesség: a sorozat vége NEM jövőbeli és a lekérdezéshez képest ≤ 2×step + 2 nap.
    A várt értékek a `timeframe`-ből SZÁRMAZNAK (rács-vak konstans elkerülve)."""
    lezart = [p for p in pontok if not p.get("reszleges")]
    if len(lezart) < 2:
        return False, "túl kevés lezárt pont (<2)"
    idok = sorted(datetime.fromisoformat(p["idopont_utc"]) for p in lezart)
    kozok = {(idok[i + 1] - idok[i]).days for i in range(len(idok) - 1)}
    if len(kozok) != 1:
        return False, f"szabálytalan rács (több lépésköz: {sorted(kozok)})"
    step = next(iter(kozok))
    if step < 1:
        return False, "0-napos lépésköz"
    var_span = varhato_span_nap(timeframe)
    if var_span is None:
        return False, f"ismeretlen timeframe: {timeframe!r}"
    span = (idok[-1] - idok[0]).days
    if span < var_span * 0.85:
        return False, f"csonka span ({span} nap < 0,85×{var_span:.0f} a(z) {timeframe!r}-hez)"
    if span > var_span * 1.2:
        return False, f"túl hosszú span ({span} nap > 1,2×{var_span:.0f} a(z) {timeframe!r}-hez)"
    kesés = (datetime.fromisoformat(lekerdezes_utc) - idok[-1]).days
    if kesés < 0:
        return False, "a sorozat vége JÖVŐBELI a lekérdezéshez képest"
    if kesés > step * 2 + 2:
        return False, f"a sorozat vége túl régi ({kesés} nap a lekérdezés előtt, step={step})"
    return True, ""


def _szam(x) -> bool:
    try:
        f = float(x)
    except (ValueError, TypeError):
        return False
    return f == f  # NaN esetén False (NaN != NaN)


def _reszleges(cella) -> bool:
    """Az isPartial cella bool-ként; NaN → False (nem részleges) — bool(NaN) True lenne."""
    if cella != cella:  # NaN
        return False
    return bool(cella)


def _bp_datum(idx):
    """Egy (pandas) index-időbélyeg budapesti naptári dátuma."""
    dt = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(seged.BUDAPEST).date()


def utolso_teljes_nap(df, mai_datum):
    """A df budapesti dátumai közül a legnagyobb, amely < mai_datum; egyébként None."""
    if df is None or len(df) == 0:
        return None
    korabbi = {_bp_datum(idx) for idx in df.index if _bp_datum(idx) < mai_datum}
    return max(korabbi) if korabbi else None


def utolso_N_teljes_nap(df, mai_datum, n: int) -> list:
    """A df budapesti dátumai közül az utolsó n, amely < mai_datum; növekvő sorrendben."""
    if df is None or len(df) == 0:
        return []
    korabbi = sorted({_bp_datum(idx) for idx in df.index if _bp_datum(idx) < mai_datum})
    return korabbi[-n:]


def _ertek_oszlop(df, kifejezes):
    """A mért érték oszlopa: a kifejezés, vagy az első nem-isPartial oszlop."""
    if kifejezes in df.columns:
        return kifejezes
    for c in df.columns:
        if str(c).lower() != "ispartial":
            return c
    return None


def _ispartial_oszlop(df):
    for c in df.columns:
        if str(c).lower() == "ispartial":
            return c
    return None


def _pontok_napokra(df, tetel, oszlop, napok) -> list:
    """A df azon pontjai, amelyek budapesti napja a `napok` halmazban van (nyers érték)."""
    napok = set(napok)
    pontok = []
    for idx, sor in df.iterrows():
        if _bp_datum(idx) not in napok:
            continue
        nyers = sor[oszlop]
        pontok.append({
            "kulcsszo": tetel.kifejezes,
            "domen": tetel.domen,
            "tipus": tetel.tipus,
            "idopont_utc": seged.idopont_iso(idx),
            "nyers_ertek": int(nyers) if _szam(nyers) else "",
        })
    return pontok


def _nyers_sorozat(df, tetel, oszlop, ip_oszlop) -> dict:
    """A teljes lekérdezés nyers órás sorozata a Task 3 szerződése szerint."""
    pontok = []
    for idx, sor in df.iterrows():
        nyers = sor[oszlop]
        pontok.append({
            "idopont_utc": seged.idopont_iso(idx),
            "ertek": int(nyers) if _szam(nyers) else "",
            "reszleges": _reszleges(sor[ip_oszlop]) if ip_oszlop is not None else False,
        })
    return {
        "kulcsszo": tetel.kifejezes,
        "ablak_kezdet_utc": seged.idopont_iso(df.index.min()),
        "ablak_veg_utc": seged.idopont_iso(df.index.max()),
        "pontok": pontok,
    }


def gyujt(kliens, config, most=None, tetelek=None):
    """Minden MEGADOTT (alap: összes) kulcsszót SZÓLÓBAN lekér (now 7-d). Visszaad:
    (egynapos_pontok, {nap_iso: [pontok]}, {kifejezes: nyers_rekord}).

    Az egynapos_pontok a CSV-hez/legfrissebb.json-hoz (utolsó teljes nap); a napi
    dict a tortenet többnapos upsertjéhez (utolsó N teljes nap); a nyers_sorozatok
    a verziókövetett nyers kimenethez (Task 6 írja ki).
    AgFeladva (429) → az EGÉSZ ág feladva; egyéb hiba csak az adott szót hagyja ki.
    """
    most = most or seged.most_utc()
    mai_datum = most.astimezone(seged.BUDAPEST).date()
    n = config.tortenet_visszapotlas_nap
    if tetelek is None:
        tetelek = config.osszes_kulcsszo()
    pontok = []
    napi_pontok = {}
    nyers_sorozatok = {}
    for tetel in tetelek:
        try:
            df = kliens.hivas(
                "kulcsszo", kliens.tr.interest_over_time,
                [tetel.kifejezes], geo=config.geo, timeframe=config.kulcsszo_idokeret,
            )
        except AgFeladva as e:
            print(f"FIGYELEM: a kulcsszó-ág feladva (429) a(z) {tetel.kifejezes!r} szónál.")
            # a blokk ELŐTT lemért szavakat a kivételre akasztjuk → a futtato menti (spec 7.4).
            # HATÓKÖR (szándékos): CSAK az AgFeladva viszi a részleget; más kivétel nem.
            e.reszleges = (pontok, napi_pontok, nyers_sorozatok)
            raise
        except PlafonTullepve as e:  # hívás-plafon → HARD ABORT, de az addigi szavak mentése
            e.reszleges = (pontok, napi_pontok, nyers_sorozatok)  # (mint AgFeladva-nál)
            raise
        except Exception as e:
            print(f"FIGYELEM: a(z) {tetel.kifejezes!r} kulcsszó kimaradt ({e}).")
            continue
        # SUCCESS-VAK: a néma üres-skip a VÁRATLAN esetben HANGOS. A tipus a megkülönböztető:
        # esemenyjelzo üres = VÁRT (sparse-by-design, spec 6.2 védett) → TELJESEN NÉMA; szintmero/hibrid
        # üres = VÁRATLAN (szint-szónak mindig lenne adata) → FIGYELEM. Exit-kód SOHA (részleges veszteség;
        # a TELJES-üres a LEGFRISSEBB-GUARD dolga). A két skip-út KÜLÖN hibaosztály (GORBE-B/MASODLAGOS-PLAFON
        # tanulság): üres df = hálózati/adathiány; hiányzó oszlop = query/parse-gyanú.
        varatlan = tetel.tipus != "esemenyjelzo"
        if df is None or len(df) == 0:
            if varatlan:
                print(f"FIGYELEM: a(z) {tetel.kifejezes!r} ({tetel.tipus}) szó ÜRES sorozatot adott "
                      f"(Google semmit — hálózati/adathiány); kimarad a napból.")
            continue
        oszlop = _ertek_oszlop(df, tetel.kifejezes)
        if oszlop is None:
            if varatlan:
                print(f"FIGYELEM: a(z) {tetel.kifejezes!r} ({tetel.tipus}) szó válaszában NINCS érték-OSZLOP "
                      f"(adat jött, de nem a szó oszlopa — query/parse-gyanú); kimarad a napból.")
            continue
        ip = _ispartial_oszlop(df)
        utolso = utolso_teljes_nap(df, mai_datum)
        if utolso is not None:
            pontok.extend(_pontok_napokra(df, tetel, oszlop, [utolso]))
        for nap in utolso_N_teljes_nap(df, mai_datum, n):
            nap_pontjai = _pontok_napokra(df, tetel, oszlop, [nap])
            if nap_pontjai:
                napi_pontok.setdefault(nap.isoformat(), []).extend(nap_pontjai)
        nyers_sorozatok[tetel.kifejezes] = _nyers_sorozat(df, tetel, oszlop, ip)
    return pontok, napi_pontok, nyers_sorozatok


def gyujt_egy_masodlagos(kliens, config, tetel, most, timeframe, gprop="", ag="kulcsszo_masodlagos"):
    """EGY nap/het szó másodlagos (RACS_IDOKERET szerinti) lekérdezése → egy rekord vagy None.

    Az `ag` ág-néven megy (külön Kliens-számláló + napló-címke; alapból `kulcsszo_masodlagos`).
    A `gprop`: Google-tulajdon ('' = web [Google-viselkedés bájt-azonos], 'youtube' = YouTube).
    Üres/oszlop nélküli df → None (a szó kimarad). AgFeladva (429) NEM itt fogódik el — a hívó (a
    másodlagos ág) csendesen feladja, de a MÁR kiírt szavak megmaradnak (spec 7.4 mintája, pótolható adaton).
    """
    from .config import TIMEFRAME_RACS
    df = kliens.hivas(
        ag, kliens.tr.interest_over_time,
        [tetel.kifejezes], geo=config.geo, timeframe=timeframe, gprop=gprop)
    if df is None or len(df) == 0:
        return None
    oszlop = _ertek_oszlop(df, tetel.kifejezes)
    if oszlop is None:
        return None
    rek = _nyers_sorozat(df, tetel, oszlop, _ispartial_oszlop(df))
    rek["racs"] = TIMEFRAME_RACS.get(timeframe, tetel.racs)   # a timeframe RÁCSA (3-m→nap, 12-m→het), NEM a config-rács
    rek["timeframe"] = timeframe          # a szó × timeframe séma (2. rész) kulcsa; a rekord ELtárolja
    rek["lekerdezes_utc"] = most.isoformat()
    # ÉRKEZÉS-ELLENŐRZÉS (1. rész): a kapott sorozat feleljen meg a KÉRT timeframe-nek — csonka/rossz → ELDOB + FIGYELEM
    ok, indok = masodlagos_alak_ok(rek["pontok"], timeframe, rek["lekerdezes_utc"])
    if not ok:
        print(f"FIGYELEM: a(z) {tetel.kifejezes!r} másodlagos ({timeframe}) válasza NEM felel meg a kért "
              f"timeframe-nek ({indok}); ELDOBVA (nem mentjük).")
        return None
    return rek


def csv_ir(mappa, idobelyeg, letoltve, geo, pontok):
    if not pontok:
        return None
    fajl = Path(mappa) / f"kulcsszo_idosor_{geo}_{idobelyeg}.csv"
    f, iro = seged.csv_iro(fajl)
    with f:
        iro.writerow([
            "kulcsszo", "domen", "tipus", "idopont_utc", "nyers_ertek", "letoltve_utc", "geo",
        ])
        for p in pontok:
            iro.writerow([
                p["kulcsszo"], p["domen"], p["tipus"], p["idopont_utc"],
                p["nyers_ertek"], letoltve, geo,
            ])
    return fajl
