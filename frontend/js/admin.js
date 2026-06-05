import { api } from './api.js';
import { auth } from './auth.js';
import { connectLive } from './live.js';

let currentUser = null;
let forms = [];
let activeSectionName = 'dashboard';

// ── Init ──────────────────────────────────────────────────────────────────
async function init() {
  if (!auth.isAuthenticated()) {
    auth.clearToken();
    window.location.href = 'login.html';
    return;
  }

  let serverUser;
  try {
    serverUser = await api.auth.me();
  } catch {
    // handleResponse already cleared the token and started navigation to login.html
    // (on 401); for other network errors, go there too
    auth.clearToken();
    window.location.href = 'login.html';
    return;
  }

  // serverUser is null only if the server returned an unexpected empty body
  if (!serverUser) {
    window.location.href = 'login.html';
    return;
  }
  if (!['admin', 'super_admin'].includes(serverUser.role)) {
    window.location.href = 'dashboard.html';
    return;
  }
  // serverUser shape: { user_id, email, role, institution_id, full_name }
  currentUser = serverUser;

  const sidebarUser = document.getElementById('sidebar-user');
  if (sidebarUser) {
    sidebarUser.textContent = (serverUser.full_name || '').trim() || serverUser.email.split('@')[0];
  }

  setupSectionSwitcher();
  setupFormUpload();
  setupDragDrop();
  setupActorTypeForm();
  setupStaffCsvUpload();

  // Honor a deep-link hash (e.g. returning from the workflow builder to #workflows).
  const known = ['dashboard', 'forms', 'workflows', 'actor-types', 'users', 'staff-import', 'notifications'];
  const hash = location.hash.replace('#', '');
  switchSection(known.includes(hash) ? hash : 'dashboard');

  // Live updates — re-render a view only when the backend reports a real change.
  connectLive({
    'form.updated': () => {
      if (activeSectionName === 'forms') loadForms();
      if (activeSectionName === 'dashboard') loadDashboard();
    },
    'workflow.updated': () => {
      if (activeSectionName === 'workflows') loadWorkflows();
      if (activeSectionName === 'dashboard') loadDashboard();
    },
    // loadNotifications refreshes both the list and the sidebar badge.
    'notification.new': () => loadNotifications(),
  });
}

// ── Section switcher ──────────────────────────────────────────────────────
function setupSectionSwitcher() {
  document.querySelectorAll('[data-section]').forEach(btn => {
    btn.addEventListener('click', () => switchSection(btn.dataset.section));
  });
}

function switchSection(name) {
  activeSectionName = name;
  document.querySelectorAll('.section-content').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('[data-section]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.section === name);
  });
  const target = document.getElementById(`section-${name}`);
  if (target) target.classList.add('active');

  if (name === 'dashboard') loadDashboard();
  else if (name === 'forms') loadForms();
  else if (name === 'workflows') loadWorkflows();
  else if (name === 'actor-types') loadActorTypes();
  else if (name === 'users') loadUsers();
  else if (name === 'staff-import') loadStaffRows();
  else if (name === 'notifications') loadNotifications();
}

// exposed so Quick Actions buttons can use it
window.switchToSection = switchSection;

// ── DASHBOARD ─────────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const [formsRes, wfsRes] = await Promise.all([api.forms.list(), api.workflows.list()]);
    const formsList = formsRes?.items ?? formsRes?.data ?? (Array.isArray(formsRes) ? formsRes : []);
    const wfsList   = wfsRes?.items  ?? wfsRes?.data  ?? (Array.isArray(wfsRes)  ? wfsRes  : []);

    set('stat-forms-total',    formsList.length);
    set('stat-forms-published', formsList.filter(f => f.status === 'PUBLISHED').length);
    set('stat-wf-total',       wfsList.length);
    set('stat-wf-active',      wfsList.filter(w => w.status === 'PUBLISHED').length);

    const breakdown = document.getElementById('dash-form-breakdown');
    if (breakdown) {
      const counts = { PROCESSING: 0, READY: 0, CONFIRMED: 0, PUBLISHED: 0, FAILED: 0 };
      formsList.forEach(f => { if (counts[f.status] !== undefined) counts[f.status]++; });
      const badgeMap = {
        PROCESSING: 'pk-badge-pending',
        READY: 'pk-badge-info',
        CONFIRMED: 'pk-badge-info',
        PUBLISHED: 'pk-badge-success',
        FAILED: 'pk-badge-error',
      };
      breakdown.innerHTML = Object.entries(counts).map(([status, count]) => `
        <div class="flex justify-between items-center">
          <span class="pk-badge ${badgeMap[status]}">${status}</span>
          <span class="t-body" style="color:var(--text-primary);font-weight:600">${count}</span>
        </div>`).join('');
    }
  } catch { /* stats are non-critical */ }
}

