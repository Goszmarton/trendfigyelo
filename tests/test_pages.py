from __future__ import annotations

import hashlib
import re
from pathlib import Path

GYOKER = Path(__file__).resolve().parent.parent
DOCS = GYOKER / "docs"


# ─────────────────────────────────────────────────────────────────────────────
# Politika-segédfüggvények (tiszta, fixtúrázható) — Task 1
#
# §5 teszt-politika: „csak saját és vendorolt eszköz, semmi külső betöltés".
# A számítási logika NEM böngészőben van (8.3), ezért itt csak betöltési és
# integritási invariánsokat őrzünk — számítási helyességet nem.
# ─────────────────────────────────────────────────────────────────────────────

# HTML: külső hivatkozás CSAK BETÖLTŐ tagek attribútumában / CSS-ben számít.
# A <a href> és <area href> NAVIGÁCIÓ (Task 7 kifelé linkel: hírforrás, Google
# Trends) — ezek KIVÉTELEK. Az xmlns="http://..." nem betöltő attribútum, így a
# tag+attribútum párosítás eleve kizárja.
_BETOLTO_ATTR = {
    "link": "href",
    "script": "src",
    "img": "src",
    "iframe": "src",
    "source": "src",
    "video": "src",
    "audio": "src",
    "form": "action",
}
_TAG = re.compile(r"<(\w+)\b([^>]*)>", re.IGNORECASE | re.DOTALL)
_KULSO_ERTEK = re.compile(r"""^\s*(?:https?:)?//""", re.IGNORECASE)

# CSS: @import és url(...) külső értékei. Az inline <style>-ra és a különálló
# .css fájlokra egyaránt (kulso_hivatkozasok_css) — egyetlen minta, nem duplikált.
_CSS_KULSO = re.compile(
    r"""(?:@import\s+|url\(\s*)["']?\s*(?:https?:)?//""",
    re.IGNORECASE,
)


def kulso_hivatkozasok_css(forras: str) -> list[str]:
    """A CSS-forrás külső @import / url(...) hivatkozásait adja vissza.

    Talál: @import url(https://...), url(//cdn...), @import 'https://...'.
    NEM talál: relatív @import "alap.css", url(kepek/bg.png), url("../x.png").
    """
    return [m.group(0) for m in _CSS_KULSO.finditer(forras)]


def _attr_ertek(attrs: str, nev: str) -> str | None:
    """Egy attribútum értéke idézőjelesen VAGY csupaszon (> és whitespace zár)."""
    m = re.search(
        rf"""\b{nev}\s*=\s*(?:["']([^"']*)["']|([^\s>"']+))""",
        attrs,
        re.IGNORECASE,
    )
    if not m:
        return None
    return m.group(1) if m.group(1) is not None else m.group(2)


def kulso_hivatkozasok_html(html: str) -> list[str]:
    """A HTML külső (abszolút vagy protokoll-relatív) BETÖLTÉSEIT adja vissza.

    Talál: <link href>, <script/img/iframe/source/video/audio src>, <form action>,
           valamint az inline CSS (@import / url(...))  ha az érték https:// vagy
           // szekvenciával kezdődik.
    NEM talál: relatív útvonal; <a href> / <area href> (navigáció, nem betöltés);
               xmlns="http://www.w3.org/..." (nem betöltő attribútum).
    """
    talalatok: list[str] = []
    for tag, attrs in _TAG.findall(html):
        attr = _BETOLTO_ATTR.get(tag.lower())
        if not attr:
            continue
        ertek = _attr_ertek(attrs, attr)
        if ertek and _KULSO_ERTEK.match(ertek):
            talalatok.append(f"<{tag.lower()} {attr}={ertek!r}>")
    talalatok += kulso_hivatkozasok_css(html)
    return talalatok


# JS: külső URL = string-literál (', ", vagy `), amely https?:// vagy //
# szekvenciával KEZDŐDIK. A „// sorvégi komment" és a „... // ..." közbülső //
# NEM string-eleji → az idézőjel/backtick-horgony zárja ki.
_JS_KULSO = re.compile(r"""["'`](?:https?:)?//""")


def kulso_hivatkozasok_js(forras: str) -> list[str]:
    """A JS-forrás külső URL string-literáljait adja vissza.

    Talál: "https://...", '//cdn...', `https://...` (idézőjellel/backtickkel KEZDŐDŐ URL).
    NEM talál: `// magyarázat` sorvégi komment, `"a // b"` közbülső //.
    """
    return [m.group(0) for m in _JS_KULSO.finditer(forras)]


# Inline <script>: a src= nélküli, NEM üres törzsű script tiltott.
_SCRIPT_BLOKK = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.IGNORECASE | re.DOTALL)


