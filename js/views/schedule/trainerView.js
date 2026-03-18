// ==================== SCHEDULE: TRAINER VIEW ====================

// ---- VIEW 3: Par trainer ----

function schedBuildTrainerView() {
  const trainers = schedGetTrainers();

  // Sidebar
  let sidebarHTML = `<div class="sched-trainer-sidebar">
    <div class="sched-trainer-sidebar-title">Formateurs</div>`;
  trainers.forEach(t => {
    const col = avatarColor(t.id);
    const ini = initials(t.name);
    const active = _schedTrainer === t.id;
    sidebarHTML += `<div class="sched-trainer-item${active ? ' active' : ''}" onclick="schedSelectTrainer('${esc(t.id)}')">
      <div style="width:24px;height:24px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
      <span class="sched-trainer-name">${esc(t.name)}</span>
    </div>`;
  });
  sidebarHTML += `</div>`;

  // Main content
  let mainHTML = '';
  if (!_schedTrainer) {
    mainHTML = `<div class="hor-empty-state" style="display:flex;align-items:center;justify-content:center;min-height:200px;">
      Sélectionnez un formateur dans la liste à gauche.
    </div>`;
  } else {
    const trainer = data.find(p => p.id === _schedTrainer);
    if (!trainer) {
      mainHTML = `<div class="hor-empty-state">Formateur introuvable.</div>`;
    } else {
      const col = avatarColor(trainer.id);
      const ini = initials(trainer.name);

      // Header
      mainHTML += `<div class="sched-trainer-header">
        <div style="width:40px;height:40px;border-radius:50%;background:${col};display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;color:#fff;flex-shrink:0;">${esc(ini)}</div>
        <div>
          <div style="font-size:15px;font-weight:700;">${esc(trainer.name)}</div>
          <div style="font-size:11px;color:var(--td);">${esc(trainer.role || '')}</div>
        </div>
      </div>`;

      // Filter entries for this trainer
      const tEntries = _schedEntries.filter(e => e.instructor_id === _schedTrainer);

      if (!tEntries.length) {
        mainHTML += `<div class="hor-empty-state">Aucun shift ce mois-ci pour ${esc(trainer.name)}.</div>`;
      } else {
        // Session IDs list
        const withSession = tEntries.filter(e => e.session_id);
        const sessionListHTML = withSession.length
          ? withSession.map(e => `
            <div class="sched-session-row">
              <span class="sched-session-date">${esc(e.date)}</span>
              <span class="sched-session-prog" style="color:${schedProgramColor(e.program)};">${esc(schedProgramLabel(e.program))}</span>
              <span class="sched-session-id" onclick="schedCopySessionId('${esc(e.session_id)}')" title="Cliquer pour copier">${esc(e.session_id)}</span>
            </div>`)
            .join('')
          : `<div style="font-size:11px;color:var(--td);padding:8px 0;">Aucun session ID généré (les nouveaux shifts en auront un).</div>`;

        mainHTML += `<div class="sched-session-list">
          <div class="sched-session-list-title">
            <span>Session IDs — ${esc(schedMonthLabel())}</span>
            <button class="btn" style="font-size:10px;padding:3px 10px;" onclick="schedExportSessions()">Exporter pour facture</button>
          </div>
          ${sessionListHTML}
        </div>`;

        // Mini calendar for the month
        const days = schedDaysInMonth(_schedMonth, _schedYear);
        const entryByDate = {};
        tEntries.forEach(e => {
          if (!entryByDate[e.date]) entryByDate[e.date] = [];
          entryByDate[e.date].push(e);
        });

        let calHTML = `<div style="font-size:13px;font-weight:700;margin-bottom:8px;">${esc(schedMonthLabel())}</div>
          <div style="overflow-x:auto;">
          <table style="border-collapse:collapse;min-width:100%;">
            <thead><tr>`;
        SCHED_DAYS_FR.forEach(d => {
          calHTML += `<th style="background:var(--sh);border:1px solid var(--b);padding:6px 8px;font-size:10px;font-weight:600;color:var(--td);text-align:center;">${d}</th>`;
        });
        calHTML += `</tr></thead><tbody><tr>`;

        const firstDow = schedDayOfWeek(schedDateStr(_schedYear, _schedMonth, 1));
        let col2 = 0;
        for (let i = 0; i < firstDow; i++) {
          calHTML += `<td style="background:var(--bg);border:1px solid var(--b);height:64px;"></td>`;
          col2++;
        }

        const todayS = schedTodayStr();
        for (let d = 1; d <= days; d++) {
          const dateS = schedDateStr(_schedYear, _schedMonth, d);
          const isToday = dateS === todayS;
          const dayArr = entryByDate[dateS] || [];
          const pills  = dayArr.slice(0, 2).map(e => {
            const bg = schedCellBg(e) || SCHED_STATUS_COLORS[e.status] || '#60a5fa';
            return `<div style="font-size:9px;font-weight:700;padding:1px 4px;border-radius:2px;background:${bg};color:#fff;margin-bottom:2px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
              onclick="schedOpenPopup('${esc(e.id)}', event); event.stopPropagation();">${esc(schedCellContent(e))}</div>`;
          }).join('');
          const overflow = dayArr.length > 2 ? `<div style="font-size:8px;color:var(--td);">+${dayArr.length - 2}</div>` : '';

          calHTML += `<td style="border:1px solid var(--b);padding:4px;vertical-align:top;min-height:64px;height:64px;background:${isToday ? 'rgba(255,107,53,0.06)' : 'var(--s)'};cursor:pointer;"
            onclick="schedClickEmpty('${esc(_schedTrainer)}','${esc(dateS)}','')">
            <div style="font-size:10px;font-weight:700;color:${isToday ? 'var(--a)' : 'var(--td)'};margin-bottom:3px;">${d}</div>
            ${pills}${overflow}
          </td>`;
          col2++;

          if (col2 % 7 === 0 && d < days) calHTML += `</tr><tr>`;
        }

        // Pad remaining
        const rem = 7 - (col2 % 7 === 0 ? 0 : col2 % 7);
        if (rem < 7) {
          for (let i = 0; i < rem; i++) {
            calHTML += `<td style="background:var(--bg);border:1px solid var(--b);height:64px;"></td>`;
          }
        }
        calHTML += `</tr></tbody></table></div>`;

        mainHTML += `<div style="background:var(--s);border:1px solid var(--b);border-radius:10px;padding:14px 18px;">${calHTML}</div>`;
      }
    }
  }

  return `<div class="sched-trainer-layout">
    ${sidebarHTML}
    <div class="sched-trainer-main">${mainHTML}</div>
  </div>`;
}
