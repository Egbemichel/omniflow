import { auth } from './auth.js';
import { api } from './api.js';

function roleHomePage(role) {
  if (role === 'admin' || role === 'super_admin') return '/admin.html';
  if (role === 'staff') return '/staff.html';
  return '/dashboard.html';
}

// ── Session gate ──────────────────────────────────────────────────────────
// Run before anything else.
// • Valid non-expired session → send user straight to their home page.
// • Expired / malformed token → clear it so the form starts completely clean.
if (auth.isAuthenticated()) {
  window.location.href = roleHomePage(auth.getUser()?.role);
} else {
  // Wipe any stale token (expired JWT, leftover from a crashed session, etc.)
  auth.clearToken();
}

// ── Magic-link token in URL (?token=) ─────────────────────────────────────
// This path is used when the backend redirects the email verification link
// back to login.html?token=<temp_token> (dev / fallback flow).
const urlParams = new URLSearchParams(window.location.search);
const urlToken  = urlParams.get('token');

if (urlToken) {
  document.body.innerHTML = `
    <div style="height:100vh;display:flex;align-items:center;justify-content:center;background-color:var(--bg-base)">
      <div style="text-align:center">
        <div style="width:48px;height:48px;border:4px solid var(--accent-primary);border-top-color:transparent;
             border-radius:9999px;animation:spin 0.8s linear infinite;margin:0 auto 1rem"></div>
        <p style="color:var(--text-muted);font-family:Inter,sans-serif;font-size:14px">Verifying magic link…</p>
      </div>
    </div>
    <style>@keyframes spin{to{transform:rotate(360deg)}}</style>`;

  api.auth.verify(urlToken)
    .then(res => {
      if (res?.access_token) {
        auth.saveToken(res.access_token);
        window.location.href = roleHomePage(auth.getUser()?.role);
      } else {
        auth.clearToken();
        alert('Invalid or expired link. Please request a new one.');
        window.location.href = '/login.html';
      }
    })
    .catch(() => {
      auth.clearToken();
      window.location.href = '/login.html';
    });
}

// ── Google OAuth ──────────────────────────────────────────────────────────
document.getElementById('btn-google')?.addEventListener('click', () => {
  if (!window.PK_CONFIG?.GOOGLE_CLIENT_ID) {
    alert('Google login is not configured.');
    return;
  }
  const { GOOGLE_CLIENT_ID, GOOGLE_REDIRECT_URI } = window.PK_CONFIG;
  const redirectUri = encodeURIComponent(
    GOOGLE_REDIRECT_URI || `${window.location.origin}/auth/oauth/google/callback`
  );
  window.location.href =
    `https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}` +
    `&redirect_uri=${redirectUri}&response_type=code&scope=${encodeURIComponent('email profile')}`;
});

// ── GitHub OAuth ──────────────────────────────────────────────────────────
document.getElementById('btn-github')?.addEventListener('click', () => {
  if (!window.PK_CONFIG?.GITHUB_CLIENT_ID) {
    alert('GitHub login is not configured.');
    return;
  }
  const { GITHUB_CLIENT_ID, GITHUB_REDIRECT_URI } = window.PK_CONFIG;
  const redirectUri = encodeURIComponent(
    GITHUB_REDIRECT_URI || `${window.location.origin}/auth/oauth/github/callback`
  );
  window.location.href =
    `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}` +
    `&redirect_uri=${redirectUri}&scope=${encodeURIComponent('user:email')}`;
});

// ── Magic-link email form ─────────────────────────────────────────────────
document.getElementById('magic-link-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = document.getElementById('email').value.trim();
  if (!email) return;

  const btn = e.target.querySelector('button[type=submit]');
  btn.textContent = 'Sending…';
  btn.disabled = true;

  try {
    await api.auth.requestMagicLink(email);
    e.target.innerHTML = `
      <div style="padding:1.5rem;background-color:rgba(0,102,204,0.08);
           border:1px solid rgba(0,102,204,0.2);border-radius:8px;text-align:center">
        <p style="color:var(--accent-primary);font-weight:600;margin-bottom:0.5rem;font-family:Inter,sans-serif;font-size:14px">
          Check your email
        </p>
        <p style="color:var(--accent-primary);font-family:Inter,sans-serif;font-size:12px">
          We've sent a sign-in link to <b>${email}</b>.
        </p>
      </div>`;
  } catch {
    btn.textContent = 'Something went wrong. Try again.';
    btn.disabled = false;
  }
});
