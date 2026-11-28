# AI Service (FastAPI): dự đoán thời lượng khám + gợi ý chuyên khoa. Mô hình đã huấn luyện nằm sẵn trong models/.
# Build/chạy qua docker-compose ở repo gốc. Chạy riêng: docker build -t clinic-ai ai-service
FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PYTHONPATH=/app/src
WORKDIR /app
# xgboost cần libgomp (OpenMP)
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.lock.txt ./
RUN pip install -r requirements.lock.txt
COPY src ./src
COPY models ./models
COPY data/triage ./data/triage
COPY pyproject.toml ./
RUN useradd -m app && chown -R app /app
USER app
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
  CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/health',timeout=3).status==200 else 1)"
CMD ["python", "-m", "ai_service", "serve", "--host", "0.0.0.0", "--port", "8001"]
