const { test, expect } = require("@playwright/test");

// Inline naptár nap-választó (a #datum-valaszto <select> helyett). A napok/index.json az elérhető napok.
async function mockNapok(page, napok) {
  await page.route(/kulcsszo_masodlagos_regresszio\.json|kulcsszo_masodlagos_nyers\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify({ kulcsszavak: {} }) }));
  await page.route(/napok\/index\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok }) }));
}
const N = "#datum-valaszto";

test("naptár 1. a legfrissebb hónap rajzol, a legfrissebb nap kiválasztva", async ({ page }) => {
  await mockNapok(page, ["2026-07-30", "2026-08-18", "2026-08-20"]);
  await page.goto("/");
  await expect(page.locator(`${N} .naptar`)).toBeVisible();
  await expect(page.locator(N)).toHaveAttribute("data-valasztott-nap", "2026-08-20");
  await expect(page.locator(N)).toHaveAttribute("data-honap", "2026-08");
  await expect(page.locator(`${N} .naptar-cim`)).toContainText("2026");
  await expect(page.locator(`${N} .naptar-cim`)).toContainText("augusztus");
  await expect(page.locator(`${N} .nap-cella.valasztott`)).toHaveText("20");
});

test("naptár 2. adat-napok kattinthatók; adat-nélküli + szomszéd-hónap napok szürkék (nem-választható)", async ({ page }) => {
  await mockNapok(page, ["2026-08-18", "2026-08-20"]);   // csak 2 adat-nap augusztusban
  await page.goto("/");
  await expect(page.locator(`${N} button.nap-cella:not([disabled])`)).toHaveCount(2);   // pontosan a 2 adat-nap
  await expect(page.locator(`${N} .nap-cella[data-nap="2026-08-18"]:not([disabled])`)).toBeVisible();
  await expect(page.locator(`${N} .nap-cella[data-nap="2026-08-19"]`)).toHaveClass(/nem-valaszthato/);  // nincs adat → szürke
  await expect(page.locator(`${N} .nap-cella.szomszed-honap`).first()).toHaveClass(/nem-valaszthato/);  // szomszéd-hónap napja
});

test("naptár 3. nap-kattintás → data-valasztott-nap + a #trend-blokk napja követi", async ({ page }) => {
  await mockNapok(page, ["2026-08-18", "2026-08-20"]);
  await page.goto("/");
  await page.locator(`${N} .nap-cella[data-nap="2026-08-18"]`).click();
  await expect(page.locator(N)).toHaveAttribute("data-valasztott-nap", "2026-08-18");
  await expect(page.locator(`${N} .nap-cella.valasztott`)).toHaveText("18");
  await expect(page.locator("#trend-blokk")).toHaveAttribute("data-nap", "2026-08-18");
});

test("naptár 4. ‹ › hónap-navigáció az adat-tartományban, a széleken letiltva; a kiválasztást nem változtatja", async ({ page }) => {
  await mockNapok(page, ["2026-07-30", "2026-08-20"]);   // tartomány: 2026-07 .. 2026-08
  await page.goto("/");
  await expect(page.locator(`${N} .honap-lep.elore`)).toBeDisabled();     // aug az utolsó adat-hónap → előre tiltva
  await expect(page.locator(`${N} .honap-lep.vissza`)).toBeEnabled();
  await page.locator(`${N} .honap-lep.vissza`).click();                   // júliusra
  await expect(page.locator(N)).toHaveAttribute("data-honap", "2026-07");
  await expect(page.locator(`${N} .naptar-cim`)).toContainText("július");
  await expect(page.locator(`${N} .honap-lep.vissza`)).toBeDisabled();    // júl az első adat-hónap → vissza tiltva
  await expect(page.locator(`${N} .honap-lep.elore`)).toBeEnabled();
  await expect(page.locator(N)).toHaveAttribute("data-valasztott-nap", "2026-08-20");   // a navigáció NEM választ
});
