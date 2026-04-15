/* ═══════════════════════════════════════════════════════════
   ecole.js — Interface École coranique v2
   Tabs: Classes | Appel | Suivi Coran | Absences | Historique
═══════════════════════════════════════════════════════════ */

/* ── État global ────────────────────────────────────────── */
let currentUser    = null;
let myClasses      = [];   // classes du prof (ou toutes si admin)
let allChildren    = [];
let allTeachers    = [];
let selectedClassId = null;  // classe ouverte dans le pane classes
let appelSessionId  = null;  // session en cours d'appel
let appelAttendance = {};    // {child_id: 'present'|'absent'|'late'}
let coranChildId    = null;

/* ── INIT & AUTH ─────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const storedToken = localStorage.getItem('access');
  if (storedToken) {
    accessToken = storedToken;
    initApp();
  }
  // Date appel = aujourd'hui
  document.getElementById('appel-date').value = new Date().toISOString().slice(0,10);
});

async function doLogin() {
  const username = document.getElementById('login-user').value.trim();
  const password = document.getElementById('login-pass').value;
  const errEl    = document.getElementById('login-error');
  errEl.classList.add('hidden');
  if (!username || !password) { errEl.textContent = 'Remplissez tous les champs.'; errEl.classList.remove('hidden'); return; }
  const res = await fetch(`${API}/auth/login/`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({username, password}),
  });
  if (!res.ok) { errEl.textContent = 'Identifiants incorrects.'; errEl.classList.remove('hidden'); return; }
  const data = await res.json();
  accessToken  = data.access;
  refreshToken = data.refresh;
  localStorage.setItem('access',  accessToken);
  localStorage.setItem('refresh', refreshToken);
  initApp();
}

async function initApp() {
  // Charger profil
  const res = await apiFetch('/school/teacher/me/');
  if (!res || !res.ok) { logout(); return; }
  const data = await res.json();
  currentUser = data.user;
  myClasses   = data.assigned_classes || [];

  // Mettre à jour le header sidebar
  document.getElementById('user-name').textContent   = currentUser.full_name || currentUser.username;
  document.getElementById('user-role').textContent   = currentUser.role === 'TEACHER' ? 'Professeur' : currentUser.role;
  document.getElementById('user-avatar').textContent = (currentUser.full_name || currentUser.username).charAt(0).toUpperCase();

  // Masquer bouton "Nouvelle classe" pour les profs
  if (currentUser.role === 'TEACHER') {
    document.getElementById('btn-add-class').classList.add('hidden');
  }

  // Basculer vers l'app
  document.getElementById('login-screen').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');

  // Peupler les selects de classes
  populateClassSelects();

  // Charger données initiales
  loadClasses();
  loadTeachers();
}

function logout() {
  accessToken = refreshToken = '';
  localStorage.removeItem('access');
  localStorage.removeItem('refresh');
  document.getElementById('app').classList.add('hidden');
  document.getElementById('login-screen').classList.remove('hidden');
}

/* ── NAVIGATION ──────────────────────────────────────────── */
function showTab(tab) {
  if (tab === 'appreciations') { loadPeriods(); }
  document.querySelectorAll('.ecole-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`pane-${tab}`).classList.add('active');
  document.getElementById(`nav-${tab}`).classList.add('active');

  // Actions au switch d'onglet
  if (tab === 'absences')     loadAbsenceStats();
  if (tab === 'sessions-hist') loadSessionsHistory();
}

/* ── POPULATOR SELECTS ───────────────────────────────────── */
function populateClassSelects() {
  const classes = myClasses.length > 0 ? myClasses : [];
  ['appel-class-select','coran-class-select','abs-class-select','hist-class-select'].forEach(id => {
    const el = document.getElementById(id);
    // Garder l'option vide initiale
    el.innerHTML = `<option value="">— Choisir —</option>`;
    classes.forEach(c => {
      el.innerHTML += `<option value="${c.id}">${esc(c.name)}</option>`;
    });
  });
}

/* ═══════════════════════════════════════════════════════════
   ONGLET CLASSES
═══════════════════════════════════════════════════════════ */
async function loadClasses() {
  const container = document.getElementById('class-cards-container');
  container.innerHTML = '<div class="class-card"><div class="skel skel-xl" style="height:120px"></div></div>'.repeat(3);

  const res = await apiFetch('/school/classes/');
  if (!res || !res.ok) return;
  const data = await res.json();
  const classes = data.results || data;
  myClasses = classes;
  populateClassSelects();

  if (!classes.length) {
    container.innerHTML = `<div style="grid-column:1/-1"><div class="empty-state">
      <div class="empty-state-icon">🏫</div>
      <div class="empty-state-title">Aucune classe</div>
      <div class="empty-state-sub">Commencez par créer la première classe.</div>
      <button class="btn btn-primary" onclick="openClassModal()">+ Nouvelle classe</button>
    </div></div>`;
    return;
  }

  container.innerHTML = classes.map(c => `
    <div class="class-card" onclick="openClassStudents(${c.id}, '${esc(c.name)}')" id="class-card-${c.id}">
      <div class="class-card-header">
        <div class="class-badge">🏫</div>
        <div>
          <div class="class-card-name">${esc(c.name)}</div>
          <div class="class-card-meta">Niv. ${esc(c.level_code)} · ${esc(c.room || '—')} · ${esc(c.schedule_notes || '—')}</div>
        </div>
      </div>
      <div class="class-card-stats">
        <div class="class-stat"><div class="class-stat-val">${c.student_count}</div><div class="class-stat-lbl">Élèves</div></div>
        ${c.teacher_name ? `<div class="class-stat"><div class="class-stat-val" style="font-size:.85rem">${esc(c.teacher_name)}</div><div class="class-stat-lbl">Professeur</div></div>` : ''}
      </div>
      ${currentUser && currentUser.role !== 'TEACHER' ? `
      <div style="display:flex;gap:8px;margin-top:12px" onclick="event.stopPropagation()">
        <button class="btn btn-sm" onclick="editClass(${c.id})">✏️ Modifier</button>
        <button class="btn btn-danger btn-sm" onclick="deleteClass(${c.id})">🗑</button>
      </div>` : ''}
    </div>
  `).join('');
}

async function loadTeachers() {
  const res = await apiFetch('/users/?role=TEACHER');
  if (!res || !res.ok) return;
  const data = await res.json();
  allTeachers = data.results || data;
  const sel = document.getElementById('class-teacher');
  if (sel) {
    sel.innerHTML = '<option value="">— Aucun —</option>';
    allTeachers.forEach(u => { sel.innerHTML += `<option value="${u.id}">${esc(u.full_name || u.username)}</option>`; });
  }
}

function openClassModal(id = null) {
  document.getElementById('class-id').value       = '';
  document.getElementById('class-name').value     = '';
  document.getElementById('class-level').value    = 'NP';
  document.getElementById('class-room').value     = '';
  document.getElementById('class-notes').value    = '';
  document.getElementById('class-teacher').value  = '';
  document.getElementById('modal-class-title').textContent = 'Nouvelle classe';
  document.getElementById('modal-class-error').classList.add('hidden');
  openModal('modal-class');
}

async function editClass(id) {
  const res = await apiFetch(`/school/classes/${id}/`);
  if (!res || !res.ok) return;
  const c = await res.json();
  document.getElementById('class-id').value       = c.id;
  document.getElementById('class-name').value     = c.name;
  document.getElementById('class-level').value    = c.level_code;
  document.getElementById('class-room').value     = c.room || '';
  document.getElementById('class-notes').value    = c.schedule_notes || '';
  document.getElementById('class-teacher').value  = c.teacher || '';
  document.getElementById('modal-class-title').textContent = 'Modifier la classe';
  document.getElementById('modal-class-error').classList.add('hidden');
  openModal('modal-class');
}

async function saveClass() {
  const id   = document.getElementById('class-id').value;
  const body = {
    name:           document.getElementById('class-name').value.trim(),
    level_code:     document.getElementById('class-level').value,
    room:           document.getElementById('class-room').value.trim(),
    schedule_notes: document.getElementById('class-notes').value.trim(),
    teacher:        document.getElementById('class-teacher').value || null,
  };
  if (!body.name) { showModalError('modal-class-error', 'Le nom est requis.'); return; }
  const method = id ? 'PUT' : 'POST';
  const path   = id ? `/school/classes/${id}/` : '/school/classes/';
  const res = await apiFetch(path, method, body);
  if (!res || !res.ok) { const err = await res.json().catch(() => ({})); showModalError('modal-class-error', err.detail || JSON.stringify(err)); return; }
  closeModal('modal-class');
  toast(id ? 'Classe modifiée ✅' : 'Classe créée ✅');
  loadClasses();
}

async function deleteClass(id) {
  const ok = await confirmDialog({ title: 'Supprimer la classe ?', msg: 'Cette action est irréversible.', icon: '🗑️', okLabel: 'Supprimer' });
  if (!ok) return;
  const res = await apiFetch(`/school/classes/${id}/`, 'DELETE');
  if (!res || (res.status !== 204 && res.status !== 200)) { toast('Erreur lors de la suppression.', 'error'); return; }
  toast('Classe supprimée.');
  loadClasses();
}

async function openClassStudents(classId, className) {
  selectedClassId = classId;
  document.getElementById('class-students-title').textContent = `👩‍🎓 Élèves — ${className}`;
  document.getElementById('class-students-panel').classList.remove('hidden');

  const tbody = document.getElementById('class-students-table');
  tbody.innerHTML = skeletonRows(4, 6);

  const res = await apiFetch(`/school/teacher/my-class/?class_id=${classId}`);
  if (!res || !res.ok) return;
  const data = await res.json();
  const classes = data.classes || [];
  const cls = classes.find(c => c.class_id === classId) || classes[0];
  const students = cls ? cls.students : [];

  if (!students.length) {
    tbody.innerHTML = emptyState({ icon: '👶', title: 'Aucun élève inscrit', actionLabel: '+ Inscrire', actionFn: 'openEnrollModal()' });
    return;
  }

  tbody.innerHTML = students.map(s => {
    const absRate = s.absences_count || 0;
    return `<tr>
      <td><strong>${esc(s.child_name)}</strong></td>
      <td>${esc(s.family_name)}</td>
      <td>${s.birth_date ? calcAge(s.birth_date) + ' ans' : '—'}</td>
      <td><span class="badge badge-purple">📖 ${s.quran_memorized} sourate(s)</span></td>
      <td><span class="badge ${absRate > 3 ? 'badge-red' : 'badge-green'}">${absRate} absence(s)</span></td>
      <td><div class="td-actions">
        <button class="btn btn-sm btn-icon" onclick="openCoranForChild(${classId}, ${s.child_id})" title="Suivi Coran">📖</button>
        <button class="btn btn-sm btn-icon" onclick="openAbsencesForChild(${s.child_id})" title="Absences">📊</button>
        <button class="btn btn-danger btn-sm btn-icon" onclick="unenrollChild(${selectedClassId}, ${s.child_id})" title="Désinscrire">🗑</button>
      </div></td>
    </tr>`;
  }).join('');
}

function calcAge(birthDate) {
  const diff = Date.now() - new Date(birthDate).getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24 * 365.25));
}