def inline_script_szegmensek(html: str) -> list[str]:
    """A tiltott inline <script> törzsek (rövidített) listája.

    Engedett: <script src="js/…"></script> (üres/whitespace törzs).
    Tiltott:  <script>…kód…</script>       (nincs src, van törzs).
    """
    talalatok: list[str] = []
    for attrs, torzs in _SCRIPT_BLOKK.findall(html):
        van_src = re.search(r"\bsrc\s*=", attrs, re.IGNORECASE)
        if not van_src and torzs.strip():
            talalatok.append(torzs.strip()[:60])
    return talalatok


# ─────────────────────────────────────────────────────────────────────────────
# Vendor-manifeszt integritás — Task 1 guard, Task 4 (vendorolás) élesíti.
#
# FORRAS.md szigorú sorformátum (soronként egy bejegyzés, a sor elejére horgonyozva):
#     `<relatív/útvonal>` — sha256: `<64 hex>`
# A relatív útvonal a docs/vendor/-hoz képest értendő (alkönyvtár is), pl.
# `chartjs/chart.umd.js`. Prózai sor NEM hoz létre bejegyzést.
# ─────────────────────────────────────────────────────────────────────────────

_FORRAS_SOR = re.compile(
    r"^\s*[-*]?\s*`(?P<fajl>[^`]+)`\s*[—-]\s*sha256:\s*`(?P<hash>[0-9a-fA-F]{64})`\s*$",
    re.IGNORECASE,
)


def _forras_bejegyzesek(forras_szoveg: str) -> dict[str, str]:
    be: dict[str, str] = {}
    for sor in forras_szoveg.splitlines():
        m = _FORRAS_SOR.match(sor)
        if m:
            be[m.group("fajl")] = m.group("hash").lower()
    return be


def vendor_integritas_ellenorzes(konyvtar: Path) -> list[str]:
    """A vendor-könyvtár és a FORRAS.md összhang-hibáit adja vissza (üres = rendben).

    Rekurzív: alkönyvtárak fájljait is nézi, a kulcs a könyvtárhoz képesti
    RELATÍV útvonal. Üres vagy nemlétező könyvtár → []. Egyébként minden
    nem-FORRAS fájlnak szerepelnie kell a FORRAS.md-ben egyező sha256-tal, és
    minden listázott bejegyzésnek léteznie kell fájlként.
    """
    hibak: list[str] = []
    if not konyvtar.is_dir():
        return hibak

    fajlok = {
        p.relative_to(konyvtar).as_posix(): p
        for p in konyvtar.rglob("*")
        if p.is_file() and p.name != "FORRAS.md"
    }
    forras_ut = konyvtar / "FORRAS.md"
    bejegyzesek = (
        _forras_bejegyzesek(forras_ut.read_text(encoding="utf-8"))
        if forras_ut.is_file()
        else {}
    )

    if not fajlok and not bejegyzesek:
        return hibak

    for nev, ut in sorted(fajlok.items()):
        if nev not in bejegyzesek:
            hibak.append(f"nincs FORRAS-bejegyzés: {nev}")
            continue
        if hashlib.sha256(ut.read_bytes()).hexdigest() != bejegyzesek[nev]:
            hibak.append(f"hash-eltérés: {nev}")
    for nev in sorted(bejegyzesek):
        if nev not in fajlok:
            hibak.append(f"listázott de hiányzó: {nev}")
    return hibak


def _index_html() -> str:
    return (DOCS / "index.html").read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Az oldal létezik és a tartós azonosítót hordozza (Task 1 trimmelt)
#   A "Phase 3" placeholder és a nyers-adat href-ek KIKERÜLTEK (C döntés) — a
#   szerkezeti horgonyokat Task 5 (váz-HTML) adja majd hozzá.
# ─────────────────────────────────────────────────────────────────────────────

def test_index_html_letezik():
    html = _index_html()
    assert "Trendfigyelő" in html                                  # tartós azonosító (Task 1)
    # Task 5 váz-horgonyok: a kétblokkos elrendezés (§7.1) + a két vezérlő + a saját/vendorolt eszközök.
    for horgony in (
        'id="kulcsszo-blokk"', 'id="trend-blokk"',
        'id="intervallum-vezerlo"', 'id="datum-valaszto"',
        'href="css/app.css"',
        'src="vendor/chartjs/chart.umd.js"',
        'src="js/app.js"',
    ):
        assert horgony in html, horgony


def test_loader_cache_busting():
    # A data-fetch cache-busting: ?v= + Date.now() (§4.1). Forrás-szintű (statikus) ellenőrzés;
    # a futásidejű hatást a Playwright-smoke igazolná (ledger nyitott elem).
    js = DOCS / "js" / "app.js"
    assert js.exists(), "docs/js/app.js hiányzik"
    src = js.read_text(encoding="utf-8")
    assert "?v=" in src and "Date.now()" in src


