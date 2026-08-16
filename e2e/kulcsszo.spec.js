const { test, expect } = require("@playwright/test");

// Task 9b kulcsszó-blokk smoke-ok — MOCKOLT kulcsszo_regresszio.json + kulcsszo_nyers.json.
// STUB-RED: ma nincs 9b-render → a 9b-DOM-ot állító smoke-ok BUKNAK (viselkedésbeli, nem ImportError),
// a 15a/15b csupa hiány-assert → SZÁNDÉKOSAN ZÖLD (regresszió-őr, nem RED-diszkriminátor).
// A DOM-szerződést lásd a ledgerben (Task 9b). A canvas CSAK a data-drawable="true" kártyán van.

// ── időbélyeg-építők (node-oldal; a böngészőben TILOS a Date, itt a mock ÉPÍTÉSÉHEZ szabad) ──────
const KEZD_MS = Date.parse("2026-07-29T20:00:00Z");
function iso(h) {
  return new Date(KEZD_MS + h * 3600000).toISOString().replace(".000Z", "+00:00");
}
const VEG = iso(168);          // "2026-08-05T20:00:00+00:00" — a részleges záró slot
const ELSO = iso(0);           // "2026-07-29T20:00:00+00:00"
const UTOLSO_LEZART = iso(167);// "2026-08-05T19:00:00+00:00"

// n_lezart órás lezárt pont KEZD-től + opcionális részleges záró; ertek konstans vagy fn(i)
function pontok(n_lezart, ertek, opts = {}) {
  const pts = [];
  for (let i = 0; i < n_lezart; i++) {
    pts.push({ idopont_utc: iso(i), ertek: typeof ertek === "function" ? ertek(i) : ertek, reszleges: false });
  }
  if (opts.partial !== false) {
    pts.push({ idopont_utc: iso(n_lezart), ertek: opts.partialErtek ?? 0, reszleges: true });
  }
  return pts;
}

// egy teljes (168 lezárt + 1 részleges) nyers ablak-rekord
function nyersRekord(kulcsszo, ertek = 50, opts = {}) {
  return {
    kulcsszo,
    ablak_kezdet_utc: opts.kezd ?? ELSO,
    ablak_veg_utc: opts.veg ?? VEG,
    pontok: opts.pontok ?? pontok(opts.n ?? 168, ertek, opts),
  };
}

function nyers(map) {
  return { kulcsszavak: map };
}

// ── napi/heti rács-fixture (6b rajzolás Szelet 1) — lepes_nap=1 (nap) vagy 7 (het) ──────────────
const NAP_MS = Date.parse("2026-08-01T00:00:00Z");
function racs_iso(i, lepes_nap) {
  return new Date(NAP_MS + i * lepes_nap * 86400000).toISOString().replace(".000Z", "+00:00");
}
// n lezart pont lepes_nap közönként (folytonos, nem-nulla) + 1 részleges záró
function racs_pontok(n, lepes_nap) {
  const pts = [];
  for (let i = 0; i < n; i++) pts.push({ idopont_utc: racs_iso(i, lepes_nap), ertek: 50, reszleges: false });
  pts.push({ idopont_utc: racs_iso(n, lepes_nap), ertek: 0, reszleges: true });
  return pts;
}
function racs_nyersRekord(kulcsszo, n, lepes_nap) {
  return { kulcsszo, ablak_kezdet_utc: racs_iso(0, lepes_nap), ablak_veg_utc: racs_iso(n, lepes_nap),
    pontok: racs_pontok(n, lepes_nap) };
}
// érvényes regresszió-intervallum ehhez a rács-ablakhoz (végpontok az első/utolsó LEZÁRT ponton)
function racs_iv(n, lepes_nap) {
  return { ervenyes: true, meredekseg_nap: 1.0, se_meredekseg: 0.4, se_masodlagos_autokorrelacio: true,
    irany: "novekszik", r2: 0.3, r2_masodlagos_autokorrelacio: true,
    ablak_kezdet_utc: racs_iso(0, lepes_nap), ablak_veg_utc: racs_iso(n, lepes_nap),
    pontok_hasznalt: n, pontok_nem_nulla: n, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 0,
    illesztes_vonal: [{ idopont_utc: racs_iso(0, lepes_nap), ertek: 40 },
      { idopont_utc: racs_iso(n - 1, lepes_nap), ertek: 55 }] };
}
// egy rács-szó teljes regresszió-bejegyzése (aktív 1_het = a rács-ablak, a többi nincs_lancolas)
function racs_regSzo(racs, n, lepes_nap) {
  return regSzo({ racs, intervallumok: {
    "1_het": racs_iv(n, lepes_nap),
    "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
    "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
  } });
}

