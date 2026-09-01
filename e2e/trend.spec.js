const { test, expect } = require("@playwright/test");

// Trend-blokk smoke-ok (27 db; Task 7 + 8a + 8b + A3-cím) — MOCKOLT legfrissebb.json + napok/index.json + napok/<nap>.json.
// A DOM-szerződést az OSZT_T/ATTR_T konstansok rögzítik. A chart-sávok canvas-belsők → a tesztelhető
// eloszlást a szűrő-gombok data-count-jai + a caption hordozzák (a T8/L9 korlátja). A T16 a JSON-tömb
// szerializálást védi egy pipe-tartalmú kategórianévvel (a pipe-változat elhasítaná).
// Az interakciós tesztek LÉTEZÉS-asserttel kezdenek, hogy a hiba tiszta count-eltérés legyen,
// ne kattintás-timeout.

const T = "#trend-blokk";
const I = "#idosor-blokk";   // a kategória-idősor ÖNÁLLÓ szekciója (jobb doboz); a legend a bal #idosor-legend-ben

// nap-váltás az INLINE NAPTÁRRAL (a régi <select>.selectOption helyett): a cél-hónapra navigál (‹/›), majd a napra kattint.
async function napValt(page, nap) {
  const el = page.locator("#datum-valaszto");
  await el.locator(".naptar").waitFor();   // a naptár async renderelése UTÁN olvassuk a data-honap-ot (különben null → nincs navigáció)
  const celHo = nap.slice(0, 7);
  while ((await el.getAttribute("data-honap")) > celHo) await page.locator("#datum-valaszto .honap-lep.vissza").click();
  while ((await el.getAttribute("data-honap")) < celHo) await page.locator("#datum-valaszto .honap-lep.elore").click();
  await page.locator(`#datum-valaszto .nap-cella[data-nap="${nap}"]`).click();
}

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

// kategória-idősor fixture (kategoriak.json alakú), a shaper első-megjelenés / valós-0 szabályát célzó:
//   08-05 {A:2,B:1} · [08-06 HIÁNYZIK — NEM kerül a tengelyre] · 08-07 {A:1,C:3} · 08-08 {B:2}
//   → napok [08-05,08-07,08-08] (csak a mért napok); A [2,1,0] · B [1,0,2] · C [null,3,0]
const KAT_IDOSOR = { napok: [
  { nap: "2026-08-05", merve: true, lista_hossz: 3, lista_kategoriaval: 3, kategoria_nelkul: 0, kategoriak: { A: 2, B: 1 } },
  { nap: "2026-08-07", merve: true, lista_hossz: 4, lista_kategoriaval: 4, kategoria_nelkul: 0, kategoriak: { A: 1, C: 3 } },
  { nap: "2026-08-08", merve: true, lista_hossz: 2, lista_kategoriaval: 2, kategoria_nelkul: 0, kategoriak: { B: 2 } },
] };

// Szelet 2 top-5-szabály fixture: 7 nem-Other kategória EGYÉRTELMŰ kumulatív rangsorral + Other (a legnagyobb, hogy
// a „top-5 az Other NÉLKÜL" tényleg kizárja). Egy nap elég (a rangsor a kumulatív összegből jön). P>Q>R>S>T (top5) > U>V.
const KAT_TOP = { napok: [
  { nap: "2026-08-10", merve: true, lista_hossz: 20, lista_kategoriaval: 20, kategoria_nelkul: 0,
    kategoriak: { P: 20, Q: 16, R: 12, S: 8, T: 4, U: 2, V: 1, Other: 30 } },
] };

