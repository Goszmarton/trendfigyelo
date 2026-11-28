"""Egységes formavilág – Task 1: design-tokenek, vendorált Inter és lucide-sprite."""
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
CSS = (DOCS / "css" / "app.css").read_text(encoding="utf-8")

TOKENEK = {
    "--oldalsav-hatter": "#202326", "--oldalsav-szoveg": "#C9CED2", "--oldalsav-cim": "#858D94",
    "--aktiv-hatter": "#8FDCD0", "--aktiv-szoveg": "#202326",
    "--hatter": "#F5F6F4", "--kartya": "#FFFFFF", "--keret": "#E2E5E3",
    "--szoveg": "#1A1D20", "--szoveg-2": "#66707A", "--akcentus": "#1F8A8A",
    "--ok": "#2E8B57", "--figy": "#D9A21B", "--hiba": "#C8414B", "--semleges": "#98A0A8",
    "--google": "#3B6FD8", "--youtube": "#D6453D",
    "--tema-1": "#0072B2", "--tema-2": "#E69F00", "--tema-3": "#009E73", "--tema-4": "#CC79A7",
    "--tema-5": "#56B4E9", "--tema-6": "#D55E00", "--tema-7": "#F0E442", "--tema-8": "#4D4D4D",
    "--graf-ml": "#8e44ad", "--graf-elorejelzes": "#16a085",
    "--graf-elorejelzes-sav": "rgba(22, 160, 133, 0.15)", "--graf-trend": "#cc3333",
    "--graf-szint": "#e69138", "--graf-sav": "rgba(120, 120, 120, 0.14)", "--graf-jelolo": "#8a8a8a",
    "--betu": '"Inter", system-ui, "Segoe UI", sans-serif',
    "--r-kartya": "12px", "--r-chip": "8px", "--r-pill": "999px",
    "--ter-1": "4px", "--ter-2": "8px", "--ter-3": "12px", "--ter-4": "16px",
    "--ter-5": "20px", "--ter-6": "24px", "--ter-7": "32px", "--ter-8": "40px",
    "--betu-cim": "30px", "--betu-szakasz": "17px", "--betu-kartya": "14.5px",
    "--betu-torzs": "14px", "--betu-seged": "12.5px", "--betu-mikro": "11px",
}

IKONOK = ["i-attekinto", "i-napi", "i-heti", "i-havi", "i-valtozasok", "i-ugyek",
          "i-kapcsolodo", "i-google", "i-youtube", "i-info", "i-menu", "i-logo"]


def _root_blokk():
    m = re.search(r":root\s*\{([^}]*)\}", CSS)
    assert m, "nincs :root blokk"
    return m.group(1)


def test_root_tokenek_a_spec_ertekeivel():
    deklaraciok = {
        k.strip(): re.sub(r"\s+", " ", v.strip()).lower()
        for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", _root_blokk())
    }
    for nev, ertek in TOKENEK.items():
        assert nev in deklaraciok, f"hiányzó token: {nev}"
        assert deklaraciok[nev] == ertek.lower(), f"{nev}: {deklaraciok[nev]} != {ertek}"


def test_inter_font_face_helyi():
    m = re.search(r"@font-face\s*\{([^}]*)\}", CSS)
    assert m, "nincs @font-face"
    blokk = m.group(1)
    assert re.search(r'font-family:\s*"Inter"', blokk)
    assert 'src: url("../vendor/inter/InterVariable.woff2")' in blokk
    assert (DOCS / "vendor/inter/InterVariable.woff2").is_file()


def test_lucide_sprite_szimbolumok():
    svg = (DOCS / "vendor/lucide/ikonok.svg").read_text(encoding="utf-8")
    for i in IKONOK:
        assert re.search(rf'<symbol\b[^>]*\bid="{i}"', svg), f"hiányzó szimbólum: {i}"
