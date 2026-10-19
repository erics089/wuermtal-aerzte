/* Würmtal Ärzte – schlanke Interaktion ohne Abhängigkeiten. */
(function () {
  "use strict";

  /* Mobile Navigation */
  var btn = document.querySelector(".menu-btn");
  var nav = document.getElementById("site-nav");
  if (btn && nav) {
    btn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      btn.setAttribute("aria-expanded", String(open));
    });
  }

  /* Arztsuche: Freitext + Ort + Fachgebiet */
  var list = document.getElementById("results");
  if (!list) return;

  var cards = Array.prototype.slice.call(list.querySelectorAll(".card"));
  var input = document.getElementById("q");
  var count = document.getElementById("count");
  var empty = document.getElementById("empty");
  var reset = document.getElementById("reset");
  var state = { q: "", ort: "", fach: "" };

  function norm(s) {
    return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ß/g, "ss");
  }

  function apply() {
    var q = norm(state.q).trim();
    var shown = 0;
    cards.forEach(function (c) {
      var ok = (!q || norm(c.dataset.text).indexOf(q) !== -1) &&
               (!state.ort || c.dataset.ort === state.ort) &&
               (!state.fach || (" " + c.dataset.fach + " ").indexOf(" " + state.fach + " ") !== -1);
      c.hidden = !ok;
      if (ok) shown++;
    });
    count.textContent = shown + " von " + cards.length + " Einträgen";
    empty.hidden = shown !== 0;
    reset.hidden = !(state.q || state.ort || state.fach);
    document.querySelectorAll("[data-filter]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(state[b.dataset.filter] === b.dataset.value));
    });
  }

  document.querySelectorAll("[data-filter]").forEach(function (b) {
    b.addEventListener("click", function () {
      var k = b.dataset.filter;
      state[k] = state[k] === b.dataset.value ? "" : b.dataset.value;
      apply();
    });
  });
  input.addEventListener("input", function () { state.q = input.value; apply(); });
  input.form.addEventListener("submit", function (e) { e.preventDefault(); });
  document.querySelectorAll("[data-reset]").forEach(function (b) {
    b.addEventListener("click", function () {
      state = { q: "", ort: "", fach: "" };
      input.value = "";
      apply();
    });
  });

  /* Startwerte aus ?q= oder #fachgebiet-Slug */
  try {
    var p = new URLSearchParams(location.search);
    if (p.get("q")) { state.q = p.get("q"); input.value = state.q; }
    if (p.get("ort")) state.ort = p.get("ort");
  } catch (e) {}
  var h = location.hash.replace("#", "");
  if (h && document.querySelector('[data-filter="fach"][data-value="' + h + '"]')) state.fach = h;
  apply();
})();
