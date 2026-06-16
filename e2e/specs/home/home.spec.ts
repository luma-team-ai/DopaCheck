import { test, expect } from "../../fixtures";
import { HomePage } from "../../pages/HomePage";

// 인증 시나리오 — chromium:auth 프로젝트(storageState 주입)로 실행.
test.describe("홈 대시보드", () => {
  let homePage: HomePage;

  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    await homePage.goto();
  });

  test("TODO: 로그인 상태로 홈이 렌더된다", async () => {
    // TODO: await expect(homePage.bottomNav).toBeVisible();
  });
});
