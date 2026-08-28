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
  { id: "kulcsszo-blokk", fajlok: ["kulcsszo_regresszio.json", "kulcsszo_nyers.json",
    "kulcsszo_masodlagos_regresszio.json", "kulcsszo_masodlagos_nyers.json",
    "kulcsszo_lanc.json"] },   // LANC-ORAS Sz2: az órás 2_het+ a láncból rajzol
  { id: "trend-blokk", fajlok: ["legfrissebb.json", "napok/index.json", "kategoriak.json"] },
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
  felbontas: "felbontas",   // item 3: a szó felbontása (óránkénti/napi/heti) minden kártyán
  intervallum_tetel: "intervallum-tetel",   // per-intervallum wrapper (oszlop): gomb-sor + magyarázat alatta
  intervallum_gomb_sor: "intervallum-gomb-sor",   // a gomb + (ha van) .ok EGY sorban
  gomb_magyarazat: "gomb-magyarazat",   // item 2: a gomb időtartam-magyarázata (mit jelent)
  teljes_forras_felirat: "teljes-forras-felirat",   // TELJES-NEZET: a kártya kimondja, honnan van adata (rács + intervallum + kezdet)
};
const ATTR = {
  aktiv: "data-aktiv-intervallum", kulcsszo: "data-kulcsszo", drawable: "data-drawable",
  ablak_veg: "data-ablak-veg", adat_veg: "data-adat-veg", pontok: "data-pontok", reszleges: "data-reszleges",
  hianyzo: "data-hianyzo", vonal: "data-vonal", szakadas: "data-szakadas",
  ymax: "data-y-max", rendered: "data-rendered", ok: "data-ok", intervallum: "data-intervallum",
  szint: "data-szint",   // 6c: esemenyjelzo szint-vonal értéke (heti medián) a kártyán
  rajzolt_pont: "data-rajzolt-pont",   // 6c javító-szelet: a RAJZOLT slotok száma (szeletelt ablak) — DOM-őr a szeletelési hibára
  felbontas: "data-felbontas",   // item 3: a kártya felbontás-rácsa (ora/nap/het) — DOM-őr
  teljes_forras: "data-teljes-forras",   // TELJES-NEZET: a per-szó választott intervallum kulcsa (het→1_ev, nap→3_ho, ora→1_het)
};
const TENGELY_FELIRAT = "relatív keresési szint (0–100)";   // EN DASH
const CSUPA_NULLA_SZOVEG = "Ezen az időszakon nincs érdemi keresési aktivitás (a mért értékek végig nulla körül).";
const URES_NINCS_ABLAK = "Az adatsor ezen az időszakon nem érhető el.";

// Szín-konstansok. A #3366cc kék KÉT KÜLÖNBÖZŐ SZEREPBEN fordul elő azonos értékkel — SZÁNDÉKOSAN külön
// konstans, hogy az egyik szerep átszínezése NE mozdítsa el némán a másikat (MIN-BC):
//  - ADAT_VONAL_SZIN: a mért ADATSOR kék vonala a vonaldiagramokban (kulcsszó-chart ÉS trend-sparkline —
//    ugyanaz a szín ugyanazért: „ez a mért adat"; testvérei a #cc3333 trend- és #e69138 szint-vonal).
//  - KATEGORIA_ALAP_SZIN: a kategória-akcentus a trend-kategória sávban (nem-tompított alap; testvérei a
//    #aec4ef tompított és a #9e9e9e/#d4d4d4 „Other" szürke — ezek MIN-BC hatókörén kívül, inline maradnak).
const ADAT_VONAL_SZIN = "#3366cc";
const KATEGORIA_ALAP_SZIN = "#3366cc";

// kulcsszó-chart tooltip közös stílusa (SZEMLE 08-19 dizájn): NINCS szín-négyzet (displayColors:false —
// egyetlen adatsornál redundáns/ronda); tiszta, tömör sötét háttér (NEM átlátszóbb — az rontaná az olvashatóságot
// a görbe fölött), lekerekített sarok; a tooltip CSAK az adatsort mutatja (filter: datasetIndex 0, nem a trend/szint-vonalat).
// A teljes-ág ezt bővíti a dátum-title callbackkel (Object.assign).
const TOOLTIP_STILUS = {
  enabled: true,
  filter: function (it) { return it.datasetIndex === 0; },
  displayColors: false,
  backgroundColor: "rgba(30, 30, 30, 0.9)",
  cornerRadius: 4,
  padding: 8,
};

// ── Task 6: vezérlők (intervallum-gombok + dátumválasztó) ────────────────────
// A gombok elérhetősége a kulcsszo_regresszio.json ervenyes mezőjéből jön (spec 7.4),
// szónkénti AGGREGÁCIÓVAL: egy intervallum engedélyezett, ha LEGALÁBB EGY szónál ervenyes.
// TASK 9b ÁTALAKÍTÁS: az aktív intervallum EGYETLEN igazságforrása a #kulcsszo-blokk
// data-aktiv-intervallum attribútuma; a gombok aria-pressed-je EBBŐL derivált (aria_szinkron).

// item 2 (2026-08-18): a gombok időtartam-magyarázata (MIT jelent) — LÁTHATÓ sub-szöveg a gomb alatt.
const GOMB_MAGYARAZAT = {
  "1_het": "mától visszafelé 1 hét",
  "2_het": "mától visszafelé 2 hét",
  "1_ho": "mától visszafelé 1 hónap",
  "3_ho": "mától visszafelé 3 hónap",
  "1_ev": "mától visszafelé 1 év",
};
const INTERVALLUMOK = [
  { kulcs: "1_het", cimke: "1 hét", hossz: 7 },
  { kulcs: "2_het", cimke: "2 hét", hossz: 14 },
  { kulcs: "1_ho", cimke: "1 hó", hossz: 30 },
  { kulcs: "3_ho", cimke: "3 hó", hossz: 90 },
  { kulcs: "1_ev", cimke: "1 év", hossz: 365 },
];
// TELJES-NEZET: ál-intervallum a fix ablakok MELLETT (NEM az INTERVALLUMOK-ban — az az aggregáció/plafon-lista).
// Per-szó a leghosszabb ÉRVÉNYES intervallumot választja (teljes_valaszt), közös dátum-tengelyre vetítve.
const TELJES_KULCS = "teljes";
const TELJES_CIMKE = "Teljes időszak";
const TELJES_MAGYARAZAT = "a gyűjtés kezdetétől máig, szavanként eltérő indulással";

// SZEMLE 08-19 (request 2): a „Kulcsszavak" cím dinamikus toldaléka az AKTÍV nézet szerint (a cím marad, mellé a nézet).
const KULCSSZO_CIM_ALAP = "Kulcsszavak";
const KULCSSZO_CIM_SUFFIX = {
  teljes: "a teljes időszakban",
  "1_het": "az elmúlt egy hétben",
  "2_het": "az elmúlt két hétben",
  "1_ho": "az elmúlt egy hónapban",
  "3_ho": "az elmúlt három hónapban",
  "1_ev": "az elmúlt egy évben",
};

