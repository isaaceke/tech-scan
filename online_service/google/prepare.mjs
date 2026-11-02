import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

// Generates reviewable deployment files only; never contacts Google or enables billing.
export function prepare({project,region='us-central1',output,folder}) {
  if (!/^[a-z][a-z0-9-]{4,28}[a-z0-9]$/.test(project || '')) throw Error('A valid Firebase project ID is required.');
  if (!/^[a-z]+-[a-z]+\d$/.test(region)) throw Error('Invalid Google Cloud region.');
  for (const key of ['owner_id','owner_email','drive_id','folder_id','folder_url']) if (!folder[key]) throw Error('Missing folder configuration: '+key);
  const env={PUBLIC_ORIGIN:`https://${project}.web.app`,ALLOWED_ORIGINS:`https://${project}.web.app,https://${project}.firebaseapp.com`,
    CLIENT_ID:'dc7101d3-3bb7-462f-92e8-374958f4ddb5',OWNER_TENANT:'38de9dec-d800-439b-a669-60f628a90e72',
    OWNER_ID:folder.owner_id,OWNER_EMAIL:folder.owner_email,DRIVE_ID:folder.drive_id,FOLDER_ID:folder.folder_id,FOLDER_URL:folder.folder_url};
  const service='enugu-techlog-scanner',identity=`scanner-relay@${project}.iam.gserviceaccount.com`;
  const secret='enugu-scanner-token-encryption';
  const sourceHash=createHash('sha256');
  for (const file of ['package-lock.json','src/service.mjs','src/panel.html','src/panel.js.txt','src/panel.css.txt','google/main.mjs','google/firestore-store.mjs','google/http-server.mjs','Dockerfile'])
    sourceHash.update(file).update(readFileSync(new URL('../'+file,import.meta.url)));
  const image=`${region}-docker.pkg.dev/${project}/scanner/${service}:${sourceHash.digest('hex').slice(0,16)}`;
  const manifest={apiVersion:'serving.knative.dev/v1',kind:'Service',metadata:{name:service,annotations:{'run.googleapis.com/ingress':'all'}},
    spec:{template:{metadata:{annotations:{'autoscaling.knative.dev/minScale':'0','autoscaling.knative.dev/maxScale':'1'}},
      spec:{serviceAccountName:identity,containerConcurrency:4,timeoutSeconds:600,containers:[{image,
        resources:{limits:{cpu:'1',memory:'512Mi'}},ports:[{containerPort:8080}],
        env:[...Object.entries(env).map(([name,value])=>({name,value})),{name:'TOKEN_ENCRYPTION_KEY',valueFrom:{secretKeyRef:{name:secret,key:'1'}}}]}]}}}};
  const firebase={hosting:{public:'public',ignore:['firebase.json','**/.*','**/node_modules/**'],
    rewrites:[{source:'**',run:{serviceId:service,region}}],
    headers:[{source:'**',headers:[{key:'Cache-Control',value:'no-store'},{key:'X-Content-Type-Options',value:'nosniff'},
      {key:'Referrer-Policy',value:'no-referrer'},
      {key:'Content-Security-Policy',value:"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}]}]},
    firestore:{rules:'firestore.rules',indexes:'firestore.indexes.json'}};
  const plan={project,region,service,image,service_identity:identity,secret,secret_version:'1',
    billing_required:true,billing_enabled_by_this_tool:false,delivery_mode:'direct',
    services:['Firebase Hosting','Cloud Firestore','Google Cloud Run','Secret Manager','Artifact Registry','Cloud Build'],
    activation_status:'NOT_ACTIVATED',native_upload_origin:'Use the actual HTTPS .run.app service address after deployment; do not use the Hosting proxy for PDF uploads.',
    human_steps:['Authorize a billing-linked project if the no-paid-hosting constraint changes.','Connect OneDrive using SIGN IN AS OWNER.','Approve operator emails through the GUI.'],
    exclusions:['Per-PDF review remains undecided.','No malware scanner, OCR, issue tracker or push notifications has been implemented.','Microsoft identity is verified directly; Firebase Authentication is not inserted as a second login.'],
    verification:'Local emulator and simulated Microsoft endpoint tests are separate from live delivery.'};
  mkdirSync(resolve(output,'public'),{recursive:true});
  const save=(file,data)=>writeFileSync(resolve(output,file),JSON.stringify(data,null,2)+'\n');
  save('cloud-run-service.json',manifest);save('firebase.json',firebase);save('.firebaserc',{projects:{default:project}});save('deployment-plan.json',plan);
  for (const [target,source] of [['public/index.html','src/panel.html'],['public/panel.js','src/panel.js.txt'],['public/panel.css','src/panel.css.txt'],
    ['firestore.rules','google/firestore.rules'],['firestore.indexes.json','google/firestore.indexes.json']])
    writeFileSync(resolve(output,target),readFileSync(new URL('../'+source,import.meta.url)));
  return plan;
}
if (process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const args=process.argv.slice(2),get=name=>args[args.indexOf(name)+1];
  if (!args.includes('--project') || !args.includes('--output')) throw Error('Usage: node google/prepare.mjs --project PROJECT --output FOLDER [--region REGION]');
  const folder=JSON.parse(readFileSync(new URL('../../control_center/scanner_folder.json',import.meta.url)));
  const plan=prepare({project:get('--project'),output:get('--output'),region:args.includes('--region')?get('--region'):undefined,folder});
  process.stdout.write(JSON.stringify({output:resolve(get('--output')),activation_status:plan.activation_status,billing_required:plan.billing_required})+'\n');
}