/* Inscription */
async function openEnrollModal() {
  const res = await apiFetch('/school/children/');
  if (!res || !res.ok) return;
  const data = await res.json();
  const children = data.results || data;
  const sel = document.getElementById('enroll-child');
  sel.innerHTML = '<option value="">— Choisir —</option>';
  children.forEach(c => { sel.innerHTML += `<option value="${c.id}">${esc(c.first_name)} (${esc(c.family_name || '')})</option>`; });
  document.getElementById('modal-enroll-error').classList.add('hidden');
  openModal('modal-enroll');
}

async function saveEnrollment() {
  const childId = document.getElementById('enroll-child').value;
  if (!childId) { showModalError('modal-enroll-error', 'Choisissez un élève.'); return; }
  const res = await apiFetch(`/school/classes/${selectedClassId}/enroll/`, 'POST', { child: childId });
  if (!res || !res.ok) { const err = await res.json().catch(() => ({})); showModalError('modal-enroll-error', err.detail || 'Erreur'); return; }
  closeModal('modal-enroll');
  toast('Élève inscrit ✅');
  openClassStudents(selectedClassId, document.getElementById('class-students-title').textContent.replace('👩‍🎓 Élèves — ',''));
}

async function unenrollChild(classId, childId) {
  const ok = await confirmDialog({ title: 'Désinscrire ?', msg: 'L\'élève sera retiré de la classe.', icon: '🗑️', okLabel: 'Désinscrire' });
  if (!ok) return;
  const res = await apiFetch(`/school/classes/${classId}/enroll/${childId}/`, 'DELETE');
  if (!res || (res.status !== 204 && res.status !== 200)) { toast('Erreur', 'error'); return; }
  toast('Désinscrit.');
  openClassStudents(selectedClassId, document.getElementById('class-students-title').textContent.replace('👩‍🎓 Élèves — ', ''));
}

