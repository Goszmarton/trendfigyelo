"use strict";
// „Havi elemzés" fül — a havi NLP-alapú korpusz-elemzés (docs/data/havi_nlp/<honap>.json)
// renderelése: összegzés (felül), NER (ország/település/személy, volumen szerint rendezve),
// klaszterek (jelentés-alapú témák, alul). TELJES EGÉSZÉBEN gépi (AI) elemzés — Claude-modellel
// generálva és a korpuszra grounding-validálva (lásd trendfigyelo/havi_nlp.py) — ezért a fülön
// mindenhol egyértelmű „gépi elemzés" jelölés szerepel. NINCS new Date() — a hónap-választás
// az (opcionális) data/havi_nlp/index.json-ból VAGY egy fix aktuális hónapból (1. fázis).

const HAVI_ALAPHONAP = "2026-09"; // 1. fázis: fix jelenlegi hónap — index.json hiányában esünk erre vissza
const SZEMELY_TOP = 18;
const havi_chartok = {};
window.havi_chartok = havi_chartok;

async function havi_honap_dontes() {
  try {
    const r = await fetch("data/havi_nlp/index.json");
    if (r.ok) {
      const idx = await r.json();
      if (idx && typeof idx.legutolso === "string" && idx.legutolso) return idx.legutolso;
      if (idx && Array.isArray(idx.honapok) && idx.honapok.length) return idx.honapok.slice().sort().pop();
    }
  } catch (e) { /* nincs index.json — fix hónapra esünk vissza */ }
  return HAVI_ALAPHONAP;
}

async function havi_betolt(honap) {
  const r = await fetch(`data/havi_nlp/${honap}.json`);
  if (!r.ok) throw new Error("nem elérhető: " + honap);
  return r.json();
}

function elem(tag, cls, szoveg) {
  const h = document.createElement(tag);
  if (cls) h.className = cls;
  if (szoveg != null) h.textContent = szoveg;
  return h;
}

// tag-lista (szavak) — inline chipek
function tag_lista(szavak) {
  const ul = document.createElement("ul");
  ul.className = "havi-tag-lista";
  (szavak || []).forEach((sz) => {
    const li = elem("li", "havi-tag", sz);
    ul.appendChild(li);
  });
  return ul;
}

// egy klaszter-kártya (a hívó már kiszűrte az üres szó-listájúakat — grounding-perem)
function klaszter_kartya(k) {
  const box = document.createElement("section");
  box.className = "elemzes-szekcio havi-klaszter";
  box.appendChild(elem("h3", null, k.cimke || "Névtelen téma"));
  box.appendChild(tag_lista(k.szavak));
  if (k.ertelmezes) box.appendChild(elem("p", "elemzes-szoveg", k.ertelmezes));
  if (Array.isArray(k.uralkodo_temak) && k.uralkodo_temak.length) {
    box.appendChild(elem("p", "halvany", "Domináns témák: " + k.uralkodo_temak.join(", ")));
  }
  return box;
}

// egy NER-csoport (Országok / Települések / Személyek) — entitásonként a nevet kiváltó szavakkal
function ner_csoport(cimSzoveg, entitasok) {
  const box = document.createElement("section");
  box.className = "elemzes-szekcio havi-ner-csoport";
  box.appendChild(elem("h3", null, cimSzoveg));
  const lista = (entitasok || []).filter((e) => e && e.nev)
    .sort((a, b) => (b.volumen || 0) - (a.volumen || 0));
  if (!lista.length) {
    box.appendChild(elem("p", "ures", "Nincs felismert entitás ebben a csoportban."));
    return box;
  }
  const ul = document.createElement("ul");
  lista.forEach((e) => {
    const li = document.createElement("li");
    const nev = document.createElement("strong");
    nev.textContent = e.nev;
    li.appendChild(nev);
    li.appendChild(document.createTextNode("  ·  " + (e.volumen || 0)));
    if (Array.isArray(e.szavak) && e.szavak.length) {
      li.appendChild(document.createTextNode(" — " + e.szavak.join(", ")));
    }
    ul.appendChild(li);
  });
  box.appendChild(ul);
  return box;
}

