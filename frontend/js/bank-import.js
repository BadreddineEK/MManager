/* ═══════════════════════════════════════════════════════════
   bank-import.js — Wizard import bancaire CSV (3 étapes)
   ═══════════════════════════════════════════════════════════
   Étape 1 : Upload fichier + paramètres basiques (séparateur, encodage, lignes à sauter)
   Étape 2 : Preview colonnes détectées + mapping vers les champs cibles
   Étape 3 : Import réel + option sauvegarder le profil + résultat
*/

let _bankImportFile     = null;  // File object
let _bankImportHeaders  = [];    // Colonnes détectées par le preview
let _bankImportProfiles = [];    // Profils sauvegardés

// ── Helper fetch multipart ─────────────────────────────────────────────────────
async function _bankApiFetch(path, formData) {
  showProgress();
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${accessToken}` },
    body: formData,
  });
  hideProgress();
  if (res.status === 401) { logout(); return null; }
  return res;
}

// ── Ouverture / reset ──────────────────────────────────────────────────────────
async function openBankImportModal() {
  _bankImportFile    = null;
  _bankImportHeaders = [];
  _bankWizardStep(1);
  document.getElementById('bk-file').value         = '';
  document.getElementById('bk-separator').value    = ';';
  document.getElementById('bk-encoding').value     = 'utf-8-sig';
  document.getElementById('bk-skip-rows').value    = '0';
  document.getElementById('bk-step1-error').textContent = '';
  document.getElementById('bk-step3-result').innerHTML  = '';
  document.getElementById('bk-save-profile').checked    = false;
  document.getElementById('bk-profile-name-row').classList.add('hidden');

  // Charger les profils sauvegardés
  await _loadBankProfiles();
  openModal('modal-bank-import');
}

function _bankWizardStep(n) {
  [1, 2, 3].forEach(i => {
    document.getElementById(`bk-step${i}`).classList.toggle('hidden', i !== n);
    const footer = document.getElementById(`bk-footer${i}`);
    if (footer) footer.classList.toggle('hidden', i !== n);
    const dot = document.getElementById(`bk-dot${i}`);
    if (dot) {
      dot.style.background = i < n ? 'var(--accent)' : i === n ? 'var(--accent)' : 'var(--border)';
      dot.style.color       = i <= n ? '#fff' : 'var(--muted)';
      dot.style.fontWeight  = i === n ? '700' : '400';
    }
  });
  const labels = {1: 'Fichier & paramètres', 2: 'Mapping colonnes', 3: 'Résultat'};
  const lbl = document.getElementById('bk-step-label');
  if (lbl) lbl.textContent = labels[n] || '';
}

// ── Profils ────────────────────────────────────────────────────────────────────
async function _loadBankProfiles() {
  const sel = document.getElementById('bk-profile-select');
  if (!sel) return;
  try {
    const res = await apiFetch('/import/bank/profiles/');
    if (res && res.ok) {
      _bankImportProfiles = await res.json();
      sel.innerHTML = '<option value="">— Nouveau mapping —</option>'
        + _bankImportProfiles.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
    }
  } catch { /* silencieux */ }
}

function onBankProfileChange() {
  const id = document.getElementById('bk-profile-select').value;
  if (!id) return;
  const p = _bankImportProfiles.find(x => String(x.id) === String(id));
  if (!p) return;
  document.getElementById('bk-separator').value = p.separator  || ';';
  document.getElementById('bk-encoding').value  = p.encoding   || 'utf-8-sig';
  document.getElementById('bk-skip-rows').value = p.skip_rows  ?? 0;
  toast(`Profil "${p.name}" chargé`, 'info', 2000);
}

// ── Étape 1 → 2 : Preview colonnes ────────────────────────────────────────────
async function bankImportPreview() {
  const fileInput = document.getElementById('bk-file');
  const errEl     = document.getElementById('bk-step1-error');
  errEl.textContent = '';

  if (!fileInput.files.length) {
    errEl.textContent = 'Sélectionnez un fichier CSV ou Excel.';
    return;
  }
  _bankImportFile = fileInput.files[0];

  const form = new FormData();
  form.append('file',      _bankImportFile);
  form.append('separator', document.getElementById('bk-separator').value);
  form.append('encoding',  document.getElementById('bk-encoding').value);
  form.append('skip_rows', document.getElementById('bk-skip-rows').value);

  const btn = document.getElementById('bk-btn-preview');
  btn.disabled = true;
  btn.textContent = '⏳ Analyse…';

  try {
    const res = await _bankApiFetch('/import/bank/preview/', form);
    if (!res || !res.ok) {
      const err = await res?.json().catch(() => ({}));
      errEl.textContent = err.detail || err.error || 'Erreur lors de l\'analyse du fichier.';
      return;
    }
    const data = await res.json();
    _bankImportHeaders = data.columns || [];
    _renderBankMappingStep(data);
    _bankWizardStep(2);
  } catch(e) {
    errEl.textContent = e.message || 'Erreur inattendue.';
  } finally {
    btn.disabled = false;
    btn.textContent = '→ Analyser le fichier';
  }
}

function _colOptions(required = false) {
  const blank = required ? '<option value="">— Choisir une colonne —</option>' : '<option value="">— (optionnel) —</option>';
  return blank + _bankImportHeaders.map(h => `<option value="${esc(h)}">${esc(h)}</option>`).join('');
}

function _autoSelect(sel, keywords) {
  const headers_lc = _bankImportHeaders.map(h => h.toLowerCase());
  for (const kw of keywords) {
    const idx = headers_lc.findIndex(h => h.includes(kw));
    if (idx >= 0) { sel.value = _bankImportHeaders[idx]; return; }
  }
}

function _renderBankMappingStep(data) {
  // Aperçu des 5 premières lignes
  const previewEl = document.getElementById('bk-preview-table');
  const rows = data.preview || [];
  if (rows.length && _bankImportHeaders.length) {
    let html = '<table style="font-size:0.75rem;width:100%;border-collapse:collapse;">';
    html += '<thead><tr>' + _bankImportHeaders.map(h => `<th style="padding:4px 8px;background:var(--bg-hover);border:1px solid var(--border);white-space:nowrap;">${esc(h)}</th>`).join('') + '</tr></thead>';
    html += '<tbody>';
    rows.forEach(row => {
      html += '<tr>' + _bankImportHeaders.map(h => `<td style="padding:3px 8px;border:1px solid var(--border);white-space:nowrap;max-width:160px;overflow:hidden;text-overflow:ellipsis;" title="${esc(row[h]||'')}">${esc(row[h] || '')}</td>`).join('') + '</tr>';
    });
    html += '</tbody></table>';
    previewEl.innerHTML = html;
  } else {
    previewEl.innerHTML = '<p style="color:var(--muted);font-size:0.82rem;">Aucun aperçu disponible.</p>';
  }

  // Remplir les selects de mapping
  const fields = ['bk-map-date','bk-map-label','bk-map-detail','bk-map-debit','bk-map-credit','bk-map-amount','bk-map-type','bk-map-ref'];
  fields.forEach(id => {
    const sel = document.getElementById(id);
    if (sel) sel.innerHTML = _colOptions(id === 'bk-map-date' || id === 'bk-map-label');
  });

  // Auto-détection intelligente
  _autoSelect(document.getElementById('bk-map-date'),   ['date', 'dat ']);
  _autoSelect(document.getElementById('bk-map-label'),  ['libelle', 'libellé', 'label', 'operat', 'désign', 'design']);
  _autoSelect(document.getElementById('bk-map-detail'), ['detail', 'détail', 'info', 'complement', 'complément']);
  _autoSelect(document.getElementById('bk-map-debit'),  ['debit', 'débit', 'sortie', 'montant débit']);
  _autoSelect(document.getElementById('bk-map-credit'), ['credit', 'crédit', 'entrée', 'montant crédit']);
  _autoSelect(document.getElementById('bk-map-amount'), ['montant', 'amount', 'valeur']);
  _autoSelect(document.getElementById('bk-map-type'),   ['type', 'nature']);
  _autoSelect(document.getElementById('bk-map-ref'),    ['ref', 'réf', 'reference', 'référence']);

  // Pré-remplir date_format, decimal_sep
  const profileId = document.getElementById('bk-profile-select').value;
  const p = _bankImportProfiles.find(x => String(x.id) === String(profileId));
  if (p) {
    document.getElementById('bk-date-format').value   = p.date_format  || '%d/%m/%Y';
    document.getElementById('bk-decimal-sep').value   = p.decimal_sep  || ',';
    document.getElementById('bk-direction-col').value = '';
  }

  document.getElementById('bk-step2-info').textContent =
    `${_bankImportHeaders.length} colonne(s) détectée(s) · ${data.total_rows || '?'} ligne(s) au total`;
}

// ── Étape 2 → 3 : Import ──────────────────────────────────────────────────────
async function bankImportRun() {
  const errEl = document.getElementById('bk-step2-error');
  errEl.textContent = '';

  const dateCol  = document.getElementById('bk-map-date').value;
  const labelCol = document.getElementById('bk-map-label').value;
  if (!dateCol || !labelCol) {
    errEl.textContent = 'Les colonnes Date et Libellé sont obligatoires.';
    return;
  }

  const form = new FormData();
  form.append('file',        _bankImportFile);
  form.append('separator',   document.getElementById('bk-separator').value);
  form.append('encoding',    document.getElementById('bk-encoding').value);
  form.append('skip_rows',   document.getElementById('bk-skip-rows').value);
  form.append('date_format', document.getElementById('bk-date-format').value);
  form.append('decimal_sep', document.getElementById('bk-decimal-sep').value);
  form.append('date_column',      dateCol);
  form.append('label_column',     labelCol);
  form.append('detail_column',    document.getElementById('bk-map-detail').value);
  form.append('debit_column',     document.getElementById('bk-map-debit').value);
  form.append('credit_column',    document.getElementById('bk-map-credit').value);
  form.append('amount_column',    document.getElementById('bk-map-amount').value);
  form.append('type_column',      document.getElementById('bk-map-type').value);
  form.append('reference_column', document.getElementById('bk-map-ref').value);

  // Sauvegarder le profil ?
  const saveProfile = document.getElementById('bk-save-profile').checked;
  const profileName = document.getElementById('bk-profile-name').value.trim();
  if (saveProfile) {
    if (!profileName) { errEl.textContent = 'Donnez un nom au profil.'; return; }
    form.append('save_profile', 'true');
    form.append('profile_name', profileName);
  }

  const btn = document.getElementById('bk-btn-import');
  btn.disabled = true;
  btn.textContent = '⏳ Import en cours…';

  _bankWizardStep(3);

  try {
    const res = await _bankApiFetch('/import/bank/', form);
    const data = res ? await res.json().catch(() => ({})) : {};
    _renderBankImportResult(data, res?.ok);
  } catch(e) {
    _renderBankImportResult({ error: e.message }, false);
  } finally {
    btn.disabled = false;
    btn.textContent = '✅ Importer';
  }
}

function _renderBankImportResult(data, ok) {
  const el = document.getElementById('bk-step3-result');
  if (!ok) {
    el.innerHTML = `<div class="alert alert-error">
      ❌ ${esc(data.detail || data.error || 'Erreur lors de l\'import')}
    </div>`;
    return;
  }

  const imported   = data.imported   ?? 0;
  const skipped    = data.skipped    ?? 0;
  const pending    = data.pending    ?? 0;
  const errors     = data.errors     || [];

  let html = `<div class="alert" style="background:var(--bg-success,#f0fdf4);border:1.5px solid var(--success,#16a34a);border-radius:10px;padding:16px 20px;">
    <div style="font-weight:700;font-size:1rem;color:var(--success,#16a34a);margin-bottom:10px;">✅ Import terminé</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;text-align:center;">
      <div style="background:#fff;border-radius:8px;padding:12px;border:1px solid var(--border);">
        <div style="font-size:1.6rem;font-weight:700;color:var(--success,#16a34a)">${imported}</div>
        <div style="font-size:0.78rem;color:var(--muted)">importées</div>
      </div>
      <div style="background:#fff;border-radius:8px;padding:12px;border:1px solid var(--border);">
        <div style="font-size:1.6rem;font-weight:700;color:var(--warning,#f59e0b)">${pending}</div>
        <div style="font-size:0.78rem;color:var(--muted)">à valider</div>
      </div>
      <div style="background:#fff;border-radius:8px;padding:12px;border:1px solid var(--border);">
        <div style="font-size:1.6rem;font-weight:700;color:var(--muted)">${skipped}</div>
        <div style="font-size:0.78rem;color:var(--muted)">ignorées (doublons)</div>
      </div>
    </div>
  </div>`;

  if (errors.length) {
    html += `<div style="margin-top:14px;">
      <div style="font-weight:600;color:var(--danger);margin-bottom:8px;">⚠️ ${errors.length} avertissement(s)</div>
      <div class="card table-wrapper" style="max-height:200px;overflow-y:auto;">
        <table style="font-size:0.78rem;"><thead><tr><th>Ligne</th><th>Message</th></tr></thead><tbody>
        ${errors.slice(0,50).map(e => `<tr><td>${e.row ?? '—'}</td><td>${esc(e.message || '')}</td></tr>`).join('')}
        ${errors.length > 50 ? `<tr><td colspan="2" style="text-align:center;color:var(--muted)">… et ${errors.length - 50} autres</td></tr>` : ''}
        </tbody></table>
      </div>
    </div>`;
  }

  if (pending > 0) {
    html += `<div style="margin-top:14px;">
      <button class="btn btn-primary" onclick="closeModal('modal-bank-import');switchTreasuryTab('pending');loadTreasury()">
        ⚠️ Voir les ${pending} transaction(s) à valider →
      </button>
    </div>`;
  } else {
    html += `<div style="margin-top:14px;">
      <button class="btn btn-primary" onclick="closeModal('modal-bank-import');loadTreasury()">
        Voir la trésorerie →
      </button>
    </div>`;
  }

  el.innerHTML = html;

  // Rafraîchir le badge "À valider"
  _refreshPendingBadge();
}

// ── Toggle profil name ─────────────────────────────────────────────────────────
function onBankSaveProfileToggle() {
  const checked = document.getElementById('bk-save-profile').checked;
  document.getElementById('bk-profile-name-row').classList.toggle('hidden', !checked);
}
