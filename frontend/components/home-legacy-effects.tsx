"use client";

import { useEffect } from "react";

function initHomeLightfield() {
  const field = document.querySelector<HTMLElement>(".home-lightfield");
  if (!field) return () => {};

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const spotsConfig = [
    {
      size: [420, 620],
      blur: [74, 108],
      opacity: [0.42, 0.62],
      x: [-0.02, 0.18],
      y: [0.02, 0.22],
      scale: [0.92, 1.16],
      parallax: 32,
      lightColors: [
        "rgba(99, 102, 241, 0.72)",
        "rgba(59, 130, 246, 0.46)",
        "rgba(59, 130, 246, 0.12)",
        "rgba(59, 130, 246, 0)",
      ],
      darkColors: [
        "rgba(129, 140, 248, 0.74)",
        "rgba(96, 165, 250, 0.48)",
        "rgba(59, 130, 246, 0.14)",
        "rgba(59, 130, 246, 0)",
      ],
    },
    {
      size: [400, 560],
      blur: [72, 102],
      opacity: [0.36, 0.54],
      x: [0.18, 0.42],
      y: [-0.04, 0.18],
      scale: [0.9, 1.18],
      parallax: 26,
      lightColors: [
        "rgba(56, 189, 248, 0.64)",
        "rgba(103, 232, 249, 0.36)",
        "rgba(56, 189, 248, 0.1)",
        "rgba(56, 189, 248, 0)",
      ],
      darkColors: [
        "rgba(34, 211, 238, 0.54)",
        "rgba(59, 130, 246, 0.34)",
        "rgba(56, 189, 248, 0.08)",
        "rgba(56, 189, 248, 0)",
      ],
    },
    {
      size: [360, 520],
      blur: [64, 92],
      opacity: [0.28, 0.42],
      x: [0.52, 0.78],
      y: [0.14, 0.42],
      scale: [0.9, 1.14],
      parallax: 20,
      lightColors: [
        "rgba(168, 85, 247, 0.48)",
        "rgba(192, 132, 252, 0.28)",
        "rgba(192, 132, 252, 0.08)",
        "rgba(192, 132, 252, 0)",
      ],
      darkColors: [
        "rgba(192, 132, 252, 0.5)",
        "rgba(129, 140, 248, 0.28)",
        "rgba(129, 140, 248, 0.08)",
        "rgba(129, 140, 248, 0)",
      ],
    },
    {
      size: [380, 540],
      blur: [68, 96],
      opacity: [0.24, 0.4],
      x: [0.06, 0.24],
      y: [0.58, 0.84],
      scale: [0.92, 1.2],
      parallax: 28,
      lightColors: [
        "rgba(34, 197, 94, 0.22)",
        "rgba(45, 212, 191, 0.2)",
        "rgba(125, 211, 252, 0.08)",
        "rgba(125, 211, 252, 0)",
      ],
      darkColors: [
        "rgba(45, 212, 191, 0.26)",
        "rgba(56, 189, 248, 0.18)",
        "rgba(56, 189, 248, 0.08)",
        "rgba(56, 189, 248, 0)",
      ],
    },
    {
      size: [420, 580],
      blur: [72, 102],
      opacity: [0.26, 0.42],
      x: [0.64, 0.9],
      y: [0.54, 0.86],
      scale: [0.9, 1.16],
      parallax: 24,
      lightColors: [
        "rgba(244, 114, 182, 0.28)",
        "rgba(251, 191, 36, 0.18)",
        "rgba(251, 191, 36, 0.08)",
        "rgba(251, 191, 36, 0)",
      ],
      darkColors: [
        "rgba(236, 72, 153, 0.24)",
        "rgba(168, 85, 247, 0.16)",
        "rgba(129, 140, 248, 0.08)",
        "rgba(129, 140, 248, 0)",
      ],
    },
    {
      size: [300, 420],
      blur: [58, 84],
      opacity: [0.18, 0.3],
      x: [0.34, 0.58],
      y: [0.34, 0.6],
      scale: [0.88, 1.12],
      parallax: 16,
      lightColors: [
        "rgba(255, 255, 255, 0.72)",
        "rgba(224, 242, 254, 0.34)",
        "rgba(224, 242, 254, 0.1)",
        "rgba(224, 242, 254, 0)",
      ],
      darkColors: [
        "rgba(255, 255, 255, 0.18)",
        "rgba(96, 165, 250, 0.16)",
        "rgba(96, 165, 250, 0.06)",
        "rgba(96, 165, 250, 0)",
      ],
    },
  ];

  const rand = (min: number, max: number) => min + Math.random() * (max - min);
  const lerp = (from: number, to: number, t: number) => from + (to - from) * t;
  const clamp = (value: number, min: number, max: number) =>
    Math.min(max, Math.max(min, value));
  const isDark = () => document.documentElement.getAttribute("data-theme") === "dark";

  const chooseTarget = (config: (typeof spotsConfig)[number]) => ({
    x: rand(config.x[0], config.x[1]),
    y: rand(config.y[0], config.y[1]),
    scale: rand(config.scale[0], config.scale[1]),
    opacity: rand(config.opacity[0], config.opacity[1]),
    size: rand(config.size[0], config.size[1]),
    blur: rand(config.blur[0], config.blur[1]),
  });

  const renderGradient = (colors: string[]) =>
    `radial-gradient(circle at 50% 50%, ${colors[0]} 0%, ${colors[1]} 28%, ${colors[2]} 58%, ${colors[3]} 80%)`;

  const applyPalette = () => {
    const dark = isDark();
    spots.forEach((spot) => {
      spot.element.style.background = renderGradient(
        dark ? spot.config.darkColors : spot.config.lightColors
      );
    });
  };

  const pointer = { currentX: 0, currentY: 0, targetX: 0, targetY: 0 };
  const resetPointer = () => {
    pointer.targetX = 0;
    pointer.targetY = 0;
  };

  const spots = spotsConfig.map((config) => {
    const element = document.createElement("span");
    element.className = "home-lightspot";
    field.appendChild(element);

    const target = chooseTarget(config);
    return {
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
  });

  applyPalette();

  const applySpot = (
    spot: (typeof spots)[number],
    viewport: { width: number; height: number }
  ) => {
    const px = spot.x * viewport.width + pointer.currentX * spot.config.parallax;
    const py = spot.y * viewport.height + pointer.currentY * spot.config.parallax;
    spot.element.style.setProperty("--spot-size", `${spot.size.toFixed(1)}px`);
    spot.element.style.setProperty("--spot-blur", `${spot.blur.toFixed(1)}px`);
    spot.element.style.setProperty("--spot-opacity", spot.opacity.toFixed(3));
    spot.element.style.transform = `translate3d(${px.toFixed(1)}px, ${py.toFixed(1)}px, 0) scale(${spot.scale.toFixed(3)})`;
  };

  let rafId = 0;

  const frame = (now: number) => {
    rafId = 0;
    const viewport = {
      width: window.innerWidth,
      height: window.innerHeight,
    };
    pointer.currentX = lerp(pointer.currentX, pointer.targetX, 0.05);
    pointer.currentY = lerp(pointer.currentY, pointer.targetY, 0.05);

    spots.forEach((spot) => {
      if (now >= spot.nextChangeAt) {
        spot.target = chooseTarget(spot.config);
        spot.nextChangeAt = now + rand(4200, 8200);
      }

      spot.x = lerp(spot.x, spot.target.x, 0.0065);
      spot.y = lerp(spot.y, spot.target.y, 0.0065);
      spot.scale = lerp(spot.scale, spot.target.scale, 0.006);
      spot.opacity = lerp(spot.opacity, spot.target.opacity, 0.012);
      spot.size = lerp(spot.size, spot.target.size, 0.005);
      spot.blur = lerp(spot.blur, spot.target.blur, 0.005);

      const maxOpacity = isDark() ? 0.42 : 0.6;
      const minOpacity = isDark() ? 0.14 : 0.18;
      spot.opacity = clamp(spot.opacity, minOpacity, maxOpacity);
      applySpot(spot, viewport);
    });

    if (!reduceMotion.matches && document.visibilityState === "visible") {
      rafId = window.requestAnimationFrame(frame);
    }
  };

  const start = () => {
    if (!rafId && !reduceMotion.matches) {
      rafId = window.requestAnimationFrame(frame);
    }
  };

  const stop = () => {
    if (rafId) {
      window.cancelAnimationFrame(rafId);
      rafId = 0;
    }
  };

  const handleVisibility = () => {
    if (document.visibilityState === "visible") {
      start();
    } else {
      stop();
    }
  };

  const handlePointerMove = (event: PointerEvent) => {
    const x = clamp(event.clientX / Math.max(window.innerWidth, 1), 0, 1);
    const y = clamp(event.clientY / Math.max(window.innerHeight, 1), 0, 1);
    pointer.targetX = (x - 0.5) * 42;
    pointer.targetY = (y - 0.5) * 34;
  };

  const themeObserver = new MutationObserver(() => {
    applyPalette();
    start();
  });
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });

  if (reduceMotion.matches) {
    const viewport = {
      width: window.innerWidth,
      height: window.innerHeight,
    };
    spots.forEach((spot) => applySpot(spot, viewport));
  } else {
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("resize", start, { passive: true });
    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    window.addEventListener("pointerleave", resetPointer);
    window.addEventListener("blur", resetPointer);

    start();

    return () => {
      stop();
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("resize", start);
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerleave", resetPointer);
      window.removeEventListener("blur", resetPointer);
      themeObserver.disconnect();
      spots.forEach((spot) => spot.element.remove());
    };
  }

  return () => {
    stop();
    document.removeEventListener("visibilitychange", handleVisibility);
    window.removeEventListener("resize", start);
    window.removeEventListener("pointermove", handlePointerMove);
    window.removeEventListener("pointerleave", resetPointer);
    window.removeEventListener("blur", resetPointer);
    themeObserver.disconnect();
    spots.forEach((spot) => spot.element.remove());
  };
}

