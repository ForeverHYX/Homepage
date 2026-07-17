  /* ---------------------------------------------------------------------------
   * Shared anchored popover controller
   *
   * Popovers stay spatially connected to the control that opened them. The
   * controller portals each surface to <body>, selects the first placement
   * that fits, clamps it inside the visual viewport, and keeps it aligned while
   * the page scrolls or resizes. Only one functional popover is open at once.
   * ------------------------------------------------------------------------- */
export function createAnchoredPopoverController() {
    var active = null;
    var positionFrame = 0;
    var viewportMargin = 12;
    var anchorGap = 10;

    function clamp(value, minimum, maximum) {
      if (maximum < minimum) return minimum;
      return Math.min(Math.max(value, minimum), maximum);
    }

    function viewportBounds() {
      var viewport = window.visualViewport;
      var left = viewport ? viewport.offsetLeft : 0;
      var top = viewport ? viewport.offsetTop : 0;
      var width = viewport ? viewport.width : window.innerWidth;
      var height = viewport ? viewport.height : window.innerHeight;
      return {
        left: left,
        top: top,
        right: left + width,
        bottom: top + height,
        width: width,
        height: height,
      };
    }

    function candidate(name, anchorRect, popoverRect) {
      if (name === "right-start") {
        return {
          name: name,
          left: anchorRect.right + anchorGap,
          top: anchorRect.top,
        };
      }
      if (name === "left-start") {
        return {
          name: name,
          left: anchorRect.left - popoverRect.width - anchorGap,
          top: anchorRect.top,
        };
      }
      if (name === "top-end") {
        return {
          name: name,
          left: anchorRect.right - popoverRect.width,
          top: anchorRect.top - popoverRect.height - anchorGap,
        };
      }
      if (name === "top-start") {
        return {
          name: name,
          left: anchorRect.left,
          top: anchorRect.top - popoverRect.height - anchorGap,
        };
      }
      if (name === "bottom-start") {
        return {
          name: name,
          left: anchorRect.left,
          top: anchorRect.bottom + anchorGap,
        };
      }
      return {
        name: "bottom-end",
        left: anchorRect.right - popoverRect.width,
        top: anchorRect.bottom + anchorGap,
      };
    }

    function placementOrder(preferred) {
      if (preferred === "right-start") {
        return ["right-start", "left-start", "bottom-start", "top-start"];
      }
      if (preferred === "left-start") {
        return ["left-start", "right-start", "bottom-end", "top-end"];
      }
      return ["bottom-end", "top-end", "left-start", "right-start"];
    }

    function overflowScore(position, popoverRect, bounds) {
      return (
        Math.max(0, bounds.left + viewportMargin - position.left) +
        Math.max(
          0,
          position.left + popoverRect.width - (bounds.right - viewportMargin)
        ) +
        Math.max(0, bounds.top + viewportMargin - position.top) +
        Math.max(
          0,
          position.top + popoverRect.height - (bounds.bottom - viewportMargin)
        )
      );
    }

    function positionActivePopover() {
      positionFrame = 0;
      if (!active || !active.anchor.isConnected || !active.popover.isConnected) {
        if (active) close(active.popover, false);
        return;
      }

      var popover = active.popover;
      var bounds = viewportBounds();
      var availableWidth = Math.max(240, bounds.width - viewportMargin * 2);
      var availableHeight = Math.max(180, bounds.height - viewportMargin * 2);
      popover.style.maxWidth = availableWidth + "px";
      popover.style.maxHeight = availableHeight + "px";
      popover.style.setProperty(
        "--anchored-popover-max-height",
        availableHeight + "px"
      );

      var anchorRect = active.anchor.getBoundingClientRect();
      var popoverRect = popover.getBoundingClientRect();
      var order = placementOrder(active.placement);
      var selected = null;
      var selectedScore = Infinity;

      for (var index = 0; index < order.length; index++) {
        var next = candidate(order[index], anchorRect, popoverRect);
        var score = overflowScore(next, popoverRect, bounds);
        if (score === 0) {
          selected = next;
          break;
        }
        if (score < selectedScore) {
          selected = next;
          selectedScore = score;
        }
      }

      var left = clamp(
        selected.left,
        bounds.left + viewportMargin,
        bounds.right - viewportMargin - popoverRect.width
      );
      var top = clamp(
        selected.top,
        bounds.top + viewportMargin,
        bounds.bottom - viewportMargin - popoverRect.height
      );
      var anchorCenterX = anchorRect.left + anchorRect.width / 2;
      var anchorCenterY = anchorRect.top + anchorRect.height / 2;
      var originX = clamp(anchorCenterX - left, 18, popoverRect.width - 18);
      var originY = clamp(anchorCenterY - top, 18, popoverRect.height - 18);
      var shiftX = 0;
      var shiftY = 0;

      if (selected.name.indexOf("right") === 0) shiftX = -8;
      if (selected.name.indexOf("left") === 0) shiftX = 8;
      if (selected.name.indexOf("bottom") === 0) shiftY = -8;
      if (selected.name.indexOf("top") === 0) shiftY = 8;

      popover.style.left = Math.round(left) + "px";
      popover.style.top = Math.round(top) + "px";
      popover.style.setProperty("--popover-origin-x", originX + "px");
      popover.style.setProperty("--popover-origin-y", originY + "px");
      popover.style.setProperty("--popover-shift-x", shiftX + "px");
      popover.style.setProperty("--popover-shift-y", shiftY + "px");
      popover.dataset.placement = selected.name;
    }

    function schedulePosition() {
      if (!active || positionFrame) return;
      positionFrame = window.requestAnimationFrame(positionActivePopover);
    }

    function onPointerDown(event) {
      if (!active) return;
      if (
        active.popover.contains(event.target) ||
        active.anchor.contains(event.target)
      ) {
        return;
      }
      close(active.popover, false);
    }

    function onKeydown(event) {
      if (event.key !== "Escape" || !active) return;
      event.preventDefault();
      close(active.popover, true);
    }

    function bindPositioningListeners() {
      document.addEventListener("pointerdown", onPointerDown, true);
      document.addEventListener("keydown", onKeydown);
      window.addEventListener("resize", schedulePosition, { passive: true });
      window.addEventListener("scroll", schedulePosition, {
        passive: true,
        capture: true,
      });
      if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", schedulePosition, {
          passive: true,
        });
        window.visualViewport.addEventListener("scroll", schedulePosition, {
          passive: true,
        });
      }
    }

    function unbindPositioningListeners() {
      document.removeEventListener("pointerdown", onPointerDown, true);
      document.removeEventListener("keydown", onKeydown);
      window.removeEventListener("resize", schedulePosition);
      window.removeEventListener("scroll", schedulePosition, true);
      if (window.visualViewport) {
        window.visualViewport.removeEventListener("resize", schedulePosition);
        window.visualViewport.removeEventListener("scroll", schedulePosition);
      }
      if (positionFrame) {
        window.cancelAnimationFrame(positionFrame);
        positionFrame = 0;
      }
    }

    function hidePopover(popover) {
      if (popover.classList.contains("is-open")) return;
      popover.classList.remove("is-positioned");
      popover.hidden = true;
      popover.inert = true;
      popover.style.removeProperty("left");
      popover.style.removeProperty("top");
      popover.style.removeProperty("max-width");
      popover.style.removeProperty("max-height");
    }

    function close(popover, restoreFocus) {
      if (!active || active.popover !== popover) return;
      var closing = active;
      active = null;
      unbindPositioningListeners();
      closing.anchor.setAttribute("aria-expanded", "false");
      popover.classList.remove("is-open");
      popover.inert = true;

      if (restoreFocus && closing.anchor.isConnected) {
        closing.anchor.focus({ preventScroll: true });
      }

      window.clearTimeout(popover._homepagePopoverCloseTimer);
      var delay = window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? 0
        : 220;
      popover._homepagePopoverCloseTimer = window.setTimeout(function () {
        hidePopover(popover);
      }, delay);
    }

    function open(popover, anchor, options) {
      if (!popover || !anchor) return;
      options = options || {};

      if (active && active.popover !== popover) {
        var previous = active.popover;
        close(previous, false);
        window.clearTimeout(previous._homepagePopoverCloseTimer);
        hidePopover(previous);
      }

      var retiringPopovers = document.querySelectorAll(
        ".anchored-popover.is-positioned"
      );
      for (var index = 0; index < retiringPopovers.length; index++) {
        var retiring = retiringPopovers[index];
        if (retiring === popover) continue;
        window.clearTimeout(retiring._homepagePopoverCloseTimer);
        retiring.classList.remove("is-open");
        hidePopover(retiring);
      }

      window.clearTimeout(popover._homepagePopoverCloseTimer);
      if (popover.parentNode !== document.body) {
        document.body.appendChild(popover);
      }
      popover.hidden = false;
      popover.inert = false;
      popover.classList.remove("is-open");
      popover.classList.add("is-positioned");
      anchor.setAttribute("aria-expanded", "true");
      anchor.setAttribute("aria-controls", popover.id);

      active = {
        popover: popover,
        anchor: anchor,
        placement: options.placement || "bottom-end",
      };
      bindPositioningListeners();
      positionActivePopover();
      void popover.offsetWidth;

      window.requestAnimationFrame(function () {
        if (!active || active.popover !== popover) return;
        positionActivePopover();
        popover.classList.add("is-open");
        var initialFocus = options.initialFocus;
        if (typeof initialFocus === "function") initialFocus = initialFocus();
        if (initialFocus && initialFocus.isConnected) {
          initialFocus.focus({ preventScroll: true });
        }
      });
    }

    function isOpen(popover) {
      return Boolean(active && active.popover === popover);
    }

    return {
      open: open,
      close: close,
      isOpen: isOpen,
      reposition: schedulePosition,
    };
  }

window.HomepageAnchoredPopover = createAnchoredPopoverController();
