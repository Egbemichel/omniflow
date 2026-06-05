import { api } from './api.js';
import { auth } from './auth.js';

// ── Shape catalogue ─────────────────────────────────────────────────────────
// w/h are the node box dimensions; used both for rendering and edge geometry.
// Loops and jumps have no shape — they are drawn as labeled arrows between nodes.
const SHAPES = {
  start:     { w: 132, h: 54,  label: 'Start' },
  entry:     { w: 92,  h: 104, label: 'Entry User' },
  actor:     { w: 176, h: 66,  label: 'Actor Step' },
  condition: { w: 112, h: 112, label: 'Condition' },
  end:       { w: 112, h: 112, label: 'End' },
};
// Exactly one of each of these is allowed per workflow.
const SINGLETON = { start: 'Start', entry: 'Entry User', end: 'End' };

const SVG_NS = 'http://www.w3.org/2000/svg';
const DRAFT_KEY = 'of_wf_graph_draft';
const graphKey = (id) => `of_wf_graph_${id}`;

// ── State ───────────────────────────────────────────────────────────────────
let nodes = [];
let edges = [];                 // { id, from, to, label }
let sel = null;                 // { kind: 'node' | 'edge', id }
let currentWorkflowId = null;   // set after first save; create-once on the backend
let actorTypes = [];
let formsList = [];
let formId = '';                // linked form (required before saving)
let seq = 0;
let dirty = false;

// Pan/zoom viewport transform applied to the canvas content (no scrollbars).
let zoom = 1;
let panX = 0;
let panY = 0;
const ZOOM_MIN = 0.25;
const ZOOM_MAX = 2.5;

const canvas = document.getElementById('wf-canvas');
const viewport = canvas.parentElement; // .pk-wf-canvas-wrap
const svg = document.getElementById('wf-edges');
const nameInput = document.getElementById('wf-name');
const formSelect = document.getElementById('wf-form-select');
const statusBadge = document.getElementById('wf-status-badge');
const saveState = document.getElementById('wf-save-state');

const uid = (p) => `${p}${Date.now().toString(36)}${seq++}`;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const nodeById = (id) => nodes.find((n) => n.id === id);
const edgeById = (id) => edges.find((e) => e.id === id);
const selNode = () => (sel?.kind === 'node' ? nodeById(sel.id) : null);
const selEdge = () => (sel?.kind === 'edge' ? edgeById(sel.id) : null);

// ── Pan / zoom ────────────────────────────────────────────────────────────────
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

