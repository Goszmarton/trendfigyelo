"use strict";
// „Heti értékelés" fül — a heti AI-riport (docs/data/heti/<het>.json) renderelése 6 részben:
// vezetői összefoglaló, figyelem átrendeződése (+ determinista divergáló sávdiagram), ügyek életútja,
// 2–3 mélyebb téma, Google–YouTube összefüggés, jövő heti figyelendők. A szöveges részek AI-generáltak
// és a korpuszra grounding-validáltak (lásd trendfigyelo/heti_ertekeles.py); a diagram a VALÓS
// számokból (eltérés a szokásos szinttől) determinista. NINCS new Date() — a hét az index.json-ból.

const HETI_SZIN_EROS = "#2a78d6";    // erősödő (pozitív eltérés) — az IDOSOR_PALETTA validált kékje
const HETI_SZIN_GYENGE = "#eb6834";  // gyengülő (negatív eltérés) — az IDOSOR_PALETTA validált narancsa
const heti_chartok = {};
window.heti_chartok = heti_chartok;

function helem(tag, cls, szoveg) {
  const h = document.createElement(tag);
  if (cls) h.className = cls;
  if (szoveg != null) h.textContent = szoveg;
  return h;
}

function url_het() {
  const m = (location.search || "").match(/[?&]het=(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : null;
}

function heti_cimke(h) {   // "2026-09-28" → "2026-09-28 – (hét)"; az ISO-hetet a fejléc adja
  return h;
}

async function heti_betolt(het) {
  const r = await fetch(`data/heti/${het}.json`);
  if (!r.ok) throw new Error("nem elérhető: " + het);
  return r.json();
}

// egy szekció: cím + opcionális bevezető + tetszőleges tartalom-elem
function heti_szekcio(cim) {
  const s = helem("section", "elemzes-szekcio heti-szekcio");
  s.appendChild(helem("h2", "elemzes-csoport-cim", cim));
  return s;
}

function lista_ul(elemek, cls) {
  const ul = helem("ul", cls || null);
  (elemek || []).filter((x) => x != null && String(x).trim()).forEach((x) =>
    ul.appendChild(helem("li", null, String(x))));
  return ul;
}

// divergáló sávdiagram: erősödő (pozitív) kék, gyengülő (negatív) narancs; legenda + a11y-adatlista
function heti_figyelem_chart(figyelem) {
  const doboz = helem("div", "heti-figyelem-chart-doboz");
  const sorok = (figyelem || []).filter((x) => x && typeof x.elteres === "number");
  if (!sorok.length) { doboz.appendChild(helem("p", "ures", "Nincs megjeleníthető eltérés-adat.")); return doboz; }
  // legenda (az identitás sosem csak szín: címkézett)
  const leg = helem("div", "heti-figyelem-legenda");
  const l1 = helem("span", "heti-leg-elem"); l1.appendChild(_szin_pont(HETI_SZIN_EROS));
  l1.appendChild(document.createTextNode(" erősödő (a szokásos fölött)")); leg.appendChild(l1);
  const l2 = helem("span", "heti-leg-elem"); l2.appendChild(_szin_pont(HETI_SZIN_GYENGE));
  l2.appendChild(document.createTextNode(" gyengülő (a szokásos alatt)")); leg.appendChild(l2);
  doboz.appendChild(leg);
  const chartDoboz = helem("div", "heti-chart-vaszon");
  chartDoboz.style.height = Math.max(240, sorok.length * 30) + "px";
  const canvas = helem("canvas"); canvas.id = "heti-figyelem-chart"; chartDoboz.appendChild(canvas);
  doboz.appendChild(chartDoboz);
  if (typeof Chart !== "undefined") {
    if (heti_chartok.figyelem && typeof heti_chartok.figyelem.destroy === "function") heti_chartok.figyelem.destroy();
    heti_chartok.figyelem = new Chart(canvas, {
      type: "bar",
      data: { labels: sorok.map((x) => x.szo),
              datasets: [{ data: sorok.map((x) => x.elteres),
                           backgroundColor: sorok.map((x) => x.elteres >= 0 ? HETI_SZIN_EROS : HETI_SZIN_GYENGE) }] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false } },
        scales: { x: { title: { display: true, text: "eltérés a szokásos szinttől" } },
                  y: { ticks: { autoSkip: false } } } },
    });
  }
  // a11y-adatlista (a canvas tartalma nem olvasható ki)
  const lista = helem("ul", "heti-chart-adatlista");
  sorok.forEach((x) => lista.appendChild(helem("li", null,
    `${x.szo} – ${x.elteres > 0 ? "+" : ""}${Math.round(x.elteres * 10) / 10}`)));
  doboz.appendChild(lista);
  return doboz;
}
function _szin_pont(szin) { const s = helem("span", "heti-leg-pont"); s.style.backgroundColor = szin; return s; }

function heti_tema_kartya(t) {
  const box = helem("section", "elemzes-szekcio heti-tema");
  box.appendChild(helem("h3", null, t.tema || "Téma"));
  const sor = (cimke, ertek) => { if (ertek && String(ertek).trim()) {
    const p = helem("p", "elemzes-szoveg");
    p.appendChild(helem("strong", null, cimke + " "));
    p.appendChild(document.createTextNode(String(ertek)));
    box.appendChild(p); } };
  sor("Keresési pálya:", t.keresesi_palya);
  sor("Kapcsolódó kifejezések:", t.kapcsolodo_kifejezesek);
  sor("Ellenőrzött események:", t.ellenorzott_esemenyek);
  sor("Magyarázat:", t.magyarazat);
  return box;
}

