"use strict";
// „Radar" fül — a backend JSON-jainak renderelése: szokatlan változások (data/elmozdulas.json)
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

const BOV_RENDEZES = { napok: "Időtartam", frissesseg: "Frissesség", mozgas: "Mozgás" };
const BOV_MOZGAS_SORREND = { erosodo: 0, stabil: 1, lecsengo: 2, nem_megallapithato: 3 };
const bov_allapot = { szakpolitika: "", rendezes: "napok", elm: null, ugy: null, kapcs: null };

function bov_elmozdulas_render(cel, elm, szak) {
  cel.innerHTML = "";
  cel.appendChild(bel("h2", "elemzes-csoport-cim", "Szokatlan változások"));
  const kulcsszavak = (elm && elm.kulcsszavak) || {};
  const lista = ((elm && elm.szokatlan_lista) || []).filter((szo) => !szak || (kulcsszavak[szo] || {}).szakpolitika === szak);
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

// minden naptári nap [elso..utolso] között, ISO-sztringként (Date nélkül, determinista).
function bov_nap_lista(elso, utolso) {
  const ki = [];
  if (!elso || !utolso || elso > utolso) return ki;
  const szokoev = (y) => (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
  const honap_hossz = (y, m) => [31, szokoev(y) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
  const pad = (n) => String(n).padStart(2, "0");
  let [y, m, d] = elso.split("-").map(Number);
  for (let i = 0; i < 1000; i++) {                 // biztonsági felső korlát (~2,7 év)
    const iso = y + "-" + pad(m) + "-" + pad(d);
    ki.push(iso);
    if (iso >= utolso) break;
    if (++d > honap_hossz(y, m)) { d = 1; if (++m > 12) { m = 1; y++; } }
  }
  return ki;
}

// napi jelenlét-idővonal: egy cella / NAPTÁRI nap (bal=régebbi, jobb=újabb). Jelen = kék, a volumen szerint
// árnyalva (sötétebb = több keresés); a hiányzó napok halványak. A backend csak a JELEN napokat küldi,
// ezért a teljes [elso..utolso] naptári tartományt magunk töltjük ki. Felirat + jelmagyarázat + végdátumok segítenek.
function bov_idovonal(sor, elso, utolso) {
  const doboz = bel("div", "bovites-idovonal-doboz");
  doboz.appendChild(bel("div", "bovites-idovonal-cim halvany", "Napi jelenlét az ablakban (régebbi → újabb):"));
  const sav = bel("div", "bovites-idovonal");
  sav.setAttribute("role", "img");
  sav.setAttribute("aria-label", "Napi jelenlét" + (elso && utolso ? " " + elso + "-tól " + utolso + "-ig" : "")
    + ": sötétebb kék = több keresés aznap, halvány = nincs jelen.");
  const jelenMap = {};
  (sor || []).forEach((p) => { if (p.jelen) jelenMap[p.nap] = Number(p.ossz_volumen) || 0; });
  const volok = Object.keys(jelenMap).map((k) => jelenMap[k]);
  const maxVol = volok.length ? Math.max.apply(null, volok) : 0;
  const napok = (elso && utolso) ? bov_nap_lista(elso, utolso) : (sor || []).map((p) => p.nap);
  napok.forEach((nap) => {
    const jelen = Object.prototype.hasOwnProperty.call(jelenMap, nap);
    const c = bel("span", "bovites-nap" + (jelen ? " jelen" : ""));
    if (jelen) {
      const t = maxVol > 0 ? jelenMap[nap] / maxVol : 1;
      c.style.backgroundColor = "rgba(42, 120, 214, " + (0.35 + 0.65 * t).toFixed(2) + ")";
    }
    c.title = nap + (jelen ? " – jelen, összvolumen: " + jelenMap[nap] : " – nincs jelen");
    sav.appendChild(c);
  });
  doboz.appendChild(sav);
  const jm = bel("div", "bovites-idovonal-jelmagy halvany");
  jm.appendChild(bel("span", "bovites-idovonal-datum", elso || ""));
  const kulcs = bel("span", "bovites-idovonal-kulcs");
  kulcs.appendChild(bel("span", "bovites-nap jelen bovites-nap-minta"));
  kulcs.appendChild(document.createTextNode(" jelen (sötétebb = több keresés) · "));
  kulcs.appendChild(bel("span", "bovites-nap bovites-nap-minta"));
  kulcs.appendChild(document.createTextNode(" nincs jelen"));
  jm.appendChild(kulcs);
  jm.appendChild(bel("span", "bovites-idovonal-datum", utolso || ""));
  doboz.appendChild(jm);
  return doboz;
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
  k.appendChild(bov_idovonal(u.idovonal, u.elso_nap, u.utolso_nap));
  return k;
}

function bov_ugyek_render(cel, ugy, szak, rend) {
  cel.innerHTML = "";
  cel.appendChild(bel("h2", "elemzes-csoport-cim", "Ügyek életútja"));
  if (!ugy) { cel.appendChild(bel("p", "ures", "Az ügyek adata nem érhető el.")); return; }
  const rendezo = {
    napok: (a, b) => (b.napok_szama || 0) - (a.napok_szama || 0),
    frissesseg: (a, b) => String(b.utolso_nap || "").localeCompare(String(a.utolso_nap || "")),
    mozgas: (a, b) => (BOV_MOZGAS_SORREND[a.mozgas] ?? 9) - (BOV_MOZGAS_SORREND[b.mozgas] ?? 9),
  }[rend] || ((a, b) => 0);
  const ugyek = (ugy.ugyek || []).filter((u) => !szak || u.szakpolitika === szak).slice().sort(rendezo);
  if (!ugyek.length) { cel.appendChild(bel("p", "ures", "Nincs megjeleníthető ügy.")); return; }
  const lista = bel("div", "bovites-ugy-lista");
  ugyek.forEach((u) => lista.appendChild(bov_ugy_kartya(u)));
  cel.appendChild(lista);
}

// „Kapcsolódó keresések": kifejezésenként top + felfutó (rising) lekérdezések; a szakpolitika-szűrő NEM érinti
function bov_kapcs_ertek(v) {
  if (typeof v === "number") return "+" + v.toLocaleString("hu-HU") + "%";
  return v == null ? "" : String(v);
}

function bov_kapcs_lista(cim, sorok, rising, sugo) {
  const oszlop = bel("div", "bovites-kapcs-oszlop");
  oszlop.appendChild(bel("h4", "bovites-kapcs-oszlopcim", cim));
  if (sugo) oszlop.appendChild(bel("div", "bovites-kapcs-sugo halvany", sugo));
  const chipek = bel("div", "bovites-chipek");
  (sorok || []).forEach((s) => {
    const nagy = rising && (s.value === "Breakout" || (typeof s.value === "number" && s.value >= 5000));
    const chip = bel("span", "bovites-chip bovites-kapcs-chip" + (nagy ? " bovites-kapcs-breakout" : ""), s.query);
    const ertek = rising ? bov_kapcs_ertek(s.value) : (s.value == null ? "" : String(s.value));
    if (ertek) chip.appendChild(bel("span", "bovites-kapcs-ertek halvany", " " + ertek));
    chipek.appendChild(chip);
  });
  if (!(sorok || []).length) chipek.appendChild(bel("span", "halvany", "Nincs adat."));
  oszlop.appendChild(chipek);
  return oszlop;
}

function bov_kapcsolodo_render(cel, kapcs) {
  if (!cel) return;
  cel.innerHTML = "";
  if (!kapcs) return;   // fail-soft: nincs adat -> a szekció üres
  cel.appendChild(bel("h2", "elemzes-csoport-cim", "Kapcsolódó keresések"));
  const lista = kapcs.kifejezesek || [];
  if (!lista.length) { cel.appendChild(bel("p", "ures", "Még nincs kapcsolódó keresés.")); return; }
  const racs = bel("div", "bovites-kapcs-lista");
  lista.forEach((k) => {
    const kartya = bel("article", "bovites-kapcs-kartya");
    kartya.appendChild(bel("h3", "bovites-kapcs-cim", k.kifejezes));
    const ketto = bel("div", "bovites-kapcs-ketto");
    ketto.appendChild(bov_kapcs_lista("Top (megszokott)", k.top, false,
      "A szám = relatív népszerűség 0–100 (100 = a leggyakoribb kapcsolódó keresés)."));
    ketto.appendChild(bov_kapcs_lista("Felfutó", k.rising, true,
      "A szám = mennyivel nőtt a keresés; a „Breakout” kiugró (nagy) felfutás."));
    kartya.appendChild(ketto);
    racs.appendChild(kartya);
  });
  cel.appendChild(racs);
}

function bov_rajzol() {
  const elmCel = document.getElementById("bovites-elmozdulas");
  if (elmCel) bov_elmozdulas_render(elmCel, bov_allapot.elm, bov_allapot.szakpolitika);
  const ugyCel = document.getElementById("bovites-ugyek");
  if (ugyCel) bov_ugyek_render(ugyCel, bov_allapot.ugy, bov_allapot.szakpolitika, bov_allapot.rendezes);
  const kapcsCel = document.getElementById("bovites-kapcsolodo");
  if (kapcsCel) bov_kapcsolodo_render(kapcsCel, bov_allapot.kapcs);
  document.querySelectorAll(".bovites-szuro-chip").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.szakpolitika === bov_allapot.szakpolitika)));
  document.querySelectorAll(".bovites-rendezes-gomb").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.rendezes === bov_allapot.rendezes)));
}

