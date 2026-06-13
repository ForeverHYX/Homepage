/**
 * Anniversary Calendar — vanilla JS port of anniversary-calendar.tsx
 * Renders into #anniversaryCalendarMount (upload page sidebar).
 * Depends on window.__ANNIVERSARY (from anniversary-data.js).
 */
(function () {
  var mount = document.getElementById("anniversaryCalendarMount");
  if (!mount || !window.__ANNIVERSARY) return;

  var MONTH_ABBR = ["Jan.", "Feb.", "Mar.", "Apr.", "May.", "June.", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."];
  var WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];
  var getAnniversariesForMonth = window.__ANNIVERSARY.getAnniversariesForMonth;
  var YEAR_MIN = window.__ANNIVERSARY.ANNIVERSARY_YEAR_MIN;
  var YEAR_MAX = window.__ANNIVERSARY.ANNIVERSARY_YEAR_MAX;

  var now = new Date();
  var viewYear = now.getFullYear();
  var viewMonth = now.getMonth();

  function daysInMonth(year, month0) {
    return new Date(year, month0 + 1, 0).getDate();
  }
  function firstWeekdayOfMonth(year, month0) {
    return new Date(year, month0, 1).getDay();
  }

  // Build the static DOM skeleton once
  function buildSkeleton() {
    mount.innerHTML =
      '<div class="card home-liquid-card anniversary-card">' +
        '<span class="home-liquid-warp" aria-hidden="true"></span>' +
        '<div class="home-liquid-body anniversary-body">' +
          '<h3 class="anniversary-card-title">Anniversaries</h3>' +
          '<div class="anniversary-year-row">' +
            '<button type="button" class="anniversary-nav-btn" id="annPrevYear" aria-label="Previous year">&lsaquo;</button>' +
            '<span class="anniversary-year-text" id="annYearText"></span>' +
            '<button type="button" class="anniversary-nav-btn" id="annNextYear" aria-label="Next year">&rsaquo;</button>' +
          '</div>' +
          '<div class="anniversary-grid-wrap">' +
            '<div class="anniversary-weekdays" id="annWeekdays"></div>' +
            '<div class="anniversary-grid" id="annGrid"></div>' +
          '</div>' +
          '<div class="anniversary-month-row">' +
            '<button type="button" class="anniversary-nav-btn" id="annPrevMonth" aria-label="Previous month">&lsaquo;</button>' +
            '<span class="anniversary-month-text" id="annMonthText"></span>' +
            '<button type="button" class="anniversary-nav-btn" id="annNextMonth" aria-label="Next month">&rsaquo;</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    var wh = document.getElementById("annWeekdays");
    for (var i = 0; i < 7; i++) {
      var s = document.createElement("span");
      s.className = "anniversary-weekday";
      s.textContent = WEEKDAYS[i];
      wh.appendChild(s);
    }
  }

  function render() {
    document.getElementById("annYearText").textContent = viewYear;
    document.getElementById("annMonthText").textContent = MONTH_ABBR[viewMonth];

    var canPrevMonth = !(viewYear === YEAR_MIN && viewMonth === 0);
    var canNextMonth = !(viewYear === YEAR_MAX && viewMonth === 11);
    document.getElementById("annPrevMonth").disabled = !canPrevMonth;
    document.getElementById("annNextMonth").disabled = !canNextMonth;
    document.getElementById("annPrevYear").disabled = viewYear <= YEAR_MIN;
    document.getElementById("annNextYear").disabled = viewYear >= YEAR_MAX;

    var events = getAnniversariesForMonth(viewYear, viewMonth);
    var total = daysInMonth(viewYear, viewMonth);
    var leading = firstWeekdayOfMonth(viewYear, viewMonth);
    var grid = document.getElementById("annGrid");
    grid.innerHTML = "";

    for (var b = 0; b < leading; b++) {
      var blank = document.createElement("span");
      blank.className = "anniversary-day empty";
      grid.appendChild(blank);
    }
    for (var d = 1; d <= total; d++) {
      (function (day) {
        var ev = events.get(day);
        var cell = document.createElement("span");
        cell.className = "anniversary-day" + (ev ? " is-important" : "");
        cell.textContent = day;
        if (ev) {
          cell.tabIndex = 0;
          cell.addEventListener("mouseenter", function (e) { showTooltip(e, ev); });
          cell.addEventListener("mouseleave", hideTooltip);
          cell.addEventListener("focus", function (e) { showTooltip(e, ev); });
          cell.addEventListener("blur", hideTooltip);
        }
        grid.appendChild(cell);
      })(d);
    }
  }

  // Tooltip — portaled to body to escape overflow:hidden / isolation:isolate
  var tooltipEl = null;
  function showTooltip(e, event) {
    var target = e.currentTarget;
    var rect = target.getBoundingClientRect();
    var TOOLTIP_HEIGHT = 72;
    var spaceAbove = rect.top;
    var spaceBelow = window.innerHeight - rect.bottom;
    var preferAbove = spaceAbove >= TOOLTIP_HEIGHT || spaceAbove >= spaceBelow;

    if (!tooltipEl) {
      tooltipEl = document.createElement("div");
      tooltipEl.className = "anniversary-tooltip";
      tooltipEl.setAttribute("role", "tooltip");
      tooltipEl.innerHTML =
        '<div class="anniversary-tooltip-title"></div>' +
        '<div class="anniversary-tooltip-desc"></div>';
      document.body.appendChild(tooltipEl);
    }
    tooltipEl.setAttribute("data-placement", preferAbove ? "above" : "below");
    tooltipEl.style.left = (rect.left + rect.width / 2) + "px";
    tooltipEl.style.top = (preferAbove ? rect.top : rect.bottom) + "px";
    tooltipEl.querySelector(".anniversary-tooltip-title").textContent = event.title;
    tooltipEl.querySelector(".anniversary-tooltip-desc").textContent = event.desc;
  }
  function hideTooltip() {
    if (tooltipEl) tooltipEl.remove();
    tooltipEl = null;
  }

  function goPrevMonth() {
    if (viewYear === YEAR_MIN && viewMonth === 0) return;
    if (viewMonth === 0) { viewYear--; viewMonth = 11; } else { viewMonth--; }
    render();
  }
  function goNextMonth() {
    if (viewYear === YEAR_MAX && viewMonth === 11) return;
    if (viewMonth === 11) { viewYear++; viewMonth = 0; } else { viewMonth++; }
    render();
  }
  function goPrevYear() { if (viewYear > YEAR_MIN) { viewYear--; render(); } }
  function goNextYear() { if (viewYear < YEAR_MAX) { viewYear++; render(); } }

  buildSkeleton();
  render();
  document.getElementById("annPrevMonth").addEventListener("click", goPrevMonth);
  document.getElementById("annNextMonth").addEventListener("click", goNextMonth);
  document.getElementById("annPrevYear").addEventListener("click", goPrevYear);
  document.getElementById("annNextYear").addEventListener("click", goNextYear);
})();
