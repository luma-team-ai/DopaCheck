import { Page, Locator } from "@playwright/test";

/** /delivery — 영수증 업로드·OCR·수동입력·분석. */
export class DeliveryPage {
  readonly page: Page;
  // TODO: 실제 locator 추가 (data-testid 권장)
  readonly fileInput: Locator;
  readonly addItemButton: Locator;
  readonly analyzeButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.fileInput = page.locator('input[type="file"]');
    this.addItemButton = page.getByRole("button", { name: /항목 추가/ });
    this.analyzeButton = page.getByRole("button", { name: /분석하기/ });
  }

  async goto() {
    await this.page.goto("/delivery");
    await this.page.waitForLoadState("networkidle");
  }
}