/* ═══════════════════════════════════════════════════════════
   ONGLET APPEL
═══════════════════════════════════════════════════════════ */
function onAppelClassChange() {
  document.getElementById('appel-session-info').classList.add('hidden');
  appelSessionId = null;
  appelAttendance = {};
}

async function loadOrCreateSession() {
  const classId  = document.getElementById('appel-class-select').value;
  const date     = document.getElementById('appel-date').value;
  const sessType = document.getElementById('appel-type').value;
  if (!classId || !date) { toast('Choisissez une classe et une date.', 'info'); return; }

  // Tenter de récupérer une session existante (GET sessions?class_id=X)
  let session = null;
  const listRes = await apiFetch(`/school/teacher/sessions/?class_id=${classId}`);
  if (listRes && listRes.ok) {
    const sessions = await listRes.json();
    session = (sessions.results || sessions).find(s => s.date === date);
  }

  if (!session) {
    // Créer nouvelle session
    const createRes = await apiFetch('/school/teacher/sessions/', 'POST', {
      school_class: parseInt(classId),
      date, session_type: sessType,
    });
    if (!createRes || !createRes.ok) {
      // Si doublon → récupérer l'id retourné
      const errData = await createRes.json().catch(() => ({}));
      if (errData.session_id) {
        appelSessionId = errData.session_id;
      } else {
        toast(errData.error || 'Erreur création séance', 'error'); return;
      }
    } else {
      const newSession = await createRes.json();
      appelSessionId = newSession.id;
    }
  } else {
    appelSessionId = session.id;
  }

  // Charger le détail (présences)
  const detailRes = await apiFetch(`/school/teacher/sessions/${appelSessionId}/`);
  if (!detailRes || !detailRes.ok) { toast('Erreur chargement séance', 'error'); return; }
  const detail = await detailRes.json();
  renderAppel(detail);
}

