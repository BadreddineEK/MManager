/* ═══════════════════════════════════════════════════════════
   school.js — Familles, enfants, impayés
   (les paiements école passent par la trésorerie)
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
  tbody.innerHTML = families.map((f, i) => {
    const paid   = parseFloat(f.current_year_paid || 0);
    const due    = parseFloat(f.current_year_due  || 0);
    const reste  = Math.max(0, due - paid);
    const status = f.payment_status || 'unpaid';
    const statusBadge = status === 'paid'
      ? '<span class="badge badge-green">✅ Soldé</span>'
      : status === 'partial'
        ? `<span class="badge badge-yellow">⚠️ Partiel</span>`
        : due > 0 ? '<span class="badge badge-red">❌ Impayé</span>'
                  : '<span class="badge badge-gray">—</span>';
    const resteDisplay = due > 0
      ? `<span class="${reste > 0 ? 'text-red' : 'text-green'}" style="font-weight:600;">${reste > 0 ? '-' : ''}${reste.toFixed(2)} €</span>`
      : '<span class="text-muted">—</span>';
    return `
    <tr class="fade-in" style="animation-delay:${i * 30}ms">
      <td><strong>${esc(f.primary_contact_name)}</strong></td>
      <td>${esc(f.phone1)}</td>
      <td>${esc(f.email) || '<span class="text-muted">—</span>'}</td>
      <td><span class="badge badge-gray">${f.children_count} enfant(s)</span></td>
      <td>${statusBadge}</td>
      <td style="white-space:nowrap;">
        <span class="badge badge-green">${paid.toFixed(2)} €</span>
        ${due > 0 ? `<span class="text-muted" style="font-size:.78rem;">/ ${due.toFixed(2)} €</span>` : ''}
      </td>
      <td>${resteDisplay}</td>
      <td><div class="td-actions">
        <button class="btn btn-sm btn-icon" onclick="editFamily(${f.id})" title="Modifier">✏️</button>
        <button class="btn btn-sm btn-icon" onclick="addSchoolPayment(${f.id}, '${esc(f.primary_contact_name).replace(/'/g, "\\'")}')" title="Enregistrer un paiement">💳</button>
        <button class="btn btn-danger btn-sm btn-icon" onclick="deleteFamily(${f.id})" title="Supprimer">🗑</button>
      </div></td>
    </tr>`;
  }).join('');
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
  _familyChildRows = [];
  _renderFamilyChildRows();
  document.getElementById('modal-family-title').textContent = id ? 'Modifier la famille' : 'Ajouter une famille';
  document.getElementById('modal-family-error').classList.add('hidden');
  openModal('modal-family');
}

// ── Enfants inline dans la modale famille ────────────────────────────────────
let _familyChildRows = []; // [{id, first_name, level, birth_date, _delete}]

const SCHOOL_LEVELS_FALLBACK = ['NP', 'N1', 'N2', 'N3', 'N4', 'CORAN', 'ADULTE'];

async function getSchoolLevels() {
  const s = await getMosqueSettings();
  return (s.school_levels && s.school_levels.length) ? s.school_levels : SCHOOL_LEVELS_FALLBACK;
}

async function _renderFamilyChildRows() {
  const container = document.getElementById('family-children-list');
  if (!container) return;
  if (_familyChildRows.filter(r => !r._delete).length === 0) {
    container.innerHTML = '<p style="font-size:.82rem;color:var(--muted);text-align:center;padding:8px 0;">Aucun enfant — cliquez sur "+ Ajouter un enfant"</p>';
    return;
  }
  const SCHOOL_LEVELS = await getSchoolLevels();
  container.innerHTML = _familyChildRows.map((row, idx) => {
    if (row._delete) return '';
    const levelOpts = SCHOOL_LEVELS.map(l =>
      `<option value="${l}"${row.level === l ? ' selected' : ''}>${l}</option>`
    ).join('');
    return `
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:8px;align-items:center;background:var(--bg-secondary);padding:8px 10px;border-radius:8px;border:1px solid var(--border);">
      <input type="text" placeholder="Prénom *" value="${esc(row.first_name || '')}"
        oninput="_updateChildRow(${idx},'first_name',this.value)"
        style="margin:0;padding:6px 10px;font-size:.85rem;" />
      <select onchange="_updateChildRow(${idx},'level',this.value)"
        style="margin:0;padding:6px 10px;font-size:.85rem;">
        <option value="">Niveau *</option>${levelOpts}
      </select>
      <input type="date" placeholder="Naissance" value="${row.birth_date || ''}"
        oninput="_updateChildRow(${idx},'birth_date',this.value)"
        style="margin:0;padding:6px 10px;font-size:.85rem;" />
      <button type="button" onclick="_removeFamilyChildRow(${idx})" title="Retirer"
        style="background:none;border:none;cursor:pointer;font-size:1.1rem;color:var(--danger);">✕</button>
    </div>`;
  }).join('');
}

function _updateChildRow(idx, field, value) {
  if (_familyChildRows[idx]) _familyChildRows[idx][field] = value;
}

function addFamilyChildRow() {
  _familyChildRows.push({ id: null, first_name: '', level: '', birth_date: '', _delete: false });
  _renderFamilyChildRows();
}

function _removeFamilyChildRow(idx) {
  if (_familyChildRows[idx].id) {
    _familyChildRows[idx]._delete = true; // suppression côté API
  } else {
    _familyChildRows.splice(idx, 1);
  }
  _renderFamilyChildRows();
}

// ── Reconduction scolaire ────────────────────────────────────────────────────
async function openReenrollModal() {
  if (!schoolYears.length) await loadSchoolYears();
  const srcSel = document.getElementById('reenroll-source');
  const tgtSel = document.getElementById('reenroll-target');
  const opts = schoolYears.map(y =>
    `<option value="${y.id}">${y.label}${y.is_active ? ' (active)' : ''}</option>`
  ).join('');
  srcSel.innerHTML = opts;
  tgtSel.innerHTML = opts;
  // Pré-sélectionner : source = année active, cible = autre
  const activeIdx = schoolYears.findIndex(y => y.is_active);
  if (activeIdx >= 0) {
    srcSel.value = schoolYears[activeIdx].id;
    const nextIdx = activeIdx + 1 < schoolYears.length ? activeIdx + 1 : activeIdx - 1;
    if (nextIdx >= 0) tgtSel.value = schoolYears[nextIdx].id;
  }
  document.getElementById('modal-reenroll-result').classList.add('hidden');
  document.getElementById('modal-reenroll-error').classList.add('hidden');
  openModal('modal-reenroll');
}

async function doReenroll() {
  const sourceId = document.getElementById('reenroll-source').value;
  const targetId = document.getElementById('reenroll-target').value;
  const autoLvl  = document.getElementById('reenroll-level-up').checked;
  const errEl    = document.getElementById('modal-reenroll-error');
  const resEl    = document.getElementById('modal-reenroll-result');
  errEl.classList.add('hidden');
  resEl.classList.add('hidden');

  if (!sourceId || !targetId) {
    errEl.textContent = 'Sélectionnez les deux années.';
    errEl.classList.remove('hidden');
    return;
  }
  if (sourceId === targetId) {
    errEl.textContent = "L'année source et l'année cible doivent être différentes.";
    errEl.classList.remove('hidden');
    return;
  }

  const btn = document.querySelector('#modal-reenroll .btn-primary');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ En cours…'; }

  const res = await apiFetch(`/school/years/${sourceId}/reenroll/`, 'POST', {
    target_year_id: parseInt(targetId),
    auto_level_up: autoLvl,
  });

  if (btn) { btn.disabled = false; btn.textContent = '🔄 Reconduire'; }

  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = err.detail || 'Erreur lors de la reconduction.';
    errEl.classList.remove('hidden');
    return;
  }
  const data = await res.json();
  resEl.innerHTML = `
    <strong>✅ Reconduction terminée</strong><br>
    <span class="badge badge-green">${data.enrolled} inscrit(s)</span>
    <span class="badge badge-gray" style="margin-left:4px;">${data.skipped} ignoré(s) (déjà inscrits)</span>
    ${data.errors && data.errors.length ? `<br><span style="color:var(--danger);font-size:.8rem;">${data.errors.length} erreur(s)</span>` : ''}
  `;
  resEl.classList.remove('hidden');
  toast(`${data.enrolled} enfant(s) reconduit(s) ✓`, 'success');
  loadFamilies();
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
  // Charger les enfants existants
  _familyChildRows = (f.children || []).map(c => ({
    id: c.id,
    first_name: c.first_name,
    level: c.level,
    birth_date: c.birth_date || '',
    _delete: false,
  }));
  _renderFamilyChildRows();
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

  // Valider enfants : chaque ligne doit avoir prénom + niveau
  const childErrors = _familyChildRows
    .filter(r => !r._delete)
    .filter(r => !r.first_name.trim() || !r.level);
  if (childErrors.length) {
    errEl.textContent = 'Chaque enfant doit avoir un prénom et un niveau.';
    errEl.classList.remove('hidden');
    return;
  }

  // 1. Sauvegarder la famille
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
  const family = await res.json();
  const familyId = family.id;

  // 2. Sauvegarder enfants : créations + suppressions
  const childOps = _familyChildRows.map(async (row) => {
    if (row._delete && row.id) {
      return apiFetch(`/school/children/${row.id}/`, 'DELETE');
    } else if (!row._delete && row.id) {
      // Mise à jour
      return apiFetch(`/school/children/${row.id}/`, 'PATCH', {
        first_name: row.first_name.trim(),
        level: row.level,
        birth_date: row.birth_date || null,
      });
    } else if (!row._delete && !row.id && row.first_name.trim()) {
      // Création
      return apiFetch('/school/children/', 'POST', {
        first_name: row.first_name.trim(),
        level: row.level,
        birth_date: row.birth_date || null,
        family: familyId,
      });
    }
  });
  await Promise.all(childOps);

  closeModal('modal-family');
  _familyChildRows = [];
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

// ── Paiements école ──────────────────────────────────────────────────────────

async function addSchoolPayment(familyId = null, familyName = '') {
  // Charger familles + années dans les sélects
  await Promise.all([
    _spLoadFamilies(),
    _spLoadYears(),
  ]);

  // Pré-sélectionner la famille si fournie
  if (familyId) {
    document.getElementById('sp-family').value = familyId;
    await _spLoadChildrenForFamily(familyId);
  } else {
    document.getElementById('sp-child').innerHTML = '<option value="">— Tous les enfants —</option>';
  }

  document.getElementById('sp-id').value     = '';
  document.getElementById('sp-date').value   = new Date().toISOString().split('T')[0];
  document.getElementById('sp-method').value = 'cash';
  document.getElementById('sp-note').value   = '';
  document.getElementById('modal-sp-title').textContent = '💳 Enregistrer un paiement école';
  document.getElementById('modal-sp-error').classList.add('hidden');

  // Pré-remplir le montant avec le tarif configuré × nb enfants de la famille
  await _spSuggestAmount(familyId);

  openModal('modal-school-payment');
}

async function _spSuggestAmount(familyId) {
  const amountEl = document.getElementById('sp-amount');
  if (!amountEl) return;
  try {
    const s = await getMosqueSettings();
    const fee = parseFloat(s.school_fee_default) || 0;
    if (!fee) return;
    let nbChildren = 1;
    if (familyId) {
      const fam = allFamilies.find(f => String(f.id) === String(familyId));
      nbChildren = fam ? (fam.children_count || 1) : 1;
    }
    amountEl.value = (fee * nbChildren).toFixed(2);
    amountEl.title = `Tarif configuré : ${fee} € × ${nbChildren} enfant(s)`;
  } catch (e) { /* silencieux */ }
}


