import { expect, test } from '@playwright/test';

/**
 * Overlay panels (select dropdowns, datepickers, menus, autocompletes) are
 * rendered by Angular Material into a CDK overlay container at the end of
 * <body>, outside the component's own stylesheet. A global style that resets
 * backgrounds, or a missing theme import, leaves them transparent: the content
 * behind shows through and the panel becomes unreadable.
 *
 * This walks the app opening each kind of overlay and asserts it paints an
 * opaque background.
 */

/** Parses rgb()/rgba() into components; returns null for keywords. */
function parseColor(value: string): { r: number; g: number; b: number; a: number } | null {
  const match = value.match(/rgba?\(([^)]+)\)/);
  if (!match) return null;
  const parts = match[1].split(',').map(p => parseFloat(p.trim()));
  return { r: parts[0], g: parts[1], b: parts[2], a: parts[3] ?? 1 };
}

async function assertOpaque(panel: any, label: string) {
  const background = await panel.evaluate((el: Element) => {
    const style = getComputedStyle(el);
    return {
      backgroundColor: style.backgroundColor,
      backgroundImage: style.backgroundImage,
      // A panel can also be made opaque by an ancestor inside the overlay.
      parentBackground: el.parentElement
        ? getComputedStyle(el.parentElement).backgroundColor
        : 'none',
    };
  });

  const own = parseColor(background.backgroundColor);
  const parent = parseColor(background.parentBackground);
  const opaque =
    (own !== null && own.a >= 0.95) ||
    (parent !== null && parent.a >= 0.95) ||
    background.backgroundImage !== 'none';

  expect(
    opaque,
    `${label} has a see-through background (own=${background.backgroundColor}, ` +
      `parent=${background.parentBackground}). Content behind it will bleed through.`
  ).toBe(true);
}

test('date picker panel is opaque', async ({ page }) => {
  await page.goto('/users/new');
  await page.waitForSelector('form', { timeout: 15_000 });

  const toggle = page.locator('mat-datepicker-toggle button').first();
  await expect(toggle).toBeVisible({ timeout: 10_000 });
  await toggle.click();

  const calendar = page.locator('.mat-datepicker-content');
  await expect(calendar).toBeVisible();
  await assertOpaque(calendar, 'datepicker panel (.mat-datepicker-content)');
});

test('select dropdown panel is opaque', async ({ page }) => {
  await page.goto('/users/new');
  await page.waitForSelector('form', { timeout: 15_000 });

  const select = page.locator('mat-select').first();
  await expect(select).toBeVisible({ timeout: 10_000 });
  await select.click();

  const panel = page.locator('.mat-mdc-select-panel');
  await expect(panel).toBeVisible();
  await assertOpaque(panel, 'select panel (.mat-mdc-select-panel)');
});

test('user menu panel is opaque', async ({ page }) => {
  await page.goto('/dashboard');
  await page.waitForSelector('app-root', { timeout: 15_000 });

  const menuTrigger = page.locator('[mat-menu-trigger-for], [matMenuTriggerFor]').first();
  const count = await menuTrigger.count();
  test.skip(count === 0, 'no menu trigger on this page');

  await menuTrigger.click();
  const panel = page.locator('.mat-mdc-menu-panel');
  await expect(panel).toBeVisible();
  await assertOpaque(panel, 'menu panel (.mat-mdc-menu-panel)');
});

test('dialog surface is opaque', async ({ page }) => {
  await page.goto('/users');
  await page.waitForSelector('table.users-table tbody tr', { timeout: 15_000 });

  const deleteButton = page.locator('button.delete-button').first();
  test.skip((await deleteButton.count()) === 0, 'no delete button visible');
  await deleteButton.click();

  const surface = page.locator('.mat-mdc-dialog-surface');
  await expect(surface).toBeVisible();
  await assertOpaque(surface, 'dialog surface (.mat-mdc-dialog-surface)');
});

/**
 * Opacity alone is not enough: a white panel over a white card with no shadow
 * or border has no discernible edge. Material 3 draws these from an elevation
 * token this theme leaves empty, so the computed shadow was `0 0 0 0`.
 */
const OVERLAYS_WITH_EDGE = [
  { selector: '.mat-datepicker-content', kind: 'datepicker' },
  { selector: '.mat-mdc-select-panel', kind: 'select' },
] as const;

for (const { selector, kind } of OVERLAYS_WITH_EDGE) {
  test(`${kind} panel has a visible edge`, async ({ page }) => {
    await page.goto('/users/new');
    await page.waitForSelector('form', { timeout: 15_000 });

    if (kind === 'datepicker') {
      await page.locator('mat-datepicker-toggle button').first().click();
    } else {
      await page.locator('mat-select').first().click();
    }

    const panel = page.locator(selector);
    await expect(panel).toBeVisible();

    const edge = await panel.evaluate((el: Element) => {
      const style = getComputedStyle(el);
      const shadow = style.boxShadow;
      // "rgba(...) 0px 0px 0px 0px" is declared but paints nothing.
      const withoutColours = shadow.replace(/rgba?\([^)]*\)/g, '').trim();
      const paintsShadow = shadow !== 'none' && !/^(?:0px\s*){3,4}$/.test(withoutColours);
      const borderWidth = parseFloat(style.borderTopWidth) || 0;
      return { shadow, borderWidth, paintsShadow };
    });

    expect(
      edge.paintsShadow || edge.borderWidth > 0,
      `${selector} has no visible boundary (box-shadow="${edge.shadow}", ` +
        `border-width=${edge.borderWidth}px). It blends into the card behind it.`
    ).toBe(true);
  });
}