function renderAppel(detail) {
  const alertEl = document.getElementById('appel-session-alert');
  alertEl.className = 'alert alert-info';
  alertEl.textContent = `Séance du ${detail.date} — ${detail.class_name} — ${detail.present_count} présent(s) / ${detail.absent_count} absent(s)`;

  const attendances = detail.attendances || [];
  appelAttendance = {};
  attendances.forEach(a => { appelAttendance[a.child] = a.status; });

  const listEl = document.getElementById('appel-students-list');
  if (!attendances.length) {
    listEl.innerHTML = '<p style="color:var(--muted);text-align:center;padding:20px">Aucun élève dans cette classe.</p>';
  } else {
    listEl.innerHTML = attendances.map(a => `
      <div class="appel-student-row" id="appel-row-${a.child}">
        <div>
          <div class="appel-student-name">${esc(a.child_name)}</div>
          <div class="appel-student-meta">Statut actuel : <strong>${statusLabel(a.status)}</strong></div>
        </div>
        <div class="appel-btns">
          <button class="appel-btn present ${a.status==='present'?'active':''}" onclick="setAttendance(${a.child},'present')">✅ Présent</button>
          <button class="appel-btn late   ${a.status==='late'?'active':''}"    onclick="setAttendance(${a.child},'late')">⏰ Retard</button>
          <button class="appel-btn absent ${a.status==='absent'?'active':''}"  onclick="setAttendance(${a.child},'absent')">❌ Absent</button>
        </div>
      </div>
    `).join('');
  }

  document.getElementById('appel-summary').classList.add('hidden');
  document.getElementById('appel-session-info').classList.remove('hidden');
}

