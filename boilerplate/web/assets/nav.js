(function () {
  "use strict";

  // =========================================================================
  // 1. Theme toggle (light → dark → auto → light)
  // =========================================================================

  var THEMES = ["light", "dark", "auto"];
  var THEME_ICONS = {
    light: "\u2600\uFE0F",  // ☀️
    dark: "\uD83C\uDF19",   // 🌙
    auto: "\uD83D\uDD04",   // 🔄
  };

  var themeBtn = document.querySelector(".theme-toggle");
  var storedMode = localStorage.getItem("theme") || "auto";

  function resolveTheme(mode) {
    if (mode === "auto") {
      return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    return mode;
  }

  function applyTheme(mode) {
    storedMode = mode;
    localStorage.setItem("theme", mode);
    document.documentElement.dataset.theme = resolveTheme(mode);
    if (themeBtn) {
      themeBtn.textContent = THEME_ICONS[mode] || THEME_ICONS.auto;
      themeBtn.title =
        mode === "light" ? "Theme: Light" :
        mode === "dark"  ? "Theme: Dark" :
                           "Theme: Auto";
    }
  }

  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var idx = (THEMES.indexOf(storedMode) + 1) % THEMES.length;
      applyTheme(THEMES[idx]);
    });
  }

  // Listen for OS theme changes when in auto mode
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
    if (storedMode === "auto") {
      document.documentElement.dataset.theme = resolveTheme("auto");
    }
  });

  // Apply on load (complements the inline FOUC-prevention script in <head>)
  applyTheme(storedMode);

  // =========================================================================
  // 2. Sidebar toggles (mobile)
  // =========================================================================

  var sidebarLeft = document.querySelector(".sidebar-left");
  var sidebarRight = document.querySelector(".sidebar-right");
  var backdrop = document.getElementById("sidebar-backdrop");
  var toggleLeft = document.getElementById("sidebar-toggle-left");
  var toggleRight = document.getElementById("sidebar-toggle-right");

  function closeSidebars() {
    if (sidebarLeft) sidebarLeft.classList.remove("open");
    if (sidebarRight) sidebarRight.classList.remove("open");
    if (backdrop) backdrop.classList.remove("visible");
  }

  if (toggleLeft && sidebarLeft) {
    toggleLeft.addEventListener("click", function () {
      var opening = !sidebarLeft.classList.contains("open");
      closeSidebars();
      if (opening) {
        sidebarLeft.classList.add("open");
        backdrop.classList.add("visible");
      }
    });
  }

  if (toggleRight && sidebarRight) {
    toggleRight.addEventListener("click", function () {
      var opening = !sidebarRight.classList.contains("open");
      closeSidebars();
      if (opening) {
        sidebarRight.classList.add("open");
        backdrop.classList.add("visible");
      }
    });
  }

  if (backdrop) {
    backdrop.addEventListener("click", closeSidebars);
  }

  // Auto-close sidebars when resizing above breakpoint
  window.addEventListener("resize", function () {
    if (window.innerWidth > 960 && sidebarLeft && sidebarLeft.classList.contains("open")) {
      closeSidebars();
    }
    if (window.innerWidth > 1200 && sidebarRight && sidebarRight.classList.contains("open")) {
      closeSidebars();
    }
  });

  // =========================================================================
  // 3. Search modal (Pagefind lazy-load)
  // =========================================================================

  var searchOverlay = document.getElementById("search-overlay");
  var searchInput = document.getElementById("search-input");
  var searchResults = document.getElementById("search-results");
  var searchTrigger = document.querySelector(".search-trigger");
  var pagefind = null;
  var searchTimeout = null;

  function openSearch() {
    if (!searchOverlay) return;
    searchOverlay.classList.add("visible");
    if (searchInput) {
      searchInput.value = "";
      searchInput.focus();
    }
    if (searchResults) searchResults.innerHTML = "";
    loadPagefind();
  }

  function closeSearch() {
    if (searchOverlay) searchOverlay.classList.remove("visible");
  }

  async function loadPagefind() {
    if (pagefind) return;
    try {
      // Dynamic import resolves relative to this module's URL (assets/nav.js)
      // so ./pagefind/pagefind.js -> assets/pagefind/pagefind.js
      pagefind = await import("./pagefind/pagefind.js");
      var baseMeta = document.querySelector('meta[name="pagefind-base"]');
      var baseUrl = baseMeta ? baseMeta.getAttribute("content") : "/";
      await pagefind.options({ baseUrl: baseUrl });
      await pagefind.init();
    } catch (e) {
      console.warn("Pagefind not available:", e);
    }
  }

  function performSearch(query) {
    if (!searchResults) return;
    if (!query || query.length < 2) {
      searchResults.innerHTML = "";
      return;
    }
    if (!pagefind) {
      searchResults.innerHTML = '<div class="search-no-results">Search index not available.</div>';
      return;
    }

    pagefind.search(query).then(function (results) {
      if (!results || !results.results || results.results.length === 0) {
        searchResults.innerHTML = '<div class="search-no-results">No results found.</div>';
        return;
      }
      // Load first 8 page results, then expand sub_results for section-level precision
      var items = results.results.slice(0, 8);
      Promise.all(items.map(function (r) { return r.data(); })).then(function (dataList) {
        var html = "";
        var count = 0;
        for (var i = 0; i < dataList.length && count < 12; i++) {
          var data = dataList[i];
          var pageTitle = (data.meta && data.meta.title) || "Untitled";
          // Use sub_results for section-level anchors (h2/h3 with IDs)
          var subs = data.sub_results;
          if (subs && subs.length > 0) {
            for (var j = 0; j < subs.length && count < 12; j++) {
              var sub = subs[j];
              var url = sub.url || data.url || "#";
              var title = sub.title || pageTitle;
              var excerpt = sub.excerpt || "";
              // Show page title as breadcrumb if sub-title differs
              var breadcrumb = (title !== pageTitle)
                ? '<div class="search-result-page">' + escapeHtml(pageTitle) + '</div>'
                : '';
              html += '<a class="search-result" href="' + url + '">'
                + breadcrumb
                + '<div class="search-result-title">' + escapeHtml(title) + '</div>'
                + '<div class="search-result-excerpt">' + excerpt + '</div>'
                + '</a>';
              count++;
            }
          } else {
            // Fallback: page-level result
            var url = data.url || "#";
            var excerpt = data.excerpt || "";
            html += '<a class="search-result" href="' + url + '">'
              + '<div class="search-result-title">' + escapeHtml(pageTitle) + '</div>'
              + '<div class="search-result-excerpt">' + excerpt + '</div>'
              + '</a>';
            count++;
          }
        }
        searchResults.innerHTML = html;
      });
    }).catch(function () {
      searchResults.innerHTML = '<div class="search-no-results">Search error.</div>';
    });
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  if (searchTrigger) {
    searchTrigger.addEventListener("click", openSearch);
  }

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(function () {
        performSearch(searchInput.value.trim());
      }, 200);
    });
  }

  // Click on overlay backdrop closes search
  if (searchOverlay) {
    searchOverlay.addEventListener("click", function (e) {
      if (e.target === searchOverlay) closeSearch();
    });
  }

  // =========================================================================
  // 4. Keyboard shortcuts
  // =========================================================================

  document.addEventListener("keydown", function (e) {
    // Ctrl+K or Cmd+K → open/close search
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      if (searchOverlay && searchOverlay.classList.contains("visible")) {
        closeSearch();
      } else {
        openSearch();
      }
    }
    // Escape → close search or sidebar
    if (e.key === "Escape") {
      if (searchOverlay && searchOverlay.classList.contains("visible")) {
        closeSearch();
      } else {
        closeSidebars();
      }
    }
  });

  // =========================================================================
  // 5. Scroll-spy for local TOC
  // =========================================================================

  var tocLinks = document.querySelectorAll(".local-toc a");
  if (tocLinks.length > 0) {
    var topbar = document.querySelector(".topbar");
    var offset = (topbar ? topbar.offsetHeight : 56) + 16;
    var headingEls = [];
    var headingMap = {};

    tocLinks.forEach(function (link) {
      var id = link.getAttribute("href");
      if (id && id.startsWith("#")) {
        var el = document.getElementById(id.slice(1));
        if (el) {
          headingEls.push(el);
          headingMap[el.id] = link;
        }
      }
    });

    var ticking = false;
    function updateSpy() {
      ticking = false;
      var current = null;
      for (var i = 0; i < headingEls.length; i++) {
        if (headingEls[i].getBoundingClientRect().top <= offset) {
          current = headingEls[i];
        }
      }
      tocLinks.forEach(function (l) { l.classList.remove("active"); });
      if (current && headingMap[current.id]) {
        headingMap[current.id].classList.add("active");
      }
    }

    window.addEventListener("scroll", function () {
      if (!ticking) {
        requestAnimationFrame(updateSpy);
        ticking = true;
      }
    });

    // Initial highlight
    updateSpy();
  }

})();
