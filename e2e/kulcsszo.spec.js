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

// ── LANC-ORAS Sz2 lánc-fixture: a tárolt kulcsszo_lanc.json alakja EGY rekord/szó (nem ablak-lista),
// reszleges NÉLKÜL. A 2_het a lánc-vég − 14 nap farkából rajzol (RACS_ABLAK_NAP["ora"]==7 → csak az
// 1_het jön a nyersből, a 2_het+ a láncból). Megosztott a 10./13./18. teszt közt.
const LVEG = iso(360);          // lánc-vég (15 nappal a KEZD után) — NINCS veg-egyező nyers ablak (a nyers VEG=iso168)
const L2HET_KEZD = iso(24);     // 2_het = a lánc-vég − 14 nap (336 óra)
function lancRek() {
  const pts = [];
  for (let i = 0; i <= 360; i++) pts.push({ idopont_utc: iso(i), ertek: 40 + (i % 20) });
  return { ablak_kezdet_utc: iso(0), ablak_veg_utc: LVEG, pontok: pts };
}
// a 2_het lánc-interval (a backend a lanc["ablak_veg_utc"]-ig szeletel; a frontend a láncból rajzolja)
function iv2hetLanc() {
  return ivErvenyes({ ablak_kezdet_utc: L2HET_KEZD, ablak_veg_utc: LVEG, pontok_hasznalt: 337,
    illesztes_vonal: [{ idopont_utc: L2HET_KEZD, ertek: 40 }, { idopont_utc: LVEG, ertek: 55 }] });
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
// 6c: esemenyjelzo szeletelt intervallum — a backend a TREND-mezőket strippeli (nincs illesztes_vonal/
// irany/meredekseg/r2/se) → a frontend NEM rajzol trendvonalat, csak a konstans szint-vonalat (data-szint-ből)
function racs_iv_szint(n, lepes_nap) {
  const iv = racs_iv(n, lepes_nap);
  ["illesztes_vonal", "irany", "meredekseg_nap", "r2", "se_meredekseg",
   "se_masodlagos_autokorrelacio", "r2_masodlagos_autokorrelacio"].forEach(function (k) { delete iv[k]; });
  return iv;
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

// A másodlagos fájlokat MINDIG route-oljuk (default üres), különben a teszt-szerver VALÓS
// másodlagos adata szivárogna be és eltolná a nem-másodlagos teszteket (routing/alap-intervallum).
async function mock(page, { regObj, nyersObj, mpRegObj, mpNyersObj, lancObj }) {
  await page.route(/kulcsszo_masodlagos_regresszio\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify(mpRegObj || { kulcsszavak: {} }) }));
  await page.route(/kulcsszo_masodlagos_nyers\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify(mpNyersObj || { kulcsszavak: {} }) }));
  // LANC-ORAS Sz2: a lánc-fájlt MINDIG route-oljuk (default üres), különben a frontend a valós
  // kulcsszo_lanc.json-t kérné a statikus szerverről és eltolná a nem-lánc teszteket (mint a másodlagos).
  await page.route(/kulcsszo_lanc\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify(lancObj || { kulcsszavak: {} }) }));
  await page.route(/kulcsszo_regresszio\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify(regObj) }));
  await page.route(/kulcsszo_nyers\.json/, (r) =>
    r.fulfill({ contentType: "application/json", body: JSON.stringify(nyersObj) }));
}

// másodlagos regresszió-fixture (szó-szintű racs; az intervallumok racs_iv/ivHibas alakúak)
function mpReg(kulcsszavak) {
  return { szamitva_utc: "2026-08-15T19:29:00+00:00", meredekseg_egyseg: "relatív pont / nap",
    elmozdulas_kuszob: 7.0, megjegyzes: "teszt", kulcsszavak };
}
function mpSzo(racs, intervallumok, over = {}) {
  const o = { racs, aktiv: over.aktiv ?? true, domen: over.domen ?? "lakhatas", tipus: over.tipus ?? "szintmero",
    meres_kezdete: over.meres_kezdete ?? null, meres_vege: over.meres_vege ?? null, intervallumok };
  if (over.szint != null) { o.szint = over.szint; o.szint_modszer = over.szint_modszer ?? "median"; }   // 6c esemenyjelzo
  return o;
}
function mpNyers(map) { return { kulcsszavak: map }; }

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
test("2a. nap-config szó MÁSODLAGOS nézete → 'nap nem-nulla' felirat (a config-rács a másodlagoshoz tartozik)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "albérlet": regSzo({ racs: "nap", domen: "lakhatas" }) }),   // primer 1_het órás valid
    nyersObj: nyers({ "albérlet": [nyersRekord("albérlet")] }),
    mpRegObj: mpReg({ "albérlet": mpSzo("nap", { "1_ho": racs_iv(30, 1) }) }),
    mpNyersObj: mpNyers({ "albérlet": [racs_nyersRekord("albérlet", 30, 1)] }),
  });
  await page.goto("/");
  await page.click('#intervallum-vezerlo button[data-intervallum="1_ho"]');   // a másodlagos (napi) nézet
  const m = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="albérlet"] .merteszamok`);
  await expect(m).toContainText("30/30 nap nem-nulla");   // a rács-szó a MÁSODLAGOS m.racs-ából
  await expect(m).not.toContainText("óra nem-nulla");     // az "óra" nem szivárog át
});

// ── 2a-FIX (SZEMLE 08-19): a PRIMER 1_het MINDIG órás (now 7-d, 168 pont) — a config-rács (nap/het) CSAK a
// másodlagos ágra vonatkozik. A nap-config szó 1_het-je NEM napi-collapse (7 pont, „nap"), hanem 168 órás pont,
// „óra nem-nulla" felirattal. Ez javítja a hitel/napelem lapos-nulla + félrecímke leletet (a _racs config↔felbontás
// összemosása). A 2a/2b (config-rács a primer feliratban) ezzel átfordul; a rács-szó helper a MÁSODLAGOSNÁL marad.
test("2a-FIX. nap-config szó PRIMER 1_het → órás (168 pont, 'óra nem-nulla'), NEM napi-collapse", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "albérlet": regSzo({ racs: "nap", domen: "lakhatas" }) }),   // config nap, de a primer 1_het órás (168)
    nyersObj: nyers({ "albérlet": [nyersRekord("albérlet")] }),                 // 168 órás pont
  });
  await page.goto("/");
  const k = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="albérlet"]`);
  expect(await k.getAttribute("data-felbontas")).toBe("ora");                   // NEM "nap"
  expect(await k.getAttribute("data-rajzolt-pont")).toBe("168");               // NEM 7 (nap-collapse)
  await expect(k.locator(".merteszamok")).toContainText("166/168 óra nem-nulla");   // NEM "nap nem-nulla"
});