def test_loader_hibakezeles():
    # Nem néma, IZOLÁLT hibaállapot (§7.5, finding 6).
    # FIGYELEM: a RÉGI assert ("catch" in src + textContent) a HIBÁS kódot is átengedte —
    # a blokk-szintű Promise.all miatt a hiányzó kulcsszo_regresszio.json elvitte a betöltött
    # kulcsszo_nyers.json-t is, és a textContent felülírta a konténert. NE egyszerűsítsd vissza
    # "catch"-re: az allSettled-alapú helyes megoldásban NINCS try/catch, a hibát rejected-
    # státuszból kezeljük, KÜLÖN gyerek-elembe írva.
    js = DOCS / "js" / "app.js"
    assert js.exists(), "docs/js/app.js hiányzik"
    src = js.read_text(encoding="utf-8")
    assert "allSettled" in src                              # per-blokk ÉS per-fájl izoláció
    assert "Hiba az adat betöltésekor" in src               # felhasználónak szánt magyar hibaszöveg
    assert "createElement" in src and "appendChild" in src, \
        "a hiba KÜLÖN gyerek-elembe kerüljön (ne a konténer textContent-jét írja felül)"
    # Statikusan NEM ellenőrizhető: a fájlonkénti izoláció TÉNYE és a hibaüzenet MINŐSÉGE
    # (melyik fájl + ok) — ezek a Playwright-smoke tárgyai (ledger nyitott elem).


# ─────────────────────────────────────────────────────────────────────────────
# Ciklus A — „csak saját és vendorolt eszköz" (a régi js_mentes helyén)
# ─────────────────────────────────────────────────────────────────────────────

def test_nincs_inline_script():
    assert inline_script_szegmensek(_index_html()) == []


def test_nincs_inline_event_handler():
    assert re.search(r"\son[a-z]+\s*=", _index_html(), re.IGNORECASE) is None


def test_nincs_javascript_url():
    # A teljes dokumentumra: az <a href="javascript:..."> navigációt is tiltja.
    assert "javascript:" not in _index_html().lower()


def test_index_html_nincs_kulso_betoltes():
    assert kulso_hivatkozasok_html(_index_html()) == []


def test_sajat_js_nincs_kulso_url():
    js_dir = DOCS / "js"
    for js in sorted(js_dir.rglob("*.js")) if js_dir.is_dir() else []:
        assert kulso_hivatkozasok_js(js.read_text(encoding="utf-8")) == [], str(js)


def test_sajat_css_nincs_kulso_url():
    css_dir = DOCS / "css"
    for css in sorted(css_dir.rglob("*.css")) if css_dir.is_dir() else []:
        assert kulso_hivatkozasok_css(css.read_text(encoding="utf-8")) == [], str(css)


# — detektorok kétirányú egységtesztjei (fals pozitív ÉS valódi találat) —

def test_html_detektor_fals_pozitivok():
    for jo in (
        '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
        '<a href="data/legfrissebb.json">x</a>',
        '<a href="https://trends.google.com/">forrás</a>',   # navigáció, nem betöltés
        '<img src="kepek/x.png">',
        '<img src=kepek/x.png>',                             # csupasz érték, relatív
        '<style>.x{background:url(bg.png)}</style>',
    ):
        assert kulso_hivatkozasok_html(jo) == [], jo


def test_html_detektor_valodi_talalatok():
    for rossz in (
        '<script src="https://cdn.example/chart.js"></script>',
        '<script src=https://cdn.example/x.js></script>',    # csupasz érték, külső
        '<link href="https://fonts.example/x.css">',
        '<link href="//fonts.example/x.css">',
        '<style>@import url(https://evil/x.css)</style>',
        '<form action="https://evil/submit"></form>',
    ):
        assert kulso_hivatkozasok_html(rossz), rossz


def test_css_detektor_fals_pozitivok():
    for jo in (
        '@import "alap.css";',
        '.x{background:url(kepek/bg.png)}',
        '.y{background:url("../kepek/bg.png")}',
    ):
        assert kulso_hivatkozasok_css(jo) == [], jo


def test_css_detektor_valodi_talalatok():
    for rossz in (
        '@import url(https://evil/x.css);',
        '.x{background:url(//cdn.evil/bg.png)}',
        "@import 'https://evil/x.css';",
    ):
        assert kulso_hivatkozasok_css(rossz), rossz


