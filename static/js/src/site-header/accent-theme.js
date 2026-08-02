/* ---------------------------------------------------------------------------
 * Site-wide accent palette
 *
 * Stores a light and dark palette independently. With synchronization on
 * (the default), the light selection is the source of truth and an accessible
 * related dark accent is derived automatically. Resolved CSS variables are
 * persisted with the descriptors so base.html can apply them before paint.
 * ------------------------------------------------------------------------- */
var ACCENT_STORAGE_KEY = "homepage_accent_theme_v1";
var ACCENT_SHADES = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"];
var ACCENT_FAMILIES = ["accent", "accent-secondary", "accent-tertiary"];
var ACCENT_PRESETS = [
  { id: "default", label: "Default", light: "#3b82f6", dark: "#60a5fa" },
  { id: "ocean", label: "Ocean", light: "#0284c7", dark: "#38bdf8" },
  { id: "violet", label: "Violet", light: "#7c3aed", dark: "#a78bfa" },
  { id: "sunset", label: "Sunset", light: "#ea580c", dark: "#fb923c" },
  { id: "forest", label: "Forest", light: "#059669", dark: "#34d399" },
  { id: "rose", label: "Rose", light: "#e11d48", dark: "#fb7185" },
];
var ACCENT_VARIABLE_NAMES = (function () {
  var names = [
    "--theme-bg", "--theme-text", "--theme-heading", "--theme-muted",
    "--accent-cyan-300", "--accent-cyan-400", "--accent-cyan-500",
    "--accent-cyan-300-rgb", "--accent-cyan-400-rgb", "--accent-cyan-500-rgb",
    "--accent-vivid-400", "--accent-vivid-500", "--accent-vivid-400-rgb",
    "--accent-vivid-500-rgb", "--accent-vivid-rgb",
  ];
  ACCENT_FAMILIES.forEach(function (family) {
    ACCENT_SHADES.forEach(function (shade) {
      names.push("--" + family + "-" + shade);
      names.push("--" + family + "-" + shade + "-rgb");
    });
  });
  for (var spot = 1; spot <= 6; spot++) {
    ["a", "b", "c"].forEach(function (channel) {
      names.push("--lightfield-" + spot + "-" + channel + "-rgb");
    });
  }
  return names;
})();

function accentClamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