async function editSchoolPayment(id) {
  const res = await apiFetch(`/school/payments/${id}/`);
  if (!res || !res.ok) { toast('Erreur chargement paiement', 'error'); return; }
  const p = await res.json();

  await Promise.all([_spLoadFamilies(), _spLoadYears()]);
  document.getElementById('sp-family').value = p.family;
  await _spLoadChildrenForFamily(p.family);

  document.getElementById('sp-id').value     = p.id;
  document.getElementById('sp-child').value  = p.child || '';
  document.getElementById('sp-year').value   = p.school_year;
  document.getElementById('sp-amount').value = p.amount;
  document.getElementById('sp-date').value   = p.date;
  document.getElementById('sp-method').value = p.method;
  document.getElementById('sp-note').value   = p.note || '';
  document.getElementById('modal-sp-title').textContent = '✏️ Modifier le paiement école';
  document.getElementById('modal-sp-error').classList.add('hidden');
  openModal('modal-school-payment');
}

async function _spLoadFamilies() {
  if (!allFamilies.length) {
    const res = await apiFetch('/school/families/');
    if (res && res.ok) {
      const data = await res.json();
      allFamilies = data.results || data;
    }
  }
  const sel = document.getElementById('sp-family');
  sel.innerHTML = '<option value="">— Choisir une famille —</option>';
  allFamilies.forEach(f => {
    sel.innerHTML += `<option value="${f.id}">${esc(f.primary_contact_name)}</option>`;
  });
  sel.onchange = () => _spLoadChildrenForFamily(sel.value);
}

