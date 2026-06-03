import { api } from './api.js';
import { auth } from './auth.js';

let currentAdminUser = null;

async function initAdmin() {
    if (!auth.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    const user = await api.auth.me();
    if (!user || !['super_admin', 'institution_admin', 'admin'].includes(user.role)) {
        window.location.href = 'dashboard.html';
        return;
    }
    currentAdminUser = user;

    if (user.role === 'super_admin') {
        const instSection = document.getElementById('section-institutions');
        if (instSection) instSection.classList.remove('hidden');
        loadInstitutions();
    }

    loadUsers();
    setupCSVUpload();
    setupInstitutionForm();
}

async function loadInstitutions() {
    try {
        const insts = await api.admin.listInstitutions();
        const tbody = document.getElementById('institution-table-body');
        if (!tbody) return;
        if (!Array.isArray(insts)) {
            tbody.innerHTML = '<tr><td colspan="5" class="py-8 text-center text-slate-400">No institutions found</td></tr>';
            return;
        }
        tbody.innerHTML = insts.map(i => `
            <tr class="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                <td class="py-4 text-sm text-slate-500">${i.id}</td>
                <td class="py-4 font-medium">${i.name}</td>
                <td class="py-4 text-sm text-slate-500">${i.type}</td>
                <td class="py-4 text-sm text-slate-500">${new Date(i.created_at).toLocaleDateString()}</td>
                <td class="py-4">
                    <div class="flex gap-3">
                        <button onclick="updateInstitution(${i.id}, '${escapeForAttribute(i.name)}', '${escapeForAttribute(i.type)}')" class="text-apple-accent hover:underline text-sm font-semibold">Update</button>
                        <button onclick="deleteInstitution(${i.id})" class="text-red-600 hover:underline text-sm font-semibold">Delete</button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Failed to load institutions:', err);
    }
}

async function loadUsers() {
    try {
        const users = await api.admin.listUsers();
        renderUsers(users);
        loadStaffRows();
    } catch (err) {
        console.error('Failed to load users:', err);
    }
}

function renderUsers(users) {
    const tbody = document.getElementById('user-table-body');
    if (!tbody) return;
    const realUsers = Array.isArray(users) ? users : [];

    if (realUsers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="py-8 text-center text-slate-400">No users found</td></tr>';
        return;
    }

    tbody.innerHTML = realUsers.map(u => `
        <tr class="border-b border-slate-50 hover:bg-slate-50 transition-colors">
            <td class="py-4">
                <p class="font-medium text-slate-900">${u.email}</p>
                <p class="text-xs text-slate-500">${u.full_name || 'N/A'}</p>
            </td>
            <td class="py-4">
                <span class="px-2 py-1 rounded text-[10px] bg-slate-100 font-bold uppercase">${u.role}</span>
            </td>
            <td class="py-4 text-slate-500 text-sm">
                Inst: ${u.institution_id}<br>
                ID: ${u.id.substring(0, 8)}...
            </td>
            <td class="py-4">
                <div class="flex gap-3">
                    <button onclick="updateUser('${u.id}', '${escapeForAttribute(u.full_name || '')}', '${escapeForAttribute(u.role)}')" class="text-apple-accent hover:underline text-sm font-semibold">Update</button>
                    <button onclick="deleteUser('${u.id}')" class="text-red-600 hover:underline text-sm font-semibold">Delete</button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function loadStaffRows() {
    try {
        const staffRows = await api.admin.listStaffRows(currentAdminUser.institution_id);
        renderStaffRows(staffRows);
    } catch (err) {
        console.error('Failed to load imported staff:', err);
    }
}

function renderStaffRows(staffRows) {
    const tbody = document.getElementById('staff-table-body');
    if (!tbody) return;
    const importedStaff = Array.isArray(staffRows) ? staffRows : [];
    if (importedStaff.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="py-8 text-center text-slate-400">No imported staff found</td></tr>';
        return;
    }

    tbody.innerHTML = importedStaff.map(row => `
        <tr class="border-b border-slate-50 hover:bg-slate-50 transition-colors">
            <td class="py-4">
                <p class="font-medium text-slate-900">${row.email}</p>
                <p class="text-xs text-slate-500">${row.name || 'Imported staff'}</p>
            </td>
            <td class="py-4">
                <span class="px-2 py-1 rounded text-[10px] bg-amber-100 text-amber-700 font-bold uppercase">${row.role}</span>
            </td>
            <td class="py-4 text-slate-500 text-sm">
                Inst: ${row.institution_id}<br>
                Dept: ${row.department || 'N/A'}
            </td>
            <td class="py-4">
                <span class="text-slate-400 text-sm font-semibold">${row.matched_user_id ? 'Matched user' : 'Pending login'}</span>
            </td>
            <td class="py-4">
                <div class="flex gap-3">
                    <button onclick="updateStaffRow('${row.id}', '${escapeForAttribute(row.email)}', '${escapeForAttribute(row.name || '')}', '${escapeForAttribute(row.role)}', '${escapeForAttribute(row.department || '')}')" class="text-apple-accent hover:underline text-sm font-semibold">Update</button>
                    <button onclick="deleteStaffRow('${row.id}')" class="text-red-600 hover:underline text-sm font-semibold">Delete</button>
                </div>
            </td>
        </tr>
    `).join('');
}

function setupCSVUpload() {
    const input = document.getElementById('staff-csv');
    if (!input) return;
    input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await api.admin.uploadStaffCSV(formData);
            alert(`Parsed ${res.rows_processed} rows successfully.`);
            loadStaffRows();
        } catch (err) {
            console.error('CSV upload failed:', err);
            alert('Failed to upload CSV. Check console.');
        }
    });
}

function setupInstitutionForm() {
    const form = document.getElementById('form-create-institution');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('inst-name').value;
        const type = document.getElementById('inst-type').value;
        try {
            await api.admin.createInstitution({ name, type });
            form.reset();
            loadInstitutions();
        } catch (err) {
            alert('Failed to create institution');
        }
    });
}

