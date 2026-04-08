/* ═══════════════════════════════════════════════════════════
   treasury.js — Transactions, reçus fiscaux PDF
═══════════════════════════════════════════════════════════ */

async function loadTreasury() {
  document.getElementById('treasury-table').innerHTML = skeletonRows(4, 9);
  const direction = document.getElementById('trs-direction-filter').value;
  const category  = document.getElementById('trs-category-filter').value;
  const regime    = document.getElementById('trs-regime-filter').value;
  const bankAcc   = document.getElementById('trs-bank-filter')?.value || '';
  const month     = document.getElementById('trs-month-filter').value;
  const year      = document.getElementById('trs-year-filter').value;
  const search    = document.getElementById('trs-search').value.trim();

  // Si mois est sélectionné, effacer le filtre année (et vice versa)
  if (month && year) {
    document.getElementById('trs-year-filter').value = '';
  }

  let url = '/treasury/transactions/?ordering=-date';
  if (direction) url += `&direction=${direction}`;
  if (category)  url += `&category=${category}`;
  if (regime)    url += `&regime=${regime}`;
  if (bankAcc)   url += `&bank_account=${bankAcc}`;
  if (month)     url += `&month=${month}`;
  else if (year) url += `&year=${year}`;
  if (search)    url += `&search=${encodeURIComponent(search)}`;

  const res = await apiFetch(url);
  if (!res || !res.ok) return;
  const data = await res.json();
  renderTreasury(data.results || data);

  // Résumé de la période affichée
  let sumUrl;
  if (month) {
    sumUrl = `/treasury/transactions/summary/?month=${month}`;
  } else if (year) {
    sumUrl = `/treasury/transactions/summary/?year=${year}`;
  } else {
    // Pas de filtre période : afficher le total cumulatif
    sumUrl = `/treasury/transactions/summary/?total=1`;
  }
  const sumRes = await apiFetch(sumUrl);
  if (sumRes && sumRes.ok) {
    const s = await sumRes.json();
    document.getElementById('trs-in').textContent  = `${s.total_in.toFixed(2)} €`;
    document.getElementById('trs-out').textContent = `${s.total_out.toFixed(2)} €`;
    const balEl = document.getElementById('trs-balance');
    balEl.textContent = `${s.balance.toFixed(2)} €`;
    balEl.style.color = s.balance >= 0 ? '#16a34a' : '#dc2626';

      // S3-5 — Soldes par régime fiscal
      const r1901 = (s.by_regime && s.by_regime['1901']) || {in: 0, out: 0};
      const r1905 = (s.by_regime && s.by_regime['1905']) || {in: 0, out: 0};
      const bal1901 = (r1901.in || 0) - (r1901.out || 0);
      const bal1905 = (r1905.in || 0) - (r1905.out || 0);
      const el1901 = document.getElementById('trs-balance-1901');
      const el1905 = document.getElementById('trs-balance-1905');
      if (el1901) {
        el1901.textContent = bal1901.toFixed(2) + ' €';
        el1901.style.color = bal1901 >= 0 ? '#16a34a' : '#dc2626';
      }
      if (el1905) {
        el1905.textContent = bal1905.toFixed(2) + ' €';
        el1905.style.color = bal1905 >= 0 ? '#16a34a' : '#dc2626';
      }
  }

  // Mettre à jour le libellé de la période dans les stats
  const inLbl  = document.querySelector('#trs-in + .lbl') || document.querySelector('#trs-in ~ .lbl');
  const outLbl = document.querySelector('#trs-out + .lbl') || document.querySelector('#trs-out ~ .lbl');
  const label  = month ? `Mois ${month}` : year ? `Année ${year}` : 'Total cumulatif';
  try {
    document.querySelector('.stat-card:nth-child(1) .lbl').textContent = `Entrées (${label})`;
    document.querySelector('.stat-card:nth-child(2) .lbl').textContent = `Sorties (${label})`;
    document.querySelector('.stat-card:nth-child(3) .lbl').textContent = month || year ? `Solde (${label})` : 'Solde total';
  } catch (e) { /* ignore */ }
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
        <button class="btn btn-sm btn-icon" onclick="downloadTxReceipt(${tx.id}, '${esc(tx.label).replace(/'/g, "\\'")}', '${tx.category}')" title="Reçu PDF">🧾</button>
        <button class="btn btn-danger btn-sm btn-icon" onclick="deleteTreasuryTransaction(${tx.id})" title="Supprimer">🗑</button>
      </div></td>
    </tr>`;
  }).join('');
}

function openTreasuryModal(prefill = {}) {
  document.getElementById('trs-id').value        = '';
  document.getElementById('trs-direction').value = 'IN';
  document.getElementById('trs-category').value  = prefill.category || 'don';
  document.getElementById('trs-label').value     = '';
  document.getElementById('trs-date').value      = new Date().toISOString().split('T')[0];
  document.getElementById('trs-amount').value    = '';
  document.getElementById('trs-method').value    = 'cash';
  document.getElementById('trs-note').value      = '';
  document.getElementById('trs-regime').value    = '';
  document.getElementById('trs-campaign').value  = '';
  _fillTrsBankSelect();
  _fillCampaignSelect();
  document.getElementById('modal-treasury-title').textContent = 'Ajouter une transaction';
  document.getElementById('modal-trs-error').classList.add('hidden');

  // Pré-remplissage conditionnel
  _onTrsCategoryChange().then(() => {
    if (prefill.familyId) {
      const sel = document.getElementById('trs-family');
      if (sel) sel.value = prefill.familyId;
    }
    if (prefill.memberId) {
      const sel = document.getElementById('trs-member');
      if (sel) sel.value = prefill.memberId;
    }
    if (prefill.familyName || prefill.memberName) {
      const name = prefill.familyName || prefill.memberName;
      const catLabel = prefill.category === 'ecole' ? 'Paiement école' : 'Cotisation';
      document.getElementById('trs-label').value = `${catLabel} — ${name}`;
    }
  });

  openModal('modal-treasury');
}

function _fillCampaignSelect() {
  const sel = document.getElementById('trs-campaign');
  sel.innerHTML = '<option value="">— Aucune cagnotte —</option>';
  (allCampaigns || []).forEach(c => {
    sel.innerHTML += `<option value="${c.id}">${esc(c.icon)} ${esc(c.name)}</option>`;
  });
}

/**
 * Affiche/masque les sélecteurs famille+année-école ou adhérent+année-cotisation
 * selon la catégorie sélectionnée. Charge les options au besoin.
 * @returns {Promise<void>}
 */
async function _onTrsCategoryChange() {
  const cat = document.getElementById('trs-category').value;
  const schoolBlock  = document.getElementById('trs-school-block');
  const memberBlock  = document.getElementById('trs-member-block');

  if (!schoolBlock || !memberBlock) return;

  schoolBlock.classList.add('hidden');
  memberBlock.classList.add('hidden');

  if (cat === 'ecole') {
    schoolBlock.classList.remove('hidden');
    // Charger familles si nécessaire
    if (!allFamilies || !allFamilies.length) {
      const res = await apiFetch('/school/families/');
      if (res && res.ok) {
        const data = await res.json();
        allFamilies = data.results || data;
      }
    }
    const famSel = document.getElementById('trs-family');
    famSel.innerHTML = '<option value="">— Famille (optionnel) —</option>';
    (allFamilies || []).forEach(f => {
      famSel.innerHTML += `<option value="${f.id}">${esc(f.primary_contact_name)}</option>`;
    });
    // Charger années scolaires
    if (!schoolYears || !schoolYears.length) await loadSchoolYears();
    const ySel = document.getElementById('trs-school-year');
    ySel.innerHTML = '<option value="">— Année scolaire (optionnel) —</option>';
    (schoolYears || []).forEach(y => {
      ySel.innerHTML += `<option value="${y.id}">${esc(y.label)}${y.is_active ? ' ✓' : ''}</option>`;
    });
  } else if (cat === 'cotisation') {
    memberBlock.classList.remove('hidden');
    // Charger adhérents si nécessaire
    if (!allMembers || !allMembers.length) {
      const res = await apiFetch('/membership/members/');
      if (res && res.ok) {
        const data = await res.json();
        allMembers = data.results || data;
      }
    }
    const mSel = document.getElementById('trs-member');
    mSel.innerHTML = '<option value="">— Adhérent (optionnel) —</option>';
    (allMembers || []).forEach(m => {
      mSel.innerHTML += `<option value="${m.id}">${esc(m.full_name)}</option>`;
    });
    // Charger années cotisation
    if (!membershipYears || !membershipYears.length) await loadMembershipYears();
    const mySel = document.getElementById('trs-membership-year');
    mySel.innerHTML = '<option value="">— Année (optionnel) —</option>';
    (membershipYears || []).forEach(y => {
      mySel.innerHTML += `<option value="${y.id}">${y.year}${y.is_active ? ' ✓' : ''}</option>`;
    });
  }
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
  _fillTrsBankSelect(tx.bank_account || null);
  _fillCampaignSelect();
  document.getElementById('trs-campaign').value  = tx.campaign || '';
  document.getElementById('modal-treasury-title').textContent = 'Modifier la transaction';
  document.getElementById('modal-trs-error').classList.add('hidden');

  // Charger sélecteurs conditionnels puis pré-remplir
  await _onTrsCategoryChange();
  if (tx.family) {
    const s = document.getElementById('trs-family');
    if (s) s.value = tx.family;
  }
  if (tx.school_year) {
    const s = document.getElementById('trs-school-year');
    if (s) s.value = tx.school_year;
  }
  if (tx.member) {
    const s = document.getElementById('trs-member');
    if (s) s.value = tx.member;
  }
  if (tx.membership_year) {
    const s = document.getElementById('trs-membership-year');
    if (s) s.value = tx.membership_year;
  }

  openModal('modal-treasury');
}

async function saveTreasuryTransaction() {
  const id  = document.getElementById('trs-id').value;
  const cat = document.getElementById('trs-category').value;

  const body = {
    direction:     document.getElementById('trs-direction').value,
    category:      cat,
    label:         document.getElementById('trs-label').value.trim(),
    date:          document.getElementById('trs-date').value,
    amount:        parseFloat(document.getElementById('trs-amount').value),
    method:        document.getElementById('trs-method').value,
    note:          document.getElementById('trs-note').value.trim(),
    regime_fiscal: document.getElementById('trs-regime').value || '',
    bank_account:  document.getElementById('trs-bank-account')?.value
                     ? parseInt(document.getElementById('trs-bank-account').value) : null,
    campaign:      document.getElementById('trs-campaign').value
                     ? parseInt(document.getElementById('trs-campaign').value)
                     : null,
    // FK optionnels école
    family:      (cat === 'ecole' && document.getElementById('trs-family')?.value)
                   ? parseInt(document.getElementById('trs-family').value) : null,
    school_year: (cat === 'ecole' && document.getElementById('trs-school-year')?.value)
                   ? parseInt(document.getElementById('trs-school-year').value) : null,
    // FK optionnels cotisation
    member:          (cat === 'cotisation' && document.getElementById('trs-member')?.value)
                       ? parseInt(document.getElementById('trs-member').value) : null,
    membership_year: (cat === 'cotisation' && document.getElementById('trs-membership-year')?.value)
                       ? parseInt(document.getElementById('trs-membership-year').value) : null,
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
async function downloadTxReceipt(id, label, category) {
  // Cotisation → reçu spécifique adhérent
  if (category === 'cotisation') {
    showProgress();
    try {
      const res = await fetch(`${API}/treasury/receipt/membership/${id}/`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) { toast('Erreur génération PDF cotisation', 'error'); return; }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `cotisation_${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast('Reçu de cotisation téléchargé ✓');
    } catch (e) {
      toast('Erreur : ' + e.message, 'error');
    } finally {
      hideProgress();
    }
    return;
  }

  // Autres catégories → reçu générique (don, école…)
  const donor = prompt(`Reçu pour "${label}"\n\nNom du donateur / bénéficiaire (laisser vide si non applicable) :`);
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
  document.getElementById('annual-receipt-year').value  = new Date().getFullYear();
  document.getElementById('annual-receipt-cat').value   = '';
  openModal('modal-annual-receipt');
}

