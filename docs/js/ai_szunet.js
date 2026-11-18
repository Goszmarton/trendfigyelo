"use strict";
// AI-elemzések SZÜNETELTETÉSE — a docs/data/ai_szunet.json alapján jelzősávot tesz a lap fejléce alá.
// A script-tag `data-tipus` attribútuma mondja meg, melyik elemzésről van szó (napi|heti|havi|ugyek|attekinto).
// A meglévő (korábbi) elemzések megjelenítése VÁLTOZATLAN. Fail-soft: hiányzó/hibás fájl → nincs sáv.

const AI_SZUNET_NEV = { napi: "napi elemzés", heti: "heti értékelés", havi: "havi elemzés", ugyek: "ügy-elemzés" };
const AI_SZUNET_HONAP = ["január", "február", "március", "április", "május", "június", "július",
  "augusztus", "szeptember", "október", "november", "december"];

function ai_szunet_datum(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
  if (!m) return "";
  return `${m[1]}. ${AI_SZUNET_HONAP[Number(m[2]) - 1]} ${Number(m[3])}.`;
}

// Tiszta függvény: a sáv szövege, vagy null, ha az adott lapon nincs szünet.
function ai_szunet_szoveg(adat, tipus) {
  const sz = (adat && adat.szunetel) || {};
  const ota = ai_szunet_datum(adat && adat.ota);
  const ota_resz = ota ? ` (${ota} óta)` : "";
  if (tipus === "attekinto") {
    const tipusok = ["napi", "heti", "havi", "ugyek"].filter(t => sz[t] === true);
    if (!tipusok.length) return null;
    return (adat.uzenet || "Az AI által generált elemzések készítése jelenleg szünetel.") + (ota ? ` Szünetel ${ota} óta.` : "");
  }
  if (sz[tipus] !== true) return null;
  return `Az AI által generált ${AI_SZUNET_NEV[tipus]} készítése jelenleg szünetel${ota_resz}. `
    + "Új elemzés nem készül, a korábbiak továbbra is böngészhetők. Az adatgyűjtés zavartalanul folytatódik.";
}

async function ai_szunet_init() {
  const tag = document.currentScript;
  const tipus = tag && tag.dataset.tipus;
  let adat = null;
  try {
    const r = await fetch("data/ai_szunet.json", { cache: "no-cache" });
    if (r.ok) adat = await r.json();
  } catch (e) { adat = null; }
  const szoveg = ai_szunet_szoveg(adat, tipus);
  if (!szoveg) return;
  const sav = document.createElement("div");
  sav.className = "ai-szunet-sav";
  sav.id = "ai-szunet-sav";
  sav.setAttribute("role", "status");
  const cim = document.createElement("strong");
  cim.textContent = "Szünetel";
  sav.appendChild(cim);
  sav.appendChild(document.createTextNode(" " + szoveg));
  const fejlec = document.querySelector("header.fejlec-doboz");
  if (fejlec) fejlec.insertAdjacentElement("afterend", sav);
  else document.body.prepend(sav);
  // a nyitóoldalon a (már nem frissülő) „mai kiemelt" helyett a sáv áll
  if (tipus === "attekinto" && adat.szunetel && adat.szunetel.napi === true) {
    const kiemelt = document.getElementById("nyitooldal-kiemelt");
    if (kiemelt) kiemelt.hidden = true;
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { ai_szunet_szoveg, ai_szunet_datum };
} else {
  ai_szunet_init();
}
