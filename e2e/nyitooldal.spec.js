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

const EL_REGGEL = { nap: "2026-10-10", mode: "reggel", felkapott: {
  top: [{ kifejezes: "időjárás", volumen: "100000" }, { kifejezes: "andoni iraola" }, { kifejezes: "atomerőmű" },
        { kifejezes: "" }, { kifejezes: "farm vip 2026" }, { kifejezes: "galavízió" }],
  reggel: { szoveg: "Ma reggel az időjárás viszi a prímet. Mögötte több hír áll." },
  este: { szoveg: "Ez a rész az esti futáskor (21:00) frissül." } } };

test("nyitóoldal: mai kiemelt reggel — vezető mondat + top chipek (üres kifejezés kiszűrve)", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: EL_REGGEL }));
  await page.goto("/index.html");
  await expect(page.locator("#nyitooldal-kiemelt")).toContainText("Mai kiemelt");
  await expect(page.locator("#nyitooldal-kiemelt .nyitooldal-kiemelt-mondat")).toHaveText("Ma reggel az időjárás viszi a prímet.");
  await expect(page.locator("#nyitooldal-kiemelt .nyitooldal-chip")).toHaveCount(5);   // a 6-ból az üres kifejezés kiesik
  await expect(page.locator("#nyitooldal-kiemelt .nyitooldal-chip").first()).toHaveText("időjárás");
  await expect(page.locator('#nyitooldal-kiemelt a[href="elemzes.html"]')).toBeVisible();
});

test("nyitóoldal: este módban placeholder esti szöveg → a reggeli narratívára esik vissza", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: {
    nap: "2026-10-10", mode: "este",
    felkapott: { top: [{ kifejezes: "benzin" }], reggel: { szoveg: "Reggeli vezető mondat. Folytatás." },
                 este: { szoveg: "Ez a rész az esti futáskor (21:00) frissül." } } } }));
  await page.goto("/index.html");
  await expect(page.locator("#nyitooldal-kiemelt .nyitooldal-kiemelt-mondat")).toHaveText("Reggeli vezető mondat.");
});

test("nyitóoldal: mai kiemelt fail-soft — 404 esetén üres kiemelt, de a kártyák + Infó megmaradnak", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/index.html");
  await expect(page.locator("#nyitooldal-kiemelt")).toBeEmpty();
  await expect(page.locator(".nyitooldal-kartya")).toHaveCount(3);
  await expect(page.locator('.nyitooldal-info-sav[href="adatokrol.html"]')).toBeVisible();
});

test("nyitóoldal: mai kiemelt fail-soft — elemzes.json van, de nincs felkapott kulcs", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: { nap: "2026-10-10", mode: "reggel" } }));
  await page.goto("/index.html");
  await expect(page.locator("#nyitooldal-kiemelt")).toBeEmpty();
  await expect(page.locator(".nyitooldal-kartya")).toHaveCount(3);
});
