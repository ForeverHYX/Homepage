/**
 * Gallery carousel + lightbox
 * --------------------------------
 * - Auto-scrolls each carousel rightward by 400px every 2s (skipped in focus mode)
 * - Pauses on hover/touch, resumes on leave/touchend
 * - Lightbox opens on slide click, closes on close button / overlay background
 */
(function () {
    "use strict";

    // Auto-scroll step (px) and interval (ms)
    var SCROLL_STEP = 400;
    var SCROLL_INTERVAL = 2000;

    /**
     * Wire up a single carousel: auto-scroll + pause/resume behaviour.
     * @param {HTMLElement} container - the .carousel-container element
     */
    function setupCarousel(container) {
        var intervalId = null;
        var paused = false;

        function tick() {
            if (paused) return;
            // At or past max scroll: snap back to start
            if (container.scrollLeft + container.clientWidth >= container.scrollWidth - 4) {
                container.scrollTo({ left: 0, behavior: "smooth" });
            } else {
                container.scrollBy({ left: SCROLL_STEP, behavior: "smooth" });
            }
        }

        function start() {
            if (intervalId !== null) return;
            intervalId = window.setInterval(tick, SCROLL_INTERVAL);
        }

        function stop() {
            if (intervalId !== null) {
                window.clearInterval(intervalId);
                intervalId = null;
            }
        }

        // Pause on hover / touch start
        container.addEventListener("mouseenter", function () { paused = true; });
        container.addEventListener("touchstart", function () { paused = true; }, { passive: true });

        // Resume on mouse leave / touch end
        container.addEventListener("mouseleave", function () { paused = false; });
        container.addEventListener("touchend", function () { paused = false; }, { passive: true });

        start();
    }

    /**
     * Wire up the lightbox: slide click to open, close button + overlay to close.
     */
    function setupLightbox() {
        var overlay = document.getElementById("lightbox-overlay");
        var closeBtn = document.getElementById("lightboxClose");
        var img = document.getElementById("lightboxImg");
        if (!overlay || !closeBtn || !img) return;

        // Open lightbox when any slide is clicked
        document.querySelectorAll(".carousel-slide").forEach(function (slide) {
            slide.addEventListener("click", function () {
                var src = slide.getAttribute("data-src");
                img.src = src;
                overlay.style.display = "flex";
                overlay.classList.add("active");
            });
        });

        // Close via close button
        closeBtn.addEventListener("click", function () {
            overlay.style.display = "none";
            overlay.classList.remove("active");
        });

        // Close when clicking the overlay background only (not the image)
        overlay.addEventListener("click", function () {
            overlay.style.display = "none";
            overlay.classList.remove("active");
        });

        // Prevent the image itself from closing the lightbox
        img.addEventListener("click", function (e) {
            e.stopPropagation();
        });
    }

    function init() {
        // Focus mode: any URL with ?focus=... disables auto-scroll
        var isFocused = /[?&]focus=/.test(window.location.search);

        document.querySelectorAll(".carousel-container").forEach(function (container) {
            // Only set up auto-scroll for carousels inside a .gallery-album (not in focus mode)
            var album = container.closest(".gallery-album");
            if (!isFocused && album) {
                setupCarousel(container);
            }
        });

        setupLightbox();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