function applyTransform() {
  canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${zoom})`;
  const label = document.getElementById('wf-zoom-level');
  if (label) label.textContent = `${Math.round(zoom * 100)}%`;
}

// Convert a screen (client) point to canvas/world coordinates. The canvas's own
// transformed bounding rect already accounts for pan, so we only divide by zoom.
function screenToWorld(clientX, clientY) {
  const r = canvas.getBoundingClientRect();
  return { x: (clientX - r.left) / zoom, y: (clientY - r.top) / zoom };
}

// Zoom toward a screen anchor, keeping the world point under it fixed.
function zoomAt(clientX, clientY, nextZoom) {
  nextZoom = clamp(nextZoom, ZOOM_MIN, ZOOM_MAX);
  const r = canvas.getBoundingClientRect();
  const originX = r.left - panX; // static position of the canvas's (0,0)
  const originY = r.top - panY;
  const wx = (clientX - r.left) / zoom;
  const wy = (clientY - r.top) / zoom;
  zoom = nextZoom;
  panX = clientX - originX - wx * zoom;
  panY = clientY - originY - wy * zoom;
  applyTransform();
}

function zoomByButton(factor) {
  const r = viewport.getBoundingClientRect();
  zoomAt(r.left + r.width / 2, r.top + r.height / 2, zoom * factor);
}

function resetView() {
  zoom = 1;
  panX = 0;
  panY = 0;
  applyTransform();
}

// ── Init ────────────────────────────────────────────────────────────────────
async function init() {
  const user = auth.getUser();
  if (!auth.isAuthenticated() || !['admin', 'super_admin'].includes(user?.role)) {
    window.location.href = 'login.html';
    return;
  }

  await Promise.all([loadActorTypes(user.institution_id), loadForms()]);
  await restoreGraph();
  populateFormSelect();
  bindToolbar();
  bindPalette();
  bindCanvas();
  bindKeyboard();
  render();
  applyTransform();
}

async function loadActorTypes(institutionId) {
  try {
    // Prefer the institution's registered actor types.
    const res = await api.admin.listActorTypes();
    const types = res?.data ?? (Array.isArray(res) ? res : []);
    actorTypes = [...new Set(types.map((t) => t.label).filter(Boolean))];
    if (actorTypes.length) return;
  } catch { /* fall back to staff CSV rows below */ }
  try {
    const res = await api.admin.listStaffRows(institutionId);
    const rows = res?.data ?? (Array.isArray(res) ? res : []);
    actorTypes = [...new Set(rows.map((r) => r.role ?? r.actor_type).filter(Boolean))];
  } catch {
    actorTypes = [];
  }
}

async function loadForms() {
  try {
    const res = await api.forms.list();
    formsList = res?.items ?? res?.data ?? (Array.isArray(res) ? res : []);
  } catch {
    formsList = [];
  }
}

function populateFormSelect() {
  const opts = ['<option value="">— Link a form (required) —</option>'];
  formsList.forEach((f) => {
    const id = f.form_id ?? f.id;
    opts.push(`<option value="${esc(id)}">${esc(f.name)}${f.status ? ` · ${esc(f.status)}` : ''}</option>`);
  });
  formSelect.innerHTML = opts.join('');
  formSelect.value = formId;
  formSelect.classList.toggle('pk-wf-need-form', !formId);
}

// ── Persistence ──────────────────────────────────────────────────────────────
// The backend now stores the full canvas graph (authoring source of truth) plus
// the flattened steps (runtime). localStorage is a fast cache / offline fallback.
async function restoreGraph() {
  const id = new URLSearchParams(location.search).get('id');
  if (id) {
    currentWorkflowId = id;
    // Prefer the server copy so the diagram round-trips across devices.
    try {
      const wf = await api.workflows.get(id);
      if (wf?.graph && Array.isArray(wf.graph.nodes)) {
        applyGraph({ ...wf.graph, name: wf.name, status: wf.status });
        return;
      }
      if (wf) { nameInput.value = wf.name ?? ''; formId = wf.form_id ?? ''; setStatus(wf.status ?? 'DRAFT'); }
    } catch { /* fall back to the local cache below */ }
  }

  const raw = id ? localStorage.getItem(graphKey(id)) : localStorage.getItem(DRAFT_KEY);
  if (raw) {
    try { applyGraph(JSON.parse(raw)); return; } catch { /* fall through */ }
  }
  if (!nodes.length) nodes = [{ ...blankNode('start'), x: 80, y: 80 }];
}

function applyGraph(g) {
  nodes = (g.nodes ?? []).map((n) => ({ w: SHAPES[n.type]?.w, h: SHAPES[n.type]?.h, ...n }));
  edges = (g.edges ?? []).map((e) => ({ id: e.id ?? uid('e'), label: '', ...e }));
  if (g.name != null && !nameInput.value) nameInput.value = g.name;
  if (g.formId) formId = g.formId;
  if (g.status) setStatus(g.status);
}

function persist(id) {
  const payload = JSON.stringify({
    nodes, edges, name: nameInput.value, formId, status: statusBadge.textContent,
  });
  localStorage.setItem(DRAFT_KEY, payload);
  if (id) localStorage.setItem(graphKey(id), payload);
}

function markDirty() {
  dirty = true;
  saveState.textContent = 'Unsaved changes';
  persist(currentWorkflowId);
}

// ── Node helpers ────────────────────────────────────────────────────────────
function blankNode(type) {
  const s = SHAPES[type];
  return { id: uid('n'), type, x: 200, y: 200, w: s.w, h: s.h, label: s.label, actorType: '', condition: '' };
}

function addNode(type, x, y) {
  if (SINGLETON[type] && nodes.some((n) => n.type === type)) {
    flash(`Only one ${SINGLETON[type]} node is allowed per workflow.`);
    return;
  }
  const s = SHAPES[type];
  const node = { ...blankNode(type), x: Math.max(0, x - s.w / 2), y: Math.max(0, y - s.h / 2) };
  nodes.push(node);
  sel = { kind: 'node', id: node.id };
  markDirty();
  render();
}

function deleteNode(id) {
  nodes = nodes.filter((n) => n.id !== id);
  edges = edges.filter((e) => e.from !== id && e.to !== id);
  if (sel?.id === id) sel = null;
  markDirty();
  render();
}

function deleteEdge(id) {
  edges = edges.filter((e) => e.id !== id);
  if (sel?.id === id) sel = null;
  markDirty();
  render();
}

function displayLabel(n) {
  if ((n.type === 'actor' || n.type === 'entry') && n.actorType) return n.actorType;
  return n.label || SHAPES[n.type].label;
}

// ── Render ──────────────────────────────────────────────────────────────────
function render() {
  canvas.querySelectorAll('.pk-wf-node, .pk-wf-edge-label').forEach((el) => el.remove());
  nodes.forEach((n) => canvas.appendChild(nodeEl(n)));
  drawEdges();
  renderProps();
}

const STICK_FIGURE = `
  <svg class="pk-wf-figure" width="40" height="56" viewBox="0 0 40 56" aria-hidden="true">
    <circle cx="20" cy="9" r="7"></circle>
    <line x1="20" y1="16" x2="20" y2="38"></line>
    <line x1="20" y1="22" x2="8"  y2="32"></line>
    <line x1="20" y1="22" x2="32" y2="32"></line>
    <line x1="20" y1="38" x2="10" y2="53"></line>
    <line x1="20" y1="38" x2="30" y2="53"></line>
  </svg>`;

function nodeEl(n) {
  const el = document.createElement('div');
  el.className = `pk-wf-node pk-wf-${n.type}${sel?.kind === 'node' && sel.id === n.id ? ' pk-wf-selected' : ''}`;
  el.dataset.id = n.id;
  el.style.cssText = `width:${n.w}px;height:${n.h}px;left:${n.x}px;top:${n.y}px`;
  const figure = n.type === 'entry' ? STICK_FIGURE : '';
  el.innerHTML = `
    <div class="pk-wf-shape">
      <span class="pk-wf-shape-inner" style="flex-direction:column">
        ${figure}<span class="pk-wf-shape-label">${esc(displayLabel(n))}</span>
      </span>
    </div>
    <div class="pk-wf-port" title="Drag to connect"></div>`;
  return el;
}

function center(n) { return { x: n.x + n.w / 2, y: n.y + n.h / 2 }; }

// Point where the line from the node centre toward (px,py) crosses the node box.
function rectEdge(n, px, py) {
  const cx = n.x + n.w / 2, cy = n.y + n.h / 2;
  const dx = px - cx, dy = py - cy;
  if (!dx && !dy) return { x: cx, y: cy };
  const scale = 1 / Math.max(Math.abs(dx) / (n.w / 2), Math.abs(dy) / (n.h / 2));
  return { x: cx + dx * scale, y: cy + dy * scale };
}

function drawEdges() {
  svg.querySelectorAll('.pk-wf-edge-path, .pk-wf-edge-hit').forEach((p) => p.remove());
  canvas.querySelectorAll('.pk-wf-edge-label').forEach((el) => el.remove());
  edges.forEach((e) => {
    const a = nodeById(e.from), b = nodeById(e.to);
    if (!a || !b) return;
    const ac = center(a), bc = center(b);
    const p1 = rectEdge(a, bc.x, bc.y);
    const p2 = rectEdge(b, ac.x, ac.y);
    const d = `M ${p1.x} ${p1.y} L ${p2.x} ${p2.y}`;

    const hit = document.createElementNS(SVG_NS, 'path');
    hit.setAttribute('class', 'pk-wf-edge-hit');
    hit.setAttribute('d', d);
    hit.dataset.edge = e.id;
    svg.appendChild(hit);

    const path = document.createElementNS(SVG_NS, 'path');
    const isSel = sel?.kind === 'edge' && sel.id === e.id;
    path.setAttribute('class', `pk-wf-edge-path${isSel ? ' pk-wf-edge-selected' : ''}`);
    path.setAttribute('marker-end', 'url(#wf-arrow)');
    path.setAttribute('d', d);
    svg.appendChild(path);

    if (e.label) {
      const chip = document.createElement('div');
      chip.className = `pk-wf-edge-label${isSel ? ' pk-wf-edge-selected' : ''}`;
      chip.style.left = `${(p1.x + p2.x) / 2}px`;
      chip.style.top = `${(p1.y + p2.y) / 2}px`;
      chip.dataset.edge = e.id;
      chip.textContent = e.label;
      canvas.appendChild(chip);
    }
  });
}

// ── Palette drag-and-drop ───────────────────────────────────────────────────
function bindPalette() {
  document.querySelectorAll('.pk-wf-palette-item').forEach((item) => {
    item.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/shape', item.dataset.shape);
      e.dataTransfer.effectAllowed = 'copy';
    });
  });
}

function bindCanvas() {
  canvas.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    canvas.classList.add('pk-wf-drag-over');
  });
  canvas.addEventListener('dragleave', () => canvas.classList.remove('pk-wf-drag-over'));
  canvas.addEventListener('drop', (e) => {
    e.preventDefault();
    canvas.classList.remove('pk-wf-drag-over');
    const shape = e.dataTransfer.getData('text/shape');
    if (!SHAPES[shape]) return;
    const p = screenToWorld(e.clientX, e.clientY);
    addNode(shape, p.x, p.y);
  });

  // Click empty canvas → deselect AND begin panning the viewport.
  canvas.addEventListener('pointerdown', (e) => {
    if (e.target === canvas || e.target === svg) {
      sel = null;
      render();
      pan = { startX: e.clientX, startY: e.clientY, panX0: panX, panY0: panY };
      canvas.classList.add('pk-wf-panning');
      canvas.setPointerCapture(e.pointerId);
    }
  });
  // Node move + connection start (event-delegated).
  canvas.addEventListener('pointerdown', onNodePointerDown);

  // Wheel: pan by default, zoom with Ctrl/Cmd (toward the cursor).
  viewport.addEventListener('wheel', (e) => {
    e.preventDefault();
    if (e.ctrlKey || e.metaKey) {
      zoomAt(e.clientX, e.clientY, zoom * (e.deltaY < 0 ? 1.1 : 0.9));
    } else {
      panX -= e.deltaX;
      panY -= e.deltaY;
      applyTransform();
    }
  }, { passive: false });

  document.getElementById('wf-zoom-in')?.addEventListener('click', () => zoomByButton(1.2));
  document.getElementById('wf-zoom-out')?.addEventListener('click', () => zoomByButton(1 / 1.2));
  document.getElementById('wf-zoom-reset')?.addEventListener('click', resetView);
  // Click an edge (or its label chip) → select it.
  svg.addEventListener('click', (e) => {
    const hit = e.target.closest('.pk-wf-edge-hit');
    if (hit) { sel = { kind: 'edge', id: hit.dataset.edge }; render(); }
  });
  canvas.addEventListener('click', (e) => {
    const chip = e.target.closest('.pk-wf-edge-label');
    if (chip) { sel = { kind: 'edge', id: chip.dataset.edge }; render(); }
  });
}

// ── Node move + connect + pan ─────────────────────────────────────────────────
let drag = null;       // { id, startX, startY, originX, originY, moved }
let connect = null;    // { from, tempPath }
let pan = null;        // { startX, startY, panX0, panY0 }

function onNodePointerDown(e) {
  const port = e.target.closest('.pk-wf-port');
  const nodeDiv = e.target.closest('.pk-wf-node');
  if (!nodeDiv) return;
  const id = nodeDiv.dataset.id;

  if (port) {
    // Begin a connection from this node.
    e.preventDefault();
    e.stopPropagation();
    const tempPath = document.createElementNS(SVG_NS, 'path');
    tempPath.setAttribute('class', 'pk-wf-edge-temp');
    svg.appendChild(tempPath);
    connect = { from: id, tempPath };
    canvas.setPointerCapture(e.pointerId);
    return;
  }

  // Begin a move (and select).
  sel = { kind: 'node', id };
  render();
  drag = { id, startX: e.clientX, startY: e.clientY, originX: nodeById(id).x, originY: nodeById(id).y, moved: false };
  canvas.setPointerCapture(e.pointerId);
}

canvas?.addEventListener('pointermove', (e) => {
  if (drag) {
    const n = nodeById(drag.id);
    if (!n) return;
    // Screen deltas are scaled by zoom; convert back to world units.
    n.x = Math.max(0, drag.originX + (e.clientX - drag.startX) / zoom);
    n.y = Math.max(0, drag.originY + (e.clientY - drag.startY) / zoom);
    if (Math.abs(e.clientX - drag.startX) + Math.abs(e.clientY - drag.startY) > 3) drag.moved = true;
    const el = canvas.querySelector(`.pk-wf-node[data-id="${drag.id}"]`);
    if (el) { el.style.left = n.x + 'px'; el.style.top = n.y + 'px'; }
    drawEdges();
  } else if (connect) {
    const p = screenToWorld(e.clientX, e.clientY);
    const from = center(nodeById(connect.from));
    connect.tempPath.setAttribute('d', `M ${from.x} ${from.y} L ${p.x} ${p.y}`);
  } else if (pan) {
    panX = pan.panX0 + (e.clientX - pan.startX);
    panY = pan.panY0 + (e.clientY - pan.startY);
    applyTransform();
  }
});

canvas?.addEventListener('pointerup', (e) => {
  if (drag) {
    if (drag.moved) markDirty();
    drag = null;
  } else if (connect) {
    const target = document.elementFromPoint(e.clientX, e.clientY)?.closest('.pk-wf-node');
    const to = target?.dataset.id;
    if (to && to !== connect.from && !edges.some((ed) => ed.from === connect.from && ed.to === to)) {
      edges.push({ id: uid('e'), from: connect.from, to, label: '' });
      markDirty();
    }
    connect.tempPath.remove();
    connect = null;
    render();
  } else if (pan) {
    pan = null;
    canvas.classList.remove('pk-wf-panning');
  }
});

// ── Properties panel ────────────────────────────────────────────────────────
function renderProps() {
  const body = document.getElementById('wf-props-body');
  if (sel?.kind === 'edge') return renderEdgeProps(body, selEdge());
  const n = selNode();
  if (!n) {
    body.innerHTML = '<p class="pk-wf-props-empty">Select a node or arrow to edit it.</p>';
    return;
  }

  const actorList = actorTypes.map((a) => `<option value="${esc(a)}">`).join('');
  const labelField = `
    <label class="pk-wf-field-label">Label</label>
    <input class="pk-input" id="pf-label" value="${esc(n.label)}" placeholder="${esc(SHAPES[n.type].label)}">`;

  let typeFields = '';
  if (n.type === 'entry' || n.type === 'actor') {
    typeFields = `
      <div style="margin-top:1rem">
        <label class="pk-wf-field-label">Actor Type</label>
        <input class="pk-input" id="pf-actor" list="wf-actor-types" value="${esc(n.actorType)}"
          placeholder="${n.type === 'entry' ? 'e.g. Patient' : 'e.g. Triage Nurse'}">
        <datalist id="wf-actor-types">${actorList}</datalist>
        <p class="t-fine" style="color:var(--text-muted);margin-top:0.375rem">Maps to the <strong>staff</strong> system role.</p>
      </div>`;
  } else if (n.type === 'condition') {
    typeFields = `
      <div style="margin-top:1rem">
        <label class="pk-wf-field-label">Condition Expression</label>
        <input class="pk-input" id="pf-condition" value="${esc(n.condition)}" placeholder="e.g. amount > 1000">
        <p class="t-fine" style="color:var(--text-muted);margin-top:0.375rem">
          Draw two arrows out of this node and label them <strong>Yes</strong> / <strong>No</strong>
          (the "No" branch is the loop exit).
        </p>
      </div>`;
  }

  const noConfig = (n.type === 'start' || n.type === 'end')
    ? `<p class="t-fine" style="color:var(--text-muted);margin-top:1rem">${n.type === 'start' ? 'Start' : 'End / result'} node — no extra configuration.</p>`
    : '';

  body.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem">
      <span class="pk-badge pk-badge-info">${n.type}</span>
      <button id="pf-delete" class="pk-btn-danger">Delete</button>
    </div>
    ${labelField}
    ${typeFields}
    ${noConfig}`;

  body.querySelector('#pf-label')?.addEventListener('input', (e) => { n.label = e.target.value; markDirty(); refreshNode(n.id); });
  body.querySelector('#pf-actor')?.addEventListener('input', (e) => { n.actorType = e.target.value; markDirty(); refreshNode(n.id); });
  body.querySelector('#pf-condition')?.addEventListener('input', (e) => { n.condition = e.target.value; markDirty(); });
  body.querySelector('#pf-delete')?.addEventListener('click', () => deleteNode(n.id));
}

