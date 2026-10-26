import { test } from '@playwright/test';

/**
 * Captures the application at three viewports for visual review.
 *
 * Not assertions — a reference set to compare against after a change, and the
 * only practical way to inspect layout, spacing and colour.
 */
const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 768, height: 1024 },
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

const OUT = process.env.SHOT_DIR ?? 'shots';

for (const viewport of VIEWPORTS) {
  for (const target of PAGES) {
    test(`${OUT} ${viewport.name} ${target.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(target.path);
      await page.waitForSelector('app-root', { timeout: 15_000 });
      await page.waitForTimeout(1200);
      await page.screenshot({
        path: `${OUT}/${viewport.name}-${target.name}.png`,
        fullPage: true,
      });
    });
  }
}

test(`${OUT} desktop datepicker-open`, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/users/new');
  await page.waitForSelector('form', { timeout: 15_000 });
  await page.locator('mat-datepicker-toggle button').first().click();
  await page.waitForSelector('.mat-datepicker-content');
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/desktop-datepicker-open.png` });
});

test(`${OUT} desktop select-open`, async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/users/new');
  await page.waitForSelector('form', { timeout: 15_000 });
  await page.locator('mat-select').first().click();
  await page.waitForSelector('.mat-mdc-select-panel');
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/desktop-select-open.png` });
});
