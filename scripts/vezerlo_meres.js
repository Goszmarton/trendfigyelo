// VEZERLŐ-MAGASSÁG mérő-harness (dev-eszköz, NEM a Playwright-suite része).
//
// MIRE VALÓ: az #intervallum-vezerlo magasságát + az első kulcsszó-kártya top-ját méri egy adott
// viewporton, a JELENLEGI (valós docs/data) és egy MOCKOLT 0-másodlagos állapotban. A vezérlő
// magassága a LETILTOTT intervallum-gombok ok-szövegeitől nő (minden tiltott gomb egy .ok sort ad).
//
// MIÉRT MARAD A REPÓBAN: a CSS-t érintő változásoknál (pl. MIN-CSS, app.css vezérlő-szabályok) ez a
// NO-OP igazolás eszköze — előtte/utána futtatva a JELENLEGI magasság (ma 235px @390×844; a CSS+MAGYARÁZÓ kör
// gomb-magyarázat sub-szövegei 155→235px-re növelték, ez SZÁNDÉKOS, nem regresszió) NEM változhat.
// Ha a szám elmozdul, az REGRESSZIÓ. FONTOS: a kiírt px-számok VIEWPORT-FÜGGŐK — a méret a kimenetben
// szerepel, hogy egy szám NE avuljon el úgy, ahogy egy régi, kontextus nélküli mérés (lásd VEZERLO-MAGAS
// leltár-tétel: a régi „hajtás alá tolja" 320px MAGAS viewporton készült, portré 390×844-en nem áll).
//
// FUTTATÁS:  node scripts/vezerlo_meres.js         (saját http.server-t indít a docs/-ra a 8000 porton)
//            VP=375x667 node scripts/vezerlo_meres.js   (más viewport, pl. iPhone SE)

const { chromium } = require("@playwright/test");
const { spawn } = require("child_process");

const [VW, VH] = (process.env.VP || "390x844").split("x").map(Number);
const PORT = 8000;
const BASE = "http://localhost:" + PORT + "/";

async function meres(page, cimke) {
  await page.setViewportSize({ width: VW, height: VH });
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  const r = await page.evaluate(() => {
    const vez = document.getElementById("intervallum-vezerlo");
    const gombok = vez ? vez.querySelectorAll("button[data-intervallum]") : [];
    const tiltott = vez ? vez.querySelectorAll("button[data-intervallum][disabled]") : [];
    const okok = vez ? vez.querySelectorAll(".intervallum-tetel .ok") : [];
    const elsoKartya = document.querySelector("#kulcsszo-blokk .kulcsszo-chart");
    return {
      vezerlo_magassag: vez ? Math.round(vez.offsetHeight) : null,
      gomb_db: gombok.length,
      engedelyezett_db: gombok.length - tiltott.length,
      tiltott_db: tiltott.length,
      ok_szoveg_db: okok.length,
      elso_kartya_top: elsoKartya ? Math.round(elsoKartya.getBoundingClientRect().top) : null,
    };
  });
  const fold = r.elso_kartya_top != null && r.elso_kartya_top < VH ? "FÖLÖTTE (látszik)" : "ALATTA (rejtve)";
  console.log(`\n[${cimke}] viewport ${VW}×${VH}:`);
  console.log(`  vezérlő magasság: ${r.vezerlo_magassag}px`);
  console.log(`  gombok: ${r.gomb_db} (engedélyezett ${r.engedelyezett_db}, tiltott ${r.tiltott_db}), ok-szövegek: ${r.ok_szoveg_db}`);
  console.log(`  első kártya top: ${r.elso_kartya_top}px → a ${VH}-es hajtás ${fold}`);
  return r;
}

(async () => {
  // saját statikus szerver a docs/-ra (a Playwright-config webServerével egyező parancs)
  const srv = spawn(".venv/bin/python", ["-m", "http.server", String(PORT), "--directory", "docs"],
    { cwd: __dirname + "/..", stdio: "ignore" });
  await new Promise((res) => setTimeout(res, 1500));

  const browser = await chromium.launch();
  try {
    const p1 = await browser.newContext();
    const jelen = await meres(await p1.newPage(), "JELENLEGI (valós docs/data)");
    await p1.close();

    const p2 = await browser.newContext();
    const page2 = await p2.newPage();
    await page2.route(/kulcsszo_masodlagos_regresszio\.json/, (route) =>
      route.fulfill({ contentType: "application/json", body: JSON.stringify({ kulcsszavak: {} }) }));
    const nulla = await meres(page2, "MOCKOLT 0-másodlagos");
    await p2.close();

    console.log("\n=== ÖSSZEGZÉS ===");
    console.log(`vezérlő: ${jelen.vezerlo_magassag}px (valós) → ${nulla.vezerlo_magassag}px (0 mp), Δ=${nulla.vezerlo_magassag - jelen.vezerlo_magassag}px`);
    console.log(`első kártya top: ${jelen.elso_kartya_top}px (valós) → ${nulla.elso_kartya_top}px (0 mp), viewport-magasság ${VH}`);
  } finally {
    await browser.close();
    srv.kill();
  }
})();
