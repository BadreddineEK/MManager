/* ═══════════════════════════════════════════════════════════
   dashboard.js — KPI enrichis, alertes contextuelles, graphiques
═══════════════════════════════════════════════════════════ */

// ── Instances Chart.js ────────────────────────────────────────────────────────
const _charts = {};
function _destroyChart(id) {
  if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
}

// ── Palette ───────────────────────────────────────────────────────────────────
const CHART_COLORS = {
  purple:      'rgba(109, 40, 217, 0.85)',
  purpleLight: 'rgba(109, 40, 217, 0.12)',
  green:       'rgba(22, 163, 74, 0.85)',
  greenLight:  'rgba(22, 163, 74, 0.12)',
  red:         'rgba(220, 38, 38, 0.85)',
  redLight:    'rgba(220, 38, 38, 0.12)',
  blue:        'rgba(37, 99, 235, 0.85)',
  orange:      'rgba(234, 88, 12, 0.85)',
  teal:        'rgba(8, 145, 178, 0.85)',
  pink:        'rgba(219, 39, 119, 0.85)',
  amber:       'rgba(217, 119, 6, 0.85)',
};
const CAT_PALETTE = [
  CHART_COLORS.purple, CHART_COLORS.green, CHART_COLORS.blue,
  CHART_COLORS.orange, CHART_COLORS.teal, CHART_COLORS.pink,
  CHART_COLORS.amber,  CHART_COLORS.red,
];

Chart.defaults.font.family = "'Inter', 'Segoe UI', system-ui, sans-serif";
Chart.defaults.font.size   = 12;
Chart.defaults.color       = '#6b7280';

