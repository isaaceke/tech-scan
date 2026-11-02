import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import {Firestore} from '@google-cloud/firestore';
import {randomUUID} from 'node:crypto';
import {FirestoreStore} from '../firestore-store.mjs';

// Explicit emulator check prevents accidental tests against a real project.
if (!/^127\.0\.0\.1:\d+$/.test(process.env.FIRESTORE_EMULATOR_HOST || '')) throw Error('A local Firestore emulator is required.');
const firestore=new Firestore({projectId:'demo-enugu-scanner'});
after(()=>firestore.terminate());
const store=(options={})=>new FirestoreStore(firestore,{namespace:'test_'+randomUUID().replaceAll('-',''),...options});

test('Firestore preserves records between service instances and commits transaction changes together',async()=>{
  const a=store(),b=new FirestoreStore(firestore,{namespace:a.rows.id});
  await a.withLease(async db=>{
    await db.transaction(async tx=>{await tx.put('approved:fixture@example.invalid',{email:'fixture@example.invalid'});await tx.put('audit:0001',{action:'EMAIL_APPROVED'});});
    await assert.rejects(db.transaction(async tx=>{await tx.put('bad',true);throw Error('rollback');}),/rollback/);
    assert.equal(await db.get('bad'),undefined);
  });
  await b.withLease(async db=>{
    assert.equal((await db.get('approved:fixture@example.invalid')).email,'fixture@example.invalid');
    assert.equal((await db.list({prefix:'audit:'})).size,1);
    await assert.rejects(db.put('audit:0001',{action:'changed'}),/cannot be changed/);
    await assert.rejects(db.delete('audit:0001'),/cannot be changed/);
  });
});
test('lease excludes another Cloud Run revision and releases after a failed operation',async()=>{
  const a=store(),b=new FirestoreStore(firestore,{namespace:a.rows.id});
  await assert.rejects(a.withLease(async()=>{await assert.rejects(b.withLease(()=>{}),/busy/);throw Error('worker failed');}),/worker failed/);
  await b.withLease(db=>db.put('recovered',true));
});
test('expired process cannot write or release the new process lease',async()=>{
  let now=100000;const a=store({clock:()=>now}),b=new FirestoreStore(firestore,{namespace:a.rows.id,clock:()=>now});
  let staleScope,newScope,releaseNew;
  const newWait=new Promise(resolve=>{releaseNew=resolve;});
  let ready;const newReady=new Promise(resolve=>{ready=resolve;});
  let newWork;
  await a.withLease(async db=>{
    staleScope=db;await db.put('initial',true);now+=120001;
    newWork=b.withLease(async scope=>{newScope=scope;await scope.put('new',true);ready();await newWait;});
    await newReady;
    await assert.rejects(staleScope.put('stale-write',true),/lost its storage lease/);
  });
  await newScope.put('after-stale-release',true);
  releaseNew();await newWork;
  await b.withLease(async db=>{assert.equal(await db.get('stale-write'),undefined);assert.equal(await db.get('after-stale-release'),true);});
});
test('prefix queries keep receipt ordering and never leak token records',async()=>{
  await store().withLease(async db=>{
    await db.put('receipt:002',{id:2});await db.put('receipt:001',{id:1});await db.put('owner-token',{ciphertext:'synthetic'});
    assert.deepEqual([...await db.list({prefix:'receipt:',limit:1,reverse:true})],[['receipt:002',{id:2}]]);
  });
});
test('Firestore security rules reject direct unauthenticated client reads',async()=>{
  const a=store();await a.withLease(db=>db.put('private-record',{ciphertext:'synthetic'}));
  const response=await fetch(`http://${process.env.FIRESTORE_EMULATOR_HOST}/v1/projects/demo-enugu-scanner/databases/(default)/documents/${a.rows.id}`);
  assert.equal(response.status,403);await response.body.cancel();
});
test('lease renews during a slow operation and expired request cannot commit',async()=>{
  const a=store({leaseMs:10000,renewMs:2000,deadlineMs:30000});
  await a.withLease(async db=>{await new Promise(resolve=>setTimeout(resolve,11000));await db.put('still-active',true);});
  const b=store({deadlineMs:30});
  await b.withLease(async db=>{await new Promise(resolve=>setTimeout(resolve,70));await assert.rejects(db.put('late',true),/expired/);});
});
