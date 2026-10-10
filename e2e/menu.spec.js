const { test, expect } = require("@playwright/test");

// Menüsor (Excel-fül) + „Az adatokról" külön oldal — statikus szerkezet-őr (nincs adat-mock, a nav statikus).
test("menüsor: 8 link + 2 csoportcímke, aktív = Google; a linkek helyesek + sorrend", async ({ page }) => {
  await page.goto("/trendek.html");
  await expect(page.locator("#fomenu a")).toHaveCount(8);
  await expect(page.locator("#fomenu .fomenu-cimke")).toHaveText(["Elemzések", "Jelzések", "Statisztikák"]);
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Google");
  await expect(page.locator('#fomenu a[href="index.html"]')).toHaveText("Áttekintő");
  await expect(page.locator('#fomenu a[href="elemzes.html"]')).toHaveText("Napi");
  await expect(page.locator('#fomenu a[href="heti.html"]')).toHaveText("Heti");
  await expect(page.locator('#fomenu a[href="havi.html"]')).toHaveText("Havi");
  await expect(page.locator('#fomenu a[href="bovites.html"]')).toHaveText("Radar");
  await expect(page.locator('#fomenu a[href="trendek.html"]')).toHaveText("Google");
  await expect(page.locator('#fomenu a[href="youtube.html"]')).toHaveText("YouTube");
  await expect(page.locator('#fomenu a[href="adatokrol.html"]')).toHaveText("Infó");
  await expect(page.locator("#fomenu a")).toHaveText(["Áttekintő", "Napi", "Heti", "Havi", "Radar", "Google", "YouTube", "Infó"]);
  await expect(page.locator("#labresz")).toBeAttached();
  await expect(page.locator("#adatokrol")).toHaveCount(0);
});

test("youtube.html: a fül betölt, a YouTube menüpont aktív", async ({ page }) => {
  await page.goto("/youtube.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("YouTube");
  await expect(page.locator("#youtube-blokk")).toBeAttached();
});

test("havi.html: a fül betölt, a Havi elemzés menüpont aktív", async ({ page }) => {
  await page.goto("/havi.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Havi");
  await expect(page.locator("#fomenu a")).toHaveText(["Áttekintő", "Napi", "Heti", "Havi", "Radar", "Google", "YouTube", "Infó"]);
});

test("heti.html: a fül betölt, a Heti értékelés menüpont aktív", async ({ page }) => {
  await page.goto("/heti.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Heti");
  await expect(page.locator("#fomenu a")).toHaveText(["Áttekintő", "Napi", "Heti", "Havi", "Radar", "Google", "YouTube", "Infó"]);
  await expect(page.locator("#heti")).toBeAttached();
});

test("bovites.html: a fül betölt, a Radar menüpont aktív", async ({ page }) => {
  await page.goto("/bovites.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Radar");
  await expect(page.locator("#fomenu a")).toHaveText(["Áttekintő", "Napi", "Heti", "Havi", "Radar", "Google", "YouTube", "Infó"]);
  await expect(page.locator("#bovites")).toBeAttached();
});

test("Infó oldal: adat + elemzés dobozok, csoportcímek, aktív fül + üres lábléc", async ({ page }) => {
  await page.goto("/adatokrol.html");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Infó");
  await expect(page.locator("#adatokrol .adat-doboz")).toHaveCount(32);  // 10 Google (+ nemlin-trend, adatforrás-marker, előrejelzés) + 5 YouTube + 3 napi elemzés + 4 heti elemzés + 5 havi elemzés + 4 bővítés doboz
  await expect(page.locator("#adatokrol .adat-csoport")).toHaveCount(6);  // Google + YouTube + „Az elemzés" (napi) + „A heti elemzés" + „A havi elemzés" + „A Radar fül"
  await expect(page.locator("#adatokrol .adat-csoport")).toHaveText([
    "Google Trend adatok", "YouTube Trend adatok", "Az elemzés (napi AI-összefoglaló)",
    "A heti elemzés (heti AI-összefoglaló)", "A havi elemzés (havi AI-összefoglaló)", "A Radar fül"]);
  await expect(page.locator("#adatokrol")).toContainText("szokatlan");
  await expect(page.locator("#adatokrol")).toContainText("ügyek életútja");
  await expect(page.locator("#adatokrol")).toContainText("kapcsolódó keresés");
  await expect(page.locator("#adatokrol")).toContainText("Google Trends");
  await expect(page.locator("#adatokrol")).toContainText("52 hét heti mediánjához");   // tüntetés-medián
  // nemlineáris (LOESS) trend doboz: nem-parametrikus statisztikai simítás + out-of-sample R² + mindig-görbe
  await expect(page.locator("#adatokrol")).toContainText("nem-parametrikus");
  await expect(page.locator("#adatokrol")).toContainText("out-of-sample");
  await expect(page.locator("#adatokrol")).toContainText("Mindig látszik a görbe");
  // előrejelzés doboz: csillapított trend, bizonytalansági sáv, visszatesztel
  await expect(page.locator("#adatokrol")).toContainText("csillapított");
  await expect(page.locator("#adatokrol")).toContainText("bizonytalansági sáv");
  await expect(page.locator("#adatokrol")).toContainText("visszatesztel");
  // elemzés-rész: pontos, precíz — a modell és a „Python számol / AI csak szöveg" elv nevesítve
  await expect(page.locator("#adatokrol")).toContainText("claude-opus-4-8");
  await expect(page.locator("#adatokrol")).toContainText("Python");
  await expect(page.locator("#adatokrol")).toContainText("hétfő");
  await expect(page.locator("#adatokrol")).toContainText("ügyek tartóssága");
  await expect(page.locator("#labresz")).toBeAttached();
  // YouTube-doboz: a fül fogalmi kerete (videó-igény, 12 szó/8 kosár, napi/heti rács, VALÓS Python-trend)
  await expect(page.locator("#adatokrol-youtube")).toBeAttached();
});

test("navigáció: a Trendek főoldalról az Az adatokról oldalra és vissza", async ({ page }) => {
  await page.goto("/trendek.html");
  await page.locator('#fomenu a[href="adatokrol.html"]').click();
  await expect(page).toHaveURL(/adatokrol\.html$/);
  await expect(page.locator("#adatokrol .adat-doboz").first()).toBeVisible();
  await page.locator('#fomenu a[href="trendek.html"]').click();
  await expect(page).toHaveURL(/trendek\.html$/);
  await expect(page.locator("#dashboard")).toBeVisible();
});

test("landing: a gyökér (/) az Áttekintő nyitóoldalt szolgálja", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('#fomenu a[aria-current="page"]')).toHaveText("Áttekintő");
  await expect(page.locator(".nyitooldal-kartya")).toHaveCount(3);
});
