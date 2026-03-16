/* ═══════════════════════════════════════════════════════════
   campaigns.js — Cagnottes / collectes
═══════════════════════════════════════════════════════════ */

async function loadCampaigns() {
  const grid = document.getElementById('campaigns-grid');
  grid.innerHTML = skeletonRows(3, 3);
  const res = await apiFetch('/treasury/campaigns/');
  if (!res || !res.ok) {
    grid.innerHTML = emptyState({
      icon: '⚠️', title: 'Impossible de charger les cagnottes',
      sub: 'Vérifiez que la migration a bien été appliquée sur le serveur.',
    });
    return;
  }
  const data    = await res.json();
  allCampaigns  = data.results || data;
  renderCampaigns(allCampaigns);

  // Alimenter le filtre transactions cagnottes
  const sel = document.getElementById('campaign-tx-filter');
  sel.innerHTML = '<option value="">Toutes les cagnottes</option>';
  allCampaigns.forEach(c => {
    sel.innerHTML += `<option value="${c.id}">${esc(c.icon)} ${esc(c.name)}</option>`;
  });
  loadCampaignTransactions();
}

function renderCampaigns(campaigns) {
  const grid = document.getElementById('campaigns-grid');
  if (!campaigns.length) {
    grid.innerHTML = emptyState({
      icon: '🎯', title: 'Aucune cagnotte créée',
      sub: 'Créez une première cagnotte pour suivre vos collectes.',
      actionLabel: '+ Nouvelle cagnotte', actionFn: 'openCampaignModal()',
    });
    return;
  }
  const fmt = v => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(v);
  grid.innerHTML = campaigns.map((c, i) => {
    const pct        = c.progress_percent || 0;
    const isComplete = pct >= 100;
    const hasGoal    = c.goal_amount !== null && c.goal_amount !== undefined;
    return `
    <div class="campaign-card ${c.status === 'closed' ? 'closed' : ''}" style="animation-delay:${i * 60}ms">
      ${c.status === 'closed' ? '<span class="campaign-badge-closed">🔒 Clôturée</span>' : ''}
      <div class="campaign-card-header">
        <div class="campaign-icon-big">${esc(c.icon)}</div>
        <div>
          <div class="campaign-card-title">${esc(c.name)}</div>
          ${c.description ? `<div class="campaign-card-desc">${esc(c.description)}</div>` : ''}
        </div>
      </div>
      ${hasGoal ? `
        <div class="campaign-progress-bar">
          <div class="campaign-progress-fill ${isComplete ? 'complete' : ''}" style="width:${pct}%"></div>
        </div>
        <div class="campaign-amounts">
          <span>Collecté : <strong>${fmt(c.collected_amount)}</strong></span>
          <span><strong>${pct}%</strong> — Objectif : ${fmt(c.goal_amount)}</span>
        </div>
      ` : `
        <div class="campaign-amounts">
          <span>Collecté : <strong>${fmt(c.collected_amount)}</strong></span>
          <span style="color:var(--muted);font-size:0.8rem;">Pas d'objectif fixé</span>
        </div>
      `}
      ${c.end_date ? `<div style="font-size:0.78rem;color:var(--muted);">📅 Fin : ${c.end_date}</div>` : ''}
      <div class="campaign-card-actions">
        <button class="btn btn-sm btn-icon" onclick="editCampaign(${c.id})" title="Modifier">✏️ Modifier</button>
        <button class="btn btn-danger btn-sm btn-icon" onclick="deleteCampaign(${c.id})" title="Supprimer">🗑</button>
      </div>
    </div>`;
  }).join('');
}