// ok-kód -> LÁTHATÓ magyar magyarázat a letiltott gombhoz (spec 7.4)
const OK_MAGYAR = {
  nincs_lancolas: "Ehhez több összefűzött nap kell",
  nincs_adat: "Nincs mért adat",
  keves_pont: "Túl kevés mért pont",
  // 6b Szelet 2: rács-tudatos üres-állapot. nincs_masodlagos = a szó még nem kapott napi/heti
  // (másodlagos) futást (rotáció). 6c: az "esemenyjelzo" ok-ot az egyesitett_reg MÁR NEM ad tovább
  // (az órás esemenyjelzo 1_het a het rovid_het_ablak-ra fordul) → a "szint-nézet készül" felirat NYUGDÍJAZVA.
  // 2026-08-18: az ELVI (soha nem javul, a szó felbontása durva) vs IDŐBELI (magától feltöltődik) eset a
  // SZÖVEGBEN különüljön el (ez volt a fő félreérthetőség). A benzin/nyugdíj (órás-only) NEM kap napi/heti
  // adatot SOHA → külön ok-kód (JOGOSULATLAN-URES-UZENET feloldva), a lánc-hossz (dinamikus N) a LANC-ORAS
  // Szelet 2-vel jön (a frontend akkor olvassa a láncot) — most TÉNY, se ígéret, se szám.
  nincs_masodlagos: "Ehhez az ablakhoz még gyűlik a napi/heti adat. Magától feltöltődik.",   // IDŐBELI
  oras_lanc_kell: "Órás felbontású szó – ehhez az ablakhoz az órás sorozat láncolása kell.",  // órás-only (benzin/nyugdíj)
  rovid_masodlagos: "A napi/heti sorozat még rövidebb ennél az ablaknál. Magától feltöltődik.",  // IDŐBELI
  rovid_het_ablak: "Heti felbontású szó – ez az ablak túl rövid a heti rácshoz. Ez nem fog feltöltődni.",  // ELVI
  rovid_span: "Túl rövid mért időszak",
  degeneralt: "Nem illeszthető",
  // TELJES-NEZET: egy szónak EGY érvényes intervalluma sincs (sem órás, sem másodlagos) → külön ok-kód,
  // NEM mosódik a fenti fix-intervallum kódokkal (a user kérése: új hiba tudható legyen).
  teljes_nincs_sorozat: "Ehhez a szóhoz még nincs rajzolható sorozat a teljes nézetben.",
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

// 6b Szelet 2: az órás + másodlagos regresszió EGYESÍTÉSE per (szó, intervallum). A meglévő
// renderelők (intervallum_vezerlo_render, kulcsszo_blokk_render) ezt fogyasztják, nem a nyers órás fájlt.
//   órás[X].ervenyes → órás (racs "ora"); különben másodlagos[X].ervenyes → másodlagos (a szó racs-a);
//   különben üres, az ELSŐDLEGES forrás ok-jával (hosszú X → másodlagos ok / nincs_masodlagos; 1_het → órás).
// A _racs/_forras az iv-en (per-INTERVALLUM), mert egy szó 1_het-je órás, 1_ho-ja másodlagos lehet.
// (Az órás ág _racs MINDIG "ora": a drawn órás intervallum az órás rácson rajzol, függetlenül a szó config-
//  rácsától [o.racs]. Az o.racs [config-rács, 2026-08-18 óta a regresszióban] a felbontás-felirathoz/benzin-eset.)
function egyesitett_reg() {
  const oras = adat["kulcsszo_regresszio.json"];
  if (!oras || !oras.kulcsszavak) return oras || null;
  const mpk = (adat["kulcsszo_masodlagos_regresszio.json"] || {}).kulcsszavak || {};
  const ki = {};
  Object.keys(oras.kulcsszavak).forEach(function (szo) {
    const o = oras.kulcsszavak[szo];
    const m = mpk[szo];
    const ivk = {};
    INTERVALLUMOK.forEach(function (it) {
      const X = it.kulcs;
      const oiv = o.intervallumok && o.intervallumok[X];
      const miv = m && m.intervallumok && m.intervallumok[X];
      if (oiv && oiv.ervenyes) {
        // SZEMLE-FIX (08-19): a PRIMER (órás) ág _racs-a MINDIG "ora" — a primer 1_het a `now 7-d` órás ablak
        // (168 pont) MINDEN szónál, függetlenül a config-rácstól. A korábbi `o.racs` a config-rácsot (nap/het)
        // tette az órás intervallumra → a 168 órás pont nap/het-slotra collapse-olt (7/1 pont) ÉS félrecímkézte
        // („nap nem-nulla"), sőt a záró-óra-nulla miatt téves `csupa_nulla`-t okozott (hitel/napelem lapos-nulla).
        // A config-rács (o.racs) KIZÁRÓLAG a MÁSODLAGOS ágra vonatkozik (lásd lentebb, m.racs). Az órás-only szó
        // (benzin/nyugdíj) változatlan (eddig is "ora"). A kártya-Felbontás/„óra nem-nulla" felirat ezt olvassa.
        // LANC-ORAS Sz2: az órás 1_het a nyers 7-napos ablakból, a HOSSZABB (2_het+) a LÁNCBÓL (kulcsszo_lanc.json)
        // rajzol. Rács-csatolt feltevés: RACS_ABLAK_NAP["ora"]==7 → csak az 1_het fér a nyers ablakba; minden
        // hosszabb érvényes órás intervallum a láncból szeletelt (regresszio._intervallumok). A forrás-választás
        // FRONTEND-oldali (nem új backend mező) — az ERVENYES-ROUTING felület nem nő.
        const _forras = (X === "1_het") ? "kulcsszo_nyers.json" : "kulcsszo_lanc.json";
        ivk[X] = Object.assign({}, oiv, { _racs: "ora", _forras: _forras });
      } else if (miv && miv.ervenyes) {
        // 3b: a masodlagos intervallum a PER-INTERVALLUM rácsán rajzol (miv.racs; a backend adja: 1_ev→het,
        // 3_ho→nap), NEM a szó-config rácsán (m.racs). Enélkül egy nap-config szó het-forrású 1_ev-je NAPI
        // slotra szóródna (6 null/heti pont → láthatatlan görbe). Szó-szintű fallback, ha nincs per-interval racs.
        ivk[X] = Object.assign({}, miv, { _racs: miv.racs || m.racs, _forras: "kulcsszo_masodlagos_nyers.json" });
      } else {
        // ÜRES: rács-tudatos ok. A hosszú intervallum SOHA nem "nincs_lancolas" (órás-láncolás, §8.2 szerint
        // a nap/het ágon irreleváns) — a másodlagos MAGA is adhat nincs_lancolas-t (a sorozat rövidebb az
        // ablaknál), ezt LEFORDÍTJUK, nem engedjük át nyersen.
        let ok;
        if (X === "1_het" && !(oiv && oiv.ok === "esemenyjelzo")) {
          ok = oiv ? oiv.ok : "nincs_adat";                          // 1_het = az órás ok — KIVÉVE esemenyjelzo
        } else if (!miv) {                                           // (6c: az órás esemenyjelzo 1_het a het-ágra fordul → rovid_het_ablak)
          // órás-only szó (benzin/nyugdíj, racs="ora") SOHA nem kap napi/heti adatot → a hosszú ablakhoz az órás
          // LÁNC kell (oras_lanc_kell); a nap/het szó a rotációból még nem kapott → nincs_masodlagos (IDŐBELI).
          ok = (o.racs === "ora") ? "oras_lanc_kell" : "nincs_masodlagos";
        } else if (miv.ok === "nincs_lancolas") {
          ok = "rovid_masodlagos";                                   // van másodlagos, de a sorozat rövidebb az ablaknál (nem órás-láncolás)
        } else if (miv.ok === "keves_pont" && m.racs === "het") {
          ok = "rovid_het_ablak";                                    // heti rácson a rövid ablak strukturálisan kevés pont, nem adathiány
        } else {
          ok = miv.ok;                                               // keves_pont (nap), esemenyjelzo — már rács-megfelelő
        }
        ivk[X] = { ervenyes: false, ok: ok };
      }
    });
    // 6c: az esemenyjelzo szint (heti medián) a MÁSODLAGOS entryn él (m), az órás o-n nincs → átvezetjük,
    // hogy a kártya-render (merteszamok_szoveg / szint-vonal / data-szint) elérje. Nem-esemenyjelzo: undefined.
    const tobb = (m && m.szint != null)
      ? { szint: m.szint, szint_modszer: m.szint_modszer,
          mai_szint: m.mai_szint, mai_elteres: m.mai_elteres,
          szint_szokasos: m.szint_szokasos, illeszkedes_szint: m.illeszkedes }
      : null;
    ki[szo] = Object.assign({}, o, { intervallumok: ivk }, tobb || {});
  });
  return { kulcsszavak: ki };
}

// TELJES-NEZET: a szó egyesített intervallumai közül a LEGHOSSZABB ÉRVÉNYES = a legkorábbi ablak_kezdet_utc
// (het→1_ev, nap→3_ho, ora→1_het) → { kulcs, iv }, vagy null ha egy sincs érvényes. Itt dől el a per-szó vágás.
function teljes_valaszt(szoreg) {
  const ivk = szoreg.intervallumok || {};
  let best = null;
  INTERVALLUMOK.forEach(function (it) {
    const iv = ivk[it.kulcs];
    if (!iv || !iv.ervenyes || !iv.ablak_kezdet_utc) return;
    if (!best || iv.ablak_kezdet_utc < best.iv.ablak_kezdet_utc) best = { kulcs: it.kulcs, iv: iv };
  });
  return best;
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
  const reg = egyesitett_reg();
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
  // Szelet 3 / ALAPNEZET: a default a legtöbb kártyát rajzoló intervallum = 1_het (13/13 órás), NEM a
  // leghosszabb érvényes. A spec 7.2 „magától tolódik kifelé" feltevése (érvényesség monoton nő ÉS a
  // leghosszabb = minden-szó-érvényes) a másodlagossal MEGTÖRT (1_ev: 1/13 rajzol). 1_het hiányában a
  // leghosszabb érvényesre esünk vissza. A hosszabb nézetek kattintásra maradnak.
  const kivalasztott = ervenyesek.length
    ? (ervenyesek.find(function (a) { return a.kulcs === "1_het"; })
       || ervenyesek.reduce(function (a, b) { return b.hossz > a.hossz ? b : a; }))
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
    // ALAPNEZET (SZEMLE 08-19, request 1): a kezdő nézet a TELJES időszak (közös tengely) — az oldal ezzel nyílik.
    // A teljes elérhető, ha van érvényes intervallum (kivalasztott != null). A fix intervallumok kattintásra jönnek.
    // (A korábbi 1_het-default megszűnt; az ALAPNEZET-KONSTANS tétel ezzel lezárul.)
    blokk.setAttribute(ATTR.aktiv, TELJES_KULCS);
  }
  // TELJES-NEZET (request 1): a "Teljes időszak" ál-gomb a lista TETEJÉN (a fix intervallumok ELŐTT); elérhető,
  // ha ≥1 intervallum érvényes (bármely szónál) — a per-szó választást a kártya-render dönti el (teljes_valaszt).
  if (ervenyesek.length) {
    const tetel = document.createElement("div");
    tetel.className = OSZT.intervallum_tetel;
    const sor = document.createElement("div");
    sor.className = OSZT.intervallum_gomb_sor;
    const gomb = document.createElement("button");
    gomb.setAttribute(ATTR.intervallum, TELJES_KULCS);
    gomb.textContent = TELJES_CIMKE;
    gomb.setAttribute("aria-pressed", "false");   // a tényleges értéket az aria_szinkron állítja be
    gomb.addEventListener("click", function () { aktiv_intervallum_valt(TELJES_KULCS); });
    sor.appendChild(gomb);
    tetel.appendChild(sor);
    const magy = document.createElement("div");
    magy.className = OSZT.gomb_magyarazat;
    magy.textContent = TELJES_MAGYARAZAT;
    tetel.appendChild(magy);
    el.appendChild(tetel);
  }
  allapotok.forEach(function (a) {
    // per-intervallum wrapper: a gomb és a saját ok-szövege EGY sorban maradjon, az intervallumok EGYMÁS ALATT
    // (a CSS a konténert flex-column-ra, a tételt flex-row-ra teszi). A meglévő szelektorok LESZÁRMAZOTTAK
    // (#intervallum-vezerlo button / .ok / .ures) → a wrapper nem töri őket.
    const tetel = document.createElement("div");
    tetel.className = OSZT.intervallum_tetel;
    const sor = document.createElement("div");   // a gomb + (ha van) .ok EGY sorban; a magyarázat ez ALATT
    sor.className = OSZT.intervallum_gomb_sor;
    const gomb = document.createElement("button");
    gomb.setAttribute(ATTR.intervallum, a.kulcs);
    gomb.textContent = a.cimke;
    if (a.ervenyes) {
      gomb.setAttribute("aria-pressed", "false");        // a tényleges értéket az aria_szinkron állítja be
      gomb.addEventListener("click", function () { aktiv_intervallum_valt(a.kulcs); });
      sor.appendChild(gomb);   // ÉRVÉNYES: CSAK a gomb — SZÁNDÉKOSAN NINCS üres .ok span (a .ok-szám szemantikája marad)
    } else {
      gomb.disabled = true;
      sor.appendChild(gomb);
      const ok = document.createElement("span"); // LÁTHATÓ magyar ok a gomb mellé (nem csak title)
      ok.className = "ok";
      ok.textContent = OK_MAGYAR[a.ok] || a.ok;
      sor.appendChild(ok);
    }
    tetel.appendChild(sor);
    // item 2 (2026-08-18): a gomb időtartam-magyarázata (MIT jelent) — LÁTHATÓ sub-szöveg a gomb alatt (nem tooltip)
    const magy = document.createElement("div");
    magy.className = OSZT.gomb_magyarazat;
    magy.textContent = GOMB_MAGYARAZAT[a.kulcs] || "";
    tetel.appendChild(magy);
    el.appendChild(tetel);
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

// ── naptár nap-választó (a select helyett; a böngészőben TILOS a Date → tiszta egész-aritmetika) ──
const NAPTAR_HETNAPOK = ["H", "K", "Sz", "Cs", "P", "Sz", "V"];   // hétfő-kezdő fejsor
const NAPTAR_HONAPOK = ["január", "február", "március", "április", "május", "június",
  "július", "augusztus", "szeptember", "október", "november", "december"];
function naptar_szoko(y) { return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0; }
function naptar_honap_napjai(y, m) {   // m: 1..12
  return [31, naptar_szoko(y) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
}
function naptar_hetnap_hetfo0(y, m, d) {   // Sakamoto → 0=vasárnap; hétfő-kezdőre: (dow+6)%7
  const t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4];
  const yy = m < 3 ? y - 1 : y;
  const dow = (yy + Math.floor(yy / 4) - Math.floor(yy / 100) + Math.floor(yy / 400) + t[m - 1] + d) % 7;
  return (dow + 6) % 7;   // 0=hétfő .. 6=vasárnap
}
function naptar_honap_lep(kulcs, delta) {   // "2026-08" ± delta hónap
  let y = +kulcs.slice(0, 4), m = +kulcs.slice(5, 7) + delta;
  while (m > 12) { m -= 12; y += 1; }
  while (m < 1) { m += 12; y -= 1; }
  return y + "-" + String(m).padStart(2, "0");
}

// KÖZÖS naptár-rács (napi ÉS heti választó): fej (‹ cím ›) + hét-fejsor + 6×7 nap-cella. A `cellaAllapot(iso, szomszed)`
// dönt cellánként: { valaszthato: bool, extraOsztaly: string, aria: string|null }. A kattintást a hívó a konténeren
// delegálja (a nap-cella `data-nap`-jából). Visszaad: a naptár <div> (a hívó teszi a #datum-valaszto / #heti-valaszto-ba).
function naptar_epit(honap, elso_ho, utolso_ho, cellaAllapot) {
  const naptar = document.createElement("div");
  naptar.className = "naptar";
  const fej = document.createElement("div");
  fej.className = "naptar-fej";
  const vissza = document.createElement("button");
  vissza.type = "button"; vissza.className = "honap-lep vissza"; vissza.textContent = "‹";
  vissza.setAttribute("aria-label", "Előző hónap");
  if (honap <= elso_ho) vissza.disabled = true;
  const cim = document.createElement("span");
  cim.className = "naptar-cim";
  const hy = +honap.slice(0, 4), hm = +honap.slice(5, 7);
  cim.textContent = hy + ". " + NAPTAR_HONAPOK[hm - 1];
  const elore = document.createElement("button");
  elore.type = "button"; elore.className = "honap-lep elore"; elore.textContent = "›";
  elore.setAttribute("aria-label", "Következő hónap");
  if (honap >= utolso_ho) elore.disabled = true;
  fej.appendChild(vissza); fej.appendChild(cim); fej.appendChild(elore);
  naptar.appendChild(fej);

  const racs = document.createElement("div");
  racs.className = "naptar-racs";
  NAPTAR_HETNAPOK.forEach(function (hn) {
    const f = document.createElement("span"); f.className = "naptar-fejnap"; f.textContent = hn;
    racs.appendChild(f);
  });
  const napok_szama = naptar_honap_napjai(hy, hm);
  const elso_hetnap = naptar_hetnap_hetfo0(hy, hm, 1);   // 0=hétfő
  const elozo_ho = naptar_honap_lep(honap, -1);
  const kov_ho = naptar_honap_lep(honap, 1);
  const elozo_napjai = naptar_honap_napjai(+elozo_ho.slice(0, 4), +elozo_ho.slice(5, 7));
  for (let i = 0; i < 42; i++) {   // 6 sor × 7 nap (fix magasság; a szomszéd-hónap napjai szürkék)
    const napszam = i - elso_hetnap + 1;   // 1-alapú a megjelenített hónapban
    let iso, szam, szomszed = false;
    if (napszam < 1) { szam = elozo_napjai + napszam; iso = elozo_ho + "-" + String(szam).padStart(2, "0"); szomszed = true; }
    else if (napszam > napok_szama) { szam = napszam - napok_szama; iso = kov_ho + "-" + String(szam).padStart(2, "0"); szomszed = true; }
    else { szam = napszam; iso = honap + "-" + String(szam).padStart(2, "0"); }
    const st = cellaAllapot(iso, szomszed);
    const cella = document.createElement("button");
    cella.type = "button";
    cella.className = "nap-cella" + (szomszed ? " szomszed-honap" : "") +
      (st.valaszthato ? "" : " nem-valaszthato") + (st.extraOsztaly ? " " + st.extraOsztaly : "");
    cella.textContent = String(szam);
    cella.setAttribute("data-nap", iso);
    if (!st.valaszthato) cella.disabled = true;                // nem-választható → letiltva
    if (st.aria) cella.setAttribute("aria-current", st.aria);
    racs.appendChild(cella);
  }
  naptar.appendChild(racs);
  return naptar;
}

function datum_valaszto_render() {
  const el = document.getElementById("datum-valaszto");
  if (!el) return;
  const idx = adat["napok/index.json"];
  const napok = (idx && Array.isArray(idx.napok)) ? idx.napok.slice().sort() : [];
  if (!napok.length) { ures_allapot(el, "Nincs elérhető nap."); return; }
  const legfrissebb = napok[napok.length - 1];
  const elerheto = {};
  napok.forEach(function (n) { elerheto[n] = true; });
  const elso_ho = napok[0].slice(0, 7);        // a tartomány első hónapja ("2026-07")
  const utolso_ho = legfrissebb.slice(0, 7);   // a tartomány utolsó hónapja
  // állapot: a kiválasztott nap (alap = legfrissebb) + a megjelenített hónap (alap = a kiválasztott hónapja)
  let valasztott = el.getAttribute("data-valasztott-nap");
  if (!valasztott || !elerheto[valasztott]) valasztott = legfrissebb;
  let honap = el.getAttribute("data-honap") || valasztott.slice(0, 7);
  if (honap < elso_ho) honap = elso_ho;
  if (honap > utolso_ho) honap = utolso_ho;
  el.setAttribute("data-valasztott-nap", valasztott);
  el.setAttribute("data-honap", honap);
  el.textContent = "";
  el.appendChild(naptar_epit(honap, elso_ho, utolso_ho, function (iso, szomszed) {
    const vanAdat = !szomszed && !!elerheto[iso];
    return { valaszthato: vanAdat, extraOsztaly: iso === valasztott ? "valasztott" : "", aria: iso === valasztott ? "date" : null };
  }));
}

// HETI naptár (hét-kiemelő): a kiválasztott hét MIND a 7 cellája kiemelve; kattintás → az adott hét.
function heti_valaszto_render() {
  const el = document.getElementById("heti-valaszto");
  if (!el) return;
  const idx = adat["napok/index.json"];
  const napok = (idx && Array.isArray(idx.napok)) ? idx.napok.slice().sort() : [];
  if (!napok.length) { el.textContent = ""; return; }   // az üres állapotot a heti_blokk_render kezeli
  const legfrissebb = napok[napok.length - 1];
  const adatHetek = {};                                  // a data-hét-hétfők (amelyik héten van adat)
  napok.forEach(function (n) { adatHetek[het_hetfoje(n)] = true; });
  const legfrissebbHet = het_hetfoje(legfrissebb);
  const elso_ho = napok[0].slice(0, 7), utolso_ho = legfrissebb.slice(0, 7);
  let valasztottHet = el.getAttribute("data-valasztott-het");
  if (!valasztottHet || !adatHetek[valasztottHet]) valasztottHet = legfrissebbHet;
  let honap = el.getAttribute("data-honap") || valasztottHet.slice(0, 7);
  if (honap < elso_ho) honap = elso_ho;
  if (honap > utolso_ho) honap = utolso_ho;
  el.setAttribute("data-valasztott-het", valasztottHet);
  el.setAttribute("data-honap", honap);
  el.textContent = "";
  el.appendChild(naptar_epit(honap, elso_ho, utolso_ho, function (iso, szomszed) {
    const hetfo = het_hetfoje(iso);
    const hetVanAdat = !!adatHetek[hetfo];
    return {
      valaszthato: !szomszed && hetVanAdat,                     // csak nem-szomszéd, adat-hét kattintható
      extraOsztaly: hetfo === valasztottHet ? "valasztott-het" : "",   // a HÉT egész sora kiemelve (szomszéd is)
      aria: null,
    };
  }));
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
const IRANY_MAGYAR = { novekszik: "iránya növekvő", csokken: "iránya csökkenő", stagnal: "iránya stagnáló" };
// ÁTTEKINTŐ: a chip a MAI ELTÉRÉST mutatja a szó saját trendjéhez (nem a trend irányát): a backend 3-állapotú
// `illeszkedes`-e — felette (▲, ma a trend fölé ugrott) / alatta (▼, a trend alá esett) / illeszkedik (✓, sávban).
const ELTERES_SZOVEG = {
  felette: "ma a szokásosnál magasabb – a trendje fölé ugrott",
  alatta: "ma a szokásosnál alacsonyabb – a trendje alá esett",
  illeszkedik: "ma a szokásos sávban – illeszkedik a trendjéhez",
};
const ELTERES_SZINT_SZOVEG = {   // esemenyjelzo (tüntetés): a MEDIÁNHOZ mérve (nincs trend)
  felette: "ma a megszokottnál magasabb – a medián fölött",
  alatta: "ma a megszokottnál alacsonyabb – a medián alatt",
  illeszkedik: "ma a megszokott szint körül – a medián közelében",
};
// TREND-panel: a szó KERESETTSÉGÉNEK IRÁNYA az elmúlt időszakban (a trendvonal meredeksége, backend `irany`).
// esemenyjelzo (tüntetés) → nincs trend ("esemeny"): a szintjét az 52 hetes mediánhoz mérjük.
const TREND_SZOVEG = {
  novekszik: "a trendje növekvő – az elmúlt időszakban emelkedik a keresettsége",
  csokken: "a trendje csökkenő – az elmúlt időszakban esik a keresettsége",
  stagnal: "a trendje stagnáló – nagyjából egy szinten mozog",
  esemeny: "esemény-jellegű szó – nincs trendje; a szintjét az elmúlt 52 hét mediánjához mérjük",
};
const TREND_SZIN = { novekszik: "#2e7d32", csokken: "#b23c3c", stagnal: "#777", esemeny: "#777" };
// az áttekintő eltérés-ikonok színei (megegyeznek az app.css ::before színeivel) — a magyarázat glyph-jei is EZEKKEL.
// felette ▲ ZÖLD (a szokásos fölé), alatta ▼ PIROS (alá), illeszkedik • SZÜRKE (semleges: követi a trendet)
const ATTEKINTO_SZIN = { felette: "#2e7d32", alatta: "#b23c3c", illeszkedik: "#777" };
// egy SZÍNES, nem-dőlt glyph a magyarázatba (a doboz dőlt-szürke; a glyph kiemelt színnel, egyenesen)
function attekinto_glif(ch, szin) {
  const s = document.createElement("span");
  s.textContent = ch;
  s.style.color = szin;
  s.style.fontStyle = "normal";
  return s;
}
// a magyarázat-doboz (a panel ALJÁN), a MÓD szerint: sima nyelvű leírás + SZÍNES ikon-legenda
function attekinto_magyarazat_epit(mod) {
  const p = document.createElement("p");
  p.className = "attekinto-magyarazat";
  const t = function (s) { p.appendChild(document.createTextNode(s)); };
  if (mod === "trend") {
    t("A szó keresettségének iránya a teljes megjelenített időszakban – a trendvonal (regressziós egyenes) meredeksége. ");
    p.appendChild(attekinto_glif("▲", TREND_SZIN.novekszik)); t(" növekvő (emelkedik) · ");
    p.appendChild(attekinto_glif("▼", TREND_SZIN.csokken));   t(" csökkenő (esik) · ");
    p.appendChild(attekinto_glif("■", TREND_SZIN.stagnal));   t(" stagnáló (nagyjából egy szinten). A tüntetés esemény-jellegű – nincs trendje, ott a szintet az elmúlt 52 hét mediánjához mérjük (");
    p.appendChild(attekinto_glif("■", TREND_SZIN.esemeny));   t(" szürke).");
    return p;
  }
  t("Azt mutatja, egy szó keresettsége ma eltért-e a saját szokásos mintázatától – és merre. ");
  p.appendChild(attekinto_glif("▲", ATTEKINTO_SZIN.felette)); t(" a szokásosnál magasabb (ma a trendje fölé ugrott) · ");
  p.appendChild(attekinto_glif("▼", ATTEKINTO_SZIN.alatta));  t(" a szokásosnál alacsonyabb (a trendje alá esett) · ");
  p.appendChild(attekinto_glif("•", ATTEKINTO_SZIN.illeszkedik)); t(" a szokásos sávban maradt (követi a trendjét). A viszonyítás a teljes megjelenített időszak trendvonalához történik; a „szokásos” sávot ennek az időszaknak az ingadozásából számoljuk (a trendvonaltól való eltérések tipikus, medián nagysága). A tüntetésnél nincs trend – ott a mai értéket az elmúlt 52 hét mediánjához mérjük.");
  return p;
}
// RACS_EGYSEG (6b első szelet): a jel-erősség feliratban a rács-SZÓ (óra/nap/hét). A mértékegység
// ("relatív pont/nap") rács-INVARIÁNS (mindkét JSON meredekseg_egyseg-e per-nap), NEM itt dől el.
// Az órás JSON nem hordoz racs-ot → default "ora" → az órás felirat bájt-azonos. Ismeretlen rács
// (config-elgépelés / jövőbeli negyedik rács) → LÁTHATÓ "? <érték>", NEM undefined, NEM néma "óra".
const RACS_SZO = { ora: "óra", nap: "nap", het: "hét" };
// item 3 (2026-08-18): a KÁRTYA-felirat felbontás-szava (a jel-erősség rács-szavától eltérő, olvasóbarát alak).
const FELBONTAS_SZO = { ora: "óránkénti", nap: "napi", het: "heti" };
function felbontas_szo(racs) {
  return FELBONTAS_SZO[racs] || ("? " + racs);   // ismeretlen rács → LÁTHATÓ, nem néma default
}
function racs_szo(racs) {
  const r = racs || "ora";
  return RACS_SZO[r] || ("? " + r);
}

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
// rács-tudatos slot-index (6b rajzolás Szelet 1): óra = az ora_index KARAKTERRE (nap*24 + óra),
// nap = nap-index, het = floor(nap-index/7). A nap/het pont 00:00:00-kor van; a het floor-ja
// fázis-invariáns a pontosan 7-naponkénti pontokra (mérve: 53 pont → 53 distinct slot, 0 collision).
function slot_index(iso, racs) {
  const nap = napok_civil(+iso.slice(0, 4), +iso.slice(5, 7), +iso.slice(8, 10));
  if (racs === "nap") return nap;
  if (racs === "het") return Math.floor(nap / 7);
  return nap * 24 + (+iso.slice(11, 13));   // "ora" / default — az ora_index-szel azonos
}

// ── TELJES-NEZET (Szelet 2): a közös LINEÁRIS dátum-tengelyhez epoch-ms Date NÉLKÜL (tz-biztos egész-aritm.) ──
// A vendor Chart.js-ben NINCS idő-adapter → type:"time" dobna; ezért numerikus x (ms) + tick/tooltip callback.
function iso_ms(iso) {   // "YYYY-MM-DDTHH:..." → epoch-ms (UTC); nap/het pont 00:00 → óra-rész 0
  return napok_civil(+iso.slice(0, 4), +iso.slice(5, 7), +iso.slice(8, 10)) * 86400000 + (+iso.slice(11, 13) || 0) * 3600000;
}
function slot_ms(i, racs) {   // slot-index → ms (a hiányzó slotok null-pontjának x-e; a rajzolt pontok iso_ms-t kapnak)
  if (racs === "nap") return i * 86400000;
  if (racs === "het") return i * 7 * 86400000;
  return i * 3600000;   // ora: az ora_index * óra-ms
}
// days_from_civil INVERZE (Howard Hinnant) — ms → { y, m, d }, Date/tz nélkül; a tengely-tick/tooltip dátumához
function civil_datum(ms) {
  let z = Math.floor(ms / 86400000) + 719468;
  const era = Math.floor((z >= 0 ? z : z - 146096) / 146097);
  const doe = z - era * 146097;
  const yoe = Math.floor((doe - Math.floor(doe / 1460) + Math.floor(doe / 36524) - Math.floor(doe / 146096)) / 365);
  const y = yoe + era * 400;
  const doy = doe - (365 * yoe + Math.floor(yoe / 4) - Math.floor(yoe / 100));
  const mp = Math.floor((5 * doy + 2) / 153);
  const d = doy - Math.floor((153 * mp + 2) / 5) + 1;
  const m = mp < 10 ? mp + 3 : mp - 9;
  return { y: m <= 2 ? y + 1 : y, m: m, d: d };
}
function ket(n) { return n < 10 ? "0" + n : "" + n; }
function ms_datum(ms, teljes_datum) {   // tick: "2025. 08."; tooltip (teljes_datum): "2025. 08. 10."
  const c = civil_datum(ms);
  return c.y + ". " + ket(c.m) + "." + (teljes_datum ? " " + ket(c.d) + "." : "");
}

function tizedes2(x) { return x.toFixed(2).replace(".", ","); }   // magyar tizedesvessző
function mered_szoveg(x) { return (x < 0 ? "-" : "+") + tizedes2(Math.abs(x)); }   // explicit előjel

// mérőszám-sor (spec 7.2/8.3): irány LEÍRÓ tendencia + meredekség (egységgel) + R² önmagyarázó legenda + a jel erőssége.
// A hamis tekintély forrása a verdikt-erejű irányszó volt (§10, MÉRT R²=0,00–0,30) → "iránya csökkenő" nem "Csökken";
// az R² legendája a SKÁLÁT írja le, nem ítéli meg az adott értéket (nincs küszöb → nincs tristate).
// A záró elem a NEM-NULLA számmal ELÖL (§8.3): "N/M óra nem-nulla (M/nevezo lezárt, K részleges kihagyva)" —
// az első szám a jel erőssége (pontok_nem_nulla/lezárt), nem a puszta fedettség; a régi "M/M óra" teljes mérést sugallt.
// A se_meredekseg NEM jelenik meg (autokorreláció-torzított, mint az R², de a ± hamis szignifikanciát
// sugallna — spec 6:599, a se-döntés). NEVEZŐ = pontok_hasznalt + pontok_hianyzo (= a lezárt órarács, robusztus).
function merteszamok_szoveg(iv, racs, szint) {
  const nevezo = iv.pontok_hasznalt + iv.pontok_hianyzo;
  const jelerosseg = iv.pontok_nem_nulla + "/" + iv.pontok_hasznalt + " " + racs_szo(racs) + " nem-nulla (" + iv.pontok_hasznalt + "/" + nevezo + " lezárt, " + iv.pontok_kihagyva_reszleges + " részleges kihagyva)";
  if (szint != null) {
    // 6c esemenyjelzo (pl. tüntetés): NINCS irány/meredekség/R² (a backend strippeli) → a mérőszám-sor a
    // SZINT-nézet. A rács ("heti") ÉS a bázis ("52 hét") KIMONDVA: a szint a szó-szintű 52 hetes heti medián,
    // MINDEN rajzoló nézeten UGYANEZ (a 3_ho-n is — nem a 13 hetes ablaké), (a) döntés. + a jel erőssége.
    return "szint: " + szint_formaz(szint) + " (heti medián, 52 hét) · " + jelerosseg;
  }
  return [
    IRANY_MAGYAR[iv.irany] || iv.irany,
    mered_szoveg(iv.meredekseg_nap) + " relatív pont/nap",
    "R² = " + tizedes2(iv.r2) + " (illeszkedés-jóság 0–1; a magasabb érték erősebb irányt jelent)",
    jelerosseg,
  ].join(" · ");
}

// a szint magyar megjelenítése: egész → "8"; tört → "8,5" (a data-szint attribútum a String(szint), gépnek)
function szint_formaz(x) { return Number.isInteger(x) ? String(x) : String(x).replace(".", ","); }

// §7.4 frissesség-felirat: NEM késésről (a nyers órás ablak a futásig ér, mint a trendlista) — két tény:
// (1) meddig tart az adat: az utolsó KIRAJZOLT LEZÁRT pont napja (B1: NEM az ablak_veg részleges slotja, ami
//     a ~00:43-futásnál másnapra esne; string-szeletelés, nincs Date);
// (2) a skála szavanként saját, nem összemérhető (§1.4). A "dátumválasztó nem hat rá" tagmondat KIKERÜLT:
//     a §7.1 per-szekció elrendezés (a vezérlő a vezérelt szekció mellett) magától közli.
function frissesseg_szoveg(aktiv_kulcs, adat_veg) {
  if (aktiv_kulcs === TELJES_KULCS) {
    // TELJES-NEZET (per-szó tengely): minden szó a SAJÁT időszakát mutatja a saját adatán, ezért a fejléc NEM
    // mond egyetlen dátumot (szavanként eltér — az adat idősávja a kártya forrás-feliratán van). §1.4 MARAD.
    return "Teljes időszak – szavanként eltérő időszak, mindegyik a saját adatán. "
      + "A pontszámok szavanként külön 0–100 skálán állnak, egymással nem összemérhetők.";
  }
  const iv = INTERVALLUMOK.find(function (i) { return i.kulcs === aktiv_kulcs; });
  const cimke = iv ? iv.cimke : aktiv_kulcs;
  // a datum_formaz már záró pontot ad → NEM teszünk mögé még egyet (különben "05.. A")
  return "A kulcsszó-görbék a kiválasztott időszakot (" + cimke + ") mutatják, az adat vége: "
    + datum_formaz(adat_veg.slice(0, 10)) + " A pontszámok szavanként külön 0–100 skálán állnak, "
    + "egymással nem összemérhetők.";
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
function nyers_ablak(szo, veg, forras, racs) {
  const kw = (adat[forras || "kulcsszo_nyers.json"] || {}).kulcsszavak || {};
  // LANC-ORAS Sz2: a lánc-forrás alakja EGY rekord (nem ablak-lista) — a 2_het+ órás ebből rajzol.
  // Egyezés az iv.ablak_veg_utc-vel (a backend a lanc["ablak_veg_utc"]-ig szeletelt); a lánc pontjai
  // mind lezártak (nincs reszleges). Nincs pont / nincs egyezés → null (kirajzolhatatlan).
  if (forras === "kulcsszo_lanc.json") {
    const rek = kw[szo];
    if (!rek || rek.ablak_veg_utc !== veg) return null;
    // LANC-2HET-VONAL: a lánc ablak_veg_utc-je VALÓS (rajzolandó) pont — NEM részleges záró slot, mint a nyersé.
    // Explicit jelző (_veg_valos), hogy a racs_epit INKLUZÍVAN vegye hozzá az utolsó pontot + a trendvonal-végpontot.
    return (rek.pontok || []).length ? Object.assign({}, rek, { _veg_valos: true }) : null;
  }
  const ablakok = kw[szo] || [];
  for (let i = 0; i < ablakok.length; i++) {
    if (ablakok[i].ablak_veg_utc !== veg) continue;
    // ÜTKÖZÉS-FIX: egy szónak TÖBB ablaka lehet AZONOS ablak_veg-gel (a másodlagos 3-m NAP + 12-m HET
    // sorozat egyszerre "ma" ér véget) → a FELBONTÁSRA (racs) is illesztünk, különben a heti intervallum
    // a rövidebb NAPI ablakot kapná (3 hó hetekre csúszva + a heti trendvonal éves végpontja kiesik).
    // A primer nyers ablaknak NINCS racs mezője → ott a szűrő kimarad (backward-kompatibilis; az órás
    // 1_het / a nap-config szavak napi útját nem érinti).
    if (racs && ablakok[i].racs && ablakok[i].racs !== racs) continue;
    // J2: rajzolható CSAK ha van legalább egy LEZÁRT pont (§7.5 2. eset: üres/csupa-részleges lista
    // séma-érvényes, de nem rajzolható → data-drawable="false" + URES_NINCS_ABLAK, NEM racs_epit-kivétel)
    const van_lezart = (ablakok[i].pontok || []).some(function (p) { return !p.reszleges; });
    return van_lezart ? ablakok[i] : null;
  }
  return null;
}

// órarács a rajzoláshoz: az ELSŐ lezárt ponttól a részleges záró slotig (kizárva); a hiányzó órák
// NULL-ok (spec 7.5: nincs interpoláció, a vonal megszakad). Visszaad: labels/ertekek/vonal/szakadas/csupa_nulla.
function racs_epit(ablak, iv, racs, szint) {
  const pontok = ablak.pontok.slice().sort(function (a, b) { return a.idopont_utc < b.idopont_utc ? -1 : 1; });
  const lezart = pontok.filter(function (p) { return !p.reszleges; });
  const elso_idx = slot_index(lezart[0].idopont_utc, racs);
  // LANC-2HET-VONAL: a NYERS ablak_veg_utc RÉSZLEGES záró slot (kizárva marad); a LÁNC-é VALÓS pont (_veg_valos)
  // → INKLUZÍV (+1), különben az utolsó pont ÉS a trendvonal-végpont kiesik. A rekord mondja meg a konvenciót,
  // NEM a hurok-határt toljuk vakon → a nyers ág (hátsó-lyuk) VÁLTOZATLAN (_veg_valos undefined → +0).
  const veg_idx = slot_index(ablak.ablak_veg_utc, racs) + (ablak._veg_valos ? 1 : 0);
  // 6c javító-szelet (latens 6b-hiba): a RAJZOLT tartomány az INTERVALLUM ablakára szeletelt, NEM a teljes rekord.
  // A kezdet az iv.ablak_kezdet_utc slotja (a BACKEND számolta, NEM a mai dátumból — a kettő eltér, ha az adat
  // régebbi), de SOSEM a rekord első lezárt pontja elé (max). Enélkül a 3_ho a teljes 52 hetet rajzolta, a felirat
  // hazudott (kórház/akciós újság 3_ho = 1_ev = 52 hét). Az órás 1_het változatlan: ott iv.ablak_kezdet <= elso pont.
  const rajz_kezd = Math.max(elso_idx, iv.ablak_kezdet_utc ? slot_index(iv.ablak_kezdet_utc, racs) : elso_idx);
  const ertek_map = {}, cimke_map = {};
  lezart.forEach(function (p) { const i = slot_index(p.idopont_utc, racs); ertek_map[i] = p.ertek; cimke_map[i] = p.idopont_utc; });
  const labels = [], ertekek = [], xy = [];   // xy: {x:ms,y} — TELJES-NEZET lineáris tengelyéhez (a category-út labels/ertekek-et használ)
  let van_nemnulla = false;
  for (let i = rajz_kezd; i < veg_idx; i++) {
    if (Object.prototype.hasOwnProperty.call(ertek_map, i)) {
      // J3: az órás label a dátumot ÉS az ÓRÁT hordozza (a tooltip ezt mutatja); a tengely-tick csak a dátumot
      // (chart_letrehoz). Nap/het rácson NINCS óra-rész → csak a dátum (a tick-regex dátum-only labelnél nem vág).
      const cimke_datum = datum_formaz(cimke_map[i].slice(0, 10));
      labels.push(racs === "nap" || racs === "het" ? cimke_datum : cimke_datum + " " + cimke_map[i].slice(11, 16));
      ertekek.push(ertek_map[i]);
      xy.push({ x: iso_ms(cimke_map[i]), y: ertek_map[i] });   // valós pont: a tényleges dátum ms-e
      if (ertek_map[i] !== 0) van_nemnulla = true;
    } else {
      labels.push("");
      ertekek.push(null);   // NULL a hiányzó óra helyén → a vonal itt megszakad (spanGaps:false)
      xy.push({ x: slot_ms(i, racs), y: null });   // hiányzó slot: null-y a slot ms-én (a vonal itt is megszakad)
    }
  }
  // regressziós vonal (S1 önőrző, V1): CSAK ha MINDKÉT végpont a KIRAJZOLT rácson, MÉRT sloton van
  // (ertekek[i] !== null). A guard a rajzolt [0, ertekek.length) tartományra megy, NEM az összes pontra —
  // különben egy RÉSZLEGES záró (veg, index == ertekek.length) vagy elso_idx elé eső végpont a tömbön KÍVÜLRE
  // írna (némán elcsúszó/1-pontos vonal), miközben a data-vonal="true" hazudna.
  let vonal = null, vonal_van = false;
  const v = iv.illesztes_vonal;
  if (v && v.length === 2) {
    const i0 = slot_index(v[0].idopont_utc, racs) - rajz_kezd;
    const i1 = slot_index(v[1].idopont_utc, racs) - rajz_kezd;
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
  // 6c: esemenyjelzo szint-VONAL — konstans vízszintes a szó-szintű heti mediánon (NEM illesztes_vonal:
  // az két végpontból trend-jellegű; ez minden slotra ugyanaz). A rajzolt hossz a sorozaté (a null-oknál is
  // fut — spanGaps:true a datasetjén), így a csúcsok fölé/alá nyúlhat, referencia-szintként.
  const szint_vonal = (szint != null) ? new Array(ertekek.length).fill(szint) : null;
  // TELJES-NEZET {x,y} párok a lineáris tengelyhez: a trend-vonal a két illesztés-végpontból (a vonal_van guard
  // már ellenőrizte, hogy mindkettő a rajzolt sorozaton van); a szint-vonal konstans, a rajzolt x-tartomány két végén.
  const vonal_xy = vonal_van ? [{ x: iso_ms(v[0].idopont_utc), y: v[0].ertek }, { x: iso_ms(v[1].idopont_utc), y: v[1].ertek }] : null;
  const szint_xy = (szint != null && xy.length) ? [{ x: xy[0].x, y: szint }, { x: xy[xy.length - 1].x, y: szint }] : null;
  return { labels: labels, ertekek: ertekek, xy: xy, vonal: vonal, vonal_van: vonal_van, vonal_xy: vonal_xy,
           szint_vonal: szint_vonal, szint_xy: szint_xy,
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
  // TELJES-NEZET: teljes módban a per-szó választás dönt (teljes_valaszt) — a data-teljes-forras a választott
  // intervallum kulcsa (a közös tengelyre vetített leghosszabb érvényes); egyébként a globális aktív intervallum.
  let iv, teljes_valasztott = null;
  if (aktiv_kulcs === TELJES_KULCS) {
    teljes_valasztott = teljes_valaszt(szoreg);
    iv = teljes_valasztott ? teljes_valasztott.iv : null;
    if (teljes_valasztott) kartya.setAttribute(ATTR.teljes_forras, teljes_valasztott.kulcs);
  } else {
    iv = szoreg.intervallumok ? szoreg.intervallumok[aktiv_kulcs] : null;
  }
  const ablak = (iv && iv.ervenyes) ? nyers_ablak(szo, iv.ablak_veg_utc, iv._forras, iv._racs) : null;

  // item 3 (2026-08-18): a szó FELBONTÁSA MINDEN kártyán (az ÜRES-en is) — rögtön látszik, miért nincs görbe
  // egy adott ablakon. Forrás: az intervallum _racs-a; üresnél a szó config-rácsa (szoreg.racs). Mindkét ág ELŐTT.
  const felbontas_racs = (iv && iv._racs) || szoreg.racs || "ora";
  kartya.setAttribute(ATTR.felbontas, felbontas_racs);
  const fb = document.createElement("p");
  fb.className = OSZT.felbontas;
  fb.textContent = "Felbontás: " + felbontas_szo(felbontas_racs);
  kartya.appendChild(fb);

  const teljes_ures = (aktiv_kulcs === TELJES_KULCS && !teljes_valasztott);   // teljes módban egy érvényes intervallum sincs
  if (!iv || !iv.ervenyes || !ablak) {
    kartya.setAttribute(ATTR.drawable, "false");
    if (teljes_ures) kartya.setAttribute(ATTR.ok, "teljes_nincs_sorozat");     // ÚJ, KÜLÖN ok-kód
    else if (iv && !iv.ervenyes && iv.ok) kartya.setAttribute(ATTR.ok, iv.ok);
    const p = document.createElement("p");
    p.className = OSZT.ures;
    p.textContent = teljes_ures ? OK_MAGYAR["teljes_nincs_sorozat"]
      : ((iv && !iv.ervenyes) ? (OK_MAGYAR[iv.ok] || iv.ok) : URES_NINCS_ABLAK);
    kartya.appendChild(p);
    return kartya;
  }

  const racs = racs_epit(ablak, iv, iv._racs, szoreg.szint);
  kartya.setAttribute(ATTR.drawable, "true");
  if (szoreg.szint != null) kartya.setAttribute(ATTR.szint, String(szoreg.szint));   // 6c: a szint-vonal értéke (heti medián)
  kartya.setAttribute(ATTR.ablak_veg, ablak.ablak_veg_utc);   // a kiválasztott nyers ablak KULCSA (regresszió ablak_veg_utc-vel egyező); részleges záró slot
  kartya.setAttribute(ATTR.adat_veg, racs.adat_veg);          // B1: a felirat „adat vége"-je — az utolsó KIRAJZOLT LEZÁRT pont (nem az ablak_veg)
  kartya.setAttribute(ATTR.pontok, String(iv.pontok_hasznalt));
  kartya.setAttribute(ATTR.reszleges, String(iv.pontok_kihagyva_reszleges));
  kartya.setAttribute(ATTR.hianyzo, String(iv.pontok_hianyzo));
  kartya.setAttribute(ATTR.szakadas, String(racs.szakadas));
  kartya.setAttribute(ATTR.rajzolt_pont, String(racs.ertekek.length));   // 6c javító-szelet: a szeletelt ablak rajzolt slot-száma
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
  m.textContent = merteszamok_szoveg(iv, iv._racs, szoreg.szint);
  kartya.appendChild(m);

  const tf = document.createElement("p");
  tf.className = OSZT.tengely_felirat;
  tf.textContent = TENGELY_FELIRAT;
  kartya.appendChild(tf);

  // TELJES-NEZET: a kártya kimondja, HONNAN van adata (a per-szó választott intervallum rácsa + hossza + kezdete)
  if (aktiv_kulcs === TELJES_KULCS && teljes_valasztott) {
    const ivm = INTERVALLUMOK.find(function (i) { return i.kulcs === teljes_valasztott.kulcs; });
    const ff = document.createElement("p");
    ff.className = OSZT.teljes_forras_felirat;
    ff.textContent = "adat forrása: " + felbontas_szo(iv._racs) + " sorozat"
      + (ivm ? " (" + ivm.cimke + ")" : "") + ", " + datum_formaz(iv.ablak_kezdet_utc.slice(0, 10)) + "-től";
    kartya.appendChild(ff);
  }

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

  // TELJES-NEZET (per-szó tengely): a lineáris dátum-tengely a KÁRTYA SAJÁT adat-tartományára AUTO-FITEL (nincs
  // min/max → Chart.js a {x:ms,y} pontok első→utolsó értékéhez illeszt) → a rövid sorozat KITÖLTI a szélességet,
  // nem lapul össze (a benzin 7 napja a saját tengelyén, nem egy 1 éves közösön). Nincs idő-adapter → type:"linear"
  // + tick/tooltip callback (ms → dátum). A y-tengely VÁLTOZATLAN 0–100 (§1.4: nincs kártyák-közti átskálázás).
  if (kartya._teljes_mod) {
    const ds = [{ data: racs.xy, spanGaps: false, borderColor: ADAT_VONAL_SZIN, borderWidth: 1.5, pointRadius: 0 }];
    if (racs.vonal_xy) ds.push({ data: racs.vonal_xy, spanGaps: true, borderColor: "#cc3333", borderWidth: 1.5, borderDash: [4, 3], pointRadius: 0 });
    if (racs.szint_xy) ds.push({ data: racs.szint_xy, spanGaps: true, borderColor: "#e69138", borderWidth: 1.5, borderDash: [6, 4], pointRadius: 0 });
    // per-szó tengely PONTOS széllel: min/max = az ELSŐ/UTOLSÓ tényleges adatpont (nincs Chart.js grace-padding →
    // a görbe a két szélt ÉRINTI, nincs felesleges gap). A tengelyen CSAK 2 tick: a KEZDŐ + a VÉG dátum (teljes).
    const teljes_pts = racs.xy.filter(function (p) { return p.y !== null; });
    const x_min = teljes_pts.length ? teljes_pts[0].x : undefined;
    const x_max = teljes_pts.length ? teljes_pts[teljes_pts.length - 1].x : undefined;
    chart_peldanyok[kartya.getAttribute(ATTR.kulcsszo)] = new Chart(canvas, {
      type: "line",
      data: { datasets: ds },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        // TOOLTIP-UX: bárhol a chart fölé érve felugorjon a legközelebbi adatpont (nem csak PONTOSAN a vonalon)
        interaction: { mode: "index", intersect: false },
        scales: {
          y: { min: 0, max: 100, title: { display: true, text: TENGELY_FELIRAT } },
          x: { type: "linear", min: x_min, max: x_max,   // pontos szél (nincs padding-gap)
               afterBuildTicks: function (sc) { sc.ticks = [{ value: sc.min }, { value: sc.max }]; },   // CSAK a kezdő + a vég dátum
               ticks: { autoSkip: false, callback: function (v) { return ms_datum(v, true); } } },
        },
        plugins: {
          legend: { display: false },
          // közös tooltip-stílus + a dátum a title-ben (teljes nap); a per-szó lineáris tengelyen a parsed.x az ms
          tooltip: Object.assign({}, TOOLTIP_STILUS, {
            callbacks: { title: function (items) { return items.length ? ms_datum(items[0].parsed.x, true) : ""; } },
          }),
        },
      },
    });
    kartya.setAttribute(ATTR.rendered, "true");
    return;
  }

  const datasetek = [{ data: racs.ertekek, spanGaps: false, borderColor: ADAT_VONAL_SZIN, borderWidth: 1.5, pointRadius: 0 }];
  if (racs.vonal) datasetek.push({ data: racs.vonal, spanGaps: true, borderColor: "#cc3333", borderWidth: 1.5, borderDash: [4, 3], pointRadius: 0 });
  // 6c: esemenyjelzo szint-vonal — konstans vízszintes referencia (narancs, a kék adattól ÉS a piros trendtől
  // is elkülönül); NEM trendvonal (data-vonal marad "false"), a bázist a merteszamok-felirat mondja ki.
  if (racs.szint_vonal) datasetek.push({ data: racs.szint_vonal, spanGaps: true, borderColor: "#e69138", borderWidth: 1.5, borderDash: [6, 4], pointRadius: 0 });
  chart_peldanyok[kartya.getAttribute(ATTR.kulcsszo)] = new Chart(canvas, {
    type: "line",
    data: { labels: racs.labels, datasets: datasetek },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      // TOOLTIP-UX (SZEMLE 08-19): index+intersect:false → bárhol a chart fölé érve felugrik a legközelebbi x
      // adatpontja (nem kell PONTOSAN a vékony vonalra/pontra vinni). A régi default (intersect:true) miatt volt „szórakozós".
      interaction: { mode: "index", intersect: false },
      scales: {
        y: { min: 0, max: 100, title: { display: true, text: TENGELY_FELIRAT } },
        // J3: a tengely-TICK csak a dátumot mutatja (a záró " HH:MM"-et levágja), a TOOLTIP a teljes labelt
        // (dátum + óra) → a #9 órás felbontás a tooltipben. Canvas-belső, DOM-ból nem assertálható (ledger).
        x: { type: "category", ticks: { maxTicksLimit: 10, callback: function (v) { const l = this.getLabelForValue(v); return l ? l.replace(/\s\d{2}:\d{2}$/, "") : l; } } },
      },
      // a tooltip CSAK az adatsort mutassa (datasetIndex 0); displayColors:false → NINCS szín-négyzet (egyetlen
      // sorozatnál redundáns/ronda); tiszta tömör sötét háttér (nem átlátszóbb — az rontaná az olvashatóságot).
      plugins: { legend: { display: false }, tooltip: TOOLTIP_STILUS },
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
// MINDEN .attekinto-panel-be rajzol (a lap TETEJÉN és ALJÁN is ugyanaz az áttekintő) — egy adatszámítás,
// két megjelenítés. A csoportosítás egyszer készül, a kitöltés panelenként (külön DOM-példányok).
function attekinto_blokk_render() {
  const panelek = document.querySelectorAll(".attekinto-panel");
  if (!panelek.length) return;
  const reg = egyesitett_reg();
  const csoportok = {};
  if (reg && reg.kulcsszavak) {
    Object.keys(reg.kulcsszavak).forEach(function (szo) {
      const d = reg.kulcsszavak[szo].domen;
      const kulcs = DOMEN_MAGYAR[d] ? d : EGYEB_KULCS;
      (csoportok[kulcs] = csoportok[kulcs] || []).push(szo);
    });
  }
  panelek.forEach(function (blokk) {
    attekinto_panel_kitolt(blokk, reg, csoportok, blokk.getAttribute("data-mod") || "elteres");
  });
}
// EGY panel kitöltése: kategória-cellák FIX oszlop-rácsban (nagy kategóriák egymás MELLETT, elválasztó
// csíkkal), cellán belül a domén-címke balra, a szó-chipek jobbra; a magyarázat a panel ALJÁN.
function attekinto_panel_kitolt(blokk, reg, csoportok, mod) {
  blokk.querySelectorAll(".attekinto-lista, .attekinto-magyarazat").forEach(function (e) { e.remove(); });
  if (reg && reg.kulcsszavak) {
    const lista = document.createElement("div");
    lista.className = "attekinto-lista";
    DOMEN_SORREND.forEach(function (d) {
      const kulcs = d === null ? EGYEB_KULCS : d;
      const szavak = csoportok[kulcs];
      if (!szavak || !szavak.length) return;
      const sor = document.createElement("div");
      sor.className = "attekinto-sor";
      sor.setAttribute("data-domen", d === null ? "egyeb" : d);
      const cimke = document.createElement("span");
      cimke.className = "attekinto-domen";
      cimke.textContent = d === null ? "Egyéb" : DOMEN_MAGYAR[d];
      sor.appendChild(cimke);
      const chipek = document.createElement("span");
      chipek.className = "attekinto-chipek";
      szavak.forEach(function (szo) {
        chipek.appendChild(attekinto_kartya(szo, reg.kulcsszavak[szo], mod));
      });
      sor.appendChild(chipek);
      lista.appendChild(sor);
    });
    blokk.appendChild(lista);
  }
  blokk.appendChild(attekinto_magyarazat_epit(mod));   // a magyarázat a panel ALJÁN
}
// egy chip. `mod`: "elteres" (mai eltérés a trendtől) vagy "trend" (a keresettség trend-iránya).
function attekinto_kartya(szo, szoreg, mod) {
  const k = document.createElement("span");
  k.className = "attekinto-kartya";
  k.setAttribute("data-kulcsszo", szo);
  // kattintható: a chipre kattintva a #kulcsszo-blokk megfelelő chartjához ugrunk (billentyűvel is)
  k.setAttribute("role", "link");
  k.setAttribute("tabindex", "0");
  function attekinto_ugras() {
    const cel = document.querySelector('#kulcsszo-blokk .' + OSZT.kartya + '[' + ATTR.kulcsszo + '="' + szo.replace(/"/g, '\\"') + '"]');
    if (cel) cel.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  k.addEventListener("click", attekinto_ugras);
  k.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); attekinto_ugras(); }
  });
  // az ikon adat-attribútuma + értéke + a teljes szöveg — a panel MÓDJA szerint
  let attr = null, ertek = null, cim = null;
  if (mod === "trend") {
    // TREND-irány: esemenyjelzo → nincs trend ("esemeny", mediánhoz); egyébként a backend `irany`-a
    if (szoreg.tipus === "esemenyjelzo") {
      attr = "data-trend"; ertek = "esemeny"; cim = TREND_SZOVEG.esemeny;
    } else {
      const _tv = teljes_valaszt(szoreg);
      const iv = _tv && _tv.iv;
      const ir = iv && iv.irany;
      if (ir && TREND_SZOVEG[ir]) { attr = "data-trend"; ertek = ir; cim = TREND_SZOVEG[ir]; }
    }
  } else {
    // MAI ELTÉRÉS: esemenyjelzo → a MEDIÁNHOZ mérve; egyébként a szó elsődleges ablakának trendjéhez
    let allapot;
    if (szoreg.tipus === "esemenyjelzo") {
      allapot = szoreg.illeszkedes_szint;
      cim = allapot ? ELTERES_SZINT_SZOVEG[allapot] : null;
    } else {
      const _tv = teljes_valaszt(szoreg);
      const iv = _tv && _tv.iv;
      allapot = iv && iv.illeszkedes;
      cim = allapot ? ELTERES_SZOVEG[allapot] : null;
    }
    if (allapot && ELTERES_SZOVEG[allapot]) { attr = "data-illeszkedes"; ertek = allapot; }
  }
  // az ikon a szó ELÉ — csak ha van állapot (nincs kitalálás)
  if (attr && ertek) {
    const ikon = document.createElement("span");
    ikon.className = "attekinto-ikon";
    ikon.setAttribute(attr, ertek);
    k.appendChild(ikon);
  }
  const nev = document.createElement("span");
  nev.className = "attekinto-szo";
  nev.textContent = szo;
  k.appendChild(nev);
  if (cim) { k.setAttribute("title", cim); k.setAttribute("aria-label", cim); }
  return k;
}
function kulcsszo_blokk_render() {
  const blokk = document.getElementById("kulcsszo-blokk");
  if (!blokk) return;
  chart_takarit();   // váltáskor: régi példányok destroy + megfigyelő le
  blokk.querySelectorAll("." + OSZT.frissesseg + ", ." + OSZT.csoport).forEach(function (e) { e.remove(); });

  const aktiv = blokk.getAttribute(ATTR.aktiv);
  // request 2: a „Kulcsszavak" cím a nézet-leírással bővül (aktiv szerint); nincs aktív → csak a bázis cím
  const cim_h2 = blokk.querySelector("h2");
  if (cim_h2) {
    const sfx = KULCSSZO_CIM_SUFFIX[aktiv];
    cim_h2.textContent = sfx ? KULCSSZO_CIM_ALAP + " – " + sfx : KULCSSZO_CIM_ALAP;
  }
  const reg = egyesitett_reg();
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

  // TELJES-NEZET (SZEMLE 08-19, per-szó tengely): NINCS közös tengely — MINDEN kártya a SAJÁT adat-időszakára
  // skálázódik (a lineáris dátum-tengely auto-fitel a kártya első→utolsó pontjára), így a rövid sorozat (pl. órás
  // benzin 7 nap) KITÖLTI a kártya szélességét, nem lapul össze egy hosszú (pl. heti 1 év) közös tengelyen. A span
  // szövegesen a forrás-feliraton marad. A kártya-Chart a _teljes_mod flaget olvassa (chart_letrehoz).
  if (aktiv === TELJES_KULCS) {
    rajzolhatok.forEach(function (k) { k._teljes_mod = true; });
  }

  // frissesseg CSAK ha van legalább egy RAJZOLHATÓ kártya (különben — mint 15a/15b — elmarad); a h2 után
  if (adat_veg) {
    const f = document.createElement("p");
    f.className = OSZT.frissesseg;
    f.textContent = frissesseg_szoveg(aktiv, adat_veg);   // teljes módban a szöveg NEM használ egyetlen dátumot (per-szó tengely)
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
  gomb_other: "kategoria-gomb--other", gomb_reset_aktiv: "kategoria-gomb--reset-aktiv", lista: "trend-lista", kartya: "trend-kartya",
  kifejezes: "trend-kifejezes", volumen: "trend-volumen", kategoria: "trend-kategoria", ures: "ures",
  sparkline_doboz: "trend-sparkline-doboz", idosor_ures: "trend-idosor-ures", idosor_ures_blokk: "trend-idosor-ures-blokk",
  normalizalas_magyarazat: "trend-normalizalas-magyarazat",   // 8b: a görbe-magasság félreolvasása ellen (LELET 2)
  idosor_adat: "idosor-adat", idosor_vonal: "idosor-vonal",   // kategória-idősor Szelet 1: rejtett DOM-tükör (nem canvas)
  idosor_chart_doboz: "idosor-chart-doboz", idosor_chart: "idosor-chart",   // Szelet 2: line-chart (a jobb #idosor-blokk-ban)
  idosor_magyarazat: "idosor-magyarazat",   // caption a jobb doboz alján (a bar-caption külön)
  idosor_legend_elem: "idosor-legend-elem", idosor_legend_pont: "idosor-legend-pont", kiemelt: "kiemelt",  // kétdobozos: HTML-legend a bal dobozban
};
const ATTR_T = {
  aktiv_kategoria: "data-aktiv-kategoria", nap: "data-nap", kifejezes: "data-kifejezes",
  volumen: "data-volumen", kategoriak: "data-kategoriak", kategoria_allapot: "data-kategoria-allapot",
  kategoria: "data-kategoria", count: "data-count",
  idosor_allapot: "data-idosor-allapot", idosor_rendered: "data-idosor-rendered",
  napok: "data-napok", vonal_szam: "data-vonal-szam", ertekek: "data-ertekek", elso_nap: "data-elso-nap",  // idősor-tükör
  idosor_chart_rendered: "data-idosor-chart-rendered", idosor_aktiv: "data-idosor-aktiv",  // Szelet 2
};
const OTHER_CIMKE = "Other";       // a Google gyűjtő-KATEGÓRIÁJA (van szűrő-gomb, szürke, utolsó)
// kategória-idősor: minden vonal ALAPBÓL szürke; a kiválasztott KÉK (a többi chart szürke-kék palettája). Nincs
// csiricsáré per-kategória szín (SZEMLE-döntés); a kiemelés a bar-chart aktív/tompított mintáját követi.
const IDOSOR_SZURKE = "#cccccc";
const IDOSOR_KIEMELT = KATEGORIA_ALAP_SZIN;   // #3366cc — az app kék akcentusa
const EGYEB_CIMKE = "egyéb";       // a besorolás HIÁNYA ([]/hiányzó mező) — NINCS szűrő-gomb
const OSSZES_CIMKE = "Összes";
const TREND_URES_SZOVEG = "Ma nem érkezett friss felkapott trend erre a napra.";
const TREND_IDOSOR_URES_ELEM = "nincs idősor ezen a napon";               // elemenkénti (D1-kiterjesztett kártya)
const TREND_IDOSOR_URES_BLOKK = "Ezen a napon egyetlen felkapott trendhez sincs idősor.";  // blokk-szintű (mind-üres nap, Task 3)
// 8b (LELET 2): KÉTFELŰ — mi NEM olvasható ki (magasság-összevetés, §1.4 önnormalizálás) + mi IGEN (alak + időzítés, §7.3).
const TREND_NORMALIZALAS_SZOVEG = "A görbék magassága nem összemérhető: mindegyik a saját aznapi csúcsához (100) "
  + "van skálázva, ezért két hasonló magasságú görbe eltérő keresettséget takarhat – azt a „volumen” mutatja. "
  + "Amit a görbe megbízhatóan mutat: egy trend saját napi lefutásának alakját és a csúcs időzítését.";

let kategoria_chart = null;        // az eloszlás-chart SAJÁT példánya (NEM a kulcsszó chart_peldanyok/chart_takarit)
let idosor_chart = null;           // a kategória-idősor line-chart SAJÁT példánya (Szelet 2)
let idosor_aktiv = "";             // a kiemelt (kék) kategória neve, vagy "" (mind szürke) — a bar aktív-mintája
let trend_chart_peldanyok = [];    // 8a: sparkline Chart-példányok TÖMBJE (MIN-TCP: NEM kifejezés-kulcsú — két
                                   // azonos kifejezésű trend különben felülírta egymást → árva Chart). KÜLÖN a
                                   // kulcsszó chart_peldanyok-tól. Csak destroy-all a rendeltetése (nincs kikeresés).
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
  const el = document.getElementById("datum-valaszto");
  const v = el && el.getAttribute("data-valasztott-nap");   // a naptár kiválasztott napja (a régi select.value helyett)
  if (v) return v;
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

// KATEGÓRIA-IDŐSOR shaper (Szelet 1): kategoriak.json → { napok:[ISO], vonalak:[{nev, ertekek:[db|null], elso_nap}] }.
// TENGELY: CSAK a MÉRT napok, egymás után — a hiányzó napok (pl. 08-06) NEM kerülnek a tengelyre, így a vonal az
// első adattól FOLYTONOSAN épül (nincs lebegő pont/üres oszlop). Érték-szabály: a kategória első megjelenése ELŐTT →
// null (a vonal a feltűnéskor kezdődik, nem lapos nulla); jelen-nap-0-előfordulás → VALÓS 0. Vonal-készlet
// ADAT-VEZÉRELT (csak az előfordult kategóriák). Sorrend: első-megjelenés, majd név.
function kategoria_idosor(kj) {
  const rekordok = ((kj && kj.napok) || []).filter(function (n) { return n && n.nap && n.kategoriak; });
  if (!rekordok.length) return { napok: [], vonalak: [] };
  const jelen = {};
  rekordok.forEach(function (n) { jelen[n.nap] = n.kategoriak; });
  const napok = Object.keys(jelen).sort();   // CSAK a mért napok (hiányzó nap NINCS a tengelyen)
  const elso = {};
  napok.forEach(function (d) {
    Object.keys(jelen[d]).forEach(function (cat) { if (!(cat in elso)) elso[cat] = d; });
  });
  const vonalak = Object.keys(elso).map(function (cat) {
    const ertekek = napok.map(function (d) {
      if (d < elso[cat]) return null;   // első megjelenés előtt → null (a vonal a feltűnéskor kezdődik)
      return jelen[d][cat] || 0;        // valós érték vagy VALÓS 0
    });
    return { nev: cat, ertekek: ertekek, elso_nap: elso[cat] };
  });
  vonalak.sort(function (a, b) {
    return a.elso_nap < b.elso_nap ? -1 : a.elso_nap > b.elso_nap ? 1 : (a.nev < b.nev ? -1 : 1);
  });
  return { napok: napok, vonalak: vonalak };
}

// a shaper eredménye rejtett DOM-tükörbe (data-* JSON) → DOM-assertálható a null-rés/első-megjelenés/valós-0 szabály.
function trend_idosor_tukor_epit(idosor) {
  const adat = document.createElement("div");
  adat.className = OSZT_T.idosor_adat;
  adat.setAttribute(ATTR_T.napok, JSON.stringify(idosor.napok));
  adat.setAttribute(ATTR_T.vonal_szam, String(idosor.vonalak.length));
  idosor.vonalak.forEach(function (v) {
    const s = document.createElement("span");
    s.className = OSZT_T.idosor_vonal;
    s.setAttribute(ATTR_T.kategoria, v.nev);
    s.setAttribute(ATTR_T.ertekek, JSON.stringify(v.ertekek));
    s.setAttribute(ATTR_T.elso_nap, v.elso_nap);
    adat.appendChild(s);
  });
  return adat;
}

// egy vonal stílusa az AKTÍV kiemelés függvényében (szürke alap / kék kiemelt / halvány tompított — a bar mintája).
function idosor_vonal_stilus(nev) {
  if (!idosor_aktiv) return { szin: IDOSOR_SZURKE, vastag: 1.5, pont: 0, sorrend: 1 };   // alap: MIND szürke
  if (nev === idosor_aktiv) return { szin: IDOSOR_KIEMELT, vastag: 2.5, pont: 2.5, sorrend: 0 };  // kiemelt: kék, felül
  return { szin: "#e6e6e6", vastag: 1, pont: 0, sorrend: 2 };                            // tompított
}

// az aktív kategória átszínezése (a count-ok/adatok VÁLTOZATLANOK — csak szín/vastagság/sorrend, mint a bar szinez).
function idosor_szinez() {
  if (idosor_chart) {
    idosor_chart.data.datasets.forEach(function (ds) {
      const st = idosor_vonal_stilus(ds.label);
      ds.borderColor = st.szin; ds.backgroundColor = st.szin;
      ds.borderWidth = st.vastag; ds.pointRadius = st.pont; ds.order = st.sorrend;
    });
    idosor_chart.update();
  }
  const blokk = document.getElementById("idosor-blokk");
  if (blokk) blokk.setAttribute(ATTR_T.idosor_aktiv, idosor_aktiv);   // DOM-tükör az aktív állapotról (a SAJÁT szekción)
  // a BAL HTML-legend aktív állapotának szinkronja: .kiemelt CSAK az aktív kategórián (kék pötty + kék szöveg)
  const legendEl = document.getElementById("idosor-legend");
  if (legendEl) {
    Array.prototype.forEach.call(legendEl.querySelectorAll("." + OSZT_T.idosor_legend_elem), function (b) {
      const akt = idosor_aktiv !== "" && b.getAttribute(ATTR_T.kategoria) === idosor_aktiv;
      b.classList.toggle(OSZT_T.kiemelt, akt);
    });
  }
}

function idosor_aktiv_valt(nev) {
  idosor_aktiv = (idosor_aktiv === (nev || "")) ? "" : (nev || "");   // ugyanarra kattintva reset (toggle)
  idosor_szinez();
}

// Szelet 2: a kategória-idősor line-chart (Chart.js). A canvas-belső (kiemelés, legend-kattintás) NEM DOM-assertálható
// → SZEMLE-köteles; a data-modellt a rejtett tükör hordozza. Alapból MINDEN vonal szürke, egyszerre EGY kék kiemelt.
function trend_idosor_chart_epit(canvas, idosor) {
  canvas.setAttribute(ATTR_T.idosor_chart_rendered, "true");   // DOM-szerződés akkor is, ha nincs Chart (a tükör a forrás)
  if (typeof Chart === "undefined") return;
  // alap: az ELSŐ kategória KIEMELVE (kék), nem „mind szürke" — így rögtön olvasható egy görbe (user-kérés)
  idosor_aktiv = (idosor.vonalak && idosor.vonalak[0] && idosor.vonalak[0].nev) || "";
  idosor_chart = new Chart(canvas, {
    type: "line",
    data: {
      labels: idosor.napok,
      datasets: idosor.vonalak.map(function (v) {
        const st = idosor_vonal_stilus(v.nev);
        return { label: v.nev, data: v.ertekek, borderColor: st.szin, backgroundColor: st.szin,
                 borderWidth: st.vastag, pointRadius: st.pont, pointHoverRadius: 4, tension: 0,
                 spanGaps: false, order: st.sorrend };   // spanGaps:false → 08-06 rés + első-megjelenés előtt NINCS pont/vonal
      }),
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false, spanGaps: false,
      interaction: { mode: "nearest", intersect: false },
      onClick: function (evt, elemek) {   // vonalra kattintás = kiemelés; üres területre = reset (a bar mintája)
        if (elemek && elemek.length) idosor_aktiv_valt(idosor_chart.data.datasets[elemek[0].datasetIndex].label);
        else idosor_aktiv_valt("");
      },
      scales: {
        x: { grid: { display: false } },   // függőleges rács KI — zaj (átlósan keresztezi a vonalakat), a dátum az x-tengelyen van
        y: { beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: "kategóriába eső trendek" },
             grid: { color: "#f0f0f0" } },   // vízszintes rács HALVÁNY — az érték-leolvasáshoz, a kék kiemelt vonal fölé nem tolakszik
      },
      plugins: {
        legend: { display: false },   // KÉTDOBOZOS: a Chart.js belső legendje KIKAPCSOLVA → a bal #idosor-legend HTML-legend
        tooltip: { enabled: true },   // nearest-pont: dátum + kategória + darabszám
      },
    },
  });
}

// a kategória-idősor kattintható HTML-legendje (a BAL #idosor-legend dobozba) — a Chart.js belső legend HELYETT.
// Kerek pötty + kategórianév; aktív = .kiemelt (kék pötty + kék szöveg). Katt → idosor_aktiv_valt (chart-kiemelés).
function idosor_legend_epit(idosor) {
  const frag = document.createDocumentFragment();
  idosor.vonalak.forEach(function (v) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = OSZT_T.idosor_legend_elem;
    b.setAttribute(ATTR_T.kategoria, v.nev);
    const pont = document.createElement("span");
    pont.className = OSZT_T.idosor_legend_pont;
    b.appendChild(pont);
    b.appendChild(document.createTextNode(v.nev));
    b.addEventListener("click", function () { idosor_aktiv_valt(v.nev); });
    frag.appendChild(b);
  });
  return frag;
}

// a kategória-idősor ÖNÁLLÓ szekciója (kétdobozos): JOBB #idosor-blokk (statikus h2 → chart-doboz+canvas → rejtett
// tükör → magyarázat) + BAL #idosor-legend (kattintható legend). NAP-FÜGGETLEN (kategoriak.json) → egyszer épül (init).
function idosor_blokk_render() {
  const blokk = document.getElementById("idosor-blokk");
  const legendEl = document.getElementById("idosor-legend");
  if (!blokk || !legendEl) return;

  // idempotencia / re-render biztonság: a korábbi chart + generált elemek törlése (a statikus h2 MARAD)
  if (idosor_chart) { idosor_chart.destroy(); idosor_chart = null; }
  idosor_aktiv = "";
  blokk.querySelectorAll("." + OSZT_T.idosor_chart_doboz + ", ." + OSZT_T.idosor_adat + ", ." + OSZT_T.idosor_magyarazat)
    .forEach(function (e) { e.remove(); });
  legendEl.innerHTML = "";
  blokk.removeAttribute(ATTR_T.idosor_aktiv);

  const idosor = kategoria_idosor(adat["kategoriak.json"]);
  if (!idosor.vonalak.length) return;   // nincs kategória-adat → csak a statikus cím marad

  const doboz = document.createElement("div");
  doboz.className = OSZT_T.idosor_chart_doboz;
  const canvas = document.createElement("canvas");
  canvas.className = OSZT_T.idosor_chart;
  doboz.appendChild(canvas);
  blokk.appendChild(doboz);

  blokk.appendChild(trend_idosor_tukor_epit(idosor));   // rejtett DOM-tükör (assertálható adat-modell)

  const mag = document.createElement("p");
  mag.className = OSZT_T.idosor_magyarazat;
  mag.textContent = "A vonalak a Google Trends napi kategória-osztályozását követik – nem a mi besorolásunk "
    + "(egy trend több kategóriába is eshet). A szürke vonalak közül kattintással emelhető ki egy kategória. "
    + "A kategória-idősor " + (idosor.napok[0] || "") + "-től érhető el – a korábbi napokon nincs kategória-adat.";
  blokk.appendChild(mag);

  legendEl.appendChild(idosor_legend_epit(idosor));   // BAL doboz: HTML-legend
  blokk.setAttribute(ATTR_T.idosor_aktiv, "");        // pre-build kezdőállapot (a chart-build után az idosor_szinez felülírja)

  trend_idosor_chart_epit(canvas, idosor);   // a canvas már a jobb dobozban van (itt áll be idosor_aktiv = az ELSŐ kategória)
  idosor_szinez();   // az alap (első kategória) tükrözése a DOM-mirror (data-idosor-aktiv) + a bal legend (.kiemelt) felé
}

function trend_szin(kategoria, tompitott) {
  if (kategoria === OTHER_CIMKE) return tompitott ? "#d4d4d4" : "#9e9e9e";   // "Other" mindig szürke
  return tompitott ? "#aec4ef" : KATEGORIA_ALAP_SZIN;
}

// egy trend-sparkline AZONNALI Chart-példányosítása (mint a kategoria_chart ma — NINCS lusta observer).
// Önnormalizált y (0–100), mért nullák (spanGaps:false), NEM feltételez folytonos alapszintet; tengely/legend
// nélkül (sparkline). A data-idosor-rendered idempotencia-őr.
// 8b: HOVER-TOOLTIP bekapcsolva. A J3 kulcsszó-formátum NEM vehető át (az órás, formázott label; itt 8 PERCES
// rács, nyers ISO label) → saját callback. interaction index/nem-intersect → OSZLOPOS hover, a célzás x-alapú,
// a doboz-magasságtól FÜGGETLEN. y max=110 (~9% FEJTÉR): a 100-értékű csúcs különben a felső peremen VÁGNA
// (LELET 3 — a magasság önmagában nem oldaná; az adat marad 0–100, csak a tengely-skála kap fejteret).
// A tooltip canvas-belső → DOM-ból NEM assertálható (L9/J3), helyessége kézi szemle.
function trend_sparkline_letrehoz(kartya) {
  if (kartya.getAttribute(ATTR_T.idosor_rendered) === "true") return;
  const idosor = kartya._idosor;
  const canvas = kartya.querySelector("canvas");
  if (!idosor || !canvas || typeof Chart === "undefined") return;
  trend_chart_peldanyok.push(new Chart(canvas, {
    type: "line",
    data: {
      labels: idosor.map(function (p) { return p.idopont_utc; }),   // időbélyeg-alapú (SOHA nem index-alapú)
      datasets: [{ data: idosor.map(function (p) { return p.ertek; }), spanGaps: false,
                   borderColor: ADAT_VONAL_SZIN, borderWidth: 1, pointRadius: 0, pointHoverRadius: 3 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },   // oszlopos hover → magasság-független célzás
      scales: { x: { display: false }, y: { display: false, min: 0, max: 110 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          callbacks: {
            // cím: a nyers ISO-ból UTC „ÉÉÉÉ. HH. NN. óó:pp” (8 perces slot) — konzisztens a kulcsszó-oldallal (UTC)
            title: function (elemek) {
              const iso = (elemek[0] && elemek[0].label) || "";
              return iso.length >= 16 ? datum_formaz(iso.slice(0, 10)) + " " + iso.slice(11, 16) : iso;
            },
            // a „/ 100” finoman jelzi az önnormalizálást (a részletes magyarázat a blokk-szintű feliraté)
            label: function (elem) { return "érték: " + elem.parsed.y + " / 100"; },
          },
        },
      },
    },
  }));
  kartya.setAttribute(ATTR_T.idosor_rendered, "true");
}

function trend_chart_takarit() {
  if (kategoria_chart) { kategoria_chart.destroy(); kategoria_chart = null; }
  // MEGJEGYZÉS: az idősor-chart NEM itt takarodik — önálló #idosor-blokk szekció, NAP-FÜGGETLEN (nem napváltás-életciklus).
  trend_chart_peldanyok.forEach(function (c) { if (c) c.destroy(); });   // 8a: a sparkline-példányok is destroy (nem halmozódhatnak)
  trend_chart_peldanyok = [];                                           // MIN-TCP: teljes ürítés (index-független, kollízió-mentes)
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
      onClick: function (evt, elemek) {   // sávra kattintás = szűrés; ÜRES területre = nullázás — ugyanaz az egy forrás
        if (elemek && elemek.length) trend_kategoria_valt(blokk, eloszlas[elemek[0].index].kategoria);
        else trend_kategoria_valt(blokk, "");   // üres területre → mint az "Összes" (data-aktiv-kategoria törlődik)
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
function trend_kartya_epit(t, blokk_ures) {
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
  vol.textContent = "volumen: " + (t.volumen != null ? t.volumen : "–");
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

  // 8a: idősor-állapot BINÁRIS (az idosor kulcs mind a napi elemeken jelen van, üresen is → nincs "hianyzik")
  const idosor = Array.isArray(t.idosor) ? t.idosor : [];
  const van_idosor = idosor.length > 0;
  k.setAttribute(ATTR_T.idosor_allapot, van_idosor ? "van" : "nincs");
  if (van_idosor) {
    // H2b: fix-magasságú, position:relative WRAPPER (különben a canvas összeesik) — a Chart.js LUSTA (Task 2)
    const doboz = document.createElement("div");
    doboz.className = OSZT_T.sparkline_doboz;
    const canvas = document.createElement("canvas");
    doboz.appendChild(canvas);
    k.appendChild(doboz);
    k._idosor = idosor;   // a lusta Chart-példányosításhoz (Task 2)
  } else if (!blokk_ures) {
    // elemenkénti üzenet — CSAK ha NEM blokk-szintű összevonás (Task 3: mind-üres napon a szöveg összevonódik)
    const u = document.createElement("p");
    u.className = OSZT_T.idosor_ures;
    u.textContent = TREND_IDOSOR_URES_ELEM;
    k.appendChild(u);
  }
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
    if (kat === "") {   // az "Összes" reset-gomb: szűrt állapotban HANGSÚLYOS ("× Összes" + reset-osztály) — a felfedezhető kilépés
      const szurt = aktiv !== "";
      g.classList.toggle(OSZT_T.gomb_reset_aktiv, szurt);
      g.textContent = szurt ? "× " + OSSZES_CIMKE : OSSZES_CIMKE;
    }
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
  mag.textContent = "A kategóriákat a Google Trends napi osztályozása adja – nem a mi besorolásunk. "
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
  blokk.querySelectorAll("." + OSZT_T.osszefoglalo + ", ." + OSZT_T.lista + ", ." + OSZT_T.ures
    + ", ." + OSZT_T.idosor_ures_blokk + ", ." + OSZT_T.normalizalas_magyarazat)
    .forEach(function (e) { e.remove(); });

  // KATEGÓRIA-IDŐSOR: már NEM itt él — önálló #idosor-blokk szekció (idosor_blokk_render), NAP-FÜGGETLEN.

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

  // 8a Tétel-4: ha a nap MINDEN eleme üres idosor-ú (idosor-ág bukása), az elemenkénti üzenet EGY blokk-jelzéssé
  // vonódik össze (üres == elemszám; köztes arányoknál elemenkénti marad). A kártyák data-idosor-allapot="nincs"-e MARAD.
  const mind_ures = trendek.every(function (t) { return !Array.isArray(t.idosor) || t.idosor.length === 0; });
  if (mind_ures) {
    const bu = document.createElement("p");
    bu.className = OSZT_T.idosor_ures_blokk;
    bu.textContent = TREND_IDOSOR_URES_BLOKK;
    blokk.appendChild(bu);   // a szekció élén, a lista előtt
  } else {
    // 8b (LELET 2): normalizálás-magyarázat a lista FÖLÉ — CSAK ha van görbe (!mind_ures). A feltétel
    // SZÁNDÉKOSAN a mind_ures-tükre, NEM a kategória (eloszlas>0): archív napon van görbe, de nincs kategória
    // → a magyarázat AKKOR IS kell; mind-üres napon nincs mit magyarázni. Az összefoglaló UTÁN, a lista ELŐTT.
    const nm = document.createElement("p");
    nm.className = OSZT_T.normalizalas_magyarazat;
    nm.textContent = TREND_NORMALIZALAS_SZOVEG;
    blokk.appendChild(nm);
  }

  const lista = document.createElement("div");
  lista.className = OSZT_T.lista;
  trendek.forEach(function (t) { lista.appendChild(trend_kartya_epit(t, mind_ures)); });   // NINCS fix hossz-feltevés
  blokk.appendChild(lista);

  // 8a: a "van" kártyák sparkline-jai AZONNAL rajzolódnak (mint a kategoria_chart ma) — a lista már a DOM-ban van
  Array.prototype.slice.call(
    lista.querySelectorAll("." + OSZT_T.kartya + "[" + ATTR_T.idosor_allapot + "='van']"))
    .forEach(trend_sparkline_letrehoz);

  trend_szinkron(blokk);   // a kezdő állapot (nincs szűrés) szinkronja
}

// a naptár vezérli a napot (esemény-delegálás a konténeren → túléli a naptár újrarajzolását)
function trend_esemeny_kot() {
  if (trend_esemeny_kotve) return;
  const el = document.getElementById("datum-valaszto");
  if (!el) return;
  el.addEventListener("click", function (ev) {
    const btn = ev.target && ev.target.closest ? ev.target.closest("button") : null;
    if (!btn || btn.disabled) return;
    if (btn.classList.contains("nap-cella")) {                 // nap kiválasztása
      el.setAttribute("data-valasztott-nap", btn.getAttribute("data-nap"));
      datum_valaszto_render();                                 // a kék kiemelés áthelyezése
      trend_nap_valt(btn.getAttribute("data-nap"));            // a dashboard nap-váltása
    } else if (btn.classList.contains("honap-lep")) {          // hónap-lépés (a kiválasztás VÁLTOZATLAN)
      const cur = el.getAttribute("data-honap") || "";
      el.setAttribute("data-honap", naptar_honap_lep(cur, btn.classList.contains("elore") ? 1 : -1));
      datum_valaszto_render();
    }
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

// ── HETI FELKAPOTT KERESÉSEK blokk — hét-logika (ISO, hétfő–vasárnap) + napi táblázat ──────────────
const HO_ROVID = ["jan.", "feb.", "márc.", "ápr.", "máj.", "jún.", "júl.", "aug.", "szept.", "okt.", "nov.", "dec."];
const NAP_NEV = ["Vasárnap", "Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat"];   // getUTCDay() index

function iso_hetszam(d) {                        // ISO 8601 hétszám (a hét csütörtökje dönt)
  const dt = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  const nap = dt.getUTCDay() || 7;              // hétfő=1 … vasárnap=7
  dt.setUTCDate(dt.getUTCDate() + 4 - nap);     // a hét csütörtökje
  const evkezd = new Date(Date.UTC(dt.getUTCFullYear(), 0, 1));
  return Math.ceil((((dt - evkezd) / 86400000) + 1) / 7);
}
function het_hetfoje(iso) {                      // egy ISO-dátum → a HETÉNEK hétfője (ISO-dátum)
  const d = new Date(Date.parse(iso + "T00:00:00Z"));
  const nap = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() - (nap - 1));
  return d.toISOString().slice(0, 10);
}
function heti_cimke(hetfo_iso) {                 // „34. hét (aug. 17–23)" / átívelő: „júl. 27 – aug. 2"
  const h = new Date(Date.parse(hetfo_iso + "T00:00:00Z"));
  const v = new Date(h.getTime() + 6 * 86400000);
  const hh = HO_ROVID[h.getUTCMonth()], vh = HO_ROVID[v.getUTCMonth()];
  const tart = (h.getUTCMonth() === v.getUTCMonth())
    ? (hh + " " + h.getUTCDate() + "–" + v.getUTCDate())
    : (hh + " " + h.getUTCDate() + " – " + vh + " " + v.getUTCDate());
  return iso_hetszam(h) + ". hét (" + tart + ")";
}
function heti_nap_cimke(iso) {                    // „Hétfő · 08-17"
  const d = new Date(Date.parse(iso + "T00:00:00Z"));
  return NAP_NEV[d.getUTCDay()] + " · " + iso.slice(5);
}
// a mért napok ISO-hetenként, LEGFRISSEBB elöl: [{hetfo, cimke, napok:[ISO]}]
function hetek_index(napok) {
  const map = {};
  napok.forEach(function (d) { const hf = het_hetfoje(d); (map[hf] = map[hf] || []).push(d); });
  return Object.keys(map).sort().reverse().map(function (hf) {
    return { hetfo: hf, cimke: heti_cimke(hf), napok: map[hf].slice().sort() };
  });
}

// a kiválasztott hét táblázata: hétfő..min(vasárnap, legfrissebb elérhető nap); hiányzó nap → „nincs adat".
async function heti_tabla_render(hetfo_iso) {
  const blokk = document.getElementById("heti-blokk");
  if (!blokk) return;
  const idx = adat["napok/index.json"];
  const napok = (idx && Array.isArray(idx.napok)) ? idx.napok.slice().sort() : [];
  const maxNap = napok.length ? napok[napok.length - 1] : null;
  const vanIndex = {}; napok.forEach(function (d) { vanIndex[d] = true; });
  const het_napjai = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(Date.parse(hetfo_iso + "T00:00:00Z") + i * 86400000).toISOString().slice(0, 10);
    if (maxNap && d > maxNap) break;                 // csak a legfrissebb elérhető napig (nincs jövő/nem-archivált)
    het_napjai.push(d);
  }
  // a hiányzó (indexben lévő, még nem cache-elt) nap-fájlok betöltése
  await Promise.all(het_napjai
    .filter(function (d) { return vanIndex[d] && !(("napok/" + d + ".json") in adat); })
    .map(function (d) {
      return json_betolt("napok/" + d + ".json").then(function (j) { adat["napok/" + d + ".json"] = j; }).catch(function () {});
    }));
  const regi = blokk.querySelector(".heti-tabla, .heti-ures"); if (regi) regi.remove();
  const tabla = document.createElement("table");
  tabla.className = "heti-tabla";
  het_napjai.forEach(function (d) {
    const tr = document.createElement("tr");
    tr.className = "heti-nap-sor";
    tr.setAttribute("data-nap", d);
    const tdN = document.createElement("td"); tdN.className = "heti-nap"; tdN.textContent = heti_nap_cimke(d);
    const tdSz = document.createElement("td"); tdSz.className = "heti-szavak";
    const napi = adat["napok/" + d + ".json"];
    const szavak = (napi && Array.isArray(napi.trendek)) ? napi.trendek.map(function (t) { return t.kifejezes; }) : [];
    tdSz.textContent = szavak.length ? szavak.join(", ") : "nincs adat";
    tr.appendChild(tdN); tr.appendChild(tdSz); tabla.appendChild(tr);
  });
  blokk.appendChild(tabla);
}

async function heti_blokk_render() {
  const valEl = document.getElementById("heti-valaszto");
  const blokk = document.getElementById("heti-blokk");
  if (!valEl || !blokk) return;
  const idx = adat["napok/index.json"];
  const napok = (idx && Array.isArray(idx.napok)) ? idx.napok.slice().sort() : [];
  if (!napok.length) {                              // nincs nap → üres állapot
    const r = blokk.querySelector(".heti-tabla, .heti-ures"); if (r) r.remove();
    const u = document.createElement("p"); u.className = "heti-ures"; u.textContent = "Még nincs napi trendlista.";
    blokk.appendChild(u); valEl.innerHTML = ""; return;
  }
  heti_valaszto_render();          // a hét-kiemelő naptár (beállítja data-valasztott-het = legfrissebb hét, ha nincs)
  heti_esemeny_kot();              // FÜGGETLEN a napi választótól: csak ezt a blokkot vezérli
  await heti_tabla_render(valEl.getAttribute("data-valasztott-het"));
}

let heti_esemeny_kotve = false;
// a heti naptár kattintás-kötése (delegált a konténeren → túléli az újrarajzolást)
function heti_esemeny_kot() {
  if (heti_esemeny_kotve) return;
  const el = document.getElementById("heti-valaszto");
  if (!el) return;
  el.addEventListener("click", function (ev) {
    const btn = ev.target && ev.target.closest ? ev.target.closest("button") : null;
    if (!btn || btn.disabled) return;
    if (btn.classList.contains("nap-cella")) {                 // egy nap → az EGÉSZ HETE
      el.setAttribute("data-valasztott-het", het_hetfoje(btn.getAttribute("data-nap")));
      heti_valaszto_render();                                  // a hét-kiemelés áthelyezése
      heti_tabla_render(el.getAttribute("data-valasztott-het"));
    } else if (btn.classList.contains("honap-lep")) {          // hónap-lépés (a kiválasztás VÁLTOZATLAN)
      const cur = el.getAttribute("data-honap") || "";
      el.setAttribute("data-honap", naptar_honap_lep(cur, btn.classList.contains("elore") ? 1 : -1));
      heti_valaszto_render();
    }
  });
  heti_esemeny_kotve = true;
}

const RENDER_HIBA_SZOVEG = "Hiba a vezérlő megjelenítésekor";
// SORREND SZÁMÍT: az intervallum-vezérlő állítja be a data-aktiv-intervallum-ot, amit a kulcsszó-blokk
// olvas; a datum-választó a TREND-BLOKK ELŐTT fut, mert a trend-blokk a legyártott <select>-hez köti a
// napváltást. Mind szinkron fn → a microtask-sorrend = a tömb sorrendje.
const RENDEREK = [
  { id: "attekinto-blokk", fn: attekinto_blokk_render },
  { id: "intervallum-vezerlo", fn: intervallum_vezerlo_render },
  { id: "kulcsszo-blokk", fn: kulcsszo_blokk_render },
  { id: "datum-valaszto", fn: datum_valaszto_render },
  { id: "idosor-blokk", fn: idosor_blokk_render },   // kategória-idősor — önálló szekció, kategoriak.json-ból (NAP-FÜGGETLEN)
  { id: "trend-blokk", fn: trend_blokk_render },
  { id: "heti-blokk", fn: heti_blokk_render },   // heti felkapott — napok/index.json-ból (a trend-blokk már betöltötte)
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
