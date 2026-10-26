/** Shared configuration and helpers for the end-to-end suite. */

export const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';
export const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:4200';

export const CREDENTIALS = {
  identifier: process.env.E2E_USER ?? 'superadmin@boscogest.com',
  password: process.env.E2E_PASSWORD ?? 'VerificaLocal123',
};

/** The key AuthService reads on construction to restore a session. */
export const TOKEN_STORAGE_KEY = 'authToken';

export async function fetchToken(): Promise<string> {
  const response = await fetch(`${API_URL}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(CREDENTIALS),
  });
  if (!response.ok) {
    throw new Error(
      `Could not sign in as ${CREDENTIALS.identifier}: ${response.status} ${await response.text()}\n` +
        `Is the backend running at ${API_URL} with a seeded database? See e2e/README.md.`
    );
  }
  const { access_token } = (await response.json()) as { access_token: string };
  return access_token;
}

export async function apiGet<T>(path: string, token: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