async function mock(page, opts) {
  // a kategória-idősor forrást MINDIG route-oljuk (default üres), hogy a teszt-szerver VALÓS kategoriak.json-ja
  // ne szivárogjon be (rejtett valós-adat-függés, a masodlagos-izoláció mintája a kulcsszo-suite-ból).
  await page.route(/kategoriak\.json/, function (r) {
    r.fulfill({ contentType: "application/json", body: JSON.stringify(opts.kategoriak || { napok: [] }) });
  });
  if (opts.legfrissebb) {
    await page.route(/legfrissebb\.json/, function (r) {
      r.fulfill({ contentType: "application/json", body: JSON.stringify(opts.legfrissebb) });
    });
  }
  // Task 9: a napok/index.json is MINDIG route-olt (alap üres), UGYANAZZAL az izolációs indokkal, mint a
  // kategoriak.json fent — a #1 "Ma felkapott" mostantól a LEGFRISSEBB napot is a napok/<nap>.json-ból olvassa,
  // ezért mockolatlanul a teszt-szerver VALÓS napi archívuma (docs/data/napok/) szivárogna be (dátum-drift →
  // nem-determinisztikus teszt). A konkrét napokat az opts.index ÍRJA FELÜL.
  await page.route(/napok\/index\.json/, function (r) {
    r.fulfill({ contentType: "application/json", body: JSON.stringify(opts.index || { napok: [] }) });
  });
  // ugyanígy MINDEN napok/<ISO-dátum>.json alapból 404 (a napfájl "nincs" ága) — a konkrét napokat opts.napok
  // ÍRJA FELÜL alább; a Playwright a KÉSŐBB regisztrált route-ot preferálja, ezért ez a széles route ELŐBB áll.
  await page.route(/napok\/\d{4}-\d{2}-\d{2}\.json/, function (r) {
    r.fulfill({ status: 404, contentType: "application/json", body: "{}" });
  });
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
  // Task 9: a szűrés-állapot (data-aktiv-kategoria) a SZEGMENS-konténeren él (per-szegmens szűrés), nem a
  // #trend-blokk-on — régi (nem szegmentált) napon EGYETLEN .trend-szegmens van, az hordozza az attribútumot.
  await expect(page.locator(`${T} .trend-szegmens`)).toHaveAttribute("data-aktiv-kategoria", "Politics");
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
  await napValt(page, "2026-08-01");
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
  // Task 9: a szűrés-állapot a SZEGMENS-konténeren él (lásd T5) — régi napon egyetlen .trend-szegmens van.
  await expect(page.locator(`${T} .trend-szegmens`)).toHaveAttribute("data-aktiv-kategoria", "Politics");
  await napValt(page, "2026-08-01");
  await expect(page.locator(`${T} .trend-szegmens`)).not.toHaveAttribute("data-aktiv-kategoria", /.+/);
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
  await napValt(page, "2026-08-01");
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
  // T21-ERŐSÍTÉS: a kategória-chart+szűrő IDŐSOR-FÜGGETLEN → a blokk-üres (idősor-bukás) jelzés MELLETT is
  // JELEN, mert a MIND_URES trendek kategóriásak (temak). A kód-út eddig is futott; most EXPLICIT assertálva.
  await expect(page.locator(`${T} canvas.kategoria-chart`)).toHaveCount(1);
  await expect(page.locator(`${T} .kategoria-szuro`)).toHaveCount(1);
});

// ── T22 — archív nap (temak nélkül, idosor-ral): sparkline MEGVAN, de kategória-chart + szűrő NINCS ──
test("22. archív nap → sparkline megvan, kategória-chart+szűrő nincs (diszkriminátor)", async ({ page }) => {
  const REGI_IDOS = [
    trend("autóversenyző", "10000", undefined, idosor_sorozat(4, "2026-07-29T20:52:00+00:00")),
    trend("valami", "5000", undefined, idosor_sorozat(3, "2026-07-29T21:00:00+00:00")),
  ];
  await mock(page, {
    legfrissebb: { top_trendek: [] },   // a legfrissebb nap üres, hogy a dátumválasztó a régi napra váltson
    index: { napok: ["2026-07-30", "2026-08-08"] },
    napok: { "2026-07-30": REGI_IDOS },
  });
  await page.goto("/");
  await napValt(page, "2026-07-30");
  // sparkline MEGVAN
  await expect(page.locator(`${T} .trend-kartya[data-idosor-allapot="van"]`)).toHaveCount(2);
  await expect(page.locator(`${T} .trend-sparkline-doboz canvas`)).toHaveCount(2);
  // kategória-chart + szűrő NINCS (nincs temak → nincs eloszlás → nincs összefoglaló)
  await expect(page.locator(`${T} .kategoria-chart-doboz`)).toHaveCount(0);
  await expect(page.locator(`${T} .kategoria-szuro`)).toHaveCount(0);
});

// ── T23 — 8b: van-görbe napon a normalizálás-magyarázat JELEN + KÉTFELŰ szöveg (volumen ÉS időzítés) ──
// A tooltip canvas-belső (L9/J3) → NEM assertálható; ezért a 8b DOM-szerződése a blokk-szintű magyarázat.
test("23. van-görbe napon a normalizálás-magyarázat jelen + kétfelű (volumen + időzítés)", async ({ page }) => {
  const VAN_KAT = [
    trend("alfa", "50000", ["Other"], idosor_sorozat(4, "2026-08-06T19:52:00+00:00")),
    trend("beta", "10000", ["Politics"], idosor_sorozat(3, "2026-08-06T20:00:00+00:00")),
  ];
  await mock(page, { legfrissebb: { top_trendek: VAN_KAT } });
  await page.goto("/");
  const nm = page.locator(`${T} .trend-normalizalas-magyarazat`);
  await expect(nm).toHaveCount(1);
  await expect(nm).toContainText("volumen");    // mi NEM olvasható ki → a keresettséget a volumen mutatja
  await expect(nm).toContainText("időzítés");   // mi IGEN → a görbe alakja + a csúcs időzítése
});