function statusLabel(s) {
  return s === 'present' ? 'Présent' : s === 'absent' ? 'Absent' : s === 'late' ? 'Retard' : s;
}

function setAttendance(childId, status) {
  appelAttendance[childId] = status;
  const row = document.getElementById(`appel-row-${childId}`);
  row.querySelectorAll('.appel-btn').forEach(b => b.classList.remove('active'));
  row.querySelector(`.appel-btn.${status}`).classList.add('active');
  row.querySelector('.appel-student-meta').innerHTML = `Statut actuel : <strong>${statusLabel(status)}</strong>`;
}

function markAll(status) {
  Object.keys(appelAttendance).forEach(id => setAttendance(parseInt(id), status));
}

async function submitAppel() {
  if (!appelSessionId) { toast('Aucune séance en cours.', 'error'); return; }
  const attendances = Object.entries(appelAttendance).map(([child_id, status]) => ({
    child_id: parseInt(child_id), status,
  }));
  const res = await apiFetch(`/school/teacher/sessions/${appelSessionId}/submit/`, 'POST', { attendances });
  if (!res || !res.ok) { const err = await res.json().catch(() => ({})); toast(err.detail || 'Erreur envoi appel', 'error'); return; }
  const result = await res.json();

  const present = attendances.filter(a => a.status === 'present').length;
  const absent  = attendances.filter(a => a.status === 'absent').length;
  const late    = attendances.filter(a => a.status === 'late').length;

  const summaryEl = document.getElementById('appel-summary');
  summaryEl.innerHTML = `
    <div class="alert" style="background:var(--green-soft);border-color:var(--green);color:var(--green)">
      ✅ Appel validé !
      <strong>${present} présent(s)</strong> · <strong>${absent} absent(s)</strong> · <strong>${late} retard(s)</strong>
    </div>`;
  summaryEl.classList.remove('hidden');
  toast('Appel validé ✅');
}

/* ═══════════════════════════════════════════════════════════
   ONGLET SUIVI CORAN
═══════════════════════════════════════════════════════════ */
async function loadCoranStudents() {
  const classId = document.getElementById('coran-class-select').value;
  const sel = document.getElementById('coran-child-select');
  sel.innerHTML = '<option value="">— Choisir —</option>';
  document.getElementById('coran-panel').classList.add('hidden');
  if (!classId) return;

  const res = await apiFetch(`/school/teacher/my-class/?class_id=${classId}`);
  if (!res || !res.ok) return;
  const data  = await res.json();
  const cls   = (data.classes || []).find(c => c.class_id == classId) || (data.classes || [])[0];
  if (!cls) return;
  cls.students.forEach(s => { sel.innerHTML += `<option value="${s.child_id}">${esc(s.child_name)}</option>`; });
}

async function loadChildQuran() {
  const childId = document.getElementById('coran-child-select').value;
  if (!childId) { document.getElementById('coran-panel').classList.add('hidden'); return; }
  coranChildId = childId;

  const res = await apiFetch(`/school/teacher/children/${childId}/quran/`);
  if (!res || !res.ok) return;
  const data = await res.json();
  renderCoran(data);
}

function renderCoran(data) {
  const memorized   = data.total_memorized || 0;
  const inProgress  = data.total_in_progress || 0;
  const notStarted  = 114 - memorized - inProgress;
  const pct         = Math.round((memorized / 114) * 100);

  document.getElementById('coran-memorized').textContent   = memorized;
  document.getElementById('coran-in-progress').textContent = inProgress;
  document.getElementById('coran-not-started').textContent = notStarted;
  document.getElementById('coran-pct').textContent         = pct + '%';
  document.getElementById('coran-progress-fill').style.width = pct + '%';

  const grid = document.getElementById('coran-surahs-grid');
  grid.innerHTML = data.surahs.map(s => `
    <div class="surah-chip ${s.status}" onclick="openSurahModal(${coranChildId}, ${s.surah_number}, '${esc(s.surah_name)}', '${s.status}', '${esc(s.notes||'')}')">
      <span class="surah-num">${s.surah_number}</span>
      <span class="surah-dot"></span>
      <span>${esc(s.surah_name)}</span>
      ${s.status === 'memorized' ? '<span style="margin-left:auto;font-size:.7rem">✅</span>' : ''}
      ${s.status === 'in_progress' ? '<span style="margin-left:auto;font-size:.7rem">⏳</span>' : ''}
    </div>
  `).join('');

  document.getElementById('coran-panel').classList.remove('hidden');
}