// ── Helpers ───────────────────────────────────────────────────────────────────
function _last6Months() {
  const months = [];
  const d = new Date();
  for (let i = 5; i >= 0; i--) {
    const m = new Date(d.getFullYear(), d.getMonth() - i, 1);
    months.push(`${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, '0')}`);
  }
  return months;
}
function _monthLabel(ym) {
  const [y, m] = ym.split('-');
  return new Date(y, m - 1).toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' });
}
function _fmtEur(n) {
  const v = parseFloat(n || 0);
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}k €`;
  return `${v.toFixed(0)} €`;
}
function _pct(num, total) {
  if (!total) return 0;
  return Math.round((num / total) * 100);
}

// ── Dashboard principal ───────────────────────────────────────────────────────
async function loadDashboard() {
  const months     = _last6Months();
  const currentYm  = new Date().toISOString().slice(0, 7);
  const now        = new Date();
  const monthLabel = now.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

  // Toutes les requêtes en parallèle
  const [fRes, cRes, aRes, mRes, tTotalRes, tMonthRes, unpaidRes, catRes] = await Promise.all([
    apiFetch('/school/families/'),
    apiFetch('/school/children/'),
    apiFetch('/school/families/arrears/'),
    apiFetch('/membership/members/'),
    apiFetch('/treasury/transactions/summary/?total=1'),
    apiFetch(`/treasury/transactions/summary/?month=${currentYm}`),
    apiFetch('/membership/members/unpaid/'),
    apiFetch(`/treasury/transactions/summary/?month=${currentYm}`),
  ]);

  const fData   = fRes?.ok      ? await fRes.json()      : null;
  const cData   = cRes?.ok      ? await cRes.json()      : null;
  const aData   = aRes?.ok      ? await aRes.json()      : null;
  const mData   = mRes?.ok      ? await mRes.json()      : null;
  const tTotal  = tTotalRes?.ok ? await tTotalRes.json() : null;
  const tMonth  = tMonthRes?.ok ? await tMonthRes.json() : null;
  const unpaid  = unpaidRes?.ok ? await unpaidRes.json() : null;

  const totalFamilies  = fData?.count  ?? (fData?.results ?? fData ?? []).length;
  const totalChildren  = cData?.count  ?? (cData?.results ?? cData ?? []).length;
  const arrearsCount   = aData?.count  ?? (aData?.families?.length ?? 0);
  const totalMembers   = mData?.count  ?? (mData?.results ?? mData ?? []).length;
  const unpaidCount    = unpaid?.count ?? 0;
  const paidCount      = Math.max(0, totalMembers - unpaidCount);

  // ── KPI Trésorerie ────────────────────────────────────────────────────────
  if (tTotal) {
    const bal = parseFloat(tTotal.balance);
    const balEl = document.getElementById('stat-balance');
    balEl.textContent = `${bal >= 0 ? '+' : ''}${_fmtEur(bal)}`;
    balEl.style.color = bal >= 0 ? '#16a34a' : '#dc2626';

    const trend = document.getElementById('kpi-balance-trend');
    if (trend) {
      trend.textContent = bal >= 0 ? '✅ Positif' : '⚠️ Déficit';
      trend.className   = `dash-kpi-badge ${bal >= 0 ? 'badge-ok' : 'badge-danger'}`;
    }
  }
  if (tMonth) {
    const mIn  = parseFloat(tMonth.total_in  || 0);
    const mOut = parseFloat(tMonth.total_out || 0);
    const subEl = document.getElementById('stat-balance-month');
    if (subEl) subEl.textContent = `${monthLabel} : +${_fmtEur(mIn)} / -${_fmtEur(mOut)}`;

    const inEl  = document.getElementById('stat-month-in');
    const outEl = document.getElementById('stat-month-out');
    if (inEl)  inEl.textContent  = `+${_fmtEur(mIn)}`;
    if (outEl) outEl.textContent = `-${_fmtEur(mOut)}`;
  }

  // ── KPI École ─────────────────────────────────────────────────────────────
  document.getElementById('stat-families').textContent = totalFamilies;
  document.getElementById('stat-children').textContent = totalChildren;
  document.getElementById('stat-arrears').textContent  = arrearsCount;
  const arrearsBadge = document.getElementById('kpi-arrears-badge');
  if (arrearsBadge && totalFamilies > 0) {
    const pct = _pct(arrearsCount, totalFamilies);
    arrearsBadge.textContent = pct === 0 ? '✅ Tous à jour' : `⚠️ ${pct}% impayés`;
    arrearsBadge.className   = `dash-kpi-badge ${pct === 0 ? 'badge-ok' : pct < 30 ? 'badge-warning' : 'badge-danger'}`;
  }

  // ── KPI Adhérents ─────────────────────────────────────────────────────────
  document.getElementById('stat-members').textContent         = totalMembers;
  document.getElementById('stat-members-paid').textContent    = paidCount;
  document.getElementById('stat-members-unpaid').textContent  = unpaidCount;
  const memberBadge = document.getElementById('kpi-members-badge');
  if (memberBadge && totalMembers > 0) {
    const pct = _pct(paidCount, totalMembers);
    memberBadge.textContent = `${pct}% cotisants`;
    memberBadge.className   = `dash-kpi-badge ${pct >= 80 ? 'badge-ok' : pct >= 50 ? 'badge-warning' : 'badge-danger'}`;
  }

  // ── Alertes contextuelles ─────────────────────────────────────────────────
  _renderAlerts({ arrearsCount, totalFamilies, unpaidCount, totalMembers, tMonth, monthLabel });

  await loadSchoolYears();

  // ── Graphique 1 : Trésorerie flux 6 mois (ligne) ─────────────────────────
  const trsIn = [], trsOut = [], trsBalance = [];
  for (const month of months) {
    const res = await apiFetch(`/treasury/transactions/summary/?month=${month}`);
    if (res?.ok) {
      const d = await res.json();
      const _in  = parseFloat(d.total_in  || 0);
      const _out = parseFloat(d.total_out || 0);
      trsIn.push(_in);
      trsOut.push(_out);
      trsBalance.push(_in - _out);
    } else {
      trsIn.push(0); trsOut.push(0); trsBalance.push(0);
    }
  }

  const periodEl = document.getElementById('dash-trs-period');
  if (periodEl) periodEl.textContent = `${_monthLabel(months[0])} → ${_monthLabel(months[5])}`;

  _destroyChart('treasury');
  _charts['treasury'] = new Chart(document.getElementById('chart-treasury'), {
    type: 'bar',
    data: {
      labels: months.map(_monthLabel),
      datasets: [
        {
          label: 'Entrées', data: trsIn,
          backgroundColor: 'rgba(22,163,74,0.7)', borderColor: 'rgba(22,163,74,1)',
          borderRadius: 5, order: 2,
        },
        {
          label: 'Sorties', data: trsOut,
          backgroundColor: 'rgba(220,38,38,0.7)', borderColor: 'rgba(220,38,38,1)',
          borderRadius: 5, order: 2,
        },
        {
          label: 'Solde', data: trsBalance,
          type: 'line', borderColor: 'rgba(109,40,217,1)',
          backgroundColor: 'rgba(109,40,217,0.08)',
          borderWidth: 2.5, pointRadius: 4, pointBackgroundColor: '#6d28d9',
          fill: true, tension: 0.35, order: 1,
        },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', labels: { boxWidth: 12, padding: 16 } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label} : ${ctx.parsed.y >= 0 ? '+' : ''}${_fmtEur(ctx.parsed.y)}`,
          },
        },
      },
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => _fmtEur(v) }, grid: { color: '#f0eef8' } },
        x: { grid: { display: false } },
      },
    },
  });

  // ── Graphique 2 : Répartition catégories recettes ─────────────────────────
  // Chercher les transactions IN du mois courant par catégorie
  const catRes2 = await apiFetch(`/treasury/transactions/?direction=IN&month=${currentYm}&page_size=1000`);
  const catTxs  = catRes2?.ok ? ((await catRes2.json()).results || []) : [];
  const catMap  = {};
  const CAT_LABELS = {
    don: 'Dons', ecole: 'École', cotisation: 'Cotisations',
    loyer: 'Loyer', salaire: 'Salaires', facture: 'Factures',
    projet: 'Projets', subvention: 'Subventions', autre: 'Autre',
  };
  catTxs.forEach(tx => {
    const cat = CAT_LABELS[tx.category] || tx.category_display || tx.category;
    catMap[cat] = (catMap[cat] || 0) + parseFloat(tx.amount || 0);
  });
  const catEntries = Object.entries(catMap).sort((a, b) => b[1] - a[1]);

  _destroyChart('categories');
  if (catEntries.length) {
    _charts['categories'] = new Chart(document.getElementById('chart-categories'), {
      type: 'doughnut',
      data: {
        labels: catEntries.map(([k]) => k),
        datasets: [{
          data: catEntries.map(([, v]) => v),
          backgroundColor: CAT_PALETTE.slice(0, catEntries.length),
          borderWidth: 2, borderColor: '#fff',
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
          tooltip: { callbacks: { label: ctx => ` ${ctx.label} : ${_fmtEur(ctx.parsed)}` } },
        },
      },
    });
  } else {
    const canvas = document.getElementById('chart-categories');
    const ctx    = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#9ca3af';
    ctx.font      = '13px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Aucune recette ce mois', canvas.width / 2, canvas.height / 2);
  }

  // ── Graphique 3 : Élèves par niveau ──────────────────────────────────────
  const children = cData ? (cData.results || cData) : [];
  const byLevel  = {};
  children.forEach(c => { byLevel[c.level] = (byLevel[c.level] || 0) + 1; });
  const lvlLabels = Object.keys(byLevel).sort();
  _destroyChart('levels');
  _charts['levels'] = new Chart(document.getElementById('chart-levels'), {
    type: 'bar',
    data: {
      labels: lvlLabels.length ? lvlLabels : ['—'],
      datasets: [{
        label: 'Élèves',
        data: lvlLabels.length ? lvlLabels.map(l => byLevel[l]) : [0],
        backgroundColor: lvlLabels.map((_, i) => CAT_PALETTE[i % CAT_PALETTE.length]),
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: '#f0eef8' } },
        x: { grid: { display: false } },
      },
    },
  });

  // ── Graphique 4 : Cotisations (donut + centre) ────────────────────────────
  _destroyChart('membership');
  _charts['membership'] = new Chart(document.getElementById('chart-membership'), {
    type: 'doughnut',
    data: {
      labels: [`À jour (${paidCount})`, `Non cotisants (${unpaidCount})`],
      datasets: [{
        data: paidCount + unpaidCount > 0 ? [paidCount, unpaidCount] : [1, 0],
        backgroundColor: [CHART_COLORS.green, CHART_COLORS.red],
        borderWidth: 3, borderColor: '#fff',
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      cutout: '68%',
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12, font: { size: 11 } } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label} : ${ctx.parsed}` } },
      },
    },
  });
  // Centre du donut
  const centerEl = document.getElementById('chart-membership-center');
  if (centerEl && totalMembers > 0) {
    const pct = _pct(paidCount, totalMembers);
    centerEl.innerHTML = `<strong>${pct}%</strong>à jour`;
    centerEl.style.color = pct >= 80 ? '#16a34a' : pct >= 50 ? '#d97706' : '#dc2626';
  }
}

// ── Alertes contextuelles ─────────────────────────────────────────────────────
function _renderAlerts({ arrearsCount, totalFamilies, unpaidCount, totalMembers, tMonth, monthLabel }) {
  const container = document.getElementById('dash-alerts-row');
  if (!container) return;
  const alerts = [];

  // Alerte impayés école
  if (arrearsCount > 0) {
    const pct = _pct(arrearsCount, totalFamilies);
    alerts.push(`
      <div class="dash-alert-card ${pct >= 30 ? 'alert-warn' : 'alert-info'}">
        <div class="dash-alert-icon">${pct >= 30 ? '⚠️' : '📋'}</div>
        <div class="dash-alert-body">
          <div class="dash-alert-title">${arrearsCount} famille${arrearsCount > 1 ? 's' : ''} sans paiement école</div>
          <div class="dash-alert-desc">Soit ${pct}% des familles inscrites — année en cours</div>
        </div>
        <button class="btn btn-sm" onclick="showSection('arrears')">Voir →</button>
      </div>`);
  } else if (totalFamilies > 0) {
    alerts.push(`
      <div class="dash-alert-card alert-ok">
        <div class="dash-alert-icon">✅</div>
        <div class="dash-alert-body">
          <div class="dash-alert-title">Toutes les familles ont payé</div>
          <div class="dash-alert-desc">Aucun impayé pour l'année scolaire en cours</div>
        </div>
      </div>`);
  }

  // Alerte non cotisants
  if (unpaidCount > 0) {
    const pct = _pct(unpaidCount, totalMembers);
    alerts.push(`
      <div class="dash-alert-card ${pct >= 30 ? 'alert-warn' : 'alert-info'}">
        <div class="dash-alert-icon">🔴</div>
        <div class="dash-alert-body">
          <div class="dash-alert-title">${unpaidCount} adhérent${unpaidCount > 1 ? 's' : ''} non cotisant${unpaidCount > 1 ? 's' : ''}</div>
          <div class="dash-alert-desc">${pct}% des adhérents n'ont pas cotisé cette année</div>
        </div>
        <button class="btn btn-sm" onclick="showSection('unpaid-members')">Voir →</button>
      </div>`);
  }

  // Alerte trésorerie mois courant
  if (tMonth) {
    const bal = parseFloat(tMonth.total_in || 0) - parseFloat(tMonth.total_out || 0);
    if (bal < 0) {
      alerts.push(`
        <div class="dash-alert-card alert-warn">
          <div class="dash-alert-icon">📉</div>
          <div class="dash-alert-body">
            <div class="dash-alert-title">Solde négatif en ${monthLabel}</div>
            <div class="dash-alert-desc">Sorties supérieures aux entrées ce mois : ${_fmtEur(bal)}</div>
          </div>
          <button class="btn btn-sm" onclick="showSection('treasury')">Détails →</button>
        </div>`);
    }
  }

  if (alerts.length) {
    container.innerHTML = alerts.join('');
    container.classList.remove('hidden');
  } else {
    container.classList.add('hidden');
  }
}

// ── Années scolaires ──────────────────────────────────────────────────────────
async function loadSchoolYears() {
  const res = await apiFetch('/school/years/');
  if (!res || !res.ok) return;
  const data = await res.json();
  schoolYears = data.results || data;

  // Select dashboard
  const dash = document.getElementById('school-year-select');
  if (dash) {
    dash.innerHTML = '<option value="">Toutes les années</option>';
    schoolYears.forEach(y => {
      dash.innerHTML += `<option value="${y.id}"${y.is_active ? ' selected' : ''}>${y.label}${y.is_active ? ' (active)' : ''}</option>`;
    });
  }
}
