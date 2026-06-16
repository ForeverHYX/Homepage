(function () {
  "use strict";

  var mount = document.getElementById("dailyArchiveCalendar");
  if (!mount) return;

  var feedbackUiStateKey = "homepage_daily_feedback_ui_state";
  var MONTH_ABBR = ["Jan.", "Feb.", "Mar.", "Apr.", "May.", "June.", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."];
  var WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];
  var selectedDate = mount.getAttribute("data-selected-date") || mount.getAttribute("data-run-date") || todayString();
  var archiveDates = readArchiveDates(mount.getAttribute("data-archive-dates") || "[]");
  var likedDates = likedDatesFromLocalState();
  var availableDates = uniqueDates(archiveDates.concat(likedDates));
  var initial = parseDate(selectedDate) || parseDate(availableDates[0]) || new Date();
  var viewYear = initial.getFullYear();
  var viewMonth = initial.getMonth();

  function buildSkeleton() {
    mount.innerHTML =
      '<span class="home-liquid-warp" aria-hidden="true"></span>' +
      '<div class="home-liquid-body anniversary-body daily-archive-body">' +
        '<h3 class="anniversary-card-title sidebar-card-title">Archive</h3>' +
        '<div class="anniversary-year-row">' +
          '<button type="button" class="anniversary-nav-btn" id="dailyArchivePrevYear" aria-label="Previous year">&lsaquo;</button>' +
          '<span class="anniversary-year-text" id="dailyArchiveYearText"></span>' +
          '<button type="button" class="anniversary-nav-btn" id="dailyArchiveNextYear" aria-label="Next year">&rsaquo;</button>' +
        '</div>' +
        '<div class="anniversary-grid-wrap">' +
          '<div class="anniversary-weekdays" id="dailyArchiveWeekdays"></div>' +
          '<div class="anniversary-grid" id="dailyArchiveGrid"></div>' +
        '</div>' +
        '<div class="anniversary-month-row">' +
          '<button type="button" class="anniversary-nav-btn" id="dailyArchivePrevMonth" aria-label="Previous month">&lsaquo;</button>' +
          '<span class="anniversary-month-text" id="dailyArchiveMonthText"></span>' +
          '<button type="button" class="anniversary-nav-btn" id="dailyArchiveNextMonth" aria-label="Next month">&rsaquo;</button>' +
        '</div>' +
      '</div>';

    var weekdays = document.getElementById("dailyArchiveWeekdays");
    WEEKDAYS.forEach(function (weekday) {
      var cell = document.createElement("span");
      cell.className = "anniversary-weekday";
      cell.textContent = weekday;
      weekdays.appendChild(cell);
    });
  }

  function render() {
    document.getElementById("dailyArchiveYearText").textContent = viewYear;
    document.getElementById("dailyArchiveMonthText").textContent = MONTH_ABBR[viewMonth];

    var grid = document.getElementById("dailyArchiveGrid");
    grid.innerHTML = "";
    for (var blank = 0; blank < firstWeekdayOfMonth(viewYear, viewMonth); blank++) {
      var empty = document.createElement("span");
      empty.className = "anniversary-day daily-archive-day empty";
      grid.appendChild(empty);
    }
    for (var day = 1; day <= daysInMonth(viewYear, viewMonth); day++) {
      grid.appendChild(dayCell(day));
    }
  }

  function dayCell(day) {
    var date = dateString(viewYear, viewMonth, day);
    var hasArchive = availableDates.indexOf(date) !== -1;
    var isLiked = likedDates.indexOf(date) !== -1;
    var isSelected = selectedDate === date;
    var cell = document.createElement(hasArchive ? "a" : "span");
    cell.className = "anniversary-day daily-archive-day" +
      (hasArchive ? " is-important" : "") +
      (isLiked ? " is-liked" : "") +
      (isSelected ? " is-selected" : "");
    cell.textContent = String(day);
    if (hasArchive) {
      cell.href = "/daily?date=" + encodeURIComponent(date);
      cell.title = isLiked ? "Liked archive for " + date : "Daily archive for " + date;
      cell.setAttribute("aria-label", cell.title);
    }
    return cell;
  }

  function goPrevMonth() {
    if (viewMonth === 0) {
      viewYear -= 1;
      viewMonth = 11;
    } else {
      viewMonth -= 1;
    }
    render();
  }

  function goNextMonth() {
    if (viewMonth === 11) {
      viewYear += 1;
      viewMonth = 0;
    } else {
      viewMonth += 1;
    }
    render();
  }

  function goPrevYear() {
    viewYear -= 1;
    render();
  }

  function goNextYear() {
    viewYear += 1;
    render();
  }

  function refreshFeedbackState() {
    likedDates = likedDatesFromLocalState();
    availableDates = uniqueDates(archiveDates.concat(likedDates));
    render();
  }

  function likedDatesFromLocalState() {
    try {
      var state = JSON.parse(localStorage.getItem(feedbackUiStateKey) || "{}");
      var likes = state && typeof state.likes === "object" && !Array.isArray(state.likes) ? state.likes : {};
      return Object.keys(likes).filter(function (date) {
        return /^\d{4}-\d{2}-\d{2}$/.test(date) && Array.isArray(likes[date]) && likes[date].length > 0;
      });
    } catch (error) {
      return [];
    }
  }

  function readArchiveDates(raw) {
    try {
      var parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.filter(isDateString) : [];
    } catch (error) {
      return [];
    }
  }

  function uniqueDates(values) {
    var seen = {};
    return values.filter(function (value) {
      if (!isDateString(value) || seen[value]) return false;
      seen[value] = true;
      return true;
    }).sort().reverse();
  }

  function isDateString(value) {
    return /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""));
  }

  function parseDate(value) {
    if (!isDateString(value)) return null;
    var parts = value.split("-").map(Number);
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  function todayString() {
    var now = new Date();
    return dateString(now.getFullYear(), now.getMonth(), now.getDate());
  }

  function dateString(year, month0, day) {
    return String(year).padStart(4, "0") + "-" + String(month0 + 1).padStart(2, "0") + "-" + String(day).padStart(2, "0");
  }

  function daysInMonth(year, month0) {
    return new Date(year, month0 + 1, 0).getDate();
  }

  function firstWeekdayOfMonth(year, month0) {
    return new Date(year, month0, 1).getDay();
  }

  buildSkeleton();
  render();
  document.getElementById("dailyArchivePrevMonth").addEventListener("click", goPrevMonth);
  document.getElementById("dailyArchiveNextMonth").addEventListener("click", goNextMonth);
  document.getElementById("dailyArchivePrevYear").addEventListener("click", goPrevYear);
  document.getElementById("dailyArchiveNextYear").addEventListener("click", goNextYear);
  window.addEventListener("daily-feedback-state-change", refreshFeedbackState);
})();
