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
  // SMTP / Notifications email
  document.getElementById('s-smtp-host').value         = data.smtp_host           || '';
  document.getElementById('s-smtp-port').value         = data.smtp_port           || 587;
  document.getElementById('s-smtp-user').value         = data.smtp_user           || '';
  document.getElementById('s-smtp-password').value     = data.smtp_password       || '';
  document.getElementById('s-smtp-use-tls').checked    = data.smtp_use_tls        !== false;
  document.getElementById('s-email-from').value        = data.email_from          || '';
  document.getElementById('s-email-subject-prefix').value = data.email_subject_prefix || '[Mosquée Manager]';
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
    // SMTP / Notifications email
    smtp_host:                document.getElementById('s-smtp-host').value.trim(),
    smtp_port:                parseInt(document.getElementById('s-smtp-port').value) || 587,
    smtp_user:                document.getElementById('s-smtp-user').value.trim(),
    smtp_password:            document.getElementById('s-smtp-password').value,
    smtp_use_tls:             document.getElementById('s-smtp-use-tls').checked,
    email_from:               document.getElementById('s-email-from').value.trim(),
    email_subject_prefix:     document.getElementById('s-email-subject-prefix').value.trim(),
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

// ── Comptes bancaires ─────────────────────────────────────────────────────────

async function loadBankAccounts() {
  const container = document.getElementById('bank-accounts-list');
  if (!container) return;
  container.innerHTML = '<p style="color:var(--muted);font-size:.85rem;">⏳ Chargement...</p>';

  const res = await apiFetch('/settings/bank-accounts/');
  if (!res || !res.ok) { container.innerHTML = '<p style="color:var(--danger);">Erreur chargement</p>'; return; }
  const accounts = await res.json();

  if (!accounts.length) {
    container.innerHTML = '<p style="color:var(--muted);font-size:.85rem;">Aucun compte configuré. Cliquez sur "+ Ajouter" pour commencer.</p>';
    return;
  }

  container.innerHTML = accounts.map(a => `
    <div class="bank-account-row" style="display:flex;align-items:center;gap:12px;padding:10px 14px;border:1.5px solid var(--border);border-radius:8px;margin-bottom:8px;background:var(--bg);">
      <div style="flex:1;">
        <strong>${esc(a.label)}</strong>
        <span style="margin-left:10px;font-size:.8rem;color:var(--muted);">${esc(a.bank_name)}</span>
        <br>
        <code style="font-size:.8rem;">${esc(a.account_number)}</code>
        <span class="badge ${a.regime === '1901' ? 'badge-1901' : a.regime === '1905' ? 'badge-1905' : 'badge-gray'}" style="margin-left:8px;">${a.regime}</span>
        ${!a.is_active ? '<span class="badge badge-gray" style="margin-left:4px;">Inactif</span>' : ''}
      </div>
      <button class="btn btn-sm" onclick="openBankAccountModal(${a.id})">✏️</button>
      <button class="btn btn-danger btn-sm" onclick="deleteBankAccount(${a.id})">🗑</button>
    </div>`).join('');
}

function openBankAccountModal(id = null) {
  document.getElementById('ba-id').value         = id || '';
  document.getElementById('ba-label').value       = '';
  document.getElementById('ba-bank-name').value   = '';
  document.getElementById('ba-account-number').value = '';
  document.getElementById('ba-regime').value      = '1901';
  document.getElementById('ba-is-active').checked = true;
  document.getElementById('modal-ba-title').textContent = id ? 'Modifier le compte' : 'Ajouter un compte bancaire';
  document.getElementById('modal-ba-error').textContent = '';

  if (id) {
    apiFetch(`/settings/bank-accounts/${id}/`).then(async res => {
      if (!res || !res.ok) return;
      const a = await res.json();
      document.getElementById('ba-label').value       = a.label;
      document.getElementById('ba-bank-name').value   = a.bank_name;
      document.getElementById('ba-account-number').value = a.account_number;
      document.getElementById('ba-regime').value      = a.regime;
      document.getElementById('ba-is-active').checked = a.is_active;
    });
  }
  openModal('modal-bank-account');
}

