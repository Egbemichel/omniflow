from typing import List
from PIL import Image
import pytesseract
from pdf2image import convert_from_path


class OCRService:
    def extract_fields(self, file_path: str) -> List[dict]:
        if file_path.lower().endswith(".pdf"):
            images = convert_from_path(file_path, first_page=1, last_page=1)
            if not images:
                return []
            image = images[0]
        else:
            image = Image.open(file_path)

        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        fields = []
        for idx, text in enumerate(data.get("text", [])):
            cleaned = text.strip()
            if not cleaned:
                continue
            fields.append(
                {
                    "field_name": cleaned,
                    "field_type": "text",
                    "required": False,
                    "position": idx,
                }
            )
        return fields
