"""Futásnapló: adatok/naplo.csv — időpont, ág, eredmény, hívásszám, hibakódok."""

import csv
from pathlib import Path

FEJLEC = ["futas_ido_utc", "ag", "eredmeny", "hivasok_szama", "hibakodok"]


def naplo_ir(mappa, futas_ido_utc: str, bejegyzesek, max_sor: int = 2000) -> Path:
    """Ágsoronkénti napló hozzáfűzése; fejléc csak új fájlnál. Görgő cap: max_sor adatsor."""
    fajl = Path(mappa) / "naplo.csv"
    uj = not fajl.exists()
    with fajl.open("a", newline="", encoding="utf-8-sig") as f:
        iro = csv.writer(f, delimiter=";")
        if uj:
            iro.writerow(FEJLEC)
        for b in bejegyzesek:
            iro.writerow([
                futas_ido_utc, b["ag"], b["eredmeny"],
                b["hivasok_szama"], b["hibakodok"],
            ])
    _cap(fajl, max_sor)
    return fajl


def _cap(fajl: Path, max_sor: int):
    """Ha a fájl > max_sor adatsor, fejléc + utolsó max_sor sorra írja újra."""
    with fajl.open(encoding="utf-8-sig", newline="") as f:
        sorok = list(csv.reader(f, delimiter=";"))
    if len(sorok) <= max_sor + 1:      # +1 a fejléc
        return
    fejlec, adat = sorok[0], sorok[1:]
    with fajl.open("w", newline="", encoding="utf-8-sig") as f:
        iro = csv.writer(f, delimiter=";")
        iro.writerow(fejlec)
        iro.writerows(adat[-max_sor:])
