const { test, expect } = require("@playwright/test");

const FIXTURE = {
  frissitve: "2026-08-22T20:00:00+00:00", modell: "claude-opus-4-8", nap: "2026-08-22",
  valtozas: { diff: { van_elozo: true, irany_valtok: [{ szo: "állás" }],
                       mozgok: [{ szo: "állás", valtozas: 2.0 }, { szo: "benzin", valtozas: -0.5 }],
                       felkapott_uj: ["eső"], felkapott_eltunt: [] },
              szoveg: "Változás-összefoglaló." },
  kulcsszavak: { szamok: [{ szo: "állás", irany: "emelkedik", mai_ertek: 10, csucs: 100 }],
                 napi: { szoveg: "Napi első bekezdés.\n\nNapi második bekezdés." },
                 teljes_kep: { szoveg: "Teljes." },
                 het: { szoveg: "Heti." } },
  felkapott: { top: [{ kifejezes: "eső", volumen: "20000" }],
               napi: { szoveg: "Felk. napi." },
               het: { szoveg: "Felk. heti." },
               het_valos: { napok: 3, visszateroek: [{ kifejezes: "eső", napok_szama: 2 }] } },
};

test("Elemzés fül: folyó próza <p>-ként, nincs feltételezés-réteg; kulcsszó-csempe marad, felkapott-csempe NEM", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: FIXTURE }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Elemzések");
  await expect(page.locator("#elemzes-fejlec")).toContainText("2026-08-22");
  // folyó próza: a „Kulcsszavak — mit látunk ma" szekció 2 bekezdést renderel <p>-ként
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Kulcsszavak — mit látunk ma")) .elemzes-szoveg')).toHaveCount(2);
  // nincs ELMÉLETI/feltételezés-réteg és nincs bullet-lista
  await expect(page.locator(".elemzes-elmeleti")).toHaveCount(0);
  await expect(page.locator("#elemzes-tartalom")).not.toContainText("feltételezés:");
  // kulcsszó VALÓS csempék + diff-összegzés + mozgók MARADNAK
  await expect(page.locator(".elemzes-csempe")).toContainText("állás");
  await expect(page.locator(".elemzes-diff-osszegzes")).toContainText("állás");
  await expect(page.locator(".elemzes-diff-mozgok")).toContainText("benzin");
  // a felkapott-csempesorok (napi top „(volumen: …)" + heti visszatérés „— N nap") NEM jelennek meg
  await expect(page.locator(".elemzes-felkapott-csempe")).toHaveCount(0);
  await expect(page.locator("#felkapott-het-valos")).toHaveCount(0);
});

test("Elemzés elrendezés: naptár bal, elemzés jobb; mobilon egymás alá", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: FIXTURE }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ json: { napok: ["2026-08-22"] } }));
  await page.setViewportSize({ width: 1200, height: 900 });
  await page.goto("/elemzes.html");
  await expect(page.locator("#elemzes-naptar .nap-cella").first()).toBeVisible();
  const nap = await page.locator("#elemzes-naptar").boundingBox();
  const tart = await page.locator("#elemzes-tartalom").boundingBox();
  expect(nap.x + nap.width).toBeLessThanOrEqual(tart.x + 1);        // naptár a tartalomtól BALRA
  await page.setViewportSize({ width: 480, height: 900 });
  const nap2 = await page.locator("#elemzes-naptar").boundingBox();
  const tart2 = await page.locator("#elemzes-tartalom").boundingBox();
  expect(tart2.y).toBeGreaterThan(nap2.y + nap2.height - 1);         // tartalom a naptár ALATT
});

const FIXTURE_YT = Object.assign({}, FIXTURE, {
  youtube: {
    szamok: [{ szo: "szorongás", domen: "egeszseg", irany: "novekszik", meredekseg: 0.05,
               ervenyes: true, mai_ertek: 43, csucs: 50, atlag: 45.0 }],
    het_valos: [{ szo: "bitcoin", kezdo: 30, veg: 57, valtozas: 27 }],
    napi: { szoveg: "YouTube napi próza." },
    teljes_kep: { szoveg: "YouTube teljes kép." },
    het: { szoveg: "YouTube heti mozgás." },
  },
});