// ── 2b. RACS_EGYSEG: ismeretlen rács → LÁTHATÓ fallback, nem néma "óra", nem undefined ─────────
test("2b. ismeretlen MÁSODLAGOS rács → látható '? <érték>' fallback (nem 'óra', nem 'undefined')", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo({ domen: "munkaeropiac" }) }),   // primer 1_het órás valid
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
    mpRegObj: mpReg({ "állás": mpSzo("negyedev", { "1_ho": racs_iv(30, 1) }, { domen: "munkaeropiac" }) }),
    mpNyersObj: mpNyers({ "állás": [racs_nyersRekord("állás", 30, 1)] }),
  });
  await page.goto("/");
  await page.click('#intervallum-vezerlo button[data-intervallum="1_ho"]');   // a másodlagos (ismeretlen rácsú) nézet
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
test("2d. nap-rácsú MÁSODLAGOS napi pontokkal → data-szakadas=0 (napi slot, nem órás-slotokra szórva)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "albérlet": regSzo({ racs: "nap", domen: "lakhatas" }) }),   // primer 1_het órás valid
    nyersObj: nyers({ "albérlet": [nyersRekord("albérlet")] }),
    mpRegObj: mpReg({ "albérlet": mpSzo("nap", { "1_ho": racs_iv(30, 1) }) }),   // 30 napi lezárt pont, 1-nap köz
    mpNyersObj: mpNyers({ "albérlet": [racs_nyersRekord("albérlet", 30, 1)] }),
  });
  await page.goto("/");
  await page.click('#intervallum-vezerlo button[data-intervallum="1_ho"]');
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="albérlet"]`);
  await expect(c).toHaveAttribute("data-drawable", "true");
  await expect(c).toHaveAttribute("data-felbontas", "nap");
  await expect(c).toHaveAttribute("data-szakadas", "0");   // napi rács folytonos, NEM 24-óránként szórt
});

// ── 2e. RACS rajzolás (Szelet 1): het-rácsú szó → heti slot-rács, FOLYTONOS (data-szakadas=0) ──
test("2e. het-rácsú MÁSODLAGOS heti pontokkal → data-szakadas=0 (heti slot, nem órás)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "akciós újság": regSzo({ racs: "het", domen: "fogyasztas" }) }),   // primer 1_het órás valid
    nyersObj: nyers({ "akciós újság": [nyersRekord("akciós újság")] }),
    mpRegObj: mpReg({ "akciós újság": mpSzo("het", { "3_ho": hetIvErv(0, 12) }, { domen: "fogyasztas" }) }),   // 12 heti pont, 7-nap köz
    mpNyersObj: mpNyers({ "akciós újság": [racs_nyersRekord("akciós újság", 12, 7)] }),
  });
  await page.goto("/");
  await page.click('#intervallum-vezerlo button[data-intervallum="3_ho"]');
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="akciós újság"]`);
  await expect(c).toHaveAttribute("data-drawable", "true");
  await expect(c).toHaveAttribute("data-felbontas", "het");
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

// ── 2g. Szelet 2 routing: másodlagos 1_ho érvényes → az 1_ho gomb ENGEDÉLYEZETT ────────────────
test("2g. másodlagos 1_ho érvényes → az 1_ho intervallum-gomb engedélyezett", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "albérlet": regSzo({ domen: "lakhatas" }) }),   // órás: 1_het valid, 1_ho nincs_lancolas
    nyersObj: nyers({ "albérlet": [nyersRekord("albérlet")] }),
    mpRegObj: mpReg({ "albérlet": mpSzo("nap", { "1_ho": racs_iv(30, 1) }) }),
    mpNyersObj: mpNyers({ "albérlet": [racs_nyersRekord("albérlet", 30, 1)] }),
  });
  await page.goto("/");
  await expect(page.locator('#intervallum-vezerlo button[data-intervallum="1_ho"]')).toBeEnabled();
});

// ── 2h. Szelet 2 üres-állapot: másodlagos NÉLKÜLI hosszú intervallum → "napi/heti adatot" ───────
test("2h. benzin (órás-only) hosszú intervallum → 'órás sorozat láncolása kell' (JOGOSULATLAN-URES-UZENET fix, item 5)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "benzin": regSzo({ domen: "fogyasztas", racs: "ora" }) }),   // csak órás, NINCS másodlagos
    nyersObj: nyers({ "benzin": [nyersRekord("benzin")] }),
    // mpRegObj/mpNyersObj: default üres → benzinnek nincs másodlagosa
  });
  await page.goto("/");
  const v = page.locator("#intervallum-vezerlo");
  // benzin órás-only (racs="ora") → oras_lanc_kell, NEM a félrevezető "napi/heti adatot" (sosem lesz napi/heti)
  await expect(v).toContainText("Órás felbontású szó – ehhez az ablakhoz az órás sorozat láncolása kell.");
  await expect(v).not.toContainText("nem gyűjtöttünk napi/heti");   // a félrevezető üzenet NEM
  await expect(v).not.toContainText("összefűzött nap");             // az órás-láncolás régi felirat NEM
});

// ── 2i. Szelet 2 integráció: másodlagos szó a hosszú intervallumon → "nap nem-nulla" ────────────
test("2i. másodlagos szó 1_ho-ra váltva → kártya drawable, 'nap nem-nulla'", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "albérlet": regSzo({ domen: "lakhatas" }) }),   // 1_het órás valid
    nyersObj: nyers({ "albérlet": [nyersRekord("albérlet")] }),
    mpRegObj: mpReg({ "albérlet": mpSzo("nap", { "1_ho": racs_iv(30, 1) }) }),
    mpNyersObj: mpNyers({ "albérlet": [racs_nyersRekord("albérlet", 30, 1)] }),
  });
  await page.goto("/");
  // ALAPNEZET (Szelet 3): a default 1_het → a másodlagos 1_ho nézethez kattintani kell
  await page.click('#intervallum-vezerlo button[data-intervallum="1_ho"]');
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="albérlet"]`);
  await expect(c).toHaveAttribute("data-drawable", "true");
  await expect(c.locator(".merteszamok")).toContainText("nap nem-nulla");   // a másodlagos napi adat rajzol
});

// ── 2j. Szelet 2 szándékos-zöld: 1_het MINDIG órás, akkor is ha van másodlagos ─────────────────
test("2j. 1_het órás marad másodlagos jelenlétében is → 'óra nem-nulla' — SZANDEKOS_ZOLD", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "albérlet": regSzo({ domen: "lakhatas" }) }),
    nyersObj: nyers({ "albérlet": [nyersRekord("albérlet")] }),
    mpRegObj: mpReg({ "albérlet": mpSzo("nap", { "1_ho": racs_iv(30, 1) }) }),
    mpNyersObj: mpNyers({ "albérlet": [racs_nyersRekord("albérlet", 30, 1)] }),
  });
  await page.goto("/");
  await page.click('#intervallum-vezerlo button[data-intervallum="1_het"]');   // váltás az órás nézetre
  const m = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="albérlet"] .merteszamok`);
  await expect(m).toContainText("166/168 óra nem-nulla");   // 1_het = órás, a másodlagos nem írja felül
});

// ── 2k. Szelet 3 / HIBA 1: nap-szó 1_ev másodlagos nincs_lancolas → NEM "összefűzött nap" ──────
test("2k. nap-szó másodlagos 1_ev nincs_lancolas → 'A napi/heti sorozat rövidebb…' (nem 'összefűzött')", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "nyaralás": regSzo({ domen: "fogyasztas" }) }),   // órás 1_het valid, 1_ev nincs_lancolas
    nyersObj: nyers({ "nyaralás": [nyersRekord("nyaralás")] }),
    mpRegObj: mpReg({ "nyaralás": mpSzo("nap", { "2_het": racs_iv(14, 1), "1_ev": ivHibas("nincs_lancolas") }, { domen: "fogyasztas" }) }),
    mpNyersObj: mpNyers({ "nyaralás": [racs_nyersRekord("nyaralás", 14, 1)] }),
  });
  await page.goto("/");
  const v = page.locator("#intervallum-vezerlo");
  await expect(v).toContainText("A napi/heti sorozat még rövidebb ennél az ablaknál. Magától feltöltődik.");   // rovid_masodlagos — IDŐBELI
  await expect(v).not.toContainText("összefűzött");                                    // a félrevezető órás-láncolás felirat NEM
});

