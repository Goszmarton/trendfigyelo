const { test, expect } = require("@playwright/test");

const UGY = { szamitva_utc: "2026-10-07T21:00:00+00:00", ablak: { kezdet: "2026-09-08", veg: "2026-10-07", nap: 30 },
  modell: "claude-opus-4-8", ugyek: [
    { nev: "Üzemanyagárak", szakpolitika: "energia_rezsi", eletut: "folyamatosan_jelenlevo", mozgas: "erosodo",
      kifejezesek: ["benzin ára", "gázolaj"], elso_nap: "2026-09-10", utolso_nap: "2026-10-07", napok_szama: 12,
      idovonal: [{ nap: "2026-09-10", jelen: true, ossz_volumen: 40 }, { nap: "2026-10-07", jelen: true, ossz_volumen: 70 }],
      osszefoglalo: "Az üzemanyagárak tartósan foglalkoztatják a keresőket." },
    { nev: "Iskolakezdés", szakpolitika: "oktataspolitika", eletut: "visszatero", mozgas: "stabil",
      kifejezesek: ["iskola"], elso_nap: "2026-09-10", utolso_nap: "2026-10-01", napok_szama: 4,
      idovonal: [{ nap: "2026-09-10", jelen: true, ossz_volumen: 20 }], osszefoglalo: "y" }] };

test("ügyek: renderel + idősáv (gördülő 30 nap) + szűrő + rendezés + idővonal", async ({ page }) => {
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ json: UGY }));
  await page.goto("/ugyek.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Ügyek");
  await expect(page.locator("#radar-idosav")).toContainText("Gördülő 30 napos ablak: 2026-09-08 – 2026-10-07");
  await expect(page.locator(".bovites-ugy")).toHaveCount(2);
  await expect(page.locator("#bovites-ugyek")).toContainText("Üzemanyagárak");
  // idővonal
  const kartya = page.locator(".bovites-ugy").first();
  await expect(kartya.locator(".bovites-idovonal-cim")).toContainText("Napi jelenlét");
  await expect(kartya.locator(".bovites-idovonal .bovites-nap").first()).toHaveAttribute("style", /rgba\(42, 120, 214/);
  // szűrő + rendezés
  await page.locator('#bovites-szuro-ugy .bovites-szuro-chip[data-szakpolitika="oktataspolitika"]').click();
  await expect(page.locator(".bovites-ugy")).toHaveCount(1);
  await expect(page.locator("#bovites-ugyek")).toContainText("Iskolakezdés");
  await page.locator('#bovites-szuro-ugy .bovites-szuro-chip[data-szakpolitika=""]').click();
  await expect(page.locator(".bovites-ugy")).toHaveCount(2);
  await page.locator('#bovites-szuro-ugy .bovites-rendezes-gomb[data-rendezes="frissesseg"]').click();
  await expect(page.locator(".bovites-ugy-nev").first()).toHaveText("Üzemanyagárak");
});

test("ügyek: fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/ugyek.html");
  await expect(page.locator("#bovites-ugyek")).toContainText("nem érhető el");
  await expect(page.locator("#radar-idosav")).toBeEmpty();
});
