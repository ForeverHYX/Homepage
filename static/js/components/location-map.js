/**
 * Opens the Yuquan Campus map beside the profile location.
 *
 * Fine pointers get an immediate hover preview. Click, keyboard activation,
 * and touch pin the same accessible popover until it is dismissed. The map is
 * loaded only after the first interaction so the homepage makes no third-party
 * request on initial load.
 */
(function () {
  "use strict";

  function initLocationMapPopover() {
    var trigger = document.getElementById("locationMapTrigger");
    var popover = document.getElementById("locationMapPopover");
    var closeButton = document.getElementById("locationMapClose");
    var frame = document.getElementById("locationMapFrame");
    var frameShell = document.getElementById("locationMapFrameShell");
    var controller = window.HomepageAnchoredPopover;
    if (!trigger || !popover || !closeButton || !frame || !frameShell || !controller) {
      return;
    }

    var closeTimer = 0;
    var pinned = false;

    function clearScheduledClose() {
      if (!closeTimer) return;
      window.clearTimeout(closeTimer);
      closeTimer = 0;
    }

    function ensureMapLoaded() {
      if (frame.getAttribute("src")) return;
      var source = frame.getAttribute("data-src");
      if (!source) return;
      frame.setAttribute("src", source);
      frame.removeAttribute("data-src");
    }

    function openPopover(initialFocus) {
      clearScheduledClose();
      ensureMapLoaded();
      controller.open(popover, trigger, {
        placement: "right-start",
        initialFocus: initialFocus ? closeButton : null,
      });
    }

    function closePopover(restoreFocus) {
      clearScheduledClose();
      pinned = false;
      controller.close(popover, restoreFocus);
    }

    function scheduleClose() {
      if (pinned) return;
      clearScheduledClose();
      closeTimer = window.setTimeout(function () {
        closeTimer = 0;
        if (
          trigger.matches(":hover") ||
          popover.matches(":hover") ||
          trigger === document.activeElement ||
          popover.contains(document.activeElement)
        ) {
          return;
        }
        controller.close(popover, false);
      }, 160);
    }

    function openFromPointer(event) {
      if (event.pointerType === "touch") return;
      pinned = false;
      openPopover(false);
    }

    frame.addEventListener("load", function () {
      frameShell.classList.add("is-loaded");
      controller.reposition();
    });

    trigger.addEventListener("pointerenter", openFromPointer);
    trigger.addEventListener("pointerleave", scheduleClose);
    trigger.addEventListener("blur", scheduleClose);
    popover.addEventListener("pointerenter", clearScheduledClose);
    popover.addEventListener("pointerleave", scheduleClose);

    trigger.addEventListener("click", function (event) {
      clearScheduledClose();
      if (controller.isOpen(popover) && pinned) {
        closePopover(false);
        return;
      }

      pinned = true;
      if (controller.isOpen(popover)) {
        if (event.detail === 0) closeButton.focus({ preventScroll: true });
        return;
      }
      openPopover(event.detail === 0);
    });

    closeButton.addEventListener("click", function () {
      closePopover(true);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initLocationMapPopover, {
      passive: true,
    });
  } else {
    initLocationMapPopover();
  }
})();
