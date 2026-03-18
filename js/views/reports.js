// ==================== VIEW: RAPPORTS ====================
// REPORT_PEOPLE is defined in state.js:
// const REPORT_PEOPLE = {
//   'L3': {type:'sac',         label:'SAC'},
//   'v1': {type:'ventes',      label:'Ventes'},
//   'r1': {type:'recrutement', label:'Recrutement'},
//   'L2': {type:'admin',       label:'Admin'}
// };

// ============================================================
// REPORT SCHEMA CONFIG
// Defines fields, sections, and key stats for each report type.
// To add a new report type: add an entry here + add to REPORT_PEOPLE in state.js.
// ============================================================

const RPT_SCHEMA = {

  sac: {
    requiredField: { id: 'rf_observations', label: 'Observations' },
    sections: [
      {
        title: "Volume d'appels",
        hint: '(tire de JustCall)',
        type: 'agent-table',
        agents: ['Hamza', 'Lilia', 'Sekou'],
        cols: [
          { label: 'Entrants',   suffix: '_in',   inputType: 'number' },
          { label: 'Sortants',   suffix: '_out',  inputType: 'number' },
          { label: 'Taux rep.%', suffix: '_rate', inputType: 'number', max: 100 },
        ],
      },
      {
        title: 'Dossiers',
        type: 'fields',
        fields: [
          { id: 'annulations',    label: 'Annulations recues',                         inputType: 'number' },
          { id: 'elite_jessica',  label: 'Dont ELITE (vers Jessica)',                  inputType: 'number' },
          { id: 'leads_en',       label: 'Leads anglais non rappeles (vers Mitchell)', inputType: 'number' },
          { id: 'unsolicited',    label: 'Appels non sollicites',                      inputType: 'number' },
        ],
      },
      { title: 'Observations',         type: 'textarea', id: 'observations', required: true, placeholder: 'Resume des observations de la semaine (obligatoire)...' },
      { title: 'Notes additionnelles', type: 'textarea', id: 'notes',        optional: true, placeholder: 'Hamza peut ajouter tout ce qui est important...' },
    ],
    keyStats: d => {
      const total = (parseInt(d.hamza_in)||0) + (parseInt(d.lilia_in)||0) + (parseInt(d.sekou_in)||0);
      return [
        { label: 'Appels entrants', val: total },
        { label: 'Annulations',     val: d.annulations },
        { label: 'Leads EN',        val: d.leads_en },
      ];
    },
  },

  ventes: {
    requiredField: { id: 'rf_overview', label: 'Overview semaine' },
    sections: [
      {
        title: 'Appels',
        type: 'fields',
        fields: [
          { id: 'appels_1er', label: 'Appels 1ers (nouveaux leads)',                      inputType: 'number' },
          { id: 'appels_2e',  label: '2e appels (suivis)',                                inputType: 'number' },
          { id: 'appels_3e',  label: '3e appels+',                                       inputType: 'number' },
          { id: 'heures',     label: 'Heures travaillees', hint: '(max 20h payees)',      inputType: 'number', max: 168 },
        ],
      },
      {
        title: 'Inscriptions conclues',
        type: 'fields',
        fields: [
          { id: 'bsp',        label: 'BSP Gardiennage', inputType: 'number' },
          { id: 'secourisme', label: 'Secourisme',       inputType: 'number' },
          { id: 'elite',      label: 'Elite',            inputType: 'number' },
        ],
      },
      {
        title: 'GHL Compliance',
        type: 'radio',
        name: 'ghl',
        options: [
          { value: 'yes', label: 'Oui — tous les appels logges dans GHL' },
          { value: 'no',  label: 'Non' },
        ],
      },
      { title: 'Overview semaine',     type: 'textarea', id: 'overview', required: true, placeholder: 'Resume general de la semaine (obligatoire)...' },
      { title: 'Notes additionnelles', type: 'textarea', id: 'notes',    optional: true, placeholder: 'Notes additionnelles...' },
    ],
    keyStats: d => {
      const inscriptions = (parseInt(d.bsp)||0) + (parseInt(d.secourisme)||0) + (parseInt(d.elite)||0);
      return [
        { label: '1ers appels',  val: d.appels_1er },
        { label: 'Inscriptions', val: inscriptions },
        { label: 'Heures',       val: d.heures },
      ];
    },
  },

  recrutement: {
    requiredField: null,
    sections: [
      {
        title: 'Entrevues',
        type: 'fields',
        fields: [
          { id: 'entrevues',    label: 'Entrevues agents completees',          inputType: 'number' },
          { id: 'retenus',      label: 'Candidats retenus',                    inputType: 'number' },
          { id: 'refuses',      label: 'Refuses',                              inputType: 'number' },
          { id: 'appels_elite', label: 'Premiers appels Elite completes',      inputType: 'number' },
          { id: 'pipeline',     label: 'Pipeline candidats actifs (total)',    inputType: 'number' },
        ],
      },
      {
        title: 'Cohortes',
        type: 'fields',
        fields: [
          { id: 'cohortes', label: 'Cohortes terminees cette semaine', inputType: 'number' },
          { id: 'top5',     label: 'Top 5 recus des profs',            inputType: 'number' },
        ],
        append: {
          type: 'radio-inline',
          label: 'Dans les 48h?',
          name: 'top5_48h',
          options: [{ value: 'yes', label: 'Oui' }, { value: 'no', label: 'Non' }],
        },
      },
      {
        title: 'Marketing',
        type: 'fields',
        fields: [
          { id: 'demandes_alex', label: 'Demandes envoyees a Alex cette semaine', inputType: 'number' },
          { id: 'demandes_desc', label: 'Description', inputType: 'text', grow: true, placeholder: 'Description des demandes...' },
        ],
      },
      { title: 'Notes additionnelles', type: 'textarea', id: 'notes', optional: true, placeholder: 'Notes additionnelles...' },
    ],
    keyStats: d => [
      { label: 'Entrevues', val: d.entrevues },
      { label: 'Retenus',   val: d.retenus },
      { label: 'Pipeline',  val: d.pipeline },
    ],
  },

  admin: {
    requiredField: null,
    sections: [
      {
        title: 'Bureau',
        type: 'fields',
        fields: [
          { id: 'checklist_pascaline', label: 'Checklist Pascaline suivie?',  inputType: 'radio-inline', name: 'checklist_pascaline', options: [{value:'yes',label:'Oui'},{value:'no',label:'Non'}] },
          { id: 'checklist_salle',     label: 'Checklist salle apres cours?', inputType: 'radio-inline', name: 'checklist_salle',     options: [{value:'yes',label:'Oui'},{value:'no',label:'Non'}] },
          { id: 'nb_cours',            label: 'Nombre de cours',              inputType: 'number' },
        ],
      },
      {
        title: 'Commissions',
        type: 'fields',
        fields: [
          { id: 'commissions', label: 'Suivi commissions a jour?', inputType: 'radio-inline', name: 'commissions', options: [{value:'yes',label:'Oui'},{value:'no',label:'Non'}] },
        ],
      },
      {
        title: 'Leads anglais (recus de Hamza)',
        type: 'fields',
        fields: [
          { id: 'leads_recus',     label: 'Leads recus',            inputType: 'number' },
          { id: 'leads_contactes', label: 'Contactes dans 24h',     inputType: 'number' },
        ],
      },
      {
        title: 'Rapport mensuel',
        hint: '(si fin de mois)',
        type: 'textareas',
        fields: [
          { id: 'etat_bureau', label: 'Etat bureau',  placeholder: 'Etat general du bureau...' },
          { id: 'incidents',   label: 'Incidents',    placeholder: 'Incidents survenus...' },
          { id: 'besoins',     label: 'Besoins',      placeholder: 'Besoins identifies...' },
        ],
      },
      { title: 'Notes additionnelles', type: 'textarea', id: 'notes', optional: true, placeholder: 'Notes additionnelles...' },
    ],
    keyStats: d => [
      { label: 'Checklist Pascaline', val: d.checklist_pascaline === 'yes' ? 'Oui' : (d.checklist_pascaline === 'no' ? 'Non' : null) },
      { label: 'Leads recus',         val: d.leads_recus },
      { label: 'Contactes 24h',       val: d.leads_contactes },
    ],
  },

};

