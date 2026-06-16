# 전역 설정 — CLAUDE.md

> **설치(최초 1회)** — 이 파일을 `~/.claude/CLAUDE.md` 에 두면 전 프로젝트에 자동 적용. 룰이 호출하는 의존성:
> - **ECC 플러그인**(code-reviewer·security-reviewer 에이전트 + 스킬): Claude Code에서 `/plugin marketplace add affaan-m/everything-claude-code` → `/plugin install everything-claude-code@everything-claude-code`
> - **GitHub CLI**: `brew install gh && gh auth login`
> - **(브라우저 테스트 시) Playwright MCP**: `claude mcp add playwright -- npx @playwright/mcp@latest`
> - `SendMessage`·`Agent`·Plan/Explore 서브에이전트는 Claude Code **내장**(설치 불필요).

## 커뮤니케이션
- 항상 존댓말, 간결·핵심만. 코드 수정 후 한국어로 이유 설명(설명 먼저 → 이해 후 커밋).

## 커밋 & PR
- 커밋 한국어 `feat/fix/refactor/docs/chore: 내용`. PR base=`main`, 머지 요청 시 바로 진행(단, 머지 직전 체크리스트·G6는 그래도 필수).
- **`Co-Authored-By` 금지.** 커밋·푸시 전 **시크릿 스캔 필수**.

## 시크릿 스캔 (커밋·푸시 전 의무)
```bash
git diff --cached | grep -iE "(password|passwd|secret|token|api_key|apikey|access_key|private_key|sk-|ghp_|gho_|glpat-|AKIA|AIza)['\"]?\s*[:=]\s*['\"][^'\"]{8,}"
```
대상: API키(`sk-`,`ghp_`,`gho_`,`glpat-`,`AKIA`,`AIza`) · 비번/토큰(`password=`,`secret=`,`token=`,`Bearer ` 하드코딩 값) · DB URL(`jdbc:`,`mysql://`,`mongodb://`) · 개인키(`-----BEGIN … PRIVATE KEY-----`).
- 실제 값 → **커밋 중단** → 환경변수(`.env`/`application-local.yml`) 분리 + `.gitignore` 확인 → 재스캔 통과 후 커밋.
- 더미값(`test`/`example`/`your-key-here`)·환경변수 참조(`${SECRET}`,`os.getenv`) → 통과.
- **이미 push됨** → 즉시 토큰 재발급 → 사용자 알림 → 히스토리 정리(`filter-branch`/`BFG`).

## 서버·브라우저 정리 (테스트 후 의무)
- 테스트 서버(Spring Boot·Vite·Flask·Next dev 등)는 테스트 후 즉시 종료: `lsof -ti:<port>` → `kill`.
- **브라우저 자동화 테스트(Playwright MCP·Claude in Chrome 등)는 종료 시 연 브라우저·탭을 필수로 닫는다**(`browser_close` 등). 백그라운드 크롬·헤드리스 프로세스를 남기지 말 것.

---

> **코딩 컨벤션 = 패턴 템플릿.** 전역은 구조·계층·네이밍 원칙만 정의한다. `{앱}`·`{도메인}`·`{tenant}`·DB·배포 타깃·멀티테넌트 여부 등 **구체값은 프로젝트 시작 시 프로젝트 CLAUDE.md에서 확정**(전역값을 그대로 박지 말 것). 쓰는 스택만 골라 적용.

# 코딩 컨벤션 (Java / Spring Boot)
**스택**: Java 21 · Spring Boot 3.x · jakarta.*(javax 금지) · JPA+QueryDSL · MySQL · Redis
**패키지**: controller / service / repository / entity / dto / exception / config / scheduler / init

