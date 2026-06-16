import { test, expect } from "../../fixtures";
import { DeliveryPage } from "../../pages/DeliveryPage";

test.describe("배달 분석", () => {
  let deliveryPage: DeliveryPage;

  test.beforeEach(async ({ page }) => {
    deliveryPage = new DeliveryPage(page);
    await deliveryPage.goto();
  });

  test("TODO: 수동입력으로 분석 후 결과·히스토리 반영", async () => {
    // TODO: 항목 입력 → 분석하기 → 결과 환산(치킨/헬스장·러닝/걷기) 확인
  });
});
