const { test, expect } = require("@playwright/test");

const SZUNET = { szunetel: { napi: true, heti: true, havi: true, ugyek: true }, ota: "2026-11-18",
  uzenet: "Az AI által generált elemzések készítése jelenleg szünetel." };

for (const [lap, nev] of [["elemzes", "napi elemzés"], ["heti", "heti értékelés"], ["havi", "havi elemzés"], ["ugyek", "ügy-elemzés"]]) {
  test(`${lap}: szüneteltetéskor a fejléc alatt jelzősáv, a tartalom-konténer megmarad`, async ({ page }) => {
    await page.route("**/data/ai_szunet.json", (r) => r.fulfill({ json: SZUNET }));
    await page.goto(`/${lap}.html`);
    const sav = page.locator("header.fejlec-doboz + #ai-szunet-sav");
    await expect(sav).toBeVisible();
    await expect(sav).toContainText(`Az AI által generált ${nev} készítése jelenleg szünetel (2026. november 18. óta)`);
    await expect(page.locator(`main#${lap === "ugyek" ? "bovites" : lap}`)).toBeAttached();
  });

  test(`${lap}: nincs szünet / hiányzó fájl → nincs sáv`, async ({ page }) => {
    await page.route("**/data/ai_szunet.json", (r) => r.fulfill({ status: 404, body: "" }));
    await page.goto(`/${lap}.html`);
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#ai-szunet-sav")).toHaveCount(0);
  });
}

test("nyitóoldal: szüneteltetéskor sáv az üzenettel, a mai kiemelt elrejtve", async ({ page }) => {
  await page.route("**/data/ai_szunet.json", (r) => r.fulfill({ json: SZUNET }));
  await page.goto("/index.html");
  await expect(page.locator("#ai-szunet-sav")).toContainText("Az AI által generált elemzések készítése jelenleg szünetel. Szünetel 2026. november 18. óta.");
  await expect(page.locator("#nyitooldal-kiemelt")).toBeHidden();
});

test("élő adatfájl: mindhárom elemzés szünetel → a napi lapon látszik a sáv", async ({ page }) => {
  await page.goto("/elemzes.html");
  await expect(page.locator("#ai-szunet-sav")).toContainText("szünetel");
});
