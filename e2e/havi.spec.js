const { test, expect } = require("@playwright/test");

test("Havi elemzés fül: klaszterek + NER + lemma + összegzés renderel", async ({ page }) => {
  await page.route("**/data/havi_nlp/**", r => r.fulfill({ json: {
    honap: "2026-09", keszult: "2026-09-30T00:00:00Z", modell: "claude-opus-4-8",
    korpusz: { egyedi_szo: 2, napok: 2 },
    lemmak: [{ szo: "csalások", lemma: "csalás" }],
    ner: { orszagok: [], telepulesek: [{ nev: "Debrecen", szavak: ["debrecen időjárás"] }], szemelyek: [] },
    klaszterek: [{ cimke: "Bűnügy", szavak: ["csalás"], ertelmezes: "leírás", uralkodo_temak: [] }],
    osszegzes: "A hónap keresései…" } }));
  await page.goto("/havi.html");
  await expect(page.locator("#havi")).toContainText("Bűnügy");
  await expect(page.locator("#havi")).toContainText("Debrecen");         // NER település
  await expect(page.locator("#havi")).toContainText("csalás");           // klaszter-tag / lemma
  await expect(page.locator("#havi")).toContainText("A hónap keresései");// összegzés
});
