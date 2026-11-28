/* Keret: mobil fiókmenü-kapcsoló (a gomb aria-expanded-et és a body.keret-menu-nyitva osztályt váltja). */
function keret_menu_init() {
  var gomb = document.getElementById("keret-menugomb");
  if (!gomb) return;
  var fatyol = document.createElement("div");
  fatyol.className = "keret-fatyol";
  fatyol.addEventListener("click", function () { allit(false); });
  document.body.appendChild(fatyol);
  function allit(nyitva) {
    gomb.setAttribute("aria-expanded", nyitva ? "true" : "false");
    document.body.classList.toggle("keret-menu-nyitva", nyitva);
  }
  gomb.addEventListener("click", function () {
    allit(gomb.getAttribute("aria-expanded") !== "true");
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && gomb.getAttribute("aria-expanded") === "true") { allit(false); gomb.focus(); }
  });
}
keret_menu_init();