// érvényes intervallum (a mini-9a horgonnyal); a végpontok az első/utolsó LEZÁRT pontnál
function ivErvenyes(over = {}) {
  return {
    ervenyes: true,
    meredekseg_nap: over.meredekseg_nap ?? 1.5,
    se_meredekseg: 0.4,
    se_masodlagos_autokorrelacio: true,
    irany: over.irany ?? "novekszik",
    r2: over.r2 ?? 0.31,
    r2_masodlagos_autokorrelacio: true,
    ablak_kezdet_utc: over.ablak_kezdet_utc ?? ELSO,
    ablak_veg_utc: over.ablak_veg_utc ?? VEG,
    pontok_hasznalt: over.pontok_hasznalt ?? 168,
    pontok_nem_nulla: over.pontok_nem_nulla ?? 166,
    pontok_kihagyva_reszleges: over.pontok_kihagyva_reszleges ?? 1,
    pontok_hianyzo: over.pontok_hianyzo ?? 0,
    illesztes_vonal: over.illesztes_vonal ?? [
      { idopont_utc: over.vonal_kezd ?? ELSO, ertek: 35.4 },
      { idopont_utc: over.vonal_veg ?? UTOLSO_LEZART, ertek: 41.9 },
    ],
  };
}

function ivHibas(ok) {
  return { ervenyes: false, ok };
}

// egy szó regresszió-bejegyzése; alapból csak 1_het érvényes, a többi nincs_lancolas
function regSzo(over = {}) {
  const iv = over.intervallumok ?? {
    "1_het": ivErvenyes(over.iv1het),
    "2_het": ivHibas("nincs_lancolas"),
    "1_ho": ivHibas("nincs_lancolas"),
    "3_ho": ivHibas("nincs_lancolas"),
    "1_ev": ivHibas("nincs_lancolas"),
  };
  return {
    meres_kezdete: over.meres_kezdete ?? "2026-07-30",
    meres_vege: over.meres_vege ?? null,
    aktiv: over.aktiv ?? true,
    domen: over.domen ?? "munkaeropiac",
    tipus: over.tipus ?? "szintmero",
    racs: over.racs,   // RACS_EGYSEG: szó-szintű rács (óra/nap/hét); hiány → undefined (nem szerializálódik, mint az órás JSON)
    intervallumok: iv,
  };
}

function reg(kulcsszavak, over = {}) {
  return {
    szamitva_utc: over.szamitva_utc ?? "2026-08-05T20:37:39+00:00",
    meredekseg_egyseg: "relatív pont / nap",
    irany_kuszob: 1.0,
    megjegyzes: "teszt",
    kulcsszavak,
  };
}

async function mock(page, { regObj, nyersObj }) {
  await page.route(/kulcsszo_regresszio\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify(regObj) }));
  await page.route(/kulcsszo_nyers\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify(nyersObj) }));
}

const K = "#kulcsszo-blokk";

// ── 1. render + domen-csoportosítás + üres kártya + K1 biconditional ──────────────────────────
test("1. render + domen-csoportosítás + üres kártya + K1 (.merteszamok == data-drawable=true)", async ({ page }) => {
  await mock(page, {
    regObj: reg({
      "állás": regSzo({ domen: "munkaeropiac" }),
      "albérlet": regSzo({ domen: "lakhatas" }),
      // ervenyes:false az aktív 1_het-en → NEM rajzolható → .ures, NINCS canvas, NINCS .merteszamok
      "hitel": regSzo({ domen: "lakhatas", intervallumok: {
        "1_het": ivHibas("nincs_adat"), "2_het": ivHibas("nincs_lancolas"),
        "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
      } }),
    }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")], "albérlet": [nyersRekord("albérlet")], "hitel": [nyersRekord("hitel")] }),
  });
  await page.goto("/");
  await expect(page.locator(`${K} .domen-csoport`)).toHaveCount(2);                 // Munkaerőpiac + Lakhatás
  await expect(page.locator(`${K} .domen-csoport[data-domen="lakhatas"] h3.domen-fejlec`)).toHaveText("Lakhatás");
  await expect(page.locator(`${K} .kulcsszo-chart`)).toHaveCount(3);                 // szavanként egy kártya
  await expect(page.locator(`${K} .kulcsszo-chart[data-drawable="true"]`)).toHaveCount(2);
  await expect(page.locator(`${K} .kulcsszo-chart[data-drawable="false"] .ures`)).toHaveCount(1);
  // K1 biconditional — MINDKÉT irány: canvas és .merteszamok pontosan a rajzolható kártyákon
  await expect(page.locator(`${K} .kulcsszo-chart canvas`)).toHaveCount(2);
  await expect(page.locator(`${K} .merteszamok`)).toHaveCount(2);                    // == data-drawable=true (nem >0)
});

// ── 2. mérőszám-sor formátum ─────────────────────────────────────────────────────────────────
test("2. mérőszám-sor: irány LEÍRÓ tendencia, 2 tizedes vessző, előjel, R² önmagyarázó legenda, nevező — nincs ± / se", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo({ iv1het: { meredekseg_nap: 1.5, irany: "novekszik", r2: 0.31 } }) }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
  });
  await page.goto("/");
  const m = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"] .merteszamok`);
  await expect(m).toContainText("iránya növekvő");
  await expect(m).toContainText("+1,50 relatív pont/nap");
  await expect(m).toContainText("R² = 0,31 (illeszkedés-jóság 0–1; a magasabb érték erősebb irányt jelent)");
  await expect(m).toContainText("166/168 óra nem-nulla");                            // a jel erőssége ELÖL (§8.3)
  await expect(m).toContainText("168/168 lezárt");                                   // nevező = hasznalt + hianyzo, zárójelben
  await expect(m).toContainText("1 részleges kihagyva");
  await expect(m).not.toContainText("±");                                            // se SEHOL
});

