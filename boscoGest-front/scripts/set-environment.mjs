#!/usr/bin/env node
/**
 * Generates src/environments/environment.prod.ts from a single domain value.
 *
 * The file used to carry a hardcoded EC2 IP over plain http, which meant every
 * redeployment to a different host required editing source, and the whole app
 * — tokens included — talked to the API unencrypted. It is now generated and
 * git-ignored, so the deployment target lives in configuration rather than in
 * the repository.
 *
 * Configuration, in order of precedence:
 *   API_URL + WS_URL   explicit URLs, for anything that does not follow the
 *                      api.<domain> convention
 *   APP_DOMAIN         base domain; yields https://api.<domain> and
 *                      wss://api.<domain>
 *
 * Either can come from the environment or from a .env.build file next to
 * package.json.
 */

import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const target = join(root, 'src', 'environments', 'environment.prod.ts');
const envFile = join(root, '.env.build');

/** Reads KEY=value pairs from .env.build, ignoring comments and blanks. */
function readEnvFile(path) {
  if (!existsSync(path)) return {};
  return Object.fromEntries(
    readFileSync(path, 'utf8')
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('#'))
      .map((line) => {
        const index = line.indexOf('=');
        return [line.slice(0, index).trim(), line.slice(index + 1).trim()];
      })
      .filter(([key]) => key)
  );
}

const fileEnv = readEnvFile(envFile);
const read = (key) => process.env[key] ?? fileEnv[key] ?? '';

const domain = read('APP_DOMAIN').replace(/^https?:\/\//, '').replace(/\/$/, '');
let apiUrl = read('API_URL');
let wsUrl = read('WS_URL');

if (!apiUrl && domain) apiUrl = `https://api.${domain}`;
if (!wsUrl && domain) wsUrl = `wss://api.${domain}`;

if (!apiUrl || !wsUrl) {
  console.error(`
Cannot generate environment.prod.ts: the deployment target is not configured.

Set APP_DOMAIN (or API_URL and WS_URL explicitly), either in the environment
or in ${envFile}:

    APP_DOMAIN=boscogest.es

which produces:

    apiUrl: https://api.boscogest.es
    wsUrl:  wss://api.boscogest.es

Copy .env.build.example to .env.build to get started. The build stops here on
purpose — a production bundle pointing at the wrong host, or at plain http,
fails silently at runtime and is far harder to notice than a failed build.
`);
  process.exit(1);
}

// Cleartext would defeat the point: tokens and personal data travel over these
// URLs, and Android blocks cleartext from a WebView served over https.
for (const [name, value] of [['API_URL', apiUrl], ['WS_URL', wsUrl]]) {
  if (value.startsWith('http://') || value.startsWith('ws://')) {
    console.error(`\n${name} uses an unencrypted scheme (${value}).`);
    console.error('Use https:// and wss://, or set ALLOW_INSECURE=1 to override.\n');
    if (read('ALLOW_INSECURE') !== '1') process.exit(1);
  }
}

// Push on Android goes through Firebase, which reads its configuration from
// android/app/google-services.json at build time. Without that file the
// plugin's register() throws a Java exception that closes the app — every
// login with notifications allowed did exactly that. The app only asks for a
// push token when the file was there.
const androidPush = existsSync(join(root, 'android', 'app', 'google-services.json'));
if (!androidPush) {
  console.warn(
    'android/app/google-services.json not found: Android builds will not register for push notifications.'
  );
}

const contents = `// GENERATED FILE — do not edit, and do not commit.
// Produced by scripts/set-environment.mjs from APP_DOMAIN / API_URL / WS_URL.
// Regenerate with: npm run config
export const environment = {
  production: true,
  apiUrl: '${apiUrl}',
  wsUrl: '${wsUrl}',
  androidPush: ${androidPush}
};
`;

mkdirSync(dirname(target), { recursive: true });
writeFileSync(target, contents);
console.log(`environment.prod.ts -> apiUrl=${apiUrl} wsUrl=${wsUrl}`);
