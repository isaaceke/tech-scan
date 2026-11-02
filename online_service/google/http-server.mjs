import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import {ScannerService, Failure} from '../src/service.mjs';

export const GOOGLE_MAX_PDF = 30 * 1024 * 1024; // Below Cloud Run's HTTP/1 32 MiB request limit.
const assets = new Map([
  ['/', ['panel.html', 'text/html']], ['/panel.js', ['panel.js.txt', 'application/javascript']],
  ['/panel.css', ['panel.css.txt', 'text/css']]
].map(([path, [file, type]]) => [path, {bytes: readFileSync(new URL('../src/' + file, import.meta.url)), type}]));
const security = {
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store'
};
export function validateEnv(env) {
  for (const key of ['PUBLIC_ORIGIN', 'CLIENT_ID', 'OWNER_TENANT', 'OWNER_ID', 'OWNER_EMAIL', 'DRIVE_ID', 'FOLDER_ID', 'FOLDER_URL'])
    if (!env[key]) throw Error('Missing service configuration: ' + key);
  const origin = new URL(env.PUBLIC_ORIGIN);
  if (origin.protocol !== 'https:' || origin.origin !== env.PUBLIC_ORIGIN) throw Error('PUBLIC_ORIGIN must be an HTTPS origin.');
  if (!/^[0-9a-f]{64}$/i.test(env.TOKEN_ENCRYPTION_KEY || '')) throw Error('Missing 32-byte token encryption secret.');
  if (!env.ALLOWED_ORIGINS) env.ALLOWED_ORIGINS = env.PUBLIC_ORIGIN;
  for (const value of env.ALLOWED_ORIGINS.split(',')) {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.origin !== value) throw Error('Invalid allowed panel origin.');
  }
}

export function createScannerServer({store, env, fetcher = fetch, clock = Date.now}) {
  validateEnv(env);
  const origins = new Set(env.ALLOWED_ORIGINS.split(','));
  const server = createServer(async (incoming, outgoing) => {
    for (const [key, value] of Object.entries(security)) outgoing.setHeader(key, value);
    try {
      const path = new URL(incoming.url, env.PUBLIC_ORIGIN).pathname;
      if (incoming.method === 'GET' && assets.has(path)) {
        const asset = assets.get(path); outgoing.setHeader('Content-Type', asset.type + '; charset=utf-8');
        outgoing.end(asset.bytes); return;
      }
      // Never trust client Host/X-Forwarded-Host or CF headers. Firebase Hosting
      // may forward a second configured origin; the service only accepts that allowlist.
      const origin = incoming.headers.origin;
      if (origin && !origins.has(origin)) throw new Failure(403, 'Use the scanner access panel.');
      const requestOrigin = origin || env.PUBLIC_ORIGIN;
      if (Number(incoming.headers['content-length']) > GOOGLE_MAX_PDF)
        throw new Failure(413, 'The PDF exceeds the online limit of 30 MB. Keep the saved PDF and reduce its size.');
      const parts = []; let size = 0;
      for await (const chunk of incoming) {
        size += chunk.length;
        if (size > GOOGLE_MAX_PDF) throw new Failure(413, 'The PDF exceeds the online limit of 30 MB. Keep the saved PDF and reduce its size.');
        parts.push(chunk);
      }
      const headers = new Headers();
      for (const [key, value] of Object.entries(incoming.headers)) {
        if (!['host', 'cf-connecting-ip', 'x-forwarded-host', 'x-forwarded-proto'].includes(key) && value !== undefined)
          headers.set(key, Array.isArray(value) ? value.join('; ') : value);
      }
      // Conservative global auth rate buckets across the service. A client cannot
      // escape throttling by supplying a forged forwarding or Cloudflare IP header.
      headers.set('cf-connecting-ip', 'google-global');
      const request = new Request(new URL(incoming.url, requestOrigin), {method: incoming.method, headers,
        ...(!['GET', 'HEAD'].includes(incoming.method) ? {body: Buffer.concat(parts)} : {})});
      const response = await store.withLease(async (db, signal) => {
        const remote = (address, options = {}) => fetcher(address, {...options,
          signal: AbortSignal.any([signal, ...(options.signal ? [options.signal] : [])])});
        const service = new ScannerService(db, {...env, HOSTING_PROVIDER: 'firebase-google-cloud', MAX_PDF_BYTES: GOOGLE_MAX_PDF}, remote, clock);
        return service.fetch(request);
      });
      outgoing.statusCode = response.status;
      for (const [key, value] of response.headers) outgoing.setHeader(key, value);
      outgoing.end(Buffer.from(await response.arrayBuffer()));
    } catch (error) {
      outgoing.statusCode = error instanceof Failure ? error.status : 503;
      outgoing.setHeader('Content-Type', 'application/json');
      if (outgoing.statusCode === 503) outgoing.setHeader('Retry-After', '5');
      outgoing.end(JSON.stringify({error: error instanceof Failure ? error.message : 'The scanner service is unavailable. The phone retains its PDF.'}));
    }
  });
  server.requestTimeout = 60000; server.headersTimeout = 30000; server.timeout = 550000;
  return server;
}
