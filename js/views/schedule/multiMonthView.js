// ==================== SCHEDULE: MULTI-MONTH VIEW ====================

// How many months to display (default 4)
let _schedMultiMonthCount = 4;

// Cache of entries keyed by "YYYY-MM"
let _schedMultiMonthCache = {};

async function schedMultiMonthLoad() {
  const fetches = [];
  let m = _schedMonth, y = _schedYear;
  for (let i = 0; i < _schedMultiMonthCount; i++) {
    const key = y + '-' + String(m).padStart(2, '0');
    if (!_schedMultiMonthCache[key]) {
      const cm = m, cy = y;
      fetches.push(
        dbGetScheduleEntries(cm, cy).then(e => { _schedMultiMonthCache[key] = e; })
                                    .catch(() => { _schedMultiMonthCache[key] = []; })
      );
    }
    m++; if (m > 12) { m = 1; y++; }
  }
  if (fetches.length) await Promise.all(fetches);
}

function schedMultiMonthInvalidate() { _schedMultiMonthCache = {}; }

/**
 * Layout per month block:
 *   ROWS    = trainers  (name sticky on the LEFT)
 *   COLUMNS = days 1..N (scrollable to the right)
 * Months stacked vertically for easy comparison.
 */
function schedBuildMultiMonthView() {
  const todayS  = schedTodayStr();
  const allTrainers = schedGetOrderedTrainers();
  const trainers = _schedTrainer
    ? allTrainers.filter(t => t.id === _schedTrainer)
    : allTrainers;

  if (!trainers.length)
    return `<div class="hor-empty-state">Aucun formateur trouvé. Ajustez le filtre.</div>`;

  let html = '';
  let m = _schedMonth, y = _schedYear;

  for (let i = 0; i < _schedMultiMonthCount; i++) {
    const key  = y + '-' + String(m).padStart(2, '0');
    let entries = _schedMultiMonthCache[key] || [];
    if (_schedProgram) entries = entries.filter(e => e.program === _schedProgram);

    // Index entries: instructor_id → date → [entries]
    const byTD = {};
    entries.forEach(e => {
      if (!byTD[e.instructor_id]) byTD[e.instructor_id] = {};
      if (!byTD[e.instructor_id][e.date]) byTD[e.instructor_id][e.date] = [];
      byTD[e.instructor_id][e.date].push(e);
    });

    const holidays = schedGetHolidaysQC(y);
    schedGetHolidaysQC(y + 1).forEach(h => holidays.add(h));
    const days  = schedDaysInMonth(m, y);
    const label = SCHED_MONTHS_FR[m - 1] + ' ' + y;

    html += _mmBlock(m, y, label, days, trainers, byTD, holidays, todayS);
    m++; if (m > 12) { m = 1; y++; }
  }

  return `<div class="mm-stack-wrap">${html}</div>
    <div style="margin-top:8px;font-size:11px;color:var(--td);opacity:0.6;">
      💡 Cellule vide → nouveau shift · Chip coloré → modifier
    </div>`;
}

function _mmBlock(month, year, label, days, trainers, byTD, holidays, todayS) {
  // --- Header: sticky name col + one <th> per day ---
  let headerCells = `<th class="mm-name-col">Formateur</th>`;
  for (let d = 1; d <= days; d++) {
    const dateS  = schedDateStr(year, month, d);
    const isToday = dateS === todayS;
    const isWe   = schedIsWeekend(year, month, d);
    const isHol  = holidays.has(dateS);
    const dow    = SCHED_DAYS_FR[schedDayOfWeek(dateS)];

    const style = isToday ? 'color:var(--a);background:rgba(255,107,53,0.18);'
      : isHol  ? 'color:#93c5fd;background:rgba(147,197,253,0.14);'
      : isWe   ? 'color:var(--td);opacity:0.55;'
      : '';

    headerCells += `<th class="mm-day-th" style="${style}" title="${isHol ? 'Jour férié' : dateS}">
      <div style="font-size:8px;line-height:1.1;">${isHol ? '🏖' : dow}</div>
      <div style="font-size:11px;font-weight:700;line-height:1.2;">${d}</div>
    </th>`;
  }

  // --- Body: one row per trainer ---
  let bodyRows = '';
  trainers.forEach(trainer => {
    const col  = avatarColor(trainer.id);
    const ini  = initials(trainer.name);
    const name = trainer.name.split(' ').slice(0, 2).join(' ');

    let row = `<tr>`;
    // Sticky name cell
    row += `<td class="mm-name-col mm-name-cell">
      <div style="display:flex;align-items:center;gap:5px;">
        <div style="width:20px;height:20px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
        <span style="font-size:11px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${esc(name)}</span>
      </div>
    </td>`;

    // One cell per day
    for (let d = 1; d <= days; d++) {
      const dateS      = schedDateStr(year, month, d);
      const isToday    = dateS === todayS;
      const isWe       = schedIsWeekend(year, month, d);
      const isHol      = holidays.has(dateS);
      const dayEntries = (byTD[trainer.id] && byTD[trainer.id][dateS]) || [];
      const dimmed     = isWe || isHol;

      const bg = isToday ? 'background:rgba(255,107,53,0.10);'
        : isHol ? 'background:rgba(147,197,253,0.10);'
        : isWe  ? 'background:rgba(255,255,255,0.018);'
        : '';

      if (dayEntries.length === 0) {
        row += `<td class="mm-cell${dimmed ? ' mm-dim' : ' mm-empty'}" style="${bg}"${
          !dimmed ? ` onclick="schedClickEmpty('${esc(trainer.id)}','${esc(dateS)}','',null)"` : ''
        }></td>`;
      } else {
        const chips = dayEntries.map(e => {
          const chipBg = schedCellBg(e) || '#3b82f6';
          const lbl    = _mmLabel(e);
          const tip    = schedCellTooltip(e);
          return `<span class="mm-chip" style="background:${chipBg};" title="${esc(tip)}"
            onclick="schedOpenPopup('${esc(e.id)}',null)">${esc(lbl)}</span>`;
        }).join('');
        row += `<td class="mm-cell" style="${bg}">${chips}</td>`;
      }
    }
    row += `</tr>`;
    bodyRows += row;
  });

  return `
    <div class="mm-block">
      <div class="mm-block-title">${esc(label)}</div>
      <div class="mm-block-scroll">
        <table class="mm-table">
          <thead><tr>${headerCells}</tr></thead>
          <tbody>${bodyRows}</tbody>
        </table>
      </div>
    </div>`;
}

function _mmLabel(entry) {
  if (!entry) return '';
  const s = entry.status || 'scheduled';
  if (s === 'vacation')    return 'VAC';
  if (s === 'unavailable') return 'OFF';
  if (s === 'holiday')     return 'F';
  if (s === 'cancelled')   return 'X';
  if (s === 'replacement') return 'R';
  const code = entry.excel_cell_code || (entry.cohorts && entry.cohorts.code) || '';
  if (code) return code;
  return (entry.program || '?').substring(0, 5);
}