async function loadCampaignTransactions() {
  const tbody      = document.getElementById('campaign-tx-table');
  tbody.innerHTML  = skeletonRows(3, 6);
  const campaignId = document.getElementById('campaign-tx-filter').value;
  let url = '/treasury/transactions/?ordering=-date';
  url += campaignId ? `&campaign=${campaignId}` : `&has_campaign=1`;
  const res = await apiFetch(url);
  if (!res || !res.ok) return;
  const data = await res.json();
  const txs  = data.results || data;
  if (!txs.length) {
    tbody.innerHTML = emptyState({
      icon: '📭', title: 'Aucune transaction liée',
      sub: 'Rattachez une transaction à une cagnotte depuis la Trésorerie.',
    });
    return;
  }
  tbody.innerHTML = txs.map((tx, i) => {
    const isIn = tx.direction === 'IN';
    return `<tr class="fade-in" style="animation-delay:${i * 30}ms">
      <td>${tx.date}</td>
      <td><strong>${esc(tx.label)}</strong></td>
      <td><span class="badge badge-purple">${esc(tx.campaign_name) || '—'}</span></td>
      <td>${isIn ? '<span class="badge badge-green">▲ Entrée</span>' : '<span class="badge badge-red">▼ Sortie</span>'}</td>
      <td style="font-weight:700;" class="${isIn ? 'text-green' : 'text-red'}">${parseFloat(tx.amount).toFixed(2)} €</td>
      <td><button class="btn btn-danger btn-sm btn-icon" onclick="deleteTreasuryTransaction(${tx.id})" title="Supprimer">🗑</button></td>
    </tr>`;
  }).join('');
}

function openCampaignModal() {
  document.getElementById('campaign-id').value          = '';
  document.getElementById('campaign-icon').value        = '🎯';
  document.getElementById('campaign-name').value        = '';
  document.getElementById('campaign-description').value = '';
  document.getElementById('campaign-goal').value        = '';
  document.getElementById('campaign-start').value       = '';
  document.getElementById('campaign-end').value         = '';
  document.getElementById('campaign-status').value      = 'active';
  document.getElementById('campaign-show-kpi').checked  = true;
  document.getElementById('modal-campaign-title').textContent = 'Nouvelle cagnotte';
  document.getElementById('modal-campaign-error').classList.add('hidden');
  openModal('modal-campaign');
}

async function editCampaign(id) {
  const res = await apiFetch(`/treasury/campaigns/${id}/`);
  if (!res || !res.ok) return;
  const c = await res.json();
  document.getElementById('campaign-id').value          = c.id;
  document.getElementById('campaign-icon').value        = c.icon;
  document.getElementById('campaign-name').value        = c.name;
  document.getElementById('campaign-description').value = c.description || '';
  document.getElementById('campaign-goal').value        = c.goal_amount || '';
  document.getElementById('campaign-start').value       = c.start_date  || '';
  document.getElementById('campaign-end').value         = c.end_date    || '';
  document.getElementById('campaign-status').value      = c.status;
  document.getElementById('campaign-show-kpi').checked  = c.show_on_kpi;
  document.getElementById('modal-campaign-title').textContent = 'Modifier la cagnotte';
  document.getElementById('modal-campaign-error').classList.add('hidden');
  openModal('modal-campaign');
}

async function saveCampaign() {
  const id      = document.getElementById('campaign-id').value;
  const goalRaw = document.getElementById('campaign-goal').value;
  const body    = {
    icon:        document.getElementById('campaign-icon').value.trim() || '🎯',
    name:        document.getElementById('campaign-name').value.trim(),
    description: document.getElementById('campaign-description').value.trim(),
    goal_amount: goalRaw ? parseFloat(goalRaw) : null,
    start_date:  document.getElementById('campaign-start').value || null,
    end_date:    document.getElementById('campaign-end').value   || null,
    status:      document.getElementById('campaign-status').value,
    show_on_kpi: document.getElementById('campaign-show-kpi').checked,
  };
  const errEl = document.getElementById('modal-campaign-error');
  if (!body.name) {
    errEl.textContent = 'Le nom de la cagnotte est obligatoire.';
    errEl.classList.remove('hidden');
    return;
  }
  const res = await apiFetch(
    id ? `/treasury/campaigns/${id}/` : '/treasury/campaigns/',
    id ? 'PUT' : 'POST',
    body
  );
  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    errEl.classList.remove('hidden');
    return;
  }
  closeModal('modal-campaign');
  toast(id ? 'Cagnotte mise à jour ✓' : 'Cagnotte créée ✓');
  loadCampaigns();
}

async function deleteCampaign(id) {
  const ok = await confirmDialog({
    title: 'Supprimer cette cagnotte ?',
    msg:   'Les transactions liées ne seront pas supprimées (juste déliées).', icon: '🗑️',
  });
  if (!ok) return;
  await apiFetch(`/treasury/campaigns/${id}/`, 'DELETE');
  toast('Cagnotte supprimée', 'info');
  loadCampaigns();
}
