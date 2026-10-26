import { test } from '@playwright/test';

/**
 * Re-captures for the figures the deletion rules and the role naming changed.
 *
 * Kept apart from guide2-shots so a refresh of these does not disturb the rest
 * of the guide's figures.
 */
const OUT = process.env.GUIDE_SHOT_DIR ?? 'guide2-shots';

test.use({ viewport: { width: 1440, height: 900 } });

async function shot(page: any, name: string, opts: { full?: boolean } = {}) {
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: opts.full ?? false });
}

test('05 role form now says which association it belongs to', async ({ page }) => {
  await page.goto('/roles/new');
  await page.waitForTimeout(2500);
  await shot(page, '05-rol-nuevo', { full: true });
});

test('12 deletion refused because of child associations', async ({ page }) => {
  await page.goto('/entities');
  await page.waitForTimeout(3000);

  // Walk the list looking for one the server refuses to delete. Which rows have
  // associations under them depends on the data, so ask rather than assume.
  const rows = page.locator('tr.mat-mdc-row, table tbody tr');
  const count = await rows.count();

  for (let i = 0; i < count; i++) {
    const del = rows.nth(i).locator('button.delete-button, button[matTooltip="Eliminar"]');
    if (!(await del.count())) continue;
    await del.first().click();
    await page.waitForTimeout(1800);

    const title = page.locator('h2[mat-dialog-title]');
    if ((await title.count()) && (await title.innerText()).includes('No se puede')) {
      await shot(page, '12-borrado-bloqueado');
      return;
    }
    // Not this one — back out and try the next.
    await page.locator('button.cancel-button').first().click();
    await page.waitForTimeout(800);
  }

  throw new Error('No association in the list has children; cannot capture the refusal.');
});

test('13 deletion confirmation naming the members affected', async ({ page }) => {
  await page.goto('/entities');
  await page.waitForTimeout(3000);

  const rows = page.locator('tr.mat-mdc-row, table tbody tr');
  const count = await rows.count();

  for (let i = 0; i < count; i++) {
    const del = rows.nth(i).locator('button.delete-button, button[matTooltip="Eliminar"]');
    if (!(await del.count())) continue;
    await del.first().click();
    await page.waitForTimeout(1800);

    const title = page.locator('h2[mat-dialog-title]');
    if ((await title.count()) && (await title.innerText()).includes('Eliminar asociación')) {
      await shot(page, '13-borrado-confirmacion');
      // Leave without deleting anything.
      await page.locator('button.cancel-button').first().click();
      return;
    }
    await page.locator('button.cancel-button').first().click();
    await page.waitForTimeout(800);
  }

  throw new Error('No deletable association found; cannot capture the confirmation.');
});
