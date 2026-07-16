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
    var carouselStates = [];
    var carouselStateByElement = new WeakMap();
    var intersectionObserver = null;
    var schedulerTimer = null;
    var nextTickAt = 0;
    var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    function hasOverflow(state) {
        return state.container.scrollWidth > state.container.clientWidth + 4;
    }

    function tickCarousel(state) {
        var container = state.container;
        if (!hasOverflow(state)) return;
        if (container.scrollLeft + container.clientWidth >= container.scrollWidth - 4) {
            container.scrollTo({ left: 0, behavior: "smooth" });
        } else {
            container.scrollBy({ left: SCROLL_STEP, behavior: "smooth" });
        }
    }

    function hasRunnableCarousel() {
        return carouselStates.some(function (state) {
            return state.visible && !state.paused && hasOverflow(state);
        });
    }

    function stopScheduler() {
        if (schedulerTimer !== null) {
            window.clearTimeout(schedulerTimer);
            schedulerTimer = null;
        }
        nextTickAt = 0;
    }

    function updateScheduler() {
        if (document.hidden || reduceMotion.matches || !hasRunnableCarousel()) {
            stopScheduler();
            return;
        }
        if (schedulerTimer !== null) return;

        var now = window.performance.now();
        if (!nextTickAt || nextTickAt <= now) {
            nextTickAt = now + SCROLL_INTERVAL;
        }
        schedulerTimer = window.setTimeout(runScheduledTick, Math.max(0, nextTickAt - now));
    }

    function runScheduledTick() {
        schedulerTimer = null;
        if (document.hidden || reduceMotion.matches || !hasRunnableCarousel()) {
            stopScheduler();
            return;
        }

        carouselStates.forEach(function (state) {
            if (state.visible && !state.paused) tickCarousel(state);
        });

        var now = window.performance.now();
        do {
            nextTickAt += SCROLL_INTERVAL;
        } while (nextTickAt <= now);
        updateScheduler();
    }

    /**
     * Wire up a single carousel: auto-scroll + pause/resume behaviour.
     * @param {HTMLElement} container - the .carousel-container element
     */
    function setupCarousel(container) {
        var state = {
            container: container,
            paused: false,
            visible: !intersectionObserver
        };
        carouselStates.push(state);
        carouselStateByElement.set(container, state);

        // Pause on hover / touch start
        container.addEventListener("mouseenter", function () {
            state.paused = true;
            updateScheduler();
        });
        container.addEventListener("touchstart", function () {
            state.paused = true;
            updateScheduler();
        }, { passive: true });

        // Resume on mouse leave / touch end
        container.addEventListener("mouseleave", function () {
            state.paused = false;
            updateScheduler();
        });
        function resumeAfterTouch() {
            state.paused = false;
            updateScheduler();
        }
        container.addEventListener("touchend", resumeAfterTouch, { passive: true });
        container.addEventListener("touchcancel", resumeAfterTouch, { passive: true });

        if (intersectionObserver) intersectionObserver.observe(container);
    }

    /**
     * Wire up the lightbox: slide click to open, close button + overlay to close.
     */
    function setupLightbox() {
        var overlay = document.getElementById("lightbox-overlay");
        var closeBtn = document.getElementById("lightboxClose");
        var img = document.getElementById("lightboxImg");
        var fullImageLoadToken = 0;
        if (!overlay || !closeBtn || !img) return;

        function closeLightbox() {
            fullImageLoadToken += 1;
            overlay.style.display = "none";
            overlay.classList.remove("active");
            img.removeAttribute("src");
        }

        // Open lightbox when any slide is clicked
        document.querySelectorAll(".carousel-slide").forEach(function (slide) {
            slide.addEventListener("click", function () {
                var fullSrc = slide.getAttribute("data-src") || "";
                var preview = slide.querySelector("img");
                var previewSrc = preview ? (preview.currentSrc || preview.src) : "";
                var resolvedFullSrc = fullSrc ? new URL(fullSrc, document.baseURI).href : "";
                var loadToken = ++fullImageLoadToken;

                // Paint the already-decoded carousel image immediately, then
                // replace it only after the full-resolution source is ready.
                img.src = previewSrc || resolvedFullSrc;
                overlay.style.display = "flex";
                overlay.classList.add("active");

                if (!resolvedFullSrc || resolvedFullSrc === previewSrc) return;
                var fullImage = new window.Image();
                fullImage.decoding = "async";
                fullImage.onload = function () {
                    if (loadToken !== fullImageLoadToken) return;
                    if (!overlay.classList.contains("active")) return;
                    img.src = resolvedFullSrc;
                };
                fullImage.src = resolvedFullSrc;
            });
        });

        // Close via close button
        closeBtn.addEventListener("click", closeLightbox);

        // Close when clicking the overlay background only (not the image)
        overlay.addEventListener("click", closeLightbox);

        // Prevent the image itself from closing the lightbox
        img.addEventListener("click", function (e) {
            e.stopPropagation();
        });
    }

    function init() {
        // Focus mode: any URL with ?focus=... disables auto-scroll
        var isFocused = /[?&]focus=/.test(window.location.search);

        if (!isFocused && "IntersectionObserver" in window) {
            intersectionObserver = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    var state = carouselStateByElement.get(entry.target);
                    if (state) state.visible = entry.isIntersecting && entry.intersectionRatio > 0;
                });
                updateScheduler();
            }, { threshold: 0.01 });
        }

        document.querySelectorAll(".carousel-container").forEach(function (container) {
            // Only set up auto-scroll for carousels inside a .gallery-album (not in focus mode)
            var album = container.closest(".gallery-album");
            if (!isFocused && album) {
                setupCarousel(container);
            }
        });

        if (carouselStates.length) {
            document.addEventListener("visibilitychange", updateScheduler);
            if (typeof reduceMotion.addEventListener === "function") {
                reduceMotion.addEventListener("change", updateScheduler);
            } else if (typeof reduceMotion.addListener === "function") {
                reduceMotion.addListener(updateScheduler);
            }
            window.addEventListener("pagehide", stopScheduler);
            window.addEventListener("pageshow", updateScheduler);
            updateScheduler();
        }

        setupLightbox();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
