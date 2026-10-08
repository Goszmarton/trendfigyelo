"""A heti értékelés hétfő + idempotencia-őre (a havi_orzo.py mintájára).

A heti.yml a „Reggeli felkapott-gyűjtés" befejezésére fut; a reggeli/napi backupok ugyanazon a napon
többször is elindíthatják. Ez a modul eldönti: (1) MA hétfő-e a `seged.esti_nap` logikai nap szerint
(a hajnali <6:00 BP futás az ELŐZŐ naphoz sorolódik, így egy vasárnap hajnali backup nem indít heti
futást), és (2) az ELŐZŐ (lezárult) hétre MA már generálódott-e (a keszult LOGIKAI napja alapján,
a backup-újraindítás kihagyása). Kimenet: a generálandó hét hétfője („YYYY-MM-DD") vagy None/üres sor.
"""
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from . import seged


def _logikai_datum(most):
    return date.fromisoformat(seged.esti_nap(most))


def hetfo_e(most):
    """True, ha az esti_nap logikai nap HÉTFŐ (isoweekday()==1)."""
    return _logikai_datum(most).isoweekday() == 1


def elozo_het_hetfo(most):
    """Az előző, LEZÁRULT hét hétfője (YYYY-MM-DD). Hétfőn futtatva a mai hétfő − 7 nap."""
    d = _logikai_datum(most)
    ezen_het_hetfo = d - timedelta(days=d.isoweekday() - 1)
    return (ezen_het_hetfo - timedelta(days=7)).isoformat()


def _keszult_logikai_nap(docs_data, het_kezdet):
    """A meglévő heti/<het_kezdet>.json keszult-jének LOGIKAI (esti_nap) napja, vagy None (a hajnali
    dedup: a hajnali generálás keszultje logikailag az előző estéhez tartozik)."""
    fajl = Path(docs_data) / "heti" / f"{het_kezdet}.json"
    try:
        art = json.loads(fajl.read_text(encoding="utf-8"))
        k = art.get("keszult") if isinstance(art, dict) else None
        return seged.esti_nap(datetime.fromisoformat(k)) if isinstance(k, str) else None
    except (OSError, ValueError, TypeError):
        return None


def mar_kesz(docs_data, het_kezdet, logikai_nap_iso):
    """True, ha erre a hétre MA (a logikai napon) már generálódott."""
    return _keszult_logikai_nap(docs_data, het_kezdet) == logikai_nap_iso


def kell_generalni(docs_data, most):
    """A generálandó hét hétfője („YYYY-MM-DD"), vagy None: ha nem hétfő, vagy MA már kész."""
    if not hetfo_e(most):
        return None
    het_kezdet = elozo_het_hetfo(most)
    if mar_kesz(docs_data, het_kezdet, seged.esti_nap(most)):
        return None
    return het_kezdet


def main(argv=None):
    """CLI: `<docs_data>` → a generálandó hét hétfője (pl. '2026-09-28'), vagy ÜRES sor (skip)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    docs_data = argv[0] if argv else "docs/data"
    het = kell_generalni(docs_data, seged.most_utc())
    print(het or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
