/* ═══════════════════════════════════════════════════════════
   nav.js — Navigation sections, sidebar mobile, bottom nav
═══════════════════════════════════════════════════════════ */

const ALL_SECTIONS = [
  'school', 'families', 'children', 'payments', 'arrears',
  'members', 'memberships', 'unpaid-members', 'treasury',
  'campaigns', 'users', 'settings', 'audit',
];

function showSection(name) {
  if (window.innerWidth <= 768) closeSidebar();

  ALL_SECTIONS.forEach(s => {
    document.getElementById(`section-${s}`).classList.add('hidden');
    const nav = document.getElementById(`nav-${s}`);
    if (nav) nav.classList.remove('active');
  });

  document.getElementById(`section-${name}`).classList.remove('hidden');
  const activeNav = document.getElementById(`nav-${name}`);
  if (activeNav) activeNav.classList.add('active');

  // Charger les données de la section affichée
  if (name === 'families')       loadFamilies();
  if (name === 'children')       loadChildren();
  if (name === 'payments')       loadPayments();
  if (name === 'arrears')        loadArrears();
  if (name === 'members')        loadMembers();
  if (name === 'memberships')    loadMembershipPayments();
  if (name === 'unpaid-members') loadUnpaidMembers();
  if (name === 'treasury')       loadTreasury();
  if (name === 'campaigns')      loadCampaigns();
  if (name === 'users')          loadUsers();
  if (name === 'settings')       loadSettings();
  if (name === 'audit')          loadAudit();
}

// ── Mobile sidebar ────────────────────────────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const btn     = document.getElementById('hamburger-btn');
  const isOpen  = sidebar.classList.contains('mobile-open');
  sidebar.classList.toggle('mobile-open', !isOpen);
  overlay.classList.toggle('open', !isOpen);
  btn.classList.toggle('open', !isOpen);
}

function closeSidebar() {
  document.getElementById('sidebar').classList.remove('mobile-open');
  document.getElementById('sidebar-overlay').classList.remove('open');
  document.getElementById('hamburger-btn').classList.remove('open');
}

// ── Bottom nav ────────────────────────────────────────────────────────────────
function setBottomNav(activeId) {
  document.querySelectorAll('.bottom-nav-item').forEach(el => el.classList.remove('active'));
  const el = document.getElementById(activeId);
  if (el) el.classList.add('active');
}
