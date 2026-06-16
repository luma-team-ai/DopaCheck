import { test, expect } from "../../fixtures";
import { HistoryPage } from "../../pages/HistoryPage";

test.describe("히스토리", () => {
  let historyPage: HistoryPage;

  test.beforeEach(async ({ page }) => {
    historyPage = new HistoryPage(page);
    await historyPage.goto();
  });

  test("TODO: 기간 필터·상세 조회·삭제(CSRF)", async () => {
    // TODO
  });
});
