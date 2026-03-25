// ==================== DB HELPERS ====================

/**
 * Upserts a person record into the `people` table.
 * Maps internal camelCase fields to DB snake_case columns.
 * @param {Object} person - Person object from global `data` array.
 */
async function dbSavePerson(person) {
  const row = {
    id: person.id, name: person.name, role: person.role||'', type: person.type,
    dept: person.dept, reports_to: person.reportsTo||null, programs: person.programs||[],
    schedule: person.schedule||'', delegate: (person.delegatable==='yes'||person.delegatable==='partial'||person.delegatable===true),
    notes: person.notes||'', avatar_color: person.avatarColor||avatarColor(person.id),
    avatar_initials: person.name.split(' ').map(w=>w[0]).join('').substring(0,2).toUpperCase(),
    sort_order: person.sort_order||99
  };
  const {error}=await db.from('people').upsert(row);
  if(error) console.error('dbSavePerson error:',error);
}

/**
 * Deletes a person and all their associated tasks from Supabase.
 * @param {string} id - Person ID to delete.
 */
async function dbDeletePerson(id) {
  const {error:e1}=await db.from('people').delete().eq('id',id);
  const {error:e2}=await db.from('tasks').delete().eq('person_id',id);
  if(e1) console.error('dbDeletePerson error:',e1);
  if(e2) console.error('dbDeleteTasks error:',e2);
}

/**
 * Archives a person by setting archived=true (soft delete).
 * @param {string} id - Person ID to archive.
 */
async function dbArchivePerson(id) {
  const {error}=await db.from('people').update({archived:true}).eq('id',id);
  if(error) console.error('dbArchivePerson error:',error);
}

/**
 * Restores an archived person by setting archived=false.
 * @param {string} id - Person ID to restore.
 */
async function dbRestorePerson(id) {
  const {error}=await db.from('people').update({archived:false}).eq('id',id);
  if(error) console.error('dbRestorePerson error:',error);
}

/**
 * Upserts the tasks/outcomes record for a person.
 * @param {string} personId - Person ID.
 * @param {Object} tasksObj - Object with `tasks`, `outcomes`, `expectedOutcomes` arrays.
 */
async function dbSaveTasks(personId, tasksObj) {
  const {error}=await db.from('tasks').upsert({
    person_id: personId,
    tasks: tasksObj.tasks||[],
    outcomes: tasksObj.outcomes||[],
    expected_outcomes: tasksObj.expectedOutcomes||[]
  });
  if(error) console.error('dbSaveTasks error:',error);
}

/**
 * Upserts a department record.
 * @param {Object} dept - Department object with `key`/`id`, `label`, `color`, `sort_order`.
 */
async function dbSaveDept(dept) {
  const {error}=await db.from('departments').upsert({id:dept.key||dept.id, label:dept.label, color:dept.color, sort_order:dept.sort_order||99});
  if(error) console.error('dbSaveDept error:',error);
}

/**
 * Deletes a department by ID.
 * @param {string} id - Department ID.
 */
async function dbDeleteDept(id) {
  const {error}=await db.from('departments').delete().eq('id',id);
  if(error) console.error('dbDeleteDept error:',error);
}

/**
 * Inserts a weekly report record and returns the created row.
 * @param {Object} report - Report payload matching the `weekly_reports` table schema.
 * @returns {Promise<Object>} The inserted report row.
 * @throws {Error} Supabase error if insert fails.
 */
async function dbSaveReport(report) {
  const {data,error} = await db.from('weekly_reports').insert(report).select().single();
  if(error) throw error;
  return data;
}

/**
 * Fetches weekly reports, optionally filtered by person.
 * @param {string|null} personId - Filter to a specific person, or null for all.
 * @returns {Promise<Object[]>} Array of report rows ordered by week_start descending.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetReports(personId) {
  let q = db.from('weekly_reports').select('*').order('week_start', {ascending:false});
  if(personId) q = q.eq('person_id', personId);
  const {data,error} = await q;
  if(error) throw error;
  return data||[];
}

/**
 * Deletes a weekly report by ID.
 * @param {string} id - Report row ID.
 * @throws {Error} Supabase error if delete fails.
 */
async function dbDeleteReport(id) {
  const {error} = await db.from('weekly_reports').delete().eq('id', id);
  if(error) throw error;
}

/**
 * Saves the canvas node order for a parent division.
 * @param {string} parentId - Division ID.
 * @param {string[]} children - Ordered array of child person IDs.
 */
async function dbSaveCanvasOrder(parentId, children) {
  const {error}=await db.from('canvas_order').upsert({id:parentId, children});
  if(error) console.error('dbSaveCanvasOrder error:',error);
}

/**
 * Loads all archived people from Supabase.
 * @returns {Promise<Object[]>} Array of archived person objects.
 */
