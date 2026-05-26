import { api } from './api.js';
import { auth } from './auth.js';

async function initDashboard() {
  try {
    const user = await api.auth.me();
    if (user) {
      document.getElementById('user-name').textContent = user.email.split('@')[0];
    }

    const tasks = await api.tasks.list();
    renderTasks(tasks);

    const subs = await api.submissions.list();
    renderSubmissions(subs);

  } catch (err) {
    console.error('Failed to load dashboard:', err);
  }
}

function renderTasks(tasks) {
  const container = document.getElementById('task-list');
  if (!tasks || tasks.length === 0) {
    container.innerHTML = '<p class="t-body text-slate-400 text-center py-12">No pending tasks found</p>';
    document.getElementById('task-count').textContent = '0';
    return;
  }

  document.getElementById('task-count').textContent = tasks.length;
  container.innerHTML = tasks.map(task => `
    <div class="flex items-center justify-between p-4 bg-slate-50 rounded-apple-sm border-hairline">
      <div>
        <p class="font-semibold text-slate-900">Task: ${task.assigned_role}</p>
        <p class="text-xs text-slate-500">ID: ${task.id}</p>
      </div>
      <button onclick="window.completeTask('${task.id}')" class="text-apple-accent hover:underline text-sm font-semibold">
        Complete
      </button>
    </div>
  `).join('');
}

function renderSubmissions(subs) {
  const container = document.getElementById('submission-list');
  if (!subs || subs.length === 0) {
    container.innerHTML = '<p class="t-body text-slate-400 text-center py-12">No submissions found</p>';
    return;
  }

  container.innerHTML = subs.map(sub => `
    <div class="flex items-center justify-between p-4 bg-slate-50 rounded-apple-sm border-hairline">
      <div>
        <p class="font-semibold text-slate-900">Submission ${sub.id.substring(0,8)}</p>
        <div class="flex gap-2 items-center">
            <span class="px-2 py-0.5 rounded-full text-[10px] uppercase font-bold tracking-wider ${getStatusClass(sub.status)}">
                ${sub.status}
            </span>
        </div>
      </div>
      <a href="/submission-detail.html?id=${sub.id}" class="text-slate-400 hover:text-slate-900">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="9 5l7 7-7 7"></path></svg>
      </a>
    </div>
  `).join('');
}

function getStatusClass(status) {
    switch(status) {
        case 'completed': return 'bg-green-100 text-green-700';
        case 'pending': return 'bg-blue-100 text-blue-700';
        default: return 'bg-slate-100 text-slate-700';
    }
}

window.completeTask = async (id) => {
  if (confirm('Complete this task?')) {
    await api.tasks.complete(id);
    initDashboard(); // Reload
  }
};

document.querySelector('button:contains("Sign Out")')?.addEventListener('click', () => {
    auth.logout();
});

// Polyfill for :contains
if (!Element.prototype.containsText) {
    window.signOut = () => {
        auth.logout();
    }
}

initDashboard();
