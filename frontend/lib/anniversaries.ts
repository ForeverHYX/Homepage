// Important date logic for the upload-page anniversary calendar.
// All dates are evaluated per (year, month) and returned as a Map<day, Event>.

export type AnniversaryEvent = {
  title: string;
  desc: string;
};

const START_DATE = new Date(Date.UTC(2025, 8, 26)); // 2025-09-26 (months are 0-indexed)

// 七夕 = 农历七月初七. Hardcoded Gregorian dates for 2025–2035 (verified).
// Out of this range, the festival is simply not marked.
const QIXI_TABLE: Record<number, { month: number; day: number }> = {
  2025: { month: 8, day: 29 },
  2026: { month: 8, day: 19 },
  2027: { month: 8, day: 8 },
  2028: { month: 8, day: 26 },
  2029: { month: 8, day: 16 },
  2030: { month: 8, day: 5 },
  2031: { month: 8, day: 24 },
  2032: { month: 8, day: 12 },
  2033: { month: 8, day: 1 },
  2034: { month: 8, day: 20 },
  2035: { month: 8, day: 10 },
};

const MS_PER_DAY = 86_400_000;

function daysBetweenUtc(a: Date, b: Date): number {
  return Math.round((b.getTime() - a.getTime()) / MS_PER_DAY);
}

function isSameUtcDate(a: Date, b: Date): boolean {
  return (
    a.getUTCFullYear() === b.getUTCFullYear() &&
    a.getUTCMonth() === b.getUTCMonth() &&
    a.getUTCDate() === b.getUTCDate()
  );
}

function makeUtc(y: number, m0: number, d: number): Date {
  return new Date(Date.UTC(y, m0, d));
}

/**
 * Returns the important events occurring in a given (year, month) where month
 * is 0-indexed. The result is keyed by the day-of-month (1–31).
 */
export function getAnniversariesForMonth(
  year: number,
  month: number,
): Map<number, AnniversaryEvent> {
  const result = new Map<number, AnniversaryEvent>();

  // How many days in this month?
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  for (let day = 1; day <= daysInMonth; day++) {
    // Use Date.UTC so the iteration date is timezone-agnostic. In CST (UTC+8)
    // a local midnight sits 8h behind UTC, so `new Date(year, month, day)`
    // would read as the PREVIOUS day in UTC and the start-date marker would
    // land on Sept 27 instead of Sept 26. Anchoring both START_DATE and the
    // iteration to UTC keeps the comparison correct regardless of TZ.
    const current = new Date(Date.UTC(year, month, day));
    const events: AnniversaryEvent[] = [];

    // 1) Start date itself (2025-09-26).
    if (isSameUtcDate(current, START_DATE)) {
      events.push({ title: "在一起", desc: "我们故事开始的那一天" });
    }

    // 2) Yearly anniversary of the start date (Sep 26 for years > 2025).
    if (
      year > START_DATE.getUTCFullYear() &&
      month === 8 && // September
      day === 26
    ) {
      const years = year - START_DATE.getUTCFullYear();
      events.push({
        title: `${years} 周年纪念日`,
        desc: `在一起整整 ${years} 年啦`,
      });
    }

    // 3) Every 100-day anniversary (strictly after the start date).
    const delta = daysBetweenUtc(START_DATE, current);
    if (delta > 0 && delta % 100 === 0) {
      events.push({
        title: `${delta} 天纪念日`,
        desc: `在一起 ${delta} 天，珍惜每一个一百天`,
      });
    }

    // 4) Valentine's Day — Feb 14.
    if (month === 1 && day === 14) {
      events.push({ title: "情人节", desc: "Valentine's Day" });
    }

    // 5) 520 — May 20.
    if (month === 4 && day === 20) {
      events.push({ title: "520", desc: "我爱你" });
    }

    // 6) 七夕 (Qixi) — lunar 7/7 via lookup table.
    const qixi = QIXI_TABLE[year];
    if (qixi && qixi.month === month && qixi.day === day) {
      events.push({ title: "七夕节", desc: "中国情人节" });
    }

    if (events.length > 0) {
      // If multiple events collide on the same day, merge descriptions.
      const title = events.map((e) => e.title).join(" · ");
      const desc = events.map((e) => `${e.title}：${e.desc}`).join("\n");
      result.set(day, { title, desc });
    }
  }

  return result;
}

export const ANNIVERSARY_YEAR_MIN = START_DATE.getUTCFullYear(); // 2025
export const ANNIVERSARY_YEAR_MAX = 2035;