def test_js_detektor_fals_pozitivok():
    for jo in (
        "const x = 1; // https://example.com magyarázat",
        'const p = "data/legfrissebb.json";',
        'const q = "a // b";',
        "const s = `összesen: ${a // b}`;",   # template literál, közbülső //
    ):
        assert kulso_hivatkozasok_js(jo) == [], jo


def test_js_detektor_valodi_talalatok():
    for rossz in (
        'fetch("https://evil/api")',
        "const u = '//cdn.evil/x';",
        "fetch(`https://evil/api`)",           # template literál URL
        "const u = `//cdn.evil/x`;",
    ):
        assert kulso_hivatkozasok_js(rossz), rossz


def test_inline_script_detektor():
    assert inline_script_szegmensek('<script src="js/app.js"></script>') == []
    assert inline_script_szegmensek("<script>alert(1)</script>")


# ─────────────────────────────────────────────────────────────────────────────
# Ciklus B — vendor-manifeszt integritás-guard (tmp_path fixtúrák)
#   Task 4 (vendorolás) élesíti; ott a „hash-teszt" már csak ennek a guardnak
#   az élesben-igazolása lesz, nem új teszt.
# ─────────────────────────────────────────────────────────────────────────────

def _ir_vendor(dir: Path, fajlok: dict[str, bytes], forras_sorok: list[str] | None):
    dir.mkdir(parents=True, exist_ok=True)
    for nev, tart in fajlok.items():
        ut = dir / nev
        ut.parent.mkdir(parents=True, exist_ok=True)
        ut.write_bytes(tart)
    if forras_sorok is not None:
        (dir / "FORRAS.md").write_text("\n".join(forras_sorok) + "\n", encoding="utf-8")


def test_vendor_egyezo_hash_nincs_hiba(tmp_path):          # (a)
    tart = b"console.log(1)"
    h = hashlib.sha256(tart).hexdigest()
    _ir_vendor(tmp_path, {"lib.js": tart}, [f"`lib.js` — sha256: `{h}`"])
    assert vendor_integritas_ellenorzes(tmp_path) == []


def test_vendor_eltero_hash_hiba(tmp_path):                # (b)
    _ir_vendor(tmp_path, {"lib.js": b"console.log(1)"}, ["`lib.js` — sha256: `" + "0" * 64 + "`"])
    assert vendor_integritas_ellenorzes(tmp_path)


def test_vendor_hianyzo_bejegyzes_hiba(tmp_path):          # (c)
    _ir_vendor(tmp_path, {"lib.js": b"x"}, [])  # van fájl, üres FORRAS.md
    assert vendor_integritas_ellenorzes(tmp_path)


def test_vendor_listazott_de_hianyzo_fajl_hiba(tmp_path):  # (d)
    _ir_vendor(tmp_path, {}, ["`lib.js` — sha256: `" + "a" * 64 + "`"])
    assert vendor_integritas_ellenorzes(tmp_path)


def test_vendor_ures_vagy_nemletezo_nincs_hiba(tmp_path):  # (e)
    assert vendor_integritas_ellenorzes(tmp_path / "nincs") == []
    ures = tmp_path / "ures"
    ures.mkdir()
    assert vendor_integritas_ellenorzes(ures) == []


def test_vendor_alkonyvtar_nem_listazott_hiba(tmp_path):   # (f)
    _ir_vendor(tmp_path, {"chartjs/chart.umd.js": b"x"}, [])  # alkönyvtárban, nem listázva
    hibak = vendor_integritas_ellenorzes(tmp_path)
    assert any("chartjs/chart.umd.js" in h for h in hibak), hibak


def test_forras_verzioszamos_sor_parseolodik():            # (g)
    h = hashlib.sha256(b"x").hexdigest()
    be = _forras_bejegyzesek(f"`chart.js@4.4.1/dist/chart.umd.js` — sha256: `{h}`")
    assert be == {"chart.js@4.4.1/dist/chart.umd.js": h}


def test_forras_nagybetus_hex_egyezik(tmp_path):           # (h)
    tart = b"console.log(1)"
    h_nagy = hashlib.sha256(tart).hexdigest().upper()
    _ir_vendor(tmp_path, {"lib.js": tart}, [f"`lib.js` — sha256: `{h_nagy}`"])
    assert vendor_integritas_ellenorzes(tmp_path) == []


def test_forras_prozai_sor_nem_bejegyzes():                # (i)
    be = _forras_bejegyzesek("Ez a Chart.js 4.4.1 disztribúció, kézzel letöltve 2026-08-05-én.")
    assert be == {}


def test_vendor_valos_docs_ma_zold():
    # Ma nincs docs/vendor/ → []. Task 4 vendorolás után ugyanez a guard igazol élesben.
    assert vendor_integritas_ellenorzes(DOCS / "vendor") == []
