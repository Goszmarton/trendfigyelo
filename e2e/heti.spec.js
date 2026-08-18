const { test, expect } = require("@playwright/test");

// HETI FELKAPOTT KERESÉSEK blokk — bal sticky hét-választó + jobb napi táblázat. Frontend/DOM (nincs canvas).
// Forrás: napok/index.json (elérhető napok) + napok/<nap>.json (trendek[].kifejezes). A hét = hétfő–vasárnap (ISO).
// A megjelenített nap-tartomány: hétfő..min(vasárnap, max(napok/index)) — a jövő/nem-archivált nap KIMARAD.

const H = "#heti-blokk";

// FIXTURE — 2 ISO-hét, hiányzó napokkal, a legfrissebb elérhető nap = 2026-08-17 (hétfő, 34. hét):
//   33. hét (aug. 10–16): 08-10, 08-11, 08-13 VAN; 08-12/14/15/16 HIÁNYZIK → „nincs adat"
//   34. hét (aug. 17–23): csak 08-17 VAN (a 08-18+ még nem archivált → nem jelenik meg)
const INDEX = { napok: ["2026-08-10", "2026-08-11", "2026-08-13", "2026-08-17"] };
const NAPOK = {
  "2026-08-10": ["alfa", "béta"],
  "2026-08-11": ["gamma"],
  "2026-08-13": ["delta", "epszilon", "zéta"],
  "2026-08-17": ["théta", "ióta"],
};

function trendek(szavak) {
  return szavak.map(function (sz, i) { return { kifejezes: sz, volumen: String(1000 - i), novekedes_pct: "100", idosor: [], hirek: [] }; });
}

async function mock(page) {
  await page.route(/kategoriak\.json/, function (r) { r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: [] }) }); });
  await page.route(/legfrissebb\.json/, function (r) { r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: trendek(["mai1", "mai2"]) }) }); });
  await page.route(/napok\/index\.json/, function (r) { r.fulfill({ contentType: "application/json", body: JSON.stringify(INDEX) }); });
  for (const nap of Object.keys(NAPOK)) {
    await page.route(new RegExp("napok/" + nap + "\\.json"), function (r) {
      r.fulfill({ contentType: "application/json", body: JSON.stringify({ nap: nap, trendek: trendek(NAPOK[nap]) }) });
    });
  }
}

// ── 1. hét-választó: ISO-hetek, legfrissebb elöl + alapból kiválasztva ──
test("1. hét-választó: ISO-heteket sorol, legfrissebb elöl, alap = legfrissebb hét", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  const opt = page.locator("#heti-valaszto select option");
  await expect(opt).toHaveCount(2);                                    // 33. + 34. hét
  await expect(opt.first()).toHaveText("34. hét (aug. 17–23)");        // legfrissebb ELÖL
  await expect(page.locator("#heti-valaszto select")).toHaveValue("2026-08-17");   // alap = legfrissebb (hétfő-dátum a value)
  await expect(opt.last()).toHaveText("33. hét (aug. 10–16)");
});

// ── 2. ISO-hét-határ (a hibás „aug 11–17" ellen élesítve) ──
test("2. a 2026-08-17 a »34. hét (aug. 17–23)« alá esik (hétfő–vasárnap, ISO)", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await expect(page.locator("#heti-valaszto select option[value=\"2026-08-17\"]")).toHaveText("34. hét (aug. 17–23)");
});

// ── 3. alap-hét (34.) táblázata: csak 08-17 (a legfrissebb elérhető napig; 08-18+ NEM) ──
test("3. alap-hét táblázata a hétfőtől a legfrissebb elérhető napig; a jövő nap NEM jelenik meg", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await expect(page.locator(`${H} .heti-nap-sor`)).toHaveCount(1);                 // csak 08-17 (a vágás)
  const sor = page.locator(`${H} .heti-nap-sor[data-nap="2026-08-17"]`);
  await expect(sor.locator(".heti-nap")).toContainText("Hétfő");
  await expect(sor.locator(".heti-szavak")).toHaveText("théta, ióta");
});

// ── 4. hét-váltás → a 33. hét mind a 7 napja; a hiányzó nap „nincs adat" ──
test("4. 33. hét: 7 nap (hétfő–vasárnap), a hiányzó nap »nincs adat«, nem marad ki", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await page.locator("#heti-valaszto select").selectOption("2026-08-10");          // 33. hét hétfője
  await expect(page.locator(`${H} .heti-nap-sor`)).toHaveCount(7);                  // hétfő–vasárnap MIND
  await expect(page.locator(`${H} .heti-nap-sor[data-nap="2026-08-10"] .heti-szavak`)).toHaveText("alfa, béta");
  await expect(page.locator(`${H} .heti-nap-sor[data-nap="2026-08-12"] .heti-szavak`)).toHaveText("nincs adat");   // hiányzó nap
  await expect(page.locator(`${H} .heti-nap-sor[data-nap="2026-08-16"] .heti-szavak`)).toHaveText("nincs adat");
});

// ── 5. egy nap sora az aznapi ÖSSZES felkapott szót tartalmazza, tárolt sorrendben ──
test("5. napi sor = az aznapi összes felkapott szó, tárolt (volumen) sorrendben", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await page.locator("#heti-valaszto select").selectOption("2026-08-10");
  await expect(page.locator(`${H} .heti-nap-sor[data-nap="2026-08-13"] .heti-szavak`)).toHaveText("delta, epszilon, zéta");
});

// ── 6. FÜGGETLEN a dátumválasztótól: a fenti chartok napja nem változik ──
test("6. hét-váltás FÜGGETLEN — a #datum-valaszto értéke és a trend-blokk napja VÁLTOZATLAN", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await expect(page.locator("#datum-valaszto select")).toHaveValue("2026-08-17");   // alap: legfrissebb nap
  await expect(page.locator("#trend-blokk")).toHaveAttribute("data-nap", "2026-08-17");
  await page.locator("#heti-valaszto select").selectOption("2026-08-10");           // hét-váltás
  await expect(page.locator("#datum-valaszto select")).toHaveValue("2026-08-17");   // VÁLTOZATLAN
  await expect(page.locator("#trend-blokk")).toHaveAttribute("data-nap", "2026-08-17");
});
