/* ═══════════════════════════════════════════════════════════
   school.js — Familles, enfants, paiements, impayés
═══════════════════════════════════════════════════════════ */

// ── Familles ──────────────────────────────────────────────────────────────────
async function loadFamilies(search = '') {
  const tbody = document.getElementById('families-table');
  tbody.innerHTML = skeletonRows(4, 6);
  const url = search
    ? `/school/families/?search=${encodeURIComponent(search)}`
    : '/school/families/';
  const res = await apiFetch(url);
  if (!res || !res.ok) return;
  const data = await res.json();
  allFamilies = data.results || data;
  renderFamilies(allFamilies);
}

function renderFamilies(families) {
  const tbody = document.getElementById('families-table');
  if (!families.length) {
    tbody.innerHTML = emptyState({
      icon: '👨‍👩‍👧', title: 'Aucune famille enregistrée',
      sub: 'Commencez par ajouter la première famille.',
      actionLabel: '+ Ajouter une famille', actionFn: 'openFamilyModal()',
    });
    return;
  }
  tbody.innerHTML = families.map((f, i) => `
    <tr class="fade-in" style="animation-delay:${i * 30}ms">
      <td><strong>${esc(f.primary_contact_name)}</strong></td>
      <td>${esc(f.phone1)}</td>
      <td>${esc(f.email) || '<span class="text-muted">—</span>'}</td>
      <td><span class="badge badge-gray">${f.children_count} enfant(s)</span></td>
      <td><span class="badge badge-green">${f.total_paid.toFixed(2)} €</span></td>
      <td><div class="td-actions">
        <button class="btn btn-sm btn-icon" onclick="editFamily(${f.id})" title="Modifier">✏️</button>
        <button class="btn btn-danger btn-sm btn-icon" onclick="deleteFamily(${f.id})" title="Supprimer">🗑</button>
      </div></td>
    </tr>
  `).join('');
}

function searchFamilies() {
  loadFamilies(document.getElementById('family-search').value);
}

function openFamilyModal(id = null) {
  document.getElementById('family-id').value      = '';
  document.getElementById('family-name').value    = '';
  document.getElementById('family-phone1').value  = '';
  document.getElementById('family-phone2').value  = '';
  document.getElementById('family-email').value   = '';
  document.getElementById('family-address').value = '';
  document.getElementById('modal-family-title').textContent = id ? 'Modifier la famille' : 'Ajouter une famille';
  document.getElementById('modal-family-error').classList.add('hidden');
  openModal('modal-family');
}

async function editFamily(id) {
  const res = await apiFetch(`/school/families/${id}/`);
  if (!res || !res.ok) return;
  const f = await res.json();
  document.getElementById('family-id').value      = f.id;
  document.getElementById('family-name').value    = f.primary_contact_name;
  document.getElementById('family-phone1').value  = f.phone1;
  document.getElementById('family-phone2').value  = f.phone2 || '';
  document.getElementById('family-email').value   = f.email  || '';
  document.getElementById('family-address').value = f.address || '';
  document.getElementById('modal-family-title').textContent = 'Modifier la famille';
  document.getElementById('modal-family-error').classList.add('hidden');
  openModal('modal-family');
}

async function saveFamily() {
  const id   = document.getElementById('family-id').value;
  const body = {
    primary_contact_name: document.getElementById('family-name').value.trim(),
    phone1:   document.getElementById('family-phone1').value.trim(),
    phone2:   document.getElementById('family-phone2').value.trim(),
    email:    document.getElementById('family-email').value.trim(),
    address:  document.getElementById('family-address').value.trim(),
  };
  const errEl = document.getElementById('modal-family-error');
  if (!body.primary_contact_name || !body.phone1) {
    errEl.textContent = 'Le nom et le téléphone sont obligatoires.';
    errEl.classList.remove('hidden');
    return;
  }
  const res = await apiFetch(
    id ? `/school/families/${id}/` : '/school/families/',
    id ? 'PUT' : 'POST',
    body
  );
  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    errEl.classList.remove('hidden');
    return;
  }
  closeModal('modal-family');
  toast(id ? 'Famille mise à jour ✓' : 'Famille ajoutée ✓');
  loadFamilies();
}

async function deleteFamily(id) {
  const ok = await confirmDialog({
    title: 'Supprimer la famille ?',
    msg:   'Cette action supprimera aussi tous les enfants et paiements associés.',
    icon:  '🗑️',
  });
  if (!ok) return;
  await apiFetch(`/school/families/${id}/`, 'DELETE');
  toast('Famille supprimée', 'info');
  loadFamilies();
}

