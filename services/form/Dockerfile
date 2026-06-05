FROM python:3.12-slim

WORKDIR /app

# poppler-utils provides pdftoppm, used by pdf2image to rasterise PDF pages
# before sending them to the Gemini vision API.
RUN apt-get update && apt-get install -y --no-install-recommends \
	poppler-utils \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8002"]
