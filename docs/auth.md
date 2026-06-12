# Auth 동기화 처리 가이드

> 담당: 김승현 | 작성일: 2026-06-11  
> Supabase `auth.users` → `public.users` 자동 동기화

---

## 왜 트리거를 못 쓰나?

Supabase SQL Editor에서 `auth.users`에 직접 트리거를 걸면
`ERROR: 42501: must be owner of relation users` 오류 발생.  
`auth` 스키마는 Supabase 내부 전용이라 일반 사용자 권한으로 접근 불가.

**해결 방법: Flask 로그인 콜백 라우트에서 직접 처리**

---

## 구현 방법

### 1. `db/client.py` — Supabase 클라이언트 + 프로필 생성 함수

```python
# db/client.py
from supabase import create_client
import os

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)

def upsert_user_profile(user_id: str, email: str, name: str):
    """
    소셜 로그인 콜백 시 public.users에 프로필 생성/업데이트
    - 최초 로그인: INSERT
    - 재로그인: id 충돌 시 무시 (ON CONFLICT)
    """
    supabase.table("users").upsert(
        {
            "id":       user_id,
            "email":    email,
            "nickname": name or email.split("@")[0]
        },
        on_conflict="id"
    ).execute()
```

---

### 2. `routes/auth.py` — 로그인 콜백 라우트

```python
# routes/auth.py
from flask import request, redirect, session
from db.client import supabase, upsert_user_profile

@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")

    # Supabase에서 세션 교환
    auth_session = supabase.auth.exchange_code_for_session(code)
    user = auth_session.user

    # Google: full_name / Kakao: name / 없으면 이메일 앞부분
    name = (
        user.user_metadata.get("full_name") or
        user.user_metadata.get("name") or
        user.email.split("@")[0]
    )

    # public.users에 프로필 자동 생성
    upsert_user_profile(
        user_id = user.id,
        email   = user.email,
        name    = name
    )

    # Flask 세션에 유저 정보 저장
    session["user_id"]  = user.id
    session["nickname"] = name
    session["email"]    = user.email

    return redirect("/")


@app.route("/logout")
def logout():
    supabase.auth.sign_out()
    session.clear()
    return redirect("/login")
```

---

### 3. 로그인 필수 데코레이터 (모든 라우트 적용)

```python
# routes/auth.py 또는 utils.py
from functools import wraps
from flask import session, redirect

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
```

**각 라우트에 적용:**

```python
# 예시: routes/delivery.py
from routes.auth import login_required

@app.route("/delivery")
@login_required
def delivery():
    user_id = session["user_id"]
    ...
```

---

## 동작 흐름

```
사용자가 Google/Kakao 로그인 버튼 클릭
            │
            ▼
    Supabase OAuth 처리
    auth.users 자동 생성
            │
            ▼  ← /auth/callback 호출
    exchange_code_for_session()
            │
            ▼
    upsert_user_profile() 호출
    public.users에 프로필 INSERT
    (재로그인 시 ON CONFLICT로 무시)
            │
            ▼
    Flask session에 user_id 저장
            │
            ▼
    홈 화면(/)으로 리다이렉트
```

---

## 주의사항

- `SUPABASE_URL`, `SUPABASE_KEY` 는 반드시 `.env` 파일로 관리, 코드에 하드코딩 금지
- `SUPABASE_KEY` 는 `anon key` 사용 (service role key 아님)
- `session.clear()` 로그아웃 시 Flask 세션도 함께 제거 필수
- RLS 정책이 `auth.uid() = user_id` 기준이므로 `public.users.id` 가 반드시 `auth.uid()` 와 동일해야 함