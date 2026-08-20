const { test, expect } = require("@playwright/test");

// ÁTTEKINTŐ: a chip a szó MAI ELTÉRÉSÉT mutatja a saját trendjéhez (3-állapotú `illeszkedes`:
// felette ▲ / alatta ▼ / illeszkedik ✓), az ikon a szó ELŐTT; a teljes szöveg a title/aria-label-ben.
function iv(over = {}) {
  return { ervenyes: true, meredekseg_nap: 1.5, irany: over.irany ?? "novekszik", r2: 0.3,
    ablak_kezdet_utc: "2026-08-12T19:00:00+00:00", ablak_veg_utc: "2026-08-19T19:00:00+00:00",
    pontok_hasznalt: 168, pontok_nem_nulla: 160, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 0,
    illesztes_vonal: [{ idopont_utc: "2026-08-12T19:00:00+00:00", ertek: 70 },
                      { idopont_utc: "2026-08-19T18:00:00+00:00", ertek: 77 }],
    mai_ertek: 74, mai_reziduum: over.mai_reziduum ?? 0, reziduum_szokasos: 6,
    illeszkedes: over.illeszkedes ?? "illeszkedik" };
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

test("attekinto: panel legfelül, kategória-sor (domén balra, chipek jobbra), eltérés-ikon a szó ELŐTT + kattint-affordancia", async ({ page }) => {
  await mock(page, reg({
    "állás": szo({ domen: "munkaeropiac", illeszkedes: "felette" }),
    "albérlet": szo({ domen: "lakhatas", illeszkedes: "illeszkedik" }),
  }));
  await page.goto("/");
  // a panel a #kulcsszo-blokk ELŐTT áll a DOM-ban
  const sorrend = await page.evaluate(() => {
    const a = document.querySelector("#attekinto-blokk");
    const k = document.querySelector("#kulcsszo-blokk");
    return a && k ? (a.compareDocumentPosition(k) & Node.DOCUMENT_POSITION_FOLLOWING) > 0 : false;
  });
  expect(sorrend).toBe(true);
  await expect(page.locator(A + " .attekinto-sor[data-domen='munkaeropiac'] .attekinto-domen")).toHaveText("Munkaerőpiac");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='állás'] .attekinto-ikon")).toHaveAttribute("data-illeszkedes", "felette");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='albérlet'] .attekinto-ikon")).toHaveAttribute("data-illeszkedes", "illeszkedik");
  // az ikon a szó ELŐTT áll (a chip első gyereke)
  const elso = await page.locator(A + " .attekinto-kartya[data-kulcsszo='állás'] > *:first-child").getAttribute("class");
  expect(elso).toContain("attekinto-ikon");
  // kattintható affordancia (chip → a szó chartjához ugrás)
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='állás']")).toHaveAttribute("role", "link");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='állás']")).toHaveAttribute("tabindex", "0");
});

test("attekinto: három eltérés-állapot (▲ felette / ▼ alatta / ✓ illeszkedik) + null → nincs ikon", async ({ page }) => {
  await mock(page, reg({
    "állás": szo({ domen: "munkaeropiac", illeszkedes: "felette" }),
    "kórház": szo({ domen: "egeszseg", illeszkedes: "alatta" }),
    "hitel": szo({ domen: "haztartasi_penzugy", illeszkedes: "illeszkedik" }),
    "benzin": szo({ domen: "energia", iv1het: { ervenyes: false, ok: "keves_pont" } }),
  }));
  await page.goto("/");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='állás'] .attekinto-ikon")).toHaveAttribute("data-illeszkedes", "felette");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='állás']")).toHaveAttribute("title", /a trendje fölé ugrott/);
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='kórház'] .attekinto-ikon")).toHaveAttribute("data-illeszkedes", "alatta");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='kórház']")).toHaveAttribute("title", /a trendje alá esett/);
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='hitel'] .attekinto-ikon")).toHaveAttribute("data-illeszkedes", "illeszkedik");
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='hitel']")).toHaveAttribute("title", /illeszkedik a trendjéhez/);
  // benzin: nincs érvényes intervallum → nincs eltérés-ikon (nem kitalált)
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='benzin'] .attekinto-ikon")).toHaveCount(0);
});

test("attekinto: magyarázó doboz a blokk ALJÁN (a lista után)", async ({ page }) => {
  await mock(page, reg({ "állás": szo({ domen: "munkaeropiac" }) }));
  await page.goto("/");
  await expect(page.locator(A + " .attekinto-magyarazat")).toHaveCount(1);
  const utan = await page.evaluate(() => {
    const lista = document.querySelector("#attekinto-blokk .attekinto-lista");
    const magy = document.querySelector("#attekinto-blokk .attekinto-magyarazat");
    return lista && magy ? (lista.compareDocumentPosition(magy) & Node.DOCUMENT_POSITION_FOLLOWING) > 0 : false;
  });
  expect(utan).toBe(true);
});

function mpReg(kulcsszavak) {
  return { szamitva_utc: "2026-08-19T19:00:00+00:00", meredekseg_egyseg: "relatív pont / nap",
    elmozdulas_kuszob: 7.0, megjegyzes: "teszt", kulcsszavak };
}