async function saveBankAccount() {
  const id = document.getElementById('ba-id').value;
  const errEl = document.getElementById('modal-ba-error');
  errEl.textContent = '';

  const body = {
    label:          document.getElementById('ba-label').value.trim(),
    bank_name:      document.getElementById('ba-bank-name').value.trim(),
    account_number: document.getElementById('ba-account-number').value.trim(),
    regime:         document.getElementById('ba-regime').value,
    is_active:      document.getElementById('ba-is-active').checked,
  };

  if (!body.label || !body.account_number) {
    errEl.textContent = 'Le libellé et le numéro de compte sont obligatoires.';
    return;
  }

  const url    = id ? `/settings/bank-accounts/${id}/` : '/settings/bank-accounts/';
  const method = id ? 'PUT' : 'POST';
  const res    = await apiFetch(url, method, body);

  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    return;
  }

  closeModal('modal-bank-account');
  toast(id ? 'Compte mis à jour ✓' : 'Compte ajouté ✓');
  loadBankAccounts();
}

async function deleteBankAccount(id) {
  const ok = await confirmDialog({ title: 'Supprimer ce compte ?', msg: 'Les transactions associées ne seront pas supprimées.', icon: '🗑️' });
  if (!ok) return;
  const res = await apiFetch(`/settings/bank-accounts/${id}/`, 'DELETE');
  if (!res || res.ok) { toast('Compte supprimé', 'info'); loadBankAccounts(); }
  else toast('Erreur suppression', 'error');
}

// ── Règles de dispatch ────────────────────────────────────────────────────────

