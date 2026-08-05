// Trendfigyelő adatbetöltő réteg (Task 5) — fetch + cache-busting + IZOLÁLT hibaállapot.
// Chartot MÉG NEM rajzol (Task 6/7/8/9b); a betöltött adatot eltárolja, a hibákat a blokkba írja
// (nem néma, spec 7.5). Csak saját, relatív erőforrások — külső URL TILOS (Task 1).
"use strict";

const ADAT = "data/";
const HIBA_SZOVEG = "Hiba az adat betöltésekor";

// cache-busting: a naponta ugyanazon az útvonalon felülírt JSON-t a ?v= friss letöltésre kényszeríti (4.1)
function adat_url(rel) {
  return ADAT + rel + "?v=" + Date.now();
}

async function json_betolt(rel) {
  const valasz = await fetch(adat_url(rel));
  if (!valasz.ok) {
    throw new Error("HTTP " + valasz.status + " - " + rel);
  }
  return valasz.json();
}

// a hibaüzenet KÜLÖN gyerek-elembe kerül (nem írja felül a blokk esetleges tartalmát),
// és a KONKRÉT hiányzó fájl(oka)t + okot mondja (nem néma, nem tartalmatlan)
function hiba_kiir(blokk_id, reszletek, bevezeto) {
  const el = document.getElementById(blokk_id);
  if (!el) return;
  const p = document.createElement("p");
  p.className = "hiba";
  p.textContent = (bevezeto || HIBA_SZOVEG) + ": " + reszletek.join("; ") + ".";
  el.appendChild(p);
}

// blokk -> a hozzá tartozó init-fájlok
const BLOKKOK = [
  { id: "kulcsszo-blokk", fajlok: ["kulcsszo_regresszio.json", "kulcsszo_nyers.json"] },
  { id: "trend-blokk", fajlok: ["legfrissebb.json", "napok/index.json"] },
];

const adat = {}; // rel -> betöltött JSON (a Task 6/7/8/9b innen rajzol)

async function blokk_betolt(blokk) {
  // FÁJLONKÉNTI izoláció: egy hiányzó fájl (ma pl. kulcsszo_regresszio.json) NE tegye
  // használhatatlanná a blokk többi, sikeresen betöltött adatát (pl. kulcsszo_nyers.json).
  const eredmenyek = await Promise.allSettled(blokk.fajlok.map(function (rel) {
    return json_betolt(rel).then(function (json) { adat[rel] = json; });
  }));
  const hibak = [];
  eredmenyek.forEach(function (e, i) {
    if (e.status === "rejected") {
      hibak.push((e.reason && e.reason.message) || blokk.fajlok[i]);
    }
  });
  if (hibak.length) {
    hiba_kiir(blokk.id, hibak);
  }
}

async function init() {
  // blokkonkénti izoláció is: egy blokk hibája se döntse el a másikat
  await Promise.allSettled(BLOKKOK.map(blokk_betolt));
  await vezerlok_render();
}

// igény szerinti napi trend-fájl (dátumválasztó — Task 6/7)
async function nap_betolt(datum) {
  return json_betolt("napok/" + datum + ".json");
}

// ── Task 6: vezérlők (intervallum-gombok + dátumválasztó) ────────────────────
// A gombok elérhetősége a kulcsszo_regresszio.json ervenyes mezőjéből jön (spec 7.4),
// szónkénti AGGREGÁCIÓVAL: egy intervallum engedélyezett, ha LEGALÁBB EGY szónál ervenyes.

const INTERVALLUMOK = [
  { kulcs: "1_het", cimke: "1 hét", hossz: 7 },
  { kulcs: "2_het", cimke: "2 hét", hossz: 14 },
  { kulcs: "1_ho", cimke: "1 hó", hossz: 30 },
  { kulcs: "3_ho", cimke: "3 hó", hossz: 90 },
  { kulcs: "1_ev", cimke: "1 év", hossz: 365 },
];

// ok-kód -> LÁTHATÓ magyar magyarázat a letiltott gombhoz (spec 7.4)
const OK_MAGYAR = {
  nincs_lancolas: "Ehhez több összefűzött nap kell",
  nincs_adat: "Nincs mért adat",
  keves_pont: "Túl kevés mért pont",
  rovid_span: "Túl rövid mért időszak",
  degeneralt: "Nem illeszthető",
};

// Ha egy intervallumnál EGYIK szó sem érvényes, több szó több OK-t adhat: a leggyakoribb (mode)
// jelenik meg; döntetlennél ez a prioritás dönt (strukturális/akcióképes ok előrébb).
const OK_PRIORITAS = ["nincs_lancolas", "keves_pont", "rovid_span", "degeneralt", "nincs_adat"];

// ismeretlen ok-kód a sor VÉGÉRE (indexOf -1 → OK_PRIORITAS.length), ne az elejére —
// egy jövőbeli, még lefordítatlan kód ne nyerjen automatikusan a döntetlennél
function ok_prioritas(o) {
  const i = OK_PRIORITAS.indexOf(o);
  return i === -1 ? OK_PRIORITAS.length : i;
}

function dominans_ok(okok) {
  if (!okok.length) return "nincs_adat";
  const szamlalo = {};
  okok.forEach(function (o) { szamlalo[o] = (szamlalo[o] || 0) + 1; });
  let legjobb = okok[0];
  okok.forEach(function (o) {
    const gyakoribb = szamlalo[o] > szamlalo[legjobb];
    const dontetlen = szamlalo[o] === szamlalo[legjobb] && ok_prioritas(o) < ok_prioritas(legjobb);
    if (gyakoribb || dontetlen) legjobb = o;
  });
  return legjobb;
}