function openCoranForChild(classId, childId) {
  document.getElementById('coran-class-select').value = classId;
  loadCoranStudents().then(() => {
    document.getElementById('coran-child-select').value = childId;
    loadChildQuran();
    showTab('coran');
  });
}

function openSurahModal(childId, surahNum, surahName, status, notes) {
  document.getElementById('surah-child-id').value  = childId;
  document.getElementById('surah-number').value    = surahNum;
  document.getElementById('surah-status').value    = status;
  document.getElementById('surah-notes').value     = notes;
  document.getElementById('modal-surah-title').textContent = `Sourate ${surahNum} — ${surahName}`;
  openModal('modal-surah');
}

async function saveSurah() {
  const childId   = document.getElementById('surah-child-id').value;
  const surahNum  = document.getElementById('surah-number').value;
  const status    = document.getElementById('surah-status').value;
  const notes     = document.getElementById('surah-notes').value.trim();
  const res = await apiFetch(`/school/teacher/children/${childId}/quran/${surahNum}/`, 'PUT', { status, notes });
  if (!res || !res.ok) { toast('Erreur enregistrement', 'error'); return; }
  closeModal('modal-surah');
  toast('Sourate mise à jour ✅');
  loadChildQuran();
}

/* ═══════════════════════════════════════════════════════════
   ONGLET ABSENCES
═══════════════════════════════════════════════════════════ */
async function loadAbsenceStats() {
  const classId = document.getElementById('abs-class-select').value;
  const listEl  = document.getElementById('abs-list');
  listEl.innerHTML = '<div class="skel skel-xl" style="height:60px;border-radius:8px;margin-bottom:8px"></div>'.repeat(4);

  // Récupérer la liste des élèves
  const classParam = classId ? `?class_id=${classId}` : '';
  const res = await apiFetch(`/school/teacher/my-class/${classParam}`);
  if (!res || !res.ok) { listEl.innerHTML = '<p style="color:var(--muted)">Choisissez une classe.</p>'; return; }
  const data    = await res.json();
  const classes = data.classes || [];

  let rows = '';
  for (const cls of classes) {
    if (classId && cls.class_id != classId) continue;
    for (const s of cls.students) {
      const rate    = s.absences_count || 0;
      const total   = 10; // on normalise sur 10 séances (approx)
      const pct     = Math.min(100, Math.round((rate / total) * 100));
      const danger  = rate >= 4 ? 'danger' : rate >= 2 ? 'warning' : '';
      rows += `
        <div style="background:var(--surface);border:1.5px solid var(--border);border-radius:var(--radius);padding:14px 18px;margin-bottom:10px;display:flex;align-items:center;gap:16px;flex-wrap:wrap">
          <div style="flex:1;min-width:140px">
            <div style="font-weight:600">${esc(s.child_name)}</div>
            <div style="font-size:.76rem;color:var(--muted)">${esc(cls.class_name)}</div>
          </div>
          <div style="flex:2;min-width:160px">
            <div class="absence-bar"><div class="absence-fill ${danger}" style="width:${pct}%"></div></div>
            <div style="font-size:.74rem;color:var(--muted);margin-top:4px">${rate} absence(s)</div>
          </div>
          <button class="btn btn-sm" onclick="openAbsencesForChild(${s.child_id})">�� Détail</button>
        </div>`;
    }
  }
  listEl.innerHTML = rows || '<p style="color:var(--muted)">Aucun élève.</p>';
}

