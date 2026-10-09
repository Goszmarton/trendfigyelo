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

test("bővítés: alfülek váltása mutatja/rejti a paneleket + leírás látszik", async ({ page }) => {
  await mock(page);
  await page.goto("/bovites.html");
  // alapból a Szokatlan változások panel látszik, a másik kettő rejtett
  await expect(page.locator("#bovites-panel-elmozdulas")).toBeVisible();
  await expect(page.locator("#bovites-panel-ugyek")).toBeHidden();
  await expect(page.locator("#bovites-panel-kapcsolodo")).toBeHidden();
  // a látszó panelnek van magyarázó leírása
  await expect(page.locator("#bovites-panel-elmozdulas .bovites-leiras")).toBeVisible();
  await expect(page.locator("#bovites-panel-elmozdulas .bovites-leiras")).toContainText("követett keresőszavak");
  // Ügyek életútja fülre váltva az a panel látszik, a fülgomb kijelölve
  await page.locator('.bovites-alful[data-panel="ugyek"]').click();
  await expect(page.locator("#bovites-panel-ugyek")).toBeVisible();
  await expect(page.locator("#bovites-panel-elmozdulas")).toBeHidden();
  await expect(page.locator('.bovites-alful[data-panel="ugyek"]')).toHaveAttribute("aria-selected", "true");
  await expect(page.locator('.bovites-alful[data-panel="elmozdulas"]')).toHaveAttribute("aria-selected", "false");
  // Kapcsolódó keresések fülre váltva
  await page.locator('.bovites-alful[data-panel="kapcsolodo"]').click();
  await expect(page.locator("#bovites-panel-kapcsolodo")).toBeVisible();
  await expect(page.locator("#bovites-panel-ugyek")).toBeHidden();
});

test("bővítés: fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/bovites.html");
  await expect(page.locator("#bovites")).toContainText("nem érhető el");
  // az alfülek a hiba ellenére megmaradnak
  await expect(page.locator(".bovites-alful")).toHaveCount(3);
});

test("bővítés: szakpolitika-szűrő szűkíti az ügy-listát", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ json: ELM }));
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ json: {
    ...UGY, ugyek: [UGY.ugyek[0],
      { nev: "Iskolakezdés", szakpolitika: "oktataspolitika", eletut: "visszatero", mozgas: "stabil",
        kifejezesek: ["iskola"], elso_nap: "2026-09-10", utolso_nap: "2026-10-01", napok_szama: 4,
        idovonal: [{ nap: "2026-09-10", jelen: true, ossz_volumen: 20 }], osszefoglalo: "y" }] } }));
  await page.goto("/bovites.html");
  await page.locator('.bovites-alful[data-panel="ugyek"]').click();
  await expect(page.locator(".bovites-ugy")).toHaveCount(2);
  // a szűrő-chip az Ügyek panelben (a globális állapotot állítja, így az elmozdulás-listát is szűri)
  await page.locator('#bovites-szuro-ugy .bovites-szuro-chip[data-szakpolitika="energia_rezsi"]').click();
  await expect(page.locator(".bovites-ugy")).toHaveCount(1);
  await expect(page.locator("#bovites-ugyek")).toContainText("Üzemanyagárak");
  await expect(page.locator("#bovites-elmozdulas")).toContainText("benzin");
  await page.locator('#bovites-szuro-ugy .bovites-szuro-chip[data-szakpolitika="oktataspolitika"]').click();
  await expect(page.locator(".bovites-ugy")).toHaveCount(1);
  await expect(page.locator("#bovites-elmozdulas")).not.toContainText("benzin");
  await page.locator('#bovites-szuro-ugy .bovites-szuro-chip[data-szakpolitika=""]').click();
  await expect(page.locator(".bovites-ugy")).toHaveCount(2);
  await page.locator('#bovites-szuro-ugy .bovites-rendezes-gomb[data-rendezes="frissesseg"]').click();
  await expect(page.locator(".bovites-ugy-nev").first()).toHaveText("Üzemanyagárak");
});

const KAPCS = { frissitve: "2026-10-07T21:00:00+00:00", kifejezesek: [
  { kifejezes: "benzin", lekerdezve: "2026-10-07T21:00:00+00:00", volumen: 90,
    top: [{ query: "benzin ár", value: 100 }, { query: "mol benzin", value: 19 }],
    rising: [{ query: "benzin ársapka", value: 8350 }, { query: "hatósági áras benzin", value: "Breakout" }] }]};

test("bővítés: kapcsolódó keresések szekció (top + rising) renderel", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ json: ELM }));
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ json: UGY }));
  await page.route("**/data/kapcsolodo.json", (r) => r.fulfill({ json: KAPCS }));
  await page.goto("/bovites.html");
  await page.locator('.bovites-alful[data-panel="kapcsolodo"]').click();
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("benzin");
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("benzin ár");         // top
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("benzin ársapka");     // rising
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("Breakout");
  // a számok jelentése (oszlop-súgók) megjelenik
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("relatív népszerűség");
  await expect(page.locator("#bovites-kapcsolodo")).toContainText("mennyivel nőtt");
});

test("bővítés: ügy-idővonal felirattal + jelmagyarázattal + volumen-árnyalással", async ({ page }) => {
  await mock(page);
  await page.goto("/bovites.html");
  await page.locator('.bovites-alful[data-panel="ugyek"]').click();
  const kartya = page.locator(".bovites-ugy").first();
  await expect(kartya.locator(".bovites-idovonal-cim")).toContainText("Napi jelenlét");
  await expect(kartya.locator(".bovites-idovonal-jelmagy")).toContainText("jelen");
  await expect(kartya.locator(".bovites-idovonal-jelmagy")).toContainText("nincs jelen");
  // a két végdátum a jelmagyarázatban
  await expect(kartya.locator(".bovites-idovonal-jelmagy")).toContainText("2026-09-10");
  await expect(kartya.locator(".bovites-idovonal-jelmagy")).toContainText("2026-10-07");
  // a jelen napok volumen szerint árnyalva (inline rgba háttér a sáv celláin)
  await expect(kartya.locator(".bovites-idovonal .bovites-nap").first()).toHaveAttribute("style", /rgba\(42, 120, 214/);
});

test("bővítés: kapcsolódó keresések fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/elmozdulas.json", (r) => r.fulfill({ json: ELM }));
  await page.route("**/data/ugyek.json", (r) => r.fulfill({ json: UGY }));
  await page.route("**/data/kapcsolodo.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/bovites.html");
  await expect(page.locator("#bovites")).toContainText("Üzemanyagárak");   // a többi blokk változatlan
});
