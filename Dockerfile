FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
COPY generated/ /build/generated/
ARG VITE_LEGAL_OPERATOR_NAME
ARG VITE_SUPPORT_EMAIL
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FRONTEND_DIST=/app/static PIPELINE_DATA_ROOT=/app/datasets
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core ffmpeg && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY datasets/jee-main-2024/ ./datasets/jee-main-2024/
COPY datasets/jee-main-2025/ ./datasets/jee-main-2025/
COPY generated/scraped-mht-cet/ ./generated/scraped-mht-cet/
COPY social/ ./social/
RUN ffmpeg -hide_banner -filters 2>/dev/null | grep -q flite
COPY docs/JEE-Predictor-Data/jee-predictor-data/ ./predictor-data/
COPY --from=frontend /build/frontend/dist ./static
RUN groupadd --gid 1000 appuser && useradd --create-home --uid 1000 --gid 1000 appuser
USER appuser
EXPOSE 10000
CMD ["sh", "-c", "python scripts/add_mht_cet.py --apply && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]
