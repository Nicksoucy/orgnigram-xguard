// ==================== DB HELPERS ====================
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

async function dbDeletePerson(id) {
  const {error:e1}=await db.from('people').delete().eq('id',id);
  const {error:e2}=await db.from('tasks').delete().eq('person_id',id);
  if(e1) console.error('dbDeletePerson error:',e1);
  if(e2) console.error('dbDeleteTasks error:',e2);
}

async function dbSaveTasks(personId, tasksObj) {
  const {error}=await db.from('tasks').upsert({
    person_id: personId,
    tasks: tasksObj.tasks||[],
    outcomes: tasksObj.outcomes||[],
    expected_outcomes: tasksObj.expectedOutcomes||[]
  });
  if(error) console.error('dbSaveTasks error:',error);
}

async function dbSaveDept(dept) {
  const {error}=await db.from('departments').upsert({id:dept.key||dept.id, label:dept.label, color:dept.color, sort_order:dept.sort_order||99});
  if(error) console.error('dbSaveDept error:',error);
}

async function dbDeleteDept(id) {
  const {error}=await db.from('departments').delete().eq('id',id);
  if(error) console.error('dbDeleteDept error:',error);
}

async function dbSaveReport(report) {
  const {data,error} = await db.from('weekly_reports').insert(report).select().single();
  if(error) throw error;
  return data;
}

async function dbGetReports(personId) {
  let q = db.from('weekly_reports').select('*').order('week_start', {ascending:false});
  if(personId) q = q.eq('person_id', personId);
  const {data,error} = await q;
  if(error) throw error;
  return data||[];
}

async function dbDeleteReport(id) {
  const {error} = await db.from('weekly_reports').delete().eq('id', id);
  if(error) throw error;
}

async function dbSaveCanvasOrder(parentId, children) {
  const {error}=await db.from('canvas_order').upsert({id:parentId, children});
  if(error) console.error('dbSaveCanvasOrder error:',error);
}

// ==================== HORAIRES DB ====================

async function dbGetScheduleWeek(weekStart, weekEnd) {
  const {data,error} = await db.from('schedule_entries')
    .select('*, locations(name,code), cohorts(code,program)')
    .gte('date', weekStart).lte('date', weekEnd)
    .order('date');
  if(error) throw error;
  return data||[];
}

async function dbGetLocations() {
  const {data,error} = await db.from('locations').select('*').eq('is_active',true).order('name');
  if(error) throw error;
  return data||[];
}

async function dbSaveScheduleEntry(entry) {
  const {data,error} = await db.from('schedule_entries').insert(entry).select().single();
  if(error) throw error;
  return data;
}

async function dbUpdateScheduleEntry(id, updates) {
  const {data,error} = await db.from('schedule_entries').update(updates).eq('id',id).select().single();
  if(error) throw error;
  return data;
}

async function dbDeleteScheduleEntry(id) {
  const {error} = await db.from('schedule_entries').delete().eq('id',id);
  if(error) throw error;
}

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
  return data || [];
}

async function dbGetPrograms() {
  const { data, error } = await db.from('programs').select('*').order('sort_order');
  if (error) throw error;
  return data || [];
}

async function dbGetCohorts(program) {
  let q = db.from('cohorts').select('*').eq('is_active', true).order('cohort_number');
  if (program) q = q.eq('program', program);
  const { data, error } = await q;
  if (error) throw error;
  return data || [];
}

// ==================== SUPABASE LOAD ====================
async function loadFromSupabase() {
  try {
    const [pRes, dRes, tRes, cvRes] = await Promise.all([
      db.from('people').select('*').order('sort_order'),
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
