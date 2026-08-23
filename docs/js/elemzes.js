"use strict";
// „Elemzés" fül — a napi AI-elemzés (docs/data/elemzes.json) renderelése + archívum-nap-választó.
// A VALÓS (tényszerű, a diff/kulcsszó-adatokból számolt) réteg csempékként + diff-összegzésként
// jelenik meg (.elemzes-megfigyeles); az AI narratíva folyó prózaként, <p class="elemzes-szoveg">
// bekezdésekben — nincs külön ELMÉLETI/feltételezés-réteg.

async function elemzes_betolt(datum) {
  const url = datum ? `data/elemzesek/${datum}.json` : "data/elemzes.json";
  const r = await fetch(url);
  if (!r.ok) throw new Error("nem elérhető: " + url);
  return r.json();
}

// egy „szekció" (folyó próza, \n\n-nal elválasztott bekezdésekkel) dobozzá építése
function szekcio_elem(cim, szekcio) {
  const box = document.createElement("section");
  box.className = "elemzes-szekcio";
  const h = document.createElement("h3");
  h.textContent = cim;
  box.appendChild(h);
  const szoveg = (szekcio && szekcio.szoveg) || "";
  szoveg.split(/\n\s*\n/).map((s) => s.trim()).filter(Boolean).forEach((bek) => {
    const p = document.createElement("p");
    p.className = "elemzes-szoveg";
    p.textContent = bek;
    box.appendChild(p);
  });
  return box;
}

// VALÓS kulcsszó-csempék (irány + mai érték + csúcs — közvetlenül a mérőszámokból, nem AI-szöveg)
function valos_kulcsszo_csempek(szamok) {
  const wrap = document.createElement("div");
  wrap.className = "elemzes-csempek";
  (szamok || []).forEach((s) => {
    const c = document.createElement("div");
    c.className = "elemzes-csempe irany-" + (s.irany || "ismeretlen");
    c.textContent = `${s.szo}: ${s.irany} (mai ${s.mai_ertek ?? "–"}, csúcs ${s.csucs ?? "–"})`;
    wrap.appendChild(c);
  });
  return wrap;
}

// VALÓS felkapott-top csempék (kifejezés + volumen — a Google Trends listából, nem AI-szöveg).
// KÜLÖN osztály (nem .elemzes-csempe), hogy a kulcsszó-mérőszám-csempéktől megkülönböztethető
// maradjon (más adatforrás: a napi felkapott-lista, nem a 13 figyelt kulcsszó).
function valos_felkapott_csempek(top) {
  const wrap = document.createElement("div");
  wrap.className = "elemzes-csempek";
  (top || []).forEach((f) => {
    const c = document.createElement("div");
    c.className = "elemzes-felkapott-csempe";
    c.textContent = `${f.kifejezes} (volumen: ${f.volumen ?? "–"})`;
    wrap.appendChild(c);
  });
  return wrap;
}

// VALÓS heti felkapott-visszatérés csempék (het_valos.visszateroek — Pythonból számolt
// „hány külön napon szerepelt" lista, NEM az AI het-narratívája). Ugyanaz a tile-osztály,
// mint a napi felkapott-top csempéké (.elemzes-felkapott-csempe) — a SAME VALÓS stílus.
// Guard: hiányzó/üres het_valos esetén nem dob, nem rajzol semmit.
function valos_felkapott_het_csempek(hetValos) {
  const wrap = document.createElement("div");
  wrap.className = "elemzes-csempek";
  wrap.id = "felkapott-het-valos";
  const visszateroek = (hetValos && hetValos.visszateroek) || [];
  visszateroek.forEach((v) => {
    const c = document.createElement("div");
    c.className = "elemzes-felkapott-csempe";
    c.textContent = `${v.kifejezes} — ${v.napok_szama} nap`;
    wrap.appendChild(c);
  });
  return wrap;
}

function rajzol(art) {
  const t = document.getElementById("elemzes-tartalom");
  t.textContent = "";
  document.getElementById("elemzes-fejlec").textContent =
    `Elemzés — ${art.nap} (${art.modell})`;

  // Mi változott ma? — a szekció (folyó AI-próza) ELŐBB, a VALÓS diff-összegzés
  // (a nap-diffből, csak van_elozo esetén) UTÁNA.
  const valt = document.createElement("div");
  const d = art.valtozas.diff;
  valt.appendChild(szekcio_elem("Mi változott ma?", art.valtozas));
  if (d.van_elozo) {
    const diffOsszegzes = document.createElement("p");
    diffOsszegzes.className = "elemzes-diff-osszegzes elemzes-megfigyeles";   // VALÓS réteg (diff-számítás)
    diffOsszegzes.textContent =
      `Irányt váltott: ${d.irany_valtok.map((v) => v.szo).join(", ") || "–"} · új felkapott: ${d.felkapott_uj.join(", ") || "–"} · eltűnt: ${d.felkapott_eltunt.join(", ") || "–"}`;
    valt.appendChild(diffOsszegzes);
  }
  // legnagyobb mozgók (VALÓS, a nap-diffből — d.mozgok) — csak ha van előző nap ÉS van mozgás
  if (d.van_elozo && Array.isArray(d.mozgok) && d.mozgok.length) {
    const mozgokP = document.createElement("p");
    mozgokP.className = "elemzes-diff-mozgok elemzes-megfigyeles";   // VALÓS réteg (diff-számítás)
    mozgokP.textContent = "legnagyobb mozgók: " + d.mozgok
      .map((m) => `${m.szo} (${m.valtozas > 0 ? "+" : ""}${m.valtozas})`)
      .join(", ");
    valt.appendChild(mozgokP);
  }
  t.appendChild(valt);

  // Kulcsszavak
  t.appendChild(valos_kulcsszo_csempek(art.kulcsszavak.szamok));
  t.appendChild(szekcio_elem("Kulcsszavak — mit látunk ma", art.kulcsszavak.napi));
  t.appendChild(szekcio_elem("Kulcsszavak — teljes kép", art.kulcsszavak.teljes_kep));
  t.appendChild(szekcio_elem("Kulcsszavak — 1 hét", art.kulcsszavak.het));

  // Felkapott
  t.appendChild(valos_felkapott_csempek(art.felkapott.top));
  t.appendChild(szekcio_elem("Felkapott — napi", art.felkapott.napi));
  t.appendChild(szekcio_elem("Felkapott — heti összesítés", art.felkapott.het));
  // VALÓS heti visszatérés-csempék (het_valos) — guard: hiányzó/üres esetén nem rajzol semmit
  const hetValos = art.felkapott.het_valos;
  if (hetValos && Array.isArray(hetValos.visszateroek) && hetValos.visszateroek.length) {
    t.appendChild(valos_felkapott_het_csempek(hetValos));
  }
}