async function downloadAnnualReceipt() {
  const year = document.getElementById('annual-receipt-year').value;
  const cat  = document.getElementById('annual-receipt-cat').value;
  if (!year) { toast('Veuillez saisir une année', 'error'); return; }
  let url = `/api/treasury/receipt/annual/?year=${year}`;
  if (cat) url += `&category=${cat}`;
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
    a.download = `bilan_${year}${cat ? '_' + cat : ''}.pdf`;
    a.click();
    URL.revokeObjectURL(objUrl);
    closeModal('modal-annual-receipt');
    toast('Bilan PDF téléchargé ✓');
  } catch (e) {
    toast('Erreur : ' + e.message, 'error');
  } finally {
    hideProgress();
  }
}

// ── Export CSV Trésorerie ─────────────────────────────────────────────────────
async function exportTreasuryCSV() {
  const direction = document.getElementById('trs-direction-filter').value;
  const category  = document.getElementById('trs-category-filter').value;
  const regime    = document.getElementById('trs-regime-filter').value;
  const bankAcc   = document.getElementById('trs-bank-filter')?.value || '';
  const month     = document.getElementById('trs-month-filter').value;
  const year      = document.getElementById('trs-year-filter').value;
  const search    = document.getElementById('trs-search').value.trim();

  // Récupère toutes les transactions avec les filtres actifs (sans pagination)
  let url = '/treasury/transactions/?ordering=-date&page_size=10000';
  if (direction) url += `&direction=${direction}`;
  if (category)  url += `&category=${category}`;
  if (regime)    url += `&regime=${regime}`;
  if (bankAcc)   url += `&bank_account=${bankAcc}`;
  if (month)     url += `&month=${month}`;
  else if (year) url += `&year=${year}`;
  if (search)    url += `&search=${encodeURIComponent(search)}`;

  showProgress();
  try {
    const res = await apiFetch(url);
    if (!res || !res.ok) { toast('Erreur chargement données', 'error'); return; }
    const data = await res.json();
    const txs  = data.results || data;

    if (!txs.length) { toast('Aucune transaction à exporter', 'info'); return; }

    // Générer CSV
    const headers = ['Date', 'Libellé', 'Catégorie', 'Direction', 'Montant (€)', 'Mode', 'Régime', 'Cagnotte', 'Note'];
    const rows = txs.map(tx => [
      tx.date,
      `"${(tx.label || '').replace(/"/g, '""')}"`,
      tx.category_display || tx.category,
      tx.direction === 'IN' ? 'Entrée' : 'Sortie',
      parseFloat(tx.amount).toFixed(2),
      tx.method_display || tx.method,
      tx.regime_fiscal || '',
      `"${(tx.campaign_name || '').replace(/"/g, '""')}"`,
      `"${(tx.note || '').replace(/"/g, '""')}"`,
    ]);

    const csvContent = [headers.join(';'), ...rows.map(r => r.join(';'))].join('\n');
    const BOM = '\uFEFF'; // BOM UTF-8 pour Excel
    const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
    const objUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const period = month || year || 'tout';
    a.href     = objUrl;
    a.download = `tresorerie_${period}.csv`;
    a.click();
    URL.revokeObjectURL(objUrl);
    toast(`Export CSV : ${txs.length} transaction(s) ✓`);
  } catch (e) {
    toast('Erreur export : ' + e.message, 'error');
  } finally {
    hideProgress();
  }
}

