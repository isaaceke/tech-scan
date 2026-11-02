import {DurableObject} from 'cloudflare:workers';
import {ScannerService} from './service.mjs';
import panel from './panel.html';
import script from './panel.js.txt';
import styles from './panel.css.txt';

export class ScannerState extends DurableObject {
  constructor(ctx, env) { super(ctx, env); this.service = new ScannerService(ctx.storage, env); }
  async fetch(request) {
    if (!await this.ctx.storage.getAlarm()) await this.ctx.storage.setAlarm(Date.now() + 3600000);
    return this.service.fetch(request);
  }
  async alarm() { await this.service.cleanup(); await this.ctx.storage.setAlarm(Date.now() + 3600000); }
}
const security = {
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store'
};
export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    let response;
    if (request.method === 'GET' && ['/', '/panel.js', '/panel.css'].includes(path)) {
      const [text, type] = path === '/' ? [panel, 'text/html'] : path === '/panel.js' ? [script, 'application/javascript'] : [styles, 'text/css'];
      response = new Response(text, {headers: {'Content-Type': type + '; charset=utf-8'}});
    } else {
      response = await env.SCANNER.get(env.SCANNER.idFromName('attair-scanner')).fetch(request);
      response = new Response(response.body, response);
    }
    for (const [key, value] of Object.entries(security)) response.headers.set(key, value);
    return response;
  }
};
