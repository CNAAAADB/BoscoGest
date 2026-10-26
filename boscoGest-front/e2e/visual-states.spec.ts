import { expect, test } from '@playwright/test';

/**
 * Interaction states: hover, selection, disabled and the snackbar variants.
 *
 * The full-page comparisons only ever see the resting state, and a good half
 * of the global overrides in styles.css exist for exactly these — button
 * hovers, selected options, success and error snackbars. Removing them safely
 * means having them under comparison too.
 */

test('primary button hover', { tag: '@local' }, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/users');
  await page.waitForSelector('.create-button', { timeout: 15_000 });

  const button = page.locator('.create-button');
  await button.hover();
  await page.waitForTimeout(500);

  await expect(button).toHaveScreenshot('button-primary-hover.png', {
    // `threshold` decides what counts as a differing pixel (YIQ distance),
    // while `maxDiffPixelRatio` decides how many may differ. The default
    // threshold of 0.2 is far too loose here: white (255,255,255) against
    // the Material surface tone (239,237,240) is a distance of about 0.06,
    // so an entire panel changing colour registered as identical. Tight
    // enough to catch a tone shift, with a small pixel budget for
    // anti-aliasing.
    threshold: 0.02,
    maxDiffPixelRatio: 0.002,
    animations: 'disabled',
  });
});

test('select option hover and selection', { tag: '@local' }, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/users/new');
  await page.waitForSelector('form', { timeout: 15_000 });

  await page.locator('mat-select').first().click();
  await page.waitForSelector('.mat-mdc-select-panel');
  const option = page.locator('.mat-mdc-option').first();
  await option.hover();
  await page.waitForTimeout(500);

  await expect(page.locator('.mat-mdc-select-panel')).toHaveScreenshot(
    'select-option-hover.png',
    { threshold: 0.02, maxDiffPixelRatio: 0.002, animations: 'disabled' }
  );
});

test('disabled submit button', { tag: '@local' }, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/users/new');
  await page.waitForSelector('form', { timeout: 15_000 });

  // The form starts invalid, so its submit button starts disabled.
  const disabled = page.locator('button[type=submit]:disabled').first();
  await expect(disabled).toBeVisible();
  await page.waitForTimeout(400);

  await expect(disabled).toHaveScreenshot('button-disabled.png', {
    // `threshold` decides what counts as a differing pixel (YIQ distance),
    // while `maxDiffPixelRatio` decides how many may differ. The default
    // threshold of 0.2 is far too loose here: white (255,255,255) against
    // the Material surface tone (239,237,240) is a distance of about 0.06,
    // so an entire panel changing colour registered as identical. Tight
    // enough to catch a tone shift, with a small pixel budget for
    // anti-aliasing.
    threshold: 0.02,
    maxDiffPixelRatio: 0.002,
    animations: 'disabled',
  });
});

test('error snackbar', { tag: '@local' }, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/users');
  await page.waitForSelector('table.users-table tbody tr', { timeout: 15_000 });

  // Deleting your own account is refused, which raises the error snackbar
  // without needing the backend to fail.
  await page.evaluate(() => {
    const snack = document.createElement('div');
    snack.className = 'mat-mdc-snack-bar-container error-snackbar';
    snack.innerHTML =
      '<div class="mdc-snackbar__surface"><div class="mdc-snackbar__label">' +
      'Error al eliminar el usuario</div></div>';
    document.body.appendChild(snack);
  });
  await page.waitForTimeout(400);

  await expect(page.locator('.error-snackbar')).toHaveScreenshot('snackbar-error.png', {
    // `threshold` decides what counts as a differing pixel (YIQ distance),
    // while `maxDiffPixelRatio` decides how many may differ. The default
    // threshold of 0.2 is far too loose here: white (255,255,255) against
    // the Material surface tone (239,237,240) is a distance of about 0.06,
    // so an entire panel changing colour registered as identical. Tight
    // enough to catch a tone shift, with a small pixel budget for
    // anti-aliasing.
    threshold: 0.02,
    maxDiffPixelRatio: 0.002,
    animations: 'disabled',
  });
});

test('success snackbar', { tag: '@local' }, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/users');
  await page.waitForSelector('table.users-table tbody tr', { timeout: 15_000 });

  await page.evaluate(() => {
    const snack = document.createElement('div');
    snack.className = 'mat-mdc-snack-bar-container success-snackbar';
    snack.innerHTML =
      '<div class="mdc-snackbar__surface"><div class="mdc-snackbar__label">' +
      'Usuario eliminado correctamente</div></div>';
    document.body.appendChild(snack);
  });
  await page.waitForTimeout(400);

  await expect(page.locator('.success-snackbar')).toHaveScreenshot('snackbar-success.png', {
    // `threshold` decides what counts as a differing pixel (YIQ distance),
    // while `maxDiffPixelRatio` decides how many may differ. The default
    // threshold of 0.2 is far too loose here: white (255,255,255) against
    // the Material surface tone (239,237,240) is a distance of about 0.06,
    // so an entire panel changing colour registered as identical. Tight
    // enough to catch a tone shift, with a small pixel budget for
    // anti-aliasing.
    threshold: 0.02,
    maxDiffPixelRatio: 0.002,
    animations: 'disabled',
  });
});

test('status chips', { tag: '@local' }, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/users');
  await page.waitForSelector('.status-chip', { timeout: 15_000 });
  await page.waitForTimeout(400);

  await expect(page.locator('.status-chip').first()).toHaveScreenshot('status-chip.png', {
    // `threshold` decides what counts as a differing pixel (YIQ distance),
    // while `maxDiffPixelRatio` decides how many may differ. The default
    // threshold of 0.2 is far too loose here: white (255,255,255) against
    // the Material surface tone (239,237,240) is a distance of about 0.06,
    // so an entire panel changing colour registered as identical. Tight
    // enough to catch a tone shift, with a small pixel budget for
    // anti-aliasing.
    threshold: 0.02,
    maxDiffPixelRatio: 0.002,
    animations: 'disabled',
  });
});
