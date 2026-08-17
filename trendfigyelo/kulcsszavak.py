"""Kulcsszó-idősorok ág (Phase 2.5): SZÓLÓ interest_over_time kulcsszavanként.

Horgony/kötegelés/normalizálás elvetve — minden szó a saját 0–100 tartományát
kapja. A gyujt visszaad: (egynapos_pontok, {nap_iso: [pontok]}, {kifejezes: nyers_rekord}).
A nyers_rekord a Task 3 szerződése szerint (ablakhatárok + isPartial-jelölés).
"""

from datetime import timezone
from pathlib import Path

from . import seged
from .kliens import AgFeladva, PlafonTullepve


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


def gyujt(kliens, config, most=None):
    """Minden kulcsszót SZÓLÓBAN lekér (now 7-d). Visszaad:
    (egynapos_pontok, {nap_iso: [pontok]}, {kifejezes: nyers_rekord}).

    Az egynapos_pontok a CSV-hez/legfrissebb.json-hoz (utolsó teljes nap); a napi
    dict a tortenet többnapos upsertjéhez (utolsó N teljes nap); a nyers_sorozatok
    a verziókövetett nyers kimenethez (Task 6 írja ki).
    AgFeladva (429) → az EGÉSZ ág feladva; egyéb hiba csak az adott szót hagyja ki.
    """
    most = most or seged.most_utc()
    mai_datum = most.astimezone(seged.BUDAPEST).date()
    n = config.tortenet_visszapotlas_nap
    pontok = []
    napi_pontok = {}
    nyers_sorozatok = {}
    for tetel in config.osszes_kulcsszo():
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


def gyujt_egy_masodlagos(kliens, config, tetel, most):
    """EGY nap/het szó másodlagos (RACS_IDOKERET szerinti) lekérdezése → egy rekord vagy None.

    A `kulcsszo_masodlagos` ág-néven megy (külön Kliens-számláló + napló-címke). Üres/oszlop
    nélküli df → None (a szó kimarad). AgFeladva (429) NEM itt fogódik el — a hívó (a másodlagos
    ág) csendesen feladja, de a MÁR kiírt szavak megmaradnak (spec 7.4 mintája, pótolható adaton).
    """
    from .config import RACS_IDOKERET
    df = kliens.hivas(
        "kulcsszo_masodlagos", kliens.tr.interest_over_time,
        [tetel.kifejezes], geo=config.geo, timeframe=RACS_IDOKERET[tetel.racs])
    if df is None or len(df) == 0:
        return None
    oszlop = _ertek_oszlop(df, tetel.kifejezes)
    if oszlop is None:
        return None
    rek = _nyers_sorozat(df, tetel, oszlop, _ispartial_oszlop(df))
    rek["racs"] = tetel.racs
    rek["lekerdezes_utc"] = most.isoformat()
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
