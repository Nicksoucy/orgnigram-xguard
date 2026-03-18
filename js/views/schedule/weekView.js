// ==================== SCHEDULE: WEEK VIEW ====================

// ---- VIEW 2: Hebdomadaire ----

function schedGetWeekStart(year, month) {
  // Return Monday of current week based on _schedMonth/_schedYear — use first week that has the 1st
  const firstDay = new Date(year, month - 1, 1);
  const dow = firstDay.getDay();
  const diff = dow === 0 ? -6 : 1 - dow;
  const monday = new Date(firstDay);
  monday.setDate(firstDay.getDate() + diff);
  return monday;
}

function schedBuildWeekView() {
  // Use _schedWeekStart if set, else compute from month
  const weekStart = _schedWeekStart || schedGetWeekStart(_schedYear, _schedMonth);
  const todayS = schedTodayStr();

  // Build 7 days
  const weekDays = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekStart);
    d.setDate(weekStart.getDate() + i);
    weekDays.push(d.toISOString().slice(0, 10));
  }

  const entries = _schedProgram
    ? _schedEntries.filter(e => e.program === _schedProgram)
    : _schedEntries;

  // Filter entries to week
  const weekEntries = entries.filter(e => weekDays.includes(e.date));

  // Group by date
  const byDate = {};
  weekEntries.forEach(e => {
    if (!byDate[e.date]) byDate[e.date] = [];
    byDate[e.date].push(e);
  });

  // Hours 8–22
  const hours = [];
  for (let h = 8; h <= 22; h++) hours.push(h);

  // Header
  let headerHTML = `<th class="time-col">Heure</th>`;
  weekDays.forEach((d, i) => {
    const isToday = d === todayS;
    const dayD = new Date(d + 'T00:00:00');
    headerHTML += `<th${isToday ? ' style="color:var(--a);background:rgba(255,107,53,0.1);"' : ''}>
      <div style="font-size:9px;color:var(--td);text-transform:uppercase;">${SCHED_DAYS_FR[i]}</div>
      <div style="font-size:12px;font-weight:700;">${dayD.getDate()} ${SCHED_MONTHS_FR[dayD.getMonth()].slice(0,3)}</div>
    </th>`;
  });

  // Body: for each hour, each day
  let bodyHTML = '';
  hours.forEach(h => {
    const hStr = String(h).padStart(2, '0') + ':00';
    bodyHTML += `<tr>`;
    bodyHTML += `<td class="time-cell">${hStr}</td>`;
    weekDays.forEach(dateS => {
      const isToday = dateS === todayS;
      const dayEntries = (byDate[dateS] || []).filter(e => {
        const st = parseInt((e.start_time || '09:00').split(':')[0]);
        return st === h;
      });
      const pills = dayEntries.map(e => {
        const color = schedProgramColor(e.program);
        const trainer = data.find(p => p.id === e.instructor_id);
        const label = (trainer ? trainer.name.split(' ')[0] : '') + ' ' + schedCellContent(e);
        return `<span class="sched-week-pill" style="background:${color};"
          onclick="schedOpenPopup('${esc(e.id)}', event); event.stopPropagation();"
          title="${esc(label)} ${esc(e.start_time||'')}–${esc(e.end_time||'')}">${esc(label.trim())}</span>`;
      }).join('');
      bodyHTML += `<td class="${isToday ? 'sched-today-col' : ''}"
        onclick="schedClickEmpty('','${esc(dateS)}','')">
        ${pills}
      </td>`;
    });
    bodyHTML += `</tr>`;
  });

  // Week nav label
  const endDay = new Date(weekStart);
  endDay.setDate(weekStart.getDate() + 6);
  const sm = SCHED_MONTHS_FR[weekStart.getMonth()];
  const em = SCHED_MONTHS_FR[endDay.getMonth()];
  const weekLabel = weekStart.getDate() + ' ' + sm + ' – ' + endDay.getDate() + ' ' + em + ' ' + endDay.getFullYear();

  return `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
      <button class="btn" onclick="schedNavWeek(-1)">&#8592;</button>
      <span style="font-size:13px;font-weight:600;">${esc(weekLabel)}</span>
      <button class="btn" onclick="schedNavWeek(1)">&#8594;</button>
    </div>
    <div class="sched-week-wrap">
      <table class="sched-week-grid">
        <thead><tr>${headerHTML}</tr></thead>
        <tbody>${bodyHTML}</tbody>
      </table>
    </div>`;
}
