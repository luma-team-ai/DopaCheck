import { test, expect } from "../../fixtures";
import { MyPage } from "../../pages/MyPage";

test.describe("마이페이지", () => {
  let myPage: MyPage;

  test.beforeEach(async ({ page }) => {
    myPage = new MyPage(page);
    await myPage.goto();
  });

  test("TODO: 내 정보·이번주 점수·완료 챌린지·총 분석 횟수 표시", async () => {
    // TODO
  });

  test("TODO: 기본 시급 모달 — 음수·미입력 거부", async () => {
    // TODO: FR-50 검증 (0 이상 정수만 허용)
  });
});
