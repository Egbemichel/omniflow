import { auth } from './auth.js';

const API_ROOT = (window.CONFIG?.API_ROOT) ?? '/api';

async function handleResponse(res) {
  if (res.status === 401) {
    auth.clearToken();              // wipe the stale / expired token
    window.location.href = '/login.html';
    throw new Error('UNAUTHORIZED'); // stop callers from doing a second redirect
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || res.statusText);
  }
  // 204 No Content (e.g. DELETE) and other empty bodies have no JSON to parse.
  if (res.status === 204 || res.headers.get('content-length') === '0') return null;
  return res.json();
}

export const api = {
  async get(path) {
    const res = await fetch(`${API_ROOT}${path}`, { headers: auth.getHeaders() });
    return handleResponse(res);
  },

  async post(path, body) {
    const res = await fetch(`${API_ROOT}${path}`, {
      method: 'POST',
      headers: { ...auth.getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return handleResponse(res);
  },

  async put(path, body) {
    const res = await fetch(`${API_ROOT}${path}`, {
      method: 'PUT',
      headers: { ...auth.getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return handleResponse(res);
  },

  async patch(path, body) {
    const res = await fetch(`${API_ROOT}${path}`, {
      method: 'PATCH',
      headers: { ...auth.getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return handleResponse(res);
  },

  async delete(path) {
    const res = await fetch(`${API_ROOT}${path}`, {
      method: 'DELETE',
      headers: auth.getHeaders()
    });
    return handleResponse(res);
  },

  auth: {
    login: (email) => api.post('/auth/magic/login', { email }),
    verify: (token) => api.get(`/auth/magic/verify?token=${token}`),
    me: () => api.get('/auth/auth/verify'),
    requestMagicLink: (email) => fetch(`${API_ROOT}/auth/magic-link/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    }).then(r => r.json())
  },

  tasks: {
    list: () => api.get('/task/tasks/inbox'),
    complete: (taskId, action = 'APPROVE') => api.post(`/task/tasks/${taskId}/complete`, { action })
  },

  submissions: {
    list: () => api.get('/task/submissions'),
    status: (id) => api.get(`/task/submissions/${id}/status`),
    history: (id) => api.get(`/task/submissions/${id}/history`),
    create: (data) => api.post('/task/submissions', data),
    updateFormData: (id, form_data) => api.patch(`/task/submissions/${id}/form-data`, { form_data })
  },

  workflows: {
    list: () => api.get('/workflow/workflows'),
    get: (id) => api.get(`/workflow/workflows/${id}`),
    create: (data) => api.post('/workflow/workflows', data),
    update: (id, data) => api.patch(`/workflow/workflows/${id}`, data),
    publish: (id) => api.post(`/workflow/workflows/${id}/publish`, {})
  },

  forms: {
    list: () => api.get('/form/forms'),
    getStatus: (id) => api.get(`/form/forms/${id}/status`),
    getSchema: (id) => api.get(`/form/forms/${id}/schema`),
    updateSchema: (id, fields) => api.patch(`/form/forms/${id}/schema`, { fields }),
    publish: (id) => api.post(`/form/forms/${id}/publish`, {}),
    delete: (id) => api.delete(`/form/forms/${id}`),
    getQr: (id) => api.get(`/form/forms/${id}/qr`),
    previewFile: (id) => fetch(`${API_ROOT}/form/forms/${id}/file`, { headers: auth.getHeaders() })
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.blob(); }),
    getSubmissions: (id, page = 1) => api.get(`/form/forms/${id}/submissions?page=${page}`),
    suggestWorkflow: (id) => api.get(`/form/forms/${id}/suggest-workflow`),
    upload: (file) => {
      const formData = new FormData();
      formData.append('file', file);
      return fetch(`${API_ROOT}/form/forms/upload`, {
        method: 'POST',
        headers: auth.getHeaders(),
        body: formData
      }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
    }
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
    listActorTypes: () => api.get('/auth/admin/actor-types'),
    createActorType: (data) => api.post('/auth/admin/actor-types', data),
    deleteActorType: (id) => api.delete(`/auth/admin/actor-types/${id}`),
    listStaffRows: (institutionId) => api.get(`/auth/admin/institutions/${institutionId}/staff`),
    updateStaffRow: (institutionId, rowId, data) => api.put(`/auth/admin/institutions/${institutionId}/staff/${rowId}`, data),
    deleteStaffRow: (institutionId, rowId) => api.delete(`/auth/admin/institutions/${institutionId}/staff/${rowId}`),
    uploadStaffCSV: (formData) => fetch(`${API_ROOT}/auth/onboarding/upload-csv`, {
      method: 'POST',
      headers: auth.getHeaders(),
      body: formData
    }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
  },

  notifications: {
    list: () => api.get('/notification/notifications'),
    markRead: (id) => api.patch(`/notification/notifications/${id}/read`, {})
  },

  formPublic: {
    schema: (formId) => fetch(`${API_ROOT}/form-public/forms/${formId}/public-schema`)
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); }),

    submit: (formId, data) => fetch(`${API_ROOT}/form-public/forms/${formId}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
  }
};
