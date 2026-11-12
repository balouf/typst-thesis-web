// web.js — behaviour of a multi-page site built with web.typ (same version).
// Everything here is an enhancement: pages read fine without it.
//   1. theme toggle (light / dark / auto)
//   2. sidebars as overlays on narrow screens
//   3. search (Pagefind index in assets/pagefind/, loaded on first use)
//   4. keyboard shortcuts
//   5. scroll-spy for the page table of contents
(function () {
  "use strict";

  // This file lives in <site>/assets/: the site root is one level up.
  var scriptUrl = document.currentScript ? document.currentScript.src : location.href;
  var french = (document.documentElement.lang || "").toLowerCase().indexOf("fr") === 0;
  var T = french
    ? { search: "Rechercher…", none: "Aucun résultat.", unavailable: "Index de recherche indisponible.", error: "Erreur de recherche.", untitled: "Sans titre", light: "Thème : clair", dark: "Thème : sombre", auto: "Thème : automatique" }
    : { search: "Search…", none: "No results found.", unavailable: "Search index not available.", error: "Search error.", untitled: "Untitled", light: "Theme: light", dark: "Theme: dark", auto: "Theme: auto" };

  function make(tag, props, parent) {
    var el = document.createElement(tag);
    for (var k in props) el[k] = props[k];
    if (parent) parent.appendChild(el);
    return el;
  }

  // ---------------------------------------------------------------------------
  // 1. Theme
  // ---------------------------------------------------------------------------

  var THEMES = ["light", "dark", "auto"];
  var themeBtn = document.querySelector(".theme-toggle");
  var mode = localStorage.getItem("theme") || "auto";
  var osDark = matchMedia("(prefers-color-scheme: dark)");

  function applyTheme(next) {
    mode = next;
    localStorage.setItem("theme", mode);
    document.documentElement.dataset.theme = mode === "auto" ? (osDark.matches ? "dark" : "light") : mode;
    if (themeBtn) themeBtn.title = T[mode];
  }

  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      applyTheme(THEMES[(THEMES.indexOf(mode) + 1) % THEMES.length]);
    });
  }
  osDark.addEventListener("change", function () { if (mode === "auto") applyTheme("auto"); });
  applyTheme(mode);

  // ---------------------------------------------------------------------------
  // 2. Sidebars
  // ---------------------------------------------------------------------------

  var sidebarLeft = document.querySelector(".sidebar-left");
  var sidebarRight = document.querySelector(".sidebar-right");
  var backdrop = make("div", { className: "sidebar-backdrop" }, document.body);

  function closeSidebars() {
    if (sidebarLeft) sidebarLeft.classList.remove("open");
    if (sidebarRight) sidebarRight.classList.remove("open");
    backdrop.classList.remove("visible");
  }

  function bindToggle(id, sidebar) {
    var btn = document.getElementById(id);
    if (!btn || !sidebar) return;
    btn.addEventListener("click", function () {
      var opening = !sidebar.classList.contains("open");
      closeSidebars();
      if (opening) {
        sidebar.classList.add("open");
        backdrop.classList.add("visible");
      }
    });
  }

  bindToggle("sidebar-toggle-left", sidebarLeft);
  bindToggle("sidebar-toggle-right", sidebarRight);
  backdrop.addEventListener("click", closeSidebars);
  window.addEventListener("resize", function () { if (window.innerWidth > 1200) closeSidebars(); });

  // The current entry of a long navigation should be visible on load.
  var active = document.querySelector(".global-nav li.active");
  if (active && sidebarLeft) active.scrollIntoView({ block: "nearest" });

  // ---------------------------------------------------------------------------
  // 3. Search
  // ---------------------------------------------------------------------------

  var searchTrigger = document.querySelector(".search-trigger");
  var overlay = null, input = null, results = null, pagefind = null, timer = null;

  function buildOverlay() {
    overlay = make("div", { className: "search-overlay" }, document.body);
    var dialog = make("div", { className: "search-dialog" }, overlay);
    var header = make("div", { className: "search-header" }, dialog);
    input = make("input", { type: "text", className: "search-input", placeholder: T.search, autocomplete: "off" }, header);
    make("kbd", { className: "search-close", textContent: "Esc" }, header).addEventListener("click", closeSearch);
    results = make("div", { className: "search-results" }, dialog);
    overlay.addEventListener("click", function (e) { if (e.target === overlay) closeSearch(); });
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () { runSearch(input.value.trim()); }, 200);
    });
  }

  function searchOpen() { return overlay && overlay.classList.contains("visible"); }

  function openSearch() {
    if (!overlay) buildOverlay();
    overlay.classList.add("visible");
    input.value = "";
    results.replaceChildren();
    input.focus();
    loadPagefind();
  }

  function closeSearch() { if (overlay) overlay.classList.remove("visible"); }

  async function loadPagefind() {
    if (pagefind) return;
    try {
      pagefind = await import(new URL("pagefind/pagefind.js", scriptUrl).href);
      await pagefind.options({ baseUrl: new URL("..", scriptUrl).pathname });
      await pagefind.init();
    } catch (e) {
      pagefind = null;
      console.warn("Pagefind not available:", e);
    }
  }

  function message(text) {
    results.replaceChildren(make("div", { className: "search-no-results", textContent: text }));
  }

  function resultLink(url, pageTitle, title, excerpt) {
    var a = make("a", { className: "search-result", href: url });
    if (title !== pageTitle) make("div", { className: "search-result-page", textContent: pageTitle }, a);
    make("div", { className: "search-result-title", textContent: title }, a);
    // Pagefind excerpts are HTML (escaped text with <mark> around matches).
    make("div", { className: "search-result-excerpt", innerHTML: excerpt || "" }, a);
    return a;
  }

  function runSearch(query) {
    if (!query || query.length < 2) { results.replaceChildren(); return; }
    if (!pagefind) { message(T.unavailable); return; }
    pagefind.search(query).then(function (found) {
      if (!found || !found.results || found.results.length === 0) { message(T.none); return; }
      return Promise.all(found.results.slice(0, 8).map(function (r) { return r.data(); })).then(function (pages) {
        var links = [];
        pages.forEach(function (data) {
          var pageTitle = (data.meta && data.meta.title) || T.untitled;
          var subs = data.sub_results && data.sub_results.length ? data.sub_results : [data];
          subs.forEach(function (sub) {
            if (links.length < 12) links.push(resultLink(sub.url || data.url || "#", pageTitle, sub.title || pageTitle, sub.excerpt));
          });
        });
        results.replaceChildren.apply(results, links);
      });
    }).catch(function () { message(T.error); });
  }

  if (searchTrigger) searchTrigger.addEventListener("click", openSearch);

  // ---------------------------------------------------------------------------
  // 4. Keyboard
  // ---------------------------------------------------------------------------

  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "k" && searchTrigger) {
      e.preventDefault();
      if (searchOpen()) closeSearch(); else openSearch();
    }
    if (e.key === "Escape") {
      if (searchOpen()) closeSearch(); else closeSidebars();
    }
  });

  // ---------------------------------------------------------------------------
  // 5. Scroll-spy
  // ---------------------------------------------------------------------------

  var spied = [];
  document.querySelectorAll(".local-toc a").forEach(function (link) {
    // Typst may write the link as "page.html#id" rather than "#id".
    var target = link.hash ? document.getElementById(decodeURIComponent(link.hash.slice(1))) : null;
    if (target) spied.push({ link: link, target: target });
  });

  if (spied.length > 0) {
    var topbar = document.querySelector(".topbar");
    var offset = (topbar ? topbar.offsetHeight : 56) + 16;
    var ticking = false;

    function updateSpy() {
      ticking = false;
      var current = null;
      spied.forEach(function (s) {
        s.link.classList.remove("active");
        if (s.target.getBoundingClientRect().top <= offset) current = s;
      });
      if (current) current.link.classList.add("active");
    }

    window.addEventListener("scroll", function () {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(updateSpy);
      }
    });
    updateSpy();
  }
})();
