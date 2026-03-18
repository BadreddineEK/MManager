/* ═══════════════════════════════════════════════════════════
   bulk.js — Saisie en masse type tableur
   -------------------------------------------------------
   openBulkModal(type)  → ouvre le tableur pour :
     'treasury'  | 'members' | 'families' | 'children'
   Chaque ligne = une entité. Sauvegarde séquentielle avec
   rapport de résultat (OK / erreurs par ligne).
═══════════════════════════════════════════════════════════ */

// ─── Config des colonnes par type ────────────────────────────────────────────

const BULK_CONFIG = {
  treasury: {
    title:   '📋 Saisie multiple — Transactions',
    columns: [
      { key: 'date',      label: 'Date *',      type: 'date',   required: true,  width: '130px' },
      { key: 'label',     label: 'Libellé *',   type: 'text',   required: true,  width: '220px', placeholder: 'Ex: Don vendredi' },
      { key: 'direction', label: 'Type *',       type: 'select', required: true,  width: '110px',
        options: [{ v: 'IN', l: '▲ Entrée' }, { v: 'OUT', l: '▼ Sortie' }] },
      { key: 'amount',    label: 'Montant € *',  type: 'number', required: true,  width: '110px', placeholder: '0.00' },
      { key: 'category',  label: 'Catégorie',    type: 'select', required: false, width: '150px',
        options: [
          { v: 'don',        l: 'Don / Sadaqa' },
          { v: 'loyer',      l: 'Loyer' },
          { v: 'salaire',    l: 'Salaire' },
          { v: 'facture',    l: 'Facture / Charges' },
          { v: 'ecole',      l: 'École' },
          { v: 'cotisation', l: 'Cotisation' },
          { v: 'projet',     l: 'Projet / Travaux' },
          { v: 'subvention', l: 'Subvention' },
          { v: 'autre',      l: 'Autre' },
        ]},
      { key: 'method',    label: 'Mode paie.',   type: 'select', required: false, width: '120px',
        options: [
          { v: 'cash',     l: 'Espèces' },
          { v: 'cheque',   l: 'Chèque' },
          { v: 'virement', l: 'Virement' },
          { v: 'autre',    l: 'Autre' },
        ]},
      { key: 'note',      label: 'Note',         type: 'text',   required: false, width: '160px', placeholder: '(optionnel)' },
    ],
    defaults: { direction: 'IN', category: 'don', method: 'cash' },
    save: async (row) => {
      if (!row.label || !row.date || !row.amount)
        throw new Error('Libellé, date et montant requis');
      const res = await apiFetch('/treasury/transactions/', 'POST', {
        direction:     row.direction || 'IN',
        category:      row.category  || 'don',
        label:         row.label,
        date:          row.date,
        amount:        parseFloat(row.amount),
        method:        row.method    || 'cash',
        note:          row.note      || '',
        regime_fiscal: '',
        campaign:      null,
      });
      if (!res || !res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(Object.values(e).flat().join(' — ') || `HTTP ${res.status}`);
      }
    },
    onDone: () => loadTreasury(),
  },

  members: {
    title:   '📋 Saisie multiple — Adhérents',
    columns: [
      { key: 'full_name', label: 'Nom complet *', type: 'text',  required: true,  width: '200px', placeholder: 'Mohamed Dupont' },
      { key: 'phone',     label: 'Téléphone',      type: 'text',  required: false, width: '140px', placeholder: '06 12 34 56 78' },
      { key: 'email',     label: 'Email',           type: 'email', required: false, width: '180px', placeholder: 'email@exemple.com' },
      { key: 'address',   label: 'Adresse',         type: 'text',  required: false, width: '200px', placeholder: '(optionnel)' },
    ],
    defaults: {},
    save: async (row) => {
      if (!row.full_name) throw new Error('Le nom est requis');
      const res = await apiFetch('/membership/members/', 'POST', {
        full_name: row.full_name,
        phone:     row.phone   || '',
        email:     row.email   || '',
        address:   row.address || '',
      });
      if (!res || !res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(Object.values(e).flat().join(' — ') || `HTTP ${res.status}`);
      }
    },
    onDone: () => loadMembers(),
  },

  families: {
    title:   '📋 Saisie multiple — Familles',
    columns: [
      { key: 'primary_contact_name', label: 'Nom contact *', type: 'text',  required: true,  width: '200px', placeholder: 'Ahmed Benali' },
      { key: 'phone1',               label: 'Tél. principal *', type: 'text', required: true, width: '140px', placeholder: '06 12 34 56 78' },
      { key: 'phone2',               label: 'Tél. secondaire',  type: 'text', required: false, width: '140px', placeholder: '(optionnel)' },
      { key: 'email',                label: 'Email',             type: 'email', required: false, width: '180px', placeholder: '(optionnel)' },
      { key: 'address',              label: 'Adresse',           type: 'text', required: false, width: '200px', placeholder: '(optionnel)' },
    ],
    defaults: {},
    save: async (row) => {
      if (!row.primary_contact_name || !row.phone1)
        throw new Error('Nom et téléphone requis');
      const res = await apiFetch('/school/families/', 'POST', {
        primary_contact_name: row.primary_contact_name,
        phone1:   row.phone1,
        phone2:   row.phone2   || '',
        email:    row.email    || '',
        address:  row.address  || '',
      });
      if (!res || !res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(Object.values(e).flat().join(' — ') || `HTTP ${res.status}`);
      }
    },
    onDone: () => loadFamilies(),
  },

  children: {
    title:   '📋 Saisie multiple — Enfants',
    columns: [
      { key: 'first_name',  label: 'Prénom *',    type: 'text',   required: true,  width: '160px', placeholder: 'Youssef' },
      { key: 'family',      label: 'Famille *',   type: 'select', required: true,  width: '180px', options: [] /* rempli dynamiquement */ },
      { key: 'level',       label: 'Niveau *',    type: 'select', required: true,  width: '100px',
        options: ['NP','N1','N2','N3','N4','N5','N6'].map(v => ({ v, l: v })) },
      { key: 'birth_date',  label: 'Naissance',   type: 'date',   required: false, width: '130px' },
    ],
    defaults: { level: 'NP' },
    save: async (row) => {
      if (!row.first_name || !row.family || !row.level)
        throw new Error('Prénom, famille et niveau requis');
      const res = await apiFetch('/school/children/', 'POST', {
        first_name: row.first_name,
        family:     parseInt(row.family),
        level:      row.level,
        birth_date: row.birth_date || null,
      });
      if (!res || !res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(Object.values(e).flat().join(' — ') || `HTTP ${res.status}`);
      }
    },
    onDone: () => loadChildren(),
  },
};

