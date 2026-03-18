// ==================== SCHEDULE: MULTI-MONTH VIEW ====================

// How many months to display (default 4)
let _schedMultiMonthCount = 4;

// Cache of entries keyed by "YYYY-MM" fetched for multi-month view
let _schedMultiMonthCache = {}; // { 'YYYY-MM': [entries] }

/**
 * Returns the start month/year for the multi-month view.
 * Shows current month as the first block.
 */
function schedMultiMonthStartDate() {
  return { month: _schedMonth, year: _schedYear };
}

/**
 * Fetches entries for all months in the multi-month range that aren't cached yet.
 * Populates _schedMultiMonthCache.
 */
async function schedMultiMonthLoad() {
  const fetches = [];
  let m = _schedMonth, y = _schedYear;
  for (let i = 0; i < _schedMultiMonthCount; i++) {
    const key = y + '-' + String(m).padStart(2, '0');
    if (!_schedMultiMonthCache[key]) {
      const cm = m, cy = y; // capture for closure
      fetches.push(
        dbGetScheduleEntries(cm, cy).then(entries => {
          _schedMultiMonthCache[key] = entries;
        }).catch(() => {
          _schedMultiMonthCache[key] = [];
        })
      );
    }
    m++; if (m > 12) { m = 1; y++; }
  }
  if (fetches.length) await Promise.all(fetches);
}

/**
 * Clears the multi-month cache so next render re-fetches.
 * Called after any shift create/update/delete.
 */
function schedMultiMonthInvalidate() {
  _schedMultiMonthCache = {};
}

/**
 * Builds the full multi-month view HTML.
 * Layout: one compact month block per row, columns = trainers (or single trainer if filtered).
 */
function schedBuildMultiMonthView() {
  const todayS = schedTodayStr();
  const allTrainers = schedGetOrderedTrainers();

  // Which trainers to show — respect filter
  const trainers = _schedTrainer
    ? allTrainers.filter(t => t.id === _schedTrainer)
    : allTrainers;

  if (!trainers.length) {
    return `<div class="hor-empty-state">Aucun formateur trouvé. Ajustez le filtre.</div>`;
  }

  let html = '';

  let m = _schedMonth, y = _schedYear;
  for (let mi = 0; mi < _schedMultiMonthCount; mi++) {
    const key = y + '-' + String(m).padStart(2, '0');
    let monthEntries = _schedMultiMonthCache[key] || [];

    // Apply program filter
    if (_schedProgram) {
      monthEntries = monthEntries.filter(e => e.program === _schedProgram);
    }

    html += _schedBuildOneMonth(m, y, trainers, monthEntries, todayS);

    m++; if (m > 12) { m = 1; y++; }
  }

  return `<div class="sched-multimonth-wrap">${html}</div>`;
}

/**
 * Builds one month block.
 * Rows = days 1..N, columns = trainer cells.
 */
function _schedBuildOneMonth(month, year, trainers, entries, todayS) {
  const days = schedDaysInMonth(month, year);
  const holidays = schedGetHolidaysQC(year);
  schedGetHolidaysQC(year + 1).forEach(h => holidays.add(h));

  const monthName = SCHED_MONTHS_FR[month - 1] + ' ' + year;

  // Index entries: instructor_id → date → [entries]
  const byTrainerDate = {};
  entries.forEach(e => {
    if (!byTrainerDate[e.instructor_id]) byTrainerDate[e.instructor_id] = {};
    if (!byTrainerDate[e.instructor_id][e.date]) byTrainerDate[e.instructor_id][e.date] = [];
    byTrainerDate[e.instructor_id][e.date].push(e);
  });

  // Header: month title + trainer columns
  let headerCols = `<th class="mm-day-col">Jour</th>`;
  trainers.forEach(t => {
    const col = avatarColor(t.id);
    const ini = initials(t.name);
    const shortName = t.name.split(' ').slice(0, 2).join(' ');
    headerCols += `<th class="mm-trainer-col" title="${esc(t.name)}">
      <div style="display:flex;align-items:center;gap:4px;justify-content:center;">
        <div style="width:16px;height:16px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:7px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
        <span style="font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:80px;">${esc(shortName)}</span>
      </div>
    </th>`;
  });

  // Body rows: one per day
  let bodyRows = '';
  for (let d = 1; d <= days; d++) {
    const dateS = schedDateStr(year, month, d);
    const isToday = dateS === todayS;
    const isWe = schedIsWeekend(year, month, d);
    const isHoliday = holidays.has(dateS);
    const dow = SCHED_DAYS_FR[schedDayOfWeek(dateS)];

    const rowBg = isToday
      ? 'background:rgba(255,107,53,0.10);'
      : isHoliday ? 'background:rgba(147,197,253,0.12);'
      : isWe ? 'background:rgba(255,255,255,0.02);'
      : '';

    const dayColor = isToday ? 'color:var(--a);font-weight:800;'
      : isHoliday ? 'color:#93c5fd;'
      : isWe ? 'color:var(--td);opacity:0.7;'
      : 'color:var(--t);';

    let row = `<tr style="${rowBg}">`;
    row += `<td class="mm-day-col" style="${dayColor}font-size:10px;white-space:nowrap;">
      <span style="opacity:0.6;font-size:9px;">${isHoliday ? '🏖' : dow}</span>
      <strong style="margin-left:2px;">${d}</strong>
    </td>`;

    trainers.forEach(t => {
      const dayEntries = (byTrainerDate[t.id] && byTrainerDate[t.id][dateS]) || [];
      if (dayEntries.length === 0) {
        const style = (isWe || isHoliday) ? 'opacity:0.3;' : '';
        row += `<td class="mm-cell mm-empty" style="${style}" onclick="schedClickEmpty('${esc(t.id)}','${esc(dateS)}','',null)"></td>`;
      } else {
        const chips = dayEntries.map(entry => {
          const bg = schedCellBg(entry);
          const label = _schedMultiLabel(entry);
          const tip = schedCellTooltip(entry);
          return `<span class="mm-chip" style="background:${bg||'#3b82f6'};" title="${esc(tip)}" onclick="schedOpenPopup('${esc(entry.id)}',null)">${esc(label)}</span>`;
        }).join('');
        row += `<td class="mm-cell" style="${rowBg}">${chips}</td>`;
      }
    });

    row += `</tr>`;
    bodyRows += row;
  }

  return `
    <div class="mm-month-block">
      <div class="mm-month-title">${esc(monthName)}</div>
      <div style="overflow-x:auto;">
        <table class="mm-table">
          <thead><tr>${headerCols}</tr></thead>
          <tbody>${bodyRows}</tbody>
        </table>
      </div>
    </div>`;
}

/**
 * Returns a very short label for a cell chip: code, session number, or program abbrev.
 */
function _schedMultiLabel(entry) {
  if (!entry) return '';
  const status = entry.status || 'scheduled';
  if (status === 'vacation')    return 'VAC';
  if (status === 'unavailable') return 'OFF';
  if (status === 'holiday')     return 'F';
  if (status === 'cancelled')   return 'X';
  if (status === 'replacement') return 'R';
  const code = entry.excel_cell_code || (entry.cohorts && entry.cohorts.code) || '';
  if (code) return code;
  return (entry.program || '?').substring(0, 5);
}
