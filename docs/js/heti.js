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

let heti_hetek = [];              // a rendelkezésre álló hetek (mindegyik a hét HÉTFŐJE, ISO)
let heti_naptar_kotve = false;

// Egy nap ISO-jából a HETE HÉTFŐJE (ISO). Tiszta aritmetika, NINCS new Date(): a naptar_hetnap_hetfo0
// (app.js, Sakamoto, 0=hétfő) adja a hét-napot, majd visszalépünk a hónaphatáron át a naptar_honap_napjai-val.
function het_hetfo(iso) {
  let [y, mo, d] = iso.split("-").map(Number);
  d -= naptar_hetnap_hetfo0(y, mo, d);                 // a hét hétfőjére
  while (d < 1) { mo--; if (mo < 1) { mo = 12; y--; } d += naptar_honap_napjai(y, mo); }
  return y + "-" + String(mo).padStart(2, "0") + "-" + String(d).padStart(2, "0");
}

// Hónap-naptár a HETEK választásához (a napi elemzés archívum-naptárának mintája, a megosztott
// naptar_epit-tel): a hét MINDEN napja egy adat-hét része; bármely napra kattintva a hét hétfőjét
// töltjük be. Az adat-hetek halványan kiemelve, a kiválasztott hét erősen.
function heti_naptar_render() {
  const el = document.getElementById("heti-het-panel");
  if (!el || !heti_hetek.length) return;
  const keszlet = new Set(heti_hetek);
  const elso_ho = heti_hetek[0].slice(0, 7);
  const utolso_ho = heti_hetek[heti_hetek.length - 1].slice(0, 7);
  let valasztott = el.getAttribute("data-valasztott-het");
  if (!valasztott || !keszlet.has(valasztott)) valasztott = heti_hetek[heti_hetek.length - 1];
  let honap = el.getAttribute("data-honap") || valasztott.slice(0, 7);
  if (honap < elso_ho) honap = elso_ho;
  if (honap > utolso_ho) honap = utolso_ho;
  el.setAttribute("data-valasztott-het", valasztott);
  el.setAttribute("data-honap", honap);
  el.textContent = "";
  el.appendChild(helem("h2", "halvany", "Hét — kattints egy hétre"));
  el.appendChild(naptar_epit(honap, elso_ho, utolso_ho, function (iso) {
    const hetfo = het_hetfo(iso);
    const vanAdat = keszlet.has(hetfo);                // a hét bármely napja választható, ha a hétnek van adata
    return {
      valaszthato: vanAdat,
      extraOsztaly: (vanAdat ? "heti-adat-het" : "") + (hetfo === valasztott ? " valasztott" : ""),
      aria: hetfo === valasztott ? "date" : null,
    };
  }));
}

function heti_naptar_kot() {
  if (heti_naptar_kotve) return;
  const el = document.getElementById("heti-het-panel");
  if (!el) return;
  el.addEventListener("click", function (ev) {
    const btn = ev.target && ev.target.closest ? ev.target.closest("button") : null;
    if (!btn || btn.disabled) return;
    if (btn.classList.contains("nap-cella")) {          // egy nap → a HETE betöltése
      const hetfo = het_hetfo(btn.getAttribute("data-nap"));
      el.setAttribute("data-valasztott-het", hetfo);
      heti_naptar_render();
      heti_valt(hetfo);
    } else if (btn.classList.contains("honap-lep")) {   // hónap-lépés (a kiválasztott hét VÁLTOZATLAN)
      const cur = el.getAttribute("data-honap") || "";
      el.setAttribute("data-honap", naptar_honap_lep(cur, btn.classList.contains("elore") ? 1 : -1));
      heti_naptar_render();
    }
  });
  heti_naptar_kotve = true;
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
  heti_hetek = (idx.hetek && idx.hetek.length) ? idx.hetek.slice().sort() : [];
  if (!heti_hetek.length) { await heti_valt("_nincs_"); return; }   // fail-soft: üres → „nem érhető el", nincs naptár
  const kert = url_het();
  const kezdo = (kert && heti_hetek.indexOf(kert) >= 0) ? kert
    : (idx.legutolso && heti_hetek.indexOf(idx.legutolso) >= 0 ? idx.legutolso : heti_hetek[heti_hetek.length - 1]);
  const panel = document.getElementById("heti-het-panel");
  if (panel) panel.setAttribute("data-valasztott-het", kezdo);
  heti_naptar_render();
  heti_naptar_kot();
  await heti_valt(kezdo);
}

document.addEventListener("DOMContentLoaded", heti_indit);
