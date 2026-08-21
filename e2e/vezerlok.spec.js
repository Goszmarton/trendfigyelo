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
  // 6b Szelet 2: a másodlagos fájlok most a kulcsszo-blokk BLOKK-jában vannak → izolálni kell (üres),
  // különben a teszt-szerver VALÓS másodlagos adata szivárogna be (rejtett valós-adat-függés).
  await page.route(/kulcsszo_masodlagos_regresszio\.json/, function (route) {
    route.fulfill({ contentType: "application/json", body: JSON.stringify({ kulcsszavak: {} }) });
  });
  await page.route(/kulcsszo_masodlagos_nyers\.json/, function (route) {
    route.fulfill({ contentType: "application/json", body: JSON.stringify({ kulcsszavak: {} }) });
  });
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

test("(b2) a letiltott intervallum-gomb OLVASHATÓ marad (a11y: jelentést hordoz — »ez a táv nem elérhető«)", async ({ page }) => {
  // Ugyanaz a fixture, mint (b): mind az 5 intervallum ervenyes:false → letiltott gombok.
  // A letiltott vezérlő WCAG 1.4.3 alól KIVÉTEL (nem szabálysértés), DE jelentést hordoz → olvashatónak kell lennie.
  // Ez az őr a #999 (2,85:1) → #6b6b6b (~5:1) váltást rögzíti. Diszkriminátor: #999-re visszaállítva ez a teszt bukik.
  await mock_regresszio(page, {
    "1_het": { ervenyes: false, ok: "nincs_adat" }, "2_het": NL, "1_ho": NL, "3_ho": NL, "1_ev": NL,
  });
  await page.goto("/");
  const gomb = page.locator("#intervallum-vezerlo button[disabled]").first();
  await expect(gomb).toBeVisible();
  const szin = await gomb.evaluate(function (el) { return getComputedStyle(el).color; });
  expect(szin).toBe("rgb(107, 107, 107)");
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
    .toHaveAttribute("data-intervallum", "teljes");   // ALAPNEZET = teljes (request 1); az 1_het gomb elérhető, de nem az alap
  await expect(page.locator('#intervallum-vezerlo button[data-intervallum="2_het"]')).toBeDisabled();
  // 6b Szelet 2 SZERZŐDÉS-JAVÍTÁS: a régi assert „összefűzött"-öt várt (órás-láncolás felirat), de a hosszú
  // intervallum forrása a nap/het másodlagos (§8.2: NEM láncolás) → a helyes üres-ok „nincs_masodlagos".
  // Ez a MÁSODIK teszt két nap alatt, ami a régi, HIBÁS szerződést kódolta (az első a test_teljes_blokkolas
  // volt, ami zöld-blokknál felülírást várt). Itt a szó nem kapott másodlagost → „napi/heti adatot", nem láncolás.
  await expect(page.locator("#intervallum-vezerlo")).toContainText("Ehhez az ablakhoz még gyűlik a napi/heti adat. Magától feltöltődik.");
  await expect(page.locator("#intervallum-vezerlo")).not.toContainText("összefűzött"); // a félrevezető órás-láncolás felirat NEM
});

test("több érvényes intervallum → az ALAPNEZET a TELJES (request 1, SZEMLE 08-19), nem az 1_het/leghosszabb", async ({ page }) => {
  // SZEMLE 08-19 / request 1: a kezdő nézet a TELJES időszak (közös tengely) — az oldal ezzel nyílik.
  // (A korábbi 1_het-default [ALAPNEZET-KONSTANS] ezzel lezárult; a fix intervallumok kattintásra jönnek.)
  await mock_regresszio(page, { "1_het": erv(), "2_het": NL, "1_ho": erv(), "3_ho": NL, "1_ev": NL });
  await page.goto("/");
  await expect(page.locator('#intervallum-vezerlo button[aria-pressed="true"]'))
    .toHaveAttribute("data-intervallum", "teljes");
});

// ── dátumválasztó ────────────────────────────────────────────────────────────

test("normál napok/index.json → naptár a legfrissebb hónapot rajzolja, alapból a LEGFRISSEBB nap kiválasztva", async ({ page }) => {
  await mock_napok_index(page, ["2026-08-02", "2026-08-03", "2026-08-04"]);
  await page.goto("/");
  await expect(page.locator("#datum-valaszto .naptar")).toBeVisible();
  await expect(page.locator("#datum-valaszto")).toHaveAttribute("data-valasztott-nap", "2026-08-04");   // alap: legfrissebb
  await expect(page.locator("#datum-valaszto")).toHaveAttribute("data-honap", "2026-08");
  await expect(page.locator("#datum-valaszto .naptar-cim")).toContainText("augusztus");
  await expect(page.locator("#datum-valaszto .nap-cella.valasztott")).toHaveText("4");
});

test("naptár: pontosan az adat-napok kattinthatók, a hónap többi napja nem-választható (szürke)", async ({ page }) => {
  await mock_napok_index(page, ["2026-08-02", "2026-08-03", "2026-08-04"]);
  await page.goto("/");
  await expect(page.locator("#datum-valaszto button.nap-cella:not([disabled])")).toHaveCount(3);   // pontosan a 3 adat-nap
  await expect(page.locator('#datum-valaszto .nap-cella[data-nap="2026-08-04"]:not([disabled])')).toBeVisible();
  await expect(page.locator('#datum-valaszto .nap-cella[data-nap="2026-08-01"]')).toHaveClass(/nem-valaszthato/);   // nincs adat → szürke
});

test("üres napok/index.json → dátumválasztó ÜRES állapot, nincs select", async ({ page }) => {
  await mock_napok_index(page, []);
  await page.goto("/");
  await expect(page.locator("#datum-valaszto .ures")).toBeVisible();
  await expect(page.locator("#datum-valaszto select")).toHaveCount(0);
});
