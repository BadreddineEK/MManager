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

// ── Cotisations → Trésorerie ──────────────────────────────────────────────────
/**
 * Ouvre le modal trésorerie pré-rempli pour une cotisation adhérent.
 * @param {number} memberId   - ID de l'adhérent (optionnel)
 * @param {string} memberName - Nom affiché dans le libellé (optionnel)
 */
function addMembershipPayment(memberId = null, memberName = '') {
  if (typeof openTreasuryModal !== 'function') {
    toast('Module trésorerie non chargé', 'error');
    return;
  }
  openTreasuryModal({ category: 'cotisation', memberId, memberName });
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
