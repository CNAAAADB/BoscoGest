import { expect, test } from '@playwright/test';

/**
 * Text contrast, which NFR-QLT-01 (WCAG 2.1 AA) and NFR-QLT-02 ("soporte a
 * usuarios mayores (tipografias y contrastes)") both require.
 *
 * WCAG 1.4.3 asks for 4.5:1 on body text and 3:1 on large text (>=18.66px
 * bold, or >=24px).
 */
const PAGES = ['/dashboard', '/users', '/users/new', '/entities', '/my-profile'];

for (const path of PAGES) {
  test(`${path} meets AA contrast`, async ({ page }) => {
    await page.goto(path);
    await page.waitForSelector('app-root', { timeout: 15_000 });
    await page.waitForTimeout(1000);

    const failures = await page.evaluate(() => {
      const toRgb = (value: string) => {
        const m = value.match(/rgba?\(([^)]+)\)/);
        if (!m) return null;
        const [r, g, b, a] = m[1].split(',').map(p => parseFloat(p.trim()));
        return { r, g, b, a: a ?? 1 };
      };
      const luminance = ({ r, g, b }: { r: number; g: number; b: number }) => {
        const f = (c: number) => {
          const s = c / 255;
          return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
        };
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
      };
      /** Walks ancestors until an opaque background is found. */
      const effectiveBackground = (el: Element) => {
        let node: Element | null = el;
        while (node) {
          const bg = toRgb(getComputedStyle(node).backgroundColor);
          if (bg && bg.a >= 0.95) return bg;
          node = node.parentElement;
        }
        return { r: 255, g: 255, b: 255, a: 1 };
      };

      const offenders: { text: string; ratio: number; size: number; colour: string }[] = [];
      for (const el of Array.from(document.querySelectorAll('body *'))) {
        if (el.children.length > 0) continue;           // only leaf text nodes
        const text = (el.textContent || '').trim();
        if (!text || text.length < 2) continue;
        const style = getComputedStyle(el);
        if (style.visibility === 'hidden' || style.display === 'none') continue;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;
        // Material icon fonts render glyphs, not readable text.
        if (style.fontFamily.toLowerCase().includes('material')) continue;

        const fg = toRgb(style.color);
        if (!fg || fg.a < 0.95) continue;
        const bg = effectiveBackground(el);

        const l1 = luminance(fg), l2 = luminance(bg);
        const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);

        const size = parseFloat(style.fontSize);
        const bold = parseInt(style.fontWeight, 10) >= 700;
        const large = size >= 24 || (bold && size >= 18.66);
        const required = large ? 3 : 4.5;

        if (ratio < required) {
          offenders.push({
            text: text.slice(0, 30),
            ratio: Math.round(ratio * 100) / 100,
            size: Math.round(size),
            colour: `${style.color} on rgb(${bg.r}, ${bg.g}, ${bg.b})`,
          });
        }
      }
      // De-duplicate: repeated table cells would drown the report.
      const seen = new Set<string>();
      return offenders.filter(o => {
        const key = `${o.colour}|${o.size}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      }).slice(0, 10);
    });

    expect(failures, `text below the AA contrast threshold on ${path}`).toEqual([]);
  });
}
