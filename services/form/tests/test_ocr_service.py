from PIL import Image
from app.services.ocr_service import OCRService


def test_ocr_extracts_fields(monkeypatch, tmp_path):
    def fake_image_to_data(image, output_type):
        return {"text": ["Name", "", "Date"]}

    monkeypatch.setattr("pytesseract.image_to_data", fake_image_to_data)

    image_path = tmp_path / "sample.png"
    Image.new("RGB", (10, 10), color="white").save(image_path)

    fields = OCRService().extract_fields(str(image_path))
    assert len(fields) == 2
    assert fields[0]["field_name"] == "Name"
    assert fields[1]["field_name"] == "Date"
