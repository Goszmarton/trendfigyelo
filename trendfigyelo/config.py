"""A config.yaml betöltése és validálása — az egyetlen konfigforrás."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class KonfigHiba(Exception):
    """Hiányzó vagy hibás konfigurációs érték."""


@dataclass
class Config:
    geo: str
    nyelv: str
    idoablak_orak: int
    idosor_idokeret: str
    referenciaszo: str
    alap_keses_mp: float
    szoras_mp: tuple
    max_probak: int
    backoff_mp: list
    trend_idosor_max: int
    proxy: object  # str | None
    kulcsszavak: dict = field(default_factory=dict)
    kulcsszo_idokeret: str = "now 7-d"
    referencia_min_atlag: float = 1.0
    naplo_max_sor: int = 2000
    tortenet_visszapotlas_nap: int = 3

    def osszes_kulcsszo(self):
        """[(kulcsszo, csoport), ...] a beolvasás sorrendjében."""
        parok = []
        for csoport, szavak in self.kulcsszavak.items():
            for szo in szavak:
                parok.append((szo, csoport))
        return parok


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
    kulcsszavak = nyers.get("kulcsszavak") or {}
    if not kulcsszavak or any(not szavak for szavak in kulcsszavak.values()):
        raise KonfigHiba("A 'kulcsszavak' üres vagy van üres csoport — minden csoportba legalább egy szó kell.")

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
        referenciaszo=_kell(nyers, "referenciaszo", ""),
        alap_keses_mp=float(_kell(kp, "alap_keses_mp", "kerespont.")),
        szoras_mp=(float(szoras[0]), float(szoras[1])),
        max_probak=int(_kell(kp, "max_probak", "kerespont.")),
        backoff_mp=list(_kell(kp, "backoff_mp", "kerespont.")),
        trend_idosor_max=int(_kell(nyers, "trend_idosor_max", "")),
        proxy=nyers.get("proxy"),
        kulcsszavak=kulcsszavak,
        kulcsszo_idokeret=nyers.get("kulcsszo_idokeret", "now 7-d"),
        referencia_min_atlag=float(nyers.get("referencia_min_atlag", 1.0)),
        naplo_max_sor=int(nyers.get("naplo_max_sor", 2000)),
        tortenet_visszapotlas_nap=int(nyers.get("tortenet_visszapotlas_nap", 3)),
    )
