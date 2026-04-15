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
  _applyModuleVisibility(modules);
}

function _applyModuleVisibility(modules) {
  if (!modules || modules.length === 0) return;

  var groupMap = { 'school': 'nav-school', 'membership': 'nav-membership' };
  for (var mod in groupMap) {
    var el = document.getElementById(groupMap[mod]);
    if (!el) continue;
    var locked = modules.indexOf(mod) === -1;
    el.classList.toggle('nav-module-locked', locked);
    el.title = locked ? 'Module non inclus dans votre plan' : '';
  }

  var itemMap = {
    'treasury': 'nav-treasury', 'campaigns': 'nav-campaigns',
    'staff': 'nav-staff', 'audit': 'nav-audit', 'import': 'nav-import'
  };
  for (var mod2 in itemMap) {
    var el2 = document.getElementById(itemMap[mod2]);
    if (!el2) continue;
    var locked2 = modules.indexOf(mod2) === -1;
    el2.classList.toggle('nav-module-locked', locked2);
    el2.title = locked2 ? 'Module non inclus dans votre plan' : '';
  }
}

function isPlanModuleAllowed(module) {
  if (!currentPlan) return true;
  var modules = (currentPlan.modules || []).map(function(m){ return m.toLowerCase(); });
  if (modules.length === 0) return true;
  return modules.indexOf(module.toLowerCase()) !== -1;
}
