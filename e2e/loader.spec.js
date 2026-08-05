const { test, expect } = require("@playwright/test");

// Task 5 adatbetöltő réteg — a HIBAKEZELÉS VISELKEDÉSÉT igazolja (nem a mai fájlhiányt).
// Az 1-3. teszt page.route()-tal MOCKOLJA a kulcsszo_regresszio.json 404-et, hogy a fájl
// tényleges létezésétől függetlenül a hibaágat vizsgálja (ma is, holnap is ugyanaz).
// A 4. (cache-busting) valós adaton fut — az minden data-kérésre igaz.

// a kulcsszo_regresszio.json-t 404-re kényszeríti (a ?v= query is illeszkedik); a többi átmegy
async function mock_regresszio_404(page) {
  await page.route(/kulcsszo_regresszio\.json/, function (route) {
    route.fulfill({ status: 404, contentType: "text/plain", body: "Not Found" });
  });
}

test("hiányzó kulcsszo_regresszio.json → MEGNEVEZETT magyar hiba a #kulcsszo-blokk-ban", async ({ page }) => {
  await mock_regresszio_404(page);
  await page.goto("/");
  const hiba = page.locator("#kulcsszo-blokk .hiba");
  await expect(hiba).toContainText("Hiba az adat betöltésekor");
  await expect(hiba).toContainText("kulcsszo_regresszio.json"); // a hibaüzenet megnevezi a fájlt
});

test("a hiba KÜLÖN gyerek-elem — a #kulcsszo-blokk többi tartalma megmarad", async ({ page }) => {
  await mock_regresszio_404(page);
  await page.goto("/");
  await expect(page.locator("#kulcsszo-blokk .hiba")).toBeVisible();          // van hiba-elem
  await expect(page.locator("#kulcsszo-blokk h2")).toHaveText("Kulcsszavak"); // az eredeti tartalom NEM tűnt el
});

test("blokkonkénti izoláció — a #trend-blokk-ban NINCS hiba", async ({ page }) => {
  await mock_regresszio_404(page);
  await page.goto("/");
  await expect(page.locator("#kulcsszo-blokk .hiba")).toBeVisible(); // a kulcsszó-blokk hibázik (mockolt 404)...
  await expect(page.locator("#trend-blokk .hiba")).toHaveCount(0);   // ...de a trend-blokk NEM (legfrissebb + napok/index betölt)
});

test("cache-busting — minden data-kérés tartalmaz ?v= paramétert (valós adaton)", async ({ page }) => {
  const data_keresek = [];
  page.on("request", function (req) {
    if (req.url().includes("/data/")) data_keresek.push(req.url());
  });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  expect(data_keresek.length).toBeGreaterThan(0);
  for (const url of data_keresek) {
    expect(url).toContain("?v=");
  }
});
