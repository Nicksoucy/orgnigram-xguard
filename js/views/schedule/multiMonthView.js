// ==================== SCHEDULE: MULTI-MONTH VIEW ====================

// How many months to display (default 4)
let _schedMultiMonthCount = 4;

// Cache of entries keyed by "YYYY-MM"
let _schedMultiMonthCache = {}; // { 'YYYY-MM': [entries] }

/**
 * Fetches entries for all months in the range that aren't cached yet.
 */
async function schedMultiMonthLoad() {
  const fetches = [];
  let m = _schedMonth, y = _schedYear;
  for (let i = 0; i < _schedMultiMonthCount; i++) {
    const key = y + '-' + String(m).padStart(2, '0');
    if (!_schedMultiMonthCache[key]) {
      const cm = m, cy = y;
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
 * Clears the cache — called after any shift save/delete.
 */
function schedMultiMonthInvalidate() {
  _schedMultiMonthCache = {};
}

/**
 * Builds the full multi-month view.
 *
 * Layout (like the Google Sheet):
 *   - LEFT sticky column: trainer name
 *   - COLUMNS: months side by side, each month = its days as columns
 *   - ROWS: one per trainer
 *
 * All months share a single table so scrolling is horizontal across all months at once.
 */
function schedBuildMultiMonthView() {
  const todayS   = schedTodayStr();
  const allTrainers = schedGetOrderedTrainers();

  const trainers = _schedTrainer
    ? allTrainers.filter(t => t.id === _schedTrainer)
    : allTrainers;

  if (!trainers.length) {
    return `<div class="hor-empty-state">Aucun formateur trouvé. Ajustez le filtre.</div>`;
  }

  // Collect all month metadata + their entries
  const months = [];
  let m = _schedMonth, y = _schedYear;
  for (let i = 0; i < _schedMultiMonthCount; i++) {
    const key  = y + '-' + String(m).padStart(2, '0');
    let entries = _schedMultiMonthCache[key] || [];
    if (_schedProgram) entries = entries.filter(e => e.program === _schedProgram);

    // Index: instructor_id → date → [entries]
    const byTrainerDate = {};
    entries.forEach(e => {
      if (!byTrainerDate[e.instructor_id]) byTrainerDate[e.instructor_id] = {};
      if (!byTrainerDate[e.instructor_id][e.date]) byTrainerDate[e.instructor_id][e.date] = [];
      byTrainerDate[e.instructor_id][e.date].push(e);
    });

    const holidays = schedGetHolidaysQC(y);
    schedGetHolidaysQC(y + 1).forEach(h => holidays.add(h));

    months.push({
      month: m, year: y,
      label: SCHED_MONTHS_FR[m - 1] + ' ' + y,
      days: schedDaysInMonth(m, y),
      byTrainerDate, holidays
    });

    m++; if (m > 12) { m = 1; y++; }
  }

  // ---- Header row 1: month group labels ----
  let hRow1 = `<th class="mm-name-col" rowspan="2">Formateur</th>`;
  months.forEach(mo => {
    hRow1 += `<th class="mm-month-header" colspan="${mo.days}">${esc(mo.label)}</th>`;
  });

  // ---- Header row 2: day numbers + day-of-week ----
  let hRow2 = '';
  months.forEach(mo => {
    for (let d = 1; d <= mo.days; d++) {
      const dateS    = schedDateStr(mo.year, mo.month, d);
      const isToday  = dateS === todayS;
      const isWe     = schedIsWeekend(mo.year, mo.month, d);
      const isHol    = mo.holidays.has(dateS);
      const isLast   = d === mo.days;
      const dow      = SCHED_DAYS_FR[schedDayOfWeek(dateS)];

      const col = isToday ? 'color:var(--a);' : isHol ? 'color:#93c5fd;' : isWe ? 'color:var(--td);opacity:0.6;' : '';
      const bg  = isToday ? 'background:rgba(255,107,53,0.15);' : isHol ? 'background:rgba(147,197,253,0.12);' : '';
      const cls = ['mm-day-head', isWe?'mm-we':'', isLast?'mm-month-sep':''].filter(Boolean).join(' ');

      hRow2 += `<th class="${cls}" style="${col}${bg}" title="${isHol ? 'Jour férié' : dateS}">
        <div style="font-size:8px;line-height:1;">${isHol ? '🏖' : dow}</div>
        <div style="font-size:10px;font-weight:700;line-height:1.3;">${d}</div>
      </th>`;
    }
  });

  // ---- Body: one row per trainer ----
  let bodyHTML = '';
  trainers.forEach(trainer => {
    const col = avatarColor(trainer.id);
    const ini = initials(trainer.name);
    const shortName = trainer.name.split(' ').slice(0, 2).join(' ');

    let row = `<tr>`;
    // Sticky trainer name cell
    row += `<td class="mm-name-col mm-name-cell">
      <div style="display:flex;align-items:center;gap:5px;">
        <div style="width:20px;height:20px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
        <span style="font-size:11px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${esc(shortName)}</span>
      </div>
    </td>`;

    // Day cells across all months
    months.forEach(mo => {
      for (let d = 1; d <= mo.days; d++) {
        const dateS     = schedDateStr(mo.year, mo.month, d);
        const isToday   = dateS === todayS;
        const isWe       = schedIsWeekend(mo.year, mo.month, d);
        const isHol      = mo.holidays.has(dateS);
        const isLast     = d === mo.days;
        const dayEntries = (mo.byTrainerDate[trainer.id] && mo.byTrainerDate[trainer.id][dateS]) || [];
        const sepCls     = isLast ? ' mm-month-sep' : '';

        const bg = isToday ? 'background:rgba(255,107,53,0.10);'
          : isHol ? 'background:rgba(147,197,253,0.10);'
          : isWe  ? 'background:rgba(255,255,255,0.015);'
          : '';

        if (dayEntries.length === 0) {
          const dimCls = (isWe || isHol) ? ' mm-dim' : ' mm-empty';
          row += `<td class="mm-cell${dimCls}${sepCls}" style="${bg}"${!(isWe||isHol)?` onclick="schedClickEmpty('${esc(trainer.id)}','${esc(dateS)}','',null)"`:''  }></td>`;
        } else {
          const chips = dayEntries.map(entry => {
            const chipBg = schedCellBg(entry) || '#3b82f6';
            const label  = _schedMultiLabel(entry);
            const tip    = schedCellTooltip(entry);
            return `<span class="mm-chip" style="background:${chipBg};" title="${esc(tip)}"
              onclick="schedOpenPopup('${esc(entry.id)}',null)">${esc(label)}</span>`;
          }).join('');
          row += `<td class="mm-cell${sepCls}" style="${bg}">${chips}</td>`;
        }
      }
    });

    row += `</tr>`;
    bodyHTML += row;
  });

  return `
    <div class="mm-outer">
      <table class="mm-table">
        <thead>
          <tr class="mm-month-row">${hRow1}</tr>
          <tr class="mm-daynum-row">${hRow2}</tr>
        </thead>
        <tbody>${bodyHTML}</tbody>
      </table>
    </div>
    <div style="margin-top:8px;font-size:11px;color:var(--td);opacity:0.6;">
      💡 Cliquez sur une cellule vide pour ajouter un shift · sur un chip pour le modifier
    </div>`;
}

/**
 * Short chip label.
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
