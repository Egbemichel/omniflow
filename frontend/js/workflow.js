import { api } from './api.js';
import { auth } from './auth.js';

let currentSteps = [];

async function initWorkflows() {
    const user = auth.getUser();
    if (!user || (user.role !== 'admin' && user.role !== 'staff')) {
        window.location.href = 'dashboard.html';
        return;
    }

    try {
        const response = await api.workflows.list();
        renderWorkflows(response.items || []);
    } catch (err) {
        console.error('Failed to load workflows:', err);
    }

    setupEventListeners();
}

function setupEventListeners() {
    const createBtn = document.getElementById('create-wf-btn');
    const closeBtn = document.getElementById('close-builder-btn');
    const cancelBtn = document.getElementById('cancel-builder-btn');
    const addStepBtn = document.getElementById('add-step-btn');
    const builderForm = document.getElementById('builder-form');
    const modal = document.getElementById('builder-modal');

    createBtn?.addEventListener('click', () => {
        resetBuilder();
        modal.classList.remove('hidden');
    });

    [closeBtn, cancelBtn].forEach(btn => {
        btn?.addEventListener('click', () => modal.classList.add('hidden'));
    });

    addStepBtn?.addEventListener('click', () => {
        addStep();
    });

    builderForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveWorkflow();
    });
}

function resetBuilder() {
    document.getElementById('wf-name').value = '';
    document.getElementById('wf-desc').value = '';
    currentSteps = [
        { id: Date.now(), name: 'Initial Review', role: 'staff', is_terminal: false }
    ];
    renderSteps();
}

function addStep() {
    currentSteps.push({
        id: Date.now(),
        name: '',
        role: 'staff',
        is_terminal: false
    });
    renderSteps();
}

function removeStep(id) {
    if (currentSteps.length <= 1) return;
    currentSteps = currentSteps.filter(s => s.id !== id);
    renderSteps();
}

function updateStep(id, field, value) {
    const step = currentSteps.find(s => s.id === id);
    if (step) {
        step[field] = value;
    }
}

function renderSteps() {
    const container = document.getElementById('steps-container');
    container.innerHTML = currentSteps.map((step, index) => `
        <div class="flex items-center gap-4 bg-slate-50 p-4 rounded-apple-sm relative group border-hairline">
            <div class="w-8 h-8 rounded-full bg-apple-accent text-white flex items-center justify-center font-bold text-xs">
                ${index + 1}
            </div>
            <div class="flex-grow grid grid-cols-2 gap-4">
                <input type="text"
                    value="${step.name}"
                    onchange="window.updateStep(${step.id}, 'name', this.value)"
                    placeholder="Step Name"
                    class="bg-white border-hairline rounded px-3 py-1 text-sm outline-none focus:ring-1 focus:ring-apple-accent">
                <select
                    onchange="window.updateStep(${step.id}, 'role', this.value)"
                    class="bg-white border-hairline rounded px-3 py-1 text-sm outline-none focus:ring-1 focus:ring-apple-accent">
                    <option value="staff" ${step.role === 'staff' ? 'selected' : ''}>Staff</option>
                    <option value="manager" ${step.role === 'manager' ? 'selected' : ''}>Manager</option>
                    <option value="admin" ${step.role === 'admin' ? 'selected' : ''}>Admin</option>
                    <option value="student" ${step.role === 'student' ? 'selected' : ''}>Student</option>
                </select>
            </div>
            <div class="flex items-center gap-2">
                <label class="flex items-center gap-1 cursor-pointer">
                    <input type="checkbox" ${step.is_terminal ? 'checked' : ''}
                        onchange="window.updateStep(${step.id}, 'is_terminal', this.checked)"
                        class="rounded text-apple-accent">
                    <span class="text-[10px] uppercase font-bold text-slate-400">Terminal</span>
                </label>
                <button type="button" onclick="window.removeStep(${step.id})" class="text-slate-300 hover:text-red-500 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
            </div>
        </div>
    `).join('');

    // Expose helpers to window for onclick/onchange in template strings
    window.updateStep = updateStep;
    window.removeStep = removeStep;
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
        initWorkflows(); // Refresh list
    } catch (err) {
        console.error('Failed to save workflow:', err);
        alert('Could not save workflow definition. Check console.');
    }
}

function renderWorkflows(workflows) {
    const container = document.getElementById('workflow-list');
    if (!workflows || workflows.length === 0) {
        container.innerHTML = '<div class="col-span-full py-12 text-center text-slate-400">No workflows defined yet.</div>';
        return;
    }

    container.innerHTML = workflows.map(wf => `
        <div class="bg-white p-6 rounded-apple-lg border-hairline hover:shadow-md transition-shadow">
            <h3 class="font-semibold text-slate-900 mb-2">${wf.name}</h3>
            <p class="text-sm text-slate-500 mb-4 line-clamp-2">${wf.description || 'No description'}</p>
            <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded ${wf.status === 'PUBLISHED' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}">
                    ${wf.status}
                </span>
                <span class="text-slate-400 text-xs">${wf.step_count || 0} steps</span>
            </div>
        </div>
    `).join('');
}

initWorkflows();
