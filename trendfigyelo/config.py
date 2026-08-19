"""A config.yaml betöltése és validálása — az egyetlen konfigforrás.

Phase 2.5: a kulcsszavak per-kulcsszó rekordok listája (kifejezes/domen/tipus);
a horgony (referenciaszo, referencia_min_atlag) elhagyva.
"""

from collections import namedtuple
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml

KulcsszoTetel = namedtuple(
    "KulcsszoTetel", ["kifejezes", "domen", "tipus", "racs"], defaults=("ora",))

TIPUSOK = {"szintmero", "esemenyjelzo", "hibrid"}

RACSOK = {"ora", "nap", "het"}

# a per-szó rács → Trends timeframe (Phase 4: szavanként a legfinomabb működő rács)
RACS_IDOKERET = {"ora": "now 7-d", "nap": "today 3-m", "het": "today 12-m"}

# PER-SZÓ TÖBB-TIMEFRAME (2026-08-19): minden nem-ora szó MINDKÉT hosszú sorozatot kapja (a felhasználó gombbal vált).
MASODLAGOS_TIMEFRAMEK = ("today 3-m", "today 12-m")
# a timeframe RÁCSA = a Google felbontása (3-m napi, 12-m heti) — a rekord `racs`-mezője EBBŐL, NEM a config-rácsból
# (egy het-config szó 3-m rekordjának rácsa `nap`); a config-rács a megjelenítési alapértelmezés marad.
TIMEFRAME_RACS = {"today 3-m": "nap", "today 12-m": "het"}


class KonfigHiba(Exception):
    """Hiányzó vagy hibás konfigurációs érték."""


@dataclass
class Config:
    geo: str
    nyelv: str
    idoablak_orak: int
    idosor_idokeret: str
    alap_keses_mp: float
    szoras_mp: tuple
    max_probak: int
    backoff_mp: list
    trend_idosor_max: int
    proxy: object  # str | None
    kulcsszavak: list = field(default_factory=list)  # [KulcsszoTetel, ...]
    kulcsszo_idokeret: str = "now 7-d"
    naplo_max_sor: int = 2000
    tortenet_visszapotlas_nap: int = 3
    modszertan_valtas: object = None  # kanonikus ISO 'YYYY-MM-DD' | None — töréspont-jelölő (CSAK jelöl)
    trend_megjelenites_max: int = 25  # a megjelenített trendlista felső korlátja (holtverseny-kiterjesztés, spec §7.3 D3)
    trend_idosor_rekesz_max: int = 5  # GORBE-B: hány holtverseny-rekesz trend kapjon idősort (forward-only, LEGUTOLSÓ ág); NEM-MÉRT, 14-nap újramérés

    def osszes_kulcsszo(self):
        """[KulcsszoTetel(kifejezes, domen, tipus), ...] a beolvasás sorrendjében."""
        return list(self.kulcsszavak)


def _kell(d: dict, kulcs: str, hol: str):
    if kulcs not in d or d[kulcs] in (None, ""):
        raise KonfigHiba(f"Hiányzó konfigmező: {hol}{kulcs}")
    return d[kulcs]


def _ellenoriz_szamlista(ertek, hol: str, hossz=None):
    """KonfigHiba, ha ertek nem szám-lista (adott hosszal / nem-üresen)."""
    if not isinstance(ertek, (list, tuple)):
        raise KonfigHiba(f"{hol}: listát vártam, nem {type(ertek).__name__}-t")
    if hossz is not None and len(ertek) != hossz:
        raise KonfigHiba(f"{hol}: pontosan {hossz} elem kell, kaptam {len(ertek)}-t")
    if hossz is None and not ertek:
        raise KonfigHiba(f"{hol}: nem lehet üres lista")
    for x in ertek:
        try:
            float(x)
        except (ValueError, TypeError):
            raise KonfigHiba(f"{hol}: nem-szám elem: {x!r}")


def _kulcsszavak_beolvas(nyers) -> list:
    """A 'kulcsszavak' listát KulcsszoTetel-ekké alakítja és validálja."""
    tetelek = nyers.get("kulcsszavak")
    if not isinstance(tetelek, list) or not tetelek:
        raise KonfigHiba("A 'kulcsszavak' nem lehet üres — per-kulcsszó rekordok listája kell.")
    ki = []
    for i, t in enumerate(tetelek):
        if not isinstance(t, dict):
            raise KonfigHiba(f"kulcsszavak[{i}]: dict kell (kifejezes/domen/tipus)")
        kifejezes = t.get("kifejezes")
        domen = t.get("domen")
        tipus = t.get("tipus")
        if not isinstance(kifejezes, str) or not kifejezes.strip():
            raise KonfigHiba(f"kulcsszavak[{i}].kifejezes: nem üres string kell")
        if not isinstance(domen, str) or not domen.strip():
            raise KonfigHiba(f"kulcsszavak[{i}].domen: nem üres string kell ({kifejezes!r})")
        if tipus not in TIPUSOK:
            raise KonfigHiba(
                f"kulcsszavak[{i}].tipus: {tipus!r} — a megengedett: {sorted(TIPUSOK)} ({kifejezes!r})")
        racs = t.get("racs", "ora")   # hiány → "ora" (visszafelé kompatibilis: mai órás viselkedés)
        if racs not in RACSOK:
            raise KonfigHiba(
                f"kulcsszavak[{i}].racs: {racs!r} — a megengedett: {sorted(RACSOK)} ({kifejezes!r})")
        ki.append(KulcsszoTetel(kifejezes, domen, tipus, racs))
    latott = set()
    for t in ki:
        if t.kifejezes in latott:
            raise KonfigHiba(f"kulcsszavak: duplikált kifejezes: {t.kifejezes!r} "
                             "(fölösleges dupla hívás + kétszeres számolás)")
        latott.add(t.kifejezes)
    return ki


