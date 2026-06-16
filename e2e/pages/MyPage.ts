import { Page, Locator } from "@playwright/test";

/** /mypage — 내 정보·이번주 점수·완료 챌린지 수·총 분석 횟수·기본 시급 모달. */
export class MyPage {
  readonly page: Page;
  // TODO: 실제 locator 추가 (data-testid 권장)
  readonly hourlyWageEditButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.hourlyWageEditButton = page.getByRole("button", { name: /시급/ });
  }

  async goto() {
    await this.page.goto("/mypage");
    await this.page.waitForLoadState("networkidle");
  }
}
