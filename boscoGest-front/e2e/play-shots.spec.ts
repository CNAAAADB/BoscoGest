import { test } from '@playwright/test';
import { API_URL } from './support';

/**
 * Capturas para la ficha de Google Play.
 *
 * No son aserciones: producen los PNG que se suben a la Consola, así que se
 * lanzan a mano y no como parte de la suite.
 *
 *   npx playwright test play-shots --project=chromium
 *
 * Se toman a 360×640 con deviceScaleFactor 3, es decir 1080×1920 reales: la
 * proporción 9:16 que espera Play y resolución suficiente para que el texto se
 * lea en la ficha. Los datos tienen que ser los del seeder de demostración —
 * nunca datos reales, porque estas imágenes acaban siendo públicas.
 */
const OUT = process.env.PLAY_SHOT_DIR ?? 'play-assets/screenshots';

test.use({
  viewport: { width: 360, height: 640 },
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
});

/** Espera a que la vista deje de cargar antes de disparar la captura. */
async function settle(page: any, ms = 2500) {
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(ms);
}

async function shot(page: any, name: string) {
  await page.screenshot({ path: `${OUT}/${name}.png` });
}

test('capturas de la ficha', async ({ page }) => {
  test.setTimeout(180_000);

  await page.goto('/dashboard');
  await settle(page);
  await shot(page, '01-inicio');

  await page.goto('/activities');
  await settle(page);
  await shot(page, '02-actividades');

  // El detalle, abierto desde la propia tarjeta: así no hay que adivinar el id.
  await page.locator('mat-card, .activity-card').first().click();
  await settle(page);
  await shot(page, '03-actividad');

  await page.goto('/blog');
  await settle(page);
  await shot(page, '04-blog');

  await page.goto('/fees/mine');
  await settle(page);
  await shot(page, '05-mis-cuotas');

  await page.goto('/users');
  await settle(page, 3000);
  await shot(page, '06-usuarios');

  await page.goto('/my-profile');
  await settle(page);
  await shot(page, '07-perfil');

  // La última, porque cierra la sesión: la pantalla de acceso con la marca.
  await page.goto('/login');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await settle(page);
  await shot(page, '08-acceso');
});
