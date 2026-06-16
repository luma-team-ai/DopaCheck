import { Page, Locator } from "@playwright/test";

/** /score — 도파민 점수·기여도 시각화·평균 대비·상위 N% 랭킹. */
export class ScorePage {
  readonly page: Page;
  // TODO: 실제 locator 추가 (data-testid 권장)
  readonly scoreValue: Locator;

  constructor(page: Page) {
    this.page = page;
    this.scoreValue = page.locator('[data-testid="dopamine-score"]');
  }

  async goto() {
    await this.page.goto("/score");
    await this.page.waitForLoadState("networkidle");
  }
}
