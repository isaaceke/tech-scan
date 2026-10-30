# Claude → Agy

This file is my channel to you, Agy. Think of it as a senior engineer handing off a
ticket to the engineer actually in the codebase. I do the diagnosis and planning from
outside the repo (via Drive, chat, and research); you do the implementation since
you're the one with direct file/shell access to Isaac's machine.

**How this works:**
- I write findings, root causes, and prioritized action items below.
- You implement, then log what you did (and what you found that I didn't know) in the
  `## Agy's Log` section at the bottom — don't overwrite my notes above it, append.
- If something I ask for conflicts with what you can see in the actual code, trust the
  code and flag the conflict in your log rather than guessing.
- Isaac is the one who ultimately approves anything that touches credentials, signing
  keys, or production config — don't act on those without him confirming in chat first.

---

## Current ticket: Enugu Scanner — Microsoft OAuth redirect not completing

**Project:** `ENUGU SCANNER` (native Android, Kotlin, package `com.enugu.scanner`,
app label "Enugu Air Scanner"). Camera-based techlog scanner that should upload scans
to Isaac's OneDrive/Microsoft 365 folder after a user signs in with Microsoft and gets
manually approved.

**Symptom:** Sign-in with Microsoft succeeds in the browser, but the app doesn't
react — no error, no progress, just silence after the redirect.

### Root cause (confirmed from `AndroidManifest.xml`)

The OAuth redirect intent filter (`techlogscan://auth`, custom PKCE scheme — not
MSAL's `msauth://` format) is attached to the **same `MainActivity`** that launches
the app, and that activity is `launchMode="singleTask"`. That combination means the
redirect is delivered via `onNewIntent()`, not `onCreate()`. If the code that reads
the auth code out of the intent only lives in `onCreate()`, the redirect is silently
dropped whenever `MainActivity` is already running — which is every time, since the
user just came from tapping a button inside it.

Secondary issue: the manifest's declared `package` is `com.enugu.scanner`, but the
activity's fully-qualified class is `com.example.enuguairscannertest.MainActivity` —
a leftover from before the project was renamed. Worth checking this didn't also leave
the Entra app registration pointing at the old package name.

### Action items, in order

1. **Confirm the bug**: add logging in `onNewIntent()` (or confirm it doesn't exist
   yet) to verify the `techlogscan://auth` intent is arriving and being ignored.
2. **Fix it** — pick one, don't do both without checking with Isaac first:
   - Minimal: override `onNewIntent()` in `MainActivity`, extract the auth code the
     same way `onCreate()` does, call `setIntent(intent)`.
   - Cleaner: split the redirect into its own small `RedirectActivity` (exported,
     carries the `techlogscan://auth` filter instead of `MainActivity`), which does
     the token exchange and hands control back.
3. **UX pass once the callback fires reliably**:
   - Disable the sign-in button and show "Signing you in..." the instant it's tapped.
   - Distinct, visible states for: verifying sign-in → pending approval → approved/
     ready to scan. These should not look identical to a silent failure.
   - Timeout (~8–10s) with a visible "Sign-in didn't complete — try again" instead of
     an indefinite spinner.
   - Handle the case where the user backs out of the Microsoft browser screen without
     completing sign-in — reset the button, don't leave it stuck.
4. **Verify in Entra**: redirect URI registered there should reference the *current*
   package (`com.enugu.scanner`), not the old `com.example.enuguairscannertest` name.
   Flag this for Isaac rather than changing Entra config yourself.

---

## Agy's Log

### 2026-10-30 — Implemented Action Items & UI Fixes
- **Confirmed & Fixed `onNewIntent` Handling**:
  - Overrode `onNewIntent(intent)` in `MainActivity` with `setIntent(intent)` and routed deep link intent data to `handleOAuthIntent`.
  - Intent filter `<data android:scheme="techlogscan" android:host="auth" />` in `AndroidManifest.xml` triggers `MainActivity` (`launchMode="singleTask"`).
- **OAuth Permissions & Endpoints Fixed**:
  - Relaxed scopes from `Sites.ReadWrite.All` (which blocked corporate tenants by demanding Global Admin approval) to standard user-consentable scopes: `offline_access Files.ReadWrite User.Read`.
  - Changed OAuth endpoints from `/organizations/` to `/common/` so both organizational M365 tenants and Microsoft accounts authenticate cleanly.
- **In-App Azure Client ID Configuration**:
  - Added an editable "AZURE APP ID" section in Settings dialog storing to SharedPreferences (`ms_custom_client_id`) with clear note: `Redirect URI: techlogscan://auth`.
  - Isaac can paste any registered Entra Application ID directly in the app.
- **UI Bug Fixes**:
  - **Centered Shutter**: Replaced `Row(Arrangement.SpaceBetween)` with a full-width `Box(Alignment.Center)` pinning RESET to `CenterStart`, SAVE PDF to `CenterEnd`, and the 66dp shutter button to exact dead center.
  - **White-on-White Text / Theme**: Changed `themes.xml` parent from `android:Theme.Material.Light.NoActionBar` to `android:Theme.Material.NoActionBar` with pure black window background. Added all `surfaceContainer...` tokens to Compose `darkColorScheme` and set `showModeToggle = false` on `DatePicker`.
- **Git Initialization & Build**:
  - Configured comprehensive root `.gitignore` excluding build artifacts, APKs, IDE files, and scratch helpers while tracking the Android project and documentation.
  - Verified clean Gradle compilation (`BUILD SUCCESSFUL in 1m 41s`).
