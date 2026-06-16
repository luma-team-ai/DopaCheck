import { test, expect } from "../../fixtures";
import { ReportPage } from "../../pages/ReportPage";

test.describe("종합 리포트", () => {
  let reportPage: ReportPage;

  test.beforeEach(async ({ page }) => {
    reportPage = new ReportPage(page);
    await reportPage.goto();
  });

  test("TODO: 진입 시 점수 재산출·비교차트 렌더", async () => {
    // TODO
  });
});