// ── T24 — 8b: mind-üres napon NINCS normalizálás-magyarázat (diszkriminátor a blokk-üres jelzés mellett) ──
test("24. mind-üres nap → nincs normalizálás-magyarázat (van blokk-üres jelzés, de nincs görbe = nincs mit magyarázni)", async ({ page }) => {
  const MIND_URES = [
    trend("egy", "50000", ["Other"]),      // mind idosor: []
    trend("ketto", "5000", ["Politics"]),
  ];
  await mock(page, { legfrissebb: { top_trendek: MIND_URES } });
  await page.goto("/");
  await expect(page.locator(`${T} .trend-idosor-ures-blokk`)).toHaveCount(1);        // a blokk-jelzés VAN
  await expect(page.locator(`${T} .trend-normalizalas-magyarazat`)).toHaveCount(0);  // a magyarázat NINCS
});

// ── T25 — 8b: DOM-sorrend — a magyarázat a LISTA ELŐTT (Q1: „előbb érkezzen"); a kategória-magyarázattól KÜLÖN elem ──
test("25. a normalizálás-magyarázat a lista ELŐTT áll, és külön elem a kategória-magyarázattól", async ({ page }) => {
  const VAN_KAT = [ trend("alfa", "50000", ["Other"], idosor_sorozat(4, "2026-08-06T19:52:00+00:00")) ];
  await mock(page, { legfrissebb: { top_trendek: VAN_KAT } });
  await page.goto("/");
  await expect(page.locator(`${T} .kategoria-magyarazat`)).toHaveCount(1);            // külön elem (kategóriás napon)
  await expect(page.locator(`${T} .trend-normalizalas-magyarazat`)).toHaveCount(1);
  const rend = await page.evaluate(function () {
    // Task 9: a lista/magyarázat a SZEGMENS-szekció gyereke (nem a #trend-blokk közvetlen gyereke) — régi
    // (nem szegmentált) napon egyetlen .trend-szegmens van, annak a gyerekein nézzük a sorrendet.
    const kids = Array.prototype.slice.call(document.querySelector("#trend-blokk .trend-szegmens").children);
    const idx = function (cls) { return kids.findIndex(function (e) { return e.classList.contains(cls); }); };
    return { nm: idx("trend-normalizalas-magyarazat"), lista: idx("trend-lista") };
  });
  expect(rend.nm).toBeGreaterThanOrEqual(0);
  expect(rend.lista).toBeGreaterThan(rend.nm);   // a magyarázat DOM-sorrendben a lista ELŐTT
});

// ── T26 — 8b: archív nap (görbe VAN, kategória NINCS) → magyarázat JELEN, összefoglaló NINCS ──
// A feltétel-szétválasztás igazolása: a magyarázat a !mind_ures-ből él (van görbe), NEM a kategóriából.
test("26. archív nap: görbe van/kategória nincs → normalizálás-magyarázat jelen, összefoglaló nincs", async ({ page }) => {
  const REGI_IDOS = [ trend("autóversenyző", "10000", undefined, idosor_sorozat(4, "2026-07-29T20:52:00+00:00")) ];
  await mock(page, {
    legfrissebb: { top_trendek: [] },   // a friss nap üres → a dátumválasztó a régi napra vált
    index: { napok: ["2026-07-30", "2026-08-08"] },
    napok: { "2026-07-30": REGI_IDOS },
  });
  await page.goto("/");
  await napValt(page, "2026-07-30");
  await expect(page.locator(`${T} .trend-normalizalas-magyarazat`)).toHaveCount(1);   // van görbe → magyarázat kell
  await expect(page.locator(`${T} .trend-osszefoglalo`)).toHaveCount(0);              // nincs kategória → nincs összefoglaló
});

// ── T27 — A3: a látható trend-cím »Ma felkapott keresések« (megkülönböztetés a »Kulcsszavak«-tól; DOM-szerződés-őr) ──
test("27. a trend-blokk h2 szövege »Ma felkapott keresések« (nem »Napi legfrissebb trendek«)", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 } });
  await page.goto("/");
  await expect(page.locator(`${T} h2`)).toHaveText("Ma felkapott keresések");
  await expect(page.locator(T)).toHaveAttribute("aria-label", "Ma felkapott keresések");
});

