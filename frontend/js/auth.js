function getToken() {
  return localStorage.getItem('cc_token');
}

function getUser() {
  try {
    return JSON.parse(localStorage.getItem('cc_user') || 'null');
  } catch {
    return null;
  }
}

function saveSession(token, user) {
  localStorage.setItem('cc_token', token);
  localStorage.setItem('cc_user', JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem('cc_token');
  localStorage.removeItem('cc_user');
}

function authHeaders() {
  const token = getToken();
  return token
    ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };
}

async function apiFetch(path, options = {}) {
  const res = await fetch(`${window.API}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
  if (res.status === 401) {
    clearSession();
    window.location.href = 'login.html';
    throw new Error('Session expired');
  }
  return res;
}

function requireRole(role, redirect = 'login.html') {
  const user = getUser();
  if (!user || !getToken()) {
    window.location.href = redirect;
    return null;
  }
  if (user.role !== role) {
    window.location.href = portalForRole(user.role);
    return null;
  }
  return user;
}

function portalForRole(role) {
  if (role === 'admin') return 'admin.html';
  if (role === 'company') return 'company.html';
  return 'landowner.html';
}

function logout() {
  clearSession();
  window.location.href = 'login.html';
}

function toast(msg, elId = 'toast') {
  const t = document.getElementById(elId);
  if (!t) return;
  t.textContent = '// ' + msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3500);
}
