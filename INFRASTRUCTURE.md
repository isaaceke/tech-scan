Current deployment: Cloudflare Workers Free is live at https://enugu-techlog-scanner.isaaceke21.workers.dev. A SQLite Durable Object persists human email approvals, encrypted Microsoft authorization, delivery receipts and audit events. Staff use identity-only Microsoft sign-in; OneDrive writes use separate owner delegated authorization. The PC is outside the upload path. Google deployment is stopped; no paid hosting was activated.

The human owner completed sign-in. The live dashboard and server confirm the configured OneDrive folder is connected. The root distribution is now version 1.4/code 5, built with the permanent address and matching signing certificate; 51 Android tests passed. The device-page defect is fixed. Live staff sign-in and relay delivery remain unverified; the dashboard had no approved staff emails at the connection check. See DEPLOYMENT.md and .build/live-free-service-verification.json for current state.

## Historical implementation notes (inactive)

Deployment continuation: on 1 November 2026 the user authorized usage-based Google billing. The current Google account is blocked from Firebase project access until the user enables mandatory two-step verification. No hosted resources, billing profile, production secret or distribution APK have been activated.

Current source update, 1 November 2026: the user selected Firebase + Google Cloud + Microsoft 365. The native Kotlin app retains its offline scanner/outbox and uses the relay API. The Google adapter runs on Cloud Run with fenced Firestore persistence, a Firebase Hosting owner panel and atomic audit records. Ten Google emulator/HTTP/deployment tests, 21 shared service/runtime tests and 67 Python tests passed. The new Google infrastructure requires billing authorization and remains undeployed. Legitimate staff sign-in and live relay delivery remain unverified. TECHLOG SCAN.apk remains the blocked 1.3 release. See online_service/google/README.md and DEPLOYMENT.md for the selected implementation and activation boundary.

The following paragraphs describe the earlier direct-sharing release. Its email panel and Android source used Microsoft folder permissions directly. No scanner server was used by that implementation.

The destination is the ATTAIR OneDrive owned by isaac.eke@attair.com.ng. Owner sign-in connects the application folder and records public drive, folder and owner IDs. The APK contains those IDs and no owner token. Operator sign-in does not change the destination.

Only a human pressing APPROVE EMAIL or Remove selected access changes a live folder permission. The panel requests signed-in write access for the exact email without sending a notification email. External sharing and guest onboarding remain subject to Microsoft policy; a successful permission creation alone does not prove operator access.

Both sign-in paths use ATTAIR tenant 38de9dec-d800-439b-a669-60f628a90e72. Owner sign-in requests User.Read Files.ReadWrite offline_access. Android and operator verification request User.Read Files.ReadWrite.All offline_access for the owner's shared folder. The human reviews the disclosed consent on Microsoft's page; refresh never expands consent. No client credentials or owner tokens authorize an operator upload.

The phone verifies Graph /me and individual write permission on the configured folder. A specific-person link counts only for a matching listed identity. Broad links, groups, inherited/read-only permissions and expired or malformed permissions are denied. GUID comparisons handle Microsoft's case variations. Access is checked on entry, periodically and before delivery; Microsoft also enforces the upload request.

Each scan is first written locally and read back to verify its bytes. On modern Android, MediaStore publishes the file only after the complete write and check. Original camera images are released after a successful local save, so a failed local save can restore them. A network error cannot undo the completed local save.

ScanDeliveryStore retains an additional private PDF and fsynced metadata journals for delivery. Each job records its original verified account, drive, root folder, aircraft, patch destination, size and SHA-256. Remote names preserve the original base and append a stable 12-character unique suffix. Retries use the same remote name. Complete receipts are saved before retained PDF bytes are deleted. Wrong-account, wrong-destination and corrupt-byte results never complete a job.

