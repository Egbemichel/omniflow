import { api } from './api.js';
import { auth } from './auth.js';

async function initAdmin() {
    const user = auth.getUser();
    if (!user || user.role !== 'admin') {
        window.location.href = 'dashboard.html';
        return;
    }

    try {
        // This endpoint might not exist yet, we'll need to add it to api.js if needed
        const users = await api.get('/auth/admin/users');
        renderUsers(users);
    } catch (err) {
        console.error('Failed to load users:', err);
    }
}

function renderUsers(users) {
    const tbody = document.getElementById('user-table-body');
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="py-8 text-center text-slate-400">No users found</td></tr>';
        return;
    }

    tbody.innerHTML = users.map(u => `
        <tr class="border-b border-slate-50 hover:bg-slate-50 transition-colors">
            <td class="py-4">
                <p class="font-medium text-slate-900">${u.email}</p>
                <p class="text-xs text-slate-500">${u.id}</p>
            </td>
            <td class="py-4">
                <span class="px-2 py-1 rounded text-[10px] bg-slate-100 font-bold uppercase">${u.role}</span>
            </td>
            <td class="py-4 text-slate-500 text-sm">
                ${u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
            </td>
            <td class="py-4">
                <button class="text-apple-accent hover:underline text-sm font-semibold">Edit</button>
            </td>
        </tr>
    `).join('');
}

initAdmin();