// ============================================================
// GENERIC RENDERERS — driven by RPT_SCHEMA
// ============================================================

/** Renders one section of a form based on its schema descriptor. */
function _rptRenderFormSection(s) {
  const titleHtml = `<div class="rpt-section-title">${s.title}${s.hint ? ` <span class="rpt-hint">${s.hint}</span>` : ''}${s.required ? ' <span class="rpt-required">*</span>' : ''}${s.optional ? ' <span class="rpt-optional">(optionnel)</span>' : ''}</div>`;

  // Agent table (SAC call volumes)
  if (s.type === 'agent-table') {
    const thead = '<tr><th>Agent</th>' + s.cols.map(c => `<th>${c.label}</th>`).join('') + '</tr>';
    const tbody = s.agents.map(agent => {
      const key = agent.toLowerCase();
      const cells = s.cols.map(c =>
        `<td><input class="rp-num" type="number" min="0"${c.max ? ` max="${c.max}"` : ''} id="rf_${key}${c.suffix}" placeholder="0"/></td>`
      ).join('');
      return `<tr><td>${agent}</td>${cells}</tr>`;
    }).join('');
    return titleHtml + `<table class="rp-table"><thead>${thead}</thead><tbody>${tbody}</tbody></table>`;
  }

  // Regular fields row
  if (s.type === 'fields') {
    const fieldsHtml = s.fields.map(f => _rptRenderFormField(f)).join('');
    const appendHtml = s.append ? _rptRenderAppend(s.append) : '';
    return titleHtml + `<div class="rpt-field-row">${fieldsHtml}</div>${appendHtml}`;
  }

  // Multiple textareas (admin monthly section)
  if (s.type === 'textareas') {
    const areas = s.fields.map(f =>
      `<label class="rpt-label" style="margin-top:8px;">${f.label}</label><textarea class="rp-textarea" id="rf_${f.id}" rows="2" placeholder="${f.placeholder || ''}"></textarea>`
    ).join('');
    return titleHtml + `<div>${areas}</div>`;
  }

  // Single textarea
  if (s.type === 'textarea') {
    return titleHtml + `<textarea class="rp-textarea" id="rf_${s.id}" rows="${s.required ? 4 : 3}" placeholder="${s.placeholder || ''}"></textarea>`;
  }

  // Standalone radio group
  if (s.type === 'radio') {
    const opts = s.options.map(o =>
      `<label class="rpt-radio-label"><input type="radio" name="rf_${s.name}" value="${o.value}"/> ${o.label}</label>`
    ).join('');
    return titleHtml + `<div class="rpt-radio-group">${opts}</div>`;
  }

  return '';
}

