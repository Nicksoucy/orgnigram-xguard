// ==================== MODALS ====================

function popDepts(){
  const sel=document.getElementById('fDept');
  sel.innerHTML='';
  departments.forEach(d=>{sel.innerHTML+=`<option value="${d.key}">${esc(d.label)}</option>`;});
}

function popReports(excludeId){
  const sel=document.getElementById('fReports');
  sel.innerHTML=`<option value="vp">You (VP)</option>`;
  data.forEach(p=>{
    if(p.id===excludeId) return;
    sel.innerHTML+=`<option value="${p.id}">${esc(p.name)} — ${esc(p.role)}</option>`;
  });
}

function openAdd(){
  editId=null;
  document.getElementById('mTitle').textContent='Add Person';
  ['fName','fEmail','fRole','fSched','fNotes'].forEach(f=>document.getElementById(f).value='');
  document.getElementById('fType').value='contractor';
  popDepts();
  document.getElementById('fDept').value='training';
  document.getElementById('fDel').value='unknown';
  sChk('fProg',[]);sChk('fLoc',[]);
  popReports(null);
  document.getElementById('fReports').value='vp';
  document.getElementById('bDel').style.display='none';
  document.getElementById('mo').classList.add('active');
  document.getElementById('fName').focus();
}

function openEdit(id){
  const p=data.find(x=>x.id===id);
  if(!p) return;
  editId=id;
  document.getElementById('mTitle').textContent='Edit — '+p.name;
  document.getElementById('fName').value=p.name;
  document.getElementById('fEmail').value=p.email||'';
  document.getElementById('fRole').value=p.role||'';
  document.getElementById('fType').value=p.type;
  popDepts();
  document.getElementById('fDept').value=p.dept;
  document.getElementById('fSched').value=p.schedule||'';
  document.getElementById('fNotes').value=p.notes||'';
  document.getElementById('fDel').value=p.delegatable||'unknown';
  sChk('fProg',p.programs);sChk('fLoc',p.locations);
  popReports(id);
  document.getElementById('fReports').value=p.reportsTo||'vp';
  document.getElementById('bDel').style.display='inline-block';
  document.getElementById('mo').classList.add('active');
}

function closeM(){document.getElementById('mo').classList.remove('active');editId=null;}

function saveP(){
  const name=document.getElementById('fName').value.trim();
  if(!name){alert('Name required');return;}
  const obj={name,email:document.getElementById('fEmail').value.trim(),role:document.getElementById('fRole').value.trim(),
    type:document.getElementById('fType').value,dept:document.getElementById('fDept').value,
    programs:gChk('fProg'),locations:gChk('fLoc'),schedule:document.getElementById('fSched').value.trim(),
    notes:document.getElementById('fNotes').value.trim(),delegatable:document.getElementById('fDel').value,
    reportsTo:document.getElementById('fReports').value};
  let person;
  if(editId){person=data.find(x=>x.id===editId);Object.assign(person,obj);}
  else{person={id:gid(),...obj};data.push(person);}
  dbSavePerson(person);
  closeM();render();
}

function delP(){
  if(!editId) return;
  const p = data.find(x=>x.id===editId);
  const name = p ? p.name : 'cette personne';
  if(!confirm(`Archiver ${name}?\n\nLa personne sera masquée mais ses données seront conservées.`)) return;
  const id=editId;
  // Reassign direct reports to VP
  data.filter(p=>p.reportsTo===id).forEach(p=>{p.reportsTo='vp';dbSavePerson(p);});
  data=data.filter(p=>p.id!==id);
  dbArchivePerson(id);
  closeM();render();
}

// ==================== DEPARTMENT MODAL ====================
function openAddDept(){
  _editDeptKey=null;
  document.getElementById('dmTitle').textContent='Add Department';
  document.getElementById('fdLabel').value='';
  document.querySelectorAll('input[name="fdColor"]').forEach(r=>r.checked=false);
  // pick a default color not yet used
  const usedColors=departments.map(d=>d.color);
  const allColors=[...document.querySelectorAll('input[name="fdColor"]')].map(r=>r.value);
  const avail=allColors.find(c=>!usedColors.includes(c))||allColors[0];
  const radio=document.querySelector(`input[name="fdColor"][value="${avail}"]`);
  if(radio) radio.checked=true;
  document.getElementById('bDeptDel').style.display='none';
  document.getElementById('dmo').classList.add('active');
  document.getElementById('fdLabel').focus();
}

