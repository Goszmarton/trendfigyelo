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
  await expect(page.locator("#havi-hu-terkep.leaflet-container")).toHaveCount(1); // NER település → térkép
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
  expect(cimek.indexOf("Összegzés")).toBeLessThan(cimek.indexOf("Tematikus besorolás"));
  // nincs lemma-térkép
  await expect(page.locator("#havi-tartalom")).not.toContainText("lemma térkép");
  // az „Országok" lista HELYETT a világtérkép jelenik meg (a volumen szerinti szinezést/rendezést
  // a dedikált világtérkép-teszt fedi le)
  await expect(page.locator("#havi-tartalom .havi-ner-csoport", { hasText: "Országok" })).toHaveCount(0);
  await expect(page.locator("#havi-vilag-terkep.leaflet-container")).toHaveCount(1);
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

test("Havi hónap-naptár: index.json-ból gombok + ?honap= URL-param a kezdő hónap", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-08", "2026-09"], legutolso: "2026-09" } }));
  const art = (h) => ({ honap: h, modell: "m", korpusz: { egyedi_szo: 1, napok: 1 }, lemmak: [],
    ner: { orszagok: [], telepulesek: [], szemelyek: [] }, klaszterek: [], osszegzes: "össz-" + h });
  await page.route("**/data/havi_nlp/2026-08.json", r => r.fulfill({ json: art("2026-08") }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: art("2026-09") }));
  // ?honap=2026-08 → a 2026-08 töltődik be
  await page.goto("/havi.html?honap=2026-08");
  await expect(page.locator("#havi-tartalom")).toContainText("össz-2026-08");
  await expect(page.locator("#havi-honap-panel .havi-honap-gomb")).toHaveCount(2);   // két hónap-gomb
  // kattintás a 2026-09-re → átvált
  await page.locator('#havi-honap-panel .havi-honap-gomb[data-honap="2026-09"]').click();
  await expect(page.locator("#havi-tartalom")).toContainText("össz-2026-09");
});

test("Havi világtérkép: ország-choropleth + külföldi város-jelölő + kattintás→szavak", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-09"], legutolso: "2026-09" } }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: {
    honap: "2026-09", modell: "m", korpusz: { egyedi_szo: 3, napok: 2 }, lemmak: [],
    ner: { orszagok: [{ nev: "Magyarország", szavak: ["magyar hír"], volumen: 900 },
                      { nev: "Németország", szavak: ["német hír"], volumen: 100 }],
           telepulesek: [{ nev: "Moszkva", szavak: ["moszkva hír"], volumen: 250 }],
           szemelyek: [] },
    klaszterek: [], osszegzes: "össz" } }));
  await page.goto("/havi.html");
  // a térkép-konténer maga kapja a Leaflet-DOM-osztályt (L.map a doboz elemre inicializál, nem beágyazva)
  await expect(page.locator("#havi-vilag-terkep.leaflet-container")).toHaveCount(1);
  // legalább egy ország-choropleth path (a szin_skala hsl(212,…) kitöltéssel)
  const orszagPath = page.locator('#havi-vilag-terkep path.leaflet-interactive[fill^="hsl(212"]').first();
  await expect(orszagPath).toBeVisible();
  // legalább egy külföldi-város kör-jelölő (a vörös fillColor #e74c3c)
  const varosMarker = page.locator('#havi-vilag-terkep path.leaflet-interactive[fill="#e74c3c"]').first();
  await expect(varosMarker).toBeVisible();
  // kattintás egy országra → a hozzá kötött szavak megjelennek a .havi-terkep-szavak dobozban
  // (közvetlen testvér-szűkítés szükséges, mert a Magyarország-térkép is kap saját
  // .havi-terkep-szavak dobozt — a Playwright :has(#id) szelektor ID-t dokumentum-szinten oldja
  // fel, nem a jelölt elemre szűkítve, ezért azt itt szándékosan kerüljük)
  const vilagSzavak = page.locator("#havi-vilag-terkep").locator("xpath=following-sibling::div[contains(@class,'havi-terkep-szavak')]");
  await orszagPath.click();
  await expect(vilagSzavak).toContainText("hír");
  // kattintás a városra → a hozzá kötött szavak megjelennek
  await varosMarker.click();
  await expect(vilagSzavak).toContainText("moszkva hír");
});