test("attekinto: tüntetés esemenyjelzo — a MEDIÁNTÓL való eltérés ikonja + title", async ({ page }) => {
  const regObj = reg({
    "tüntetés": szo({ domen: "kozelet", tipus: "esemenyjelzo",
      iv1het: { ervenyes: false, ok: "esemenyjelzo" } }),
  });
  const mp = mpReg({ "tüntetés": { racs: "het", aktiv: true, domen: "kozelet", tipus: "esemenyjelzo",
    szint: 8, szint_modszer: "median", mai_szint: 30, mai_elteres: 22, szint_szokasos: 1,
    illeszkedes: "felette", intervallumok: {} } });
  await mock(page, regObj, mp);
  await page.goto("/");
  const kartya = page.locator(A + " .attekinto-kartya[data-kulcsszo='tüntetés']");
  await expect(kartya).toHaveCount(1);
  await expect(kartya.locator(".attekinto-ikon")).toHaveAttribute("data-illeszkedes", "felette");
  await expect(kartya).toHaveAttribute("title", /medián/);
  await expect(kartya).toHaveAttribute("aria-label", /medián/);
});

// ── TREND-panel (a Kulcsszavak alatt, data-mod="trend"): a trend IRÁNYÁT mutatja az `irany`-ból ──
const B = "#attekinto-blokk-alul";

test("trend-panel: a chip ikonja a TREND-irányt kódolja (data-trend az irany-ból), külön title", async ({ page }) => {
  await mock(page, reg({
    "állás": szo({ domen: "munkaeropiac", irany: "novekszik", illeszkedes: "illeszkedik" }),
    "hitel": szo({ domen: "haztartasi_penzugy", irany: "csokken", illeszkedes: "illeszkedik" }),
    "benzin": szo({ domen: "energia", irany: "stagnal", illeszkedes: "illeszkedik" }),
  }));
  await page.goto("/");
  await expect(page.locator(B + " .attekinto-kartya[data-kulcsszo='állás'] .attekinto-ikon")).toHaveAttribute("data-trend", "novekszik");
  await expect(page.locator(B + " .attekinto-kartya[data-kulcsszo='állás']")).toHaveAttribute("title", /trendje növekvő/);
  await expect(page.locator(B + " .attekinto-kartya[data-kulcsszo='hitel'] .attekinto-ikon")).toHaveAttribute("data-trend", "csokken");
  await expect(page.locator(B + " .attekinto-kartya[data-kulcsszo='benzin'] .attekinto-ikon")).toHaveAttribute("data-trend", "stagnal");
  // a trend-panel a felső eltérés-panelnél NEM használ data-illeszkedes-t a chipen
  await expect(page.locator(B + " .attekinto-kartya[data-kulcsszo='állás'] .attekinto-ikon[data-illeszkedes]")).toHaveCount(0);
});

test("trend-panel: tüntetés esemenyjelzo → 'esemeny' (nincs trend), a title a mediánt említi", async ({ page }) => {
  const regObj = reg({
    "tüntetés": szo({ domen: "kozelet", tipus: "esemenyjelzo", iv1het: { ervenyes: false, ok: "esemenyjelzo" } }),
  });
  const mp = mpReg({ "tüntetés": { racs: "het", aktiv: true, domen: "kozelet", tipus: "esemenyjelzo",
    szint: 8, szint_modszer: "median", mai_szint: 30, mai_elteres: 22, szint_szokasos: 1,
    illeszkedes: "felette", intervallumok: {} } });
  await mock(page, regObj, mp);
  await page.goto("/");
  const kartya = page.locator(B + " .attekinto-kartya[data-kulcsszo='tüntetés']");
  await expect(kartya.locator(".attekinto-ikon")).toHaveAttribute("data-trend", "esemeny");
  await expect(kartya).toHaveAttribute("title", /medián/);
});

// REGRESSZIÓ-ŐR (a user által talált bug): mindkét panel a TELJES (leghosszabb ablak = legkorábbi
// ablak_kezdet_utc, = a megjelenített chart) intervallumot használja — NEM a legrövidebbet. A rövid órás
// 1_het egy nap/het szónál más (téves) irányt/eltérést adhat, mint a valódi hosszú napi/heti ablak.
test("mindkét panel a TELJES (leghosszabb) ablakot használja, nem a legrövidebbet", async ({ page }) => {
  const rovid = iv({ irany: "novekszik", illeszkedes: "felette" });                 // 1_het kezdet 2026-08-12
  const hosszu = Object.assign(iv({ irany: "csokken", illeszkedes: "alatta" }),
    { ablak_kezdet_utc: "2025-08-12T19:00:00+00:00" });                             // 1_ev korábbi kezdet = hosszabb
  await mock(page, reg({
    "állás": { meres_kezdete: "2025-08-01", meres_vege: null, aktiv: true, domen: "munkaeropiac", tipus: "szintmero", racs: "het",
      intervallumok: { "1_het": rovid, "2_het": ivHibas("nincs_lancolas"),
        "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": hosszu } },
  }));
  await page.goto("/");
  // eltérés-panel: a HOSSZÚ ablak "alatta" (▼), NEM a rövid "felette"
  await expect(page.locator(A + " .attekinto-kartya[data-kulcsszo='állás'] .attekinto-ikon")).toHaveAttribute("data-illeszkedes", "alatta");
  // trend-panel: a HOSSZÚ ablak "csokken", NEM a rövid "novekszik"
  await expect(page.locator(B + " .attekinto-kartya[data-kulcsszo='állás'] .attekinto-ikon")).toHaveAttribute("data-trend", "csokken");
});
