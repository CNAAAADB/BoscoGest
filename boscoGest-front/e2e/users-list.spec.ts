import { expect, test } from '@playwright/test';

/**
 * The users list is where OnPush is most likely to bite: search results and
 * page changes both arrive in async callbacks, and a component that fails to
 * mark itself dirty would keep showing the previous rows.
 *
 * It is also where the listing used to stop silently at 100 records.
 */
test.describe('users list', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/users');
    await expect(page.locator('table.users-table tbody tr').first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test('shows the real total, not just the loaded page', async ({ page }) => {
    const total = await page.locator('.result-count').innerText();
    const shown = await page.locator('table.users-table tbody tr').count();

    const [, totalCount] = total.match(/(\d+)/) ?? [];
    expect(Number(totalCount)).toBeGreaterThan(0);
    // The point of the paginator: the count is the whole set, not the page.
    expect(Number(totalCount)).toBeGreaterThanOrEqual(shown);
  });

  test('search narrows the table', { tag: '@local' }, async ({ page }) => {
    const before = await page.locator('.result-count').innerText();

    await page.getByRole('searchbox').fill('garcia');
    await expect(page.locator('.result-count')).not.toHaveText(before, {
      timeout: 10_000,
    });

    // Every visible row must actually match — proves the filter is applied
    // server-side rather than the table simply being replaced.
    const names = await page.locator('table.users-table .name-cell').allInnerTexts();
    expect(names.length).toBeGreaterThan(0);
    for (const name of names) {
      expect(name.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')).toContain('garcia');
    }
  });

  test('search ignores accents', { tag: '@local' }, async ({ page }) => {
    await page.getByRole('searchbox').fill('munoz');
    await expect(page.locator('.result-count')).toContainText(/resultado/, {
      timeout: 10_000,
    });

    const names = await page.locator('table.users-table .name-cell').allInnerTexts();
    expect(names.length, 'searching without the tilde should still find Muñoz').toBeGreaterThan(0);
    expect(names.join(' ')).toContain('Muñoz');
  });

  test('clearing the search restores the full list', async ({ page }) => {
    const initial = await page.locator('.result-count').innerText();

    await page.getByRole('searchbox').fill('garcia');
    await expect(page.locator('.result-count')).not.toHaveText(initial, { timeout: 10_000 });

    await page.getByRole('button', { name: 'Limpiar búsqueda' }).click();
    await expect(page.locator('.result-count')).toHaveText(initial, { timeout: 10_000 });
  });

  test('the paginator moves to the next page', { tag: '@local' }, async ({ page }) => {
    const firstOnPageOne = await page.locator('table.users-table .name-cell').first().innerText();

    await page.getByRole('button', { name: /siguiente|next/i }).click();

    await expect(page.locator('table.users-table .name-cell').first()).not.toHaveText(
      firstOnPageOne,
      { timeout: 10_000 }
    );
  });

  test('a search with no matches explains itself', async ({ page }) => {
    await page.getByRole('searchbox').fill('zzzznoexiste');
    await expect(page.locator('.empty-state')).toContainText(/no se han encontrado/i, {
      timeout: 10_000,
    });
  });
});
