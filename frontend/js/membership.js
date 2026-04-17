/* ═══════════════════════════════════════════════════════════
   membership.js — Adhérents, non-cotisants
   (les cotisations passent par la trésorerie)
═══════════════════════════════════════════════════════════ */

// ── Adhérents ─────────────────────────────────────────────────────────────────
async function loadMembers() {
  document.getElementById('members-table').innerHTML = skeletonRows(4, 6);
  const status = document.getElementById('member-status-filter').value;
  const search = document.getElementById('member-search').value.trim();
  let url = '/membership/members/?';
  if (status) url += `status=${status}&`;
  if (search) url += `search=${encodeURIComponent(search)}`;
  const res = await apiFetch(url);
  if (!res || !res.ok) return;
  const data = await res.json();
  allMembers = data.results || data;
  renderMembers(allMembers);
}

function renderMembers(members) {
  const tbody = document.getElementById('members-table');
  if (!members.length) {
    tbody.innerHTML = emptyState({
      icon: '🪪', title: 'Aucun adhérent enregistré',
      sub: 'Ajoutez des adhérents depuis le bouton ci-dessus.',
      actionLabel: '+ Ajouter un adhérent', actionFn: 'openMemberModal()',
    });
    return;
  }
  tbody.innerHTML = members.map((m, i) => {
    const badge = m.is_current_year_paid
      ? '<span class="badge badge-green">✅ À jour</span>'
      : '<span class="badge badge-red">❌ Non cotisant</span>';
    return `
    <tr class="fade-in" style="animation-delay:${i * 30}ms">
      <td><strong>${esc(m.full_name)}</strong></td>
      <td>${esc(m.phone)  || '<span class="text-muted">—</span>'}</td>
      <td>${esc(m.email)  || '<span class="text-muted">—</span>'}</td>
      <td>${badge}</td>
      <td><span class="badge badge-gray">${parseFloat(m.total_paid || 0).toFixed(2)} €</span></td>
      <td><div class="td-actions">
        <button class="btn btn-sm btn-icon" onclick="editMember(${m.id})" title="Modifier">✏️</button>
        <button class="btn btn-sm btn-icon" onclick="addMembershipPayment(${m.id}, '${esc(m.full_name).replace(/'/g, "\\'")}')" title="Enregistrer une cotisation">💳</button>
        <button class="btn btn-sm btn-icon" onclick="downloadMemberSheet(${m.id}, '${esc(m.full_name).replace(/'/g, "\\'")}')" title="Fiche adhérent PDF">📄</button>
        <button class="btn btn-danger btn-sm btn-icon" onclick="deleteMember(${m.id})" title="Supprimer">🗑</button>
      </div></td>
    </tr>`;
  }).join('');
}

function searchMembers() { loadMembers(); }

function openMemberModal() {
  document.getElementById('member-id').value       = '';
  document.getElementById('member-fullname').value = '';
  document.getElementById('member-phone').value    = '';
  document.getElementById('member-email').value    = '';
  document.getElementById('member-address').value  = '';
  document.getElementById('modal-member-title').textContent = 'Ajouter un adhérent';
  document.getElementById('modal-member-error').classList.add('hidden');
  openModal('modal-member');
}

async function editMember(id) {
  const res = await apiFetch(`/membership/members/${id}/`);
  if (!res || !res.ok) return;
  const m = await res.json();
  document.getElementById('member-id').value       = m.id;
  document.getElementById('member-fullname').value = m.full_name;
  document.getElementById('member-phone').value    = m.phone   || '';
  document.getElementById('member-email').value    = m.email   || '';
  document.getElementById('member-address').value  = m.address || '';
  document.getElementById('modal-member-title').textContent = "Modifier l'adhérent";
  document.getElementById('modal-member-error').classList.add('hidden');
  openModal('modal-member');
}

async function saveMember() {
  const id   = document.getElementById('member-id').value;
  const body = {
    full_name: document.getElementById('member-fullname').value.trim(),
    phone:     document.getElementById('member-phone').value.trim(),
    email:     document.getElementById('member-email').value.trim(),
    address:   document.getElementById('member-address').value.trim(),
  };
  const errEl = document.getElementById('modal-member-error');
  if (!body.full_name) {
    errEl.textContent = 'Le nom complet est obligatoire.';
    errEl.classList.remove('hidden');
    return;
  }
  const res = await apiFetch(
    id ? `/membership/members/${id}/` : '/membership/members/',
    id ? 'PUT' : 'POST',
    body
  );
  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    errEl.classList.remove('hidden');
    return;
  }
  closeModal('modal-member');
  toast(id ? 'Adhérent mis à jour ✓' : 'Adhérent ajouté ✓');
  loadMembers();
}

async function deleteMember(id) {
  const ok = await confirmDialog({
    title: "Supprimer l'adhérent ?",
    msg:   'Toutes ses cotisations seront également supprimées.', icon: '🗑️',
  });
  if (!ok) return;
  await apiFetch(`/membership/members/${id}/`, 'DELETE');
  toast('Adhérent supprimé', 'info');
  loadMembers();
}

// ── Cotisations ───────────────────────────────────────────────────────────────

async function addMembershipPayment(memberId = null, memberName = '') {
  await Promise.all([
    _mpLoadMembers(),
    _mpLoadYears(),
  ]);

  if (memberId) {
    document.getElementById('mp-member').value = memberId;
  }

  document.getElementById('mp-amount').value = '';
  document.getElementById('mp-date').value   = new Date().toISOString().split('T')[0];
  document.getElementById('mp-method').value = 'cash';
  document.getElementById('mp-note').value   = '';
  document.getElementById('modal-mp-error').classList.add('hidden');
  openModal('modal-membership-payment');
}

