"use strict";
// Színek egy helyen: a CSS-tokenek (docs/css/app.css :root) olvasása, témaszínek, közös Chart.js-alap.
// Klasszikus script (globális függvények), Node-tesztekhez module.exports-szal (ai_szunet.js mintája).
// Betöltési sorrend: vendor/chartjs/chart.umd.js (ha van) → szinek.js → az oldal saját JS-e.
// Az app.css a <head>-ben van, így a getComputedStyle a script futásakor már érvényes.

// A tartalékértékek a token-értékek tükrei: ha a stíluslap nem érhető el (vagy Node-ban fut), se törjön a rajzolás.
const SZIN_TARTALEK = {
  "hatter": "#F5F6F4", "kartya": "#FFFFFF", "keret": "#E2E5E3", "szoveg": "#1A1D20", "szoveg-2": "#66707A",
  "akcentus": "#1F8A8A", "ok": "#2E8B57", "figy": "#D9A21B", "hiba": "#C8414B", "semleges": "#98A0A8",
  "google": "#3B6FD8", "youtube": "#D6453D",
  "tema-1": "#0072B2", "tema-2": "#E69F00", "tema-3": "#009E73", "tema-4": "#CC79A7",
  "tema-5": "#56B4E9", "tema-6": "#D55E00", "tema-7": "#F0E442", "tema-8": "#4D4D4D",
  "graf-ml": "#8e44ad", "graf-elorejelzes": "#16a085", "graf-elorejelzes-sav": "rgba(22, 160, 133, 0.15)",
  "graf-trend": "#cc3333", "graf-szint": "#e69138", "graf-sav": "rgba(120, 120, 120, 0.14)",
  "graf-jelolo": "#8a8a8a", "graf-racs": "#EEF0EE",
  "betu": '"Inter", system-ui, "Segoe UI", sans-serif',
};

// a token értéke (pl. "google" → "#3B6FD8"), ahogy a CSS-ben szerepel, trimmelve; hiányában a tartalék.
function szin(nev, tartalek) {
  let ertek = "";
  try {
    if (typeof document !== "undefined" && typeof getComputedStyle === "function") {
      ertek = getComputedStyle(document.documentElement).getPropertyValue("--" + nev).trim();
    }
  } catch (e) { ertek = ""; }
  if (ertek) return ertek;
  return tartalek !== undefined ? tartalek : (SZIN_TARTALEK[nev] || "");
}

// egy token „#rrggbb" értékéből rgba(...) az adott átlátszósággal (hőtérkép, tompított változatok)
function szin_atlatszo(nev, alfa) {
  let h = szin(nev).replace("#", "");
  if (h.length === 3) h = h.split("").map(function (c) { return c + c; }).join("");
  const n = parseInt(h, 16);
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return szin(nev);
  return "rgba(" + ((n >> 16) & 255) + ", " + ((n >> 8) & 255) + ", " + (n & 255) + ", " + alfa + ")";
}

const TEMA_SORREND_GOOGLE = ["megelhetes", "egeszsegugy", "oktatas", "gazdasag", "politika"];
// a youtube.js YT_DOMEN_SORREND-jének tükre (a záró null „Egyéb" nélkül)
const TEMA_SORREND_YOUTUBE = ["egeszseg", "penzugy", "kozelet", "haztartas", "csalad", "szabadido", "tanulas", "otthon"];

// egy domén témaszíne; ismeretlen → --semleges
function tema_szin(domen, forras) {
  const lista = forras === "youtube" ? TEMA_SORREND_YOUTUBE : TEMA_SORREND_GOOGLE;
  const i = lista.indexOf(domen);
  return i >= 0 ? szin("tema-" + (i + 1)) : szin("semleges");
}

// a mért adatvonal színe: YouTube-blokkban --youtube, egyébként --google
function adat_vonal_szin(elem) {
  const yt = elem && typeof elem.closest === "function" && elem.closest("#youtube-blokk");
  return szin(yt ? "youtube" : "google");
}

// közös Chart.js-alapok (egyszer, betöltéskor)
function grafikon_alap() {
  if (typeof Chart === "undefined" || !Chart.defaults) return;
  Chart.defaults.font.family = szin("betu");
  Chart.defaults.color = szin("szoveg-2");
  Chart.defaults.borderColor = szin("graf-racs");   // Chart.js alap rácsszín
  Chart.defaults.elements.line.borderWidth = 1.5;
  Chart.defaults.plugins.tooltip.backgroundColor = szin("szoveg");
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { szin, szin_atlatszo, tema_szin, TEMA_SORREND_GOOGLE, TEMA_SORREND_YOUTUBE, grafikon_alap };
} else {
  grafikon_alap();
}
