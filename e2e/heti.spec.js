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

// ── 1. hét-kiemelő naptár: a legfrissebb hét sora kiemelve (alap = 34. hét, hétfő 08-17) ──
test("1. hét-kiemelő naptár: alap = a legfrissebb hét, mind a 7 napja kiemelve (34. hét, 08-17..08-23)", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await expect(page.locator("#heti-valaszto .naptar")).toBeVisible();
  await expect(page.locator("#heti-valaszto")).toHaveAttribute("data-valasztott-het", "2026-08-17");   // legfrissebb hét hétfője
  await expect(page.locator("#heti-valaszto")).toHaveAttribute("data-honap", "2026-08");
  await expect(page.locator("#heti-valaszto .nap-cella.valasztott-het")).toHaveCount(7);                // az EGÉSZ hét sora
  await expect(page.locator('#heti-valaszto .nap-cella[data-nap="2026-08-17"]')).toHaveClass(/valasztott-het/);
  await expect(page.locator('#heti-valaszto .nap-cella[data-nap="2026-08-23"]')).toHaveClass(/valasztott-het/);
});

// ── 2. adat-hét napjai kattinthatók; az adat-nélküli hét napjai szürkék ──
test("2. adat-hét napjai kattinthatók, adat-nélküli hét szürke (nem-választható)", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await expect(page.locator('#heti-valaszto .nap-cella[data-nap="2026-08-10"]:not([disabled])')).toBeVisible();  // 33. hét
  await expect(page.locator('#heti-valaszto .nap-cella[data-nap="2026-08-17"]:not([disabled])')).toBeVisible();  // 34. hét
  await expect(page.locator('#heti-valaszto .nap-cella[data-nap="2026-08-05"]')).toHaveClass(/nem-valaszthato/); // 08-03..09 hét: nincs adat
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
  await page.locator('#heti-valaszto .nap-cella[data-nap="2026-08-10"]').click();  // a 33. hét egy napja → az egész hét
  await expect(page.locator("#heti-valaszto")).toHaveAttribute("data-valasztott-het", "2026-08-10");
  await expect(page.locator(`${H} .heti-nap-sor`)).toHaveCount(7);                  // hétfő–vasárnap MIND
  await expect(page.locator(`${H} .heti-nap-sor[data-nap="2026-08-10"] .heti-szavak`)).toHaveText("alfa, béta");
  await expect(page.locator(`${H} .heti-nap-sor[data-nap="2026-08-12"] .heti-szavak`)).toHaveText("nincs adat");   // hiányzó nap
  await expect(page.locator(`${H} .heti-nap-sor[data-nap="2026-08-16"] .heti-szavak`)).toHaveText("nincs adat");
});

// ── 5. egy nap sora az aznapi ÖSSZES felkapott szót tartalmazza, tárolt sorrendben ──
test("5. napi sor = az aznapi összes felkapott szó, tárolt (volumen) sorrendben", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await page.locator('#heti-valaszto .nap-cella[data-nap="2026-08-10"]').click();
  await expect(page.locator(`${H} .heti-nap-sor[data-nap="2026-08-13"] .heti-szavak`)).toHaveText("delta, epszilon, zéta");
});

// ── 6. FÜGGETLEN a dátumválasztótól: a fenti chartok napja nem változik ──
test("6. hét-váltás FÜGGETLEN — a #datum-valaszto értéke és a trend-blokk napja VÁLTOZATLAN", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await expect(page.locator("#datum-valaszto")).toHaveAttribute("data-valasztott-nap", "2026-08-17");   // alap: legfrissebb nap
  await expect(page.locator("#trend-blokk")).toHaveAttribute("data-nap", "2026-08-17");
  await page.locator('#heti-valaszto .nap-cella[data-nap="2026-08-10"]').click();   // hét-váltás (a heti naptár KÜLÖN vezérlő maradt)
  await expect(page.locator("#datum-valaszto")).toHaveAttribute("data-valasztott-nap", "2026-08-17");   // VÁLTOZATLAN
  await expect(page.locator("#trend-blokk")).toHaveAttribute("data-nap", "2026-08-17");
});

// ── N. szegmentált nap (reggel/este) → két .heti-szegmens; régi nap → egyetlen lista (VÁLTOZATLAN) ──
test("N. heti: szegmentált nap reggel/este elválasztóval, régi nap egy lista", async ({ page }) => {
  const IDX = { napok: ["2026-08-17"] };
  await page.route(/kategoriak\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: [] }) }));
  await page.route(/legfrissebb\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: [] }) }));
  await page.route(/napok\/index\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify(IDX) }));
  await page.route(/napok\/2026-08-17\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({
    nap: "2026-08-17",
    reggel: { trendek: [{ kifejezes: "reg1" }, { kifejezes: "reg2" }], frissitve: "2026-08-17T07:00:00+00:00" },
    este: { trendek: [{ kifejezes: "est1" }], frissitve: "2026-08-17T19:00:00+00:00" },
  }) }));
  await page.goto("/");
  const sor = page.locator('#heti-blokk .heti-nap-sor[data-nap="2026-08-17"]');
  await expect(sor.locator('.heti-szegmens[data-szegmens="reggel"]')).toContainText("reg1, reg2");
  await expect(sor.locator('.heti-szegmens[data-szegmens="este"]')).toContainText("est1");
});

// ── N+1. napközben CSAK-REGGEL szegmens (nincs még `este`) → CÍMKÉZETT „Reggel:" lista, este-szegmens NINCS ──
// spec §8 #3: a szegmentált nap akár egyetlen populált szegmenssel is címkézve jelenik meg (NEM lapul le).
test("N+1. heti: csak-reggel szegmentált nap → címkézett Reggel lista, este nélkül", async ({ page }) => {
  const IDX = { napok: ["2026-08-17"] };
  await page.route(/kategoriak\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: [] }) }));
  await page.route(/legfrissebb\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: [] }) }));
  await page.route(/napok\/index\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify(IDX) }));
  await page.route(/napok\/2026-08-17\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({
    nap: "2026-08-17",
    reggel: { trendek: [{ kifejezes: "reg1" }, { kifejezes: "reg2" }], frissitve: "2026-08-17T07:00:00+00:00" },
  }) }));
  await page.goto("/");
  const sor = page.locator('#heti-blokk .heti-nap-sor[data-nap="2026-08-17"]');
  const reggel = sor.locator('.heti-szegmens[data-szegmens="reggel"]');
  await expect(reggel).toBeVisible();
  await expect(reggel).toContainText("Reggel:");
  await expect(reggel).toContainText("reg1, reg2");
  await expect(sor.locator('.heti-szegmens[data-szegmens="este"]')).toHaveCount(0);   // napközben még nincs este
});