// ── 2a. RACS_EGYSEG: nap-rácsú szó → a rács-SZÓ "nap" (nem hardkódolt "óra") ───────────────────
test("2a. nap-rácsú szó → 'nap nem-nulla' felirat (nem 'óra')", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "albérlet": regSzo({ racs: "nap", domen: "lakhatas" }) }),
    nyersObj: nyers({ "albérlet": [nyersRekord("albérlet")] }),
  });
  await page.goto("/");
  const m = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="albérlet"] .merteszamok`);
  await expect(m).toContainText("166/168 nap nem-nulla");   // a rács-szó a szó racs-ából
  await expect(m).not.toContainText("óra nem-nulla");       // az "óra" nem szivárog át
});

// ── 2b. RACS_EGYSEG: ismeretlen rács → LÁTHATÓ fallback, nem néma "óra", nem undefined ─────────
test("2b. ismeretlen rács → látható '? <érték>' fallback (nem 'óra', nem 'undefined')", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo({ racs: "negyedev" }) }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
  });
  await page.goto("/");
  const m = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"] .merteszamok`);
  await expect(m).toContainText("? negyedev nem-nulla");    // a nyers érték LÁTHATÓ
  await expect(m).not.toContainText("óra nem-nulla");       // NEM néma "óra"
  await expect(m).not.toContainText("undefined");           // NEM undefined
});

// ── 2c. RACS_EGYSEG szándékos-zöld: racs hiánya → "óra" (órás út bájt-azonos) ──────────────────
test("2c. racs nélküli szó → 'óra nem-nulla' (default) — SZANDEKOS_ZOLD regresszió-őr", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo() }),                     // NINCS racs → default "ora"
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
  });
  await page.goto("/");
  const m = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"] .merteszamok`);
  await expect(m).toContainText("166/168 óra nem-nulla");
});

// ── 2d. RACS rajzolás (Szelet 1): nap-rácsú szó → napi slot-rács, FOLYTONOS (data-szakadas=0) ──
test("2d. nap-rácsú szó napi pontokkal → data-szakadas=0 (nem órás-slotokra szórva)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "albérlet": racs_regSzo("nap", 14, 1) }),   // 14 napi lezárt pont, 1-nap köz
    nyersObj: nyers({ "albérlet": [racs_nyersRekord("albérlet", 14, 1)] }),
  });
  await page.goto("/");
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="albérlet"]`);
  await expect(c).toHaveAttribute("data-drawable", "true");
  await expect(c).toHaveAttribute("data-szakadas", "0");   // napi rács folytonos, NEM 24-óránként szórt
});

// ── 2e. RACS rajzolás (Szelet 1): het-rácsú szó → heti slot-rács, FOLYTONOS (data-szakadas=0) ──
test("2e. het-rácsú szó heti pontokkal → data-szakadas=0 (heti slot, nem órás)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "akciós újság": racs_regSzo("het", 8, 7) }),   // 8 heti lezárt pont, 7-nap köz
    nyersObj: nyers({ "akciós újság": [racs_nyersRekord("akciós újság", 8, 7)] }),
  });
  await page.goto("/");
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="akciós újság"]`);
  await expect(c).toHaveAttribute("data-drawable", "true");
  await expect(c).toHaveAttribute("data-szakadas", "0");
});

// ── 2f. RACS rajzolás szándékos-zöld: órás szó (racs nélkül) → data-szakadas VÁLTOZATLAN ───────
test("2f. órás szó teljes ablakkal → data-szakadas=0 (óra ág változatlan) — SZANDEKOS_ZOLD", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo() }),                      // NINCS racs → órás ág, 168 óránkénti pont
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),    // teljes órás ablak, lyuk nélkül
  });
  await page.goto("/");
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`);
  await expect(c).toHaveAttribute("data-drawable", "true");
  await expect(c).toHaveAttribute("data-szakadas", "0");   // órás rács folytonos, most is és a szelet után is
});

// ── 3. ablak-választás ablak_veg-egyezéssel (mod 2) ──────────────────────────────────────────
test("3. ablak-választás: a regresszió ablak_veg_utc-jével EGYEZŐ ablak (nem utolsó, nem max)", async ({ page }) => {
  // A regresszió 1_het ablak_veg = VEG = iso(168) = a k=0 ablak (a hét LEGRÉGEBBI ablaka).
  // Tömb: [3,6,0,5,1,4,2] → utolsó elem k=2 (veg iso(216)); max(ablak_veg) k=6 (veg iso(312)).
  // Helyes választás = VEG-EGYEZÉS (k=0) → sem az "utolsó rekord", sem a "max(ablak_veg)" nem adja.
  // SZERZŐDÉS: az ablak-választás a regresszió ablak_veg_utc-jével való EGYEZÉS, NEM a legfrissebb ablak.
  const ablakok = [3, 6, 0, 5, 1, 4, 2].map((k) =>
    nyersRekord("állás", 50, { kezd: iso(k * 24), veg: iso(k * 24 + 168), pontok: pontok(168, 50) }));
  await mock(page, {
    regObj: reg({ "állás": regSzo() }),   // regSzo default 1_het ablak_veg = VEG = iso(168) = k=0
    nyersObj: nyers({ "állás": ablakok }),
  });
  await page.goto("/");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`)).toHaveAttribute("data-ablak-veg", VEG);
});

