#!/usr/bin/env python3
"""Patch ecole.html et ecole.js pour ajouter le module Appreciations."""

import re

# ── PATCH ecole.html ──────────────────────────────────────────────────────────

with open('/home/mosquee/nidham-dev/frontend/ecole.html', 'r') as f:
    html = f.read()

# 1. Nav item
OLD_NAV = '      <button class="nav-item" id="nav-sessions-hist" onclick="showTab(\'sessions-hist\')">\n        <span class="nav-icon">🗓️</span> Historique\n      </button>'
NEW_NAV = OLD_NAV + """
      <button class="nav-item" id="nav-appreciations" onclick="showTab('appreciations')">
        <span class="nav-icon">🎓</span> Appréciations
      </button>"""

if OLD_NAV in html:
    html = html.replace(OLD_NAV, NEW_NAV, 1)
    print("✅ nav-item OK")
else:
    print("❌ nav-item NOT FOUND")

# 2. Pane Appreciations (insérer avant </main>)
PANE_APPRECIATIONS = """
    <!-- ── APPRÉCIATIONS ────────────────────────────────────────────────── -->
    <div id="pane-appreciations" class="ecole-pane content-area">
      <div class="page-header">
        <div>
          <h1 class="page-title">🎓 Appréciations</h1>
          <div class="breadcrumb">École coranique · Bulletins & notes</div>
        </div>
        <div style="display:flex;gap:8px">
          <button class="btn btn-primary" id="btn-new-period" onclick="openPeriodModal()">+ Nouvelle période</button>
          <button class="btn btn-primary" id="btn-save-grades" onclick="saveAllGrades()" style="display:none">💾 Enregistrer tout</button>
        </div>
      </div>
      <div class="content-body">
        <!-- Sélection période -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-body" style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
            <div class="form-group" style="flex:1;min-width:200px;margin:0">
              <label class="form-label">Période</label>
              <select id="grade-period-select" class="form-control" onchange="onPeriodChange()">
                <option value="">— Sélectionner une période —</option>
              </select>
            </div>
            <div class="form-group" style="flex:1;min-width:180px;margin:0">
              <label class="form-label">Classe</label>
              <select id="grade-class-select" class="form-control" onchange="loadGradeStudents()">
                <option value="">— Toutes les classes —</option>
              </select>
            </div>
            <button class="btn" id="btn-publish-period" onclick="publishPeriod()" style="display:none;align-self:flex-end">📢 Publier les bulletins</button>
          </div>
        </div>
        <!-- Info période -->
        <div id="grade-period-info" class="alert hidden" style="margin-bottom:16px"></div>
        <!-- Tableau élèves -->
        <div class="card table-wrapper" id="grade-table-card" style="display:none">
          <table>
            <thead>
              <tr>
                <th>Élève</th>
                <th>Mention</th>
                <th>Appréciation</th>
                <th>Absences</th>
                <th>Sourates</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="grade-students-table"></tbody>
          </table>
          <div style="padding:12px;text-align:right">
            <button class="btn btn-primary" onclick="saveAllGrades()">💾 Enregistrer tout</button>
          </div>
        </div>
        <div id="grade-empty" class="alert hidden">Aucun élève inscrit dans cette période / classe.</div>
      </div>
    </div>
"""

if "  </main>" in html:
    html = html.replace("  </main>", PANE_APPRECIATIONS + "\n  </main>", 1)
    print("✅ pane OK")
else:
    print("❌ pane anchor NOT FOUND")

