const { test, expect } = require("@playwright/test");

// Trend-blokk smoke-ok (21 db; Task 7 + 8a) — MOCKOLT legfrissebb.json + napok/index.json + napok/<nap>.json.
// A DOM-szerződést az OSZT_T/ATTR_T konstansok rögzítik. A chart-sávok canvas-belsők → a tesztelhető
// eloszlást a szűrő-gombok data-count-jai + a caption hordozzák (a T8/L9 korlátja). A T16 a JSON-tömb
// szerializálást védi egy pipe-tartalmú kategórianévvel (a pipe-változat elhasítaná).
// Az interakciós tesztek LÉTEZÉS-asserttel kezdenek, hogy a hiba tiszta count-eltérés legyen,
// ne kattintás-timeout.

const T = "#trend-blokk";

// egy trend-elem; temak === undefined → a mező HIÁNYZIK (régi archív nap), [] → nincs besorolás, [...] → van
// idosor: opcionális pont-tömb ({idopont_utc, ertek}); alap [] (üres — D1-kiterjesztett / mind-üres eset).
function trend(kifejezes, volumen, temak, idosor) {
  const e = { kifejezes, volumen, novekedes_pct: "100", idosor: idosor || [], hirek: [] };
  if (temak !== undefined) { e.temak = temak; e.topics = temak.map(function (_, i) { return i + 1; }); }
  return e;
}

// SZÁNDÉKOSAN nem-uniform sorozat: n pont, adott kezdettel, 8 perces ráccsal, szórt értékekkel.
// A fixture-ben két eltérő hosszú/kezdetű sorozat bizonyítja, hogy a kód nem feltételez fix pontszámot/közös kezdetet.
function idosor_sorozat(n, kezdet_iso) {
  const t0 = new Date(kezdet_iso).getTime();
  const pontok = [];
  for (let i = 0; i < n; i++) {
    pontok.push({ idopont_utc: new Date(t0 + i * 8 * 60000).toISOString(), ertek: (i % 3 === 0) ? 100 : 0 });
  }
  return pontok;
}

// kategóriás nap: 16 elem, egy MULTI-kategóriás (huth gergely) → 17 besorolás 16 trendre.
// Eloszlás: Other 6, Law and Government 4, Entertainment 3, Politics 2, Jobs and Education 1, Sports 1.
const MAI16 = [
  trend("időjárás", "50000", ["Other"]),
  trend("miniszter", "10000", ["Jobs and Education"]),
  trend("idősek", "5000", ["Law and Government"]),
  trend("horvátország", "5000", ["Other"]),
  trend("gajdos lászló", "5000", ["Law and Government"]),
  trend("televízió", "5000", ["Entertainment"]),
  trend("vitézy dávid", "2000", ["Other"]),
  trend("pósfai gábor", "2000", ["Law and Government"]),
  trend("huth gergely", "2000", ["Politics", "Law and Government"]),
  trend("incidens", "2000", ["Other"]),
  trend("the walt disney company", "2000", ["Entertainment"]),
  trend("mtk–pafc", "2000", ["Sports"]),
  trend("hortay olivér", "2000", ["Politics"]),
  trend("híd", "2000", ["Other"]),
  trend("tv2", "2000", ["Entertainment"]),
  trend("idokep radar", "2000", ["Other"]),
];

// régi nap: FELTŰNŐEN más hosszú (3 elem), temak MEZŐ NÉLKÜL (Task 3a előtti archív)
const REGI3 = [
  trend("autóversenyző", "10000"),
  trend("valami", "5000"),
  trend("másik", "2000"),
];

// kevert kis nap a T15-höz: van ["Other"], van valódi, és van [] (besorolás hiánya)
const MIX = [
  trend("other-elem", "5000", ["Other"]),
  trend("politics-elem", "5000", ["Politics"]),
  trend("ures-elem", "5000", []),
];

