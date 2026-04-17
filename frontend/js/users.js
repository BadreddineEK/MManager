/* ═══════════════════════════════════════════════════════════
   users.js — RBAC, gestion des utilisateurs
═══════════════════════════════════════════════════════════ */

const ROLE_LABELS = {
  ADMIN: '🔑 Admin', TRESORIER: '💼 Trésorier',
  ECOLE_MANAGER: '🎓 École Manager', TEACHER: '📖 Professeur',
  SECRETARY: '📝 Secrétaire', VIEWER: '👁️ Lecture seule', '': '—',
};
const ROLE_BADGE = {
  ADMIN: 'badge-red', TRESORIER: 'badge-blue',
  ECOLE_MANAGER: 'badge-green', VIEWER: 'badge-gray', '': '',
};

const PERM_MODULES = [
  { key: 'school',     label: '🎓 École',        hasDelete: true  },
  { key: 'membership', label: '🤝 Cotisations',   hasDelete: true  },
  { key: 'treasury',   label: '💰 Trésorerie',    hasDelete: true  },
  { key: 'campaigns',  label: '🎯 Cagnottes',     hasDelete: true  },
  { key: 'users',      label: '👥 Utilisateurs',  hasDelete: true  },
  { key: 'settings',   label: '⚙️ Paramètres',    hasDelete: false },
];

let currentUser = null;

// ── RBAC ──────────────────────────────────────────────────────────────────────
async function loadCurrentUser() {
  const res = await apiFetch('/users/me/');
  if (!res || !res.ok) return;
  currentUser = await res.json();
  applyRBAC();
}

function applyRBAC() {
  if (!currentUser) return;
  const perms  = currentUser.effective_permissions || {};
  const role   = currentUser.role || '';

  // Nav items — masquer si la permission est false
  // nav-school et nav-membership sont des divs de groupe
  // nav-audit et nav-import sont reservés aux ADMIN uniquement
  const isAdmin = role === 'ADMIN';
  const navMap = {
    'nav-school':         perms.school?.read,
    'nav-membership':     perms.membership?.read,
    'nav-treasury':       perms.treasury?.read,
    'nav-campaigns':      perms.campaigns?.read,
    'nav-unpaid-members': perms.membership?.read,
    'nav-users':          perms.users?.read,
    'nav-settings':       perms.settings?.read,
    'nav-audit':          isAdmin ? true : false,
    'nav-import':         isAdmin ? true : false,
  };
  Object.entries(navMap).forEach(([id, allowed]) => {
    const el = document.getElementById(id);
    if (el) el.style.display = (allowed === false) ? 'none' : '';
  });

  // Bottom nav — masquer si pas d'accès
  const bottomMap = {
    'bn-families': perms.school?.read,
    'bn-members':  perms.membership?.read,
    'bn-treasury': perms.treasury?.read,
  };
  Object.entries(bottomMap).forEach(([id, allowed]) => {
    const el = document.getElementById(id);
    if (el) el.style.display = (allowed === false) ? 'none' : '';
  });

  // Boutons d'ajout (write)
  const writeBtns = [
    ['btn-add-school',    perms.school?.write],
    ['btn-add-member',    perms.membership?.write],
    ['btn-add-treasury',  perms.treasury?.write],
    ['btn-add-campaign',  perms.campaigns?.write],
    ['btn-add-user',      perms.users?.write],
    ['btn-bulk-school',   perms.school?.write],
    ['btn-bulk-members',  perms.membership?.write],
    ['btn-bulk-treasury', perms.treasury?.write],
  ];
  writeBtns.forEach(([id, allowed]) => {
    const el = document.getElementById(id);
    if (el) el.style.display = (allowed === false) ? 'none' : '';
  });

  // Bouton Enregistrer paramètres
  const saveSettingsBtn = document.getElementById('btn-save-settings');
  if (saveSettingsBtn) saveSettingsBtn.style.display = (perms.settings?.write === false) ? 'none' : '';

  // Rôle dans le chip utilisateur
  const roleDisplay = document.getElementById('user-role-display');
  if (roleDisplay) roleDisplay.textContent = ROLE_LABELS[role] || role || '—';

  // Rediriger automatiquement vers la 1ère section accessible pour les non-ADMIN
  _redirectToFirstAllowedSection(perms, role);
}