// ── Import bancaire CSV ────────────────────────────────────────────────────────

let allBankAccounts = [];

async function loadBankAccountsForImport() {
  const res = await apiFetch('/settings/bank-accounts/');
  if (!res || !res.ok) return;
  allBankAccounts = await res.json();
  const sel = document.getElementById('bank-import-account');
  if (!sel) return;
  sel.innerHTML = '<option value="">— Détecter automatiquement —</option>';
  allBankAccounts.forEach(a => {
    sel.innerHTML += `<option value="${a.id}">${esc(a.label)} (${a.account_number})</option>`;
  });
}

function openBankImportModal() {
  loadBankAccountsForImport();
  document.getElementById('bank-import-file').value = '';
  document.getElementById('bank-import-result').innerHTML = '';
  openModal('modal-bank-import');
}

async function runBankImport() {
  const fileInput = document.getElementById('bank-import-file');
  const accountId = document.getElementById('bank-import-account').value;
  const resultEl  = document.getElementById('bank-import-result');

  if (!fileInput.files.length) {
    resultEl.innerHTML = '<div class="alert alert-error">Veuillez sélectionner un fichier CSV.</div>';
    return;
  }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  if (accountId) formData.append('bank_account', accountId);

  showProgress();
  resultEl.innerHTML = '<div style="color:var(--muted);font-size:.85rem;">⏳ Import en cours...</div>';

  try {
    const res = await fetch(`${API}/treasury/import/bank/`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}` },
      body: formData,
    });

    const data = await res.json();

    if (!res.ok) {
      resultEl.innerHTML = `<div class="alert alert-error">${esc(data.detail || JSON.stringify(data))}</div>`;
      return;
    }

    const pendingLink = data.pending_review > 0
      ? `<br><a href="#" onclick="closeModal('modal-bank-import');loadImportPending();showSection('treasury');switchTreasuryTab('pending')" style="color:var(--accent);">→ Voir les ${data.pending_review} transaction(s) à valider</a>`
      : '';

    resultEl.innerHTML = `
      <div class="alert alert-success" style="line-height:1.8;">
        ✅ <strong>${data.imported}</strong> transaction(s) importée(s)<br>
        ⏭ <strong>${data.skipped_duplicates}</strong> doublon(s) ignoré(s)<br>
        ⚠️ <strong>${data.pending_review}</strong> en attente de catégorisation
        ${pendingLink}
      </div>`;

    loadTreasury();
  } catch (e) {
    resultEl.innerHTML = `<div class="alert alert-error">Erreur : ${esc(e.message)}</div>`;
  } finally {
    hideProgress();
  }
}

// ── Tableau de révision des transactions importées ─────────────────────────────

async function loadImportPending() {
  const tbody = document.getElementById('import-pending-table');
  if (!tbody) return;
  tbody.innerHTML = skeletonRows(3, 6);

  const res = await apiFetch('/treasury/import/pending/');
  if (!res || !res.ok) { tbody.innerHTML = '<tr><td colspan="6">Erreur chargement</td></tr>'; return; }
  const txs = await res.json();

  const badge = document.getElementById('pending-badge');
  if (badge) badge.textContent = txs.length > 0 ? txs.length : '';

  if (!txs.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--muted);">✅ Aucune transaction en attente — tout est validé.</td></tr>`;
    return;
  }

  tbody.innerHTML = txs.map(tx => {
    const isIn = tx.direction === 'IN';
    return `
    <tr>
      <td>${tx.date}</td>
      <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(tx.label)}">${esc(tx.label)}</td>
      <td style="font-weight:700;" class="${isIn ? 'text-green' : 'text-red'}">${isIn ? '▲' : '▼'} ${parseFloat(tx.amount).toFixed(2)} €</td>
      <td>
        <select id="pending-cat-${tx.id}" style="width:auto;margin:0;padding:4px 8px;font-size:.83rem;">
          <option value="">— Catégorie —</option>
          <option value="don">Don / Sadaqa</option>
          <option value="loyer">Loyer</option>
          <option value="salaire">Salaire / Honoraires</option>
          <option value="facture">Facture / Charges</option>
          <option value="ecole">École coranique</option>
          <option value="cotisation">Cotisation adhérent</option>
          <option value="projet">Projet / Travaux</option>
          <option value="subvention">Subvention</option>
          <option value="autre">Autre</option>
        </select>
      </td>
      <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(tx.note)||''}">${esc(tx.note)||'<span class="text-muted">—</span>'}</td>
      <td>
        <button class="btn btn-sm btn-primary" onclick="validatePendingTx(${tx.id})">✔ Valider</button>
        <button class="btn btn-sm" onclick="editTreasuryTransaction(${tx.id})">✏️</button>
      </td>
    </tr>`;
  }).join('');
}