function set(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── FORMS ─────────────────────────────────────────────────────────────────
window.refreshForms = loadForms;

async function loadForms() {
  const container = document.getElementById('forms-list');
  try {
    const res = await api.forms.list();
    forms = res?.items ?? res?.data ?? (Array.isArray(res) ? res : []);
    if (forms.length === 0) {
      container.innerHTML = '<p class="pk-empty">No forms yet. Upload one to get started.</p>';
      return;
    }
    container.innerHTML = forms.map(f => formRow(f)).join('');
    lucide.createIcons();
  } catch (err) {
    container.innerHTML = '<p class="pk-empty" style="color:var(--accent-error)">Failed to load forms.</p>';
    console.error(err);
  }
}

function formStatusBadge(status) {
  const map = {
    PROCESSING: 'pk-badge-pending',
    READY: 'pk-badge-info',
    CONFIRMED: 'pk-badge-info',
    PUBLISHED: 'pk-badge-success',
    FAILED: 'pk-badge-error',
  };
  return `<span class="pk-badge ${map[status] ?? 'pk-badge-neutral'}">${status ?? 'UNKNOWN'}</span>`;
}

function formRow(f) {
  const id = f.form_id ?? f.id;
  return `
    <div class="pk-list-item" style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap">
      <div>
        <p class="t-body" style="color:var(--text-primary);font-weight:600">${esc(f.name ?? f.original_filename ?? 'Untitled form')}</p>
        <p class="t-caption" style="color:var(--text-muted)">${id}</p>
      </div>
      <div class="flex items-center gap-3" style="flex-shrink:0">
        ${formStatusBadge(f.status)}
        <button onclick="previewForm('${jsStr(id)}')" class="pk-btn-ghost" style="padding:0.375rem" title="Preview uploaded file"><i data-lucide="eye" style="width:16px;height:16px"></i></button>
        <button onclick="showFormDetail('${jsStr(id)}')" class="pk-btn-link">Detail</button>
        ${(f.status === 'READY' || f.status === 'CONFIRMED')
          ? `<button onclick="publishForm('${jsStr(id)}')" class="pk-btn-secondary">Publish</button>`
          : ''}
        ${f.status === 'PUBLISHED'
          ? `<button onclick="showQrModal('${jsStr(id)}')" class="pk-btn-ghost" style="padding:0.375rem"><i data-lucide="qr-code" style="width:16px;height:16px"></i></button>`
          : ''}
        <button onclick="deleteForm('${jsStr(id)}')" class="pk-btn-danger" style="padding:0.375rem">
          <i data-lucide="trash-2" style="width:14px;height:14px"></i>
        </button>
      </div>
    </div>`;
}

window.showFormDetail = async (formId) => {
  const panel = document.getElementById('form-detail-panel');
  const content = document.getElementById('form-detail-content');
  content.innerHTML = '<p class="pk-empty">Loading…</p>';
  panel.classList.remove('hidden');
  panel.scrollIntoView({ behavior: 'smooth' });
  try {
    const res = await api.forms.getSchema(formId);
    const form = res?.data ?? res;
    renderFormDetail(formId, form);
  } catch {
    content.innerHTML = '<p class="pk-empty" style="color:var(--accent-error)">Failed to load form detail.</p>';
  }
};

function renderFormDetail(formId, form) {
  const content = document.getElementById('form-detail-content');
  const fields = form?.fields ?? [];
  content.innerHTML = `
    <div class="mb-6">
      <p class="t-body" style="color:var(--text-primary);font-weight:600">${esc(form?.name ?? '')}</p>
      <p class="t-caption" style="color:var(--text-muted)">${form?.status ?? ''}</p>
    </div>
    <h3 class="t-body mb-3" style="color:var(--text-primary);font-weight:600">Extracted Fields</h3>
    <div id="schema-fields" class="space-y-2 mb-6">
      ${fields.length
        ? fields.map((field, i) => fieldEditorRow(field, i)).join('')
        : '<p class="pk-empty">No fields extracted yet.</p>'}
    </div>
    <div class="flex gap-3 flex-wrap">
      <button onclick="previewForm('${jsStr(formId)}')" class="pk-btn-secondary" style="display:inline-flex;align-items:center;gap:0.25rem"><i data-lucide="eye" style="width:14px;height:14px"></i>Preview File</button>
      <button onclick="saveSchema('${jsStr(formId)}')" class="pk-btn-primary">Save Schema</button>
      ${['READY', 'CONFIRMED'].includes(form?.status)
        ? `<button onclick="publishForm('${jsStr(formId)}')" class="pk-btn-secondary">Publish Form</button>`
        : ''}
      ${form?.status === 'PUBLISHED'
        ? `<button onclick="showQrModal('${jsStr(formId)}')" class="pk-btn-secondary" style="display:inline-flex;align-items:center;gap:0.25rem"><i data-lucide="qr-code" style="width:14px;height:14px"></i>Show QR</button>`
        : ''}
    </div>`;
  lucide.createIcons();
}

const FIELD_TYPES = ['text', 'textarea', 'number', 'date', 'time', 'email', 'phone', 'select', 'radio', 'checkbox', 'signature'];
const CHOICE_TYPES = ['select', 'radio', 'checkbox'];

function fieldEditorRow(field, i) {
  const ftype = field.field_type ?? 'text';
  const optionsStr = Array.isArray(field.options) ? field.options.join(', ') : '';
  const showOptions = CHOICE_TYPES.includes(ftype);
  return `
    <div class="field-row" data-idx="${i}">
      <div class="flex gap-2 items-center">
        <input type="text" value="${esc(field.field_name ?? '')}" data-idx="${i}" data-key="field_name"
          class="pk-input flex-1" placeholder="Field label">
        <select data-idx="${i}" data-key="field_type" class="pk-input" style="width:130px"
          onchange="toggleOptionsInput(${i})">
          ${FIELD_TYPES.map(t =>
            `<option value="${t}"${ftype === t ? ' selected' : ''}>${t}</option>`
          ).join('')}
        </select>
        <label style="display:flex;align-items:center;gap:0.25rem;white-space:nowrap;font-size:12px;color:var(--text-muted)">
          <input type="checkbox" data-idx="${i}" data-key="required"${field.required ? ' checked' : ''}> Req
        </label>
      </div>
      <input type="text" value="${esc(optionsStr)}" data-idx="${i}" data-key="options"
        class="pk-input" placeholder="Choices (comma-separated)"
        style="margin-top:0.375rem;font-size:12px;${showOptions ? '' : 'display:none'}">
    </div>`;
}

// Show the choices input only for select/radio/checkbox fields.
window.toggleOptionsInput = (i) => {
  const sel = document.querySelector(`[data-idx="${i}"][data-key="field_type"]`);
  const opt = document.querySelector(`[data-idx="${i}"][data-key="options"]`);
  if (sel && opt) opt.style.display = CHOICE_TYPES.includes(sel.value) ? '' : 'none';
};

window.saveSchema = async (formId) => {
  const rows = document.querySelectorAll('#schema-fields .field-row');
  const fields = Array.from(rows).map((_, i) => {
    const field_name = document.querySelector(`[data-idx="${i}"][data-key="field_name"]`)?.value.trim() ?? '';
    const field_type = document.querySelector(`[data-idx="${i}"][data-key="field_type"]`)?.value ?? 'text';
    const required = document.querySelector(`[data-idx="${i}"][data-key="required"]`)?.checked ?? false;
    const rawOptions = document.querySelector(`[data-idx="${i}"][data-key="options"]`)?.value ?? '';
    const options = CHOICE_TYPES.includes(field_type)
      ? rawOptions.split(',').map(s => s.trim()).filter(Boolean)
      : [];
    return { field_name, field_type, required, position: i, options: options.length ? options : null };
  }).filter(f => f.field_name);

  try {
    await api.forms.updateSchema(formId, fields);
    showFormDetail(formId);
  } catch (err) {
    alert('Failed to save schema: ' + err.message);
  }
};

window.publishForm = async (formId) => {
  if (!confirm('Publish this form? End users will be able to submit it.')) return;
  try {
    await api.forms.publish(formId);
    loadForms();
    closeFormDetail();
  } catch (err) {
    alert('Failed to publish form: ' + err.message);
  }
};

window.deleteForm = async (formId) => {
  if (!confirm('Delete this form? This cannot be undone.')) return;
  try {
    await api.forms.delete(formId);
    loadForms();
    closeFormDetail();
  } catch (err) {
    alert('Failed to delete form: ' + err.message);
  }
};

window.showQrModal = async (formId) => {
  const modal = document.getElementById('qr-modal');
  const img = document.getElementById('qr-image');
  const urlEl = document.getElementById('qr-url');
  const dlLink = document.getElementById('qr-download');
  img.src = '';
  urlEl.textContent = 'Loading…';
  modal.classList.remove('hidden');
  try {
    const res = await api.forms.getQr(formId);
    const qr = res?.data ?? res;
    const src = `data:image/png;base64,${qr.qr_code_base64}`;
    img.src = src;
    urlEl.textContent = qr.url ?? '';
    dlLink.href = src;
  } catch {
    urlEl.textContent = 'Failed to load QR code.';
  }
};

window.previewForm = async (formId) => {
  const modal = document.getElementById('preview-modal');
  const body = document.getElementById('preview-body');
  body.innerHTML = '<p class="pk-empty">Loading preview…</p>';
  modal.classList.remove('hidden');
  try {
    const blob = await api.forms.previewFile(formId);
    const url = URL.createObjectURL(blob);
    modal.dataset.objUrl = url;
    if (blob.type.startsWith('image/')) {
      body.innerHTML = `<img src="${url}" alt="Form preview" style="max-width:100%;max-height:70vh;border-radius:8px;border:1px solid var(--border-default)">`;
    } else if (blob.type === 'application/pdf') {
      body.innerHTML = `<iframe src="${url}" title="Form preview" style="width:100%;height:70vh;border:1px solid var(--border-default);border-radius:8px"></iframe>`;
    } else {
      body.innerHTML = `<div style="text-align:center">
        <p class="t-body" style="color:var(--text-muted);margin-bottom:1rem">This file type (${esc(blob.type || 'unknown')}) can't be shown inline.</p>
        <a href="${url}" download class="pk-btn-secondary" style="text-decoration:none">Download to view</a>
      </div>`;
    }
  } catch {
    body.innerHTML = '<p class="pk-empty" style="color:var(--accent-error)">Failed to load preview.</p>';
  }
};

window.closePreview = () => {
  const modal = document.getElementById('preview-modal');
  modal.classList.add('hidden');
  if (modal.dataset.objUrl) {
    URL.revokeObjectURL(modal.dataset.objUrl);
    delete modal.dataset.objUrl;
  }
  document.getElementById('preview-body').innerHTML = '';
};

window.openUploadZone = () => {
  document.getElementById('form-upload-zone').classList.toggle('hidden');
};

window.closeFormDetail = closeFormDetail;

function closeFormDetail() {
  document.getElementById('form-detail-panel').classList.add('hidden');
}

function setupFormUpload() {
  const input = document.getElementById('form-file-input');
  if (!input) return;
  input.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    input.value = '';
    document.getElementById('form-upload-zone').classList.add('hidden');
    try {
      await api.forms.upload(file);
      await loadForms();
    } catch (err) {
      alert('Upload failed: ' + err.message);
    }
  });
}

