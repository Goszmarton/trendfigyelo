const { test, expect } = require("@playwright/test");

const FIXTURE = {
  frissitve: "2026-08-22T20:00:00+00:00", modell: "claude-sonnet-5", nap: "2026-08-22",
  valtozas: { diff: { van_elozo: true, irany_valtok: [{ szo: "állás" }],
                       mozgok: [{ szo: "állás", valtozas: 2.0 }, { szo: "benzin", valtozas: -0.5 }],
                       felkapott_uj: ["eső"], felkapott_eltunt: [] },
              szoveg: "Változás-összefoglaló.", megfigyelesek: ["állás emelkedésbe váltott"], elmeleti: ["időjárás hathat"] },
  kulcsszavak: { szamok: [{ szo: "állás", irany: "emelkedik", mai_ertek: 10, csucs: 100 }],
                 napi: { szoveg: "Napi.", megfigyelesek: [], elmeleti: [] },
                 teljes_kep: { szoveg: "Teljes.", megfigyelesek: [], elmeleti: [] },
                 het: { szoveg: "Heti.", megfigyelesek: [], elmeleti: [] } },
  felkapott: { top: [{ kifejezes: "eső", volumen: "20000" }],
               napi: { szoveg: "Felk. napi.", megfigyelesek: [], elmeleti: [] },
               het: { szoveg: "Felk. heti.", megfigyelesek: [], elmeleti: [] },
               het_valos: { napok: 3, visszateroek: [{ kifejezes: "eső", napok_szama: 2 }] } },
};

test("Elemzés fül: VALÓS és ELMÉLETI réteg külön, aktív fül", async ({ page }) => {
  await page.route("**/data/elemzes.json", (r) => r.fulfill({ json: FIXTURE }));
  await page.route("**/data/elemzesek/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/elemzes.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Elemzés");
  await expect(page.locator("#elemzes-fejlec")).toContainText("2026-08-22");
  await expect(page.locator(".elemzes-megfigyeles").first()).toContainText("állás emelkedésbe váltott");
  await expect(page.locator(".elemzes-elmeleti").first()).toContainText("feltételezés:");
  await expect(page.locator(".elemzes-csempe")).toContainText("állás");
  // FIX 2 — heti VALÓS visszatérés-csempék (a het_valos.visszateroek, NEM az AI-szöveg)
  await expect(page.locator("#felkapott-het-valos .elemzes-felkapott-csempe")).toHaveCount(1);
  await expect(page.locator("#felkapott-het-valos .elemzes-felkapott-csempe")).toContainText("eső — 2 nap");
  // FIX 3 — „legnagyobb mozgók" a Mi változott ma? VALÓS összegzésben
  await expect(page.locator(".elemzes-diff-mozgok")).toContainText("állás");
  await expect(page.locator(".elemzes-diff-mozgok")).toContainText("benzin");
});
