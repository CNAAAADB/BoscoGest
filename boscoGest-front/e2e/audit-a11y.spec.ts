import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

/**
 * Automated accessibility audit.
 *
 * NFR-QLT-01 requires WCAG 2.1 AA and NFR-QLT-02 calls out older members, but
 * nothing verified either. axe-core cannot prove conformance — roughly a third
 * of the criteria need a human — but it catches the mechanical failures
 * reliably, and those are what the review found most of.
 */
const PAGES = [
  { name: 'login', path: '/login', anonymous: true },
  { name: 'dashboard', path: '/dashboard' },
  { name: 'users', path: '/users' },
  { name: 'user form', path: '/users/new' },
  { name: 'entities', path: '/entities' },
  { name: 'settings', path: '/settings' },
  { name: 'my profile', path: '/my-profile' },
];

for (const { name, path } of PAGES) {
  test(`${name} has no WCAG 2.1 A/AA violations`, async ({ page }) => {
    await page.goto(path);
    await page.waitForSelector('app-root', { timeout: 15_000 });
    await page.waitForTimeout(1200);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    // Report every violation with the elements involved, so a failure says
    // what to fix rather than just that something is wrong.
    const summary = results.violations.map(v => ({
      id: v.id,
      impact: v.impact,
      help: v.help,
      nodes: v.nodes.length,
      example: v.nodes[0]?.html?.slice(0, 90),
      // For contrast failures axe reports the measured ratio and the colours,
      // which is what makes the report actionable rather than just a flag.
      detail: v.nodes[0]?.any?.[0]?.message?.slice(0, 140),
    }));

    expect(summary, `axe violations on ${path}`).toEqual([]);
  });
}

test('the document declares Spanish', async ({ page }) => {
  await page.goto('/login');
  // WCAG 3.1.1: a screen reader picks its voice and pronunciation from this.
  await expect(page.locator('html')).toHaveAttribute('lang', 'es');
});