def _modszertan_valtas_beolvas(nyers):
    """A töréspont-jelölő normalizálása kanonikus ISO 'YYYY-MM-DD' stringgé (vagy None).

    Elfogadott: str (ISO dátum) és datetime.date. A datetime.datetime a date
    ALOSZTÁLYA, de idő-komponenssel — az elgépelt időbélyeg-alakot elutasítjuk
    (nem csonkoljuk csendben). Minden más bemenet → KonfigHiba.
    """
    ertek = nyers.get("modszertan_valtas")
    if ertek is None:
        return None
    if isinstance(ertek, datetime):
        raise KonfigHiba(
            f"modszertan_valtas: dátum kell (YYYY-MM-DD), nem időbélyeg: {ertek!r}")
    if isinstance(ertek, date):
        return ertek.isoformat()
    if isinstance(ertek, str):
        try:
            return date.fromisoformat(ertek.strip()).isoformat()
        except ValueError:
            raise KonfigHiba(f"modszertan_valtas: nem ISO dátum: {ertek!r}")
    raise KonfigHiba(
        f"modszertan_valtas: str vagy dátum kell, nem {type(ertek).__name__}")


def betolt(utvonal="config.yaml") -> Config:
    """A config.yaml beolvasása Config objektummá; hibás konfig → KonfigHiba."""
    p = Path(utvonal)
    if not p.exists():
        raise KonfigHiba(f"Nincs konfigfájl: {p}")
    try:
        nyers = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise KonfigHiba(f"Hibás YAML: {e}") from e

    kp = nyers.get("kerespont") or {}
    kulcsszavak = _kulcsszavak_beolvas(nyers)

    szoras = _kell(kp, "szoras_mp", "kerespont.")
    _ellenoriz_szamlista(szoras, "kerespont.szoras_mp", 2)
    if float(szoras[0]) < 0:
        raise KonfigHiba("kerespont.szoras_mp: nem lehet negatív")
    if float(szoras[0]) > float(szoras[1]):
        raise KonfigHiba("kerespont.szoras_mp: az alsó határ nem lehet nagyobb a felsőnél")

    backoff = _kell(kp, "backoff_mp", "kerespont.")
    _ellenoriz_szamlista(backoff, "kerespont.backoff_mp")

    if float(_kell(kp, "alap_keses_mp", "kerespont.")) < 0:
        raise KonfigHiba("kerespont.alap_keses_mp: nem lehet negatív")
    if int(_kell(kp, "max_probak", "kerespont.")) < 1:
        raise KonfigHiba("kerespont.max_probak: legalább 1 kell legyen")

    return Config(
        geo=_kell(nyers, "geo", ""),
        nyelv=_kell(nyers, "nyelv", ""),
        idoablak_orak=int(_kell(nyers, "idoablak_orak", "")),
        idosor_idokeret=_kell(nyers, "idosor_idokeret", ""),
        alap_keses_mp=float(_kell(kp, "alap_keses_mp", "kerespont.")),
        szoras_mp=(float(szoras[0]), float(szoras[1])),
        max_probak=int(_kell(kp, "max_probak", "kerespont.")),
        backoff_mp=list(_kell(kp, "backoff_mp", "kerespont.")),
        trend_idosor_max=int(_kell(nyers, "trend_idosor_max", "")),
        proxy=nyers.get("proxy"),
        kulcsszavak=kulcsszavak,
        kulcsszo_idokeret=nyers.get("kulcsszo_idokeret", "now 7-d"),
        naplo_max_sor=int(nyers.get("naplo_max_sor", 2000)),
        trend_megjelenites_max=int(nyers.get("trend_megjelenites_max", 25)),
        trend_idosor_rekesz_max=int(nyers.get("trend_idosor_rekesz_max", 5)),
        tortenet_visszapotlas_nap=int(nyers.get("tortenet_visszapotlas_nap", 3)),
        modszertan_valtas=_modszertan_valtas_beolvas(nyers),
    )
