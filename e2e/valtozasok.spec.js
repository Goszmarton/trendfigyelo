const { test, expect } = require("@playwright/test");

const ELM = { szamitva_utc: "2026-10-07T18:00:00+00:00",
  kulcsszavak: { "benzin": { szokatlan: true, irany: "emelkedik", elteres: 3.0, idotartam_pont: 5,
      megbizhatosag: "magas", szakpolitika: "energia_rezsi", sav: {} },
    "iskola": { szokatlan: true, irany: "csokken", elteres: 2.0, idotartam_pont: 3,
      megbizhatosag: "kozepes", szakpolitika: "oktataspolitika", sav: {} } },
  szokatlan_lista: ["benzin", "iskola"] };

test("változások: renderel + idősáv (számítva) + szakpolitika-szűrő", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ json: ELM }));
  await page.goto("/valtozasok.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Változások");
  await expect(page.locator("#radar-idosav")).toContainText("számítva: 2026-10-07");
  await expect(page.locator("#bovites-elmozdulas")).toContainText("benzin");
  await expect(page.locator("#bovites-elmozdulas")).toContainText("emelkedik");
  await expect(page.locator(".bovites-elm-kartya")).toHaveCount(2);
  await page.locator('#bovites-szuro-elm .bovites-szuro-chip[data-szakpolitika="energia_rezsi"]').click();
  await expect(page.locator(".bovites-elm-kartya")).toHaveCount(1);
  await expect(page.locator("#bovites-elmozdulas")).toContainText("benzin");
  await expect(page.locator("#bovites-elmozdulas")).not.toContainText("iskola");
});

test("változások: fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/valtozasok.html");
  await expect(page.locator("#bovites-elmozdulas")).toContainText("nem érhető el");
  await expect(page.locator("#radar-idosav")).toBeEmpty();
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Változások");
});
