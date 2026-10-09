const { test, expect } = require("@playwright/test");

const INDEX = { hetek: ["2026-09-21", "2026-09-28"], legutolso: "2026-09-28" };

function hetiArt(het) {
  return {
    het_kezdet: het, het_veg: "2026-10-04", iso_het: "2026-W40", modell: "claude-opus-4-8",
    korpusz: { het_kezdet: het, het_veg: "2026-10-04", iso_het: "2026-W40", napok: 7, egyedi_felkapott: 12 },
    vezetoi_osszefoglalo: ["Megállapítás egy.", "Megállapítás kettő."],
    figyelem_atrendezodes: { erosodo: ["benzinár"], gyengulo: ["nyugdíj"] },
    ugyek_eletutja: { rovid_kiugras: "Rövid x.", hosszabb_kiugras: "Hosszú y.", visszatero: "Vissza z." },
    melyebb_temak: [{ tema: "Üzemanyag", keresesi_palya: "nőtt", kapcsolodo_kifejezesek: "benzin, gázár",
                      ellenorzott_esemenyek: "Hír A.", magyarazat: "Mert." }],
    google_youtube_osszefugges: "Párhuzam a szorongásnál.",
    jovo_heti_figyelendok: ["Figyeld a benzinárat."],
    figyelem: [{ szo: "benzinár", elteres: 12.0, irany: "nő", illeszkedes: "felette", domen: "megelhetes" },
               { szo: "nyugdíj", elteres: -7.0, irany: "csökken", illeszkedes: "alatta", domen: "megelhetes" }],
  };
}

async function mock(page, art) {
  await page.route("**/data/heti/index.json", (r) => r.fulfill({ json: INDEX }));
  await page.route("**/data/heti/*.json", (r) => {
    if (r.request().url().includes("index.json")) return r.fallback();
    return r.fulfill({ json: art });
  });
}

test("heti: a 6 rész + a figyelem-diagram renderel", async ({ page }) => {
  await mock(page, hetiArt("2026-09-28"));
  await page.goto("/heti.html");
  await expect(page.locator("#heti-tartalom")).toContainText("Megállapítás egy.");
  await expect(page.locator("#heti-tartalom")).toContainText("Üzemanyag");
  await expect(page.locator("#heti-tartalom")).toContainText("Párhuzam a szorongásnál.");
  await expect(page.locator("#heti-tartalom")).toContainText("Figyeld a benzinárat.");
  // a figyelem-diagram adatlistája (a11y-fallback) a két szót tartalmazza
  await expect(page.locator(".heti-figyelem-chart-doboz")).toBeAttached();
  await expect(page.locator("#heti-tartalom")).toContainText("benzinár");
  await expect(page.locator("#heti-tartalom")).toContainText("nyugdíj");
});

test("heti: hónap-naptár — adat-hét napja kiemelve, korábbi hétre kattintva kiválasztódik", async ({ page }) => {
  await mock(page, hetiArt("2026-09-28"));
  await page.goto("/heti.html");
  // a hét-naptár megjelenik, az adat-hetek napjai kiemelve (a 2026-09-28 és 2026-09-21 hétfők is)
  await expect(page.locator("#heti-het-panel .naptar")).toBeAttached();
  await expect(page.locator('#heti-het-panel .nap-cella[data-nap="2026-09-28"].heti-adat-het')).toBeAttached();
  // alapból a legutolsó hét (09-28) a kiválasztott
  await expect(page.locator('#heti-het-panel .nap-cella[data-nap="2026-09-28"]')).toHaveAttribute("aria-current", "date");
  // a korábbi hét (09-21 hétfő) napjára kattintva az a hét lesz a kiválasztott
  await page.locator('#heti-het-panel .nap-cella[data-nap="2026-09-21"]').click();
  await expect(page.locator('#heti-het-panel .nap-cella[data-nap="2026-09-21"]')).toHaveAttribute("aria-current", "date");
  await expect(page.locator('#heti-het-panel .nap-cella[data-nap="2026-09-28"]')).not.toHaveAttribute("aria-current", "date");
});

test("heti: fail-soft, ha nincs adat", async ({ page }) => {
  await page.route("**/data/heti/index.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.route("**/data/heti/*.json", (r) => r.fulfill({ status: 404, body: "" }));
  await page.goto("/heti.html");
  await expect(page.locator("#heti-tartalom")).toContainText("nem érhető el");
});
