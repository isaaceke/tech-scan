// Hosting adapters persist and serialize all mutable state. PDFs stay on the
// phone until this service independently reads back the owner's OneDrive copy.
export const VERSION = '1.1.0';
import {createHash} from 'node:crypto';
export const MAX_PDF = 32 * 1024 * 1024;
const GRAPH = 'https://graph.microsoft.com/v1.0';
const LOGIN = 'https://login.microsoftonline.com';
const REDIRECT = 'techlogscan://auth';
const GOOGLE_AUTH = 'https://accounts.google.com/o/oauth2/v2/auth';
const GOOGLE_TOKEN = 'https://oauth2.googleapis.com/token';
const GOOGLE_USERINFO = 'https://openidconnect.googleapis.com/v1/userinfo';
const enc = new TextEncoder();
const dec = new TextDecoder();
export class Failure extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
const check = (ok, message, status = 400) => { if (!ok) throw new Failure(status, message); };
const hex = bytes => [...new Uint8Array(bytes)].map(x => x.toString(16).padStart(2, '0')).join('');
export const sha256 = async bytes => hex(await crypto.subtle.digest('SHA-256', bytes));
const base64 = bytes => btoa(String.fromCharCode(...bytes));
const unbase64 = value => Uint8Array.from(atob(value), c => c.charCodeAt(0));
const random = () => base64(crypto.getRandomValues(new Uint8Array(32))).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
const encode = value => encodeURIComponent(value);
export function email(value) {
  check(typeof value === 'string', 'Enter the Microsoft account email.');
  const result = value.trim().toLowerCase();
  check(result.length <= 254 && /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(result), 'Enter the Microsoft account email.');
  return result;
}
export async function bounded(response, limit) {
  const parts = []; let size = 0;
  if (!response.body) return new Uint8Array();
  const reader = response.body.getReader();
  try {
    for (;;) {
      const {value, done} = await reader.read(); if (done) break;
      size += value.byteLength;
      check(size <= limit, 'The PDF or response exceeds the permitted size.', 413);
      parts.push(value);
    }
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  finally { reader.releaseLock(); }
  const result = new Uint8Array(size); let position = 0;
  for (const part of parts) { result.set(part, position); position += part.byteLength; }
  return result;
}
const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), {
  status, headers: {'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...headers}
});