// ── 2l. Szelet 3 / HIBA 2: het-szó 2_het keves_pont → "heti rácson…túl rövid" (nem adathiány) ──
test("2l. het-szó 2_het keves_pont → 'A heti rácson ez az ablak túl rövid' (nem 'Túl kevés mért pont')", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "akciós újság": regSzo({ domen: "fogyasztas" }) }),
    nyersObj: nyers({ "akciós újság": [nyersRekord("akciós újság")] }),
    mpRegObj: mpReg({ "akciós újság": mpSzo("het", { "3_ho": racs_iv(12, 7), "2_het": ivHibas("keves_pont") }, { domen: "fogyasztas" }) }),
    mpNyersObj: mpNyers({ "akciós újság": [racs_nyersRekord("akciós újság", 12, 7)] }),
  });
  await page.goto("/");
  const v = page.locator("#intervallum-vezerlo");
  await expect(v).toContainText("Heti felbontású szó – ez az ablak túl rövid a heti rácshoz. Ez nem fog feltöltődni.");   // rovid_het_ablak — ELVI
  await expect(v).not.toContainText("Túl kevés mért pont");               // az adathiányt sugalló felirat NEM
});

// ── 2n. 6c/Szelet 1: esemenyjelzo (tüntetés) 1_het → rovid_het_ablak, NEM a nyugdíjazott felirat ──
test("2n. esemenyjelzo het-szó 1_het → 'A heti rácson ez az ablak túl rövid' (nem 'Eseményjelző — szint-nézet készül')", async ({ page }) => {
  await mock(page, {
    // Szelet 1 UTÁNI backend-alak: az órás ág esemenyjelzo → MINDEN intervallum ervenyes:false, ok:"esemenyjelzo"
    regObj: reg({ "tüntetés": regSzo({ domen: "kozelet", tipus: "esemenyjelzo", intervallumok: {
      "1_het": ivHibas("esemenyjelzo"), "2_het": ivHibas("esemenyjelzo"), "1_ho": ivHibas("esemenyjelzo"),
      "3_ho": ivHibas("esemenyjelzo"), "1_ev": ivHibas("esemenyjelzo"),
    } }) }),
    nyersObj: nyers({ "tüntetés": [nyersRekord("tüntetés")] }),
    // másodlagos het szeletelve: 1_het/2_het/1_ho keves_pont (rövid heti ablak); 3_ho/1_ev érvényes (rajzol)
    mpRegObj: mpReg({ "tüntetés": mpSzo("het",
      { "1_het": ivHibas("keves_pont"), "2_het": ivHibas("keves_pont"), "1_ho": ivHibas("keves_pont"),
        "3_ho": racs_iv(12, 7), "1_ev": racs_iv(52, 7) },
      { domen: "kozelet", tipus: "esemenyjelzo" }) }),
    mpNyersObj: mpNyers({ "tüntetés": [racs_nyersRekord("tüntetés", 52, 7)] }),
  });
  await page.goto("/");
  const v = page.locator("#intervallum-vezerlo");
  await expect(v).toContainText("Heti felbontású szó – ez az ablak túl rövid a heti rácshoz. Ez nem fog feltöltődni.");  // esemenyjelzo 1_het → rovid_het_ablak (ELVI)
  await expect(v).not.toContainText("Eseményjelző — szint-nézet készül");  // a nyugdíjazott felirat NEM
});

// ── 2o. 6c/Szelet 2: esemenyjelzo szint-vonal rendering — data-szint + felirat (rács ÉS bázis KIMONDVA) ──
test("2o. esemenyjelzo tüntetés 3_ho/1_ev → data-szint='8' + 'szint: 8 (heti medián, 52 hét)' + NINCS trendvonal", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "tüntetés": regSzo({ domen: "kozelet", tipus: "esemenyjelzo", intervallumok: {
      "1_het": ivHibas("esemenyjelzo"), "2_het": ivHibas("esemenyjelzo"), "1_ho": ivHibas("esemenyjelzo"),
      "3_ho": ivHibas("esemenyjelzo"), "1_ev": ivHibas("esemenyjelzo"),
    } }) }),
    nyersObj: nyers({ "tüntetés": [nyersRekord("tüntetés")] }),
    // szint=8 szó-szinten; 3_ho/1_ev ervenyes, TREND-mezők NÉLKÜL (Szelet 1 strip); 1_het/2_het/1_ho keves_pont.
    // A szeletelt 3_ho/1_ev a rekord TELJES ablak_veg-jét örökli (a nyers_ablak erre illeszt) → mindkettő 52,7.
    mpRegObj: mpReg({ "tüntetés": mpSzo("het",
      { "1_het": ivHibas("keves_pont"), "2_het": ivHibas("keves_pont"), "1_ho": ivHibas("keves_pont"),
        "3_ho": racs_iv_szint(52, 7), "1_ev": racs_iv_szint(52, 7) },
      { domen: "kozelet", tipus: "esemenyjelzo", szint: 8 }) }),
    mpNyersObj: mpNyers({ "tüntetés": [racs_nyersRekord("tüntetés", 52, 7)] }),
  });
  await page.goto("/");
  await expect(page.locator(`${K} .hiba`)).toHaveCount(0);                       // a strippelt esemenyjelzo rajzolása NEM dob (merteszamok szint-ág)
  const kartya = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="tüntetés"]`);
  await expect(kartya).toHaveAttribute("data-szint", "8");                       // az érték a kártyán
  await expect(kartya).toContainText("szint: 8 (heti medián, 52 hét)");          // rács (heti) + bázis (52 hét) KIMONDVA
  await expect(kartya).toHaveAttribute("data-drawable", "true");                 // 1_ev (alapnézet) rajzol
  await expect(kartya).toHaveAttribute("data-vonal", "false");                   // NINCS második (trend)vonal a szint mellett
  // váltás 3_ho-ra: a felirat UGYANAZ (52 hetes szó-szintű bázis, (a) döntés — nem a 13 hetes ablak mediánja)
  await page.locator('button[data-intervallum="3_ho"]').click();
  await expect(kartya).toContainText("szint: 8 (heti medián, 52 hét)");
});

// ── 6c JAVÍTÓ-SZELET: a racs_epit az iv.ablak_kezdet_utc-re szeleteljen (latens 6b-hiba) ─────────
// het iv [kezdHet, vegHet) hetekben; ervenyes, trendvonallal (kontroll szintmero szó)
function hetIvErv(kezdHet, vegHet) {
  return { ervenyes: true, meredekseg_nap: 0.5, se_meredekseg: 0.3, se_masodlagos_autokorrelacio: true,
    irany: "novekszik", r2: 0.4, r2_masodlagos_autokorrelacio: true,
    ablak_kezdet_utc: racs_iso(kezdHet, 7), ablak_veg_utc: racs_iso(vegHet, 7),
    pontok_hasznalt: vegHet - kezdHet, pontok_nem_nulla: vegHet - kezdHet, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 0,
    illesztes_vonal: [{ idopont_utc: racs_iso(kezdHet, 7), ertek: 40 }, { idopont_utc: racs_iso(vegHet - 1, 7), ertek: 55 }] };
}
// het iv esemenyjelzo-alakban: ervenyes, TREND-mezők NÉLKÜL (Szelet 1 strip)
function hetIvSzint(kezdHet, vegHet) {
  return { ervenyes: true, ablak_kezdet_utc: racs_iso(kezdHet, 7), ablak_veg_utc: racs_iso(vegHet, 7),
    pontok_hasznalt: vegHet - kezdHet, pontok_nem_nulla: vegHet - kezdHet, pontok_kihagyva_reszleges: 1, pontok_hianyzo: 0 };
}
async function valt_es_olvas(page, szo, interv) {
  await page.locator(`button[data-intervallum="${interv}"]`).click();
  const k = page.locator(`#kulcsszo-blokk .kulcsszo-chart[data-kulcsszo="${szo}"]`);
  await k.waitFor();
  const rp = await k.getAttribute("data-rajzolt-pont");
  const belso = await page.evaluate((s) => {
    const el = document.querySelector(`#kulcsszo-blokk .kulcsszo-chart[data-kulcsszo="${s}"]`);
    const r = el && el._racs;
    return r ? { ert: r.ertekek.length, szintv: r.szint_vonal ? r.szint_vonal.length : null } : null;
  }, szo);
  return { rp, belso };
}

