FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# chromadb is optional — only needed for the chroma live_benchmark target.
# Uncomment to bake it into the image:
# RUN pip install --no-cache-dir chromadb>=0.5

COPY backend ./backend
COPY web ./web
COPY bench ./bench
COPY run.py .

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT}"]
