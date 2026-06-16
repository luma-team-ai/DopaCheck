import { test, expect } from "../../fixtures";
import { TimePage } from "../../pages/TimePage";

test.describe("시간 시각화", () => {
  let timePage: TimePage;

  test.beforeEach(async ({ page }) => {
    timePage = new TimePage(page);
    await timePage.goto();
  });

  test("TODO: 주간 사용시간 입력 후 환산·도넛 차트 표시", async () => {
    // TODO
  });
});
