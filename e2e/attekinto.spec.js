const { test, expect } = require("@playwright/test");

test("áttekintő: nav aktív = Áttekintő, 3 kártya + Infó-belépő, helyes linkek", async ({ page }) => {
  await page.goto("/index.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Áttekintő");
  await expect(page.locator(".attekinto-kartya")).toHaveCount(3);
  await expect(page.locator(".attekinto-kartya h2")).toHaveText(["Elemzések", "Radar", "Statisztikák"]);
  // terület-linkek
  await expect(page.locator('.attekinto-kartya a[href="elemzes.html"]')).toBeVisible();
  await expect(page.locator('.attekinto-kartya a[href="heti.html"]')).toBeVisible();
  await expect(page.locator('.attekinto-kartya a[href="havi.html"]')).toBeVisible();
  await expect(page.locator('.attekinto-kartya a[href="bovites.html"]')).toBeVisible();
  await expect(page.locator('.attekinto-kartya a[href="trendek.html"]')).toBeVisible();
  await expect(page.locator('.attekinto-kartya a[href="youtube.html"]')).toBeVisible();
  // Infó-belépő a nyitóoldalon is
  await expect(page.locator('.attekinto-info-sav[href="adatokrol.html"]')).toBeVisible();
});
