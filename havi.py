"""A havi NLP-elemzés generáló belépője (a havi.yml workflow ezt hívja): a havi_orzo által
megadott hónapra generál (fail-soft), siker esetén frissíti a hónap-indexet is. Az elemzes.py
mintája; a kulcsot a havi_nlp `_NlpKliens` az ANTHROPIC_API_KEY env-ből olvassa."""
import sys

from trendfigyelo import havi_nlp, seged


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or not argv[0]:
        print("Nincs megadott hónap — nincs teendő.")
        return 0
    honap = argv[0]
    docs_data = "docs/data"
    keszult_iso = seged.most_utc().isoformat()
    eredmeny = havi_nlp.havi_nlp_generalas(docs_data, honap, keszult_iso)
    if eredmeny is None:
        print(f"A havi elemzés generálása elhasalt ({honap}) — nincs index-frissítés.")
        return 1
    havi_nlp.havi_nlp_index_ir(docs_data)
    print(f"Havi elemzés kész: {honap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
