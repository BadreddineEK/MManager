/* ═══════════════════════════════════════════════════════════
   dashboard.js — KPI, graphiques Chart.js, années scolaires
═══════════════════════════════════════════════════════════ */

// ── Instances Chart.js ────────────────────────────────────────────────────────
const _charts = {};

function _destroyChart(id) {
  if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
}

// ── Palette cohérente avec le thème violet/dark ───────────────────────────────
const CHART_COLORS = {
  purple:      'rgba(124, 58, 237, 0.8)',
  purpleLight: 'rgba(124, 58, 237, 0.15)',
  green:       'rgba(22, 163, 74, 0.8)',
  greenLight:  'rgba(22, 163, 74, 0.15)',
  red:         'rgba(220, 38, 38, 0.8)',
  redLight:    'rgba(220, 38, 38, 0.15)',
  blue:        'rgba(59, 130, 246, 0.8)',
  orange:      'rgba(234, 88, 12, 0.8)',
  gray:        'rgba(156, 163, 175, 0.8)',
};

Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
Chart.defaults.color = '#6b7280';

// ── Helpers date ──────────────────────────────────────────────────────────────
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

// ── Dashboard principal ───────────────────────────────────────────────────────
async function loadDashboard() {
  const months = _last6Months();

  const [fRes, cRes, pRes, aRes, mRes, tTotalRes, tMonthRes, unpaidRes] = await Promise.all([
    apiFetch('/school/families/'),
    apiFetch('/school/children/'),
    apiFetch('/school/payments/'),
    apiFetch('/school/families/arrears/'),
    apiFetch('/membership/members/'),
    apiFetch('/treasury/transactions/summary/?total=1'),
    apiFetch(`/treasury/transactions/summary/?month=${new Date().toISOString().slice(0, 7)}`),
    apiFetch('/membership/members/unpaid/'),
  ]);

  const fData    = fRes?.ok      ? await fRes.json()      : null;
  const cData    = cRes?.ok      ? await cRes.json()      : null;
  const pData    = pRes?.ok      ? await pRes.json()      : null;
  const aData    = aRes?.ok      ? await aRes.json()      : null;
  const mData    = mRes?.ok      ? await mRes.json()      : null;
  const tTotal   = tTotalRes?.ok ? await tTotalRes.json() : null;
  const tSum     = tMonthRes?.ok ? await tMonthRes.json() : null;
  const unpaid   = unpaidRes?.ok ? await unpaidRes.json() : null;

  const families   = fData  ? (fData.results  || fData)  : [];
  const children   = cData  ? (cData.results  || cData)  : [];
  const payments   = pData  ? (pData.results  || pData)  : [];
  const members    = mData  ? (mData.results  || mData)  : [];
  const unpaidList = unpaid ? (unpaid.results || unpaid) : [];

  // ── KPI stat-cards ────────────────────────────────────────────────────────
  document.getElementById('stat-families').textContent = fData?.count ?? families.length;
  document.getElementById('stat-children').textContent = cData?.count ?? children.length;
  document.getElementById('stat-payments').textContent = pData?.count ?? payments.length;
  document.getElementById('stat-arrears').textContent  = aData?.count ?? (aData?.families?.length ?? 0);
  document.getElementById('stat-members').textContent  = mData?.count ?? members.length;

  if (tTotal) {
    const bal = parseFloat(tTotal.balance);
    const el  = document.getElementById('stat-balance');
    el.textContent = `${bal >= 0 ? '+' : ''}${bal.toFixed(0)} €`;
    el.style.color = bal >= 0 ? '#16a34a' : '#dc2626';
    // Sous-titre : entrées/sorties du mois courant
    if (tSum) {
      const mBal = parseFloat(tSum.balance ?? 0);
      const now = new Date();
      const monthLabel = now.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
      const sub = document.getElementById('stat-balance-month');
      if (sub) sub.textContent = `${monthLabel} : ${mBal >= 0 ? '+' : ''}${mBal.toFixed(0)} €`;
    }
  }

  await loadSchoolYears();

  // ── Graphique 1 : Paiements école — 6 derniers mois ──────────────────────
  const payByMonth = {};
  months.forEach(m => { payByMonth[m] = 0; });
  payments.forEach(p => {
    const key = p.date?.slice(0, 7);
    if (key in payByMonth) payByMonth[key] += parseFloat(p.amount || 0);
  });
  _destroyChart('school-payments');
  _charts['school-payments'] = new Chart(document.getElementById('chart-school-payments'), {
    type: 'bar',
    data: {
      labels: months.map(_monthLabel),
      datasets: [{
        label: 'Paiements (€)',
        data: months.map(m => payByMonth[m]),
        backgroundColor: CHART_COLORS.purple,
        borderColor: CHART_COLORS.purple,
        borderRadius: 6,
      }],
    },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
  });

  // ── Graphique 2 : Enfants par niveau ─────────────────────────────────────
  const byLevel = {};
  children.forEach(c => { byLevel[c.level] = (byLevel[c.level] || 0) + 1; });
  const lvlLabels = Object.keys(byLevel).sort();
  const palette   = ['#7c3aed','#2563eb','#16a34a','#ea580c','#dc2626','#0891b2','#a855f7'];
  _destroyChart('levels');
  _charts['levels'] = new Chart(document.getElementById('chart-levels'), {
    type: 'doughnut',
    data: {
      labels: lvlLabels.length ? lvlLabels : ['Aucun élève'],
      datasets: [{
        data: lvlLabels.length ? lvlLabels.map(l => byLevel[l]) : [1],
        backgroundColor: palette, borderWidth: 2,
      }],
    },
    options: { responsive: true, plugins: { legend: { position: 'right' } } },
  });

  // ── Graphique 3 : Trésorerie entrées vs sorties — 6 derniers mois ────────
  const trsIn = [], trsOut = [];
  for (const month of months) {
    const res = await apiFetch(`/treasury/transactions/summary/?month=${month}`);
    if (res?.ok) {
      const d = await res.json();
      trsIn.push(parseFloat(d.total_in  || 0));
      trsOut.push(parseFloat(d.total_out || 0));
    } else {
      trsIn.push(0); trsOut.push(0);
    }
  }
  _destroyChart('treasury');
  _charts['treasury'] = new Chart(document.getElementById('chart-treasury'), {
    type: 'bar',
    data: {
      labels: months.map(_monthLabel),
      datasets: [
        { label: 'Entrées (€)', data: trsIn,  backgroundColor: CHART_COLORS.green, borderRadius: 4 },
        { label: 'Sorties (€)', data: trsOut, backgroundColor: CHART_COLORS.red,   borderRadius: 4 },
      ],
    },
    options: { responsive: true, plugins: { legend: { position: 'top' } }, scales: { y: { beginAtZero: true } } },
  });

  // ── Graphique 4 : Adhérents cotisants vs non cotisants ────────────────────
  const unpaidCount = unpaid?.count ?? unpaidList.length;
  const totalMbrs   = mData?.count  ?? members.length;
  const paidCount   = Math.max(0, totalMbrs - unpaidCount);
  _destroyChart('membership');
  _charts['membership'] = new Chart(document.getElementById('chart-membership'), {
    type: 'pie',
    data: {
      labels: [`✅ À jour (${paidCount})`, `❌ Non cotisants (${unpaidCount})`],
      datasets: [{
        data: [paidCount, unpaidCount],
        backgroundColor: [CHART_COLORS.green, CHART_COLORS.red], borderWidth: 2,
      }],
    },
    options: { responsive: true, plugins: { legend: { position: 'bottom' } } },
  });
}

// ── Années scolaires ──────────────────────────────────────────────────────────
async function loadSchoolYears() {
  const res = await apiFetch('/school/years/');
  if (!res || !res.ok) return;
  const data = await res.json();
  schoolYears = data.results || data;

  // Select filtre paiements
  const sel = document.getElementById('payment-year-filter');
  sel.innerHTML = '<option value="">Toutes les années</option>';
  schoolYears.forEach(y => {
    sel.innerHTML += `<option value="${y.id}">${y.label}${y.is_active ? ' ✓' : ''}</option>`;
  });

  // Select dashboard
  const dash = document.getElementById('school-year-select');
  if (dash) {
    dash.innerHTML = '<option value="">Toutes les années</option>';
    schoolYears.forEach(y => {
      dash.innerHTML += `<option value="${y.id}"${y.is_active ? ' selected' : ''}>${y.label}${y.is_active ? ' (active)' : ''}</option>`;
    });
  }
}