// pipe-tartalmú kategórianév a T16-hoz: a "Law|Government" a JSON-szerializálást védi (a pipe-változat elhasítaná);
// a "Government" a fél-név önálló kategóriája (a pipe-változat tévesen ide sorolná a multi-elemet)
const PIPE = [
  trend("multi", "5000", ["Politics", "Law|Government"]),
  trend("kormanyzat", "5000", ["Government"]),
];

async function mock(page, opts) {
  if (opts.legfrissebb) {
    await page.route(/legfrissebb\.json/, function (r) {
      r.fulfill({ contentType: "application/json", body: JSON.stringify(opts.legfrissebb) });
    });
  }
  if (opts.index) {
    await page.route(/napok\/index\.json/, function (r) {
      r.fulfill({ contentType: "application/json", body: JSON.stringify(opts.index) });
    });
  }
  if (opts.napok) {
    for (const nap of Object.keys(opts.napok)) {
      const trendek = opts.napok[nap];
      await page.route(new RegExp("napok/" + nap + "\\.json"), function (r) {
        r.fulfill({ contentType: "application/json", body: JSON.stringify({ nap: nap, trendek: trendek }) });
      });
    }
  }
}

// ── T1 — lista renderel: kártyaszám + kifejezes + volumen ──────────────────────
test("1. lista renderel: N kártya, mindegyiken kifejezes + volumen", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  await expect(page.locator(`${T} .trend-kartya`)).toHaveCount(16);
  const elso = page.locator(`${T} .trend-kartya`).first();
  await expect(elso.locator(".trend-kifejezes")).toHaveText("időjárás");
  await expect(elso.locator(".trend-volumen")).toContainText("50000");
});

// ── T2 — kategória-címke három állapota (van / nincs / hianyzik) ────────────────
test("2. kategória-címke három állapot: van/nincs/hianyzik, [] és hiányzó egyaránt »egyéb«", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: [
    trend("a", "5000", ["Politics"]),
    trend("b", "5000", []),
    trend("c", "5000"),
  ] } });
  await page.goto("/");
  await expect(page.locator(`${T} .trend-kartya`)).toHaveCount(3);
  const k = function (kif) { return page.locator(`${T} .trend-kartya[data-kifejezes="${kif}"]`); };
  await expect(k("a")).toHaveAttribute("data-kategoria-allapot", "van");
  await expect(k("a").locator(".trend-kategoria")).toContainText("Politics");
  await expect(k("b")).toHaveAttribute("data-kategoria-allapot", "nincs");
  await expect(k("b").locator(".trend-kategoria")).toContainText("egyéb");
  await expect(k("c")).toHaveAttribute("data-kategoria-allapot", "hianyzik");
  await expect(k("c").locator(".trend-kategoria")).toContainText("egyéb");
});

// ── T3 — chart megléte kategóriás napon ────────────────────────────────────────
test("3. kategória-eloszlás chart jelen (canvas) kategóriás napon", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  await expect(page.locator(`${T} canvas.kategoria-chart`)).toHaveCount(1);
});

// ── T4 — eloszlás a gombokban + forrás/magyarázat (osztálynévre, NEM színre) ────
test("4. eloszlás a szűrő-gombokban + Other utolsó/--other + caption (17/16 + Google-forrás)", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  await expect(page.locator(`${T} .kategoria-szuro .kategoria-gomb`)).toHaveCount(7); // Összes + 6 kategória
  await expect(page.locator(`${T} .kategoria-gomb[data-kategoria="Other"]`)).toHaveAttribute("data-count", "6");
  await expect(page.locator(`${T} .kategoria-gomb[data-kategoria="Law and Government"]`)).toHaveAttribute("data-count", "4");
  await expect(page.locator(`${T} .kategoria-gomb[data-kategoria="Politics"]`)).toHaveAttribute("data-count", "2");
  // "Other" az UTOLSÓ gomb (viselkedés) + megkülönböztető OSZTÁLY (nem számított szín)
  await expect(page.locator(`${T} .kategoria-szuro .kategoria-gomb`).last()).toHaveAttribute("data-kategoria", "Other");
  await expect(page.locator(`${T} .kategoria-gomb[data-kategoria="Other"]`)).toHaveClass(/kategoria-gomb--other/);
  // caption: 17 besorolás / 16 trend + a Google-forrás
  await expect(page.locator(`${T} .kategoria-magyarazat`)).toContainText("17");
  await expect(page.locator(`${T} .kategoria-magyarazat`)).toContainText("16");
  await expect(page.locator(`${T} .kategoria-magyarazat`)).toContainText("Google Trends");
});

