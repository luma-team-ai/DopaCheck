import { defineConfig, devices } from "@playwright/test";
import path from "path";

export const AUTH_FILE = path.join(__dirname, "e2e/.auth/user.json");

// 포트는 환경변수로 덮어쓸 수 있다(기본 5000). macOS는 5000을 AirPlay(ControlCenter)가
// 점유하므로 로컬에선 `PORT=5055 npm run e2e`처럼 다른 포트를 쓰면 된다.
const PORT = process.env.PORT ?? "5000";
const BASE_URL = process.env.BASE_URL ?? `http://localhost:${PORT}`;

// 이 프로젝트는 Flask(Python) 앱이다. dev 서버는 `flask --app app run`으로 뜬다.
// E2E 인증은 OAuth(Google/Kakao) 대신 로컬 전용 우회 라우트 `/auth/dev_login`을 사용한다
// (FLASK_ENV=development + localhost 요청에서만 동작 — routes/dev_only.py).
export default defineConfig({
  testDir: "./e2e/specs",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI
    ? [
        ["html", { outputFolder: "playwright-report", open: "never" }],
        ["junit", { outputFile: "playwright-results.xml" }],
        ["github"],
      ]
    : [
        ["html", { outputFolder: "playwright-report", open: "never" }],
        ["list"],
      ],
  use: {
    baseURL: BASE_URL,
    // 사람이 보기 좋게 동작을 늦추려면 SLOWMO=700(ms) 처럼 주고 --headed로 실행한다.
    launchOptions: { slowMo: Number(process.env.SLOWMO ?? 0) },
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
    screenshot: "only-on-failure",
    trace: "on-first-retry",
    video: "on", // 항상 녹화 (test-results/<test>/video.webm)
  },
  globalSetup: "./e2e/global.setup.ts",
  globalTeardown: "./e2e/global.teardown.ts",
  projects: [
    { name: "setup", testMatch: /global\.setup\.ts/ },
    {
      name: "chromium:guest",
      use: { ...devices["Desktop Chrome"] },
      // 인증 불필요 시나리오 — specs/auth/(로그인) + specs/flow/(자체 로그인하는 전체 여정)
      testMatch: ["**/auth/**/*.spec.ts", "**/flow/**/*.spec.ts"],
    },
    {
      name: "chromium:auth",
      use: { ...devices["Desktop Chrome"], storageState: AUTH_FILE },
      dependencies: ["setup"],
      // 인증 필요 시나리오 — auth/·flow/ 제외 전부(홈·delivery·time·report·history·score·challenge·mypage)
      testIgnore: ["**/auth/**/*.spec.ts", "**/flow/**/*.spec.ts"],
    },
  ],
  // 로컬: FLASK_ENV=development 여야 /auth/dev_login 우회가 열린다. MariaDB가 떠 있어야 한다.
  // 이미 서버를 띄워뒀으면 그대로 재사용한다(reuseExistingServer).
  webServer: {
    command: `FLASK_ENV=development python3 -m flask --app app run --port ${PORT}`,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  outputDir: "test-results",
});
