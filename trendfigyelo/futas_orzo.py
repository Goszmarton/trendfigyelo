"""Idempotencia-őr a napi trendgyűjtéshez.

A `napi.yml` több ütemezett cron-idősávból is elindulhat (fő + fallback slotok),
hogy a GitHub ingatag scheduler-e miatt ne maradjon ki egy nap sem. Ez az őr dönti
el egy ÜTEMEZETT futásnál: gyűjtsön-e, vagy némán lépjen ki, mert ma már gyűjtöttünk.

A napi (Google) jel a `docs/data/legfrissebb.json` 'frissitve' időbélyege (a gyűjtés
UTC-ideje): ha a DÁTUM-előtagja a mai UTC-dátum, akkor ma már megvan az adat. A youtube
jelnek nincs ilyen felső 'frissitve' mezője, ezért ott a `youtube_nyers.json` kulcsszó-
rekordjainak LEGFRISSEBB 'lekerdezes_utc'-je adja az utolsó gyűjtés dátumát.

Mindkét út döntése pure és tesztelt; a hiányzó/olvashatatlan jel biztonságos
alapértelmezése: NEM gyűjtöttünk (inkább gyűjtsünk, mint tévesen kihagyjunk egy napot).
"""
import json
import os
import sys
from datetime import datetime, timezone

from . import seged

ALAP_LEGFRISSEBB = "docs/data/legfrissebb.json"
ALAP_YOUTUBE_NYERS = "docs/data/youtube_nyers.json"


def _frissitve_datuma(legfrissebb_path):
    """A legfrissebb.json 'frissitve' mezőjének ISO-dátum előtagja (YYYY-MM-DD), vagy None.

    Hiányzó fájl, hibás JSON vagy hiányzó/rövid 'frissitve' esetén None.
    """
    try:
        with open(legfrissebb_path, encoding="utf-8") as f:
            adat = json.load(f)
    except (OSError, ValueError):
        return None
    frissitve = adat.get("frissitve")
    if not isinstance(frissitve, str) or len(frissitve) < 10:
        return None
    return frissitve[:10]


def mar_gyujtottunk_ma(legfrissebb_path, ma_utc):
    """True, ha a legfrissebb adat 'frissitve' dátuma == ma_utc (YYYY-MM-DD).

    Hiányzó/olvashatatlan jel → False (inkább gyűjtsünk, mint tévesen kihagyjunk).
    """
    return _frissitve_datuma(legfrissebb_path) == ma_utc


def _youtube_utolso_datuma(youtube_nyers_path):
    """A youtube_nyers.json LEGFRISSEBB 'lekerdezes_utc'-jének dátum-előtagja, vagy None.

    Minden kulcsszó minden rekordján végigmegy, és a legkésőbbi lekérdezés dátumát
    (YYYY-MM-DD) adja vissza. Hiányzó fájl, hibás JSON, üres/érvénytelen jel → None.
    """
    try:
        with open(youtube_nyers_path, encoding="utf-8") as f:
            adat = json.load(f)
    except (OSError, ValueError):
        return None
    kulcsszavak = adat.get("kulcsszavak")
    if not isinstance(kulcsszavak, dict):
        return None
    lekerdezesek = [
        rek["lekerdezes_utc"]
        for rekordok in kulcsszavak.values() if isinstance(rekordok, list)
        for rek in rekordok
        if isinstance(rek, dict)
        and isinstance(rek.get("lekerdezes_utc"), str) and len(rek["lekerdezes_utc"]) >= 10
    ]
    if not lekerdezesek:
        return None
    return max(lekerdezesek)[:10]


def youtube_mar_gyujtottunk_ma(youtube_nyers_path, ma_utc):
    """True, ha a legfrissebb youtube-lekérdezés dátuma == ma_utc (YYYY-MM-DD).

    Hiányzó/olvashatatlan jel → False (inkább gyűjtsünk, mint tévesen kihagyjunk).
    """
    return _youtube_utolso_datuma(youtube_nyers_path) == ma_utc


def _szegmens_datuma(docs_data, szegmens, nap_bp):
    """A napok/<nap_bp>.json <szegmens>.frissitve dátum-előtagja (YYYY-MM-DD), vagy None."""
    fajl = os.path.join(str(docs_data), "napok", f"{nap_bp}.json")
    try:
        with open(fajl, encoding="utf-8") as f:
            adat = json.load(f)
    except (OSError, ValueError):
        return None
    szeg = adat.get(szegmens) if isinstance(adat, dict) else None
    fr = szeg.get("frissitve") if isinstance(szeg, dict) else None
    if not isinstance(fr, str) or len(fr) < 10:
        return None
    return fr[:10]


def szegmens_mar_gyujtottunk_ma(docs_data, szegmens, ma_bp):
    """True, ha a <szegmens>.frissitve dátuma == ma_bp (YYYY-MM-DD).

    Hiányzó/olvashatatlan jel → False (inkább gyűjtsünk, mint tévesen kihagyjunk).
    """
    # A 'frissitve' UTC-ben van (napi_ir a most.isoformat()-ot írja), itt viszont a
    # budapesti naptári nappal (ma_bp) hasonlítjuk; a 09:00/21:00 budapesti triggereknél
    # ez egybeesik, az egyetlen eltérés (budapesti éjfél utáni backup-futás) FAIL-OPEN
    # (újra gyűjt, sosem hamis kihagyás) — ne "javítsd" UTC-összehasonlításra.
    return _szegmens_datuma(docs_data, szegmens, ma_bp) == ma_bp


def main(argv=None):
    """CLI: kiírja a KIHAGYÁSI döntést a napi.yml / youtube.yml őr-lépésének.

    'true'  → ma már gyűjtöttünk, az ütemezett futás hagyja ki a gyűjtést.
    'false' → ma még nincs adat, gyűjtsön.

    A `--youtube` kapcsoló a youtube-jelre (youtube_nyers.json legfrissebb
    'lekerdezes_utc'-je) vált; enélkül a napi legfrissebb.json 'frissitve' a jel.

    A `--szegmens` kapcsoló a szegmens-tudatos felkapott őr-ágára vált (reggel/este),
    a napok/<ma_bp>.json <szegmens>.frissitve dátumát vizsgálja, ma-t Budapest-napból számítva.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--szegmens" in argv:
        i = argv.index("--szegmens")
        szegmens = argv[i + 1]
        maradek = argv[:i] + argv[i + 2:]
        docs_data = maradek[0] if maradek else "docs/data"
        ma_bp = seged.most_utc().astimezone(seged.BUDAPEST).date().isoformat()
        print("true" if szegmens_mar_gyujtottunk_ma(docs_data, szegmens, ma_bp) else "false")
        return 0
    youtube = "--youtube" in argv
    argv = [a for a in argv if a != "--youtube"]
    ma = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if youtube:
        path = argv[0] if argv else ALAP_YOUTUBE_NYERS
        megvan = youtube_mar_gyujtottunk_ma(path, ma)
    else:
        path = argv[0] if argv else ALAP_LEGFRISSEBB
        megvan = mar_gyujtottunk_ma(path, ma)
    print("true" if megvan else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
