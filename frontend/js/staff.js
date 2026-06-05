import { api } from './api.js';
import { auth } from './auth.js';
import { connectLive } from './live.js';
import { renderSubmittedForm, collectForm } from './form-render.js';

let currentUser = null;

// ── Init ──────────────────────────────────────────────────────────────────
async function init() {
  if (!auth.isAuthenticated()) {
    auth.clearToken();
    window.location.href = 'login.html';
    return;
  }

  const user = auth.getUser(); // non-null guaranteed by isAuthenticated()
  if (user.role !== 'staff') {
    window.location.href = (user.role === 'admin' || user.role === 'super_admin')
      ? 'admin.html'
      : 'dashboard.html';
    return;
  }
  currentUser = user;

  const sidebarUser = document.getElementById('sidebar-user');
  if (sidebarUser) sidebarUser.textContent = auth.getDisplayName();

  // Populate account section eagerly (no API call needed)
  set('acct-email', user.email || '—');
  set('acct-name', (user.full_name || '').trim() || '—');
  set('acct-role', user.role || '—');
  set('acct-actor-type', user.actor_type || '—');

  setupSectionSwitcher();
  switchSection('tasks');

  // Live updates — refresh the inbox the moment a task is routed here.
  connectLive({
    'task.updated': () => window.loadTasks(),
    'notification.new': () => window.loadTasks(),
  });
}

// ── Section switcher ──────────────────────────────────────────────────────
function setupSectionSwitcher() {
  document.querySelectorAll('[data-section]').forEach(btn => {
    btn.addEventListener('click', () => switchSection(btn.dataset.section));
  });
}

function switchSection(name) {
  document.querySelectorAll('.section-content').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('[data-section]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.section === name);
  });
  const target = document.getElementById(`section-${name}`);
  if (target) target.classList.add('active');
  if (name === 'tasks') loadTasks();
}

// ── Tasks ─────────────────────────────────────────────────────────────────
window.loadTasks = async function () {
  const container = document.getElementById('task-list');
  container.innerHTML = '<p class="pk-empty">Loading…</p>';
  try {
    const res = await api.tasks.list();
    const tasks = res?.data ?? (Array.isArray(res) ? res : []);
    renderTasks(tasks);
  } catch {
    container.innerHTML = '<p class="pk-empty" style="color:var(--accent-error)">Failed to load tasks. Try refreshing.</p>';
  }
};

function renderTasks(tasks) {
  const container = document.getElementById('task-list');
  const countEl   = document.getElementById('task-count');
  const pluralEl  = document.getElementById('task-plural');
  const badge     = document.getElementById('task-badge');
  const count     = tasks?.length ?? 0;

  if (countEl) countEl.textContent = count;
  if (pluralEl) pluralEl.textContent = count === 1 ? '' : 's';
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline-flex' : 'none';
  }

  if (count === 0) {
    container.innerHTML = '<p class="pk-empty">No pending tasks — you\'re all caught up.</p>';
    return;
  }

  container.innerHTML = tasks.map(task => `
    <div id="task-${task.id}" class="pk-list-item">
      <div>
        <p class="t-body" style="color:var(--text-primary);font-weight:600">
          Submission <span class="t-mono" style="color:var(--text-muted)">${task.submission_id.substring(0, 8).toUpperCase()}</span>
        </p>
        <p class="t-caption mt-1" style="color:var(--text-muted)">Step: ${task.assigned_role ?? '—'}</p>
      </div>
      <div class="flex gap-3">
        <button onclick="viewDetail('${task.submission_id}')" class="pk-btn-secondary">View</button>
        <button id="done-${task.id}" onclick="markDone('${task.id}')" class="pk-btn-primary">Mark Done</button>
      </div>
    </div>
  `).join('');
}

