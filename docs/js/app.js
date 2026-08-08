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

// ── DOM-szerződés kulcs-konstansai (osztály- és attribútumnevek + magyar szövegek) ───────────
// NÉVVEL ellátva, mert a Playwright-smoke-ok pontos szöveg-/attribútum-egyezésre mennek (egy elgépelés drága).
const OSZT = {
  kartya: "kulcsszo-chart", cimke: "kulcsszo-cimke", chart_doboz: "chart-doboz", csoport: "domen-csoport", fejlec: "domen-fejlec",
  merteszamok: "merteszamok", tengely_felirat: "tengely-felirat", ures: "ures",
  csupa_nulla: "csupa-nulla", elettartam: "elettartam", frissesseg: "frissesseg",
};
const ATTR = {
  aktiv: "data-aktiv-intervallum", kulcsszo: "data-kulcsszo", drawable: "data-drawable",
  ablak_veg: "data-ablak-veg", adat_veg: "data-adat-veg", pontok: "data-pontok", reszleges: "data-reszleges",
  hianyzo: "data-hianyzo", vonal: "data-vonal", szakadas: "data-szakadas",
  ymax: "data-y-max", rendered: "data-rendered", ok: "data-ok", intervallum: "data-intervallum",
};
const TENGELY_FELIRAT = "relatív keresési szint (0–100)";   // EN DASH
const CSUPA_NULLA_SZOVEG = "Ezen az időszakon nincs érdemi keresési aktivitás (a mért értékek végig nulla körül).";
const URES_NINCS_ABLAK = "Az adatsor ezen az időszakon nem érhető el.";

// ── Task 6: vezérlők (intervallum-gombok + dátumválasztó) ────────────────────
// A gombok elérhetősége a kulcsszo_regresszio.json ervenyes mezőjéből jön (spec 7.4),
// szónkénti AGGREGÁCIÓVAL: egy intervallum engedélyezett, ha LEGALÁBB EGY szónál ervenyes.
// TASK 9b ÁTALAKÍTÁS: az aktív intervallum EGYETLEN igazságforrása a #kulcsszo-blokk
// data-aktiv-intervallum attribútuma; a gombok aria-pressed-je EBBŐL derivált (aria_szinkron).

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
  p.className = OSZT.ures;
  p.textContent = uzenet;
  el.appendChild(p);
}

// kétféle üres-szöveg: a hiányzó adat NEM ugyanaz, mint a "van adat, de nincs érvényes ablak"
const URES_NINCS_ADAT = "A kulcsszó-adat még nem érhető el.";      // hiányzó/üres regresszió
const URES_NINCS_ERVENYES = "Egyetlen időszak sem érvényes még.";  // van adat, de egy intervallum sem érvényes

