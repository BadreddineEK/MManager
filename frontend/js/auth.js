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
    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('app-screen').classList.remove('hidden');
    loadDashboard();
    loadCurrentUser(); // RBAC
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
  }
}

async function logout() {
  await apiFetch('/auth/logout/', 'POST', { refresh: refreshToken }).catch(() => {});
  localStorage.clear();
  location.reload();
}

// ── Helpers internes ──────────────────────────────────────────────────────────
function _applyJwtToUI(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const initials = (payload.email || 'U')[0].toUpperCase();
    document.getElementById('user-avatar').textContent        = initials;
    document.getElementById('user-name-display').textContent  = payload.email || '—';
    const roleLabels = {
      ADMIN: 'Admin', TRESORIER: 'Trésorier',
      ECOLE_MANAGER: 'École Manager', VIEWER: 'Lecture seule',
    };
    document.getElementById('user-role-display').textContent =
      roleLabels[payload.role] || payload.role || '—';
    if (payload.mosque_slug) {
      document.getElementById('dashboard-mosque-name').textContent = payload.mosque_slug;
    }
  } catch (e) { /* token malformé */ }
}

// ── Auto-login si token présent ───────────────────────────────────────────────
(function restoreSession() {
  if (!accessToken) return;
  try {
    const payload  = JSON.parse(atob(accessToken.split('.')[1]));
    const isExpired = payload.exp * 1000 < Date.now();
    if (!isExpired) {
      _applyJwtToUI(accessToken);
      document.getElementById('login-screen').classList.add('hidden');
      document.getElementById('app-screen').classList.remove('hidden');
      loadDashboard();
      loadCurrentUser(); // RBAC
    } else {
      localStorage.clear();
    }
  } catch (e) {
    localStorage.clear();
  }
})();