// vízszintes barchart egy szekcióba (cimkek + ertekek), a Chart-példányt kulcson eltárolva
function havi_barchart(kulcs, canvasId, cimkek, ertekek) {
  const doboz = document.createElement("div");
  doboz.className = "havi-chart-doboz";
  const canvas = document.createElement("canvas");
  canvas.id = canvasId;
  doboz.appendChild(canvas);
  if (typeof Chart !== "undefined" && cimkek.length) {
    havi_chartok[kulcs] = new Chart(canvas, {
      type: "bar",
      data: { labels: cimkek, datasets: [{ data: ertekek, backgroundColor: "#3366cc" }] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, title: { display: true, text: "volumen" } } } },
    });
  }
  // képernyőolvasó-alternatíva: a canvas fallback-tartalma nem jelenik meg (és nem olvasható ki),
  // ezért a cimke+érték párokat egy vizuálisan elrejtett listában is felsoroljuk (a szavak NÉLKÜL).
  if (cimkek.length) {
    const lista = document.createElement("ul");
    lista.className = "havi-chart-adatlista";
    cimkek.forEach((c, i) => {
      const li = elem("li", null, `${c} – ${ertekek[i] != null ? ertekek[i] : 0}`);
      lista.appendChild(li);
    });
    doboz.appendChild(lista);
  }
  return doboz;
}

function rajzol(art) {
  const t = document.getElementById("havi-tartalom");
  t.textContent = "";
  const korpusz = art.korpusz || {};
  document.getElementById("havi-fejlec").textContent =
    `Havi elemzés – ${art.honap} (${korpusz.egyedi_szo != null ? korpusz.egyedi_szo : "?"} egyedi szó, ` +
    `${korpusz.napok != null ? korpusz.napok : "?"} nap)`;

  t.appendChild(elem("p", "halvany",
    `Gépi elemzés — a(z) ${art.modell || "AI"} modell automatikusan generálta a hónap felkapott keresései alapján.`));

  // 1) Összegzés — LEGFELÜL
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Összegzés"));
  t.appendChild(elem("p", "elemzes-szoveg", art.osszegzes || ""));

  // 2) NER — Országok / Települések (volumen-listák; Fázis B → térképek), majd Személyek
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Felismert entitások (NER)"));
  const ner = art.ner || {};
  t.appendChild(ner_csoport("Országok", ner.orszagok));
  t.appendChild(ner_csoport("Települések", ner.telepulesek));

  const szemSzek = document.createElement("section");
  szemSzek.className = "elemzes-szekcio havi-szemely-szekcio";
  szemSzek.appendChild(elem("h3", null, "Személyek (leggyakoribbak)"));
  const szemelyek = (ner.szemelyek || []).filter((e) => e && e.nev)
    .sort((a, b) => (b.volumen || 0) - (a.volumen || 0)).slice(0, SZEMELY_TOP);
  if (!szemelyek.length) {
    szemSzek.appendChild(elem("p", "ures", "Nincs felismert személy ebben a hónapban."));
  } else {
    szemSzek.appendChild(havi_barchart("szemely", "havi-szemely-chart",
      szemelyek.map((e) => e.nev), szemelyek.map((e) => e.volumen || 0)));
  }
  t.appendChild(szemSzek);

  // 3) Klaszterek — LEGALUL (a grounding-perem szerint az üres szó-listájú klaszter NEM jelenik meg)
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Témák (klaszterek)"));
  const klaszterek = (art.klaszterek || []).filter((k) => Array.isArray(k.szavak) && k.szavak.length);
  if (!klaszterek.length) {
    t.appendChild(elem("p", "ures", "Nincs megjeleníthető téma ebben a hónapban."));
  } else {
    const kSorolt = klaszterek.slice().sort((a, b) => (b.volumen || 0) - (a.volumen || 0));
    t.appendChild(havi_barchart("klaszter", "havi-klaszter-chart",
      kSorolt.map((k) => k.cimke || "Névtelen"), kSorolt.map((k) => k.volumen || 0)));
    klaszterek.forEach((k) => t.appendChild(klaszter_kartya(k)));
  }
}

async function havi_indit() {
  try {
    const honap = await havi_honap_dontes();
    rajzol(await havi_betolt(honap));
  } catch (e) {
    document.getElementById("havi-fejlec").textContent = "Havi elemzés – nem érhető el";
    document.getElementById("havi-tartalom").textContent =
      "A havi elemzés jelenleg nem érhető el (még nem készült el ehhez a hónaphoz).";
  }
}

document.addEventListener("DOMContentLoaded", havi_indit);