// ── 4. regressziós vonal jelen → data-vonal="true" ───────────────────────────────────────────
test("4. illesztes_vonal + mindkét végpont a címkékben → data-vonal=true", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo() }),   // vonal végpontjai: ELSO és UTOLSO_LEZART (a nyersben megvannak)
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
  });
  await page.goto("/");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`)).toHaveAttribute("data-vonal", "true");
});

// ── 5. vonal hiányzó ÉS elcsúszott végpont → data-vonal="false", görbe rajzol (4b + 4c/S1) ────
test("5. hiányzó illesztes_vonal (4b) és ablak-elcsúszott végpont (4c) → data-vonal=false, canvas megvan", async ({ page }) => {
  const ivNoVonal = ivErvenyes(); delete ivNoVonal.illesztes_vonal;                 // 4b: nincs horgony
  const ivDrift = ivErvenyes({ vonal_veg: "2099-01-01T00:00:00+00:00" });           // 4c: végpont nincs a címkékben
  await mock(page, {
    regObj: reg({
      "nincs": regSzo({ domen: "munkaeropiac", intervallumok: { "1_het": ivNoVonal,
        "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }),
      "drift": regSzo({ domen: "munkaeropiac", intervallumok: { "1_het": ivDrift,
        "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }),
    }),
    nyersObj: nyers({ "nincs": [nyersRekord("nincs")], "drift": [nyersRekord("drift")] }),
  });
  await page.goto("/");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="nincs"]`)).toHaveAttribute("data-vonal", "false");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="drift"]`)).toHaveAttribute("data-vonal", "false");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="drift"] canvas`)).toHaveCount(1);  // a görbe rajzol
});

// ── 6. fedettség pontos számok + nevező (mod 4) ──────────────────────────────────────────────
test("6. data-pontok / data-reszleges / data-hianyzo pontos egyenlőség; nevező = pontok + hianyzo", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo({ iv1het: { pontok_hasznalt: 144, pontok_nem_nulla: 140, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 24 } }) }),
    nyersObj: nyers({ "állás": [nyersRekord("állás", 50, { n: 144 })] }),
  });
  await page.goto("/");
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`);
  await expect(c).toHaveAttribute("data-pontok", "144");
  await expect(c).toHaveAttribute("data-reszleges", "1");
  await expect(c).toHaveAttribute("data-hianyzo", "24");
  await expect(c.locator(".merteszamok")).toContainText("140/144 óra nem-nulla");   // jel erőssége elöl
  await expect(c.locator(".merteszamok")).toContainText("144/168 lezárt");          // nevező = 144 + 24, zárójelben
});

// ── 7. §7.5 üres intervallum + lyukas sorozat (6a + 6b) ──────────────────────────────────────
test("7. üres intervallum → .ures + data-ok; lyukas sorozat → data-hianyzo>0 (a vonal a rajzolóban szakad)", async ({ page }) => {
  await mock(page, {
    regObj: reg({
      "ures": regSzo({ intervallumok: { "1_het": ivHibas("nincs_adat"),
        "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }),
      "lyukas": regSzo({ iv1het: { pontok_hasznalt: 144, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 24 } }),
    }),
    nyersObj: nyers({
      "ures": [nyersRekord("ures")],
      // BELSŐ lyuk: iso(0..71) + iso(96..167) = 144 lezárt, a 24 hiányzó óra iso(72..95) KÖZÉPEN;
      // a részleges a záró slotnál (iso(168), §6:213). Így a vonal ténylegesen MEGSZAKAD, nem farok-csonka.
      "lyukas": [nyersRekord("lyukas", 50, { pontok: [
        ...pontok(72, 50, { partial: false }),
        ...Array.from({ length: 72 }, (_, j) => ({ idopont_utc: iso(96 + j), ertek: 50, reszleges: false })),
        { idopont_utc: iso(168), ertek: 0, reszleges: true },
      ] })],
    }),
  });
  await page.goto("/");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="ures"] .ures`)).toBeVisible();
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="ures"]`)).toHaveAttribute("data-ok", "nincs_adat");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="lyukas"]`)).toHaveAttribute("data-hianyzo", "24");
  // a megszakadás tesztelhető tény: data-szakadas = a rajzolt dataset null-pontjainak száma (nincs interpoláció)
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="lyukas"]`)).toHaveAttribute("data-szakadas", "24");
});

// ── 8. élettartam-feliratok (mod 6) ──────────────────────────────────────────────────────────
// FIGYELEM: a "mérés kezdete" ág valós 1_het adaton SZERKEZETILEG elérhetetlen (a Google visszamenőleg
// adja a 7 napot → az első pont = az ablak kezdete). Ez láncolt (Phase 4) kódút → a "csonka" mock
// szándékosan fej-csonkolt sorozatot épít. A (c) mai konstelláció bizonyítja, hogy MA egyik sem szólal meg.
test("8. élettartam: fej-csonkolt→mérés kezdete, eltávolított→már nem mérjük, mai konstelláció→NINCS", async ({ page }) => {
  await mock(page, {
    regObj: reg({
      "csonka": regSzo({ meres_kezdete: "2026-08-01", iv1het: { pontok_hasznalt: 96, pontok_hianyzo: 72 } }),
      "regi": regSzo({ aktiv: false, meres_vege: "2026-08-01" }),
      "mai": regSzo({ meres_kezdete: "2026-07-30" }),
    }),
    nyersObj: nyers({
      "csonka": [nyersRekord("csonka", 50, { pontok: pontok(96, 50).map((p, i) => ({ ...p, idopont_utc: iso(72 + i) })) })],
      "regi": [nyersRekord("regi")],
      "mai": [nyersRekord("mai")],
    }),
  });
  await page.goto("/");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="csonka"] .elettartam`)).toContainText("mérés kezdete");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="regi"] .elettartam`)).toContainText("már nem mérjük");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="mai"]`)).toBeVisible();          // a kártya renderel
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="mai"] .elettartam`)).toHaveCount(0);
});

// ── 9. csupa-nulla vs nem-nulla (#4) ─────────────────────────────────────────────────────────
test("9. minden lezárt pont 0 → .csupa-nulla + chart renderel; nem-nulla szó → NINCS .csupa-nulla", async ({ page }) => {
  await mock(page, {
    regObj: reg({
      "nulla": regSzo({ iv1het: { meredekseg_nap: 0.0, irany: "stagnal", r2: 0.0,
        illesztes_vonal: [{ idopont_utc: ELSO, ertek: 0 }, { idopont_utc: UTOLSO_LEZART, ertek: 0 }] } }),
      "aktiv": regSzo(),
    }),
    nyersObj: nyers({ "nulla": [nyersRekord("nulla", 0)], "aktiv": [nyersRekord("aktiv", 50)] }),
  });
  await page.goto("/");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="nulla"] .csupa-nulla`)).toBeVisible();
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="nulla"] canvas`)).toHaveCount(1);
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="aktiv"] .csupa-nulla`)).toHaveCount(0);
});