// ── T28 (MIN-TCP) — a trend-sparkline példány-nyilvántartás NE KULCSOLJON kifejezésre: két azonos
// kifejezésű trend a régi map-ben felülírta egymást → napváltáskor az ELSŐ Chart ÁRVÁN maradt (a takarit
// csak a map-ben lévő — utolsó — példányt destroy-olta). A rekesz-út (GORBE-B) leszemlézve, ez most mehet.
test("28. két azonos kifejezésű trend → napváltás UTÁN nincs árva Chart (nem kifejezés-kulcsú nyilvántartás)", async ({ page }) => {
  // A friss nap KÉT „dupla" nevű trendje (mindkettő idősorral → mindkettő sparkline-t rajzol).
  const DUPLA = [
    trend("dupla", "50000", ["Other"], idosor_sorozat(4, "2026-08-07T20:52:00+00:00")),
    trend("dupla", "10000", ["Other"], idosor_sorozat(3, "2026-08-07T21:00:00+00:00")),
  ];
  const REGI = [ trend("archív", "5000", ["Other"], idosor_sorozat(4, "2026-07-29T20:52:00+00:00")) ];
  await mock(page, {
    legfrissebb: { top_trendek: DUPLA },                 // a friss (08-08) nap = a két dupla
    index: { napok: ["2026-07-30", "2026-08-08"] },
    napok: { "2026-07-30": REGI },
  });
  await page.goto("/");

  // KÉT sparkline-canvas rajzolódik (a két azonos nevű kártyához külön canvas)
  const canvasok = page.locator(`${T} .trend-sparkline-doboz canvas`);
  await expect(canvasok).toHaveCount(2);
  const fogantyuk = await canvasok.elementHandles();
  // SANITY: mindkét Chart él a napváltás ELŐTT (a teszt-beállítás nem üres)
  const el_elotte = await Promise.all(fogantyuk.map(function (h) {
    return page.evaluate(function (c) { return !!(window.Chart && Chart.getChart(c)); }, h);
  }));
  expect(el_elotte.filter(Boolean).length).toBe(2);

  // NAPVÁLTÁS a régi napra → trend_blokk_render → trend_chart_takarit() destroy-ol MINDENT, amit nyilvántart.
  // A váltás ASZINKRON (napok/<nap>.json fetch) → determinisztikusan a data-nap attribútumra várunk (a
  // .trend-kifejezes-re várni strict-mode-ot dobna az átmeneti két „dupla"-n).
  await napValt(page, "2026-07-30");
  await expect(page.locator("#trend-blokk")).toHaveAttribute("data-nap", "2026-07-30");
  await expect(page.locator(`${T} .trend-kartya`)).toHaveCount(1);            // a régi nap kártyái leültek (a 2 „dupla" eltűnt)
  await expect(page.locator(`${T} .trend-kifejezes`)).toHaveText("archív");   // egyetlen kártya → a régi nap kirajzolódott

  // A napváltás után a KÉT régi-napi canvashoz kötött Chart EGYIKE SEM élhet. A bugos (kifejezés-kulcsú)
  // map csak az utolsó „dupla" példányt destroy-olta → az első ÁRVÁN maradt (Chart.getChart még visszaadja).
  const el_utana = await Promise.all(fogantyuk.map(function (h) {
    return page.evaluate(function (c) { return !!(window.Chart && Chart.getChart(c)); }, h);
  }));
  expect(el_utana.filter(Boolean).length).toBe(0);
});

// ── Task 9 — #1 Napi „Ma felkapott": szegmentált nap → két blokk egymás alatt (Reggeli/Esti), per-szegmens szűrés ──
test("N. napi: szegmentált nap két blokkja (Reggeli + Esti), saját chippel", async ({ page }) => {
  const IDX = { napok: ["2026-08-31"] };
  await page.route(/kategoriak\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: [] }) }));
  await page.route(/legfrissebb\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: [], kulcsszavak: {}, kulcsszo_osszesites: [] }) }));
  await page.route(/napok\/index\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify(IDX) }));
  await page.route(/napok\/2026-08-31\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({
    nap: "2026-08-31",
    reggel: { trendek: [trend("reggeli-szo", "5000", ["Sports"])], frissitve: "2026-08-31T07:00:00+00:00" },
    este: { trendek: [trend("esti-szo", "9000", ["Politics"]), trend("esti-ketto", "8000", ["Politics"])], frissitve: "2026-08-31T19:00:00+00:00" },
  }) }));
  await page.goto("/");
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="reggel"]')).toBeVisible();
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="este"]')).toBeVisible();
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="reggel"] .trend-kartya')).toHaveCount(1);
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="este"] .trend-kartya')).toHaveCount(2);
  // per-szegmens szűrő: az esti "Politics (2)" chip csak az esti blokkban
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="este"] .kategoria-szuro button[data-kategoria="Politics"]')).toHaveAttribute("data-count", "2");
});