test("Havi Magyarország-térkép: magyar településjelölő + hover + kattintás→szavak", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-09"], legutolso: "2026-09" } }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: {
    honap: "2026-09", modell: "m", korpusz: { egyedi_szo: 3, napok: 2 }, lemmak: [],
    ner: { orszagok: [],
           telepulesek: [{ nev: "Debrecen", szavak: ["debrecen időjárás"], volumen: 400 }],
           szemelyek: [] },
    klaszterek: [], osszegzes: "össz" } }));
  await page.goto("/havi.html");
  // a Magyarország-térkép konténere maga kapja a Leaflet-DOM-osztályt
  await expect(page.locator("#havi-hu-terkep.leaflet-container")).toHaveCount(1);
  // az „Országok" listát felváltó világtérkép mellett a Települések-lista HELYETT a Magyarország-térkép jelenik meg
  await expect(page.locator("#havi-tartalom .havi-ner-csoport", { hasText: "Települések" })).toHaveCount(0);
  // megyehatár-alapréteg jelen van: a vendorelt megye-GeoJSON 20 külön feature-t rajzol
  // (stroke="#999"), ez megkülönbözteti az egyetlen HUN-körvonal fallback-től (stroke="#888")
  const megyePaths = page.locator('#havi-hu-terkep path[stroke="#999"]');
  await expect(megyePaths).not.toHaveCount(0);
  const megyeSzam = await megyePaths.count();
  expect(megyeSzam).toBeGreaterThan(1);
  // legalább egy magyar település kör-jelölő
  const varosMarker = page.locator('#havi-hu-terkep path.leaflet-interactive').first();
  await expect(varosMarker).toBeVisible();
  // kattintás a településre → a hozzá kötött szavak megjelennek
  // (közvetlen testvér-szűkítés szükséges, mert a Világtérkép is kap saját .havi-terkep-szavak dobozt)
  await varosMarker.click();
  const huSzavak = page.locator("#havi-hu-terkep").locator("xpath=following-sibling::div[contains(@class,'havi-terkep-szavak')]");
  await expect(huSzavak).toContainText("debrecen időjárás");
});

test("Havi térkép jelmagyarázat + nem-illeszthető nevek fallback-lista (grounding/a11y)", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-09"], legutolso: "2026-09" } }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: {
    honap: "2026-09", modell: "m", korpusz: { egyedi_szo: 3, napok: 2 }, lemmak: [],
    ner: { orszagok: [{ nev: "Magyarország", szavak: ["magyar hír"], volumen: 900 },
                      { nev: "Seholország", szavak: ["seholország hír"], volumen: 42 }],
           telepulesek: [{ nev: "Debrecen", szavak: ["debrecen időjárás"], volumen: 400 },
                         { nev: "Sehol-falva", szavak: ["sehol-falva hír"], volumen: 17 }],
           szemelyek: [] },
    klaszterek: [], osszegzes: "össz" } }));
  await page.goto("/havi.html");
  await expect(page.locator("#havi-vilag-terkep.leaflet-container")).toHaveCount(1);
  await expect(page.locator("#havi-hu-terkep.leaflet-container")).toHaveCount(1);
  // jelmagyarázat mindkét térkép alatt
  await expect(page.locator(".havi-terkep-jelmagyarazat")).toHaveCount(2);
  // világtérkép fallback: nincs ISO-match ("Seholország") ÉS nincs koordináta ("Sehol-falva" — se HU, se külföldi város)
  const vilagFallback = page.locator("#havi-vilag-terkep").locator(
    "xpath=following-sibling::*[contains(@class,'havi-terkep-fallback')][1]");
  await expect(vilagFallback).toContainText("Seholország");
  await expect(vilagFallback).toContainText("42");
  await expect(vilagFallback).toContainText("Sehol-falva");
  await expect(vilagFallback).toContainText("17");
  // HU-térkép fallback: ugyanaz a "Sehol-falva" NEM ismétlődik meg (se HU, se varos koord → csak a világ-fallback-ban)
  const huFallback = page.locator("#havi-hu-terkep").locator(
    "xpath=following-sibling::*[contains(@class,'havi-terkep-fallback')][1]");
  await expect(huFallback).toHaveCount(0);
  // Debrecen (van HU-koord) NEM jelenik meg egyik fallback-listában sem
  await expect(page.locator(".havi-terkep-fallback")).not.toContainText("Debrecen");
});