function accentNormalizeHex(value) {
  var candidate = String(value || "").trim().replace(/^#/, "");
  if (/^[0-9a-f]{3}$/i.test(candidate)) {
    candidate = candidate.replace(/(.)/g, "$1$1");
  }
  if (!/^[0-9a-f]{6}$/i.test(candidate)) return null;
  return "#" + candidate.toLowerCase();
}

function accentHexToRgb(value) {
  var hex = accentNormalizeHex(value) || "#3b82f6";
  return {
    r: parseInt(hex.slice(1, 3), 16),
    g: parseInt(hex.slice(3, 5), 16),
    b: parseInt(hex.slice(5, 7), 16),
  };
}

function accentRgbToHex(color) {
  function channel(value) {
    return Math.round(accentClamp(value, 0, 255)).toString(16).padStart(2, "0");
  }
  return "#" + channel(color.r) + channel(color.g) + channel(color.b);
}

function accentMix(color, target, amount) {
  return {
    r: color.r + (target.r - color.r) * amount,
    g: color.g + (target.g - color.g) * amount,
    b: color.b + (target.b - color.b) * amount,
  };
}

function accentRgbToHsv(color) {
  var r = color.r / 255;
  var g = color.g / 255;
  var b = color.b / 255;
  var maximum = Math.max(r, g, b);
  var minimum = Math.min(r, g, b);
  var delta = maximum - minimum;
  var hue = 0;
  if (delta) {
    if (maximum === r) hue = ((g - b) / delta) % 6;
    else if (maximum === g) hue = (b - r) / delta + 2;
    else hue = (r - g) / delta + 4;
    hue *= 60;
    if (hue < 0) hue += 360;
  }
  return {
    h: hue,
    s: maximum ? delta / maximum : 0,
    v: maximum,
  };
}

function accentHsvToRgb(hue, saturation, value) {
  var h = ((hue % 360) + 360) % 360;
  var s = accentClamp(saturation, 0, 1);
  var v = accentClamp(value, 0, 1);
  var chroma = v * s;
  var sector = h / 60;
  var x = chroma * (1 - Math.abs((sector % 2) - 1));
  var rgb = [0, 0, 0];
  if (sector < 1) rgb = [chroma, x, 0];
  else if (sector < 2) rgb = [x, chroma, 0];
  else if (sector < 3) rgb = [0, chroma, x];
  else if (sector < 4) rgb = [0, x, chroma];
  else if (sector < 5) rgb = [x, 0, chroma];
  else rgb = [chroma, 0, x];
  var match = v - chroma;
  return { r: (rgb[0] + match) * 255, g: (rgb[1] + match) * 255, b: (rgb[2] + match) * 255 };
}

function accentRgbToHsl(color) {
  var r = color.r / 255;
  var g = color.g / 255;
  var b = color.b / 255;
  var maximum = Math.max(r, g, b);
  var minimum = Math.min(r, g, b);
  var lightness = (maximum + minimum) / 2;
  var delta = maximum - minimum;
  var hue = 0;
  var saturation = 0;
  if (delta) {
    saturation = delta / (1 - Math.abs(2 * lightness - 1));
    if (maximum === r) hue = 60 * (((g - b) / delta) % 6);
    else if (maximum === g) hue = 60 * ((b - r) / delta + 2);
    else hue = 60 * ((r - g) / delta + 4);
    if (hue < 0) hue += 360;
  }
  return { h: hue, s: saturation, l: lightness };
}

function accentHslToRgb(hue, saturation, lightness) {
  var h = ((hue % 360) + 360) % 360;
  var s = accentClamp(saturation, 0, 1);
  var l = accentClamp(lightness, 0, 1);
  var chroma = (1 - Math.abs(2 * l - 1)) * s;
  var sector = h / 60;
  var x = chroma * (1 - Math.abs((sector % 2) - 1));
  var rgb = [0, 0, 0];
  if (sector < 1) rgb = [chroma, x, 0];
  else if (sector < 2) rgb = [x, chroma, 0];
  else if (sector < 3) rgb = [0, chroma, x];
  else if (sector < 4) rgb = [0, x, chroma];
  else if (sector < 5) rgb = [x, 0, chroma];
  else rgb = [chroma, 0, x];
  var match = l - chroma / 2;
  return { r: (rgb[0] + match) * 255, g: (rgb[1] + match) * 255, b: (rgb[2] + match) * 255 };
}

function accentPresetById(id) {
  for (var index = 0; index < ACCENT_PRESETS.length; index++) {
    if (ACCENT_PRESETS[index].id === id) return ACCENT_PRESETS[index];
  }
  return null;
}

function accentBuildScale(baseHex, mode) {
  var base = accentHexToRgb(baseHex);
  var white = { r: 255, g: 255, b: 255 };
  var black = { r: 0, g: 0, b: 0 };
  var recipes = mode === "dark"
    ? {
        "50": [white, 0.93], "100": [white, 0.84], "200": [white, 0.67],
        "300": [white, 0.3], "400": [base, 0], "500": [black, 0.1],
        "600": [black, 0.2], "700": [black, 0.3], "800": [black, 0.4],
        "900": [black, 0.52], "950": [black, 0.66],
      }
    : {
        "50": [white, 0.93], "100": [white, 0.84], "200": [white, 0.68],
        "300": [white, 0.45], "400": [white, 0.2], "500": [base, 0],
        "600": [black, 0.11], "700": [black, 0.24], "800": [black, 0.36],
        "900": [black, 0.49], "950": [black, 0.64],
      };
  var scale = {};
  ACCENT_SHADES.forEach(function (shade) {
    var recipe = recipes[shade];
    scale[shade] = accentRgbToHex(accentMix(base, recipe[0], recipe[1]));
  });
  return scale;
}

function accentBuildVariables(baseHex, mode) {
  var base = accentHexToRgb(baseHex);
  var hsv = accentRgbToHsv(base);
  var secondary = accentRgbToHex(accentHsvToRgb(hsv.h - 18, hsv.s * 0.94, hsv.v));
  var tertiary = accentRgbToHex(accentHsvToRgb(hsv.h + 22, hsv.s * 0.9, hsv.v));
  var cyan = accentRgbToHex(accentHsvToRgb(hsv.h - 30, hsv.s * 0.96, hsv.v));
  var vivid = accentRgbToHex(accentHsvToRgb(hsv.h + 54, hsv.s * 0.88, hsv.v));
  var scales = {
    accent: accentBuildScale(baseHex, mode),
    "accent-secondary": accentBuildScale(secondary, mode),
    "accent-tertiary": accentBuildScale(tertiary, mode),
  };
  var cyanScale = accentBuildScale(cyan, mode);
  var vividScale = accentBuildScale(vivid, mode);
  var variables = {};
  ACCENT_FAMILIES.forEach(function (family) {
    ACCENT_SHADES.forEach(function (shade) {
      var value = scales[family][shade];
      var rgb = accentHexToRgb(value);
      variables["--" + family + "-" + shade] = value;
      variables["--" + family + "-" + shade + "-rgb"] = Math.round(rgb.r) + ", " + Math.round(rgb.g) + ", " + Math.round(rgb.b);
    });
  });
  ["300", "400", "500"].forEach(function (shade) {
    var cyanColor = accentHexToRgb(cyanScale[shade]);
    variables["--accent-cyan-" + shade] = cyanScale[shade];
    variables["--accent-cyan-" + shade + "-rgb"] = Math.round(cyanColor.r) + ", " + Math.round(cyanColor.g) + ", " + Math.round(cyanColor.b);
  });
  ["400", "500"].forEach(function (shade) {
    var vividColor = accentHexToRgb(vividScale[shade]);
    variables["--accent-vivid-" + shade] = vividScale[shade];
    variables["--accent-vivid-" + shade + "-rgb"] = Math.round(vividColor.r) + ", " + Math.round(vividColor.g) + ", " + Math.round(vividColor.b);
  });
  variables["--accent-vivid-rgb"] = variables["--accent-vivid-500-rgb"];

  function setLightfieldColor(spot, channel, color) {
    variables["--lightfield-" + spot + "-" + channel + "-rgb"] =
      Math.round(color.r) + ", " + Math.round(color.g) + ", " + Math.round(color.b);
  }
  function companion(offset, saturationMultiplier, value) {
    return accentHsvToRgb(
      hsv.h + offset,
      accentClamp(hsv.s * saturationMultiplier, 0.42, 0.96),
      accentClamp(value, 0, 1)
    );
  }
  var modeValue = mode === "dark" ? Math.max(hsv.v, 0.82) : hsv.v;
  setLightfieldColor(1, "a", accentHexToRgb(mode === "dark" ? scales["accent-tertiary"]["400"] : scales["accent-tertiary"]["500"]));
  setLightfieldColor(1, "b", accentHexToRgb(mode === "dark" ? scales.accent["400"] : scales.accent["500"]));
  setLightfieldColor(1, "c", accentHexToRgb(scales.accent["500"]));
  setLightfieldColor(2, "a", accentHexToRgb(mode === "dark" ? cyanScale["400"] : scales["accent-secondary"]["400"]));
  setLightfieldColor(2, "b", accentHexToRgb(mode === "dark" ? scales.accent["500"] : cyanScale["300"]));
  setLightfieldColor(2, "c", accentHexToRgb(scales["accent-secondary"]["400"]));
  setLightfieldColor(3, "a", accentHexToRgb(mode === "dark" ? vividScale["400"] : vividScale["500"]));
  setLightfieldColor(3, "b", accentHexToRgb(mode === "dark" ? scales["accent-tertiary"]["400"] : vividScale["400"]));
  setLightfieldColor(3, "c", accentHexToRgb(mode === "dark" ? scales["accent-tertiary"]["400"] : vividScale["400"]));
  setLightfieldColor(4, "a", companion(-120, 0.9, modeValue));
  setLightfieldColor(4, "b", companion(-78, 0.82, modeValue));
  setLightfieldColor(4, "c", accentHexToRgb(mode === "dark" ? scales["accent-secondary"]["400"] : scales["accent-secondary"]["300"]));
  setLightfieldColor(5, "a", companion(100, 0.78, modeValue));
  setLightfieldColor(5, "b", companion(180, 0.86, modeValue));
  setLightfieldColor(5, "c", accentHexToRgb(mode === "dark" ? scales["accent-tertiary"]["400"] : accentRgbToHex(companion(180, 0.86, modeValue))));
  setLightfieldColor(6, "a", { r: 255, g: 255, b: 255 });
  setLightfieldColor(6, "b", accentHexToRgb(mode === "dark" ? scales.accent["400"] : scales["accent-secondary"]["100"]));
  setLightfieldColor(6, "c", accentHexToRgb(mode === "dark" ? scales.accent["400"] : scales["accent-secondary"]["100"]));

  if (mode === "dark") {
    variables["--theme-bg"] = accentRgbToHex(accentHslToRgb(hsv.h, 0.54, 0.08));
    variables["--theme-text"] = accentRgbToHex(accentHslToRgb(hsv.h, 0.2, 0.82));
    variables["--theme-heading"] = accentRgbToHex(accentHslToRgb(hsv.h, 0.28, 0.94));
    variables["--theme-muted"] = accentRgbToHex(accentHslToRgb(hsv.h, 0.18, 0.73));
  } else {
    variables["--theme-bg"] = accentRgbToHex(accentHslToRgb(hsv.h, 0.58, 0.95));
    variables["--theme-text"] = accentRgbToHex(accentHslToRgb(hsv.h, 0.22, 0.28));
    variables["--theme-heading"] = accentRgbToHex(accentHslToRgb(hsv.h, 0.38, 0.11));
    variables["--theme-muted"] = accentRgbToHex(accentHslToRgb(hsv.h, 0.16, 0.43));
  }
  return variables;
}

function accentBuildDescriptor(id, mode, customBase) {
  var preset = accentPresetById(id);
  var base = preset ? preset[mode] : accentNormalizeHex(customBase);
  if (!base) {
    preset = ACCENT_PRESETS[0];
    id = "default";
    base = preset[mode];
  }
  return {
    id: preset ? preset.id : "custom",
    base: base,
    vars: preset && preset.id === "default" ? {} : accentBuildVariables(base, mode),
  };
}

function accentDeriveDarkBase(lightBase) {
  var hsl = accentRgbToHsl(accentHexToRgb(lightBase));
  var saturation = accentClamp(hsl.s * 0.92, 0.42, 0.9);
  var lightness = accentClamp(Math.max(hsl.l, 0.64), 0.58, 0.72);
  return accentRgbToHex(accentHslToRgb(hsl.h, saturation, lightness));
}

function accentDeriveDarkDescriptor(light) {
  var preset = accentPresetById(light.id);
  if (preset) return accentBuildDescriptor(preset.id, "dark");
  return accentBuildDescriptor("custom", "dark", accentDeriveDarkBase(light.base));
}

function accentNormalizeDescriptor(value, mode) {
  if (value && value.id === "custom" && accentNormalizeHex(value.base)) {
    return accentBuildDescriptor("custom", mode, value.base);
  }
  var preset = accentPresetById(value && value.id);
  return accentBuildDescriptor(preset ? preset.id : "default", mode);
}

function accentNormalizeState(raw) {
  var state = {
    version: 1,
    sync: !(raw && raw.sync === false),
    light: accentNormalizeDescriptor(raw && raw.light, "light"),
    dark: accentNormalizeDescriptor(raw && raw.dark, "dark"),
  };
  if (state.sync) state.dark = accentDeriveDarkDescriptor(state.light);
  return state;
}

function accentCurrentTheme() {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

function accentApplyState(state) {
  var root = document.documentElement;
  var theme = accentCurrentTheme();
  var palette = state[theme];
  ACCENT_VARIABLE_NAMES.forEach(function (name) {
    root.style.removeProperty(name);
  });
  Object.keys(palette.vars).forEach(function (name) {
    root.style.setProperty(name, palette.vars[name]);
  });
  root.dataset.accentTheme = palette.id;
  root.dataset.accentSync = state.sync ? "true" : "false";
  document.dispatchEvent(
    new CustomEvent("homepage:accentchange", {
      detail: { theme: theme, palette: palette, sync: state.sync },
    })
  );
}

export function initAccentTheme() {
  var bootstrap = window.__homepageAccentTheme || {};
  var state = accentNormalizeState(bootstrap.state);
  var root = document.documentElement;
  var trigger = document.getElementById("accentThemeToggle");
  var popover = document.getElementById("accentPalettePopover");
  var syncToggle = document.getElementById("accentSyncToggle");
  var modeSelector = document.getElementById("accentModeSelector");
  var modeButtons = Array.prototype.slice.call(document.querySelectorAll("[data-accent-mode]"));
  var presetButtons = Array.prototype.slice.call(document.querySelectorAll("[data-accent-preset]"));
  var editingLabel = document.getElementById("accentEditingLabel");
  var colorField = document.getElementById("accentColorField");
  var colorMarker = document.getElementById("accentColorMarker");
  var hueSlider = document.getElementById("accentHueSlider");
  var hexInput = document.getElementById("accentHexInput");
  var colorPreview = document.getElementById("accentColorPreview");
  var resetButton = document.getElementById("accentResetButton");
  var editorMode = "light";
  var originalTheme = null;
  var persistTimer = 0;

  function exposeState() {
    window.__homepageAccentTheme = {
      storageKey: ACCENT_STORAGE_KEY,
      state: state,
    };
    window.HomepageAccentTheme = {
      getState: function () { return JSON.parse(JSON.stringify(state)); },
      apply: function () { accentApplyState(state); },
      presets: ACCENT_PRESETS.map(function (preset) { return preset.id; }),
    };
  }

  function persist() {
    window.clearTimeout(persistTimer);
    persistTimer = 0;
    try {
      localStorage.setItem(ACCENT_STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
      /* Storage can be unavailable in private browsing; live theming still works. */
    }
    exposeState();
  }

  function schedulePersist() {
    window.clearTimeout(persistTimer);
    persistTimer = window.setTimeout(persist, 120);
  }

  function displayedDescriptor() {
    return state.sync ? state.light : state[editorMode];
  }

  function renderControls() {
    if (!syncToggle) return;
    syncToggle.setAttribute("aria-checked", state.sync ? "true" : "false");
    syncToggle.classList.toggle("is-on", state.sync);
    modeSelector.hidden = state.sync;
    modeButtons.forEach(function (button) {
      var selected = button.dataset.accentMode === editorMode;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-pressed", selected ? "true" : "false");
    });
    if (editingLabel) {
      editingLabel.textContent = state.sync ? "Synced" : editorMode === "dark" ? "Dark" : "Light";
    }

    var descriptor = displayedDescriptor();
    presetButtons.forEach(function (button) {
      var selected = descriptor.id === button.dataset.accentPreset;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-pressed", selected ? "true" : "false");
    });

    var hsv = accentRgbToHsv(accentHexToRgb(descriptor.base));
    var hue = Math.round(hsv.h) % 360;
    if (colorField) {
      colorField.style.setProperty("--picker-hue", hue);
      colorField.setAttribute("aria-valuenow", String(Math.round(hsv.v * 100)));
      colorField.setAttribute(
        "aria-valuetext",
        Math.round(hsv.s * 100) + "% saturation, " + Math.round(hsv.v * 100) + "% brightness"
      );
    }
    if (colorMarker) {
      colorMarker.style.left = hsv.s * 100 + "%";
      colorMarker.style.top = (1 - hsv.v) * 100 + "%";
      colorMarker.style.background = descriptor.base;
    }
    if (hueSlider) hueSlider.value = String(hue);
    if (hexInput && document.activeElement !== hexInput) {
      hexInput.value = descriptor.base.toUpperCase();
    }
    if (colorPreview) colorPreview.style.background = descriptor.base;
  }

  function applyAndRender(shouldPersist) {
    accentApplyState(state);
    renderControls();
    exposeState();
    if (shouldPersist === "defer") schedulePersist();
    else if (shouldPersist) persist();
  }

  function choosePreset(id) {
    if (state.sync) {
      state.light = accentBuildDescriptor(id, "light");
      state.dark = accentDeriveDarkDescriptor(state.light);
    } else {
      state[editorMode] = accentBuildDescriptor(id, editorMode);
    }
    applyAndRender(true);
  }

  function chooseCustom(base, persistence) {
    var normalized = accentNormalizeHex(base);
    if (!normalized) return;
    if (state.sync) {
      state.light = accentBuildDescriptor("custom", "light", normalized);
      state.dark = accentDeriveDarkDescriptor(state.light);
    } else {
      state[editorMode] = accentBuildDescriptor("custom", editorMode, normalized);
    }
    applyAndRender(persistence);
  }

  function chooseHsv(hue, saturation, value, persistence) {
    chooseCustom(accentRgbToHex(accentHsvToRgb(hue, saturation, value)), persistence);
  }

  function updateFromField(event, persistence) {
    if (!colorField) return;
    var rect = colorField.getBoundingClientRect();
    var saturation = accentClamp((event.clientX - rect.left) / Math.max(rect.width, 1), 0, 1);
    var value = 1 - accentClamp((event.clientY - rect.top) / Math.max(rect.height, 1), 0, 1);
    var hue = Number(hueSlider.value || 0);
    chooseHsv(hue, saturation, value, persistence);
  }

  accentApplyState(state);
  exposeState();
  if (!trigger || !popover || !window.HomepageAnchoredPopover) return;

  trigger.addEventListener("click", function () {
    if (window.HomepageAnchoredPopover.isOpen(popover)) {
      window.HomepageAnchoredPopover.close(popover, true);
      return;
    }
    window.HomepageAnchoredPopover.open(popover, trigger, { placement: "bottom-end" });
  });

  popover.addEventListener("homepage:popoveropen", function () {
    originalTheme = accentCurrentTheme();
    editorMode = state.sync ? "light" : originalTheme;
    renderControls();
  });

  popover.addEventListener("homepage:popoverclose", function () {
    if (!originalTheme) return;
    root.setAttribute("data-theme", originalTheme);
    root.style.colorScheme = originalTheme;
    originalTheme = null;
    accentApplyState(state);
    persist();
  });

  syncToggle.addEventListener("click", function () {
    state.sync = !state.sync;
    if (state.sync) {
      state.dark = accentDeriveDarkDescriptor(state.light);
    } else {
      editorMode = accentCurrentTheme();
    }
    applyAndRender(true);
    if (window.HomepageAnchoredPopover.reposition) {
      window.HomepageAnchoredPopover.reposition();
    }
  });

  modeButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      if (state.sync) return;
      editorMode = button.dataset.accentMode === "dark" ? "dark" : "light";
      root.setAttribute("data-theme", editorMode);
      root.style.colorScheme = editorMode;
      accentApplyState(state);
      renderControls();
    });
  });

  presetButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      choosePreset(button.dataset.accentPreset);
    });
  });

  if (colorField) {
    colorField.addEventListener("pointerdown", function (event) {
      event.preventDefault();
      colorField.setPointerCapture(event.pointerId);
      updateFromField(event, "defer");
    });
    colorField.addEventListener("pointermove", function (event) {
      if (!colorField.hasPointerCapture(event.pointerId)) return;
      updateFromField(event, "defer");
    });
    colorField.addEventListener("pointerup", function (event) {
      if (colorField.hasPointerCapture(event.pointerId)) {
        updateFromField(event, true);
        colorField.releasePointerCapture(event.pointerId);
      }
    });
    colorField.addEventListener("keydown", function (event) {
      var descriptor = displayedDescriptor();
      var hsv = accentRgbToHsv(accentHexToRgb(descriptor.base));
      var increment = event.shiftKey ? 0.1 : 0.02;
      if (event.key === "ArrowLeft") hsv.s -= increment;
      else if (event.key === "ArrowRight") hsv.s += increment;
      else if (event.key === "ArrowDown") hsv.v -= increment;
      else if (event.key === "ArrowUp") hsv.v += increment;
      else return;
      event.preventDefault();
      chooseHsv(hsv.h, accentClamp(hsv.s, 0, 1), accentClamp(hsv.v, 0, 1), true);
    });
  }

  if (hueSlider) {
    hueSlider.addEventListener("input", function () {
      var hsv = accentRgbToHsv(accentHexToRgb(displayedDescriptor().base));
      chooseHsv(Number(hueSlider.value), hsv.s, hsv.v, "defer");
    });
    hueSlider.addEventListener("change", persist);
  }

  if (hexInput) {
    hexInput.addEventListener("input", function () {
      var normalized = accentNormalizeHex(hexInput.value);
      hexInput.setAttribute("aria-invalid", normalized ? "false" : "true");
      if (normalized) chooseCustom(normalized, "defer");
    });
    hexInput.addEventListener("change", function () {
      var normalized = accentNormalizeHex(hexInput.value);
      if (normalized) chooseCustom(normalized, true);
      else {
        hexInput.value = displayedDescriptor().base.toUpperCase();
        hexInput.setAttribute("aria-invalid", "false");
      }
    });
  }

  if (resetButton) {
    resetButton.addEventListener("click", function () {
      choosePreset("default");
    });
  }

  var themeObserver = new MutationObserver(function () {
    accentApplyState(state);
    if (!window.HomepageAnchoredPopover.isOpen(popover)) renderControls();
  });
  themeObserver.observe(root, { attributes: true, attributeFilter: ["data-theme"] });
  renderControls();
}
