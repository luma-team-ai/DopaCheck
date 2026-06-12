# 🔀 리베이스 가이드 — main MariaDB 전환 (PR #22) 이후

> 작성: 2026-06-12 · 대상: 진행 중 PR #16·#19·#20 담당자
> 배경: **PR #22 머지로 main이 Supabase → MariaDB로 전환**되었습니다(`51be2ed`). PRD Ver1.1 §11 ERD 정합.
> 기존 PR들은 **Supabase 기반 또는 옛 main에서 분기**되어 그대로 두면 충돌·중복입니다. 아래대로 정리하세요.

---

## 0. 무엇이 바뀌었나 (main 기준)

| 영역 | 이전 (Supabase) | 현재 (MariaDB, #22) |
|---|---|---|
| DB 접근 | `from db.client import get_supabase` → `get_supabase().table(...).select()...` | `from db.client import db` → `with db() as cursor: cursor.execute("... %s", (...))` |
| 데이터 격리 | RLS(`auth.uid()`) | **앱 필터 `WHERE user_id = %s`** (모든 쿼리 필수) |
| 세션 | `session["user"]["id"]` (중첩) | **`session["user_id"]`** (평면) |
| 인증 가드 | `if not session.get("user")` | `if not session.get("user_id")` |
| 주차 경계 | `kst_bounds` → `+09:00` ISO | `kst_bounds` → `"YYYY-MM-DD HH:MM:SS"` (DB 세션 TZ +09:00 고정) |
| 스키마 | `db/schema.sql` Postgres+RLS | MariaDB DDL (users.id BIGINT, 나머지 uuid CHAR(36)) |
| 의존성 | `supabase` | `pymysql` |
| env | `SUPABASE_URL/KEY` | `DB_HOST/PORT/USER/PASSWORD/NAME` |

---

## 1. PR별 액션 요약

| PR | 담당 | 액션 | 이유 |
|---|---|---|---|
| **#19** (fix/p2-security) | vapsnamheo-dev | ❌ **Close** (재작업 X) | login_required 강화·type_filter 화이트리스트 등 보안개선을 **#22가 이미 흡수**. Supabase 기반 history diff는 무의미 |
| **#16** (feature/social-login) | HyunDove | 🔁 **Rebase + OAuth만 남기기** | db/client·history·report·app·session은 **main 채택**, 본인은 `auth.py` OAuth 구현 + `login.html`만 |
| **#20** (feat/ai-module) | 50seok | 🔁 **Rebase + challenge.py만 db() 재작업** | history/report는 직접 수정 안 함 → main 자동 채택. `routes/challenge.py`의 `get_supabase`만 `db()`로 전환 |

---

## 2. 공통 리베이스 절차

```bash
# 0) 최신 main 받기
git fetch origin

# 1) 본인 브랜치에서 rebase
git switch <본인-브랜치>          # 예: feature/social-login
git rebase origin/main

# 2) 충돌 나면 — §3 원칙대로 해소 후
git add <해소한-파일>
git rebase --continue

# 3) 테스트 (pymysql 필요: pip install pymysql)
python3 -m pytest -q

# 4) 강제 푸시 (rebase 후 히스토리 변경되므로 --force-with-lease)
git push --force-with-lease
# → 기존 PR이 자동 갱신됩니다 (새 PR 신청 불필요)
```

> ⚠️ `--force-with-lease` 사용(그냥 `--force` 금지 — 원격 덮어쓰기 사고 방지).

---

## 3. 충돌 해소 원칙 (어느 쪽을 택하나)

| 충돌 파일 | 택할 것 | 비고 |
|---|---|---|
| `db/client.py` | **main 채택** | #22의 `db()` 컨텍스트매니저가 표준. 본인 버전 버림 |
| `db/schema.sql` | **main 채택** | MariaDB DDL 확정본 |
| `routes/history.py` · `routes/report.py` | **main 채택** | #22에서 MariaDB로 재작성 완료 |
| `app.py` | **main 채택** | 세션 평면 `user_id`, Blueprint 등록 |
| `requirements.txt` · `.env.example` | **main 채택** (본인 추가분만 병합) | #16: OAuth 키, #20: ANTHROPIC_API_KEY 등 본인 라인만 추가 |
| `routes/auth.py` (#16) | **병합** | main의 `login_required`(user_id) 유지 + 본인 OAuth 콜백 구현 살림 |
| `routes/challenge.py` (#20) | **본인 것 유지하되 DB부분 전환** | §4 참고 |
| `templates/*` | 보통 **본인 것 유지** | UI는 담당자 작업 |

### DB 코드 전환 패턴 (본인 신규 코드에 적용)
```python
# ❌ 이전 (Supabase)
supabase = get_supabase()
rows = supabase.table("challenges").select("*").eq("user_id", uid).execute().data or []

# ✅ 이후 (MariaDB) — WHERE user_id = %s 앱 필터 필수, %s 바인딩만
from db.client import db
with db() as cursor:
    cursor.execute(
        "SELECT * FROM user_challenges WHERE user_id = %s",
        (uid,),
    )
    rows = cursor.fetchall() or []
```
- 세션: `user_id = session.get("user_id")` → falsy면 `abort(401)`
- 동적 테이블명은 **딕셔너리 화이트리스트**로만(`TABLE_MAP` 패턴, f-string에 사용자 입력 직접 금지)
- `id`(uuid) 채번: INSERT 시 앱에서 `str(uuid.uuid4())` 생성 권장(#23)

---

## 4. PR별 상세

### #19 — Close
1. PR 본문에 코멘트: "보안개선(login_required user_id·type_filter 화이트리스트·XSS)은 #22에 흡수됨 → close."
2. 누락 항목이 있는지 #22 머지본(`routes/history.py`)과 대조. 빠진 게 있으면 그 항목만 새 이슈로.
3. `gh pr close 19` · 브랜치 정리.

### #16 — 소셜 로그인 (OAuth만)
1. `git rebase origin/main`
2. 충돌: `db/client.py`·`routes/history.py`·`routes/report.py`·`app.py` → **전부 main 채택**(`git checkout --theirs <file>` 후 본인 변경이 정말 필요한지 재확인).
3. `routes/auth.py`: main의 `login_required`(user_id 기반) 유지 + 본인 `oauth_start`/`oauth_callback` 실제 구현 이식. **`users` 조회는 `email`(예: `kakao_{id}`)로** — PRD users엔 provider 컬럼 없음.
4. `upsert_user_profile`: `with db() as cursor` 단일 트랜잭션 + `INSERT ... ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)`. 세션엔 `session["user_id"] = user_id` 저장.
5. `.env.example`에 `GOOGLE_CLIENT_ID/SECRET`·`KAKAO_CLIENT_ID` 추가.
6. `pytest` → `git push --force-with-lease`.

### #20 — 챌린지 (challenge.py db() 전환)
1. `git rebase origin/main` (history/report는 충돌 없이 main 채택될 것).
2. `routes/challenge.py`: `from db.client import get_supabase` → `from db.client import db`. 두 곳(`:25`, `:129`)의 `supabase.table(...)` 호출을 §3 패턴으로 전환. **모든 쿼리에 `WHERE user_id = %s`**.
3. 세션: `session["user"]["id"]` → `session.get("user_id")` + falsy 방어. (이전 리뷰 P1: challenge_page에 `@login_required` 추가)
4. FR-35 활성 중복참여: 앱 레벨 `SELECT ... WHERE user_id=%s AND challenge_id=%s AND is_completed=0` 존재 확인(#23 연계).
5. `tests/test_challenge.py`·`tests/test_history.py`: `get_supabase` 목킹 → `db` 컨텍스트매니저 목킹으로 교체.
6. `pytest` → `git push --force-with-lease`.

---

## 5. 머지 순서 (충돌 최소화)
```
#19 close
  → #16 (인증 기반 — users INSERT/세션) 먼저
  → #20 (challenge — 인증·세션 의존)
  → #23(커넥션풀·FR-35) / #14(SECRET_KEY) 후속
```

문의는 메인 세션(A)으로. contract 변경이 필요하면 PR에 `[CONTRACT-CHANGE-REQUEST]` 표시 후 보류.
