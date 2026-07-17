  /* ---------------------------------------------------------------------------
   * Theme toggle
   *
   * Toggles data-theme between "light" and "dark", persists to localStorage,
   * and swaps which SVG icon is visible. The inline <head> script in base.html
   * already sets data-theme before this runs; on init we just sync the icon.
   * ------------------------------------------------------------------------- */
export function initThemeToggle() {
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