# 3. Modal nouvelle période
MODAL_PERIOD = """
<!-- ── MODAL PÉRIODE ─────────────────────────────────────────────────────────── -->
<div id="modal-period" class="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <h3 id="modal-period-title">Nouvelle période</h3>
      <button class="btn-close" onclick="closeModal('modal-period')">✕</button>
    </div>
    <div class="modal-body">
      <input type="hidden" id="period-id">
      <div class="form-group">
        <label class="form-label">Nom *</label>
        <input id="period-name" class="form-control" placeholder="ex: Trimestre 1">
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Début *</label>
          <input id="period-start" type="date" class="form-control">
        </div>
        <div class="form-group">
          <label class="form-label">Fin *</label>
          <input id="period-end" type="date" class="form-control">
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Ordre d'affichage</label>
        <input id="period-order" type="number" class="form-control" value="1" min="1" max="10">
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('modal-period')">Annuler</button>
      <button class="btn btn-primary" onclick="savePeriod()">💾 Enregistrer</button>
    </div>
  </div>
</div>

<!-- ── MODAL APPRÉCIATION ÉLÈVE ──────────────────────────────────────────────── -->
<div id="modal-grade" class="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <h3 id="modal-grade-title">Appréciation</h3>
      <button class="btn-close" onclick="closeModal('modal-grade')">✕</button>
    </div>
    <div class="modal-body">
      <input type="hidden" id="grade-child-id">
      <div class="form-group">
        <label class="form-label">Mention *</label>
        <select id="grade-mention" class="form-control">
          <option value="TB">TB — Très bien</option>
          <option value="B">B — Bien</option>
          <option value="AB">AB — Assez bien</option>
          <option value="P">P — Peut mieux faire</option>
          <option value="I">I — Insuffisant</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Appréciation libre</label>
        <textarea id="grade-appreciation" class="form-control" rows="3" placeholder="Commentaire du professeur..."></textarea>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Absences sur la période</label>
          <input id="grade-absences" type="number" class="form-control" value="0" min="0">
        </div>
        <div class="form-group">
          <label class="form-label">Sourates mémorisées</label>
          <input id="grade-surahs" type="number" class="form-control" value="0" min="0">
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('modal-grade')">Annuler</button>
      <button class="btn btn-primary" onclick="saveGradeFromModal()">💾 Enregistrer</button>
    </div>
  </div>
</div>
"""

# Insert before <!-- ── SCRIPTS ──
if "<!-- ── SCRIPTS" in html:
    html = html.replace("<!-- ── SCRIPTS", MODAL_PERIOD + "\n<!-- ── SCRIPTS", 1)
    print("✅ modals OK")
else:
    print("❌ scripts anchor NOT FOUND")

with open('/home/mosquee/nidham-dev/frontend/ecole.html', 'w') as f:
    f.write(html)

print(f"✅ ecole.html: {len(html)} chars")

# ── PATCH ecole.js ────────────────────────────────────────────────────────────

with open('/home/mosquee/nidham-dev/frontend/js/ecole.js', 'r') as f:
    js = f.read()

