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
import sys
from datetime import datetime, timezone

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


def main(argv=None):
    """CLI: kiírja a KIHAGYÁSI döntést a napi.yml / youtube.yml őr-lépésének.

    'true'  → ma már gyűjtöttünk, az ütemezett futás hagyja ki a gyűjtést.
    'false' → ma még nincs adat, gyűjtsön.

    A `--youtube` kapcsoló a youtube-jelre (youtube_nyers.json legfrissebb
    'lekerdezes_utc'-je) vált; enélkül a napi legfrissebb.json 'frissitve' a jel.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
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
