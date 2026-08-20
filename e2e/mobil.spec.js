const { test, expect } = require("@playwright/test");

// Task 10 §1 — render-on-load GUARD (data-rendered near-vs-far). A mért geometriát rögzíti kód-formában.
// FONTOS: a canvas ELEM eagerly jön létre (kartya_letrehoz:415), tehát a canvas jelenléte TAUTOLÓGIA lenne; a
// data-rendered CSAK rajzoláskor (chart_letrehoz:507) kerül fel → az méri a valódi lusta állapotot.
// A near-vs-far szerkezet BEÉPÍTETT nem-vacuous bizonyíték: ha a pozitív magától teljesülne (eager), a negatív
// oldal is teljesülne → a teszt BUKNA. A mock a napi valós adattól független (kulcsszo.spec.js mintája).
// ÁTTEKINTŐ-PANEL ÚJRAMÉRÉS (2026-08-20, #attekinto-blokk hozzáadva a #kulcsszo-blokk ELÉ): a panel legfelülre
// tolja a kulcsszó-kártyákat → load-kor (scrollY=0, 360×640, zóna-alja = VH+rootMargin(400) = 1040) MÉRT top:
// állás=1317px, albérlet=1880px, hitel=2385px — MINDHÁROM a zónán KÍVÜL → load-kor 0 kártya rendered (ez a
// panel SZÁNDÉKOS, prominens elhelyezésének helyes következménye, NEM render-regresszió). A pozitív bizonyíték
// ezért innentől scrollIntoViewIfNeeded-del jön (mint a kulcsszo.spec.js "11." tesztje): az elsőt a zónába
// görgetve MÉRT scrollY=1242, állás top=75px, albérlet top=638px (mindkettő a zónában) → RENDERED; a hitel
// (utolsó) ekkor top=1143px, a zóna-alján (1040) TÚL marad → NEM rendered — a near-vs-far szerkezet megmarad.

const KEZD_MS = Date.parse("2026-07-29T20:00:00Z");
const iso = (h) => new Date(KEZD_MS + h * 3600000).toISOString().replace(".000Z", "+00:00");
function pontok(n) { const p = []; for (let i = 0; i < n; i++) p.push({ idopont_utc: iso(i), ertek: 30 + (i % 20), reszleges: false }); p.push({ idopont_utc: iso(n), ertek: 0, reszleges: true }); return p; }
function ivErvenyes() { return { ervenyes: true, meredekseg_nap: 1.5, se_meredekseg: 0.4, se_masodlagos_autokorrelacio: true, irany: "novekszik", r2: 0.31, r2_masodlagos_autokorrelacio: true, ablak_kezdet_utc: iso(0), ablak_veg_utc: iso(168), pontok_hasznalt: 168, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 0, illesztes_vonal: [{ idopont_utc: iso(0), ertek: 35 }, { idopont_utc: iso(167), ertek: 42 }] }; }
function ivHibas(ok) { return { ervenyes: false, ok }; }
function regSzo(domen) { return { meres_kezdete: "2026-07-30", meres_vege: null, aktiv: true, domen, tipus: "szintmero", intervallumok: { "1_het": ivErvenyes(), "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }; }
const REG = { szamitva_utc: "2026-08-05T20:37:39+00:00", meredekseg_egyseg: "relatív pont / nap", irany_kuszob: 1.0, megjegyzes: "teszt", kulcsszavak: { "állás": regSzo("munkaeropiac"), "albérlet": regSzo("lakhatas"), "hitel": regSzo("lakhatas") } };
const NYERS = { kulcsszavak: { "állás": [{ kulcsszo: "állás", ablak_kezdet_utc: iso(0), ablak_veg_utc: iso(168), pontok: pontok(168) }], "albérlet": [{ kulcsszo: "albérlet", ablak_kezdet_utc: iso(0), ablak_veg_utc: iso(168), pontok: pontok(168) }], "hitel": [{ kulcsszo: "hitel", ablak_kezdet_utc: iso(0), ablak_veg_utc: iso(168), pontok: pontok(168) }] } };

async function mock_kulcsszo(page) {
  // 6b Szelet 2: a másodlagos fájlok a kulcsszo-blokk BLOKK-jában vannak → izoláljuk (üres), különben a
  // teszt-szerver VALÓS másodlagosa (pl. albérlet) beszivárog → a default a leghosszabb érvényesre ugrik →
  // az első kártya (állás, nincs másodlagosa) üres → nem renderel. (Rejtett valós-adat-függés volt.)
  await page.route(/kulcsszo_masodlagos_regresszio\.json/, (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify({ kulcsszavak: {} }) }));
  await page.route(/kulcsszo_masodlagos_nyers\.json/, (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify({ kulcsszavak: {} }) }));
  await page.route(/kulcsszo_regresszio\.json/, (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify(REG) }));
  await page.route(/kulcsszo_nyers\.json/, (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify(NYERS) }));
}

// ── G1 — render-on-load: a panel miatt load-kor SENKI nem rendered; a zónába görgetett kártya IGEN, a TÁVOLI NEM (beépített nem-vacuous) ──
test("G1. render-on-load 360x640-en: a #attekinto-blokk miatt load-kor 0 kártya rendered; zónába görgetve az első IGEN, a TÁVOLI (utolsó) NEM", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 });
  await mock_kulcsszo(page);
  await page.goto("/");
  const kartyak = page.locator("#kulcsszo-blokk .kulcsszo-chart");
  await expect(kartyak).toHaveCount(3);
  await page.evaluate(() => window.scrollTo(0, 0));
  // LOAD-KOR: a panel a fold alá tolja mindhárom kártyát (lásd fenti mért geometria) → egyik sem rendered.
  await expect(page.locator("#kulcsszo-blokk .kulcsszo-chart[data-rendered='true']")).toHaveCount(0);
  // POZITÍV: az elsőt a zónába görgetve (scrollIntoViewIfNeeded) rajzolódik.
  await kartyak.first().scrollIntoViewIfNeeded();
  await expect(kartyak.first()).toHaveAttribute("data-rendered", "true");
  // NEGATÍV (beépített nem-vacuous bizonyíték): a TÁVOLI (utolsó) kártya EKKOR is a zónán KÍVÜL marad → NEM rajzolódik.
  // Ha a data-rendered eagerly kerülne fel (canvas-tautológia), ez is "true" lenne → a teszt bukna.
  await expect(kartyak.last()).not.toHaveAttribute("data-rendered", "true");
});

// ── G2 — a dátum-<select> érintési célmérete >= 24px (WCAG 2.5.8 AA); MÉRT ma: 19px (BUKIK) ──
test("G2. a dátum-select magassága >= 24px (WCAG 2.5.8 AA; ma 19px bukna)", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 });
  await page.goto("/");
  const sel = page.locator("#datum-valaszto select");
  await expect(sel).toHaveCount(1);
  const bb = await sel.boundingBox();
  expect(bb.height).toBeGreaterThanOrEqual(24);
});

// ── G3 — a coarse-réteg (44px érintési célméret) nem törölhető NÉMÁN: a @media (pointer: coarse) szabály LÉTEZIK ──
test("G3. a @media (pointer: coarse) réteg jelen az app.css-ben (a 44px érintési célméret őre)", async ({ page }) => {
  const css = await (await page.request.get("/css/app.css")).text();
  expect(css).toMatch(/@media\s*\(\s*pointer:\s*coarse\s*\)/);
});
