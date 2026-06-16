import { Page, Locator } from "@playwright/test";

/** /time — 유튜브·인스타·틱톡·게임 주간 사용시간 입력·분석. */
export class TimePage {
  readonly page: Page;
  // TODO: 실제 locator 추가 (data-testid 권장)
  readonly analyzeButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.analyzeButton = page.getByRole("button", { name: /분석/ });
  }

  async goto() {
    await this.page.goto("/time");
    await this.page.waitForLoadState("networkidle");
  }
}