async function validatePendingTx(id) {
  const catSel = document.getElementById(`pending-cat-${id}`);
  const category = catSel ? catSel.value : '';
  if (!category) {
    toast('Veuillez choisir une catégorie avant de valider.', 'error');
    return;
  }

  const res = await apiFetch(`/treasury/import/pending/${id}/`, 'PATCH', { category });
  if (!res || !res.ok) {
    toast('Erreur lors de la validation.', 'error');
    return;
  }
  toast('Transaction validée ✓');
  loadImportPending();
  loadTreasury();
}

function switchTreasuryTab(tab) {
  const tabTreasury    = document.getElementById('treasury-main-tab');
  const tabPending     = document.getElementById('treasury-pending-tab');
  const tabCash        = document.getElementById('treasury-cash-tab');
  const tabDashboard   = document.getElementById('treasury-dashboard-tab');
  const panelMain      = document.getElementById('treasury-main-panel');
  const panelPending   = document.getElementById('treasury-pending-panel');
  const panelCash      = document.getElementById('treasury-cash-panel');
  const panelDashboard = document.getElementById('treasury-dashboard-panel');
  if (!tabTreasury || !tabPending) return;

  // reset all tabs
  [tabTreasury, tabPending, tabCash, tabDashboard].forEach(t => t && t.classList.remove('btn-primary'));
  [panelMain, panelPending, panelCash, panelDashboard].forEach(p => p && p.classList.add('hidden'));

  if (tab === 'pending') {
    tabPending.classList.add('btn-primary');
    panelPending.classList.remove('hidden');
    loadImportPending();
  } else if (tab === 'cash') {
    tabCash && tabCash.classList.add('btn-primary');
    panelCash && panelCash.classList.remove('hidden');
    loadCashCounts();
  } else if (tab === 'dashboard') {
    tabDashboard && tabDashboard.classList.add('btn-primary');
    panelDashboard && panelDashboard.classList.remove('hidden');
    loadTreasuryDashboard();
  } else {
    tabTreasury.classList.add('btn-primary');
    panelMain.classList.remove('hidden');
  }
}

