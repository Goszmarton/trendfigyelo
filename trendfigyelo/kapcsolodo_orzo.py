"""A kapcsolódó-keresések NAPI egyszer-őre (a bovites_orzo mintája): a kapcsolodo.yml a 'Napi
trendgyűjtés' után fut, a backupok többször indíthatnak. Egyszer/logikai nap (seged.esti_nap),
hogy a szigorú related-kvótát ne égessük el újrafutáskor. Kimenet: a logikai nap vagy üres sor."""
import json
import sys
from datetime import datetime
from pathlib import Path

from . import seged


def _frissitve_logikai(docs_data):
    try:
        art = json.loads((Path(docs_data) / "kapcsolodo.json").read_text(encoding="utf-8"))
        k = art.get("frissitve") if isinstance(art, dict) else None
        return seged.esti_nap(datetime.fromisoformat(k)) if isinstance(k, str) else None
    except (OSError, ValueError, TypeError):
        return None


def kell(docs_data, most):
    """A logikai nap (futni kell), vagy "" ha ma (a logikai napon) már frissült."""
    logikai = seged.esti_nap(most)
    return "" if _frissitve_logikai(docs_data) == logikai else logikai


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    docs_data = argv[0] if argv else "docs/data"
    print(kell(docs_data, seged.most_utc()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
