"""A heti értékelés generáló belépője (a heti.yml workflow ezt hívja): a heti_orzo által megadott
hétre generál (fail-soft), siker esetén frissíti a hét-indexet is. A kulcsot a heti_ertekeles
_HetiKliens az ANTHROPIC_API_KEY env-ből olvassa."""
import sys

from trendfigyelo import heti_ertekeles, seged


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or not argv[0]:
        print("Nincs megadott hét — nincs teendő.")
        return 0
    het_kezdet = argv[0]
    docs_data = "docs/data"
    keszult_iso = seged.most_utc().isoformat()
    eredmeny = heti_ertekeles.heti_generalas(docs_data, het_kezdet, keszult_iso)
    if eredmeny is None:
        print(f"A heti értékelés generálása elhasalt ({het_kezdet}) — nincs index-frissítés.")
        return 1
    heti_ertekeles.heti_index_ir(docs_data)
    print(f"Heti értékelés kész: {het_kezdet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
