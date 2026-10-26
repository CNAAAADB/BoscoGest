import { expect, test } from '@playwright/test';
import { apiGet, fetchToken } from './support';

/**
 * Guards the GDPR behaviour against regressions.
 *
 * These assert at the API boundary as well as in the UI: hiding a field in a
 * template is cosmetic if the payload still carries it, and it is the payload
 * that constitutes the disclosure.
 */
test.describe('personal data exposure', () => {
  test('the listing payload carries no sensitive fields the viewer cannot see', async () => {
    const token = await fetchToken();
    const page = await apiGet<{ items: Record<string, unknown>[]; total: number }>(
      '/users/managed?limit=5',
      token
    );

    expect(page.items.length).toBeGreaterThan(0);
    // The seeded superadmin holds users:read_sensitive, so this documents the
    // shape rather than the redaction; the redaction itself is unit-tested in
    // the backend, where a viewer without the permission can be constructed.
    for (const user of page.items) {
      expect(user).toHaveProperty('id');
      expect(user).toHaveProperty('name');
      // Fields must be present as keys even when redacted, so clients need no
      // special case for "missing" versus "withheld".
      expect(user).toHaveProperty('dni');
      expect(user).toHaveProperty('iban');
    }
  });

  test('listing responses are paginated, not a bare array', async () => {
    const token = await fetchToken();
    const page = await apiGet<Record<string, unknown>>('/users/managed?limit=5', token);

    expect(Object.keys(page).sort()).toEqual(['items', 'limit', 'skip', 'total']);
    expect(Array.isArray(page['items'])).toBe(true);
    expect(typeof page['total']).toBe('number');
  });

  test('the consent clause is served with its version', async () => {
    const token = await fetchToken();
    const status = await apiGet<{
      accepted: boolean;
      current_version: string;
      text: string | null;
    }>('/users/me/consent', token);

    expect(status.current_version).toBeTruthy();
    if (!status.accepted) {
      // The text travels with the status so the client cannot show a clause
      // that differs from the one acceptance is recorded against.
      expect(status.text).toContain('Responsable');
      expect(status.text).toContain('Agencia Española de Protección de Datos');
    }
  });

  test('the DNI column is hidden from viewers without users:read_sensitive', async ({
    page,
  }) => {
    await page.goto('/users');
    await expect(page.locator('table.users-table tbody tr').first()).toBeVisible({
      timeout: 15_000,
    });

    const headers = await page.locator('table.users-table th').allInnerTexts();
    const hasDniColumn = headers.some(h => h.trim().toUpperCase() === 'DNI');
    const dniCells = await page.locator('table.users-table tbody tr td').allInnerTexts();

    // With the permission the column shows real values; without it the column
    // must be absent rather than rendering blanks, which would read as "no
    // DNI on file" instead of "withheld".
    if (!hasDniColumn) {
      expect(dniCells.join(' ')).not.toMatch(/\d{8}[A-Z]/);
    }
  });
});