// ── T5 — szűrő szűr ────────────────────────────────────────────────────────────
test("5. »Politics« szűrés: csak a Politics-kártyák láthatók + data-aktiv-kategoria + aria-pressed", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  const gomb = page.locator(`${T} .kategoria-gomb[data-kategoria="Politics"]`);
  await expect(gomb).toHaveCount(1);
  await gomb.click();
  await expect(page.locator(T)).toHaveAttribute("data-aktiv-kategoria", "Politics");
  await expect(gomb).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(`${T} .trend-kartya:visible`)).toHaveCount(2); // huth gergely + hortay olivér
});

// ── T6 — multi-kategóriás elem mindkét szűrésnél ───────────────────────────────
test("6. multi-kategóriás elem (huth gergely) látszik Politics ÉS Law and Government szűrésnél is", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  const huth = page.locator(`${T} .trend-kartya[data-kifejezes="huth gergely"]`);
  const gp = page.locator(`${T} .kategoria-gomb[data-kategoria="Politics"]`);
  const gl = page.locator(`${T} .kategoria-gomb[data-kategoria="Law and Government"]`);
  await expect(gp).toHaveCount(1);
  await gp.click();
  await expect(huth).toBeVisible();
  await gl.click();
  await expect(huth).toBeVisible();
});

// ── T7 — újrakattintás kikapcsol ───────────────────────────────────────────────
test("7. az aktív kategóriára újrakattintva a szűrés kikapcsol (data-aktiv-kategoria törlődik)", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  const gomb = page.locator(`${T} .kategoria-gomb[data-kategoria="Politics"]`);
  await expect(gomb).toHaveCount(1);
  await gomb.click();
  await gomb.click();
  await expect(page.locator(T)).not.toHaveAttribute("data-aktiv-kategoria", /.+/);
  await expect(page.locator(`${T} .trend-kartya:visible`)).toHaveCount(16);
});

// ── T8 — eloszlás VÁLTOZATLAN szűrt állapotban ─────────────────────────────────
test("8. a sávok (data-count) szűrés közben VÁLTOZATLANOK — nem számolódnak újra", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  const other = page.locator(`${T} .kategoria-gomb[data-kategoria="Other"]`);
  const politics = page.locator(`${T} .kategoria-gomb[data-kategoria="Politics"]`);
  await expect(politics).toHaveCount(1);
  await politics.click();
  await expect(other).toHaveAttribute("data-count", "6");      // Other maradt 6, NEM 0
  await expect(politics).toHaveAttribute("data-count", "2");   // Politics maradt 2, NEM 100%
});

// ── T9 — nap-függő MEGJELENÉS (kategóriás nap) ─────────────────────────────────
test("9. kategóriás napon a chart ÉS a szűrő jelen", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  await expect(page.locator(`${T} canvas.kategoria-chart`)).toHaveCount(1);
  await expect(page.locator(`${T} .kategoria-szuro`)).toHaveCount(1);
});

