import { test, expect } from "../../fixtures";

/**
 * 전체 여정 E2E — 로그인 화면부터 끝까지 순회한다.
 *
 * - chromium:guest 프로젝트(storageState 없음, 신선한 컨텍스트)에서 실행되며 자체적으로 dev_login한다.
 *   (OAuth는 외부 IdP라 자동화 불가 → 로컬 전용 우회 /auth/dev_login으로 세션 생성)
 * - 이 앱의 실제 네비게이션은 하단 탭바(분석=/delivery·리포트·점수·챌린지·마이페이지)다.
 *   탭바에 있는 항목은 "버튼 클릭"으로, 없는 항목(시간·히스토리·관리자·로그아웃)은 직접 이동으로 순회한다.
 * - admin 화면은 dev_test 계정의 role='admin' 사전 세팅이 필요하다.
 * - video: "on"이라 test-results/.../video.webm에 전체 여정이 녹화된다.
 */
test.describe("전체 여정", () => {
  test("로그인 → 전 기능 순회 → 관리자 → 로그아웃", async ({ page }) => {
    // 탭바의 링크를 href로 클릭(상단/하단 중복 대비 visible 우선)
    const clickTab = async (href: string, urlPart: RegExp) => {
      await page.locator(`a[href="${href}"]:visible`).first().click();
      await page.waitForURL(urlPart);
      await page.waitForLoadState("networkidle");
    };

    // 1) 로그인 화면 — 소셜 로그인 버튼 노출 확인
    await page.goto("/login");
    await expect(page.getByRole("link", { name: /카카오/ })).toBeVisible();
    await expect(page.getByRole("link", { name: /Google/i })).toBeVisible();

    // 2) 로그인(로컬 우회) → 홈
    await page.goto("/auth/dev_login");
    await page.waitForURL(/\/home/);
    await expect(page.locator('a[href="/delivery"]:visible').first()).toBeVisible();

    // 3) 하단 탭바 버튼으로 순회 (분석 → 리포트 → 점수 → 챌린지)
    await clickTab("/delivery", /\/delivery/);
    await clickTab("/report", /\/report/);
    await clickTab("/score", /\/score/);
    await clickTab("/challenge", /\/challenge/);

    // 4) 탭바에 없는 화면 — 직접 이동
    //    마이페이지는 헤더 아바타 드롭다운(숨김) 안에 있어 탭 클릭 불가 → 직접 이동
    await page.goto("/mypage");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/mypage/);

    await page.goto("/time"); // 시간 분석(nav 숨김 페이지)
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/time/);

    await page.goto("/history"); // 히스토리
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/history/);

    // 5) 관리자 — role='admin' 사전 세팅 시 접근 가능(아니면 /home으로 리다이렉트)
    await page.goto("/admin");
    await page.waitForLoadState("networkidle");
    await expect(page, "role='admin' 미설정 시 /home으로 리다이렉트됨").toHaveURL(/\/admin/);

    // 6) 로그아웃 → 로그인 화면
    await page.goto("/logout");
    await page.waitForURL(/\/login/);
  });
});
