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

const googleButton = document.getElementById("btn-google");

googleButton?.addEventListener("click", () => {
    console.log("clicked, config:", window.PK_CONFIG);

    if (!window.PK_CONFIG || !window.PK_CONFIG.GOOGLE_CLIENT_ID) {
        alert("Google login is not configured.");
        return;
    }

    const clientId = window.PK_CONFIG.GOOGLE_CLIENT_ID;
    const configuredRedirectUri = window.PK_CONFIG.GOOGLE_REDIRECT_URI || `${window.location.origin}/auth/oauth/google/callback`;
    const redirectUri = encodeURIComponent(configuredRedirectUri);
    const scope = encodeURIComponent("email profile");
    const url = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=${scope}`;
    window.location.href = url;
});

document.getElementById("btn-github").addEventListener("click", () => {
    if (!window.PK_CONFIG || !window.PK_CONFIG.GITHUB_CLIENT_ID) {
        alert("GitHub login is not configured.");
        return;
    }

    const clientId = window.PK_CONFIG.GITHUB_CLIENT_ID;
    const configuredRedirectUri = window.PK_CONFIG.GITHUB_REDIRECT_URI || `${window.location.origin}/auth/oauth/github/callback`;
    const redirectUri = encodeURIComponent(configuredRedirectUri);
    const scope = encodeURIComponent("user:email");
    const url = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scope}`;
    window.location.href = url;
});