// ── 10. alapértelmezett = leghosszabb + váltás + aria-szinkron (mod 3, 4. pont) ──────────────
test("10. default a leghosszabb érvényes; kattintásra data-ablak-veg + data-pontok VÁLTOZIK; pontosan 1 aria-pressed", async ({ page }) => {
  const veg1het = VEG, pont1het = 168;
  const veg1ho = iso(720), pont1ho = 720;   // fiktív, mock-vezérelt (1_ho ma csak mockkal drawable)
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivErvenyes({ ablak_veg_utc: veg1het, pontok_hasznalt: pont1het }),
      "1_ho": ivErvenyes({ ablak_veg_utc: veg1ho, pontok_hasznalt: pont1ho }),
      "2_het": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
    } }) }),
    nyersObj: nyers({ "állás": [
      nyersRekord("állás", 50, { veg: veg1het, n: 168 }),
      nyersRekord("állás", 50, { kezd: iso(0), veg: veg1ho, pontok: pontok(pont1ho, 50) }),
    ] }),
  });
  await page.goto("/");
  await expect(page.locator(K)).toHaveAttribute("data-aktiv-intervallum", "1_ho");   // leghosszabb érvényes
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`)).toHaveAttribute("data-ablak-veg", veg1ho);
  await page.locator('#intervallum-vezerlo button[data-intervallum="1_het"]').click();
  await expect(page.locator(K)).toHaveAttribute("data-aktiv-intervallum", "1_het");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`)).toHaveAttribute("data-ablak-veg", veg1het);
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`)).toHaveAttribute("data-pontok", String(pont1het));
  await expect(page.locator('#intervallum-vezerlo button[aria-pressed="true"]')).toHaveCount(1);
  await expect(page.locator('#intervallum-vezerlo button[aria-pressed="true"]')).toHaveAttribute("data-intervallum", "1_het");
});

// ── 11. lusta renderelés (mod 3) ─────────────────────────────────────────────────────────────
test("11. kis viewport → csak az első kártyák data-rendered; scroll → a lejjebbi is megkapja", async ({ page }) => {
  const szavak = {}; const nyersMap = {};
  for (let i = 0; i < 8; i++) { szavak["szo" + i] = regSzo(); nyersMap["szo" + i] = [nyersRekord("szo" + i)]; }
  await mock(page, { regObj: reg(szavak), nyersObj: nyers(nyersMap) });
  await page.setViewportSize({ width: 380, height: 320 });
  await page.goto("/");
  const rendered = page.locator(`${K} .kulcsszo-chart[data-rendered="true"]`);
  await expect(rendered).not.toHaveCount(0);                                         // auto-retry: várd meg az IO-callbacket
  expect(await rendered.count()).toBeLessThan(8);                                    // de NEM mind renderelt egyszerre
  await page.locator(`${K} .kulcsszo-chart[data-kulcsszo="szo7"]`).scrollIntoViewIfNeeded();
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="szo7"]`)).toHaveAttribute("data-rendered", "true");
});

