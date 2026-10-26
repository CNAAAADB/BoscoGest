import { expect, test } from '@playwright/test';

/**
 * Every feature route is lazy-loaded, so reaching one means fetching a chunk at
 * runtime. A broken import fails only here — the build stays green.
 *
 * Each check also asserts the page did not bounce back to login and that
 * nothing was logged to the console: under OnPush a component can render
 * structurally while its content never arrives.
 */
/**
 * An entity with no custom branding configured answers 404, which the client
 * treats as "use the defaults". Expected, not a failure.
 */
const EXPECTED_404 = /\/branding\/entity\/\d+/;

const ROUTES = [
  { path: '/dashboard', heading: /dashboard/i },
  { path: '/users', heading: /usuarios/i },
  { path: '/entities', heading: /asociaciones/i },
  { path: '/activities', heading: /actividades/i },
  { path: '/my-profile', heading: /perfil/i },
  { path: '/settings', heading: /ajustes|configuraci/i },
];

for (const { path, heading } of ROUTES) {
  test(`${path} loads its lazy chunk and renders`, async ({ page }) => {
    // Chrome logs "Failed to load resource" for any non-2xx response, whether
    // or not the application handles it. Those are tracked separately: a
    // missing entity branding is a legitimate state that AuthService already
    // falls back from, and counting it as an application error would make the
    // suite fail on a correctly-behaving app.
    const appErrors: string[] = [];
    const failedRequests: string[] = [];
    page.on('console', msg => {
      if (msg.type() !== 'error') return;
      const text = msg.text();
      if (/Failed to load resource/i.test(text)) return;
      appErrors.push(text);
    });
    page.on('pageerror', error => appErrors.push(error.message));
    page.on('response', response => {
      if (response.status() >= 400 && !EXPECTED_404.test(response.url())) {
        failedRequests.push(`${response.status()} ${response.url()}`);
      }
    });

    await page.goto(path);

    // Redirected to login means the route or the guard is broken.
    await expect(page.locator('app-login')).toHaveCount(0);
    await expect(page).toHaveURL(new RegExp(`${path}$`));

    const content = page.locator('app-root');
    await expect(content).toContainText(heading, { timeout: 15_000 });

    expect(
      appErrors.filter(e => !/favicon|Autofocus|DevTools/i.test(e)),
      `application errors on ${path}`
    ).toEqual([]);
    expect(failedRequests, `unexpected failed requests on ${path}`).toEqual([]);
  });
}

test('an unknown route falls back to the dashboard', async ({ page }) => {
  await page.goto('/no-existe');
  await expect(page).toHaveURL(/\/dashboard$/);
});
