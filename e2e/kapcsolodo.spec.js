const { test, expect } = require("@playwright/test");

const KAPCS = { frissitve: "2026-10-07T21:00:00+00:00", kifejezesek: [
  { kifejezes: "benzin", lekerdezve: "2026-10-07T21:00:00+00:00", volumen: 90,
    top: [{ query: "benzin ár", value: 100 }, { query: "mol benzin", value: 19 }],
    rising: [{ query: "benzin ársapka", value: 8350 }, { query: "hatósági áras benzin", value: "Breakout" }] }]};

test("kapcsolódó: renderel (top + rising + súgók) + idősáv (napi)", async ({ page }) => {
  await page.route("**/data/kapcsolodo.json", (r) => r.fulfill({ json: KAPCS }));
  await page.goto("/kapcsolodo.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Kapcsolódó");
  await expect(page.locator("#radar-idosav")).toContainText("Naponta frissül · utolsó: 2026-10-07");
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("benzin ár");        // top
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("benzin ársapka");    // rising
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("Breakout");
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("relatív népszerűség");
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("mennyivel nőtt");
});

test("kapcsolódó: fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/kapcsolodo.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/kapcsolodo.html");
  await expect(page.locator("#radar-idosav")).toBeEmpty();
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Kapcsolódó");
});