function setupDragDrop() {
  const zone = document.getElementById('form-upload-zone');
  if (!zone) return;
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', async e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (!file) return;
    zone.classList.add('hidden');
    try {
      await api.forms.upload(file);
      await loadForms();
    } catch (err) {
      alert('Upload failed: ' + err.message);
    }
  });
}

// ── WORKFLOWS ─────────────────────────────────────────────────────────────
// Workflow creation lives in the dedicated builder page (workflow-builder.html).

async function loadWorkflows() {
  const container = document.getElementById('workflows-list');
  try {
    const res = await api.workflows.list();
    const list = res?.items ?? res?.data ?? (Array.isArray(res) ? res : []);
    if (list.length === 0) {
      container.innerHTML = '<p class="pk-empty col-span-full">No workflows yet. Create one to get started.</p>';
      return;
    }
    container.innerHTML = list.map(w => workflowCard(w)).join('');
    lucide.createIcons();
  } catch {
    container.innerHTML = '<p class="pk-empty col-span-full" style="color:var(--accent-error)">Failed to load workflows.</p>';
  }
}

function workflowCard(w) {
  const status = w.status ?? 'DRAFT';
  const badgeMap = { DRAFT: 'pk-badge-neutral', PUBLISHED: 'pk-badge-success', ARCHIVED: 'pk-badge-warning' };
  const wfId = w.workflow_id ?? w.id;
  return `
    <div class="pk-card flex flex-col gap-4">
      <div class="flex justify-between items-start gap-2">
        <div>
          <p class="t-body" style="color:var(--text-primary);font-weight:600">${esc(w.name)}</p>
          <p class="t-caption" style="color:var(--text-muted)">${esc(w.description ?? '')}</p>
        </div>
        <span class="pk-badge ${badgeMap[status] ?? 'pk-badge-neutral'}">${status}</span>
      </div>
      <div class="flex gap-2 mt-auto">
        <a href="workflow-builder.html?id=${encodeURIComponent(wfId)}" class="pk-btn-secondary" style="flex:1;text-decoration:none">
          ${status === 'DRAFT' ? 'Edit' : 'Open'}
        </a>
        ${status === 'DRAFT'
          ? `<button onclick="publishWorkflow('${jsStr(wfId)}')" class="pk-btn-primary" style="flex:1">Publish</button>`
          : ''}
      </div>
    </div>`;
}

