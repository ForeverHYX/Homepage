/**
 * site-header.js hooks into the markup rendered by app/templates/base.html and
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
   * for nested routes (e.g. /daily/articles/some-slug matches /daily).
   * ------------------------------------------------------------------------- */
  function initActiveRoutes() {
    var path = window.location.pathname || "/";
    if (path === "/login") {
      var intendedPath = new URLSearchParams(window.location.search).get("next");
      if (!intendedPath || intendedPath === "/upload") path = "/upload";
    }
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
      if (isActive) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    }
  }

  /* ---------------------------------------------------------------------------
   * Header: mobile menu + search + search dropdown
   *
   * State is held in plain local variables; rendering is done by toggling
   * classes and rebuilding the portaled dropdown DOM.
   * ------------------------------------------------------------------------- */
  function initHeader() {
    var navCluster = document.getElementById("navCluster");
    var navIsland = document.getElementById("navIsland");
    var navLinks = document.getElementById("navLinks");
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

    navMobilePanel.inert = true;

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
      dd.setAttribute("role", "region");
      dd.setAttribute("aria-label", "Search results");
      dd.style.position = "fixed";
      dd.style.zIndex = "9999";
      dd.addEventListener("keydown", handleDropdownKeydown);

      var results = document.createElement("div");
      results.id = "inlineSearchResults";
      results.setAttribute("aria-live", "polite");
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

      function anchorRect() {
        var useIsland = window.matchMedia("(max-width: 820px)").matches;
        return (useIsland ? navIsland : input).getBoundingClientRect();
      }

      function positionDropdown() {
        if (cancelled || !dropdown || !input) return;
        var rect = anchorRect();
        if (rect.width > 100) {
          var viewport = window.visualViewport;
          var viewportBottom = viewport
            ? viewport.offsetTop + viewport.height
            : window.innerHeight;
          var top = rect.bottom + 8;
          var availableHeight = Math.max(0, viewportBottom - top - 12);
          dropdown.style.left = rect.left + "px";
          dropdown.style.top = top + "px";
          dropdown.style.width = rect.width + "px";
          dropdown.style.maxHeight = Math.min(400, availableHeight) + "px";
        }
      }

      // Track the full width transition so the dropdown finishes aligned with
      // the expanded input rather than freezing at an intermediate width.
      var intervalId = window.setInterval(function () {
        if (cancelled || !input) return;
        positionDropdown();
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
      if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", positionDropdown, {
          passive: true,
        });
        window.visualViewport.addEventListener("scroll", positionDropdown, {
          passive: true,
        });
      }

      return function cleanup() {
        cancelled = true;
        window.clearInterval(intervalId);
        window.clearTimeout(timeoutId);
        window.removeEventListener("resize", positionDropdown);
        window.removeEventListener("scroll", positionDropdown, true);
        if (window.visualViewport) {
          window.visualViewport.removeEventListener("resize", positionDropdown);
          window.visualViewport.removeEventListener("scroll", positionDropdown);
        }
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
        anchor.tabIndex = -1;
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

    function resultLinks() {
      return dropdownResultsEl
        ? Array.prototype.slice.call(dropdownResultsEl.querySelectorAll("a"))
        : [];
    }

    function focusResult(index) {
      var links = resultLinks();
      if (!links.length) return false;
      var nextIndex = Math.max(0, Math.min(index, links.length - 1));
      links[nextIndex].focus();
      return true;
    }

    function handleDropdownKeydown(event) {
      var links = resultLinks();
      if (!links.length) return;
      var index = links.indexOf(document.activeElement);
      if (event.key === "ArrowDown") {
        event.preventDefault();
        focusResult(index < 0 ? 0 : index + 1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        if (index <= 0) {
          inlineSearchInput.focus();
        } else {
          focusResult(index - 1);
        }
      } else if (event.key === "Tab" && index >= 0) {
        event.preventDefault();
        if (event.shiftKey) {
          inlineSearchInput.focus();
        } else {
          searchCloseBtn.focus();
        }
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
     * Ensure /api/search-index has been fetched and cached on state.
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
    function setSearchControlsHidden(hidden) {
      searchTrigger.inert = hidden;
      searchTrigger.setAttribute("aria-hidden", hidden ? "true" : "false");
      if (navLinks) {
        navLinks.inert = hidden;
        navLinks.setAttribute("aria-hidden", hidden ? "true" : "false");
      }
    }

    function setSearchOpen(open) {
      var activeElement = document.activeElement;
      var shouldRestoreFocus =
        !open &&
        activeElement &&
        (inlineSearchInput === activeElement ||
          searchCloseBtn === activeElement ||
          (dropdownEl && dropdownEl.contains(activeElement)));
      state.searchOpen = open;
      searchTrigger.setAttribute("aria-expanded", open ? "true" : "false");
      inlineSearchInput.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) {
        navIsland.classList.add("search-mode");
        openDropdown();
        ensureSearchIndex();
        inlineSearchInput.focus({ preventScroll: true });
        setSearchControlsHidden(true);
      } else {
        setSearchControlsHidden(false);
        navIsland.classList.remove("search-mode");
        closeDropdown();
        // Clear query both in state and in the DOM input.
        state.query = "";
        if (inlineSearchInput.value !== "") inlineSearchInput.value = "";
        if (shouldRestoreFocus) {
          searchTrigger.focus({ preventScroll: true });
        }
      }
    }

    function closeSearch() {
      if (state.searchOpen) setSearchOpen(false);
    }

    function setMobileMenuOpen(open) {
      var shouldRestoreFocus =
        !open &&
        document.activeElement &&
        navMobilePanel.contains(document.activeElement);
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
        navMobilePanel.setAttribute("aria-hidden", "false");
        navMobilePanel.inert = false;
        navMobilePanel.classList.add("open");
      } else {
        if (shouldRestoreFocus) {
          navMobileTrigger.focus({ preventScroll: true });
        }
        navMobilePanel.setAttribute("aria-hidden", "true");
        navMobilePanel.inert = true;
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

    inlineSearchInput.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown") {
        if (focusResult(0)) event.preventDefault();
      } else if (event.key === "ArrowUp") {
        var links = resultLinks();
        if (links.length && focusResult(links.length - 1)) {
          event.preventDefault();
        }
      }
    });

    // Clicking anywhere inside #navCluster keeps menus open; clicking outside
    // closes both search and mobile menu.
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
      if (themeToggle) {
        var label = isDark ? "Switch to light mode" : "Switch to dark mode";
        themeToggle.setAttribute("aria-label", label);
        themeToggle.setAttribute("title", label);
        themeToggle.setAttribute("aria-pressed", isDark ? "true" : "false");
      }
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
   * overlay with a dedicated news card, fetches /api/site/news and renders its
   * all_news_html field. Closes on Escape / overlay click / close button click;
   * locks body scroll while open.
   * ------------------------------------------------------------------------- */
  function initNewsModal() {
    var btn = document.getElementById("newsExpandBtn");
    if (!btn) return;

    var overlay = null;
    var closeBtn = null;
    var modalCard = null;
    var previousFocus = null;
    var isModalClosing = false;
    var savedOverflow = "";
    var savedPaddingRight = "";

    function openModal() {
      if (overlay) return; // already open

      overlay = document.createElement("div");
      overlay.className = "news-modal-overlay";
      previousFocus = document.activeElement;

      var card = document.createElement("div");
      card.className = "news-modal-card";
      card.setAttribute("role", "dialog");
      card.setAttribute("aria-modal", "true");
      card.setAttribute("aria-labelledby", "newsModalTitle");
      card.tabIndex = -1;
      modalCard = card;
      // Keep clicks on the card from bubbling to the overlay (which closes).
      card.addEventListener("click", function (e) {
        e.stopPropagation();
      });

      var header = document.createElement("div");
      header.className = "news-modal-header";
      var title = document.createElement("h2");
      title.id = "newsModalTitle";
      title.className = "news-modal-title";
      title.textContent = "News";
      header.appendChild(title);

      closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.className = "news-modal-close";
      closeBtn.setAttribute("aria-label", "Close");
      closeBtn.innerHTML = "&times;";
      header.appendChild(closeBtn);
      card.appendChild(header);

      var body = document.createElement("div");
      body.className = "news-modal-body";
      card.appendChild(body);

      // Loading placeholder while we fetch.
      var loading = document.createElement("div");
      loading.className = "news-modal-status";
      loading.setAttribute("role", "status");
      loading.textContent = "Loading…";
      body.appendChild(loading);

      overlay.appendChild(card);
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
        if (overlay && !isModalClosing) {
          overlay.classList.add("is-active");
          closeBtn.focus({ preventScroll: true });
        }
      });

      // Wire up close interactions.
      overlay.addEventListener("click", closeModal);
      closeBtn.addEventListener("click", closeModal, { passive: true });
      document.addEventListener("keydown", onKeydown);

      // Fetch news HTML.
      fetch("/api/site/news", { headers: { Accept: "application/json" } })
        .then(function (response) {
          if (!response.ok) throw new Error("site/news failed");
          return response.json();
        })
        .then(function (data) {
          if (!overlay) return;
          // Replace the loading placeholder with the real news HTML.
          while (body.firstChild) body.removeChild(body.firstChild);
          var wrap = document.createElement("div");
          wrap.className = "home-news-modal-content";
          wrap.innerHTML = data && data.all_news_html ? data.all_news_html : "";
          body.appendChild(wrap);
        })
        .catch(function () {
          if (!overlay) return;
          while (body.firstChild) body.removeChild(body.firstChild);
          var err = document.createElement("div");
          err.className = "news-modal-status";
          err.setAttribute("role", "alert");
          err.textContent = "Failed to load news.";
          body.appendChild(err);
        });
    }

    function closeModal() {
      if (!overlay || isModalClosing) return;
      isModalClosing = true;
      var current = overlay;
      var currentCloseBtn = closeBtn;
      var returnFocus = previousFocus;

      // Fade out, then remove.
      current.classList.remove("is-active");
      window.setTimeout(function () {
        document.removeEventListener("keydown", onKeydown);
        if (currentCloseBtn) {
          currentCloseBtn.removeEventListener("click", closeModal);
        }
        if (current.parentNode) current.parentNode.removeChild(current);
        overlay = null;
        closeBtn = null;
        modalCard = null;
        previousFocus = null;
        isModalClosing = false;
        if (returnFocus && returnFocus.isConnected) {
          returnFocus.focus({ preventScroll: true });
        }
        document.body.style.overflow = savedOverflow;
        document.body.style.paddingRight = savedPaddingRight;
      }, 300);
    }

    function onKeydown(event) {
      if (isModalClosing) {
        if (event.key === "Tab" || event.key === "Escape") {
          event.preventDefault();
        }
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        closeModal();
        return;
      }
      if (event.key === "Tab" && modalCard) {
        var focusable = Array.prototype.slice.call(
          modalCard.querySelectorAll(
            'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
          )
        );
        if (!focusable.length) {
          event.preventDefault();
          modalCard.focus();
          return;
        }
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }

    btn.addEventListener("click", openModal);
  }
})();