// ── T10 — nap-függő ELREJTÉS (régi nap): chart+szűrő eltűnik, kártyalista marad ─
test("10. régi napon (nincs kategória) a chart ÉS a szűrő ELTŰNIK, de a kártyalista MEGVAN", async ({ page }) => {
  await mock(page, {
    legfrissebb: { top_trendek: MAI16 },
    index: { napok: ["2026-08-01", "2026-08-07"] },
    napok: { "2026-08-01": REGI3, "2026-08-07": MAI16 },
  });
  await page.goto("/");
  await page.locator("#datum-valaszto select").selectOption("2026-08-01");
  // közös szabály MINDKÉT ága:
  await expect(page.locator(`${T} .trend-kartya`)).toHaveCount(3);        // a kártyalista MEGVAN (régi 3)
  await expect(page.locator(`${T} .kategoria-szuro`)).toHaveCount(0);     // a szűrő eltűnt
  await expect(page.locator(`${T} canvas.kategoria-chart`)).toHaveCount(0); // a chart eltűnt
});

// ── T11 — napváltás NULLÁZZA a szűrést ─────────────────────────────────────────
test("11. napváltáskor az aktív szűrés nullázódik", async ({ page }) => {
  await mock(page, {
    legfrissebb: { top_trendek: MAI16 },
    index: { napok: ["2026-08-01", "2026-08-07"] },
    napok: { "2026-08-01": REGI3, "2026-08-07": MAI16 },
  });
  await page.goto("/");
  const gomb = page.locator(`${T} .kategoria-gomb[data-kategoria="Politics"]`);
  await expect(gomb).toHaveCount(1);
  await gomb.click();
  await expect(page.locator(T)).toHaveAttribute("data-aktiv-kategoria", "Politics");
  await page.locator("#datum-valaszto select").selectOption("2026-08-01");
  await expect(page.locator(T)).not.toHaveAttribute("data-aktiv-kategoria", /.+/);
});

// ── T12 — változó lista-hossz (16 vs FELTŰNŐEN más 3) ──────────────────────────
test("12. a kártyaszám a data hosszát követi: mai 16, régi 3 (nincs fix 15/16 feltevés)", async ({ page }) => {
  await mock(page, {
    legfrissebb: { top_trendek: MAI16 },
    index: { napok: ["2026-08-01", "2026-08-07"] },
    napok: { "2026-08-01": REGI3, "2026-08-07": MAI16 },
  });
  await page.goto("/");
  await expect(page.locator(`${T} .trend-kartya`)).toHaveCount(16);
  await page.locator("#datum-valaszto select").selectOption("2026-08-01");
  await expect(page.locator(`${T} .trend-kartya`)).toHaveCount(3);
});

// ── T13 — szűrő-gomb aria-szinkron a data-aktiv-kategoria-ból (9b aria_szinkron) ─
test("13. pontosan egy gomb aria-pressed=true a data-aktiv-kategoria-ból derivál", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  const gomb = page.locator(`${T} .kategoria-gomb[data-kategoria="Politics"]`);
  await expect(gomb).toHaveCount(1);
  await gomb.click();
  await expect(page.locator(`${T} .kategoria-gomb[aria-pressed="true"]`)).toHaveCount(1);
  await expect(page.locator(`${T} .kategoria-gomb[aria-pressed="true"]`)).toHaveAttribute("data-kategoria", "Politics");
});

// ── T14 — üres trendlista → §7.5 üzenet ────────────────────────────────────────
test("14. üres top_trendek (API-blokk) → .ures §7.5-üzenet a lista helyén", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: [] } });
  await page.goto("/");
  await expect(page.locator(`${T} .ures`)).toBeVisible();
  await expect(page.locator(`${T} .trend-kartya`)).toHaveCount(0);
});

// ── T15 — az "Other" szűrés az ["Other"]-kártyákat mutatja, NEM az []/hiányzót ──
test("15. »Other« szűrés az ['Other']-címkés kártyákat mutatja, az []/hiányzót NEM", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MIX } });
  await page.goto("/");
  const other = page.locator(`${T} .kategoria-gomb[data-kategoria="Other"]`);
  await expect(other).toHaveCount(1);
  await other.click();
  await expect(page.locator(`${T} .trend-kartya[data-kifejezes="other-elem"]`)).toBeVisible();
  await expect(page.locator(`${T} .trend-kartya[data-kifejezes="ures-elem"]`)).toBeHidden();      // [] NEM Other
  await expect(page.locator(`${T} .trend-kartya[data-kifejezes="politics-elem"]`)).toBeHidden();  // más kategória
});

