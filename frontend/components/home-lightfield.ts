export function initHomeLightfield() {
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
