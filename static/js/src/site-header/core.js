  /* ---------------------------------------------------------------------------
   * Footer year
   * ------------------------------------------------------------------------- */
export function setFooterYear() {
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
export function initActiveRoutes() {
    var root = document.documentElement;
    root.classList.add("nav-booting");
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
    window.requestAnimationFrame(function () {
      root.classList.remove("nav-booting");
    });
  }

  /* ---------------------------------------------------------------------------
   * Page entry
   *
   * The old animation moved an entire page shell, including every translucent
   * card. On long Daily pages that forced the browser to composite a multi-
   * thousand-pixel backdrop-filter tree. Animate only small, visible content
   * bodies instead; the glass plates themselves remain stable and fully live.
   * ------------------------------------------------------------------------- */
export function initPageEntry() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    var cards = document.querySelectorAll(
      ".site-main .home-glass, .site-main .home-liquid-card"
    );
    var visibleBodies = [];
    var viewportHeight = Math.max(window.innerHeight || 0, 1);
    var maxAnimatedHeight = viewportHeight * 1.35;

    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      var parentMaterial = card.parentElement
        ? card.parentElement.closest(".home-glass, .home-liquid-card")
        : null;
      if (parentMaterial) continue;

      var body = card.querySelector(
        ":scope > .home-glass-body, :scope > .home-liquid-body"
      );
      if (!body) continue;

      var rect = body.getBoundingClientRect();
      if (
        rect.bottom > -40 &&
        rect.top < viewportHeight + 80 &&
        rect.height <= maxAnimatedHeight
      ) {
        visibleBodies.push(body);
      }
    }

    if (!visibleBodies.length) return;

    window.requestAnimationFrame(function () {
      for (var index = 0; index < visibleBodies.length; index++) {
        (function (body, order) {
          body.style.setProperty("--page-enter-delay", Math.min(order, 3) * 24 + "ms");
          body.classList.add("page-enter");

          var release = function () {
            body.classList.remove("page-enter");
            body.style.removeProperty("--page-enter-delay");
            body.removeEventListener("animationend", handleAnimationEnd);
          };
          var handleAnimationEnd = function (event) {
            if (event.target === body && event.animationName === "pageContentEnter") {
              release();
            }
          };
          body.addEventListener("animationend", handleAnimationEnd);
          window.setTimeout(release, 520);
        })(visibleBodies[index], index);
      }
    });
  }