async function dbGetArchivedPeople() {
  const {data,error} = await db.from('people').select('*').eq('archived',true).order('sort_order');
  if(error) throw error;
  return (data||[]).map(p=>({
    id:p.id, name:p.name, role:p.role||'', type:p.type||'contractor',
    dept:p.dept||'', programs:p.programs||[], locations:[],
    schedule:p.schedule||'', notes:p.notes||'',
    delegatable:p.delegate===true||p.delegate==='yes'||p.delegate==='partial'?'yes':'no',
    reportsTo:p.reports_to||'vp',
    avatarColor:p.avatar_color, sort_order:p.sort_order||99,
    archived:true
  }));
}

// ==================== HORAIRES DB ====================

/**
 * Fetches all schedule entries for a given week range, with location and cohort joins.
 * @param {string} weekStart - ISO date string for start of week e.g. "2026-03-16"
 * @param {string} weekEnd   - ISO date string for end of week e.g. "2026-03-22"
 * @returns {Promise<Object[]>} Array of schedule_entries rows with joined data.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetScheduleWeek(weekStart, weekEnd) {
  const {data,error} = await db.from('schedule_entries')
    .select('*, locations(name,code), cohorts(code,program)')
    .gte('date', weekStart).lte('date', weekEnd)
    .order('date');
  if(error) throw error;
  return data||[];
}

/**
 * Fetches all active locations ordered by name.
 * @returns {Promise<Object[]>} Array of location rows.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetLocations() {
  const {data,error} = await db.from('locations').select('*').eq('is_active',true).order('name');
  if(error) throw error;
  return data||[];
}

/**
 * Maps internal `quart` field to DB column `shift_type` before writing.
 * @param {Object} entry - Schedule entry with optional `quart` field.
 * @returns {Object} Entry with `quart` renamed to `shift_type`.
 */
function _schedEntryToDb(entry) {
  const e = { ...entry };
  if ('quart' in e) { e.shift_type = e.quart; delete e.quart; }
  return e;
}

/**
 * Maps DB `shift_type` column back to internal `quart` field after reading.
 * @param {Object|null} row - DB row with optional `shift_type` field.
 * @returns {Object|null} Row with `shift_type` renamed to `quart`.
 */
function _schedEntryFromDb(row) {
  if (!row) return row;
  const r = { ...row };
  if ('shift_type' in r) { r.quart = r.shift_type; delete r.shift_type; }
  return r;
}

/**
 * Inserts a new schedule entry and returns the created row.
 * @param {Object} entry - Schedule entry payload (uses internal `quart` field).
 * @returns {Promise<Object>} Created row mapped back to internal format.
 * @throws {Error} Supabase error if insert fails.
 */
async function dbSaveScheduleEntry(entry) {
  const {data,error} = await db.from('schedule_entries').insert(_schedEntryToDb(entry)).select().single();
  if(error) throw error;
  return _schedEntryFromDb(data);
}

/**
 * Updates an existing schedule entry by ID.
 * @param {string} id - schedule_entries row ID.
 * @param {Object} updates - Partial update payload (uses internal `quart` field).
 * @returns {Promise<Object>} Updated row mapped back to internal format.
 * @throws {Error} Supabase error if update fails.
 */
async function dbUpdateScheduleEntry(id, updates) {
  const {data,error} = await db.from('schedule_entries').update(_schedEntryToDb(updates)).eq('id',id).select().single();
  if(error) throw error;
  return _schedEntryFromDb(data);
}

/**
 * Deletes a schedule entry by ID.
 * @param {string} id - schedule_entries row ID.
 * @throws {Error} Supabase error if delete fails.
 */
async function dbDeleteScheduleEntry(id) {
  const {error} = await db.from('schedule_entries').delete().eq('id',id);
  if(error) throw error;
}

/**
 * Persists the trainer row display order to localStorage.
 * Uses localStorage instead of Supabase — per-browser, instant, no schema needed.
 * @param {string[]} orderArr - Ordered array of instructor_id strings.
 */
function dbSaveTrainerOrder(orderArr) {
  try { localStorage.setItem('xg_schedule_trainer_order', JSON.stringify(orderArr)); } catch(e) {}
}

/**
 * Loads the saved trainer row display order from localStorage.
 * @returns {string[]} Ordered array of instructor_id strings, or [] if not set.
 */
function dbLoadTrainerOrder() {
  try { return JSON.parse(localStorage.getItem('xg_schedule_trainer_order') || '[]') || []; } catch(e) { return []; }
}

/**
 * Copies all schedule entries from one week to another, shifting dates by the offset.
 * Resets status to 'scheduled' on all copied entries.
 * @param {string} sourceStart - ISO date of source week Monday e.g. "2026-03-16"
 * @param {string} targetStart - ISO date of target week Monday e.g. "2026-03-23"
 * @returns {Promise<number>} Number of entries copied.
 * @throws {Error} Supabase error if read or insert fails.
 */