window.markDone = async function (taskId) {
  const btn = document.getElementById(`done-${taskId}`);
  if (btn) { btn.textContent = 'Processing…'; btn.disabled = true; }
  try {
    await api.tasks.complete(taskId);
    document.getElementById(`task-${taskId}`)?.remove();
    const remaining = document.querySelectorAll('[id^="task-"]').length;
    const countEl  = document.getElementById('task-count');
    const pluralEl = document.getElementById('task-plural');
    const badge    = document.getElementById('task-badge');
    if (countEl) countEl.textContent = remaining;
    if (pluralEl) pluralEl.textContent = remaining === 1 ? '' : 's';
    if (badge) { badge.textContent = remaining; badge.style.display = remaining > 0 ? 'inline-flex' : 'none'; }
    if (remaining === 0) {
      document.getElementById('task-list').innerHTML = '<p class="pk-empty">No pending tasks — you\'re all caught up.</p>';
    }
  } catch {
    if (btn) { btn.textContent = 'Mark Done'; btn.disabled = false; }
    alert('Could not complete task. Please try again.');
  }
};

let detailFormData = {};   // last-loaded form_data for the open submission

window.viewDetail = async function (submissionId) {
  const panel  = document.getElementById('detail-panel');
  const fields = document.getElementById('detail-fields');
  fields.innerHTML = '<p class="pk-empty">Loading…</p>';
  panel.classList.remove('hidden');
  panel.scrollIntoView({ behavior: 'smooth' });

  try {
    const [history, status] = await Promise.all([
      api.submissions.history(submissionId),
      api.submissions.status(submissionId)
    ]);

    const statusClass = status?.status === 'COMPLETED' ? 'pk-badge-success' : 'pk-badge-info';
    const historyItems = Array.isArray(history) ? history : (history?.data ?? []);
    detailFormData = status?.form_data ?? {};

    fields.innerHTML = `
      <div style="display:flex;gap:1rem;align-items:center;margin-bottom:1rem">
        <span class="t-caption-strong" style="color:var(--text-muted)">ID</span>
        <span class="t-mono" style="color:var(--text-primary)">${submissionId}</span>
      </div>
      <div style="display:flex;gap:1rem;align-items:center;margin-bottom:1.5rem">
        <span class="t-caption-strong" style="color:var(--text-muted)">Status</span>
        <span class="pk-badge ${statusClass}">${status?.status ?? '—'}</span>
      </div>
      <div class="flex justify-between items-center mb-3">
        <h3 class="t-caption-strong" style="color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em">Submitted Form</h3>
        <button onclick="saveSubmissionForm('${submissionId}')" class="pk-btn-primary">Save</button>
      </div>
      <div id="detail-form" class="space-y-4 mb-3"><p class="pk-empty">Loading form…</p></div>
      <span id="detail-form-msg" class="t-caption" style="color:var(--text-muted)"></span>
      <h3 class="t-caption-strong" style="color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;margin:1.5rem 0 0.75rem">History</h3>
      <div class="space-y-2">
        ${historyItems.length === 0
          ? '<p class="pk-empty">No history yet.</p>'
          : historyItems.map(h => `
              <div class="pk-list-item">
                <span class="t-caption" style="color:var(--text-primary)">${esc(h.action)}</span>
                <span class="t-caption" style="color:var(--text-muted)">${esc(h.actor_id)}</span>
              </div>`).join('')}
      </div>`;

    // Render the full form (editable) from its schema, pre-filled with values.
    await renderSubmittedForm(document.getElementById('detail-form'), status, { editable: true });
  } catch {
    fields.innerHTML = '<p class="pk-empty">Could not load submission details.</p>';
  }
};

window.saveSubmissionForm = async function (submissionId) {
  const msg = document.getElementById('detail-form-msg');
  // Merge edited values over the loaded data so fields not in the schema
  // (e.g. staff-added keys) survive.
  const updated = { ...detailFormData, ...collectForm(document.getElementById('detail-form')) };
  if (msg) { msg.style.color = 'var(--text-muted)'; msg.textContent = 'Saving…'; }
  try {
    const res = await api.submissions.updateFormData(submissionId, updated);
    detailFormData = res?.form_data ?? updated;
    if (msg) { msg.style.color = 'var(--state-success)'; msg.textContent = 'Saved ✓'; }
  } catch (err) {
    if (msg) { msg.style.color = 'var(--accent-error)'; msg.textContent = 'Save failed: ' + err.message; }
  }
};

// ── Utilities ──────────────────────────────────────────────────────────────
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function set(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

init();
