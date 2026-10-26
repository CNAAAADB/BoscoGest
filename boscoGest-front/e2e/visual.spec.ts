import { expect, test } from '@playwright/test';

/**
 * Pixel comparison against committed baselines.
 *
 * Its purpose is to make removing the !important overrides in styles.css a
 * verifiable operation rather than a hopeful one: with the theme now producing
 * real tokens most of them should be redundant, and this says exactly which
 * ones are not.
 *
 * Regenerate deliberately with `npm run e2e -- visual --update-snapshots` after
 * an intended visual change.
 */
const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
];

const PAGES = [
  { name: 'dashboard', path: '/dashboard' },
  { name: 'users', path: '/users' },
  { name: 'user-form', path: '/users/new' },
  { name: 'entities', path: '/entities' },
  { name: 'settings', path: '/settings' },
  { name: 'my-profile', path: '/my-profile' },
];

for (const viewport of VIEWPORTS) {
  for (const target of PAGES) {
    test(`${viewport.name} ${target.name}`, { tag: '@local' }, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(target.path);
      await page.waitForSelector('app-root', { timeout: 15_000 });
      // Let fonts, icons and any entry animation settle.
      await page.waitForTimeout(1500);

      await expect(page).toHaveScreenshot(`${viewport.name}-${target.name}.png`, {
        fullPage: true,
        // Anti-aliasing differs slightly between runs; this is tight enough to
        // catch a colour or layout change and loose enough not to flap.
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
  }
}

test('desktop datepicker open', { tag: '@local' }, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/users/new');
  await page.waitForSelector('form', { timeout: 15_000 });
  await page.locator('mat-datepicker-toggle button').first().click();
  await page.waitForSelector('.mat-datepicker-content');
  await page.waitForTimeout(800);

  await expect(page).toHaveScreenshot('desktop-datepicker-open.png', {
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

test('desktop select open', { tag: '@local' }, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/users/new');
  await page.waitForSelector('form', { timeout: 15_000 });
  await page.locator('mat-select').first().click();
  await page.waitForSelector('.mat-mdc-select-panel');
  await page.waitForTimeout(800);

  await expect(page).toHaveScreenshot('desktop-select-open.png', {
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

test('desktop confirm dialog', { tag: '@local' }, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/users');
  await page.waitForSelector('table.users-table tbody tr', { timeout: 15_000 });
  await page.locator('button.delete-button').first().click();
  await page.waitForSelector('.mat-mdc-dialog-surface');
  await page.waitForTimeout(800);

  await expect(page).toHaveScreenshot('desktop-confirm-dialog.png', {
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
