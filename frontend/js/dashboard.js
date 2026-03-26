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

function _monthsOfYear(year) {
  const months = [];
  for (let m = 1; m <= 12; m++) {
    months.push(`${year}-${String(m).padStart(2, '0')}`);
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

// ── État filtre courant ───────────────────────────────────────────────────────
let _dashFilterMode = '6m';   // '6m' | 'year' | 'last-year' | 'custom'
let _dashFilterYear = null;   // ex: 2024

// Retourne { months, label } selon le mode actif
function _getFilterMonths() {
  const now = new Date();
  if (_dashFilterMode === '6m') {
    const months = _last6Months();
    return { months, label: `${_monthLabel(months[0])} → ${_monthLabel(months[5])}` };
  }
  if (_dashFilterMode === 'year') {
    const months = _monthsOfYear(now.getFullYear());
    return { months, label: `Année ${now.getFullYear()}` };
  }
  if (_dashFilterMode === 'last-year') {
    const months = _monthsOfYear(now.getFullYear() - 1);
    return { months, label: `Année ${now.getFullYear() - 1}` };
  }
  if (_dashFilterMode === 'custom' && _dashFilterYear) {
    const months = _monthsOfYear(_dashFilterYear);
    return { months, label: `Année ${_dashFilterYear}` };
  }
  // fallback
  const months = _last6Months();
  return { months, label: `${_monthLabel(months[0])} → ${_monthLabel(months[5])}` };
}

// ── Dashboard principal ───────────────────────────────────────────────────────
async function loadDashboard() {
  const now        = new Date();
  const currentYm  = now.toISOString().slice(0, 7);
  const monthLabel = now.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

  // ── Remplir le select d'années disponibles (2022 → cette année) ──────────
  const yearSelect = document.getElementById('dash-trs-year-select');
  if (yearSelect && yearSelect.options.length <= 1) {
    const startYear = 2022;
    for (let y = now.getFullYear(); y >= startYear; y--) {
      const opt = document.createElement('option');
      opt.value = y;
      opt.textContent = y;
      yearSelect.appendChild(opt);
    }
  }

  // Requêtes statiques (familles, adhérents, solde total) en parallèle
  const [fRes, cRes, aRes, mRes, tTotalRes, tMonthRes, unpaidRes] = await Promise.all([
    apiFetch('/school/families/'),
    apiFetch('/school/children/'),
    apiFetch('/school/families/arrears/'),
    apiFetch('/membership/members/'),
    apiFetch('/treasury/transactions/summary/?total=1'),
    apiFetch(`/treasury/transactions/summary/?month=${currentYm}`),
    apiFetch('/membership/members/unpaid/'),
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

  // ── KPI Trésorerie (solde global, toujours) ───────────────────────────────
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
  // KPI mois courant (toujours le mois actuel, indépendant du filtre)
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

  // ── Graphique niveaux & adhérents (statiques, pas filtrés) ───────────────
  _renderLevelsChart(cData);
  _renderMembershipChart(paidCount, unpaidCount, totalMembers);

  // ── Graphiques trésorerie (filtrés) ──────────────────────────────────────
  await _renderTreasuryCharts();

  // ── Brancher les boutons filtre ───────────────────────────────────────────
  _initTrsFilter();
}

// ── Init boutons filtre (appelé une seule fois) ───────────────────────────────
function _initTrsFilter() {
  const container = document.getElementById('dash-trs-filter');
  if (!container || container.dataset.bound) return;
  container.dataset.bound = '1';

  container.querySelectorAll('.dtf-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      container.querySelectorAll('.dtf-btn').forEach(b => b.classList.remove('dtf-active'));
      btn.classList.add('dtf-active');
      document.getElementById('dash-trs-year-select').value = '';
      _dashFilterMode = btn.dataset.mode;
      _dashFilterYear = null;
      await _renderTreasuryCharts();
    });
  });

  document.getElementById('dash-trs-year-select').addEventListener('change', async function () {
    if (!this.value) return;
    container.querySelectorAll('.dtf-btn').forEach(b => b.classList.remove('dtf-active'));
    _dashFilterMode = 'custom';
    _dashFilterYear = parseInt(this.value);
    await _renderTreasuryCharts();
  });
}

// ── Graphiques trésorerie (flux + catégories) — re-rendus à chaque filtre ────
async function _renderTreasuryCharts() {
  const { months, label } = _getFilterMonths();

  // Sous-titre période
  const periodEl  = document.getElementById('dash-trs-period');
  if (periodEl) periodEl.textContent = label;
  const catPeriodEl = document.getElementById('dash-cat-period');
  if (catPeriodEl) catPeriodEl.textContent = `— ${label}`;

  // Afficher un spinner pendant le chargement
  _setChartLoading('chart-treasury', true);

  // Charger toutes les données de la période en parallèle
  const summaries = await Promise.all(
    months.map(m => apiFetch(`/treasury/transactions/summary/?month=${m}`).then(r => r?.ok ? r.json() : null))
  );

  const trsIn = [], trsOut = [], trsBalance = [];
  summaries.forEach(d => {
    const _in  = parseFloat(d?.total_in  || 0);
    const _out = parseFloat(d?.total_out || 0);
    trsIn.push(_in);
    trsOut.push(_out);
    trsBalance.push(_in - _out);
  });

  _setChartLoading('chart-treasury', false);
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

  // ── Graphique catégories pour la période sélectionnée ────────────────────
  // Construire le filtre API (year ou mois individuels)
  let catParams = '';
  if (_dashFilterMode === 'year') {
    catParams = `year=${new Date().getFullYear()}`;
  } else if (_dashFilterMode === 'last-year') {
    catParams = `year=${new Date().getFullYear() - 1}`;
  } else if (_dashFilterMode === 'custom' && _dashFilterYear) {
    catParams = `year=${_dashFilterYear}`;
  } else {
    // 6 mois : on agrège les résultats des summaries déjà chargés
    catParams = null;
  }

  let catTxs = [];
  if (catParams) {
    const catRes = await apiFetch(`/treasury/transactions/?direction=IN&${catParams}&page_size=1000`);
    catTxs = catRes?.ok ? ((await catRes.json()).results || []) : [];
  } else {
    // 6 mois glissants : agréger depuis les summaries déjà chargés
    const catFromSummaries = {};
    summaries.forEach(d => {
      if (!d?.categories) return;
      Object.entries(d.categories).forEach(([cat, vals]) => {
        catFromSummaries[cat] = (catFromSummaries[cat] || 0) + (vals.in || 0);
      });
    });
    // on reconstruit un tableau synthétique
    catTxs = Object.entries(catFromSummaries).map(([category, amount]) => ({ category, amount }));
  }

  const catMap = {};
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
    const ctx2   = canvas.getContext('2d');
    ctx2.clearRect(0, 0, canvas.width, canvas.height);
    ctx2.fillStyle = '#9ca3af';
    ctx2.font      = '13px Inter, sans-serif';
    ctx2.textAlign = 'center';
    ctx2.fillText('Aucune recette sur cette période', canvas.width / 2, canvas.height / 2);
  }
}

// ── Loader canvas ─────────────────────────────────────────────────────────────
function _setChartLoading(canvasId, loading) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  if (loading) {
    _destroyChart(canvasId === 'chart-treasury' ? 'treasury' : canvasId);
    const ctx2 = canvas.getContext('2d');
    ctx2.clearRect(0, 0, canvas.width, canvas.height);
    ctx2.fillStyle = '#c4b5fd';
    ctx2.font      = '13px Inter, sans-serif';
    ctx2.textAlign = 'center';
    ctx2.fillText('Chargement…', canvas.width / 2, canvas.height / 2);
  }
}

// ── Graphique niveaux ─────────────────────────────────────────────────────────
function _renderLevelsChart(cData) {
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
}

// ── Graphique adhérents (donut) ───────────────────────────────────────────────
function _renderMembershipChart(paidCount, unpaidCount, totalMembers) {
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

  const dash = document.getElementById('school-year-select');
  if (dash) {
    dash.innerHTML = '<option value="">Toutes les années</option>';
    schoolYears.forEach(y => {
      dash.innerHTML += `<option value="${y.id}"${y.is_active ? ' selected' : ''}>${y.label}${y.is_active ? ' (active)' : ''}</option>`;
    });
  }
}