async function dbCopyWeek(sourceStart, targetStart) {
  const sourceEnd = dayjs(sourceStart).add(6,'day').format('YYYY-MM-DD');
  const {data,error} = await db.from('schedule_entries').select('*').gte('date',sourceStart).lte('date',sourceEnd);
  if(error) throw error;
  const offset = dayjs(targetStart).diff(dayjs(sourceStart),'day');
  const copies = (data||[]).map(({id,created_at,updated_at,time_range,...e})=>({
    ...e,
    date: dayjs(e.date).add(offset,'day').format('YYYY-MM-DD'),
    status:'scheduled'
  }));
  if(!copies.length) return 0;
  const {error:e2} = await db.from('schedule_entries').insert(copies);
  if(e2) throw e2;
  return copies.length;
}

// ==================== SCHEDULE MODULE DB ====================

/**
 * Fetches all schedule entries for a given month, with cohort and location joins.
 * Optionally filters to a single instructor.
 * @param {number} month - Month number (1–12).
 * @param {number} year  - 4-digit year.
 * @param {string} [instructorId] - Optional instructor UUID to filter by.
 * @returns {Promise<Object[]>} Array of entries mapped to internal format (quart field).
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetScheduleEntries(month, year, instructorId) {
  const startDate = year + '-' + String(month).padStart(2, '0') + '-01';
  const endDate   = new Date(year, month, 0).toISOString().split('T')[0]; // last day of month
  let q = db.from('schedule_entries')
    .select('*, cohorts(code,program), locations(name,code,city)')
    .gte('date', startDate)
    .lte('date', endDate)
    .order('date');
  if (instructorId) q = q.eq('instructor_id', instructorId);
  const { data, error } = await q;
  if (error) throw error;
  return (data || []).map(_schedEntryFromDb);
}

/**
 * Fetches all programs ordered by sort_order.
 * @returns {Promise<Object[]>} Array of program rows.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetPrograms() {
  const { data, error } = await db.from('programs').select('*').order('sort_order');
  if (error) throw error;
  return data || [];
}

/**
 * Fetches active cohorts, optionally filtered by program.
 * @param {string} [program] - Optional program key to filter by e.g. "BSP".
 * @returns {Promise<Object[]>} Array of cohort rows ordered by cohort_number.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetCohorts(program) {
  let q = db.from('cohorts').select('*').eq('is_active', true).order('cohort_number');
  if (program) q = q.eq('program', program);
  const { data, error } = await q;
  if (error) throw error;
  return data || [];
}

// ==================== SUPABASE LOAD ====================

/**
 * Loads all app data from Supabase on startup: people, departments, tasks, canvas order.
 * Populates global `VP`, `data`, `departments`, `tasksData`, and `cvOrder`.
 * Falls back gracefully if the load fails — keeps whatever is in memory.
 */
async function loadFromSupabase() {
  try {
    const [pRes, dRes, tRes, cvRes] = await Promise.all([
      db.from('people').select('*').eq('archived', false).order('sort_order'),
      db.from('departments').select('*').order('sort_order'),
      db.from('tasks').select('*'),
      db.from('canvas_order').select('*')
    ]);

    if(pRes.error) throw pRes.error;
    if(dRes.error) throw dRes.error;

    // Map people rows
    const vpRow = pRes.data.find(p=>p.id==='vp');
    if(vpRow){
      VP = {
        id:'vp', name:vpRow.name, role:vpRow.role, type:vpRow.type||'exec',
        dept:vpRow.dept||'all', programs:vpRow.programs||[],
        locations:[], schedule:vpRow.schedule||'', notes:vpRow.notes||'',
        delegatable:vpRow.delegate||'no', reportsTo:null,
        avatarColor:vpRow.avatar_color
      };
    }

    data = pRes.data
      .filter(p=>p.id!=='vp')
      .map(p=>({
        id:p.id, name:p.name, role:p.role||'', type:p.type||'contractor',
        dept:p.dept||'', programs:p.programs||[], locations:[],
        schedule:p.schedule||'', notes:p.notes||'',
        delegatable:p.delegate===true||p.delegate==='yes'||p.delegate==='partial'?'yes':'no', reportsTo:p.reports_to||'vp',
        avatarColor:p.avatar_color, sort_order:p.sort_order||99
      }));

    // Map departments — use 'id' as the key
    departments = dRes.data.map(d=>({
      key:d.id, label:d.label, color:d.color, sort_order:d.sort_order||99
    }));

    // Helper: parse items that may be double-serialized strings
    const parseItems = arr => (arr||[]).map(item=>{
      if(typeof item==='string'){try{return JSON.parse(item);}catch(e){return {id:'i_'+Math.random().toString(36).slice(2),text:item};}}
      if(!item.id) item.id='i_'+Math.random().toString(36).slice(2);
      return item;
    });

    // Map tasks
    tasksData = {};
    if(tRes.data){
      tRes.data.forEach(row=>{
        tasksData[row.person_id]={
          tasks: parseItems(row.tasks),
          outcomes: parseItems(row.outcomes),
          expectedOutcomes: parseItems(row.expected_outcomes)
        };
      });
    }

    // Map canvas order
    cvOrder = {};
    if(cvRes.data){
      cvRes.data.forEach(row=>{ cvOrder[row.id]=row.children; });
    }

    // Rebuild CV_DIVS from departments
    cvBuildDivisions();

  } catch(err) {
    console.error('Supabase load failed:', err);
    // Fallback: keep whatever data is already in memory (or empty)
    if(departments.length===0){
      // minimal fallback so the UI renders
      departments=[{key:'training',label:'Training',color:'#60a5fa',sort_order:1}];
    }
  }
}

