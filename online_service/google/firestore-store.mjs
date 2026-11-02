import {createHash, randomUUID} from 'node:crypto';
import {Failure} from '../src/service.mjs';

const id = key => createHash('sha256').update(key).digest('hex');
const decode = row => row.exists ? JSON.parse(row.get('json')) : undefined;

// A fenced lease serializes operations across Cloud Run instances and revisions.
// Only small JSON records enter Firestore; PDFs continue to live on the phone.
export class FirestoreStore {
  constructor(firestore, {namespace = 'scanner_state_v1', clock = Date.now, leaseMs = 120000,
    renewMs = 20000, deadlineMs = 540000} = {}) {
    if (!/^[a-z][a-z0-9_]{0,60}$/.test(namespace)) throw Error('Invalid scanner namespace.');
    this.firestore = firestore; this.rows = firestore.collection(namespace);
    this.lock = firestore.doc('scanner_locks/' + namespace);
    this.clock = clock; this.leaseMs = leaseMs; this.renewMs = renewMs; this.deadlineMs = deadlineMs;
  }
  async withLease(work) {
    const holder = randomUUID(), controller = new AbortController();
    const acquired = await this.firestore.runTransaction(async tx => {
      const row = await tx.get(this.lock), old = row.exists ? row.data() : {};
      if (old.holder && old.expires_at > this.clock()) return false;
      tx.set(this.lock, {holder, expires_at: this.clock() + this.leaseMs}); return true;
    });
    if (!acquired) throw new Failure(503, 'The scanner service is busy. The phone retains its PDF for retry.');
    const scope = new LeasedStore(this, holder, controller.signal);
    let renewal = Promise.resolve();
    const timer = setInterval(() => {
      renewal = renewal.then(async () => {
        if (controller.signal.aborted) return;
        await this.firestore.runTransaction(async tx => {
          await scope.check(tx); tx.update(this.lock, {expires_at: this.clock() + this.leaseMs});
        });
      }).catch(() => controller.abort());
    }, this.renewMs);
    const deadline = setTimeout(() => controller.abort(), this.deadlineMs);
    try { return await work(scope, controller.signal); }
    finally {
      clearInterval(timer); clearTimeout(deadline); controller.abort(); await renewal;
      // Never clear a lease acquired by a newer process after ours expired.
      await this.firestore.runTransaction(async tx => {
        const row = await tx.get(this.lock);
        if (row.exists && row.get('holder') === holder) tx.set(this.lock, {holder: '', expires_at: 0});
      }).catch(() => {});
    }
  }
}

class LeasedStore {
  constructor(store, holder, signal) { this.store = store; this.holder = holder; this.signal = signal; }
  async check(tx) {
    if (this.signal.aborted) throw new Failure(503, 'The scanner operation expired. The phone retains its PDF.');
    const row = await tx.get(this.store.lock);
    if (!row.exists || row.get('holder') !== this.holder || row.get('expires_at') <= this.store.clock())
      throw new Failure(503, 'The scanner operation lost its storage lease. Retry the saved PDF.');
  }
  ref(key) { return this.store.rows.doc(id(key)); }
  async get(key) { return this.transaction(tx => tx.get(key)); }
  async put(key, value) { return this.transaction(tx => tx.put(key, value)); }
  async delete(key) { return this.transaction(tx => tx.delete(key)); }
  async list({prefix = '', limit = 1000, reverse = false} = {}) {
    return this.store.firestore.runTransaction(async tx => {
      await this.check(tx);
      const query = this.store.rows.where('key', '>=', prefix).where('key', '<', prefix + '\uffff')
        .orderBy('key', reverse ? 'desc' : 'asc').limit(limit);
      const result = await tx.get(query);
      return new Map(result.docs.map(row => [row.get('key'), decode(row)]));
    });
  }
  async transaction(work) {
    return this.store.firestore.runTransaction(async tx => {
      await this.check(tx);
      const changes = new Map();
      const facade = {
        get: async key => changes.has(key) ? structuredClone(changes.get(key)) : decode(await tx.get(this.ref(key))),
        put: async (key, value) => { changes.set(key, structuredClone(value)); },
        delete: async key => { changes.set(key, undefined); }
      };
      const result = await work(facade);
      // Read before any write, as required by Firestore transactions. Application
      // audit rows are append-only; database administrators remain privileged.
      for (const [key, value] of changes) if (key.startsWith('audit:')) {
        if (value === undefined || (await tx.get(this.ref(key))).exists) throw Error('Audit events cannot be changed.');
      }
      for (const [key, value] of changes) {
        if (value === undefined) tx.delete(this.ref(key));
        else tx.set(this.ref(key), {key, json: JSON.stringify(value)});
      }
      return result;
    });
  }
}
