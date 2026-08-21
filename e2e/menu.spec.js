const { test, expect } = require("@playwright/test");

// Menüsor (Excel-fül) + „Az adatokról" külön oldal — statikus szerkezet-őr (nincs adat-mock, a nav statikus).
test("menüsor: 2 fül, aktív = Trendek; a linkek helyesek", async ({ page }) => {
  await page.goto("/");
  const linkek = page.locator("#fomenu a");
  await expect(linkek).toHaveCount(2);
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Trendek");
  await expect(page.locator('#fomenu a[href="adatokrol.html"]')).toHaveText("Az adatokról");
  await expect(page.locator("#labresz")).toBeAttached();          // üres lábléc jelen
  await expect(page.locator("#adatokrol")).toHaveCount(0);        // az infó-tartalom NEM a főoldalon van
});

test("Az adatokról oldal: tematikus dobozok + aktív fül + üres lábléc", async ({ page }) => {
  await page.goto("/adatokrol.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Az adatokról");
  await expect(page.locator("#adatokrol .adat-doboz")).toHaveCount(8);   // 8 tematikus egység
  await expect(page.locator("#adatokrol")).toContainText("Google Trends");
  await expect(page.locator("#adatokrol")).toContainText("52 hét heti mediánjához");   // tüntetés-medián
  await expect(page.locator("#labresz")).toBeAttached();
});

test("navigáció: a Trendek főoldalról az Az adatokról oldalra és vissza", async ({ page }) => {
  await page.goto("/");
  await page.locator('#fomenu a[href="adatokrol.html"]').click();
  await expect(page).toHaveURL(/adatokrol\.html$/);
  await expect(page.locator("#adatokrol .adat-doboz").first()).toBeVisible();
  await page.locator('#fomenu a[href="index.html"]').click();
  await expect(page).toHaveURL(/\/(index\.html)?$/);
  await expect(page.locator("#dashboard")).toBeVisible();
});