// ── Redirection vers la 1ère section accessible ───────────────────────────────
function _redirectToFirstAllowedSection(perms, role) {
  if (role === 'ADMIN' || !role) return;
  const ordered = [
    { section: 'treasury',  allowed: perms.treasury?.read },
    { section: 'families',  allowed: perms.school?.read },
    { section: 'members',   allowed: perms.membership?.read },
    { section: 'campaigns', allowed: perms.campaigns?.read },
  ];
  const first = ordered.find(x => x.allowed === true);
  if (first) showSection(first.section);
}

// ── Liste utilisateurs ────────────────────────────────────────────────────────
async function loadUsers() {
  document.getElementById('users-table').innerHTML = skeletonRows(3, 7);
  const res = await apiFetch('/users/');
  if (!res || !res.ok) { toast('Erreur chargement utilisateurs', 'error'); return; }
  const users = await res.json();
  const tbody = document.getElementById('users-table');
  if (!users.length) {
    tbody.innerHTML = emptyState({
      icon: '👤', title: 'Aucun utilisateur',
      sub: 'Créez un premier compte utilisateur.',
      actionLabel: '+ Ajouter un utilisateur', actionFn: 'openUserModal()',
    });
    return;
  }
  tbody.innerHTML = '';
  users.forEach((u, i) => {
    const perms = u.effective_permissions || {};
    const permsSummary = PERM_MODULES
      .filter(m => perms[m.key]?.read)
      .map(m => m.label).join(', ') || '—';
    const tr = document.createElement('tr');
    tr.className = 'fade-in';
    tr.style.animationDelay = `${i * 30}ms`;
    tr.innerHTML = `
      <td><strong>${u.username_display || u.username}</strong></td>
      <td>${u.email || '<span style="color:var(--muted)">—</span>'}</td>
      <td>${u.first_name || ''} ${u.last_name || ''}</td>
      <td><span class="badge ${ROLE_BADGE[u.role] || 'badge-gray'}">${ROLE_LABELS[u.role] || u.role}</span></td>
      <td style="font-size:0.78rem;color:var(--muted);max-width:200px;">${u.role === 'ADMIN' ? '<em>Tout</em>' : permsSummary}</td>
      <td>${u.is_active ? '<span class="badge badge-green">✅ Actif</span>' : '<span class="badge badge-red">❌ Inactif</span>'}</td>
      <td><div class="td-actions">
        <button class="btn btn-sm btn-icon" onclick="openUserModal(${u.id})" title="Modifier">✏️</button>
        <button class="btn btn-danger btn-sm btn-icon" onclick="deleteUser(${u.id}, '${u.username}')" title="Supprimer">🗑</button>
      </div></td>`;
    tbody.appendChild(tr);
  });
}

// ── Grille permissions ────────────────────────────────────────────────────────
function renderPermsTable(permsData) {
  const tbody = document.getElementById('user-modal-perms-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  PERM_MODULES.forEach(mod => {
    const p  = permsData?.[mod.key] || {};
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid var(--border)';
    tr.innerHTML = `
      <td style="padding:7px 8px;font-weight:500;">${mod.label}</td>
      <td style="text-align:center;padding:7px 4px;">
        <input type="checkbox" data-mod="${mod.key}" data-act="read"   ${p.read   ? 'checked' : ''} onchange="syncPermCheckbox(this)" />
      </td>
      <td style="text-align:center;padding:7px 4px;">
        <input type="checkbox" data-mod="${mod.key}" data-act="write"  ${p.write  ? 'checked' : ''} onchange="syncPermCheckbox(this)" />
      </td>
      <td style="text-align:center;padding:7px 4px;">
        ${mod.hasDelete
          ? `<input type="checkbox" data-mod="${mod.key}" data-act="delete" ${p.delete ? 'checked' : ''} onchange="syncPermCheckbox(this)" />`
          : '<span style="color:var(--muted);">—</span>'
        }
      </td>`;
    tbody.appendChild(tr);
  });
}

