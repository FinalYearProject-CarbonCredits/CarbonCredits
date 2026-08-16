function getToken() {
  return localStorage.getItem('cc_token');
}

function getRefreshToken() {
  return localStorage.getItem('cc_refresh_token');
}

function getUser() {
  try {
    return JSON.parse(localStorage.getItem('cc_user') || 'null');
  } catch {
    return null;
  }
}

function saveSession(token, user, refreshToken) {
  localStorage.setItem('cc_token', token);
  localStorage.setItem('cc_user', JSON.stringify(user));
  if (refreshToken) localStorage.setItem('cc_refresh_token', refreshToken);
}

function clearSession() {
  localStorage.removeItem('cc_token');
  localStorage.removeItem('cc_user');
  localStorage.removeItem('cc_refresh_token');
}

function authHeaders() {
  const token = getToken();
  return token
    ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };
}

let _refreshing = null;

async function tryRefreshToken() {
  if (_refreshing) return _refreshing;
  const rt = getRefreshToken();
  if (!rt) return false;
  _refreshing = (async () => {
    try {
      const res = await fetch(`${window.API}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      saveSession(data.access_token, getUser(), data.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      _refreshing = null;
    }
  })();
  return _refreshing;
}

async function apiFetch(path, options = {}) {
  let res = await fetch(`${window.API}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
  if (res.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      res = await fetch(`${window.API}${path}`, {
        ...options,
        headers: { ...authHeaders(), ...(options.headers || {}) },
      });
      if (res.status !== 401) return res;
    }
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

async function logout() {
  const rt = getRefreshToken();
  if (rt) {
    try {
      await fetch(`${window.API}/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      });
    } catch { /* ignore */ }
  }
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
