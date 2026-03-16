/* ═══════════════════════════════════════════════════════════
   settings.js — Paramètres de la mosquée, KPI screen
═══════════════════════════════════════════════════════════ */

async function loadSettings() {
  const alert = document.getElementById('settings-alert');
  alert.textContent = '';
  const res = await apiFetch('/settings/');
  if (!res) return;
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert.innerHTML = `<div class="alert alert-error">${err.detail || 'Erreur chargement paramètres'}</div>`;
    return;
  }
  const data = await res.json();
  document.getElementById('s-mosque-name').value     = data.mosque_name       || '';
  document.getElementById('s-mosque-timezone').value = data.mosque_timezone   || 'Europe/Paris';
  document.getElementById('s-mosque-slug').value     = data.mosque_slug       || '';
  document.getElementById('s-school-year').value     = data.active_school_year_label || '';
  document.getElementById('s-school-fee').value      = data.school_fee_default || 0;
  document.getElementById('s-school-fee-mode').value = data.school_fee_mode   || 'annual';
  const levels = Array.isArray(data.school_levels)
    ? data.school_levels.join(',')
    : (data.school_levels || '');
  document.getElementById('s-school-levels').value      = levels;
  document.getElementById('s-membership-fee').value     = data.membership_fee_amount || 0;
  document.getElementById('s-membership-mode').value    = data.membership_fee_mode   || 'per_person';
  document.getElementById('s-receipt-logo').value       = data.receipt_logo_url      || '';
  document.getElementById('s-receipt-address').value    = data.receipt_address        || '';
  document.getElementById('s-receipt-phone').value      = data.receipt_phone          || '';
  document.getElementById('s-receipt-legal').value      = data.receipt_legal_mention  || '';
  // KPI widgets
  document.getElementById('s-kpi-school').checked      = data.show_kpi_school     !== false;
  document.getElementById('s-kpi-membership').checked  = data.show_kpi_membership !== false;
  document.getElementById('s-kpi-treasury').checked    = data.show_kpi_treasury   !== false;
  document.getElementById('s-kpi-campaigns').checked   = data.show_kpi_campaigns  !== false;
  document.getElementById('s-kpi-refresh').value       = data.kpi_refresh_secs    || 60;
}

async function saveSettings() {
  const alert   = document.getElementById('settings-alert');
  alert.textContent = '';
  const levelsRaw = document.getElementById('s-school-levels').value;
  const levels    = levelsRaw.split(',').map(l => l.trim()).filter(Boolean);
  const payload = {
    mosque_name:              document.getElementById('s-mosque-name').value.trim(),
    mosque_timezone:          document.getElementById('s-mosque-timezone').value.trim(),
    active_school_year_label: document.getElementById('s-school-year').value.trim(),
    school_fee_default:       parseFloat(document.getElementById('s-school-fee').value)    || 0,
    school_fee_mode:          document.getElementById('s-school-fee-mode').value,
    school_levels:            levels,
    membership_fee_amount:    parseFloat(document.getElementById('s-membership-fee').value) || 0,
    membership_fee_mode:      document.getElementById('s-membership-mode').value,
    receipt_logo_url:         document.getElementById('s-receipt-logo').value.trim(),
    receipt_address:          document.getElementById('s-receipt-address').value.trim(),
    receipt_phone:            document.getElementById('s-receipt-phone').value.trim(),
    receipt_legal_mention:    document.getElementById('s-receipt-legal').value.trim(),
    show_kpi_school:          document.getElementById('s-kpi-school').checked,
    show_kpi_membership:      document.getElementById('s-kpi-membership').checked,
    show_kpi_treasury:        document.getElementById('s-kpi-treasury').checked,
    show_kpi_campaigns:       document.getElementById('s-kpi-campaigns').checked,
    kpi_refresh_secs:         parseInt(document.getElementById('s-kpi-refresh').value) || 60,
  };
  const res = await apiFetch('/settings/', 'PUT', payload);
  if (!res) return;
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    toast('Erreur : ' + JSON.stringify(err), 'error', 5000);
    return;
  }
  toast('Paramètres enregistrés ✓');
}

function openKPIScreen() {
  let slug = document.getElementById('s-mosque-slug').value.trim();
  if (!slug) {
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      slug = payload.mosque_slug || '';
    } catch (e) {}
  }
  if (!slug) {
    toast("Slug de mosquée introuvable — enregistrez d'abord les paramètres.", 'error', 4000);
    return;
  }
  localStorage.setItem('kpi_slug', slug);
  window.open('/kpi.html', '_blank');
}
