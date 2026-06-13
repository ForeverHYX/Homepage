"use strict";
(() => {
  const START_DATE = new Date(Date.UTC(2025, 8, 26));
  const QIXI_TABLE = {
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
    2035: { month: 8, day: 10 }
  };
  const MS_PER_DAY = 864e5;
  function daysBetweenUtc(a, b) {
    return Math.round((b.getTime() - a.getTime()) / MS_PER_DAY);
  }
  function isSameUtcDate(a, b) {
    return a.getUTCFullYear() === b.getUTCFullYear() && a.getUTCMonth() === b.getUTCMonth() && a.getUTCDate() === b.getUTCDate();
  }
  function getAnniversariesForMonth(year, month) {
    const result = /* @__PURE__ */ new Map();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    for (let day = 1; day <= daysInMonth; day++) {
      const current = new Date(Date.UTC(year, month, day));
      const events = [];
      if (isSameUtcDate(current, START_DATE)) {
        events.push({ title: "\u5728\u4E00\u8D77", desc: "\u6211\u4EEC\u6545\u4E8B\u5F00\u59CB\u7684\u90A3\u4E00\u5929" });
      }
      if (year > START_DATE.getUTCFullYear() && month === 8 && // September
      day === 26) {
        const years = year - START_DATE.getUTCFullYear();
        events.push({
          title: `${years} \u5468\u5E74\u7EAA\u5FF5\u65E5`,
          desc: `\u5728\u4E00\u8D77\u6574\u6574 ${years} \u5E74\u5566`
        });
      }
      const delta = daysBetweenUtc(START_DATE, current);
      if (delta > 0 && delta % 100 === 0) {
        events.push({
          title: `${delta} \u5929\u7EAA\u5FF5\u65E5`,
          desc: `\u5728\u4E00\u8D77 ${delta} \u5929\uFF0C\u73CD\u60DC\u6BCF\u4E00\u4E2A\u4E00\u767E\u5929`
        });
      }
      if (month === 1 && day === 14) {
        events.push({ title: "\u60C5\u4EBA\u8282", desc: "Valentine's Day" });
      }
      if (month === 4 && day === 20) {
        events.push({ title: "520", desc: "\u6211\u7231\u4F60" });
      }
      const qixi = QIXI_TABLE[year];
      if (qixi && qixi.month === month && qixi.day === day) {
        events.push({ title: "\u4E03\u5915\u8282", desc: "\u4E2D\u56FD\u60C5\u4EBA\u8282" });
      }
      if (events.length > 0) {
        const title = events.map((e) => e.title).join(" \xB7 ");
        const desc = events.map((e) => `${e.title}\uFF1A${e.desc}`).join("\n");
        result.set(day, { title, desc });
      }
    }
    return result;
  }
  const ANNIVERSARY_YEAR_MIN = START_DATE.getUTCFullYear();
  const ANNIVERSARY_YEAR_MAX = 2035;
  // Expose to global scope
  window.__ANNIVERSARY = {
    getAnniversariesForMonth,
    ANNIVERSARY_YEAR_MIN,
    ANNIVERSARY_YEAR_MAX,
  };
})();