// 2p. KONTROLL (nem-esemenyjelzo): 3_ho RAJZOLT pont != 1_ev — a szeletelés az ablak_kezdet_utc-re megy
test("2p. kontroll het-szó (akciós újság): 3_ho rajzolt=13, 1_ev rajzolt=52 (nem azonos görbe)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "akciós újság": regSzo({ domen: "fogyasztas" }) }),   // órás 1_het ervenyes
    nyersObj: nyers({ "akciós újság": [nyersRekord("akciós újság")] }),
    mpRegObj: mpReg({ "akciós újság": mpSzo("het", { "1_het": ivHibas("keves_pont"), "2_het": ivHibas("keves_pont"),
      "1_ho": ivHibas("keves_pont"), "3_ho": hetIvErv(39, 52), "1_ev": hetIvErv(0, 52) }, { domen: "fogyasztas" }) }),
    mpNyersObj: mpNyers({ "akciós újság": [racs_nyersRekord("akciós újság", 52, 7)] }),
  });
  await page.goto("/");
  const h3 = await valt_es_olvas(page, "akciós újság", "3_ho");
  const ev = await valt_es_olvas(page, "akciós újság", "1_ev");
  expect(h3.rp).toBe("13");                       // 3_ho: 52-39 = 13 heti slot (a szeletelt ablak)
  expect(ev.rp).toBe("52");                       // 1_ev: a teljes 52 hét
  expect(h3.belso.ert).toBe(13);                  // a _racs.ertekek is szeletelt
  expect(ev.belso.ert).toBe(52);
});

// 2q. TÜNTETÉS szint-ág: 3_ho=12 / 1_ev=52 RAJZOLT pont, ÉS a szint-vonal hossza EGYÜTT MOZOG a szeletelt sorozattal
test("2q. tüntetés szint-ág: 3_ho rajzolt=12, 1_ev=52, és szint_vonal.length == ertekek.length", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "tüntetés": regSzo({ domen: "kozelet", tipus: "esemenyjelzo", intervallumok: {
      "1_het": ivHibas("esemenyjelzo"), "2_het": ivHibas("esemenyjelzo"), "1_ho": ivHibas("esemenyjelzo"),
      "3_ho": ivHibas("esemenyjelzo"), "1_ev": ivHibas("esemenyjelzo") } }) }),
    nyersObj: nyers({ "tüntetés": [nyersRekord("tüntetés")] }),
    mpRegObj: mpReg({ "tüntetés": mpSzo("het", { "1_het": ivHibas("keves_pont"), "2_het": ivHibas("keves_pont"),
      "1_ho": ivHibas("keves_pont"), "3_ho": hetIvSzint(40, 52), "1_ev": hetIvSzint(0, 52) },
      { domen: "kozelet", tipus: "esemenyjelzo", szint: 8 }) }),
    mpNyersObj: mpNyers({ "tüntetés": [racs_nyersRekord("tüntetés", 52, 7)] }),
  });
  await page.goto("/");
  const h3 = await valt_es_olvas(page, "tüntetés", "3_ho");
  const ev = await valt_es_olvas(page, "tüntetés", "1_ev");
  expect(h3.rp).toBe("12");                        // 3_ho: 52-40 = 12
  expect(ev.rp).toBe("52");
  expect(h3.belso.szintv).toBe(12);                // a szint-vonal EGYÜTT MOZOG a szeletelt sorozattal
  expect(h3.belso.szintv).toBe(h3.belso.ert);      // Array.fill(szint) hossza == ertekek hossza
  expect(ev.belso.szintv).toBe(52);
});

// ── 2m. Szelet 3 / ALAPNEZET: 1_het + hosszú érvényes → az ALAP az 1_het (nem a leghosszabb) ───
test("2m. van érvényes intervallum → az ALAPNEZET a TELJES (request 1), nem az 1_het/leghosszabb", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "albérlet": regSzo({ domen: "lakhatas" }) }),   // 1_het órás valid
    nyersObj: nyers({ "albérlet": [nyersRekord("albérlet")] }),
    mpRegObj: mpReg({ "albérlet": mpSzo("nap", { "3_ho": racs_iv(90, 1) }) }),   // 3_ho másodlagos valid
    mpNyersObj: mpNyers({ "albérlet": [racs_nyersRekord("albérlet", 90, 1)] }),
  });
  await page.goto("/");
  await expect(page.locator('#intervallum-vezerlo button[aria-pressed="true"]'))
    .toHaveAttribute("data-intervallum", "teljes");   // a kezdő nézet a teljes időszak (az oldal ezzel nyílik)
});

// ── TELJES-NEZET Szelet 1 (DOM-only routing) — 4 RED, mind AZONNALI AssertionError ──────────────
// A B/C/D a teljes módba evaluate(aktiv_intervallum_valt("teljes"))-szel lép: a még nem létező gombra
// kattintás TIMEOUT lenne (nem AssertionError); a gomb léte + huzalozása a T1 (gomb) dolga. A count()/
// getAttribute() + toBe() AZONNAL bukik (Expected/Received diff), nem retry-timeout.

// T1 (test_teljes_gomb_es_felirat): "Teljes időszak" gomb + sub-szöveg jelen, kattintás → data-aktiv="teljes"
test("teljes-nezet 1: 'Teljes időszak' gomb + sub-szöveg + kattintás huzalozás (data-aktiv-intervallum=teljes)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo() }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
  });
  await page.goto("/");
  const teljes = page.locator('#intervallum-vezerlo button[data-intervallum="teljes"]');
  expect(await teljes.count()).toBe(1);                                   // AZONNALI: 0 → 1
  expect((await teljes.textContent()).trim()).toContain("Teljes időszak");
  await expect(page.locator("#intervallum-vezerlo")).toContainText("szavanként eltérő indulással");   // a sub-szöveg (egyedi a teljes gombra)
  await teljes.click();
  expect(await page.locator("#kulcsszo-blokk").getAttribute("data-aktiv-intervallum")).toBe("teljes");
});

