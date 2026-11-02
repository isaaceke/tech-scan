import test from 'node:test';
import assert from 'node:assert/strict';
import {Miniflare, Response as MFResponse} from 'miniflare';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';

test('packaged Worker runs its SQLite Durable Object, owner sign-in, email panel API and full PDF delivery in workerd', async()=>{
  const env={...JSON.parse(readFileSync('wrangler.jsonc')).vars,CLIENT_ID:'runtime-client',OWNER_ID:'runtime-owner',
    OWNER_EMAIL:'owner@example.invalid',DRIVE_ID:'runtime-drive',FOLDER_ID:'runtime-root',TOKEN_ENCRYPTION_KEY:'bc'.repeat(32)};
  let file, metadata, ownerTokenCalls=0, signedDownloadCalls=0;
  const folders=new Map();
  const mf=new Miniflare({modules:true,modulesRoot:resolve('../.build/worker-bundle'),scriptPath:resolve('../.build/worker-bundle/worker.js'),compatibilityDate:'2026-08-01',
    compatibilityFlags:['nodejs_compat'],modulesRules:[{type:'Text',include:['**/*.txt','**/*.html']}],
    durableObjects:{SCANNER:{className:'ScannerState',useSQLite:true}},bindings:env,
    outboundService:async request=>{
      const url=new URL(request.url),path=decodeURIComponent(url.pathname),method=request.method;
      const token=request.headers.get('Authorization');
      const reply=(value,status=200)=>new MFResponse(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
      if(url.hostname==='login.microsoftonline.com') {
        const fields=new URLSearchParams(await request.text());
        if(path.endsWith('/devicecode')) return reply({device_code:'runtime-device',user_code:'TEST-ONLY',verification_uri:'https://microsoft.com/devicelogin',expires_in:900,interval:5});
        const owner=fields.get('grant_type')!=='authorization_code';if(owner)ownerTokenCalls++;
        return reply({access_token:owner?'runtime-owner-access':'runtime-staff-access',refresh_token:'runtime-refresh',expires_in:3600,scope:owner?'User.Read Files.ReadWrite offline_access':'User.Read offline_access'});
      }
      if(url.hostname==='download.example.invalid') {
        assert.equal(token,null);signedDownloadCalls++;return new MFResponse(file);
      }
      assert.equal(url.hostname,'graph.microsoft.com');
      if(path==='/v1.0/me')return reply(token==='Bearer runtime-owner-access'?{id:'runtime-owner',mail:env.OWNER_EMAIL}:{id:'runtime-staff',mail:'staff@example.invalid'});
      assert.equal(token,'Bearer runtime-owner-access');
      const prefix='/v1.0/drives/runtime-drive/items/',rel=path.slice(prefix.length);
      const item=(id,name,parent,isFolder)=>({id,name,[isFolder?'folder':'file']:{},parentReference:{driveId:env.DRIVE_ID,id:parent}});
      if(rel===env.FOLDER_ID)return reply(item(env.FOLDER_ID,'scanner','drive-root',true));
      if(method==='POST'&&rel.endsWith('/children')) {
        const parent=rel.replace(/\/children$/,''),body=await request.json(),folder=item('aircraft-folder',body.name,parent,true);
        folders.set(`${parent}:/${body.name}`,folder);return reply(folder,201);
      }
      if(method==='PUT') {
        file=new Uint8Array(await request.arrayBuffer());const [parent,name]=rel.replace(/:\/content$/,'').split(':/');
        metadata={...item('verified-pdf',name,parent,false),size:file.length};return reply(metadata,201);
      }
      if(rel==='verified-pdf/content')return new MFResponse(null,{status:302,headers:{Location:'https://download.example.invalid/verified.pdf'}});
      if(rel==='verified-pdf')return reply(metadata);
      if(folders.has(rel))return reply(folders.get(rel));return reply({error:'missing'},404);
    }});
  try {
    const call=async(path,body,bearer,options={})=>{
      const response=await mf.dispatchFetch('https://scanner.example.invalid'+path,{method:body===undefined?'GET':'POST',body:body===undefined?undefined:JSON.stringify(body),
        ...options,headers:{...(body===undefined?{}:{'Content-Type':'application/json'}),...(bearer?{Authorization:'Bearer '+bearer}:{}),...options.headers}});
      try { return {response,result:await response.json()}; }
      catch (error) { throw new Error('Runtime response failed at ' + path, {cause:error}); }
    };
    const health=await call('/health');assert.equal(health.result.storage_connected,false);
    const panel=await mf.dispatchFetch('https://scanner.example.invalid/');assert.match(await panel.text(),/APPROVE EMAIL/);
    assert.match(panel.headers.get('Content-Security-Policy'),/frame-ancestors 'none'/);
    const start=await call('/api/owner/signin/start',{});assert.equal(start.response.status,200,JSON.stringify(start.result));
    await new Promise(resolve=>setTimeout(resolve,5100));
    const connected=await call('/api/owner/signin/poll',{id:start.result.id,secret:start.result.secret});assert.equal(connected.response.status,200,JSON.stringify(connected.result));
    const owner=connected.result.session_token;assert.equal(ownerTokenCalls,1);
    assert.equal((await call('/api/owner/emails',{email:'staff@example.invalid'},owner)).response.status,200);
    const auth=await call('/api/auth/start',{});
    const signed=await call('/api/auth/finish',{state:auth.result.state,device_secret:auth.result.device_secret,code:'runtime-code'});
    assert.equal(signed.result.status,'APPROVED');
    // Use the real two-page camera PDF saved by the Android app; authentication
    // and Microsoft endpoints are synthetic in this isolated runtime test.
    const bytes=readFileSync('../.build/native-camera-scan.pdf'),digest=createHash('sha256').update(bytes).digest('hex');
    const id='12121212-3434-4567-8899-aabbccddeeff';
    const uploaded=await call(`/api/scans/${id}?name=RUNTIME_PROOF__121212123434.pdf&aircraft=ENO&patch=false`,undefined,signed.result.session_token,
      {method:'PUT',body:bytes,headers:{'Content-Type':'application/pdf','Content-Length':String(bytes.length),'X-Scan-SHA256':digest}});
    assert.equal(uploaded.response.status,200,JSON.stringify(uploaded.result));assert.equal(uploaded.result.sha256,digest);
    assert.equal(uploaded.result.account_id,'runtime-staff');assert.equal(signedDownloadCalls,1);
    const overview=await call('/api/owner/overview',undefined,owner);assert.equal(overview.result.receipts.length,1);
    assert.equal((await call('/api/owner/emails/remove',{email:'staff@example.invalid'},owner)).response.status,200);
    assert.equal((await call('/api/auth/status',undefined,signed.result.session_token)).result.status,'DENIED');
  } finally {await mf.dispose();}
});
