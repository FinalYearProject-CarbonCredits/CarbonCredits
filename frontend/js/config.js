/** Shared API base — set on window to avoid duplicate const conflicts between scripts. */
(function () {
  const host = window.location.hostname || '127.0.0.1';
  window.API = `http://${host}:8000/api`;
  window.BACKEND = `http://${host}:8000`;
})();

function backendUnreachableMessage() {
  return `Cannot reach backend at ${window.BACKEND}. Start it: cd backend && python main.py`;
}

function apiErrorMessage(data, fallback) {
  if (!data || !data.detail) return fallback;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map(d => d.msg || String(d)).join('; ');
  return fallback;
}