test("N+1. napi: régi (nem szegmentált) nap egyetlen blokk, cím nélkül", async ({ page }) => {
  await page.route(/kategoriak\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: [] }) }));
  await page.route(/legfrissebb\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: [], kulcsszavak: {}, kulcsszo_osszesites: [] }) }));
  await page.route(/napok\/index\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: ["2026-08-20"] }) }));
  await page.route(/napok\/2026-08-20\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({
    nap: "2026-08-20", trendek: [trend("regi-szo", "5000", ["Sports"])],
  }) }));
  await page.goto("/");
  await expect(page.locator('#trend-blokk .trend-szegmens')).toHaveCount(1);
  await expect(page.locator('#trend-blokk .trend-szegmens-cim')).toHaveCount(0);   // régi napon nincs címke
  await expect(page.locator('#trend-blokk .trend-kartya')).toHaveCount(1);
});

test("N+2. napi: kék-vonalas gyűjtés-info a cím alatt + beszédes blokk-fejlécek (reggel/este lekérdezés)", async ({ page }) => {
  const IDX = { napok: ["2026-08-31"] };
  await page.route(/kategoriak\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: [] }) }));
  await page.route(/legfrissebb\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: [], kulcsszavak: {}, kulcsszo_osszesites: [] }) }));
  await page.route(/napok\/index\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify(IDX) }));
  await page.route(/napok\/2026-08-31\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({
    nap: "2026-08-31",
    reggel: { trendek: [trend("reggeli-szo", "5000", ["Sports"])], frissitve: "2026-08-31T07:00:00+00:00" },
    este: { trendek: [trend("esti-szo", "9000", ["Politics"])], frissitve: "2026-08-31T19:00:00+00:00" },
  }) }));
  await page.goto("/");
  // (1a) statikus kék-vonalas gyűjtés-info a szekció-cím alatt
  const info = page.locator("#trend-blokk .trend-gyujtes-info");
  await expect(info).toBeVisible();
  await expect(info).toContainText("naponta kétszer");
  await expect(info).toContainText("9:00");
  await expect(info).toContainText("21:00");
  // (1b) beszédes blokk-fejlécek a kártyák fölött
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="reggel"] .trend-szegmens-cim')).toHaveText("Reggeli lekérdezés · 9:00");
  await expect(page.locator('#trend-blokk .trend-szegmens[data-szegmens="este"] .trend-szegmens-cim')).toHaveText("Esti lekérdezés · 21:00");
});

// ── KATEGÓRIA-IDŐSOR Szelet 1 — shaper + DOM-tükör (.idosor-adat). Canvast NEM érint, DOM-assertálható. ──
// A tükör a null-rés / első-megjelenés / valós-0 szabályt hordozza (JSON-tömb data-ertekek, mint a data-kategoriak).
test("idősor-adat: a tengely CSAK a mért napokat tartalmazza (08-06 hiányzó nap KIMARAD)", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 }, kategoriak: KAT_IDOSOR });
  await page.goto("/");
  const adat = page.locator(`${I} .idosor-adat`);
  await expect(adat).toHaveCount(1);
  await expect(adat).toHaveAttribute("data-napok",
    JSON.stringify(["2026-08-05", "2026-08-07", "2026-08-08"]));   // 08-06 NINCS a tengelyen → folytonos vonal
  await expect(adat.locator('.idosor-vonal[data-kategoria="A"]')).toHaveAttribute("data-ertekek", "[2,1,0]");
  await expect(adat.locator('.idosor-vonal[data-kategoria="B"]')).toHaveAttribute("data-ertekek", "[1,0,2]");
});

test("idősor-adat: a kategória első megjelenése ELŐTT null (nem lapos nulla)", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 }, kategoriak: KAT_IDOSOR });
  await page.goto("/");
  const adat = page.locator(`${I} .idosor-adat`);
  await expect(adat).toHaveCount(1);
  // C csak 08-07-en tűnik fel → 08-05 null (a vonal a feltűnéskor kezdődik), 08-08-on valós 0
  await expect(adat.locator('.idosor-vonal[data-kategoria="C"]')).toHaveAttribute("data-ertekek", "[null,3,0]");
});

