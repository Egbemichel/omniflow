// Shared renderer for viewing a submitted form from its schema, pre-filled with
// the submission's saved values. Used by dashboard.html (read-only) and
// staff.html (editable). Mirrors the widgets of the public submission page.

import { api } from './api.js';

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function inputType(t) {
  return ({ date: 'date', time: 'time', number: 'number', email: 'email', phone: 'tel' }[t]) || 'text';
}

function controlFor(f, value, editable) {
  const type = f.field_type;
  const dis = editable ? '' : 'disabled';
  const v = value == null ? '' : String(value);
  const options = Array.isArray(f.options)
    ? f.options.map((o) => String(o)).filter((o) => o.trim())
    : [];

  if (type === 'select' && options.length) {
    return `<select data-input class="pk-input" ${dis}>
        <option value="">Select…</option>
        ${options.map((o) => `<option value="${esc(o)}"${o === v ? ' selected' : ''}>${esc(o)}</option>`).join('')}
      </select>`;
  }
  if (type === 'radio' && options.length) {
    return `<div class="flex flex-col gap-2" style="margin-top:0.25rem">
        ${options.map((o) => `
          <label class="flex items-center gap-2" style="cursor:pointer">
            <input type="radio" name="opt-${esc(f.field_name)}" value="${esc(o)}"${o === v ? ' checked' : ''} ${dis}>
            <span class="t-body" style="color:var(--text-primary)">${esc(o)}</span>
          </label>`).join('')}
      </div>`;
  }
  if (type === 'checkbox' && options.length) {
    const selected = v.split(',').map((s) => s.trim());
    return `<div class="flex flex-col gap-2" style="margin-top:0.25rem">
        ${options.map((o) => `
          <label class="flex items-center gap-2" style="cursor:pointer">
            <input type="checkbox" value="${esc(o)}"${selected.includes(o) ? ' checked' : ''} ${dis}>
            <span class="t-body" style="color:var(--text-primary)">${esc(o)}</span>
          </label>`).join('')}
      </div>`;
  }
  if (type === 'checkbox') {
    return `<label class="flex items-center gap-2" style="cursor:pointer;margin-top:0.25rem">
        <input type="checkbox" data-input${v === 'Yes' ? ' checked' : ''} ${dis}>
        <span class="t-body" style="color:var(--text-muted)">Yes</span>
      </label>`;
  }
  if (type === 'signature') {
    return v.startsWith('data:image')
      ? `<img src="${esc(v)}" alt="signature" style="max-height:90px;border:1px solid var(--border-default);border-radius:8px;background:var(--bg-surface);margin-top:0.25rem">`
      : '<p class="t-caption" style="color:var(--text-muted)">No signature</p>';
  }
  if (type === 'textarea') {
    return `<textarea data-input rows="3" class="pk-input" ${dis}>${esc(v)}</textarea>`;
  }
  return `<input type="${inputType(type)}" data-input class="pk-input" value="${esc(v)}" ${dis}>`;
}

// Render the form into `container`. `fields` is the schema's field list;
// `values` is the submission's { field_name: value } map.
export function renderForm(container, fields, values, { editable } = {}) {
  values = values || {};
  if (!fields || !fields.length) {
    container.innerHTML = '<p class="pk-empty">This form has no fields.</p>';
    return;
  }
  container.innerHTML = fields.map((f) => `
    <div class="pk-field" data-field-name="${esc(f.field_name)}" data-field-type="${esc(f.field_type)}">
      <label class="block t-caption-strong mb-1" style="color:var(--text-muted)">
        ${esc(f.field_name)}${f.required ? ' <span style="color:var(--state-error)">*</span>' : ''}
      </label>
      ${controlFor(f, values[f.field_name], editable)}
    </div>`).join('');
}

// Fetch the form's schema and render it pre-filled from a submission's status
// ({ form_id, form_data }). Falls back to value-derived text fields if the
// schema can't be fetched. Used by both the dashboard and staff detail views.
export async function renderSubmittedForm(container, status, { editable } = {}) {
  const values = (status && status.form_data) || {};
  let fields = null;
  if (status && status.form_id) {
    try {
      const schema = await api.formPublic.schema(status.form_id);
      fields = (schema && schema.fields) || null;
    } catch { /* schema unavailable — fall back below */ }
  }
  if (!fields || !fields.length) {
    fields = Object.keys(values).map((name) => ({ field_name: name, field_type: 'text' }));
  }
  renderForm(container, fields, values, { editable });
}

// Read the (possibly edited) values back out as a { field_name: value } map.
export function collectForm(container) {
  const out = {};
  container.querySelectorAll('.pk-field').forEach((w) => {
    const name = w.dataset.fieldName;
    const type = w.dataset.fieldType;
    let value = '';
    if (type === 'radio') {
      const c = w.querySelector('input[type="radio"]:checked');
      value = c ? c.value : '';
    } else if (type === 'checkbox') {
      const boxes = w.querySelectorAll('input[type="checkbox"]');
      value = boxes.length > 1
        ? Array.from(boxes).filter((b) => b.checked).map((b) => b.value).join(', ')
        : (boxes[0] && boxes[0].checked ? 'Yes' : '');
    } else if (type === 'signature') {
      const img = w.querySelector('img');
      value = img ? img.getAttribute('src') : '';
    } else {
      const c = w.querySelector('[data-input]');
      value = c ? c.value : '';
    }
    out[name] = value;
  });
  return out;
}