function renderEdgeProps(body, edge) {
  if (!edge) { body.innerHTML = '<p class="pk-wf-props-empty">Select a node or arrow to edit it.</p>'; return; }
  const from = nodeById(edge.from), to = nodeById(edge.to);
  const presets = ['Yes', 'No', 'If', 'Else'];
  body.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem">
      <span class="pk-badge pk-badge-neutral">arrow</span>
      <button id="pf-edge-delete" class="pk-btn-danger">Delete</button>
    </div>
    <p class="t-fine" style="color:var(--text-muted);margin-bottom:1rem">
      ${esc(from ? displayLabel(from) : '?')} → ${esc(to ? displayLabel(to) : '?')}
    </p>
    <label class="pk-wf-field-label">Branch label</label>
    <input class="pk-input" id="pf-edge-label" value="${esc(edge.label)}" placeholder="e.g. Yes / No">
    <div style="display:flex;flex-wrap:wrap;gap:0.375rem;margin-top:0.625rem">
      ${presets.map((p) => `<button type="button" class="pk-btn-secondary pf-edge-preset" data-v="${p}" style="padding:0.25rem 0.75rem;min-height:32px;font-size:13px">${p}</button>`).join('')}
    </div>`;

  body.querySelector('#pf-edge-label')?.addEventListener('input', (e) => { edge.label = e.target.value; markDirty(); drawEdges(); });
  body.querySelector('#pf-edge-delete')?.addEventListener('click', () => deleteEdge(edge.id));
  body.querySelectorAll('.pf-edge-preset').forEach((btn) => {
    btn.addEventListener('click', () => { edge.label = btn.dataset.v; markDirty(); render(); });
  });
}

// Re-render just one node's label without rebuilding the whole canvas.
function refreshNode(id) {
  const el = canvas.querySelector(`.pk-wf-node[data-id="${id}"] .pk-wf-shape-label`);
  const n = nodeById(id);
  if (el && n) el.textContent = displayLabel(n);
  drawEdges();
}

// ── Keyboard ────────────────────────────────────────────────────────────────
function bindKeyboard() {
  document.addEventListener('keydown', (e) => {
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;
    if ((e.key === 'Delete' || e.key === 'Backspace') && sel) {
      e.preventDefault();
      if (sel.kind === 'edge') deleteEdge(sel.id); else deleteNode(sel.id);
    }
  });
}

// ── Toolbar: back / form / save / publish ───────────────────────────────────
function bindToolbar() {
  document.getElementById('wf-back').addEventListener('click', () => {
    window.location.href = 'admin.html#workflows';
  });
  nameInput.addEventListener('input', () => markDirty());
  formSelect.addEventListener('change', () => {
    formId = formSelect.value;
    formSelect.classList.toggle('pk-wf-need-form', !formId);
    markDirty();
  });
  document.getElementById('wf-save').addEventListener('click', () => save(false));
  document.getElementById('wf-publish').addEventListener('click', () => save(true));
}

function setStatus(status) {
  statusBadge.textContent = status;
  statusBadge.className = `pk-badge ${status === 'PUBLISHED' ? 'pk-badge-success' : 'pk-badge-neutral'}`;
  // A published workflow is immutable — disable saving/publishing.
  const locked = status === 'PUBLISHED';
  document.getElementById('wf-save').disabled = locked;
  document.getElementById('wf-publish').disabled = locked;
  if (locked) saveState.textContent = 'Published — locked. Create a new version to edit.';
}

function flash(msg) {
  saveState.style.color = 'var(--state-error)';
  saveState.textContent = msg;
  setTimeout(() => { saveState.style.color = 'var(--text-muted)'; }, 4000);
}

// Hard rules: linked form + exactly one Start / Entry User / End.
function validate() {
  const problems = [];
  if (!formId) problems.push('link a form');
  for (const [type, label] of Object.entries(SINGLETON)) {
    const count = nodes.filter((n) => n.type === type).length;
    if (count !== 1) problems.push(`have exactly one ${label} (found ${count})`);
  }
  return problems;
}

// Order the actor/entry nodes by walking edges from Start; fall back to vertical
// position. Back-edges (loops) are naturally bounded by the visited set.
function orderedStepNodes() {
  const start = nodes.find((n) => n.type === 'start');
  const visited = new Set();
  const order = [];
  const walk = (id) => {
    if (!id || visited.has(id)) return;
    visited.add(id);
    const n = nodeById(id);
    if (n && (n.type === 'entry' || n.type === 'actor')) order.push(n);
    edges.filter((e) => e.from === id).forEach((e) => walk(e.to));
  };
  if (start) walk(start.id);
  nodes.filter((n) => (n.type === 'entry' || n.type === 'actor') && !visited.has(n.id))
    .sort((a, b) => a.y - b.y)
    .forEach((n) => order.push(n));
  return order;
}

function buildSteps() {
  const stepNodes = orderedStepNodes();
  // The backend validator requires exactly one terminal step, so only the last
  // step in traversal order is marked terminal (there is one End node).
  return stepNodes.map((n, i) => ({
    step_name: (n.label || n.actorType || SHAPES[n.type].label).slice(0, 200),
    assigned_role: n.type === 'entry' ? 'end_user' : 'staff',
    step_order: i + 1,
    is_terminal: i === stepNodes.length - 1,
  }));
}

async function save(publish) {
  const name = nameInput.value.trim();
  if (!name) { flash('Give the workflow a name first.'); nameInput.focus(); return; }

  const problems = validate();
  if (problems.length) { flash(`Before saving: ${problems.join('; ')}.`); return; }

  const steps = buildSteps();
  const graph = { nodes, edges, formId };
  saveState.style.color = 'var(--text-muted)';
  saveState.textContent = 'Saving…';
  try {
    if (!currentWorkflowId) {
      const res = await api.workflows.create({ name, description: '', form_id: formId, steps, graph });
      currentWorkflowId = res?.id ?? res?.workflow_id ?? null;
    } else {
      // Re-sync the whole draft: the backend replaces steps and stores the graph.
      await api.workflows.update(currentWorkflowId, { name, form_id: formId, steps, graph });
    }

    if (publish && currentWorkflowId) {
      await api.workflows.publish(currentWorkflowId);
      setStatus('PUBLISHED');
    }

    dirty = false;
    persist(currentWorkflowId);
    saveState.textContent = publish ? 'Published ✓' : 'Saved ✓';
    if (publish) setTimeout(() => { window.location.href = 'admin.html#workflows'; }, 600);
  } catch (err) {
    flash(`Could not ${publish ? 'publish' : 'save'}: ${err.message}`);
  }
}

// Warn before leaving with unsaved changes.
window.addEventListener('beforeunload', (e) => {
  if (dirty) { e.preventDefault(); e.returnValue = ''; }
});

init();