test("idősor-adat: jelen-napon a 0-előfordulás VALÓS 0 (nem null)", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 }, kategoriak: KAT_IDOSOR });
  await page.goto("/");
  const adat = page.locator(`${I} .idosor-adat`);
  await expect(adat).toHaveCount(1);
  // A a 08-08-on hiányzik a kategoriak-mapből, DE már megjelent → VALÓS 0 (index 2); B a 08-07-en 0 (index 1)
  await expect(adat.locator('.idosor-vonal[data-kategoria="A"]')).toHaveAttribute("data-ertekek", "[2,1,0]");
  await expect(adat.locator('.idosor-vonal[data-kategoria="B"]')).toHaveAttribute("data-ertekek", "[1,0,2]");
});

test("idősor-adat: a vonalak száma == az előfordult kategóriák (a nem-látott NINCS)", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 }, kategoriak: KAT_IDOSOR });
  await page.goto("/");
  const adat = page.locator(`${I} .idosor-adat`);
  await expect(adat).toHaveCount(1);
  await expect(adat).toHaveAttribute("data-vonal-szam", "3");      // A, B, C — nem több
  await expect(adat.locator(".idosor-vonal")).toHaveCount(3);
});

// ── KATEGÓRIA-IDŐSOR Szelet 2 — line-chart (canvas), most KÉTDOBOZOS: legend a BAL #idosor-legend, chart a JOBB
// #idosor-blokk. A canvas-belső (szürke→kék kiemelés) NEM DOM-assertálható → SZEMLE-köteles; a HTML-legend AKTÍV
// állapota (.kiemelt) + a data-idosor-aktiv tükör DOM-assertálható. ──
test("idősor-chart: canvas + data-idosor-chart-rendered a JOBB #idosor-blokk-ban", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 }, kategoriak: KAT_TOP });
  await page.goto("/");
  await expect(page.locator(`${I} canvas.idosor-chart`)).toHaveCount(1);
  await expect(page.locator(`${I} canvas.idosor-chart`)).toHaveAttribute("data-idosor-chart-rendered", "true");
  await expect(page.locator(`${T} canvas.idosor-chart`)).toHaveCount(0);   // NEM a trend-blokkban (átköltözött)
});

// ÚJRATERVEZÉS (SZEMLE-visszajelzés): a szín/kiemelés modell szürke-alap + kék-kiemelés (canvas-belső → SZEMLE),
// a korábbi top-5-default / per-kategória-szín SZABÁLY MEGSZŰNT. A DOM-assertálható: cím, elhelyezés, caption, tükör.
test("idősor-chart: a jobb doboz h2 címe »Napi keresési kategóriák idősora«", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 }, kategoriak: KAT_TOP });
  await page.goto("/");
  await expect(page.locator(`${I} h2`)).toHaveText("Napi keresési kategóriák idősora");
});

test("idősor-elrendezés: az idősor SAJÁT #idosor-blokk szekció, a DOM-ban a #trend-blokk ELŐTT", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 }, kategoriak: KAT_TOP });
  await page.goto("/");
  await expect(page.locator(I)).toHaveCount(1);
  const elotte = await page.evaluate(function () {
    const idos = document.querySelector("#idosor-blokk");
    const trend = document.querySelector("#trend-blokk");
    // az idősor-szekció a trend-szekció ELŐTT áll (nem a trend-blokkon BELÜL)
    return !!(idos && trend && !trend.contains(idos)
      && (idos.compareDocumentPosition(trend) & Node.DOCUMENT_POSITION_FOLLOWING));
  });
  expect(elotte).toBe(true);   // az idősor MEGELŐZI a „Ma felkapott keresések" szekciót
});

test("idősor-chart: a cím a canvas ELŐTT, a magyarázat a canvas UTÁN (a jobb dobozban)", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 }, kategoriak: KAT_IDOSOR });   // legkorábbi 2026-08-05
  await page.goto("/");
  const mag = page.locator(`${I} .idosor-magyarazat`);
  await expect(mag).toContainText("2026-08-05");
  await expect(mag).toContainText("Google Trends");
  await expect(mag).toContainText("több kategóriába");   // multi-kategória megjegyzés
  const sorrend = await page.evaluate(function () {
    const b = document.querySelector("#idosor-blokk");
    const cim = b.querySelector("h2");
    const canvas = b.querySelector("canvas.idosor-chart");
    const mag = b.querySelector(".idosor-magyarazat");
    const cimElotte = cim.compareDocumentPosition(canvas) & Node.DOCUMENT_POSITION_FOLLOWING;   // cim < canvas
    const magUtan = canvas.compareDocumentPosition(mag) & Node.DOCUMENT_POSITION_FOLLOWING;      // canvas < mag
    return !!(cimElotte && magUtan);
  });
  expect(sorrend).toBe(true);
});

