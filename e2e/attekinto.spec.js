const { test, expect } = require("@playwright/test");

function iv(over = {}) {
  return { ervenyes: true, meredekseg_nap: over.meredekseg_nap ?? 1.5,
    irany: over.irany ?? "novekszik", r2: 0.3,
    ablak_kezdet_utc: "2026-08-12T19:00:00+00:00", ablak_veg_utc: "2026-08-19T19:00:00+00:00",
    pontok_hasznalt: 168, pontok_nem_nulla: 160, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 0,
    illesztes_vonal: [{ idopont_utc: "2026-08-12T19:00:00+00:00", ertek: 70 },
                      { idopont_utc: "2026-08-19T18:00:00+00:00", ertek: 77 }],
    mai_ertek: over.mai_ertek ?? 74, mai_reziduum: over.mai_reziduum ?? -3,
    reziduum_szokasos: over.reziduum_szokasos ?? 6, illeszkedes: over.illeszkedes ?? "illeszkedik" };
}
function ivHibas(ok) { return { ervenyes: false, ok }; }
function szo(over = {}) {
  return { meres_kezdete: "2026-07-30", meres_vege: null, aktiv: true,
    domen: over.domen ?? "munkaeropiac", tipus: over.tipus ?? "szintmero", racs: over.racs,
    intervallumok: { "1_het": over.iv1het ?? iv(over),
      "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
      "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } };
}
function reg(kulcsszavak) {
  return { szamitva_utc: "2026-08-19T19:00:00+00:00", meredekseg_egyseg: "relatív pont / nap",
    irany_kuszob: 1.0, megjegyzes: "teszt", kulcsszavak };
}
async function mock(page, regObj, mpRegObj) {
  await page.route(/kulcsszo_masodlagos_regresszio\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify(mpRegObj || { kulcsszavak: {} }) }));
  await page.route(/kulcsszo_masodlagos_nyers\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify({ kulcsszavak: {} }) }));
  await page.route(/kulcsszo_regresszio\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify(regObj) }));
  await page.route(/kulcsszo_nyers\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify({ kulcsszavak: {} }) }));
}
const A = "#attekinto-blokk";

test("attekinto: panel legfelül, domen-csoportok, irány-ikon", async ({ page }) => {
  await mock(page, reg({
    "állás": szo({ domen: "munkaeropiac", irany: "csokken" }),
    "albérlet": szo({ domen: "lakhatas", irany: "stagnal" }),
  }));
  await page.goto("/");
  // a panel a #kulcsszo-blokk ELŐTT áll a DOM-ban
  const sorrend = await page.evaluate(() => {
    const a = document.querySelector("#attekinto-blokk");
    const k = document.querySelector("#kulcsszo-blokk");
    return a && k ? (a.compareDocumentPosition(k) & Node.DOCUMENT_POSITION_FOLLOWING) > 0 : false;
  });
  expect(sorrend).toBe(true);
  await expect(page.locator(A + " .attekinto-csoport[data-domen='munkaeropiac'] h3")).toHaveText("Munkaerőpiac");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='állás'] .attekinto-ikon"))
    .toHaveAttribute("data-irany", "csokken");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='albérlet'] .attekinto-ikon"))
    .toHaveAttribute("data-irany", "stagnal");
});

test("attekinto: illeszkedés-jelző két állapota + null → nincs jelző", async ({ page }) => {
  await mock(page, reg({
    "állás": szo({ domen: "munkaeropiac", irany: "csokken", illeszkedes: "illeszkedik" }),
    "hitel": szo({ domen: "haztartasi_penzugy", irany: "novekszik", illeszkedes: "tavolabb" }),
    "benzin": szo({ domen: "energia", iv1het: { ervenyes: false, ok: "keves_pont" } }),
  }));
  await page.goto("/");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='állás'] .attekinto-illeszkedes"))
    .toHaveAttribute("data-illeszkedes", "illeszkedik");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='hitel'] .attekinto-illeszkedes"))
    .toHaveAttribute("data-illeszkedes", "tavolabb");
  // benzin: nincs érvényes intervallum → nincs illeszkedés-jelző (nem kitalált)
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='benzin'] .attekinto-illeszkedes")).toHaveCount(0);
});

test("attekinto: ⓘ-magyarázó doboz jelen van", async ({ page }) => {
  await mock(page, reg({ "állás": szo({ domen: "munkaeropiac" }) }));
  await page.goto("/");
  await expect(page.locator(A + " .attekinto-magyarazat")).toHaveCount(1);
});

function mpReg(kulcsszavak) {
  return { szamitva_utc: "2026-08-19T19:00:00+00:00", meredekseg_egyseg: "relatív pont / nap",
    elmozdulas_kuszob: 7.0, megjegyzes: "teszt", kulcsszavak };
}

test("attekinto: tüntetés esemenyjelzo — nincs nyíl, mediántól-eltérés", async ({ page }) => {
  const regObj = reg({
    "tüntetés": szo({ domen: "kozelet", tipus: "esemenyjelzo",
      iv1het: { ervenyes: false, ok: "esemenyjelzo" } }),
  });
  const mp = mpReg({ "tüntetés": { racs: "het", aktiv: true, domen: "kozelet", tipus: "esemenyjelzo",
    szint: 8, szint_modszer: "median", mai_szint: 30, mai_elteres: 22, szint_szokasos: 1,
    illeszkedes: "tavolabb", intervallumok: {} } });
  await mock(page, regObj, mp);
  await page.goto("/");
  const kartya = page.locator(A + " .attekinto-kartya[data-kulcsszo='tüntetés']");
  await expect(kartya).toHaveCount(1);
  await expect(kartya.locator(".attekinto-ikon")).not.toHaveAttribute("data-irany", /.+/);   // nincs nyíl
  await expect(kartya.locator(".attekinto-illeszkedes")).toHaveAttribute("data-illeszkedes", "tavolabb");
  await expect(kartya.locator(".attekinto-illeszkedes")).toContainText("mediántól");
});
