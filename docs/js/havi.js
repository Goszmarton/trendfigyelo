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

const havi_terkepek = {};
window.havi_terkepek = havi_terkepek;

const HONAP_NEV = ["január", "február", "március", "április", "május", "június",
                   "július", "augusztus", "szeptember", "október", "november", "december"];
function honap_cimke(h) {                       // "2026-09" → "2026. szeptember"
  const [ev, ho] = (h || "").split("-");
  const i = parseInt(ho, 10) - 1;
  return (i >= 0 && i < 12) ? `${ev}. ${HONAP_NEV[i]}` : h;
}
function url_honap() {                           // ?honap=YYYY-MM (NINCS new Date())
  const m = (location.search || "").match(/[?&]honap=(\d{4}-\d{2})/);
  return m ? m[1] : null;
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

// kék-csíkos infó-jegyzet (a .mltrend-info/.predikcio-info mintájára — lásd docs/css/app.css .havi-info)
function havi_info(szoveg) {
  return elem("p", "havi-info", szoveg);
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
  box.setAttribute("data-klaszter-cimke", k.cimke || "");
  box.appendChild(elem("h3", null, k.cimke || "Névtelen téma"));
  if (k.ertelmezes) box.appendChild(elem("p", "elemzes-szoveg", k.ertelmezes));
  box.appendChild(tag_lista(k.szavak));
  if (Array.isArray(k.uralkodo_temak) && k.uralkodo_temak.length) {
    box.appendChild(elem("p", "halvany", "Domináns témák: " + k.uralkodo_temak.join(", ")));
  }
  return box;
}

// klaszter-barchart oszlopkattintás → a megfelelő téma-kártyára görgetés + rövid kiemelés
// (NINCS new Date() — a kiemelés eltávolítása setTimeout-tal történik, nem időbélyeg-alapon)
function havi_klaszter_ugras(cimke) {
  const kartya = document.querySelector(
    '#havi-tartalom .havi-klaszter[data-klaszter-cimke="' + (cimke || "").replace(/"/g, '\\"') + '"]');
  if (!kartya) return;
  kartya.scrollIntoView({ behavior: "smooth", block: "start" });
  kartya.classList.add("havi-klaszter-kiemelt");
  setTimeout(() => kartya.classList.remove("havi-klaszter-kiemelt"), 1600);
}
window.havi_klaszter_ugras = havi_klaszter_ugras;

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
// opcionális onOszlop(index): oszlopra kattintva hívjuk (pl. klaszter-kártyára ugráshoz)
function havi_barchart(kulcs, canvasId, cimkek, ertekek, onOszlop) {
  const doboz = document.createElement("div");
  doboz.className = "havi-chart-doboz";
  // a magasság a sávok számához igazodik (min 320px, ~34px/sáv) → minden címke elfér, nem lapul össze
  doboz.style.height = Math.max(320, (cimkek.length || 0) * 34) + "px";
  const canvas = document.createElement("canvas");
  canvas.id = canvasId;
  doboz.appendChild(canvas);
  if (typeof Chart !== "undefined" && cimkek.length) {
    if (havi_chartok[kulcs] && typeof havi_chartok[kulcs].destroy === "function") {
      havi_chartok[kulcs].destroy();
    }
    havi_chartok[kulcs] = new Chart(canvas, {
      type: "bar",
      data: { labels: cimkek, datasets: [{ data: ertekek, backgroundColor: "#3366cc" }] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, title: { display: true, text: "volumen" } },
                  y: { ticks: { autoSkip: false } } },   // MINDEN kategória-név látsszon (ne skip-eljen)
        onClick: (e, elemek) => { if (onOszlop && elemek && elemek.length) onOszlop(elemek[0].index); },
        onHover: (e, elemek) => {
          if (e.native && e.native.target) e.native.target.style.cursor = (onOszlop && elemek && elemek.length) ? "pointer" : "default";
        } },
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

// Világtérkép (Fázis B): a vendored geo-assetek (Task 1) betöltése + cache-elése — egyszer töltjük,
// a hónap-váltások közt újra felhasználjuk.
let _geo = null;
async function geo_assetek() {
  if (_geo) return _geo;
  try {
    const [vilag, iso, huk, varos, megyek] = await Promise.all([
      fetch("vendor/geo/vilag-orszagok.geojson").then(r => r.json()),
      fetch("vendor/geo/orszag-nev-iso.json").then(r => r.json()),
      fetch("vendor/geo/hu-telepules-koord.json").then(r => r.json()),
      fetch("vendor/geo/varos-koord.json").then(r => r.json()),
      // a megye-alapréteg IZOLÁLT hibával: ha CSAK ez hiányzik, a HU-térkép a
      // HUN-körvonalra esik vissza, a többi térkép/pont érintetlen (párhuzamos betöltés)
      fetch("vendor/geo/hu-megyek.geojson").then(r => r.json()).catch(() => null),
    ]);
    _geo = { vilag, iso, huk, varos, megyek };
    return _geo;
  } catch (e) {
    return null;   // fail-soft: a hívó erre a Fázis A volumen-listára esik vissza
  }
}
function kulcs(nev) { return (nev || "").trim().toLowerCase(); }
function szin_skala(v, max) {   // világos→sötét kék a volumen arányában
  const t = max > 0 ? Math.min(1, v / max) : 0;
  const l = Math.round(85 - 55 * t);       // 85%→30% világosság
  return `hsl(212, 70%, ${l}%)`;
}

// fail-soft: ha nincs Leaflet, a Fázis A volumen-listára esünk vissza (ner_csoport)
function _terkep_fallback(cimSzoveg, entitasok) {
  return ner_csoport(cimSzoveg, entitasok);
}

// jelmagyarázat-sor egy térkép alá (szín/méret = volumen)
function _terkep_jelmagyarazat(szoveg) {
  return elem("p", "havi-terkep-jelmagyarazat", szoveg);
}

// „nem térképezhető" fallback-lista (grounding/a11y: semmi ne tűnjön el csendben) — csak ha van tartalma
function _nem_illesztheto_lista(entitasok) {
  const lista = (entitasok || []).filter((e) => e && e.nev);
  if (!lista.length) return null;
  const box = elem("div", "havi-terkep-fallback");
  box.appendChild(elem("p", "halvany", "Nem térképezhető:"));
  const ul = document.createElement("ul");
  lista.forEach((e) => {
    ul.appendChild(elem("li", null, `${e.nev} · ${e.volumen || 0}`));
  });
  box.appendChild(ul);
  return box;
}

// Világtérkép-építő — ország-choropleth (volumen szerinti kék-skála) + külföldi-város kör-jelölők,
// hover-tooltip, kattintásra a kötött szavak a .havi-terkep-szavak dobozban jelennek meg.
async function vilag_terkep(orszagok, telepulesek) {
  const doboz = elem("div"); doboz.id = "havi-vilag-terkep"; doboz.className = "havi-terkep-doboz";
  const szavakDoboz = elem("div", "havi-terkep-szavak");
  if (typeof L === "undefined") { return _terkep_fallback("Országok", orszagok); }   // fail-soft
  const g = await geo_assetek();
  if (!g) { return _terkep_fallback("Országok", orszagok); }   // fail-soft: geo-asset betöltés bukott
  const featureIdek = new Set(g.vilag.features.map(f => f.id));
  const orszMap = {}; (orszagok || []).forEach(o => { const iso = g.iso[kulcs(o.nev)]; if (iso && featureIdek.has(iso)) orszMap[iso] = o; });
  const maxO = Math.max(1, ...(orszagok || []).map(o => o.volumen || 0));
  // nem-illeszthető: ország nincs ISO-match VAGY az ISO nincs feature-ként a GeoJSON-ban; ÉS
  // külföldi (nem HU) település, aminek se HU-, se külföldi-város koordinátája nincs
  // (a HU-koordinátás települést a hu_terkep, a külföldi-koordinátásat ez a térkép jelöli — így
  // egy név legfeljebb egy helyen szerepel: térkép VAGY pontosan egy fallback-lista).
  const orszNemIllesztheto = (orszagok || []).filter((o) => {
    const iso = g.iso[kulcs(o.nev)];
    return !iso || !featureIdek.has(iso);
  });
  const telepNemIllesztheto = (telepulesek || []).filter((t) => !g.huk[kulcs(t.nev)] && !g.varos[kulcs(t.nev)]);
  // térkép (későn, a doboz DOM-ba kerülése után inicializálva — Leaflet-nek méretezett konténer kell)
  setTimeout(() => {
    if (havi_terkepek.vilag && typeof havi_terkepek.vilag.remove === "function") {
      try { havi_terkepek.vilag.remove(); } catch (e) { /* stale/elszabadult ref — nem dől el */ }
    }
    const map = L.map(doboz, { attributionControl: true }).setView([30, 10], 1.4);
    L.geoJSON(g.vilag, {
      style: f => { const o = orszMap[f.id]; return { weight: 1, color: "#888",
        fillColor: o ? szin_skala(o.volumen || 0, maxO) : "#eee", fillOpacity: o ? 0.85 : 0.25 }; },
      onEachFeature: (f, layer) => { const o = orszMap[f.id]; if (o) {
        layer.bindTooltip(`${o.nev} · volumen: ${o.volumen || 0}`);
        layer.on("click", () => { szavakDoboz.textContent = `${o.nev}: ${(o.szavak || []).join(", ")}`; }); } },
    }).addTo(map);
    // külföldi városok (nincs HU-koordinátájuk) kör-jelölőként
    const kulf = (telepulesek || []).filter(t => !g.huk[kulcs(t.nev)] && g.varos[kulcs(t.nev)]);
    const maxV = Math.max(1, ...kulf.map(t => t.volumen || 0));
    kulf.forEach(t => { const c = g.varos[kulcs(t.nev)];
      L.circleMarker(c, { radius: 5 + 9 * ((t.volumen || 0) / maxV), color: "#c0392b", fillColor: "#e74c3c", fillOpacity: 0.8, weight: 1 })
        .bindTooltip(`${t.nev} · volumen: ${t.volumen || 0}`)
        .on("click", () => { szavakDoboz.textContent = `${t.nev}: ${(t.szavak || []).join(", ")}`; })
        .addTo(map); });
    havi_terkepek.vilag = map;
  }, 0);
  const wrap = elem("section", "elemzes-szekcio");
  wrap.appendChild(elem("h3", null, "Havonta megjelent országok és nem-magyar települések a keresésekben"));
  wrap.appendChild(doboz); wrap.appendChild(szavakDoboz);
  wrap.appendChild(_terkep_jelmagyarazat("Sötétebb szín / nagyobb pont = nagyobb volumen."));
  const fallback = _nem_illesztheto_lista(orszNemIllesztheto.concat(telepNemIllesztheto));
  if (fallback) wrap.appendChild(fallback);
  return wrap;
}

// Magyarország-térkép — magyar települések kör-jelölőkkel (volumen szerinti méret), hover-tooltip,
// kattintásra a kötött szavak a .havi-terkep-szavak dobozban jelennek meg (a vilag_terkep mintájára).
async function hu_terkep(telepulesek) {
  const doboz = elem("div"); doboz.id = "havi-hu-terkep"; doboz.className = "havi-terkep-doboz";
  const szavakDoboz = elem("div", "havi-terkep-szavak");
  if (typeof L === "undefined") { return _terkep_fallback("Települések", telepulesek); }   // fail-soft
  const g = await geo_assetek();
  if (!g) { return _terkep_fallback("Települések", telepulesek); }   // fail-soft: geo-asset betöltés bukott
  const hazai = (telepulesek || []).filter(t => g.huk[kulcs(t.nev)]);
  const maxV = Math.max(1, ...hazai.map(t => t.volumen || 0));
  // térkép (későn, a doboz DOM-ba kerülése után inicializálva — Leaflet-nek méretezett konténer kell)
  setTimeout(() => {
    if (havi_terkepek.hu && typeof havi_terkepek.hu.remove === "function") {
      try { havi_terkepek.hu.remove(); } catch (e) { /* stale/elszabadult ref — nem dől el */ }
    }
    const map = L.map(doboz, { attributionControl: true }).setView([47.16, 19.5], 6.6);
    // Alapréteg: a vendorelt megyehatár-GeoJSON (Task 1 csiszolás) → a pontok ne üres/körvonal-nélküli
    // háttéren lebegjenek, hanem a megyék tagolása is látszódjon; a nézetet a rétegre illesztjük.
    // Fallback (megye-asset hiányzik): a már vendorelt világ-GeoJSON HUN feature-je (a korábbi viselkedés).
    if (g.megyek && (g.megyek.features || []).length) {
      const alap = L.geoJSON(g.megyek, { interactive: false, style: { color: "#999", weight: 1, fillColor: "#f2f2f2", fillOpacity: 0.9 } }).addTo(map);
      try { map.fitBounds(alap.getBounds(), { padding: [12, 12] }); } catch (e) { /* üres bounds — marad a setView */ }
    } else {
      const hun = (g.vilag.features || []).find((f) => f.id === "HUN");
      if (hun) {
        const alap = L.geoJSON(hun, { interactive: false, style: { color: "#888", weight: 1, fillColor: "#f2f2f2", fillOpacity: 0.9 } }).addTo(map);
        try { map.fitBounds(alap.getBounds(), { padding: [12, 12] }); } catch (e) { /* üres bounds — marad a setView */ }
      }
    }
    hazai.forEach(t => { const c = g.huk[kulcs(t.nev)];
      L.circleMarker(c, { radius: 5 + 9 * ((t.volumen || 0) / maxV), color: "#c0392b", fillColor: "#e74c3c", fillOpacity: 0.8, weight: 1 })
        .bindTooltip(`${t.nev} · volumen: ${t.volumen || 0}`)
        .on("click", () => { szavakDoboz.textContent = `${t.nev}: ${(t.szavak || []).join(", ")}`; })
        .addTo(map); });
    havi_terkepek.hu = map;
  }, 0);
  // nem-illeszthető (HU-térkép szempontjából): a HU-koordináta nélküli település vagy külföldi
  // (van g.varos-koordinátája → már a világtérképen szerepel — NEM ismételjük itt), vagy teljesen
  // koordináta nélküli (se HU, se külföldi) → azt a világtérkép fallback-listája már felsorolja
  // (lásd vilag_terkep telepNemIllesztheto) — így ide NEM kerül duplán, a HU fallback ezért
  // ebben az adatmodellben jellemzően üres marad (nincs kettős felsorolás).
  const wrap = elem("section", "elemzes-szekcio");
  wrap.appendChild(elem("h3", null, "Havonta megjelent magyar települések a keresésekben"));
  wrap.appendChild(doboz); wrap.appendChild(szavakDoboz);
  wrap.appendChild(_terkep_jelmagyarazat("Nagyobb pont = nagyobb volumen."));
  return wrap;
}

async function rajzol(art) {
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
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Országok és települések a havi keresésekben"));
  t.appendChild(havi_info(
    "A térképeken a havi keresőszavakban felismert ország- és településnevek jelennek meg, " +
    "gyakoriság (volumen) szerint színezve/méretezve — minél sötétebb/nagyobb a jelölés, annál " +
    "nagyobb volumen tartozik hozzá. Egy jelölésre kattintva a hozzá kötött keresőszavak jelennek " +
    "meg. A térképre nem illeszthető nevek a lista alatt szerepelnek."));
  const ner = art.ner || {};
  t.appendChild(await vilag_terkep(ner.orszagok, ner.telepulesek));
  t.appendChild(await hu_terkep(ner.telepulesek));

  const szemSzek = document.createElement("section");
  szemSzek.className = "elemzes-szekcio havi-szemely-szekcio";
  szemSzek.appendChild(elem("h3", null, "Megjelent személynevek a havi keresésekben"));
  szemSzek.appendChild(havi_info(
    "A sáv hossza a volument mutatja: a személyhez kötött keresőszavak legmagasabb kereső-" +
    "szintjeinek összegét. Minél hosszabb egy sáv, annál nagyobb figyelmet kapott az adott " +
    "személy a hónap kereséseiben."));
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
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Tematikus besorolás"));
  t.appendChild(havi_info(
    "Egy téma volumene a hozzá tartozó keresőszavak volumenének összege — ez adja a barchart " +
    "oszlopainak magasságát is."));
  const klaszterek = (art.klaszterek || []).filter((k) => Array.isArray(k.szavak) && k.szavak.length);
  if (!klaszterek.length) {
    t.appendChild(elem("p", "ures", "Nincs megjeleníthető téma ebben a hónapban."));
  } else {
    const kSorolt = klaszterek.slice().sort((a, b) => (b.volumen || 0) - (a.volumen || 0));
    t.appendChild(havi_barchart("klaszter", "havi-klaszter-chart",
      kSorolt.map((k) => k.cimke || "Névtelen"), kSorolt.map((k) => k.volumen || 0),
      (i) => havi_klaszter_ugras(kSorolt[i].cimke)));
    klaszterek.forEach((k) => t.appendChild(klaszter_kartya(k)));
  }
}

async function havi_indit() {
  let idx = { honapok: [], legutolso: null };
  try {
    const r = await fetch("data/havi_nlp/index.json");
    if (r.ok) idx = await r.json();
  } catch (e) { /* nincs index — HAVI_ALAPHONAP-ra esünk */ }
  const honapok = (idx.honapok && idx.honapok.length) ? idx.honapok.slice() : [HAVI_ALAPHONAP];
  const kert = url_honap();
  const kezdo = (kert && honapok.indexOf(kert) >= 0) ? kert
    : (idx.legutolso && honapok.indexOf(idx.legutolso) >= 0 ? idx.legutolso : honapok[honapok.length - 1]);
  honap_panel_epit(honapok, kezdo);
  await honap_valt(kezdo);
}
function honap_panel_epit(honapok, aktiv) {
  const panel = document.getElementById("havi-honap-panel");
  panel.textContent = "";
  panel.appendChild(elem("h2", "halvany", "Hónap"));
  honapok.slice().sort().reverse().forEach((h) => {
    const g = document.createElement("button");
    g.type = "button"; g.className = "havi-honap-gomb";
    g.setAttribute("data-honap", h);
    g.setAttribute("aria-pressed", h === aktiv ? "true" : "false");
    g.textContent = honap_cimke(h);
    g.addEventListener("click", () => {
      panel.querySelectorAll(".havi-honap-gomb").forEach((b) =>
        b.setAttribute("aria-pressed", b.getAttribute("data-honap") === h ? "true" : "false"));
      honap_valt(h);
    });
    panel.appendChild(g);
  });
}
async function honap_valt(honap) {
  try { await rajzol(await havi_betolt(honap)); }
  catch (e) {
    document.getElementById("havi-fejlec").textContent = "Havi elemzés – nem érhető el";
    document.getElementById("havi-tartalom").textContent =
      "A havi elemzés jelenleg nem érhető el (még nem készült el ehhez a hónaphoz).";
  }
}

document.addEventListener("DOMContentLoaded", havi_indit);