test("Elemzés: két nevesített szegmens + YouTube-csempék és 3 szekció, ha van youtube blokk", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: FIXTURE_YT }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  // két szegmens-cím
  await expect(page.locator("h2.elemzes-szegmens")).toHaveText([
    "Google keresések napi elemzése", "YouTube keresések napi elemzése"]);
  // YouTube VALÓS csempe: mai + ÁTLAG (nem csúcs — a 12-m normálás miatt a csúcs mindig ~100)
  await expect(page.locator("#youtube-szegmens .elemzes-csempe")).toContainText("szorongás");
  await expect(page.locator("#youtube-szegmens .elemzes-csempe")).toContainText("átlag 45");
  await expect(page.locator("#youtube-szegmens .elemzes-csempe")).not.toContainText("csúcs");
  // 3 YouTube AI-szekció renderel (folyó próza <p>-ként)
  await expect(page.locator("#youtube-szegmens .elemzes-szekcio")).toHaveCount(3);
  await expect(page.locator("#youtube-szegmens")).toContainText("YouTube napi próza.");
});

test("Elemzés: régi archív-nap (nincs youtube blokk) → nincs YouTube-szegmens, a Google-rész ép", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: FIXTURE }));  // nincs youtube
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator("#youtube-szegmens")).toHaveCount(0);
  await expect(page.locator("h2.elemzes-szegmens")).toHaveText(["Google keresések napi elemzése"]);
  await expect(page.locator(".elemzes-csempe")).toContainText("állás");   // Google-rész változatlan
});

test("Elemzés fül: ÚJ felkapott 4 szekció (reggeli/esti/nap íve/heti)", async ({ page }) => {
  const UJ = {
    nap: "2026-09-01", modell: "claude-opus-4-8",
    valtozas: { diff: { irany_valtok: [], mozgok: [], felkapott_uj: [], felkapott_eltunt: [], van_elozo: false }, szoveg: "v" },
    kulcsszavak: { szamok: [], napi: { szoveg: "k1" }, teljes_kep: { szoveg: "k2" }, het: { szoveg: "k3" } },
    felkapott: {
      top: [], reggel_top: [], este_top: [], reggel_este_diff: { uj_estere: [], eltunt_estere: [], megmaradt: [] },
      reggel: { szoveg: "reggeli próza" }, este: { szoveg: "esti próza" },
      teljes_nap: { szoveg: "a nap íve próza" }, het: { szoveg: "heti próza" }, het_valos: { napok: 0, visszateroek: [] },
    },
  };
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: UJ }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — reggeli (9:00)")) .elemzes-szoveg')).toHaveText("reggeli próza");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — esti (21:00)")) .elemzes-szoveg')).toHaveText("esti próza");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — a nap íve")) .elemzes-szoveg')).toHaveText("a nap íve próza");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — heti összesítés")) .elemzes-szoveg')).toHaveText("heti próza");
  // a régi „Felkapott — napi" cím NEM jelenik meg az új alaknál
  await expect(page.locator('h3:text-is("Felkapott — napi")')).toHaveCount(0);
});

test("Elemzés fül: RÉGI felkapott {napi,het} → a mostani 2 szekció (visszafelé kompat)", async ({ page }) => {
  const REGI = {
    nap: "2026-08-22", modell: "m",
    valtozas: { diff: { irany_valtok: [], mozgok: [], felkapott_uj: [], felkapott_eltunt: [], van_elozo: false }, szoveg: "v" },
    kulcsszavak: { szamok: [], napi: { szoveg: "k1" }, teljes_kep: { szoveg: "k2" }, het: { szoveg: "k3" } },
    felkapott: { top: [], napi: { szoveg: "régi napi" }, het: { szoveg: "régi heti" }, het_valos: { napok: 0, visszateroek: [] } },
  };
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: REGI }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator('.elemzes-szekcio:has(h3:text-is("Felkapott — napi")) .elemzes-szoveg')).toHaveText("régi napi");
  await expect(page.locator('h3:text-is("Felkapott — reggeli (9:00)")')).toHaveCount(0);
});
