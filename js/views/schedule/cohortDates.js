// ==================== SCHEDULE: COHORT DATES ====================

// Generate dates for one cohort starting at startDate, skipping holidays & wrong days
function schedGenCohortDates(patternKey, startDate, year) {
  const p = SCHED_COHORT_PATTERNS[patternKey];
  if (!p) return [];
  const holidays = schedGetHolidaysQC(year);
  const also = schedGetHolidaysQC(year + 1);
  also.forEach(h => holidays.add(h));

  // For Mon-Thu patterns (soir/jour), use week-based logic:
  // Each week must have exactly the right number of days.
  // If a Mon-Thu day is a holiday, add Friday of that week to compensate.
  const isMonThuPattern = JSON.stringify(p.days) === JSON.stringify([1,2,3,4]);

  if (isMonThuPattern) {
    const dates = [];
    let d = new Date(startDate + 'T00:00:00');
    // Align to the Monday of the start week
    const startDow = d.getDay(); // 0=Sun,1=Mon...
    // If startDate is not Mon, keep it as-is (first week may be partial)
    let safety = 0;
    while (dates.length < p.sessions && safety < 500) {
      safety++;
      const iso = d.toISOString().slice(0,10);
      const dow = d.getDay();

      if (dow === 1) {
        // Start of a Mon-Thu week: collect this week's valid days
        // Find how many Mon-Thu days are holidays this week
        let weekDates = [];
        let holidaysThisWeek = 0;
        for (let offset = 0; offset < 4; offset++) { // Mon=0, Tue=1, Wed=2, Thu=3
          const wd = new Date(d);
          wd.setDate(wd.getDate() + offset);
          const wiso = wd.toISOString().slice(0,10);
          if (holidays.has(wiso)) {
            holidaysThisWeek++;
          } else {
            weekDates.push(wiso);
          }
        }
        // If any Mon-Thu were holidays, add equivalent Fridays to compensate
        if (holidaysThisWeek > 0) {
          for (let fi = 0; fi < holidaysThisWeek; fi++) {
            const fri = new Date(d);
            fri.setDate(fri.getDate() + 4 + fi); // Friday = +4 from Monday
            const fiso = fri.toISOString().slice(0,10);
            if (!holidays.has(fiso) && !weekDates.includes(fiso)) {
              weekDates.push(fiso);
            }
          }
          weekDates.sort();
        }
        // Add this week's dates (up to remaining sessions needed)
        weekDates.forEach(wd => {
          if (dates.length < p.sessions) dates.push(wd);
        });
        // Skip to next Monday
        d.setDate(d.getDate() + 7);
      } else if (dow === 0 || dow === 6 || dow > 4) {
        // Skip weekends (shouldn't happen if we jump by week, but safety)
        d.setDate(d.getDate() + 1);
      } else {
        // Mid-week start (first week only) — just add valid days individually
        const iso2 = d.toISOString().slice(0,10);
        if ([1,2,3,4].includes(dow) && !holidays.has(iso2)) {
          dates.push(iso2);
        }
        d.setDate(d.getDate() + 1);
        // When we hit Monday, the loop above takes over
      }
    }
    return dates;
  }

  // Consecutive patterns: just advance day by day, skip weekends+holidays
  // Works for any start day (Lun, Mar, Mer, etc.)
  if (p.consecutive) {
    const dates = [];
    let d = new Date(startDate + 'T00:00:00');
    let safety = 0;
    while (dates.length < p.sessions && safety < 200) {
      safety++;
      const iso = d.toISOString().slice(0,10);
      const dow = d.getDay();
      if (dow >= 1 && dow <= 5 && !holidays.has(iso)) {
        dates.push(iso);
      }
      d.setDate(d.getDate() + 1);
    }
    return dates;
  }

  // Default logic for other patterns (weekend, etc.)
  const dates = [];
  let d = new Date(startDate + 'T00:00:00');
  let safety = 0;
  while (dates.length < p.sessions && safety < 500) {
    safety++;
    const iso = d.toISOString().slice(0,10);
    const dow = d.getDay();
    if (p.days.includes(dow) && !holidays.has(iso)) {
      dates.push(iso);
    }
    d.setDate(d.getDate() + 1);
  }
  return dates;
}
