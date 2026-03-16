/* ═══════════════════════════════════════════════════════════
   treasury.js — Transactions, reçus fiscaux PDF
═══════════════════════════════════════════════════════════ */

async function loadTreasury() {
  document.getElementById('treasury-table').innerHTML = skeletonRows(4, 9);
  const direction = document.getElementById('trs-direction-filter').value;
  const category  = document.getElementById('trs-category-filter').value;
  const regime    = document.getElementById('trs-regime-filter').value;
  const month     = document.getElementById('trs-month-filter').value;
  const search    = document.getElementById('trs-search').value.trim();

  let url = '/treasury/transactions/?ordering=-date';
  if (direction) url += `&direction=${direction}`;
  if (category)  url += `&category=${category}`;
  if (regime)    url += `&regime=${regime}`;
  if (month)     url += `&month=${month}`;
  if (search)    url += `&search=${encodeURIComponent(search)}`;

  const res = await apiFetch(url);
  if (!res || !res.ok) return;
  const data = await res.json();
  renderTreasury(data.results || data);

  // Résumé du mois
  const today  = new Date().toISOString().slice(0, 7);
  const sumUrl = `/treasury/transactions/summary/?month=${month || today}`;
  const sumRes = await apiFetch(sumUrl);
  if (sumRes && sumRes.ok) {
    const s = await sumRes.json();
    document.getElementById('trs-in').textContent  = `${s.total_in.toFixed(2)} €`;
    document.getElementById('trs-out').textContent = `${s.total_out.toFixed(2)} €`;
    const balEl = document.getElementById('trs-balance');
    balEl.textContent = `${s.balance.toFixed(2)} €`;
    balEl.style.color = s.balance >= 0 ? '#16a34a' : '#dc2626';
  }
}

function renderTreasury(txs) {
  const tbody = document.getElementById('treasury-table');
  if (!txs.length) {
    tbody.innerHTML = emptyState({
      icon: '🏦', title: 'Aucune transaction enregistrée',
      sub: 'Ajoutez une entrée ou sortie depuis le bouton ci-dessus.',
      actionLabel: '+ Ajouter une transaction', actionFn: 'openTreasuryModal()',
    });
    return;
  }
  tbody.innerHTML = txs.map((tx, i) => {
    const isIn = tx.direction === 'IN';
    const dirBadge = isIn
      ? '<span class="badge badge-green">▲ Entrée</span>'
      : '<span class="badge badge-red">▼ Sortie</span>';
    const regimeBadge = tx.regime_fiscal === '1901'
      ? '<span class="badge badge-1901">1901</span>'
      : tx.regime_fiscal === '1905'
        ? '<span class="badge badge-1905">1905</span>'
        : '<span style="color:var(--muted);font-size:.8rem;">—</span>';
    return `
    <tr class="fade-in" style="animation-delay:${i * 30}ms">
      <td>${tx.date}</td>
      <td><strong>${esc(tx.label)}</strong></td>
      <td><span class="badge badge-gray">${esc(tx.category_display)}</span></td>
      <td>${dirBadge}</td>
      <td style="font-weight:700;" class="${isIn ? 'text-green' : 'text-red'}">${parseFloat(tx.amount).toFixed(2)} €</td>
      <td><span class="badge badge-blue">${esc(tx.method_display)}</span></td>
      <td>${regimeBadge}</td>
      <td style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(tx.note)||''}">${esc(tx.note) || '<span class="text-muted">—</span>'}</td>
      <td><div class="td-actions">
        <button class="btn btn-sm btn-icon" onclick="editTreasuryTransaction(${tx.id})" title="Modifier">✏️</button>
        <button class="btn btn-sm btn-icon" onclick="downloadTxReceipt(${tx.id}, '${esc(tx.label).replace(/'/g, "\\'")}')" title="Reçu PDF">🧾</button>
        <button class="btn btn-danger btn-sm btn-icon" onclick="deleteTreasuryTransaction(${tx.id})" title="Supprimer">🗑</button>
      </div></td>
    </tr>`;
  }).join('');
}

function openTreasuryModal() {
  document.getElementById('trs-id').value        = '';
  document.getElementById('trs-direction').value = 'IN';
  document.getElementById('trs-category').value  = 'don';
  document.getElementById('trs-label').value     = '';
  document.getElementById('trs-date').value      = new Date().toISOString().split('T')[0];
  document.getElementById('trs-amount').value    = '';
  document.getElementById('trs-method').value    = 'cash';
  document.getElementById('trs-note').value      = '';
  document.getElementById('trs-regime').value    = '';
  document.getElementById('trs-campaign').value  = '';
  _fillCampaignSelect();
  document.getElementById('modal-treasury-title').textContent = 'Ajouter une transaction';
  document.getElementById('modal-trs-error').classList.add('hidden');
  openModal('modal-treasury');
}

function _fillCampaignSelect() {
  const sel = document.getElementById('trs-campaign');
  sel.innerHTML = '<option value="">— Aucune cagnotte —</option>';
  (allCampaigns || []).forEach(c => {
    sel.innerHTML += `<option value="${c.id}">${esc(c.icon)} ${esc(c.name)}</option>`;
  });
}

