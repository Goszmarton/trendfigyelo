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

test("360px: nyitott fiók -> háttérre koppintás zár", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 700 });
  await page.goto("/trendek.html");
  await page.locator("#keret-menugomb").click();
  await expect(page.locator("#fomenu")).toBeVisible();
  await page.mouse.click(340, 400);
  await expect(page.locator("#fomenu")).toBeHidden();
  await expect(page.locator("#keret-menugomb")).toHaveAttribute("aria-expanded", "false");
});

test("360px: nyitott fiók -> a gomb újra kattintva zár (a gomb nincs letakarva)", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 700 });
  await page.goto("/trendek.html");
  const g = page.locator("#keret-menugomb");
  await g.click();
  await expect(page.locator("#fomenu")).toBeVisible();
  await g.click();
  await expect(page.locator("#fomenu")).toBeHidden();
  await expect(g).toHaveAttribute("aria-expanded", "false");
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

// ---- Task 4: felső sáv, állapot-pill, badge-ek ----
test("keret_ido_szoveg és keret_pill: tiszta függvények", async ({ page }) => {
  await page.goto("/trendek.html");
  const r = await page.evaluate(function () {
    const most = new Date("2026-11-28T21:30:00Z");
    const t = function (h) { return new Date(Date.parse("2026-11-28T20:00:00Z") - h * 3600000).toISOString(); };
    return [keret_ido_szoveg("2026-11-28T20:00:00Z", most), keret_ido_szoveg("2026-11-27T20:00:00Z", most),
      keret_ido_szoveg("2026-11-25T20:00:00Z", most), keret_ido_szoveg(null, most), keret_ido_szoveg("hibás", most),
      keret_pill(["2026-11-28T08:00:00Z"], new Date("2026-11-28T20:00:00Z")),
      keret_pill([t(30)], new Date("2026-11-28T20:00:00Z")), keret_pill([t(50)], new Date("2026-11-28T20:00:00Z")),
      keret_pill(["2026-11-28T08:00:00Z", null], new Date("2026-11-28T20:00:00Z"))];
  });
  expect(r.slice(0, 5)).toEqual(["ma 21:00", "tegnap 21:00", "nov. 25. 21:00", "–", "–"]);
  expect(r[5]).toEqual({ allapot: "ok", szoveg: "Gyűjtés rendben" });
  expect(r[6].allapot).toBe("figy");
  expect(r[7]).toEqual({ allapot: "hiba", szoveg: "Gyűjtés hiba" });
  expect(r[8]).toBeNull();
});

function friss(h) { return new Date(Date.now() - h * 3600000).toISOString(); }

test("trendek: pill = Gyűjtés rendben, a header első gyereke, gyűjtési idők a felső sávban", async ({ page }) => {
  await page.route("**/data/legfrissebb.json*", (r) => r.fulfill({ json: { frissitve: friss(2), top_trendek: [], trend_idosorok: [], kulcsszavak: {}, kulcsszo_osszesites: [] } }));
  await page.route("**/data/youtube_regresszio.json*", (r) => r.fulfill({ json: { szamitva_utc: friss(3), kulcsszavak: {} } }));
  await page.goto("/trendek.html");
  const pill = page.locator("header.fejlec-doboz > .keret-pill").first();
  await expect(pill).toContainText("Gyűjtés rendben");
  await expect(pill).toHaveClass(/keret-pill--ok/);
  expect(await page.evaluate(function () { return document.querySelector("header.fejlec-doboz").firstElementChild.classList.contains("keret-pill"); })).toBe(true);
  await expect(page.locator("#keret-felso")).toContainText(/Google: (ma|tegnap) \d\d:\d\d/);
  await expect(page.locator("#keret-felso")).toContainText("Statisztikák / Google");
});

