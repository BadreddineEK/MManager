/* ═══════════════════════════════════════════════════════════
   auth.js — Login, logout, restauration de session
   DOIT être chargé EN DERNIER (dépend de tous les autres modules)
═══════════════════════════════════════════════════════════ */

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
    const initials = (payload.email || 'U')[0].toUpperCase();
    document.getElementById('user-avatar').textContent       = initials;
    document.getElementById('user-name-display').textContent = payload.email || '—';
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
(function restoreSession() {
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
    }
  } catch (e) {
    localStorage.clear();
  }
})();
