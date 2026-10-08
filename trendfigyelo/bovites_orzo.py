"""A Bővítés (ügy-életút) NAPI idempotencia-őre (az elemzes_orzo/heti_orzo mintája). A bovites.yml
a 'Napi trendgyűjtés' (esti) befejezésére fut; a backupok ugyanazon a napon többször indíthatnak.
Egyszer/logikai nap (seged.esti_nap). Kimenet: a generálandó vég-nap (YYYY-MM-DD) vagy üres sor (skip)."""
import json
import sys
from datetime import datetime
from pathlib import Path

from . import seged


def _keszult_logikai_nap(docs_data):
    try:
        art = json.loads((Path(docs_data) / "ugyek.json").read_text(encoding="utf-8"))
        k = art.get("szamitva_utc") if isinstance(art, dict) else None
        return seged.esti_nap(datetime.fromisoformat(k)) if isinstance(k, str) else None
    except (OSError, ValueError, TypeError):
        return None


def kell_generalni(docs_data, most):
    """A generálandó vég-nap (a logikai nap), vagy None, ha ma (a logikai napon) már kész."""
    logikai = seged.esti_nap(most)
    if _keszult_logikai_nap(docs_data) == logikai:
        return None
    return logikai


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    docs_data = argv[0] if argv else "docs/data"
    nap = kell_generalni(docs_data, seged.most_utc())
    print(nap or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