test("trendek: legfrissebb.json 404 -> nincs pill, Google: –, a #kulcsszo-blokk renderel", async ({ page }) => {
  await page.route("**/data/legfrissebb.json*", (r) => r.fulfill({ status: 404, body: "nincs" }));
  await page.goto("/trendek.html");
  await expect(page.locator("#keret-felso")).toContainText("Google: –");
  await expect(page.locator(".keret-pill")).toHaveCount(0);
  await expect(page.locator("#kulcsszo-blokk")).toBeAttached();
});

test("ugyek: egyetlen .keret-pill, tartalmazza a #radar-idosav szövegét", async ({ page }) => {
  await page.route("**/data/ai_szunet.json*", (r) => r.fulfill({ json: { szunetel: { ugyek: true }, ota: "2026-11-18" } }));
  await page.route("**/data/ugyek.json*", (r) => r.fulfill({ json: { szamitva_utc: "2026-10-07T21:00:00+00:00",
    ablak: { kezdet: "2026-09-08", veg: "2026-10-07", nap: 30 }, modell: "m", ugyek: [] } }));
  await page.goto("/ugyek.html");
  await expect(page.locator(".keret-pill")).toHaveCount(1);
  await expect(page.locator(".keret-pill")).toContainText("Szünetel");
  await expect(page.locator(".keret-pill")).toContainText("Gördülő 30 napos ablak: 2026-09-08 – 2026-10-07");
  await expect(page.locator("#radar-idosav")).toContainText("Gördülő 30 napos ablak");
});

test("kapcsolodo: a #radar-idosav osztálya keret-pill, szövege változatlan", async ({ page }) => {
  await page.goto("/kapcsolodo.html");
  await expect(page.locator("#radar-idosav")).toHaveClass(/keret-pill/);
  await expect(page.locator("#radar-idosav")).not.toBeEmpty();
});

test("badge: az Ügyek link textContent akkor is 'Ügyek', ha data-badge=44", async ({ page }) => {
  const ugyek = []; for (let i = 0; i < 44; i++) ugyek.push({ nev: "u" + i, kifejezesek: [], idovonal: [] });
  await page.route("**/data/ugyek.json*", (r) => r.fulfill({ json: { ablak: { kezdet: "2026-09-08", veg: "2026-10-07", nap: 30 }, ugyek } }));
  await page.goto("/valtozasok.html");
  const l = page.locator('#fomenu a[href="ugyek.html"]');
  await expect(l).toHaveAttribute("data-badge", "44");
  expect(await l.evaluate(function (e) { return e.textContent.trim(); })).toBe("Ügyek");
});

test("badge: napi/heti/havi szünetben ⏸, a Google/YouTube statikus badge érintetlen", async ({ page }) => {
  await page.route("**/data/ai_szunet.json*", (r) => r.fulfill({ json: { szunetel: { napi: true, heti: true, havi: false }, ota: "2026-11-18" } }));
  await page.goto("/trendek.html");
  await expect(page.locator('#fomenu a[href="elemzes.html"]')).toHaveAttribute("data-badge", "⏸");
  await expect(page.locator('#fomenu a[href="havi.html"]')).not.toHaveAttribute("data-badge", /.*/);
  await expect(page.locator('#fomenu a[href="trendek.html"]')).toHaveAttribute("data-badge", /^\d+$/);
});

test("breadcrumb a heti.html-en: Elemzések / Heti", async ({ page }) => {
  await page.goto("/heti.html");
  await expect(page.locator(".keret-morzsa")).toHaveText("Elemzések / Heti");
});

