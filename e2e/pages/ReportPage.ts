import { Page, Locator } from "@playwright/test";

/** /report — 통합 대시보드·도파민 점수·저번주 vs 이번주 비교차트. */
export class ReportPage {
  readonly page: Page;
  // TODO: 실제 locator 추가 (data-testid 권장)
  readonly comparisonChart: Locator;

  constructor(page: Page) {
    this.page = page;
    this.comparisonChart = page.locator("canvas");
  }

  async goto() {
    await this.page.goto("/report");
    await this.page.waitForLoadState("networkidle");
  }
}