// T2 (test_teljes_per_szo_valasztas): minden szó a LEGHOSSZABB ÉRVÉNYES intervallumát választja
// (het→1_ev, nap→3_ho, ora→1_het) — data-teljes-forras a választott kulcs. A kórháznak 3_ho ÉS 1_ev is
// érvényes → az 1_ev (korábbi kezdet) nyer, NEM az első/egyetlen érvényes.
test("teljes-nezet 2: per-szó választás data-teljes-forras (het→1_ev, nap→3_ho, ora→1_het)", async ({ page }) => {
  await mock(page, {
    regObj: reg({
      "kórház": regSzo({ domen: "egeszseg", racs: "het", intervallumok: {
        "1_het": ivHibas("keves_pont"), "2_het": ivHibas("keves_pont"), "1_ho": ivHibas("keves_pont"),
        "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }),   // az órás mind érvénytelen → a másodlagos dönt
      "nyaralás": regSzo({ domen: "lakhatas", racs: "nap", intervallumok: {
        "1_het": ivHibas("keves_pont"), "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
        "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }),
      "benzin": regSzo({ domen: "fogyasztas", racs: "ora" }),                          // órás 1_het VALID → teljes = 1_het
    }),
    nyersObj: nyers({ "benzin": [nyersRekord("benzin")] }),
    mpRegObj: mpReg({
      "kórház": mpSzo("het", { "3_ho": hetIvErv(-12, 0), "1_ev": hetIvErv(-52, 0) }, { domen: "egeszseg" }),
      "nyaralás": mpSzo("nap", { "3_ho": racs_iv(90, 1) }, { domen: "lakhatas" }),
    }),
    mpNyersObj: mpNyers({
      "kórház": [racs_nyersRekord("kórház", 52, 7)],
      "nyaralás": [racs_nyersRekord("nyaralás", 90, 1)],
    }),
  });
  await page.goto("/");
  await expect(page.locator("#kulcsszo-blokk")).toHaveAttribute("data-aktiv-intervallum", "teljes");   // a teljes az ALAPNEZET (request 1)
  const forras = async (szo) => page.locator(`${K} .kulcsszo-chart[data-kulcsszo="${szo}"]`).getAttribute("data-teljes-forras");
  expect(await forras("kórház")).toBe("1_ev");     // het → a leghosszabb érvényes (nem a 3_ho)
  expect(await forras("nyaralás")).toBe("3_ho");   // nap → 3_ho
  expect(await forras("benzin")).toBe("1_het");    // ora → 1_het (nincs másodlagos, GATE)
});

// (A korábbi „teljes-nezet 3: közös kezdet (data-teljes-kezdet)" teszt TÖRÖLVE — a SZEMLE 08-19 per-szó
//  tengely döntéssel a közös tengely + data-teljes-kezdet megszűnt; a per-szó választást a teljes-nezet 2 fedi.)

// T4 (test_teljes_ures_ok_kod): egy szónak EGY érvényes intervalluma sincs (sem órás, sem másodlagos) →
// ÚJ, KÜLÖN ok-kód "teljes_nincs_sorozat", NEM a meglévők egyike. (állás valid → a teljes mód aktív.)
test("teljes-nezet 4: mind-érvénytelen szó → data-ok='teljes_nincs_sorozat' (új, külön ok-kód)", async ({ page }) => {
  await mock(page, {
    regObj: reg({
      "állás": regSzo(),                                                              // 1_het valid → teljes mód aktív
      "mindenrossz": regSzo({ domen: "lakhatas", intervallumok: {
        "1_het": ivHibas("nincs_adat"), "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
        "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }),   // NINCS másodlagos → sehol nem érvényes
    }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
  });
  await page.goto("/");
  await expect(page.locator("#kulcsszo-blokk")).toHaveAttribute("data-aktiv-intervallum", "teljes");   // a teljes az ALAPNEZET (request 1)
  const k = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="mindenrossz"]`);
  expect(await k.getAttribute("data-drawable")).toBe("false");
  expect(await k.getAttribute("data-ok")).toBe("teljes_nincs_sorozat");
});

// T5 (SZEMLE 08-19, per-szó tengely): teljes módban minden szó a SAJÁT időszakát mutatja → a fejléc NE mondjon
// EGYETLEN dátumot (szavanként eltér), hanem a per-szó szöveget. A dátum a kártya forrás-feliratán van, nem a fejlécen.
test("teljes-nezet 5: fejléc per-szó szöveg (nincs egyetlen dátum a fejlécen)", async ({ page }) => {
  await mock(page, {
    regObj: reg({
      "állás": regSzo({ domen: "munkaeropiac", racs: "nap", intervallumok: {
        "1_het": ivHibas("keves_pont"), "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
        "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }),
      "albérlet": regSzo({ domen: "lakhatas", racs: "nap", intervallumok: {
        "1_het": ivHibas("keves_pont"), "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
        "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas") } }),
    }),
    mpRegObj: mpReg({
      "állás": mpSzo("nap", { "3_ho": racs_iv(30, 1) }, { domen: "munkaeropiac" }),
      "albérlet": mpSzo("nap", { "3_ho": racs_iv(90, 1) }, { domen: "lakhatas" }),
    }),
    mpNyersObj: mpNyers({
      "állás": [racs_nyersRekord("állás", 30, 1)],
      "albérlet": [racs_nyersRekord("albérlet", 90, 1)],
    }),
  });
  await page.goto("/");
  const fr = page.locator("#kulcsszo-blokk .frissesseg");
  await expect(fr).toContainText("szavanként eltérő időszak, mindegyik a saját adatán");   // per-szó fejléc
  await expect(fr).not.toContainText("2026. 08. 30.");   // NEM az első kártya dátuma
  await expect(fr).not.toContainText("2026. 10. 29.");   // ÉS nem is egyetlen globális dátum → nincs dátum a fejlécen
});

// T6 (SZEMLE 08-19, request 2): a „Kulcsszavak" cím marad + a nézet-leírás mellé (aktív intervallum szerint).
test("teljes-nezet 6: a Kulcsszavak cím a nézet-leírással bővül (aktív intervallum szerint)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "albérlet": regSzo({ domen: "lakhatas" }) }),   // 1_het órás valid
    nyersObj: nyers({ "albérlet": [nyersRekord("albérlet")] }),
    mpRegObj: mpReg({ "albérlet": mpSzo("nap", { "3_ho": racs_iv(90, 1) }) }),   // 3_ho másodlagos valid
    mpNyersObj: mpNyers({ "albérlet": [racs_nyersRekord("albérlet", 90, 1)] }),
  });
  await page.goto("/");
  const h2 = page.locator("#kulcsszo-blokk h2");
  await expect(h2).toHaveText("Kulcsszavak – a teljes időszakban");        // ALAPNEZET = teljes
  await page.locator('#intervallum-vezerlo button[data-intervallum="1_het"]').click();
  await expect(h2).toHaveText("Kulcsszavak – az elmúlt egy hétben");        // 1_het nézet
  await page.locator('#intervallum-vezerlo button[data-intervallum="3_ho"]').click();
  await expect(h2).toHaveText("Kulcsszavak – az elmúlt három hónapban");    // 3_ho nézet
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
  await page.locator('#intervallum-vezerlo button[data-intervallum="1_het"]').click();   // a teljes az alap (request 1) → a fix 1_het nézethez kattintunk
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
// ÚJRAMÉRVE (LANC-ORAS Sz2, 2026-08-21): a régi jelenet órás 1_ho-t rajzoltatott egy FIKTÍV 720-pontos
// NYERS ablakból — a Sz2 routing (órás X!=1_het → LÁNC) legitim módon megváltoztatta a forrást. A generikus
// váltás-mechanizmust most a VALÓS Sz2-viselkedésre mérjük: 1_het (nyers) → 2_het (LÁNCBÓL). Az órás 1_ho
// ág fedése MEGMARAD, a VALÓS jelenlegi állapotra mérve: ma nincs_lancolas (a lánc 21 nap < 30) → gomb TILTOTT;
// ez az assert MEGSZÓLAL, amikor a lánc eléri a 30 napot és az 1_ho drawable lesz (ORAS-1HO-FEDES).
test("10. default = teljes; 1_het (nyers) → 2_het (LÁNCBÓL) váltás: data-ablak-veg + data-pontok VÁLTOZIK; 1 aria-pressed; órás 1_ho ma nincs_lancolas (gomb tiltott)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivErvenyes({ ablak_veg_utc: VEG, pontok_hasznalt: 168 }),   // nyers 7-napos ablak
      "2_het": iv2hetLanc(),                                               // láncból szeletelt (veg = lánc-vég)
      "1_ho": ivHibas("nincs_lancolas"),   // VALÓS: az órás 1_ho ma nincs_lancolas (lánc 21<30) — a fedés MEGSZÓLAL 30 nap fölött
      "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
    } }) }),
    nyersObj: nyers({ "állás": [nyersRekord("állás", 50, { veg: VEG, n: 168 })] }),
    lancObj: { kulcsszavak: { "állás": lancRek() } },
  });
  await page.goto("/");
  await expect(page.locator(K)).toHaveAttribute("data-aktiv-intervallum", "teljes");
  // VALÓS jelenlegi viselkedés — az órás 1_ho nincs_lancolas → a gombja TILTOTT (ORAS-1HO-FEDES: 30 nap fölött megszólal)
  await expect(page.locator('#intervallum-vezerlo button[data-intervallum="1_ho"]')).toBeDisabled();
  await page.locator('#intervallum-vezerlo button[data-intervallum="1_het"]').click();
  await expect(page.locator(K)).toHaveAttribute("data-aktiv-intervallum", "1_het");
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`);
  await expect(c).toHaveAttribute("data-ablak-veg", VEG);
  const pont1het = Number(await c.getAttribute("data-pontok"));
  await page.locator('#intervallum-vezerlo button[data-intervallum="2_het"]').click();   // váltás a LÁNCBÓL rajzolt hosszabb nézetre
  await expect(page.locator(K)).toHaveAttribute("data-aktiv-intervallum", "2_het");
  await expect(c).toHaveAttribute("data-ablak-veg", LVEG);                                // a LÁNC vége, NEM a nyers VEG
  const pont2het = Number(await c.getAttribute("data-pontok"));
  expect(pont2het).toBeGreaterThan(pont1het);                                             // a ~14-napos lánc-farok ≫ a 7-napos nyers
  await expect(page.locator('#intervallum-vezerlo button[aria-pressed="true"]')).toHaveCount(1);
  await expect(page.locator('#intervallum-vezerlo button[aria-pressed="true"]')).toHaveAttribute("data-intervallum", "2_het");
});

// ── CSS+MAGYARÁZÓ kör: blokk-elválasztás, kártya-felbontás, gomb-magyarázat ────────────────────

// Item 1 — a nagy blokkok LÁTHATÓAN elválnak (lekerekített keret), a háttér FEHÉR (a szürkítés visszavonva).
// getComputedStyle-lal DOM-assertálható. Diszkriminátor: a keret/rádiusz eltávolítására, ill. a .vezerlo-sav
// #fafafa-ra visszaállítására ez a teszt bukik.
test("CSS: a kulcsszó- és trend-blokk lekerekített kerettel elválik; a vezérlő-sáv háttere FEHÉR (nem szürke)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo({ domen: "munkaeropiac" }) }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
  });
  await page.goto("/");
  for (const id of ["#kulcsszo-blokk", "#trend-blokk"]) {
    const st = await page.locator(id).evaluate((el) => {
      const s = getComputedStyle(el);
      return { r: s.borderTopLeftRadius, bw: s.borderTopWidth, bs: s.borderTopStyle, bg: s.backgroundColor };
    });
    expect(st.r).not.toBe("0px");                     // lekerekített sarok
    expect(st.bs).toBe("solid");                      // van keret (nem 'none')
    expect(parseFloat(st.bw)).toBeGreaterThan(0);
    expect(st.bg).toBe("rgb(255, 255, 255)");         // FEHÉR háttér marad (a szürkítés rosszabb volt → visszavonva)
  }
  // négy .vezerlo-sav (intervallum-vezérlő + idősor-legend + dátum-választó + hét-választó) — MIND fehér,
  // a d86af56 #fafafa szürkítés VISSZAVONVA. (A szám a szekciók számát tükrözi: kulcsszó, idősor, trend, heti.)
  const vezBgs = await page.locator(".vezerlo-sav").evaluateAll((els) => els.map((el) => getComputedStyle(el).backgroundColor));
  expect(vezBgs).toHaveLength(4);
  for (const bg of vezBgs) expect(bg).toBe("rgb(255, 255, 255)");
});

// Item 3 — MINDEN kártyán ott a szó felbontása (óránkénti/napi/heti), az ÜRESEN is → megszűnik a „miért nincs
// görbe ezen az ablakon" zavar. Rajzolt kártya: az aktív intervallum tényleges rácsa (órás ablakon „óránkénti").
// Üres kártya: nincs _racs → a szó config-rácsára esik vissza (nap/het) → a natív felbontást mutatja.
test("Felbontás-sor MINDEN kártyán (rajzolton ÉS üresen): óránkénti/napi/heti + data-felbontas", async ({ page }) => {
  await mock(page, {
    regObj: reg({
      "benzin": regSzo({ domen: "fogyasztas", racs: "ora" }),                     // órás szó, 1_het rajzol → óránkénti
      "hitel":  regSzo({ domen: "lakhatas", racs: "nap", intervallumok: {         // napi szó, ÜRES 1_het (nincs_adat)
        "1_het": ivHibas("nincs_adat"), "2_het": ivHibas("nincs_lancolas"),
        "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
      } }),
      "tüntetés": regSzo({ domen: "kozelet", racs: "het", intervallumok: {        // heti szó, ÜRES 1_het (ELVI: túl rövid)
        "1_het": ivHibas("nincs_adat"), "2_het": ivHibas("nincs_lancolas"),
        "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
      } }),
    }),
    nyersObj: nyers({ "benzin": [nyersRekord("benzin")], "hitel": [nyersRekord("hitel")], "tüntetés": [nyersRekord("tüntetés")] }),
  });
  await page.goto("/");
  await expect(page.locator(`${K} .kulcsszo-chart .felbontas`)).toHaveCount(3);   // MINDEN kártyán, az üreseken is
  const b = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="benzin"]`);
  await expect(b).toHaveAttribute("data-felbontas", "ora");
  await expect(b.locator(".felbontas")).toHaveText("Felbontás: óránkénti");        // rajzolt órás
  const h = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="hitel"]`);
  await expect(h).toHaveAttribute("data-felbontas", "nap");
  await expect(h.locator(".felbontas")).toHaveText("Felbontás: napi");             // ÜRES kártyán IS (config-rács)
  const t = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="tüntetés"]`);
  await expect(t).toHaveAttribute("data-felbontas", "het");
  await expect(t.locator(".felbontas")).toHaveText("Felbontás: heti");             // ÜRES heti szó
});

// Item 2 — minden intervallum-gomb ALATT egy LÁTHATÓ idő-táv magyarázat (sub-szöveg, NEM title-tooltip: mobilon
// a tooltip nem elérhető). A .gomb-magyarazat a .intervallum-tetel-en belül, a gomb-sor ALATT.
test("Intervallum-gombok: minden gomb alatt LÁTHATÓ idő-táv magyarázat (sub-szöveg, nem tooltip)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo() }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
  });
  await page.goto("/");
  const magy = page.locator("#intervallum-vezerlo .gomb-magyarazat");
  await expect(magy).toHaveCount(6);                                               // az 5 fix + a "Teljes időszak" gomb alatt
  await expect(magy.first()).toBeVisible();                                        // LÁTHATÓ (nem néma title)
  const parok = { "1_het": "mától visszafelé 1 hét", "2_het": "mától visszafelé 2 hét",
    "1_ho": "mától visszafelé 1 hónap", "3_ho": "mától visszafelé 3 hónap", "1_ev": "mától visszafelé 1 év" };
  for (const kulcs of Object.keys(parok)) {
    await expect(page.locator(
      `#intervallum-vezerlo .intervallum-tetel:has(button[data-intervallum="${kulcs}"]) .gomb-magyarazat`
    )).toHaveText(parok[kulcs]);
  }
  // TELJES-NEZET: a 6. gomb sub-szövege is LÁTHATÓ (a guard szándéka — minden gomb alatt magyarázat — kiterjesztve)
  await expect(page.locator(
    '#intervallum-vezerlo .intervallum-tetel:has(button[data-intervallum="teljes"]) .gomb-magyarazat'
  )).toHaveText("a gyűjtés kezdetétől máig, szavanként eltérő indulással");
});