| 영역 | 규칙 |
|---|---|
| Entity | @Getter만(Setter 금지), @NoArgsConstructor(PROTECTED)+@Builder, Soft Delete=@SQLDelete+@SQLRestriction, @PrePersist로 createdAt/기본status, 상태전이는 엔티티 메서드로 캡슐화 |
| DTO | Request=Record+Bean Validation, Response=Record+`from(Entity)`, 네이밍 `{도메인}Request/Response`, 엔티티 직접 노출 금지 |
| Repository | 단순조회=메서드 네이밍, N+1 방지=@EntityGraph, 복잡쿼리=`{Repo}Custom+Impl`, QueryDSL Projections로 DTO 매핑 |
| Service | 클래스 `@Transactional(readOnly=true)`, 쓰기만 `@Transactional` 명시, Controller엔 금지. 예외=`CustomException(ErrorCode)`. 캐시=`@Cacheable/@CacheEvict`(Redis) |
| Controller | `ResponseEntity<DTO>`+상태코드, `@Valid` 항상, Swagger `@Tag/@Operation` 필수, 비즈니스 로직 금지 |
| Exception | ErrorCode enum(HttpStatus+code+message), `CustomException(ErrorCode)` 단일패턴, GlobalExceptionHandler 일괄, 응답=`{timestamp,code,message}` |
| Flyway | `V{n}__{설명}.sql`, 한 파일=한 변경, **기존 마이그레이션 수정 금지** |

**네이밍**: Entity=PascalCase, Enum=UPPER_SNAKE_CASE, Service=`find/create/update/delete~`, API URL=kebab-case 복수형(`/api/work-orders`), ErrorCode=도메인 prefix+3자리(E001). **테스트 항상 동반.**

**ECC 스킬 자동 적용**: 새 기능·버그·엔드포인트→`/springboot-tdd` · 테스트→`/tdd-workflow` · 인증/인가/시크릿/민감데이터→`/security-review` · Flyway→`/database-migrations` · REST 설계→`/api-design`

---

# 코딩 컨벤션 (Python / Flask)
**스택(기본값, 프로젝트별 조정)**: Python 3.11 · Flask 3.1 · Gunicorn · Pydantic · pytest. DB·배포·외부연동은 프로젝트 선택(예: Supabase/PostgreSQL, Render, APScheduler).
**패키지 구조 템플릿** (`{도메인}`은 프로젝트값으로 치환):
```
backend/
  main.py · requirements.txt · .env(.example) · {배포설정 예: render.yaml} · db/schema.sql
  app/__init__.py(create_app) · config.py · errors.py
  app/middleware/   (auth.py)
  app/routes/       (Blueprint, {도메인}.py)
  app/services/     ({도메인}_service.py)
  app/repositories/ (base.py + {도메인}_repository.py)
  app/models/       (schemas.py — Pydantic)
  app/utils/        (외부 연동 팩토리: DB 클라이언트·스케줄러·AI 등 필요 시)
  tests/            (conftest.py + test_*.py)
```

| 영역 | 규칙 |
|---|---|
| 계층 흐름 | middleware → routes(Blueprint) → services → repositories → DB. 단방향, 역참조 금지 |
| Middleware | `require_auth`(JWT 검증 → `g.user`). 인증 실패 401 / 권한 없음 403 |
| Routes | Blueprint, 요청 파싱+service 호출+상태코드만. 비즈니스 로직 금지. URL=kebab-case 복수형(`/api/{리소스}`) |
| Services | 도메인 규칙·검증. 예외=`ApiError(status, message)` 단일 패턴. `g.user`는 내부에서 읽음. repo는 **모듈 수준 인스턴스**(테스트 `patch` 가능) |
| Repositories | DB CRUD, `BaseRepository` 상속. 조회는 명시 컬럼(과다조회 주의) |
| Models | Pydantic Request/Response(`models/schemas.py`), Enum=`str,Enum`. dict 직접 노출 자제 |
| 에러 | `ApiError(code,msg)` → `register_error_handlers` 일괄 → 응답 `{"error":msg}`(+detail). 500은 스택 로깅 |
| 외부 클라이언트 | DB/AI 클라이언트는 `utils/` 단일 팩토리(예: `get_supabase()`), 키는 env, **repo/service에서만** 호출 |
| 테스트 | pytest `tests/test_*.py` + conftest 픽스처. 기능·엣지 테스트 동반 |

