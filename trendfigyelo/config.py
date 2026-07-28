"""A config.yaml betöltése és validálása — az egyetlen konfigforrás.

Phase 2.5: a kulcsszavak per-kulcsszó rekordok listája (kifejezes/domen/tipus);
a horgony (referenciaszo, referencia_min_atlag) elhagyva.
"""

from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path

import yaml

KulcsszoTetel = namedtuple("KulcsszoTetel", ["kifejezes", "domen", "tipus"])

TIPUSOK = {"szintmero", "esemenyjelzo", "hibrid"}


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
        ki.append(KulcsszoTetel(kifejezes, domen, tipus))
    latott = set()
    for t in ki:
        if t.kifejezes in latott:
            raise KonfigHiba(f"kulcsszavak: duplikált kifejezes: {t.kifejezes!r} "
                             "(fölösleges dupla hívás + kétszeres számolás)")
        latott.add(t.kifejezes)
    return ki


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
        tortenet_visszapotlas_nap=int(nyers.get("tortenet_visszapotlas_nap", 3)),
    )
