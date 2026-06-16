import { Page, Locator } from "@playwright/test";

/** /admin — 관리자 통계 대시보드 (admin_required 가드, role='admin'만 접근). */
export class AdminPage {
  readonly page: Page;
  // TODO: 실제 locator 추가 (data-testid 권장)
  readonly statsTotalUsers: Locator;

  constructor(page: Page) {
    this.page = page;
    this.statsTotalUsers = page.locator('[data-testid="stat-total-users"]');
  }

  async goto() {
    await this.page.goto("/admin");
    await this.page.waitForLoadState("networkidle");
  }
}
