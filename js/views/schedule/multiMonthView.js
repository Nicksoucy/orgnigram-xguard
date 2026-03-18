// ==================== SCHEDULE: MULTI-MONTH VIEW ====================

// How many months to display (default 4)
let _schedMultiMonthCount = 4;

// Cache of entries keyed by "YYYY-MM"
let _schedMultiMonthCache = {};

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

/** Clears cache — call after any shift save/delete. */
function schedMultiMonthInvalidate() {
  _schedMultiMonthCache = {};
}

/**
 * Builds the full multi-month view.
 *
 * Layout — like the Google Sheet:
 *   ROWS    = days (1..N)
 *   COLUMNS = trainers
 *   Each month = its own table block, stacked vertically.
 *   All blocks share the same column widths so they align visually.
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

  // Build trainer header (shared across all month blocks)
  const trainerHeader = _mmTrainerHeader(trainers);

  // Build one block per month, stacked
  let blocksHTML = '';
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

    const label = SCHED_MONTHS_FR[m - 1] + ' ' + y;
    const days  = schedDaysInMonth(m, y);

    blocksHTML += _mmOneMonthBlock(m, y, label, days, trainers, byTrainerDate, holidays, todayS, trainerHeader, i === 0);

    m++; if (m > 12) { m = 1; y++; }
  }

  return `
    <div class="mm-stack-wrap">
      ${blocksHTML}
    </div>
    <div style="margin-top:8px;font-size:11px;color:var(--td);opacity:0.6;">
      💡 Cliquez sur une cellule vide pour ajouter un shift · sur un chip pour le modifier
    </div>`;
}

/**
 * Builds the trainer header row HTML (reused in every month block).
 */
function _mmTrainerHeader(trainers) {
  let cells = `<th class="mm-day-col">Jour</th>`;
  trainers.forEach(t => {
    const col = avatarColor(t.id);
    const ini = initials(t.name);
    const name = t.name.split(' ').slice(0, 2).join(' ');
    cells += `<th class="mm-trainer-col">
      <div style="display:flex;align-items:center;gap:4px;justify-content:center;">
        <div style="width:16px;height:16px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:7px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
        <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:90px;font-size:10px;">${esc(name)}</span>
      </div>
    </th>`;
  });
  return cells;
}

/**
 * Builds one month block: a title bar + a scrollable table (rows = days, cols = trainers).
 */
function _mmOneMonthBlock(month, year, label, days, trainers, byTrainerDate, holidays, todayS, trainerHeader, isFirst) {
  let bodyRows = '';

  for (let d = 1; d <= days; d++) {
    const dateS   = schedDateStr(year, month, d);
    const isToday = dateS === todayS;
    const isWe    = schedIsWeekend(year, month, d);
    const isHol   = holidays.has(dateS);
    const dow     = SCHED_DAYS_FR[schedDayOfWeek(dateS)];

    const rowBg = isToday   ? 'background:rgba(255,107,53,0.10);'
      : isHol   ? 'background:rgba(147,197,253,0.10);'
      : isWe    ? 'background:rgba(255,255,255,0.02);'
      : '';

    const dayStyle = isToday  ? 'color:var(--a);font-weight:800;'
      : isHol  ? 'color:#93c5fd;'
      : isWe   ? 'color:var(--td);opacity:0.65;'
      : 'color:var(--t);';

    let row = `<tr style="${rowBg}">`;
    // Day label cell
    row += `<td class="mm-day-col" style="${dayStyle}">
      <span style="font-size:8px;opacity:0.7;">${isHol ? '🏖' : dow}</span>
      <strong style="margin-left:3px;font-size:11px;">${d}</strong>
    </td>`;

    // One cell per trainer
    trainers.forEach(t => {
      const dayEntries = (byTrainerDate[t.id] && byTrainerDate[t.id][dateS]) || [];

      if (dayEntries.length === 0) {
        const dimmed = isWe || isHol;
        row += `<td class="mm-cell${dimmed ? ' mm-dim' : ' mm-empty'}" style="${rowBg}"${
          !dimmed ? ` onclick="schedClickEmpty('${esc(t.id)}','${esc(dateS)}','',null)"` : ''
        }></td>`;
      } else {
        const chips = dayEntries.map(entry => {
          const chipBg = schedCellBg(entry) || '#3b82f6';
          const lbl    = _schedMultiLabel(entry);
          const tip    = schedCellTooltip(entry);
          return `<span class="mm-chip" style="background:${chipBg};" title="${esc(tip)}"
            onclick="schedOpenPopup('${esc(entry.id)}',null)">${esc(lbl)}</span>`;
        }).join('');
        row += `<td class="mm-cell" style="${rowBg}">${chips}</td>`;
      }
    });

    row += `</tr>`;
    bodyRows += row;
  }

  // Always render <thead> for column width consistency; visually hide it after first block
  const theadClass = isFirst ? '' : ' class="mm-thead-hidden"';

  return `
    <div class="mm-block">
      <div class="mm-block-title">${esc(label)}</div>
      <div class="mm-block-scroll">
        <table class="mm-table">
          <thead${theadClass}>
            <tr>${trainerHeader}</tr>
          </thead>
          <tbody>${bodyRows}</tbody>
        </table>
      </div>
    </div>`;
}

/** Short chip label. */
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
