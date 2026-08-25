const { test, expect } = require("@playwright/test");
const Y = "#youtube-blokk";

function iso(d) { return new Date(d).toISOString(); }
function napiPontok(n) {
  const ki = []; const kezd = Date.UTC(2026, 4, 22);
  for (let i = 0; i < n; i++) ki.push({ idopont_utc: iso(kezd + i*86400000), ertek: 40, reszleges: i === n-1 });
  return ki;
}
function ivErvenyes() {
  return { ervenyes: true, meredekseg_nap: 0.5, irany: "novekszik", r2: 0.4,
           ablak_kezdet_utc: iso(Date.UTC(2026,4,22)), ablak_veg_utc: iso(Date.UTC(2026,7,20)),
           illesztes_vonal: [{idopont_utc: iso(Date.UTC(2026,4,22)), ertek: 30},
                             {idopont_utc: iso(Date.UTC(2026,7,20)), ertek: 50}],
           se_masodlagos_autokorrelacio: true, r2_masodlagos_autokorrelacio: true,
           pontok_hasznalt: 90, mai_ertek: 50, illeszkedes: "illeszkedik" };
}
function ivRovidHet() { return { ervenyes: false, ok: "keves_pont" }; }

async function mock(page, { reg, nyers }) {
  const rou = async (rel, obj) =>
    page.route(u => u.pathname.endsWith(rel), r => r.fulfill({ json: obj }));
  await rou("youtube_regresszio.json", reg);
  await rou("youtube_nyers.json", nyers);
  // a Google-blokkok üresek maradjanak (ne szivárogjon a teszt-szerver adata)
  for (const f of ["kulcsszo_regresszio.json","kulcsszo_nyers.json","kulcsszo_masodlagos_nyers.json",
                   "kulcsszo_masodlagos_regresszio.json","kulcsszo_lanc.json"])
    await rou(f, { kulcsszavak: {} });
}

test("YouTube-fül: kosár-csoportok + napi szó rajzol + trend", async ({ page }) => {
  await mock(page, {
    reg: { kulcsszavak: {
      "edzés": { racs: "nap", aktiv: true, domen: "egeszseg", tipus: "szintmero",
                 intervallumok: { "1_het": ivErvenyes(), "2_het": ivErvenyes(),
                                  "1_ho": ivErvenyes(), "3_ho": ivErvenyes(), "1_ev": ivErvenyes() } },
      "klíma": { racs: "het", aktiv: true, domen: "otthon", tipus: "szintmero",
                 intervallumok: { "1_het": ivRovidHet(), "2_het": ivRovidHet(),
                                  "1_ho": ivErvenyes(), "3_ho": ivErvenyes(), "1_ev": ivErvenyes() } },
    }},
    nyers: { kulcsszavak: {
      "edzés": [{ kulcsszo:"edzés", racs:"nap", timeframe:"today 3-m",
                  ablak_kezdet_utc: iso(Date.UTC(2026,4,22)), ablak_veg_utc: iso(Date.UTC(2026,7,20)),
                  pontok: napiPontok(90) }],
      "klíma": [{ kulcsszo:"klíma", racs:"het", timeframe:"today 12-m",
                  ablak_kezdet_utc: iso(Date.UTC(2025,7,20)), ablak_veg_utc: iso(Date.UTC(2026,7,20)),
                  pontok: napiPontok(53) }],
    }},
  });
  await page.goto("/youtube.html");
  await expect(page.locator(`${Y} .domen-csoport`)).toHaveCount(2);       // 2 kosár
  await expect(page.locator(`${Y} .kulcsszo-chart`)).toHaveCount(2);
  // váltás 1 hét ablakra: az edzés (napi) rajzol, a klíma (heti) a "túl rövid" üzenetet hozza
  await page.locator('#youtube-intervallum-vezerlo button', { hasText: "1 hét" }).click();
  await expect(page.locator(`${Y} .kulcsszo-chart[data-drawable="true"]`)).toHaveCount(1);
  await expect(page.locator(`${Y} .kulcsszo-chart .ok`)).toContainText("túl rövid");
});