// ── 11. lusta renderelés (mod 3) ─────────────────────────────────────────────────────────────
test("11. kis viewport → csak az első kártyák data-rendered; scroll → a lejjebbi is megkapja", async ({ page }) => {
  const szavak = {}; const nyersMap = {};
  for (let i = 0; i < 8; i++) { szavak["szo" + i] = regSzo(); nyersMap["szo" + i] = [nyersRekord("szo" + i)]; }
  await mock(page, { regObj: reg(szavak), nyersObj: nyers(nyersMap) });
  // 6b Szelet 2: itt EGYETLEN szónak sincs másodlagos adata → mind a 4 hosszú intervallum-gomb TILTOTT.
  // ÁTTEKINTŐ-PANEL ÚJRAMÉRÉS (2026-08-20, #attekinto-blokk hozzáadva a #kulcsszo-blokk ELÉ; 380 széles, 8
  // szintetikus szó — mind "munkaeropiac" domén, tehát a panel EGYETLEN domén-csoportot rajzol 8 kártyával —,
  // 0 másodlagos, ALAPNEZET=teljes): MÉRT top (scrollY=0): szo0=1468px, szo1=1953px, …, szo7=4860px. Az IO
  // zóna-alja = VH + rootMargin(400); VH=700 → zóna-alja 1100 → MIND a 8 kártya a zónán KÍVÜL → load-kor 0
  // kártya rendered (a panel prominens elhelyezésének SZÁNDÉKOS, helyes következménye, NEM render-regresszió).
  // A pozitív bizonyíték ezért scrollIntoViewIfNeeded-del jön: a szo0-t a zónába görgetve MÉRT eredmény —
  // szo0/szo1/szo2 → rendered="true", szo3..szo7 → marad NEM rendered (near-vs-far szerkezet megmarad: a
  // TÁVOLI szo7 EKKOR is kívül esik). Végül a szo7-et is a zónába görgetve az IS rajzolódik (valódi lusta
  // állapot, nem "sosem renderel" hiba). MIÉRT nem prod-hatás: éles adaton 4 szónak VAN másodlagosa → rövidebb
  // vezérlő; a szintetikus 0-másodlagos a friss-telepítés/KULCS-LISTA esete (lásd VEZERLO-MAGAS leltár-megfigyelés).
  await page.setViewportSize({ width: 380, height: 700 });
  await page.goto("/");
  const rendered = page.locator(`${K} .kulcsszo-chart[data-rendered="true"]`);
  // LOAD-KOR: a panel a fold alá tolja mind a 8 kártyát → egyik sem rendered.
  await expect(rendered).toHaveCount(0);
  // POZITÍV: a szo0-t a zónába görgetve rajzolódik (a szomszédos szo1/szo2 is, de nem mind a 8).
  await page.locator(`${K} .kulcsszo-chart[data-kulcsszo="szo0"]`).scrollIntoViewIfNeeded();
  await expect(rendered).not.toHaveCount(0);                                         // auto-retry: várd meg az IO-callbacket
  expect(await rendered.count()).toBeLessThan(8);                                    // de NEM mind renderelt egyszerre
  // NEGATÍV (beépített nem-vacuous bizonyíték): a TÁVOLI szo7 EKKOR is a zónán KÍVÜL marad → NEM rendered.
  await expect(page.locator(`${K} .kulcsszo-chart[data-kulcsszo="szo7"]`)).not.toHaveAttribute("data-rendered", "true");
  // majd a szo7-et is a zónába görgetve AZ IS rajzolódik (valódi lusta állapot, nem "sosem renderel" hiba).
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
// ÚJRAMÉRVE (LANC-ORAS Sz2, 2026-08-21): a régi jelenet órás 1_ho-t rajzoltatott FIKTÍV 720-pontos NYERS
// ablakból; a Sz2 routing (órás X!=1_het → LÁNC) megváltoztatta a forrást. A frissesseg-követést a VALÓS
// Sz2-viselkedésre mérjük: 1_het (nyers) → 2_het (LÁNCBÓL). Az órás 1_ho fedése MEGMARAD (nincs_lancolas → tiltott gomb).
test("13. .frissesseg: cimke + dátum az aktív intervallumból (nem a szamitva_utc-ból); 1_het → 2_het (LÁNCBÓL) váltásra követi", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivErvenyes({ ablak_veg_utc: VEG }),
      "2_het": iv2hetLanc(),                                             // láncból; ablak_veg = LVEG (2026-08-13)
      "1_ho": ivHibas("nincs_lancolas"),   // VALÓS: órás 1_ho ma nincs_lancolas (ORAS-1HO-FEDES)
      "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
    } }) }, { szamitva_utc: "2026-08-06T02:00:00+00:00" /* KÉSŐBBI nap, mint az ablak_veg */ }),
    nyersObj: nyers({ "állás": [nyersRekord("állás", 50, { veg: VEG })] }),
    lancObj: { kulcsszavak: { "állás": lancRek() } },
  });
  await page.goto("/");
  await expect(page.locator('#intervallum-vezerlo button[data-intervallum="1_ho"]')).toBeDisabled();   // órás 1_ho nincs_lancolas — fedés
  await page.locator('#intervallum-vezerlo button[data-intervallum="1_het"]').click();   // a teljes az alap → a fix 1_het nézethez kattintunk
  const f = page.locator(`${K} .frissesseg`);
  // a frissesseg az AKTÍV intervallum ablak_veg-jét mutatja (NEM 08-06 szamitva)
  await expect(f).toContainText("(1 hét)");
  await expect(f).toContainText("2026. 08. 05.");                                    // veg1het napja, NEM 08-06
  await page.locator('#intervallum-vezerlo button[data-intervallum="2_het"]').click();
  await expect(f).toContainText("(2 hét)");
  await expect(f).toContainText(LVEG.slice(0, 10).replace(/-/g, ". ") + ".");        // váltás után a LÁNC ablak_veg napja (2026. 08. 13.)
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

