const { test, expect } = require("@playwright/test");

test("tema_szin: Google/YouTube témák és ismeretlen", async ({ page }) => {
  await page.goto("/trendek.html");
  const r = await page.evaluate(function () {
    return [tema_szin("megelhetes", "google"), tema_szin("politika", "google"),
            tema_szin("nincs_ilyen", "google"), tema_szin("egeszseg", "youtube"), tema_szin("x", "youtube")];
  });
  expect(r.map(function (s) { return s.toLowerCase(); }))
    .toEqual(["#0072b2", "#56b4e9", "#98a0a8", "#0072b2", "#98a0a8"]);
});

const KEZD = Date.parse("2026-07-29T20:00:00Z");
function iso(h) { return new Date(KEZD + h * 3600000).toISOString().replace(".000Z", "+00:00"); }

async function mockKulcsszo(page) {
  const pontok = [];
  for (let i = 0; i < 168; i++) pontok.push({ idopont_utc: iso(i), ertek: 40 + (i % 10), reszleges: false });
  pontok.push({ idopont_utc: iso(168), ertek: 0, reszleges: true });
  const iv = { ervenyes: true, meredekseg_nap: 1.5, se_meredekseg: 0.4, se_masodlagos_autokorrelacio: true,
    irany: "novekszik", r2: 0.31, r2_masodlagos_autokorrelacio: true, ablak_kezdet_utc: iso(0), ablak_veg_utc: iso(168),
    pontok_hasznalt: 168, pontok_nem_nulla: 166, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 0,
    illesztes_vonal: [{ idopont_utc: iso(0), ertek: 35 }, { idopont_utc: iso(167), ertek: 42 }] };
  const reg = { szamitva_utc: "2026-08-05T20:37:39+00:00", meredekseg_egyseg: "x", irany_kuszob: 1.0, megjegyzes: "t",
    kulcsszavak: { "teszt szó": { meres_kezdete: "2026-07-30", meres_vege: null, aktiv: true, domen: "megelhetes",
      tipus: "szintmero", intervallumok: { "1_het": iv, "2_het": { ervenyes: false, ok: "nincs_lancolas" },
        "1_ho": { ervenyes: false, ok: "nincs_lancolas" }, "3_ho": { ervenyes: false, ok: "nincs_lancolas" },
        "1_ev": { ervenyes: false, ok: "nincs_lancolas" } } } } };
  const nyers = { kulcsszavak: { "teszt szó": [{ kulcsszo: "teszt szó", ablak_kezdet_utc: iso(0), ablak_veg_utc: iso(168), pontok }] } };
  const ures = { kulcsszavak: {} };
  const rou = (re, obj) => page.route(re, (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify(obj) }));
  await rou(/kulcsszo_masodlagos_regresszio\.json/, ures);
  await rou(/kulcsszo_masodlagos_nyers\.json/, ures);
  await rou(/kulcsszo_lanc\.json/, ures);
  await rou(/kulcsszo_regresszio\.json/, reg);
  await rou(/kulcsszo_nyers\.json/, nyers);
}

test("kulcsszó-chart adatvonala a --google színű; a domén-cím előtt témaszín-pötty", async ({ page }) => {
  await mockKulcsszo(page);
  await page.goto("/trendek.html");
  await page.locator("#kulcsszo-blokk .kulcsszo-chart").first().scrollIntoViewIfNeeded();
  await page.waitForFunction(function () { return window.chart_peldanyok && !!window.chart_peldanyok["teszt szó"]; });
  const szin = await page.evaluate(function () {
    return window.chart_peldanyok["teszt szó"].data.datasets[0].borderColor;
  });
  expect(szin.toLowerCase()).toBe("#3b6fd8");
  const h3 = page.locator("#kulcsszo-blokk .domen-fejlec").first();
  await expect(h3).toHaveText("Megélhetési problémák");                       // a cím szövege változatlan
  const potty = await h3.locator(".ui-tema-potty").evaluate(function (e) { return getComputedStyle(e).backgroundColor; });
  expect(potty).toBe("rgb(0, 114, 178)");                                      // --tema-1
});

test("Chart.js alapok a tokenekből", async ({ page }) => {
  await page.goto("/trendek.html");
  const r = await page.evaluate(function () {
    return [Chart.defaults.font.family, Chart.defaults.color];
  });
  expect(r[0]).toContain("Inter");
  expect(r[1].toLowerCase()).toBe("#66707a");
});

test("vonal-paletta: nincs benne a --tema-7 (#F0E442)", async ({ page }) => {
  await page.goto("/trendek.html");
  const p = await page.evaluate(function () { return IDOSOR_PALETTA.map(function (s) { return s.toLowerCase(); }); });
  expect(p).toHaveLength(7);
  expect(p).not.toContain("#f0e442");
});

// ---- Task 3: oldalsáv + fiókmenü ----
const OLDALAK = ["index", "elemzes", "heti", "havi", "valtozasok", "ugyek", "kapcsolodo", "trendek", "youtube", "adatokrol"];

test("oldalsáv 1280px: #fomenu látható, bal oldalt, 240px, aktív link háttere", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/trendek.html");
  await expect(page.locator("#fomenu")).toBeVisible();
  const b = await page.locator(".keret-oldalsav").boundingBox();
  expect(b.x).toBeLessThan(2);
  expect(Math.abs(b.width - 240)).toBeLessThanOrEqual(2);
  const bg = await page.locator('#fomenu a[aria-current="page"]').evaluate(function (e) { return getComputedStyle(e).backgroundColor; });
  expect(bg).toBe("rgb(143, 220, 208)");
});

test("360px: #fomenu rejtett, menügomb katt -> látható, aria-expanded=true", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 700 });
  await page.goto("/trendek.html");
  await expect(page.locator("#fomenu")).toBeHidden();
  const g = page.locator("#keret-menugomb");
  await expect(g).toHaveAttribute("aria-expanded", "false");
  await g.click();
  await expect(page.locator("#fomenu")).toBeVisible();
  await expect(g).toHaveAttribute("aria-expanded", "true");
});

test("360px: document.scrollWidth <= 360 mind a 10 oldalon", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 700 });
  for (const o of OLDALAK) {
    await page.goto("/" + o + ".html");
    const w = await page.evaluate(function () { return document.documentElement.scrollWidth; });
    expect(w, o).toBeLessThanOrEqual(360);
  }
});

test("JS kikapcsolva 1280px: a 10 menülink látható", async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1280, height: 800 }, baseURL: "http://localhost:8000" });
  const p = await ctx.newPage();
  await p.goto("/trendek.html");
  await expect(p.locator("#fomenu a")).toHaveCount(10);
  for (const a of await p.locator("#fomenu a").all()) await expect(a).toBeVisible();
  await ctx.close();
});

test("Tab-bal a második menülinkre: outline színe rgb(31, 138, 138)", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/trendek.html");
  await page.locator("#fomenu a").first().focus();
  await page.keyboard.press("Tab");
  const c = await page.locator("#fomenu a").nth(1).evaluate(function (e) { return getComputedStyle(e).outlineColor; });
  expect(c).toBe("rgb(31, 138, 138)");
});
