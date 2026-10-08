# kapcsolodo.py  (repo gyökér — a masodlagos_only + heti.py mintája)
"""A kapcsolódó-keresések gyűjtő belépője (a kapcsolodo.yml ezt hívja): saját, SZŰK plafonú Kliens
(kvóta-védelem) → kapcsolodo.gyujt a felkapott jelöltekre → atomi írás. Soft-fail: a related-kvóta
kimerülése nem dob (gyujt soft-fail-el szónként); NEM indít más ágat."""
import argparse

from trendfigyelo import kapcsolodo, seged
from trendfigyelo.config import betolt
from trendfigyelo.kliens import Kliens


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--cap", type=int, default=kapcsolodo.CAP)
    p.add_argument("docs_data", nargs="?", default="docs/data")
    args = p.parse_args(argv)
    config = betolt()
    kliens = Kliens(config, plafon=args.cap * config.max_probak + 1)   # saját, szűk plafon
    adat = kapcsolodo.gyujt(args.docs_data, kliens, config, seged.most_utc(), cap=args.cap)
    kapcsolodo.kapcsolodo_ir(args.docs_data, adat)
    print(f"Kapcsolódó keresések: {len(adat['kifejezesek'])} kifejezés (frissítve {adat['frissitve']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
