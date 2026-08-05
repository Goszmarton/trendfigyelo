# Vendorolt eszközök — forrás és integritás

A `docs/vendor/` alatti fájlok külső eszközök **pinelt** másolatai. Minden fájlhoz
egy gépi sor tartozik (relatív útvonal + sha256), amit a `tests/test_pages.py`
`vendor_integritas_ellenorzes` guardja őriz: a fájl tényleges sha256-jának egyeznie
kell az itt rögzítettel, és nem lóghat sem listázatlan fájl, sem hiányzó bejegyzés.

## chart.js 4.5.1 (MIT)

- Csomag: `chart.js`, verzió: **4.5.1**
- Fájl: `chartjs/chart.umd.js` (a tarball `package/dist/chart.umd.js` tagja)
- Méret: 208 518 bájt (~204 KB)
- Licenc: **MIT**
- Tarball: https://registry.npmjs.org/chart.js/-/chart.js-4.5.1.tgz
- Tarball sha512 (npm registry `dist.integrity`, letöltéskor egyeztetve):
  `sha512-GIjfiT9dbmHRiYi6Nl2yFCq7kkwdkp1W/lp2J99rX0yo9tgJGn3lKQATztIjb5tVtevcBtIdICNWqlq5+E8/Pw==`

**Őszinte korlát:** a fenti registry-integrity a **kiadott tarballt** pinneli (a
szállítási csatorna, az npm registry attesztációja), **nem** a Chart.js szerzőinek
kriptográfiai aláírása. A letöltött tarball sha512-je bájtra egyezett ezzel az
értékkel; ebből a **verifikált** tarballból bontottuk ki a fájlt, és annak sha256-ja
szerepel a gépi sorban (ezt őrzi a guard). Adapter nélkül vendoroljuk (kategória-tengely,
magyar címkék előre formázva); a date-adapter + date-fns nincs vendorolva.

`chartjs/chart.umd.js` — sha256: `ecc3cd1eeb8c34d2178e3f59fd63ec5a3d84358c11730af0b9958dc886d7652a`