/** Renders a single field inside a fields row. */
function _rptRenderFormField(f) {
  const growClass = f.grow ? ' rpt-field-grow' : '';
  if (f.inputType === 'radio-inline') {
    const opts = f.options.map(o =>
      `<label class="rpt-radio-label"><input type="radio" name="rf_${f.name}" value="${o.value}"/> ${o.label}</label>`
    ).join('');
    return `<div class="rpt-field${growClass}"><label class="rpt-label">${f.label}</label><div class="rpt-radio-group rpt-radio-inline">${opts}</div></div>`;
  }
  if (f.inputType === 'text') {
    return `<div class="rpt-field${growClass}"><label class="rpt-label">${f.label}</label><input class="rpt-text-input" type="text" id="rf_${f.id}" placeholder="${f.placeholder || ''}"/></div>`;
  }
  // Default: number input
  return `<div class="rpt-field${growClass}"><label class="rpt-label">${f.label}${f.hint ? ` <span class="rpt-optional">${f.hint}</span>` : ''}</label><input class="rp-num" type="number" min="0"${f.max ? ` max="${f.max}"` : ''} id="rf_${f.id}" placeholder="0"/></div>`;
}

/** Renders an appended inline-radio below a fields row (e.g. "Dans les 48h?"). */
function _rptRenderAppend(a) {
  if (a.type === 'radio-inline') {
    const opts = a.options.map(o =>
      `<label class="rpt-radio-label"><input type="radio" name="rf_${a.name}" value="${o.value}"/> ${o.label}</label>`
    ).join('');
    return `<div class="rpt-field-row"><div class="rpt-field"><label class="rpt-label">${a.label}</label><div class="rpt-radio-group rpt-radio-inline">${opts}</div></div></div>`;
  }
  return '';
}