async function _mpLoadMembers() {
  const res = await apiFetch('/membership/members/');
  if (!res || !res.ok) return;
  const data = await res.json();
  const members = data.results || data;
  const sel = document.getElementById('mp-member');
  sel.innerHTML = '<option value="">— Choisir un adhérent —</option>';
  members.forEach(m => {
    sel.innerHTML += `<option value="${m.id}">${esc(m.full_name)}</option>`;
  });
}

async function _mpLoadYears() {
  const res = await apiFetch('/membership/years/');
  if (!res || !res.ok) return;
  const data = await res.json();
  const years = data.results || data;
  const sel = document.getElementById('mp-year');
  sel.innerHTML = '<option value="">— Choisir une année —</option>';
  years.forEach(y => {
    sel.innerHTML += `<option value="${y.id}" ${y.is_active ? 'selected' : ''}>${y.year}${y.is_active ? ' ✓' : ''} — ${y.amount_expected} €</option>`;
  });
}

async function saveMembershipPayment() {
  const errEl = document.getElementById('modal-mp-error');
  const body = {
    member:          parseInt(document.getElementById('mp-member').value) || null,
    membership_year: parseInt(document.getElementById('mp-year').value)   || null,
    amount:          parseFloat(document.getElementById('mp-amount').value),
    date:            document.getElementById('mp-date').value,
    method:          document.getElementById('mp-method').value,
    note:            document.getElementById('mp-note').value.trim(),
  };

  if (!body.member || !body.membership_year || !body.amount || !body.date) {
    errEl.textContent = 'Adhérent, année, montant et date sont obligatoires.';
    errEl.classList.remove('hidden');
    return;
  }

  const res = await apiFetch('/membership/payments/', 'POST', body);
  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    errEl.classList.remove('hidden');
    return;
  }
  closeModal('modal-membership-payment');
  toast('Cotisation enregistrée ✓ — Transaction trésorerie créée automatiquement');
  loadMembers();
}

// ── Non cotisants ─────────────────────────────────────────────────────────────
async function loadUnpaidMembers() {
  const infoEl  = document.getElementById('unpaid-members-info');
  infoEl.classList.add('hidden');
  document.getElementById('unpaid-members-alert').innerHTML = '';
  document.getElementById('unpaid-members-table').innerHTML = skeletonRows(4, 4);

  const res = await apiFetch('/membership/members/unpaid/');
  if (!res) return;
  if (res.status === 404) {
    document.getElementById('unpaid-members-table').innerHTML = '';
    toast("Aucune année de cotisation active. Créez-en une depuis l'Admin Django.", 'error', 5000);
    return;
  }
  if (!res.ok) return;
  const data = await res.json();

  infoEl.textContent = `Année active : ${data.year} — ${data.count} adhérent(s) non cotisant(s) — Montant attendu : ${data.amount_expected.toFixed(2)} €`;
  infoEl.classList.remove('hidden');

  const tbody = document.getElementById('unpaid-members-table');
  if (!data.members.length) {
    tbody.innerHTML = emptyState({ icon: '✅', title: 'Tous les adhérents ont cotisé !', sub: 'Aucun impayé pour l\'année en cours.' });
    return;
  }
  tbody.innerHTML = data.members.map((m, i) => `
    <tr class="fade-in" style="animation-delay:${i * 30}ms">
      <td><strong>${esc(m.full_name)}</strong></td>
      <td>${esc(m.phone) || '<span class="text-muted">—</span>'}</td>
      <td>${esc(m.email) || '<span class="text-muted">—</span>'}</td>
      <td>${parseFloat(m.total_paid || 0).toFixed(2)} €</td>
    </tr>
  `).join('');
}

// ── Helpers sélects ───────────────────────────────────────────────────────────
async function loadMembershipYears() {
  const res = await apiFetch('/membership/years/');
  if (!res || !res.ok) return;
  const data = await res.json();
  membershipYears = data.results || data;
}

async function loadMembersForSelect(selectId) {
  if (!allMembers.length) {
    const res = await apiFetch('/membership/members/');
    if (res && res.ok) {
      const data = await res.json();
      allMembers = data.results || data;
    }
  }
  const sel = document.getElementById(selectId);
  sel.innerHTML = '<option value="">-- Choisir un adhérent --</option>';
  allMembers.forEach(m => {
    sel.innerHTML += `<option value="${m.id}">${esc(m.full_name)}</option>`;
  });
}

async function loadMembershipYearsForSelect(selectId) {
  if (!membershipYears.length) await loadMembershipYears();
  const sel = document.getElementById(selectId);
  sel.innerHTML = '<option value="">-- Choisir une année --</option>';
  membershipYears.forEach(y => {
    sel.innerHTML += `<option value="${y.id}">${y.year}${y.is_active ? ' ✓ active' : ''}</option>`;
  });
}

// ── Fiche adhérent PDF ────────────────────────────────────────────────────────
async function downloadMemberSheet(memberId, memberName) {
  showProgress();
  try {
    const res = await apiFetch(`/treasury/receipt/member/${memberId}/`);
    if (!res || !res.ok) {
      const err = res ? await res.json().catch(() => ({})) : {};
      toast(err.detail || 'Erreur lors de la génération de la fiche', 'error', 4000);
      return;
    }
    const blob   = await res.blob();
    const objUrl = URL.createObjectURL(blob);
    const a      = document.createElement('a');
    a.href       = objUrl;
    a.download   = `fiche_${memberName.replace(/\s+/g, '_')}.pdf`;
    a.click();
    URL.revokeObjectURL(objUrl);
    toast(`Fiche de ${memberName} téléchargée ✓`);
  } catch (e) {
    toast('Erreur : ' + e.message, 'error');
  } finally {
    hideProgress();
  }
}
