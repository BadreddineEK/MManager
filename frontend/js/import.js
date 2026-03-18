/**
 * import.js — Import de données en masse (CSV / Excel)
 * ======================================================
 * Trois types : transactions, members, school
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
  switchImportTab('transactions');
  await Promise.all([
    loadMembershipYearsForImport(),
    loadSchoolYearsForImport(),
  ]);
}

function switchImportTab(tab) {
  const tabs = ['transactions', 'members', 'school'];
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