/**
 * Collects all field values from the DOM for a given report type schema.
 * Returns a flat data object with all field IDs as keys.
 */
function _rptCollectSchema(schema) {
  const d = {};

  schema.sections.forEach(s => {
    if (s.type === 'agent-table') {
      s.agents.forEach(agent => {
        const key = agent.toLowerCase();
        s.cols.forEach(c => {
          d[`${key}${c.suffix}`] = rptNumEl(`rf_${key}${c.suffix}`);
        });
      });
    } else if (s.type === 'fields') {
      s.fields.forEach(f => {
        if (f.inputType === 'radio-inline') {
          d[f.id] = rptRadioVal(`rf_${f.name}`);
        } else if (f.inputType === 'text') {
          d[f.id] = rptValEl(`rf_${f.id}`);
        } else {
          d[f.id] = rptNumEl(`rf_${f.id}`);
        }
      });
      if (s.append && s.append.type === 'radio-inline') {
        d[s.append.name] = rptRadioVal(`rf_${s.append.name}`);
      }
    } else if (s.type === 'textareas') {
      s.fields.forEach(f => { d[f.id] = rptValEl(`rf_${f.id}`); });
    } else if (s.type === 'textarea') {
      d[s.id] = rptValEl(`rf_${s.id}`);
    } else if (s.type === 'radio') {
      d[s.name] = rptRadioVal(`rf_${s.name}`);
    }
  });

  return d;
}

/**
 * Renders the detail view of a saved report using schema-driven row/section helpers.
 * Falls back gracefully for unknown report types.
 */
function _rptDetailFromSchema(r) {
  const d = r.data || {};
  const schema = RPT_SCHEMA[r.report_type];
  if (!schema) return '<div class="rpt-empty">Donnees non disponibles.</div>';

  const row = (label, val) =>
    '<div class="rpt-detail-row"><span class="rpt-detail-key">' + label + '</span><span>' + (val != null && val !== '' ? val : '—') + '</span></div>';
  const section = (title, content) =>
    '<div class="rpt-detail-section"><div class="rpt-detail-section-title">' + title + '</div><div class="rpt-detail-text">' + esc(content) + '</div></div>';
  const yesNo = v => v === 'yes' ? 'Oui' : (v === 'no' ? 'Non' : '—');

  let html = '';

  schema.sections.forEach(s => {
    if (s.type === 'agent-table') {
      const thead = '<tr><th>Agent</th>' + s.cols.map(c => `<th>${c.label}</th>`).join('') + '</tr>';
      const tbody = s.agents.map(agent => {
        const key = agent.toLowerCase();
        const cells = s.cols.map(c => `<td>${d[`${key}${c.suffix}`] != null ? d[`${key}${c.suffix}`] : '—'}</td>`).join('');
        return `<tr><td>${agent}</td>${cells}</tr>`;
      }).join('');
      html += `<table class="rp-table" style="margin-top:8px;"><thead>${thead}</thead><tbody>${tbody}</tbody></table>`;
    } else if (s.type === 'fields') {
      s.fields.forEach(f => {
        if (f.inputType === 'radio-inline') {
          html += row(f.label, yesNo(d[f.id]));
        } else if (f.inputType === 'text') {
          html += row(f.label, d[f.id]);
        } else {
          html += row(f.label, d[f.id]);
        }
      });
      if (s.append && s.append.type === 'radio-inline') {
        html += row(s.append.label, yesNo(d[s.append.name]));
      }
    } else if (s.type === 'textareas') {
      s.fields.forEach(f => { if (d[f.id]) html += section(f.label, d[f.id]); });
    } else if (s.type === 'textarea') {
      if (d[s.id]) html += section(s.title, d[s.id]);
    } else if (s.type === 'radio') {
      html += row(s.title, yesNo(d[s.name]));
    }
  });

  return html || '<div class="rpt-empty">Donnees non disponibles.</div>';
}