// ─── État interne ─────────────────────────────────────────────────────────────
let _bulkType   = null;
let _bulkRowIdx = 0;

// ─── Ouverture du modal ───────────────────────────────────────────────────────
async function openBulkModal(type) {
  _bulkType   = type;
  _bulkRowIdx = 0;

  const cfg = BULK_CONFIG[type];
  if (!cfg) return;

  // Pour les enfants : peupler dynamiquement les familles
  if (type === 'children') {
    const res  = await apiFetch('/school/families/?page_size=500');
    const data = res && res.ok ? await res.json() : {};
    const fams = data.results || data || [];
    cfg.columns.find(c => c.key === 'family').options =
      fams.map(f => ({ v: String(f.id), l: f.primary_contact_name }));
  }

  // Titre
  document.getElementById('bulk-modal-title').textContent = cfg.title;

  // Construire l'entête du tableau
  const thead = document.getElementById('bulk-thead');
  thead.innerHTML =
    '<tr>' +
    cfg.columns.map(c =>
      `<th style="min-width:${c.width};white-space:nowrap;">${c.label}</th>`
    ).join('') +
    '<th style="width:36px;"></th>' +
    '</tr>';

  // Vider le tbody et ajouter 3 lignes vides
  document.getElementById('bulk-tbody').innerHTML = '';
  for (let i = 0; i < 3; i++) _bulkAddRow();

  // Masquer le rapport
  const report = document.getElementById('bulk-report');
  report.classList.add('hidden');
  report.innerHTML = '';

  // Bouton sauvegarder actif
  document.getElementById('bulk-save-btn').disabled = false;
  document.getElementById('bulk-save-btn').textContent = '💾 Enregistrer tout';

  openModal('modal-bulk');
}

