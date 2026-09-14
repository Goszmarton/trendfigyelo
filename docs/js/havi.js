"use strict";
// „Havi elemzés" fül — a havi NLP-alapú korpusz-elemzés (docs/data/havi_nlp/<honap>.json)
// renderelése: klaszterek (jelentés-alapú témák), NER (ország/település/személy), szó→lemma
// térkép (auditálhatóság) és összegzés. TELJES EGÉSZÉBEN gépi (AI) elemzés — Claude-modellel
// generálva és a korpuszra grounding-validálva (lásd trendfigyelo/havi_nlp.py) — ezért a fülön
// mindenhol egyértelmű „gépi elemzés" jelölés szerepel. NINCS new Date() — a hónap-választás
// az (opcionális) data/havi_nlp/index.json-ból VAGY egy fix aktuális hónapból (1. fázis).

const HAVI_ALAPHONAP = "2026-09"; // 1. fázis: fix jelenlegi hónap — index.json hiányában esünk erre vissza

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
  const lista = (entitasok || []).filter((e) => e && e.nev);
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
    if (Array.isArray(e.szavak) && e.szavak.length) {
      li.appendChild(document.createTextNode(" — " + e.szavak.join(", ")));
    }
    ul.appendChild(li);
  });
  box.appendChild(ul);
  return box;
}

// szó → lemma térkép — auditálhatóság: mit egyszerűsített a modell mire
function lemma_terkep(lemmak) {
  const box = document.createElement("section");
  box.className = "elemzes-szekcio havi-lemma";
  box.appendChild(elem("h3", null, "Szó → lemma térkép"));
  if (!Array.isArray(lemmak) || !lemmak.length) {
    box.appendChild(elem("p", "ures", "Nincs lemma-adat."));
    return box;
  }
  const table = document.createElement("table");
  table.className = "havi-lemma-tablazat";
  const thead = document.createElement("thead");
  thead.innerHTML = "<tr><th>Szó</th><th>Lemma</th></tr>";
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  lemmak.forEach((l) => {
    const tr = document.createElement("tr");
    const td1 = elem("td", null, l.szo || "");
    const td2 = elem("td", null, l.lemma || "");
    tr.appendChild(td1);
    tr.appendChild(td2);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  box.appendChild(table);
  return box;
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

  // Klaszterek — a grounding-perem szerint az üres szó-listájú klaszter NEM jelenik meg (ledger-döntés)
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Témák (klaszterek)"));
  const klaszterek = (art.klaszterek || []).filter((k) => Array.isArray(k.szavak) && k.szavak.length);
  if (!klaszterek.length) {
    t.appendChild(elem("p", "ures", "Nincs megjeleníthető téma ebben a hónapban."));
  } else {
    klaszterek.forEach((k) => t.appendChild(klaszter_kartya(k)));
  }

  // NER — 3 csoport
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Felismert entitások (NER)"));
  const ner = art.ner || {};
  t.appendChild(ner_csoport("Országok", ner.orszagok));
  t.appendChild(ner_csoport("Települések", ner.telepulesek));
  t.appendChild(ner_csoport("Személyek", ner.szemelyek));

  // Szó → lemma térkép
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Szó → lemma térkép (auditálhatóság)"));
  t.appendChild(lemma_terkep(art.lemmak));

  // Összegzés
  t.appendChild(elem("h2", "elemzes-csoport-cim", "Összegzés"));
  t.appendChild(elem("p", "elemzes-szoveg", art.osszegzes || ""));
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