// ── 12. Y-tengely fix 0–100 + felirat (#9) ───────────────────────────────────────────────────
test("12. data-y-max=100 + tengely-felirat", async ({ page }) => {
  await mock(page, { regObj: reg({ "állás": regSzo() }), nyersObj: nyers({ "állás": [nyersRekord("állás")] }) });
  await page.goto("/");
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`);
  await expect(c).toHaveAttribute("data-y-max", "100");
  // (a): a tengely-felirat DOM-elemként a kártyán — a Chart.js scales.title a CANVASBA rajzol,
  // a Playwright azt nem olvassa; a §7.2 „a tengely mondja ki a relatív skálát" tesztelendő tény.
  await expect(c.locator(".tengely-felirat")).toHaveText("relatív keresési szint (0–100)");   // EN DASH "–"
});

// ── 13. frissesség-felirat követi az aktív intervallumot + dátum az ablak_veg_utc-ból (mod 5, F1) ─
test("13. .frissesseg: cimke + dátum az aktív intervallumból (nem a szamitva_utc-ból); váltásra követi", async ({ page }) => {
  const veg1het = VEG /* 08-05 */, veg1ho = iso(720);
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivErvenyes({ ablak_veg_utc: veg1het }),
      "1_ho": ivErvenyes({ ablak_veg_utc: veg1ho }),
      "2_het": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
    } }) }, { szamitva_utc: "2026-08-06T02:00:00+00:00" /* KÉSŐBBI nap, mint az ablak_veg */ }),
    nyersObj: nyers({ "állás": [
      nyersRekord("állás", 50, { veg: veg1het }),
      nyersRekord("állás", 50, { kezd: iso(0), veg: veg1ho, pontok: pontok(720, 50) }),
    ] }),
  });
  await page.goto("/");
  const f = page.locator(`${K} .frissesseg`);
  await expect(f).toContainText("(1 hó)");                                           // default = leghosszabb
  await expect(f).toContainText(veg1ho.slice(0, 10).replace(/-/g, ". ") + ".");      // az ablak_veg napja, NEM 08-06
  await page.locator('#intervallum-vezerlo button[data-intervallum="1_het"]').click();
  await expect(f).toContainText("(1 hét)");
  await expect(f).toContainText("2026. 08. 05.");
});

// ── 14. nincs illeszkedő nyers ablak → .ures, NINCS .merteszamok, NINCS canvas (2. pont, bináris) ─
test("14. ervenyes:true de nincs veg-egyező nyers ablak → data-drawable=false, .ures, NINCS .merteszamok/canvas/data-ablak-veg", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo() }),                    // 1_het ablak_veg = VEG
    nyersObj: nyers({ "állás": [nyersRekord("állás", 50, { veg: iso(24) })] }),   // NINCS VEG-egyező ablak
  });
  await page.goto("/");
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`);
  await expect(c).toHaveAttribute("data-drawable", "false");
  await expect(c.locator(".ures")).toBeVisible();
  await expect(c.locator(".merteszamok")).toHaveCount(0);   // BINÁRIS: nem-rajzolható → nincs mérőszám
  await expect(c.locator("canvas")).toHaveCount(0);
  await expect(c).not.toHaveAttribute("data-ablak-veg", /.*/);   // az attribútum HIÁNYZIK (nem hazudik), nem csak ≠ VEG
  await expect(page.locator(`${K} .frissesseg`)).toHaveCount(0);  // D1: nincs RAJZOLHATÓ kártya → nincs frissesség-dátum
});

// ── 15a. nincs aktív intervallum (a): ÜRES regresszió → Task 6 URES_NINCS_ADAT ─────────────────
// FIGYELEM: a .frissesseg elhagyása a §7.4 "Felirat kötelező" FELTÉTELES olvasata: nincs rajzolt
// intervallum → nincs mit dátumozni (nem hiba). SZÁNDÉKOSAN ZÖLD a stub-körben (regresszió-őr): a
// mai app.js már teljesíti a hiány-asserteket; a Task 6 (a) smoke párja (e2e/vezerlok.spec.js).
// A "hiányzó" (404) esetet a Task 5 loader .hiba-ja fedi (loader.spec.js) — itt az ÜRES ág, hogy a
// "NINCS .hiba" a 9b nem-dobásáról szóljon, ne a loader 404-jéről.
test("15a. üres kulcsszo_regresszio.json → nincs 9b-DOM, nincs .hiba, Task 6 URES_NINCS_ADAT megmarad", async ({ page }) => {
  await mock(page, { regObj: reg({}), nyersObj: nyers({}) });
  await page.goto("/");
  await expect(page.locator(`${K} .kulcsszo-chart`)).toHaveCount(0);
  await expect(page.locator(`${K} .frissesseg`)).toHaveCount(0);
  await expect(page.locator(K)).not.toHaveAttribute("data-aktiv-intervallum", /.*/);
  await expect(page.locator(`${K} .hiba`)).toHaveCount(0);                           // a 9b NEM kivétellel kezeli
  await expect(page.locator("#intervallum-vezerlo .ures")).toBeVisible();            // Task 6 URES_NINCS_ADAT
});

