import { Page, Locator } from "@playwright/test";

/** /login — 비로그인 진입 화면 (Google/Kakao 소셜 로그인 버튼). */
export class LoginPage {
  readonly page: Page;
  // TODO: 템플릿에 data-testid 부여 후 교체
  readonly googleLoginButton: Locator;
  readonly kakaoLoginButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.googleLoginButton = page.getByRole("link", { name: /google/i });
    this.kakaoLoginButton = page.getByRole("link", { name: /kakao|카카오/i });
  }

  async goto() {
    await this.page.goto("/login");
    await this.page.waitForLoadState("networkidle");
  }
}