// ── Stock Caisse ───────────────────────────────────────────────────────────────

const DENOMINATIONS = [
  { value: "500.00", label: "Billet 500 €" },
  { value: "200.00", label: "Billet 200 €" },
  { value: "100.00", label: "Billet 100 €" },
  { value: "50.00",  label: "Billet 50 €" },
  { value: "20.00",  label: "Billet 20 €" },
  { value: "10.00",  label: "Billet 10 €" },
  { value: "5.00",   label: "Billet 5 €" },
  { value: "2.00",   label: "Pièce 2 €" },
  { value: "1.00",   label: "Pièce 1 €" },
  { value: "0.50",   label: "Pièce 50 cts" },
  { value: "0.20",   label: "Pièce 20 cts" },
  { value: "0.10",   label: "Pièce 10 cts" },
  { value: "0.05",   label: "Pièce 5 cts" },
];

async function loadCashCounts() {
  const tbody = document.getElementById('cash-counts-table');
  const kpi   = document.getElementById('cash-latest-total');
  if (!tbody) return;

  const res = await apiFetch('/treasury/cash-counts/');
  if (!res || !res.ok) { tbody.innerHTML = '<tr><td colspan="4">Erreur de chargement</td></tr>'; return; }
  const data = await res.json();

  if (data.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#888">Aucun pointage enregistré</td></tr>';
    if (kpi) kpi.textContent = '—';
    return;
  }

  if (kpi) kpi.textContent = formatEur(data[0].total);

  tbody.innerHTML = data.map(c => `
    <tr>
      <td>${c.date}</td>
      <td><strong>${formatEur(c.total)}</strong></td>
      <td style="color:#888;font-size:.85em">${c.note || '—'}</td>
      <td style="display:flex;gap:4px;flex-wrap:wrap;">
        <button class="btn btn-sm btn-primary" onclick="openCashCountModal(${c.id})">✏️ Modifier</button>
        <button class="btn btn-sm btn-danger" onclick="deleteCashCount(${c.id})">🗑</button>
      </td>
    </tr>
  `).join('');
}

// Ouvre le modal en mode création (id=null) ou édition (id=nombre)
async function openCashCountModal(editId = null) {
  // Stocker l'id en cours d'édition sur le bouton Save
  const saveBtn = document.getElementById('cash-count-save-btn');
  if (saveBtn) saveBtn.dataset.editId = editId || '';

  const titleEl = document.getElementById('cash-count-modal-title');

  const grid = document.getElementById('cash-denominations-grid');
  if (grid) {
    grid.innerHTML = DENOMINATIONS.map(d => `
      <div class="cash-denom-row">
        <label>${d.label}</label>
        <input type="number" min="0" value="0" id="denom-${d.value.replace('.', '_')}"
               class="input denom-input" data-denom="${d.value}"
               oninput="updateCashTotal()" style="width:80px;text-align:center">
        <span class="denom-sub" id="sub-${d.value.replace('.', '_')}">= 0,00 €</span>
      </div>
    `).join('');
  }
  document.getElementById('cash-count-total-preview').textContent = '0,00 €';
  document.getElementById('cash-count-note').value = '';
  if (document.getElementById('cash-count-error')) document.getElementById('cash-count-error').textContent = '';

  if (editId) {
    // Mode édition : charger le pointage existant et pré-remplir
    if (titleEl) titleEl.textContent = '✏️ Modifier le pointage';
    const res = await apiFetch(`/treasury/cash-counts/${editId}/`);
    if (!res || !res.ok) { toast('Erreur de chargement', 'error'); return; }
    const data = await res.json();

    document.getElementById('cash-count-date').value = data.date;
    document.getElementById('cash-count-note').value = data.note || '';

    // Pré-remplir les quantités
    data.lines.forEach(l => {
      const key = String(parseFloat(l.denomination).toFixed(2)).replace('.', '_');
      const input = document.getElementById(`denom-${key}`);
      if (input) {
        input.value = l.quantity;
      }
    });
    updateCashTotal();
  } else {
    // Mode création
    if (titleEl) titleEl.textContent = '💵 Nouveau pointage de caisse';
    document.getElementById('cash-count-date').value = new Date().toISOString().slice(0, 10);
  }

  openModal('modal-cash-count');
}

