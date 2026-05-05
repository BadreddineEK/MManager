/**
 * import.js — Onboarding & import de données en masse (CSV)
 * ======================================================
 * Trois types : transactions bancaires, adhérents, école coranique
 *
 * Fonctionnement :
 *  1. Sélectionner le type d'import (onglets)
 *  2. Choisir le fichier + l'année cible
 *  3. "Simulation" cochée → dry_run=true → rapport sans écriture
 *  4. Décocher simulation → import réel avec rapport final
 */

// ─────────────────────────────────────────────────────────────────
// Initialisation de la section
// ─────────────────────────────────────────────────────────────────

async function initImportSection() {
  switchImportTab('setup');  // Paramètres mosquée = onglet par défaut
  await Promise.all([
    loadMembershipYearsForImport(),
    loadSchoolYearsForImport(),
    loadSettingsIntoSetupForm(),
  ]);
}

async function loadSettingsIntoSetupForm() {
  try {
    const res = await apiFetch('/settings/');
    if (!res || !res.ok) return;
    const d = await res.json();
    if (d.mosque_name)  document.getElementById('setup-mosque-name').value  = d.mosque_name;
    if (d.mosque_timezone) {
      const sel = document.getElementById('setup-timezone');
      if (sel) sel.value = d.mosque_timezone;
    }
    if (d.active_school_year_label) document.getElementById('setup-school-year').value   = d.active_school_year_label;
    if (d.school_levels?.length)    document.getElementById('setup-school-levels').value = d.school_levels.join(',');
    if (d.school_fee_default)       document.getElementById('setup-school-fee').value    = d.school_fee_default;
    if (d.school_fee_mode)          document.getElementById('setup-school-fee-mode').value = d.school_fee_mode;
    if (d.membership_fee_amount)    document.getElementById('setup-membership-fee').value = d.membership_fee_amount;
    if (d.membership_fee_mode)      document.getElementById('setup-membership-mode').value = d.membership_fee_mode;
  } catch(e) { /* silencieux */ }
}

async function saveSetupForm() {
  const errEl = document.getElementById('setup-form-error');
  const okEl  = document.getElementById('setup-form-success');
  errEl.classList.add('hidden');
  okEl.classList.add('hidden');

  const mosqueName = document.getElementById('setup-mosque-name').value.trim();
  if (!mosqueName) {
    errEl.textContent = 'Le nom de la mosquée est obligatoire.';
    errEl.classList.remove('hidden');
    return;
  }

  const levelsRaw = document.getElementById('setup-school-levels').value.trim();
  const levels = levelsRaw ? levelsRaw.split(',').map(l => l.trim().toUpperCase()).filter(Boolean) : ['NP','N1','N2','N3','N4','N5','N6'];

  const body = {
    mosque_name:              mosqueName,
    mosque_timezone:          document.getElementById('setup-timezone').value,
    active_school_year_label: document.getElementById('setup-school-year').value.trim(),
    school_levels:            levels,
    school_fee_default:       parseFloat(document.getElementById('setup-school-fee').value) || 0,
    school_fee_mode:          document.getElementById('setup-school-fee-mode').value,
    membership_fee_amount:    parseFloat(document.getElementById('setup-membership-fee').value) || 0,
    membership_fee_mode:      document.getElementById('setup-membership-mode').value,
  };

  const res = await apiFetch('/settings/', 'PUT', body);
  if (!res || !res.ok) {
    const err = await res?.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    errEl.classList.remove('hidden');
    return;
  }
  okEl.innerHTML = `
    ✅ Paramètres enregistrés !
    ${body.active_school_year_label ? `<br>🏫 Année scolaire <strong>${body.active_school_year_label}</strong> créée/activée.` : ''}
    ${body.membership_fee_amount > 0 ? `<br>🤝 Année de cotisation <strong>${new Date().getFullYear()}</strong> créée/activée (${body.membership_fee_amount} €).` : ''}
    <br><span style="font-size:.8rem;color:var(--muted);">Vous pouvez maintenant importer vos données ou commencer la saisie.</span>
  `;
  okEl.classList.remove('hidden');
  // Masquer la bannière si présente
  document.getElementById('onboarding-welcome-banner')?.classList.add('hidden');
  localStorage.setItem('onboarding_banner_dismissed', '1');
  toast('Paramètres enregistrés ✓', 'success');
  invalidateMosqueSettings();

  // Mettre à jour le nom affiché dans la sidebar
  const nameEl = document.getElementById('sidebar-mosque-name') || document.getElementById('dashboard-mosque-name');
  if (nameEl) nameEl.textContent = body.mosque_name;
}

