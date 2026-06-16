import { FullConfig } from "@playwright/test";

async function globalTeardown(_config: FullConfig) {
  // TODO: dev_login으로 생성된 테스트 데이터 정리가 필요하면 여기서 처리.
  console.log("teardown complete");
}

export default globalTeardown;
