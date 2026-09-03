"""Az AI-elemzés idempotencia-őre + mód-tudatos logikai nap (a futas_orzo.py mintájára).

A napi.yml/reggeli.yml backup-cronjai 'success'-szel zárnak akkor is, ha nem gyűjtöttek,
és mindegyik újraindítja az elemzes.yml-t. Enélkül az elemzés ugyanaznap többször
regenerálódik (nem-determinisztikus próza = flash), az éjfél-utáni esti backup pedig a
KÖVETKEZŐ napra írna üres elemzést (mert a nyers budapesti dátumot használná). Ez a modul
mód szerinti logikai napot ad (reggel = BP naptári nap, este = esti_nap) és eldönti,
kész-e már a mai (nap, mód) elemzés.
"""
import json
import sys
from pathlib import Path

from . import seged


def elemzes_nap(mode, most):
    """A (mode) logikai elemzés-napja. reggel: budapesti naptári nap; este: seged.esti_nap.

    Az esti ág a hajnali (<6:00 BP) futást az ELŐZŐ estére sorolja — nincs következő-napi
    elcsúszás, ezért az éjfél-utáni backup nem ír üres 'holnapi' elemzést."""
    if mode == "este":
        return seged.esti_nap(most)
    return most.astimezone(seged.BUDAPEST).date().isoformat()


def _artefakt_modja(docs_data, nap):
    """Az elemzesek/<nap>.json 'mode' mezője, vagy None (hiányzó/olvashatatlan/régi archív)."""
    fajl = Path(docs_data) / "elemzesek" / f"{nap}.json"
    try:
        art = json.loads(fajl.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return art.get("mode") if isinstance(art, dict) else None


def elemzes_mar_kesz(docs_data, nap, mode):
    """True, ha a mai (nap) elemzés ebben a módban már kész (a backup-újraindítás kihagyható).

    reggel: kész, ha a mai fájl LÉTEZIK (idempotens; sosem ír felül egy esti teljeset →
            nem downgrade-el). este: kész CSAK ha a létező 'mode' == 'este' (teljes) —
            'reggel' esetén az esti LEFUT (scoped → teljes upgrade).
    Hiányzó/olvashatatlan → False (fail-open: inkább fusson, mint tévesen kihagyja)."""
    if mode == "reggel":
        return (Path(docs_data) / "elemzesek" / f"{nap}.json").exists()
    return _artefakt_modja(docs_data, nap) == "este"


def main(argv=None):
    """CLI: `--mode <reggel|este> <docs_data>` → 'true' (ma kész, hagyd ki) / 'false' (fuss)."""
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = "este"
    if "--mode" in argv:
        i = argv.index("--mode")
        mode = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    docs_data = argv[0] if argv else "docs/data"
    nap = elemzes_nap(mode, seged.most_utc())
    print("true" if elemzes_mar_kesz(docs_data, nap, mode) else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