// ── Enfants ───────────────────────────────────────────────────────────────────
async function loadChildren(search = '') {
  const tbody = document.getElementById('children-table');
  tbody.innerHTML = skeletonRows(4, 5);
  const level = document.getElementById('child-level-filter').value;
  let url = '/school/children/?';
  if (search) url += `search=${encodeURIComponent(search)}&`;
  if (level)  url += `level=${level}`;
  const res = await apiFetch(url);
  if (!res || !res.ok) return;
  const data = await res.json();
  allChildren = data.results || data;
  renderChildren(allChildren);
}

function renderChildren(children) {
  const tbody = document.getElementById('children-table');
  if (!children.length) {
    tbody.innerHTML = emptyState({
      icon: '🧒', title: 'Aucun enfant enregistré',
      sub: 'Ajoutez des enfants depuis le bouton ci-dessus.',
      actionLabel: '+ Ajouter un enfant', actionFn: 'openChildModal()',
    });
    return;
  }
  tbody.innerHTML = children.map((c, i) => `
    <tr class="fade-in" style="animation-delay:${i * 30}ms">
      <td><strong>${esc(c.first_name)}</strong></td>
      <td><span class="badge badge-purple">${esc(c.level)}</span></td>
      <td>${esc(getFamilyName(c.family))}</td>
      <td>${c.birth_date || '<span class="text-muted">—</span>'}</td>
      <td><div class="td-actions">
        <button class="btn btn-sm btn-icon" onclick="editChild(${c.id})" title="Modifier">✏️</button>
        <button class="btn btn-danger btn-sm btn-icon" onclick="deleteChild(${c.id})" title="Supprimer">🗑</button>
      </div></td>
    </tr>
  `).join('');
}

function searchChildren() {
  loadChildren(document.getElementById('child-search').value);
}

function getFamilyName(id) {
  const f = allFamilies.find(f => f.id === id);
  return f ? f.primary_contact_name : `Famille #${id}`;
}

async function openChildModal() {
  await loadFamiliesForSelect('child-family');
  document.getElementById('child-id').value        = '';
  document.getElementById('child-firstname').value = '';
  document.getElementById('child-level').value     = '';
  document.getElementById('child-birthdate').value = '';
  document.getElementById('modal-child-title').textContent = 'Ajouter un enfant';
  document.getElementById('modal-child-error').classList.add('hidden');
  openModal('modal-child');
}

async function editChild(id) {
  await loadFamiliesForSelect('child-family');
  const res = await apiFetch(`/school/children/${id}/`);
  if (!res || !res.ok) return;
  const c = await res.json();
  document.getElementById('child-id').value        = c.id;
  document.getElementById('child-firstname').value = c.first_name;
  document.getElementById('child-family').value    = c.family;
  document.getElementById('child-level').value     = c.level;
  document.getElementById('child-birthdate').value = c.birth_date || '';
  document.getElementById('modal-child-title').textContent = "Modifier l'enfant";
  document.getElementById('modal-child-error').classList.add('hidden');
  openModal('modal-child');
}

async function saveChild() {
  const id   = document.getElementById('child-id').value;
  const body = {
    first_name: document.getElementById('child-firstname').value.trim(),
    family:     parseInt(document.getElementById('child-family').value),
    level:      document.getElementById('child-level').value,
    birth_date: document.getElementById('child-birthdate').value || null,
  };
  const errEl = document.getElementById('modal-child-error');
  if (!body.first_name || !body.family || !body.level) {
    errEl.textContent = 'Prénom, famille et niveau sont obligatoires.';
    errEl.classList.remove('hidden');
    return;
  }
  const res = await apiFetch(
    id ? `/school/children/${id}/` : '/school/children/',
    id ? 'PUT' : 'POST',
    body
  );
  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    errEl.classList.remove('hidden');
    return;
  }
  closeModal('modal-child');
  toast(id ? 'Enfant mis à jour ✓' : 'Enfant ajouté ✓');
  loadChildren();
}

async function deleteChild(id) {
  const ok = await confirmDialog({ title: "Supprimer l'enfant ?", msg: 'Cette action est irréversible.', icon: '🗑️' });
  if (!ok) return;
  await apiFetch(`/school/children/${id}/`, 'DELETE');
  toast('Enfant supprimé', 'info');
  loadChildren();
}

