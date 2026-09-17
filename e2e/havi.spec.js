const { test, expect } = require("@playwright/test");

test("Havi elemzés fül: klaszterek + NER + összegzés renderel", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-09"], legutolso: "2026-09" } }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: {
    honap: "2026-09", keszult: "2026-09-30T00:00:00Z", modell: "claude-opus-4-8",
    korpusz: { egyedi_szo: 2, napok: 2 },
    lemmak: [{ szo: "csalások", lemma: "csalás" }],
    ner: { orszagok: [], telepulesek: [{ nev: "Debrecen", szavak: ["debrecen időjárás"] }], szemelyek: [] },
    klaszterek: [{ cimke: "Bűnügy", szavak: ["csalás"], ertelmezes: "leírás", uralkodo_temak: [] }],
    osszegzes: "A hónap keresései…" } }));
  await page.goto("/havi.html");
  await expect(page.locator("#havi")).toContainText("Bűnügy");
  await expect(page.locator("#havi")).toContainText("Debrecen");         // NER település
  await expect(page.locator("#havi")).toContainText("csalás");           // klaszter-tag
  await expect(page.locator("#havi")).toContainText("A hónap keresései");// összegzés
});

test("Havi reorg: összegzés ELÖL, klaszterek ALUL, nincs lemma-térkép, országok volumen szerint", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-09"], legutolso: "2026-09" } }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: {
    honap: "2026-09", modell: "m", korpusz: { egyedi_szo: 3, napok: 2 },
    lemmak: [{ szo: "csalások", lemma: "csalás" }],
    ner: { orszagok: [{ nev: "Németország", szavak: ["a"], volumen: 100 },
                      { nev: "Magyarország", szavak: ["b"], volumen: 900 }],
           telepulesek: [], szemelyek: [] },
    klaszterek: [{ cimke: "Bűnügy", szavak: ["csalás"], ertelmezes: "leírás", uralkodo_temak: [], volumen: 500 }],
    osszegzes: "A hónap keresései…" } }));
  await page.goto("/havi.html");
  await expect(page.locator("#havi")).toContainText("A hónap keresései");
  // sorrend: az összegzés a klaszter-cím ELŐTT van a DOM-ban
  const cimek = await page.locator("#havi-tartalom .elemzes-csoport-cim").allTextContents();
  expect(cimek.indexOf("Összegzés")).toBeLessThan(cimek.indexOf("Témák (klaszterek)"));
  // nincs lemma-térkép
  await expect(page.locator("#havi-tartalom")).not.toContainText("lemma térkép");
  // országok volumen szerint csökkenő: Magyarország (900) a Németország (100) ELŐTT
  const orsz = await page.locator("#havi-tartalom .havi-ner-csoport", { hasText: "Országok" }).innerText();
  expect(orsz.indexOf("Magyarország")).toBeLessThan(orsz.indexOf("Németország"));
});

test("Havi barchartok: személy-barchart (top N, nincs '— szavak') + klaszter-eloszlás", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-09"], legutolso: "2026-09" } }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: {
    honap: "2026-09", modell: "m", korpusz: { egyedi_szo: 3, napok: 2 }, lemmak: [],
    ner: { orszagok: [], telepulesek: [],
           szemelyek: [{ nev: "Orbán Viktor", szavak: ["orbán viktor kötcse"], volumen: 900 },
                       { nev: "Magyar Péter", szavak: ["magyar péter"], volumen: 400 }] },
    klaszterek: [{ cimke: "Sport", szavak: ["foci"], ertelmezes: "s", uralkodo_temak: [], volumen: 700 },
                 { cimke: "Bűnügy", szavak: ["csalás"], ertelmezes: "b", uralkodo_temak: [], volumen: 300 }],
    osszegzes: "össz" } }));
  await page.goto("/havi.html");
  await expect(page.locator("#havi-szemely-chart")).toHaveCount(1);        // személy-barchart canvas
  await expect(page.locator("#havi-klaszter-chart")).toHaveCount(1);       // klaszter-eloszlás canvas
  // a személy neve megvan, de a kötött szó („— szavak") NEM jelenik meg a szekcióban
  const szem = await page.locator(".havi-szemely-szekcio").innerText();
  expect(szem).toContain("Orbán Viktor");
  expect(szem).not.toContain("orbán viktor kötcse");
  // a Chart-példányok léteznek és 2 személy / 2 klaszter adattal
  const adat = await page.evaluate(() => ({
    szem: (window.havi_chartok && window.havi_chartok.szemely) ? window.havi_chartok.szemely.data.labels.length : 0,
    kl: (window.havi_chartok && window.havi_chartok.klaszter) ? window.havi_chartok.klaszter.data.labels.length : 0 }));
  expect(adat.szem).toBe(2);
  expect(adat.kl).toBe(2);
});
