const { test, expect } = require("@playwright/test");

// Task 10 §1 — render-on-load GUARD (data-rendered near-vs-far). A mért geometriát rögzíti kód-formában:
// az első kulcsszó-kártya (~708px, 360×640) a rootMargin:400 zónán (alja 1040) BELÜL → chart_letrehoz rajzol →
// data-rendered="true" load-kor. Egy TÁVOLI kártya (zónán kívül, ~1506px) NEM rajzolódik → data-rendered=null.
// FONTOS: a canvas ELEM eagerly jön létre (kartya_letrehoz:415), tehát a canvas jelenléte TAUTOLÓGIA lenne; a
// data-rendered CSAK rajzoláskor (chart_letrehoz:507) kerül fel → az méri a valódi lusta állapotot.
// A near-vs-far szerkezet BEÉPÍTETT nem-vacuous bizonyíték: ha a pozitív magától teljesülne (eager), a negatív
// oldal is teljesülne → a teszt BUKNA. A mock a napi valós adattól független (kulcsszo.spec.js mintája).

const KEZD_MS = Date.parse("2026-07-29T20:00:00Z");
const iso = (h) => new Date(KEZD_MS + h * 3600000).toISOString().replace(".000Z", "+00:00");
function pontok(n) { const p = []; for (let i = 0; i < n; i++) p.push({ idopont_utc: iso(i), ertek: 30 + (i % 20), reszleges: false }); p.push({ idopont_utc: iso(n), ertek: 0, reszleges: true }); return p; }
function ivErvenyes() { return { ervenyes: true, meredekseg_nap: 1.5, se_meredekseg: 0.4, se_masodlagos_autokorrelacio: true, irany: "novekszik", r2: 0.31, r2_masodlagos_autokorrelacio: true, ablak_kezdet_utc: iso(0), ablak_veg_utc: iso(168), pontok_hasznalt: 168, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 0, illesztes_vonal: [{ idopont_utc: iso(0), ertek: 35 }, { idopont_utc: iso(167), ertek: 42 }] }; }
function ivHibas(ok) { return { ervenyes: false, ok }; }
function regSzo(domen) { return { meres_kezdete: "2026-07-30", meres_vege: null, aktiv: true, domen, tipus: "szintmero", intervallumok: { "1_het": ivErvenyes(), "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }; }
const REG = { szamitva_utc: "2026-08-05T20:37:39+00:00", meredekseg_egyseg: "relatív pont / nap", irany_kuszob: 1.0, megjegyzes: "teszt", kulcsszavak: { "állás": regSzo("munkaeropiac"), "albérlet": regSzo("lakhatas"), "hitel": regSzo("lakhatas") } };
const NYERS = { kulcsszavak: { "állás": [{ kulcsszo: "állás", ablak_kezdet_utc: iso(0), ablak_veg_utc: iso(168), pontok: pontok(168) }], "albérlet": [{ kulcsszo: "albérlet", ablak_kezdet_utc: iso(0), ablak_veg_utc: iso(168), pontok: pontok(168) }], "hitel": [{ kulcsszo: "hitel", ablak_kezdet_utc: iso(0), ablak_veg_utc: iso(168), pontok: pontok(168) }] } };

async function mock_kulcsszo(page) {
  await page.route(/kulcsszo_regresszio\.json/, (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify(REG) }));
  await page.route(/kulcsszo_nyers\.json/, (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify(NYERS) }));
}

// ── G1 — render-on-load: az első (zónában lévő) kártya rendered, egy TÁVOLI (zónán kívüli) NEM (beépített nem-vacuous) ──
test("G1. render-on-load: első kulcsszó-kártya data-rendered=true 360x640-en (rootMargin:400 zóna lefedi ~708px), egy TÁVOLI kártya NEM", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 });
  await mock_kulcsszo(page);
  await page.goto("/");
  const kartyak = page.locator("#kulcsszo-blokk .kulcsszo-chart");
  await expect(kartyak).toHaveCount(3);
  await page.evaluate(() => window.scrollTo(0, 0));
  // POZITÍV: az első kártya (~708px) a rootMargin:400 zónán (alja 1040) BELÜL → rajzolódik load-kor
  await expect(kartyak.first()).toHaveAttribute("data-rendered", "true");
  // NEGATÍV (beépített nem-vacuous bizonyíték): a TÁVOLI (utolsó, ~1506px) kártya a zónán KÍVÜL → NEM rajzolódik.
  // Ha a data-rendered eagerly kerülne fel (canvas-tautológia), ez is "true" lenne → a teszt bukna.
  await expect(kartyak.last()).not.toHaveAttribute("data-rendered", "true");
});
