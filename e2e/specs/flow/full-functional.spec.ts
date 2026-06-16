import { test, expect } from "../../fixtures";

/**
 * 로그인부터 각 기능을 실제로 "수기 작동"시키는 종합 기능 테스트.
 *
 * - OCR(영수증 업로드)은 AI 키가 닫혀 제외. 배달/시간은 수동 입력 경로로 검증한다.
 *   (두 경로 모두 AI 코멘트 실패 시 fallback 후 환산·DB 저장은 정상 동작)
 * - 데이터 생성(배달·시간) → 점수/리포트/히스토리에 반영 → 챌린지·시급·관리자까지 전 기능 순회.
 * - 사람이 볼 수 있게: SLOWMO=700 + --headed, video:on 녹화.
 *
 * 실행: SLOWMO=700 PORT=5055 npx playwright test full-functional --project=chromium:guest --headed
 */
test.describe("전체 기능(수기)", () => {
  // 페이지 전환이 잦아 한 번에 길게 — 타임아웃 여유
  test.setTimeout(120_000);

  test("로그인 → 배달·시간 입력 → 점수·리포트·히스토리 반영 → 챌린지·시급·관리자", async ({ page }) => {
    // ── 0) 로그인 화면 → 로그인 ──────────────────────────────────────
    await page.goto("/login");
    await expect(page.getByRole("link", { name: /카카오/ })).toBeVisible();
    await expect(page.getByRole("link", { name: /Google/i })).toBeVisible();

    await page.goto("/auth/dev_login");
    await page.waitForURL(/\/home/);

    // ── 1) 배달 수동입력 → 분석/저장 ────────────────────────────────
    await page.goto("/delivery/manual");
    await page.waitForLoadState("networkidle");
    await page.locator(".food-input").first().fill("마라탕");
    await page.locator(".price-input").first().fill("18000");
    await expect(page.locator("#total-amount")).not.toHaveText("0");
    await page.getByRole("button", { name: "분석하기" }).click();
    await expect(page.getByText("분석 결과").first()).toBeVisible();

    // ── 2) 시간 수동입력 → 분석/저장 ────────────────────────────────
    await page.goto("/time");
    await page.waitForLoadState("networkidle");
    await page.locator("#youtube_h").fill("10");
    await page.locator("#instagram_h").fill("2");
    await page.locator("#game_h").fill("5");
    await page.locator("#hourly_wage").fill("12000");
    await page.getByRole("button", { name: "분석하기" }).click();
    await expect(page.getByText("시간 분석 결과")).toBeVisible();

    // ── 3) 점수 — 입력 데이터로 산출되어 표시 ───────────────────────
    await page.goto("/score");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("점수 트렌드").first()).toBeVisible();

    // ── 4) 리포트 — 진입 시 재산출 후 표시 ──────────────────────────
    await page.goto("/report");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("도파민 점수").first()).toBeVisible();

    // ── 5) 히스토리 — 방금 만든 기록이 보이고 상세/필터 동작 ─────────
    await page.goto("/history");
    await page.waitForLoadState("networkidle");
    const records = page.locator('[onclick^="goDetail"]');
    expect(await records.count()).toBeGreaterThan(0); // 배달+시간 기록 존재
    // 상세 진입
    await records.first().click();
    await page.waitForURL(/\/history\//);
    await expect(page.getByText(/환산|주문 내역|총 사용/).first()).toBeVisible();
    // 필터(이번 달) 동작
    await page.goto("/history");
    await page.getByRole("link", { name: "이번 달" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.locator('[onclick^="goDetail"]').first()).toBeVisible();

    // ── 6) 챌린지 참여 ──────────────────────────────────────────────
    await page.goto("/challenge");
    await page.waitForLoadState("networkidle");
    const joinButtons = page.locator(".btn-join");
    if ((await joinButtons.count()) > 0) {
      await joinButtons.first().click();
      await expect(
        page.locator('.btn-joined, button:has-text("참여 중")').first()
      ).toBeVisible();
    } else {
      await expect(page.getByText("참여 중").first()).toBeVisible();
    }

    // ── 7) 마이페이지 시급 저장 (FR-50) ────────────────────────────
    await page.goto("/mypage");
    await page.waitForLoadState("networkidle");
    await page.locator("#openWageModalBtn").click();
    await expect(page.locator("#wageModal")).toBeVisible();
    await page.locator("#hourly_wage").fill("14000");
    await page.getByRole("button", { name: "저장하기" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/14,000\s*원/).first()).toBeVisible();

    // ── 8) 관리자 대시보드 (role='admin' 사전 세팅) ────────────────
    await page.goto("/admin");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/admin/);
    await expect(page.getByText("가입자").first()).toBeVisible();

    // ── 9) 로그아웃 ─────────────────────────────────────────────────
    await page.goto("/logout");
    await page.waitForURL(/\/login/);
  });
});