// egy intervallum globális állapota (aggregáció: legalább egy szónál ervenyes)
function intervallum_allapot(kulcsszavak, kulcs) {
  let ervenyes = false;
  const okok = [];
  Object.keys(kulcsszavak).forEach(function (szo) {
    const iv = kulcsszavak[szo].intervallumok && kulcsszavak[szo].intervallumok[kulcs];
    if (!iv) return;
    if (iv.ervenyes) ervenyes = true;
    else if (iv.ok) okok.push(iv.ok);
  });
  return { ervenyes: ervenyes, ok: ervenyes ? null : dominans_ok(okok) };
}

function ures_allapot(el, uzenet) {
  el.textContent = "";
  const p = document.createElement("p");
  p.className = "ures";
  p.textContent = uzenet;
  el.appendChild(p);
}

// kétféle üres-szöveg: a hiányzó adat NEM ugyanaz, mint a "van adat, de nincs érvényes ablak"
const URES_NINCS_ADAT = "A kulcsszó-adat még nem érhető el.";      // hiányzó/üres regresszió
const URES_NINCS_ERVENYES = "Egyetlen időszak sem érvényes még.";  // van adat, de egy intervallum sem érvényes

function intervallum_vezerlo_render() {
  const el = document.getElementById("intervallum-vezerlo");
  if (!el) return;
  const reg = adat["kulcsszo_regresszio.json"];
  if (!reg || !reg.kulcsszavak || !Object.keys(reg.kulcsszavak).length) {
    ures_allapot(el, URES_NINCS_ADAT);          // (a) nincs adat (a #kulcsszo-blokk hibáját a loader külön kiírta)
    return;
  }
  const allapotok = INTERVALLUMOK.map(function (iv) {
    const a = intervallum_allapot(reg.kulcsszavak, iv.kulcs);
    return { kulcs: iv.kulcs, cimke: iv.cimke, hossz: iv.hossz, ervenyes: a.ervenyes, ok: a.ok };
  });
  const ervenyesek = allapotok.filter(function (a) { return a.ervenyes; });
  const kivalasztott = ervenyesek.length
    ? ervenyesek.reduce(function (a, b) { return b.hossz > a.hossz ? b : a; })
    : null;
  el.textContent = "";
  // (b) VAN adat, de EGYIK intervallum sem érvényes: NEM egy mondat — mind az 5 letiltott gomb
  // a saját ok-szövegével jelenik meg (spec 7.4: a letiltott gomb magyarázatot adjon), + .ures fejléc
  if (!kivalasztott) {
    const fejlec = document.createElement("p");
    fejlec.className = "ures";
    fejlec.textContent = URES_NINCS_ERVENYES;
    el.appendChild(fejlec);
  }
  allapotok.forEach(function (a) {
    const gomb = document.createElement("button");
    gomb.setAttribute("data-intervallum", a.kulcs);
    gomb.textContent = a.cimke;
    if (a.ervenyes) {
      gomb.setAttribute("aria-pressed", kivalasztott && a.kulcs === kivalasztott.kulcs ? "true" : "false");
      el.appendChild(gomb);
    } else {
      gomb.disabled = true;
      el.appendChild(gomb);
      const ok = document.createElement("span"); // LÁTHATÓ magyar ok a gomb mellé (nem csak title)
      ok.className = "ok";
      ok.textContent = OK_MAGYAR[a.ok] || a.ok;
      el.appendChild(ok);
    }
  });
}

function datum_formaz(iso) {
  const r = iso.split("-"); // "2026-08-04" -> "2026. 08. 04."
  return r[0] + ". " + r[1] + ". " + r[2] + ".";
}

function datum_valaszto_render() {
  const el = document.getElementById("datum-valaszto");
  if (!el) return;
  const idx = adat["napok/index.json"];
  const napok = (idx && Array.isArray(idx.napok)) ? idx.napok.slice() : [];
  if (!napok.length) {
    ures_allapot(el, "Nincs elérhető nap.");
    return;
  }
  napok.sort(); // növekvő ISO -> a legfrissebb az utolsó
  const legfrissebb = napok[napok.length - 1];
  el.textContent = "";
  const sel = document.createElement("select");
  napok.forEach(function (nap) {
    const opt = document.createElement("option");
    opt.value = nap;
    opt.textContent = datum_formaz(nap);
    if (nap === legfrissebb) opt.selected = true; // alapból a legfrissebb nap
    sel.appendChild(opt);
  });
  el.appendChild(sel);
}

const RENDER_HIBA_SZOVEG = "Hiba a vezérlő megjelenítésekor";
const RENDEREK = [
  { id: "intervallum-vezerlo", fn: intervallum_vezerlo_render },
  { id: "datum-valaszto", fn: datum_valaszto_render },
];

// a két vezérlő EGYMÁSTÓL FÜGGETLENÜL renderel (Task 5 allSettled-izoláció); a render-KIVÉTELT
// is a Task 5 hiba_kiir mintájával jelezzük (nem néma) — render-specifikus bevezetővel
async function vezerlok_render() {
  const eredmenyek = await Promise.allSettled(RENDEREK.map(function (r) {
    return Promise.resolve().then(r.fn);
  }));
  eredmenyek.forEach(function (e, i) {
    if (e.status === "rejected") {
      hiba_kiir(RENDEREK[i].id, [(e.reason && e.reason.message) || "renderelési hiba"], RENDER_HIBA_SZOVEG);
    }
  });
}

document.addEventListener("DOMContentLoaded", init);