**네이밍**: 파일·함수 snake_case, 클래스 PascalCase, Enum 값 UPPER_SNAKE. Service 메서드 `list/get/create/update/delete`.
**ECC 스킬**: 인증/시크릿→`/security-review` · REST 설계→`/api-design` · 테스트→`/tdd-workflow`.
**멀티테넌트(B2B) 프로젝트만 추가**(흔치 않음): `middleware/tenant.py`+`services/tenant_guard.py` → 헤더 테넌트ID(`X-…-Id`)는 **입력값 취급**, 매 요청 멤버십 재검증(cross-tenant IDOR 차단) · repo 테넌트 스코프 필수(`.eq('{tenant}_id', …)`)+컬럼 비정규화 · 격리 테스트 동반.

---

# 코딩 컨벤션 (TypeScript / Next.js)
**스택(기본값)**: Next.js 16(App Router) · TypeScript · Tailwind 4. 인증·배포는 프로젝트 선택(예: Supabase Auth, Vercel).
**패키지 구조 템플릿**:
```
frontend/src/
  app/(auth)/      (login·signup 등 인증 화면)
  app/(dashboard)/ (layout.tsx + {도메인}/page.tsx, [id] 동적)
  app/layout.tsx · app/page.tsx · app/globals.css  [ · app/auth/callback — OAuth 시]
  components/{영역}/  (PascalCase.tsx)
  lib/api/         (client.ts + endpoints.ts + {도메인}.ts)
  lib/{외부}/       (예: supabase/)
  types/index.ts · constants/index.ts
```

| 영역 | 규칙 |
|---|---|
| 라우팅 | App Router, route group `(auth)`/`(dashboard)`, `layout.tsx`+`page.tsx`, 동적 `[id]`. URL kebab-case |
| API 호출 | `import { api, authHeaders } from "@/lib/api/client"`. 도메인 래퍼 `lib/api/{도메인}.ts`, 경로 상수 `lib/api/endpoints.ts`. **URL 하드코딩 금지** → `NEXT_PUBLIC_API_URL`(미설정 시 프로덕션 빌드 실패 처리) |
| 인증 | 토큰은 **앱 prefix 키**로 저장 `localStorage['{앱}AccessToken']`(프로젝트마다 prefix 통일). 요청 헤더=`authHeaders(token)` → `Authorization: Bearer` |
| 컴포넌트 | `components/{영역}/PascalCase.tsx`. 상태·이벤트 쓰면 `'use client'` |
| 타입/상수 | 공유 타입 `types/index.ts`, 라벨·상수 `constants/index.ts`(백엔드 Enum과 값 일치) |
| 에러 | `api`가 던지는 Error에 `.status` 실림 → 메시지 매칭 대신 **status로 분기**(예: 404만 null) |
| 빌드 | `npm run build` PASS + lint 통과 |

**네이밍**: 컴포넌트·타입 PascalCase, 함수·변수 camelCase, 라우트 폴더 kebab-case.
**멀티테넌트일 때만**: `authHeaders(token, tenantId)`로 테넌트 헤더(`X-…-Id`) 추가 + 테넌트 ID도 앱 prefix 키로 저장.

---

# Git 워크트리 워크플로우 (예외 없음)
**브랜치=워크트리명**: `{역할}/{이슈}-{세부}` (예 `backend/42-sensor-api`).
메인 세션은 **main 유지 · 구현은 서브에이전트**(원칙적으로 직접 코드 작성 금지 — 예외: 한 줄 픽스·Trivial은 메인 직접 허용).

> **스택별 빌드/테스트 명령**(아래 단계에서 "테스트/빌드"는 이 표로 치환): Java=`./gradlew compileJava` + `./gradlew test` · Flask=`pytest` · Next=`npm run build`(+`npm test`).