function rajzol_heti(art) {
  const t = document.getElementById("heti-tartalom");
  t.textContent = "";
  document.getElementById("heti-fejlec").textContent =
    `Heti értékelés – ${art.het_kezdet} … ${art.het_veg} (${art.iso_het || ""})`;
  t.appendChild(helem("p", "halvany",
    `Gépi elemzés — a(z) ${art.modell || "AI"} modell automatikusan generálta az előző hét kereséseiből.`));

  // 1) Vezetői összefoglaló
  const s1 = heti_szekcio("Vezetői összefoglaló");
  s1.appendChild(lista_ul(art.vezetoi_osszefoglalo, "heti-lista"));
  t.appendChild(s1);

  // 2) A figyelem átrendeződése + diagram
  const s2 = heti_szekcio("A figyelem átrendeződése");
  const fa = art.figyelem_atrendezodes || {};
  if ((fa.erosodo || []).length) { s2.appendChild(helem("h3", null, "Erősödő témák")); s2.appendChild(lista_ul(fa.erosodo)); }
  if ((fa.gyengulo || []).length) { s2.appendChild(helem("h3", null, "Gyengülő témák")); s2.appendChild(lista_ul(fa.gyengulo)); }
  s2.appendChild(heti_figyelem_chart(art.figyelem));
  t.appendChild(s2);

  // 3) Ügyek életútja
  const s3 = heti_szekcio("Az ügyek életútja");
  const ue = art.ugyek_eletutja || {};
  const ujsor = (cimke, ertek) => { if (ertek && String(ertek).trim()) {
    const p = helem("p", "elemzes-szoveg");
    p.appendChild(helem("strong", null, cimke + " "));
    p.appendChild(document.createTextNode(String(ertek)));
    s3.appendChild(p); } };
  ujsor("Rövid kiugrás:", ue.rovid_kiugras);
  ujsor("Hosszabb kiugrás:", ue.hosszabb_kiugras);
  ujsor("Visszatérő:", ue.visszatero);
  t.appendChild(s3);

  // 4) Mélyebb témák
  const s4 = heti_szekcio("Mélyebb témaelemzés");
  const temak = (art.melyebb_temak || []).filter((x) => x && x.tema);
  if (!temak.length) s4.appendChild(helem("p", "ures", "Ezen a héten nincs kiemelt mélyebb téma."));
  else temak.forEach((x) => s4.appendChild(heti_tema_kartya(x)));
  t.appendChild(s4);

  // 5) Google–YouTube összefüggés
  const s5 = heti_szekcio("Google–YouTube összefüggés");
  s5.appendChild(helem("p", "elemzes-szoveg", art.google_youtube_osszefugges || ""));
  t.appendChild(s5);

  // 6) Jövő heti figyelendők
  const s6 = heti_szekcio("Mit érdemes figyelni a jövő héten");
  s6.appendChild(lista_ul(art.jovo_heti_figyelendok, "heti-lista"));
  t.appendChild(s6);
}

function heti_panel_epit(hetek, aktiv) {
  const panel = document.getElementById("heti-het-panel");
  panel.textContent = "";
  panel.appendChild(helem("h2", "halvany", "Hét"));
  hetek.slice().sort().reverse().forEach((h) => {
    const g = document.createElement("button");
    g.type = "button"; g.className = "heti-het-gomb";
    g.setAttribute("data-het", h);
    g.setAttribute("aria-pressed", h === aktiv ? "true" : "false");
    g.textContent = heti_cimke(h);
    g.addEventListener("click", () => {
      panel.querySelectorAll(".heti-het-gomb").forEach((b) =>
        b.setAttribute("aria-pressed", b.getAttribute("data-het") === h ? "true" : "false"));
      heti_valt(h);
    });
    panel.appendChild(g);
  });
}

async function heti_valt(het) {
  try { rajzol_heti(await heti_betolt(het)); }
  catch (e) {
    document.getElementById("heti-fejlec").textContent = "Heti értékelés – nem érhető el";
    document.getElementById("heti-tartalom").textContent =
      "A heti értékelés jelenleg nem érhető el (még nem készült el ehhez a héthez).";
  }
}

async function heti_indit() {
  let idx = { hetek: [], legutolso: null };
  try {
    const r = await fetch("data/heti/index.json");
    if (r.ok) idx = await r.json();
  } catch (e) { /* nincs index */ }
  const hetek = (idx.hetek && idx.hetek.length) ? idx.hetek.slice() : [];
  if (!hetek.length) { await heti_valt("_nincs_"); return; }   // fail-soft: üres → „nem érhető el"
  const kert = url_het();
  const kezdo = (kert && hetek.indexOf(kert) >= 0) ? kert
    : (idx.legutolso && hetek.indexOf(idx.legutolso) >= 0 ? idx.legutolso : hetek[hetek.length - 1]);
  heti_panel_epit(hetek, kezdo);
  await heti_valt(kezdo);
}

document.addEventListener("DOMContentLoaded", heti_indit);
