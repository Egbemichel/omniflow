import { api } from './api.js';

const loginForm = document.querySelector('form');
const emailInput = document.getElementById('email');
const submitBtn = loginForm.querySelector('button[type="submit"]');

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = emailInput.value;
  if (!email) return;

  submitBtn.disabled = true;
  submitBtn.textContent = 'Sending...';

  try {
    const res = await api.auth.login(email);
    if (res.msg) {
      loginForm.innerHTML = `
        <div class="p-6 bg-blue-50 border border-blue-100 rounded-apple-sm text-center">
            <p class="t-body text-blue-700 font-semibold mb-2">Check your email</p>
            <p class="t-fine text-blue-600">We've sent a magic link to <b>${email}</b>. Click the link to sign in.</p>
        </div>
      `;
    } else {
        throw new Error(res.detail || 'Login failed');
    }
  } catch (err) {
    alert(err.message);
    submitBtn.disabled = false;
    submitBtn.textContent = 'Send Magic Link';
  }
});

// Check for magic link token in URL
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

if (token) {
    document.body.innerHTML = `
        <div class="h-screen flex items-center justify-center bg-apple-base">
            <div class="text-center">
                <div class="w-12 h-12 border-4 border-apple-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p class="t-body text-slate-600">Verifying magic link...</p>
            </div>
        </div>
    `;

    api.auth.verify(token).then(res => {
        if (res.access_token) {
            localStorage.setItem('token', res.access_token);
            window.location.href = '/dashboard.html';
        } else {
            alert('Invalid or expired link');
            window.location.href = '/login.html';
        }
    }).catch(err => {
        alert('Verification failed');
        window.location.href = '/login.html';
    });
}
