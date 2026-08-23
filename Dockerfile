# 홈서버(hmoeserver) 배포 이미지 — deploy/home/compose.yml 이 이 Dockerfile 로 빌드한다.
# 공개는 Cloudflare Tunnel → shared-net → dopacheck-app:8000 경로다(호스트 nginx 없음).
# 127.0.0.1:8091 publish 는 서버 로컬 스모크 전용. 배포 절차는 docs/guide/DEV_GUIDE.md §6.
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Procfile과 동일 구성 (workers 2, timeout 120)
CMD ["gunicorn", "app:app", "--workers", "2", "--bind", "0.0.0.0:8000", "--timeout", "120"]