## 순서
1. 레포 없으면 `gh repo create` 먼저. `docs/STATUS.md` 없으면 표준 템플릿 생성.
2. 이슈 등록 `gh issue create --title "feat: …" --label feature` → 번호 확인.
3. 코드 분석(Explore 서브에이전트로 기존 패턴·재사용 파악) → Plan 모드 계획 → 사용자 승인.
4. **구현 서브 디스패치** `git worktree add ../{name} -b {branch}`. 책임/금지 = ↓[서브 책임 블록].
5. **메인 검수**(순서·누락 금지):
   - 워크트리에서 **테스트 재실행**(스택별 명령, 서브 보고 검증).
   - **code-reviewer 호출**(메인이 직접 Agent) — 트리거: 버그수정 / 서비스·레포 변경 / 트랜잭션·동시성·분산락 / DB쿼리·배치 / 마이그레이션. 프롬프트=변경파일 절대경로+의도+P1/P2/P3 분류.
   - **security-reviewer 호출**(해당 시) — 트리거: 인증·인가 / API키·시크릿 / 결제·환불 / 외부API / Webhook / 멱등성 / Rate-Limit.
   - reviewer 원본 평가 — **P 등급 임의 다운그레이드 금지**.
6. **P1 픽스 루프**(메인 주도, **cap 2회**): SendMessage(구현 서브) 픽스 → SendMessage(리뷰어 서브) 재검토. 한 줄은 메인 직접. cap 초과 P1 잔존 → PR 분할 / 후속 이슈 분리(P2 격하 시 PR 본문 명시) / 사용자 에스컬레이션.
7. **PR 생성**(`Closes #N` 필수, 본문=↓[PR 템플릿]).
8. **머지 직전 체크**(누락 시 머지 금지): Self-Review P1 카운트 일치 · code-reviewer P1 잔존 0 · 보안영역이면 Security Review 섹션 존재 · 빌드/테스트 PASS 명시 · auto-review.yml PASS.
9. **머지 직후**(누락 금지): `gh issue comment {N}`(Critical이면 reviewer P1도 기록) · README 갱신(새 ErrorCode/환경변수/API/의존성/마이그레이션 시) · **`docs/STATUS.md` 갱신**(A-B-C에선 A만).
10. **정리**: `git worktree remove … && git branch -d … && git push origin --delete …`

**버그 판단**: 현재 작업 관련→같은 워크트리 / 무관→새 이슈+워크트리 / 긴급 프로덕션→main에서 `hotfix/{N}-{내용}` 브랜치(구현은 서브).

## 서브 책임 블록 (모든 구현 서브 프롬프트에 명시)
```
## 책임 (이것만)
1. 워크트리+브랜치 생성(지정 이름)
2. 코드 + 단위/통합 테스트
3. 빌드/테스트 PASS (스택별: Java=./gradlew compileJava+test · Flask=pytest · Next=npm run build, 오류 0)
4. 단계별 커밋(feat: 모델/스키마→서비스→라우트·컨트롤러→테스트 순, 스택 계층대로), push 금지
5. 메인/A에 보고: 변경파일 절대경로 + 의도 + 빌드결과
## 금지 (메인/A가 함)
self-review·security-review 호출 / PR 작성·생성 / push / 머지 / STATUS.md 수정
보고 후 대기 (메인이 SendMessage로 P1 픽스 명령 가능)
```

## 구현자 ≠ 리뷰어 (필수)
구현자와 리뷰어는 **항상 다른 서브에이전트**(자기 코드 자기 리뷰 금지). 리뷰어 호출·픽스 루프는 **메인이 직접 주도**.

| 상황 | 사용 |
|---|---|
| 픽스 명령(구현자 자기 코드 수정) | `SendMessage(구현 서브)` — 컨텍스트 유지 |
| 재검토(리뷰어 픽스 검증) | `SendMessage(리뷰어 서브)` — 이전 P1 비교 |
| 다른 영역 새 작업 / 추가 리뷰어 의견 | `Agent({...})` — 컨텍스트 분리 |

픽스 명령을 새 Agent로 보내기 **금지**(표면 픽스만 됨). SendMessage 부재 시 새 prompt에 워크트리 경로+픽스 항목+reviewer 결과 명시.

---

