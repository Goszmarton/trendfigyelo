const { test, expect } = require("@playwright/test");

// §7.1 per-szekció sticky vezérlősávok — SZERKEZETI (ST1) + COMPUTED-STYLE (ST2) smoke.
// STUB-RED (SORREND 2): ma nincs .szekcio/.vezerlo-sav wrapper (a DOC-COMMIT csak a spec-et
// írta át; a HTML/CSS a GREEN-lépés) → mindkét teszt VISELKEDÉSBELI expect-eltéréssel BUKIK
// (ST1: toHaveCount(1) → Received 0; ST2: not.toHaveCount(0) → Received 0). Szándékosan zöld ÚJ teszt NINCS.
//
// A vizuális "tényleg tapad-e görgetéskor" (scroll + boundingBox) FLAKY → NEM ide tartozik,
// kézi szemle (L9). Itt csak a szerkezet és a computed position őrizhető megbízhatóan.
//
// :has() a Playwright CSS-engine-jében 1.15 óta támogatott (itt 1.62.1) — ha mégsem menne, a RED
// nem "Received 0" lenne, hanem szelektor-hiba, tehát a futás maga is igazolja a :has() működését.
// Verzió-független tartalék (ha valaha regresszálna):
//   page.locator(".szekcio").filter({ has: page.locator("#kulcsszo-blokk") }).locator("#intervallum-vezerlo")

test("ST1. per-szekció szerkezet: intervallum-vezérlő a Kulcsszavak szekcióban, dátumválasztó a Trend szekcióban (keresztben nem)", async ({ page }) => {
  await page.goto("/");
  // POZITÍV előbb: ez adja a valódi RED-et (a .szekcio wrapper hiányzik → count 0), NEM a keresztellenőrzés.
  await expect(page.locator(".szekcio:has(#kulcsszo-blokk) #intervallum-vezerlo")).toHaveCount(1);
  await expect(page.locator(".szekcio:has(#trend-blokk) #datum-valaszto")).toHaveCount(1);
  // keresztben NEM: a dátumválasztó nincs a Kulcsszavak szekcióban (GREEN után válik érdemivé).
  await expect(page.locator(".szekcio:has(#kulcsszo-blokk) #datum-valaszto")).toHaveCount(0);
});

test("ST2. a .vezerlo-sav computed position: sticky (asztali)", async ({ page }) => {
  await page.goto("/");
  // RED itt: nincs .vezerlo-sav → Received 0 (viselkedésbeli, nem hard-timeout); a guard eldob, így az
  // evaluate le sem fut, nem lesz 30 s-es locator-timeout.
  await expect(page.locator(".vezerlo-sav")).not.toHaveCount(0);
  const pos = await page.locator(".vezerlo-sav").first().evaluate(function (el) {
    return getComputedStyle(el).position;
  });
  expect(pos).toBe("sticky");
});
