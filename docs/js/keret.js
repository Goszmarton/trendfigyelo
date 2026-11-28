/* Keret: mobil fiókmenü-kapcsoló (a gomb aria-expanded-et és a body.keret-menu-nyitva osztályt váltja). */
function keret_menu_init() {
  var gomb = document.getElementById("keret-menugomb");
  if (!gomb) return;
  var fatyol = document.createElement("div");
  fatyol.className = "keret-fatyol";
  fatyol.addEventListener("click", function () { allit(false); });
  document.body.appendChild(fatyol);
  // a fiók a (sticky) felső sáv ALATT kezdődik: a sáv alsó széle (mobilon 2 sorba törhet, görgetéskor a tetejére tapad) CSS-változóba kerül
  function sav_magassag() {
    var felso = document.getElementById("keret-felso");
    if (felso) document.documentElement.style.setProperty("--keret-felso-h", Math.ceil(felso.getBoundingClientRect().bottom) + "px");
  }
  function allit(nyitva) {
    if (nyitva) sav_magassag();
    gomb.setAttribute("aria-expanded", nyitva ? "true" : "false");
    document.body.classList.toggle("keret-menu-nyitva", nyitva);
    if (nyitva) {
      var elso = document.querySelector("#fomenu a");
      if (elso) elso.focus();
    }
  }
  window.addEventListener("resize", sav_magassag);
  window.addEventListener("scroll", function () { if (document.body.classList.contains("keret-menu-nyitva")) sav_magassag(); }, { passive: true });
  gomb.addEventListener("click", function () {
    allit(gomb.getAttribute("aria-expanded") !== "true");
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && gomb.getAttribute("aria-expanded") === "true") { allit(false); gomb.focus(); }
  });
}

/* ---- Felső sáv: breadcrumb, gyűjtési idők, állapot-pill, menü-badge-ek ---- */
// Budapest-idő részei egy Date-ből.
function keret_bp_reszek(d) {
  const f = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Budapest", year: "numeric", month: "2-digit",
    day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  const o = {};
  f.formatToParts(d).forEach(function (p) { o[p.type] = p.value; });
  return { ev: Number(o.year), ho: Number(o.month), nap: Number(o.day), ora: o.hour, perc: o.minute };
}

// Régi, számszerű forma: „ÉÉÉÉ. HH. NN. ÓÓ:PP" (Budapest-idő); a `most` paraméter API-stabilitás miatt marad.
function keret_ido_szoveg(iso, most) {
  if (!iso) return "–";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "–";
  const a = keret_bp_reszek(d);
  return keret_nap_szoveg(a) + " " + a.ora + ":" + a.perc;
}

function keret_nap_szoveg(r) {
  return r.ev + ". " + String(r.ho).padStart(2, "0") + ". " + String(r.nap).padStart(2, "0") + ".";
}

// A pill állapotához mért (legrégebbi) utolsó gyűjtés napja; hiányzó/hibás -> "".
function keret_pill_datum(iso_lista) {
  let regi = null;
  for (let i = 0; i < iso_lista.length; i++) {
    const t = iso_lista[i] ? new Date(iso_lista[i]).getTime() : NaN;
    if (isNaN(t)) return "";
    if (regi === null || t < regi) regi = t;
  }
  return regi === null ? "" : keret_nap_szoveg(keret_bp_reszek(new Date(regi)));
}

function keret_pill(iso_lista, most) {
  let regi = null;
  for (let i = 0; i < iso_lista.length; i++) {
    const t = iso_lista[i] ? new Date(iso_lista[i]).getTime() : NaN;
    if (isNaN(t)) return null;
    if (regi === null || t < regi) regi = t;
  }
  if (regi === null) return null;
  const ora = (most.getTime() - regi) / 3600000;
  if (ora <= 26) return { allapot: "ok", szoveg: "Gyűjtés rendben" };
  if (ora <= 48) return { allapot: "figy", szoveg: "Gyűjtés késik" };
  return { allapot: "hiba", szoveg: "Gyűjtés hiba" };
}

async function keret_json(url) {
  try {
    const r = await fetch(url + "?v=" + Date.now(), { cache: "no-cache" });
    return r.ok ? await r.json() : null;
  } catch (e) { return null; }
}

function keret_elem(tag, osztaly, szoveg) {
  const e = document.createElement(tag);
  if (osztaly) e.className = osztaly;
  if (szoveg !== undefined) e.textContent = szoveg;
  return e;
}

function keret_breadcrumb(felso) {
  const link = document.querySelector("#fomenu a.aktiv, #fomenu a[aria-current='page']");
  if (!link) return;
  const csoport = link.closest(".fomenu-csoport");
  const cimke = csoport && csoport.querySelector(".fomenu-cimke");
  const szoveg = (cimke ? cimke.textContent.trim() + " / " : "") + link.textContent.trim();
  felso.appendChild(keret_elem("div", "keret-morzsa", szoveg));
}