function editDept(key){
  const dept=departments.find(d=>d.key===key);
  if(!dept) return;
  _editDeptKey=key;
  document.getElementById('dmTitle').textContent='Edit Department';
  document.getElementById('fdLabel').value=dept.label;
  document.querySelectorAll('input[name="fdColor"]').forEach(r=>r.checked=(r.value===dept.color));
  const memberCount=data.filter(p=>p.dept===key).length;
  document.getElementById('bDeptDel').style.display=memberCount===0?'inline-block':'none';
  document.getElementById('dmo').classList.add('active');
  document.getElementById('fdLabel').focus();
}

function closeDeptM(){document.getElementById('dmo').classList.remove('active');_editDeptKey=null;}

function saveDept(){
  const label=document.getElementById('fdLabel').value.trim();
  if(!label){alert('Department name required');return;}
  const colorRadio=document.querySelector('input[name="fdColor"]:checked');
  const color=colorRadio?colorRadio.value:'#60a5fa';
  let dept;
  if(_editDeptKey){
    // editing existing
    dept=departments.find(d=>d.key===_editDeptKey);
    if(dept){dept.label=label;dept.color=color;}
  } else {
    // adding new — generate key from label
    const key=label.toLowerCase().replace(/[^a-z0-9]/g,'_').replace(/_+/g,'_').replace(/^_|_$/g,'')||('dept_'+Date.now());
    if(departments.find(d=>d.key===key)){alert('A department with a similar name already exists');return;}
    dept={key, label, color, sort_order:departments.length+1};
    departments.push(dept);
  }
  if(dept) dbSaveDept(dept);
  closeDeptM();
  render();
}

function delDept(){
  if(!_editDeptKey) return;
  const memberCount=data.filter(p=>p.dept===_editDeptKey).length;
  if(memberCount>0){alert('Cannot delete — move all members to another department first.');return;}
  if(!confirm('Delete this department?')) return;
  const key=_editDeptKey;
  departments=departments.filter(d=>d.key!==key);
  dbDeleteDept(key);
  closeDeptM();
  render();
}

// ==================== FUTURE MODAL ====================
function openFM(){
  fEditIdx=null;
  document.getElementById('fmTitle').textContent='Plan a Change';
  const pSel=document.getElementById('ffPerson');
  pSel.innerHTML='';
  data.forEach(p=>{pSel.innerHTML+=`<option value="${p.id}">${esc(p.name)}</option>`;});
  const rSel=document.getElementById('ffReports');
  rSel.innerHTML=`<option value="vp">You (VP)</option>`;
  data.forEach(p=>{rSel.innerHTML+=`<option value="${p.id}">${esc(p.name)}</option>`;});
  document.getElementById('ffRole').value='';
  document.getElementById('ffType').value='contractor';
  document.getElementById('ffNotes').value='';
  document.getElementById('bFDel').style.display='none';
  document.getElementById('fmo').classList.add('active');
}

function editFChange(idx){
  const fc=futureChanges[idx];
  fEditIdx=idx;
  document.getElementById('fmTitle').textContent='Edit Change';
  const pSel=document.getElementById('ffPerson');
  pSel.innerHTML='';
  data.forEach(p=>{pSel.innerHTML+=`<option value="${p.id}">${esc(p.name)}</option>`;});
  pSel.value=fc.personId;
  const rSel=document.getElementById('ffReports');
  rSel.innerHTML=`<option value="vp">You (VP)</option>`;
  data.forEach(p=>{rSel.innerHTML+=`<option value="${p.id}">${esc(p.name)}</option>`;});
  rSel.value=fc.futureReportsTo;
  document.getElementById('ffRole').value=fc.futureRole||'';
  document.getElementById('ffType').value=fc.futureType||'contractor';
  document.getElementById('ffNotes').value=fc.notes||'';
  document.getElementById('bFDel').style.display='inline-block';
  document.getElementById('fmo').classList.add('active');
}

function closeFM(){document.getElementById('fmo').classList.remove('active');fEditIdx=null;}

function saveFChange(){
  const personId=document.getElementById('ffPerson').value;
  const obj={personId,futureReportsTo:document.getElementById('ffReports').value,
    futureRole:document.getElementById('ffRole').value.trim(),
    futureType:document.getElementById('ffType').value,
    notes:document.getElementById('ffNotes').value.trim()};
  if(fEditIdx!==null){futureChanges[fEditIdx]=obj;}
  else{futureChanges.push(obj);}
  closeFM();render();
}

function delFChange(){
  if(fEditIdx===null)return;
  futureChanges.splice(fEditIdx,1);
  closeFM();render();
}

// ==================== EXPORT ====================
function expJSON(){
  const b=new Blob([JSON.stringify({vp:VP,team:data,futureChanges},null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='xguard-org-chart.json';a.click();
}
function expFutureJSON(){
  const b=new Blob([JSON.stringify({currentTeam:data,futureChanges},null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='xguard-future-plan.json';a.click();
}
