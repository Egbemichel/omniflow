import { api } from './api.js';
import { auth } from './auth.js';

function extractFormId() {
  const pathMatch = window.location.pathname.match(/\/submit\/([^/]+)/);
  if (pathMatch) return pathMatch[1];
  return new URLSearchParams(window.location.search).get('form_id');
}

// HTML-escape for both text content and quoted attribute values. Labels/options
// come from OCR, so treat them as untrusted.
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

// Maps a field_type to a plain <input type="…">. Choice/multiline types are
// handled separately in controlFor().
function fieldInputType(fieldType) {
  const map = { date: 'date', time: 'time', number: 'number', email: 'email', phone: 'tel' };
  return map[fieldType] || 'text';
}

function showError(msg) {
  document.getElementById('error-msg').textContent = msg;
  document.getElementById('error-panel').classList.remove('hidden');
  document.getElementById('form-panel').classList.add('hidden');
}

function showStatus(submissionId) {
  document.getElementById('form-panel').classList.add('hidden');
  document.getElementById('status-panel').classList.remove('hidden');
  document.getElementById('submission-ref').textContent = submissionId.substring(0, 8).toUpperCase();
  if (window.lucide) lucide.createIcons();
}

// Builds the input control(s) for one field based on its type.
// select/radio/checkbox use f.options (array of strings) when available;
// without options, select/radio gracefully fall back to a text input and
// checkbox becomes a single yes/no toggle.
function controlFor(f) {
  const type = f.field_type;
  const req = f.required ? 'required' : '';
  const options = Array.isArray(f.options)
    ? f.options.map((o) => String(o)).filter((o) => o.trim())
    : [];

  if (type === 'select' && options.length) {
    return `<select data-input class="pk-input" ${req}>
        <option value="">Select…</option>
        ${options.map((o) => `<option value="${esc(o)}">${esc(o)}</option>`).join('')}
      </select>`;
  }

  if (type === 'radio' && options.length) {
    return `<div class="flex flex-col gap-2" style="margin-top:0.25rem">
        ${options.map((o) => `
          <label class="flex items-center gap-2" style="cursor:pointer">
            <input type="radio" name="opt-${esc(f.id)}" value="${esc(o)}" ${req}>
            <span class="t-body" style="color:var(--text-primary)">${esc(o)}</span>
          </label>`).join('')}
      </div>`;
  }

  if (type === 'checkbox' && options.length) {
    return `<div class="flex flex-col gap-2" style="margin-top:0.25rem">
        ${options.map((o) => `
          <label class="flex items-center gap-2" style="cursor:pointer">
            <input type="checkbox" value="${esc(o)}">
            <span class="t-body" style="color:var(--text-primary)">${esc(o)}</span>
          </label>`).join('')}
      </div>`;
  }

  if (type === 'checkbox') {
    // Single yes/no toggle when there are no discrete options.
    return `<label class="flex items-center gap-2" style="cursor:pointer;margin-top:0.25rem">
        <input type="checkbox" data-input ${req}>
        <span class="t-body" style="color:var(--text-muted)">Yes</span>
      </label>`;
  }

  if (type === 'signature') {
    return `<div class="pk-signature-wrap" style="margin-top:0.25rem">
        <canvas class="pk-signature-pad"></canvas>
        <button type="button" class="pk-btn-link" style="margin-top:0.25rem"
          onclick="clearSignature(this)">Clear</button>
      </div>`;
  }

  if (type === 'textarea') {
    return `<textarea data-input rows="3" class="pk-input" ${req}></textarea>`;
  }

  // text, number, date, time, email, phone — plus select/radio fallback.
  return `<input type="${fieldInputType(type)}" data-input class="pk-input" ${req}>`;
}

function renderForm(schema) {
  const nameEl = document.getElementById('form-name');
  if (nameEl) nameEl.textContent = schema.name || 'Form';

  const container = document.getElementById('form-fields');
  if (!schema.fields || schema.fields.length === 0) {
    container.innerHTML = '<p class="pk-empty">This form has no fields.</p>';
  } else {
    container.innerHTML = schema.fields.map((f) => `
      <div class="pk-field"
           data-field-id="${esc(f.id)}"
           data-field-name="${esc(f.field_name)}"
           data-field-type="${esc(f.field_type)}"
           data-required="${f.required ? 'true' : 'false'}">
        <label class="block t-caption-strong mb-1" style="color:var(--text-muted)">
          ${esc(f.field_name)}${f.required ? ' <span style="color:var(--state-error)">*</span>' : ''}
        </label>
        ${controlFor(f)}
      </div>
    `).join('');
  }

  document.getElementById('form-panel').classList.remove('hidden');
  // Canvas needs a laid-out box to size itself, so init after the panel is shown.
  initSignaturePads();
}