// ── #2 szegmens-váltó — a kategória-idősor szegmentált kategoriak.json-t olvas, alap a Napi összesen szegmens ──
test("N. idősor: szegmens-váltó — alap Napi összesen, váltásra a reggeli számok", async ({ page }) => {
  const KJ = { napok: [
    { nap: "2026-08-10",
      reggel: { kategoriak: { "Sports": 3 } },
      este:   { kategoriak: { "Sports": 1, "Politics": 2 } } },
  ]};
  await page.route(/kategoriak\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify(KJ) }));
  await page.route(/legfrissebb\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: [] }) }));
  await page.route(/napok\/index\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: ["2026-08-10"] }) }));
  await page.goto("/");
  const tukor = page.locator("#idosor-blokk .idosor-adat");
  await expect(tukor).toHaveAttribute("data-vonal-szam", "2");                 // osszesen: Sports + Politics
  await expect(page.locator('.idosor-szegmens-valto [data-szegmens="osszesen"]')).toHaveAttribute("aria-pressed", "true");
  await page.locator('.idosor-szegmens-valto [data-szegmens="reggel"]').click();
  await expect(page.locator("#idosor-blokk .idosor-adat")).toHaveAttribute("data-vonal-szam", "1");  // reggel: csak Sports
});

// ── Napi összesen mód — a nap MEGLÉVŐ szegmenseinek darabszám-összege ──
test("N. idősor: Napi összesen — reggel+este darabszám-összeg", async ({ page }) => {
  await mock(page, { kategoriak: { napok: [
    { nap: "2026-09-01", reggel: { kategoriak: { Sports: 3, Other: 8 } },
                          este:   { kategoriak: { Sports: 1, Politics: 2, Other: 12 } } } ] } });
  await page.goto("/");
  const tukor = page.locator("#idosor-blokk .idosor-adat");
  await expect(tukor.locator('.idosor-vonal[data-kategoria="Sports"]')).toHaveAttribute("data-ertekek", "[4]");
  await expect(tukor.locator('.idosor-vonal[data-kategoria="Politics"]')).toHaveAttribute("data-ertekek", "[2]");
  await expect(tukor.locator('.idosor-vonal[data-kategoria="Other"]')).toHaveAttribute("data-ertekek", "[20]");
});

test("N. idősor: Napi összesen — csak reggeli nap → csak a reggeli számít (nincs áthúzott este)", async ({ page }) => {
  await mock(page, { kategoriak: { napok: [
    { nap: "2026-09-01", reggel: { kategoriak: { Sports: 3 } } } ] } });   // NINCS este
  await page.goto("/");
  await expect(page.locator('#idosor-blokk .idosor-adat .idosor-vonal[data-kategoria="Sports"]'))
    .toHaveAttribute("data-ertekek", "[3]");
});

test("N. idősor: Napi összesen — régi lapos rekord EGYSZER számít", async ({ page }) => {
  await mock(page, { kategoriak: { napok: [
    { nap: "2026-08-05", kategoriak: { A: 2 } } ] } });   // legacy (nincs reggel/este)
  await page.goto("/");
  await expect(page.locator('#idosor-blokk .idosor-adat .idosor-vonal[data-kategoria="A"]'))
    .toHaveAttribute("data-ertekek", "[2]");
});

test("N. idősor: három szegmens-gomb, sorrend Napi összesen · Reggeli · Esti, alap az összesen", async ({ page }) => {
  await mock(page, { kategoriak: { napok: [
    { nap: "2026-09-01", reggel: { kategoriak: { Sports: 3 } }, este: { kategoriak: { Politics: 2 } } } ] } });
  await page.goto("/");
  const gombok = page.locator(".idosor-szegmens-valto button");
  await expect(gombok).toHaveCount(3);
  await expect(gombok.nth(0)).toHaveAttribute("data-szegmens", "osszesen");
  await expect(gombok.nth(1)).toHaveAttribute("data-szegmens", "reggel");
  await expect(gombok.nth(2)).toHaveAttribute("data-szegmens", "este");
  await expect(gombok.nth(0)).toHaveText("Napi összesen");
  await expect(gombok.nth(0)).toHaveAttribute("aria-pressed", "true");
});

