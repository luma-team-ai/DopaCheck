# 홈서버(hmoeserver) 배포 이미지 — deploy/home/compose.yml 이 이 Dockerfile 로 빌드한다.
# 공개는 Cloudflare Tunnel → shared-net → dopacheck-app:8000 경로다(호스트 nginx 없음).
# 127.0.0.1:8091 publish 는 서버 로컬 스모크 전용. 배포 절차는 docs/guide/DEV_GUIDE.md §6.
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 비루트 구동 — 이 컨테이너는 터널로 인터넷에 직접 노출되는 유일한 프로세스이면서
# 무관한 세 스택(community·mes·pension)과 shared-net 을 공유한다. root 로 돌면
# 앱 침해가 곧바로 공유망 전체를 스캔·접근할 수 있는 발판이 된다.
# 앱은 런타임에 디스크를 쓰지 않는다(이미지 처리도 BytesIO — ai/image_prep.py) —
# /app 은 읽기만 하므로 소유권을 바꿀 필요가 없다.
# ⚠️ 홈 디렉터리는 **실재하고 쓸 수 있어야** 한다. `-d /nonexistent` 로 두면 gunicorn(26.x)의
#    control server 가 매 기동마다 `[ERROR] Control server error: [Errno 13] Permission denied:
#    '/nonexistent'` 를 남긴다(2026-08-23 실측 — 서빙 자체는 되지만 로그가 오염된다).
RUN useradd -r -u 10001 -m -d /home/app -s /usr/sbin/nologin app
USER app

EXPOSE 8000

# Procfile과 동일 구성 (workers 2, timeout 120)
CMD ["gunicorn", "app:app", "--workers", "2", "--bind", "0.0.0.0:8000", "--timeout", "120"]