ScannerApplication initializes the outbox on every process startup. WorkManager uses connected-network constraints, unique immediate work, 15-minute periodic recovery and exponential retry from 30 seconds. Inline and background delivery share a mutex. Jobs for a previous account remain retained and do not starve the current account's deliveries. The home screen shows pending count, errors and the latest verified receipt. Android schedules retries; timing can be delayed by power management or force-stop.

MicrosoftGraphPdfClient verifies the original /me identity, exact root and aircraft/patch parents, uploaded metadata and independent item metadata. It downloads the PDF and compares SHA-256 before reporting delivery. Signed HTTPS download redirects receive no Graph bearer token. The loopback override is used only by JVM tests; the APK uses https://graph.microsoft.com/v1.0.

An optional selected-folder write is separate from ATTAIR delivery and cannot count as cloud success. Local documents remain available even when Microsoft access is unavailable.

The panel's Verify PDF delivery action uses a legitimately signed-in test account, then independently downloads metadata and bytes as the ATTAIR owner. A live successful run saves .build/live-folder-verification.json. The separate owner-only probe does not prove operator delivery and explicitly records operator_access_verified:false. Test clients never create live proof files.

Owner sessions and refresh tokens use Windows DPAPI and Microsoft's expiry metadata. Operator test tokens stay in panel memory. Android tokens and pending scans are excluded from backup. Sanitized panel diagnostics record events, connection state, timestamps, HTTP status and AADSTS codes without recording tokens, passwords or sign-in codes.

Builds run the production authorization/delivery tests in fresh packaging directories, compare source/configuration fingerprints and inspect the packaged public config. Missing IDs or a build failure preserve the existing root APK. Successful replacement keeps a timestamped backup.

Current status: configured root APK version 1.3 (code 4), with the owner-connected drive/folder IDs. The owner signed in successfully and live owner-only delivery of the native Android PDF passed through the built production Kotlin classes, followed by independent owner read-back. The separate preview remains unconfigured. There are 42 current Python checks and 45 current Android checks, plus 17 historical backend checks and 2 unrelated sample tests. Simulated HTTP checks and native local scanning do not establish live Microsoft consent, guest redemption or operator delivery. See END_TO_END_CHECK.md for the current evidence.

No guarantee for every arbitrary email is possible through direct Microsoft sharing when the tenant can reject external identities or user consent. The app does not modify that policy. Stop at an actual Microsoft denial and retain its diagnostic code; do not distribute an unconfigured APK or send staff through repeated tests of a failed prerequisite.

Official references:

- [OneDrive permissions](https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/permissions_reference?view=odsp-graph-online)
- [Graph scopes and consent](https://learn.microsoft.com/en-us/graph/permissions-reference)
- [Specific-person sharing links](https://learn.microsoft.com/en-us/graph/api/resources/sharinglink?view=graph-rest-1.0)
- [Folder invitations](https://learn.microsoft.com/en-us/graph/api/driveitem-invite?view=graph-rest-1.0)
- [Download redirects](https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0)
- [External-sharing policy failures](https://learn.microsoft.com/en-us/troubleshoot/sharepoint/sharing-and-permissions/responsestatusnotok-sharing-sharepoint-onedrive-site)

The older backend and inactive deployment templates are historical sources. The current panel does not launch them and the current Android source does not contact them.

The replacement root APK removes the former Render server address and backend authentication routes responsible for the obsolete server-unreachable flow. Physical-phone installation and approved staff-account Microsoft authentication have not been performed by tools. No account permissions were changed during the live owner checks.

Confirmed rollout blocker, 1 November 2026: Microsoft returned AADSTS90094 for the personal test account. ATTAIR's consent policy prevents that account from granting the app's requested permissions. The exact rule (permission classification, guest restriction, assignment or application/publisher restrictions) has not been read; no organization settings were changed. The direct-sharing route is not proven usable under the requested no-administrator-consent constraint. Owner-only success remains separate evidence. See ACCESS_BLOCKER.md before further rollout or sign-in requests.