// ── Task 5: komponensek (kártya, chip-sor, oldalfejléc) a Google és YouTube oldalon ──
const STAT_OLDALAK = [
  { nev: "Google", url: "/trendek.html", vez: "#intervallum-vezerlo", tartalom: "#kulcsszo-blokk" },
  { nev: "YouTube", url: "/youtube.html", vez: "#youtube-intervallum-vezerlo", tartalom: "#youtube-blokk" },
];
for (const o of STAT_OLDALAK) {
  test.describe(o.nev + " oldal komponensek", () => {
    test.use({ viewport: { width: 1280, height: 900 } });

    test("a chip-sor a saját szakasza fölött van, a gombjai egy sorban", async ({ page }) => {
      await page.goto(o.url);
      const sav = page.locator(".szekcio:has(" + o.tartalom + ") .vezerlo-sav").first();
      await expect(sav.locator("button").first()).toBeVisible();
      const sb = await sav.boundingBox();
      const tb = await page.locator(o.tartalom).boundingBox();
      expect(sb.y + sb.height).toBeLessThanOrEqual(tb.y + 1);
      const ys = await sav.locator("button").evaluateAll(function (bs) { return bs.map(function (b) { return Math.round(b.getBoundingClientRect().y); }); });
      expect(ys.length).toBeGreaterThan(1);
      expect(new Set(ys).size).toBe(1);
    });

    test("aktív intervallum-gomb kerete --akcentus", async ({ page }) => {
      await page.goto(o.url);
      const g = page.locator(o.vez + ' button[aria-pressed="true"]').first();
      await expect(g).toBeVisible();
      expect(await g.evaluate(function (e) { return getComputedStyle(e).borderTopColor; })).toBe("rgb(31, 138, 138)");
    });

    test("Tab-fókusz egy chipen: kontúr --akcentus", async ({ page }) => {
      await page.goto(o.url);
      const g = page.locator(o.vez + " button:not([disabled])").first();
      await expect(g).toBeVisible();
      await g.focus();
      await page.keyboard.press("Shift+Tab");
      await page.keyboard.press("Tab");
      const c = await g.evaluate(function (e) { const s = getComputedStyle(e); return [s.outlineColor, s.outlineStyle]; });
      expect(c[0]).toBe("rgb(31, 138, 138)");
      expect(c[1]).not.toBe("none");
    });

    test("h1 30px / 800", async ({ page }) => {
      await page.goto(o.url);
      const s = await page.locator("h1").first().evaluate(function (e) { const c = getComputedStyle(e); return [c.fontSize, c.fontWeight]; });
      expect(s).toEqual(["30px", "800"]);
    });
  });
}

test("a kulcsszó-kártya 12px sarok, fehér, --keret keret", async ({ page }) => {
  await mockKulcsszo(page);
  await page.goto("/trendek.html");
  const k = page.locator("#kulcsszo-blokk .kulcsszo-chart").first();
  await expect(k).toBeVisible();
  const s = await k.evaluate(function (e) { const c = getComputedStyle(e); return [c.borderTopLeftRadius, c.backgroundColor, c.borderTopColor]; });
  expect(s).toEqual(["12px", "rgb(255, 255, 255)", "rgb(226, 229, 227)"]);
});

test("hosszú felkapott kifejezés nem lóg ki a trendkártyából", async ({ page }) => {
  const hosszu = "hosszúkifejezés".repeat(6).slice(0, 80);
  await page.route(/kategoriak\.json/, (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: [] }) }));
  await page.route(/napok\/index\.json/, (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: [] }) }));
  await page.route(/legfrissebb\.json/, (r) => r.fulfill({ contentType: "application/json", body: JSON.stringify({
    top_trendek: [{ kifejezes: hosszu, volumen: "5000", novekedes_pct: "100", idosor: [], hirek: [], temak: ["Other"], topics: [1] }] }) }));
  await page.goto("/trendek.html");
  const k = page.locator("#trend-blokk .trend-kartya").first();
  await expect(k).toBeVisible({ timeout: 8000 });
  const m = await k.evaluate(function (e) { return [e.scrollWidth, e.clientWidth]; });
  expect(m[0]).toBeLessThanOrEqual(m[1]);
});

// ── Task 6: Elemzések, Áttekintő, Infó ──
test("index.html: a 3 .nyitooldal-kartya egy rácsban (azonos y), 12px sarok", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/index.html");
  const k = page.locator(".nyitooldal-kartya");
  await expect(k).toHaveCount(3);
  const ys = [];
  for (let i = 0; i < 3; i++) ys.push((await k.nth(i).boundingBox()).y);
  expect(ys[1]).toBe(ys[0]);
  expect(ys[2]).toBe(ys[0]);
  const s = await k.first().evaluate(function (e) { const c = getComputedStyle(e); return [c.borderTopLeftRadius, c.borderTopColor]; });
  expect(s).toEqual(["12px", "rgb(226, 229, 227)"]);
});

