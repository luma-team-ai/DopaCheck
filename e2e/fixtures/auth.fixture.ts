import { test as base, Page } from "@playwright/test";

type AuthFixtures = {
  authenticatedPage: Page;
};

export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    // storageState는 playwright.config.ts의 chromium:auth 프로젝트에서 주입된다.
    await use(page);
  },
});

export { expect } from "@playwright/test";
