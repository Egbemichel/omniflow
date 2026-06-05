"""OCR service tests.

The Gemini network call (`OCRService._call_gemini`) is mocked at the service
method level — we never touch the SDK or the HTTP layer. These tests exercise
the response-to-rows mapping, type normalisation, and error handling.
"""

import pytest

from app.services.ocr_service import OCRError, OCRService


def _service():
    # api_key supplied so construction never depends on the environment;
    # _call_gemini is mocked in every test, so the key is otherwise unused.
    return OCRService(api_key="test-key")


def test_extract_fields_maps_gemini_response(monkeypatch):
    def fake_call(self, file_path):
        return {
            "fields": [
                {"label": "Full Name", "value": "", "field_type": "text"},
                {"label": "Date of Birth", "value": "", "field_type": "date"},
                {"label": "Age", "value": "", "field_type": "number"},
            ]
        }

    monkeypatch.setattr(OCRService, "_call_gemini", fake_call)

    fields = _service().extract_fields("/uploads/1/form.png")

    assert [f["field_name"] for f in fields] == ["Full Name", "Date of Birth", "Age"]
    assert [f["field_type"] for f in fields] == ["text", "date", "number"]
    assert [f["position"] for f in fields] == [0, 1, 2]
    assert all(f["required"] is False for f in fields)


def test_extract_fields_normalises_type_synonyms(monkeypatch):
    def fake_call(self, file_path):
        return {
            "fields": [
                {"label": "DOB", "field_type": "datepicker"},
                {"label": "Email Address", "field_type": "e-mail"},
                {"label": "Mobile", "field_type": "telephone"},
                {"label": "Comments", "field_type": "paragraph"},
                {"label": "Sex", "field_type": "radio_group"},
                {"label": "Mystery", "field_type": "something-weird"},
            ]
        }

    monkeypatch.setattr(OCRService, "_call_gemini", fake_call)

    types = [f["field_type"] for f in _service().extract_fields("/uploads/1/x.png")]

    assert types == ["date", "email", "phone", "textarea", "radio", "text"]


def test_extract_fields_carries_and_cleans_options(monkeypatch):
    def fake_call(self, file_path):
        return {
            "fields": [
                {"label": "Sex", "field_type": "radio", "options": ["Male", "Female", "  "]},
                {"label": "Country", "field_type": "select", "options": ["NG", "CM"]},
                {"label": "Full Name", "field_type": "text", "options": []},
                {"label": "Subscribe", "field_type": "checkbox"},
            ]
        }

    monkeypatch.setattr(OCRService, "_call_gemini", fake_call)

    fields = _service().extract_fields("/uploads/1/x.png")
    assert fields[0]["options"] == ["Male", "Female"]  # blank choice dropped
    assert fields[1]["options"] == ["NG", "CM"]
    assert fields[2]["options"] is None  # empty list -> None
    assert fields[3]["options"] is None  # missing -> None


def test_extract_fields_honours_required_flag(monkeypatch):
    def fake_call(self, file_path):
        return {
            "fields": [
                {"label": "Required Field", "field_type": "text", "required": True},
                {"label": "Optional Field", "field_type": "text"},
            ]
        }

    monkeypatch.setattr(OCRService, "_call_gemini", fake_call)

    fields = _service().extract_fields("/uploads/1/x.png")
    assert fields[0]["required"] is True
    assert fields[1]["required"] is False


def test_extract_fields_skips_blank_labels_and_reindexes(monkeypatch):
    def fake_call(self, file_path):
        return {
            "fields": [
                {"label": "  ", "field_type": "text"},
                {"label": "Kept", "field_type": "text"},
                {"not_a_field": True},
                {"label": "Also Kept", "field_type": "email"},
            ]
        }

    monkeypatch.setattr(OCRService, "_call_gemini", fake_call)

    fields = _service().extract_fields("/uploads/1/x.png")
    assert [f["field_name"] for f in fields] == ["Kept", "Also Kept"]
    assert [f["position"] for f in fields] == [0, 1]


def test_extract_fields_empty_or_missing_fields(monkeypatch):
    monkeypatch.setattr(OCRService, "_call_gemini", lambda self, fp: {"fields": []})
    assert _service().extract_fields("/uploads/1/x.png") == []

    monkeypatch.setattr(OCRService, "_call_gemini", lambda self, fp: {})
    assert _service().extract_fields("/uploads/1/x.png") == []


def test_call_gemini_without_key_raises():
    service = OCRService(api_key="")
    with pytest.raises(OCRError):
        service._call_gemini("/uploads/1/x.png")


def test_call_gemini_retries_once_on_malformed_json(monkeypatch):
    service = OCRService(api_key="test-key")
    # Avoid real file/poppler work; _generate is mocked below.
    monkeypatch.setattr(
        OCRService, "_load_image_blobs", lambda self, fp: [("image/png", b"x")]
    )

    prompts = []

    def fake_generate(self, prompt, blobs):
        prompts.append(prompt)
        if len(prompts) == 1:
            return "this is not json"  # first reply unparseable -> triggers retry
        return '{"fields": [{"label": "Name", "field_type": "text"}]}'

    monkeypatch.setattr(OCRService, "_generate", fake_generate)

    result = service._call_gemini("/uploads/1/form.png")
    assert result["fields"][0]["label"] == "Name"
    assert len(prompts) == 2  # retried exactly once
    assert prompts[1] != prompts[0]  # stricter prompt used on the retry


def test_call_gemini_raises_after_retry_exhausted(monkeypatch):
    service = OCRService(api_key="test-key")
    monkeypatch.setattr(
        OCRService, "_load_image_blobs", lambda self, fp: [("image/png", b"x")]
    )

    calls = []

    def always_garbage(self, prompt, blobs):
        calls.append(prompt)
        return "still not valid json"

    monkeypatch.setattr(OCRService, "_generate", always_garbage)

    with pytest.raises(OCRError):
        service._call_gemini("/uploads/1/form.png")
    assert len(calls) == 2  # original attempt + one retry, then gives up


def test_signature_field_type_preserved(monkeypatch):
    def fake_call(self, file_path):
        return {"fields": [{"label": "Signature", "field_type": "signature"}]}

    monkeypatch.setattr(OCRService, "_call_gemini", fake_call)
    fields = _service().extract_fields("/uploads/1/x.png")
    assert fields[0]["field_type"] == "signature"


def test_parse_json_strips_markdown_fence():
    raw = '```json\n{"fields": [{"label": "Name", "field_type": "text"}]}\n```'
    parsed = OCRService._parse_json(raw)
    assert parsed["fields"][0]["label"] == "Name"


def test_parse_json_rejects_non_json():
    with pytest.raises(OCRError):
        OCRService._parse_json("not json at all")