// ============================================================
// HELPERS
// ============================================================

function rptPersonName(id) {
  if (id === 'vp') return VP.name;
  const p = data.find(x => x.id === id);
  return p ? p.name : id;
}

function rptPersonRole(id) {
  if (id === 'vp') return VP.role;
  const p = data.find(x => x.id === id);
  return p ? p.role : '';
}

function rptWeekLabel(weekStart, weekEnd) {
  if (!weekStart) return 'Semaine inconnue';
  const fmt = d => {
    const parts = d.split('-');
    const months = ['jan','fev','mar','avr','mai','jun','jul','aou','sep','oct','nov','dec'];
    return parseInt(parts[2]) + ' ' + months[parseInt(parts[1])-1];
  };
  if (weekEnd) return 'Semaine du ' + fmt(weekStart) + ' au ' + fmt(weekEnd);
  return 'Semaine du ' + fmt(weekStart);
}

function rptCurrentWeek() {
  const today = new Date();
  const dow = today.getDay();
  const diff = (dow === 0) ? -6 : 1 - dow;
  const mon = new Date(today); mon.setDate(today.getDate() + diff);
  const sun = new Date(mon);   sun.setDate(mon.getDate() + 6);
  const fmt = d => d.toISOString().slice(0,10);
  return { start: fmt(mon), end: fmt(sun) };
}

function rptValEl(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}
function rptNumEl(id) {
  const v = rptValEl(id);
  return v === '' ? null : parseInt(v);
}
function rptRadioVal(name) {
  const el = document.querySelector('input[name="' + name + '"]:checked');
  return el ? el.value : null;
}

// ============================================================
// KEY STATS — driven by schema
// ============================================================

function rptKeyStats(reportType, reportData) {
  const schema = RPT_SCHEMA[reportType];
  if (!schema || !schema.keyStats) return '';
  const stats = schema.keyStats(reportData || {});
  return stats.map(s =>
    '<span class="rpt-stat-chip"><span class="rpt-stat-val">' + (s.val != null ? s.val : '—') + '</span><span class="rpt-stat-key">' + s.label + '</span></span>'
  ).join('');
}

// ============================================================
// FORM BUILDER — generic, driven by schema
// ============================================================

function rptBuildForm(personId) {
  const meta = REPORT_PEOPLE[personId];
  if (!meta) return '<div class="rpt-empty">Gabarit non defini.</div>';
  const schema = RPT_SCHEMA[meta.type];
  if (!schema) return '<div class="rpt-empty">Schema non defini pour ce type.</div>';

  const week = rptCurrentWeek();
  const body = schema.sections.map(s => _rptRenderFormSection(s)).join('');

  return `
    <div class="rpt-form" id="rpt-form-wrap">
      <div class="rpt-form-header">
        <span class="rpt-form-title">Nouveau rapport — ` + esc(rptPersonName(personId)) + `</span>
        <button class="btn" onclick="rptCancelForm()">Annuler</button>
      </div>
      <div class="rpt-week-row">
        <div class="rpt-field">
          <label class="rpt-label">Debut de semaine</label>
          <input type="date" class="rpt-date-input" id="rf_week_start" value="` + week.start + `"/>
        </div>
        <div class="rpt-field">
          <label class="rpt-label">Fin de semaine</label>
          <input type="date" class="rpt-date-input" id="rf_week_end" value="` + week.end + `"/>
        </div>
      </div>
      ` + body + `
      <div class="rpt-form-actions">
        <button class="btn primary" onclick="rptSubmit('` + personId + `')">Soumettre le rapport</button>
        <button class="btn" onclick="rptCancelForm()">Annuler</button>
      </div>
    </div>
  `;
}