function switchImportTab(tab) {
  const tabs = ['setup', 'transactions', 'members', 'school'];
  tabs.forEach(t => {
    const panel = document.getElementById(`import-panel-${t}`);
    const btn   = document.getElementById(`import-tab-${t}`);
    if (!panel || !btn) return;
    if (t === tab) {
      panel.classList.remove('hidden');
      btn.classList.add('btn-primary');
      btn.classList.remove('btn-outline');
    } else {
      panel.classList.add('hidden');
      btn.classList.remove('btn-primary');
      btn.classList.add('btn-outline');
    }
  });
  // Masquer le résultat précédent
  const res = document.getElementById('import-result');
  if (res) res.classList.add('hidden');
}

// ─────────────────────────────────────────────────────────────────
// Chargement des années (selects)
// ─────────────────────────────────────────────────────────────────

async function loadMembershipYearsForImport() {
  const sel = document.getElementById('import-members-year');
  if (!sel) return;
  try {
    const res = await apiFetch('/membership/years/');
    const data = res && res.ok ? await res.json() : null;
    const years = data ? (Array.isArray(data) ? data : (data.results || [])) : [];
    sel.innerHTML = years.length
      ? years.map(y => `<option value="${y.id}">${y.year}${y.is_active ? ' ✓' : ''}</option>`).join('')
      : '<option value="">Aucune année disponible</option>';
  } catch {
    sel.innerHTML = '<option value="">Erreur de chargement</option>';
  }
}

async function loadSchoolYearsForImport() {
  const sel = document.getElementById('import-school-year');
  if (!sel) return;
  try {
    const res = await apiFetch('/school/years/');
    const data = res && res.ok ? await res.json() : null;
    const years = data ? (Array.isArray(data) ? data : (data.results || [])) : [];
    sel.innerHTML = years.length
      ? years.map(y => `<option value="${y.id}">${y.label}${y.is_active ? ' ✓' : ''}</option>`).join('')
      : '<option value="">Aucune année disponible</option>';
  } catch {
    sel.innerHTML = '<option value="">Erreur de chargement</option>';
  }
}

// ─────────────────────────────────────────────────────────────────
// Lancement de l'import
// ─────────────────────────────────────────────────────────────────

async function runImport(type) {
  const mosqueId = getMosqueId();
  if (!mosqueId) {
    toast('Mosquée non identifiée — reconnectez-vous.', 'error');
    return;
  }

  let fileInput, dryRunCheck, extraField, extraValue;

  if (type === 'transactions') {
    fileInput   = document.getElementById('import-tx-file');
    dryRunCheck = document.getElementById('import-tx-dryrun');
  } else if (type === 'members') {
    fileInput   = document.getElementById('import-members-file');
    dryRunCheck = document.getElementById('import-members-dryrun');
    extraField  = 'membership_year';
    extraValue  = document.getElementById('import-members-year')?.value;
  } else if (type === 'school') {
    fileInput   = document.getElementById('import-school-file');
    dryRunCheck = document.getElementById('import-school-dryrun');
    extraField  = 'school_year';
    extraValue  = document.getElementById('import-school-year')?.value;
  }

  if (!fileInput?.files?.length) {
    toast('Sélectionnez un fichier CSV ou Excel.', 'error');
    return;
  }
  if (extraField && !extraValue) {
    toast('Sélectionnez une année cible.', 'error');
    return;
  }

  const file    = fileInput.files[0];
  const dryRun  = dryRunCheck?.checked ?? true;
  const endpoint = `/api/import/${type}/`;

  const form = new FormData();
  form.append('file', file);
  form.append('mosque_id', mosqueId);
  form.append('dry_run', dryRun ? 'true' : 'false');
  if (extraField) form.append(extraField, extraValue);

  showProgress();
  try {
    const result = await apiPostForm(endpoint, form);
    renderImportResult(result, type, dryRun);
  } catch (err) {
    hideProgress();
    toast(err.message || 'Erreur lors de l\'import.', 'error');
  }
  hideProgress();
}

