"""Idempotencia-őr a napi trendgyűjtéshez.

A `napi.yml` több ütemezett cron-idősávból is elindulhat (fő + fallback slotok),
hogy a GitHub ingatag scheduler-e miatt ne maradjon ki egy nap sem. Ez az őr dönti
el egy ÜTEMEZETT futásnál: gyűjtsön-e, vagy némán lépjen ki, mert ma már gyűjtöttünk.

A jel a `docs/data/legfrissebb.json` 'frissitve' időbélyege (a gyűjtés UTC-ideje):
ha a DÁTUM-előtagja a mai UTC-dátum, akkor ma már megvan az adat.

A pótolhatatlan órás Google-utat érinti, ezért a döntés pure és tesztelt; a
hiányzó/olvashatatlan jel biztonságos alapértelmezése: NEM gyűjtöttünk (inkább
gyűjtsünk, mint tévesen kihagyjunk egy napot).
"""
import json
import sys
from datetime import datetime, timezone

ALAP_LEGFRISSEBB = "docs/data/legfrissebb.json"


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


def main(argv=None):
    """CLI: kiírja a KIHAGYÁSI döntést a napi.yml őr-lépésének.

    'true'  → ma már gyűjtöttünk, az ütemezett futás hagyja ki a gyűjtést.
    'false' → ma még nincs adat, gyűjtsön.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    path = argv[0] if argv else ALAP_LEGFRISSEBB
    ma = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print("true" if mar_gyujtottunk_ma(path, ma) else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
