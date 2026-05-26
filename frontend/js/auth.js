/**
 * Simple Auth state management for OmniFlow
 */

export const auth = {
  getToken: () => localStorage.getItem('of_token'),
  saveToken: (token) => localStorage.setItem('of_token', token),
  clearToken: () => localStorage.removeItem('of_token'),

  getUser: () => {
    const token = auth.getToken();
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload;
    } catch (e) {
      return null;
    }
  },

  isAuthenticated: () => !!auth.getToken(),

  logout: () => {
    auth.clearToken();
    window.location.href = 'login.html';
  },

  getHeaders: () => {
    const token = auth.getToken();
    const user = auth.getUser();
    return {
      'Authorization': `Bearer ${token}`,
      'X-User-Id': user?.sub || '',
      'X-User-Role': user?.role || ''
    };
  }
};
