import { Page, Locator } from "@playwright/test";

/** / — 홈 대시보드 (이번 주 점수·챌린지 집계·하단 네비). */
export class HomePage {
  readonly page: Page;
  // TODO: 실제 locator 추가 (data-testid 권장)
  readonly bottomNav: Locator;

  constructor(page: Page) {
    this.page = page;
    this.bottomNav = page.locator("nav");
  }

  async goto() {
    await this.page.goto("/");
    await this.page.waitForLoadState("networkidle");
  }
}
