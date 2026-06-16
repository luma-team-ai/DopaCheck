import { test, expect } from "../../fixtures";
import { ScorePage } from "../../pages/ScorePage";

test.describe("도파민 점수", () => {
  let scorePage: ScorePage;

  test.beforeEach(async ({ page }) => {
    scorePage = new ScorePage(page);
    await scorePage.goto();
  });

  test("TODO: 점수·기여도·평균 대비·상위 N% 랭킹 표시", async () => {
    // TODO: 랭킹은 시드 더미(#131) 선행 필요
  });
});