export class ScannerService {
  constructor(storage, env, fetcher = fetch, clock = Date.now) {
    this.db = storage; this.env = env; this.fetcher = (address, options) => fetcher(address, options); this.clock = clock;
    this.tail = Promise.resolve();
  }
  // Serialize token refresh, permission decisions and delivery commits across
  // network awaits. Runtime restarts recover exclusively from durable records.
  async fetch(request) {
    const work = this.tail.then(() => this.route(request));
    this.tail = work.catch(() => {});
    try { return await work; }
    catch (error) {
      return json({error: error instanceof Failure ? error.message : 'The online service could not complete this operation. The phone retains its PDF.'},
        error instanceof Failure ? error.status : 503);
    }
  }
  destination() {
    return {drive_id: this.env.DRIVE_ID, folder_id: this.env.FOLDER_ID,
      owner_id: this.env.OWNER_ID, owner_email: this.env.OWNER_EMAIL, folder_url: this.env.FOLDER_URL};
  }
  maxPdf() { return Math.min(MAX_PDF, Number(this.env.MAX_PDF_BYTES) || MAX_PDF); }
  // Commit an action and its audit event together. No PDF or token enters audit.
  async commit(changes, action, actor, subject) {
    await this.db.transaction(async tx => {
      const head = await tx.get('audit-head') || {sequence: 0, hash: ''};
      const event = {sequence: head.sequence + 1, previous_hash: head.hash,
        timestamp: this.clock(), action, actor: {id: actor.id, email: actor.email}, subject};
      event.hash = await sha256(enc.encode(JSON.stringify(event)));
      for (const [key, value] of changes) {
        if (value === undefined) await tx.delete(key); else await tx.put(key, value);
      }
      await tx.put('audit:' + String(event.sequence).padStart(16, '0'), event);
      await tx.put('audit-head', {sequence: event.sequence, hash: event.hash});
    });
  }
  async key() {
    check(/^[0-9a-f]{64}$/i.test(this.env.TOKEN_ENCRYPTION_KEY || ''), 'Online storage setup is incomplete.', 503);
    if (!this.cryptoKey) this.cryptoKey = await crypto.subtle.importKey('raw',
      Uint8Array.from(this.env.TOKEN_ENCRYPTION_KEY.match(/../g), v => parseInt(v, 16)), 'AES-GCM', false, ['encrypt', 'decrypt']);
    return this.cryptoKey;
  }
  async seal(value, context) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ciphertext = await crypto.subtle.encrypt({name: 'AES-GCM', iv, additionalData: enc.encode(context)}, await this.key(), enc.encode(JSON.stringify(value)));
    // Small token records only; never base64-encode a PDF.
    return {iv: base64(iv), ciphertext: base64(new Uint8Array(ciphertext))};
  }
  async open(value, context) {
    check(value, 'Sign in again to reconnect the online service.', 401);
    try {
      return JSON.parse(dec.decode(await crypto.subtle.decrypt({name: 'AES-GCM', iv: unbase64(value.iv),
        additionalData: enc.encode(context)}, await this.key(), unbase64(value.ciphertext))));
    } catch { throw new Failure(401, 'Sign in again to reconnect the online service.'); }
  }
  async requestJson(request) {
    check((request.headers.get('content-type') || '').startsWith('application/json'), 'Send a JSON request.', 415);
    try { return JSON.parse(dec.decode(await bounded(request, 16384))); }
    catch (error) { if (error instanceof Failure) throw error; throw new Failure(400, 'Invalid request.'); }
  }
  async remote(url, options = {}) {
    try { return await this.fetcher(url, {...options, redirect: 'manual', signal: AbortSignal.timeout(60000)}); }
    catch { throw new Failure(503, 'Microsoft is unreachable. The phone retains its PDF for retry.'); }
  }
  async oauth(realm, endpoint, fields) {
    const response = await this.remote(`${LOGIN}/${encode(realm)}/oauth2/v2.0/${endpoint}`, {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: new URLSearchParams(fields).toString()
    });
    let result;
    try { result = JSON.parse(dec.decode(await bounded(response, 65536))); }
    catch { throw new Failure(503, 'Microsoft sign-in returned an invalid response.'); }
    return result;
  }
  async googleOAuth(endpoint, fields) {
    const response = await this.remote(endpoint, {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: new URLSearchParams(fields).toString()
    });
    let result;
    try { result = JSON.parse(dec.decode(await bounded(response, 65536))); }
    catch { throw new Failure(503, 'Google sign-in returned an invalid response.'); }
    return result;
  }
  async googleProfile(token, idToken) {
    if (idToken && typeof idToken === 'string' && idToken.split('.').length === 3) {
      try {
        const raw = idToken.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        const pad = raw.padEnd(raw.length + (4 - raw.length % 4) % 4, '=');
        const payload = JSON.parse(dec.decode(unbase64(pad)));
        if (payload.sub && payload.email) {
          check(payload.email_verified !== false, 'Google email address is not verified.', 401);
          return {id: 'google:' + payload.sub, email: email(payload.email), name: payload.name || payload.email};
        }
      } catch {}
    }
    const response = await this.remote(GOOGLE_USERINFO, {headers: {Accept: 'application/json', Authorization: 'Bearer ' + token}});
    if (!response.ok) { await response.body?.cancel(); throw new Failure(401, 'Google did not verify the account.'); }
    let info;
    try { info = JSON.parse(dec.decode(await bounded(response, 65536))); }
    catch { throw new Failure(503, 'Google returned an invalid user profile.'); }
    check(info.sub && info.email, 'Google did not return user account details.', 401);
    check(info.email_verified !== false, 'Google email address is not verified.', 401);
    return {id: 'google:' + info.sub, email: email(info.email), name: info.name || info.email};
  }
  oauthError(result) {
    const code = /AADSTS\d+/.exec(result.error_description || '')?.[0];
    return code ? `Microsoft blocked sign-in (${code}). Your account's sign-in policy must allow this application.` : 'Microsoft sign-in did not complete. Sign in again.';
  }
  tokenRecord(result, previous = {}) {
    check(typeof result.access_token === 'string' && result.access_token.length > 10 &&
      Number.isFinite(Number(result.expires_in)) && Number(result.expires_in) > 0 &&
      (!result.token_type || result.token_type.toLowerCase() === 'bearer'), this.oauthError(result), 401);
    return {access_token: result.access_token, refresh_token: result.refresh_token || previous.refresh_token || '',
      expires_at: this.clock() + Number(result.expires_in) * 1000, scope: result.scope || previous.scope || ''};
  }
  async token(key, realm) {
    let record = await this.open(await this.db.get(key), key);
    if (this.clock() + 90000 >= record.expires_at) {
      check(record.refresh_token, 'Sign-in expired. Sign in again.', 401);
      if (realm === 'google') {
        const result = await this.googleOAuth(GOOGLE_TOKEN, {
          client_id: this.env.GOOGLE_CLIENT_ID,
          client_secret: this.env.GOOGLE_CLIENT_SECRET || '',
          grant_type: 'refresh_token',
          refresh_token: record.refresh_token
        });
        check(result.access_token && result.expires_in, result.error_description || 'Google refresh failed.', 401);
        record = {access_token: result.access_token, refresh_token: result.refresh_token || record.refresh_token,
          expires_at: this.clock() + Number(result.expires_in) * 1000, scope: result.scope || record.scope};
      } else {
        const result = await this.oauth(realm, 'token', {client_id: this.env.CLIENT_ID,
          grant_type: 'refresh_token', refresh_token: record.refresh_token});
        record = this.tokenRecord(result, record); // No new scope requested on refresh.
      }
      await this.db.put(key, await this.seal(record, key));
    }
    return record.access_token;
  }
  async ownerAccess() {
    try { return await this.token('owner-token', this.env.OWNER_TENANT); }
    catch (error) {
      if (error.status === 401) {
        await this.db.put('owner-connection-problem', true);
        throw new Failure(503, 'The owner must reconnect OneDrive in the access panel. The phone retains its PDF.');
      }
      throw error;
    }
  }
  async graph(path, token, options = {}) {
    check(path.startsWith('/') && !path.startsWith('//'), 'Invalid Microsoft address.', 503);
    const response = await this.remote(GRAPH + path, {...options, headers: {
      Accept: 'application/json', ...options.headers, Authorization: 'Bearer ' + token
    }});
    if (!response.ok) { await response.body?.cancel(); throw new Failure(response.status === 401 ? 401 :
      response.status === 404 ? 404 : response.status === 409 ? 409 : 503,
      response.status === 401 ? 'Microsoft authorization expired. Sign in again.' : 'Microsoft could not complete the folder operation. The phone retains its PDF.'); }
    try { return JSON.parse(dec.decode(await bounded(response, 262144))); }
    catch (error) { if (error instanceof Failure) throw error; throw new Failure(503, 'Microsoft returned an invalid folder response.'); }
  }
  async profile(token) {
    const profile = await this.graph('/me?$select=id,mail,userPrincipalName,displayName', token);
    check(typeof profile.id === 'string' && profile.id.length > 0, 'Microsoft did not verify the account.', 401);
    return {id: profile.id, email: email(profile.mail || profile.userPrincipalName), name: profile.displayName || ''};
  }
  owner(profile) { return profile.id.toLowerCase() === this.env.OWNER_ID.toLowerCase() && profile.email === email(this.env.OWNER_EMAIL); }
  path(id) { return `/drives/${encode(this.env.DRIVE_ID)}/items/${encode(id)}`; }
  async root(token) {
    const folder = await this.graph(this.path(this.env.FOLDER_ID) + '?$select=id,folder,parentReference', token);
    check(folder.id === this.env.FOLDER_ID && folder.folder && folder.parentReference?.driveId === this.env.DRIVE_ID,
      'Microsoft did not confirm the configured owner folder.', 503);
  }
  async session(profile, role, tokens, realm) {
    const bearer = random(); const digest = await sha256(enc.encode(bearer));
    const expiry = this.clock() + (role === 'owner' ? 12 * 3600000 : 30 * 86400000);
    await this.db.put('session:' + digest, {profile, role, expires_at: expiry, realm});
    if (tokens && role === 'operator') await this.db.put('identity-token:' + profile.id,
      await this.seal(tokens, 'identity-token:' + profile.id));
    return {session_token: bearer, expires_at: expiry, profile};
  }
  async authenticate(request, role) {
    const authorization = request.headers.get('authorization');
    const bearer = authorization?.startsWith('Bearer ') ? authorization.slice(7) :
      /(?:^|;\s*)__session=([A-Za-z0-9_-]+)/.exec(request.headers.get('cookie') || '')?.[1];
    check(bearer && /^[A-Za-z0-9_-]{43}$/.test(bearer), 'Sign in to continue.', 401);
    const digest = await sha256(enc.encode(bearer));
    const session = await this.db.get('session:' + digest);
    check(session && session.expires_at > this.clock(), 'Sign-in expired. Sign in again.', 401);
    if (role) check(session.role === role && (role !== 'owner' || this.owner(session.profile)), 'Owner sign-in is required.', 403);
    return {...session, digest};
  }
  async approved(profile, bind = false) {
    if (this.owner(profile)) return true;
    const key = 'approved:' + profile.email;
    const approval = await this.db.get(key);
    if (!approval || (approval.identity_id && approval.identity_id !== profile.id)) return false;
    if (bind && !approval.identity_id) await this.commit([[key, {...approval, identity_id: profile.id}]],
      'ACCOUNT_LINKED', profile, {email: profile.email, identity_id: profile.id});
    return true;
  }
  async rate(request, kind, limit) {
    const bucket = Math.floor(this.clock() / 3600000);
    const ip = request.headers.get('cf-connecting-ip') || 'local';
    const key = `rate:${kind}:${bucket}:` + await sha256(enc.encode(ip));
    const count = await this.db.get(key) || 0;
    check(count < limit, 'Too many sign-in requests. Try again later.', 429);
    await this.db.put(key, count + 1);
  }
  async operatorStatus(session, bind = false) {
    const allowed = await this.approved(session.profile, bind);
    const connected = !!(await this.db.get('owner-token')) && !await this.db.get('owner-connection-problem');
    return {profile: session.profile, status: !allowed ? 'DENIED' : !connected ? 'NOT_CONFIGURED' : 'APPROVED',
      message: !allowed ? 'This Microsoft email is not approved in the owner panel.' : !connected ?
        'The owner must connect the online service to OneDrive.' : 'Approved for scan delivery.', destination: this.destination()};
  }
  async route(request) {
    const url = new URL(request.url); const path = url.pathname; const method = request.method;
    if (method !== 'GET') {
      const origin = request.headers.get('origin');
      check(!origin || origin === url.origin, 'The request must come from this access panel.', 403);
    }
    if (path === '/health' && method === 'GET') return json({service: 'enugu-scanner-relay', version: VERSION,
      storage_connected: !!(await this.db.get('owner-token')) && !await this.db.get('owner-connection-problem'), destination: this.destination(),
      max_pdf_bytes: this.maxPdf(), hosting: this.env.HOSTING_PROVIDER || 'cloudflare', delivery_mode: 'direct',
      google_auth_enabled: !!this.env.GOOGLE_CLIENT_ID});
    await this.key();
    if (path === '/api/auth/start' && method === 'POST') {
      await this.rate(request, 'operator', 30);
      const state = random(), deviceSecret = random(), verifier = random();
      await this.db.put('challenge:' + state, {expires_at: this.clock() + 600000, secret_digest: await sha256(enc.encode(deviceSecret)),
        sealed: await this.seal({verifier}, 'challenge:' + state)});
      const challenge = base64(new Uint8Array(await crypto.subtle.digest('SHA-256', enc.encode(verifier)))).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
      const params = new URLSearchParams({client_id: this.env.CLIENT_ID, response_type: 'code', response_mode: 'query',
        redirect_uri: REDIRECT, scope: 'User.Read offline_access', code_challenge: challenge, code_challenge_method: 'S256',
        state, prompt: 'select_account'});
      return json({state, device_secret: deviceSecret, authorization_url: `${LOGIN}/common/oauth2/v2.0/authorize?${params}`});
    }
    if (path === '/api/auth/finish' && method === 'POST') {
      const body = await this.requestJson(request);
      check(typeof body.state === 'string' && /^[A-Za-z0-9_-]{43}$/.test(body.state) && typeof body.device_secret === 'string', 'Invalid sign-in request.');
      const challenge = await this.db.get('challenge:' + body.state);
      check(challenge && challenge.expires_at > this.clock() && challenge.secret_digest === await sha256(enc.encode(body.device_secret)), 'Sign-in response does not match this phone.', 401);
      check(typeof body.code === 'string' && body.code.length > 0 && body.code.length < 8192, 'Microsoft did not return a sign-in code.');
      const {verifier} = await this.open(challenge.sealed, 'challenge:' + body.state);
      await this.db.delete('challenge:' + body.state); // One attempt, never replay a code.
      const result = await this.oauth('common', 'token', {client_id: this.env.CLIENT_ID, grant_type: 'authorization_code',
        code: body.code, redirect_uri: REDIRECT, code_verifier: verifier});
      const tokens = this.tokenRecord(result); const profile = await this.profile(tokens.access_token);
      const signed = await this.session(profile, 'operator', tokens, 'common');
      return json({...signed, ...(await this.operatorStatus({profile}, true))});
    }
    if (path === '/api/auth/google/start' && method === 'POST') {
      check(this.env.GOOGLE_CLIENT_ID, 'Google sign-in is not configured on this scanner service.', 503);
      await this.rate(request, 'operator', 30);
      const state = random(), deviceSecret = random(), verifier = random();
      const body = await this.requestJson(request).catch(() => ({}));
      const callbackMode = body.callback_mode === 'web';
      const redirectUri = callbackMode ? (url.origin + '/api/auth/google/callback') : REDIRECT;
      await this.db.put('google-challenge:' + state, {
        expires_at: this.clock() + 600000,
        secret_digest: await sha256(enc.encode(deviceSecret)),
        redirect_uri: redirectUri,
        sealed: await this.seal({verifier, redirect_uri: redirectUri}, 'google-challenge:' + state)
      });
      const challenge = base64(new Uint8Array(await crypto.subtle.digest('SHA-256', enc.encode(verifier)))).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
      const params = new URLSearchParams({
        client_id: this.env.GOOGLE_CLIENT_ID,
        response_type: 'code',
        redirect_uri: redirectUri,
        scope: 'openid email profile',
        code_challenge: challenge,
        code_challenge_method: 'S256',
        state,
        prompt: 'select_account'
      });
      return json({state, device_secret: deviceSecret, redirect_uri: redirectUri, authorization_url: `${GOOGLE_AUTH}?${params}`});
    }
    if (path === '/api/auth/google/finish' && method === 'POST') {
      check(this.env.GOOGLE_CLIENT_ID, 'Google sign-in is not configured on this scanner service.', 503);
      const body = await this.requestJson(request);
      check(typeof body.state === 'string' && /^[A-Za-z0-9_-]{43}$/.test(body.state) && typeof body.device_secret === 'string', 'Invalid sign-in request.');
      const challenge = await this.db.get('google-challenge:' + body.state);
      check(challenge && challenge.expires_at > this.clock() && challenge.secret_digest === await sha256(enc.encode(body.device_secret)), 'Sign-in response does not match this phone.', 401);
      check(typeof body.code === 'string' && body.code.length > 0 && body.code.length < 8192, 'Google did not return a sign-in code.');
      const {verifier, redirect_uri} = await this.open(challenge.sealed, 'google-challenge:' + body.state);
      await this.db.delete('google-challenge:' + body.state);
      const result = await this.googleOAuth(GOOGLE_TOKEN, {
        client_id: this.env.GOOGLE_CLIENT_ID,
        client_secret: this.env.GOOGLE_CLIENT_SECRET || '',
        grant_type: 'authorization_code',
        code: body.code,
        redirect_uri: body.redirect_uri || redirect_uri || REDIRECT,
        code_verifier: verifier
      });
      check(result.access_token && result.expires_in, result.error_description || 'Google sign-in did not complete.', 401);
      const profile = await this.googleProfile(result.access_token, result.id_token);
      const tokens = {access_token: result.access_token, refresh_token: result.refresh_token || '', expires_in: result.expires_in, scope: result.scope || 'openid email profile'};
      const signed = await this.session(profile, 'operator', tokens, 'google');
      const status = await this.operatorStatus({profile}, true);
      if (status.status !== 'APPROVED') {
        await this.db.put('pending:' + profile.email, {email: profile.email, name: profile.name, provider: 'google', requested_at: this.clock()});
      } else {
        await this.db.delete('pending:' + profile.email);
      }
      return json({...signed, ...status});
    }
    if (path === '/api/auth/google/callback' && method === 'GET') {
      const code = url.searchParams.get('code');
      const state = url.searchParams.get('state');
      const err = url.searchParams.get('error') || url.searchParams.get('error_description');
      if (err || !code || !state) {
        const errMsg = err || 'Google sign-in was declined.';
        return new Response(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Enugu Air Scanner</title>
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <style>body{background:#0b101b;color:#e6edf7;font-family:sans-serif;padding:32px;text-align:center;}
          .box{max-width:480px;margin:40px auto;background:#141d2c;padding:32px;border-radius:12px;}
          h2{color:#f87171;}a{display:inline-block;margin-top:24px;padding:12px 24px;background:#3b82f6;color:#fff;text-decoration:none;border-radius:8px;}</style></head>
          <body><div class="box"><h2>Sign-In Did Not Complete</h2><p>${errMsg}</p>
          <a href="techlogscan://auth?error=${encode(errMsg)}">Return to Scanner App</a></div></body></html>`,
          {status: 400, headers: {'Content-Type': 'text/html; charset=utf-8'}});
      }
      const challenge = await this.db.get('google-challenge:' + state);
      if (!challenge || challenge.expires_at <= this.clock()) {
        return new Response('<!DOCTYPE html><html><body style="background:#0b101b;color:#e6edf7;font-family:sans-serif;padding:32px;text-align:center;"><h2>Sign-in request expired</h2><p>Please initiate sign-in again from the scanner app.</p></body></html>',
          {status: 401, headers: {'Content-Type': 'text/html; charset=utf-8'}});
      }
      const {verifier, redirect_uri} = await this.open(challenge.sealed, 'google-challenge:' + state);
      await this.db.delete('google-challenge:' + state);
      const result = await this.googleOAuth(GOOGLE_TOKEN, {
        client_id: this.env.GOOGLE_CLIENT_ID,
        client_secret: this.env.GOOGLE_CLIENT_SECRET || '',
        grant_type: 'authorization_code',
        code,
        redirect_uri: redirect_uri || (url.origin + '/api/auth/google/callback'),
        code_verifier: verifier
      });
      check(result.access_token && result.expires_in, result.error_description || 'Google sign-in did not complete.', 401);
      const profile = await this.googleProfile(result.access_token, result.id_token);
      const tokens = {access_token: result.access_token, refresh_token: result.refresh_token || '', expires_in: result.expires_in, scope: result.scope || 'openid email profile'};
      const signed = await this.session(profile, 'operator', tokens, 'google');
      const status = await this.operatorStatus({profile}, true);
      const appRedirect = `techlogscan://auth?session_token=${encode(signed.session_token)}&email=${encode(profile.email)}&account_id=${encode(profile.id)}&status=${encode(status.status)}&expires_at=${signed.expires_at}`;
      if (status.status !== 'APPROVED') {
        await this.db.put('pending:' + profile.email, {email: profile.email, name: profile.name, provider: 'google', requested_at: this.clock()});
      } else {
        await this.db.delete('pending:' + profile.email);
      }
      return new Response(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Enugu Air Scanner</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="0;url=${appRedirect}">
        <style>body{background:#0b101b;color:#e6edf7;font-family:sans-serif;padding:32px;text-align:center;}
        .box{max-width:480px;margin:40px auto;background:#141d2c;padding:32px;border-radius:12px;}
        h2{color:#34d399;}a{display:inline-block;margin-top:24px;padding:12px 24px;background:#10b981;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold;}</style>
        <script>window.location.href = ${JSON.stringify(appRedirect)};</script></head>
        <body><div class="box"><h2>${status.status === 'APPROVED' ? 'Sign-In Approved' : 'Sign-In Pending Approval'}</h2>
        <p>${status.status === 'APPROVED' ? 'Returning to Enugu Air Techlog Scanner...' : 'Your Google account ' + profile.email + ' is awaiting approval in the Control Center.'}</p>
        <a href="${appRedirect}">Open Techlog Scanner</a></div></body></html>`,
        {status: 200, headers: {'Content-Type': 'text/html; charset=utf-8'}});
    }
    if (path === '/api/auth/status' && method === 'GET') {
      return json(await this.operatorStatus(await this.authenticate(request)));
    }
    if (path === '/api/auth/logout' && method === 'POST') {
      const session = await this.authenticate(request); await this.db.delete('session:' + session.digest);
      return json({signed_out: true}, 200, {'Set-Cookie': '__session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0'});
    }
    if (path === '/api/owner/signin/start' && method === 'POST') {
      await this.rate(request, 'owner', 10);
      const result = await this.oauth(this.env.OWNER_TENANT, 'devicecode', {client_id: this.env.CLIENT_ID,
        scope: 'User.Read Files.ReadWrite offline_access'});
      check(result.device_code && result.user_code && result.expires_in > 0 && result.verification_uri, this.oauthError(result), 401);
      const verification = new URL(result.verification_uri);
      check(verification.protocol === 'https:' && !verification.username && !verification.password && !verification.port &&
        ['microsoft.com', 'www.microsoft.com', 'login.microsoft.com', 'login.microsoftonline.com'].includes(verification.hostname), 'Unexpected Microsoft sign-in page.', 503);
      const id = random(), secret = random(), interval = Math.max(5, Number(result.interval) || 5);
      await this.db.put('owner-challenge:' + id, {expires_at: this.clock() + Number(result.expires_in) * 1000,
        next_poll: this.clock() + interval * 1000, interval, secret_digest: await sha256(enc.encode(secret)),
        sealed: await this.seal({device_code: result.device_code}, 'owner-challenge:' + id)});
      return json({id, secret, user_code: result.user_code, verification_uri: verification.href, interval, expires_in: result.expires_in});
    }
    if (path === '/api/owner/signin/poll' && method === 'POST') {
      const body = await this.requestJson(request);
      check(typeof body.id === 'string' && /^[A-Za-z0-9_-]{43}$/.test(body.id) && typeof body.secret === 'string', 'Invalid owner sign-in.');
      const key = 'owner-challenge:' + body.id, challenge = await this.db.get(key);
      check(challenge && challenge.expires_at > this.clock() && challenge.secret_digest === await sha256(enc.encode(body.secret)), 'Owner sign-in expired or did not match this panel.', 401);
      if (this.clock() < challenge.next_poll) return json({status: 'PENDING', interval: challenge.interval}, 202);
      const {device_code} = await this.open(challenge.sealed, key);
      challenge.next_poll = this.clock() + challenge.interval * 1000; await this.db.put(key, challenge);
      const result = await this.oauth(this.env.OWNER_TENANT, 'token', {client_id: this.env.CLIENT_ID,
        grant_type: 'urn:ietf:params:oauth:grant-type:device_code', device_code});
      if (['authorization_pending', 'slow_down'].includes(result.error)) {
        if (result.error === 'slow_down') { challenge.interval += 5; challenge.next_poll = this.clock() + challenge.interval * 1000; await this.db.put(key, challenge); }
        return json({status: 'PENDING', interval: challenge.interval}, 202);
      }
      await this.db.delete(key);
      const tokens = this.tokenRecord(result); const profile = await this.profile(tokens.access_token);
      check(this.owner(profile), 'Sign in with the Microsoft account that owns the scanner folder.', 403);
      await this.root(tokens.access_token);
      await this.commit([['owner-token', await this.seal(tokens, 'owner-token')], ['owner-connection-problem', undefined]],
        'OWNER_CONNECTED', profile, this.destination());
      const signed = await this.session(profile, 'owner', null, this.env.OWNER_TENANT);
      return json({...signed, status: 'CONNECTED'}, 200, {'Set-Cookie': `__session=${signed.session_token}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=43200`});
    }
    if (path === '/api/owner/overview' && method === 'GET') {
      const session = await this.authenticate(request, 'owner');
      return json({owner: session.profile, destination: this.destination(), storage_connected: !!(await this.db.get('owner-token')) && !await this.db.get('owner-connection-problem'),
        approved_emails: [...(await this.db.list({prefix: 'approved:'})).values()],
        pending_requests: [...(await this.db.list({prefix: 'pending:'})).values()],
        receipts: [...(await this.db.list({prefix: 'receipt:', limit: 30, reverse: true})).values()],
        audit: [...(await this.db.list({prefix: 'audit:', limit: 50, reverse: true})).values()]});
    }
    if (path === '/api/owner/emails' && method === 'POST') {
      const session = await this.authenticate(request, 'owner'); const body = await this.requestJson(request);
      const approvedEmail = email(body.email);
      const key = 'approved:' + approvedEmail;
      const old = await this.db.get(key);
      if (!old) await this.commit([[key, {email: approvedEmail, identity_id: null, approved_at: this.clock(), approved_by: session.profile.id}]],
        'EMAIL_APPROVED', session.profile, {email: approvedEmail});
      await this.db.delete('pending:' + approvedEmail);
      return json({approved: true, email: approvedEmail}); // Invoked only by the human panel button.
    }
    if (path === '/api/owner/emails/remove' && method === 'POST') {
      const session = await this.authenticate(request, 'owner'); const body = await this.requestJson(request);
      const removed = email(body.email), key = 'approved:' + removed;
      if (await this.db.get(key)) await this.commit([[key, undefined]], 'EMAIL_REMOVED', session.profile, {email: removed});
      return json({removed: true});
    }
    if (path.startsWith('/api/scans/') && method === 'PUT') return this.upload(request, url);
    return json({error: 'Unknown scanner service route.'}, 404);
  }
  async ensureFolder(parentId, name, token) {
    let folder;
    try { folder = await this.graph(this.path(parentId) + ':/' + encode(name) + '?$select=id,name,folder,parentReference', token); }
    catch (error) {
      if (error.status !== 404) throw error;
      try { folder = await this.graph(this.path(parentId) + '/children', token, {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, folder: {}, '@microsoft.graph.conflictBehavior': 'fail'})}); }
      catch (race) { if (race.status !== 409) throw race; folder = await this.graph(this.path(parentId) + ':/' + encode(name), token); }
    }
    check(folder.id && folder.name === name && folder.folder && folder.parentReference?.driveId === this.env.DRIVE_ID && folder.parentReference?.id === parentId,
      'Microsoft returned a different aircraft or patches folder.', 503);
    return folder.id;
  }
  requireItem(item, job, parentId) {
    check(item.id && item.name === job.name && item.size === job.size && item.file &&
      item.parentReference?.driveId === this.env.DRIVE_ID && item.parentReference?.id === parentId,
      'Microsoft did not confirm the exact PDF destination, name and size.', 503);
  }
  async download(itemId, expected) {
    const token = await this.ownerAccess();
    let response = await this.remote(GRAPH + this.path(itemId) + '/content', {headers: {Authorization: 'Bearer ' + token}});
    let current = GRAPH + this.path(itemId) + '/content'; let redirects = 0;
    while ([301, 302, 303, 307, 308].includes(response.status)) {
      check(redirects++ < 5, 'Too many PDF download redirects.', 503);
      const location = response.headers.get('location'); await response.body?.cancel();
      check(location, 'Microsoft did not return a PDF download address.', 503);
      const next = new URL(location, current);
      check(next.protocol === 'https:' && !next.username && !next.password, 'Unexpected Microsoft download address.', 503);
      current = next.href;
      response = await this.remote(current); // No bearer sent to a preauthenticated download host.
    }
    check(response.status === 200, 'Microsoft could not read back the uploaded PDF.', 503);
    check(response.body, 'Microsoft did not return PDF bytes.', 503);
    const hash = createHash('sha256'); const reader = response.body.getReader(); let count = 0;
    try {
      for (;;) {
        const {value, done} = await reader.read(); if (done) break;
        count += value.byteLength;
        check(count <= expected, 'The PDF read back from Microsoft exceeds its expected size.', 503);
        hash.update(value);
      }
      check(count === expected, 'The PDF read back from Microsoft has the wrong size.', 503);
      return hash.digest('hex');
    } catch (error) { await reader.cancel().catch(() => {}); throw error; }
    finally { reader.releaseLock(); }
  }
  async upload(request, url) {
    const session = await this.authenticate(request);
    const tokenKey = session.role === 'owner' ? 'owner-token' : 'identity-token:' + session.profile.id;
    const verified = session.realm === 'google'
      ? await this.googleProfile(await this.token(tokenKey, 'google'))
      : await this.profile(await this.token(tokenKey, session.realm));
    check(verified.id === session.profile.id && verified.email === session.profile.email, 'The signed-in account changed.', 401);
    check(await this.approved(verified, true), 'This email is not approved in the owner panel.', 403);
    const id = url.pathname.slice('/api/scans/'.length);
    check(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id), 'Invalid scan identifier.');
    const name = url.searchParams.get('name'), aircraft = url.searchParams.get('aircraft'), patch = url.searchParams.get('patch');
    const size = Number(request.headers.get('content-length')), digest = request.headers.get('x-scan-sha256');
    check(typeof name === 'string' && name.length >= 5 && name.length <= 200 && /\.pdf$/i.test(name) && !/[\\/:*?"<>|\x00-\x1f]/.test(name) &&
      /^[A-Z0-9-]{2,16}$/.test(aircraft || '') && ['true', 'false'].includes(patch), 'Invalid PDF destination.');
    check(request.headers.get('content-type') === 'application/pdf' && Number.isInteger(size) && size > 0 && size <= this.maxPdf() && /^[0-9a-f]{64}$/.test(digest || ''), 'Invalid PDF size or digest.');
    const bytes = await bounded(request, size);
    check(bytes.byteLength === size && dec.decode(bytes.slice(0, 5)) === '%PDF-' && await sha256(bytes) === digest, 'The received PDF does not match the saved scan.');
    const job = {id, account_id: verified.id, email: verified.email, name, aircraft, patch: patch === 'true', size, sha256: digest};
    const key = 'scan:' + verified.id + ':' + id;
    const nameKey = 'name:' + await sha256(enc.encode(JSON.stringify([aircraft, job.patch, name])));
    const nameClaim = await this.db.get(nameKey);
    check(!nameClaim || nameClaim === key, 'This filename already belongs to another scan. Use a different scan filename.', 409);
    if (!nameClaim) await this.db.put(nameKey, key);
    const prior = await this.db.get(key);
    if (prior) check(JSON.stringify(prior.job) === JSON.stringify(job), 'This scan identifier already belongs to different PDF bytes or a different destination.', 409);
    else await this.db.put(key, {job}); // Durable idempotency metadata before a remote write.
    if (prior?.receipt) return json(prior.receipt);
    const ownerToken = await this.ownerAccess();
    check(this.owner(await this.profile(ownerToken)), 'The owner authorization does not match this folder.', 403);
    await this.root(ownerToken);
    let parentId = await this.ensureFolder(this.env.FOLDER_ID, aircraft, ownerToken);
    if (job.patch) parentId = await this.ensureFolder(parentId, 'patches', ownerToken);
    if (!prior?.remote_checked) {
      let exists = false;
      try { await this.graph(this.path(parentId) + ':/' + encode(name), ownerToken); exists = true; }
      catch (error) { if (error.status !== 404) throw error; }
      check(!exists, 'A file already exists with this scan filename. It has not been overwritten.', 409);
      await this.db.put(key, {job, remote_checked: true});
    }
    const item = await this.graph(this.path(parentId) + ':/' + encode(name) + ':/content', ownerToken,
      {method: 'PUT', headers: {'Content-Type': 'application/pdf'}, body: bytes});
    this.requireItem(item, job, parentId);
    const observed = await this.graph(this.path(item.id) + '?$select=id,name,size,file,parentReference', ownerToken);
    this.requireItem(observed, job, parentId); check(observed.id === item.id, 'Microsoft returned a different uploaded PDF.', 503);
    check(await this.download(item.id, size) === digest, 'The PDF read back from Microsoft differs from the scan.', 503);
    // The approval cannot change mid-upload because all operations are serialized.
    const receipt = {...job, item_id: item.id, drive_id: this.env.DRIVE_ID, root_folder_id: this.env.FOLDER_ID,
      parent_id: parentId, verified_at: this.clock()};
    await this.commit([[key, {job, receipt, remote_checked: true}],
      ['receipt:' + String(receipt.verified_at).padStart(16, '0') + ':' + id, receipt]],
      'DELIVERY_VERIFIED', verified, receipt);
    return json(receipt);
  }
  async cleanup() {
    for (const prefix of ['challenge:', 'owner-challenge:', 'session:', 'rate:']) {
      const rows = await this.db.list({prefix, limit: 1000});
      for (const [key, value] of rows) {
        const oldRate = prefix === 'rate:' && Number(key.split(':')[2]) < Math.floor(this.clock() / 3600000) - 1;
        if (oldRate || value.expires_at <= this.clock()) await this.db.delete(key);
      }
    }
  }
}
