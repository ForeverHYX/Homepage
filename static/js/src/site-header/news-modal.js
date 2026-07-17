  /* ---------------------------------------------------------------------------
   * Home page "all news" anchored popover
   *
   * The expanded list uses the shared functional-card material and grows from
   * the News control. It remains non-modal: no viewport scrim, body scroll
   * lock, or focus trap. The fetched response is cached in the mounted panel.
   * ------------------------------------------------------------------------- */
export function initNewsPopover() {
    var button = document.getElementById("newsExpandBtn");
    var controller = window.HomepageAnchoredPopover;
    if (!button || !controller) return;

    var popover = null;
    var closeButton = null;
    var popoverBody = null;
    var newsLoaded = false;
    var newsLoading = false;

    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-haspopup", "dialog");

    function buildPopover() {
      if (popover) return popover;

      popover = document.createElement("section");
      popover.id = "newsPopover";
      popover.className =
        "anchored-popover card home-liquid-card news-popover";
      popover.setAttribute("role", "dialog");
      popover.setAttribute("aria-labelledby", "newsPopoverTitle");
      popover.hidden = true;
      popover.inert = true;

      var warp = document.createElement("span");
      warp.className = "home-liquid-warp";
      warp.setAttribute("aria-hidden", "true");
      popover.appendChild(warp);

      var surfaceBody = document.createElement("div");
      surfaceBody.className = "home-liquid-body news-popover-surface";

      var header = document.createElement("header");
      header.className = "news-popover-header";
      var headingGroup = document.createElement("div");
      var eyebrow = document.createElement("p");
      eyebrow.className = "popover-eyebrow";
      eyebrow.textContent = "Latest updates";
      var title = document.createElement("h2");
      title.id = "newsPopoverTitle";
      title.className = "news-popover-title";
      title.textContent = "News";
      headingGroup.appendChild(eyebrow);
      headingGroup.appendChild(title);
      header.appendChild(headingGroup);

      closeButton = document.createElement("button");
      closeButton.type = "button";
      closeButton.className = "popover-close-btn";
      closeButton.setAttribute("aria-label", "Close news");
      closeButton.innerHTML =
        '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>';
      closeButton.addEventListener("click", function () {
        controller.close(popover, true);
      });
      header.appendChild(closeButton);
      surfaceBody.appendChild(header);

      popoverBody = document.createElement("div");
      popoverBody.className = "news-popover-scroll";
      surfaceBody.appendChild(popoverBody);
      popover.appendChild(surfaceBody);
      document.body.appendChild(popover);
      return popover;
    }

    function renderStatus(message, role) {
      while (popoverBody.firstChild) popoverBody.removeChild(popoverBody.firstChild);
      var status = document.createElement("div");
      status.className = "news-popover-status";
      status.setAttribute("role", role || "status");
      status.textContent = message;
      popoverBody.appendChild(status);
    }

    function loadNews() {
      if (newsLoaded || newsLoading) return;
      newsLoading = true;
      renderStatus("Loading…", "status");

      fetch("/api/site/news", { headers: { Accept: "application/json" } })
        .then(function (response) {
          if (!response.ok) throw new Error("site/news failed");
          return response.json();
        })
        .then(function (data) {
          while (popoverBody.firstChild) {
            popoverBody.removeChild(popoverBody.firstChild);
          }
          var wrap = document.createElement("div");
          wrap.className = "home-news-popover-content";
          wrap.innerHTML = data && data.all_news_html ? data.all_news_html : "";
          popoverBody.appendChild(wrap);
          newsLoaded = true;
          controller.reposition();
        })
        .catch(function () {
          renderStatus("Failed to load news.", "alert");
        })
        .then(function () {
          newsLoading = false;
        });
    }

    function togglePopover() {
      buildPopover();
      if (controller.isOpen(popover)) {
        controller.close(popover, true);
        return;
      }
      controller.open(popover, button, {
        placement: "right-start",
        initialFocus: closeButton,
      });
      loadNews();
    }

    button.addEventListener("click", togglePopover);
  }