async function editTreasuryTransaction(id) {
  const res = await apiFetch(`/treasury/transactions/${id}/`);
  if (!res || !res.ok) return;
  const tx = await res.json();
  document.getElementById('trs-id').value        = tx.id;
  document.getElementById('trs-direction').value = tx.direction;
  document.getElementById('trs-category').value  = tx.category;
  document.getElementById('trs-label').value     = tx.label;
  document.getElementById('trs-date').value      = tx.date;
  document.getElementById('trs-amount').value    = tx.amount;
  document.getElementById('trs-method').value    = tx.method;
  document.getElementById('trs-note').value      = tx.note || '';
  document.getElementById('trs-regime').value    = tx.regime_fiscal || '';
  _fillCampaignSelect();
  document.getElementById('trs-campaign').value  = tx.campaign || '';
  document.getElementById('modal-treasury-title').textContent = 'Modifier la transaction';
  document.getElementById('modal-trs-error').classList.add('hidden');
  openModal('modal-treasury');
}

async function saveTreasuryTransaction() {
  const id   = document.getElementById('trs-id').value;
  const body = {
    direction:     document.getElementById('trs-direction').value,
    category:      document.getElementById('trs-category').value,
    label:         document.getElementById('trs-label').value.trim(),
    date:          document.getElementById('trs-date').value,
    amount:        parseFloat(document.getElementById('trs-amount').value),
    method:        document.getElementById('trs-method').value,
    note:          document.getElementById('trs-note').value.trim(),
    regime_fiscal: document.getElementById('trs-regime').value || '',
    campaign:      document.getElementById('trs-campaign').value
                     ? parseInt(document.getElementById('trs-campaign').value)
                     : null,
  };
  const errEl = document.getElementById('modal-trs-error');
  if (!body.label || !body.date || !body.amount) {
    errEl.textContent = 'Libellé, date et montant sont obligatoires.';
    errEl.classList.remove('hidden');
    return;
  }
  const res = await apiFetch(
    id ? `/treasury/transactions/${id}/` : '/treasury/transactions/',
    id ? 'PUT' : 'POST',
    body
  );
  if (!res || !res.ok) {
    const err = await res.json().catch(() => ({}));
    errEl.textContent = JSON.stringify(err);
    errEl.classList.remove('hidden');
    return;
  }
  closeModal('modal-treasury');
  toast(id ? 'Transaction mise à jour ✓' : 'Transaction enregistrée ✓');
  loadTreasury();
}

async function deleteTreasuryTransaction(id) {
  const ok = await confirmDialog({ title: 'Supprimer cette transaction ?', msg: 'Cette action est irréversible.', icon: '🗑️' });
  if (!ok) return;
  await apiFetch(`/treasury/transactions/${id}/`, 'DELETE');
  toast('Transaction supprimée', 'info');
  loadTreasury();
}

// ── Reçus fiscaux PDF ─────────────────────────────────────────────────────────
async function downloadTxReceipt(id, label) {
  const donor = prompt(`Reçu pour "${label}"\n\nNom du donateur (laisser vide si non applicable) :`);
  if (donor === null) return;
  showProgress();
  const donorParam = donor.trim() ? `?donor=${encodeURIComponent(donor.trim())}` : '';
  try {
    const res = await fetch(`${API}/treasury/receipt/transaction/${id}/${donorParam}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!res.ok) { toast('Erreur génération PDF', 'error'); return; }
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `recu_${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    toast('Reçu PDF téléchargé ✓');
  } catch (e) {
    toast('Erreur : ' + e.message, 'error');
  } finally {
    hideProgress();
  }
}

function openAnnualReceiptModal() {
  document.getElementById('annual-receipt-donor').value = '';
  document.getElementById('annual-receipt-year').value  = new Date().getFullYear();
  document.getElementById('annual-receipt-cat').value   = '';
  openModal('modal-annual-receipt');
}

async function downloadAnnualReceipt() {
  const donor = document.getElementById('annual-receipt-donor').value.trim();
  const year  = document.getElementById('annual-receipt-year').value;
  const cat   = document.getElementById('annual-receipt-cat').value;
  let url = `/api/treasury/receipt/annual/?year=${year}`;
  if (donor) url += `&donor=${encodeURIComponent(donor)}`;
  if (cat)   url += `&category=${cat}`;
  showProgress();
  try {
    const res = await fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      toast(err.detail || 'Aucune transaction trouvée pour cette période', 'error', 5000);
      return;
    }
    const blob   = await res.blob();
    const objUrl = URL.createObjectURL(blob);
    const a      = document.createElement('a');
    a.href     = objUrl;
    a.download = `recap_dons_${year}.pdf`;
    a.click();
    URL.revokeObjectURL(objUrl);
    closeModal('modal-annual-receipt');
    toast('Récapitulatif PDF téléchargé ✓');
  } catch (e) {
    toast('Erreur : ' + e.message, 'error');
  } finally {
    hideProgress();
  }
}
