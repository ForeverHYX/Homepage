import { initActiveRoutes, initPageEntry, setFooterYear } from "./core.js";
import { initHeader } from "./navigation-search.js";
import { initThemeToggle } from "./theme.js";
import { initNewsPopover } from "./news-modal.js";

export function initSiteHeader() {
  setFooterYear();
  initActiveRoutes();
  initPageEntry();
  initHeader();
  initThemeToggle();
  initNewsPopover();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSiteHeader, { passive: true });
} else {
  initSiteHeader();
}