function syncPermCheckbox(cb) {
  const mod     = cb.dataset.mod;
  const act     = cb.dataset.act;
  const checked = cb.checked;
  const getBox  = a => document.querySelector(`input[data-mod="${mod}"][data-act="${a}"]`);
  if (checked) {
    if (act === 'write')  { const r = getBox('read');  if (r) r.checked = true; }
    if (act === 'delete') { const r = getBox('read'); const w = getBox('write'); if (r) r.checked = true; if (w) w.checked = true; }
  } else {
    if (act === 'read')  { const w = getBox('write'); const d = getBox('delete'); if (w) w.checked = false; if (d) d.checked = false; }
    if (act === 'write') { const d = getBox('delete'); if (d) d.checked = false; }
  }
}

function readPermsFromModal() {
  const perms = {};
  PERM_MODULES.forEach(mod => {
    const r = document.querySelector(`input[data-mod="${mod.key}"][data-act="read"]`);
    const w = document.querySelector(`input[data-mod="${mod.key}"][data-act="write"]`);
    const d = document.querySelector(`input[data-mod="${mod.key}"][data-act="delete"]`);
    perms[mod.key] = {
      read:  r ? r.checked : false,
      write: w ? w.checked : false,
      ...(mod.hasDelete ? { delete: d ? d.checked : false } : {}),
    };
  });
  return perms;
}

function onUserRoleChange() {
  const role    = document.getElementById('user-modal-role').value;
  const section = document.getElementById('user-modal-perms-section');
  if (role === 'ADMIN') {
    section.style.opacity       = '0.4';
    section.style.pointerEvents = 'none';
    renderPermsTable({
      school:     { read: true, write: true, delete: true },
      membership: { read: true, write: true, delete: true },
      treasury:   { read: true, write: true, delete: true },
      campaigns:  { read: true, write: true, delete: true },
      users:      { read: true, write: true, delete: true },
      settings:   { read: true, write: true },
    });
  } else {
    section.style.opacity       = '1';
    section.style.pointerEvents = '';
    if (role === 'TRESORIER') {
      renderPermsTable({
        school:     { read: false, write: false, delete: false },
        membership: { read: true,  write: true,  delete: false },
        treasury:   { read: true,  write: true,  delete: false },
        campaigns:  { read: true,  write: true,  delete: false },
        users:      { read: false, write: false, delete: false },
        settings:   { read: false, write: false },
      });
    } else if (role === 'ECOLE_MANAGER') {
      renderPermsTable({
        school:     { read: true,  write: true,  delete: false },
        membership: { read: false, write: false, delete: false },
        treasury:   { read: false, write: false, delete: false },
        campaigns:  { read: false, write: false, delete: false },
        users:      { read: false, write: false, delete: false },
        settings:   { read: false, write: false },
      });
    } else if (role === 'VIEWER') {
      renderPermsTable({
        school:     { read: true,  write: false, delete: false },
        membership: { read: true,  write: false, delete: false },
        treasury:   { read: true,  write: false, delete: false },
        campaigns:  { read: true,  write: false, delete: false },
        users:      { read: false, write: false, delete: false },
        settings:   { read: false, write: false },
      });
    } else if (role === 'TEACHER') {
      renderPermsTable({
        school:     { read: true,  write: false, delete: false },
        membership: { read: false, write: false, delete: false },
        treasury:   { read: false, write: false, delete: false },
        campaigns:  { read: false, write: false, delete: false },
        users:      { read: false, write: false, delete: false },
        settings:   { read: false, write: false },
      });
    } else if (role === 'SECRETARY') {
      renderPermsTable({
        school:     { read: false, write: false, delete: false },
        membership: { read: true,  write: true,  delete: false },
        treasury:   { read: true,  write: false, delete: false },
        campaigns:  { read: false, write: false, delete: false },
        users:      { read: false, write: false, delete: false },
        settings:   { read: false, write: false },
      });
    } else {
      renderPermsTable({});
    }
  }
}