# 사이클 비용 매트릭스
| 영역 | 트리거 | 구현자 | reviewer | 검증 게이트 | cap |
|---|---|---|---|---|---|
| **Critical** | race/분산락/트랜잭션/결제·환불/인증·인가/webhook·멱등성/분산정합성 | opus | code-reviewer opus (+ security-reviewer opus — 보안 트리거 있을 때) | G1/G3.5/G6 의무 | 2회 |
| **Normal** | 일반 CRUD/컨트롤러+DTO/단순가드/알림/테스트 | sonnet | code-reviewer sonnet 1회 | G1+G6만 | 1회 |
| **Trivial** | 설정/문서/dead code/import/단순 스키마 변경(ALTER) | sonnet or 메인 | 생략 가능(메타 자체 검수) | 생략 | 0회 |

**판단 모호 → Critical 우선.** cap 초과 P1 잔존 → PR 분할/후속 이슈/에스컬레이션.

**모델 배정**: opus=트랜잭션·분산락·도메인모델·보안설계·외부 P1 핫픽스·큰 리팩터링 / sonnet(기본)=TDD·API 계층(컨트롤러/라우트+DTO)·CRUD·마이그레이션·외부연동(WebClient 등)·리스너·일반 reviewer / haiku=체크박스·import·텍스트·라벨·빌드확인(보통 메인 직접).

---

# 검증 게이트 (회귀 차단) — 메타 자체 검수
메타가 단독 결정하는 지점마다 **자체 검수로 회귀 차단** — 회귀 패턴(stale 단정 / reviewer 결과 임의 격하 / 운영 config 검증 누락 / destructive 미점검) 점검.

| 게이트 | 시점 | 검증 항목 |
|---|---|---|
| **G1** | handoff 작성 직후, B/C 스폰 직전 | 회귀 패턴 / stale / handoff 누락 |
| **G3.5** | reviewer 종합 직후, P 등급 결정 직전 | P1→P2 격하 정당성 / 후속 분리 근거 |
| **G6** | PR 머지 직전 | 이전 PR 픽스 회귀 / 운영 config 영향 / destructive SQL 운영데이터 |

- **Phase 흐름(Critical)**: [1]handoff+**G1** → [2]구현 → [3]사후검수(code-reviewer)+**G3.5**(P등급) → [4]P1 픽스(cap2) → [5]재검수 → [6]머지 직전 **G6**.
- **Normal**: [1]handoff+G1 → [2]구현 → [3]code-reviewer(sonnet) → [4]P1 픽스 → [6]G6.
- **자동 진행**: 사이클 확정 후 게이트는 AskUserQuestion 없이 즉시 실행, 결과만 보고. **FAIL 시에만** 수정 방향 컨펌. FAIL 무시하고 머지 금지.

**게이트 = 메타 자체 검수**(3개 항목 모두 PASS해야 통과): ① stale 정보 ② 이전 PR과 동일 회귀 패턴 재발 ③ handoff 누락 항목. PR 본문에 `G1(자체검수): PASS — 근거 N건` 형식으로 기록.

---

# 표준 템플릿

## PR 본문
```markdown
Closes #N

## 변경 내역
- …

## 🔒 Self-Review (code-reviewer 원본 요약)
- P1 <건수> → 픽스/잔존/후속 분리 · P2 <건수>

## 🛡️ Security Review (해당 시)
- P1 <건수> → 처리

## 🛡️ 검증 게이트 (자체 검수)
- G1: PASS/FAIL → {근거/수정} · G3.5: PASS/FAIL → {수정} · G6: PASS/FAIL → {회귀 결과}

## 테스트
- [x] 테스트 PASS (n/n) — 스택별: Java=./gradlew test · Flask=pytest · Next=npm run build/test
```

## 트러블슈팅 코멘트 (머지 직후)
`gh issue comment {N} --body "…"` — 관련 이슈 없으면 `docs/troubleshooting/*.md`. 수정 커밋 여러 개면 각 해시 기록.
```markdown
## 🔧 트러블슈팅 (PR #N 머지)
**상황**: … **원인**: … **해결**: …(핵심 커밋 해시)
### Reviewer P1 (Critical 시) — …
### 후속 이슈 — #N
```

---

