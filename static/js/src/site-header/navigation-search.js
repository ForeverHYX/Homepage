  /* ---------------------------------------------------------------------------
   * Header: mobile menu + search + search dropdown
   *
   * State is held in plain local variables; rendering is done by toggling
   * classes and rebuilding the portaled dropdown DOM.
   * ------------------------------------------------------------------------- */
export function initHeader() {
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
