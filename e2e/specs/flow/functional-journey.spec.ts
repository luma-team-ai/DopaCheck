import { test, expect } from "../../fixtures";

/**
 * 실기능 E2E (수동입력 위주) — 실제로 값을 입력/제출하고 결과·상태 변화를 검증한다.
 *
 * - OCR(영수증 업로드)은 외부 AI API가 닫혀 있어 제외. 배달은 "수동 입력" 경로로 검증한다.
 *   (수동 경로는 칼로리/코멘트 AI 실패 시에도 지출 환산·저장은 정상 동작 — routes/delivery.py)
 * - AI가 필요 없는 기능: 배달 수동입력 저장 / 챌린지 참여 / 마이페이지 시급 저장.
 * - 사람이 볼 수 있게: SLOWMO=700 + --headed 로 실행, video:on 으로 녹화.
 *
 * 실행: SLOWMO=700 PORT=5055 npx playwright test functional-journey --project=chromium:guest --headed
 */
test.describe("실기능 여정", () => {
  test("배달 수동입력 분석 · 챌린지 참여 · 시급 저장", async ({ page }) => {
    // 로그인(로컬 우회)
    await page.goto("/auth/dev_login");
    await page.waitForURL(/\/home/);

    // ── 1) 배달 수동입력 → 실제 분석/저장 ───────────────────────────────
    await page.goto("/delivery/manual");
    await page.waitForLoadState("networkidle");

    await page.locator(".food-input").first().fill("마라탕");
    await page.locator(".price-input").first().fill("15000");
    // 수량 기본 1. JS가 합계(#total-amount)를 실시간 계산한다.
    await expect(page.locator("#total-amount")).not.toHaveText("0");

    await page.getByRole("button", { name: "분석하기" }).click();

    // 결과 화면 렌더 = 수동입력 분석 파이프라인(환산·DB저장·점수재산출) 성공
    await expect(page.getByText("분석 결과").first()).toBeVisible();

    // ── 2) 챌린지 참여 ───────────────────────────────────────────────
    await page.goto("/challenge");
    await page.waitForLoadState("networkidle");

    const joinButtons = page.locator(".btn-join");
    if ((await joinButtons.count()) > 0) {
      await joinButtons.first().click(); // AJAX join
      // 참여 후 "참여 중"(btn-joined) 상태로 전환되는지 확인
      await expect(
        page.locator('.btn-joined, button:has-text("참여 중")').first()
      ).toBeVisible();
    } else {
      // 이미 전부 참여된 상태도 유효한 기능 결과
      await expect(page.getByText("참여 중").first()).toBeVisible();
    }

    // ── 3) 마이페이지 시급 저장 (FR-50) ──────────────────────────────
    await page.goto("/mypage");
    await page.waitForLoadState("networkidle");

    await page.locator("#openWageModalBtn").click();
    await expect(page.locator("#wageModal")).toBeVisible();
    await page.locator("#hourly_wage").fill("13500");
    await page.getByRole("button", { name: "저장하기" }).click();

    // 저장 후 마이페이지로 복귀하며 변경된 시급(13,500원)이 표시되는지 확인 = DB 반영
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/13,500\s*원/).first()).toBeVisible();
  });
});
