import { defineConfig, devices } from '@playwright/test';

/**
 * Configuración para los generadores de capturas.
 *
 * No son pruebas: escriben las imágenes de la guía de usuario y de las fichas
 * de Google Play y App Store. Viven aparte de la suite por dos motivos —
 * fallan si la base de datos no tiene contenido de demostración, y cuando
 * arrancan sobrescriben imágenes ya revisadas con lo que haya en ese momento.
 *
 *   npm run e2e:shots -- play-shots
 *
 * Necesitan el stack levantado con datos de demostración; ver e2e/README.md.
 */
export default defineConfig({
  testDir: './e2e',
  // Solo los generadores. La suite normal vive en playwright.config.ts y los
  // excluye con testIgnore.
  testMatch: [
    '**/play-shots.spec.ts',
    '**/guide-shots.spec.ts',
    '**/guide2-shots.spec.ts',
    '**/guide2-updates.spec.ts',
    '**/screenshots.spec.ts',
  ],
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:4200',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
  ],
});
