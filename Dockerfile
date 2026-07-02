# OCI(oci-arm1) 단독 구동용 이미지 — 호스트 nginx가 dopacheck.luma200ok.com → 127.0.0.1:8091 프록시
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Procfile과 동일 구성 (workers 2, timeout 120)
CMD ["gunicorn", "app:app", "--workers", "2", "--bind", "0.0.0.0:8000", "--timeout", "120"]
