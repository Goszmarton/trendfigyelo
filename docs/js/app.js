// Trendfigyelő adatbetöltő réteg (Task 5) — fetch + cache-busting + IZOLÁLT hibaállapot.
// Chartot MÉG NEM rajzol (Task 6/7/8/9b); a betöltött adatot eltárolja, a hibákat a blokkba írja
// (nem néma, spec 7.5). Csak saját, relatív erőforrások — külső URL TILOS (Task 1).
"use strict";

const ADAT = "data/";
const HIBA_SZOVEG = "Hiba az adat betöltésekor";

// cache-busting: a naponta ugyanazon az útvonalon felülírt JSON-t a ?v= friss letöltésre kényszeríti (4.1)
function adat_url(rel) {
  return ADAT + rel + "?v=" + Date.now();
}

async function json_betolt(rel) {
  const valasz = await fetch(adat_url(rel));
  if (!valasz.ok) {
    throw new Error("HTTP " + valasz.status + " - " + rel);
  }
  return valasz.json();
}

// a hibaüzenet KÜLÖN gyerek-elembe kerül (nem írja felül a blokk esetleges tartalmát),
// és a KONKRÉT hiányzó fájl(oka)t + okot mondja (nem néma, nem tartalmatlan)
function hiba_kiir(blokk_id, reszletek) {
  const el = document.getElementById(blokk_id);
  if (!el) return;
  const p = document.createElement("p");
  p.className = "hiba";
  p.textContent = HIBA_SZOVEG + ": " + reszletek.join("; ") + ".";
  el.appendChild(p);
}

// blokk -> a hozzá tartozó init-fájlok
const BLOKKOK = [
  { id: "kulcsszo-blokk", fajlok: ["kulcsszo_regresszio.json", "kulcsszo_nyers.json"] },
  { id: "trend-blokk", fajlok: ["legfrissebb.json", "napok/index.json"] },
];

const adat = {}; // rel -> betöltött JSON (a Task 6/7/8/9b innen rajzol)

async function blokk_betolt(blokk) {
  // FÁJLONKÉNTI izoláció: egy hiányzó fájl (ma pl. kulcsszo_regresszio.json) NE tegye
  // használhatatlanná a blokk többi, sikeresen betöltött adatát (pl. kulcsszo_nyers.json).
  const eredmenyek = await Promise.allSettled(blokk.fajlok.map(function (rel) {
    return json_betolt(rel).then(function (json) { adat[rel] = json; });
  }));
  const hibak = [];
  eredmenyek.forEach(function (e, i) {
    if (e.status === "rejected") {
      hibak.push((e.reason && e.reason.message) || blokk.fajlok[i]);
    }
  });
  if (hibak.length) {
    hiba_kiir(blokk.id, hibak);
  }
}

async function init() {
  // blokkonkénti izoláció is: egy blokk hibája se döntse el a másikat
  return Promise.allSettled(BLOKKOK.map(blokk_betolt));
}

// igény szerinti napi trend-fájl (dátumválasztó — Task 6/7)
async function nap_betolt(datum) {
  return json_betolt("napok/" + datum + ".json");
}

document.addEventListener("DOMContentLoaded", init);