function initHomeLiquidGlass() {
  const cards = Array.from(
    document.querySelectorAll<HTMLElement>(".home-liquid-card")
  );
  if (!cards.length) return () => {};

  const SVG_NS = "http://www.w3.org/2000/svg";
  const XLINK_NS = "http://www.w3.org/1999/xlink";
  const desktopLiquidGlass = window.matchMedia("(min-width: 801px)");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const clamp = (value: number, min: number, max: number) =>
    Math.min(max, Math.max(min, value));
  const lerp = (from: number, to: number, t: number) => from + (to - from) * t;
  const displacementMapCache = new Map<string, string>();

  const smoothstep = (edge0: number, edge1: number, value: number) => {
    const t = clamp((value - edge0) / Math.max(edge1 - edge0, 0.0001), 0, 1);
    return t * t * (3 - 2 * t);
  };

  const roundedRectSDF = (
    x: number,
    y: number,
    halfWidth: number,
    halfHeight: number,
    radius: number
  ) => {
    const qx = Math.abs(x) - halfWidth + radius;
    const qy = Math.abs(y) - halfHeight + radius;
    const ax = Math.max(qx, 0);
    const ay = Math.max(qy, 0);
    return Math.hypot(ax, ay) + Math.min(Math.max(qx, qy), 0) - radius;
  };

  type FilterRefs = {
    filter: Element;
    image: Element;
    edgeMaskAlpha: Element;
    displacements: Element[];
    blur: Element;
  };

  type LiquidState = {
    card: HTMLElement;
    warp: HTMLElement;
    id: string;
    width: number;
    height: number;
    radius: number;
    theme: string;
    mapKey: string;
    displacementScale: number;
    aberration: number;
    backdropFilter: string;
    active: boolean;
    filterRefs: FilterRefs | null;
    bounds: { left: number; top: number; width: number; height: number };
    current: { lightX: number; lightY: number; angle: number; glow: number };
    target: { lightX: number; lightY: number; angle: number; glow: number };
  };

  const ensureSvgRoot = () => {
    let svg = document.getElementById("home-liquid-svg-root") as SVGSVGElement | null;
    if (svg) {
      const defs = svg.querySelector("defs");
      if (defs) {
        return { svg, defs };
      }
    }

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
    return { svg, defs };
  };

  const getMapSpec = (width: number, height: number, radius: number) => {
    const mapWidth = clamp(Math.round(width), 160, 360);
    const mapHeight = clamp(Math.round(height), 120, 420);
    const halfWidth = mapWidth * 0.5 - 1.5;
    const halfHeight = mapHeight * 0.5 - 1.5;
    const mapRadius = Math.max(
      6,
      Math.min(radius, Math.min(halfWidth, halfHeight) - 2)
    );
    const normalizedRadius = Number(mapRadius.toFixed(2));

    return {
      mapWidth,
      mapHeight,
      mapRadius,
      key: `${mapWidth}x${mapHeight}x${normalizedRadius}`,
    };
  };

  const createDisplacementMap = (
    mapWidth: number,
    mapHeight: number,
    radius: number
  ) => {
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d", { alpha: false });
    if (!context) return "";

    canvas.width = mapWidth;
    canvas.height = mapHeight;

    const image = context.createImageData(mapWidth, mapHeight);
    const data = image.data;
    const halfWidth = mapWidth * 0.5 - 1.5;
    const halfHeight = mapHeight * 0.5 - 1.5;
    const maxRadius = radius;
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
  };

  const getDisplacementMap = (width: number, height: number, radius: number) => {
    const spec = getMapSpec(width, height, radius);
    let mapUrl = displacementMapCache.get(spec.key);

    if (!mapUrl) {
      mapUrl = createDisplacementMap(
        spec.mapWidth,
        spec.mapHeight,
        spec.mapRadius
      );
      displacementMapCache.set(spec.key, mapUrl);
    }

    return {
      key: spec.key,
      url: mapUrl,
    };
  };

  const setHref = (node: Element, value: string) => {
    node.setAttribute("href", value);
    node.setAttributeNS(XLINK_NS, "href", value);
  };

  const createNode = (tag: string, attrs: Record<string, string | number>) => {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs).forEach(([key, value]) =>
      node.setAttribute(key, String(value))
    );
    return node;
  };

  const createFilter = (defs: SVGDefsElement, id: string): FilterRefs => {
    defs.querySelector(`#${id}`)?.remove();

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
    const edgeMask = createNode("feComponentTransfer", {
      in: "EDGE_INTENSITY",
      result: "EDGE_MASK",
    });
    const edgeMaskAlpha = createNode("feFuncA", {
      type: "discrete",
      tableValues: "0 0.09 1",
    });
    edgeMask.appendChild(edgeMaskAlpha);
    filter.appendChild(edgeMask);

    filter.appendChild(
      createNode("feOffset", {
        in: "SourceGraphic",
        dx: "0",
        dy: "0",
        result: "CENTER_ORIGINAL",
      })
    );

    const channels: Array<["RED" | "GREEN" | "BLUE", string, number]> = [
      ["RED", "1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0", 1],
      ["GREEN", "0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0", 1],
      ["BLUE", "0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0", 1],
    ];

    const displacements = channels.map(([name, matrix, channelScale]) => {
      const displacement = createNode("feDisplacementMap", {
          in: "SourceGraphic",
          in2: "DISPLACEMENT_MAP",
          scale: channelScale,
          xChannelSelector: "R",
          yChannelSelector: "B",
          result: `${name}_DISPLACED`,
      });
      filter.appendChild(displacement);
      filter.appendChild(
        createNode("feColorMatrix", {
          in: `${name}_DISPLACED`,
          type: "matrix",
          values: matrix,
          result: `${name}_CHANNEL`,
        })
      );
      return displacement;
    });

    filter.appendChild(
      createNode("feBlend", {
        in: "GREEN_CHANNEL",
        in2: "BLUE_CHANNEL",
        mode: "screen",
        result: "GB_BLEND",
      })
    );
    filter.appendChild(
      createNode("feBlend", {
        in: "RED_CHANNEL",
        in2: "GB_BLEND",
        mode: "screen",
        result: "RGB_BLEND",
      })
    );
    const blur = createNode("feGaussianBlur", {
      in: "RGB_BLEND",
      stdDeviation: "0.32",
      result: "ABERRATED_BLURRED",
    });
    filter.appendChild(
      blur
    );
    filter.appendChild(
      createNode("feComposite", {
        in: "ABERRATED_BLURRED",
        in2: "EDGE_MASK",
        operator: "in",
        result: "EDGE_ABERRATION",
      })
    );

    const invertedMask = createNode("feComponentTransfer", {
      in: "EDGE_MASK",
      result: "INVERTED_MASK",
    });
    invertedMask.appendChild(
      createNode("feFuncA", {
        type: "table",
        tableValues: "1 0",
      })
    );
    filter.appendChild(invertedMask);
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

    return {
      filter,
      image,
      edgeMaskAlpha,
      displacements,
      blur,
    };
  };

  const updateFilter = (
    refs: FilterRefs,
    mapUrl: string,
    scale: number,
    aberration: number
  ) => {
    setHref(refs.image, mapUrl);
    refs.edgeMaskAlpha.setAttribute(
      "tableValues",
      `0 ${Math.min(aberration * 0.05, 0.24).toFixed(3)} 1`
    );

    const channelScales = [
      scale,
      Math.max(scale * (1 - aberration * 0.05), 1),
      Math.max(scale * (1 - aberration * 0.1), 1),
    ];
    refs.displacements.forEach((displacement, index) => {
      displacement.setAttribute("scale", channelScales[index].toFixed(3));
    });
    refs.blur.setAttribute(
      "stdDeviation",
      Math.max(0.1, 0.5 - aberration * 0.1).toFixed(3)
    );
  };

  const { defs } = ensureSvgRoot();
  const states: LiquidState[] = cards.flatMap((card, index) => {
    const warp = card.querySelector<HTMLElement>(".home-liquid-warp");
    if (!warp) {
      return [];
    }

    return [{
      card,
      warp,
      id: `home-liquid-filter-${index + 1}`,
      width: 0,
      height: 0,
      radius: 0,
      theme: "",
      mapKey: "",
      displacementScale: 0,
      aberration: 0,
      backdropFilter: "",
      active: false,
      filterRefs: null,
      bounds: { left: 0, top: 0, width: 0, height: 0 },
      current: { lightX: 18, lightY: 12, angle: 135, glow: 0.58 },
      target: { lightX: 18, lightY: 12, angle: 135, glow: 0.58 },
    }];
  });

  if (!states.length) return () => {};

  const syncGeometry = (state: LiquidState) => {
    const rect = state.card.getBoundingClientRect();
    state.bounds.left = rect.left;
    state.bounds.top = rect.top;
    state.bounds.width = rect.width;
    state.bounds.height = rect.height;
    return rect;
  };

  const clearFilter = (state: LiquidState) => {
    if (!state.active && !state.backdropFilter) {
      return;
    }

    state.active = false;
    state.backdropFilter = "";
    state.warp.style.filter = "";
    state.warp.style.backdropFilter = "";
    state.warp.style.removeProperty("-webkit-backdrop-filter");
  };

  const syncFilter = (state: LiquidState) => {
    const rect = syncGeometry(state);
    const styles = getComputedStyle(state.card);
    const width = Math.round(rect.width);
    const height = Math.round(rect.height);
    const radius = parseFloat(styles.borderTopLeftRadius) || 32;
    const theme =
      document.documentElement.getAttribute("data-theme") === "dark"
        ? "dark"
        : "light";
    const warpVisible = getComputedStyle(state.warp).display !== "none";
    const displacementScale =
      parseFloat(styles.getPropertyValue("--liquid-displacement-scale")) ||
      (theme === "dark" ? 22 : 25);
    const aberration =
      parseFloat(styles.getPropertyValue("--liquid-aberration")) ||
      (theme === "dark" ? 1.4 : 1.8);
    const backdropFilter = `blur(${styles.getPropertyValue("--liquid-blur").trim() || "22px"}) saturate(${styles.getPropertyValue("--liquid-saturation").trim() || "180%"}) brightness(${styles.getPropertyValue("--liquid-brightness").trim() || "1.08"})`;
    const enabled =
      desktopLiquidGlass.matches && warpVisible && width >= 20 && height >= 20;

    if (!enabled) {
      state.width = width;
      state.height = height;
      state.radius = radius;
      state.theme = theme;
      state.displacementScale = displacementScale;
      state.aberration = aberration;
      state.mapKey = "";
      clearFilter(state);
      return;
    }

    const geometryChanged =
      state.width !== width || state.height !== height || state.radius !== radius;
    const themeChanged = state.theme !== theme;
    const filterChanged =
      state.displacementScale !== displacementScale ||
      state.aberration !== aberration;
    const backdropChanged = state.backdropFilter !== backdropFilter;

    state.width = width;
    state.height = height;
    state.radius = radius;
    state.theme = theme;
    state.displacementScale = displacementScale;
    state.aberration = aberration;
    state.backdropFilter = backdropFilter;

    if (
      state.active &&
      !geometryChanged &&
      !themeChanged &&
      !filterChanged &&
      !backdropChanged
    ) {
      return;
    }

    const refs = state.filterRefs ?? (state.filterRefs = createFilter(defs, state.id));
    if (geometryChanged || !state.mapKey || filterChanged || themeChanged) {
      const map = getDisplacementMap(width, height, radius);
      state.mapKey = map.key;
      updateFilter(refs, map.url, displacementScale, aberration);
    }

    state.warp.style.filter = `url(#${state.id})`;
    state.warp.style.backdropFilter = backdropFilter;
    state.warp.style.setProperty(
      "-webkit-backdrop-filter",
      backdropFilter
    );
    state.active = true;
  };

  let rafId = 0;
  let targetSyncRafId = 0;
  let geometrySyncRafId = 0;
  let filterSyncRafId = 0;
  let refreshTargetsAfterFilter = false;

  const applyState = (state: (typeof states)[number]) => {
    state.card.style.setProperty("--liquid-light-x", `${state.current.lightX.toFixed(2)}%`);
    state.card.style.setProperty("--liquid-light-y", `${state.current.lightY.toFixed(2)}%`);
    state.card.style.setProperty("--liquid-angle", `${state.current.angle.toFixed(2)}deg`);
    state.card.style.setProperty("--liquid-glow", state.current.glow.toFixed(3));
  };

  const frame = () => {
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

    if (pending) {
      rafId = window.requestAnimationFrame(frame);
    }
  };

  const scheduleFrame = () => {
    if (!rafId) {
      rafId = window.requestAnimationFrame(frame);
    }
  };

  const scheduleFilterSync = (refreshTargets = false) => {
    refreshTargetsAfterFilter = refreshTargetsAfterFilter || refreshTargets;
    if (filterSyncRafId) {
      return;
    }

    filterSyncRafId = window.requestAnimationFrame(() => {
      filterSyncRafId = 0;
      states.forEach(syncFilter);

      if (refreshTargetsAfterFilter) {
        refreshTargetsAfterFilter = false;
        scheduleTargetSync();
      }
    });
  };

  const cleanups: Array<() => void> = [];
  const pagePointer = { x: window.innerWidth * 0.5, y: window.innerHeight * 0.2 };

  states.forEach((state) => {
    syncFilter(state);
    applyState(state);
  });

  const syncTargetsFromPointer = () => {
    if (!desktopLiquidGlass.matches || reduceMotion.matches) {
      return;
    }

    states.forEach((state) => {
      const width = Math.max(state.bounds.width, 1);
      const height = Math.max(state.bounds.height, 1);

      if (width < 20 || height < 20) {
        return;
      }

      const x = clamp(((pagePointer.x - state.bounds.left) / width) * 100, 8, 92);
      const y = clamp(((pagePointer.y - state.bounds.top) / height) * 100, 8, 92);
      const dx = (x - 50) / 50;
      const dy = (y - 50) / 50;

      state.target.lightX = x;
      state.target.lightY = y;
      state.target.angle = 135 + dx * 18 + dy * 10;
      state.target.glow = 0.58 + (Math.abs(dx) + Math.abs(dy)) * 0.035;
    });
    scheduleFrame();
  };

  function scheduleTargetSync() {
    if (!desktopLiquidGlass.matches || reduceMotion.matches || targetSyncRafId) {
      return;
    }

    targetSyncRafId = window.requestAnimationFrame(() => {
      targetSyncRafId = 0;
      syncTargetsFromPointer();
    });
  }

  const scheduleGeometrySync = () => {
    if (!desktopLiquidGlass.matches || geometrySyncRafId) {
      return;
    }

    geometrySyncRafId = window.requestAnimationFrame(() => {
      geometrySyncRafId = 0;
      states.forEach(syncGeometry);
      scheduleTargetSync();
    });
  };

  if (!reduceMotion.matches) {
    const handlePagePointerMove = (event: PointerEvent) => {
      pagePointer.x = event.clientX;
      pagePointer.y = event.clientY;
      scheduleTargetSync();
    };

    const handlePagePointerReset = () => {
      pagePointer.x = window.innerWidth * 0.5;
      pagePointer.y = window.innerHeight * 0.2;
      scheduleTargetSync();
    };

    window.addEventListener("pointermove", handlePagePointerMove, { passive: true });
    window.addEventListener("pointerleave", handlePagePointerReset);
    window.addEventListener("pointercancel", handlePagePointerReset);
    window.addEventListener("blur", handlePagePointerReset);

    cleanups.push(() => {
      window.removeEventListener("pointermove", handlePagePointerMove);
      window.removeEventListener("pointerleave", handlePagePointerReset);
      window.removeEventListener("pointercancel", handlePagePointerReset);
      window.removeEventListener("blur", handlePagePointerReset);
    });

    scheduleTargetSync();
  }

  const resizeObserver = new ResizeObserver(() => {
    scheduleFilterSync(true);
  });
  states.forEach((state) => resizeObserver.observe(state.card));

  const themeObserver = new MutationObserver(() => {
    scheduleFilterSync();
  });
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });

  const handleResize = () => {
    scheduleFilterSync(true);
  };
  window.addEventListener("resize", handleResize, { passive: true });
  window.addEventListener("scroll", scheduleGeometrySync, { passive: true });

  const handleMotionChange = () => {
    if (reduceMotion.matches) {
      states.forEach((state) => {
        state.current = { lightX: 18, lightY: 12, angle: 135, glow: 0.58 };
        state.target = { lightX: 18, lightY: 12, angle: 135, glow: 0.58 };
        applyState(state);
      });
      return;
    }

    scheduleTargetSync();
  };

  const handleBreakpointChange = () => {
    scheduleFilterSync(true);
  };

  if (typeof reduceMotion.addEventListener === "function") {
    reduceMotion.addEventListener("change", handleMotionChange);
    cleanups.push(() => reduceMotion.removeEventListener("change", handleMotionChange));
  } else if (typeof reduceMotion.addListener === "function") {
    reduceMotion.addListener(handleMotionChange);
    cleanups.push(() => reduceMotion.removeListener(handleMotionChange));
  }

  if (typeof desktopLiquidGlass.addEventListener === "function") {
    desktopLiquidGlass.addEventListener("change", handleBreakpointChange);
    cleanups.push(() =>
      desktopLiquidGlass.removeEventListener("change", handleBreakpointChange)
    );
  } else if (typeof desktopLiquidGlass.addListener === "function") {
    desktopLiquidGlass.addListener(handleBreakpointChange);
    cleanups.push(() =>
      desktopLiquidGlass.removeListener(handleBreakpointChange)
    );
  }

  return () => {
    if (rafId) {
      window.cancelAnimationFrame(rafId);
    }
    if (targetSyncRafId) {
      window.cancelAnimationFrame(targetSyncRafId);
    }
    if (geometrySyncRafId) {
      window.cancelAnimationFrame(geometrySyncRafId);
    }
    if (filterSyncRafId) {
      window.cancelAnimationFrame(filterSyncRafId);
    }
    resizeObserver.disconnect();
    themeObserver.disconnect();
    window.removeEventListener("resize", handleResize);
    window.removeEventListener("scroll", scheduleGeometrySync);
    cleanups.forEach((cleanup) => cleanup());
    states.forEach((state) => state.filterRefs?.filter.remove());
  };
}

export function HomeLegacyEffects() {
  useEffect(() => {
    const cleanupLightfield = initHomeLightfield();
    const cleanupLiquidGlass = initHomeLiquidGlass();

    return () => {
      cleanupLiquidGlass();
      cleanupLightfield();
    };
  }, []);

  return null;
}
