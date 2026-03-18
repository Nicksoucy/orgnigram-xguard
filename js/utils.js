// ==================== UTILS ====================

/** CSS class map: program key → badge class name */
const TC = {'BSP':'t-bsp','RCR':'t-rcr','Élite':'t-elite','CV':'t-cv','Drone':'t-drone','SAC':'t-sac','MKT':'t-mkt','Sales':'t-sales'};

/** Legacy department map — backward compat proxy over the live `departments` array */
const DM = new Proxy({},{get:(_,k)=>{const d=departments.find(x=>x.key===k);return d?{l:d.label,d:d.color}:null;}});

/**
 * HTML-escapes a string for safe insertion into innerHTML.
 * @param {string} s - Raw string to escape.
 * @returns {string} HTML-safe string.
 */
function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}

/**
 * Generates a random unique person ID prefixed with "p_".
 * @returns {string} e.g. "p_4xk9m2r"
 */
function gid(){return 'p_'+Math.random().toString(36).substr(2,9);}

/**
 * Returns the CSS badge class for a person type.
 * @param {string} t - Person type: 'lead' | 'employee' | 'exec' | 'contractor'
 * @returns {string} CSS class name.
 */
function bc(t){return t==='lead'?'b-lead':t==='employee'?'b-emp':t==='exec'?'b-exec':'b-con';}

/**
 * Returns the human-readable label for a person type.
 * @param {string} t - Person type.
 * @returns {string} e.g. "Lead", "Employee", "VP", "Contractor"
 */
function bl(t){return t==='lead'?'Lead':t==='employee'?'Employee':t==='exec'?'VP':'Contractor';}

/**
 * Returns the delegation capacity emoji indicator.
 * @param {string} d - Delegation value: 'yes' | 'partial' | 'no' | other
 * @returns {string} Emoji: green circle | yellow circle | red circle | white circle
 */
function di(d){return d==='yes'?'🟢':d==='partial'?'🟡':d==='no'?'🔴':'⚪';}

/**
 * Returns all direct reports for a given person ID.
 * @param {string} pid - Parent person ID.
 * @returns {Object[]} Array of person objects from the global `data` array.
 */
function getChildren(pid){return data.filter(p=>p.reportsTo===pid);}

/**
 * Looks up a person by ID, including the VP sentinel.
 * @param {string} id - Person ID or 'vp'.
 * @returns {Object|undefined} Person object, or undefined if not found.
 */
function getById(id){return id==='vp'?VP:data.find(p=>p.id===id);}

/**
 * Returns all people including VP.
 * @returns {Object[]} [VP, ...data]
 */
function allPeople(){return [VP,...data];}

/**
 * Deterministically maps a person ID to one of 10 avatar colours.
 * Same ID always produces the same colour.
 * @param {string} id - Person ID string.
 * @returns {string} Hex colour e.g. "#ff6b35"
 */
function avatarColor(id){
  const colors=['#ff6b35','#34d399','#60a5fa','#a78bfa','#fbbf24','#f472b6','#22d3ee','#f87171','#86efac','#fdba74'];
  let h=0; for(let i=0;i<id.length;i++) h=(h*31+id.charCodeAt(i))&0xffff;
  return colors[h%colors.length];
}

/**
 * Returns up to 2 uppercase initials from a full name.
 * @param {string} name - Full name e.g. "Marc Eric Deschambault"
 * @returns {string} e.g. "ME"
 */
function initials(name){
  const p=name.trim().split(/\s+/);
  return (p[0]?.[0]||'')+(p[1]?.[0]||'');
}

/**
 * Reads all checked checkbox values inside a container element.
 * @param {string} id - Container element ID.
 * @returns {string[]} Array of checked input values.
 */
function gChk(id){return [...document.querySelectorAll(`#${id} input:checked`)].map(c=>c.value);}

/**
 * Sets checked state of checkboxes inside a container based on a values array.
 * @param {string} id - Container element ID.
 * @param {string[]} v - Array of values that should be checked.
 */
function sChk(id,v){document.querySelectorAll(`#${id} input`).forEach(c=>{c.checked=v.includes(c.value);});}

/**
 * Generates a random unique task ID prefixed with "tk_".
 * @returns {string} e.g. "tk_4xk9m2"
 */
function gTaskId(){ return 'tk_'+Math.random().toString(36).substr(2,7); }

/**
 * Shows a toast notification at the bottom-right of the screen.
 * Auto-dismisses after ~3 seconds with a fade-out animation.
 * @param {string} msg - Message to display.
 * @param {boolean} [isDanger=false] - If true, renders in red (error style).
 */
function showFlash(msg, isDanger) {
  const el = document.createElement('div');
  el.className = 'hor-flash' + (isDanger ? ' danger' : '');
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 400); }, 2800);
}

/**
 * Returns all trainers from the global `data` array.
 * Includes anyone in the training or sac department, or with assigned programs.
 * Excludes exec-type people (VP).
 * @returns {Object[]} Filtered array of trainer person objects.
 */
function getTrainers() {
  return data.filter(p =>
    p.type !== 'exec' &&
    (p.dept === 'training' || p.dept === 'sac' || (p.programs && p.programs.length > 0))
  );
}
