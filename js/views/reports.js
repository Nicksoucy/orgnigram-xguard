// ==================== VIEW: RAPPORTS ====================
// REPORT_PEOPLE is defined in state.js:
// const REPORT_PEOPLE = {
//   'L3': {type:'sac', label:'SAC'},
//   'v1': {type:'ventes', label:'Ventes'},
//   'r1': {type:'recrutement', label:'Recrutement'},
//   'L2': {type:'admin', label:'Admin'}
// };

// ---- Helpers ----

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

// Default current week Mon-Sun
function rptCurrentWeek() {
  const today = new Date();
  const dow = today.getDay();
  const diff = (dow === 0) ? -6 : 1 - dow;
  const mon = new Date(today); mon.setDate(today.getDate() + diff);
  const sun = new Date(mon);   sun.setDate(mon.getDate() + 6);
  const fmt = d => d.toISOString().slice(0,10);
  return { start: fmt(mon), end: fmt(sun) };
}

// Key stats preview per report type
function rptKeyStats(reportType, reportData) {
  if (!reportData) return '';
  const d = reportData;
  const stat = (label, val) =>
    '<span class="rpt-stat-chip"><span class="rpt-stat-val">' + (val != null ? val : '—') + '</span><span class="rpt-stat-key">' + label + '</span></span>';

  if (reportType === 'sac') {
    const total = (parseInt(d.hamza_in)||0) + (parseInt(d.lilia_in)||0) + (parseInt(d.sekou_in)||0);
    return stat('Appels entrants', total) +
           stat('Annulations', d.annulations != null ? d.annulations : '—') +
           stat('Leads EN', d.leads_en != null ? d.leads_en : '—');
  }
  if (reportType === 'ventes') {
    const inscriptions = (parseInt(d.bsp)||0) + (parseInt(d.secourisme)||0) + (parseInt(d.elite)||0);
    return stat('1ers appels', d.appels_1er != null ? d.appels_1er : '—') +
           stat('Inscriptions', inscriptions) +
           stat('Heures', d.heures != null ? d.heures : '—');
  }
  if (reportType === 'recrutement') {
    return stat('Entrevues', d.entrevues != null ? d.entrevues : '—') +
           stat('Retenus', d.retenus != null ? d.retenus : '—') +
           stat('Pipeline', d.pipeline != null ? d.pipeline : '—');
  }
  if (reportType === 'admin') {
    return stat('Checklist Pascaline', d.checklist_pascaline === 'yes' ? 'Oui' : (d.checklist_pascaline === 'no' ? 'Non' : '—')) +
           stat('Leads recus', d.leads_recus != null ? d.leads_recus : '—') +
           stat('Contactes 24h', d.leads_contactes != null ? d.leads_contactes : '—');
  }
  return '';
}

// ---- Form builders per type ----

function rptFormSAC() {
  return `
    <div class="rpt-section-title">Volume d'appels <span class="rpt-hint">(tire de JustCall)</span></div>
    <table class="rp-table">
      <thead><tr><th>Agent</th><th>Entrants</th><th>Sortants</th><th>Taux rep.%</th></tr></thead>
      <tbody>
        <tr>
          <td>Hamza</td>
          <td><input class="rp-num" type="number" min="0" id="rf_hamza_in" placeholder="0"/></td>
          <td><input class="rp-num" type="number" min="0" id="rf_hamza_out" placeholder="0"/></td>
          <td><input class="rp-num" type="number" min="0" max="100" id="rf_hamza_rate" placeholder="0"/></td>
        </tr>
        <tr>
          <td>Lilia</td>
          <td><input class="rp-num" type="number" min="0" id="rf_lilia_in" placeholder="0"/></td>
          <td><input class="rp-num" type="number" min="0" id="rf_lilia_out" placeholder="0"/></td>
          <td><input class="rp-num" type="number" min="0" max="100" id="rf_lilia_rate" placeholder="0"/></td>
        </tr>
        <tr>
          <td>Sekou</td>
          <td><input class="rp-num" type="number" min="0" id="rf_sekou_in" placeholder="0"/></td>
          <td><input class="rp-num" type="number" min="0" id="rf_sekou_out" placeholder="0"/></td>
          <td><input class="rp-num" type="number" min="0" max="100" id="rf_sekou_rate" placeholder="0"/></td>
        </tr>
      </tbody>
    </table>

    <div class="rpt-section-title">Dossiers</div>
    <div class="rpt-field-row">
      <div class="rpt-field">
        <label class="rpt-label">Annulations recues</label>
        <input class="rp-num" type="number" min="0" id="rf_annulations" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Dont ELITE (vers Jessica)</label>
        <input class="rp-num" type="number" min="0" id="rf_elite_jessica" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Leads anglais non rappeles (vers Mitchell)</label>
        <input class="rp-num" type="number" min="0" id="rf_leads_en" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Appels non sollicites</label>
        <input class="rp-num" type="number" min="0" id="rf_unsolicited" placeholder="0"/>
      </div>
    </div>

    <div class="rpt-section-title">Observations <span class="rpt-required">*</span></div>
    <textarea class="rp-textarea" id="rf_observations" rows="4" placeholder="Resume des observations de la semaine (obligatoire)..."></textarea>

    <div class="rpt-section-title">Notes additionnelles <span class="rpt-optional">(optionnel)</span></div>
    <textarea class="rp-textarea" id="rf_notes" rows="3" placeholder="Hamza peut ajouter tout ce qui est important..."></textarea>
  `;
}