// ─────────────────────────────────────────────────────────────────
// Affichage du résultat
// ─────────────────────────────────────────────────────────────────

function renderImportResult(data, type, dryRun) {
  const container = document.getElementById('import-result');
  const header    = document.getElementById('import-result-header');
  const body      = document.getElementById('import-result-body');
  if (!container || !header || !body) return;

  container.classList.remove('hidden');

  const labels = { transactions: 'Transactions', members: 'Adhérents', school: 'École' };
  const mode   = dryRun ? '🔍 Simulation' : '✅ Import réel';
  header.innerHTML = `<span>${mode} — ${labels[type] || type}</span>`;

  let html = '';

  // Résumé
  if (dryRun && data.would_create !== undefined) {
    if (typeof data.would_create === 'object') {
      html += `<div class="import-summary import-summary-dry">`;
      html += `<div class="import-summary-title">📋 Ce qui serait importé</div>`;
      html += `<ul>`;
      for (const [k, v] of Object.entries(data.would_create)) {
        html += `<li><strong>${v}</strong> ${k}</li>`;
      }
      html += `</ul>`;
    } else {
      html += `<div class="import-summary import-summary-dry">`;
      html += `<div class="import-summary-title">📋 <strong>${data.would_create}</strong> lignes seraient importées</div>`;
    }
    html += `<div style="margin-top:8px;font-size:0.82rem;color:var(--text-secondary);">`;
    html += `Lignes ignorées : <strong>${data.skipped ?? 0}</strong>`;
    html += `&nbsp;·&nbsp;Décochez "Simulation" puis relancez pour importer réellement.`;
    html += `</div></div>`;
  } else if (!dryRun && data.imported !== undefined) {
    html += `<div class="import-summary import-summary-ok">`;
    html += `<div class="import-summary-title">✅ Import terminé</div>`;
    if (typeof data.imported === 'object') {
      html += `<ul>`;
      for (const [k, v] of Object.entries(data.imported)) {
        html += `<li><strong>${v}</strong> ${k} importés</li>`;
      }
      html += `</ul>`;
    } else {
      html += `<p><strong>${data.imported}</strong> ligne(s) importée(s).</p>`;
    }
    html += `<div style="margin-top:8px;font-size:0.82rem;color:var(--text-secondary);">`;
    html += `Lignes ignorées : <strong>${data.skipped ?? 0}</strong>`;
    html += `</div></div>`;
  }

  // Erreurs détaillées
  const errors = data.errors || [];
  if (errors.length > 0) {
    html += `<div style="margin-top:14px;">`;
    html += `<div style="font-weight:600;color:var(--danger);margin-bottom:8px;">`;
    html += `⚠️ ${errors.length} avertissement${errors.length > 1 ? 's' : ''}`;
    html += `</div>`;
    html += `<div class="import-errors-table-wrap">`;
    html += `<table class="table" style="font-size:0.8rem;">`;
    html += `<thead><tr><th>Ligne</th><th>Champ</th><th>Message</th></tr></thead><tbody>`;
    errors.slice(0, 100).forEach(e => {
      html += `<tr>
        <td style="white-space:nowrap;">${e.row ?? '—'}</td>
        <td><code>${e.field ?? '—'}</code></td>
        <td>${escapeHtml(e.message ?? '')}</td>
      </tr>`;
    });
    if (errors.length > 100) {
      html += `<tr><td colspan="3" style="text-align:center;color:var(--text-secondary);">… et ${errors.length - 100} autres</td></tr>`;
    }
    html += `</tbody></table></div></div>`;
  } else if (Object.keys(data).length > 0) {
    html += `<p style="color:var(--success);margin-top:10px;font-size:0.85rem;">Aucun avertissement. ✓</p>`;
  }

  body.innerHTML = html;

  // Scroll vers le résultat
  container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ─────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────

function getMosqueId() {
  try {
    const token = localStorage.getItem('access');
    if (!token) return null;
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.mosque_id || null;
  } catch {
    return null;
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * apiPostForm — envoie un FormData via fetch avec le token JWT.
 * Distinct de apiPost (qui envoie du JSON).
 */
async function apiPostForm(url, formData) {
  const token = localStorage.getItem('access');
  const res = await fetch(url, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = json.detail || json.error || `Erreur HTTP ${res.status}`;
    throw new Error(msg);
  }
  return json;
}