// ── 15b. nincs aktív intervallum (b): van adat, de EGYIK intervallum sem érvényes ──────────────
// SZÁNDÉKOSAN ZÖLD (regresszió-őr) — a Task 6 (b) smoke párja: az 5 letiltott gomb + ok-szöveg
// VÁLTOZATLANUL ott marad, a 9b render nem írja felül és nem dob kivételt.
test("15b. minden intervallum ervenyes:false → 5 letiltott gomb marad, nincs 9b-DOM, nincs .hiba", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivHibas("nincs_adat"), "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
      "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
    } }) }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
  });
  await page.goto("/");
  await expect(page.locator("#intervallum-vezerlo .ures")).toBeVisible();            // Task 6 URES_NINCS_ERVENYES
  await expect(page.locator("#intervallum-vezerlo button[disabled]")).toHaveCount(5);
  await expect(page.locator(`${K} .kulcsszo-chart`)).toHaveCount(0);
  await expect(page.locator(`${K} .frissesseg`)).toHaveCount(0);
  await expect(page.locator(`${K} .hiba`)).toHaveCount(0);
});

// ── 16. veg-egyező ablak LEZÁRT PONT NÉLKÜL (§7.5 2. eset, J2) ────────────────────────────────
test("16. veg-egyező nyers ablak LEZÁRT pont nélkül → data-drawable=false, .ures, NINCS canvas/merteszamok, NINCS .hiba", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo() }),   // 1_het ervenyes, ablak_veg = VEG
    // veg-EGYEZŐ ablak, de CSAK részleges pont (nincs lezárt) → séma-érvényes, de kirajzolhatatlan
    nyersObj: nyers({ "állás": [{ kulcsszo: "állás", ablak_kezdet_utc: ELSO, ablak_veg_utc: VEG,
      pontok: [{ idopont_utc: VEG, ertek: 0, reszleges: true }] }] }),
  });
  await page.goto("/");
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`);
  await expect(c).toHaveAttribute("data-drawable", "false");
  await expect(c.locator(".ures")).toBeVisible();
  await expect(c.locator("canvas")).toHaveCount(0);
  await expect(c.locator(".merteszamok")).toHaveCount(0);
  await expect(page.locator(`${K} .hiba`)).toHaveCount(0);   // nem kivétellel kezeljük (nincs racs_epit TypeError)
});

// ── 17. ora_index hónap-/évhatáron át (J4) — a böngészőbeli egész-aritmetika olcsó fedezete ───
test("17. ablak 2027-12-28 → 2028-01-04 belső lyukkal → data-szakadas pontos (ora_index év-/hónaphatár)", async ({ page }) => {
  const YMS = Date.parse("2027-12-28T00:00:00Z");
  const yiso = function (h) { return new Date(YMS + h * 3600000).toISOString().replace(".000Z", "+00:00"); };
  const pts = [];
  for (let i = 0; i < 72; i++) pts.push({ idopont_utc: yiso(i), ertek: 50, reszleges: false });     // 12-28..12-30
  for (let i = 96; i < 168; i++) pts.push({ idopont_utc: yiso(i), ertek: 50, reszleges: false });   // 24h BELSŐ lyuk: yiso(72..95)
  pts.push({ idopont_utc: yiso(168), ertek: 0, reszleges: true });
  const ivY = ivErvenyes({ ablak_kezdet_utc: yiso(0), ablak_veg_utc: yiso(168),
    pontok_hasznalt: 144, pontok_hianyzo: 24,
    illesztes_vonal: [{ idopont_utc: yiso(0), ertek: 35 }, { idopont_utc: yiso(167), ertek: 42 }] });
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivY, "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
      "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }) }),
    nyersObj: nyers({ "állás": [{ kulcsszo: "állás", ablak_kezdet_utc: yiso(0), ablak_veg_utc: yiso(168), pontok: pts }] }),
  });
  await page.goto("/");
  // a rács [elso_idx, veg_idx) az évhatáron át 168 slot; 144 jelen + 24 null → ha a napok_civil hibázna a
  // hónap-/évhatáron, a rácsméret elcsúszna és a szakadás ≠ 24 lenne
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`)).toHaveAttribute("data-szakadas", "24");
});

// ── 18. illesztes_vonal végpontja a RÉSZLEGES záró pont (a rajzolt rácson KÍVÜL) — V1, a 4c testvére ─────
// A 4c a "sehol sem szerepel" esetet gyakorolta; ez a "szerepel, de nem a rajzolt LEZÁRT rácson" esetet
// (a részleges záró = a mini-9a M1 mutációja: a részleges pontot horgonyozza). A régi idopont_halmaz-guard
// átengedte volna (a részleges is benne volt) → tömbön kívüli írás; a V1-javított guard elutasítja.
test("18. illesztes_vonal végpontja a részleges záró pont → data-vonal=false, canvas megvan, nincs kivétel", async ({ page }) => {
  const ivR = ivErvenyes({ illesztes_vonal: [{ idopont_utc: ELSO, ertek: 35 }, { idopont_utc: VEG, ertek: 42 }] });  // VEG = a részleges záró slot
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivR, "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
      "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }) }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),   // 168 lezárt + részleges VEG-nél
  });
  await page.goto("/");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`)).toHaveAttribute("data-vonal", "false");
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"] canvas`)).toHaveCount(1);
  await expect(page.locator(`${K} .hiba`)).toHaveCount(0);
});

