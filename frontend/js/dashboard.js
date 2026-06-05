import { api } from './api.js';
import { auth } from './auth.js';
import { connectLive } from './live.js';
import { renderSubmittedForm } from './form-render.js';

let currentUser = null;

// ── Init ──────────────────────────────────────────────────────────────────
async function init() {
  if (!auth.isAuthenticated()) {
    auth.clearToken();
    window.location.href = 'login.html';
    return;
  }

  const user = auth.getUser(); // non-null guaranteed by isAuthenticated()

  // Route non-end_users to their own pages
  if (user.role === 'admin' || user.role === 'super_admin') {
    window.location.href = 'admin.html';
    return;
  }
  if (user.role === 'staff') {
    window.location.href = 'staff.html';
    return;
  }

  currentUser = user;

  const sidebarUser = document.getElementById('sidebar-user');
  if (sidebarUser) sidebarUser.textContent = auth.getDisplayName();

  // Account section — populated from JWT (no API call needed)
  set('acct-email', user.email || '—');
  set('acct-name', (user.full_name || '').trim() || '—');
  set('acct-role', user.role || '—');

  setupSectionSwitcher();
  switchSection('submissions');

  // Live updates — reflect workflow progress on the submitter's tracker.
  connectLive({
    'submission.updated': () => loadSubmissions(),
    'notification.new': () => loadSubmissions(),
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
  if (name === 'submissions') loadSubmissions();
}

// ── Submissions ────────────────────────────────────────────────────────────
window.loadSubmissions = loadSubmissions;

async function loadSubmissions() {
  const container = document.getElementById('submissions-list');
  container.innerHTML = '<p class="pk-empty">Loading…</p>';
  try {
    const res = await api.submissions.list();
    const list = res?.data ?? (Array.isArray(res) ? res : []);
    if (list.length === 0) {
      container.innerHTML = '<p class="pk-empty">No submissions yet. Scan a QR code to fill and submit a form.</p>';
      return;
    }
    container.innerHTML = list.map(sub => submissionRow(sub)).join('');
    lucide.createIcons();
  } catch {
    container.innerHTML = '<p class="pk-empty" style="color:var(--accent-error)">Failed to load submissions.</p>';
  }
}

function submissionStatusBadge(status) {
  const map = {
    SUBMITTED:  'pk-badge-info',
    COMPLETED:  'pk-badge-success',
    STEP_1:     'pk-badge-warning',
    STEP_2:     'pk-badge-warning',
    STEP_3:     'pk-badge-warning',
    STEP_4:     'pk-badge-warning',
  };
  return `<span class="pk-badge ${map[status] ?? 'pk-badge-neutral'}">${status ?? 'UNKNOWN'}</span>`;
}

function submissionRow(sub) {
  const id  = sub.submission_id ?? sub.id ?? '';
  const ref = id.substring(0, 8).toUpperCase();
  const date = sub.created_at ? new Date(sub.created_at).toLocaleDateString() : '—';
  return `
    <div class="pk-list-item" style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap">
      <div>
        <p class="t-body" style="color:var(--text-primary);font-weight:600">Ref: ${ref}</p>
        <p class="t-caption" style="color:var(--text-muted)">${date}</p>
      </div>
      <div class="flex items-center gap-3" style="flex-shrink:0">
        ${submissionStatusBadge(sub.status)}
        <button onclick="viewSubmission('${id}')" class="pk-btn-link">Details</button>
      </div>
    </div>`;
}

window.viewSubmission = async (submissionId) => {
  const panel   = document.getElementById('sub-detail-panel');
  const content = document.getElementById('sub-detail-content');
  content.innerHTML = '<p class="pk-empty">Loading…</p>';
  panel.classList.remove('hidden');
  panel.scrollIntoView({ behavior: 'smooth' });

  try {
    const [statusRes, historyRes] = await Promise.all([
      api.submissions.status(submissionId),
      api.submissions.history(submissionId)
    ]);

    const status      = statusRes?.data ?? statusRes;
    const historyList = historyRes?.data ?? (Array.isArray(historyRes) ? historyRes : []);
    const badgeClass  = status?.status === 'COMPLETED' ? 'pk-badge-success' : 'pk-badge-info';

    content.innerHTML = `
      <div class="flex gap-4 items-center mb-6 flex-wrap">
        <div>
          <p class="t-caption-strong uppercase" style="color:var(--text-muted)">Reference</p>
          <p class="t-mono" style="color:var(--text-primary)">${submissionId.substring(0, 8).toUpperCase()}</p>
        </div>
        <div>
          <p class="t-caption-strong uppercase" style="color:var(--text-muted)">Status</p>
          <span class="pk-badge ${badgeClass}">${status?.status ?? '—'}</span>
        </div>
      </div>
      <h3 class="t-caption-strong uppercase" style="color:var(--text-muted);letter-spacing:0.05em;margin-bottom:0.75rem">Submitted Form</h3>
      <div id="dash-form-view" class="space-y-4 mb-6"><p class="pk-empty">Loading form…</p></div>
      <h3 class="t-caption-strong uppercase" style="color:var(--text-muted);letter-spacing:0.05em;margin-bottom:0.75rem">Progress</h3>
      <div class="space-y-2">
        ${historyList.length === 0
          ? '<p class="pk-empty">No history yet.</p>'
          : historyList.map(h => `
              <div class="pk-list-item">
                <span class="t-caption" style="color:var(--text-primary)">${h.action ?? '—'}</span>
                <span class="t-caption" style="color:var(--text-muted)">${h.actor_id ?? '—'}</span>
              </div>`).join('')}
      </div>`;

    // Render the full form (read-only) from its schema, pre-filled with values.
    const formView = document.getElementById('dash-form-view');
    await renderSubmittedForm(formView, status, { editable: false });
  } catch {
    content.innerHTML = '<p class="pk-empty" style="color:var(--accent-error)">Could not load submission details.</p>';
  }
};

// ── Utilities ──────────────────────────────────────────────────────────────
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

// Read-only render of a submission's form_data (end users cannot edit).
function readonlyFields(formData) {
  const entries = Object.entries(formData || {});
  if (!entries.length) return '<p class="pk-empty">No fields captured.</p>';
  return entries.map(([k, v]) => {
    const isSig = typeof v === 'string' && v.startsWith('data:image');
    const val = isSig
      ? `<img src="${esc(v)}" alt="signature" style="max-height:80px;border:1px solid var(--border-default);border-radius:8px;background:var(--bg-surface)">`
      : `<span class="t-body" style="color:var(--text-primary)">${esc(v) || '—'}</span>`;
    return `<div class="pk-list-item" style="flex-direction:column;align-items:flex-start;gap:0.25rem">
      <span class="t-caption-strong uppercase" style="color:var(--text-muted)">${esc(k)}</span>
      ${val}
    </div>`;
  }).join('');
}

function set(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = String(val ?? '');
}

init();
