# GPT → Agy: OneDrive Architecture Review and Next Actions

Date: 2026-10-31

## Goal (non-negotiable)

All scanned PDFs must be stored in **Isaac's Microsoft 365 OneDrive**:

- Owner/storage account: `isaac.eke@attair.com.ng`
- Employees from other companies sign into the Android scanner using their own Microsoft accounts.
- Employees do not use their own OneDrive storage.
- Isaac manually approves or rejects each employee.
- Approved employees upload through the backend.
- The backend writes files into a dedicated application folder in Isaac's OneDrive.
- Employees must never receive Isaac's OneDrive access token, refresh token, client secret, or direct OneDrive access.
- Do not use the old `SPLIT` folder or upload to an employee's drive.
- Preserve all existing scanner/camera/PDF functionality.

## Entra app registration already created

- App: `ATTAIR Techlog OneDrive Connector`
- Client ID: `dc7101d3-3bb7-462f-92e8-374958f4ddb5`
- Tenant ID: `38de9dec-d800-439b-a669-60f628a90e72`
- Redirect URI registered for the Android public client: `techlogscan://auth`
- Current configured delegated permissions were `User.Read` and `Files.ReadWrite.AppFolder` (verify actual portal state before relying on this; do not silently change permissions).
- No client secret should ever be embedded in the Android app.

## What I found in the current repository

The Android app's `MicrosoftOAuthManager.kt` currently:
- Uses the Client ID above.
- Signs employees in with Microsoft using PKCE and requests `offline_access User.Read`.
- Registers the employee with the backend.
- Sends PDF uploads to `/api/scans/upload` on the backend, rather than directly to Graph.
- Checks an operator status locally before attempting upload.

The backend's `backend/main.py` currently:
- Has the target account configured as `isaac.eke@attair.com.ng`.
- Uses client-credentials flow with `CLIENT_SECRET` to obtain a Graph application token.
- Has an operator approval database and upload route (inspect the complete route and all authorization checks).
- Describes the target as Isaac's OneDrive AppFolder.

These are code-level intentions, **not proof that Graph authorization or an upload works**.

## Required investigation — do this before changing code or asking Isaac to change Entra

1. Inspect the complete current backend upload route and all related Graph helper functions. Trace the actual Graph URL, drive/user targeting, folder creation, file upload, error handling, and success response.
2. Confirm from current Microsoft documentation whether the required **application permission** for app-folder access is supported for a Microsoft 365 work/school OneDrive and whether it requires tenant admin consent. Distinguish delegated permissions from application permissions. Do not assume delegated `Files.ReadWrite.AppFolder` authorizes backend client-credentials access.
3. Confirm whether application-only access can address Isaac's OneDrive AppFolder using the chosen endpoint. If not, identify the supported secure alternative (for example, backend-held delegated authorization established by Isaac), including token renewal and consent requirements.
4. Confirm how the backend will securely identify and target Isaac's drive. Do not assume `/me` works in client-credentials flow. Verify whether a user/drive-specific Graph endpoint is required.
5. Verify the app-folder endpoint and upload path against official Microsoft Graph documentation. Do not use `/me/drive/root:/SPLIT`.
6. Inspect employee identity verification and authorization. The backend must validate a Microsoft-issued employee identity/token or a secure backend session; it must not trust a client-supplied email address or a locally stored `APPROVED` status as proof of identity/approval.
7. Inspect the approval links/tokens. They must be protected against unauthorized approval, replay, guessing, and unintended public access.
8. Review CORS, admin authentication, upload size/type limits, filename/path sanitization, duplicate handling, and upload persistence/retry behavior.
9. Remove insecure hard-coded fallback secrets/passwords. In particular, do not ship or deploy with the default `ADMIN_SECRET` value `enugu2026`. Require strong deployment secrets and fail safely when required secrets are absent.
10. Ensure failed or uncertain Graph uploads are not reported as successful and local scans are not deleted until the backend confirms durable storage.

## Implementation rules

- Do not modify the working scanner/camera workflow.
- Do not add broad `Files.ReadWrite` merely to make an error disappear.
- Do not create or expose a client secret in Android.
- Do not ask Isaac to grant admin consent until you provide the exact permission name, permission type (Application or Delegated), why it is needed, and the exact Entra screen/action.
- Do not claim an AppFolder exists or that upload works until an actual test file is visible in Isaac's OneDrive.
- Do not make speculative changes. Make minimal, reviewable changes with tests.
- Never print secrets, tokens, or full authorization headers in logs.

## Required response to Isaac

First provide a concise report with:

A. Current verified architecture and actual code paths.
B. The supported Microsoft authorization model for Isaac's work/school OneDrive.
C. Exact Entra permissions required, including whether admin consent is mandatory.
D. Exact manual actions Isaac must perform in Entra/OneDrive, if any.
E. Code changes required in backend and Android.
F. Security issues found, ranked by severity.
G. A reproducible end-to-end test proving an approved employee can upload a PDF into Isaac's dedicated app folder.

Do not begin a risky rewrite until the authorization model is verified. Once verified, implement the smallest complete solution and report changed files and test results.