for (const u of ["/elemzes.html", "/heti.html", "/havi.html"]) {
  test("a .ai-szunet-sav a --figy tónusú és a header után áll: " + u, async ({ page }) => {
    await page.route("**/data/ai_szunet.json*", (r) => r.fulfill({ json: { szunetel: { napi: true, heti: true, havi: true }, ota: "2026-11-18" } }));
    await page.goto(u);
    const sav = page.locator("header.fejlec-doboz + #ai-szunet-sav");
    await expect(sav).toHaveCount(1);
    const s = await sav.evaluate(function (e) { const c = getComputedStyle(e); return [c.backgroundColor, c.borderLeftColor]; });
    expect(s[0]).toBe("rgba(217, 162, 27, 0.12)");
    expect(s[1]).toBe("rgb(217, 162, 27)");
  });
}

test("havi: a térkép-konténer kártya-kerettel, a #ef6c33 jelölő megvan", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-09"], legutolso: "2026-09" } }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: {
    honap: "2026-09", modell: "m", korpusz: { egyedi_szo: 3, napok: 2 }, lemmak: [],
    ner: { orszagok: [{ nev: "Németország", szavak: ["a"], volumen: 100 }],
           telepulesek: [{ nev: "Berlin", szavak: ["b"], volumen: 50 }], szemelyek: [] },
    klaszterek: [], osszegzes: "x" } }));
  await page.goto("/havi.html");
  const t = page.locator("#havi-vilag-terkep.leaflet-container");
  await expect(t).toHaveCount(1);
  const s = await t.evaluate(function (e) { const c = getComputedStyle(e); return [c.borderTopLeftRadius, c.borderTopColor]; });
  expect(s).toEqual(["12px", "rgb(226, 229, 227)"]);
  await expect(page.locator('#havi-vilag-terkep path.leaflet-interactive[fill="#ef6c33"]').first()).toBeVisible();
});

test("a naptár nap-cella érintési célmérete >= 24px (elemzés, heti)", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  for (const u of ["/elemzes.html", "/heti.html"]) {
    await page.goto(u);
    const c = page.locator(".nap-cella:not([disabled])").first();
    await expect(c).toBeVisible();
    const bb = await c.boundingBox();
    expect(bb.height).toBeGreaterThanOrEqual(24);
    expect(bb.width).toBeGreaterThanOrEqual(24);
  }
});

test("Infó: .adat-doboz 12px sarok, --keret keret; a kiválasztott nap --akcentus", async ({ page }) => {
  await page.goto("/adatokrol.html");
  const s = await page.locator(".adat-doboz").first().evaluate(function (e) { const c = getComputedStyle(e); return [c.borderTopLeftRadius, c.borderTopColor]; });
  expect(s).toEqual(["12px", "rgb(226, 229, 227)"]);
  await page.goto("/elemzes.html");
  const v = page.locator(".nap-cella.valasztott").first();
  await expect(v).toBeVisible();
  expect(await v.evaluate(function (e) { return getComputedStyle(e).backgroundColor; })).toBe("rgb(31, 138, 138)");
});