async function loadDispatchRules() {
  const container = document.getElementById('dispatch-rules-list');
  if (!container) return;
  container.innerHTML = '<p style="color:var(--muted);font-size:.85rem;">⏳ Chargement...</p>';

  const res = await apiFetch('/settings/dispatch-rules/');
  if (!res || !res.ok) { container.innerHTML = '<p style="color:var(--danger);">Erreur chargement</p>'; return; }
  const rules = await res.json();

  if (!rules.length) {
    container.innerHTML = '<p style="color:var(--muted);font-size:.85rem;">Aucune règle configurée. Ajoutez des mots-clés pour que l\'import CSV catégorise automatiquement les transactions.</p>';
    return;
  }

  const FIELD_LABELS = { label: 'Libellé', detail: 'Détail', both: 'Lib. ou Détail' };
  const DIR_LABELS   = { IN: '▲ Entrée', OUT: '▼ Sortie', auto: 'Auto' };

  container.innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:.85rem;">
      <thead><tr style="color:var(--muted);font-size:.78rem;border-bottom:1.5px solid var(--border);">
        <th style="padding:6px 8px;text-align:left;">Priorité</th>
        <th style="padding:6px 8px;text-align:left;">Mot-clé</th>
        <th style="padding:6px 8px;text-align:left;">Champ</th>
        <th style="padding:6px 8px;text-align:left;">Catégorie</th>
        <th style="padding:6px 8px;text-align:left;">Direction</th>
        <th style="padding:6px 8px;text-align:left;">Actif</th>
        <th style="padding:6px 8px;"></th>
      </tr></thead>
      <tbody>
        ${rules.map(r => `
        <tr style="border-bottom:1px solid var(--border);">
          <td style="padding:6px 8px;">${r.priority}</td>
          <td style="padding:6px 8px;"><code>${esc(r.keyword)}</code></td>
          <td style="padding:6px 8px;color:var(--muted);">${FIELD_LABELS[r.field] || r.field}</td>
          <td style="padding:6px 8px;"><span class="badge badge-gray">${esc(r.category)}</span></td>
          <td style="padding:6px 8px;">${DIR_LABELS[r.direction] || r.direction}</td>
          <td style="padding:6px 8px;">${r.is_active ? '✅' : '⛔'}</td>
          <td style="padding:6px 8px;">
            <button class="btn btn-sm" onclick="openDispatchRuleModal(${r.id})">✏️</button>
            <button class="btn btn-danger btn-sm" onclick="deleteDispatchRule(${r.id})">🗑</button>
          </td>
        </tr>`).join('')}
      </tbody>
    </table>`;
}

function openDispatchRuleModal(id = null) {
  document.getElementById('dr-id').value        = id || '';
  document.getElementById('dr-keyword').value    = '';
  document.getElementById('dr-field').value      = 'both';
  document.getElementById('dr-category').value   = 'don';
  document.getElementById('dr-direction').value  = 'auto';
  document.getElementById('dr-priority').value   = '10';
  document.getElementById('dr-is-active').checked = true;
  document.getElementById('modal-dr-title').textContent = id ? 'Modifier la règle' : 'Ajouter une règle de dispatch';
  document.getElementById('modal-dr-error').textContent = '';

  if (id) {
    apiFetch(`/settings/dispatch-rules/${id}/`).then(async res => {
      if (!res || !res.ok) return;
      const r = await res.json();
      document.getElementById('dr-keyword').value    = r.keyword;
      document.getElementById('dr-field').value      = r.field;
      document.getElementById('dr-category').value   = r.category;
      document.getElementById('dr-direction').value  = r.direction;
      document.getElementById('dr-priority').value   = r.priority;
      document.getElementById('dr-is-active').checked = r.is_active;
    });
  }
  openModal('modal-dispatch-rule');
}

async function saveDispatchRule() {
  const id = document.getElementById('dr-id').value;
  const errEl = document.getElementById('modal-dr-error');
  errEl.textContent = '';

  const body = {
    keyword:   document.getElementById('dr-keyword').value.trim(),
    field:     document.getElementById('dr-field').value,
    category:  document.getElementById('dr-category').value,
    direction: document.getElementById('dr-direction').value,
    priority:  parseInt(document.getElementById('dr-priority').value) || 10,
    is_active: document.getElementById('dr-is-active').checked,
  };

  if (!body.keyword) { errEl.textContent = 'Le mot-clé est obligatoire.'; return; }

  const url    = id ? `/settings/dispatch-rules/${id}/` : '/settings/dispatch-rules/';
  const method = id ? 'PUT' : 'POST';
  const res    = await apiFetch(url, method, body);

  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    return;
  }

  closeModal('modal-dispatch-rule');
  toast(id ? 'Règle mise à jour ✓' : 'Règle ajoutée ✓');
  loadDispatchRules();
}

async function deleteDispatchRule(id) {
  const ok = await confirmDialog({ title: 'Supprimer cette règle ?', msg: 'Elle ne sera plus appliquée aux prochains imports.', icon: '🗑️' });
  if (!ok) return;
  const res = await apiFetch(`/settings/dispatch-rules/${id}/`, 'DELETE');
  if (!res || res.ok) { toast('Règle supprimée', 'info'); loadDispatchRules(); }
  else toast('Erreur suppression', 'error');
}

// ── Personnel (Staff) ─────────────────────────────────────────────────────────

const STAFF_ROLES = {
  enseignant: '📚 Enseignant',
  imam:       '🕌 Imam',
  entretien:  '🧹 Entretien',
  comptable:  '📊 Comptable',
  gardien:    '🔑 Gardien',
  autre:      '👤 Autre',
};

async function loadStaff() {
  const container = document.getElementById('staff-list');
  if (!container) return;
  container.innerHTML = '<p style="color:var(--muted);font-size:.85rem;">⏳ Chargement...</p>';

  const res = await apiFetch('/settings/staff/');
  if (!res || !res.ok) { container.innerHTML = '<p style="color:var(--danger);">Erreur chargement</p>'; return; }
  const members = await res.json();

  if (!members.length) {
    container.innerHTML = '<p style="color:var(--muted);font-size:.85rem;">Aucun membre du personnel configuré.</p>';
    return;
  }

  container.innerHTML = members.map(m => `
    <div style="display:flex;align-items:center;gap:12px;padding:10px 14px;border:1.5px solid var(--border);border-radius:8px;margin-bottom:8px;background:var(--bg);">
      <div style="flex:1;">
        <strong>${esc(m.full_name)}</strong>
        <span class="badge badge-gray" style="margin-left:8px;">${STAFF_ROLES[m.role] || m.role}</span>
        ${!m.is_active ? '<span class="badge badge-gray" style="margin-left:4px;opacity:.6;">Inactif</span>' : ''}
        <br>
        ${m.monthly_salary ? `<span style="font-size:.82rem;color:var(--muted);">Salaire : <strong>${parseFloat(m.monthly_salary).toFixed(2).replace('.', ',')} €/mois</strong></span>` : ''}
        ${m.name_keyword ? `<span style="font-size:.75rem;color:var(--muted);margin-left:10px;">Mot-clé CSV : <code>${esc(m.name_keyword)}</code></span>` : ''}
      </div>
      <button class="btn btn-sm" onclick="openStaffModal(${m.id})">✏️</button>
      <button class="btn btn-danger btn-sm" onclick="deleteStaff(${m.id})">🗑</button>
    </div>`).join('');
}

async function openStaffModal(id = null) {
  document.getElementById('staff-id').value           = id || '';
  document.getElementById('staff-full-name').value    = '';
  document.getElementById('staff-role').value         = 'enseignant';
  document.getElementById('staff-salary').value       = '';
  document.getElementById('staff-name-keyword').value = '';
  document.getElementById('staff-iban').value         = '';
  document.getElementById('staff-phone').value        = '';
  document.getElementById('staff-email').value        = '';
  document.getElementById('staff-note').value         = '';
  document.getElementById('staff-is-active').checked  = true;
  document.getElementById('staff-start-date').value   = '';
  document.getElementById('staff-end-date').value     = '';
  document.getElementById('staff-modal-title').textContent = id ? '✏️ Modifier le personnel' : '👤 Nouveau membre du personnel';
  document.getElementById('staff-error').textContent  = '';

  if (id) {
    const res = await apiFetch(`/settings/staff/${id}/`);
    if (!res || !res.ok) return;
    const m = await res.json();
    document.getElementById('staff-full-name').value    = m.full_name    || '';
    document.getElementById('staff-role').value         = m.role         || 'enseignant';
    document.getElementById('staff-salary').value       = m.monthly_salary != null ? m.monthly_salary : '';
    document.getElementById('staff-name-keyword').value = m.name_keyword  || '';
    document.getElementById('staff-iban').value         = m.iban_fragment || '';
    document.getElementById('staff-phone').value        = m.phone         || '';
    document.getElementById('staff-email').value        = m.email         || '';
    document.getElementById('staff-note').value         = m.note          || '';
    document.getElementById('staff-is-active').checked  = m.is_active !== false;
    document.getElementById('staff-start-date').value   = m.start_date   || '';
    document.getElementById('staff-end-date').value     = m.end_date      || '';
  }

  openModal('modal-staff');
}

async function saveStaff() {
  const errEl = document.getElementById('staff-error');
  errEl.textContent = '';
  const id  = document.getElementById('staff-id').value || null;
  const salary = document.getElementById('staff-salary').value.trim();
  const body = {
    full_name:      document.getElementById('staff-full-name').value.trim(),
    role:           document.getElementById('staff-role').value,
    monthly_salary: salary ? parseFloat(salary) : null,
    name_keyword:   document.getElementById('staff-name-keyword').value.trim(),
    iban_fragment:  document.getElementById('staff-iban').value.trim(),
    phone:          document.getElementById('staff-phone').value.trim(),
    email:          document.getElementById('staff-email').value.trim(),
    note:           document.getElementById('staff-note').value.trim(),
    is_active:      document.getElementById('staff-is-active').checked,
    start_date:     document.getElementById('staff-start-date').value || null,
    end_date:       document.getElementById('staff-end-date').value   || null,
  };

  if (!body.full_name) { errEl.textContent = 'Le nom complet est obligatoire.'; return; }

  const url    = id ? `/settings/staff/${id}/` : '/settings/staff/';
  const method = id ? 'PUT' : 'POST';
  const res    = await apiFetch(url, method, body);

  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    return;
  }

  closeModal('modal-staff');
  toast(id ? 'Personnel mis à jour ✓' : 'Personnel ajouté ✓');
  loadStaff();
}

async function deleteStaff(id) {
  const ok = await confirmDialog({ title: 'Supprimer ce membre ?', msg: 'Cette action est irréversible.', icon: '🗑️' });
  if (!ok) return;
  const res = await apiFetch(`/settings/staff/${id}/`, 'DELETE');
  if (!res || res.ok) { toast('Supprimé', 'info'); loadStaff(); }
  else toast('Erreur suppression', 'error');
}
