import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import {Firestore} from '@google-cloud/firestore';
import {readFileSync} from 'node:fs';
import {createHash,randomUUID} from 'node:crypto';
import {request as httpRequest} from 'node:http';
import {FirestoreStore} from '../firestore-store.mjs';
import {createScannerServer,GOOGLE_MAX_PDF,validateEnv} from '../http-server.mjs';
import {env,MicrosoftFixture} from '../../test/fixtures.mjs';
if (!/^127\.0\.0\.1:\d+$/.test(process.env.FIRESTORE_EMULATOR_HOST || '')) throw Error('A local Firestore emulator is required.');
const firestore=new Firestore({projectId:'demo-enugu-scanner'});
after(()=>firestore.terminate());

test('real HTTP Google service and Firestore recover delivery after restart, verify camera PDF and reject revoked identity',async()=>{
  const store=new FirestoreStore(firestore,{namespace:'test_'+randomUUID().replaceAll('-','')});
  const ms=new MicrosoftFixture();let now=Date.now(),server,address;
  const configuration={...env,PUBLIC_ORIGIN:'https://run.example.invalid',ALLOWED_ORIGINS:'https://run.example.invalid,https://panel.example.invalid'};
  async function start() {
    server=createScannerServer({store,env:configuration,fetcher:ms.fetch,clock:()=>now});
    await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));address='http://127.0.0.1:'+server.address().port;
  }
  async function stop(){server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
  async function call(path,body,token,options={}) {
    const response=await fetch(address+path,{method:body===undefined?'GET':'POST',body:body===undefined?undefined:JSON.stringify(body),...options,
      headers:{...(body===undefined?{}:{'Content-Type':'application/json'}),...(token?{Authorization:'Bearer '+token}:{}),...options.headers}});
    return {status:response.status,value:await response.json(),headers:response.headers};
  }
  await start();
  try {
    const panel=await fetch(address);assert.equal(panel.status,200);assert.match(await panel.text(),/Activity history/);
    assert.match(panel.headers.get('Content-Security-Policy'),/frame-ancestors 'none'/);
    const health=await call('/health');assert.equal(health.value.hosting,'firebase-google-cloud');assert.equal(health.value.max_pdf_bytes,GOOGLE_MAX_PDF);
    const begin=await call('/api/owner/signin/start',{});now+=6000;
    const connected=await call('/api/owner/signin/poll',{id:begin.value.id,secret:begin.value.secret});assert.equal(connected.status,200,JSON.stringify(connected.value));
    assert.match(connected.headers.get('set-cookie'),/__session=.*HttpOnly; Secure/);const owner=connected.value.session_token;
    const cookie=connected.headers.get('set-cookie').split(';')[0];
    // Exact Firebase Hosting panel origin is accepted; a third-party origin is rejected.
    assert.equal((await call('/api/owner/overview',undefined,undefined,{headers:{Cookie:cookie}})).status,200);
    assert.equal((await call('/api/owner/emails',{email:'staff@example.invalid'},owner,{headers:{Origin:'https://panel.example.invalid'}})).status,200);
    assert.equal((await call('/api/owner/emails',{email:'evil@example.invalid'},owner,{headers:{Origin:'https://evil.example.invalid'}})).status,403);
    const auth=await call('/api/auth/start',{});
    const signed=await call('/api/auth/finish',{state:auth.value.state,device_secret:auth.value.device_secret,code:'synthetic-code'});assert.equal(signed.value.status,'APPROVED');
    const token=signed.value.session_token;
    const bytes=readFileSync(new URL('../../../.build/native-camera-scan.pdf',import.meta.url));
    const digest=createHash('sha256').update(bytes).digest('hex'),id='12121212-3434-4567-8899-aabbccddeeff';
    const upload=()=>call(`/api/scans/${id}?name=GOOGLE_PROOF__121212123434.pdf&aircraft=ENO&patch=false`,undefined,token,
      {method:'PUT',body:bytes,headers:{'Content-Type':'application/pdf','Content-Length':String(bytes.length),'X-Scan-SHA256':digest}});
    ms.loseResponse=true;assert.equal((await upload()).status,503);
    await stop();await start();
    const uploaded=await upload();assert.equal(uploaded.status,200,JSON.stringify(uploaded.value));assert.equal(uploaded.value.sha256,digest);
    assert.equal(uploaded.value.root_folder_id,env.FOLDER_ID);assert.equal(ms.files.size,1);
    const writes=ms.puts;assert.equal((await upload()).status,200);assert.equal(ms.puts,writes);
    const overview=await call('/api/owner/overview',undefined,owner);assert.equal(overview.value.receipts.length,1);
    assert.equal(overview.value.audit.filter(x=>x.action==='DELIVERY_VERIFIED').length,1);
    await call('/api/owner/emails/remove',{email:'staff@example.invalid'},owner);
    await stop();await start();
    assert.equal((await upload()).status,403);assert.equal(ms.puts,writes);
    assert.equal((await call('/api/owner/overview',undefined,token)).status,403);
    assert.ok(!JSON.stringify(overview.value).includes('synthetic-owner-access'));
  } finally {await stop();}
});
test('production configuration rejects missing secrets and malformed origins',()=>{
  assert.throws(()=>validateEnv({...env,PUBLIC_ORIGIN:'http://localhost'}),/HTTPS/);
  assert.throws(()=>validateEnv({...env,PUBLIC_ORIGIN:'https://run.example.invalid',TOKEN_ENCRYPTION_KEY:''}),/secret/);
  assert.throws(()=>validateEnv({...env,PUBLIC_ORIGIN:'https://run.example.invalid',ALLOWED_ORIGINS:'https://evil.example.invalid/path'}),/origin/);
});
test('oversized declared upload is rejected before reading body or opening storage',async()=>{
  let storageCalls=0;
  const server=createScannerServer({store:{withLease:()=>{storageCalls++;throw Error('must not enter storage');}},
    env:{...env,PUBLIC_ORIGIN:'https://run.example.invalid'}});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try {
    const result=await new Promise((resolve,reject)=>{
      const request=httpRequest({hostname:'127.0.0.1',port:server.address().port,path:'/api/scans/fixture',method:'PUT',
        headers:{'Content-Type':'application/pdf','Content-Length':GOOGLE_MAX_PDF+1}},response=>{
          let body='';response.on('data',chunk=>body+=chunk);response.on('end',()=>resolve({status:response.statusCode,body}));
        });
      request.on('error',reject);request.end();
    });
    assert.equal(result.status,413);assert.match(result.body,/30 MB/);assert.equal(storageCalls,0);
  } finally {server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
});