test("valtozasok: az elmozdulás-tételek kártyák (12px), az irány-jel ▲ zöld, ▼ piros", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ json: { szamitva_utc: "2026-10-07T18:00:00+00:00",
    kulcsszavak: {
      benzin: { szokatlan: true, irany: "emelkedik", elteres: 3.0, idotartam_pont: 5, megbizhatosag: "magas", sav: {} },
      iskola: { szokatlan: true, irany: "csokken", elteres: 2.0, idotartam_pont: 3, megbizhatosag: "kozepes", sav: {} } },
    szokatlan_lista: ["benzin", "iskola"] } }));
  await page.goto("/valtozasok.html");
  const k = page.locator(".bovites-elm-kartya");
  await expect(k).toHaveCount(2);
  const s = await k.first().evaluate(function (e) { const c = getComputedStyle(e); return [c.borderTopLeftRadius, c.borderTopColor]; });
  expect(s).toEqual(["12px", "rgb(226, 229, 227)"]);
  const jel = function (sel) { return page.locator(sel + " .bovites-elm-irany").evaluate(function (e) {
    const c = getComputedStyle(e, "::before"); return [c.content, c.color]; }); };
  expect(await jel(".bovites-irany-emelkedik")).toEqual(['"▲"', "rgb(46, 139, 87)"]);
  expect(await jel(".bovites-irany-csokken")).toEqual(['"▼"', "rgb(200, 65, 75)"]);
});

test("ugyek: a 120 karakteres ügycím tördelődik, nem lóg ki a kártyából", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  const hosszu = "Hosszúhosszú".repeat(10);
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ json: { szamitva_utc: "2026-10-07T21:00:00+00:00",
    ablak: { kezdet: "2026-09-08", veg: "2026-10-07", nap: 30 }, modell: "m",
    ugyek: [{ nev: hosszu, szakpolitika: "energia_rezsi", eletut: "folyamatosan_jelenlevo", mozgas: "stabil",
      kifejezesek: [hosszu], elso_nap: "2026-09-10", utolso_nap: "2026-10-07", napok_szama: 1,
      idovonal: [{ nap: "2026-09-10", jelen: true, ossz_volumen: 40 }], osszefoglalo: "x" }] } }));
  await page.goto("/ugyek.html");
  await expect(page.locator(".bovites-ugy")).toHaveCount(1);
  const r = await page.evaluate(function () {
    const k = document.querySelector(".bovites-ugy"), n = document.querySelector(".bovites-ugy-nev");
    return { radius: getComputedStyle(k).borderTopLeftRadius, kSw: k.scrollWidth, kCw: k.clientWidth,
      nR: n.getBoundingClientRect().right, kR: k.getBoundingClientRect().right, doc: document.documentElement.scrollWidth };
  });
  expect(r.radius).toBe("12px");
  expect(r.nR).toBeLessThanOrEqual(r.kR);
  expect(r.kSw).toBeLessThanOrEqual(r.kCw);
  expect(r.doc).toBeLessThanOrEqual(390);
});

test("kapcsolodo: a szűrő-gombok chip-stílusúak, a kapcsolódó chipek/kártya is", async ({ page }) => {
  await page.goto("/ugyek.html");
  const g = page.locator(".bovites-szuro-chip");
  await expect(g.first()).toBeVisible();
  const s = await g.nth(1).evaluate(function (e) { const c = getComputedStyle(e); return [c.borderTopLeftRadius, c.borderTopColor]; });
  expect(s).toEqual(["999px", "rgb(226, 229, 227)"]);
  const a = await g.first().evaluate(function (e) { const c = getComputedStyle(e); return [c.backgroundColor, c.borderTopColor]; });
  expect(a).toEqual(["rgb(227, 244, 241)", "rgb(31, 138, 138)"]);
  await page.route("**/data/kapcsolodo.json", (r) => r.fulfill({ json: { frissitve: "2026-10-07T21:00:00+00:00", kifejezesek: [
    { kifejezes: "benzin", lekerdezve: "2026-10-07T21:00:00+00:00", volumen: 90,
      top: [{ query: "benzin ár", value: 100 }], rising: [{ query: "benzin ársapka", value: 8350 }] }] } }));
  await page.goto("/kapcsolodo.html");
  const c = await page.locator(".bovites-chip").first().evaluate(function (e) { const c = getComputedStyle(e); return [c.borderTopLeftRadius, c.borderTopColor]; });
  expect(c).toEqual(["999px", "rgb(226, 229, 227)"]);
  expect(await page.locator(".bovites-kapcs-kartya").first().evaluate(function (e) { return getComputedStyle(e).borderTopLeftRadius; })).toBe("12px");
});