// szakpolitika-szűrő chip-sor (hozzáfűz, nem töröl) — a Szokatlan változások és az Ügyek panelbe is kerül
function bov_szakpolitika_epit(cel) {
  if (!cel) return;
  const sor = bel("div", "bovites-szuro-sor");
  sor.appendChild(bel("span", "halvany", "Szakpolitika:"));
  const chip = (kulcs, felirat) => {
    const b = bel("button", "bovites-szuro-chip", felirat);
    b.type = "button";
    b.dataset.szakpolitika = kulcs;
    b.addEventListener("click", () => { bov_allapot.szakpolitika = kulcs; bov_rajzol(); });
    sor.appendChild(b);
  };
  chip("", "Összes");
  Object.keys(BOV_SZAKPOLITIKA).forEach((k) => chip(k, BOV_SZAKPOLITIKA[k]));
  cel.appendChild(sor);
}

// rendezés-sor (hozzáfűz) — csak az Ügyek életútja panelben
function bov_rendezes_epit(cel) {
  if (!cel) return;
  const rsor = bel("div", "bovites-szuro-sor");
  rsor.appendChild(bel("span", "halvany", "Ügyek rendezése:"));
  Object.keys(BOV_RENDEZES).forEach((k) => {
    const b = bel("button", "bovites-rendezes-gomb", BOV_RENDEZES[k]);
    b.type = "button";
    b.dataset.rendezes = k;
    b.addEventListener("click", () => { bov_allapot.rendezes = k; bov_rajzol(); });
    rsor.appendChild(b);
  });
  cel.appendChild(rsor);
}