// ============================================================
// COLLECT — generic, driven by schema
// ============================================================

function rptCollectForm(personId) {
  const meta = REPORT_PEOPLE[personId];
  const schema = RPT_SCHEMA[meta.type];
  const weekStart = rptValEl('rf_week_start');
  const weekEnd   = rptValEl('rf_week_end');
  if (!weekStart) { alert('Veuillez choisir un debut de semaine.'); return null; }

  // Required field validation
  if (schema.requiredField) {
    const val = rptValEl('rf_' + schema.requiredField.id);
    if (!val) { alert('Le champ "' + schema.requiredField.label + '" est obligatoire.'); return null; }
  }

  const formData = _rptCollectSchema(schema);

  return {
    person_id:   personId,
    week_start:  weekStart,
    week_end:    weekEnd || null,
    report_type: meta.type,
    data:        formData,
    notes:       formData.notes || null,
  };
}

// ============================================================
// DETAIL HTML — generic, driven by schema
// ============================================================

function rptDetailHTML(r) {
  return _rptDetailFromSchema(r);
}

// ============================================================
// SUBMIT & DELETE
// ============================================================

async function rptSubmit(personId) {
  const payload = rptCollectForm(personId);
  if (!payload) return;
  const btn = document.querySelector('#rpt-form-wrap .btn.primary');
  if (btn) { btn.disabled = true; btn.textContent = 'Envoi...'; }
  try {
    await dbSaveReport(payload);
    _rptShowForm = false;
    await rptReloadAndRender(personId);
    showFlash('Rapport soumis avec succes');
  } catch(e) {
    console.error('rptSubmit error:', e);
    alert('Erreur lors de la sauvegarde: ' + (e.message || e));
    if (btn) { btn.disabled = false; btn.textContent = 'Soumettre le rapport'; }
  }
}

async function rptDelete(reportId) {
  if (!confirm('Supprimer ce rapport? Cette action est irreversible.')) return;
  try {
    await dbDeleteReport(reportId);
    await rptReloadAndRender(_rptSelectedId);
  } catch(e) {
    console.error('rptDelete error:', e);
    alert('Erreur lors de la suppression: ' + (e.message || e));
  }
}

// ============================================================
// CARD & SIDEBAR HTML
// ============================================================

function rptToggleExpand(reportId) {
  const body = document.getElementById('rpt-body-' + reportId);
  const btn  = document.getElementById('rpt-toggle-' + reportId);
  if (!body) return;
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  if (btn) btn.textContent = isOpen ? 'Voir details' : 'Reduire';
}

function rptCardHTML(r) {
  const submittedDate = r.created_at
    ? new Date(r.created_at).toLocaleDateString('fr-CA', {day:'numeric', month:'short', year:'numeric'})
    : '';
  const statsHtml = rptKeyStats(r.report_type, r.data || {});
  return `
    <div class="rpt-report-card">
      <div class="rpt-report-card-header">
        <div class="rpt-report-card-meta">
          <span class="rpt-report-week">${rptWeekLabel(r.week_start, r.week_end)}</span>
          ${submittedDate ? '<span class="rpt-report-submitted">Soumis le ' + submittedDate + '</span>' : ''}
        </div>
        <div class="rpt-report-card-stats">${statsHtml}</div>
        <div class="rpt-report-card-actions">
          <button class="btn" id="rpt-toggle-${r.id}" onclick="rptToggleExpand('${r.id}')">Voir details</button>
          <button class="btn danger" onclick="rptDelete('${r.id}')">Supprimer</button>
        </div>
      </div>
      <div class="rpt-report-card-body" id="rpt-body-${r.id}" style="display:none;">
        ${rptDetailHTML(r)}
      </div>
    </div>
  `;
}