async function _spLoadChildrenForFamily(familyId) {
  const sel = document.getElementById('sp-child');
  sel.innerHTML = '<option value="">— Tous les enfants —</option>';
  if (!familyId) return;
  const res = await apiFetch(`/school/children/?family=${familyId}`);
  if (!res || !res.ok) return;
  const data = await res.json();
  const children = data.results || data;
  children.forEach(c => {
    sel.innerHTML += `<option value="${c.id}">${esc(c.first_name)} (${esc(c.level)})</option>`;
  });
}

async function _spLoadYears() {
  if (!schoolYears.length) await loadSchoolYears();
  const sel = document.getElementById('sp-year');
  sel.innerHTML = '<option value="">— Choisir une année —</option>';
  schoolYears.forEach(y => {
    const active = y.is_active ? ' ✓' : '';
    sel.innerHTML += `<option value="${y.id}" ${y.is_active ? 'selected' : ''}>${esc(y.label)}${active}</option>`;
  });
}

async function saveSchoolPayment() {
  const errEl = document.getElementById('modal-sp-error');
  const body = {
    family:      parseInt(document.getElementById('sp-family').value) || null,
    child:       parseInt(document.getElementById('sp-child').value)  || null,
    school_year: parseInt(document.getElementById('sp-year').value)   || null,
    amount:      parseFloat(document.getElementById('sp-amount').value),
    date:        document.getElementById('sp-date').value,
    method:      document.getElementById('sp-method').value,
    note:        document.getElementById('sp-note').value.trim(),
  };

  if (!body.family || !body.school_year || !body.amount || !body.date) {
    errEl.textContent = 'Famille, année scolaire, montant et date sont obligatoires.';
    errEl.classList.remove('hidden');
    return;
  }

  const id     = document.getElementById('sp-id').value;
  const url    = id ? `/school/payments/${id}/` : '/school/payments/';
  const method = id ? 'PUT' : 'POST';
  const res    = await apiFetch(url, method, body);
  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    errEl.classList.remove('hidden');
    return;
  }
  closeModal('modal-school-payment');
  toast(id ? 'Paiement modifié ✓ — Trésorerie mise à jour' : 'Paiement enregistré ✓ — Transaction trésorerie créée automatiquement');
  if (id) loadSchoolPaymentsList(); else loadFamilies();
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