function intervallum_vezerlo_render() {
  const el = document.getElementById("intervallum-vezerlo");
  const blokk = document.getElementById("kulcsszo-blokk");
  if (!el) return;
  const reg = adat["kulcsszo_regresszio.json"];
  if (!reg || !reg.kulcsszavak || !Object.keys(reg.kulcsszavak).length) {
    if (blokk) blokk.removeAttribute(ATTR.aktiv);        // (a) nincs adat → NINCS aktív intervallum (9b korai kilépés)
    ures_allapot(el, URES_NINCS_ADAT);
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
    if (blokk) blokk.removeAttribute(ATTR.aktiv);        // (b) nincs érvényes → NINCS aktív intervallum
    const fejlec = document.createElement("p");
    fejlec.className = OSZT.ures;
    fejlec.textContent = URES_NINCS_ERVENYES;
    el.appendChild(fejlec);
  } else if (blokk) {
    // EGYETLEN igazságforrás — kezdeti aktív = a leghosszabb ÉRVÉNYES intervallum (spec 7.2/7.4);
    // magától tolódik kifelé, ahogy újabb gombok nyílnak. A kattintás ezt írja át (aktiv_intervallum_valt).
    blokk.setAttribute(ATTR.aktiv, kivalasztott.kulcs);
  }
  allapotok.forEach(function (a) {
    const gomb = document.createElement("button");
    gomb.setAttribute(ATTR.intervallum, a.kulcs);
    gomb.textContent = a.cimke;
    if (a.ervenyes) {
      gomb.setAttribute("aria-pressed", "false");        // a tényleges értéket az aria_szinkron állítja be
      gomb.addEventListener("click", function () { aktiv_intervallum_valt(a.kulcs); });
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
  aria_szinkron();
}

// az aria-pressed a data-aktiv-intervallum-ból DERIVÁLT (egyetlen igazságforrás) — pontosan egy gomb aktív
function aria_szinkron() {
  const blokk = document.getElementById("kulcsszo-blokk");
  const aktiv = blokk ? blokk.getAttribute(ATTR.aktiv) : null;
  document.querySelectorAll("#intervallum-vezerlo button[" + ATTR.intervallum + "]").forEach(function (g) {
    if (g.disabled) return;
    g.setAttribute("aria-pressed", g.getAttribute(ATTR.intervallum) === aktiv ? "true" : "false");
  });
}

// intervallum-váltás (a Task 6 "gombok INTERAKCIÓJA → 7/9b" döntésének BEVÁLTÁSA, nem új scope):
// egy helyen írjuk a data-aktiv-intervallum-ot, majd újraszinkronizáljuk az aria-t és újrarajzoljuk a chartokat
function aktiv_intervallum_valt(kulcs) {
  const blokk = document.getElementById("kulcsszo-blokk");
  if (!blokk) return;
  blokk.setAttribute(ATTR.aktiv, kulcs);
  aria_szinkron();
  kulcsszo_blokk_render();   // a chart_takarit() a régi Chart-példányokat destroy-olja, mielőtt újat épít
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

// ── Task 9b: kulcsszó-blokk — szavankénti chartok + regresszió + mérőszámok + üres állapotok ──
// A chart idősora a kulcsszo_nyers.json-ból (7.2), a regresszió + elérhetőség a kulcsszo_regresszio.json-ból (8.3).
// A frontend NEM SZÁMOL: a regressziós vonal a mini-9a illesztes_vonal két végpontjából rajzolódik.

const DOMEN_MAGYAR = {
  munkaeropiac: "Munkaerőpiac", kozigazgatas: "Közigazgatás", lakhatas: "Lakhatás",
  fogyasztas: "Fogyasztás", egeszseg: "Egészség", energia: "Energia",
  jovedelem: "Jövedelem", haztartasi_penzugy: "Háztartási pénzügy", kozelet: "Közélet",
};
// megjelenítési sorrend; a null (besorolatlan/eltávolított szó) az "Egyéb" csoportba, a lista VÉGÉRE
const DOMEN_SORREND = ["munkaeropiac", "kozigazgatas", "lakhatas", "fogyasztas", "egeszseg",
  "energia", "jovedelem", "haztartasi_penzugy", "kozelet", null];
const EGYEB_KULCS = "__egyeb__";
const IRANY_MAGYAR = { novekszik: "Növekszik", csokken: "Csökken", stagnal: "Stagnál" };

const chart_peldanyok = {};   // szo -> Chart-példány (a destroy()-hoz, spec 8b: nem halmozódhatnak)
let megfigyelo = null;        // IntersectionObserver a lusta canvas-rajzoláshoz (mobil-görgetés, spec 6)

// tiszta string→egész órarács-index (NINCS Date a böngészőben, nincs tz-konverzió): days_from_civil
// (Howard Hinnant, egész-aritmetika) UTC-re; csak KÜLÖNBSÉGEK számítanak (rács-pozíció, lyuk-detektálás).
function napok_civil(y, m, d) {
  y -= m <= 2 ? 1 : 0;
  const era = Math.floor((y >= 0 ? y : y - 399) / 400);
  const yoe = y - era * 400;
  const doy = Math.floor((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1;
  const doe = yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy;
  return era * 146097 + doe - 719468;
}
function ora_index(iso) {   // "YYYY-MM-DDTHH:..." -> egész óra-index (UTC)
  return napok_civil(+iso.slice(0, 4), +iso.slice(5, 7), +iso.slice(8, 10)) * 24 + (+iso.slice(11, 13));
}

function tizedes2(x) { return x.toFixed(2).replace(".", ","); }   // magyar tizedesvessző
function mered_szoveg(x) { return (x < 0 ? "-" : "+") + tizedes2(Math.abs(x)); }   // explicit előjel

// mérőszám-sor (spec 7.2/8.3): irány + meredekség (egységgel) + R² (másodlagos) + fedettség.
// A se_meredekseg NEM jelenik meg (autokorreláció-torzított, mint az R², de a ± hamis szignifikanciát
// sugallna — spec 6:599, a se-döntés). NEVEZŐ = pontok_hasznalt + pontok_hianyzo (= a lezárt órarács, robusztus).
function merteszamok_szoveg(iv) {
  const nevezo = iv.pontok_hasznalt + iv.pontok_hianyzo;
  return [
    IRANY_MAGYAR[iv.irany] || iv.irany,
    mered_szoveg(iv.meredekseg_nap) + " relatív pont/nap",
    "R² = " + tizedes2(iv.r2) + " (másodlagos)",
    iv.pontok_hasznalt + "/" + nevezo + " óra (" + iv.pontok_kihagyva_reszleges + " részleges kihagyva)",
  ].join(" · ");
}

// §7.4 frissesség-felirat: NEM késésről (a nyers órás ablak a futásig ér, mint a trendlista) — két tény:
// (1) meddig tart az adat: az utolsó KIRAJZOLT LEZÁRT pont napja (B1: NEM az ablak_veg részleges slotja, ami
//     a ~00:43-futásnál másnapra esne; string-szeletelés, nincs Date);
// (2) a dátumválasztó nem hat rá + a skála szavanként saját, nem összemérhető (§1.4).
function frissesseg_szoveg(aktiv_kulcs, adat_veg) {
  const iv = INTERVALLUMOK.find(function (i) { return i.kulcs === aktiv_kulcs; });
  const cimke = iv ? iv.cimke : aktiv_kulcs;
  // a datum_formaz már záró pontot ad → NEM teszünk mögé még egyet (különben "05.. A")
  return "A kulcsszó-görbék a kiválasztott időszakot (" + cimke + ") mutatják, az adat vége: "
    + datum_formaz(adat_veg.slice(0, 10)) + " A dátumválasztó csak a napi trendekre hat, ezekre a "
    + "görbékre nem; a pontszámok szavanként külön 0–100 skálán állnak, egymással nem összemérhetők.";
}

// spec 7.2 élettartam-jelölés — HÁROM állapot szétválasztva, string-összehasonlítással (nincs Date):
// "mérés kezdete" CSAK ha a görbe a KÉSŐBBI mérési kezdet miatt rövidebb (a rajzolt ablak elején tényleges
// hiány), NEM pusztán mert van meres_kezdete (teljes rácson az első pont == az ablak kezdete → nincs felirat).
function elettartam_szoveg(szoreg, iv, ablak) {
  if (szoreg.aktiv === false) {
    return szoreg.meres_vege
      ? "már nem mérjük (utolsó mérés: " + datum_formaz(szoreg.meres_vege) + ")"
      : "már nem mérjük";
  }
  const mk = szoreg.meres_kezdete;
  if (!mk) return null;
  const ablak_kezdet_datum = iv.ablak_kezdet_utc.slice(0, 10);
  const lezart = ablak.pontok.filter(function (p) { return !p.reszleges; })
    .slice().sort(function (a, b) { return a.idopont_utc < b.idopont_utc ? -1 : 1; });
  if (!lezart.length) return null;
  const elso_datum = lezart[0].idopont_utc.slice(0, 10);
  // meres_kezdete az ablakon belülre esik ÉS előtte nincs mért pont (az első pont >= meres_kezdete)
  if (mk > ablak_kezdet_datum && elso_datum >= mk) return "mérés kezdete: " + datum_formaz(mk);
  return null;
}

// a rajzolt nyers ablak kiválasztása: a regresszió intervallumának ablak_veg_utc-jével való EGYEZÉS
// (spec 8.3/mod 8) — NEM "utolsó rekord" és NEM max(ablak_veg); egyezés hiánya → null (kirajzolhatatlan)
function nyers_ablak(szo, veg) {
  const kw = (adat["kulcsszo_nyers.json"] || {}).kulcsszavak || {};
  const ablakok = kw[szo] || [];
  for (let i = 0; i < ablakok.length; i++) {
    if (ablakok[i].ablak_veg_utc !== veg) continue;
    // J2: rajzolható CSAK ha van legalább egy LEZÁRT pont (§7.5 2. eset: üres/csupa-részleges lista
    // séma-érvényes, de nem rajzolható → data-drawable="false" + URES_NINCS_ABLAK, NEM racs_epit-kivétel)
    const van_lezart = (ablakok[i].pontok || []).some(function (p) { return !p.reszleges; });
    return van_lezart ? ablakok[i] : null;
  }
  return null;
}

// órarács a rajzoláshoz: az ELSŐ lezárt ponttól a részleges záró slotig (kizárva); a hiányzó órák
// NULL-ok (spec 7.5: nincs interpoláció, a vonal megszakad). Visszaad: labels/ertekek/vonal/szakadas/csupa_nulla.
function racs_epit(ablak, iv) {
  const pontok = ablak.pontok.slice().sort(function (a, b) { return a.idopont_utc < b.idopont_utc ? -1 : 1; });
  const lezart = pontok.filter(function (p) { return !p.reszleges; });
  const elso_idx = ora_index(lezart[0].idopont_utc);
  const veg_idx = ora_index(ablak.ablak_veg_utc);        // a részleges slot; a lezárt rács [elso_idx, veg_idx)
  const ertek_map = {}, cimke_map = {};
  lezart.forEach(function (p) { const i = ora_index(p.idopont_utc); ertek_map[i] = p.ertek; cimke_map[i] = p.idopont_utc; });
  const labels = [], ertekek = [];
  let van_nemnulla = false;
  for (let i = elso_idx; i < veg_idx; i++) {
    if (Object.prototype.hasOwnProperty.call(ertek_map, i)) {
      // J3: a label a dátumot ÉS az ÓRÁT is hordozza (a tooltip ezt mutatja); a tengely-tick csak a dátumot (chart_letrehoz)
      labels.push(datum_formaz(cimke_map[i].slice(0, 10)) + " " + cimke_map[i].slice(11, 16));
      ertekek.push(ertek_map[i]);
      if (ertek_map[i] !== 0) van_nemnulla = true;
    } else {
      labels.push("");
      ertekek.push(null);   // NULL a hiányzó óra helyén → a vonal itt megszakad (spanGaps:false)
    }
  }
  // regressziós vonal (S1 önőrző, V1): CSAK ha MINDKÉT végpont a KIRAJZOLT rácson, MÉRT sloton van
  // (ertekek[i] !== null). A guard a rajzolt [0, ertekek.length) tartományra megy, NEM az összes pontra —
  // különben egy RÉSZLEGES záró (veg, index == ertekek.length) vagy elso_idx elé eső végpont a tömbön KÍVÜLRE
  // írna (némán elcsúszó/1-pontos vonal), miközben a data-vonal="true" hazudna.
  let vonal = null, vonal_van = false;
  const v = iv.illesztes_vonal;
  if (v && v.length === 2) {
    const i0 = ora_index(v[0].idopont_utc) - elso_idx;
    const i1 = ora_index(v[1].idopont_utc) - elso_idx;
    const rajta = function (i) { return i >= 0 && i < ertekek.length && ertekek[i] !== null; };
    if (rajta(i0) && rajta(i1)) {
      vonal_van = true;
      vonal = new Array(ertekek.length).fill(null);
      vonal[i0] = v[0].ertek;
      vonal[i1] = v[1].ertek;
    }
  }
  // J1: a data-szakadas a TÉNYLEGES rajzolt datasetből derül (nem párhuzamos számláló) → egy null→0
  // interpoláló mutáció (§7.5 tiltja a nullával tömést) így PIROSÍT, nem marad láthatatlan
  // B1: az „adat vége" az utolsó KIRAJZOLT LEZÁRT pont (a lezart növekvő; az utolsó a legkésőbbi) — NEM az
  // ablak_veg_utc (részleges záró slot). A ~00:43-futásnál a kettő KÜLÖN napra esik → a felirat egyébként
  // egy nappal többet állítana, mint amennyi ki van rajzolva (ugyanaz a tautológia-osztály, mint a data-ablak-veg).
  return { labels: labels, ertekek: ertekek, vonal: vonal, vonal_van: vonal_van,
           adat_veg: lezart[lezart.length - 1].idopont_utc,
           szakadas: ertekek.filter(function (v) { return v === null; }).length,
           csupa_nulla: lezart.length > 0 && !van_nemnulla };
}

// egy kulcsszó-kártya (EAGER DOM); a canvas ELEM azonnal, a Chart.js-példány LUSTA (data-rendered).
// BINÁRIS szerződés: rajzolható → canvas + .merteszamok; nem rajzolható → .ures (mérőszám NÉLKÜL, spec 6:599).
function kartya_letrehoz(szo, szoreg, aktiv_kulcs) {
  const kartya = document.createElement("div");
  kartya.className = OSZT.kartya;
  kartya.setAttribute(ATTR.kulcsszo, szo);
  // H1: LÁTHATÓ kulcsszó-címke MINDEN kártyán (a canvas/ures FÖLÖTT), mindkét ág ELŐTT — a .ures ág korán
  // return-öl, ezért itt, a legelső gyermekként; a szó eddig csak a data-kulcsszo attribútumban volt (gépnek).
  const cimke = document.createElement("h4");
  cimke.className = OSZT.cimke;
  cimke.textContent = szo;
  kartya.appendChild(cimke);
  const iv = szoreg.intervallumok ? szoreg.intervallumok[aktiv_kulcs] : null;
  const ablak = (iv && iv.ervenyes) ? nyers_ablak(szo, iv.ablak_veg_utc) : null;

  if (!iv || !iv.ervenyes || !ablak) {
    kartya.setAttribute(ATTR.drawable, "false");
    if (iv && !iv.ervenyes && iv.ok) kartya.setAttribute(ATTR.ok, iv.ok);
    const p = document.createElement("p");
    p.className = OSZT.ures;
    p.textContent = (iv && !iv.ervenyes) ? (OK_MAGYAR[iv.ok] || iv.ok) : URES_NINCS_ABLAK;
    kartya.appendChild(p);
    return kartya;
  }

  const racs = racs_epit(ablak, iv);
  kartya.setAttribute(ATTR.drawable, "true");
  kartya.setAttribute(ATTR.ablak_veg, ablak.ablak_veg_utc);   // a kiválasztott nyers ablak KULCSA (regresszió ablak_veg_utc-vel egyező); részleges záró slot
  kartya.setAttribute(ATTR.adat_veg, racs.adat_veg);          // B1: a felirat „adat vége"-je — az utolsó KIRAJZOLT LEZÁRT pont (nem az ablak_veg)
  kartya.setAttribute(ATTR.pontok, String(iv.pontok_hasznalt));
  kartya.setAttribute(ATTR.reszleges, String(iv.pontok_kihagyva_reszleges));
  kartya.setAttribute(ATTR.hianyzo, String(iv.pontok_hianyzo));
  kartya.setAttribute(ATTR.szakadas, String(racs.szakadas));
  kartya.setAttribute(ATTR.vonal, racs.vonal_van ? "true" : "false");
  kartya.setAttribute(ATTR.ymax, "100");

  // H2b: a canvas dedikált, fix-magasságú, position:relative WRAPPERBE kerül (Chart.js kanonikus minta) —
  // a responsive+maintainAspectRatio:false a WRAPPER 100%-át tölti, így a görbe a kártya teljes belső
  // szélességét használja (a korábbi width/height !important a Chart.js méretezésével ütközött).
  const doboz = document.createElement("div");
  doboz.className = OSZT.chart_doboz;
  const canvas = document.createElement("canvas");
  doboz.appendChild(canvas);
  kartya.appendChild(doboz);

  const m = document.createElement("p");
  m.className = OSZT.merteszamok;
  m.textContent = merteszamok_szoveg(iv);
  kartya.appendChild(m);

  const tf = document.createElement("p");
  tf.className = OSZT.tengely_felirat;
  tf.textContent = TENGELY_FELIRAT;
  kartya.appendChild(tf);

  if (racs.csupa_nulla) {
    const cn = document.createElement("p");
    cn.className = OSZT.csupa_nulla;
    cn.textContent = CSUPA_NULLA_SZOVEG;
    kartya.appendChild(cn);
  }
  const et = elettartam_szoveg(szoreg, iv, ablak);
  if (et) {
    const e = document.createElement("p");
    e.className = OSZT.elettartam;
    e.textContent = et;
    kartya.appendChild(e);
  }
  kartya._racs = racs;   // a lusta Chart-példányosításhoz
  return kartya;
}

// a Chart.js-példány LUSTA létrehozása (viewportba éréskor); a régi példányt a chart_takarit destroy-olja
function chart_letrehoz(kartya) {
  if (kartya.getAttribute(ATTR.rendered) === "true") return;
  const racs = kartya._racs;
  const canvas = kartya.querySelector("canvas");
  if (!racs || !canvas || typeof Chart === "undefined") return;
  const datasetek = [{ data: racs.ertekek, spanGaps: false, borderColor: "#3366cc", borderWidth: 1.5, pointRadius: 0 }];
  if (racs.vonal) datasetek.push({ data: racs.vonal, spanGaps: true, borderColor: "#cc3333", borderWidth: 1.5, borderDash: [4, 3], pointRadius: 0 });
  chart_peldanyok[kartya.getAttribute(ATTR.kulcsszo)] = new Chart(canvas, {
    type: "line",
    data: { labels: racs.labels, datasets: datasetek },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      scales: {
        y: { min: 0, max: 100, title: { display: true, text: TENGELY_FELIRAT } },
        // J3: a tengely-TICK csak a dátumot mutatja (a záró " HH:MM"-et levágja), a TOOLTIP a teljes labelt
        // (dátum + óra) → a #9 órás felbontás a tooltipben. Canvas-belső, DOM-ból nem assertálható (ledger).
        x: { type: "category", ticks: { maxTicksLimit: 10, callback: function (v) { const l = this.getLabelForValue(v); return l ? l.replace(/\s\d{2}:\d{2}$/, "") : l; } } },
      },
      plugins: { legend: { display: false }, tooltip: { enabled: true } },   // hover-tooltip IGEN, zoom NEM (spec 8.3)
    },
  });
  kartya.setAttribute(ATTR.rendered, "true");
}

// intervallum-váltáskor/újrarajzoláskor: a régi Chart-példányokat destroy-olni KELL (spec 8b: nem
// halmozódhatnak, a tooltip ne a régi adatot mutassa) + a megfigyelőt leválasztani
function chart_takarit() {
  Object.keys(chart_peldanyok).forEach(function (k) {
    if (chart_peldanyok[k]) chart_peldanyok[k].destroy();
    delete chart_peldanyok[k];
  });
  if (megfigyelo) { megfigyelo.disconnect(); megfigyelo = null; }
}

function lusta_megfigyel(kartyak) {
  if (typeof IntersectionObserver === "undefined") {   // tartalék: rajzoljunk mindent, ha nincs IO
    kartyak.forEach(chart_letrehoz);
    return;
  }
  megfigyelo = new IntersectionObserver(function (bejegyzesek) {
    bejegyzesek.forEach(function (b) {
      if (!b.isIntersecting) return;
      chart_letrehoz(b.target);
      megfigyelo.unobserve(b.target);   // egyszer rajzolunk, aztán leválik
    });
    // rootMargin: a fold alatti ~400px-en belüli kártyát előrajzoljuk (a vezérlők + a hosszú
    // frissesség-felirat keskeny viewporton lejjebb tolják az első kártyát); a többi görgetésre jön
  }, { rootMargin: "400px" });
  kartyak.forEach(function (k) { megfigyelo.observe(k); });
}

function kulcsszo_blokk_render() {
  const blokk = document.getElementById("kulcsszo-blokk");
  if (!blokk) return;
  chart_takarit();   // váltáskor: régi példányok destroy + megfigyelő le
  blokk.querySelectorAll("." + OSZT.frissesseg + ", ." + OSZT.csoport).forEach(function (e) { e.remove(); });

  const aktiv = blokk.getAttribute(ATTR.aktiv);
  const reg = adat["kulcsszo_regresszio.json"];
  // KORAI KILÉPÉS (spec 7.4 (a)/(b)): nincs aktív intervallum → nincs chart, nincs frissesseg, NINCS kivétel
  if (!aktiv || !reg || !reg.kulcsszavak) return;

  // csoportosítás domen szerint (a frissesseg-dátumot NEM innen — lásd lent, D1)
  const csoportok = {};
  Object.keys(reg.kulcsszavak).forEach(function (szo) {
    const d = reg.kulcsszavak[szo].domen;
    const kulcs = DOMEN_MAGYAR[d] ? d : EGYEB_KULCS;
    (csoportok[kulcs] = csoportok[kulcs] || []).push(szo);
  });

  // kártyák felépítése; a frissesseg-dátum a ténylegesen RAJZOLHATÓ kártya ablakából (D1), NEM a regresszió
  // állításából — ha egy szó ervenyes:true, de nincs nyers ablaka (14./16.), NEM ad dátumot (nincs mit dátumozni).
  const rajzolhatok = [];
  let adat_veg = null;
  DOMEN_SORREND.forEach(function (d) {
    const kulcs = d === null ? EGYEB_KULCS : d;
    const szavak = csoportok[kulcs];
    if (!szavak || !szavak.length) return;
    const cs = document.createElement("div");
    cs.className = OSZT.csoport;
    cs.setAttribute("data-domen", d === null ? "egyeb" : d);
    const h3 = document.createElement("h3");
    h3.className = OSZT.fejlec;
    h3.textContent = d === null ? "Egyéb" : DOMEN_MAGYAR[d];
    cs.appendChild(h3);
    szavak.forEach(function (szo) {
      const k = kartya_letrehoz(szo, reg.kulcsszavak[szo], aktiv);
      cs.appendChild(k);
      if (k.getAttribute(ATTR.drawable) === "true") {
        rajzolhatok.push(k);
        if (!adat_veg) adat_veg = k.getAttribute(ATTR.adat_veg);   // az ELSŐ rajzolható kártya utolsó KIRAJZOLT LEZÁRT pontja (B1)
      }
    });
    blokk.appendChild(cs);
  });

  // frissesseg CSAK ha van legalább egy RAJZOLHATÓ kártya (különben — mint 15a/15b — elmarad); a h2 után
  if (adat_veg) {
    const f = document.createElement("p");
    f.className = OSZT.frissesseg;
    f.textContent = frissesseg_szoveg(aktiv, adat_veg);
    const h2 = blokk.querySelector("h2");
    if (h2) h2.insertAdjacentElement("afterend", f); else blokk.appendChild(f);
  }
  lusta_megfigyel(rajzolhatok);
}

// ── Task 7: trend-blokk — napi felkapott trendlista + kategória-eloszlás chart + kategória-szűrő ──
// Forrás: legfrissebb.json → top_trendek (a legfrissebb nap), régi napokon napok/<nap>.json → trendek.
// A dátumválasztó vezérli (a select változása → trend_nap_valt). NINCS görbe (8a) és NINCS hírblokk (L8).
// Egyetlen igazságforrás a szűréshez: #trend-blokk[data-aktiv-kategoria] (9b data-aktiv-intervallum mintája).
const OSZT_T = {
  osszefoglalo: "trend-osszefoglalo", chart_doboz: "kategoria-chart-doboz", chart: "kategoria-chart",
  magyarazat: "kategoria-magyarazat", szuro: "kategoria-szuro", gomb: "kategoria-gomb",
  gomb_other: "kategoria-gomb--other", lista: "trend-lista", kartya: "trend-kartya",
  kifejezes: "trend-kifejezes", volumen: "trend-volumen", kategoria: "trend-kategoria", ures: "ures",
};
const ATTR_T = {
  aktiv_kategoria: "data-aktiv-kategoria", nap: "data-nap", kifejezes: "data-kifejezes",
  volumen: "data-volumen", kategoriak: "data-kategoriak", kategoria_allapot: "data-kategoria-allapot",
  kategoria: "data-kategoria", count: "data-count",
};
const OTHER_CIMKE = "Other";       // a Google gyűjtő-KATEGÓRIÁJA (van szűrő-gomb, szürke, utolsó)
const EGYEB_CIMKE = "egyéb";       // a besorolás HIÁNYA ([]/hiányzó mező) — NINCS szűrő-gomb
const OSSZES_CIMKE = "Összes";
const TREND_URES_SZOVEG = "Ma nem érkezett friss felkapott trend erre a napra.";

let kategoria_chart = null;        // az eloszlás-chart SAJÁT példánya (NEM a kulcsszó chart_peldanyok/chart_takarit)
let trend_esemeny_kotve = false;   // a dátumválasztó change-kötése egyszer

// a rendezett nap-lista + a legfrissebb nap (a napok/index.json-ból)
function trend_napok() {
  const idx = adat["napok/index.json"];
  return (idx && Array.isArray(idx.napok)) ? idx.napok.slice().sort() : [];
}
function trend_legfrissebb_nap() {
  const n = trend_napok();
  return n.length ? n[n.length - 1] : null;
}

// az adott nap trendjei: legfrissebb → legfrissebb.json top_trendek; régebbi → napok/<nap>.json trendek.
// Visszaad: tömb, VAGY null (a régi nap még nincs betöltve — a trend_nap_valt tölti be és újrahív).
function trend_adat_nap(nap) {
  if (!nap || nap === trend_legfrissebb_nap()) {
    const lf = adat["legfrissebb.json"];
    return lf ? (lf.top_trendek || []) : [];
  }
  const napi = adat["napok/" + nap + ".json"];
  return napi ? (napi.trendek || []) : null;
}

// a megjelenítendő nap: a #trend-blokk data-nap-ja, vagy a dátumválasztó értéke, vagy a legfrissebb
function trend_aktualis_nap(blokk) {
  const meglevo = blokk.getAttribute(ATTR_T.nap);
  if (meglevo) return meglevo;
  const sel = document.querySelector("#datum-valaszto select");
  if (sel && sel.value) return sel.value;
  return trend_legfrissebb_nap();
}

// kategória-eloszlás: MINDEN elem MINDEN temak-kategóriájában számít (a multi többször);
// []/hiányzó NEM számít. Sorrend: valódi kategóriák count-CSÖKKENŐ (tie ábécé), majd "Other" UTOLSÓ.
function kategoria_eloszlas(trendek) {
  const szam = {};
  trendek.forEach(function (t) {
    (Array.isArray(t.temak) ? t.temak : []).forEach(function (k) { szam[k] = (szam[k] || 0) + 1; });
  });
  const kulcsok = Object.keys(szam);
  const valodi = kulcsok.filter(function (k) { return k !== OTHER_CIMKE; })
    .sort(function (a, b) { return szam[b] - szam[a] || (a < b ? -1 : 1); });
  const rend = valodi.concat(kulcsok.indexOf(OTHER_CIMKE) >= 0 ? [OTHER_CIMKE] : []);
  return rend.map(function (k) { return { kategoria: k, count: szam[k] }; });
}

function trend_szin(kategoria, tompitott) {
  if (kategoria === OTHER_CIMKE) return tompitott ? "#d4d4d4" : "#9e9e9e";   // "Other" mindig szürke
  return tompitott ? "#aec4ef" : "#3366cc";
}

function trend_chart_takarit() {
  if (kategoria_chart) { kategoria_chart.destroy(); kategoria_chart = null; }
}

function trend_chart_epit(canvas, eloszlas, blokk) {
  if (typeof Chart === "undefined") return;   // a canvas elem akkor is megvan (a szerződés DOM-oldali)
  kategoria_chart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: eloszlas.map(function (e) { return e.kategoria; }),
      datasets: [{ data: eloszlas.map(function (e) { return e.count; }),
                   backgroundColor: eloszlas.map(function (e) { return trend_szin(e.kategoria, false); }) }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      plugins: { legend: { display: false } },
      onClick: function (evt, elemek) {   // a sávra kattintás = szűrés (ugyanaz az egy forrás)
        if (elemek && elemek.length) trend_kategoria_valt(blokk, eloszlas[elemek[0].index].kategoria);
      },
    },
  });
  kategoria_chart._eloszlas = eloszlas;
}

// szűréskor a chart CSAK SZÍNEZ (aktív teli, többi tompított); a sáv-ÉRTÉKEK/count-ok VÁLTOZATLANOK
function trend_chart_szinez(aktiv) {
  if (!kategoria_chart) return;
  const el = kategoria_chart._eloszlas || [];
  kategoria_chart.data.datasets[0].backgroundColor = el.map(function (e) {
    return trend_szin(e.kategoria, aktiv !== "" && e.kategoria !== aktiv);
  });
  kategoria_chart.update();
}

function trend_gomb_epit(kategoria, cimke, count, blokk) {
  const g = document.createElement("button");
  g.className = OSZT_T.gomb + (kategoria === OTHER_CIMKE ? " " + OSZT_T.gomb_other : "");
  g.setAttribute(ATTR_T.kategoria, kategoria);
  if (count != null) g.setAttribute(ATTR_T.count, String(count));
  g.setAttribute("aria-pressed", "false");
  g.textContent = count != null ? (cimke + " (" + count + ")") : cimke;
  g.addEventListener("click", function () { trend_kategoria_valt(blokk, kategoria); });
  return g;
}

// egy trendkártya: kifejezes + volumen + kategória-címke (három állapot). NINCS görbe (8a) és hír (L8).
function trend_kartya_epit(t) {
  const k = document.createElement("div");
  k.className = OSZT_T.kartya;
  const kif = t.kifejezes || "";
  k.setAttribute(ATTR_T.kifejezes, kif);
  k.setAttribute(ATTR_T.volumen, t.volumen != null ? String(t.volumen) : "");
  // három kategória-állapot (spec:386-387): van / nincs ([]) / hianyzik (mező hiányzik) — az adatban KÜLÖNBÖZŐ
  const van_mezo = Object.prototype.hasOwnProperty.call(t, "temak");
  const temak = Array.isArray(t.temak) ? t.temak : [];
  const allapot = !van_mezo ? "hianyzik" : (temak.length === 0 ? "nincs" : "van");
  k.setAttribute(ATTR_T.kategoria_allapot, allapot);
  // JSON-tömb (NEM pipe): bármely Google-címkére biztos, verzió-független
  k.setAttribute(ATTR_T.kategoriak, JSON.stringify(allapot === "van" ? temak : []));

  const cimke = document.createElement("h4");
  cimke.className = OSZT_T.kifejezes;
  cimke.textContent = kif;
  k.appendChild(cimke);

  const vol = document.createElement("p");
  vol.className = OSZT_T.volumen;
  vol.textContent = "volumen: " + (t.volumen != null ? t.volumen : "—");
  k.appendChild(vol);

  const kat = document.createElement("p");
  kat.className = OSZT_T.kategoria;
  if (allapot === "van") {
    const szoveg = temak.join(", ");
    kat.textContent = szoveg;
    kat.setAttribute("aria-label", "Google Trends kategória: " + szoveg);   // forrás-attribúció a címkénél
    kat.setAttribute("title", "Google Trends kategória: " + szoveg);
  } else {
    kat.textContent = EGYEB_CIMKE;   // [] és hiányzó egyaránt „egyéb" a felületen
  }
  k.appendChild(kat);
  return k;
}

// szűrés (toggle): az aktív kategóriára (vagy Összesre) újra kattintva kikapcsol; különben beáll
function trend_kategoria_valt(blokk, kategoria) {
  const jelenlegi = blokk.getAttribute(ATTR_T.aktiv_kategoria) || "";
  const uj = (kategoria === "" || kategoria === jelenlegi) ? "" : kategoria;
  if (uj) blokk.setAttribute(ATTR_T.aktiv_kategoria, uj);
  else blokk.removeAttribute(ATTR_T.aktiv_kategoria);
  trend_szinkron(blokk);
}

// MINDENT a data-aktiv-kategoria-ból derivál: kártya-láthatóság, gomb aria-pressed, chart-színezés
function trend_szinkron(blokk) {
  const aktiv = blokk.getAttribute(ATTR_T.aktiv_kategoria) || "";
  blokk.querySelectorAll("." + OSZT_T.kartya).forEach(function (k) {
    let kategoriak = [];
    try { kategoriak = JSON.parse(k.getAttribute(ATTR_T.kategoriak) || "[]"); } catch (e) { kategoriak = []; }
    const lathato = !aktiv || kategoriak.indexOf(aktiv) >= 0;   // a multi-elem MINDEN kategóriájánál látszik
    if (lathato) k.removeAttribute("hidden"); else k.setAttribute("hidden", "");
  });
  blokk.querySelectorAll("." + OSZT_T.gomb).forEach(function (g) {
    const kat = g.getAttribute(ATTR_T.kategoria) || "";
    // az "Összes" gomb data-kategoria-ja "" → szűrés nélkül (aktiv="") kat===aktiv igaz rá; a második
    // tag (aktiv===""&&kat==="") REDUNDÁNS volt (ha igaz, kat===aktiv már igaz). Egyszerűsítve.
    g.setAttribute("aria-pressed", kat === aktiv ? "true" : "false");
  });
  trend_chart_szinez(aktiv);
}

// az összefoglaló (chart + magyarázat + szűrő) — CSAK kategóriás napon (van_kategoria)
function trend_osszefoglalo_epit(trendek, eloszlas, blokk) {
  const oss = document.createElement("div");
  oss.className = OSZT_T.osszefoglalo;

  const doboz = document.createElement("div");
  doboz.className = OSZT_T.chart_doboz;
  const canvas = document.createElement("canvas");
  canvas.className = OSZT_T.chart;
  doboz.appendChild(canvas);
  oss.appendChild(doboz);

  const besorolas = eloszlas.reduce(function (s, e) { return s + e.count; }, 0);
  const mag = document.createElement("p");
  mag.className = OSZT_T.magyarazat;
  mag.textContent = "A kategóriákat a Google Trends napi osztályozása adja — nem a mi besorolásunk. "
    + "Egy trend több kategóriába is tartozhat, ezért a kategóriák összege (" + besorolas + ") több lehet, "
    + "mint a megjelenített trendek száma (" + trendek.length + ").";
  oss.appendChild(mag);

  const szuro = document.createElement("div");
  szuro.className = OSZT_T.szuro;
  szuro.appendChild(trend_gomb_epit("", OSSZES_CIMKE, null, blokk));   // „Összes" reset — count nélkül
  eloszlas.forEach(function (e) { szuro.appendChild(trend_gomb_epit(e.kategoria, e.kategoria, e.count, blokk)); });
  oss.appendChild(szuro);

  trend_chart_epit(canvas, eloszlas, blokk);   // a canvas már a DOM-ban van, mire a Chart példányosít
  return oss;
}

// a trend-blokk teljes újraépítése az aktuális napra (init + minden napváltás)
function trend_blokk_render() {
  const blokk = document.getElementById("trend-blokk");
  if (!blokk) return;
  trend_esemeny_kot();

  const nap = trend_aktualis_nap(blokk);
  if (nap) blokk.setAttribute(ATTR_T.nap, nap);

  trend_chart_takarit();
  blokk.querySelectorAll("." + OSZT_T.osszefoglalo + ", ." + OSZT_T.lista + ", ." + OSZT_T.ures)
    .forEach(function (e) { e.remove(); });

  const trendek = trend_adat_nap(nap);
  if (trendek === null) return;   // a régi nap még tölt (async) — a trend_nap_valt újrahív

  if (!trendek.length) {          // §7.5 lista-szintű üres állapot
    const u = document.createElement("p");
    u.className = OSZT_T.ures;
    u.textContent = TREND_URES_SZOVEG;
    blokk.appendChild(u);
    return;
  }

  // EGY közös predikátum a teljes összefoglalóra (chart + szűrő): eloszlas.length > 0.
  // EZ EKVIVALENS a "van legalább egy elem nem-üres temak-kal" (van_kategoria) feltétellel: a
  // kategoria_eloszlas MINDEN temak-bejegyzést számol, tehát eloszlas.length > 0 ⟺ van legalább egy
  // temak-bejegyzés ⟺ van legalább egy nem-üres temak ([]/hiányzó semmit nem ad hozzá). NE bontsd szét.
  const eloszlas = kategoria_eloszlas(trendek);
  if (eloszlas.length > 0) blokk.appendChild(trend_osszefoglalo_epit(trendek, eloszlas, blokk));

  const lista = document.createElement("div");
  lista.className = OSZT_T.lista;
  trendek.forEach(function (t) { lista.appendChild(trend_kartya_epit(t)); });   // NINCS fix hossz-feltevés
  blokk.appendChild(lista);

  trend_szinkron(blokk);   // a kezdő állapot (nincs szűrés) szinkronja
}

// a dátumválasztó változása vezérli a napot (esemény-delegálás a konténeren → túléli a select újraépítését)
function trend_esemeny_kot() {
  if (trend_esemeny_kotve) return;
  const el = document.getElementById("datum-valaszto");
  if (!el) return;
  el.addEventListener("change", function (ev) {
    if (ev.target && ev.target.tagName === "SELECT") trend_nap_valt(ev.target.value);
  });
  trend_esemeny_kotve = true;
}

// napváltás: a szűrés NULLÁZÓDIK; a régi napot igény szerint betölti, majd újrarenderel
async function trend_nap_valt(nap) {
  const blokk = document.getElementById("trend-blokk");
  if (!blokk) return;
  blokk.setAttribute(ATTR_T.nap, nap);
  blokk.removeAttribute(ATTR_T.aktiv_kategoria);   // a szűrés SOHA nem éli túl a napváltást
  const rel = "napok/" + nap + ".json";
  if (nap !== trend_legfrissebb_nap() && !(rel in adat)) {
    try { adat[rel] = await nap_betolt(nap); }
    catch (e) { hiba_kiir("trend-blokk", [(e && e.message) || rel]); return; }
  }
  trend_blokk_render();
}

const RENDER_HIBA_SZOVEG = "Hiba a vezérlő megjelenítésekor";
// SORREND SZÁMÍT: az intervallum-vezérlő állítja be a data-aktiv-intervallum-ot, amit a kulcsszó-blokk
// olvas; a datum-választó a TREND-BLOKK ELŐTT fut, mert a trend-blokk a legyártott <select>-hez köti a
// napváltást. Mind szinkron fn → a microtask-sorrend = a tömb sorrendje.
const RENDEREK = [
  { id: "intervallum-vezerlo", fn: intervallum_vezerlo_render },
  { id: "kulcsszo-blokk", fn: kulcsszo_blokk_render },
  { id: "datum-valaszto", fn: datum_valaszto_render },
  { id: "trend-blokk", fn: trend_blokk_render },
];

// a renderek EGYMÁSTÓL FÜGGETLENÜL futnak (Task 5 allSettled-izoláció); a render-KIVÉTELT
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
