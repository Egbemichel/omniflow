import { auth } from './auth.js';

const API_ROOT = '/api';

export const api = {
  async get(path) {
    const res = await fetch(`${API_ROOT}${path}`, {
      headers: auth.getHeaders()
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
        ...auth.getHeaders(),
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

  async put(path, body) {
    const res = await fetch(`${API_ROOT}${path}`, {
      method: 'PUT',
      headers: {
        ...auth.getHeaders(),
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

  async delete(path) {
    const res = await fetch(`${API_ROOT}${path}`, {
      method: 'DELETE',
      headers: auth.getHeaders()
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
    me: () => api.get('/auth/auth/verify')
  },

  tasks: {
    list: () => api.get('/task/tasks/inbox'),
    complete: (taskId, action = 'APPROVE') => api.post(`/task/tasks/${taskId}/complete`, { action })
  },

  submissions: {
    list: () => api.get('/task/submissions'),
    status: (id) => api.get(`/task/submissions/${id}/status`),
    history: (id) => api.get(`/task/submissions/${id}/history`),
    create: (data) => api.post('/task/submissions', data)
  },

  workflows: {
    list: () => api.get('/workflow/workflows'),
    get: (id) => api.get(`/workflow/workflows/${id}`),
    create: (data) => api.post('/workflow/workflows', data),
    publish: (id) => api.post(`/form/forms/${id}/publish`, {}) // In this system, publishing a form makes the workflow ready
  },

  forms: {
    list: () => api.get('/form/forms'),
    getSchema: (id) => api.get(`/form/forms/${id}/schema`),
    updateSchema: (id, fields) => api.patch(`/form/forms/${id}/schema`, { fields }),
    publish: (id) => api.post(`/form/forms/${id}/publish`, {})
  },

  admin: {
    listUsers: () => api.get('/auth/admin/users'),
    updateUser: (id, data) => api.put(`/auth/admin/users/${id}`, data),
    deleteUser: (id) => api.delete(`/auth/admin/users/${id}`),
    updateUserRole: (id, role) => api.put(`/auth/admin/users/${id}/role`, { role }),
    listInstitutions: () => api.get('/auth/institutions/'),
    createInstitution: (data) => api.post('/auth/institutions/', data),
    updateInstitution: (id, data) => api.put(`/auth/institutions/${id}`, data),
    deleteInstitution: (id) => api.delete(`/auth/institutions/${id}`),
    listStaffRows: (institutionId) => api.get(`/auth/admin/institutions/${institutionId}/staff`),
    updateStaffRow: (institutionId, rowId, data) => api.put(`/auth/admin/institutions/${institutionId}/staff/${rowId}`, data),
    deleteStaffRow: (institutionId, rowId) => api.delete(`/auth/admin/institutions/${institutionId}/staff/${rowId}`),
    uploadStaffCSV: (formData) => {
        return fetch(`${API_ROOT}/auth/onboarding/upload-csv`, {
            method: 'POST',
            headers: auth.getHeaders(),
            body: formData
        }).then(res => res.json());
    }
  },

  notifications: {
    list: () => api.get('/notification/notifications'),
    markRead: (id) => api.post(`/notification/notifications/${id}/read`, {})
  }
};