function rptSidebarItem(pid, count) {
  const meta  = REPORT_PEOPLE[pid];
  const name  = rptPersonName(pid);
  const role  = rptPersonRole(pid);
  const col   = avatarColor(pid);
  const inits = initials(name);
  const active = (_rptSelectedId === pid);
  return `
    <div class="rpt-sidebar-item${active ? ' active' : ''}" onclick="rptSelectPerson('${pid}')">
      <div class="tk-avatar" style="background:${col};width:34px;height:34px;font-size:11px;flex-shrink:0;">${inits}</div>
      <div class="rpt-sidebar-info">
        <div class="rpt-sidebar-name">${esc(name)}</div>
        <div class="rpt-sidebar-role">${esc(meta.label)}${role ? ' — ' + esc(role) : ''}</div>
      </div>
      <span class="rpt-sidebar-badge" id="rpt-sbadge-${pid}">${count}</span>
    </div>
  `;
}

// ============================================================
// RELOAD & RENDER
// ============================================================

async function rptReloadAndRender(personId) {
  _rptSelectedId = personId;
  _rptShowForm = false;
  const mainArea = document.getElementById('rpt-main-area');
  if (!mainArea) { render(); return; }
  mainArea.innerHTML = '<div class="rpt-loading">Chargement...</div>';
  try {
    const reports = await dbGetReports(personId);
    const badge = document.getElementById('rpt-sbadge-' + personId);
    if (badge) badge.textContent = reports.length;
    mainArea.innerHTML = rptBuildMainArea(personId, reports);
  } catch(e) {
    console.error('rptReloadAndRender error:', e);
    mainArea.innerHTML = '<div class="rpt-empty">Erreur de chargement: ' + esc(e.message || String(e)) + '</div>';
  }
}

function rptBuildMainArea(personId, reports) {
  const meta = REPORT_PEOPLE[personId];
  const name = rptPersonName(personId);
  const col  = avatarColor(personId);

  const reportsHtml = reports.length
    ? reports.map(r => rptCardHTML(r)).join('')
    : '<div class="rpt-empty">Aucun rapport soumis pour cette personne.</div>';

  const formHtml = _rptShowForm ? rptBuildForm(personId) : '';

  return `
    <div class="rpt-main-person-header">
      <div class="tk-avatar" style="background:${col};width:40px;height:40px;font-size:14px;flex-shrink:0;">${initials(name)}</div>
      <div style="flex:1;min-width:0;">
        <div class="rpt-main-person-name">${esc(name)}</div>
        <div class="rpt-main-person-label">${esc(meta.label)}${rptPersonRole(personId) ? ' — ' + esc(rptPersonRole(personId)) : ''}</div>
      </div>
      ${!_rptShowForm ? '<button class="btn primary" onclick="rptOpenForm(\'' + personId + '\')">+ Nouveau rapport</button>' : ''}
    </div>
    ${formHtml}
    <div class="rpt-reports-list">
      ${reportsHtml}
    </div>
  `;
}

function rptSelectPerson(personId) {
  _rptSelectedId = personId;
  _rptShowForm = false;
  document.querySelectorAll('.rpt-sidebar-item').forEach(el => {
    el.classList.toggle('active', el.getAttribute('onclick') === "rptSelectPerson('" + personId + "')");
  });
  const ctrlBtn = document.getElementById('rpt-ctrl-new-btn');
  if (ctrlBtn) {
    ctrlBtn.style.display = '';
    ctrlBtn.setAttribute('onclick', "rptOpenForm('" + personId + "')");
  }
  const mainArea = document.getElementById('rpt-main-area');
  if (!mainArea) return;
  mainArea.innerHTML = '<div class="rpt-loading">Chargement...</div>';
  dbGetReports(personId).then(reports => {
    mainArea.innerHTML = rptBuildMainArea(personId, reports);
  }).catch(e => {
    mainArea.innerHTML = '<div class="rpt-empty">Erreur: ' + esc(e.message || String(e)) + '</div>';
  });
}