function rptFormVentes() {
  return `
    <div class="rpt-section-title">Appels</div>
    <div class="rpt-field-row">
      <div class="rpt-field">
        <label class="rpt-label">Appels 1ers (nouveaux leads)</label>
        <input class="rp-num" type="number" min="0" id="rf_appels_1er" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">2e appels (suivis)</label>
        <input class="rp-num" type="number" min="0" id="rf_appels_2e" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">3e appels+</label>
        <input class="rp-num" type="number" min="0" id="rf_appels_3e" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Heures travaillees <span class="rpt-optional">(max 20h payees)</span></label>
        <input class="rp-num" type="number" min="0" max="168" id="rf_heures" placeholder="0"/>
      </div>
    </div>

    <div class="rpt-section-title">Inscriptions conclues</div>
    <div class="rpt-field-row">
      <div class="rpt-field">
        <label class="rpt-label">BSP Gardiennage</label>
        <input class="rp-num" type="number" min="0" id="rf_bsp" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Secourisme</label>
        <input class="rp-num" type="number" min="0" id="rf_secourisme" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Elite</label>
        <input class="rp-num" type="number" min="0" id="rf_elite" placeholder="0"/>
      </div>
    </div>

    <div class="rpt-section-title">GHL Compliance</div>
    <div class="rpt-radio-group">
      <label class="rpt-radio-label"><input type="radio" name="rf_ghl" value="yes"/> Oui — tous les appels logges dans GHL</label>
      <label class="rpt-radio-label"><input type="radio" name="rf_ghl" value="no"/> Non</label>
    </div>

    <div class="rpt-section-title">Overview semaine <span class="rpt-required">*</span></div>
    <textarea class="rp-textarea" id="rf_overview" rows="4" placeholder="Resume general de la semaine (obligatoire)..."></textarea>

    <div class="rpt-section-title">Notes additionnelles <span class="rpt-optional">(optionnel)</span></div>
    <textarea class="rp-textarea" id="rf_notes" rows="3" placeholder="Notes additionnelles..."></textarea>
  `;
}

