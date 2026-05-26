import { getHeaders } from './auth.js';

const API_ROOT = '/api';

export const api = {
  async get(path) {
    const res = await fetch(`${API_ROOT}${path}`, {
      headers: getHeaders()
    });
    if (res.status === 401) {
      window.location.href = '/login.html';
      return;
    }
    return res.json();
  },

  async post(path, body) {
    const res = await fetch(`${API_ROOT}${path}`, {
      method: 'POST',
      headers: {
        ...getHeaders(),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    if (res.status === 401) {
      window.location.href = '/login.html';
      return;
    }
    return res.json();
  },

  auth: {
    login: (email) => api.post('/auth/magic/login', { email }),
    verify: (token) => api.get(`/auth/magic/verify?token=${token}`),
    me: () => api.get('/auth/me')
  },

  tasks: {
    list: () => api.get('/task/tasks/inbox'),
    complete: (taskId) => api.post(`/task/tasks/${taskId}/complete`, {})
  },

  submissions: {
    list: () => api.get('/task/submissions'),
    status: (id) => api.get(`/task/submissions/${id}/status`),
    history: (id) => api.get(`/task/submissions/${id}/history`)
  },

  notifications: {
    list: () => api.get('/notification/notifications'),
    markRead: (id) => api.post(`/notification/notifications/${id}/read`, {})
  }
};
