// ==================== UTILS ====================
const TC = {'BSP':'t-bsp','RCR':'t-rcr','Élite':'t-elite','CV':'t-cv','Drone':'t-drone','SAC':'t-sac','MKT':'t-mkt','Sales':'t-sales'};

// Legacy DM getter for backward compat
const DM = new Proxy({},{get:(_,k)=>{const d=departments.find(x=>x.key===k);return d?{l:d.label,d:d.color}:null;}});

function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}
function gid(){return 'p_'+Math.random().toString(36).substr(2,9);}
function bc(t){return t==='lead'?'b-lead':t==='employee'?'b-emp':t==='exec'?'b-exec':'b-con';}
function bl(t){return t==='lead'?'Lead':t==='employee'?'Employee':t==='exec'?'VP':'Contractor';}
function di(d){return d==='yes'?'🟢':d==='partial'?'🟡':d==='no'?'🔴':'⚪';}
function getChildren(pid){return data.filter(p=>p.reportsTo===pid);}
function getById(id){return id==='vp'?VP:data.find(p=>p.id===id);}
function allPeople(){return [VP,...data];}

function avatarColor(id){
  const colors=['#ff6b35','#34d399','#60a5fa','#a78bfa','#fbbf24','#f472b6','#22d3ee','#f87171','#86efac','#fdba74'];
  let h=0; for(let i=0;i<id.length;i++) h=(h*31+id.charCodeAt(i))&0xffff;
  return colors[h%colors.length];
}
function initials(name){
  const p=name.trim().split(/\s+/);
  return (p[0]?.[0]||'')+(p[1]?.[0]||'');
}

function gChk(id){return [...document.querySelectorAll(`#${id} input:checked`)].map(c=>c.value);}
function sChk(id,v){document.querySelectorAll(`#${id} input`).forEach(c=>{c.checked=v.includes(c.value);});}

function gTaskId(){ return 'tk_'+Math.random().toString(36).substr(2,7); }

// ---- Shared flash notification (task 9) ----
function showFlash(msg, isDanger) {
  const el = document.createElement('div');
  el.className = 'hor-flash' + (isDanger ? ' danger' : '');
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 400); }, 2800);
}

// ---- Shared trainer filter (task 10) ----
function getTrainers() {
  return data.filter(p =>
    p.type !== 'exec' &&
    (p.dept === 'training' || p.dept === 'sac' || (p.programs && p.programs.length > 0))
  );
}
