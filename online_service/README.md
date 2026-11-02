The active deployment is Cloudflare Workers Free at https://enugu-techlog-scanner.isaaceke21.workers.dev, with the existing Microsoft OneDrive destination. The scope is the owner's email panel and native scanner PDF delivery. There is no antivirus, OCR or separate validation pipeline. Google deployment is stopped; its local adapter is retained as an inactive reference. No paid hosting or billing account has been activated.

This is the replacement for direct staff access to the ATTAIR OneDrive. It runs on Cloudflare Workers Free with one SQLite-backed Durable Object. The PC is not part of the delivery path.

The owner approves primary Microsoft emails in either the hosted access panel or the Windows Control Center. An unlisted account is denied immediately; no pending-request queue is created. The first approved sign-in binds that email to Microsoft's returned account ID. Every upload checks current approval and independently verifies the Microsoft identity.

Operator authorization uses the common Microsoft authority with User.Read and offline_access only. The service creates and retains PKCE challenges, redeems codes itself, verifies Graph /me, and issues opaque scanner sessions. No operator requests access to the owner's company files. Organizational policies can still restrict identity sign-in; live personal-account sign-in remains to be verified.

Owner connection is a human SIGN IN AS OWNER action. The service requests the owner's existing delegated User.Read Files.ReadWrite offline_access authorization in the ATTAIR tenant. It checks the exact owner and configured drive/folder before retaining encrypted tokens. The owner's earlier Windows DPAPI session is preserved locally and is not exported by this implementation.

Owner and identity token records use AES-GCM with record-specific authenticated data. TOKEN_ENCRYPTION_KEY is a generated 32-byte Cloudflare secret. It must be preserved across deployments; replacing it requires reconnecting Microsoft accounts. No owner token or encryption key enters the APK. Do not enable request-body/token logging.

PDFs remain in the phone's local storage and durable outbox. The service accepts a PDF up to 32 MB, verifies its SHA-256, uploads under the configured root/aircraft/patch folder, reads back metadata and streams the remote bytes through SHA-256. Only a matching readback produces a durable receipt. Retries preserve the original name and job ID. The service reserves names per destination and refuses to overwrite a pre-existing file outside its own journal. The service does not keep an extra server PDF archive.

Cloudflare Free includes 100,000 Worker requests/day, 100,000 Durable Object requests/day, 13,000 GB-seconds/day of Durable Object duration, 5 million storage row reads/day and 100,000 writes/day. SQLite Durable Object storage is available on Free. The outer Worker forwards API work; PDF work runs in the Durable Object, whose documented CPU allowance is 30 seconds per request. Hitting free quotas can interrupt service; the phone retains its PDF. There is no paid subscription or automatic paid upgrade in this project.

Verified official references (1 November 2026):

- https://developers.cloudflare.com/workers/platform/pricing/
- https://developers.cloudflare.com/durable-objects/platform/limits/
- https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow

Deployment sequence for the maintainer:

1. The owner completes private Cloudflare account sign-in and uses Workers Free. CLI deployment additionally needs the owner's authorization of official Wrangler login.
2. Use Node 24 LTS (validated with the bundled Node 24.22.1), then run npm ci, npm run check and npm test in this folder. Node 26 showed an intermittent local Miniflare connection reset; the complete suite passed on Node 24. The runtime test uses isolated synthetic Microsoft identities and endpoints; it does not approve real accounts. When available, it sends the real camera-captured PDF through the packaged service locally.
3. Deploy with the bundled Wrangler CLI into that Free account. Create TOKEN_ENCRYPTION_KEY as a secret only if it does not already exist. Never print it or put it in wrangler.jsonc, source control or an APK.
4. Record the deployment's actual permanent workers.dev address in the public scanner_service.json asset and verify /health identifies enugu-scanner-relay and the exact connected drive/folder IDs.
5. The human owner opens the hosted panel or Windows Control Center and completes SIGN IN AS OWNER. Approvals remain human GUI actions.
6. Verify live delivery through the service and legitimate personal-account identity sign-in. Record these separately from local simulated evidence. Build/release guards require online owner storage to be connected before replacing TECHLOG SCAN.apk.

Current status: the Worker and its encryption secret are deployed, and the human owner connected the exact ATTAIR OneDrive folder. Live health, dashboard connection and unauthenticated-access checks passed. The missing allowed host for Microsoft's current https://login.microsoft.com/device response was fixed and verified live; 23 service/runtime tests pass. The root TECHLOG SCAN.apk is now 1.4/code 5, built after the connected-service guard and 51 passing Android tests, with the permanent address and previous signing certificate. The old APK is backed up. No real email approvals were changed through tools; the dashboard's staff list was empty at the connection check. Live staff sign-in and delivery remain unverified.