// Reads the submitted value from one field wrapper, handling each widget type.
function collectField(wrapper) {
  const type = wrapper.dataset.fieldType;
  let value = null;

  if (type === 'radio') {
    const checked = wrapper.querySelector('input[type="radio"]:checked');
    value = checked ? checked.value : null;
  } else if (type === 'checkbox') {
    const boxes = wrapper.querySelectorAll('input[type="checkbox"]');
    if (boxes.length > 1) {
      const vals = Array.from(boxes).filter((b) => b.checked).map((b) => b.value);
      value = vals.length ? vals.join(', ') : null;
    } else {
      const box = boxes[0];
      value = box && box.checked ? 'Yes' : null;
    }
  } else if (type === 'signature') {
    const canvas = wrapper.querySelector('canvas.pk-signature-pad');
    value = canvas && canvas.dataset.signed === 'true' ? canvas.toDataURL('image/png') : null;
  } else {
    const control = wrapper.querySelector('[data-input]');
    value = control && control.value.trim() ? control.value : null;
  }

  return {
    field_id: wrapper.dataset.fieldId,
    field_name: wrapper.dataset.fieldName,
    value,
  };
}

// ── Signature pad ───────────────────────────────────────────────────────────
// Vanilla pointer-event drawing (touch + mouse + pen), no library.
function initSignaturePads() {
  document.querySelectorAll('canvas.pk-signature-pad').forEach(setupSignaturePad);
}

function setupSignaturePad(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, rect.width) * ratio;
  canvas.height = Math.max(1, rect.height) * ratio;

  const ctx = canvas.getContext('2d');
  ctx.scale(ratio, ratio);
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = '#111111';

  let drawing = false;
  let last = null;

  const point = (e) => {
    const r = canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };

  canvas.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    drawing = true;
    last = point(e);
    canvas.setPointerCapture?.(e.pointerId);
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!drawing) return;
    e.preventDefault();
    const p = point(e);
    ctx.beginPath();
    ctx.moveTo(last.x, last.y);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    last = p;
    canvas.dataset.signed = 'true';
  });
  const stop = () => { drawing = false; };
  canvas.addEventListener('pointerup', stop);
  canvas.addEventListener('pointerleave', stop);
}

window.clearSignature = (btn) => {
  const canvas = btn.closest('.pk-signature-wrap')?.querySelector('canvas.pk-signature-pad');
  if (!canvas) return;
  canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
  canvas.dataset.signed = '';
};

async function init() {
  const formId = extractFormId();
  if (!formId) {
    showError('No form specified. Please scan the QR code again.');
    return;
  }
  try {
    const schema = await api.formPublic.schema(formId);
    renderForm(schema);
  } catch {
    showError('Could not load the form. It may no longer be available.');
  }
}

document.getElementById('submit-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formId = extractFormId();
  const btn = document.getElementById('submit-btn');

  const wrappers = Array.from(e.target.querySelectorAll('.pk-field'));

  // Required-field validation (works across all widget types).
  const missing = wrappers.filter(
    (w) => w.dataset.required === 'true' && !collectField(w).value
  );
  if (missing.length > 0) {
    const first = missing[0];
    first.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const control = first.querySelector('[data-input], input, canvas');
    if (control) {
      control.focus?.();
      control.classList.add('pk-input-error');
    }
    return;
  }

  btn.textContent = 'Submitting…';
  btn.disabled = true;

  const fieldValues = wrappers.map(collectField);

  // If the submitter is signed in, tag the submission with their id so it shows
  // up on their dashboard and they receive progress notifications. Anonymous QR
  // submissions (no session) stay anonymous and are tracked by reference number.
  const submitter_id = auth.getUser()?.sub || null;

  try {
    const result = await api.formPublic.submit(formId, { field_values: fieldValues, submitter_id });
    if (result?.submission_id) {
      showStatus(result.submission_id);
    } else {
      throw new Error('Unexpected response');
    }
  } catch {
    btn.textContent = 'Submit';
    btn.disabled = false;
    alert('Submission failed. Please check your connection and try again.');
  }
});

document.addEventListener('focusin', (e) => {
  if (e.target.classList?.contains('pk-input-error')) {
    e.target.classList.remove('pk-input-error');
  }
});

init();
