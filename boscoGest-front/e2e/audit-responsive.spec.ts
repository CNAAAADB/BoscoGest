import { expect, test } from '@playwright/test';

/**
 * Layout checks across the viewports the SRS targets: the platform is
 * explicitly web *and* mobile (SRS 3.1), so a view that only works on a
 * desktop is not finished.
 *
 * Rather than comparing pixels, these assert properties that are always wrong:
 * the page scrolling sideways, content escaping the viewport, or controls too
 * small to hit with a thumb.
 */
const VIEWPORTS = [
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 390, height: 844 },
  { name: 'mobile-small', width: 320, height: 568 },
];

const PAGES = ['/dashboard', '/users', '/users/new', '/entities', '/settings', '/my-profile'];

for (const viewport of VIEWPORTS) {
  for (const path of PAGES) {
    test(`${viewport.name} ${path} does not scroll sideways`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(path);
      await page.waitForSelector('app-root', { timeout: 15_000 });
      await page.waitForTimeout(800);

      const overflow = await page.evaluate(() => {
        const doc = document.documentElement;
        const offenders: { tag: string; cls: string; width: number }[] = [];
        if (doc.scrollWidth > doc.clientWidth + 1) {
          for (const el of Array.from(document.querySelectorAll('body *'))) {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0) continue;
            if (rect.right > doc.clientWidth + 1) {
              // Only report elements that are not inside a scroll container:
              // a table that scrolls inside its own box is correct.
              let node: HTMLElement | null = el.parentElement;
              let scrollable = false;
              while (node && node !== document.body) {
                const overflowX = getComputedStyle(node).overflowX;
                if (overflowX === 'auto' || overflowX === 'scroll') { scrollable = true; break; }
                node = node.parentElement;
              }
              if (!scrollable) {
                offenders.push({
                  tag: el.tagName.toLowerCase(),
                  cls: (el.className || '').toString().slice(0, 60),
                  width: Math.round(rect.right),
                });
              }
            }
          }
        }
        return { pageWidth: doc.scrollWidth, viewport: doc.clientWidth, offenders: offenders.slice(0, 5) };
      });

      expect(
        overflow.offenders,
        `page is ${overflow.pageWidth}px wide in a ${overflow.viewport}px viewport`
      ).toEqual([]);
    });
  }
}

test('mobile: wide tables scroll inside their own container', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/users');
  await page.waitForSelector('table.users-table tbody tr', { timeout: 15_000 });

  const result = await page.evaluate(() => {
    const table = document.querySelector('table.users-table') as HTMLElement;
    let node = table.parentElement;
    while (node && node !== document.body) {
      const overflowX = getComputedStyle(node).overflowX;
      if (overflowX === 'auto' || overflowX === 'scroll') {
        return { scrollable: true, canScroll: node.scrollWidth > node.clientWidth };
      }
      node = node.parentElement;
    }
    return { scrollable: false, canScroll: false };
  });

  expect(
    result.scrollable,
    'the users table has no horizontal scroll container, so the action buttons ' +
      'in the last column cannot be reached on a phone'
  ).toBe(true);
});

test('mobile: interactive controls are large enough to tap', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/users');
  await page.waitForSelector('table.users-table tbody tr', { timeout: 15_000 });

  const small = await page.evaluate(() => {
    // Comfort, not conformance: WCAG 2.1 sets no minimum target size at AA
    // (2.5.5 Target Size is AAA, and 2.5.8 arrived in WCAG 2.2). The SRS asks
    // for 2.1 AA, so this guards NFR-QLT-02 — usability for older members —
    // rather than a conformance criterion. 40px matches Material's own icon
    // button size.
    const MIN = 40;
    const offenders: { label: string; w: number; h: number }[] = [];
    for (const el of Array.from(document.querySelectorAll('button, a[href], [role=button]'))) {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      if (rect.width < MIN || rect.height < MIN) {
        offenders.push({
          label: (el.getAttribute('aria-label') || el.textContent || el.className || '')
            .toString().trim().slice(0, 40),
          w: Math.round(rect.width),
          h: Math.round(rect.height),
        });
      }
    }
    return offenders.slice(0, 8);
  });

  expect(small, 'controls smaller than 40x40 CSS px on a phone').toEqual([]);
});
