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
