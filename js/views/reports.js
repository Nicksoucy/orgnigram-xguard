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

  ventes_drone: {
    requiredField: { id: 'rf_overview', label: 'Overview semaine' },
    sections: [
      {
        title: 'Appels Drone',
        type: 'fields',
        fields: [
          { id: 'drone_1er',   label: 'Appels 1ers (nouveaux leads drone)',    inputType: 'number' },
          { id: 'drone_2e',    label: '2e appels drone (suivis)',              inputType: 'number' },
          { id: 'drone_3e',    label: '3e appels+ drone',                     inputType: 'number' },
        ],
      },
      {
        title: 'Appels Elite',
        type: 'fields',
        fields: [
          { id: 'elite_1er',   label: 'Appels 1ers Elite',                    inputType: 'number' },
          { id: 'elite_2e',    label: '2e appels Elite (suivis)',              inputType: 'number' },
        ],
      },
      {
        title: 'Resultats',
        type: 'fields',
        fields: [
          { id: 'ententes_drone', label: 'Ententes de paiement drone',        inputType: 'number' },
          { id: 'ententes_elite', label: 'Ententes de paiement Elite',        inputType: 'number' },
          { id: 'closed_drone',   label: 'Ventes fermees drone',              inputType: 'number' },
          { id: 'closed_elite',   label: 'Ventes fermees Elite',              inputType: 'number' },
          { id: 'heures',         label: 'Heures travaillees',                inputType: 'number', max: 168 },
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
      const droneAppels = (parseInt(d.drone_1er)||0) + (parseInt(d.drone_2e)||0) + (parseInt(d.drone_3e)||0);
      const eliteAppels = (parseInt(d.elite_1er)||0) + (parseInt(d.elite_2e)||0);
      const totalClosed = (parseInt(d.closed_drone)||0) + (parseInt(d.closed_elite)||0);
      return [
        { label: 'Appels drone',  val: droneAppels },
        { label: 'Appels elite',  val: eliteAppels },
        { label: 'Ventes',        val: totalClosed },
        { label: 'Heures',        val: d.heures },
      ];
    },
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
    mainArea.innerHTML = await rptBuildMainArea(personId, reports);
  } catch(e) {
    console.error('rptReloadAndRender error:', e);
    mainArea.innerHTML = '<div class="rpt-empty">Erreur de chargement: ' + esc(e.message || String(e)) + '</div>';
  }
}

async function rptBuildMainArea(personId, reports) {
  const meta = REPORT_PEOPLE[personId];
  const name = rptPersonName(personId);
  const col  = avatarColor(personId);

  // Coaching section (Heidys, Domingos) — shown above manual reports
  const coachingHtml = await rptBuildCoachingSection(personId);

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
    ${coachingHtml}
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
  dbGetReports(personId).then(async reports => {
    mainArea.innerHTML = await rptBuildMainArea(personId, reports);
  }).catch(e => {
    mainArea.innerHTML = '<div class="rpt-empty">Erreur: ' + esc(e.message || String(e)) + '</div>';
  });
}

function rptOpenForm(personId) {
  _rptShowForm = true;
  const mainArea = document.getElementById('rpt-main-area');
  if (!mainArea) return;
  dbGetReports(personId).then(async reports => {
    mainArea.innerHTML = await rptBuildMainArea(personId, reports);
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
  dbGetReports(_rptSelectedId).then(async reports => {
    mainArea.innerHTML = await rptBuildMainArea(_rptSelectedId, reports);
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
      mainHtml = await rptBuildMainArea(_rptSelectedId, reports);
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

// ============================================================
// COACHING VIEW — automated coaching data from Nitro
// Shown above manual reports for agents with coaching data.
// ============================================================

const COACHING_PEOPLE = ['v1', 't11'];

const COACHING_DIMENSIONS = [
  { key: 'intro',         label: 'Introduction',      icon: '👋' },
  { key: 'qualification', label: 'Qualification',      icon: '🎯' },
  { key: 'objections',    label: 'Gestion objections', icon: '🛡️' },
  { key: 'closing',       label: 'Closing',            icon: '🤝' },
  { key: 'empathy',       label: 'Empathie',           icon: '💬' },
  { key: 'energy',        label: 'Energie',            icon: '⚡' },
  { key: 'duration',      label: 'Duree appels',       icon: '⏱️' },
  { key: 'engagement',    label: 'Engagement',         icon: '🔥' },
];

// ── Coaching helpers ──

function _coachingScoreColor(score) {
  if (score == null) return 'var(--td)';
  if (score >= 8)   return 'var(--g)';
  if (score >= 6)   return 'var(--y)';
  if (score >= 4)   return 'var(--a)';
  return 'var(--r)';
}

function _coachingDelta(val) {
  if (val == null || val === 0) return '';
  const sign = val > 0 ? '+' : '';
  const color = val > 0 ? 'var(--g)' : 'var(--r)';
  return ' <span style="color:' + color + ';font-size:11px;font-weight:600;">' + sign + val.toFixed(1) + '</span>';
}

function _coachingProgressBar(pct, label) {
  const clampPct = Math.min(100, Math.max(0, pct || 0));
  const barColor = clampPct >= 100 ? 'var(--g)' : 'linear-gradient(90deg, var(--g), var(--cy))';
  return `<div style="margin:12px 0;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
      <span style="font-size:13px;color:var(--t);">${esc(label)}</span>
      <span style="font-size:14px;font-weight:600;color:${clampPct >= 100 ? 'var(--g)' : 'var(--cy)'};">${clampPct.toFixed(1)}%</span>
    </div>
    <div style="height:8px;background:var(--sh);border-radius:4px;overflow:hidden;">
      <div style="height:100%;width:${clampPct}%;background:${barColor};border-radius:4px;transition:width 0.5s;"></div>
    </div>
  </div>`;
}

function _coachingScoreCard(dim, score, delta, rankBadge) {
  const color = _coachingScoreColor(score);
  const badge = rankBadge ? '<div style="position:absolute;top:-6px;right:-6px;background:var(--r);color:#fff;font-size:9px;font-weight:700;width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;">' + rankBadge + '</div>' : '';
  return `<div style="position:relative;background:color-mix(in srgb, ${color} 6%, var(--s));border:1px solid var(--b);border-radius:10px;padding:12px 8px;text-align:center;min-width:90px;">
    ${badge}
    <div style="font-size:16px;margin-bottom:2px;">${dim.icon}</div>
    <div style="font-size:24px;font-weight:700;color:${color};line-height:1.2;">${score != null ? score.toFixed(1) : '—'}${_coachingDelta(delta)}</div>
    <div style="font-size:11px;color:var(--td);margin-top:4px;">${dim.label}</div>
  </div>`;
}

function _dimLabel(key) {
  const dim = COACHING_DIMENSIONS.find(d => d.key === key);
  return dim ? dim.icon + ' ' + dim.label : key;
}

// ── Objection coaching tips (mapped per objection text) ──
const OBJECTION_TIPS = {
  "C'est trop cher": "Recadrer vers la valeur: 'C'est un investissement — le BSP ouvre la porte a des emplois a 25$+/h'",
  "Pas le budget": "Proposer le plan de paiement ou les subventions disponibles",
  "Question sur le prix": "Ne pas donner le prix tout de suite — qualifier d'abord, puis presenter la valeur",
  "Je vais reflechir": "Creer l'urgence: 'Les places sont limitees, la prochaine cohorte est dans X jours'",
  "Pas le temps": "Offrir les horaires flexibles (soir/fin de semaine) et la duree courte de la formation",
  "Pas interesse": "Creuser: 'Qu'est-ce qui vous avait pousse a nous contacter au depart?'",
  "Pas le bon moment": "Ancrer une date: 'Quand serait le bon moment? On peut vous reserver une place'",
  "Doit consulter quelqu'un": "Proposer un appel a 3: 'On peut faire un appel ensemble avec votre...'",
  "Envoyez-moi de l'info": "Accepter mais fixer un rappel: 'Je vous envoie ca — on se reparle jeudi pour en discuter?'",
  "Quand est la prochaine cohorte": "Signal d'interet! Donner la date et enchainer: 'Il reste X places, je peux vous inscrire?'",
  "Est-ce reconnu/accredite": "Rassurer avec les accreditations BSP et confirmer la validite legale",
  "Rappeler plus tard": "Fixer un RDV precis: 'Parfait — mardi a 14h ca vous va?'",
  "Je ne suis pas decideur": "Identifier le decideur: 'Qui serait la bonne personne? Je peux l'appeler directement'",
  "J'ai deja un fournisseur": "Differenciateur: 'Qu'est-ce qui vous plait chez eux? On offre X en plus...'",
};

// ── Period filter state ──
let _coachingPeriod = '1sem'; // '1sem', '2sem', '1mois', '3mois', 'tout'

// ── Aggregate multiple coaching reports into one view ──
function _coachingAggregate(reports) {
  if (!reports.length) return null;
  if (reports.length === 1) return reports[0];

  const avgScores = {};
  COACHING_DIMENSIONS.forEach(dim => {
    const vals = reports.map(r => (r.scores || {})[dim.key]).filter(v => v != null);
    avgScores[dim.key] = vals.length ? vals.reduce((a,b) => a+b, 0) / vals.length : null;
  });

  // Merge objections across all reports
  const objMap = {};
  reports.forEach(r => {
    (r.top_objections || []).forEach(o => {
      const obj = typeof o === 'string' ? { text: o, count: 1 } : o;
      const key = obj.text || '';
      objMap[key] = (objMap[key] || 0) + (obj.count || 1);
    });
  });
  const mergedObjections = Object.entries(objMap)
    .sort((a,b) => b[1] - a[1])
    .slice(0, 10)
    .map(([text, count]) => ({ text, count }));

  // Merge strengths/improvements from averaged scores
  const sorted = Object.entries(avgScores).filter(([,v]) => v != null).sort((a,b) => b[1] - a[1]);
  const strengths = sorted.slice(0, 3).map(([k]) => k);
  const improvements = sorted.slice(-3).reverse().map(([k]) => k);

  // Merge recommendations (deduplicate)
  const recsSet = new Set();
  reports.forEach(r => (r.recommendations || []).forEach(rec => {
    const txt = typeof rec === 'string' ? rec : (rec.text || '');
    if (txt) recsSet.add(txt);
  }));

  // Merge call breakdown
  const breakdown = {};
  reports.forEach(r => {
    Object.entries(r.call_breakdown || {}).forEach(([k, v]) => {
      breakdown[k] = (breakdown[k] || 0) + v;
    });
  });

  const totalCalls = reports.reduce((s, r) => s + (r.calls_analyzed || 0), 0);

  return {
    scores: avgScores,
    comparison: reports[0].comparison || {},
    top_objections: mergedObjections,
    strengths,
    improvements,
    recommendations: [...recsSet].slice(0, 5),
    call_breakdown: breakdown,
    calls_analyzed: totalCalls,
    week_start: reports[reports.length - 1].week_start,
    week_end: reports[0].week_end,
    raw_summary: null, // no raw summary for aggregate
  };
}

// ── Main coaching section builder ──
// ── Radar chart renderer (uses Chart.js) ──
let _radarChartInstance = null;
function _renderRadarChart(canvasId, scores, prevScores) {
  setTimeout(() => {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;
    if (_radarChartInstance) { _radarChartInstance.destroy(); _radarChartInstance = null; }
    const labels = COACHING_DIMENSIONS.map(d => d.label);
    const data = COACHING_DIMENSIONS.map(d => scores[d.key] != null ? scores[d.key] : 0);
    const prev = prevScores ? COACHING_DIMENSIONS.map(d => prevScores[d.key] != null ? prevScores[d.key] : 0) : null;

    const datasets = [{
      label: 'Score actuel',
      data: data,
      backgroundColor: 'rgba(251,146,60,0.15)',
      borderColor: 'rgba(251,146,60,0.8)',
      borderWidth: 2,
      pointBackgroundColor: 'rgba(251,146,60,1)',
      pointRadius: 4,
    }];
    if (prev) {
      datasets.push({
        label: 'Semaine prec.',
        data: prev,
        backgroundColor: 'rgba(148,163,184,0.08)',
        borderColor: 'rgba(148,163,184,0.4)',
        borderWidth: 1,
        borderDash: [4, 4],
        pointRadius: 2,
      });
    }
    // Benchmark line at 7
    datasets.push({
      label: 'Objectif (7)',
      data: Array(8).fill(7),
      backgroundColor: 'transparent',
      borderColor: 'rgba(52,211,153,0.25)',
      borderWidth: 1,
      borderDash: [2, 2],
      pointRadius: 0,
    });

    _radarChartInstance = new Chart(canvas, {
      type: 'radar',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            min: 0, max: 10,
            ticks: { stepSize: 2, font: { size: 10 }, color: '#6b7280', backdropColor: 'transparent' },
            grid: { color: 'rgba(148,163,184,0.15)' },
            pointLabels: { font: { size: 11, weight: '500' }, color: '#94a3b8' },
            angleLines: { color: 'rgba(148,163,184,0.1)' },
          },
        },
        plugins: {
          legend: { display: true, position: 'bottom', labels: { font: { size: 10 }, color: '#94a3b8', boxWidth: 12 } },
        },
      },
    });
  }, 50);
}

// ── Auto-coaching insights generator ──
function _generateCoachingInsights(allReports) {
  const insights = [];
  if (allReports.length < 1) return insights;

  const latest = allReports[0];
  const latestScores = latest.scores || {};
  const comp = latest.comparison || {};

  // 1. Biggest drop this week
  let biggestDrop = null;
  COACHING_DIMENSIONS.forEach(d => {
    const delta = comp[d.key];
    if (delta != null && delta < -0.5 && (!biggestDrop || delta < biggestDrop.delta)) {
      biggestDrop = { dim: d, delta, score: latestScores[d.key] };
    }
  });
  if (biggestDrop) {
    insights.push({
      type: 'drop',
      icon: '📉',
      title: biggestDrop.dim.icon + ' ' + biggestDrop.dim.label + ': ' + biggestDrop.delta.toFixed(1) + ' cette semaine',
      detail: 'Score actuel: ' + (biggestDrop.score != null ? biggestDrop.score.toFixed(1) : '?') + '/10. Focus sur cette dimension cette semaine.',
    });
  }

  // 2. Consistent weakness (below 5.0 for 3+ weeks)
  if (allReports.length >= 3) {
    COACHING_DIMENSIONS.forEach(d => {
      const last3 = allReports.slice(0, 3).map(r => (r.scores || {})[d.key]).filter(v => v != null);
      if (last3.length === 3 && last3.every(v => v < 5.0)) {
        const avg = (last3.reduce((a,b) => a+b, 0) / 3).toFixed(1);
        insights.push({
          type: 'weakness',
          icon: '🔴',
          title: d.icon + ' ' + d.label + ' en dessous de 5.0 depuis 3 semaines',
          detail: 'Moyenne: ' + avg + '/10. Priorite de coaching cette semaine.',
        });
      }
    });
  }

  // 3. Biggest improvement
  let biggestGain = null;
  COACHING_DIMENSIONS.forEach(d => {
    const delta = comp[d.key];
    if (delta != null && delta > 0.5 && (!biggestGain || delta > biggestGain.delta)) {
      biggestGain = { dim: d, delta, score: latestScores[d.key] };
    }
  });
  if (biggestGain) {
    insights.push({
      type: 'gain',
      icon: '🟢',
      title: biggestGain.dim.icon + ' ' + biggestGain.dim.label + ': +' + biggestGain.delta.toFixed(1) + ' cette semaine',
      detail: 'Bon progres! Score actuel: ' + (biggestGain.score != null ? biggestGain.score.toFixed(1) : '?') + '/10.',
    });
  }

  // 4. Improving streak (3+ weeks up)
  if (allReports.length >= 3) {
    COACHING_DIMENSIONS.forEach(d => {
      const last3 = allReports.slice(0, 3).map(r => (r.scores || {})[d.key]).filter(v => v != null);
      if (last3.length === 3 && last3[0] > last3[1] && last3[1] > last3[2]) {
        insights.push({
          type: 'streak',
          icon: '🔥',
          title: d.icon + ' ' + d.label + ' en progression depuis 3 semaines',
          detail: last3[2].toFixed(1) + ' → ' + last3[1].toFixed(1) + ' → ' + last3[0].toFixed(1) + '. Continuer!',
        });
      }
    });
  }

  return insights.slice(0, 4); // max 4 insights
}

// ── Loading skeleton HTML ──
function _coachingLoadingSkeleton() {
  return '<div style="margin-bottom:24px;">'
    + '<div class="coaching-skeleton coaching-skeleton-bar"></div>'
    + '<div style="display:flex;gap:6px;margin-bottom:12px;">' + '<div class="coaching-skeleton" style="width:90px;height:30px;border-radius:20px;"></div>'.repeat(5) + '</div>'
    + '<div class="coaching-skeleton coaching-skeleton-card"></div>'
    + '<div class="coaching-grid-2col" style="gap:12px;margin-bottom:12px;">'
    + '<div class="coaching-skeleton coaching-skeleton-radar"></div>'
    + '<div class="coaching-skeleton coaching-skeleton-card" style="height:300px;"></div>'
    + '</div></div>';
}

async function rptBuildCoachingSection(personId) {
  if (!COACHING_PEOPLE.includes(personId)) return '';

  let allReports = [];
  let coachingData = [];
  let nitroArr = [];
  let cronLogs = [];
  let allCalls = [];

  try {
    [allReports, coachingData, nitroArr, allCalls] = await Promise.all([
      dbGetCoachingReports(personId, 52),
      dbGetCoachingData(personId, 365),
      dbGetNitroStatus(personId),
      dbGetCalls(personId),
    ]);
    if (authIsAdmin()) cronLogs = await dbGetCronLogs(personId, 5);
  } catch(e) {
    console.error('rptBuildCoachingSection error:', e);
    return '<div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);border-radius:12px;padding:20px;text-align:center;">'
      + '<div style="font-size:20px;margin-bottom:8px;">❌</div>'
      + '<div style="font-weight:600;color:var(--r);margin-bottom:4px;">Erreur de chargement</div>'
      + '<div style="font-size:12px;color:var(--td);margin-bottom:12px;">' + esc(e.message || String(e)) + '</div>'
      + '<button onclick="render();" style="padding:8px 20px;border-radius:8px;border:1px solid var(--b);background:var(--s);color:var(--t);cursor:pointer;font-size:13px;">🔄 Reessayer</button>'
      + '</div>';
  }

  let html = '<div style="margin-bottom:24px;" id="coaching-section-' + personId + '">';

  // Inject coaching CSS (inline to avoid cache issues)
  html += '<style>'
    + '.coaching-grid-2col{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}'
    + '.coaching-grid-4col{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}'
    + '@media(max-width:768px){'
    + '.coaching-grid-2col{grid-template-columns:1fr!important}'
    + '.coaching-grid-4col{grid-template-columns:repeat(2,1fr)!important}'
    + '}'
    + '</style>';

  // ── Nitro progress ──
  const activeNitro = nitroArr.find(n => n.status === 'running');
  if (activeNitro) {
    html += '<div style="background:var(--s);border:1px solid var(--b);border-radius:10px;padding:16px;margin-bottom:16px;">';
    html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;"><span style="font-size:16px;">⚡</span><span style="font-weight:600;color:var(--t);">Transcription en cours</span>';
    if (activeNitro.gpu_active) html += '<span style="background:var(--g);color:#000;font-size:10px;padding:2px 6px;border-radius:4px;font-weight:600;">GPU</span>';
    html += '</div>';
    html += _coachingProgressBar(activeNitro.pct, activeNitro.done + ' / ' + activeNitro.total + ' fichiers');
    html += '</div>';
  }

  // ── Stats Summary Bar (from real calls data) ──
  const totalCalls = allCalls.length;
  const now = new Date();
  const thisWeekStart = new Date(now); thisWeekStart.setDate(now.getDate() - now.getDay() + 1); thisWeekStart.setHours(0,0,0,0);
  const callsThisWeek = allCalls.filter(c => new Date(c.call_time) >= thisWeekStart).length;
  const lastCallDate = allCalls.length ? allCalls[0].call_time : null;
  const lastCallLabel = lastCallDate ? new Date(lastCallDate).toLocaleDateString('fr-CA', { day:'numeric', month:'short' }) : '—';

  // Trend: this week vs last week
  const lastWeekStart = new Date(thisWeekStart); lastWeekStart.setDate(lastWeekStart.getDate() - 7);
  const callsLastWeek = allCalls.filter(c => { const d = new Date(c.call_time); return d >= lastWeekStart && d < thisWeekStart; }).length;
  let trendLabel = '';
  if (callsLastWeek > 0) {
    const pctChange = Math.round(((callsThisWeek - callsLastWeek) / callsLastWeek) * 100);
    if (pctChange > 0) trendLabel = '<span style="color:var(--g);">↑ +' + pctChange + '%</span>';
    else if (pctChange < 0) trendLabel = '<span style="color:var(--r);">↓ ' + pctChange + '%</span>';
    else trendLabel = '<span style="color:var(--td);">→ stable</span>';
  }

  html += '<div style="display:flex;gap:1px;margin-bottom:16px;border-radius:12px;overflow:hidden;">';
  const statBox = (icon, val, label) => '<div style="flex:1;background:var(--s);padding:14px 12px;text-align:center;"><div style="font-size:20px;font-weight:700;color:var(--t);">' + icon + ' ' + val + '</div><div style="font-size:11px;color:var(--td);margin-top:2px;">' + label + '</div></div>';
  html += statBox('📞', totalCalls, 'Appels transcrits');
  html += statBox('📊', callsThisWeek, 'Cette semaine');
  html += statBox('🔄', lastCallLabel, 'Dernier appel');
  if (trendLabel) html += '<div style="flex:1;background:var(--s);padding:14px 12px;text-align:center;"><div style="font-size:18px;font-weight:700;">' + trendLabel + '</div><div style="font-size:11px;color:var(--td);margin-top:2px;">vs sem. prec.</div></div>';
  html += '</div>';

  // ── Sync Health Warning ──
  if (cronLogs.length) {
    const lastCron = cronLogs[0];
    const lastCronDate = lastCron.started_at ? new Date(lastCron.started_at) : null;
    const hoursSince = lastCronDate ? (Date.now() - lastCronDate.getTime()) / (1000 * 60 * 60) : 999;

    if (hoursSince > 48) {
      html += '<div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:10px;padding:12px 16px;margin-bottom:16px;display:flex;align-items:center;gap:10px;">';
      html += '<span style="font-size:20px;">🚨</span>';
      html += '<div><div style="font-weight:600;color:var(--r);font-size:13px;">Sync manquant depuis ' + Math.round(hoursSince) + 'h</div>';
      html += '<div style="font-size:11px;color:var(--td);">Le dernier cron a tourne le ' + (lastCronDate ? lastCronDate.toLocaleDateString('fr-CA', {day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}) : '?') + '. Verifier que NITRO est allume et Tailscale connecte.</div>';
      html += '</div></div>';
    } else if (lastCron.status === 'error') {
      html += '<div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:10px;padding:12px 16px;margin-bottom:16px;display:flex;align-items:center;gap:10px;">';
      html += '<span style="font-size:20px;">❌</span>';
      html += '<div><div style="font-weight:600;color:var(--r);font-size:13px;">Dernier sync en erreur</div>';
      html += '<div style="font-size:11px;color:var(--td);">' + esc(lastCron.error_msg || 'Erreur inconnue') + '</div>';
      html += '</div></div>';
    } else if (lastCron.status === 'partial') {
      html += '<div style="background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.3);border-radius:10px;padding:12px 16px;margin-bottom:16px;display:flex;align-items:center;gap:10px;">';
      html += '<span style="font-size:20px;">⚠️</span>';
      html += '<div><div style="font-weight:600;color:var(--y);font-size:13px;">Sync partiel</div>';
      html += '<div style="font-size:11px;color:var(--td);">' + esc(lastCron.error_msg || 'Certains appels ont echoue') + '</div>';
      html += '</div></div>';
    }
  } else if (coachingData.length === 0) {
    html += '<div style="background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.3);border-radius:10px;padding:12px 16px;margin-bottom:16px;display:flex;align-items:center;gap:10px;">';
    html += '<span style="font-size:20px;">📡</span>';
    html += '<div><div style="font-weight:600;color:var(--y);font-size:13px;">Aucun sync detecte</div>';
    html += '<div style="font-size:11px;color:var(--td);">Le cron quotidien n\'a jamais tourne avec succes pour cette personne.</div>';
    html += '</div></div>';
  }

  // ── Period Filter Pills (with real call counts) ──
  const _daysAgo = (d) => { const dt = new Date(); dt.setDate(dt.getDate() - d); dt.setHours(0,0,0,0); return dt; };
  const periods = [
    { key: '1sem', label: 'Cette semaine', weeks: 1, since: thisWeekStart },
    { key: '2sem', label: '2 semaines', weeks: 2, since: _daysAgo(14) },
    { key: '1mois', label: '1 mois', weeks: 4, since: _daysAgo(30) },
    { key: '3mois', label: '3 mois', weeks: 13, since: _daysAgo(90) },
    { key: 'tout', label: 'Tout', weeks: 999, since: null },
  ];

  html += '<div style="display:flex;gap:6px;margin-bottom:16px;flex-wrap:wrap;">';
  periods.forEach(p => {
    const active = p.key === _coachingPeriod;
    const count = p.since ? allCalls.filter(c => new Date(c.call_time) >= p.since).length : allCalls.length;
    html += '<button onclick="_coachingPeriod=\'' + p.key + '\';render();" style="padding:6px 14px;border-radius:20px;border:1px solid ' + (active ? 'var(--a)' : 'var(--b)') + ';background:' + (active ? 'var(--a)' : 'var(--s)') + ';color:' + (active ? '#fff' : 'var(--td)') + ';font-size:12px;font-weight:' + (active ? '600' : '400') + ';cursor:pointer;">' + p.label + ' <span style="opacity:0.7;">(' + count + ')</span></button>';
  });
  html += '</div>';

  // ── Filter reports by selected period ──
  const periodConfig = periods.find(p => p.key === _coachingPeriod) || periods[0];
  const filteredReports = allReports.slice(0, periodConfig.weeks);
  const coaching = filteredReports.length ? _coachingAggregate(filteredReports) : null;

  // ── ROW 2: Auto-Coaching Insights ──
  const insights = _generateCoachingInsights(allReports);
  if (insights.length) {
    html += '<div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:16px;margin-bottom:16px;">';
    html += '<div style="font-weight:700;color:var(--t);margin-bottom:10px;font-size:14px;">🎯 Cette semaine en coaching</div>';
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;">';
    insights.forEach(ins => {
      const bgMap = { drop: 'rgba(239,68,68,0.06)', weakness: 'rgba(239,68,68,0.06)', gain: 'rgba(52,211,153,0.06)', streak: 'rgba(251,146,60,0.06)' };
      const borderMap = { drop: 'rgba(239,68,68,0.15)', weakness: 'rgba(239,68,68,0.15)', gain: 'rgba(52,211,153,0.15)', streak: 'rgba(251,146,60,0.15)' };
      html += '<div style="background:' + (bgMap[ins.type] || 'var(--sh)') + ';border:1px solid ' + (borderMap[ins.type] || 'var(--b)') + ';border-radius:10px;padding:12px;">';
      html += '<div style="font-size:13px;font-weight:600;color:var(--t);margin-bottom:4px;">' + ins.icon + ' ' + esc(ins.title) + '</div>';
      html += '<div style="font-size:11px;color:var(--td);line-height:1.4;">' + esc(ins.detail) + '</div>';
      html += '</div>';
    });
    html += '</div></div>';
  }

  if (coaching) {
    const scores = coaching.scores || {};
    const comp = coaching.comparison || {};

    // Determine weakest 3 for rank badges
    const ranked = COACHING_DIMENSIONS
      .map(d => ({ key: d.key, score: scores[d.key] }))
      .filter(d => d.score != null)
      .sort((a, b) => a.score - b.score);
    const weakest3 = ranked.slice(0, 3).map(d => d.key);

    // ── ROW 3: Radar Chart + Score Cards (side by side) ──
    const periodLabel = rptWeekLabel(coaching.week_start, coaching.week_end);
    html += '<div class="coaching-grid-2col" style="gap:16px;margin-bottom:16px;">';

    // LEFT: Radar Chart
    const radarId = 'radar-' + personId + '-' + Date.now();
    html += '<div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:16px;">';
    html += '<div style="font-weight:700;color:var(--t);margin-bottom:8px;font-size:14px;">🕸️ Profil de competences</div>';
    html += '<div style="height:280px;position:relative;"><canvas id="' + radarId + '"></canvas></div>';
    html += '</div>';

    // RIGHT: Global score + score cards
    html += '<div>';
    // Global score header
    html += '<div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:16px;margin-bottom:12px;display:flex;align-items:center;gap:16px;">';
    const allScoreVals = COACHING_DIMENSIONS.map(d => scores[d.key]).filter(v => v != null);
    if (allScoreVals.length) {
      const globalScore = allScoreVals.reduce((a,b) => a+b, 0) / allScoreVals.length;
      const globalDelta = comp.global != null ? comp.global : null;
      const pct = Math.round(globalScore * 10);
      const circumference = 2 * Math.PI * 38;
      const offset = circumference - (pct / 100) * circumference;
      const gColor = _coachingScoreColor(globalScore);
      html += '<div style="position:relative;width:80px;height:80px;flex-shrink:0;">';
      html += '<svg width="80" height="80" viewBox="0 0 80 80">';
      html += '<circle cx="40" cy="40" r="34" fill="none" stroke="var(--sh)" stroke-width="5"/>';
      html += '<circle cx="40" cy="40" r="34" fill="none" stroke="' + gColor + '" stroke-width="5" stroke-linecap="round" stroke-dasharray="' + (2*Math.PI*34).toFixed(1) + '" stroke-dashoffset="' + ((2*Math.PI*34) - (pct/100)*(2*Math.PI*34)).toFixed(1) + '" transform="rotate(-90 40 40)" style="transition:stroke-dashoffset 0.6s;"/>';
      html += '</svg>';
      html += '<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;">';
      html += '<div style="font-size:20px;font-weight:800;color:' + gColor + ';line-height:1;">' + globalScore.toFixed(1) + '</div>';
      html += '<div style="font-size:9px;color:var(--td);">/10</div>';
      html += '</div></div>';
      html += '<div>';
      html += '<div style="font-weight:700;color:var(--t);font-size:15px;">Score global' + _coachingDelta(globalDelta) + '</div>';
      html += '<div style="font-size:12px;color:var(--td);">' + periodLabel + ' &middot; ' + (coaching.calls_analyzed || 0) + ' appels</div>';
      html += '</div>';
    }
    html += '</div>';

    // Score grid (4x2)
    html += '<div class="coaching-grid-4col">';
    COACHING_DIMENSIONS.forEach(dim => {
      const score = scores[dim.key] != null ? scores[dim.key] : null;
      const delta = comp[dim.key] != null ? comp[dim.key] : null;
      const weakIdx = weakest3.indexOf(dim.key);
      const badge = weakIdx >= 0 ? (weakIdx + 1) : null;
      html += _coachingScoreCard(dim, score, delta, badge);
    });
    html += '</div>';
    html += '</div>'; // end right column
    html += '</div>'; // end grid row

    // Render radar chart after DOM is ready
    const prevScores = allReports.length >= 2 ? allReports[1].scores : null;
    _renderRadarChart(radarId, scores, prevScores);

    // ── ROW 4: Forces + Ameliorations ──
    const strengths = coaching.strengths || [];
    const improvements = coaching.improvements || [];
    if (strengths.length || improvements.length) {
      html += '<div class="coaching-grid-2col">';
      if (strengths.length) {
        html += '<div style="background:rgba(52,211,153,0.06);border:1px solid rgba(52,211,153,0.15);border-radius:12px;padding:16px;">';
        html += '<div style="font-weight:700;color:var(--g);margin-bottom:10px;font-size:14px;">✅ Forces</div>';
        strengths.forEach(s => { html += '<div style="font-size:13px;color:var(--t);padding:3px 0;">• ' + esc(_dimLabel(s)) + '</div>'; });
        html += '</div>';
      }
      if (improvements.length) {
        html += '<div style="background:rgba(251,191,36,0.06);border:1px solid rgba(251,191,36,0.15);border-radius:12px;padding:16px;">';
        html += '<div style="font-weight:700;color:var(--y);margin-bottom:10px;font-size:14px;">⚠️ A ameliorer</div>';
        improvements.forEach(s => { html += '<div style="font-size:13px;color:var(--t);padding:3px 0;">• ' + esc(_dimLabel(s)) + '</div>'; });
        html += '</div>';
      }
      html += '</div>';
    }

    // ── ROW 5: Objections + Recommendations side by side ──
    const objections = coaching.top_objections || [];
    const recs = coaching.recommendations || [];
    const breakdown = coaching.call_breakdown || {};
    const hasBreakdown = Object.keys(breakdown).length > 0;

    if (objections.length || recs.length) {
      html += '<div class="coaching-grid-2col">';

      // LEFT: Objections
      if (objections.length) {
        html += '<div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:16px;">';
        html += '<div style="font-weight:700;color:var(--t);margin-bottom:12px;font-size:14px;">🗣️ Objections frequentes</div>';
        objections.forEach(o => {
          const obj = typeof o === 'string' ? { text: o } : o;
          const count = obj.count || 0;
          const maxCount = objections[0] ? (typeof objections[0] === 'object' ? objections[0].count || 1 : 1) : 1;
          const pct = Math.round((count / maxCount) * 100);
          const tipKey = Object.keys(OBJECTION_TIPS).find(k => (obj.text || '').toLowerCase().includes(k.toLowerCase().substring(0, 10)));
          html += '<div style="padding:5px 0;border-bottom:1px solid var(--sh);">';
          html += '<div style="display:flex;align-items:center;gap:8px;">';
          html += '<div style="flex:1;font-size:12px;color:var(--t);font-weight:500;">' + esc(obj.text || obj) + '</div>';
          html += '<div style="min-width:80px;display:flex;align-items:center;gap:4px;">';
          html += '<div style="flex:1;height:3px;background:var(--sh);border-radius:2px;"><div style="height:100%;width:' + pct + '%;background:var(--a);border-radius:2px;"></div></div>';
          html += '<span style="font-size:10px;color:var(--td);min-width:20px;text-align:right;">' + count + 'x</span>';
          html += '</div></div>';
          if (tipKey && OBJECTION_TIPS[tipKey]) {
            html += '<div style="font-size:10px;color:var(--cy);margin-top:2px;padding-left:4px;">💡 ' + esc(OBJECTION_TIPS[tipKey]) + '</div>';
          }
          html += '</div>';
        });
        html += '</div>';
      }

      // RIGHT: Recommendations
      if (recs.length) {
        html += '<div style="background:rgba(96,165,250,0.05);border:1px solid rgba(96,165,250,0.15);border-radius:12px;padding:16px;">';
        html += '<div style="font-weight:700;color:var(--bl);margin-bottom:12px;font-size:14px;">💡 Recommandations</div>';
        recs.forEach((r, i) => {
          const txt = typeof r === 'string' ? r : (r.text || JSON.stringify(r));
          html += '<div style="display:flex;gap:8px;padding:5px 0;align-items:flex-start;">';
          html += '<div style="background:var(--bl);color:#fff;font-size:10px;font-weight:700;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;">' + (i + 1) + '</div>';
          html += '<div style="font-size:12px;color:var(--t);line-height:1.5;">' + esc(txt) + '</div>';
          html += '</div>';
        });
        html += '</div>';
      }
      html += '</div>';
    }

    // Call breakdown (Domingos only)
    if (hasBreakdown) {
      html += '<div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:16px;margin-bottom:16px;display:flex;gap:24px;justify-content:center;">';
      html += '<div style="font-weight:700;color:var(--t);font-size:14px;align-self:center;">📞 Repartition</div>';
      Object.entries(breakdown).forEach(([key, val]) => {
        const colors = { drone: 'var(--cy)', elite: 'var(--p)', autre: 'var(--td)' };
        html += '<div style="text-align:center;padding:4px 16px;">';
        html += '<div style="font-size:24px;font-weight:700;color:' + (colors[key] || 'var(--t)') + ';">' + val + '</div>';
        html += '<div style="font-size:11px;color:var(--td);text-transform:capitalize;">' + esc(key) + '</div>';
        html += '</div>';
      });
      html += '</div>';
    }

    // Raw summary (collapsible)
    if (coaching.raw_summary) {
      html += '<details style="margin-bottom:16px;">';
      html += '<summary style="cursor:pointer;font-weight:600;color:var(--td);font-size:12px;padding:8px 0;">📝 Resume complet</summary>';
      html += '<div style="margin-top:8px;font-size:12px;color:var(--t);line-height:1.6;padding:12px;background:var(--sh);border-radius:8px;white-space:pre-wrap;">' + esc(coaching.raw_summary) + '</div>';
      html += '</details>';
    }

  } else if (!activeNitro) {
    html += '<div class="rpt-empty" style="margin-bottom:16px;">Aucune donnee de coaching disponible. Les rapports seront generes chaque vendredi a 15h.</div>';
  }

  // ── Weekly volume chart ──
  if (coachingData.length > 1) {
    const sorted = coachingData.slice().sort((a, b) => a.sync_date.localeCompare(b.sync_date));
    const maxCalls = Math.max(...sorted.map(d => d.calls_transcribed || 0), 1);
    html += '<div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:16px;margin-bottom:16px;">';
    html += '<div style="font-weight:700;color:var(--t);margin-bottom:12px;font-size:14px;">📈 Volume d\'appels par semaine</div>';
    html += '<div style="display:flex;gap:4px;align-items:flex-end;height:100px;">';
    sorted.forEach(d => {
      const calls = d.calls_transcribed || 0;
      const pct = Math.max(2, Math.round((calls / maxCalls) * 100));
      const label = d.sync_date ? d.sync_date.substring(5) : '';
      html += '<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;">';
      html += '<div style="font-size:10px;font-weight:600;color:var(--t);">' + calls + '</div>';
      html += '<div style="width:100%;background:var(--sh);border-radius:4px;position:relative;height:80px;">';
      html += '<div style="position:absolute;bottom:0;width:100%;height:' + pct + '%;background:var(--a);border-radius:4px;transition:height 0.3s;"></div>';
      html += '</div>';
      html += '<div style="font-size:9px;color:var(--td);white-space:nowrap;">' + esc(label) + '</div>';
      html += '</div>';
    });
    html += '</div></div>';
  }

  // ── Score progression (all weeks trend table) ──
  if (allReports.length > 1) {
    const chronological = allReports.slice().reverse();
    html += '<div style="background:var(--s);border:1px solid var(--b);border-radius:12px;padding:16px;margin-bottom:16px;">';
    html += '<div style="font-weight:700;color:var(--t);margin-bottom:12px;font-size:14px;">📊 Progression des scores</div>';
    html += '<div style="overflow-x:auto;">';
    html += '<table style="width:100%;font-size:11px;border-collapse:collapse;">';
    html += '<tr><th style="text-align:left;color:var(--td);padding:4px 6px;border-bottom:1px solid var(--b);">Dimension</th>';
    chronological.forEach(r => {
      html += '<th style="text-align:center;color:var(--td);padding:4px 6px;border-bottom:1px solid var(--b);white-space:nowrap;">' + esc(r.week_start ? r.week_start.substring(5) : '') + '</th>';
    });
    html += '</tr>';
    COACHING_DIMENSIONS.forEach(dim => {
      html += '<tr>';
      html += '<td style="padding:4px 6px;color:var(--t);border-bottom:1px solid var(--b);">' + dim.icon + ' ' + esc(dim.label) + '</td>';
      chronological.forEach(r => {
        const val = (r.scores || {})[dim.key];
        const color = val != null ? _coachingScoreColor(val) : 'var(--td)';
        html += '<td style="text-align:center;padding:4px 6px;color:' + color + ';font-weight:600;border-bottom:1px solid var(--b);">' + (val != null ? val.toFixed(1) : '—') + '</td>';
      });
      html += '</tr>';
    });
    html += '<tr style="font-weight:700;"><td style="padding:4px 6px;color:var(--t);border-top:2px solid var(--b);">Global</td>';
    chronological.forEach(r => {
      const vals = Object.values(r.scores || {}).filter(v => typeof v === 'number');
      const g = vals.length ? vals.reduce((a,b) => a+b, 0) / vals.length : 0;
      html += '<td style="text-align:center;padding:4px 6px;color:' + _coachingScoreColor(g) + ';border-top:2px solid var(--b);">' + g.toFixed(1) + '</td>';
    });
    html += '</tr></table></div></div>';
  }

  // ── Cron logs (admin only) — with progress bars ──
  if (authIsAdmin() && cronLogs.length) {
    html += '<div style="background:var(--s);border:1px solid var(--b);border-radius:10px;padding:16px;margin-bottom:16px;">';
    html += '<div style="font-weight:600;color:var(--t);margin-bottom:10px;font-size:13px;">⚙️ Crons <span style="font-size:11px;color:var(--td);">(admin)</span></div>';
    cronLogs.forEach(log => {
      const isSuccess = log.status === 'success';
      const isError = log.status === 'error';
      const isPartial = log.status === 'partial';
      const isRunning = log.status === 'running';
      const statusIcon = isSuccess ? '✅' : isError ? '❌' : isPartial ? '⚠️' : '⏳';
      const date = log.started_at ? new Date(log.started_at).toLocaleDateString('fr-CA', { day:'numeric', month:'short', hour:'2-digit', minute:'2-digit' }) : '—';
      const dur = log.duration_sec != null ? log.duration_sec + 's' : '';
      const calls = log.calls_processed != null ? log.calls_processed : 0;
      const newT = log.transcripts_new || 0;

      // Progress calculation: success=100%, error/partial based on calls vs expected
      let pct = 100;
      let barColor = 'var(--g)';
      if (isError) { pct = calls > 0 ? Math.min(90, Math.round(calls / Math.max(calls + 5, 10) * 100)) : 0; barColor = 'var(--r)'; }
      else if (isPartial) { pct = 85; barColor = 'var(--y)'; }
      else if (isRunning) { pct = 50; barColor = 'var(--cy)'; }

      html += '<div style="padding:8px 0;border-bottom:1px solid var(--sh);">';

      // Row 1: status, date, type, stats
      html += '<div style="font-size:12px;color:var(--t);display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px;">';
      html += '<span>' + statusIcon + '</span>';
      html += '<span style="color:var(--td);min-width:110px;">' + esc(date) + '</span>';
      html += '<span style="text-transform:capitalize;font-weight:500;">' + esc(log.cron_type.replace('_',' ')) + '</span>';
      if (calls > 0) html += '<span style="color:var(--td);">' + calls + ' appels</span>';
      if (newT > 0) html += '<span style="color:var(--g);font-weight:600;">+' + newT + ' transcripts</span>';
      if (dur) html += '<span style="color:var(--td);">' + dur + '</span>';
      html += '</div>';

      // Row 2: progress bar
      html += '<div style="display:flex;align-items:center;gap:8px;">';
      html += '<div style="flex:1;height:6px;background:var(--sh);border-radius:3px;overflow:hidden;">';
      html += '<div style="height:100%;width:' + pct + '%;background:' + barColor + ';border-radius:3px;transition:width 0.3s;"></div>';
      html += '</div>';
      html += '<span style="font-size:10px;color:' + barColor + ';font-weight:600;min-width:32px;text-align:right;">' + pct + '%</span>';
      html += '</div>';

      // Row 3: error message if any
      if (log.error_msg && log.error_msg.startsWith('dates:')) {
        html += '<div style="font-size:10px;color:var(--cy);margin-top:4px;">📅 ' + esc(log.error_msg.substring(6)) + '</div>';
      } else if (log.error_msg) {
        html += '<div style="font-size:10px;color:var(--r);margin-top:4px;">❌ ' + esc(log.error_msg.substring(0, 120)) + '</div>';
      }

      html += '</div>';
    });
    html += '</div>';
  }

  html += '</div>';
  return html;
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
