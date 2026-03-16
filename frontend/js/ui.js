/* ═══════════════════════════════════════════════════════════
   ui.js — Toasts, confirm dialog, skeleton, empty state, modals
═══════════════════════════════════════════════════════════ */

// ── Toasts ────────────────────────────────────────────────────────────────────
function toast(msg, type = 'success', duration = 3500) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `
    <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
    <span class="toast-msg">${msg}</span>
    <button class="toast-close" onclick="removeToast(this.parentElement)">✕</button>`;
  container.appendChild(el);
  setTimeout(() => removeToast(el), duration);
}

function removeToast(el) {
  if (!el || !el.parentElement) return;
  el.classList.add('removing');
  setTimeout(() => el.remove(), 220);
}

// ── Confirm dialog ────────────────────────────────────────────────────────────
function confirmDialog({ title = 'Confirmation', msg = '', icon = '🗑️', okLabel = 'Supprimer', okClass = 'btn-danger' } = {}) {
  return new Promise(resolve => {
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-msg').textContent   = msg;
    document.getElementById('confirm-icon').textContent  = icon;
    const okBtn     = document.getElementById('confirm-ok-btn');
    const cancelBtn = document.getElementById('confirm-cancel-btn');
    okBtn.textContent = okLabel;
    okBtn.className   = `btn ${okClass}`;
    const overlay = document.getElementById('confirm-overlay');
    overlay.classList.add('open');
    const cleanup = (val) => {
      overlay.classList.remove('open');
      okBtn.onclick     = null;
      cancelBtn.onclick = null;
      resolve(val);
    };
    okBtn.onclick     = () => cleanup(true);
    cancelBtn.onclick = () => cleanup(false);
  });
}

// ── Skeleton helpers ──────────────────────────────────────────────────────────
function skeletonRows(n, cols) {
  const widths = ['skel-lg', 'skel-md', 'skel-sm', 'skel-xl', 'skel-md'];
  return Array.from({ length: n }, () =>
    `<tr class="skeleton-row">${Array.from({ length: cols }, (_, i) =>
      `<td><div class="skel ${widths[i % widths.length]}"></div></td>`
    ).join('')}</tr>`
  ).join('');
}

// ── Empty state helper ────────────────────────────────────────────────────────
function emptyState({ icon = '📭', title = 'Aucune donnée', sub = '', actionLabel = '', actionFn = '' } = {}) {
  return `<tr><td colspan="99">
    <div class="empty-state">
      <div class="empty-state-icon">${icon}</div>
      <div class="empty-state-title">${title}</div>
      ${sub ? `<div class="empty-state-sub">${sub}</div>` : ''}
      ${actionLabel && actionFn ? `<button class="btn btn-primary" onclick="${actionFn}">${actionLabel}</button>` : ''}
    </div>
  </td></tr>`;
}

// ── Modals ────────────────────────────────────────────────────────────────────
function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// Fermer les modals en cliquant en dehors
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.classList.remove('open');
    });
  });
});

// ── Escape HTML ───────────────────────────────────────────────────────────────
function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