// ── Liste des paiements école ─────────────────────────────────────────────────

async function loadSchoolPaymentsList() {
  const tbody = document.getElementById('school-payments-table');
  if (!tbody) return;
  tbody.innerHTML = skeletonRows(4, 9);

  const method = document.getElementById('sp-method-filter')?.value || '';
  const status = document.getElementById('sp-status-filter')?.value || '';
  const search = document.getElementById('sp-search')?.value.trim() || '';
  let url = '/school/payments/?ordering=-date&page_size=500';
  if (method) url += `&method=${method}`;
  if (status) url += `&status=${status}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;

  const res = await apiFetch(url);
  if (!res || !res.ok) { tbody.innerHTML = '<tr><td colspan="9">Erreur chargement</td></tr>'; return; }
  const data = await res.json();
  const payments = data.results || data;

  // KPI summary
  const summaryEl = document.getElementById('sp-summary');
  const totalEl = document.getElementById('sp-total-amount');
  const countEl = document.getElementById('sp-count');
  if (summaryEl && payments.length > 0) {
    const total = payments.reduce((s, p) => s + parseFloat(p.amount), 0);
    totalEl.textContent = total.toFixed(2) + ' €';
    countEl.textContent = payments.length;
    summaryEl.style.display = 'flex';
  } else if (summaryEl) {
    summaryEl.style.display = 'none';
  }

  if (!payments.length) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:32px;color:var(--muted);">Aucun paiement enregistré.</td></tr>`;
    return;
  }

  const methodLabels = { cash: 'Espèces', cheque: 'Chèque', virement: 'Virement', autre: 'Autre' };
  tbody.innerHTML = payments.map((p, i) => `
    <tr class="fade-in" style="animation-delay:${i * 20}ms">
      <td>${p.date}</td>
      <td><strong>${esc(p.family_name || '—')}</strong></td>
      <td>${esc(p.child_name || '<span class="text-muted">—</span>')}</td>
      <td>${esc(p.school_year_label || '—')}</td>
      <td><span class="badge badge-green">${parseFloat(p.amount).toFixed(2)} €</span></td>
      <td><span class="badge badge-gray">${methodLabels[p.method] || p.method}</span></td>
      <td><span class="badge ${p.status === 'validated' ? 'badge-green' : 'badge-yellow'}">${p.status === 'validated' ? '✅ Validé' : '⏳ En attente'}</span></td>
      <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(p.note || '') || '<span class="text-muted">—</span>'}</td>
      <td><div class="td-actions">
        <button class="btn btn-sm btn-icon" onclick="editSchoolPayment(${p.id})" title="Modifier">✏️</button>
        <button class="btn btn-sm btn-icon" onclick="downloadSchoolPaymentReceipt(${p.id}, ${JSON.stringify(p.family_name || p.child_name || '')})" title="Télécharger le reçu PDF">🧾</button>
        <button class="btn btn-danger btn-sm btn-icon" onclick="deleteSchoolPayment(${p.id})" title="Supprimer">🗑</button>
      </div></td>
    </tr>
  `).join('');
}

