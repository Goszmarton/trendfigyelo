"""A havi NLP-elemzés utolsó-nap + idempotencia-őre (az elemzes_orzo.py mintájára).

A havi.yml a „Napi trendgyűjtés" (este) befejezésére fut; a napi backup-cronok/dispatch
ugyanazon a napon többször is elindíthatják. Ez a modul eldönti: (1) MA a hó UTOLSÓ napja-e
a `seged.esti_nap` logikai nap szerint (a hajnali <6:00 BP backup az ELŐZŐ estére sorolódik,
így a hó-forduló utáni éjfél-utáni futás nem csúszik a következő hónapra), és (2) erre a
hónapra MA már készült-e generálás (a backup-újraindítás kihagyása). Kimenet: a generálandó
hónap („YYYY-MM") vagy None/üres sor (skip).
"""
import calendar
import json
import sys
from datetime import date, datetime
from pathlib import Path

from . import seged


def havi_logikai_honap(most):
    """A logikai hónap („YYYY-MM") az esti_nap (hajnal-korrekciós) nap szerint."""
    return seged.esti_nap(most)[:7]


def utolso_nap_e(most):
    """True, ha az esti_nap logikai nap a saját hónapjának UTOLSÓ napja."""
    d = date.fromisoformat(seged.esti_nap(most))
    return d.day == calendar.monthrange(d.year, d.month)[1]


def _keszult_logikai_nap(docs_data, honap):
    """A meglévő havi_nlp/<honap>.json 'keszult' időbélyegének LOGIKAI (esti_nap) napja
    (YYYY-MM-DD), vagy None. A LOGIKAI nap kell (nem a nyers UTC-dátum): a hajnali (<6:00 BP)
    generálás keszultje a KÖVETKEZŐ UTC-napra esik, de logikailag az ELŐZŐ estéhez tartozik —
    a nyers dátum összevetése ezért a hajnali backupon tévesen újragenerált (dupla Opus-költség)."""
    fajl = Path(docs_data) / "havi_nlp" / f"{honap}.json"
    try:
        art = json.loads(fajl.read_text(encoding="utf-8"))
        k = art.get("keszult") if isinstance(art, dict) else None
        return seged.esti_nap(datetime.fromisoformat(k)) if isinstance(k, str) else None
    except (OSError, ValueError, TypeError):
        return None


def mar_kesz(docs_data, honap, logikai_nap_iso):
    """True, ha erre a hónapra MA (a logikai napon) már generálódott (a keszult LOGIKAI napja == ma).

    Hiányzó/olvashatatlan/korábbi/keszult-nélküli → False: a hó-közben kézzel generált fájl
    az utolsó napon ÚJRAGENERÁLÓDIK a teljes havi adattal; egy bukott (fail-soft, fájl-írás
    nélküli) futás után a backup újrapróbál. A logikai-nap összevetés miatt a hajnali backup
    NEM generál újra (ugyanarra a logikai estére esik)."""
    return _keszult_logikai_nap(docs_data, honap) == logikai_nap_iso


def kell_generalni(docs_data, most):
    """A generálandó hónap („YYYY-MM"), vagy None: ha nem a hó utolsó napja, vagy MA már kész."""
    if not utolso_nap_e(most):
        return None
    logikai = seged.esti_nap(most)
    honap = logikai[:7]
    if mar_kesz(docs_data, honap, logikai):
        return None
    return honap


def main(argv=None):
    """CLI: `<docs_data>` → a generálandó hónap (pl. '2026-09'), vagy ÜRES sor (skip)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    docs_data = argv[0] if argv else "docs/data"
    honap = kell_generalni(docs_data, seged.most_utc())
    print(honap or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
