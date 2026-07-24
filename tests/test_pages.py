import re
from pathlib import Path


def test_index_html_letezik_es_hivatkozik_az_adatra():
    gyoker = Path(__file__).resolve().parent.parent
    html = (gyoker / "docs" / "index.html").read_text(encoding="utf-8")
    assert "Trendfigyelő" in html
    # href-scoped: a linkeknek valódi <a href="..."> hivatkozásként kell szerepelniük
    for link in ("data/legfrissebb.json", "data/tortenet.json", "data/napok/index.json"):
        assert re.search(rf'href=["\']{re.escape(link)}["\']', html), f"hiányzó href: {link}"
    assert "Phase 3" in html


def test_index_html_js_mentes():
    """Biztosít, hogy az oldal teljesen JS-mentes."""
    gyoker = Path(__file__).resolve().parent.parent
    html = (gyoker / "docs" / "index.html").read_text(encoding="utf-8")

    # Nincs <script> tag
    assert "<script" not in html.lower(), "HTML nem lehet <script> tagot tartalmazni"

    # Nincs javascript: URL
    assert "javascript:" not in html.lower(), "HTML nem lehet javascript: URL-t tartalmazni"

    # Nincs inline event handler (onclick, onload, onerror, stb.)
    assert re.search(r"\son[a-z]+\s*=", html, re.IGNORECASE) is None, \
        "HTML nem tartalmazhat inline event handler attribútumot"
