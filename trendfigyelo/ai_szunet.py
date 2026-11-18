"""Az AI-generált elemzések (napi / heti / havi / Radar-ügyek) SZÜNETELTETÉSI kapcsolója.

Szünetben a generáló lépés el sem indul → NINCS Anthropic API-hívás (token-költség).

Egyetlen forrás: `docs/data/ai_szunet.json`, pl.
    {"szunetel": {"napi": true, "heti": true, "havi": true}, "ota": "2026-11-18", "uzenet": "..."}
A workflow-őrök (elemzes/heti/havi/bovites.yml) ezt olvassák a generálás ELŐTT; a honlap ugyanebből
írja ki a szüneteltetés tényét. A meglévő elemzések NEM törlődnek. Hiányzó/hibás fájl = nincs szünet
(fail-open, hogy egy elírt fájl ne állítsa le csendben a generálást). Csak stdlib.

CLI: `python -m trendfigyelo.ai_szunet <napi|heti|havi|ugyek> [docs/data]` → "true" / "false".
"""
import json
import sys
from pathlib import Path

FAJLNEV = "ai_szunet.json"
TIPUSOK = ("napi", "heti", "havi", "ugyek")


def szunetel(tipus, data_dir="docs/data"):
    if tipus not in TIPUSOK:
        raise ValueError(f"ismeretlen típus: {tipus}")
    try:
        d = json.loads((Path(data_dir) / FAJLNEV).read_text(encoding="utf-8"))
        return (d.get("szunetel") or {}).get(tipus) is True
    except (OSError, ValueError, AttributeError):
        return False


def main(argv):
    tipus = argv[1]
    data_dir = argv[2] if len(argv) > 2 else "docs/data"
    print("true" if szunetel(tipus, data_dir) else "false")


if __name__ == "__main__":
    main(sys.argv)
