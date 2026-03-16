/* ═══════════════════════════════════════════════════════════
   audit.js — Journal d'audit des actions sensibles
═══════════════════════════════════════════════════════════ */

const ACTION_BADGE = {
  CREATE:      { label: 'Création',      cls: 'badge-green'  },
  UPDATE:      { label: 'Modification',  cls: 'badge-blue'   },
  DELETE:      { label: 'Suppression',   cls: 'badge-red'    },
  LOGIN:       { label: 'Connexion',     cls: 'badge-gray'   },
  LOGOUT:      { label: 'Déconnexion',   cls: 'badge-gray'   },
  EXPORT:      { label: 'Export',        cls: 'badge-purple' },
  IMPORT:      { label: 'Import',        cls: 'badge-purple' },
  SEND_NOTIF:  { label: 'Notification',  cls: 'badge-orange' },
};

const ENTITY_ICON = {
  Family:           '👨‍👩‍👧',
  Child:            '🧒',
  SchoolPayment:    '💳',
  SchoolYear:       '📅',
  Member:           '🤝',
  MembershipPayment:'💳',
  MembershipYear:   '📅',
  TreasuryTransaction:'💰',
  Campaign:         '🎯',
  User:             '👤',
  SchoolArrears:    '📧',
  MembershipUnpaid: '📧',
};

let _auditPage      = 1;
let _auditTotalPages = 1;

async function loadAudit(page = 1) {
  _auditPage = page;
  const alert = document.getElementById('audit-alert');
  alert.textContent = '';

  const action   = document.getElementById('audit-filter-action').value;
  const entity   = document.getElementById('audit-filter-entity').value.trim();
  const userId   = document.getElementById('audit-filter-user').value.trim();
  const dateFrom = document.getElementById('audit-filter-from').value;
  const dateTo   = document.getElementById('audit-filter-to').value;

  const params = new URLSearchParams({ page });
  if (action)   params.set('action', action);
  if (entity)   params.set('entity', entity);
  if (userId)   params.set('user_id', userId);
  if (dateFrom) params.set('from', dateFrom);
  if (dateTo)   params.set('to', dateTo);

  const res = await apiFetch(`/audit/?${params}`);
  if (!res) return;
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert.innerHTML = `<div class="alert alert-error">${err.detail || 'Erreur chargement audit'}</div>`;
    return;
  }
  const data = await res.json();
  renderAuditLogs(data);
}

function renderAuditLogs(data) {
  const tbody = document.getElementById('audit-table');
  const info  = document.getElementById('audit-info');
  const pager = document.getElementById('audit-pager');

  _auditTotalPages = data.total_pages || 1;
  const count = data.count || 0;

  info.textContent = `${count} entrée${count > 1 ? 's' : ''} trouvée${count > 1 ? 's' : ''}`;

  if (!data.results || data.results.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:32px;">Aucun événement trouvé.</td></tr>';
    pager.innerHTML = '';
    return;
  }

  tbody.innerHTML = data.results.map(log => {
    const badge  = ACTION_BADGE[log.action] || { label: log.action, cls: 'badge-gray' };
    const icon   = ENTITY_ICON[log.entity] || '🔹';
    const user   = log.user ? log.user.display || log.user.username : '<span style="color:var(--muted)">Système</span>';
    const dt     = new Date(log.created_at);
    const dateStr = dt.toLocaleDateString('fr-FR', { day:'2-digit', month:'2-digit', year:'numeric' });
    const timeStr = dt.toLocaleTimeString('fr-FR', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
    const payloadStr = log.payload && Object.keys(log.payload).length
      ? Object.entries(log.payload).map(([k,v]) => `<span class="audit-kv"><b>${k}</b>: ${v}</span>`).join(' ')
      : '<span style="color:var(--muted)">—</span>';

    return `<tr>
      <td style="white-space:nowrap;">
        <div style="font-size:0.85rem;font-weight:600;">${dateStr}</div>
        <div style="font-size:0.75rem;color:var(--muted);">${timeStr}</div>
      </td>
      <td style="font-size:0.85rem;">${user}</td>
      <td><span class="badge ${badge.cls}">${badge.label}</span></td>
      <td style="font-size:0.85rem;">${icon} ${log.entity}</td>
      <td style="font-size:0.82rem;color:var(--muted);">${log.entity_id ?? '—'}</td>
      <td style="font-size:0.78rem;line-height:1.7;">${payloadStr}</td>
    </tr>`;
  }).join('');

  // Pagination
  const prevDisabled = _auditPage <= 1 ? 'disabled' : '';
  const nextDisabled = _auditPage >= _auditTotalPages ? 'disabled' : '';
  pager.innerHTML = `
    <div class="pagination">
      <button class="btn btn-sm" ${prevDisabled} onclick="loadAudit(${_auditPage - 1})">‹ Précédent</button>
      <span style="font-size:0.82rem;color:var(--muted);">Page ${_auditPage} / ${_auditTotalPages}</span>
      <button class="btn btn-sm" ${nextDisabled} onclick="loadAudit(${_auditPage + 1})">Suivant ›</button>
    </div>`;
}

function resetAuditFilters() {
  document.getElementById('audit-filter-action').value = '';
  document.getElementById('audit-filter-entity').value = '';
  document.getElementById('audit-filter-user').value   = '';
  document.getElementById('audit-filter-from').value   = '';
  document.getElementById('audit-filter-to').value     = '';
  loadAudit(1);
}