// ─── Ajouter une ligne vide ───────────────────────────────────────────────────
function _bulkAddRow() {
  const cfg   = BULK_CONFIG[_bulkType];
  const tbody = document.getElementById('bulk-tbody');
  const idx   = _bulkRowIdx++;
  const tr    = document.createElement('tr');
  tr.id       = `bulk-row-${idx}`;
  tr.dataset.idx = idx;

  cfg.columns.forEach(col => {
    const td = document.createElement('td');

    if (col.type === 'select') {
      const sel = document.createElement('select');
      sel.className   = 'bulk-cell';
      sel.dataset.key = col.key;
      if (!col.required) {
        const opt = document.createElement('option');
        opt.value = ''; opt.textContent = '—';
        sel.appendChild(opt);
      }
      (col.options || []).forEach(o => {
        const opt = document.createElement('option');
        opt.value = o.v; opt.textContent = o.l;
        if (cfg.defaults && cfg.defaults[col.key] === o.v) opt.selected = true;
        sel.appendChild(opt);
      });
      td.appendChild(sel);
    } else {
      const inp = document.createElement('input');
      inp.type        = col.type === 'number' ? 'number' : (col.type === 'date' ? 'date' : (col.type === 'email' ? 'email' : 'text'));
      inp.className   = 'bulk-cell';
      inp.dataset.key = col.key;
      inp.placeholder = col.placeholder || '';
      if (col.type === 'number') { inp.min = '0'; inp.step = '0.01'; }
      if (cfg.defaults && cfg.defaults[col.key]) inp.value = cfg.defaults[col.key];
      // Pour les transactions : pré-remplir la date du jour
      if (col.type === 'date' && col.key === 'date')
        inp.value = new Date().toISOString().split('T')[0];
      // Tab sur dernière cellule de dernière ligne → ajoute une ligne
      if (col === cfg.columns[cfg.columns.length - 1]) {
        inp.addEventListener('keydown', e => {
          if (e.key === 'Tab' && !e.shiftKey) {
            const rows = document.getElementById('bulk-tbody').querySelectorAll('tr');
            if (tr === rows[rows.length - 1]) {
              e.preventDefault();
              _bulkAddRow();
              // focus première cellule de la nouvelle ligne
              const newRow = document.getElementById(`bulk-row-${_bulkRowIdx - 1}`);
              newRow?.querySelector('.bulk-cell')?.focus();
            }
          }
        });
      }
      td.appendChild(inp);
    }
    tr.appendChild(td);
  });

  // Bouton supprimer la ligne
  const tdDel = document.createElement('td');
  const btnDel = document.createElement('button');
  btnDel.className   = 'btn btn-danger btn-sm btn-icon bulk-del-btn';
  btnDel.textContent = '✕';
  btnDel.title       = 'Supprimer cette ligne';
  btnDel.onclick     = () => { tr.remove(); _bulkUpdateLineNumbers(); };
  tdDel.appendChild(btnDel);
  tr.appendChild(tdDel);

  tbody.appendChild(tr);
  _bulkUpdateLineNumbers();
}

function _bulkUpdateLineNumbers() {
  document.getElementById('bulk-row-count').textContent =
    `${document.getElementById('bulk-tbody').querySelectorAll('tr').length} ligne(s)`;
}

// ─── Lecture d'une ligne ──────────────────────────────────────────────────────
function _bulkReadRow(tr) {
  const row = {};
  tr.querySelectorAll('.bulk-cell').forEach(el => {
    row[el.dataset.key] = el.value.trim ? el.value.trim() : el.value;
  });
  return row;
}

function _bulkIsRowEmpty(row) {
  return Object.values(row).every(v => !v || v === '—');
}

// ─── Sauvegarde ───────────────────────────────────────────────────────────────
async function saveBulk() {
  const cfg    = BULK_CONFIG[_bulkType];
  const rows   = [...document.getElementById('bulk-tbody').querySelectorAll('tr')];
  const filled = rows.filter(tr => !_bulkIsRowEmpty(_bulkReadRow(tr)));

  if (!filled.length) {
    toast('Aucune ligne à enregistrer.', 'error');
    return;
  }

  const btn = document.getElementById('bulk-save-btn');
  btn.disabled    = true;
  btn.textContent = '⏳ Enregistrement…';

  const report  = document.getElementById('bulk-report');
  report.classList.remove('hidden');
  report.innerHTML = '';

  let ok = 0, errors = 0;

  for (let i = 0; i < filled.length; i++) {
    const tr  = filled[i];
    const row = _bulkReadRow(tr);
    const lineNum = i + 1;

    // Surbrillance de la ligne en cours
    tr.classList.remove('bulk-row-ok', 'bulk-row-error');
    tr.classList.add('bulk-row-saving');

    try {
      await cfg.save(row);
      tr.classList.remove('bulk-row-saving');
      tr.classList.add('bulk-row-ok');
      ok++;
      report.innerHTML += `<div class="bulk-report-line bulk-report-ok">✅ Ligne ${lineNum} enregistrée</div>`;
    } catch (err) {
      tr.classList.remove('bulk-row-saving');
      tr.classList.add('bulk-row-error');
      errors++;
      report.innerHTML += `<div class="bulk-report-line bulk-report-err">❌ Ligne ${lineNum} — ${err.message}</div>`;
    }
  }

  btn.disabled = false;
  const total = ok + errors;
  if (errors === 0) {
    btn.textContent = `✅ Tout enregistré (${ok}/${total})`;
    toast(`${ok} enregistrement${ok > 1 ? 's' : ''} ajouté${ok > 1 ? 's' : ''} ✓`);
    cfg.onDone();
    // Fermer automatiquement après 1,2s si tout OK
    setTimeout(() => closeModal('modal-bulk'), 1200);
  } else {
    btn.textContent = `💾 Réessayer les erreurs`;
    toast(`${ok} OK · ${errors} erreur${errors > 1 ? 's' : ''}`, 'error');
    cfg.onDone(); // rafraîchit quand même la liste pour les lignes OK
  }
}