// ── LANC-ORAS Sz2: órás 2_het a LÁNCBÓL rajzol (nem a 7-napos nyersből) ─────────────────────────
// A 2_het interval ervenyes (a backend a láncból szeletelte), az ablak_veg = a LÁNC vége (iso360),
// amihez NINCS veg-egyező nyers 7-napos ablak. Ha a frontend a nyersből próbál rajzolni → nincs
// egyezés → data-drawable=false (a 14. teszt mintája). A HELYES Sz2-viselkedés: a 2_het a
// kulcsszo_lanc.json-ból rajzol → drawable=true, és a rajzolt tartomány a lánc ~14-napos farka
// (≫ a 7-napos nyers 168 pontja), NEM az 1_het nyújtása. A lánc-fixture a fájl tetején (lancRek/iv2hetLanc).

test("18. LANC-ORAS Sz2: órás 2_het a LÁNCBÓL rajzol (drawable=true, ~14 nap ≫ 168), nem a 7-napos nyersből", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivErvenyes(),                                        // nyers 7-napos ablak (VEG)
      "2_het": iv2hetLanc(),                                        // láncból szeletelt (veg = lánc-vég)
      "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
    } }) }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),           // CSAK a VEG (iso168) ablak — NINCS iso360-egyező
    lancObj: { kulcsszavak: { "állás": lancRek() } },               // a lánc a 2_het forrása
  });
  await page.goto("/");
  await page.click('#intervallum-vezerlo button[data-intervallum="2_het"]');
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`);
  await expect(c).toHaveAttribute("data-drawable", "true");         // RED: ma a nyersből próbál → nincs iso360-ablak → false
  await expect(c).toHaveAttribute("data-ablak-veg", LVEG);          // a rajzolt ablak a LÁNC vége, nem a nyers VEG
  const rp = Number(await c.getAttribute("data-rajzolt-pont"));
  expect(rp).toBeGreaterThan(168);                                  // a lánc ~14-napos farka, NEM a 7-napos nyers (168)
});

// ── LANC-2HET-VONAL: a lánc-forrás ablak_veg_utc = utolsó VALÓS pont (a nyersé = RÉSZLEGES záró slot). A
// veg_idx kizárólagos felső határa a NYERS konvencióra épült → a láncnál az utolsó pont ÉS a trendvonal kiesett.
// A fix a FORRÁS konvencióját teszi explicitté (a rekord _veg_valos jelzője), a NYERS ág változatlan.
test("19. LANC-2HET-VONAL (a): lánc-forrású 2_het → a trendvonal dataset LÉTREJÖN (data-vonal=true)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivErvenyes(), "2_het": iv2hetLanc(),
      "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
    } }) }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
    lancObj: { kulcsszavak: { "állás": lancRek() } },
  });
  await page.goto("/");
  await page.click('#intervallum-vezerlo button[data-intervallum="2_het"]');
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`);
  await expect(c).toHaveAttribute("data-drawable", "true");
  await expect(c).toHaveAttribute("data-vonal", "true");   // RED: ma false — a vonal-végpont az utolsó valós ponton (veg_idx) a rajzolt tartományon KÍVÜL esik
});

