// YouTube-fül (Task 8): adatbetöltés + reg-egyesítés (CSAK másodlagos, se órás, se lánc) + render.
// Klasszikus script; a docs/js/app.js globális leaf-jeit (közös scope) hívja — app.js NEM módosul.
// A gombsor/kártya/áttekintő render az app.js megfelelő render-függvényeinek (intervallum_vezerlo_render,
// kulcsszo_blokk_render, attekinto_blokk_render — ~313-403 / 1173-1241 / 1071-1086) LEHATÁROLT átvétele
// a #youtube-* id-kre; a rajzoló/formázó leaf-eket (nyers_ablak, racs_epit, kartya_letrehoz, chart_letrehoz,
// teljes_valaszt, INTERVALLUMOK, OK_MAGYAR, TREND_SZOVEG, EGYEB_KULCS, ...) közvetlenül újrahasznosítja.
// A domén-kosarazás (DOMEN_MAGYAR/DOMEN_SORREND) NEM közös az app.js-szel: a Google-fül 9 doménjéből csak
// egeszseg+kozelet fedi a YouTube 8 doménjét, ezért a fájl SAJÁT YT_DOMEN_MAGYAR/YT_DOMEN_SORREND térképet
// definiál mind a 8 config-doménre (lásd lentebb) — a final-review kosár-összeomlás FINDING javítása.
"use strict";
(function () {
  const YT_REG = "youtube_regresszio.json", YT_NYERS = "youtube_nyers.json";
  const BLOKK = "youtube-blokk", VEZ = "youtube-intervallum-vezerlo", ATT = "youtube-attekinto";

  // YouTube-fül SAJÁT domén-térképe (a config.yaml youtube: blokk mind a 8 doménjére) — az app.js globális
  // DOMEN_MAGYAR/DOMEN_SORREND-je a Google-fül 9 doménjét ismeri, ebből csak egeszseg+kozelet fedi a YouTube
  // 8 doménjét; a maradék 6 (penzugy/haztartas/csalad/szabadido/tanulas/otthon) rájuk esne az "Egyéb" kosárba
  // (kosár-összeomlás, final-review FINDING). Az app.js EGYÉB_KULCS-át (üres-kosár tartófiók) újrahasznosítjuk,
  // de a címke/sorrend itt SAJÁT — app.js NEM módosul.
  const YT_DOMEN_MAGYAR = {
    egeszseg: "Egészség / jóllét", penzugy: "Pénzügy", kozelet: "Közélet / hír",
    haztartas: "Háztartás / megélhetés", csalad: "Család", szabadido: "Szabadidő / utazás",
    tanulas: "Tanulás", otthon: "Otthon / energia",
  };
  const YT_DOMEN_SORREND = ["egeszseg", "penzugy", "kozelet", "haztartas", "csalad", "szabadido", "tanulas", "otthon", null];

  async function yt_init() {
    // fájlonkénti izoláció (app.js blokk_betolt mintája, Task 5): egy hiányzó fájl se akassza meg a másikat
    const fajlok = [YT_REG, YT_NYERS];
    const eredmenyek = await Promise.allSettled(fajlok.map(function (rel) {
      return json_betolt(rel).then(function (json) { adat[rel] = json; });
    }));
    const hibak = [];
    eredmenyek.forEach(function (e, i) {
      if (e.status === "rejected") hibak.push((e.reason && e.reason.message) || fajlok[i]);
    });
    if (hibak.length) hiba_kiir(BLOKK, hibak);
    yt_render();
  }

  // egyesített reg: per (szó, intervallum) a MÁSODLAGOS regresszióból (nincs órás, nincs lánc a YouTube-adatban),
  // _forras/_racs beállítva a rajzoló leaf-eknek (nyers_ablak/racs_epit/kartya_letrehoz). A visszaadott alak
  // FLAT szó->szoreg map (nem {kulcsszavak:...} burok) — ezt fogyasztja az itt lévő render-hármas.
  function yt_egyesitett_reg() {
    const reg = (adat[YT_REG] && adat[YT_REG].kulcsszavak) || {};
    const ki = {};
    Object.keys(reg).forEach(function (szo) {
      const szoreg = reg[szo];
      const ivk = {};
      Object.keys(szoreg.intervallumok || {}).forEach(function (k) {
        const cella = szoreg.intervallumok[k];
        const racs = cella.racs || szoreg.racs;
        // a heti rácson a "kevés pont" STRUKTURÁLIS (az ablak túl rövid a heti mintavételhez), nem adathiány —
        // ugyanaz a fordítás, mint a Google-fül egyesitett_reg-jében (app.js:268-269, keves_pont+het→rovid_het_ablak)
        const ok = (!cella.ervenyes && cella.ok === "keves_pont" && racs === "het") ? "rovid_het_ablak" : cella.ok;
        ivk[k] = Object.assign({}, cella, { ok: ok, _forras: YT_NYERS, _racs: racs });
      });
      ki[szo] = Object.assign({}, szoreg, { intervallumok: ivk });
    });
    return ki;
  }

  function yt_render() {
    const egyesitett = yt_egyesitett_reg();
    yt_vezerlo_render(egyesitett);   // gombsor a #youtube-intervallum-vezerlo-ba
    yt_blokk_render(egyesitett);     // kosár-csoportosított kártyák a #youtube-blokk-ba
    yt_attekinto_render(egyesitett); // trend-panel a #youtube-attekinto-ba
  }

  // ── gombsor (app.js intervallum_vezerlo_render lehatárolt átvétele) ──────────────────────────
  function yt_vezerlo_render(reg) {
    const el = document.getElementById(VEZ);
    const blokk = document.getElementById(BLOKK);
    if (!el) return;
    if (!reg || !Object.keys(reg).length) {
      if (blokk) blokk.removeAttribute(ATTR.aktiv);
      ures_allapot(el, URES_NINCS_ADAT);
      return;
    }
    const allapotok = INTERVALLUMOK.map(function (iv) {
      const a = intervallum_allapot(reg, iv.kulcs);
      return { kulcs: iv.kulcs, cimke: iv.cimke, hossz: iv.hossz, ervenyes: a.ervenyes, ok: a.ok };
    });
    const ervenyesek = allapotok.filter(function (a) { return a.ervenyes; });
    el.textContent = "";
    if (!ervenyesek.length) {
      if (blokk) blokk.removeAttribute(ATTR.aktiv);
      const fejlec = document.createElement("p");
      fejlec.className = OSZT.ures;
      fejlec.textContent = URES_NINCS_ERVENYES;
      el.appendChild(fejlec);
    } else if (blokk) {
      // ALAPNEZET: a kezdő nézet a TELJES időszak (a Google-fül mintájára) — yt_render csak egyszer fut init-kor.
      blokk.setAttribute(ATTR.aktiv, TELJES_KULCS);
    }
    if (ervenyesek.length) {
      const tetel = document.createElement("div");
      tetel.className = OSZT.intervallum_tetel;
      const sor = document.createElement("div");
      sor.className = OSZT.intervallum_gomb_sor;
      const gomb = document.createElement("button");
      gomb.setAttribute(ATTR.intervallum, TELJES_KULCS);
      gomb.textContent = TELJES_CIMKE;
      gomb.setAttribute("aria-pressed", "false");
      gomb.addEventListener("click", function () { yt_aktiv_intervallum_valt(TELJES_KULCS); });
      sor.appendChild(gomb);
      tetel.appendChild(sor);
      const magy = document.createElement("div");
      magy.className = OSZT.gomb_magyarazat;
      magy.textContent = TELJES_MAGYARAZAT;
      tetel.appendChild(magy);
      el.appendChild(tetel);
    }
    allapotok.forEach(function (a) {
      const tetel = document.createElement("div");
      tetel.className = OSZT.intervallum_tetel;
      const sor = document.createElement("div");
      sor.className = OSZT.intervallum_gomb_sor;
      const gomb = document.createElement("button");
      gomb.setAttribute(ATTR.intervallum, a.kulcs);
      gomb.textContent = a.cimke;
      if (a.ervenyes) {
        gomb.setAttribute("aria-pressed", "false");
        gomb.addEventListener("click", function () { yt_aktiv_intervallum_valt(a.kulcs); });
        sor.appendChild(gomb);
      } else {
        gomb.disabled = true;
        sor.appendChild(gomb);
        const ok = document.createElement("span");
        ok.className = "ok";
        ok.textContent = OK_MAGYAR[a.ok] || a.ok;
        sor.appendChild(ok);
      }
      tetel.appendChild(sor);
      const magy = document.createElement("div");
      magy.className = OSZT.gomb_magyarazat;
      magy.textContent = GOMB_MAGYARAZAT[a.kulcs] || "";
      tetel.appendChild(magy);
      el.appendChild(tetel);
    });
    yt_aria_szinkron();
  }

  // az aria-pressed a #youtube-blokk data-aktiv-intervallum-ból DERIVÁLT (egyetlen igazságforrás)
  function yt_aria_szinkron() {
    const blokk = document.getElementById(BLOKK);
    const aktiv = blokk ? blokk.getAttribute(ATTR.aktiv) : null;
    document.querySelectorAll("#" + VEZ + " button[" + ATTR.intervallum + "]").forEach(function (g) {
      if (g.disabled) return;
      g.setAttribute("aria-pressed", g.getAttribute(ATTR.intervallum) === aktiv ? "true" : "false");
    });
  }

  // intervallum-váltás: a data-aktiv-intervallum egy helyen íródik, majd aria-szinkron + kártya-újrarajzolás
  function yt_aktiv_intervallum_valt(kulcs) {
    const blokk = document.getElementById(BLOKK);
    if (!blokk) return;
    blokk.setAttribute(ATTR.aktiv, kulcs);
    yt_aria_szinkron();
    yt_blokk_render(yt_egyesitett_reg());   // a chart_takarit() a régi Chart-példányokat destroy-olja
  }

  // ── kosár-csoportosított kártyák (app.js kulcsszo_blokk_render lehatárolt átvétele) ─────────
  function yt_blokk_render(reg) {
    const blokk = document.getElementById(BLOKK);
    if (!blokk) return;
    chart_takarit();
    blokk.querySelectorAll("." + OSZT.frissesseg + ", ." + OSZT.csoport).forEach(function (e) { e.remove(); });

    const aktiv = blokk.getAttribute(ATTR.aktiv);
    if (!aktiv || !reg || !Object.keys(reg).length) return;   // korai kilépés: nincs aktív intervallum → nincs chart

    const csoportok = {};
    Object.keys(reg).forEach(function (szo) {
      const d = reg[szo].domen;
      const kulcs = YT_DOMEN_MAGYAR[d] ? d : EGYEB_KULCS;
      (csoportok[kulcs] = csoportok[kulcs] || []).push(szo);
    });

    const rajzolhatok = [];
    let adat_veg = null;
    YT_DOMEN_SORREND.forEach(function (d) {
      const kulcs = d === null ? EGYEB_KULCS : d;
      const szavak = csoportok[kulcs];
      if (!szavak || !szavak.length) return;
      const cs = document.createElement("div");
      cs.className = OSZT.csoport;
      cs.setAttribute("data-domen", d === null ? "egyeb" : d);
      const h3 = document.createElement("h3");
      h3.className = OSZT.fejlec;
      h3.textContent = d === null ? "Egyéb" : YT_DOMEN_MAGYAR[d];
      cs.appendChild(h3);
      szavak.forEach(function (szo) {
        const k = kartya_letrehoz(szo, reg[szo], aktiv);
        cs.appendChild(k);
        if (k.getAttribute(ATTR.drawable) === "true") {
          rajzolhatok.push(k);
          if (!adat_veg) adat_veg = k.getAttribute(ATTR.adat_veg);
        } else {
          // YouTube-fül DOM-szerződés (e2e): a kártya nem-rajzolható okszövege .ok osztályt is kap
          // (app.js kartya_letrehoz csak .ures-t ad — ez utólagos, nem-invazív kiegészítés, app.js NEM módosul)
          const uresP = k.querySelector("." + OSZT.ures);
          if (uresP) uresP.classList.add("ok");
        }
      });
      blokk.appendChild(cs);
    });

    // TELJES-NEZET: per-szó tengely (a chart_letrehoz a _teljes_mod flaget olvassa)
    if (aktiv === TELJES_KULCS) {
      rajzolhatok.forEach(function (k) { k._teljes_mod = true; });
    }

    if (adat_veg) {
      const f = document.createElement("p");
      f.className = OSZT.frissesseg;
      f.textContent = frissesseg_szoveg(aktiv, adat_veg);
      blokk.appendChild(f);
    }
    lusta_megfigyel(rajzolhatok);
  }

  // ── trend-panel (app.js attekinto_blokk_render/attekinto_panel_kitolt/attekinto_kartya lehatárolt
  //    átvétele, "trend" módban): teljes_valaszt(szoreg).iv.irany → TREND_SZOVEG[irany]. A chip-ugrás a
  //    #youtube-blokk-ra megy (nem a Google #kulcsszo-blokk-jára, mint az app.js eredetiben). ────────────
  function yt_attekinto_render(reg) {
    const blokk = document.getElementById(ATT);
    if (!blokk) return;
    blokk.textContent = "";
    const csoportok = {};
    Object.keys(reg || {}).forEach(function (szo) {
      const d = reg[szo].domen;
      const kulcs = YT_DOMEN_MAGYAR[d] ? d : EGYEB_KULCS;
      (csoportok[kulcs] = csoportok[kulcs] || []).push(szo);
    });
    if (reg && Object.keys(reg).length) {
      const lista = document.createElement("div");
      lista.className = "attekinto-lista";
      YT_DOMEN_SORREND.forEach(function (d) {
        const kulcs = d === null ? EGYEB_KULCS : d;
        const szavak = csoportok[kulcs];
        if (!szavak || !szavak.length) return;
        const sor = document.createElement("div");
        sor.className = "attekinto-sor";
        sor.setAttribute("data-domen", d === null ? "egyeb" : d);
        const cimke = document.createElement("span");
        cimke.className = "attekinto-domen";
        cimke.textContent = d === null ? "Egyéb" : YT_DOMEN_MAGYAR[d];
        sor.appendChild(cimke);
        const chipek = document.createElement("span");
        chipek.className = "attekinto-chipek";
        szavak.forEach(function (szo) {
          chipek.appendChild(yt_attekinto_kartya(szo, reg[szo]));
        });
        sor.appendChild(chipek);
        lista.appendChild(sor);
      });
      blokk.appendChild(lista);
    }
    blokk.appendChild(attekinto_magyarazat_epit("trend"));
  }

  function yt_attekinto_kartya(szo, szoreg) {
    const k = document.createElement("span");
    k.className = "attekinto-kartya";
    k.setAttribute("data-kulcsszo", szo);
    k.setAttribute("role", "link");
    k.setAttribute("tabindex", "0");
    function ugras() {
      const cel = document.querySelector("#" + BLOKK + " ." + OSZT.kartya + "[" + ATTR.kulcsszo + '="' + szo.replace(/"/g, '\\"') + '"]');
      if (cel) cel.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    k.addEventListener("click", ugras);
    k.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ugras(); }
    });
    const tv = teljes_valaszt(szoreg);
    const ir = tv && tv.iv && tv.iv.irany;
    let cim = null;
    if (ir && TREND_SZOVEG[ir]) {
      const ikon = document.createElement("span");
      ikon.className = "attekinto-ikon";
      ikon.setAttribute("data-trend", ir);
      k.appendChild(ikon);
      cim = TREND_SZOVEG[ir];
    }
    const nev = document.createElement("span");
    nev.className = "attekinto-szo";
    nev.textContent = szo;
    k.appendChild(nev);
    if (cim) { k.setAttribute("title", cim); k.setAttribute("aria-label", cim); }
    return k;
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", yt_init);
  else yt_init();
})();
