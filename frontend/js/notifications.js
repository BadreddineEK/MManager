/* ═══════════════════════════════════════════════════════════
   notifications.js — Envoi de rappels email (impayés / non cotisants)
═══════════════════════════════════════════════════════════ */

async function sendArrearsNotifs() {
  const btn = document.getElementById('btn-send-arrears-notif');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Envoi…'; }
  const res = await apiFetch('/notifications/send-arrears/', 'POST', {});
  if (btn) { btn.disabled = false; btn.innerHTML = '📧 Envoyer rappels'; }
  if (!res) return;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast('Erreur : ' + (data.detail || JSON.stringify(data)), 'error', 5000);
    return;
  }
  openNotifResultModal(data, 'Rappels — Familles avec impayés');
}

async function sendUnpaidMembersNotifs() {
  const btn = document.getElementById('btn-send-unpaid-notif');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Envoi…'; }
  const res = await apiFetch('/notifications/send-unpaid-members/', 'POST', {});
  if (btn) { btn.disabled = false; btn.innerHTML = '📧 Envoyer rappels'; }
  if (!res) return;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    toast('Erreur : ' + (data.detail || JSON.stringify(data)), 'error', 5000);
    return;
  }
  openNotifResultModal(data, 'Rappels — Adhérents non cotisants');
}

function openNotifResultModal(data, title) {
  document.getElementById('notif-result-title').textContent = title;

  const year = data.year || '—';
  const sentCount    = (data.sent    || []).length;
  const failedCount  = (data.failed  || []).length;
  const skippedCount = (data.skipped || []).length;

  const sentRows = (data.sent || []).map(r =>
    `<tr><td>${r.name || r.email}</td><td style="color:var(--success)">✅ Envoyé</td></tr>`
  ).join('');
  const failedRows = (data.failed || []).map(r =>
    `<tr><td>${r.name || r.email}</td><td style="color:var(--danger)">❌ ${r.error || 'Échec'}</td></tr>`
  ).join('');
  const skippedRows = (data.skipped || []).map(r =>
    `<tr><td>${r.name}</td><td style="color:var(--muted)">⚠️ Pas d'email</td></tr>`
  ).join('');

  document.getElementById('notif-result-body').innerHTML = `
    <p style="margin-bottom:16px;font-size:0.88rem;color:var(--muted);">Année : <strong>${year}</strong></p>
    <div class="stats-row" style="grid-template-columns:repeat(3,1fr);max-width:360px;margin-bottom:20px;">
      <div class="stat-card">
        <div class="num text-green">${sentCount}</div>
        <div class="lbl">Envoyés</div>
      </div>
      <div class="stat-card">
        <div class="num text-red">${failedCount}</div>
        <div class="lbl">Échecs</div>
      </div>
      <div class="stat-card">
        <div class="num" style="color:var(--muted)">${skippedCount}</div>
        <div class="lbl">Sans email</div>
      </div>
    </div>
    ${sentRows || failedRows || skippedRows ? `
    <div class="card table-wrapper" style="max-height:280px;overflow-y:auto;">
      <table>
        <thead><tr><th>Destinataire</th><th>Statut</th></tr></thead>
        <tbody>${sentRows}${failedRows}${skippedRows}</tbody>
      </table>
    </div>` : '<p style="color:var(--muted);text-align:center;padding:20px;">Aucun destinataire trouvé.</p>'}
  `;
  document.getElementById('modal-notif-result').classList.remove('hidden');
}

async function testEmail() {
  const to  = document.getElementById('s-smtp-test-email').value.trim();
  const btn = document.getElementById('btn-smtp-test');
  const status = document.getElementById('smtp-test-status');
  if (!to) { status.innerHTML = '<span style="color:var(--danger)">Saisissez une adresse email.</span>'; return; }
  btn.disabled = true;
  btn.textContent = '⏳ Test…';
  status.textContent = '';
  const res = await apiFetch('/notifications/test/', 'POST', { to });
  btn.disabled = false;
  btn.textContent = '✉️ Tester SMTP';
  if (!res) return;
  const data = await res.json().catch(() => ({}));
  if (res.ok) {
    status.innerHTML = `<span style="color:var(--success)">✅ Email envoyé à ${to}</span>`;
  } else {
    status.innerHTML = `<span style="color:var(--danger)">❌ ${data.detail || data.error || 'Erreur SMTP'}</span>`;
  }
}
