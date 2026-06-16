import { Page } from "@playwright/test";

/**
 * 로컬 전용 우회 로그인. OAuth 폼이 없으므로 `/auth/dev_login`으로 세션을 만든다.
 * (FLASK_ENV=development + localhost에서만 동작 — routes/dev_only.py)
 */
export async function loginViaDevRoute(page: Page) {
  await page.goto("/auth/dev_login");
  // "/"는 "/home"으로 302된다. 최종 도착지를 기다린다.
  await page.waitForURL(/\/home/);
}

export async function isLoggedIn(page: Page): Promise<boolean> {
  // 헤더 프로필 아바타 드롭다운 트리거로 로그인 상태를 판단한다.
  // TODO: 템플릿에 data-testid="user-menu" 부여 후 정확도 향상.
  return page.locator('[data-testid="user-menu"]').isVisible();
}

export async function logout(page: Page) {
  await page.goto("/logout");
  await page.waitForURL(/\/login/);
}