// ── 20. LÁTHATÓ kulcsszó-címke minden kártyán (H1) — rajzolható ÉS nem-rajzolható is ──────────
// A szó eddig csak a data-kulcsszo attribútumban volt (gépnek, nem embernek); a canvas fölé LÁTHATÓ
// h4.kulcsszo-cimke kell, a szó szövegével, ékezetes szónál is, és a .ures kártyán KÜLÖNÖSEN (ott csak
// egy magyarázó mondat áll szó nélkül). A címke szövege PONTOSAN a data-kulcsszo értéke.
test("20. minden kártyán LÁTHATÓ .kulcsszo-cimke a szó pontos szövegével (rajzolható + üres, ékezetes)", async ({ page }) => {
  await mock(page, {
    regObj: reg({
      "albérlet": regSzo({ domen: "lakhatas" }),                       // rajzolható, ékezetes
      "tüntetés": regSzo({ domen: "kozelet" }),                        // rajzolható, ékezetes
      // ervenyes:false → nem rajzolható (.ures), itt KÜLÖNÖSEN kell a látható szó
      "hitel": regSzo({ domen: "lakhatas", intervallumok: {
        "1_het": ivHibas("nincs_adat"), "2_het": ivHibas("nincs_lancolas"),
        "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }),
    }),
    nyersObj: nyers({ "albérlet": [nyersRekord("albérlet")], "tüntetés": [nyersRekord("tüntetés")], "hitel": [nyersRekord("hitel")] }),
  });
  await page.goto("/");
  for (const szo of ["albérlet", "tüntetés", "hitel"]) {
    const cimke = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="${szo}"] h4.kulcsszo-cimke`);
    await expect(cimke).toHaveCount(1);
    await expect(cimke).toHaveText(szo);   // PONTOS egyezés a data-kulcsszo értékkel
  }
  // a nem-rajzolható kártyán a címke a magyarázó szöveg MELLETT áll (nem helyette)
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="hitel"][data-drawable="false"] .ures`)).toBeVisible();
});

// ── 21. B1: a frissesség-dátum az utolsó KIRAJZOLT LEZÁRT pontból, NEM az ablak_veg (részleges slot) ─
// A ~00:43 UTC-s futás konstellációja: az ablak T00:00-ra záródik (RÉSZLEGES slot, MÁSNAP), az utolsó
// LEZÁRT pont az ELŐZŐ nap T23:00. Eddig a felirat az ablak_veg napját írta ki (tautológia) → egy nappal
// többet állított, mint amennyi adat ki van rajzolva. A felirat az utolsó lezárt pont napját mutassa.
// MUTÁCIÓ (vissza ablak_veg-re) ezt PIROSÍTJA. A ~20:37-es futásoknál a két nap egybeesik → 13. zöld marad.
test("21. frissesség-dátum = utolsó kirajzolt lezárt pont napja (00:43-futás: ablak_veg másnap T00:00)", async ({ page }) => {
  const ABL_KEZD = "2026-08-06T00:00:00+00:00";
  const UTOLSO   = "2026-08-06T23:00:00+00:00";   // utolsó LEZÁRT pont — ez a HELYES „adat vége"
  const ABL_VEG  = "2026-08-07T00:00:00+00:00";   // RÉSZLEGES záró slot — MÁSNAP (a tautológia forrása)
  const lezartPontok = [];
  for (let h = 0; h < 24; h++) {                  // 24 lezárt óra 08-06-on (00:00..23:00)
    lezartPontok.push({ idopont_utc: `2026-08-06T${String(h).padStart(2, "0")}:00:00+00:00`, ertek: 30 + h, reszleges: false });
  }
  lezartPontok.push({ idopont_utc: ABL_VEG, ertek: 0, reszleges: true });   // részleges záró (08-07T00:00)
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivErvenyes({ ablak_kezdet_utc: ABL_KEZD, ablak_veg_utc: ABL_VEG, pontok_hasznalt: 24,
        illesztes_vonal: [{ idopont_utc: ABL_KEZD, ertek: 30 }, { idopont_utc: UTOLSO, ertek: 53 }] }),
      "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
      "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
    } }) }),
    nyersObj: nyers({ "állás": [{ kulcsszo: "állás", ablak_kezdet_utc: ABL_KEZD, ablak_veg_utc: ABL_VEG, pontok: lezartPontok }] }),
  });
  await page.goto("/");
  const f = page.locator(`${K} .frissesseg`);
  await expect(f).toContainText("(1 hét)");
  await expect(f).toContainText("2026. 08. 06.");        // az utolsó LEZÁRT pont napja (a kirajzolt adat vége)
  await expect(f).not.toContainText("2026. 08. 07.");    // az ablak_veg (részleges slot) napja NEM jelenhet meg
});
