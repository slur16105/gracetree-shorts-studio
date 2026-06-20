import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 20_000,
  fullyParallel: false,
  workers: 1,
  reporter: 'line'
})
