import { expect, test } from '@playwright/test';
import { fetchToken, TOKEN_STORAGE_KEY, API_URL } from './support';

/**
 * Screenshots for the fees user guide.
 *
 * Not assertions — these produce the figures the guide embeds, so they are run
 * deliberately rather than as part of the suite. Each one is framed on the
 * element being explained rather than the whole page, so the figure stays
 * legible when scaled down to fit a printed page.
 */
const OUT = process.env.GUIDE_SHOT_DIR ?? 'guide-shots';

/** Signs in as the given member so their own view can be captured. */
async function loginAs(page: any, email: string, password: string) {
  const response = await fetch(`${API_URL}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ identifier: email, password }),
  });
  if (!response.ok) throw new Error(`login failed for ${email}: ${response.status}`);
  const { access_token } = (await response.json()) as { access_token: string };
  await page.goto('/login');
  await page.evaluate(
    ([key, value]: [string, string]) => localStorage.setItem(key, value),
    [TOKEN_STORAGE_KEY, access_token] as [string, string]
  );
}

test.use({ viewport: { width: 1440, height: 900 } });

/** The entity the sample fee belongs to. The picker opens on the first entity
 *  alphabetically, which is not it. */
const ENTITY = process.env.GUIDE_ENTITY ?? 'Horta';

async function openFeesFor(page: any, entity = ENTITY) {
  await page.goto('/fees');
  await page.waitForTimeout(2000);
  const picker = page.locator('mat-select').first();
  await picker.click();
  await page.waitForTimeout(500);
  await page.getByRole('option', { name: entity, exact: true }).first().click();
  await page.waitForTimeout(2000);
}

test('01 admin fee list', async ({ page }) => {
  await openFeesFor(page);
  await page.screenshot({ path: `${OUT}/01-cuotas-lista.png`, fullPage: false });
});

test('02 new fee form', async ({ page }) => {
  await openFeesFor(page);
  const newFee = page.getByRole('button', { name: /nueva cuota/i });
  if (await newFee.count()) {
    await newFee.first().click();
    await page.waitForTimeout(1200);
  }
  await page.screenshot({ path: `${OUT}/02-cuota-nueva.png`, fullPage: false });
});

test('03 roster and generation', async ({ page }) => {
  await openFeesFor(page);
  const tab = page.getByRole('tab', { name: /asignaciones/i });
  if (await tab.count()) {
    await tab.first().click();
    await page.waitForTimeout(1500);
  }
  // The button is disabled until a fee is chosen in this form.
  const feePicker = page.locator('form.generate-form mat-select').first();
  if (await feePicker.count()) {
    await feePicker.click();
    await page.waitForTimeout(500);
    await page.getByRole('option').first().click();
    await page.waitForTimeout(1500);
  }
  const view = page.getByRole('button', { name: /ver socios y padr/i });
  if (await view.count()) {
    await view.first().click();
    await page.waitForTimeout(2500);
  }
  await page.screenshot({ path: `${OUT}/03-padron.png`, fullPage: true });
});

test('04 proof queue', async ({ page }) => {
  await openFeesFor(page);
  const tab = page.getByRole('tab', { name: /asignaciones/i });
  if (await tab.count()) {
    await tab.first().click();
    await page.waitForTimeout(2000);
  }
  const queue = page.locator('.proof-queue');
  if (await queue.count()) {
    await queue.scrollIntoViewIfNeeded();
    await page.waitForTimeout(600);
    await queue.screenshot({ path: `${OUT}/04-cola-justificantes.png` });
  } else {
    await page.screenshot({ path: `${OUT}/04-cola-justificantes.png`, fullPage: true });
  }
});

test('05 assignments table', async ({ page }) => {
  await openFeesFor(page);
  const tab = page.getByRole('tab', { name: /asignaciones/i });
  if (await tab.count()) {
    await tab.first().click();
    await page.waitForTimeout(2000);
  }
  // Choose the fee first: an empty picker and a disabled button read as a
  // broken screen in a figure.
  const feePicker = page.locator('form.generate-form mat-select').first();
  if (await feePicker.count()) {
    await feePicker.click();
    await page.waitForTimeout(500);
    await page.getByRole('option').first().click();
    await page.waitForTimeout(1500);
  }
  // Framed on the table rather than the page, so the rows stay legible in print.
  const table = page.locator('table').last();
  if (await table.count()) {
    await table.scrollIntoViewIfNeeded();
    await page.waitForTimeout(600);
    await table.screenshot({ path: `${OUT}/05-asignaciones.png` });
  } else {
    await page.screenshot({ path: `${OUT}/05-asignaciones.png`, fullPage: true });
  }
});

test('06 member view', async ({ page }) => {
  await loginAs(page, 'maria.lopez@ejemplo.org', 'Socio12345!');
  await page.goto('/fees/mine');
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/06-mis-cuotas.png`, fullPage: false });
});

test('07 proof dialog', async ({ page }) => {
  await loginAs(page, 'maria.lopez@ejemplo.org', 'Socio12345!');
  await page.goto('/fees/mine');
  await page.waitForTimeout(2500);
  const pay = page.getByRole('button', { name: /he pagado/i });
  await expect(pay.first()).toBeVisible({ timeout: 10_000 });
  await pay.first().click();
  await page.waitForTimeout(1200);
  const dialog = page.locator('mat-dialog-container');
  await dialog.screenshot({ path: `${OUT}/07-enviar-justificante.png` });
});

test('08 member awaiting review', async ({ page }) => {
  await loginAs(page, 'luis.perez@ejemplo.org', 'Socio12345!');
  await page.goto('/fees/mine');
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/08-justificante-enviado.png`, fullPage: false });
});
