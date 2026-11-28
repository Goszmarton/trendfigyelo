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
    "--akcentus-halvany": "#E3F4F1", "--akcentus-sotet": "#145f5f",
    "--arnyek": "0 4px 16px rgba(26, 29, 32, 0.07)",
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


# ── Task 2: szinek.js, JS-színek tokenre ─────────────────────────────────────
JS = DOCS / "js"
HAVI_LEAFLET_ENGEDELYEZETT = {"#ef6c33", "#fff", "#5a7fb0", "#c3ccd6", "#f3f0e9", "#2c4a73", "#999", "#888"}
SZIN_MINTA = re.compile(r"#[0-9a-fA-F]{3,6}\b|rgba?\(")
OLDAL_JS = ("js/app.js", "js/heti.js", "js/havi.js", "js/bovites.js", "js/youtube.js")


def _js_megjegyzes_nelkul(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?<![:\"'\\])//[^\n]*", "", src)


def test_szinek_js_letezik_es_exportal():
    src = (JS / "szinek.js").read_text(encoding="utf-8")
    for nev in ("function szin(", "function tema_szin(", "function grafikon_alap(", "TEMA_SORREND_GOOGLE", "module.exports"):
        assert nev in src, nev


def test_js_nincs_beegetett_hex_szin():
    hibak = []
    for f in sorted(JS.glob("*.js")):
        if f.name == "szinek.js":
            continue
        for i, sor in enumerate(_js_megjegyzes_nelkul(f.read_text(encoding="utf-8")).splitlines(), 1):
            for m in SZIN_MINTA.finditer(sor):
                if f.name == "havi.js" and m.group(0).lower() in HAVI_LEAFLET_ENGEDELYEZETT:
                    continue
                hibak.append(f"{f.name}:{i}: {m.group(0)}")
    assert not hibak, hibak


def test_szinek_js_a_chart_utan_es_az_oldal_js_elott_tolt():
    for html in sorted(DOCS.glob("*.html")):
        srcs = re.findall(r'<script src="([^"]+)"', html.read_text(encoding="utf-8"))
        if not any(x in srcs for x in OLDAL_JS):
            continue
        assert "js/szinek.js" in srcs, html.name
        i = srcs.index("js/szinek.js")
        for x in srcs:
            if x == "vendor/chartjs/chart.umd.js":
                assert srcs.index(x) < i, html.name
            if x in OLDAL_JS:
                assert srcs.index(x) > i, html.name


def test_vonalpaletta_nem_hasznalja_a_tema_7_et():
    src = (JS / "app.js").read_text(encoding="utf-8")
    m = re.search(r"const IDOSOR_PALETTA = \[([^\]]*)\]", src)
    assert m, "nincs IDOSOR_PALETTA"
    assert "7" not in [x.strip() for x in m.group(1).split(",")]
    assert not re.search(r'szin\("tema-7"\)', src)


def test_attekinto_ikonok_css_a_tokeneket_hasznalja():
    for hex_ in ("#2e7d32", "#b23c3c", "#777"):
        assert hex_ not in CSS.lower(), hex_


# ---- Task 3: oldalsáv + fiókmenü ----
import yaml

GYOKER = DOCS.parent
OLDALAK = ["index", "elemzes", "heti", "havi", "valtozasok", "ugyek", "kapcsolodo",
           "trendek", "youtube", "adatokrol"]


def _oldal(nev):
    return (DOCS / f"{nev}.html").read_text(encoding="utf-8")


def _nav_normalizalt(html):
    m = re.search(r'<nav id="fomenu".*?</nav>', html, re.DOTALL)
    assert m, "nincs #fomenu"
    nav = m.group(0)
    nav = nav.replace(' aria-current="page"', "")
    nav = re.sub(r'\s+aktiv(?=")', "", nav)
    nav = nav.replace(' class="aktiv"', "")
    return re.sub(r"\s+", " ", nav)


def test_menu_mind_a_10_oldalon_azonos():
    navok = {o: _nav_normalizalt(_oldal(o)) for o in OLDALAK}
    elso = navok["index"]
    for o, n in navok.items():
        assert n == elso, o


def test_minden_oldalon_keret_vaz():
    for o in OLDALAK:
        h = _oldal(o)
        assert '<body class="keret"' in h, o
        assert 'class="keret-oldalsav"' in h, o
        assert 'class="keret-fo"' in h, o
        assert 'id="keret-felso"' in h, o
        assert 'id="keret-menugomb"' in h, o
        assert 'src="js/keret.js"' in h, o
        assert h.index('class="keret-oldalsav"') < h.index('id="fomenu"') < h.index('class="keret-fo"'), o


def test_statikus_badge_egyezik_a_configgal():
    c = yaml.safe_load((GYOKER / "config.yaml").read_text(encoding="utf-8"))
    g, y = len(c["kulcsszavak"]), len(c["youtube"])
    for o in OLDALAK:
        h = _oldal(o)
        assert re.search(rf'<a href="trendek\.html"[^>]*data-badge="{g}"', h), o
        assert re.search(rf'<a href="youtube\.html"[^>]*data-badge="{y}"', h), o


def test_body_data_keret_oldal():
    for o, v in {"index": "attekinto", "elemzes": "napi", "heti": "heti", "havi": "havi", "valtozasok": "valtozasok",
                 "ugyek": "ugyek", "kapcsolodo": "kapcsolodo", "trendek": "google", "youtube": "youtube",
                 "adatokrol": "info"}.items():
        assert f'<body class="keret" data-keret-oldal="{v}">' in _oldal(o), o


def test_css_szinek_csak_tokenbol():
    """A :root blokkon kívül a deklaráció-ÉRTÉKEKBEN nincs #hex / rgb(a)( literál."""
    kod = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    kod = re.sub(r":root\s*\{[^}]*\}", "", kod, count=1)
    ertekek = re.findall(r"(?<![\w-])[a-z-]+\s*:\s*([^;{}]+)(?=[;}])", kod)
    hibas = [e.strip() for e in ertekek if re.search(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", e)]
    assert not hibas, hibas
