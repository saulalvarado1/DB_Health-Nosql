import { defineConfig, devices } from '@playwright/test'

const baseURL = process.env.E2E_BASE_URL
const browserChannel = process.env.E2E_BROWSER_CHANNEL as 'chrome' | 'msedge' | undefined

if (!baseURL) {
  throw new Error('E2E_BASE_URL debe apuntar al frontend aislado.')
}

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 120_000,
  expect: {
    timeout: 20_000,
  },
  reporter: [['list']],
  use: {
    baseURL,
    screenshot: 'only-on-failure',
    trace: 'off',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        ...(browserChannel ? { channel: browserChannel } : {}),
      },
    },
  ],
  outputDir: 'test-results',
})