window.publishWorkflow = async (wfId) => {
  if (!confirm('Publish this workflow? It cannot be structurally edited once active submissions exist.')) return;
  try {
    await api.workflows.publish(wfId);
    loadWorkflows();
  } catch (err) {
    alert('Failed to publish workflow: ' + err.message);
  }
};

// ── ACTOR TYPES ───────────────────────────────────────────────────────────
window.openAddActorType = () => {
  document.getElementById('at-label').value = '';
  const role = document.getElementById('at-role');
  if (role) role.value = 'staff';
  document.getElementById('actor-type-modal').classList.remove('hidden');
};

function setupActorTypeForm() {
  const form = document.getElementById('actor-type-form');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const label = document.getElementById('at-label').value.trim();
    const system_role = document.getElementById('at-role')?.value || 'staff';
    if (!label) return;
    try {
      await api.admin.createActorType({ label, system_role });
      document.getElementById('actor-type-modal').classList.add('hidden');
      loadActorTypes();
    } catch (err) {
      alert('Failed to register actor type: ' + err.message);
    }
  });
}

window.deleteActorType = async (id, label) => {
  if (!confirm(`Delete actor type "${label}"? Existing users keep their current role and actor type.`)) return;
  try {
    await api.admin.deleteActorType(id);
    loadActorTypes();
  } catch (err) {
    alert('Failed to delete actor type: ' + err.message);
  }
};