// ── #2 fix: üres szegmensre váltva a váltó MARAD (nincs zsákutca) + rövid jelzés; vissza-váltás újra chartot ad ──
test("N. idősor: üres szegmensen a váltó látszik + vissza lehet váltani", async ({ page }) => {
  const KJ = { napok: [
    { nap: "2026-08-10", este: { kategoriak: { "Sports": 2 } } },   // CSAK esti adat; reggeli NINCS
  ]};
  await page.route(/kategoriak\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify(KJ) }));
  await page.route(/legfrissebb\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ top_trendek: [] }) }));
  await page.route(/napok\/index\.json/, r => r.fulfill({ contentType: "application/json", body: JSON.stringify({ napok: ["2026-08-10"] }) }));
  await page.goto("/");
  await expect(page.locator("#idosor-blokk .idosor-adat")).toHaveAttribute("data-vonal-szam", "1");   // este: van chart
  // váltás reggelre → nincs adat, DE a váltó marad + jelzés
  await page.locator('.idosor-szegmens-valto [data-szegmens="reggel"]').click();
  await expect(page.locator(".idosor-szegmens-valto")).toHaveCount(1);                                 // a váltó NEM tűnt el
  await expect(page.locator('.idosor-szegmens-valto [data-szegmens="reggel"]')).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#idosor-blokk .idosor-adat")).toHaveCount(0);                             // nincs tükör (üres)
  await expect(page.locator("#idosor-blokk .idosor-magyarazat")).toContainText("nincs kategória-adat");
  // vissza este-re → újra van chart
  await page.locator('.idosor-szegmens-valto [data-szegmens="este"]').click();
  await expect(page.locator("#idosor-blokk .idosor-adat")).toHaveAttribute("data-vonal-szam", "1");
});

// ── HTML-legend a BAL #idosor-legend dobozban (a Chart.js belső legend kikapcsolva) — DOM-assertálható ──
test("idősor-legend: a bal #idosor-legend N kattintható elemet tartalmaz (data-kategoria), a jobb dobozban NINCS legend", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 }, kategoriak: KAT_IDOSOR });   // A, B, C → 3 vonal
  await page.goto("/");
  const legend = page.locator("#idosor-legend .idosor-legend-elem");
  await expect(legend).toHaveCount(3);
  await expect(page.locator('#idosor-legend .idosor-legend-elem[data-kategoria="A"]')).toHaveCount(1);
  await expect(page.locator('#idosor-legend .idosor-legend-elem[data-kategoria="B"]')).toHaveCount(1);
  await expect(page.locator('#idosor-legend .idosor-legend-elem[data-kategoria="C"]')).toHaveCount(1);
  await expect(page.locator(`${I} .idosor-legend-elem`)).toHaveCount(0);   // a legend NEM a jobb (chart) dobozban van
});

test("idősor-legend: kattintásra az elem .kiemelt lesz + data-idosor-aktiv tükör; újrakatt törli (toggle)", async ({ page }) => {
  await mock(page, { legfrissebb: { top_trendek: MAI16 }, kategoriak: KAT_IDOSOR });
  await page.goto("/");
  const bE = page.locator('#idosor-legend .idosor-legend-elem[data-kategoria="B"]');
  await expect(bE).toHaveCount(1);
  // alap (user-kérés): az ELSŐ kategória KIEMELT (nem „mind szürke")
  await expect(page.locator("#idosor-legend .idosor-legend-elem.kiemelt")).toHaveCount(1);
  await expect(page.locator("#idosor-legend .idosor-legend-elem").first()).toHaveClass(/kiemelt/);   // az első a kiemelt
  await expect(page.locator(I)).not.toHaveAttribute("data-idosor-aktiv", "");                         // van alap-kiválasztás
  // katt B-re → B kiemelt, más nem; a tükör B
  await bE.click();
  await expect(bE).toHaveClass(/kiemelt/);
  await expect(page.locator("#idosor-legend .idosor-legend-elem.kiemelt")).toHaveCount(1);
  await expect(page.locator(I)).toHaveAttribute("data-idosor-aktiv", "B");
  // újra B → reset (toggle)
  await bE.click();
  await expect(page.locator("#idosor-legend .idosor-legend-elem.kiemelt")).toHaveCount(0);
  await expect(page.locator(I)).toHaveAttribute("data-idosor-aktiv", "");
});