# A-B-C 오케스트레이션
**사용자는 A 세션 하나만 연다.** B(백엔드)·C(프론트)는 A가 스폰하는 **구현 서브**(세션 전환 없음). *(letter A/B/C는 이 섹션 전용 명칭 — 워크트리 워크플로우의 "구현 서브/리뷰어 서브"와 구분.)*

| 역할 | 정체 | 책임 | 금지 |
|---|---|---|---|
| **A(메타)** | 사용자가 여는 유일 세션 | 설계·handoff·B·C 스폰·검수·머지·배포·STATUS.md | 코드 직접 작성(예외: 한 줄 픽스·Trivial) |
| **B/C** | A가 스폰 | 워크트리 구현·테스트·커밋·보고 | 도메인 결정·push·PR·머지·STATUS.md |

**Phase**: 0.설계(A: api-contract.md + STATUS.md + handoff) → 1.구현(A가 B·C 병렬 스폰) → 2.검수·배포(B·C 완료 시 A 자동 검수→PR→머지→배포) → 3.버그수정(A가 fix 서브 스폰). 사용자 행동은 Phase 0의 1줄 지시뿐.

**A의 B·C 스폰**: `Agent({ subagent_type:"general-purpose", model:"sonnet"(Critical=opus), run_in_background:true, isolation:"worktree", prompt:"docs/handoff/{영역}-next.md 읽고 작업. 워크트리:{path}, 브랜치:{역할}/{N}-{내용}" + [서브 책임 블록] })`. 완료 알림 → A 검수 → push+PR+머지+배포.

**진행 확인**: 사용자가 A에 "백엔드 현황?" → A가 워크트리 git log+변경파일 요약(B·C 단계별 커밋이라 추적 가능).

**A 검수 기준**(B·C 완료 후): api-contract.md 스펙 일치 · ErrorCode 준수 · 빌드/테스트 PASS 재확인 · code-reviewer 호출(사이클 매트릭스) · 머지 순서 백엔드→프론트.

**버그 수정 스폰**: `Agent(prompt: 버그/재현/예상원인(파일:라인)/최소수정범위 + "수정 후 기존 테스트 PASS, 워크트리 커밋·보고, push/PR/머지 금지")`.

## 매체별 역할
| 매체 | 자동로드 | 용도 | 갱신 |
|---|---|---|---|
| `CLAUDE.md` | ✅ | 영구 룰 | 룰 변경 시 |
| `docs/STATUS.md` | ❌ 명시 | 인프라·머지·다음작업 | **A만**(매 머지 후) |
| `docs/api-contract.md` | ❌ 명시 | API 단일진실 | **A만**(Phase 0+변경) |
| `docs/handoff/*.md` | ❌ | A→B·C 지시 | A 작성, 완료 후 `archive/` |
| GitHub 이슈/PR | ❌(`gh`) | 단위작업+트러블슈팅 | B·C 생성, A 머지 |

## 자동 생성 규칙
- **STATUS.md** (Phase 0서 없으면 A가 즉시 생성). 위치: 단일레포 `<root>/docs/`, 멀티레포 `<workspace>/docs/`(A 통합). 섹션: 마지막 갱신일 / 인프라 표 / 마지막 머지 PR / 다음 작업(P0·P1·P2 체크리스트) / 알려진 이슈 표.
- **api-contract.md** (Phase 0서 양쪽 영향 모델 결정 시). 섹션: 인증모델 / 핵심 엔드포인트 표 / DTO 스키마 / ErrorCode 체계 / 환경변수·CORS. **변경=A만**; B·C 필요 시 PR에 `[CONTRACT-CHANGE-REQUEST]` 표시+보류 → A가 contract 갱신+handoff 재발행 → B·C 재개.

## handoff 템플릿
- **{영역}-next.md**(신규): 이슈 #N·제목 / 사이클(Critical·Normal·Trivial) / 구현 범위 / contract 참조 §섹션 / 완료기준(빌드/테스트 PASS·단계별 커밋·A 보고 후 대기).
- **{영역}-fix-{N}.md**(버그): 현상 1줄 / 재현(요청·응답) / 예상 원인(파일:라인) / 최소 수정범위 / 완료기준(정상 동작·기존 테스트 PASS·A 보고 후 대기).