test("20. LANC-2HET-VONAL (b): lánc-forrású 2_het → az UTOLSÓ PONT is rajzolódik (adat, nem dísz)", async ({ page }) => {
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivErvenyes(), "2_het": iv2hetLanc(),
      "1_ho": ivHibas("nincs_lancolas"), "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
    } }) }),
    nyersObj: nyers({ "állás": [nyersRekord("állás")] }),
    lancObj: { kulcsszavak: { "állás": lancRek() } },
  });
  await page.goto("/");
  await page.click('#intervallum-vezerlo button[data-intervallum="2_het"]');
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`);
  // a lánc-farok iso(24)..iso(360) INKLUZÍV = 337 slot (a régi kizárólagos [24,360) csak 336-ot rajzol → RED)
  await expect(c).toHaveAttribute("data-rajzolt-pont", "337");
  await expect(c).toHaveAttribute("data-adat-veg", LVEG);   // az utolsó KIRAJZOLT lezárt pont a lánc vége
});

// ŐRZŐ (SZÁNDÉKOS-ZÖLD, fogak MÉRVE): a NYERS ág HÁTSÓ-LYUK viselkedése VÁLTOZATLAN a fix után. A nyers
// ablak_veg RÉSZLEGES slot (iso168), az utolsó LEZÁRT pont iso164 (iso165/166/167 HIÁNYZIK). A rajzolt tartomány
// [0, veg_idx=168) → 168 slot, a 3 hátsó null BENNMARAD. FOGAK: a tiltott naiv fix (veg_idx=utolsó lezárt+1=165)
// itt 165-öt adna → e teszt PIROSÍTANÁ; a helyes forrás-konvenciós fix (nyers _veg_valos undefined → +0) 168-at ad.
test("21. ŐRZŐ: nyers HÁTSÓ-LYUK változatlan a LANC-2HET-VONAL fix után (data-rajzolt-pont=168, a 3 hátsó null bennmarad)", async ({ page }) => {
  const gapPts = [];
  for (let i = 0; i < 165; i++) gapPts.push({ idopont_utc: iso(i), ertek: 50, reszleges: false });   // iso0..iso164 lezárt
  gapPts.push({ idopont_utc: iso(168), ertek: 0, reszleges: true });                                  // részleges záró; iso165/166/167 HIÁNYZIK
  await mock(page, {
    regObj: reg({ "állás": regSzo({ intervallumok: {
      "1_het": ivErvenyes({ ablak_kezdet_utc: ELSO, ablak_veg_utc: VEG, pontok_hasznalt: 165, pontok_hianyzo: 3,
        illesztes_vonal: [{ idopont_utc: ELSO, ertek: 35 }, { idopont_utc: iso(164), ertek: 42 }] }),
      "2_het": ivHibas("nincs_lancolas"), "1_ho": ivHibas("nincs_lancolas"),
      "3_ho": ivHibas("nincs_lancolas"), "1_ev": ivHibas("nincs_lancolas"),
    } }) }),
    nyersObj: nyers({ "állás": [{ kulcsszo: "állás", ablak_kezdet_utc: ELSO, ablak_veg_utc: VEG, pontok: gapPts }] }),
  });
  await page.goto("/");
  await page.click('#intervallum-vezerlo button[data-intervallum="1_het"]');
  const c = page.locator(`${K} .kulcsszo-chart[data-kulcsszo="állás"]`);
  await expect(c).toHaveAttribute("data-drawable", "true");
  await expect(c).toHaveAttribute("data-rajzolt-pont", "168");   // a részleges slotig; a 3 hátsó null BENNMARAD (nyers konvenció változatlan)
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
  await page.locator('#intervallum-vezerlo button[data-intervallum="1_het"]').click();   // a teljes az alap (request 1) → a fix 1_het nézethez kattintunk
  const f = page.locator(`${K} .frissesseg`);
  await expect(f).toContainText("(1 hét)");
  await expect(f).toContainText("2026. 08. 06.");        // az utolsó LEZÁRT pont napja (a kirajzolt adat vége)
  await expect(f).not.toContainText("2026. 08. 07.");    // az ablak_veg (részleges slot) napja NEM jelenhet meg
});
