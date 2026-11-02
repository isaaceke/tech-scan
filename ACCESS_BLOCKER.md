Current deployment: Cloudflare Workers Free is live at https://enugu-techlog-scanner.isaaceke21.workers.dev. The human owner completed private Microsoft sign-in and the actual configured OneDrive folder is connected. The initial "Unexpected Microsoft sign-in page" error was reproduced: Microsoft returned https://login.microsoft.com/device, which was missing from the server's allowed-host list. The fix passed 23 service/runtime tests and the deployed owner sign-in succeeded.

The replacement requests only User.Read and offline_access from staff; the owner separately authorizes storage. Live legitimate staff sign-in and PDF delivery remain unverified. No real email approvals or tenant policies were changed through tools; the dashboard had no approved staff emails at the connection check. The root distribution is now 1.4/code 5, configured for the live connected service, with the previous signing certificate and 51 passing Android tests. Google deployment is inactive. See DEPLOYMENT.md for the current rollout.

## Historical blockers and inactive implementations

Deployment continuation: on 1 November 2026 the user authorized usage-based Google billing. The current Google account is blocked from Firebase project access until the user enables mandatory two-step verification. No hosted resources, billing profile, production secret or distribution APK have been activated.

Current replacement: the user selected Firebase + Google Cloud + Microsoft 365. Cloud Run/Firestore relay code and Firebase Hosting panel deployment files are implemented and locally tested. This changes staff sign-in to identity-only Microsoft permission; only the owner authorizes OneDrive storage. Legitimate staff sign-in and live relay delivery remain unverified. Google requires billing for Cloud Run, conflicting with the earlier no-paid-hosting instruction until explicitly resolved. No Google service, billing account, production secret, real email approval or replacement distribution APK has been activated. See online_service/google/README.md.

The following describes the earlier direct-sharing release. Its personal-account workflow is blocked by Microsoft's ATTAIR consent policy. Repeating the same sign-in or reinstalling version 1.3 cannot change that policy.

Microsoft recognized isaaceke21@gmail.com, then returned AADSTS90094 on 1 November 2026 at 01:56:42 Africa/Lagos (00:56:42 UTC). The response explicitly says an administrator set a policy preventing this account from granting the application its requested permissions.

The scanner now addresses the ATTAIR tenant to reach the owner's company OneDrive. This changed the account-selection page. The dashboard's email approval grants folder access; Microsoft app consent is an additional requirement before a delegated access token can be used. A successful owner scan/upload is not proof of external-user sign-in or consent.

The current direct-upload design requests delegated User.Read and Files.ReadWrite.All, plus offline_access. Delegated Files.ReadWrite.All does not inherently require administrator consent in Microsoft's general permission reference, but an organization may prohibit users from granting it. The screenshot confirms that the current request is prohibited for the personal test account. Unverified publisher status is visible; it is not enough evidence to identify the exact policy rule.

For a human ATTAIR administrator who chooses to review this app:

- Application: ATTAIR Techlog OneDrive Connector
- Client ID: dc7101d3-3bb7-462f-92e8-374958f4ddb5
- Resource tenant: 38de9dec-d800-439b-a669-60f628a90e72
- Permission type: delegated; no application permission or client secret is used by the APK
- Requested Graph permissions: User.Read and Files.ReadWrite.All
- Requested identity scope: offline_access
- Intended destination: the ATTAIR app folder owned by isaac.eke@attair.com.ng
- Request ID: 087f39e1-3379-4c7f-af4c-c3325f960200
- Correlation ID: a984dd17-7de0-4d59-8879-d776e21ddd7d
- Provider error: AADSTS90094

Authorizing the application does not approve an employee's email in the scanner dashboard. Folder approvals remain human GUI actions. The assistant has not requested or granted administrator consent, changed tenant policy, approved an operator, or authenticated as an administrator.

Reducing consent is not a verified fix for this account. Microsoft's OneDrive reference distinguishes access to the user's own files from other users' shared files for work/school tokens. App-folder permissions target the signed-in person's app storage and do not independently grant access to this owner's folder. Legacy Files.ReadWrite.Selected is not intended for direct Graph calls; Files.SelectedOperations.Selected itself requires administrator consent. The shared-item API documents Files.ReadWrite as a least privilege, but that does not establish that ATTAIR's policy allows this external account to consent to it or that it will authorize the required delivery. No untested narrower-scope build has been handed to the user.

If administrator consent remains unacceptable, the architecture needs an owner-authorized upload relay. Staff would authenticate their Microsoft identity with basic identity permission, the relay would check the human-managed email list, and uploads would use the owner's existing delegated storage authorization. The owner token must stay in protected service storage and never go into staff APKs. Every upload must recheck identity and the list, retain its scan on failure, and verify the actual destination and PDF bytes. The relay must have a stable address reachable by staff phones. Free hosting or an always-online reachable PC must be established before that can be presented as a working replacement. No hosting or architecture change has been activated.

The current source-only diagnostics patch preserves the actual error code and explains the organization blocker. It does not solve app consent, and the root APK has not been rebuilt just to change the error text.

Replacement now prepared: the user requires uploads while the Control Center PC is off. Cloudflare Free service source, human email-panel source and identity-only Android relay source have been implemented. Local service tests, the packaged workerd runtime transaction, native transport/journal tests and Android preview packaging passed. Cloudflare private sign-in and hosting activation remain pending. No legitimate personal-account sign-in or live relay delivery has yet been proved; this does not turn the earlier owner-only evidence into staff end-to-end proof. The existing root APK remains version 1.3.

Official references:

- [Microsoft's AADSTS90094 troubleshooting](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/troubleshoot-consent-issues)
- [User and administrator consent](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/user-admin-consent-overview)
- [OneDrive permissions and shared files](https://learn.microsoft.com/en-us/onedrive/developer/rest-api/concepts/permissions_reference?view=odsp-graph-online)
- [Microsoft Graph selected-file permissions](https://learn.microsoft.com/en-us/graph/permissions-reference#filesselectedoperationsselected)
- [Shared-item API permissions](https://learn.microsoft.com/en-us/graph/api/shares-get?view=graph-rest-1.0)
