"use strict";
// Áttekintő nyitóoldal: a „mai kiemelt" betöltése a napi elemzésből (data/elemzes.json).
// NINCS new Date(); a nap/mód az adatból jön. Fail-soft: hiány esetén a blokk üres marad.

function nyitooldal_el(tag, cls, szoveg) {
  const h = document.createElement(tag);
  if (cls) h.className = cls;
  if (szoveg != null) h.textContent = szoveg;
  return h;
}

async function nyitooldal_json(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch (e) { return null; }
}

function nyitooldal_elso_mondat(szoveg) {
  if (!szoveg) return "";
  const s = String(szoveg).trim();
  if (!s) return "";
  const m = s.match(/^[\s\S]*?[.!?](\s|$)/);
  let r = (m ? m[0] : s).trim();
  if (r.length > 240) r = r.slice(0, 240).trim() + "…";
  return r;
}

function nyitooldal_placeholder(t) {
  return !t || !String(t).trim() || String(t).indexOf("az esti futáskor") !== -1;
}

function nyitooldal_narrativa(fel, mode) {
  const sorrend = mode === "este" ? ["este", "reggel"] : ["reggel", "este"];
  for (let i = 0; i < sorrend.length; i++) {
    const k = sorrend[i];
    const t = fel && fel[k] && fel[k].szoveg;
    if (!nyitooldal_placeholder(t)) return t;
  }
  return "";
}

function nyitooldal_kiemelt_render(cel, d) {
  if (!cel) return;
  cel.innerHTML = "";
  const fel = (d && d.felkapott) || {};
  const mondat = nyitooldal_elso_mondat(nyitooldal_narrativa(fel, d && d.mode));
  const top = (fel.top || []).map(function (x) { return x && x.kifejezes; }).filter(Boolean).slice(0, 5);
  if (!mondat && !top.length) return;   // fail-soft: nincs mit mutatni
  cel.appendChild(nyitooldal_el("h2", "nyitooldal-kiemelt-cim", "Mai kiemelt"));
  if (mondat) cel.appendChild(nyitooldal_el("p", "nyitooldal-kiemelt-mondat", mondat));
  if (top.length) {
    const chipek = nyitooldal_el("div", "nyitooldal-kiemelt-chipek");
    top.forEach(function (sz) { chipek.appendChild(nyitooldal_el("span", "nyitooldal-chip", sz)); });
    cel.appendChild(chipek);
  }
  const link = nyitooldal_el("a", "nyitooldal-kiemelt-link", "Tovább a napi elemzéshez →");
  link.href = "elemzes.html";
  cel.appendChild(link);
}

async function nyitooldal_init() {
  const d = await nyitooldal_json("data/elemzes.json");
  nyitooldal_kiemelt_render(document.getElementById("nyitooldal-kiemelt"), d);
}

nyitooldal_init();