function rptFormRecrutement() {
  return `
    <div class="rpt-section-title">Entrevues</div>
    <div class="rpt-field-row">
      <div class="rpt-field">
        <label class="rpt-label">Entrevues agents completees</label>
        <input class="rp-num" type="number" min="0" id="rf_entrevues" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Candidats retenus</label>
        <input class="rp-num" type="number" min="0" id="rf_retenus" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Refuses</label>
        <input class="rp-num" type="number" min="0" id="rf_refuses" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Premiers appels Elite completes</label>
        <input class="rp-num" type="number" min="0" id="rf_appels_elite" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Pipeline candidats actifs (total)</label>
        <input class="rp-num" type="number" min="0" id="rf_pipeline" placeholder="0"/>
      </div>
    </div>

    <div class="rpt-section-title">Cohortes</div>
    <div class="rpt-field-row">
      <div class="rpt-field">
        <label class="rpt-label">Cohortes terminees cette semaine</label>
        <input class="rp-num" type="number" min="0" id="rf_cohortes" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Top 5 recus des profs</label>
        <input class="rp-num" type="number" min="0" id="rf_top5" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Dans les 48h?</label>
        <div class="rpt-radio-group rpt-radio-inline">
          <label class="rpt-radio-label"><input type="radio" name="rf_top5_48h" value="yes"/> Oui</label>
          <label class="rpt-radio-label"><input type="radio" name="rf_top5_48h" value="no"/> Non</label>
        </div>
      </div>
    </div>

    <div class="rpt-section-title">Marketing</div>
    <div class="rpt-field-row">
      <div class="rpt-field">
        <label class="rpt-label">Demandes envoyees a Alex cette semaine</label>
        <input class="rp-num" type="number" min="0" id="rf_demandes_alex" placeholder="0"/>
      </div>
      <div class="rpt-field rpt-field-grow">
        <label class="rpt-label">Description</label>
        <input class="rpt-text-input" type="text" id="rf_demandes_desc" placeholder="Description des demandes..."/>
      </div>
    </div>

    <div class="rpt-section-title">Notes additionnelles <span class="rpt-optional">(optionnel)</span></div>
    <textarea class="rp-textarea" id="rf_notes" rows="3" placeholder="Notes additionnelles..."></textarea>
  `;
}

function rptFormAdmin() {
  return `
    <div class="rpt-section-title">Bureau</div>
    <div class="rpt-field-row">
      <div class="rpt-field">
        <label class="rpt-label">Checklist Pascaline suivie?</label>
        <div class="rpt-radio-group rpt-radio-inline">
          <label class="rpt-radio-label"><input type="radio" name="rf_checklist_pascaline" value="yes"/> Oui</label>
          <label class="rpt-radio-label"><input type="radio" name="rf_checklist_pascaline" value="no"/> Non</label>
        </div>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Checklist salle apres cours?</label>
        <div class="rpt-radio-group rpt-radio-inline">
          <label class="rpt-radio-label"><input type="radio" name="rf_checklist_salle" value="yes"/> Oui</label>
          <label class="rpt-radio-label"><input type="radio" name="rf_checklist_salle" value="no"/> Non</label>
        </div>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Nombre de cours</label>
        <input class="rp-num" type="number" min="0" id="rf_nb_cours" placeholder="0"/>
      </div>
    </div>

    <div class="rpt-section-title">Commissions</div>
    <div class="rpt-field-row">
      <div class="rpt-field">
        <label class="rpt-label">Suivi commissions a jour?</label>
        <div class="rpt-radio-group rpt-radio-inline">
          <label class="rpt-radio-label"><input type="radio" name="rf_commissions" value="yes"/> Oui</label>
          <label class="rpt-radio-label"><input type="radio" name="rf_commissions" value="no"/> Non</label>
        </div>
      </div>
    </div>

    <div class="rpt-section-title">Leads anglais (recus de Hamza)</div>
    <div class="rpt-field-row">
      <div class="rpt-field">
        <label class="rpt-label">Leads recus</label>
        <input class="rp-num" type="number" min="0" id="rf_leads_recus" placeholder="0"/>
      </div>
      <div class="rpt-field">
        <label class="rpt-label">Contactes dans 24h</label>
        <input class="rp-num" type="number" min="0" id="rf_leads_contactes" placeholder="0"/>
      </div>
    </div>

    <div class="rpt-section-title">Rapport mensuel <span class="rpt-optional">(si fin de mois)</span></div>
    <div>
      <label class="rpt-label" style="margin-top:8px;">Etat bureau</label>
      <textarea class="rp-textarea" id="rf_etat_bureau" rows="2" placeholder="Etat general du bureau..."></textarea>
      <label class="rpt-label" style="margin-top:8px;">Incidents</label>
      <textarea class="rp-textarea" id="rf_incidents" rows="2" placeholder="Incidents survenus..."></textarea>
      <label class="rpt-label" style="margin-top:8px;">Besoins</label>
      <textarea class="rp-textarea" id="rf_besoins" rows="2" placeholder="Besoins identifies..."></textarea>
    </div>

    <div class="rpt-section-title">Notes additionnelles <span class="rpt-optional">(optionnel)</span></div>
    <textarea class="rp-textarea" id="rf_notes" rows="3" placeholder="Notes additionnelles..."></textarea>
  `;
}