// ── Paiements école ───────────────────────────────────────────────────────────
async function loadPayments() {
  const tbody  = document.getElementById('payments-table');
  tbody.innerHTML = skeletonRows(4, 8);
  const yearId = document.getElementById('payment-year-filter').value;
  let url = '/school/payments/?';
  if (yearId) url += `year_id=${yearId}`;
  const res = await apiFetch(url);
  if (!res || !res.ok) return;
  const data = await res.json();
  const payments = data.results || data;
  if (!payments.length) {
    tbody.innerHTML = emptyState({
      icon: '💳', title: 'Aucun paiement enregistré',
      sub: 'Enregistrez un premier paiement.',
      actionLabel: '+ Ajouter un paiement', actionFn: 'openPaymentModal()',
    });
    return;
  }
  tbody.innerHTML = payments.map((p, i) => `
    <tr class="fade-in" style="animation-delay:${i * 30}ms">
      <td>${p.date}</td>
      <td><strong>${esc(p.family_name)}</strong></td>
      <td>${p.child_name ? esc(p.child_name) : '<span class="text-muted">—</span>'}</td>
      <td>${esc(p.school_year_label)}</td>
      <td><strong>${parseFloat(p.amount).toFixed(2)} €</strong></td>
      <td><span class="badge badge-blue">${esc(p.method_display || p.method)}</span></td>
      <td style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(p.note)||''}">${esc(p.note) || '<span class="text-muted">—</span>'}</td>
      <td><div class="td-actions">
        <button class="btn btn-sm btn-icon" onclick="editPayment(${p.id})" title="Modifier">✏️</button>
        <button class="btn btn-sm btn-icon" onclick="downloadSchoolReceipt(${p.id}, '${esc(p.family_name).replace(/'/g, "\\'")}')" title="Reçu PDF">🧾</button>
        <button class="btn btn-danger btn-sm btn-icon" onclick="deletePayment(${p.id})" title="Supprimer">🗑</button>
      </div></td>
    </tr>
  `).join('');
}

async function openPaymentModal() {
  await loadFamiliesForSelect('payment-family');
  await loadYearsForSelect('payment-year');
  document.getElementById('payment-id').value       = '';
  document.getElementById('payment-child').innerHTML = '<option value="">-- Aucun --</option>';
  document.getElementById('payment-date').value     = new Date().toISOString().split('T')[0];
  document.getElementById('payment-amount').value   = '';
  document.getElementById('payment-method').value   = 'cash';
  document.getElementById('payment-note').value     = '';
  document.getElementById('modal-payment-title').textContent = 'Enregistrer un paiement';
  document.getElementById('modal-payment-error').classList.add('hidden');
  openModal('modal-payment');
}

async function editPayment(id) {
  await loadFamiliesForSelect('payment-family');
  await loadYearsForSelect('payment-year');
  const res = await apiFetch(`/school/payments/${id}/`);
  if (!res || !res.ok) return;
  const p = await res.json();
  document.getElementById('payment-id').value     = p.id;
  document.getElementById('payment-family').value = p.family;
  document.getElementById('payment-year').value   = p.school_year;
  await loadChildrenForFamily();
  document.getElementById('payment-child').value  = p.child || '';
  document.getElementById('payment-date').value   = p.date;
  document.getElementById('payment-amount').value = p.amount;
  document.getElementById('payment-method').value = p.method;
  document.getElementById('payment-note').value   = p.note || '';
  document.getElementById('modal-payment-title').textContent = 'Modifier le paiement';
  document.getElementById('modal-payment-error').classList.add('hidden');
  openModal('modal-payment');
}

async function loadChildrenForFamily() {
  const familyId = document.getElementById('payment-family').value;
  const sel = document.getElementById('payment-child');
  sel.innerHTML = '<option value="">-- Aucun --</option>';
  if (!familyId) return;
  const res = await apiFetch('/school/children/?search=');
  if (!res || !res.ok) return;
  const data = await res.json();
  const children = (data.results || data).filter(c => c.family === parseInt(familyId));
  children.forEach(c => {
    sel.innerHTML += `<option value="${c.id}">${esc(c.first_name)} (${esc(c.level)})</option>`;
  });
}

