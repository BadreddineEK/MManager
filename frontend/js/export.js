/* ═══════════════════════════════════════════════════════════
   export.js — Export Excel/PDF, backup import/export
═══════════════════════════════════════════════════════════ */

// ── Export Excel / PDF ────────────────────────────────────────────────────────
async function exportFile(resource, format) {
  const url = `${API}/export/${resource}/${format}/`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${localStorage.getItem('access')}` },
  });
  if (!res.ok) { toast('Erreur export', 'error'); return; }
  const blob = await res.blob();
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  const ext  = format === 'excel' ? 'xlsx' : 'pdf';
  a.download = `${resource}_${new Date().toISOString().slice(0, 10)}.${ext}`;
  a.click();
}

// ── Backup export ─────────────────────────────────────────────────────────────
async function backupExport() {
  const statusEl = document.getElementById('backup-export-status');
  statusEl.textContent = '⏳ Génération en cours…';
  try {
    const res = await fetch(`${API}/backup/export/`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('access')}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      statusEl.textContent = '❌ ' + (err.detail || "Erreur lors de l'export");
      return;
    }
    const cd       = res.headers.get('Content-Disposition') || '';
    const match    = cd.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : `backup_${new Date().toISOString().slice(0, 10)}.zip`;
    const blob = await res.blob();
    const a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    statusEl.textContent = `✅ Sauvegarde téléchargée : ${filename}`;
  } catch (e) {
    statusEl.textContent = '❌ Erreur réseau : ' + e.message;
  }
}

// ── Backup import ─────────────────────────────────────────────────────────────
function backupImportPreview() {
  const input    = document.getElementById('backup-file-input');
  const btn      = document.getElementById('backup-import-btn');
  const statusEl = document.getElementById('backup-import-status');
  if (input.files && input.files[0]) {
    btn.disabled       = false;
    statusEl.textContent = `📂 Fichier sélectionné : ${input.files[0].name}`;
    statusEl.style.color = 'var(--muted)';
  } else {
    btn.disabled         = true;
    statusEl.textContent = '';
  }
}

async function backupImport() {
  const input    = document.getElementById('backup-file-input');
  const statusEl = document.getElementById('backup-import-status');
  const btn      = document.getElementById('backup-import-btn');

  if (!input.files || !input.files[0]) {
    statusEl.textContent = '⚠️ Sélectionnez d\'abord un fichier ZIP.';
    return;
  }
  const file = input.files[0];
  if (!confirm(`Importer "${file.name}" ?\n\nLes données existantes ne seront pas écrasées. Les nouvelles données seront fusionnées.`)) return;

  btn.disabled          = true;
  statusEl.innerHTML    = '⏳ Import en cours, veuillez patienter…';
  statusEl.style.color  = 'var(--muted)';

  try {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API}/backup/import/`, {
      method:  'POST',
      headers: { Authorization: `Bearer ${localStorage.getItem('access')}` },
      body:    formData,
    });
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      statusEl.innerHTML = `<span style="color:var(--red);">❌ ${data.detail || "Erreur lors de l'import"}</span>`;
      btn.disabled = false;
      return;
    }

    const c     = data.created || {};
    const lines = Object.entries(c).map(([k, v]) =>
      `<li><strong>${v}</strong> ${k.replace(/_/g, ' ')}</li>`
    ).join('');
    statusEl.innerHTML = `
      <div style="background:var(--green-soft);border:1px solid #86efac;border-radius:8px;padding:14px;color:#14532d;">
        <strong>✅ Import terminé — ${data.total_created} enregistrement(s) créé(s)</strong>
        <ul style="margin-top:8px;padding-left:18px;font-size:0.8rem;">${lines}</ul>
        ${data.errors && data.errors.length
          ? `<details style="margin-top:8px;font-size:0.76rem;"><summary>${data.errors.length} avertissement(s)</summary><ul>${data.errors.map(e => `<li>${e}</li>`).join('')}</ul></details>`
          : ''}
      </div>`;
    input.value  = '';
    btn.disabled = true;
  } catch (e) {
    statusEl.innerHTML = `<span style="color:var(--red);">❌ Erreur réseau : ${e.message}</span>`;
    btn.disabled = false;
  }
}
