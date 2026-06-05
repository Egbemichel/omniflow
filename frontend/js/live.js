import { auth } from './auth.js';

const API_ROOT = (window.CONFIG && window.CONFIG.API_ROOT) || '/api';

// Opens a Server-Sent Events stream to the gateway and routes named events to
// handlers. The server only emits an event when something actually changed, so
// handlers (which typically refetch a view) run only on real updates — no polling.
//
//   connectLive({ 'form.updated': () => loadForms() })
//
// Event types: form.updated, workflow.updated, task.updated, submission.updated,
// notification.new. Returns { close }.
export function connectLive(handlers = {}) {
  const token = auth.getToken && auth.getToken();
  if (!token) return { close() {} };

  let es = null;
  let closed = false;

  function open() {
    if (closed) return;
    es = new EventSource(`${API_ROOT}/events?token=${encodeURIComponent(token)}`);

    Object.entries(handlers).forEach(([type, fn]) => {
      es.addEventListener(type, (ev) => {
        let data = null;
        try { data = ev.data ? JSON.parse(ev.data) : null; } catch { /* ignore */ }
        try { fn(data); } catch (err) { console.error(`live handler "${type}" failed`, err); }
      });
    });

    // Server signals an unusable token by closing; stop retrying in that case.
    es.addEventListener('unauthorized', () => { closed = true; es.close(); });
    es.onerror = () => {
      // EventSource auto-reconnects on transient drops. A 401 (expired/invalid
      // token) closes the stream permanently, which is what we want.
    };
  }

  open();

  // Some browsers drop the stream while the tab is backgrounded; reopen on return.
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && !closed && es && es.readyState === EventSource.CLOSED) open();
  });

  return { close() { closed = true; if (es) es.close(); } };
}
