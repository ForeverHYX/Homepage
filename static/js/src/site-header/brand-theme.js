/* ---------------------------------------------------------------------------
 * Palette-aware homepage mark
 *
 * The checked-in PNGs remain the no-JavaScript fallback and provide the exact
 * alpha masks. At runtime, a small canvas recolors those masks with the active
 * accent gradient for both the navigation mark and the browser favicon.
 * ------------------------------------------------------------------------- */

function brandThemeColor(styles, name, fallback) {
  return styles.getPropertyValue(name).trim() || fallback;
}

function brandThemeRender(image, width, height, colors) {
  var canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  var context = canvas.getContext("2d");
  if (!context) return null;

  context.clearRect(0, 0, width, height);
  context.drawImage(image, 0, 0, width, height);
  context.globalCompositeOperation = "source-in";
  var gradient = context.createLinearGradient(0, 0, width, 0);
  gradient.addColorStop(0, colors[0]);
  gradient.addColorStop(0.48, colors[1]);
  gradient.addColorStop(1, colors[2]);
  context.fillStyle = gradient;
  context.fillRect(0, 0, width, height);
  context.globalCompositeOperation = "source-over";

  try {
    return canvas.toDataURL("image/png");
  } catch (error) {
    return null;
  }
}

export function initBrandTheme() {
  var root = document.documentElement;
  var navIcon = document.querySelector(".nav-brand-icon");
  var faviconLinks = Array.prototype.slice.call(
    document.querySelectorAll('link[rel="icon"][type="image/png"]')
  );
  var assets = [];
  var renderFrame = 0;
  var lastSignature = "";
  var requestFrame = window.requestAnimationFrame || function (callback) {
    return window.setTimeout(callback, 16);
  };

  function addAsset(element, source, width, height, kind) {
    if (!element || !source || !width || !height) return;
    var asset = {
      element: element,
      image: new Image(),
      width: width,
      height: height,
      kind: kind,
      ready: false,
    };
    asset.image.decoding = "async";
    asset.image.onload = function () {
      asset.ready = true;
      scheduleRender();
    };
    asset.image.src = source;
    assets.push(asset);
  }

  if (navIcon) {
    addAsset(
      navIcon,
      navIcon.currentSrc || navIcon.src,
      Number(navIcon.getAttribute("width")) || 104,
      Number(navIcon.getAttribute("height")) || 48,
      "navigation"
    );
  }

  faviconLinks.forEach(function (link) {
    var size = /^(\d+)x(\d+)$/.exec(link.sizes.value);
    if (!size) return;
    addAsset(link, link.href, Number(size[1]), Number(size[2]), "favicon");
  });

  function render() {
    renderFrame = 0;
    if (!assets.length || assets.some(function (asset) { return !asset.ready; })) return;
    var styles = window.getComputedStyle(root);
    var colors = [
      brandThemeColor(styles, "--accent-500", "#3b82f6"),
      brandThemeColor(styles, "--accent-cyan-400", "#22d3ee"),
      brandThemeColor(styles, "--accent-vivid-400", "#c084fc"),
    ];
    var signature = root.getAttribute("data-theme") + "|" + colors.join("|");
    if (signature === lastSignature) return;
    lastSignature = signature;

    assets.forEach(function (asset) {
      var themedSource = brandThemeRender(asset.image, asset.width, asset.height, colors);
      if (!themedSource) return;
      if (asset.kind === "navigation") asset.element.src = themedSource;
      else asset.element.href = themedSource;
      asset.element.dataset.accentThemed = "true";
    });
  }

  function scheduleRender() {
    if (renderFrame) return;
    renderFrame = requestFrame(render);
  }

  document.addEventListener("homepage:accentchange", scheduleRender);
  scheduleRender();
}
