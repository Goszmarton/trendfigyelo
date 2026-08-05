const { test, expect } = require("@playwright/test");

// Task 6 vezérlő-smoke-ok — MOCKOLT kulcsszo_regresszio.json / napok/index.json forgatókönyvekkel,
// hogy a smoke NE függjön a valós napi futástól. STUB-RED: ma nincs vezérlő-JS → mind BUKIK
// (not-found/timeout). GREEN után az alábbi DOM-szerződést kell teljesíteni.

const NL = { ervenyes: false, ok: "nincs_lancolas" };

function erv() {
  return {
    ervenyes: true, meredekseg_nap: -1.0, se_meredekseg: 0.5, irany: "csokken",
    r2: 0.1, r2_masodlagos_autokorrelacio: true,
    ablak_kezdet_utc: "2026-07-28T20:00:00+00:00", ablak_veg_utc: "2026-08-04T20:00:00+00:00",
    pontok_hasznalt: 168, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 0,
  };
}

function regresszio(intervallumok) {
  return {
    szamitva_utc: "2026-08-04T20:00:00+00:00",
    meredekseg_egyseg: "relatív pont / nap",
    irany_kuszob: 1.0,
    megjegyzes: "teszt",
    kulcsszavak: {
      szo: {
        meres_kezdete: "2026-07-30", meres_vege: null, aktiv: true,
        domen: "g", tipus: "szintmero", intervallumok: intervallumok,
      },
    },
  };
}

async function mock_regresszio(page, intervallumok) {
  await page.route(/kulcsszo_regresszio\.json/, function (route) {
    route.fulfill({ contentType: "application/json", body: JSON.stringify(regresszio(intervallumok)) });
  });
}

async function mock_napok_index(page, napok) {
  await page.route(/napok\/index\.json/, function (route) {
    route.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: napok }) });
  });
}

// ── intervallum-vezérlő ──────────────────────────────────────────────────────

// FIGYELEM: az (a) hiányzó-adat és a (b) van-adat-de-nincs-érvényes-ablak eset SZÁNDÉKOSAN
// KÜLÖNBÖZŐ megjelenítést kap (spec 7.4: a letiltott gomb magyarázatot adjon). NE egyszerűsítsd
// vissza egy sorra: (b)-ben mind az 5 letiltott gomb + ok-szöveg látszik, (a)-ban egy mondat, 0 gomb.

test("(b) minden intervallum ervenyes:false → 5 LETILTOTT gomb ok-szöveggel + .ures fejléc", async ({ page }) => {
  await mock_regresszio(page, {
    "1_het": { ervenyes: false, ok: "nincs_adat" }, "2_het": NL, "1_ho": NL, "3_ho": NL, "1_ev": NL,
  });
  await page.goto("/");
  await expect(page.locator("#intervallum-vezerlo .ures")).toBeVisible();                  // fejléc
  await expect(page.locator("#intervallum-vezerlo button")).toHaveCount(5);                // mind az 5 gomb jelen
  await expect(page.locator("#intervallum-vezerlo button[disabled]")).toHaveCount(5);       // mind letiltott
  await expect(page.locator("#intervallum-vezerlo button:not([disabled])")).toHaveCount(0); // 0 élő gomb
  await expect(page.locator("#intervallum-vezerlo .ok")).toHaveCount(5);                    // mindegyik mellett ok-szöveg
});

test("(a) hiányzó kulcsszo_regresszio.json → .ures üzenet ÉS NULLA gomb (ez különbözteti meg a (b)-től)", async ({ page }) => {
  await page.route(/kulcsszo_regresszio\.json/, function (route) {
    route.fulfill({ status: 404, contentType: "text/plain", body: "Not Found" });
  });
  await page.goto("/");
  await expect(page.locator("#intervallum-vezerlo .ures")).toBeVisible();
  await expect(page.locator("#intervallum-vezerlo button")).toHaveCount(0); // NINCS gomb (szemben a (b) 5 gombjával)
});

test("1_het ervenyes, többi false → az 1_het KIVÁLASZTVA; a 2_het tiltott, magyar magyarázattal", async ({ page }) => {
  await mock_regresszio(page, { "1_het": erv(), "2_het": NL, "1_ho": NL, "3_ho": NL, "1_ev": NL });
  await page.goto("/");
  await expect(page.locator('#intervallum-vezerlo button[aria-pressed="true"]'))
    .toHaveAttribute("data-intervallum", "1_het");
  await expect(page.locator('#intervallum-vezerlo button[data-intervallum="2_het"]')).toBeDisabled();
  await expect(page.locator("#intervallum-vezerlo")).toContainText("összefűzött"); // nincs_lancolas magyar oka
});

test("1_het és 1_ho ervenyes → a LEGHOSSZABB (1_ho) van kiválasztva", async ({ page }) => {
  await mock_regresszio(page, { "1_het": erv(), "2_het": NL, "1_ho": erv(), "3_ho": NL, "1_ev": NL });
  await page.goto("/");
  await expect(page.locator('#intervallum-vezerlo button[aria-pressed="true"]'))
    .toHaveAttribute("data-intervallum", "1_ho");
});

// ── dátumválasztó ────────────────────────────────────────────────────────────

test("normál napok/index.json → dátumválasztó feltöltve, alapból a LEGFRISSEBB nap", async ({ page }) => {
  await mock_napok_index(page, ["2026-08-02", "2026-08-03", "2026-08-04"]);
  await page.goto("/");
  const sel = page.locator("#datum-valaszto select");
  await expect(sel.locator("option")).toHaveCount(3);
  await expect(sel).toHaveValue("2026-08-04");        // alapból a legfrissebb
  await expect(sel).toContainText("2026. 08. 04.");   // magyar dátumformátum
});

test("üres napok/index.json → dátumválasztó ÜRES állapot, nincs select", async ({ page }) => {
  await mock_napok_index(page, []);
  await page.goto("/");
  await expect(page.locator("#datum-valaszto .ures")).toBeVisible();
  await expect(page.locator("#datum-valaszto select")).toHaveCount(0);
});
