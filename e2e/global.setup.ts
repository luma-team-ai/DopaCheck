import { chromium, FullConfig } from "@playwright/test";
import path from "path";

const AUTH_FILE = path.join(__dirname, ".auth/user.json");

/**
 * E2E 인증 세팅.
 *
 * 이 앱은 Google/Kakao OAuth 전용 로그인이라 이메일/비밀번호 폼이 없다.
 * 외부 IdP를 E2E에서 통과시키는 대신, 로컬 전용 우회 라우트 `/auth/dev_login`을
 * 사용한다(routes/dev_only.py — FLASK_ENV=development + localhost 요청에서만 동작).
 * 이 라우트는 dev_test@example.com 계정으로 세션을 만들고 홈(/)으로 리다이렉트한다.
 *
 * 캡처한 storageState(세션 쿠키)는 chromium:auth 프로젝트가 재사용한다.
 */
async function globalSetup(config: FullConfig) {
  const { baseURL } = config.projects[0].use;
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto(`${baseURL}/auth/dev_login`);
  // dev_login은 "/"로 리다이렉트하고, "/"는 다시 "/home"으로 302된다. 최종 도착지를 기다린다.
  await page.waitForURL(/\/home/);

  await context.storageState({ path: AUTH_FILE });
  await browser.close();
}

export default globalSetup;
