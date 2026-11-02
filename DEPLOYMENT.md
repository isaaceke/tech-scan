Cloudflare Workers Free is deployed at https://enugu-techlog-scanner.isaaceke21.workers.dev. This address serves both the email dashboard and the Android upload API. Google deployment is stopped. No paid hosting or billing account was activated.

The owner opens that address, clicks SIGN IN AS OWNER, and completes the Microsoft device-code sign-in as isaac.eke@attair.com.ng. The service verifies the exact configured owner and ATTAIR OneDrive folder before retaining encrypted delegated authorization. The existing Windows DPAPI session stays on this computer.

The live Microsoft device-code response uses https://login.microsoft.com/device. The server now accepts that exact Microsoft host; the initial missing-host defect was reproduced, fixed, tested and deployed. The human owner completed private sign-in, and both the dashboard and /health confirm the configured OneDrive connection. Live staff authentication and PDF delivery remain unverified. The dashboard contained no approved staff emails at the connection check.

The root TECHLOG SCAN.apk is now version 1.4/code 5, containing the permanent HTTPS service address. The connected-service build guard passed, all 51 Android tests passed without skips, the packaged destination and service configuration matched, and apksigner verified the same certificate as the previous release. The old 1.3 APK is backed up in .build/apk-backups/TECHLOG SCAN.20261101-232226-682208.apk. SHA-256 of the updated APK: 674b5c0aae8f7ae67794c3775006005d336b0b7db61620a2e6896d5acdcbceb2. Future updates can use C:\Python314\python.exe control_center\build_apk.py.

Staff authenticate with Microsoft identity-only permission (User.Read and offline_access). Only the owner authorizes OneDrive storage. Real email approval and removal remain human GUI actions. The phone retains each PDF until verified delivery; the PC is outside the upload path. There is no antivirus, OCR or separate validation pipeline.

Evidence: .build/live-free-service-verification.json. Source and deployment details: online_service/README.md. Preserve the existing TOKEN_ENCRYPTION_KEY secret across deployments; never regenerate it as a routine deployment step.
