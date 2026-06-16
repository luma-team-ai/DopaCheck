import { Page, Locator } from "@playwright/test";

/** /history — 날짜별 기록 목록·상세·삭제·기간 필터. */
export class HistoryPage {
  readonly page: Page;
  // TODO: 실제 locator 추가 (data-testid 권장)
  readonly filterChips: Locator;

  constructor(page: Page) {
    this.page = page;
    this.filterChips = page.getByRole("button", { name: /이번 주|이번 달|전체/ });
  }

  async goto() {
    await this.page.goto("/history");
    await this.page.waitForLoadState("networkidle");
  }
}
