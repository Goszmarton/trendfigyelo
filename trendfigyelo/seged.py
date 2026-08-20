"""Közös segédfüggvények: idő, szöveggé alakítás, CSV-író, atomi lemezírás."""

import csv
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BUDAPEST = ZoneInfo("Europe/Budapest")


def atomi_ir_szoveg(fajl, szoveg: str, encoding: str = "utf-8") -> Path:
    """Atomi szöveg-lemezírás (ATOMI-IRAS): temp fájl UGYANABBAN a könyvtárban + `os.replace`.

    A `write_text` in-place ír → egy megszakadt írás (crash/OOM/leállás írás közben) csonkíthatja a
    PÓTOLHATATLAN fájlt. Itt előbb egy temp fájlba írunk (a cél könyvtárában, hogy az `os.replace` azonos
    fájlrendszeren fusson → atomi rename), majd egy lépésben a helyére cseréljük. Hiba esetén a temp
    törlődik (nincs szemét), és a MEGLÉVŐ fájl bájtjai SÉRTETLENEK maradnak.
    """
    fajl = Path(fajl)
    fajl.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(fajl.parent), prefix=fajl.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(szoveg)
        os.replace(tmp, fajl)                       # atomi rename az azonos könyvtárban
    except BaseException:
        try:
            os.unlink(tmp)                          # ne maradjon szemét temp fájl
        except OSError:
            pass
        raise
    return fajl


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
