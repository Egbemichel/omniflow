import { api } from './api.js';
import { auth } from './auth.js';

let currentSteps = [];

async function initWorkflows() {
  const user = auth.getUser();
  if (!user || !['super_admin', 'institution_admin', 'admin'].includes(user.role)) {
    window.location.href = 'dashboard.html';
    return;
  }
  auth.updateUIForRole();

  const nameEl = document.getElementById('user-name');
  if (nameEl) nameEl.textContent = auth.getDisplayName();

  try {
    const response = await api.workflows.list();
    renderWorkflows(response.items || []);
  } catch (err) {
    console.error('Failed to load workflows:', err);
  }

  setupEventListeners();
}

function setupEventListeners() {
  const modal = document.getElementById('builder-modal');
  document.getElementById('create-wf-btn')?.addEventListener('click', () => {
    resetBuilder();
    modal.classList.remove('hidden');
  });
  [
    document.getElementById('close-builder-btn'),
    document.getElementById('cancel-builder-btn')
  ].forEach(btn => btn?.addEventListener('click', () => modal.classList.add('hidden')));

  document.getElementById('add-step-btn')?.addEventListener('click', addStep);
  document.getElementById('builder-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    await saveWorkflow();
  });
}

function resetBuilder() {
  document.getElementById('wf-name').value = '';
  document.getElementById('wf-desc').value = '';
  currentSteps = [{ id: Date.now(), name: 'Initial Review', role: 'staff', is_terminal: false }];
  renderSteps();
}

function addStep() {
  currentSteps.push({ id: Date.now(), name: '', role: 'staff', is_terminal: false });
  renderSteps();
}

function removeStep(id) {
  if (currentSteps.length <= 1) return;
  currentSteps = currentSteps.filter(s => s.id !== id);
  renderSteps();
}

function updateStep(id, field, value) {
  const step = currentSteps.find(s => s.id === id);
  if (step) step[field] = value;
}

function renderSteps() {
  const container = document.getElementById('steps-container');
  container.innerHTML = currentSteps.map((step, index) => `
    <div style="display:flex;align-items:center;gap:1rem;background-color:var(--bg-base);padding:1rem;border-radius:8px;border:1px solid var(--border-default)">
      <div style="width:32px;height:32px;border-radius:8px;background-color:var(--accent-primary);color:var(--text-on-dark);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;flex-shrink:0">
        ${index + 1}
      </div>
      <div style="flex-grow:1;display:grid;grid-template-columns:1fr 1fr;gap:1rem">
        <input type="text"
          value="${step.name}"
          onchange="window.updateStep(${step.id}, 'name', this.value)"
          placeholder="Step Name"
          class="pk-input" style="min-height:36px;padding:0.375rem 0.75rem">
        <select
          onchange="window.updateStep(${step.id}, 'role', this.value)"
          class="pk-input" style="min-height:36px;padding:0.375rem 0.75rem">
          <option value="staff" ${step.role === 'staff' ? 'selected' : ''}>Staff</option>
          <option value="manager" ${step.role === 'manager' ? 'selected' : ''}>Manager</option>
          <option value="admin" ${step.role === 'admin' ? 'selected' : ''}>Admin</option>
        </select>
      </div>
      <div style="display:flex;align-items:center;gap:0.5rem">
        <label style="display:flex;align-items:center;gap:0.25rem;cursor:pointer">
          <input type="checkbox" ${step.is_terminal ? 'checked' : ''}
            onchange="window.updateStep(${step.id}, 'is_terminal', this.checked)">
          <span class="t-fine" style="color:var(--text-muted);font-weight:600;text-transform:uppercase">Terminal</span>
        </label>
        <button type="button" onclick="window.removeStep(${step.id})"
          style="background:none;border:none;cursor:pointer;color:var(--border-default);padding:0.25rem;display:flex;align-items:center"
          onmouseover="this.style.color='var(--state-error)'" onmouseout="this.style.color='var(--border-default)'">
          <i data-lucide="trash-2" style="width:16px;height:16px"></i>
        </button>
      </div>
    </div>
  `).join('');

  window.updateStep = updateStep;
  window.removeStep = removeStep;
  if (window.lucide) lucide.createIcons();
}

async function saveWorkflow() {
  const name = document.getElementById('wf-name').value;
  const description = document.getElementById('wf-desc').value;
  const payload = {
    name,
    description,
    steps: currentSteps.map((s, idx) => ({
      step_name: s.name || `Step ${idx + 1}`,
      assigned_role: s.role,
      step_order: idx + 1,
      is_terminal: s.is_terminal
    }))
  };
  try {
    await api.workflows.create(payload);
    document.getElementById('builder-modal').classList.add('hidden');
    initWorkflows();
  } catch (err) {
    console.error('Failed to save workflow:', err);
    alert('Could not save workflow definition.');
  }
}

function renderWorkflows(workflows) {
  const container = document.getElementById('workflow-list');
  if (!workflows || workflows.length === 0) {
    container.innerHTML = '<div class="col-span-full pk-empty">No workflows defined yet.</div>';
    return;
  }

  container.innerHTML = workflows.map(wf => `
    <div class="pk-card" style="cursor:pointer">
      <h3 class="t-body" style="color:var(--text-primary);font-weight:600;margin-bottom:0.5rem">${wf.name}</h3>
      <p class="t-caption" style="color:var(--text-muted);margin-bottom:1rem;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical">${wf.description || 'No description'}</p>
      <div style="display:flex;align-items:center;justify-content:space-between">
        <span class="pk-badge ${wf.status === 'PUBLISHED' ? 'pk-badge-success' : 'pk-badge-warning'}">${wf.status}</span>
        <span class="t-caption" style="color:var(--text-muted)">${wf.step_count || 0} steps</span>
      </div>
    </div>
  `).join('');
}

initWorkflows();
