/* Einwilligungsverwaltung (DSGVO / § 25 TDDDG).
 *
 * Grundprinzip: Inhalte, die Daten an Dritte übertragen oder Skripte nachladen,
 * stehen im HTML nur als Platzhalter und werden erst nach Einwilligung aktiviert.
 *
 *   <iframe data-consent="external" data-src="https://…" hidden></iframe>
 *   <script type="text/plain" data-consent="statistics" data-src="https://…"></script>
 *
 * Kategorien: "necessary" (immer aktiv, speichert nur die Auswahl selbst) und
 * die in CATEGORIES genannten optionalen Kategorien (hier: "external").
 * Die Auswahl liegt in localStorage (kein Cookie), Gültigkeit 6 Monate.
 */
(function () {
  "use strict";

  var KEY = "avw-consent";
  var VERSION = 1;
  var MAX_AGE = 182 * 24 * 60 * 60 * 1000;
  var CATEGORIES = ["external"];

  var banner = document.getElementById("consent");
  var modal = document.getElementById("consent-modal");
  if (!banner || !modal) return;

  var lastFocus = null;

  function read() {
    try {
      var d = JSON.parse(localStorage.getItem(KEY));
      if (d && d.v === VERSION && d.c && Date.now() - d.ts < MAX_AGE) return d.c;
    } catch (e) {}
    return null;
  }

  function write(choice) {
    try { localStorage.setItem(KEY, JSON.stringify({ v: VERSION, ts: Date.now(), c: choice })); } catch (e) {}
  }

  function activate(choice) {
    var reload = false;
    document.querySelectorAll("[data-consent]").forEach(function (el) {
      var allowed = !!choice[el.dataset.consent];
      if (el.tagName === "SCRIPT") {
        if (allowed && !el.dataset.loaded) {
          var s = document.createElement("script");
          s.src = el.dataset.src;
          s.async = true;
          el.dataset.loaded = "1";
          el.parentNode.insertBefore(s, el.nextSibling);
        } else if (!allowed && el.dataset.loaded) {
          reload = true; // geladene Skripte lassen sich nicht entladen
        }
      } else if (el.tagName === "IFRAME") {
        if (allowed) {
          if (el.getAttribute("src") !== el.dataset.src) el.setAttribute("src", el.dataset.src);
          el.hidden = false;
        } else {
          el.removeAttribute("src");
          el.hidden = true;
        }
      }
    });
    document.querySelectorAll("[data-consent-placeholder]").forEach(function (ph) {
      ph.hidden = !!choice[ph.dataset.consentPlaceholder];
    });
    return reload;
  }

  function save(choice) {
    var before = read() || {};
    write(choice);
    var needReload = activate(choice);
    banner.hidden = true;
    closeModal(true);
    if (needReload && CATEGORIES.some(function (c) { return before[c] && !choice[c]; })) location.reload();
  }

  function all(v) {
    var c = {};
    CATEGORIES.forEach(function (k) { c[k] = v; });
    return c;
  }

  function fromForm() {
    var c = {};
    CATEGORIES.forEach(function (k) {
      var box = modal.querySelector('input[name="' + k + '"]');
      c[k] = !!(box && box.checked);
    });
    return c;
  }

  function openModal() {
    var cur = read() || all(false);
    CATEGORIES.forEach(function (k) {
      var box = modal.querySelector('input[name="' + k + '"]');
      if (box) box.checked = !!cur[k];
    });
    lastFocus = document.activeElement;
    modal.hidden = false;
    var first = modal.querySelector("button, input:not(:disabled)");
    if (first) first.focus();
  }

  function closeModal(silent) {
    if (modal.hidden) return;
    modal.hidden = true;
    if (!silent && lastFocus && lastFocus.focus) lastFocus.focus();
    if (!silent && !read()) banner.hidden = false;
  }

  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-consent-action]");
    if (t) {
      var a = t.dataset.consentAction;
      if (a === "accept") save(all(true));
      else if (a === "reject") save(all(false));
      else if (a === "save") save(fromForm());
      else if (a === "settings") { banner.hidden = true; openModal(); }
      else if (a === "close") closeModal(false);
      return;
    }
    var g = e.target.closest("[data-consent-grant]");
    if (g) {
      var cur = read() || all(false);
      cur[g.dataset.consentGrant] = true;
      save(cur);
      return;
    }
    if (e.target.closest("[data-consent-open]")) { openModal(); return; }
    if (e.target === modal) closeModal(false);
  });

  document.addEventListener("keydown", function (e) {
    if (modal.hidden) return;
    if (e.key === "Escape") { closeModal(false); return; }
    if (e.key !== "Tab") return;
    var f = modal.querySelectorAll("button, input:not(:disabled), a[href]");
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  var stored = read();
  if (stored) activate(stored);
  else banner.hidden = false;
})();
