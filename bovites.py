# bovites.py  (repo gyökér — a heti.py mintája)
"""A Bővítés ügy-életút generáló belépője (a bovites.yml ezt hívja): a megadott vég-napra generál
(gördülő 30 nap, fail-soft). A kulcsot az ugyek._UgyKliens az ANTHROPIC_API_KEY env-ből olvassa."""
import sys

from trendfigyelo import seged, ugyek


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or not argv[0]:
        print("Nincs megadott vég-nap — nincs teendő.")
        return 0
    veg_nap = argv[0]
    keszult_iso = seged.most_utc().isoformat()
    eredmeny = ugyek.ugy_generalas("docs/data", veg_nap, keszult_iso)
    if eredmeny is None:
        print(f"Az ügy-elemzés generálása elhasalt ({veg_nap}).")
        return 1
    print(f"Ügy-elemzés kész: {veg_nap} ({len(eredmeny.get('ugyek', []))} ügy)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
