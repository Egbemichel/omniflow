export const auth = {
  getToken: () => sessionStorage.getItem('of_token'),
  saveToken: (token) => sessionStorage.setItem('of_token', token),
  clearToken: () => sessionStorage.removeItem('of_token'),

  getUser: () => {
    const token = auth.getToken();
    if (!token) return null;
    try {
      // JWT uses base64url; convert to standard base64 + restore padding
      const b64url = token.split('.')[1] || '';
      const b64 = b64url.replace(/-/g, '+').replace(/_/g, '/');
      const pad = b64.length % 4;
      const padded = pad ? b64 + '='.repeat(4 - pad) : b64;
      return JSON.parse(atob(padded));
    } catch {
      return null;
    }
  },

  // True only when token exists AND is not yet expired
  isAuthenticated: () => {
    const user = auth.getUser();
    if (!user) return false;
    const now = Math.floor(Date.now() / 1000);
    return !user.exp || user.exp > now;
  },

  getDisplayName: () => {
    const user = auth.getUser();
    if (!user) return 'User';
    const fullName = (user.full_name || '').trim();
    if (fullName) return fullName;
    if (user.email) return user.email.split('@')[0];
    return 'User';
  },

  logout: () => {
    auth.clearToken();
    window.location.href = 'login.html';
  },

  getHeaders: () => {
    const token = auth.getToken();
    const user = auth.getUser();
    return {
      'Authorization': `Bearer ${token || ''}`,
      'X-User-Id': user?.sub || '',
      'X-User-Role': user?.role || ''
    };
  }
};
