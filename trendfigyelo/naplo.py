"""Futásnapló: adatok/naplo.csv — időpont, ág, eredmény, hívásszám, hibakódok."""

import csv
from pathlib import Path

FEJLEC = ["futas_ido_utc", "ag", "eredmeny", "hivasok_szama", "hibakodok"]


def naplo_ir(mappa, futas_ido_utc: str, bejegyzesek) -> Path:
    """Ágsoronkénti napló hozzáfűzése; fejléc csak új fájlnál."""
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
    return fajl
