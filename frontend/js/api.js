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
  return res;
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
