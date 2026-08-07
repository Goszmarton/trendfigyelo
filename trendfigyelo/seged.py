"""Közös segédfüggvények: idő, szöveggé alakítás, CSV-író."""

import csv
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BUDAPEST = ZoneInfo("Europe/Budapest")


def most_utc() -> datetime:
    """Aktuális idő UTC-ben, tz-aware."""
    return datetime.now(timezone.utc)


def szovegge(ertek) -> str:
    """None/lista biztonságos szöveggé alakítása egy CSV-cellába."""
    if ertek is None:
        return ""
    if isinstance(ertek, (list, tuple)):
        return ", ".join(str(e) for e in ertek)
    return str(ertek)


def idove(ts) -> str:
    """Unix-időbélyeg (vagy (ts, ...) páros) olvasható UTC-idővé."""
    if isinstance(ts, (list, tuple)):
        ts = ts[0] if ts else None
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat(timespec="seconds")
    except (ValueError, TypeError, OSError):
        return str(ts)


def idopont_iso(ts) -> str:
    """datetime/pandas Timestamp → UTC ISO. tz-naiv bemenetet UTC-nek vesz."""
    dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
    if not isinstance(dt, datetime):
        return str(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def bp_idobelyeg(dt: datetime) -> str:
    """Budapesti idő fájlnévhez: '%Y-%m-%d_%H%M'."""
    return f"{dt.astimezone(BUDAPEST):%Y-%m-%d_%H%M}"


def csv_iro(fajl: Path):
    """utf-8-sig, pontosvesszős CSV-író. Visszaad: (fájlobjektum, writer)."""
    f = fajl.open("w", newline="", encoding="utf-8-sig")
    return f, csv.writer(f, delimiter=";")


def utolso_res(napok: list) -> list:
    """B2: az ISO-dátumlista UTOLSÓ KÉT eleme közé eső naptári nap(ok), rendezve.

    Belső folytonosság-ellenőrzés kimaradt napi futás észlelésére: NEM a „ma"-hoz
    mér (időzóna-/éjfél-zaj mentes), csak az utolsó intervallumot nézi (minden rés
    pontosan egyszer naplózódik). TISZTA: nincs IO, nincs rendszeróra.

    A függvény MAGA rendezi a bemenetet (nem előfeltétel a hívói sorrend), majd a két
    legkésőbbi dátum KÖZÉ (nyílt intervallum) eső napokat adja vissza ISO-alakban,
    valódi dátum-aritmetikával (`date.fromisoformat`). Folytonos pár (1 nap köz) →
    []; üres/egyelemű lista → [].
    """
    rendezett = sorted(napok)
    if len(rendezett) < 2:
        return []
    elozo = date.fromisoformat(rendezett[-2])
    utolso = date.fromisoformat(rendezett[-1])
    return [(elozo + timedelta(days=n)).isoformat()
            for n in range(1, (utolso - elozo).days)]
