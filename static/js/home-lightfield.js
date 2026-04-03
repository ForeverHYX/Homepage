(function () {
    const field = document.querySelector(".home-lightfield");
    const layout = document.querySelector(".home-layout");
    if (!field || !layout) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const spotsConfig = [
        { size: [250, 320], blur: [42, 56], opacity: [0.22, 0.34], x: [0.01, 0.18], y: [0.04, 0.2] },
        { size: [250, 320], blur: [42, 56], opacity: [0.2, 0.32], x: [0.02, 0.18], y: [0.36, 0.62] },
        { size: [220, 290], blur: [40, 52], opacity: [0.18, 0.28], x: [0.26, 0.44], y: [0.18, 0.46] },
        { size: [220, 300], blur: [40, 54], opacity: [0.16, 0.26], x: [0.48, 0.74], y: [0.32, 0.68] },
    ];

    const rand = (min, max) => min + Math.random() * (max - min);
    const lerp = (from, to, t) => from + (to - from) * t;
    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
    const isDark = () => document.documentElement.getAttribute("data-theme") === "dark";

    function chooseTarget(config) {
        return {
            x: rand(config.x[0], config.x[1]),
            y: rand(config.y[0], config.y[1]),
            scale: rand(0.88, 1.16),
            opacity: rand(config.opacity[0], config.opacity[1]),
            size: rand(config.size[0], config.size[1]),
            blur: rand(config.blur[0], config.blur[1]),
        };
    }

    const spots = spotsConfig.map((config) => {
        const element = document.createElement("span");
        element.className = "home-lightspot";
        field.appendChild(element);

        const target = chooseTarget(config);
        const state = {
            element,
            config,
            x: target.x,
            y: target.y,
            scale: target.scale,
            opacity: target.opacity,
            size: target.size,
            blur: target.blur,
            target,
            nextChangeAt: performance.now() + rand(1800, 3400),
        };

        return state;
    });

    function applySpot(spot, rect) {
        const px = spot.x * rect.width;
        const py = spot.y * rect.height;
        spot.element.style.setProperty("--spot-size", `${spot.size.toFixed(1)}px`);
        spot.element.style.setProperty("--spot-blur", `${spot.blur.toFixed(1)}px`);
        spot.element.style.setProperty("--spot-opacity", spot.opacity.toFixed(3));
        spot.element.style.transform = `translate3d(${px.toFixed(1)}px, ${py.toFixed(1)}px, 0) scale(${spot.scale.toFixed(3)})`;
    }

    let rafId = 0;

    function frame(now) {
        rafId = 0;
        const rect = layout.getBoundingClientRect();

        spots.forEach((spot) => {
            if (now >= spot.nextChangeAt) {
                spot.target = chooseTarget(spot.config);
                spot.nextChangeAt = now + rand(2200, 4200);
            }

            spot.x = lerp(spot.x, spot.target.x, 0.018);
            spot.y = lerp(spot.y, spot.target.y, 0.018);
            spot.scale = lerp(spot.scale, spot.target.scale, 0.016);
            spot.opacity = lerp(spot.opacity, spot.target.opacity, 0.02);
            spot.size = lerp(spot.size, spot.target.size, 0.016);
            spot.blur = lerp(spot.blur, spot.target.blur, 0.016);

            const maxOpacity = isDark() ? 0.18 : 0.38;
            const minOpacity = isDark() ? 0.08 : 0.12;
            spot.opacity = clamp(spot.opacity, minOpacity, maxOpacity);
            applySpot(spot, rect);
        });

        if (!reduceMotion.matches && document.visibilityState === "visible") {
            rafId = window.requestAnimationFrame(frame);
        }
    }

    function start() {
        if (!rafId && !reduceMotion.matches) {
            rafId = window.requestAnimationFrame(frame);
        }
    }

    function stop() {
        if (rafId) {
            window.cancelAnimationFrame(rafId);
            rafId = 0;
        }
    }

    if (reduceMotion.matches) {
        const rect = layout.getBoundingClientRect();
        spots.forEach((spot) => applySpot(spot, rect));
        return;
    }

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            start();
        } else {
            stop();
        }
    });

    window.addEventListener("resize", start, { passive: true });
    start();
})();
