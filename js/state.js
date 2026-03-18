// ==================== GLOBAL STATE ====================
let VP = {id:'vp',name:'You',role:'VP of Training',type:'exec',dept:'all',programs:[],locations:['Montréal','Ligne','Québec'],schedule:'',notes:'',delegatable:'no',reportsTo:null};

let data = [];

// Future changes: array of {personId, futureReportsTo, futureRole, futureType, notes}
let futureChanges = [];

// Tasks & Outcomes: { personId: { tasks:[{id,text,done}], outcomes:[{id,text}], expectedOutcomes:[{id,text}] } }
let tasksData = {};

let editId = null, fEditIdx = null, currentView = 'dept';

let departments = [];

// Canvas state
let _cvZoom = 0.72, _cvPanX = 0, _cvPanY = 0, _cvDrag = null, _cvInited = false, _cvBaseW = 0, _cvBaseH = 0;
let CV_DIVS = [];
let cvOrder = {};

// Tasks view filter state
let _tkFilter = '', _tkDept = 'all';

// Tasks card order (persisted to localStorage)
let _tkCardOrder = JSON.parse(localStorage.getItem('tkCardOrder')||'[]');

// Department modal state
let _editDeptKey = null;

// Horaires view state
let _horCurrentWeek = null; // will be set to current Monday on init
let _horLocations = [];
let _horEntries = [];
let _horFilter = 'all'; // 'all','formation_qc','rcr_mtl','classe_mtl','formation_ligne'
let _horViewMode = 'week'; // 'week' | 'month'
let _horDpInited = false;

// Schedule view state
let _schedMonth = new Date().getMonth() + 1;
let _schedYear  = new Date().getFullYear();
let _schedView  = 'grid'; // 'grid' | 'week' | 'trainer'
let _schedTrainer  = null;
let _schedProgram  = null;
let _schedEntries  = [];
let _schedLocations = [];
let _schedPrograms  = [];

// Schedule trainer row order (array of instructor_ids, persisted to Supabase)
let _schedTrainerOrder = []; // [] = default order from data array

// Reports view state
const REPORT_PEOPLE = {
  'L3': {type:'sac',        label:'SAC'},
  'v1': {type:'ventes',     label:'Ventes'},
  'r1': {type:'recrutement',label:'Recrutement'},
  'L2': {type:'admin',      label:'Admin'}
};
let _rptSelectedId = null; // currently selected person in Reports view
let _rptShowForm   = false; // is the new-report form open?
