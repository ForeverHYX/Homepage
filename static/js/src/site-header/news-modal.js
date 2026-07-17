  /* ---------------------------------------------------------------------------
   * Home page "all news" modal
   *
   * Only attached if #newsExpandBtn exists (home page). Creates a full-screen
   * overlay with a dedicated news card, fetches /api/site/news and renders its
   * all_news_html field. Closes on Escape / overlay click / close button click;
   * locks body scroll while open.
   * ------------------------------------------------------------------------- */
export function initNewsModal() {
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
