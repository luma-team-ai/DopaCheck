import { test, expect } from "../../fixtures";
import { ChallengePage } from "../../pages/ChallengePage";

test.describe("챌린지", () => {
  let challengePage: ChallengePage;

  test.beforeEach(async ({ page }) => {
    challengePage = new ChallengePage(page);
    await challengePage.goto();
  });

  test("TODO: 챌린지 참여 후 활성 상태·달성률 반영", async () => {
    // TODO: 동일 챌린지 활성 중복 참여 불가(FR-35)도 검증
  });
});