// -- Recu PDF paiement ecole
async function downloadSchoolPaymentReceipt(id, label) {
  showProgress();
  try {
    const res = await apiFetch(`/school/payments/${id}/receipt/`);
    if (!res || !res.ok) {
      const err = res ? await res.json().catch(() => ({})) : {};
      toast(err.detail || 'Erreur reception du recu', 'error', 4000);
      return;
    }
    const blob   = await res.blob();
    const objUrl = URL.createObjectURL(blob);
    const a      = document.createElement('a');
    a.href       = objUrl;
    a.download   = `recu_ecole_${(label || 'paiement').replace(/\s+/g, '_')}_${id}.pdf`;
    a.click();
    URL.revokeObjectURL(objUrl);
    toast('Recu telecharge ✓');
  } catch (e) {
    toast('Erreur : ' + e.message, 'error');
  } finally {
    hideProgress();
  }
}

async function deleteSchoolPayment(id) {
  const ok = await confirmDialog({ title: 'Supprimer ce paiement ?', msg: 'La transaction trésorerie associée sera aussi supprimée.', icon: '🗑️' });
  if (!ok) return;
  const res = await apiFetch(`/school/payments/${id}/`, 'DELETE');
  if (!res || res.ok) { toast('Paiement supprimé', 'info'); loadSchoolPaymentsList(); }
  else toast('Erreur suppression', 'error');
}