function bov_datum(s) { return (s ? String(s) : "").slice(0, 10); }

function bov_idosav_ir(szoveg) {
  const cel = document.getElementById("radar-idosav");
  if (cel) cel.textContent = szoveg || "";
}

async function bov_init() {
  if (document.getElementById("bovites-elmozdulas")) {
    bov_allapot.elm = await bov_json("data/elmozdulas.json");
    bov_idosav_ir(bov_allapot.elm
      ? "Aktuális kiugrások — a szavak szokásos szintjéhez képest · számítva: " + bov_datum(bov_allapot.elm.szamitva_utc)
      : "");
    bov_szakpolitika_epit(document.getElementById("bovites-szuro-elm"));
  } else if (document.getElementById("bovites-ugyek")) {
    bov_allapot.ugy = await bov_json("data/ugyek.json");
    const ab = bov_allapot.ugy && bov_allapot.ugy.ablak;
    bov_idosav_ir(ab ? "Gördülő " + ab.nap + " napos ablak: " + ab.kezdet + " – " + ab.veg : "");
    bov_szakpolitika_epit(document.getElementById("bovites-szuro-ugy"));
    bov_rendezes_epit(document.getElementById("bovites-szuro-ugy"));
  } else if (document.getElementById("bovites-kapcsolodo")) {
    bov_allapot.kapcs = await bov_json("data/kapcsolodo.json");
    bov_idosav_ir(bov_allapot.kapcs ? "Naponta frissül · utolsó: " + bov_datum(bov_allapot.kapcs.frissitve) : "");
  }
  bov_rajzol();
}

bov_init();
