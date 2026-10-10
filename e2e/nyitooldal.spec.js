const { test, expect } = require("@playwright/test");

test("nyitóoldal: nav aktív = Áttekintő, 3 kártya + Infó-belépő, helyes linkek", async ({ page }) => {
  await page.goto("/index.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Áttekintő");
  await expect(page.locator(".nyitooldal-kartya")).toHaveCount(3);
  await expect(page.locator(".nyitooldal-kartya h2")).toHaveText(["Elemzések", "Radar", "Statisztikák"]);
  for (const h of ["elemzes", "heti", "havi", "bovites", "trendek", "youtube"]) {
    await expect(page.locator(`.nyitooldal-kartya a[href="${h}.html"]`)).toBeVisible();
  }
  await expect(page.locator('.nyitooldal-info-sav[href="adatokrol.html"]')).toBeVisible();
});
