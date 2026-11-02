import test from 'node:test';
import assert from 'node:assert/strict';
import {sha256} from '../src/service.mjs';
import {fixture, PDF, env} from './fixtures.mjs';
const enc = new TextEncoder();
const staffProfile = {id:'synthetic-staff', mail:'staff@example.invalid', displayName:'Synthetic staff'};
test('owner sign-in accepts the current live Microsoft device address and legacy Microsoft addresses',async()=>{
  const f=await fixture();
  for (const uri of ['https://login.microsoft.com/device', 'https://microsoft.com/devicelogin',
    'https://www.microsoft.com/devicelogin', 'https://login.microsoftonline.com/common/oauth2/deviceauth']) {
    f.ms.verificationUri=uri;
    const result=await f.call('/api/owner/signin/start',{});
    assert.equal(result.status,200);assert.equal(result.value.verification_uri,uri);
    assert.equal(result.value.user_code,'TEST-CODE');assert.equal(result.value.device_code,undefined);
  }
});
test('owner sign-in rejects lookalike hosts, insecure addresses, URL credentials and unexpected ports',async()=>{
  const f=await fixture();
  for (const uri of ['http://login.microsoft.com/device', 'https://login.microsoft.com.evil.example.invalid/device',
    'https://evil.example.invalid@login.microsoft.com/device', 'https://login.microsoft.com:444/device',
    'https://evil.example.invalid/device', 'https://microsoft.com.evil.example.invalid/devicelogin',
    'https://login.microsoftonline.com.evil.example.invalid/device']) {
    f.ms.verificationUri=uri;
    const result=await f.call('/api/owner/signin/start',{});
    assert.equal(result.status,503);assert.equal(result.value.error,'Unexpected Microsoft sign-in page.');
    assert.equal(result.value.user_code,undefined);assert.equal(result.value.secret,undefined);
  }
});
test('approved Microsoft identity uploads with owner authorization, independent byte readback and persistent receipt',async()=>{
  const f=await fixture(),{signed}=await f.staff();assert.equal(signed.value.status,'APPROVED');
  const uploaded=await f.upload(signed.value.session_token);assert.equal(uploaded.status,200);
  assert.equal(uploaded.value.account_id,staffProfile.id);assert.equal(uploaded.value.sha256,await sha256(PDF));
  assert.equal(uploaded.value.root_folder_id,env.FOLDER_ID);assert.equal(f.ms.puts,1);
  const overview=await f.call('/api/owner/overview',undefined,f.owner);assert.equal(overview.value.receipts.length,1);
  assert.ok(!JSON.stringify(overview.value).includes('synthetic-owner-access'));
});
test('unapproved sign-in creates no pending request or approval and cannot upload',async()=>{
  const f=await fixture(),{signed}=await f.staff(false);assert.equal(signed.value.status,'DENIED');
  assert.equal((await f.upload(signed.value.session_token)).status,403);assert.equal(f.ms.puts,0);
  assert.equal((await f.call('/api/owner/overview',undefined,f.owner)).value.approved_emails.length,0);
});
test('removed approval immediately rejects subsequent uploads with an existing session',async()=>{
  const f=await fixture(),{signed}=await f.staff();await f.call('/api/owner/emails/remove',{email:staffProfile.mail},f.owner);
  assert.equal((await f.upload(signed.value.session_token)).status,403);assert.equal(f.ms.puts,0);
});
test('wrong owner cannot connect storage or receive an administrator session',async()=>{
  const f=await fixture();f.ms.profiles.set('synthetic-owner-access',staffProfile);
  const start=await f.call('/api/owner/signin/start',{});f.advance(6000);
  const result=await f.call('/api/owner/signin/poll',{id:start.value.id,secret:start.value.secret});
  assert.equal(result.status,403);assert.equal(result.value.session_token,undefined);
});
test('operator cannot list approved emails or invoke approval routes',async()=>{
  const f=await fixture(),{signed}=await f.staff(false);
  assert.equal((await f.call('/api/owner/emails',{email:staffProfile.mail},signed.value.session_token)).status,403);
  assert.equal((await f.call('/api/owner/overview',undefined,signed.value.session_token)).status,403);
});
test('sign-in URL requests only identity, PKCE S256, common authority and fixed Android redirect',async()=>{
  const f=await fixture(),start=await f.call('/api/auth/start',{}),url=new URL(start.value.authorization_url);
  assert.equal(url.pathname,'/common/oauth2/v2.0/authorize');assert.equal(url.searchParams.get('scope'),'User.Read offline_access');
  assert.equal(url.searchParams.get('code_challenge_method'),'S256');assert.equal(url.searchParams.get('redirect_uri'),'techlogscan://auth');
  assert.notEqual(start.value.device_secret,start.value.state);assert.ok(!url.href.includes(start.value.device_secret));
});
test('wrong device secret cannot redeem a code, and a completed request cannot replay',async()=>{
  const f=await fixture(),start=await f.call('/api/auth/start',{});
  const wrong=await f.call('/api/auth/finish',{state:start.value.state,device_secret:'wrong',code:'synthetic-code'});assert.equal(wrong.status,401);
  assert.equal(f.ms.calls.filter(c=>c.path==='/common/oauth2/v2.0/token').length,0);
  const body={state:start.value.state,device_secret:start.value.device_secret,code:'synthetic-code'};
  assert.equal((await f.call('/api/auth/finish',body)).status,200);assert.equal((await f.call('/api/auth/finish',body)).status,401);
});
test('actual consent error yields no session and preserves organization diagnostic code',async()=>{
  const f=await fixture();f.ms.consentError=true;const {signed}=await f.staff(false);
  assert.equal(signed.status,401);assert.match(signed.value.error,/AADSTS90094/);assert.equal(signed.value.session_token,undefined);
});
test('corrupt Microsoft readback never issues a receipt; retry after service restart uses the same filename',async()=>{
  const f=await fixture(),{signed}=await f.staff();f.ms.corrupt=true;
  assert.equal((await f.upload(signed.value.session_token)).status,503);
  assert.equal((await f.call('/api/owner/overview',undefined,f.owner)).value.receipts.length,0);
  f.ms.corrupt=false;f.restart();assert.equal((await f.upload(signed.value.session_token)).status,200);
  assert.equal(f.ms.files.size,1);assert.equal(f.ms.puts,2);
});
test('lost upload response recovers after restart, and a verified retry does not duplicate the file',async()=>{
  const f=await fixture(),{signed}=await f.staff();f.ms.loseResponse=true;
  assert.equal((await f.upload(signed.value.session_token)).status,503);f.restart();
  assert.equal((await f.upload(signed.value.session_token)).status,200);
  assert.equal((await f.upload(signed.value.session_token)).status,200);assert.equal(f.ms.puts,2);assert.equal(f.ms.files.size,1);
});
test('changing PDF bytes or aircraft for a previously admitted job is rejected',async()=>{
  const f=await fixture(),{signed}=await f.staff();assert.equal((await f.upload(signed.value.session_token)).status,200);
  assert.equal((await f.upload(signed.value.session_token,enc.encode('%PDF-1.4 other'))).status,409);
  assert.equal((await f.upload(signed.value.session_token,PDF,{aircraft:'ENP'})).status,409);assert.equal(f.ms.puts,1);
});
test('wrong drive metadata and traversal names cannot complete delivery',async()=>{
  const f=await fixture(),{signed}=await f.staff();f.ms.wrongDrive=true;
  assert.equal((await f.upload(signed.value.session_token)).status,503);assert.equal(f.ms.puts,0);
  assert.equal((await f.upload(signed.value.session_token,PDF,{name:'../bad.pdf'})).status,400);
});
test('sessions refresh Microsoft tokens without requesting more permissions',async()=>{
  const f=await fixture(),{signed}=await f.staff();f.advance(3700000);
  assert.equal((await f.upload(signed.value.session_token)).status,200);
  assert.ok(f.ms.calls.filter(c=>c.path.endsWith('/token')).length>=4);
});
test('tokens are encrypted with record-specific authentication and never returned by health',async()=>{
  const f=await fixture();const storage=JSON.stringify([...f.db.data]);assert.ok(!storage.includes('synthetic-owner-access'));
  const health=await f.call('/health');assert.ok(!JSON.stringify(health.value).includes('token'));
  assert.equal((await f.call('/api/owner/emails',{email:'malicious@example.invalid'},f.owner,{headers:{Origin:'https://evil.example.invalid'}})).status,403);
});
test('another Microsoft identity with the same email is rejected after the first signed-in identity is linked',async()=>{
  const f=await fixture(),{signed}=await f.staff();f.ms.profiles.set('synthetic-staff-access',{...staffProfile,id:'different-id'});
  const {signed:second}=await f.staff(false);assert.equal(second.value.status,'DENIED');
  assert.equal((await f.upload(second.value.session_token)).status,403);assert.equal(f.ms.puts,0);
});
test('a PDF already present outside the relay cannot be overwritten even on a later retry',async()=>{
  const f=await fixture(),{signed}=await f.staff();f.ms.existingFile=true;
  assert.equal((await f.upload(signed.value.session_token)).status,409);f.restart();
  assert.equal((await f.upload(signed.value.session_token)).status,409);assert.equal(f.ms.puts,0);
});
test('expired owner storage authorization does not send staff through a misleading sign-in loop',async()=>{
  const f=await fixture(),{signed}=await f.staff();f.advance(3700000);f.ms.ownerRefreshDenied=true;
  const result=await f.upload(signed.value.session_token);assert.equal(result.status,503);assert.match(result.value.error,/owner must reconnect/i);
  assert.equal((await f.call('/health')).value.storage_connected,false);
  assert.equal((await f.call('/api/auth/status',undefined,signed.value.session_token)).value.status,'NOT_CONFIGURED');
});
test('audit records human email decisions, account binding and verified bytes once; retries are idempotent',async()=>{
  const f=await fixture(),{signed}=await f.staff();
  await f.call('/api/owner/emails',{email:staffProfile.mail},f.owner); // Repeated click produces no second decision.
  await f.upload(signed.value.session_token);await f.upload(signed.value.session_token);
  await f.call('/api/owner/emails/remove',{email:staffProfile.mail},f.owner);
  const events=[...(await f.db.list({prefix:'audit:'})).values()];
  assert.deepEqual(events.map(x=>x.action),['OWNER_CONNECTED','EMAIL_APPROVED','ACCOUNT_LINKED','DELIVERY_VERIFIED','EMAIL_REMOVED']);
  let previous='';
  for (const event of events) {
    assert.equal(event.previous_hash,previous);const {hash,...record}=event;
    assert.equal(hash,await sha256(enc.encode(JSON.stringify(record))));previous=hash;
  }
  assert.equal(events[3].subject.sha256,await sha256(PDF));
  assert.ok(!JSON.stringify(events).includes('synthetic-owner-access'));
  assert.equal((await f.call('/api/owner/overview',undefined,signed.value.session_token)).status,403);
});
test('failed audit commit rolls back approval and delivery receipt so a saved scan can retry',async()=>{
  const f=await fixture(),realPut=f.db.put.bind(f.db);let fail=false;
  f.db.put=async(key,value)=>{if(fail&&key.startsWith('audit:'))throw Error('synthetic storage failure');return realPut(key,value);};
  fail=true;
  assert.equal((await f.call('/api/owner/emails',{email:staffProfile.mail},f.owner)).status,503);
  assert.equal(await f.db.get('approved:'+staffProfile.mail),undefined);
  fail=false;const {signed}=await f.staff();fail=true;
  assert.equal((await f.upload(signed.value.session_token)).status,503);
  assert.equal((await f.call('/api/owner/overview',undefined,f.owner)).value.receipts.length,0);
  fail=false;f.restart();assert.equal((await f.upload(signed.value.session_token)).status,200);
  assert.equal((await f.call('/api/owner/overview',undefined,f.owner)).value.receipts.length,1);
});
test('Firebase Hosting owner cookie works and logout removes it without disconnecting storage',async()=>{
  const f=await fixture();
  const cookie='__session='+f.owner;
  assert.equal((await f.call('/api/owner/overview',undefined,undefined,{headers:{Cookie:cookie}})).status,200);
  const logout=await f.call('/api/auth/logout',{},undefined,{headers:{Cookie:cookie}});
  assert.match(logout.headers.get('set-cookie'),/__session=;.*HttpOnly.*Secure/);
  assert.equal((await f.call('/api/owner/overview',undefined,f.owner)).status,401);
  assert.equal((await f.call('/health')).value.storage_connected,true);
});
