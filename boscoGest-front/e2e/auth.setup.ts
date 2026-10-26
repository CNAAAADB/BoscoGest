import { test as setup } from '@playwright/test';
import { fetchToken, TOKEN_STORAGE_KEY } from './support';

/**
 * Signs in once and saves the browser state for every other test.
 *
 * The token is obtained from the API rather than by filling in the login form:
 * the form is covered by its own test, and repeating it everywhere would make
 * the whole suite fail for one unrelated reason.
 */
setup('authenticate', async ({ page }) => {
  const token = await fetchToken();

  // localStorage is per-origin, so the page must be on it before writing.
  await page.goto('/login');
  await page.evaluate(
    ([key, value]) => localStorage.setItem(key, value),
    [TOKEN_STORAGE_KEY, token] as const
  );

  await page.context().storageState({ path: 'e2e/.auth/user.json' });
});
