// ==================== AUTH ====================
// Supabase Auth wrapper — login, logout, session, role

let _authUser    = null; // supabase auth user object
let _authRole    = null; // 'admin' | 'formateur' | 'hr' | 'agent'
let _authTrainerId = null; // linked instructor id (for formateurs)

/**
 * Returns true if the current user is an admin.
 */
function authIsAdmin()     { return _authRole === 'admin'; }
function authIsHR()        { return _authRole === 'hr'; }
function authIsFormateur() { return _authRole === 'formateur'; }
function authIsAgent()     { return _authRole === 'agent'; }

/**
 * Returns true if logged in.
 */
function authIsLoggedIn() { return !!_authUser; }

/**
 * Returns the linked instructor id for a formateur user, or null for admins.
 */
function authTrainerId() { return _authTrainerId; }

/**
 * Initialises auth: checks existing session, loads role.
 * Resolves when done (whether logged in or not).
 */
async function authInit() {
  const { data: { session } } = await db.auth.getSession();
  if (session) {
    _authUser = session.user;
    await _authLoadRole();
  }

  // Listen for future auth changes (login/logout)
  db.auth.onAuthStateChange(async (event, session) => {
    if (event === 'SIGNED_IN' && session) {
      _authUser = session.user;
      await _authLoadRole();
      _authHideLoginScreen();
      location.reload(); // clean reload to apply RLS + role restrictions
    } else if (event === 'SIGNED_OUT') {
      _authUser = null;
      _authRole = null;
      _authTrainerId = null;
      _authShowLoginScreen();
    }
  });
}

/**
 * Loads the role row from user_profiles for the current user.
 */
async function _authLoadRole() {
  if (!_authUser) return;
  const { data, error } = await db
    .from('user_profiles')
    .select('role, instructor_id')
    .eq('user_id', _authUser.id)
    .single();

  if (error || !data) {
    // No profile found — deny access by default (no role = no access)
    _authRole      = null;
    _authTrainerId = null;
    console.warn('user_profiles lookup failed:', error?.message);
  } else {
    _authRole      = data.role || null;
    _authTrainerId = data.instructor_id || null;
  }
}

/**
 * Signs in with email + password.
 * Returns { error } or { user }.
 */
async function authLogin(email, password) {
  const { data, error } = await db.auth.signInWithPassword({ email, password });
  if (error) return { error };
  return { user: data.user };
}

/**
 * Signs out the current user.
 */
async function authLogout() {
  await db.auth.signOut();
}

// ─── Login screen ────────────────────────────────────────────────────────────

function _authShowLoginScreen() {
  let screen = document.getElementById('auth-screen');
  if (!screen) {
    screen = document.createElement('div');
    screen.id = 'auth-screen';
    document.body.appendChild(screen);
  }
  screen.style.display = 'flex';
  screen.innerHTML = `
    <div class="auth-box">
      <div class="auth-logo">
        <div style="font-family:'Space Mono',monospace;font-size:10px;letter-spacing:2px;color:var(--a);text-transform:uppercase;margin-bottom:4px;">Training Division</div>
        <div style="font-size:28px;font-weight:700;color:var(--t);">XGuard</div>
      </div>
      <div id="auth-error" style="display:none;background:rgba(239,68,68,0.12);border:1px solid #ef4444;border-radius:6px;padding:8px 12px;font-size:12px;color:#f87171;margin-bottom:12px;"></div>
      <label style="font-size:11px;color:var(--td);margin-bottom:4px;display:block;">Courriel</label>
      <input id="auth-email" type="email" placeholder="vous@xguard.ca"
        style="width:100%;padding:10px 12px;background:var(--sh);border:1px solid var(--b);border-radius:8px;color:var(--t);font-size:13px;margin-bottom:12px;box-sizing:border-box;outline:none;"
        onkeydown="if(event.key==='Enter')authSubmitLogin()"/>
      <label style="font-size:11px;color:var(--td);margin-bottom:4px;display:block;">Mot de passe</label>
      <input id="auth-password" type="password" placeholder="••••••••"
        style="width:100%;padding:10px 12px;background:var(--sh);border:1px solid var(--b);border-radius:8px;color:var(--t);font-size:13px;margin-bottom:20px;box-sizing:border-box;outline:none;"
        onkeydown="if(event.key==='Enter')authSubmitLogin()"/>
      <button id="auth-btn" onclick="authSubmitLogin()"
        style="width:100%;padding:12px;background:var(--a);color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;transition:opacity 0.15s;">
        Se connecter
      </button>
      <div style="margin-top:16px;font-size:11px;color:var(--td);text-align:center;opacity:0.6;">
        Accès sur invitation seulement
      </div>
    </div>`;

  // Focus email field
  setTimeout(() => {
    const el = document.getElementById('auth-email');
    if (el) el.focus();
  }, 50);
}

function _authHideLoginScreen() {
  const screen = document.getElementById('auth-screen');
  if (screen) screen.style.display = 'none';
}

async function authSubmitLogin() {
  const email    = (document.getElementById('auth-email')?.value || '').trim();
  const password = document.getElementById('auth-password')?.value || '';
  const btn      = document.getElementById('auth-btn');
  const errDiv   = document.getElementById('auth-error');

  if (!email || !password) {
    _authShowError('Veuillez remplir tous les champs.');
    return;
  }

  btn.textContent  = 'Connexion…';
  btn.disabled     = true;
  errDiv.style.display = 'none';

  const { error } = await authLogin(email, password);
  if (error) {
    _authShowError(error.message === 'Invalid login credentials'
      ? 'Courriel ou mot de passe incorrect.'
      : error.message);
    btn.textContent = 'Se connecter';
    btn.disabled    = false;
  }
  // On success, onAuthStateChange fires → reloads page
}

function _authShowError(msg) {
  const errDiv = document.getElementById('auth-error');
  if (!errDiv) return;
  errDiv.textContent   = msg;
  errDiv.style.display = 'block';
}

/**
 * Renders the user chip in the header (name + logout button).
 * Called from render() after login.
 */
function authRenderUserChip() {
  if (!_authUser) return;
  const existing = document.getElementById('auth-user-chip');
  if (existing) return; // already rendered

  const chip = document.createElement('div');
  chip.id = 'auth-user-chip';
  const email     = _authUser.email || '';
  const shortName = email.split('@')[0];
  const roleLabel = _authRole === 'admin' ? '🔑 Admin' : _authRole === 'hr' ? '🏢 RH' : _authRole === 'agent' ? '📞 Agent' : '👤 Formateur';

  chip.innerHTML = `
    <span style="font-size:11px;color:var(--td);">${roleLabel}</span>
    <span style="font-size:11px;color:var(--t);font-weight:600;">${shortName}</span>
    <button onclick="authLogout()" title="Déconnexion"
      style="background:none;border:1px solid var(--b);border-radius:5px;color:var(--td);padding:3px 8px;font-size:10px;cursor:pointer;">
      ⎋ Quitter
    </button>`;
  document.querySelector('header')?.appendChild(chip);
}