function updateCashTotal() {
  let total = 0;
  DENOMINATIONS.forEach(d => {
    const id    = `denom-${d.value.replace('.', '_')}`;
    const subId = `sub-${d.value.replace('.', '_')}`;
    const qty   = parseInt(document.getElementById(id)?.value || 0);
    const sub   = qty * parseFloat(d.value);
    total += sub;
    const subEl = document.getElementById(subId);
    if (subEl) subEl.textContent = `= ${formatEur(sub)}`;
  });
  const preview = document.getElementById('cash-count-total-preview');
  if (preview) preview.textContent = formatEur(total);
}

async function saveCashCount() {
  const date  = document.getElementById('cash-count-date')?.value;
  const note  = document.getElementById('cash-count-note')?.value || '';
  const errEl = document.getElementById('cash-count-error');
  const saveBtn = document.getElementById('cash-count-save-btn');
  const editId = saveBtn?.dataset.editId ? parseInt(saveBtn.dataset.editId) : null;

  if (!date) { if (errEl) errEl.textContent = 'La date est obligatoire.'; return; }
  if (errEl) errEl.textContent = '';

  const lines = [];
  DENOMINATIONS.forEach(d => {
    const qty = parseInt(document.getElementById(`denom-${d.value.replace('.', '_')}`)?.value || 0);
    if (qty > 0) lines.push({ denomination: d.value, quantity: qty });
  });

  if (lines.length === 0) {
    if (errEl) errEl.textContent = 'Veuillez saisir au moins une coupure.';
    return;
  }

  let res;
  if (editId) {
    // PATCH — modifier le pointage existant
    res = await apiFetch(`/treasury/cash-counts/${editId}/`, 'PATCH', { date, note, lines });
  } else {
    // POST — nouveau pointage
    res = await apiFetch('/treasury/cash-counts/', 'POST', { date, note, lines });
  }

  if (!res || !res.ok) {
    const err = await res?.json().catch(() => ({}));
    if (errEl) errEl.textContent = JSON.stringify(err);
    return;
  }
  closeModal('modal-cash-count');
  toast(editId ? 'Pointage mis à jour ✓' : 'Pointage enregistré ✓');
  loadCashCounts();
}

async function deleteCashCount(id) {
  if (!confirm('Supprimer ce pointage de caisse ?')) return;
  const res = await apiFetch(`/treasury/cash-counts/${id}/`, 'DELETE');
  if (res && res.ok) {
    toast('Pointage supprimé');
    loadCashCounts();
  } else {
    toast('Erreur lors de la suppression', 'error');
  }
}

function formatEur(v) {
  return Number(v).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
}

function formatDenom(v) {
  const f = parseFloat(v);
  if (f >= 5) return `Billet ${f.toFixed(0)} €`;
  if (f >= 1) return `Pièce ${f.toFixed(0)} €`;
  return `Pièce ${Math.round(f * 100)} cts`;
}

// ── Tableau de bord trésorerie ─────────────────────────────────────────────────

const CAT_LABELS = {
  don: 'Don / Sadaqa', loyer: 'Loyer', salaire: 'Salaire',
  facture: 'Facture', ecole: 'École', cotisation: 'Cotisation',
  projet: 'Projet', subvention: 'Subvention', autre: 'Autre',
};

