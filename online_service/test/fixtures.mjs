import assert from 'node:assert/strict';
import {ScannerService, sha256, MAX_PDF} from '../src/service.mjs';
const enc = new TextEncoder();
export const PDF = enc.encode('%PDF-1.4\nsynthetic offline test document\n%%EOF');
export const jobId = '11111111-2222-4333-8444-555555555555';
const ownerProfile = {id:'synthetic-owner', mail:'owner@example.invalid', displayName:'Synthetic owner'};
const staffProfile = {id:'synthetic-staff', mail:'staff@example.invalid', displayName:'Synthetic staff'};
export const env = {CLIENT_ID:'synthetic-client', OWNER_TENANT:'synthetic-tenant', OWNER_ID:ownerProfile.id,
  OWNER_EMAIL:ownerProfile.mail, DRIVE_ID:'synthetic-drive', FOLDER_ID:'synthetic-root',
  FOLDER_URL:'https://example.invalid/folder', TOKEN_ENCRYPTION_KEY:'a1'.repeat(32)};
const reply = (value, status=200, headers={}) => new Response(JSON.stringify(value), {status, headers:{'Content-Type':'application/json',...headers}});
export class MemoryStorage {
  data = new Map();
  async get(key) { return structuredClone(this.data.get(key)); }
  async put(key,value) { this.data.set(key,structuredClone(value)); }
  async delete(key) { return this.data.delete(key); }
  async transaction(work) {
    const before = structuredClone(this.data);
    try { return await work(this); }
    catch (error) { this.data = before; throw error; }
  }
  async list({prefix='',limit=1000,reverse=false}={}) {
    const keys=[...this.data.keys()].filter(k=>k.startsWith(prefix)).sort(); if(reverse) keys.reverse();
    return new Map(keys.slice(0,limit).map(k=>[k,structuredClone(this.data.get(k))]));
  }
}
export class MicrosoftFixture {
  profiles = new Map([['synthetic-owner-access', ownerProfile],['synthetic-staff-access',staffProfile]]);
  folders = new Map(); files = new Map(); calls=[]; puts=0; corrupt=false; wrongDrive=false; loseResponse=false; consentError=false;
  ownerRefreshDenied=false; existingFile=false; verificationUri='https://login.microsoft.com/device';
  ownerResult() { return {access_token:'synthetic-owner-access',refresh_token:'synthetic-owner-refresh',expires_in:3600,token_type:'Bearer',scope:'User.Read Files.ReadWrite offline_access'}; }
  staffResult() { return {access_token:'synthetic-staff-access',refresh_token:'synthetic-staff-refresh',expires_in:3600,token_type:'Bearer',scope:'User.Read offline_access'}; }
  item(id,name,parent,folder=false) { return {id,name,[folder?'folder':'file']:{},parentReference:{driveId:this.wrongDrive?'wrong-drive':env.DRIVE_ID,id:parent}}; }
  fetch = async (address, options={}) => {
    const url = new URL(address); const path=decodeURIComponent(url.pathname); const method=options.method||'GET';
    const token=new Headers(options.headers).get('Authorization')?.replace('Bearer ','');
    this.calls.push({path,method,token,host:url.hostname});
    if(url.hostname==='download.example.invalid') {
      assert.equal(token,undefined, 'No Graph bearer may reach signed download URL');
      const bytes=this.files.values().next().value.bytes.slice(); if(this.corrupt) bytes[0]=0;
      return new Response(bytes);
    }
    if(url.hostname==='login.microsoftonline.com') {
      const fields=new URLSearchParams(options.body);
      if(path.endsWith('/devicecode')) return reply({device_code:'synthetic-device-code',user_code:'TEST-CODE',verification_uri:this.verificationUri,expires_in:900,interval:5});
      if(this.consentError && fields.get('grant_type')==='authorization_code') return reply({error:'access_denied',error_description:'AADSTS90094 synthetic organization denial'},400);
      if(fields.get('grant_type')==='refresh_token') {
        if(this.ownerRefreshDenied && fields.get('refresh_token')==='synthetic-owner-refresh') return reply({error:'invalid_grant'},400);
        assert.equal(fields.has('scope'),false); return reply(fields.get('refresh_token')==='synthetic-owner-refresh'?this.ownerResult():this.staffResult());
      }
      if(fields.get('grant_type')==='authorization_code') {
        assert.ok(fields.get('code_verifier')); assert.equal(fields.get('redirect_uri'),'techlogscan://auth');
        assert.equal(path,'/common/oauth2/v2.0/token'); return reply(this.staffResult());
      }
      return reply(this.ownerResult());
    }
    if(url.hostname==='oauth2.googleapis.com') {
      const payload=btoa(JSON.stringify({sub:'google-sub-123',email:'googlestaff@example.invalid',email_verified:true,name:'Google Staff'})).replaceAll('=','');
      return reply({access_token:'synthetic-google-access',refresh_token:'synthetic-google-refresh',expires_in:3600,token_type:'Bearer',id_token:'header.'+payload+'.signature'});
    }
    if(url.hostname==='openidconnect.googleapis.com') {
      return reply({sub:'google-sub-123',email:'googlestaff@example.invalid',email_verified:true,name:'Google Staff'});
    }
    assert.equal(url.hostname,'graph.microsoft.com');
    if(path==='/v1.0/me') return this.profiles.has(token)?reply(this.profiles.get(token)):reply({error:'expired'},401);
    assert.equal(token,'synthetic-owner-access','Corporate drive calls require only the owner token');
    const prefix='/v1.0/drives/'+env.DRIVE_ID+'/items/';
    assert.ok(path.startsWith(prefix)); const rel=path.slice(prefix.length);
    if(rel===env.FOLDER_ID) return reply(this.item(env.FOLDER_ID,'scanner','drive-root',true));
    if(method==='POST'&&rel.endsWith('/children')) {
      const parent=rel.slice(0,-'/children'.length), name=JSON.parse(options.body).name;
      const folder=this.item('folder-'+this.folders.size,name,parent,true);this.folders.set(`${parent}:/${name}`,folder); return reply(folder,201);
    }
    if(method==='PUT') {
      this.puts++; const relative=rel.replace(/:\/content$/,''); const [parent,name]=relative.split(':/');
      const id=this.files.get(relative)?.item.id||'pdf-'+this.files.size;
      const bytes=new Uint8Array(options.body);const item={...this.item(id,name,parent),size:bytes.length};
      this.files.set(relative,{item,bytes});
      if(this.loseResponse) { this.loseResponse=false;throw Error('Synthetic connection lost after Microsoft accepted the bytes'); }
      return reply(item,201);
    }
    if(this.folders.has(rel)) return reply(this.folders.get(rel));
    if(this.existingFile && rel.includes(':/') && /\.pdf$/i.test(rel)) return reply(this.item('external-file',rel.split(':/')[1],rel.split(':/')[0]));
    const file=[...this.files.values()].find(f=>f.item.id===rel.replace(/\/content$/,''));
    if(file) return rel.endsWith('/content')?new Response(null,{status:302,headers:{location:'https://download.example.invalid/signed.pdf'}}):reply(file.item);
    return reply({error:'synthetic missing'},404);
  }
}
export async function fixture() {
  let now=Date.now(); const db=new MemoryStorage(), ms=new MicrosoftFixture();
  let service=new ScannerService(db,env,ms.fetch,()=>now);
  async function call(path,body,token,options={}) {
    const headers={...(body===undefined?{}:{'Content-Type':'application/json'}),...(token?{Authorization:'Bearer '+token}:{}),...options.headers};
    const response=await service.fetch(new Request('https://scanner.example.invalid'+path,{method:body===undefined?'GET':'POST',
      body:body===undefined?undefined:JSON.stringify(body),...options,headers}));
    return {status:response.status,value:await response.json(),headers:response.headers};
  }
  const begin=await call('/api/owner/signin/start',{}); now+=6000;
  const connected=await call('/api/owner/signin/poll',{id:begin.value.id,secret:begin.value.secret});
  assert.equal(connected.status,200);const owner=connected.value.session_token;
  async function staff(approve=true) {
    if(approve) assert.equal((await call('/api/owner/emails',{email:staffProfile.mail},owner)).status,200);
    const start=await call('/api/auth/start',{});
    const signed=await call('/api/auth/finish',{state:start.value.state,device_secret:start.value.device_secret,code:'synthetic-code'});
    return {signed,start};
  }
  async function upload(token,bytes=PDF,changes={}) {
    const query=new URLSearchParams({name:'LOG__111111112222.pdf',aircraft:'ENO',patch:'false',...changes});
    return call('/api/scans/'+jobId+'?'+query,undefined,token,{method:'PUT',body:bytes,headers:{'Content-Type':'application/pdf',
      'Content-Length':String(bytes.length),'X-Scan-SHA256':await sha256(bytes)}});
  }
  return {db,ms,call,staff,upload,owner,get service(){return service;},advance:ms=>{now+=ms;},restart:()=>{service=new ScannerService(db,env,ms.fetch,()=>now);}};
}