// ── T16 — pipe-tartalmú kategórianév → a JSON-tömb szerializálás biztos (a pipe-változat elhasítaná) ──
test("16. pipe-tartalmú kategórianév: a teljes néven szűr, a fél-néven NEM (JSON-tömb védi, nem pipe)", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: PIPE } });
  await page.goto("/");
  const teljes = page.locator(`${T} .kategoria-gomb[data-kategoria="Law|Government"]`);
  const felnev = page.locator(`${T} .kategoria-gomb[data-kategoria="Government"]`);
  const multi = page.locator(`${T} .trend-kartya[data-kifejezes="multi"]`);
  await expect(teljes).toHaveCount(1);
  await expect(felnev).toHaveCount(1);
  // TELJES név: a multi látszik (JSON: benne van a "Law|Government"; pipe: a split nem tartalmazza a teljes nevet)
  await teljes.click();
  await expect(multi).toBeVisible();
  await teljes.click();   // reset (toggle ki)
  // FÉL-név ("Government"): a multi NEM látszik (JSON: külön kategória; pipe: a split tévesen tartalmazná)
  await felnev.click();
  await expect(multi).toBeHidden();
});

// ── T17 — az "Összes" reset-gomb szűrt állapotban HANGSÚLYOS (reset-osztály; DOM-oldali → tesztelhető) ──
test("17. az »Összes« reset-gomb: szűrt állapotban reset-osztály, szűretlenül és kikapcsolás után nincs", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  const ossz = page.locator(`${T} .kategoria-gomb[data-kategoria=""]`);
  const politics = page.locator(`${T} .kategoria-gomb[data-kategoria="Politics"]`);
  await expect(ossz).toHaveCount(1);
  await expect(ossz).not.toHaveClass(/kategoria-gomb--reset-aktiv/);   // szűretlen: NINCS
  await politics.click();
  await expect(ossz).toHaveClass(/kategoria-gomb--reset-aktiv/);       // szűrve: RAJTA VAN (az egy forrásból: data-aktiv-kategoria)
  await politics.click();
  await expect(ossz).not.toHaveClass(/kategoria-gomb--reset-aktiv/);   // kikapcsolva: megint NINCS
});

// ── T18 — idősoros kártya: canvas + data-idosor-allapot="van" (nem-uniform sorozatok) ──
test("18. idősoros kártya → canvas + data-idosor-allapot=van (nem-uniform)", async ({ page }) => {
  const VAN = [
    trend("alfa", "50000", ["Other"], idosor_sorozat(4, "2026-08-06T19:52:00+00:00")),
    trend("beta", "50000", ["Other"], idosor_sorozat(3, "2026-08-06T20:00:00+00:00")),
  ];
  await mock(page, { legfrissebb: { top_trendek: VAN } });
  await page.goto("/");
  const kartyak = page.locator(`${T} .trend-kartya[data-idosor-allapot="van"]`);
  await expect(kartyak).toHaveCount(2);
  await expect(kartyak.first().locator(".trend-sparkline-doboz canvas")).toHaveCount(1);
});

// ── T19 — D1-kiterjesztett (üres idosor) kártya: elemenkénti üzenet + data-idosor-allapot="nincs", NINCS canvas ──
test("19. üres idosor → 'nincs idősor ezen a napon' + data-idosor-allapot=nincs, nincs canvas", async ({ page }) => {
  const VEGYES = [
    trend("van-gorbe", "50000", ["Other"], idosor_sorozat(4, "2026-08-06T19:52:00+00:00")),
    trend("nincs-gorbe", "2000", ["Other"]),   // D1-kiterjesztett: idosor []
  ];
  await mock(page, { legfrissebb: { top_trendek: VEGYES } });
  await page.goto("/");
  const nincs = page.locator(`${T} .trend-kartya[data-idosor-allapot="nincs"]`);
  await expect(nincs).toHaveCount(1);
  await expect(nincs.locator(".trend-idosor-ures")).toHaveText("nincs idősor ezen a napon");
  await expect(nincs.locator("canvas")).toHaveCount(0);
});

