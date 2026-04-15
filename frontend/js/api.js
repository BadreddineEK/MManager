/* ═══════════════════════════════════════════════════════════
   api.js — Configuration API, état global, apiFetch, progress
═══════════════════════════════════════════════════════════ */

// En dev (fichier ouvert directement) → nginx dev sur port 8080
// En prod (servi par Nginx) → URL relative /api (même origine)
const API = (location.protocol === 'file:' || location.hostname === 'localhost')
  ? 'http://localhost:8080/api'
  : '/api';

let accessToken  = localStorage.getItem('access')  || '';
let refreshToken = localStorage.getItem('refresh') || '';

// ── État global partagé entre modules ────────────────────────────────────────
let allFamilies    = [];
let allChildren    = [];
let schoolYears    = [];
let allMembers     = [];
let membershipYears = [];
let allCampaigns   = [];

// ── Progress bar ──────────────────────────────────────────────────────────────
let _progressTimer = null;

function showProgress() {
  const el = document.getElementById('top-progress');
  el.classList.remove('hidden');
  clearTimeout(_progressTimer);
}

function hideProgress() {
  _progressTimer = setTimeout(() => {
    document.getElementById('top-progress').classList.add('hidden');
  }, 300);
}

// ── apiFetch ──────────────────────────────────────────────────────────────────
async function apiFetch(path, method = 'GET', body = null) {
  showProgress();
  const opts = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
    },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API}${path}`, opts);
  hideProgress();
  if (res.status === 401) { logout(); return null; }
  if (res.status === 403) {
    // Vérifier si c'est un blocage plan (pas un manque de rôle)
    try {
      const clone = res.clone();
      const d = await clone.json();
      const msg = d.detail || '';
      if (msg.includes("plan") || msg.includes("module") || msg.includes("inclus")) {
        _showPlanUpgradeToast(msg);
      }
    } catch(e) {}
  }
  return res;
}

function _showPlanUpgradeToast(msg) {
  // Afficher un toast "upgrade" non intrusif
  const existing = document.getElementById('plan-upgrade-toast');
  if (existing) existing.remove();
  const el = document.createElement('div');
  el.id = 'plan-upgrade-toast';
  el.style.cssText = `
    position:fixed; bottom:80px; left:50%; transform:translateX(-50%);
    background:#1e40af; color:#fff; padding:12px 20px; border-radius:12px;
    font-size:14px; z-index:9999; max-width:90vw; text-align:center;
    box-shadow:0 4px 20px rgba(0,0,0,0.3); display:flex; gap:12px; align-items:center;
  `;
  el.innerHTML = `
    <span>🔒 Fonctionnalité réservée à un plan supérieur</span>
    <a href="https://nidham.fr/#pricing" target="_blank"
       style="background:#fff;color:#1e40af;padding:4px 12px;border-radius:8px;font-weight:600;text-decoration:none;white-space:nowrap;">
      Upgrader
    </a>
    <button onclick="this.parentElement.remove()" style="background:none;border:none;color:#fff;font-size:18px;cursor:pointer;padding:0">×</button>
  `;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 8000);
}

/**
 * api(path, method, body) — wrapper qui parse le JSON et throw sur erreur HTTP.
 * Usage: const data = await api('/school/classes/');
 */
async function api(path, method = 'GET', body = null) {
  const res = await apiFetch(path, method, body);
  if (!res) throw new Error('Non authentifié');
  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try { const d = await res.json(); detail = d.detail || d.error || JSON.stringify(d); } catch(e) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}