async function loadActorTypes() {
  const tbody = document.getElementById('actor-types-body');
  try {
    const [typesRes, usersRes] = await Promise.all([
      api.admin.listActorTypes(),
      api.admin.listUsers().catch(() => []),
    ]);
    const types = typesRes?.data ?? (Array.isArray(typesRes) ? typesRes : []);
    const users = usersRes?.data ?? (Array.isArray(usersRes) ? usersRes : []);
    if (types.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" class="pk-empty">No actor types yet. Click “Add Actor Type” to create one.</td></tr>';
      return;
    }
    const counts = {};
    users.forEach(u => { if (u.actor_type) counts[u.actor_type] = (counts[u.actor_type] ?? 0) + 1; });
    const roleBadge = { admin: 'pk-badge-info', staff: 'pk-badge-neutral', end_user: 'pk-badge-warning' };
    tbody.innerHTML = types.map(t => `
      <tr>
        <td><span class="t-body" style="color:var(--text-primary);font-weight:600">${esc(t.label)}</span></td>
        <td><span class="pk-badge ${roleBadge[t.system_role] ?? 'pk-badge-neutral'}">${esc(t.system_role)}</span></td>
        <td><span class="t-body" style="color:var(--text-muted)">${counts[t.label] ?? 0}</span></td>
        <td><button onclick="deleteActorType('${jsStr(t.id)}','${jsStr(t.label)}')" class="pk-btn-danger">Delete</button></td>
      </tr>`).join('');
  } catch {
    tbody.innerHTML = '<tr><td colspan="4" class="pk-empty" style="color:var(--accent-error)">Failed to load actor types.</td></tr>';
  }
}

