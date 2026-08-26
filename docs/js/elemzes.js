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

// Megjegyzés: a nyers felkapott-csempesorok (napi top „(volumen: …)" + heti visszatérés
// „— N nap") KIVÉVE (user-döntés 2026-08-23) — a felkapottat az AI-próza foglalja össze.
// A het_valos VALÓS réteg az artefaktban MARAD (fail-safe adat), csak nem rajzoljuk csempeként.

// egy nevesített szegmens-cím (Google / YouTube)
function szegmens_cim(szoveg) {
  const h = document.createElement("h2");
  h.className = "elemzes-szegmens";
  h.textContent = szoveg;
  return h;
}

// YouTube-szegmens: VALÓS csempék (a Google-render újrahasznosításával) + 3 AI-szekció
function youtube_szegmens(yt) {
  const box = document.createElement("section");
  box.id = "youtube-szegmens";
  box.appendChild(szegmens_cim("YouTube keresések napi elemzése"));
  box.appendChild(valos_kulcsszo_csempek(yt.szamok));
  box.appendChild(szekcio_elem("YouTube — mit néznek ma", yt.napi));
  box.appendChild(szekcio_elem("YouTube — teljes kép", yt.teljes_kep));
  box.appendChild(szekcio_elem("YouTube — heti mozgás", yt.het));
  return box;
}

function rajzol(art) {
  const t = document.getElementById("elemzes-tartalom");
  t.textContent = "";
  document.getElementById("elemzes-fejlec").textContent =
    `Elemzés — ${art.nap} (${art.modell})`;

  t.appendChild(szegmens_cim("Google keresések napi elemzése"));

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

  // Felkapott — CSAK az AI-próza (a nyers csempesorok kivéve; lásd a fenti megjegyzést)
  t.appendChild(szekcio_elem("Felkapott — napi", art.felkapott.napi));
  t.appendChild(szekcio_elem("Felkapott — heti összesítés", art.felkapott.het));

  // YouTube-szegmens — fail-soft: régi archív-nap (nincs art.youtube) → nincs YouTube-rész
  if (art.youtube) t.appendChild(youtube_szegmens(art.youtube));
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
