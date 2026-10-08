const { test, expect } = require("@playwright/test");

const ELM = { szamitva_utc: "2026-10-07T18:00:00+00:00",
  kulcsszavak: { "benzin": { szokatlan: true, irany: "emelkedik", elteres: 3.0, elteres_nyers: 12.0,
      idotartam_pont: 5, idotartam_ota_utc: "2026-10-07T12:00:00+00:00", megbizhatosag: "magas",
      domen: "megelhetes", tipus: "szintmero", szakpolitika: "energia_rezsi", sav: {} } },
  szokatlan_lista: ["benzin"] };
const UGY = { szamitva_utc: "2026-10-07T21:00:00+00:00", ablak: { kezdet: "2026-09-08", veg: "2026-10-07", nap: 30 },
  modell: "claude-opus-4-8", ugyek: [
    { nev: "Üzemanyagárak", szakpolitika: "energia_rezsi", eletut: "folyamatosan_jelenlevo", mozgas: "erosodo",
      kifejezesek: ["benzin ára", "gázolaj"], elso_nap: "2026-09-10", utolso_nap: "2026-10-07", napok_szama: 12,
      idovonal: [{ nap: "2026-09-10", jelen: true, ossz_volumen: 40 }, { nap: "2026-10-07", jelen: true, ossz_volumen: 70 }],
      osszefoglalo: "Az üzemanyagárak tartósan foglalkoztatják a keresőket." }] };

async function mock(page) {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ json: ELM }));
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ json: UGY }));
}

test("bővítés: szokatlan-változások blokk + ügy-lista renderel", async ({ page }) => {
  await mock(page);
  await page.goto("/bovites.html");
  await expect(page.locator("#bovites-elmozdulas")).toContainText("benzin");
  await expect(page.locator("#bovites-elmozdulas")).toContainText("emelkedik");
  await expect(page.locator("#bovites-ugyek")).toContainText("Üzemanyagárak");
  await expect(page.locator("#bovites-ugyek")).toContainText("benzin ára");
  await expect(page.locator(".bovites-ugy")).toHaveCount(1);
});

test("bővítés: fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/bovites.html");
  await expect(page.locator("#bovites")).toContainText("nem érhető el");
});
