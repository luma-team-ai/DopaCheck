import { test, expect } from "../../fixtures";
import { LoginPage } from "../../pages/LoginPage";

// 비로그인(게스트) 시나리오 — chromium:guest 프로젝트로 실행.
test.describe("로그인", () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test("소셜 로그인 버튼이 노출된다", async () => {
    await expect(loginPage.googleLoginButton).toBeVisible();
    await expect(loginPage.kakaoLoginButton).toBeVisible();
  });

  test("TODO: 비로그인으로 보호 페이지 접근 시 /login 리다이렉트", async ({ page }) => {
    // TODO: await page.goto("/mypage"); await expect(page).toHaveURL(/\/login/);
  });
});