JS_APPRECIATIONS = """

// ═══════════════════════════════════════════════════════════════════════════
// APPRÉCIATIONS — Périodes & Grades
// ═══════════════════════════════════════════════════════════════════════════

let allPeriods = [];
let currentPeriodId = null;
let gradeRows = {};  // { child_id: { mention, appreciation, absences_count, surah_memorized_count, class_id } }

async function loadPeriods() {
  try {
    const data = await api('/school/periods/');
    allPeriods = data.results || data;
    const sel = document.getElementById('grade-period-select');
    sel.innerHTML = '<option value="">— Sélectionner une période —</option>';
    allPeriods.forEach(p => {
      sel.innerHTML += `<option value="${p.id}">${p.name} ${p.is_published ? '📢' : ''}</option>`;
    });
  } catch(e) {
    showToast('Erreur chargement périodes', 'error');
  }
}

function onPeriodChange() {
  const sel = document.getElementById('grade-period-select');
  currentPeriodId = sel.value || null;
  gradeRows = {};
  document.getElementById('grade-table-card').style.display = 'none';
  document.getElementById('grade-empty').classList.add('hidden');
  document.getElementById('btn-publish-period').style.display = 'none';

  if (!currentPeriodId) {
    document.getElementById('grade-period-info').classList.add('hidden');
    return;
  }

  const period = allPeriods.find(p => p.id == currentPeriodId);
  if (period) {
    const info = document.getElementById('grade-period-info');
    info.className = 'alert alert-info';
    info.textContent = `📅 ${period.name} · du ${period.start_date} au ${period.end_date}${period.is_published ? ' · ✅ Bulletins publiés' : ''}`;
    document.getElementById('btn-publish-period').style.display = period.is_published ? 'none' : '';
  }

  // Charger les classes dispo
  loadGradeClasses();
}

async function loadGradeClasses() {
  try {
    const data = await api('/school/classes/');
    const rows = data.results || data;
    const sel = document.getElementById('grade-class-select');
    sel.innerHTML = '<option value="">— Toutes les classes —</option>';
    rows.forEach(c => {
      sel.innerHTML += `<option value="${c.id}">${c.name}</option>`;
    });
    await loadGradeStudents();
  } catch(e) {}
}

async function loadGradeStudents() {
  if (!currentPeriodId) return;

  const classId = document.getElementById('grade-class-select').value;
  gradeRows = {};

  try {
    // Élèves inscrits dans la classe (ou tous si pas de classe sélectionnée)
    let url = classId ? `/school/classes/${classId}/students/` : '/school/children/';
    const data = await api(url);
    const students = data.results || data;

    // Grades existants pour cette période
    let existingGrades = {};
    try {
      const gData = await api(`/school/periods/${currentPeriodId}/grades/`);
      const gList = gData.results || gData;
      gList.forEach(g => { existingGrades[g.child] = g; });
    } catch(e) {}

    const tbody = document.getElementById('grade-students-table');
    tbody.innerHTML = '';

    if (!students.length) {
      document.getElementById('grade-table-card').style.display = 'none';
      document.getElementById('grade-empty').classList.remove('hidden');
      return;
    }

    document.getElementById('grade-empty').classList.add('hidden');
    document.getElementById('grade-table-card').style.display = '';

    students.forEach(s => {
      const childId = s.child_id || s.id;
      const existing = existingGrades[childId] || {};
      gradeRows[childId] = {
        mention: existing.mention || 'B',
        appreciation: existing.appreciation || '',
        absences_count: existing.absences_count || 0,
        surah_memorized_count: existing.surah_memorized_count || 0,
        class_id: classId || existing.school_class || null,
      };

      const mentionColor = { TB: 'var(--green)', B: 'var(--accent)', AB: '#f59e0b', P: '#d97706', I: 'var(--red)' };
      const m = gradeRows[childId].mention;

      tbody.innerHTML += `
        <tr id="grade-row-${childId}">
          <td><strong>${s.first_name || s.child_first_name || '—'} ${s.last_name || s.child_last_name || ''}</strong></td>
          <td>
            <select class="form-control" style="width:80px;padding:4px"
              onchange="gradeRows[${childId}].mention=this.value;updateMentionColor(${childId},this.value)">
              ${['TB','B','AB','P','I'].map(v => `<option value="${v}" ${v===m?'selected':''}>${v}</option>`).join('')}
            </select>
          </td>
          <td>
            <input class="form-control" style="min-width:180px" value="${gradeRows[childId].appreciation}"
              oninput="gradeRows[${childId}].appreciation=this.value"
              placeholder="Appréciation...">
          </td>
          <td>
            <input type="number" class="form-control" style="width:60px;padding:4px" min="0"
              value="${gradeRows[childId].absences_count}"
              oninput="gradeRows[${childId}].absences_count=parseInt(this.value)||0">
          </td>
          <td>
            <input type="number" class="form-control" style="width:60px;padding:4px" min="0"
              value="${gradeRows[childId].surah_memorized_count}"
              oninput="gradeRows[${childId}].surah_memorized_count=parseInt(this.value)||0">
          </td>
          <td>
            <button class="btn btn-sm" onclick="openGradeModal(${childId})">✏️</button>
          </td>
        </tr>`;
    });

  } catch(e) {
    showToast('Erreur chargement élèves: ' + e.message, 'error');
  }
}

function updateMentionColor(childId, mention) {
  const colors = { TB: 'var(--green)', B: 'var(--accent)', AB: '#f59e0b', P: '#d97706', I: 'var(--red)' };
  const sel = document.querySelector(`#grade-row-${childId} select`);
  if (sel) sel.style.color = colors[mention] || '';
}

async function saveAllGrades() {
  if (!currentPeriodId) return showToast('Sélectionner une période', 'warning');

  const payload = Object.entries(gradeRows).map(([child_id, g]) => ({
    child_id: parseInt(child_id),
    mention: g.mention,
    appreciation: g.appreciation,
    absences_count: g.absences_count,
    surah_memorized_count: g.surah_memorized_count,
    class_id: g.class_id,
  }));

  if (!payload.length) return showToast('Aucun élève à enregistrer', 'warning');

  try {
    showProgress();
    const res = await api(`/school/periods/${currentPeriodId}/grades/`, 'POST', payload);
    showToast(`✅ ${res.saved} appréciation(s) enregistrée(s)${res.errors?.length ? ' · ' + res.errors.length + ' erreur(s)' : ''}`, res.errors?.length ? 'warning' : 'success');
  } catch(e) {
    showToast('Erreur: ' + e.message, 'error');
  } finally {
    hideProgress();
  }
}

function openGradeModal(childId) {
  const g = gradeRows[childId];
  if (!g) return;
  document.getElementById('grade-child-id').value = childId;
  document.getElementById('grade-mention').value = g.mention;
  document.getElementById('grade-appreciation').value = g.appreciation;
  document.getElementById('grade-absences').value = g.absences_count;
  document.getElementById('grade-surahs').value = g.surah_memorized_count;
  const row = document.getElementById('grade-row-' + childId);
  const name = row ? row.querySelector('td strong')?.textContent : 'Élève';
  document.getElementById('modal-grade-title').textContent = '🎓 ' + name;
  openModal('modal-grade');
}

function saveGradeFromModal() {
  const childId = parseInt(document.getElementById('grade-child-id').value);
  if (!childId || !gradeRows[childId]) return;
  gradeRows[childId].mention = document.getElementById('grade-mention').value;
  gradeRows[childId].appreciation = document.getElementById('grade-appreciation').value;
  gradeRows[childId].absences_count = parseInt(document.getElementById('grade-absences').value) || 0;
  gradeRows[childId].surah_memorized_count = parseInt(document.getElementById('grade-surahs').value) || 0;

  // Mettre à jour la ligne du tableau
  const row = document.getElementById('grade-row-' + childId);
  if (row) {
    row.querySelector('select').value = gradeRows[childId].mention;
    row.querySelector('input[type=text], input:not([type])').value = gradeRows[childId].appreciation;
    const nums = row.querySelectorAll('input[type=number]');
    if (nums[0]) nums[0].value = gradeRows[childId].absences_count;
    if (nums[1]) nums[1].value = gradeRows[childId].surah_memorized_count;
  }
  closeModal('modal-grade');
  showToast('Appréciation mise à jour — pensez à enregistrer tout', 'info');
}

// ── Créer une nouvelle période ──────────────────────────────────────────────

function openPeriodModal(period = null) {
  document.getElementById('period-id').value = period?.id || '';
  document.getElementById('period-name').value = period?.name || '';
  document.getElementById('period-start').value = period?.start_date || '';
  document.getElementById('period-end').value = period?.end_date || '';
  document.getElementById('period-order').value = period?.order || 1;
  document.getElementById('modal-period-title').textContent = period ? 'Modifier période' : 'Nouvelle période';
  openModal('modal-period');
}

async function savePeriod() {
  const id = document.getElementById('period-id').value;
  const name = document.getElementById('period-name').value.trim();
  const start = document.getElementById('period-start').value;
  const end = document.getElementById('period-end').value;
  const order = parseInt(document.getElementById('period-order').value) || 1;

  if (!name || !start || !end) return showToast('Nom, début et fin obligatoires', 'warning');

  // Get active school year
  let schoolYearId = null;
  try {
    const yData = await api('/school/years/?is_active=true');
    const years = yData.results || yData;
    if (years.length) schoolYearId = years[0].id;
  } catch(e) {}

  if (!schoolYearId) return showToast('Aucune année scolaire active', 'error');

  const payload = { name, start_date: start, end_date: end, order, school_year: schoolYearId };
  try {
    showProgress();
    if (id) {
      await api(`/school/periods/${id}/`, 'PATCH', payload);
      showToast('Période modifiée', 'success');
    } else {
      await api('/school/periods/', 'POST', payload);
      showToast('Période créée', 'success');
    }
    closeModal('modal-period');
    await loadPeriods();
  } catch(e) {
    showToast('Erreur: ' + e.message, 'error');
  } finally {
    hideProgress();
  }
}

async function publishPeriod() {
  if (!currentPeriodId) return;
  const period = allPeriods.find(p => p.id == currentPeriodId);
  const ok = await confirmAction(
    'Publier les bulletins',
    `Publier les bulletins de "${period?.name}" ? Les familles pourront les consulter.`,
    '📢'
  );
  if (!ok) return;
  try {
    await api(`/school/periods/${currentPeriodId}/publish/`, 'POST');
    showToast('Bulletins publiés ✅', 'success');
    document.getElementById('btn-publish-period').style.display = 'none';
    await loadPeriods();
    onPeriodChange();
  } catch(e) {
    showToast('Erreur: ' + e.message, 'error');
  }
}
"""

# Append JS at end of file
js += JS_APPRECIATIONS

with open('/home/mosquee/nidham-dev/frontend/js/ecole.js', 'w') as f:
    f.write(js)

print(f"✅ ecole.js: {len(js)} chars")

# ── Patch showTab pour charger les périodes au switch ──────────────────────
# On modifie showTab dans ecole.js pour appeler loadPeriods() quand on switch vers appreciations
with open('/home/mosquee/nidham-dev/frontend/js/ecole.js', 'r') as f:
    js2 = f.read()

OLD_SHOW_TAB = "function showTab(name) {"
NEW_SHOW_TAB = """function showTab(name) {
  if (name === 'appreciations') { loadPeriods(); }"""

if OLD_SHOW_TAB in js2:
    js2 = js2.replace(OLD_SHOW_TAB, NEW_SHOW_TAB, 1)
    print("✅ showTab patch OK")
else:
    print("⚠️  showTab not found — appending loadPeriods call")

with open('/home/mosquee/nidham-dev/frontend/js/ecole.js', 'w') as f:
    f.write(js2)

print("✅ DONE")