// ── USERS ─────────────────────────────────────────────────────────────────
async function loadUsers() {
  const tbody = document.getElementById('user-table-body');
  try {
    const res = await api.admin.listUsers();
    const list = res?.data ?? (Array.isArray(res) ? res : []);
    if (list.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="pk-empty">No users found.</td></tr>';
      return;
    }
    tbody.innerHTML = list.map(u => `
      <tr>
        <td>
          <p class="t-body" style="color:var(--text-primary);font-weight:600">${esc(u.full_name || u.email)}</p>
          <p class="t-caption" style="color:var(--text-muted)">${esc(u.email)}</p>
        </td>
        <td><span class="pk-badge pk-badge-neutral">${esc(u.role)}</span></td>
        <td><span class="t-caption" style="color:var(--text-muted)">${esc(u.actor_type ?? '—')}</span></td>
        <td>
          <span class="pk-badge ${u.is_active !== false ? 'pk-badge-success' : 'pk-badge-error'}">
            ${u.is_active !== false ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td>
          <div class="flex gap-2">
            <button onclick="editUser('${jsStr(u.id)}','${jsStr(u.full_name || '')}','${jsStr(u.role)}','${jsStr(u.actor_type || '')}')"
              class="pk-btn-link">Edit</button>
            <button onclick="deleteUser('${jsStr(u.id)}')" class="pk-btn-danger">Delete</button>
          </div>
        </td>
      </tr>`).join('');
  } catch {
    tbody.innerHTML = '<tr><td colspan="5" class="pk-empty" style="color:var(--accent-error)">Failed to load users.</td></tr>';
  }
}

window.editUser = async (userId, currentName, currentRole, currentActorType) => {
  const fullName = prompt('Full name:', currentName);
  if (fullName === null) return;
  const role = prompt('System role (admin / staff / end_user):', currentRole);
  if (role === null) return;
  const actorType = prompt('Actor type (leave blank for admin/end_user):', currentActorType);
  if (actorType === null) return;
  try {
    await api.admin.updateUser(userId, { full_name: fullName, role, actor_type: actorType || null });
    loadUsers();
  } catch (err) {
    alert('Failed to update user: ' + err.message);
  }
};

window.deleteUser = async (userId) => {
  if (!confirm('Delete this user? This cannot be undone.')) return;
  try {
    await api.admin.deleteUser(userId);
    loadUsers();
  } catch (err) {
    alert('Failed to delete user: ' + err.message);
  }
};

// ── STAFF IMPORT ──────────────────────────────────────────────────────────
function setupStaffCsvUpload() {
  const input = document.getElementById('staff-csv');
  if (!input) return;
  input.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    input.value = '';
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await api.admin.uploadStaffCSV(formData);
      const count = res?.data?.rows_processed ?? res?.rows_processed ?? '?';
      alert(`Imported ${count} staff rows successfully.`);
      loadStaffRows();
    } catch (err) {
      alert('CSV upload failed: ' + err.message);
    }
  });
}