function keret_idok(felso, google_iso, youtube_iso, most) {
  const dob = keret_elem("div", "keret-idok");
  [["Google", google_iso, "google"], ["YouTube", youtube_iso, "youtube"]].forEach(function (x) {
    const s = keret_elem("span", "keret-ido");
    s.appendChild(keret_elem("i", "keret-potty keret-potty--" + x[2]));
    s.appendChild(document.createTextNode(x[0] + ": " + keret_ido_szoveg(x[1], most)));
    dob.appendChild(s);
  });
  felso.appendChild(dob);
}

function keret_ota_szoveg(ota) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(ota || "");
  return m ? m[1] + ". " + m[2] + ". " + m[3] + ". óta" : "";
}

// Állapot-pill: pötty + felirat + dátum (szöveg vagy meglévő elem), a fejléc ELSŐ gyereke.
function keret_pill_beszur(pill, datum) {
  const fejlec = document.querySelector("header.fejlec-doboz");
  if (!fejlec) return;
  const div = keret_elem("div", "keret-pill keret-pill--" + pill.allapot);
  div.appendChild(keret_elem("i", "keret-pill-potty"));
  div.appendChild(keret_elem("span", "keret-pill-szoveg", pill.szoveg));
  if (datum && datum.nodeType) div.appendChild(datum);
  else if (datum) div.appendChild(keret_elem("span", "keret-pill-datum", datum));
  fejlec.insertBefore(div, fejlec.firstChild);
}

async function keret_init() {
  const oldal = document.body.getAttribute("data-keret-oldal");
  if (!oldal) return;
  const most = new Date();
  const felso = document.getElementById("keret-felso");
  const radar = document.getElementById("radar-idosav");
  // a Radar-idősáv (szövegét később a bovites.js írja) osztállyal válik pill-lé
  if (radar && (oldal === "valtozasok" || oldal === "kapcsolodo" || oldal === "ugyek")) {
    radar.classList.add("keret-pill", "keret-pill--semleges");
  }
  const [leg, yt, szunet, elm, ugy] = await Promise.all([
    keret_json("data/legfrissebb.json"), keret_json("data/youtube_regresszio.json"),
    keret_json("data/ai_szunet.json"), keret_json("data/elmozdulas.json"), keret_json("data/ugyek.json")]);
  const g_iso = (leg && leg.frissitve) || null, y_iso = (yt && yt.szamitva_utc) || null;
  if (felso) { keret_breadcrumb(felso); keret_idok(felso, g_iso, y_iso, most); }

  const szunetel = function (t) { return !!(szunet && szunet.szunetel && szunet.szunetel[t] === true); };
  const ota = szunet && keret_ota_szoveg(szunet.ota);
  let p = null, lista = [];
  if (oldal === "google") p = keret_pill([g_iso], most), lista = [g_iso];
  else if (oldal === "youtube") p = keret_pill([y_iso], most), lista = [y_iso];
  else if (oldal === "attekinto") p = keret_pill([g_iso, y_iso], most), lista = [g_iso, y_iso];
  if (p) keret_pill_beszur(p, keret_pill_datum(lista));
  if ((oldal === "napi" || oldal === "heti" || oldal === "havi") && szunetel(oldal)) {
    keret_pill_beszur({ allapot: "figy", szoveg: "Szünetel" }, ota || "");
  }
  if (oldal === "ugyek" && szunetel("ugyek")) {
    // a Radar-idősáv elem maga költözik a pillbe (a szövegét később ugyanebbe a node-ba írja a bovites.js)
    keret_pill_beszur({ allapot: "figy", szoveg: "Szünetel" }, radar || ota || "");
    if (radar) { radar.classList.remove("keret-pill", "keret-pill--semleges"); radar.classList.add("keret-pill-datum"); }
  }

  const badge = function (kulcs, ertek) {
    const l = document.querySelector('#fomenu a[data-keret-badge="' + kulcs + '"]');
    if (!l) return;
    if (ertek) l.setAttribute("data-badge", String(ertek)); else l.removeAttribute("data-badge");
  };
  badge("valtozasok", elm && Array.isArray(elm.szokatlan_lista) ? elm.szokatlan_lista.length : 0);
  badge("ugyek", ugy && Array.isArray(ugy.ugyek) ? ugy.ugyek.length : 0);
  ["napi", "heti", "havi"].forEach(function (t) { badge(t, szunetel(t) ? "⏸" : 0); });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { keret_ido_szoveg, keret_pill, keret_pill_datum, keret_ota_szoveg };
} else {
  keret_menu_init();
  keret_init();
}
