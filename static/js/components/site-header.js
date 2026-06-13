/**
 * site-header.js — Vanilla JS port of:
 *   - frontend/components/site-header.tsx
 *   - frontend/components/site-search-dropdown.tsx
 *   - frontend/components/use-active-theme.ts
 *
 * Hooks into the markup rendered by app/templates/base.html and
 * app/templates/pages/home.html. Pure vanilla JS, no dependencies.
 * Load with `<script ... defer>`.
 */
(function () {
  "use strict";

  /* ---------------------------------------------------------------------------
   * Bootstrap
   * ------------------------------------------------------------------------- */
  function init() {
    setFooterYear();
    initActiveRoutes();
    initHeader();
    initThemeToggle();
    initNewsModal();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { passive: true });
  } else {
    init();
  }

  /* ---------------------------------------------------------------------------
   * Footer year
   * ------------------------------------------------------------------------- */
  function setFooterYear() {
    var el = document.getElementById("footerYear");
    if (el) el.textContent = String(new Date().getFullYear());
  }

  /* ---------------------------------------------------------------------------
   * Active route highlighting
   *
   * Reads window.location.pathname and sets data-active="true" on matching
   * .nav-link / .nav-mobile-link elements. Exact match for "/", prefix match
   * for nested routes (e.g. /articles/some-slug matches /articles).
   * ------------------------------------------------------------------------- */
  function initActiveRoutes() {
    var path = window.location.pathname || "/";
    var links = document.querySelectorAll(
      ".nav-link[data-route], .nav-mobile-link[data-route]"
    );
    for (var i = 0; i < links.length; i++) {
      var link = links[i];
      var route = link.getAttribute("data-route") || "";
      var isActive =
        route === "/"
          ? path === "/"
          : path === route || path.indexOf(route + "/") === 0;
      link.setAttribute("data-active", isActive ? "true" : "false");
    }
  }

  /* ---------------------------------------------------------------------------
   * Header: mobile menu + search + search dropdown
   *
   * Mirrors the React SiteHeader + SiteSearchDropdown components. State is
   * held in plain local variables; rendering is done by toggling classes and
   * rebuilding the portaled dropdown DOM.
   * ------------------------------------------------------------------------- */
  function initHeader() {
    var navCluster = document.getElementById("navCluster");
    var navIsland = document.getElementById("navIsland");
    var navMobileTrigger = document.getElementById("navMobileTrigger");
    var navMobilePanel = document.getElementById("navMobilePanel");
    var searchTrigger = document.getElementById("searchTrigger");
    var searchCloseBtn = document.getElementById("searchCloseBtn");
    var inlineSearchInput = document.getElementById("inlineSearchInput");

    if (
      !navCluster ||
      !navIsland ||
      !navMobileTrigger ||
      !navMobilePanel ||
      !searchTrigger ||
      !searchCloseBtn ||
      !inlineSearchInput
    ) {
      return; // markup not present, nothing to wire up
    }

    // --- State --------------------------------------------------------------
    var state = {
      searchOpen: false,
      mobileMenuOpen: false,
      query: "",
      searchIndex: null, // null = not yet loaded, array once fetched
      searchIndexLoading: false,
    };

    // --- Dropdown lifecycle helpers ----------------------------------------
    var dropdownEl = null;
    var dropdownResultsEl = null;
    var dropdownCleanup = null; // function that tears down listeners + DOM

    /**
     * Build the portaled dropdown element. Returns the dropdown node and its
     * inner results container.
     */
    function createDropdownNode() {
      var dd = document.createElement("div");
      dd.id = "searchDropdown";
      dd.className = "search-dropdown";
      dd.style.position = "fixed";
      dd.style.zIndex = "9999";

      var results = document.createElement("div");
      results.id = "inlineSearchResults";
      results.style.padding = "8px 0";
      dd.appendChild(results);

      return { dd: dd, results: results };
    }

    /**
     * Poll the search input width (it animates from 0 during the CSS
     * transition) and position the dropdown once it is wide enough. Also
     * reposition on resize/scroll.
     */
    function startDropdownTracking(dropdown, input) {
      var cancelled = false;

      function positionDropdown() {
        if (cancelled || !dropdown || !input) return;
        var rect = input.getBoundingClientRect();
        if (rect.width > 100) {
          dropdown.style.left = rect.left + "px";
          dropdown.style.top = rect.bottom + 8 + "px";
          dropdown.style.width = rect.width + "px";
        }
      }

      // Poll every 50ms until the input has a sensible width, then stop polling.
      var intervalId = window.setInterval(function () {
        if (cancelled || !input) return;
        var rect = input.getBoundingClientRect();
        if (rect.width > 100) {
          dropdown.style.left = rect.left + "px";
          dropdown.style.top = rect.bottom + 8 + "px";
          dropdown.style.width = rect.width + "px";
          window.clearInterval(intervalId);
        }
      }, 50);

      // Safety net: stop polling after 500ms no matter what.
      var timeoutId = window.setTimeout(function () {
        window.clearInterval(intervalId);
        positionDropdown();
      }, 500);

      window.addEventListener("resize", positionDropdown, { passive: true });
      window.addEventListener("scroll", positionDropdown, {
        passive: true,
        capture: true,
      });

      return function cleanup() {
        cancelled = true;
        window.clearInterval(intervalId);
        window.clearTimeout(timeoutId);
        window.removeEventListener("resize", positionDropdown);
        window.removeEventListener("scroll", positionDropdown, true);
      };
    }

    function openDropdown() {
      if (dropdownEl) return;
      var built = createDropdownNode();
      dropdownEl = built.dd;
      dropdownResultsEl = built.results;
      document.body.appendChild(dropdownEl);
      dropdownCleanup = startDropdownTracking(dropdownEl, inlineSearchInput);
      renderResults();
    }

    function closeDropdown() {
      if (dropdownCleanup) {
        dropdownCleanup();
        dropdownCleanup = null;
      }
      if (dropdownEl && dropdownEl.parentNode) {
        dropdownEl.parentNode.removeChild(dropdownEl);
      }
      dropdownEl = null;
      dropdownResultsEl = null;
    }

    /**
     * Rebuild the dropdown contents based on the current query + index.
     */
    function renderResults() {
      if (!dropdownResultsEl) return;

      // Clear previous children
      while (dropdownResultsEl.firstChild) {
        dropdownResultsEl.removeChild(dropdownResultsEl.firstChild);
      }

      var normalized = state.query.trim().toLowerCase();
      if (!normalized) {
        dropdownEl.classList.remove("has-results");
        return;
      }
      dropdownEl.classList.add("has-results");

      var hits = computeHits(normalized);
      if (hits.length === 0) {
        var empty = document.createElement("div");
        empty.style.padding = "12px";
        empty.style.textAlign = "center";
        empty.style.color = "var(--muted)";
        empty.textContent = "No results found.";
        dropdownResultsEl.appendChild(empty);
        return;
      }

      for (var i = 0; i < hits.length; i++) {
        var hit = hits[i];
        var anchor = document.createElement("a");
        anchor.href = hit.url;
        var title = document.createElement("div");
        title.className = "search-result-title";
        var chip = document.createElement("span");
        chip.className = "search-result-chip";
        chip.textContent = hit.type;
        title.appendChild(chip);
        title.appendChild(document.createTextNode(hit.title));
        anchor.appendChild(title);
        // Clicking a result closes search and navigates (default anchor
        // behavior handles the navigation).
        anchor.addEventListener("click", resetNavigationState, {
          passive: true,
        });
        dropdownResultsEl.appendChild(anchor);
      }
    }

    /**
     * Filter the search index by title/desc/tags (case-insensitive includes).
     */
    function computeHits(normalized) {
      if (!state.searchIndex) return [];
      var out = [];
      for (var i = 0; i < state.searchIndex.length; i++) {
        var item = state.searchIndex[i];
        var tags = item.tags || [];
        var tagHit = false;
        for (var t = 0; t < tags.length; t++) {
          if (
            tags[t] &&
            String(tags[t]).toLowerCase().indexOf(normalized) !== -1
          ) {
            tagHit = true;
            break;
          }
        }
        if (
          (item.title &&
            String(item.title).toLowerCase().indexOf(normalized) !== -1) ||
          (item.desc &&
            String(item.desc).toLowerCase().indexOf(normalized) !== -1) ||
          tagHit
        ) {
          out.push(item);
        }
      }
      return out;
    }

    /**
     * Ensure /api/search-index has been fetched (cached on state). Mirrors the
     * React useEffect that runs when search opens.
     */
    function ensureSearchIndex() {
      if (state.searchIndex || state.searchIndexLoading) return;
      state.searchIndexLoading = true;
      fetch("/api/search-index")
        .then(function (response) {
          if (!response.ok) throw new Error("search-index failed");
          return response.json();
        })
        .then(function (data) {
          state.searchIndex = Array.isArray(data) ? data : [];
          renderResults();
        })
        .catch(function () {
          state.searchIndex = [];
          renderResults();
        })
        .finally(function () {
          state.searchIndexLoading = false;
        });
    }

    // --- State mutators -----------------------------------------------------
    function setSearchOpen(open) {
      state.searchOpen = open;
      searchTrigger.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) {
        navIsland.classList.add("search-mode");
        openDropdown();
        ensureSearchIndex();
        // Mirror the React setTimeout focus (input needs to be visible first).
        window.setTimeout(function () {
          if (state.searchOpen) inlineSearchInput.focus();
        }, 100);
      } else {
        navIsland.classList.remove("search-mode");
        closeDropdown();
        // Clear query both in state and in the DOM input.
        state.query = "";
        if (inlineSearchInput.value !== "") inlineSearchInput.value = "";
      }
    }

    function closeSearch() {
      if (state.searchOpen) setSearchOpen(false);
    }

    function setMobileMenuOpen(open) {
      state.mobileMenuOpen = open;
      navMobileTrigger.setAttribute("aria-expanded", open ? "true" : "false");
      navMobileTrigger.setAttribute(
        "title",
        open ? "Close Menu" : "Open Menu"
      );
      navMobileTrigger.setAttribute(
        "aria-label",
        open ? "Close menu" : "Open menu"
      );
      if (open) {
        navMobilePanel.classList.add("open");
      } else {
        navMobilePanel.classList.remove("open");
      }
    }

    function resetNavigationState() {
      closeSearch();
      if (state.mobileMenuOpen) setMobileMenuOpen(false);
    }

    // --- Event wiring -------------------------------------------------------
    navMobileTrigger.addEventListener("click", function () {
      closeSearch();
      setMobileMenuOpen(!state.mobileMenuOpen);
    });

    searchTrigger.addEventListener("click", function () {
      if (state.mobileMenuOpen) setMobileMenuOpen(false);
      setSearchOpen(true);
    });

    searchCloseBtn.addEventListener("click", closeSearch);

    inlineSearchInput.addEventListener("input", function (event) {
      state.query = event.target.value;
      renderResults();
    });

    // Clicking anywhere inside #navCluster keeps menus open; clicking outside
    // closes both search and mobile menu. Mirrors the React document click
    // handler bound to navClusterRef.
    document.addEventListener("click", function (event) {
      if (!navCluster || navCluster.contains(event.target)) return;
      if (state.searchOpen) closeSearch();
      if (state.mobileMenuOpen) setMobileMenuOpen(false);
    });

    // Clicking any nav link closes both search + mobile menu.
    var navLinkEls = navCluster.querySelectorAll(
      ".nav-link, .nav-mobile-link, .nav-brand"
    );
    for (var i = 0; i < navLinkEls.length; i++) {
      navLinkEls[i].addEventListener("click", resetNavigationState, {
        passive: true,
      });
    }

    // Escape closes whichever is open.
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      if (state.searchOpen) {
        event.preventDefault();
        closeSearch();
      } else if (state.mobileMenuOpen) {
        event.preventDefault();
        setMobileMenuOpen(false);
      }
    });
  }

  /* ---------------------------------------------------------------------------
   * Theme toggle
   *
   * Toggles data-theme between "light" and "dark", persists to localStorage,
   * and swaps which SVG icon is visible. The inline <head> script in base.html
   * already sets data-theme before this runs; on init we just sync the icon.
   * ------------------------------------------------------------------------- */
  function initThemeToggle() {
    var themeToggle = document.getElementById("themeToggle");
    var moonIcon = document.querySelector(".theme-icon-moon");
    var sunIcon = document.querySelector(".theme-icon-sun");

    function currentTheme() {
      return document.documentElement.getAttribute("data-theme") === "dark"
        ? "dark"
        : "light";
    }

    function syncIcon() {
      var isDark = currentTheme() === "dark";
      if (moonIcon) moonIcon.style.display = isDark ? "none" : "";
      if (sunIcon) sunIcon.style.display = isDark ? "" : "none";
    }

    // Initial sync (the inline head script has already applied the theme).
    syncIcon();

    // Keep icons in sync if anything else mutates data-theme (mirrors the
    // MutationObserver in use-active-theme).
    if (typeof MutationObserver !== "undefined") {
      var observer = new MutationObserver(syncIcon);
      observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    }

    if (!themeToggle) return;
    themeToggle.addEventListener("click", function () {
      var nextTheme = currentTheme() === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", nextTheme);
      document.documentElement.style.colorScheme = nextTheme;
      try {
        localStorage.setItem("theme", nextTheme);
      } catch (e) {
        /* localStorage may be unavailable (private mode, etc.) — ignore */
      }
      // syncIcon runs via the MutationObserver, but call it directly too in
      // case MutationObserver is unavailable.
      syncIcon();
    });
  }

  /* ---------------------------------------------------------------------------
   * Home page "all news" modal
   *
   * Only attached if #newsExpandBtn exists (home page). Creates a full-screen
   * overlay using the existing .lightbox-overlay.active CSS, fetches
   * /api/site/home and renders its all_news_html field. Closes on Escape /
   * overlay click / close button click; locks body scroll while open.
   * ------------------------------------------------------------------------- */
  function initNewsModal() {
    var btn = document.getElementById("newsExpandBtn");
    if (!btn) return;

    var overlay = null;
    var closeBtn = null;
    var savedOverflow = "";
    var savedPaddingRight = "";

    function openModal() {
      if (overlay) return; // already open

      overlay = document.createElement("div");
      overlay.className = "lightbox-overlay";

      var card = document.createElement("div");
      card.className = "card home-liquid-card lightbox-content";
      // Keep clicks on the card from bubbling to the overlay (which closes).
      card.addEventListener("click", function (e) {
        e.stopPropagation();
      });

      // Loading placeholder while we fetch.
      var loading = document.createElement("div");
      loading.style.padding = "32px";
      loading.style.color = "var(--muted)";
      loading.textContent = "Loading…";
      card.appendChild(loading);

      closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.className = "lightbox-close";
      closeBtn.setAttribute("aria-label", "Close");
      closeBtn.innerHTML = "&times;";

      overlay.appendChild(card);
      overlay.appendChild(closeBtn);
      document.body.appendChild(overlay);

      // Lock body scroll (and compensate for the scrollbar width to avoid
      // layout shift).
      savedOverflow = document.body.style.overflow;
      savedPaddingRight = document.body.style.paddingRight;
      var scrollbarWidth =
        window.innerWidth - document.documentElement.clientWidth;
      document.body.style.overflow = "hidden";
      if (scrollbarWidth > 0) {
        document.body.style.paddingRight = scrollbarWidth + "px";
      }

      // Force a frame so the CSS opacity transition kicks in.
      window.requestAnimationFrame(function () {
        if (overlay) overlay.classList.add("active");
      });

      // Wire up close interactions.
      overlay.addEventListener("click", closeModal);
      closeBtn.addEventListener("click", closeModal, { passive: true });
      document.addEventListener("keydown", onKeydown);

      // Fetch news HTML.
      fetch("/api/site/home", { headers: { Accept: "application/json" } })
        .then(function (response) {
          if (!response.ok) throw new Error("site/home failed");
          return response.json();
        })
        .then(function (data) {
          if (!overlay) return;
          // Replace the loading placeholder with the real news HTML.
          while (card.firstChild) card.removeChild(card.firstChild);
          var wrap = document.createElement("div");
          wrap.className = "home-news-all";
          wrap.innerHTML = data && data.all_news_html ? data.all_news_html : "";
          card.appendChild(wrap);
        })
        .catch(function () {
          if (!overlay) return;
          while (card.firstChild) card.removeChild(card.firstChild);
          var err = document.createElement("div");
          err.style.padding = "32px";
          err.style.color = "var(--muted)";
          err.textContent = "Failed to load news.";
          card.appendChild(err);
        });
    }

    function closeModal() {
      if (!overlay) return;
      document.removeEventListener("keydown", onKeydown);
      if (closeBtn) closeBtn.removeEventListener("click", closeModal);
      var current = overlay;
      overlay = null;
      closeBtn = null;

      // Fade out, then remove.
      current.classList.remove("active");
      window.setTimeout(function () {
        if (current.parentNode) current.parentNode.removeChild(current);
      }, 400);

      // Restore body scroll.
      document.body.style.overflow = savedOverflow;
      document.body.style.paddingRight = savedPaddingRight;
    }

    function onKeydown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeModal();
      }
    }

    btn.addEventListener("click", openModal);
  }
})();