// ==================== COACHING / NITRO DB ====================

/**
 * Fetches the last N days of coaching_data for a person, ordered by sync_date descending.
 * @param {string} personId - Person ID to filter by.
 * @param {number} [days=30] - Number of days to look back.
 * @returns {Promise<Object[]>} Array of coaching_data rows.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetCoachingData(personId, days=30) {
  const since = dayjs().subtract(days,'day').format('YYYY-MM-DD');
  const {data,error} = await db.from('coaching_data').select('*')
    .eq('person_id', personId)
    .gte('sync_date', since)
    .order('sync_date', {ascending:false});
  if(error) throw error;
  return data||[];
}

/**
 * Fetches coaching_reports for a person, ordered by week_start descending.
 * @param {string} personId - Person ID to filter by.
 * @param {number} [limit=12] - Maximum number of reports to return.
 * @returns {Promise<Object[]>} Array of coaching_report rows.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetCalls(personId, since=null, until=null) {
  let q = db.from('calls').select('id,call_time,duration_s,contact_name,word_count')
    .eq('person_id', personId)
    .order('call_time', {ascending:false});
  if (since) q = q.gte('call_time', since);
  if (until) q = q.lte('call_time', until);
  q = q.limit(2000);
  const {data,error} = await q;
  if(error) throw error;
  return data||[];
}

async function dbGetCoachingReports(personId, limit=12) {
  const {data,error} = await db.from('coaching_reports').select('*')
    .eq('person_id', personId)
    .order('week_start', {ascending:false})
    .limit(limit);
  if(error) throw error;
  return data||[];
}

/**
 * Fetches the most recent coaching_report for a person.
 * @param {string} personId - Person ID to filter by.
 * @returns {Promise<Object|null>} The latest coaching_report row, or null if none.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetLatestCoachingReport(personId) {
  const {data,error} = await db.from('coaching_reports').select('*')
    .eq('person_id', personId)
    .order('week_start', {ascending:false})
    .limit(1)
    .single();
  if(error && error.code!=='PGRST116') throw error;
  return data||null;
}

/**
 * Fetches all nitro_status rows for a person (all task_types).
 * @param {string} personId - Person ID to filter by.
 * @returns {Promise<Object[]>} Array of nitro_status rows.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetNitroStatus(personId) {
  const {data,error} = await db.from('nitro_status').select('*')
    .eq('person_id', personId);
  if(error) throw error;
  return data||[];
}

/**
 * Fetches cron_logs for a person, ordered by started_at descending.
 * @param {string} personId - Person ID to filter by.
 * @param {number} [limit=20] - Maximum number of log entries to return.
 * @returns {Promise<Object[]>} Array of cron_logs rows.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetCronLogs(personId, limit=20) {
  const {data,error} = await db.from('cron_logs').select('*')
    .eq('person_id', personId)
    .order('started_at', {ascending:false})
    .limit(limit);
  if(error) throw error;
  return data||[];
}

/**
 * Fetches ALL nitro_status rows (for admin dashboard).
 * @returns {Promise<Object[]>} Array of all nitro_status rows.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetAllNitroStatus() {
  const {data,error} = await db.from('nitro_status').select('*');
  if(error) throw error;
  return data||[];
}

/**
 * Fetches ALL cron_logs, ordered by started_at descending.
 * @param {number} [limit=50] - Maximum number of log entries to return.
 * @returns {Promise<Object[]>} Array of cron_logs rows.
 * @throws {Error} Supabase error if query fails.
 */
async function dbGetAllCronLogs(limit=50) {
  const {data,error} = await db.from('cron_logs').select('*')
    .order('started_at', {ascending:false})
    .limit(limit);
  if(error) throw error;
  return data||[];
}