function rptOpenForm(personId) {
  _rptShowForm = true;
  const mainArea = document.getElementById('rpt-main-area');
  if (!mainArea) return;
  dbGetReports(personId).then(reports => {
    mainArea.innerHTML = rptBuildMainArea(personId, reports);
    const form = document.getElementById('rpt-form-wrap');
    if (form) form.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }).catch(e => {
    mainArea.innerHTML = '<div class="rpt-empty">Erreur: ' + esc(e.message || String(e)) + '</div>';
  });
}

function rptCancelForm() {
  _rptShowForm = false;
  if (!_rptSelectedId) return;
  const mainArea = document.getElementById('rpt-main-area');
  if (!mainArea) return;
  dbGetReports(_rptSelectedId).then(reports => {
    mainArea.innerHTML = rptBuildMainArea(_rptSelectedId, reports);
  }).catch(e => {
    mainArea.innerHTML = '<div class="rpt-empty">Erreur: ' + esc(e.message || String(e)) + '</div>';
  });
}

function rptFilterSelect(val) {
  _rptSelectedId = val || null;
  _rptShowForm = false;
  render();
}

// ============================================================
// MAIN RENDER ENTRY POINT
// ============================================================

async function renderReports(ct, cl) {
  cl.innerHTML = `
    <select onchange="rptFilterSelect(this.value)" id="rpt-filter-select">
      <option value="">— Filtrer par personne —</option>
      ${Object.keys(REPORT_PEOPLE).map(pid => {
        const name = rptPersonName(pid);
        const meta = REPORT_PEOPLE[pid];
        return '<option value="' + pid + '"' + (_rptSelectedId === pid ? ' selected' : '') + '>' + esc(name) + ' (' + esc(meta.label) + ')</option>';
      }).join('')}
    </select>
    <button class="btn primary" id="rpt-ctrl-new-btn" style="${_rptSelectedId ? '' : 'display:none;'}" onclick="rptOpenForm('${_rptSelectedId || ''}')">+ Nouveau rapport</button>
  `;

  let countsByPerson = {};
  Object.keys(REPORT_PEOPLE).forEach(pid => { countsByPerson[pid] = 0; });
  try {
    const all = await dbGetReports(null);
    all.forEach(r => {
      if (countsByPerson.hasOwnProperty(r.person_id)) countsByPerson[r.person_id]++;
    });
  } catch(e) {
    console.error('renderReports load error:', e);
  }

  const sidebarHtml = Object.keys(REPORT_PEOPLE)
    .map(pid => rptSidebarItem(pid, countsByPerson[pid]))
    .join('');

  let mainHtml = '<div class="rpt-empty rpt-empty-select"><span>Selectionnez une personne dans la liste pour voir ses rapports.</span></div>';
  if (_rptSelectedId) {
    try {
      const reports = await dbGetReports(_rptSelectedId);
      mainHtml = rptBuildMainArea(_rptSelectedId, reports);
    } catch(e) {
      mainHtml = '<div class="rpt-empty">Erreur: ' + esc(e.message || String(e)) + '</div>';
    }
  }

  ct.innerHTML = `
    <div class="rpt-layout">
      <div class="rpt-sidebar">
        <div class="rpt-sidebar-title">Personnes</div>
        ${sidebarHtml}
      </div>
      <div class="rpt-main" id="rpt-main-area">
        ${mainHtml}
      </div>
    </div>
  `;
}

// ---- Legacy: keep openWeeklyReport for tasks.js compatibility ----
function openWeeklyReport(pid) {
  _rptSelectedId = pid;
  _rptShowForm = false;
  currentView = 'reports';
  document.querySelectorAll('.vtab').forEach(b => {
    const matches = b.getAttribute('onclick') && b.getAttribute('onclick').includes("'reports'");
    b.classList.toggle('active', matches);
  });
  render();
}