// ── T20 — KÜLÖN életciklus: kulcsszó-intervallum váltás NEM destroy-olja a trend-sparkline-t (L9-őr) ──
test("20. kulcsszó-intervallum váltás után a trend-sparkline Chart él (KÜLÖN életciklus)", async ({ page }) => {
  // LOKÁLIS route CSAK ide (a közös mock()-ot a 16 meglévő smoke használja — ott NEM bővítünk). Két intervallum
  // ervenyes → van kattintható, a default-kiválasztottól (leghosszabb=1_ho) KÜLÖNBÖZŐ gomb (1_het) is.
  await page.route(/kulcsszo_regresszio\.json/, function (r) {
    r.fulfill({ contentType: "application/json", body: JSON.stringify({
      kulcsszavak: { "próba": { aktiv: true, domen: "g", tipus: "szintmero", intervallumok: {
        "1_het": { ervenyes: true, meredekseg_nap: -1.0, se_meredekseg: 0.5, irany: "csokken" },
        "2_het": { ervenyes: false, ok: "nincs_lancolas" },
        "1_ho":  { ervenyes: true, meredekseg_nap: -1.0, se_meredekseg: 0.5, irany: "csokken" },
        "3_ho":  { ervenyes: false, ok: "nincs_lancolas" },
        "1_ev":  { ervenyes: false, ok: "nincs_lancolas" },
      } } },
    }) });
  });
  await mock(page, {
    legfrissebb: { top_trendek: [ trend("alfa", "50000", ["Other"], idosor_sorozat(4, "2026-08-06T20:52:00+00:00")) ] },
  });
  await page.goto("/");
  const canvas = page.locator(`${T} .trend-sparkline-doboz canvas`).first();
  await expect(canvas).toHaveCount(1);
  // AZONNALI rajzolás: a Chart már a renderkor létezik (nincs scrollIntoView / első poll)
  expect(await canvas.evaluate((c) => !!Chart.getChart(c))).toBe(true);
  // kulcsszó-intervallum váltás (1_het, ≠ a default-kiválasztott 1_ho) → globális chart_takarit() fut
  await page.locator("#intervallum-vezerlo button:not([disabled])").first().click();
  // a trend-sparkline Chart TOVÁBBRA is él (a KÜLÖN életciklus nem engedte destroy-olni)
  expect(await canvas.evaluate((c) => !!Chart.getChart(c))).toBe(true);
});

// ── T21 — mind-üres nap (idosor-ág bukása): EGY blokk-szintű jelzés, NINCS elemenkénti fal ──
test("21. mind-üres nap → egyetlen blokk-jelzés, N kártya data-idosor-allapot=nincs, nincs elemenkénti szöveg", async ({ page }) => {
  const MIND_URES = [
    trend("egy", "50000", ["Other"]),    // mind idosor: []
    trend("ketto", "10000", ["Politics"]),
    trend("harom", "5000", ["Other"]),
  ];
  await mock(page, { legfrissebb: { top_trendek: MIND_URES } });
  await page.goto("/");
  await expect(page.locator(`${T} .trend-idosor-ures-blokk`)).toHaveText("Ezen a napon egyetlen felkapott trendhez sincs idősor.");
  await expect(page.locator(`${T} .trend-kartya[data-idosor-allapot="nincs"]`)).toHaveCount(3);
  await expect(page.locator(`${T} .trend-idosor-ures`)).toHaveCount(0);   // az elemenkénti szöveg ÖSSZEVONÓDOTT
});
