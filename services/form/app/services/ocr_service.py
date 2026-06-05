"""Form field extraction via the Gemini 2.5 Flash vision API.

The uploaded file (PDF or image) already lives on disk in the Form Service's
persistent volume. We rasterise PDFs page-by-page (pdf2image), send the
image(s) inline to Gemini, and ask for a structured field list. The model both
reads the labels and infers the most appropriate input type per field, so the
end-user form can render the right widget (date picker, number, etc.).

`extract_fields` returns the row shape `FormRepository.replace_fields` expects:
`{field_name, field_type, required, position}`. The Gemini network call lives in
`_call_gemini`, isolated so tests mock it at the service-method level.
"""

import io
import json
import os
from typing import List

from app.utils.config import get_gemini_api_key, get_gemini_model

# Input widgets the end-user renderer can produce. Gemini is asked to use these
# names, but we normalise common synonyms defensively.
_ALLOWED_TYPES = {
    "text",
    "textarea",
    "number",
    "date",
    "time",
    "email",
    "phone",
    "select",
    "radio",
    "checkbox",
    "signature",
}

_TYPE_ALIASES = {
    "datepicker": "date",
    "datetime": "date",
    "dob": "date",
    "integer": "number",
    "numeric": "number",
    "decimal": "number",
    "age": "number",
    "e-mail": "email",
    "mail": "email",
    "tel": "phone",
    "telephone": "phone",
    "mobile": "phone",
    "phone_number": "phone",
    "paragraph": "textarea",
    "multiline": "textarea",
    "long_text": "textarea",
    "address": "textarea",
    "dropdown": "select",
    "choice": "select",
    "boolean": "checkbox",
    "checkbox_group": "checkbox",
    "option": "radio",
    "radio_group": "radio",
}

_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
}

_PROMPT = """You are a form digitisation assistant for Paper Killer, a platform \
that converts institutional paper forms — from hospitals, schools and government \
offices — into digital forms. The attached image(s) are ONE form (it may span \
multiple page images).

Extract EVERY visible field a person is meant to fill in, as a JSON array.

Return ONLY valid JSON, no markdown fences, in exactly this shape:
{"fields": [
  {"label": "<field name / question>",
   "value": "<pre-filled content, or empty string if blank>",
   "field_type": "<type>",
   "options": ["<choice>", ...],
   "confidence": "low"}
]}

field_type MUST be one of: text, textarea, number, date, time, email, phone, \
select, radio, checkbox, signature.

Rules:
- READING ORDER: output fields top-left to bottom-right, then continue with the \
next column. Keep that order in the array.
- Treat a multi-word label as ONE field ("Date of Birth" is one field, not three).
- Dates / "date of birth" -> date. Age / quantity / amount / count -> number. \
Email -> email. Phone / mobile / tel -> phone.
- SIGNATURES: a blank signing space IS an input — never skip it. Detect ruled \
lines, empty boxes, or captions such as "Signature", "Sign here", "Signed", \
"Authorized by", "Approved by", "Parent/Guardian signature" or "Witness". Use \
field_type "signature"; set "value" to "signed" if ink is visibly present, else \
"". Split a combined caption: "Signature & Date" -> two fields (signature + \
date); "Name & Signature" -> text + signature.
- CHECKBOXES: use field_type "checkbox" and set "value" to "checked" or \
"unchecked" depending on whether the box is marked.
- "Sex", "Gender", "Marital status" or any set of mutually exclusive options \
-> radio (question as the label). A fixed list of choices / dropdown -> select. \
For select, radio and multi-choice checkbox groups, list the printed choices in \
"options"; use an empty list [] otherwise.
- Long free text, address, comments -> textarea. Everything else -> text.
- TABLES: flatten every fillable cell into its own field. Label each cell \
"TableName_RowN_ColName" (e.g. "Medications_Row1_Dosage") using the table's \
heading/caption as TableName, the 1-based row number as RowN, and the column \
header as ColName.
- CONFIDENCE: only include the "confidence" key, set to "low", for fields you are \
unsure about (blurred text, ambiguous label or type). Omit the key entirely when \
you are confident.
- Ignore decorative text, page numbers and printed instructions that are not \
inputs — but a signature line or box IS an input, never skip it."""


# Used for the single retry when the first response is not valid JSON.
_STRICT_PROMPT = _PROMPT + """

CRITICAL: Your previous reply could not be parsed as JSON. Reply with VALID JSON \
ONLY — a single JSON object matching the shape above. No prose, no markdown, no \
code fences, no comments, no trailing commas. Output nothing but the JSON object."""