async function savePayment() {
  const id   = document.getElementById('payment-id').value;
  const body = {
    family:      parseInt(document.getElementById('payment-family').value),
    school_year: parseInt(document.getElementById('payment-year').value),
    child:       document.getElementById('payment-child').value
                   ? parseInt(document.getElementById('payment-child').value)
                   : null,
    date:        document.getElementById('payment-date').value,
    amount:      parseFloat(document.getElementById('payment-amount').value),
    method:      document.getElementById('payment-method').value,
    note:        document.getElementById('payment-note').value.trim(),
  };
  const errEl = document.getElementById('modal-payment-error');
  if (!body.family || !body.school_year || !body.date || !body.amount) {
    errEl.textContent = 'Famille, année, date et montant sont obligatoires.';
    errEl.classList.remove('hidden');
    return;
  }
  const res = await apiFetch(
    id ? `/school/payments/${id}/` : '/school/payments/',
    id ? 'PUT' : 'POST',
    body
  );
  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    errEl.classList.remove('hidden');
    return;
  }
  closeModal('modal-payment');
  toast(id ? 'Paiement mis à jour ✓' : 'Paiement enregistré ✓');
  loadPayments();
}

async function downloadSchoolReceipt(id, familyName) {
  showProgress();
  try {
    const res = await fetch(`${API}/school/payments/${id}/receipt/`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      toast(err.detail || 'Erreur génération PDF', 'error');
      return;
    }
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `recu_ecole_${familyName.replace(/\s+/g, '_')}_${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    toast('Reçu PDF téléchargé ✓');
  } catch (e) {
    toast('Erreur : ' + e.message, 'error');
  } finally {
    hideProgress();
  }
}

async function deletePayment(id) {
  const ok = await confirmDialog({ title: 'Supprimer ce paiement ?', msg: 'Cette action est irréversible.', icon: '🗑️' });
  if (!ok) return;
  await apiFetch(`/school/payments/${id}/`, 'DELETE');
  toast('Paiement supprimé', 'info');
  loadPayments();
}

// ── Impayés ───────────────────────────────────────────────────────────────────
async function loadArrears() {
  const infoEl  = document.getElementById('arrears-info');
  infoEl.classList.add('hidden');
  document.getElementById('arrears-alert').innerHTML = '';
  document.getElementById('arrears-table').innerHTML = skeletonRows(4, 4);

  const res = await apiFetch('/school/families/arrears/');
  if (!res) return;

  if (res.status === 404) {
    document.getElementById('arrears-table').innerHTML = '';
    toast("Aucune année scolaire active. Créez-en une depuis l'Admin Django.", 'error', 5000);
    return;
  }
  if (!res.ok) return;
  const data = await res.json();

  infoEl.textContent = `Année active : ${data.school_year} — ${data.count} famille(s) sans paiement`;
  infoEl.classList.remove('hidden');

  const tbody = document.getElementById('arrears-table');
  if (!data.families.length) {
    tbody.innerHTML = emptyState({ icon: '✅', title: 'Toutes les familles ont payé !', sub: 'Aucun impayé pour l\'année en cours.' });
    return;
  }
  tbody.innerHTML = data.families.map((f, i) => `
    <tr class="fade-in" style="animation-delay:${i * 30}ms">
      <td><strong>${esc(f.primary_contact_name)}</strong></td>
      <td>${esc(f.phone1)}</td>
      <td>${esc(f.email) || '<span class="text-muted">—</span>'}</td>
      <td><span class="badge badge-gray">${f.children_count} enfant(s)</span></td>
    </tr>
  `).join('');
}

// ── Helpers sélects ───────────────────────────────────────────────────────────
async function loadFamiliesForSelect(selectId) {
  if (!allFamilies.length) {
    const res = await apiFetch('/school/families/');
    if (res && res.ok) {
      const data = await res.json();
      allFamilies = data.results || data;
    }
  }
  const sel = document.getElementById(selectId);
  sel.innerHTML = '<option value="">-- Choisir une famille --</option>';
  allFamilies.forEach(f => {
    sel.innerHTML += `<option value="${f.id}">${esc(f.primary_contact_name)}</option>`;
  });
}

async function loadYearsForSelect(selectId) {
  if (!schoolYears.length) await loadSchoolYears();
  const sel = document.getElementById(selectId);
  sel.innerHTML = '<option value="">-- Choisir une année --</option>';
  schoolYears.forEach(y => {
    sel.innerHTML += `<option value="${y.id}">${y.label}${y.is_active ? ' ✓ active' : ''}</option>`;
  });
}
