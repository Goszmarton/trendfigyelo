const { test, expect } = require("@playwright/test");

// Minimál smoke: a kiszolgált oldal betölt, és a főcím látszik.
// (A Task 5 loader-smoke és a Task 6 vezérlő-smoke-ok külön lépésben jönnek.)
test("az oldal betölt és a főcím látszik", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toHaveText("Google Trendek – Mire keresnek rá Magyarországon?");
});
