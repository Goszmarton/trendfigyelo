const { test, expect } = require("@playwright/test");

// Task 7 trend-blokk smoke-ok (16 db) — MOCKOLT legfrissebb.json + napok/index.json + napok/<nap>.json.
// A DOM-szerződést az OSZT_T/ATTR_T konstansok rögzítik. A chart-sávok canvas-belsők → a tesztelhető
// eloszlást a szűrő-gombok data-count-jai + a caption hordozzák (a T8/L9 korlátja). A T16 a JSON-tömb
// szerializálást védi egy pipe-tartalmú kategórianévvel (a pipe-változat elhasítaná).
// Az interakciós tesztek LÉTEZÉS-asserttel kezdenek, hogy a hiba tiszta count-eltérés legyen,
// ne kattintás-timeout.

const T = "#trend-blokk";

// egy trend-elem; temak === undefined → a mező HIÁNYZIK (régi archív nap), [] → nincs besorolás, [...] → van
function trend(kifejezes, volumen, temak) {
  const e = { kifejezes, volumen, novekedes_pct: "100", idosor: [], hirek: [] };
  if (temak !== undefined) { e.temak = temak; e.topics = temak.map(function (_, i) { return i + 1; }); }
  return e;
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
