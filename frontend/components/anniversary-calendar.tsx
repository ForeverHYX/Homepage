"use client";

import { useMemo, useState, type SyntheticEvent } from "react";
import {
  ANNIVERSARY_YEAR_MAX,
  ANNIVERSARY_YEAR_MIN,
  getAnniversariesForMonth,
  type AnniversaryEvent,
} from "@/lib/anniversaries";

const MONTH_ABBR = [
  "Jan.", "Feb.", "Mar.", "Apr.", "May.", "June.",
  "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.",
];

// Sunday-start week. The user is happy to switch to Monday-start if desired.
const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];

function daysInMonth(year: number, month0: number): number {
  return new Date(year, month0 + 1, 0).getDate();
}

function firstWeekdayOfMonth(year: number, month0: number): number {
  return new Date(year, month0, 1).getDay(); // 0=Sun … 6=Sat
}

type TooltipState = {
  title: string;
  desc: string;
  x: number;
  y: number;
  placement: "above" | "below";
} | null;

export function AnniversaryCalendar() {
  // Initial view: the current month.
  const now = new Date();
  const [viewYear, setViewYear] = useState<number>(now.getFullYear());
  const [viewMonth, setViewMonth] = useState<number>(now.getMonth());
  const [tooltip, setTooltip] = useState<TooltipState>(null);

  const events = useMemo(
    () => getAnniversariesForMonth(viewYear, viewMonth),
    [viewYear, viewMonth],
  );

  const totalDays = daysInMonth(viewYear, viewMonth);
  const leadingBlanks = firstWeekdayOfMonth(viewYear, viewMonth);

  // Build a flat list of cells (blanks + days) for the 7-col grid.
  const cells: ({ day: number; event?: AnniversaryEvent } | null)[] = [];
  for (let i = 0; i < leadingBlanks; i++) cells.push(null);
  for (let d = 1; d <= totalDays; d++) {
    cells.push({ day: d, event: events.get(d) });
  }

  const canPrevMonth = !(viewYear === ANNIVERSARY_YEAR_MIN && viewMonth === 0);
  const canNextMonth = !(viewYear === ANNIVERSARY_YEAR_MAX && viewMonth === 11);

  const goPrevMonth = () => {
    if (!canPrevMonth) return;
    if (viewMonth === 0) {
      setViewYear(viewYear - 1);
      setViewMonth(11);
    } else {
      setViewMonth(viewMonth - 1);
    }
  };
  const goNextMonth = () => {
    if (!canNextMonth) return;
    if (viewMonth === 11) {
      setViewYear(viewYear + 1);
      setViewMonth(0);
    } else {
      setViewMonth(viewMonth + 1);
    }
  };

  const canPrevYear = viewYear > ANNIVERSARY_YEAR_MIN;
  const canNextYear = viewYear < ANNIVERSARY_YEAR_MAX;
  const goPrevYear = () => {
    if (canPrevYear) setViewYear(viewYear - 1);
  };
  const goNextYear = () => {
    if (canNextYear) setViewYear(viewYear + 1);
  };

  const showTooltip = (
    e: SyntheticEvent<HTMLSpanElement>,
    event: AnniversaryEvent,
  ) => {

    const rect = e.currentTarget.getBoundingClientRect();
    const TOOLTIP_ESTIMATED_HEIGHT = 72;
    const spaceAbove = rect.top;
    const spaceBelow = window.innerHeight - rect.bottom;
    const preferAbove =
      spaceAbove >= TOOLTIP_ESTIMATED_HEIGHT || spaceAbove >= spaceBelow;
    setTooltip({
      title: event.title,
      desc: event.desc,
      x: rect.left + rect.width / 2,
      y: preferAbove ? rect.top : rect.bottom,
      placement: preferAbove ? "above" : "below",
    });
  };

  const hideTooltip = () => setTooltip(null);

  return (
    <div className="card home-liquid-card anniversary-card">
      <span className="home-liquid-warp" aria-hidden="true" />
      <div className="home-liquid-body anniversary-body">
        <h3 className="anniversary-card-title">纪念日</h3>

        {/* Year navigation */}
        <div className="anniversary-year-row">
          <button
            type="button"
            className="anniversary-nav-btn"
            onClick={goPrevYear}
            disabled={!canPrevYear}
            aria-label="Previous year"
          >
            &lsaquo;
          </button>
          <span className="anniversary-year-text">{viewYear}</span>
          <button
            type="button"
            className="anniversary-nav-btn"
            onClick={goNextYear}
            disabled={!canNextYear}
            aria-label="Next year"
          >
            &rsaquo;
          </button>
        </div>

        {/* Inner rounded rectangle: the wall-calendar block */}
        <div className="anniversary-grid-wrap">
          <div className="anniversary-weekdays">
            {WEEKDAYS.map((w, i) => (
              <span key={i} className="anniversary-weekday">
                {w}
              </span>
            ))}
          </div>

          <div className="anniversary-grid">
            {cells.map((cell, idx) => {
              if (!cell) {
                return <span key={`blank-${idx}`} className="anniversary-day empty" />;
              }
              const isImportant = Boolean(cell.event);
              return (
                <span
                  key={cell.day}
                  className={`anniversary-day${isImportant ? " is-important" : ""}`}
                  onMouseEnter={isImportant ? (e) => showTooltip(e, cell.event!) : undefined}
                  onMouseLeave={isImportant ? hideTooltip : undefined}
                  onFocus={isImportant ? (e) => showTooltip(e, cell.event!) : undefined}
                  onBlur={isImportant ? hideTooltip : undefined}
                  tabIndex={isImportant ? 0 : -1}
                >
                  {cell.day}
                </span>
              );
            })}
          </div>
        </div>

        {/* Month navigation */}
        <div className="anniversary-month-row">
          <button
            type="button"
            className="anniversary-nav-btn"
            onClick={goPrevMonth}
            disabled={!canPrevMonth}
            aria-label="Previous month"
          >
            &lsaquo;
          </button>
          <span className="anniversary-month-text">{MONTH_ABBR[viewMonth]}</span>
          <button
            type="button"
            className="anniversary-nav-btn"
            onClick={goNextMonth}
            disabled={!canNextMonth}
            aria-label="Next month"
          >
            &rsaquo;
          </button>
        </div>
      </div>

      {/* Fixed-position tooltip — escapes any parent overflow: hidden */}
      {tooltip && (
        <div
          className="anniversary-tooltip"
          data-placement={tooltip.placement}
          style={{ left: tooltip.x, top: tooltip.y }}
          role="tooltip"
        >
          <div className="anniversary-tooltip-title">{tooltip.title}</div>
          <div className="anniversary-tooltip-desc">{tooltip.desc}</div>
        </div>
      )}
    </div>
  );
}
