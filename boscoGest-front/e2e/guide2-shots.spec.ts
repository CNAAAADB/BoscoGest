import { expect, test } from '@playwright/test';

/**
 * Screenshots for the entities and users guide.
 *
 * Run deliberately, not as part of the suite: they produce the figures the
 * guide embeds. Framed on the element being explained wherever the whole page
 * would be mostly empty space.
 */
const OUT = process.env.GUIDE_SHOT_DIR ?? 'guide2-shots';

test.use({ viewport: { width: 1440, height: 900 } });

async function shot(page: any, name: string, opts: { full?: boolean } = {}) {
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: opts.full ?? false });
}

test('01 entity list', async ({ page }) => {
  await page.goto('/entities');
  await page.waitForTimeout(2500);
  await shot(page, '01-asociaciones-lista');
});

test('02 entity form', async ({ page }) => {
  await page.goto('/entities/new');
  await page.waitForTimeout(2000);
  await shot(page, '02-asociacion-nueva');
});

test('03 entity detail', async ({ page }) => {
  await page.goto('/entities');
  await page.waitForTimeout(2500);
  const view = page.locator('button.view-button, button[matTooltip*="etalle"]').first();
  if (await view.count()) {
    await view.click();
    await page.waitForTimeout(2500);
  }
  await shot(page, '03-asociacion-detalle', { full: true });
});

test('04 roles list', async ({ page }) => {
  await page.goto('/roles');
  await page.waitForTimeout(2500);
  await shot(page, '04-roles-lista');
});

test('05 role form with permissions', async ({ page }) => {
  await page.goto('/roles/new');
  await page.waitForTimeout(2500);
  await shot(page, '05-rol-nuevo', { full: true });
});

test('06 users list', async ({ page }) => {
  await page.goto('/users');
  await page.waitForTimeout(2500);
  await shot(page, '06-usuarios-lista');
});

test('07 user form', async ({ page }) => {
  await page.goto('/users/new');
  await page.waitForTimeout(2500);
  await shot(page, '07-usuario-nuevo', { full: true });
});

test('08 membership form', async ({ page }) => {
  await page.goto('/users');
  await page.waitForTimeout(2500);
  const membership = page.locator('button.membership-button').first();
  if (await membership.count()) {
    await membership.click();
    await page.waitForTimeout(2500);
  }
  await shot(page, '08-membresia');
});

test('09 bulk import', async ({ page }) => {
  await page.goto('/users/import');
  await page.waitForTimeout(2500);
  await shot(page, '09-importacion', { full: true });
});

test('10 import history', async ({ page }) => {
  await page.goto('/users/import/history');
  await page.waitForTimeout(2500);
  await shot(page, '10-historial-importaciones');
});

test('11 search in users', async ({ page }) => {
  await page.goto('/users');
  await expect(page.locator('table.users-table tbody tr').first()).toBeVisible({ timeout: 15_000 });
  await page.getByRole('searchbox').fill('munoz');
  await page.waitForTimeout(2000);
  const card = page.locator('mat-card').first();
  await card.screenshot({ path: `${OUT}/11-busqueda.png` });
});
