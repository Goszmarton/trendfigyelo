const { test, expect } = require("@playwright/test");

// Menüsor (Excel-fül) + „Az adatokról" külön oldal — statikus szerkezet-őr (nincs adat-mock, a nav statikus).
test("menüsor: 3 fül, aktív = Trendek; a linkek helyesek", async ({ page }) => {
  await page.goto("/");
  const linkek = page.locator("#fomenu a");
  await expect(linkek).toHaveCount(3);
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Trendek");
  await expect(page.locator('#fomenu a[href="elemzes.html"]')).toHaveText("Elemzés");
  await expect(page.locator('#fomenu a[href="adatokrol.html"]')).toHaveText("Infó");
  await expect(page.locator("#labresz")).toBeAttached();          // üres lábléc jelen
  await expect(page.locator("#adatokrol")).toHaveCount(0);        // az infó-tartalom NEM a főoldalon van
});

test("Infó oldal: adat + elemzés dobozok, csoportcímek, aktív fül + üres lábléc", async ({ page }) => {
  await page.goto("/adatokrol.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Infó");
  await expect(page.locator("#adatokrol .adat-doboz")).toHaveCount(11);  // 8 adat + 3 elemzés egység
  await expect(page.locator("#adatokrol .adat-csoport")).toHaveCount(2);  // „Az adatok" + „Az elemzés" csoportcím
  await expect(page.locator("#adatokrol")).toContainText("Google Trends");
  await expect(page.locator("#adatokrol")).toContainText("52 hét heti mediánjához");   // tüntetés-medián
  // elemzés-rész: pontos, precíz — a modell és a „Python számol / AI csak szöveg" elv nevesítve
  await expect(page.locator("#adatokrol")).toContainText("claude-opus-4-8");
  await expect(page.locator("#adatokrol")).toContainText("Python");
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
