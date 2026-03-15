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

// Department modal state
let _editDeptKey = null;
