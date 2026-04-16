/* ═══════════════════════════════════════════════════════════
   plan.js — Chargement du plan, enforcement UI, bannière essai
   Dépend de : api.js
   Chargé avant : auth.js
═══════════════════════════════════════════════════════════ */

let currentPlan = null;

async function loadCurrentPlan() {
  try {
    const res = await apiFetch('/settings/plan/');
    if (!res || !res.ok) return;
    currentPlan = await res.json();
    _applyPlanToUI(currentPlan);
  } catch (e) {
    console.warn('[plan] Impossible de charger le plan', e);
  }
}

function _applyPlanToUI(plan) {
  if (!plan) return;

  const badge = document.getElementById('plan-badge');
  if (badge) {
    badge.textContent = plan.plan_name || 'Free';
    badge.className   = 'plan-badge plan-badge-' + (plan.plan_name || 'free').toLowerCase();
  }

  const brandName = document.getElementById('sidebar-mosque-name');
  if (brandName && plan.mosque_name) {
    brandName.textContent = plan.mosque_name;
    document.title = plan.mosque_name + ' — Nidham';
  }

  const banner    = document.getElementById('plan-banner');
  const trialInfo = document.getElementById('plan-trial-info');
  if (banner && trialInfo) {
    if (plan.status === 'trial' && plan.days_remaining !== undefined) {
      const d = plan.days_remaining;
      trialInfo.textContent = d > 0
        ? '⏳ Essai : ' + d + ' jour' + (d > 1 ? 's' : '') + ' restant' + (d > 1 ? 's' : '')
        : '⚠️ Essai expiré';
      trialInfo.className = d <= 3 ? 'trial-urgent' : 'trial-info';
      banner.classList.remove('hidden');
    } else if (plan.status === 'expired') {
      trialInfo.textContent = '🔴 Abonnement expiré';
      trialInfo.className = 'trial-urgent';
      banner.classList.remove('hidden');
    } else {
      banner.classList.add('hidden');
    }
  }

  const modules = (plan.modules || []).map(function(m){ return m.toLowerCase(); });
  // Normaliser : treasury_full/treasury_fec → treasury, school_basic/school_full → school
  const normalized = [];
  modules.forEach(function(m) {
    normalized.push(m);
    if (m.startsWith('treasury')) { normalized.push('treasury'); normalized.push('campaigns'); }
    if (m.startsWith('school'))   normalized.push('school');
    if (m === 'core')             normalized.push('membership');
  });
  _applyModuleVisibility(normalized);
}

function _applyModuleVisibility(modules) {
  if (!modules || modules.length === 0) return;

  // Ces items sont toujours accessibles pour l'ADMIN, peu importe le plan
  var ALWAYS_VISIBLE = ['users', 'settings', 'import', 'audit'];

  // Modules pilotés par le plan
  var allMap = {
    'school':      'nav-school',
    'membership':  'nav-membership',
    'treasury':    'nav-treasury',
    'campaigns':   'nav-campaigns',
    'staff':       'nav-staff',
  };
  for (var mod in allMap) {
    var el = document.getElementById(allMap[mod]);
    if (!el) continue;
    var locked = modules.indexOf(mod) === -1;
    el.classList.toggle('nav-module-locked', locked);
    el.title = locked ? 'Module non inclus dans votre plan' : '';
  }

  // Toujours débloquer les items d'administration
  ALWAYS_VISIBLE.forEach(function(id) {
    var el = document.getElementById('nav-' + id);
    if (!el) return;
    el.classList.remove('nav-module-locked');
    el.title = '';
  });
}

function isPlanModuleAllowed(module) {
  if (!currentPlan) return true;
  var modules = (currentPlan.modules || []).map(function(m){ return m.toLowerCase(); });
  if (modules.length === 0) return true;
  return modules.indexOf(module.toLowerCase()) !== -1;
}
