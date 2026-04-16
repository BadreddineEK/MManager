/* ═══════════════════════════════════════════════════════════
   auth.js — Login, logout, restauration de session
   DOIT être chargé EN DERNIER (dépend de tous les autres modules)
═══════════════════════════════════════════════════════════ */

// ── Retour vers le portail ────────────────────────────────────────────────────
function _goToPortal() {
  const hn = location.hostname;
  if (hn.endsWith('.nidham.local')) location.href = 'http://nidham.local:8080/portal.html';
  else if (hn.endsWith('.nidham.fr'))  location.href = 'https://nidham.fr/';
  else                                 location.href = '/portal.html';
}

// ── Verification tenant au demarrage ─────────────────────────────────────────
async function _checkTenant() {
  const hn = location.hostname;
  if (hn === 'localhost' || hn === '127.0.0.1' || /^\d+\.\d+\.\d+\.\d+$/.test(hn)) return true;
  try {
    const res = await fetch('/health/', { method: 'GET' });
    if (!res.ok) throw new Error('tenant not found');
    return true;
  } catch (e) {
    const screen = document.getElementById('tenant-error-screen');
    const msg    = document.getElementById('tenant-error-domain');
    if (screen) screen.classList.remove('hidden');
    if (msg)    msg.textContent = 'Sous-domaine introuvable : ' + hn;
    return false;
  }
}

async function login() {
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const errEl    = document.getElementById('login-error');
  errEl.classList.add('hidden');

  try {
    const res = await fetch(`${API}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error('Identifiants incorrects');
    const data = await res.json();
    accessToken  = data.access;
    refreshToken = data.refresh;
    localStorage.setItem('access',  accessToken);
    localStorage.setItem('refresh', refreshToken);
    _applyJwtToUI(accessToken);
    _showApp();
    loadDashboard();
    loadCurrentUser();  // RBAC
    loadCurrentPlan();  // Plan enforcement
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}

async function logout() {
  await apiFetch('/auth/logout/', 'POST', { refresh: refreshToken }).catch(() => {});
  localStorage.clear();
  const hn = location.hostname;
  if (hn.endsWith('.nidham.local'))     location.href = 'http://nidham.local:8080/';
  else if (hn.endsWith('.nidham.fr'))   location.href = 'https://nidham.fr/';
  else if (/^192\.168\.|^10\.|^172\.(1[6-9]|2[0-9]|3[01])\./.test(hn))
                                        location.href = 'http://' + hn + ':8080/';
  else                                  location.reload();
}

// ── Afficher app, masquer login ───────────────────────────────────────────────
function _showApp() {
  document.getElementById('login-screen').classList.add('hidden');
  document.getElementById('app-screen').classList.remove('hidden');
}

// ── Helpers internes ──────────────────────────────────────────────────────────
function _applyJwtToUI(token) {
  try {
    const payload  = JSON.parse(atob(token.split('.')[1]));
    const displayName = payload.username_display || payload.email || 'Utilisateur';
    const initials = displayName[0].toUpperCase();
    document.getElementById('user-avatar').textContent       = initials;
    document.getElementById('user-name-display').textContent = displayName;
    const roleLabels = {
      ADMIN: 'Admin', TRESORIER: 'Trésorier',
      ECOLE_MANAGER: 'École Manager', TEACHER: 'Professeur',
      SECRETARY: 'Secrétaire', VIEWER: 'Lecture seule',
    };
    document.getElementById('user-role-display').textContent =
      roleLabels[payload.role] || payload.role || '—';
    if (payload.mosque_slug) {
      const el = document.getElementById('dashboard-mosque-name');
      if (el) el.textContent = payload.mosque_slug;
    }
  } catch (e) { /* token malformé */ }
}

// ── Auto-login : hash URL ou localStorage ────────────────────────────────────
(async function restoreSession() {
  // 0. Verifier que le tenant existe
  const tenantOk = await _checkTenant();
  if (!tenantOk) return;

  // 1. Lire tokens depuis #access=...&refresh=... (injecté par portal.html)
  if (location.hash && location.hash.length > 1) {
    const hp = new URLSearchParams(location.hash.slice(1));
    const ha = hp.get('access');
    const hr = hp.get('refresh');
    if (ha) {
      accessToken  = ha;
      refreshToken = hr || '';
      localStorage.setItem('access',  accessToken);
      localStorage.setItem('refresh', refreshToken);
      history.replaceState(null, '', location.pathname + location.search);
    }
  }

  // 2. Valider le token
  if (!accessToken) return;
  try {
    const payload   = JSON.parse(atob(accessToken.split('.')[1]));
    const isExpired = payload.exp * 1000 < Date.now();
    if (!isExpired) {
      _applyJwtToUI(accessToken);
      _showApp();
      loadDashboard();
      loadCurrentUser();  // RBAC
      loadCurrentPlan();  // Plan enforcement
    } else {
      localStorage.clear();
      setTimeout(()=>{ if(typeof toast==='function') toast('Session expirée, veuillez vous reconnecter.','warning',5000); },200);
    }
  } catch (e) {
    localStorage.clear();
  }
})();