function rptBuildForm(personId) {
  const meta = REPORT_PEOPLE[personId];
  if (!meta) return '<div class="rpt-empty">Gabarit non defini.</div>';
  const week = rptCurrentWeek();

  let body = '';
  if (meta.type === 'sac')           body = rptFormSAC();
  else if (meta.type === 'ventes')   body = rptFormVentes();
  else if (meta.type === 'recrutement') body = rptFormRecrutement();
  else if (meta.type === 'admin')    body = rptFormAdmin();

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

// ---- Collect form data ----

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

function rptCollectForm(personId) {
  const meta = REPORT_PEOPLE[personId];
  const weekStart = rptValEl('rf_week_start');
  const weekEnd   = rptValEl('rf_week_end');
  if (!weekStart) { alert('Veuillez choisir un debut de semaine.'); return null; }

  let formData = {};

  if (meta.type === 'sac') {
    const obs = rptValEl('rf_observations');
    if (!obs) { alert('Le champ Observations est obligatoire.'); return null; }
    formData = {
      hamza_in:       rptNumEl('rf_hamza_in'),
      hamza_out:      rptNumEl('rf_hamza_out'),
      hamza_rate:     rptNumEl('rf_hamza_rate'),
      lilia_in:       rptNumEl('rf_lilia_in'),
      lilia_out:      rptNumEl('rf_lilia_out'),
      lilia_rate:     rptNumEl('rf_lilia_rate'),
      sekou_in:       rptNumEl('rf_sekou_in'),
      sekou_out:      rptNumEl('rf_sekou_out'),
      sekou_rate:     rptNumEl('rf_sekou_rate'),
      annulations:    rptNumEl('rf_annulations'),
      elite_jessica:  rptNumEl('rf_elite_jessica'),
      leads_en:       rptNumEl('rf_leads_en'),
      unsolicited:    rptNumEl('rf_unsolicited'),
      observations:   obs,
      notes:          rptValEl('rf_notes')
    };
  } else if (meta.type === 'ventes') {
    const overview = rptValEl('rf_overview');
    if (!overview) { alert('Le champ Overview semaine est obligatoire.'); return null; }
    formData = {
      appels_1er:   rptNumEl('rf_appels_1er'),
      appels_2e:    rptNumEl('rf_appels_2e'),
      appels_3e:    rptNumEl('rf_appels_3e'),
      heures:       rptNumEl('rf_heures'),
      bsp:          rptNumEl('rf_bsp'),
      secourisme:   rptNumEl('rf_secourisme'),
      elite:        rptNumEl('rf_elite'),
      ghl_compliant: rptRadioVal('rf_ghl'),
      overview:     overview,
      notes:        rptValEl('rf_notes')
    };
  } else if (meta.type === 'recrutement') {
    formData = {
      entrevues:      rptNumEl('rf_entrevues'),
      retenus:        rptNumEl('rf_retenus'),
      refuses:        rptNumEl('rf_refuses'),
      appels_elite:   rptNumEl('rf_appels_elite'),
      pipeline:       rptNumEl('rf_pipeline'),
      cohortes:       rptNumEl('rf_cohortes'),
      top5:           rptNumEl('rf_top5'),
      top5_48h:       rptRadioVal('rf_top5_48h'),
      demandes_alex:  rptNumEl('rf_demandes_alex'),
      demandes_desc:  rptValEl('rf_demandes_desc'),
      notes:          rptValEl('rf_notes')
    };
  } else if (meta.type === 'admin') {
    formData = {
      checklist_pascaline: rptRadioVal('rf_checklist_pascaline'),
      checklist_salle:     rptRadioVal('rf_checklist_salle'),
      nb_cours:            rptNumEl('rf_nb_cours'),
      commissions:         rptRadioVal('rf_commissions'),
      leads_recus:         rptNumEl('rf_leads_recus'),
      leads_contactes:     rptNumEl('rf_leads_contactes'),
      etat_bureau:         rptValEl('rf_etat_bureau'),
      incidents:           rptValEl('rf_incidents'),
      besoins:             rptValEl('rf_besoins'),
      notes:               rptValEl('rf_notes')
    };
  }

  return {
    person_id:   personId,
    week_start:  weekStart,
    week_end:    weekEnd || null,
    report_type: meta.type,
    data:        formData,
    notes:       formData.notes || null
  };
}

// ---- Submit ----

async function rptSubmit(personId) {
  const payload = rptCollectForm(personId);
  if (!payload) return;
  const btn = document.querySelector('#rpt-form-wrap .btn.primary');
  if (btn) { btn.disabled = true; btn.textContent = 'Envoi...'; }
  try {
    await dbSaveReport(payload);
    _rptShowForm = false;
    await rptReloadAndRender(personId);
    // Show flash confirmation
    const flash = document.createElement('div');
    flash.style.cssText = 'position:fixed;bottom:24px;right:24px;background:var(--g);color:#000;padding:12px 20px;border-radius:8px;font-weight:700;z-index:10000;font-size:13px;font-family:"DM Sans",sans-serif;';
    flash.textContent = 'Rapport soumis avec succes';
    document.body.appendChild(flash);
    setTimeout(() => flash.remove(), 3000);
  } catch(e) {
    console.error('rptSubmit error:', e);
    alert('Erreur lors de la sauvegarde: ' + (e.message || e));
    if (btn) { btn.disabled = false; btn.textContent = 'Soumettre le rapport'; }
  }
}

// ---- Delete ----

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

// ---- Expand / collapse report cards ----

function rptToggleExpand(reportId) {
  const body = document.getElementById('rpt-body-' + reportId);
  const btn  = document.getElementById('rpt-toggle-' + reportId);
  if (!body) return;
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  if (btn) btn.textContent = isOpen ? 'Voir details' : 'Reduire';
}

// ---- Detail HTML per report type ----

function rptDetailHTML(r) {
  const d = r.data || {};
  const row = (label, val) => '<div class="rpt-detail-row"><span class="rpt-detail-key">' + label + '</span><span>' + (val != null && val !== '' ? val : '—') + '</span></div>';
  const section = (title, content) => '<div class="rpt-detail-section"><div class="rpt-detail-section-title">' + title + '</div><div class="rpt-detail-text">' + esc(content) + '</div></div>';

  if (r.report_type === 'sac') {
    return `
      <table class="rp-table" style="margin-top:8px;">
        <thead><tr><th>Agent</th><th>Entrants</th><th>Sortants</th><th>Taux rep.%</th></tr></thead>
        <tbody>
          <tr><td>Hamza</td><td>${d.hamza_in!=null?d.hamza_in:'—'}</td><td>${d.hamza_out!=null?d.hamza_out:'—'}</td><td>${d.hamza_rate!=null?d.hamza_rate:'—'}</td></tr>
          <tr><td>Lilia</td><td>${d.lilia_in!=null?d.lilia_in:'—'}</td><td>${d.lilia_out!=null?d.lilia_out:'—'}</td><td>${d.lilia_rate!=null?d.lilia_rate:'—'}</td></tr>
          <tr><td>Sekou</td><td>${d.sekou_in!=null?d.sekou_in:'—'}</td><td>${d.sekou_out!=null?d.sekou_out:'—'}</td><td>${d.sekou_rate!=null?d.sekou_rate:'—'}</td></tr>
        </tbody>
      </table>
      ${row('Annulations', d.annulations)}
      ${row('Dont ELITE (vers Jessica)', d.elite_jessica)}
      ${row('Leads anglais (vers Mitchell)', d.leads_en)}
      ${row('Appels non sollicites', d.unsolicited)}
      ${d.observations ? section('Observations', d.observations) : ''}
      ${d.notes ? section('Notes additionnelles', d.notes) : ''}
    `;
  }
  if (r.report_type === 'ventes') {
    return `
      ${row('Appels 1ers', d.appels_1er)}
      ${row('2e appels', d.appels_2e)}
      ${row('3e appels+', d.appels_3e)}
      ${row('Heures travaillees', d.heures)}
      ${row('BSP Gardiennage', d.bsp)}
      ${row('Secourisme', d.secourisme)}
      ${row('Elite', d.elite)}
      ${row('GHL compliant', d.ghl_compliant === 'yes' ? 'Oui' : (d.ghl_compliant === 'no' ? 'Non' : '—'))}
      ${d.overview ? section('Overview semaine', d.overview) : ''}
      ${d.notes ? section('Notes additionnelles', d.notes) : ''}
    `;
  }
  if (r.report_type === 'recrutement') {
    return `
      ${row('Entrevues agents', d.entrevues)}
      ${row('Retenus', d.retenus)}
      ${row('Refuses', d.refuses)}
      ${row('Appels Elite', d.appels_elite)}
      ${row('Pipeline actifs', d.pipeline)}
      ${row('Cohortes terminees', d.cohortes)}
      ${row('Top 5 des profs', d.top5)}
      ${row('Dans les 48h', d.top5_48h === 'yes' ? 'Oui' : (d.top5_48h === 'no' ? 'Non' : '—'))}
      ${row('Demandes a Alex', (d.demandes_alex != null ? d.demandes_alex : '—') + (d.demandes_desc ? ' — ' + d.demandes_desc : ''))}
      ${d.notes ? section('Notes additionnelles', d.notes) : ''}
    `;
  }
  if (r.report_type === 'admin') {
    return `
      ${row('Checklist Pascaline', d.checklist_pascaline === 'yes' ? 'Oui' : (d.checklist_pascaline === 'no' ? 'Non' : '—'))}
      ${row('Checklist salle', d.checklist_salle === 'yes' ? 'Oui' : (d.checklist_salle === 'no' ? 'Non' : '—'))}
      ${row('Nombre de cours', d.nb_cours)}
      ${row('Commissions a jour', d.commissions === 'yes' ? 'Oui' : (d.commissions === 'no' ? 'Non' : '—'))}
      ${row('Leads recus', d.leads_recus)}
      ${row('Contactes dans 24h', d.leads_contactes)}
      ${d.etat_bureau ? section('Etat bureau', d.etat_bureau) : ''}
      ${d.incidents ? section('Incidents', d.incidents) : ''}
      ${d.besoins ? section('Besoins', d.besoins) : ''}
      ${d.notes ? section('Notes additionnelles', d.notes) : ''}
    `;
  }
  return '<div class="rpt-empty">Donnees non disponibles.</div>';
}

// ---- Report card HTML ----

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

// ---- Sidebar person item ----

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

// ---- Reload and re-render only the main area ----

async function rptReloadAndRender(personId) {
  _rptSelectedId = personId;
  _rptShowForm = false;
  const mainArea = document.getElementById('rpt-main-area');
  if (!mainArea) { render(); return; }
  mainArea.innerHTML = '<div class="rpt-loading">Chargement...</div>';
  try {
    const reports = await dbGetReports(personId);
    // Update sidebar count badge
    const badge = document.getElementById('rpt-sbadge-' + personId);
    if (badge) badge.textContent = reports.length;
    mainArea.innerHTML = rptBuildMainArea(personId, reports);
  } catch(e) {
    console.error('rptReloadAndRender error:', e);
    mainArea.innerHTML = '<div class="rpt-empty">Erreur de chargement: ' + esc(e.message || String(e)) + '</div>';
  }
}

// ---- Build main area HTML ----

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

// ---- User actions ----

function rptSelectPerson(personId) {
  _rptSelectedId = personId;
  _rptShowForm = false;
  // Update sidebar active states
  document.querySelectorAll('.rpt-sidebar-item').forEach(el => {
    el.classList.toggle('active', el.getAttribute('onclick') === "rptSelectPerson('" + personId + "')");
  });
  // Update controls bar button
  const ctrlBtn = document.getElementById('rpt-ctrl-new-btn');
  if (ctrlBtn) {
    ctrlBtn.style.display = '';
    ctrlBtn.setAttribute('onclick', "rptOpenForm('" + personId + "')");
  }
  // Load and render main area
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

// ---- Main render entry point ----

async function renderReports(ct, cl) {
  // Controls bar
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

  // Load report counts for sidebar
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
  // Switch to reports view and select that person
  _rptSelectedId = pid;
  _rptShowForm = false;
  currentView = 'reports';
  document.querySelectorAll('.vtab').forEach(b => {
    const matches = b.getAttribute('onclick') && b.getAttribute('onclick').includes("'reports'");
    b.classList.toggle('active', matches);
  });
  render();
}