// ── archívum nap-választó — a naptar_epit (app.js:454) VALÓS interfészét használja:
// cellaAllapot(iso, szomszed) → { valaszthato, extraOsztaly, aria } (NEM "valaszthato"/"tiltott" string);
// a kattintható nap-cella `data-nap`-ot hordoz (NEM data-iso). Ugyanaz az állapot-a-konténeren minta,
// mint a datum_valaszto_render/trend_esemeny_kot (app.js:506-530, 1797-1816).
let elemzes_archivum_napok = null;
let elemzes_esemeny_kotve = false;

function elemzes_naptar_render() {
  const el = document.getElementById("elemzes-naptar");
  const napok = elemzes_archivum_napok;
  if (!el || !napok || !napok.length) return;
  const keszlet = new Set(napok);
  const elso_ho = napok[0].slice(0, 7), utolso_ho = napok[napok.length - 1].slice(0, 7);
  let valasztott = el.getAttribute("data-valasztott-nap");
  if (!valasztott || !keszlet.has(valasztott)) valasztott = napok[napok.length - 1];
  let honap = el.getAttribute("data-honap") || valasztott.slice(0, 7);
  if (honap < elso_ho) honap = elso_ho;
  if (honap > utolso_ho) honap = utolso_ho;
  el.setAttribute("data-valasztott-nap", valasztott);
  el.setAttribute("data-honap", honap);
  el.textContent = "";
  el.appendChild(naptar_epit(honap, elso_ho, utolso_ho, function (iso, szomszed) {
    const vanAdat = !szomszed && keszlet.has(iso);
    return { valaszthato: vanAdat, extraOsztaly: iso === valasztott ? "valasztott" : "", aria: iso === valasztott ? "date" : null };
  }));
}

function elemzes_esemeny_kot() {
  if (elemzes_esemeny_kotve) return;
  const el = document.getElementById("elemzes-naptar");
  if (!el) return;
  el.addEventListener("click", async function (ev) {
    const btn = ev.target && ev.target.closest ? ev.target.closest("button") : null;
    if (!btn || btn.disabled) return;
    if (btn.classList.contains("nap-cella")) {                  // nap kiválasztása → új elemzés betöltése
      const iso = btn.getAttribute("data-nap");
      el.setAttribute("data-valasztott-nap", iso);
      elemzes_naptar_render();
      try {
        rajzol(await elemzes_betolt(iso));
      } catch (e) {
        document.getElementById("elemzes-tartalom").textContent = "Az elemzés jelenleg nem érhető el.";
      }
    } else if (btn.classList.contains("honap-lep")) {           // hónap-lépés (a kiválasztás VÁLTOZATLAN)
      const cur = el.getAttribute("data-honap") || "";
      el.setAttribute("data-honap", naptar_honap_lep(cur, btn.classList.contains("elore") ? 1 : -1));
      elemzes_naptar_render();
    }
  });
  elemzes_esemeny_kotve = true;
}

async function elemzes_indit() {
  try {
    rajzol(await elemzes_betolt(null));
  } catch (e) {
    document.getElementById("elemzes-fejlec").textContent = "Elemzés — nem érhető el";
    document.getElementById("elemzes-tartalom").textContent = "Az elemzés jelenleg nem érhető el.";
  }
  // archívum-választó — opcionális, fail-soft: ha nincs index.json, a fül csak a legfrissebbet mutatja
  try {
    const r = await fetch("data/elemzesek/index.json");
    if (!r.ok) throw new Error("nincs archívum");
    const idx = await r.json();
    if (idx && Array.isArray(idx.napok) && idx.napok.length && typeof naptar_epit === "function") {
      elemzes_archivum_napok = idx.napok.slice().sort();
      elemzes_naptar_render();
      elemzes_esemeny_kot();
    }
  } catch (e) { /* nincs archívum */ }
}

document.addEventListener("DOMContentLoaded", elemzes_indit);