test("Havi geo-asset betöltési hiba: fail-soft — a térképek listára esnek vissza, a fül többi része renderel", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-09"], legutolso: "2026-09" } }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: {
    honap: "2026-09", modell: "m", korpusz: { egyedi_szo: 3, napok: 2 }, lemmak: [],
    ner: { orszagok: [{ nev: "Magyarország", szavak: ["magyar hír"], volumen: 900 }],
           telepulesek: [{ nev: "Debrecen", szavak: ["debrecen időjárás"], volumen: 400 }],
           szemelyek: [{ nev: "Orbán Viktor", szavak: ["orbán viktor"], volumen: 900 }] },
    klaszterek: [{ cimke: "Sport", szavak: ["foci"], ertelmezes: "s", uralkodo_temak: [], volumen: 700 }],
    osszegzes: "A hónap keresései…" } }));
  await page.route("**/vendor/geo/**", r => r.fulfill({ status: 404, body: "nem elérhető" }));
  await page.goto("/havi.html");
  // a térképek NEM inicializálódnak (geo-asset hiányzik) — a Fázis A listákra esünk vissza
  await expect(page.locator("#havi-vilag-terkep")).toHaveCount(0);
  await expect(page.locator("#havi-hu-terkep")).toHaveCount(0);
  await expect(page.locator("#havi-tartalom .havi-ner-csoport", { hasText: "Országok" })).toHaveCount(1);
  await expect(page.locator("#havi-tartalom .havi-ner-csoport", { hasText: "Települések" })).toHaveCount(1);
  // a fül többi része (összegzés, személy-barchart, klaszter) VÁLTOZATLANUL renderel
  await expect(page.locator("#havi")).toContainText("A hónap keresései");
  await expect(page.locator("#havi-szemely-chart")).toHaveCount(1);
  await expect(page.locator("#havi-klaszter-chart")).toHaveCount(1);
  await expect(page.locator("#havi")).toContainText("Sport");
});

test("Havi csiszolás: jobb szekció-címek + kék-csíkos infók + klaszter-kártya szöveg-elöl sorrend", async ({ page }) => {
  await page.route("**/data/havi_nlp/index.json", r => r.fulfill({ json: { honapok: ["2026-09"], legutolso: "2026-09" } }));
  await page.route("**/data/havi_nlp/2026-09.json", r => r.fulfill({ json: {
    honap: "2026-09", modell: "m", korpusz: { egyedi_szo: 3, napok: 2 }, lemmak: [],
    ner: { orszagok: [{ nev: "Magyarország", szavak: ["magyar hír"], volumen: 900 }],
           telepulesek: [{ nev: "Debrecen", szavak: ["debrecen időjárás"], volumen: 400 }],
           szemelyek: [{ nev: "Orbán Viktor", szavak: ["orbán viktor kötcse"], volumen: 900 }] },
    klaszterek: [{ cimke: "Bűnügy", szavak: ["csalás"], ertelmezes: "leírás a témáról", uralkodo_temak: [], volumen: 500 }],
    osszegzes: "A hónap keresései…" } }));
  await page.goto("/havi.html");
  // C) NER-cím + térkép-alcímek (a "(térkép)" törölve)
  await expect(page.locator("#havi-tartalom .elemzes-csoport-cim", { hasText: "Országok és települések a havi keresésekben" })).toHaveCount(1);
  await expect(page.locator("#havi-tartalom")).toContainText("Havonta megjelent országok és nem-magyar települések a keresésekben");
  await expect(page.locator("#havi-tartalom")).toContainText("Havonta megjelent magyar települések a keresésekben");
  await expect(page.locator("#havi-tartalom")).not.toContainText("(térkép)");
  // D) Személyek-cím
  await expect(page.locator("#havi-tartalom")).toContainText("Megjelent személynevek a havi keresésekben");
  // E) Klaszterek-cím
  await expect(page.locator("#havi-tartalom .elemzes-csoport-cim", { hasText: "Tematikus besorolás" })).toHaveCount(1);
  // kék-csíkos infók: legalább 3
  const infoSzam = await page.locator("#havi-tartalom .havi-info").count();
  expect(infoSzam).toBeGreaterThanOrEqual(3);
  // F) klaszter-kártya: az ertelmezes-szöveg a tag-chipek ELŐTT áll a DOM-ban
  const sorrend = await page.locator(".havi-klaszter").first().evaluate((box) => {
    const szoveg = box.querySelector(".elemzes-szoveg");
    const chipek = box.querySelector(".havi-tag-lista");
    if (!szoveg || !chipek) return null;
    // DOCUMENT_POSITION_FOLLOWING (4) === szoveg a chipek ELŐTT van
    return !!(szoveg.compareDocumentPosition(chipek) & Node.DOCUMENT_POSITION_FOLLOWING);
  });
  expect(sorrend).toBe(true);
});
