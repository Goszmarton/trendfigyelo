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
    )
