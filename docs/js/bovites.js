"use strict";
// „Bővítés" fül — a backend JSON-jainak renderelése: szokatlan változások (data/elmozdulas.json)
// és ügyek életútja + napi jelenlét-idővonal (data/ugyek.json). A frontend nem számol statisztikát,
// csak megjelenít. NINCS new Date().

const BOV_ELETUT = { ujonnan_megfigyelt: "Újonnan megfigyelt", folyamatosan_jelenlevo: "Folyamatosan jelen",
  visszatero: "Visszatérő", egyeb: "Egyéb" };
const BOV_MOZGAS = { erosodo: "Erősödő", stabil: "Stabil", lecsengo: "Lecsengő",
  nem_megallapithato: "Nem megállapítható" };
const BOV_SZAKPOLITIKA = { szocialpolitika: "Szociálpolitika", egeszsegpolitika: "Egészségpolitika",
  oktataspolitika: "Oktatáspolitika", gazdasag_foglalkoztatas: "Gazdaság- és foglalkoztatáspolitika",
  lakhatas: "Lakhatás", energia_rezsi: "Energia és rezsi", kozelet_kozigazgatas: "Közélet és közigazgatás",
  egyeb: "Egyéb / nem közpolitikai" };
const BOV_IRANY = { emelkedik: "emelkedik", csokken: "csökken", stabil: "stabil" };
const BOV_MEGBIZ = { magas: "magas", kozepes: "közepes", alacsony: "alacsony" };

function bel(tag, cls, szoveg) {
  const h = document.createElement(tag);
  if (cls) h.className = cls;
  if (szoveg != null) h.textContent = szoveg;
  return h;
}

async function bov_json(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch (e) { return null; }
}

function bov_elmozdulas_render(cel, elm) {
  cel.innerHTML = "";
  cel.appendChild(bel("h2", "elemzes-csoport-cim", "Szokatlan változások"));
  const lista = (elm && elm.szokatlan_lista) || [];
  const kulcsszavak = (elm && elm.kulcsszavak) || {};
  if (!elm) { cel.appendChild(bel("p", "ures", "A szokatlan változások adata nem érhető el.")); return; }
  if (!lista.length) { cel.appendChild(bel("p", "ures", "Nincs szokatlan elmozdulás.")); return; }
  const racs = bel("div", "bovites-elm-racs");
  lista.forEach((szo) => {
    const k = kulcsszavak[szo] || {};
    const kartya = bel("div", "bovites-elm-kartya bovites-irany-" + (k.irany || "stabil"));
    kartya.appendChild(bel("div", "bovites-elm-szo", szo));
    kartya.appendChild(bel("div", "bovites-elm-irany", BOV_IRANY[k.irany] || k.irany || ""));
    const r = [];
    if (typeof k.elteres === "number") r.push("eltérés: ×" + String(k.elteres).replace(".", ",") + " a szokásoshoz képest");
    if (k.idotartam_pont != null) r.push("mióta tart: " + k.idotartam_pont + " pont");
    if (k.megbizhatosag) r.push("megbízhatóság: " + (BOV_MEGBIZ[k.megbizhatosag] || k.megbizhatosag));
    r.forEach((t) => kartya.appendChild(bel("div", "bovites-elm-adat", t)));
    if (k.szakpolitika) kartya.appendChild(bel("span", "bovites-cimke", BOV_SZAKPOLITIKA[k.szakpolitika] || k.szakpolitika));
    racs.appendChild(kartya);
  });
  cel.appendChild(racs);
}

// napi jelenlét-sáv: egy cella / nap; jelen = kitöltött, nincs = halvány; a cím tartalmazza a napot + volument
function bov_idovonal(sor) {
  const sav = bel("div", "bovites-idovonal");
  sav.setAttribute("role", "img");
  sav.setAttribute("aria-label", "Napi jelenlét az ablakban");
  (sor || []).forEach((p) => {
    const c = bel("span", "bovites-nap" + (p.jelen ? " jelen" : ""));
    c.title = p.nap + (p.jelen ? " – jelen, összvolumen: " + p.ossz_volumen : " – nincs jelen");
    sav.appendChild(c);
  });
  return sav;
}

function bov_ugy_kartya(u) {
  const k = bel("article", "bovites-ugy");
  k.appendChild(bel("h3", "bovites-ugy-nev", u.nev));
  const cimkek = bel("div", "bovites-cimkek");
  if (u.szakpolitika) cimkek.appendChild(bel("span", "bovites-cimke", BOV_SZAKPOLITIKA[u.szakpolitika] || u.szakpolitika));
  cimkek.appendChild(bel("span", "bovites-cimke bovites-eletut", BOV_ELETUT[u.eletut] || u.eletut || ""));
  cimkek.appendChild(bel("span", "bovites-cimke bovites-mozgas-" + (u.mozgas || ""), BOV_MOZGAS[u.mozgas] || u.mozgas || ""));
  k.appendChild(cimkek);
  if (u.osszefoglalo) k.appendChild(bel("p", "bovites-osszefoglalo", u.osszefoglalo));
  const chipek = bel("div", "bovites-chipek");
  (u.kifejezesek || []).forEach((x) => chipek.appendChild(bel("span", "bovites-chip", x)));
  k.appendChild(chipek);
  k.appendChild(bel("div", "bovites-meta halvany",
    u.elso_nap + " – " + u.utolso_nap + " · " + u.napok_szama + " nap"));
  k.appendChild(bov_idovonal(u.idovonal));
  return k;
}

function bov_ugyek_render(cel, ugy) {
  cel.innerHTML = "";
  cel.appendChild(bel("h2", "elemzes-csoport-cim", "Ügyek életútja"));
  if (!ugy) { cel.appendChild(bel("p", "ures", "Az ügyek adata nem érhető el.")); return; }
  const ugyek = (ugy.ugyek || []).slice().sort((a, b) => (b.napok_szama || 0) - (a.napok_szama || 0));
  if (!ugyek.length) { cel.appendChild(bel("p", "ures", "Nincs megjeleníthető ügy.")); return; }
  const lista = bel("div", "bovites-ugy-lista");
  ugyek.forEach((u) => lista.appendChild(bov_ugy_kartya(u)));
  cel.appendChild(lista);
}

async function bov_init() {
  const [elm, ugy] = await Promise.all([bov_json("data/elmozdulas.json"), bov_json("data/ugyek.json")]);
  const fejlec = document.getElementById("bovites-fejlec");
  if (!elm && !ugy) {
    document.getElementById("bovites").textContent = "A bővítés adata nem érhető el.";
    if (fejlec) fejlec.textContent = "Nem érhető el.";
    return;
  }
  if (fejlec) {
    const ab = ugy && ugy.ablak;
    fejlec.textContent = ab ? "Ablak: " + ab.kezdet + " – " + ab.veg + " (" + ab.nap + " nap)" : "";
  }
  bov_elmozdulas_render(document.getElementById("bovites-elmozdulas"), elm);
  bov_ugyek_render(document.getElementById("bovites-ugyek"), ugy);
}

bov_init();