async function loadTreasuryDashboard() {
  const res = await apiFetch('/treasury/transactions/dashboard/');
  if (!res || !res.ok) { toast('Erreur chargement tableau de bord', 'error'); return; }
  const d = await res.json();

  // KPI globaux
  const fmt = v => parseFloat(v).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
  document.getElementById('dash-total-in').textContent  = fmt(d.total_in);
  document.getElementById('dash-total-out').textContent = fmt(d.total_out);
  const balEl = document.getElementById('dash-balance');
  balEl.textContent = fmt(d.balance);
  balEl.style.color = d.balance >= 0 ? '#16a34a' : '#dc2626';
  const cashEl = document.getElementById('dash-cash-stock');
  cashEl.textContent = d.cash_stock ? fmt(d.cash_stock.total) : '—';
  if (d.cash_stock) cashEl.title = `Pointage du ${d.cash_stock.date}`;

  // Solde par compte
  const accEl = document.getElementById('dash-by-account');
  if (!d.by_account.length) {
    accEl.innerHTML = '<p style="color:var(--muted);font-size:.85rem;">Aucun compte configuré</p>';
  } else {
    accEl.innerHTML = d.by_account.map(a => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);">
        <div>
          <strong style="font-size:.9rem;">${esc(a.label)}</strong>
          ${a.regime ? `<span class="badge badge-${a.regime === '1901' ? '1901' : '1905'}" style="margin-left:6px;">${a.regime}</span>` : ''}
          ${a.bank_name ? `<span style="font-size:.75rem;color:var(--muted);margin-left:6px;">${esc(a.bank_name)}</span>` : ''}
        </div>
        <span style="font-weight:700;color:${a.balance >= 0 ? '#16a34a' : '#dc2626'};">${fmt(a.balance)}</span>
      </div>`).join('');
  }

  // Top catégories
  const renderCats = (list, el) => {
    if (!list.length) { el.innerHTML = '<p style="color:var(--muted);font-size:.82rem;">—</p>'; return; }
    const max = list[0].total;
    el.innerHTML = list.map(c => {
      const pct = max > 0 ? Math.round((c.total / max) * 100) : 0;
      return `<div style="margin-bottom:6px;">
        <div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:2px;">
          <span>${CAT_LABELS[c.category] || c.category}</span>
          <strong>${fmt(c.total)}</strong>
        </div>
        <div style="background:var(--border);border-radius:4px;height:6px;">
          <div style="background:var(--accent);height:6px;border-radius:4px;width:${pct}%;"></div>
        </div>
      </div>`;
    }).join('');
  };
  renderCats(d.top_in, document.getElementById('dash-top-in'));
  renderCats(d.top_out, document.getElementById('dash-top-out'));

  // Graphique mensuel (barres SVG simples)
  const chartEl = document.getElementById('dash-monthly-chart');
  if (!d.monthly.length) { chartEl.innerHTML = '<p style="color:var(--muted);font-size:.85rem;">Pas encore de données</p>'; return; }
  const maxVal = Math.max(...d.monthly.map(m => Math.max(m.in, m.out)), 1);
  const barH = 80;
  const barW = 28;
  const gap  = 8;
  const totalW = d.monthly.length * (barW * 2 + gap + 10);
  let svg = `<svg viewBox="0 0 ${totalW} ${barH + 30}" style="width:100%;min-width:${totalW}px;height:${barH + 30}px;">`;
  d.monthly.forEach((m, i) => {
    const x = i * (barW * 2 + gap + 10);
    const hIn  = Math.max(2, Math.round((m.in  / maxVal) * barH));
    const hOut = Math.max(2, Math.round((m.out / maxVal) * barH));
    svg += `<rect x="${x}" y="${barH - hIn}" width="${barW}" height="${hIn}" fill="#16a34a" rx="3" opacity=".85">
      <title>Entrées ${m.month} : ${fmt(m.in)}</title></rect>`;
    svg += `<rect x="${x + barW + 2}" y="${barH - hOut}" width="${barW}" height="${hOut}" fill="#dc2626" rx="3" opacity=".85">
      <title>Sorties ${m.month} : ${fmt(m.out)}</title></rect>`;
    const label = m.month.slice(2).replace('-', '/');
    svg += `<text x="${x + barW}" y="${barH + 14}" text-anchor="middle" font-size="9" fill="var(--muted)">${label}</text>`;
  });
  svg += '</svg>';
  svg += '<div style="display:flex;gap:16px;margin-top:6px;font-size:.78rem;"><span style="color:#16a34a">■ Entrées</span><span style="color:#dc2626">■ Sorties</span></div>';
  chartEl.innerHTML = svg;
}

// ─── S3-1 ─ Modal Récap mensuel ──────────────────────────────────
function openMonthlyRecapModal() {
  // Pré-remplir avec le mois courant
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const inp = document.getElementById('monthly-recap-month');
  if (inp && !inp.value) inp.value = `${yyyy}-${mm}`;
  openModal('modal-monthly-recap');
}

async function loadMonthlyRecap() {
  const inp = document.getElementById('monthly-recap-month');
  const month = inp ? inp.value : '';
  if (!month) { showNotif('Veuillez sélectionner un mois.', 'error'); return; }

  const contentEl = document.getElementById('monthly-recap-content');
  contentEl.innerHTML = '<p style="text-align:center;color:var(--muted)">Chargement…</p>';

  const title = document.getElementById('monthly-recap-title');
  if (title) title.textContent = `📅 Récapitulatif mensuel — ${month}`;

  try {
    const res = await apiFetch(`/treasury/transactions/summary/?month=${month}`);
    if (!res.ok) throw new Error('Erreur serveur');
    const s = await res.json();

    const esc = v => String(v ?? '').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    const fmt = v => parseFloat(v || 0).toFixed(2) + ' €';
    const fmtColor = v => {
      const n = parseFloat(v || 0);
      const color = n >= 0 ? '#16a34a' : '#dc2626';
      return `<span style="color:${color};font-weight:600;">${fmt(n)}</span>`;
    };

    // Tableau par catégorie
    const cats = s.categories || {};
    const catLabels = {
      'don': 'Dons', 'cotisation': 'Cotisations', 'loyer': 'Loyer',
      'travaux': 'Travaux', 'charge': 'Charges', 'autre': 'Autre'
    };
    const catRows = Object.entries(cats).map(([key, val]) => {
      const label = catLabels[key] || key;
      const inV = val.in || 0;
      const outV = val.out || 0;
      const solde = inV - outV;
      if (inV === 0 && outV === 0) return '';
      return `<tr>
        <td>${esc(label)}</td>
        <td style="text-align:right;color:#16a34a;">${fmt(inV)}</td>
        <td style="text-align:right;color:#dc2626;">${fmt(outV)}</td>
        <td style="text-align:right;">${fmtColor(solde)}</td>
      </tr>`;
    }).filter(Boolean).join('');

    // Tableau par régime
    const regimes = s.by_regime || {};
    const regimeLabels = {'1901':'Loi 1901 (Assoc.)','1905':'Loi 1905 (Culte)','non_precise':'Non précisé'};
    const regimeRows = Object.entries(regimes).map(([key, val]) => {
      const label = regimeLabels[key] || key;
      const inV = val.in || 0;
      const outV = val.out || 0;
      const solde = inV - outV;
      if (inV === 0 && outV === 0) return '';
      return `<tr>
        <td>${esc(label)}</td>
        <td style="text-align:right;color:#16a34a;">${fmt(inV)}</td>
        <td style="text-align:right;color:#dc2626;">${fmt(outV)}</td>
        <td style="text-align:right;">${fmtColor(solde)}</td>
      </tr>`;
    }).filter(Boolean).join('');

    const tableStyle = 'width:100%;border-collapse:collapse;font-size:14px;margin-bottom:16px;';
    const thStyle = 'background:var(--surface);padding:8px 12px;text-align:left;border-bottom:2px solid var(--border);font-weight:700;font-size:13px;';
    const tdStyle = 'padding:7px 12px;border-bottom:1px solid var(--border);';

    contentEl.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px;">
        <div class="stat-card" style="padding:12px 16px;">
          <div style="font-size:13px;color:var(--muted);">Total entrées</div>
          <div style="font-size:20px;font-weight:700;color:#16a34a;">${fmt(s.total_in)}</div>
        </div>
        <div class="stat-card" style="padding:12px 16px;">
          <div style="font-size:13px;color:var(--muted);">Total sorties</div>
          <div style="font-size:20px;font-weight:700;color:#dc2626;">${fmt(s.total_out)}</div>
        </div>
        <div class="stat-card" style="padding:12px 16px;">
          <div style="font-size:13px;color:var(--muted);">Solde net</div>
          <div style="font-size:20px;font-weight:700;">${fmtColor(s.balance)}</div>
        </div>
      </div>

      <h4 style="margin:0 0 8px;font-size:15px;">Par catégorie</h4>
      <table style="${tableStyle}">
        <thead>
          <tr>
            <th style="${thStyle}">Catégorie</th>
            <th style="${thStyle}text-align:right;">Entrées</th>
            <th style="${thStyle}text-align:right;">Sorties</th>
            <th style="${thStyle}text-align:right;">Solde</th>
          </tr>
        </thead>
        <tbody id="recap-cat-tbody">
          ${catRows || '<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:16px;">Aucune donnée</td></tr>'}
        </tbody>
      </table>

      <h4 style="margin:0 0 8px;font-size:15px;">Par régime fiscal</h4>
      <table style="${tableStyle}">
        <thead>
          <tr>
            <th style="${thStyle}">Régime</th>
            <th style="${thStyle}text-align:right;">Entrées</th>
            <th style="${thStyle}text-align:right;">Sorties</th>
            <th style="${thStyle}text-align:right;">Solde</th>
          </tr>
        </thead>
        <tbody id="recap-regime-tbody">
          ${regimeRows || '<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:16px;">Aucune donnée</td></tr>'}
        </tbody>
      </table>`;
  } catch (e) {
    contentEl.innerHTML = `<p style="color:#dc2626;text-align:center;">Erreur : ${e.message}</p>`;
  }
}

function printMonthlyRecap() {
  const content = document.getElementById('monthly-recap-content');
  const title = document.getElementById('monthly-recap-title');
  if (!content) return;
  const w = window.open('', '_blank', 'width=800,height=600');
  w.document.write(`<!DOCTYPE html><html><head>
    <meta charset="utf-8"><title>${title ? title.textContent : 'Récap mensuel'}</title>
    <style>
      body{font-family:Arial,sans-serif;padding:24px;color:#1a1a2e;}
      h1{font-size:18px;margin-bottom:16px;}
      table{width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px;}
      th{background:#f1f5f9;padding:8px;text-align:left;border-bottom:2px solid #e2e8f0;}
      td{padding:6px 8px;border-bottom:1px solid #e2e8f0;}
      .kpi-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;}
      .kpi{border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;}
      .kpi .lbl{font-size:12px;color:#64748b;}
      .kpi .val{font-size:18px;font-weight:700;}
      @media print{body{padding:10px;}}
    </style>
  </head><body>
    <h1>${title ? title.textContent : 'Récapitulatif mensuel'}</h1>
    ${content.innerHTML}
  </body></html>`);
  w.document.close();
  w.focus();
  setTimeout(() => w.print(), 500);
}
