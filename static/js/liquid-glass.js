(function () {
    const cards = Array.from(document.querySelectorAll(".home-liquid-card"));
    if (!cards.length) return;

    const SVG_NS = "http://www.w3.org/2000/svg";
    const XLINK_NS = "http://www.w3.org/1999/xlink";
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const mobileViewport = window.matchMedia("(max-width: 800px)");
    if (mobileViewport.matches) return;
    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
    const lerp = (from, to, t) => from + (to - from) * t;

    function smoothstep(edge0, edge1, value) {
        const t = clamp((value - edge0) / Math.max(edge1 - edge0, 0.0001), 0, 1);
        return t * t * (3 - 2 * t);
    }

    function roundedRectSDF(x, y, halfWidth, halfHeight, radius) {
        const qx = Math.abs(x) - halfWidth + radius;
        const qy = Math.abs(y) - halfHeight + radius;
        const ax = Math.max(qx, 0);
        const ay = Math.max(qy, 0);
        return Math.hypot(ax, ay) + Math.min(Math.max(qx, qy), 0) - radius;
    }

    function ensureSvgRoot() {
        let svg = document.getElementById("home-liquid-svg-root");
        if (svg) return svg;

        svg = document.createElementNS(SVG_NS, "svg");
        svg.setAttribute("id", "home-liquid-svg-root");
        svg.setAttribute("aria-hidden", "true");
        svg.setAttribute("width", "0");
        svg.setAttribute("height", "0");
        svg.style.position = "absolute";
        svg.style.width = "0";
        svg.style.height = "0";
        svg.style.pointerEvents = "none";
        svg.style.overflow = "hidden";
        document.body.appendChild(svg);

        const defs = document.createElementNS(SVG_NS, "defs");
        svg.appendChild(defs);
        return svg;
    }

    function createDisplacementMap(width, height, radius) {
        const mapWidth = clamp(Math.round(width), 160, 360);
        const mapHeight = clamp(Math.round(height), 120, 420);
        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d", { alpha: false });
        if (!context) return "";

        canvas.width = mapWidth;
        canvas.height = mapHeight;

        const image = context.createImageData(mapWidth, mapHeight);
        const data = image.data;
        const halfWidth = mapWidth * 0.5 - 1.5;
        const halfHeight = mapHeight * 0.5 - 1.5;
        const maxRadius = Math.max(6, Math.min(radius, Math.min(halfWidth, halfHeight) - 2));
        const edgeWidth = Math.max(14, Math.min(mapWidth, mapHeight) * 0.16);
        const eps = 1.15;

        for (let y = 0; y < mapHeight; y += 1) {
            for (let x = 0; x < mapWidth; x += 1) {
                const px = x + 0.5 - mapWidth * 0.5;
                const py = y + 0.5 - mapHeight * 0.5;
                const dist = roundedRectSDF(px, py, halfWidth, halfHeight, maxRadius);
                const depth = Math.max(-dist, 0);

                let red = 128;
                let blue = 128;

                if (dist <= edgeWidth * 2.6) {
                    const gradX =
                        roundedRectSDF(px + eps, py, halfWidth, halfHeight, maxRadius) -
                        roundedRectSDF(px - eps, py, halfWidth, halfHeight, maxRadius);
                    const gradY =
                        roundedRectSDF(px, py + eps, halfWidth, halfHeight, maxRadius) -
                        roundedRectSDF(px, py - eps, halfWidth, halfHeight, maxRadius);
                    const gradLength = Math.hypot(gradX, gradY) || 1;
                    const nx = gradX / gradLength;
                    const ny = gradY / gradLength;

                    const rim = 1 - smoothstep(0, edgeWidth * 0.92, depth);
                    const shoulder =
                        smoothstep(edgeWidth * 0.14, edgeWidth * 0.52, depth) *
                        (1 - smoothstep(edgeWidth * 0.52, edgeWidth * 1.3, depth));
                    const plateau =
                        smoothstep(edgeWidth * 1.05, edgeWidth * 1.95, depth) *
                        (1 - smoothstep(edgeWidth * 1.95, edgeWidth * 3.1, depth));

                    const refraction = rim * 0.84 + shoulder * 0.24 + plateau * 0.06;
                    const dome = plateau * 0.12;
                    const domeX = (px / Math.max(halfWidth, 1)) * dome * 26;
                    const domeY = (py / Math.max(halfHeight, 1)) * dome * 26;
                    const shiftX = nx * refraction * 88 - domeX;
                    const shiftY = ny * refraction * 88 - domeY;

                    red = clamp(Math.round(128 + shiftX), 0, 255);
                    blue = clamp(Math.round(128 + shiftY), 0, 255);
                }

                const offset = (y * mapWidth + x) * 4;
                data[offset] = red;
                data[offset + 1] = 128;
                data[offset + 2] = blue;
                data[offset + 3] = 255;
            }
        }

        context.putImageData(image, 0, 0);
        return canvas.toDataURL("image/png");
    }

    function setHref(node, value) {
        node.setAttribute("href", value);
        node.setAttributeNS(XLINK_NS, "href", value);
    }

    function createNode(tag, attrs) {
        const node = document.createElementNS(SVG_NS, tag);
        Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
        return node;
    }

    function buildFilter(defs, id, mapUrl, scale, aberration) {
        const existing = defs.querySelector(`#${id}`);
        if (existing) existing.remove();

        const filter = createNode("filter", {
            id,
            x: "-35%",
            y: "-35%",
            width: "170%",
            height: "170%",
            "color-interpolation-filters": "sRGB",
        });

        const image = createNode("feImage", {
            x: "0",
            y: "0",
            width: "100%",
            height: "100%",
            result: "DISPLACEMENT_MAP",
            preserveAspectRatio: "none",
        });
        setHref(image, mapUrl);
        filter.appendChild(image);
        filter.appendChild(
            createNode("feColorMatrix", {
                in: "DISPLACEMENT_MAP",
                type: "matrix",
                values: [
                    "0.3 0.3 0.3 0 0",
                    "0.3 0.3 0.3 0 0",
                    "0.3 0.3 0.3 0 0",
                    "0 0 0 1 0",
                ].join(" "),
                result: "EDGE_INTENSITY",
            })
        );
        filter.appendChild(createNode("feComponentTransfer", { in: "EDGE_INTENSITY", result: "EDGE_MASK" }));
        const edgeMask = filter.lastChild;
        if (edgeMask) {
            edgeMask.appendChild(
                createNode("feFuncA", {
                    type: "discrete",
                    tableValues: `0 ${Math.min(aberration * 0.05, 0.24).toFixed(3)} 1`,
                })
            );
        }
        filter.appendChild(
            createNode("feOffset", {
                in: "SourceGraphic",
                dx: "0",
                dy: "0",
                result: "CENTER_ORIGINAL",
            })
        );

        const redDisp = createNode("feDisplacementMap", {
            in: "SourceGraphic",
            in2: "DISPLACEMENT_MAP",
            scale,
            xChannelSelector: "R",
            yChannelSelector: "B",
            result: "RED_DISPLACED",
        });
        filter.appendChild(redDisp);
        filter.appendChild(
            createNode("feColorMatrix", {
                in: "RED_DISPLACED",
                type: "matrix",
                values: "1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0",
                result: "RED_CHANNEL",
            })
        );

        const greenDisp = createNode("feDisplacementMap", {
            in: "SourceGraphic",
            in2: "DISPLACEMENT_MAP",
            scale: Math.max(scale * (1 - aberration * 0.05), 1),
            xChannelSelector: "R",
            yChannelSelector: "B",
            result: "GREEN_DISPLACED",
        });
        filter.appendChild(greenDisp);
        filter.appendChild(
            createNode("feColorMatrix", {
                in: "GREEN_DISPLACED",
                type: "matrix",
                values: "0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0",
                result: "GREEN_CHANNEL",
            })
        );

        const blueDisp = createNode("feDisplacementMap", {
            in: "SourceGraphic",
            in2: "DISPLACEMENT_MAP",
            scale: Math.max(scale * (1 - aberration * 0.1), 1),
            xChannelSelector: "R",
            yChannelSelector: "B",
            result: "BLUE_DISPLACED",
        });
        filter.appendChild(blueDisp);
        filter.appendChild(
            createNode("feColorMatrix", {
                in: "BLUE_DISPLACED",
                type: "matrix",
                values: "0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0",
                result: "BLUE_CHANNEL",
            })
        );

        filter.appendChild(createNode("feBlend", { in: "GREEN_CHANNEL", in2: "BLUE_CHANNEL", mode: "screen", result: "GB_BLEND" }));
        filter.appendChild(createNode("feBlend", { in: "RED_CHANNEL", in2: "GB_BLEND", mode: "screen", result: "RGB_BLEND" }));
        filter.appendChild(
            createNode("feGaussianBlur", {
                in: "RGB_BLEND",
                stdDeviation: Math.max(0.1, 0.5 - aberration * 0.1),
                result: "ABERRATED_BLURRED",
            })
        );
        filter.appendChild(
            createNode("feComposite", {
                in: "ABERRATED_BLURRED",
                in2: "EDGE_MASK",
                operator: "in",
                result: "EDGE_ABERRATION",
            })
        );
        filter.appendChild(createNode("feComponentTransfer", { in: "EDGE_MASK", result: "INVERTED_MASK" }));
        const invertedMask = filter.lastChild;
        if (invertedMask) {
            invertedMask.appendChild(
                createNode("feFuncA", {
                    type: "table",
                    tableValues: "1 0",
                })
            );
        }
        filter.appendChild(
            createNode("feComposite", {
                in: "CENTER_ORIGINAL",
                in2: "INVERTED_MASK",
                operator: "in",
                result: "CENTER_CLEAN",
            })
        );
        filter.appendChild(
            createNode("feComposite", {
                in: "EDGE_ABERRATION",
                in2: "CENTER_CLEAN",
                operator: "over",
            })
        );

        defs.appendChild(filter);
    }

    const svgRoot = ensureSvgRoot();
    const defs = svgRoot.querySelector("defs");
    if (!defs) return;

    const states = cards.map((card, index) => ({
        card,
        warp: card.querySelector(".home-liquid-warp"),
        id: `home-liquid-filter-${index + 1}`,
        width: 0,
        height: 0,
        radius: 0,
        theme: "",
        current: { lightX: 18, lightY: 12, angle: 135, glow: 0.78 },
        target: { lightX: 18, lightY: 12, angle: 135, glow: 0.78 },
    })).filter((state) => state.warp);

    if (!states.length) return;

    function syncFilter(state) {
        const styles = getComputedStyle(state.card);
        const rect = state.card.getBoundingClientRect();
        const width = Math.round(rect.width);
        const height = Math.round(rect.height);
        const radius = parseFloat(styles.borderTopLeftRadius) || 32;
        const theme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";

        if (width < 20 || height < 20) return;
        if (state.width === width && state.height === height && state.radius === radius && state.theme === theme) {
            return;
        }

        state.width = width;
        state.height = height;
        state.radius = radius;
        state.theme = theme;

        const displacementScale = parseFloat(styles.getPropertyValue("--liquid-displacement-scale")) || (theme === "dark" ? 22 : 25);
        const aberration = parseFloat(styles.getPropertyValue("--liquid-aberration")) || (theme === "dark" ? 1.4 : 1.8);
        const mapUrl = createDisplacementMap(width, height, radius);
        buildFilter(defs, state.id, mapUrl, displacementScale, aberration);

        state.warp.style.filter = `url(#${state.id})`;
        state.warp.style.backdropFilter = `blur(${styles.getPropertyValue("--liquid-blur").trim() || "22px"}) saturate(${styles.getPropertyValue("--liquid-saturation").trim() || "180%"}) brightness(${styles.getPropertyValue("--liquid-brightness").trim() || "1.08"})`;
        state.warp.style.webkitBackdropFilter = state.warp.style.backdropFilter;
    }

    let rafId = 0;

    function applyState(state) {
        state.card.style.setProperty("--liquid-light-x", `${state.current.lightX.toFixed(2)}%`);
        state.card.style.setProperty("--liquid-light-y", `${state.current.lightY.toFixed(2)}%`);
        state.card.style.setProperty("--liquid-angle", `${state.current.angle.toFixed(2)}deg`);
        state.card.style.setProperty("--liquid-glow", state.current.glow.toFixed(3));
    }

    function frame() {
        rafId = 0;
        let pending = false;

        states.forEach((state) => {
            state.current.lightX = lerp(state.current.lightX, state.target.lightX, 0.14);
            state.current.lightY = lerp(state.current.lightY, state.target.lightY, 0.14);
            state.current.angle = lerp(state.current.angle, state.target.angle, 0.14);
            state.current.glow = lerp(state.current.glow, state.target.glow, 0.12);
            applyState(state);

            const delta =
                Math.abs(state.current.lightX - state.target.lightX) +
                Math.abs(state.current.lightY - state.target.lightY) +
                Math.abs(state.current.angle - state.target.angle) +
                Math.abs(state.current.glow - state.target.glow);

            if (delta > 0.08) pending = true;
        });

        if (pending) rafId = window.requestAnimationFrame(frame);
    }

    function scheduleFrame() {
        if (!rafId) rafId = window.requestAnimationFrame(frame);
    }

    function resetTarget(state) {
        state.target.lightX = 18;
        state.target.lightY = 12;
        state.target.angle = 135;
        state.target.glow = 0.78;
        scheduleFrame();
    }

    states.forEach((state) => {
        syncFilter(state);
        applyState(state);

        if (!reduceMotion.matches) {
            state.card.addEventListener("pointermove", (event) => {
                const rect = state.card.getBoundingClientRect();
                const x = clamp(((event.clientX - rect.left) / rect.width) * 100, 8, 92);
                const y = clamp(((event.clientY - rect.top) / rect.height) * 100, 8, 92);
                const dx = (x - 50) / 50;
                const dy = (y - 50) / 50;

                state.target.lightX = x;
                state.target.lightY = y;
                state.target.angle = 135 + dx * 18 + dy * 10;
                state.target.glow = 0.84 + (Math.abs(dx) + Math.abs(dy)) * 0.08;
                scheduleFrame();
            });

            state.card.addEventListener("pointerleave", () => resetTarget(state));
            state.card.addEventListener("pointercancel", () => resetTarget(state));
        }
    });

    const resizeObserver = new ResizeObserver(() => {
        states.forEach(syncFilter);
    });
    states.forEach((state) => resizeObserver.observe(state.card));

    const themeObserver = new MutationObserver(() => {
        states.forEach(syncFilter);
    });
    themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme"],
    });

    window.addEventListener("resize", () => {
        states.forEach(syncFilter);
    }, { passive: true });

    const handleMotionChange = () => {
        if (reduceMotion.matches) {
            states.forEach((state) => {
                state.current = { lightX: 18, lightY: 12, angle: 135, glow: 0.78 };
                state.target = { lightX: 18, lightY: 12, angle: 135, glow: 0.78 };
                applyState(state);
            });
        }
    };

    if (typeof reduceMotion.addEventListener === "function") {
        reduceMotion.addEventListener("change", handleMotionChange);
    } else if (typeof reduceMotion.addListener === "function") {
        reduceMotion.addListener(handleMotionChange);
    }
})();
