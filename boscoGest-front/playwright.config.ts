import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-end tests.
 *
 * These cover what a unit test cannot: that the application actually renders
 * and reacts. That matters more than usual here because every component uses
 * OnPush change detection, where a component that fails to mark itself dirty
 * shows stale or empty content while the build stays perfectly green.
 *
 * They need a running backend and a database with seeded data. See e2e/README.md.
 */
export default defineConfig({
  testDir: './e2e',
  // En CI se saltan las pruebas marcadas @local. Son las que allí no pueden
  // pasar, por dos motivos ajenos al código:
  //
  //   - Las líneas base visuales están generadas en macOS y se llaman
  //     *-chromium-darwin.png. El CI corre en Linux, donde Playwright busca
  //     *-chromium-linux.png, no encuentra ninguna y falla siempre.
  //   - Algunas pruebas necesitan un centenar de socios (búsqueda, paginación,
  //     el diálogo de borrado) y allí solo existe el usuario del seeder.
  //
  // En local sí se ejecutan, que es donde sirven de red de seguridad. Un job
  // permanentemente en rojo no lo mira nadie, y acaba tapando fallos reales.
  grepInvert: process.env.CI ? /@local/ : undefined,

  // Los generadores de capturas quedan fuera de la ejecución normal. No son
  // pruebas: escriben imágenes para la documentación y para las fichas de las
  // tiendas, y necesitan una base de datos con contenido de demostración. En
  // una suite corriente hacen dos cosas malas — fallan cuando no hay esos
  // datos, y cuando sí arrancan sobrescriben las imágenes ya revisadas con lo
  // que haya en ese momento.
  //
  // Se lanzan a mano, por ejemplo:
  //   npx playwright test play-shots --project=chromium
  testIgnore: [
    '**/play-shots.spec.ts',
    '**/guide-shots.spec.ts',
    '**/guide2-shots.spec.ts',
    '**/guide2-updates.spec.ts',
    '**/screenshots.spec.ts',
  ],
  // The suite talks to a real backend, so tests share state and must not race.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',

  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:4200',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    // Generous: the dev server compiles lazy chunks on first navigation.
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  projects: [
    // Signs in once through the API and saves the session for everything else,
    // rather than driving the login form in every test.
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
    },
  ],

  // Started only when E2E_START_SERVER is set: otherwise the runner assumes a
  // server is already up, which is the usual case while developing.
  webServer: process.env.E2E_START_SERVER
    ? {
        command: 'npm start',
        url: process.env.E2E_BASE_URL ?? 'http://localhost:4200',
        reuseExistingServer: true,
        timeout: 180_000,
      }
    : undefined,
});