async function openAbsencesForChild(childId) {
  const res = await apiFetch(`/school/teacher/children/${childId}/absences/`);
  if (!res || !res.ok) return;
  const data  = await res.json();
  const stats = data.stats;
  const modal = document.getElementById('modal-session-detail');
  document.getElementById('modal-session-title').textContent = `📊 Absences — ${data.child_name}`;
  document.getElementById('modal-session-body').innerHTML = `
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">
      <div class="coran-stat"><div class="coran-stat-val" style="color:var(--accent)">${stats.total_sessions}</div><div class="coran-stat-lbl">Séances</div></div>
      <div class="coran-stat"><div class="coran-stat-val" style="color:var(--green)">${stats.present}</div><div class="coran-stat-lbl">Présences</div></div>
      <div class="coran-stat"><div class="coran-stat-val" style="color:var(--red)">${stats.absent}</div><div class="coran-stat-lbl">Absences</div></div>
      <div class="coran-stat"><div class="coran-stat-val" style="color:#f59e0b">${stats.late}</div><div class="coran-stat-lbl">Retards</div></div>
      <div class="coran-stat"><div class="coran-stat-val" style="color:var(--accent)">${stats.attendance_rate}%</div><div class="coran-stat-lbl">Taux</div></div>
    </div>
    ${data.recent_absences && data.recent_absences.length ? `
      <h4 style="margin-bottom:10px">Absences récentes</h4>
      ${data.recent_absences.map(a => `<div style="padding:8px 12px;background:var(--red-soft);border-radius:8px;margin-bottom:6px;font-size:.85rem">
        📅 ${a.date} — ${esc(a.class_name || '')} <span style="color:var(--red);font-weight:600">${a.status === 'absent' ? '❌ Absent' : '⏰ Retard'}</span>
      </div>`).join('')}
    ` : '<p style="color:var(--muted)">Aucune absence récente.</p>'}
  `;
  openModal('modal-session-detail');
}

/* ═══════════════════════════════════════════════════════════
   ONGLET HISTORIQUE
═══════════════════════════════════════════════════════════ */
async function loadSessionsHistory() {
  const classId = document.getElementById('hist-class-select').value;
  const tbody   = document.getElementById('hist-sessions-table');
  tbody.innerHTML = skeletonRows(5, 6);

  const url = classId ? `/school/teacher/sessions/?class_id=${classId}` : '/school/teacher/sessions/';
  const res = await apiFetch(url);
  if (!res || !res.ok) return;
  const data = await res.json();
  const sessions = data.results || data;

  if (!sessions.length) {
    tbody.innerHTML = emptyState({ icon: '🗓️', title: 'Aucune séance' });
    return;
  }

  const typeLabels = { arabic:'Arabe', quran:'Coran', both:'Arabe + Coran', other:'Autre' };
  tbody.innerHTML = sessions.map(s => `
    <tr>
      <td>${s.date}</td>
      <td><strong>${esc(s.class_name)}</strong></td>
      <td><span class="badge badge-gray">${typeLabels[s.session_type] || s.session_type || '—'}</span></td>
      <td><span class="badge badge-green">${s.present_count} ✅</span></td>
      <td><span class="badge badge-red">${s.absent_count} ❌</span></td>
      <td><button class="btn btn-sm btn-icon" onclick="showSessionDetail(${s.id})" title="Voir détail">🔍</button></td>
    </tr>
  `).join('');
}

async function showSessionDetail(sessionId) {
  const res = await apiFetch(`/school/teacher/sessions/${sessionId}/`);
  if (!res || !res.ok) return;
  const d = await res.json();
  document.getElementById('modal-session-title').textContent = `Séance du ${d.date} — ${d.class_name}`;
  document.getElementById('modal-session-body').innerHTML = `
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">
      <span class="badge badge-green">${d.present_count} présent(s)</span>
      <span class="badge badge-red">${d.absent_count} absent(s)</span>
    </div>
    <div style="display:flex;flex-direction:column;gap:6px">
      ${(d.attendances || []).map(a => `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 14px;background:${a.status==='present'?'var(--green-soft)':a.status==='absent'?'var(--red-soft)':'#fef9c3'};border-radius:8px">
          <span style="font-weight:600">${esc(a.child_name)}</span>
          <span>${a.status === 'present' ? '✅ Présent' : a.status === 'absent' ? '❌ Absent' : '⏰ Retard'}</span>
        </div>`).join('')}
    </div>`;
  openModal('modal-session-detail');
}

/* ── Helpers ─────────────────────────────────────────────── */
function showModalError(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.remove('hidden');
}


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