async function loadStaffRows() {
  const tbody = document.getElementById('staff-table-body');
  try {
    const res = await api.admin.listStaffRows(currentUser.institution_id);
    const list = res?.data ?? (Array.isArray(res) ? res : []);
    if (list.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="pk-empty">No imported staff. Upload a CSV to get started.</td></tr>';
      return;
    }
    tbody.innerHTML = list.map(row => `
      <tr>
        <td>
          <p class="t-body" style="color:var(--text-primary);font-weight:600">${esc(row.name || 'Unnamed')}</p>
          <p class="t-caption" style="color:var(--text-muted)">${esc(row.email)}</p>
        </td>
        <td><span class="pk-badge pk-badge-warning">${esc(row.role)}</span></td>
        <td><span class="t-caption" style="color:var(--text-muted)">${esc(row.department || '—')}</span></td>
        <td>
          <span class="pk-badge ${row.matched_user_id ? 'pk-badge-success' : 'pk-badge-neutral'}">
            ${row.matched_user_id ? 'Matched' : 'Pending'}
          </span>
        </td>
        <td>
          <div class="flex gap-2">
            <button onclick="editStaffRow('${jsStr(row.id)}','${jsStr(row.email)}','${jsStr(row.name || '')}','${jsStr(row.role)}','${jsStr(row.department || '')}')"
              class="pk-btn-link">Edit</button>
            <button onclick="deleteStaffRow('${jsStr(row.id)}')" class="pk-btn-danger">Delete</button>
          </div>
        </td>
      </tr>`).join('');
  } catch {
    tbody.innerHTML = '<tr><td colspan="5" class="pk-empty" style="color:var(--accent-error)">Failed to load staff rows.</td></tr>';
  }
}

window.editStaffRow = async (rowId, email, name, role, dept) => {
  const newEmail = prompt('Email:', email);
  if (newEmail === null) return;
  const newName = prompt('Name:', name);
  if (newName === null) return;
  const newRole = prompt('Role (actor type):', role);
  if (newRole === null) return;
  const newDept = prompt('Department:', dept);
  if (newDept === null) return;
  try {
    await api.admin.updateStaffRow(currentUser.institution_id, rowId, {
      email: newEmail, name: newName, role: newRole, department: newDept
    });
    loadStaffRows();
  } catch (err) {
    alert('Failed to update staff row: ' + err.message);
  }
};

window.deleteStaffRow = async (rowId) => {
  if (!confirm('Remove this imported staff row?')) return;
  try {
    await api.admin.deleteStaffRow(currentUser.institution_id, rowId);
    loadStaffRows();
  } catch (err) {
    alert('Failed to delete staff row: ' + err.message);
  }
};

// ── NOTIFICATIONS ──────────────────────────────────────────────────────────
async function loadNotifications() {
  const container = document.getElementById('notifications-list');
  try {
    const res = await api.notifications.list();
    const list = res?.data ?? (Array.isArray(res) ? res : []);
    const unread = list.filter(n => !n.read).length;
    const badge = document.getElementById('notif-badge');
    if (badge) {
      badge.textContent = unread;
      badge.style.display = unread > 0 ? 'inline-flex' : 'none';
    }
    if (list.length === 0) {
      container.innerHTML = '<p class="pk-empty">No notifications.</p>';
      return;
    }
    container.innerHTML = list.map(n => `
      <div class="pk-list-item flex justify-between items-start gap-3"
           style="${!n.read ? 'background-color:rgba(0,102,204,0.04);border-left:3px solid var(--accent-primary)' : ''}">
        <div>
          <p class="t-body" style="color:var(--text-primary)${!n.read ? ';font-weight:600' : ''}">${esc(n.message ?? n.content ?? '')}</p>
          <p class="t-caption" style="color:var(--text-muted);margin-top:0.25rem">${new Date(n.created_at).toLocaleString()}</p>
        </div>
        ${!n.read
          ? `<button onclick="markOneRead('${jsStr(n.id)}')" class="pk-btn-ghost" style="flex-shrink:0;font-size:12px">Mark read</button>`
          : ''}
      </div>`).join('');
  } catch {
    container.innerHTML = '<p class="pk-empty" style="color:var(--accent-error)">Failed to load notifications.</p>';
  }
}

window.markAllRead = async () => {
  try {
    const res = await api.notifications.list();
    const list = res?.data ?? (Array.isArray(res) ? res : []);
    await Promise.all(list.filter(n => !n.read).map(n => api.notifications.markRead(n.id)));
    loadNotifications();
  } catch (err) {
    alert('Failed to mark all read: ' + err.message);
  }
};

window.markOneRead = async (notifId) => {
  try {
    await api.notifications.markRead(notifId);
    loadNotifications();
  } catch (err) {
    alert('Failed to mark notification read: ' + err.message);
  }
};

// ── Utilities ──────────────────────────────────────────────────────────────
function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function jsStr(value) {
  return String(value ?? '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

init();
