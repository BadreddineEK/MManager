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
    checkOnboardingStatus();  // Onboarding si 1ère config
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

// ── Slug mosquée courant (depuis JWT) ────────────────────────────────────────
function getMosqueSlug() {
  try {
    const token = localStorage.getItem('access');
    if (!token) return '';
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.mosque_slug || '';
  } catch (e) { return ''; }
}

// ── Onboarding : check 1ère configuration ───────────────────────────────────
async function checkOnboardingStatus() {
  try {
    // Seulement pour les ADMIN
    const token = localStorage.getItem('access');
    if (!token) return;
    const payload = JSON.parse(atob(token.split('.')[1]));
    if (payload.role !== 'ADMIN') return;

    const res = await apiFetch('/settings/status/');
    if (!res || !res.ok) return;
    const data = await res.json();

    if (!data.configured) {
      // 1ère connexion → afficher bannière + aller sur onboarding
      _showOnboardingBanner();
      showSection('import');
      // Activer l'onglet "Paramètres mosquée" en premier
      if (typeof switchImportTab === 'function') switchImportTab('setup');
    }
  } catch (e) { /* silencieux */ }
}

function _showOnboardingBanner() {
  const existing = document.getElementById('onboarding-welcome-banner');
  if (existing) { existing.classList.remove('hidden'); return; }
  const banner = document.createElement('div');
  banner.id = 'onboarding-welcome-banner';
  banner.innerHTML = `
    <div style="
      background: linear-gradient(135deg, rgba(167,139,250,.15), rgba(96,165,250,.1));
      border: 1.5px solid var(--purple);
      border-radius: 14px;
      padding: 20px 24px;
      margin-bottom: 20px;
      display: flex; align-items: flex-start; gap: 16px;
    ">
      <span style="font-size:2rem;flex-shrink:0;">🎉</span>
      <div>
        <div style="font-weight:800;font-size:1.05rem;margin-bottom:6px;">Bienvenue sur Nidham Manager !</div>
        <div style="font-size:.88rem;color:var(--muted);line-height:1.6;">
          Avant de commencer, configurez votre mosquée en 2 minutes :<br>
          <strong>1.</strong> Remplissez les paramètres ci-dessous (nom, année scolaire, tarifs)<br>
          <strong>2.</strong> Importez vos données existantes si besoin (adhérents, familles, trésorerie)
        </div>
        <button onclick="document.getElementById('onboarding-welcome-banner').classList.add('hidden');localStorage.setItem('onboarding_banner_dismissed','1');"
          style="margin-top:10px;background:none;border:1px solid var(--border);border-radius:8px;padding:4px 12px;font-size:.8rem;cursor:pointer;color:var(--muted);">
          Fermer
        </button>
      </div>
    </div>`;
  const section = document.getElementById('section-import');
  if (section) section.insertBefore(banner, section.firstChild.nextSibling);
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
      checkOnboardingStatus();  // Onboarding si 1ère config
      loadCurrentPlan();  // Plan enforcement
    } else {
      localStorage.clear();
      setTimeout(()=>{ if(typeof toast==='function') toast('Session expirée, veuillez vous reconnecter.','warning',5000); },200);
    }
  } catch (e) {
    localStorage.clear();
  }
})();