class OCRError(Exception):
    """Raised when the Gemini extraction cannot be completed."""


class OCRService:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key if api_key is not None else get_gemini_api_key()
        self._model = model or get_gemini_model()

    # ── Public API ──────────────────────────────────────────────────────────
    def extract_fields(self, file_path: str) -> List[dict]:
        """Extract form fields from the file at `file_path`.

        Returns rows ready for `FormRepository.replace_fields`.
        """
        raw = self._call_gemini(file_path)
        return self._map_fields(raw)

    # ── Gemini call + retry orchestration ───────────────────────────────────
    def _call_gemini(self, file_path: str) -> dict:
        """Render the page image(s) and ask Gemini for the structured fields.

        If the first reply is not valid JSON, retry exactly once with a stricter
        prompt. If the retry is also unparseable, the OCRError propagates — the
        background task then marks the form FAILED and publishes a failed event.
        """
        if not self._api_key:
            raise OCRError("GEMINI_API_KEY is not configured")

        blobs = self._load_image_blobs(file_path)
        try:
            return self._parse_json(self._generate(_PROMPT, blobs))
        except OCRError:
            # One stricter retry demanding valid JSON only.
            return self._parse_json(self._generate(_STRICT_PROMPT, blobs))

    def _generate(self, prompt: str, blobs: List[tuple]) -> str:
        """One Gemini request returning the raw text reply. Network boundary —
        mocked in tests."""
        # Imported lazily so unit tests (which mock this method) need neither
        # the SDK nor poppler installed.
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(self._model)

        parts: list = [prompt]
        for mime_type, data in blobs:
            parts.append({"mime_type": mime_type, "data": data})

        try:
            response = model.generate_content(
                parts,
                generation_config={"response_mime_type": "application/json"},
            )
            return response.text
        except Exception as exc:  # pragma: no cover - network/SDK errors
            raise OCRError(f"Gemini request failed: {exc}") from exc

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _load_image_blobs(self, file_path: str) -> List[tuple]:
        """Return `(mime_type, raw_bytes)` for each page/image.

        PDFs are rasterised to one PNG per page; images are read as-is. The SDK
        transmits these as base64 inline_data parts.
        """
        if file_path.lower().endswith(".pdf"):
            from pdf2image import convert_from_path

            blobs = []
            for page in convert_from_path(file_path):
                buf = io.BytesIO()
                page.save(buf, format="PNG")
                blobs.append(("image/png", buf.getvalue()))
            if not blobs:
                raise OCRError("PDF produced no pages")
            return blobs

        with open(file_path, "rb") as handle:
            data = handle.read()
        ext = os.path.splitext(file_path)[1].lower()
        return [(_MIME_BY_EXT.get(ext, "image/png"), data)]

    @staticmethod
    def _parse_json(text: str) -> dict:
        cleaned = (text or "").strip()
        # Strip ```json fences if the model added them despite the JSON mime ask.
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```", 2)[1]
            if cleaned.lstrip().lower().startswith("json"):
                cleaned = cleaned.lstrip()[4:]
            cleaned = cleaned.strip("` \n")
        try:
            parsed = json.loads(cleaned)
        except (ValueError, TypeError) as exc:
            raise OCRError("Gemini returned non-JSON output") from exc
        if not isinstance(parsed, dict):
            raise OCRError("Gemini JSON is not an object")
        return parsed

    @classmethod
    def _normalise_type(cls, raw_type) -> str:
        value = str(raw_type or "").strip().lower()
        value = _TYPE_ALIASES.get(value, value)
        return value if value in _ALLOWED_TYPES else "text"

    @classmethod
    def _map_fields(cls, raw: dict) -> List[dict]:
        fields = raw.get("fields") if isinstance(raw, dict) else None
        if not isinstance(fields, list):
            return []

        rows: List[dict] = []
        for field in fields:
            if not isinstance(field, dict):
                continue
            label = str(field.get("label") or "").strip()
            if not label:
                continue
            rows.append(
                {
                    "field_name": label,
                    "field_type": cls._normalise_type(field.get("field_type")),
                    "required": bool(field.get("required", False)),
                    "position": len(rows),
                    "options": cls._clean_options(field.get("options")),
                }
            )
        return rows

    @staticmethod
    def _clean_options(raw) -> list | None:
        """Normalise a choice list to non-empty strings, or None when absent."""
        if not isinstance(raw, list):
            return None
        cleaned = [str(o).strip() for o in raw if str(o).strip()]
        return cleaned or None