function openUserModal(userId = null) {
  document.getElementById('user-modal-id').value          = userId || '';
  document.getElementById('user-modal-title').textContent = userId ? "Modifier l'utilisateur" : 'Créer un utilisateur';
  document.getElementById('user-modal-username').value    = '';
  document.getElementById('user-modal-email').value       = '';
  document.getElementById('user-modal-firstname').value   = '';
  document.getElementById('user-modal-lastname').value    = '';
  document.getElementById('user-modal-password').value    = '';
  document.getElementById('user-modal-role').value        = 'ECOLE_MANAGER';
  document.getElementById('user-modal-active').checked    = true;
  document.getElementById('user-modal-username-row').style.display = userId ? 'none' : '';
  document.getElementById('user-modal-pw-hint').textContent        = userId ? '(laisser vide pour ne pas changer)' : '';

  if (userId) {
    apiFetch(`/users/${userId}/`).then(r => r && r.json()).then(u => {
      if (!u) return;
      document.getElementById('user-modal-email').value     = u.email;
      document.getElementById('user-modal-firstname').value = u.first_name || '';
      document.getElementById('user-modal-lastname').value  = u.last_name  || '';
      document.getElementById('user-modal-role').value      = u.role || '';
      document.getElementById('user-modal-active').checked  = u.is_active;
      const permsData = u.role === 'ADMIN' ? u.effective_permissions : (u.permissions_data || {});
      const section   = document.getElementById('user-modal-perms-section');
      if (u.role === 'ADMIN') { section.style.opacity = '0.4'; section.style.pointerEvents = 'none'; }
      else                    { section.style.opacity = '1';   section.style.pointerEvents = ''; }
      renderPermsTable(permsData);
    });
  } else {
    onUserRoleChange();
  }
  openModal('modal-user');
}

async function saveUser() {
  const userId = document.getElementById('user-modal-id').value;
  const role   = document.getElementById('user-modal-role').value;
  const payload = {
    email:            document.getElementById('user-modal-email').value.trim(),
    first_name:       document.getElementById('user-modal-firstname').value.trim(),
    last_name:        document.getElementById('user-modal-lastname').value.trim(),
    role:             role,
    is_active:        document.getElementById('user-modal-active').checked,
    permissions_data: role === 'ADMIN' ? {} : readPermsFromModal(),
  };
  const pw = document.getElementById('user-modal-password').value;
  if (pw) payload.password = pw;

  let res;
  if (userId) {
    res = await apiFetch(`/users/${userId}/`, 'PUT', payload);
  } else {
    payload.username = document.getElementById('user-modal-username').value.trim();
    res = await apiFetch('/users/', 'POST', payload);
  }
  if (!res) return;
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    toast(JSON.stringify(err), 'error', 5000);
    return;
  }
  closeModal('modal-user');
  toast(userId ? 'Utilisateur mis à jour ✓' : 'Utilisateur créé ✓');
  loadUsers();
}

async function deleteUser(userId, username) {
  const ok = await confirmDialog({
    title: `Supprimer "${username}" ?`,
    msg:   'Cet utilisateur sera définitivement supprimé.', icon: '🗑️',
  });
  if (!ok) return;
  const res = await apiFetch(`/users/${userId}/`, 'DELETE');
  if (res && res.status === 204) { toast('Utilisateur supprimé', 'info'); loadUsers(); }
}
