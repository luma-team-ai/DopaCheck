import { Page, Locator } from "@playwright/test";

/** /challenge — 기본·추천 챌린지 목록·참여·달성률 프로그레스. */
export class ChallengePage {
  readonly page: Page;
  // TODO: 실제 locator 추가 (data-testid 권장)
  readonly joinButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.joinButton = page.getByRole("button", { name: /참여하기/ });
  }

  async goto() {
    await this.page.goto("/challenge");
    await this.page.waitForLoadState("networkidle");
  }
}