function escapeForAttribute(value) {
    return String(value ?? '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

window.updateInstitution = async (institutionId, currentName, currentType) => {
    const name = prompt('Institution name:', currentName);
    if (name === null) return;
    const type = prompt('Institution type:', currentType);
    if (type === null) return;
    try {
        await api.admin.updateInstitution(institutionId, { name, type });
        loadInstitutions();
    } catch (err) {
        alert('Failed to update institution');
    }
};

window.deleteInstitution = async (institutionId) => {
    if (!confirm('Delete this institution? This cannot be undone.')) return;
    try {
        await api.admin.deleteInstitution(institutionId);
        loadInstitutions();
    } catch (err) {
        alert('Failed to delete institution');
    }
};

window.updateUser = async (userId, currentName, currentRole) => {
    const fullName = prompt('Full name:', currentName);
    if (fullName === null) return;
    const role = prompt('Role (super_admin, institution_admin, admin, staff, viewer):', currentRole);
    if (role === null) return;
    try {
        await api.admin.updateUser(userId, { full_name: fullName, role });
        loadUsers();
    } catch (err) {
        alert('Failed to update user');
    }
};

window.deleteUser = async (userId) => {
    if (!confirm('Delete this user? This cannot be undone.')) return;
    try {
        await api.admin.deleteUser(userId);
        loadUsers();
    } catch (err) {
        alert('Failed to delete user');
    }
};

window.updateStaffRow = async (rowId, currentEmail, currentName, currentRole, currentDepartment) => {
    const email = prompt('Email:', currentEmail);
    if (email === null) return;
    const name = prompt('Name:', currentName);
    if (name === null) return;
    const role = prompt('Role:', currentRole);
    if (role === null) return;
    const department = prompt('Department:', currentDepartment);
    if (department === null) return;
    try {
        await api.admin.updateStaffRow(currentAdminUser.institution_id, rowId, { email, name, role, department });
        loadStaffRows();
    } catch (err) {
        alert('Failed to update imported staff');
    }
};

window.deleteStaffRow = async (rowId) => {
    if (!confirm('Delete this imported staff row?')) return;
    try {
        await api.admin.deleteStaffRow(currentAdminUser.institution_id, rowId);
        loadStaffRows();
    } catch (err) {
        alert('Failed to delete imported staff');
    }
};

initAdmin();
