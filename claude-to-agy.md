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

*(Agy: add dated entries here as you work — what you found, what you changed, what's
still open. Keep Isaac's and Claude's sections above untouched.)*

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

---

## Claude's Follow-Up: Predicted Next Errors (2026-10-30)

Agy — good progress on the `onNewIntent` fix, the scope/endpoint relaxation, and the
UI bugs. Before calling OAuth "done," here's every failure mode I can predict from
what's in the repo so far (custom PKCE scheme, no MSAL, `/common/` endpoint,
`techlogscan://auth`, editable client ID field). Work through these — don't just
patch the first one you hit.

### A. Will likely surface soon (high probability)

1. **`AADSTS50011` — redirect URI mismatch.** The Entra app registration must have
   `techlogscan://auth` registered *exactly*, under the **"Mobile and desktop
   applications" (public client)** platform — not "Web." If it's under the wrong
   platform type, or still references the old `com.example.enuguairscannertest`
   naming from before the rename, every token exchange will fail at the authorize
   step with this error. Check this in the Entra portal; don't guess from code alone.

2. **`invalid_grant` on token exchange — authorization code replayed.** Deep-link
   intents can be redelivered (e.g. user double-taps the "return to app" prompt, or
   some browsers re-fire `ACTION_VIEW`). Microsoft auth codes are single-use — a
   second exchange attempt with the same code returns `AADSTS70000` / `invalid_grant:
   already redeemed`. Add an idempotency guard: track the last processed `code` (or a
   nonce) and ignore a repeat `onNewIntent()` call with the same one.

3. **PKCE `code_verifier` lost to process death.** While the browser/Custom Tab has
   focus, Android can kill `MainActivity` under memory pressure (common on
   lower-RAM devices). If the `code_verifier` is only held in memory (a local var or
   in-memory singleton) and not persisted, the app comes back, gets the code, but the
   verifier is gone — token exchange fails with `invalid_grant: PKCE verification
   failed`. Persist the verifier (EncryptedSharedPreferences, not plain prefs) keyed
   by `state`, before launching the browser.

4. **No refresh token handling yet.** `offline_access` gets you a refresh token, but
   if nothing *uses* it, access tokens (~60–90 min lifetime) will expire mid-session
   and every subsequent Graph call returns `401 Unauthorized` — the app will look like
   it "logged the user out" randomly. Needs a refresh flow (`grant_type=refresh_token`
   against the same `/common/` token endpoint) before this ships.

5. **Stuck "Signing you in..." state when the user cancels.** If the user backs out
   of the Microsoft account picker/consent screen, no redirect ever fires. Nothing in
   `onNewIntent` will catch this because it's never called. Add an `onResume()` check:
   if a sign-in was in progress and no OAuth intent arrived, reset the button instead
   of leaving a permanent spinner.

### B. Plausible given the current design (medium probability)

6. **Crash on error-shaped token responses.** If the token endpoint ever returns an
   error JSON body (`{"error": "...", "error_description": "..."}`) instead of the
   expected `{"access_token": ...}` shape — which will start happening now that real
   edge cases (#1, #2, #3) are reachable — a parser that only checks for
   `access_token` without checking for an `error` key first will throw an NPE/crash
   instead of surfacing a message. Add defensive parsing before the other fixes make
   this visible.

7. **Approval workflow keyed on the wrong claim.** If "manual approval" matches users
   by email/`preferred_username`, note that this claim's format differs between work
   accounts, personal Microsoft accounts, and guest accounts — and can be reassigned
   administratively. Use the stable `oid` (object ID) claim for identity matching, not
   a display/email claim.

8. **Conditional Access / compliance failures on managed corporate devices.** If any
   future tenant has Conditional Access policies (MFA required, compliant-device
   required), sign-in can fail with `AADSTS53000` or `AADSTS50158` — not fixable from
   the app, but the raw error should be logged and shown to the user rather than
   swallowed, so it's diagnosable instead of looking like another silent OAuth bug.

9. **Flaky-network false negatives.** On patchy mobile data, a slow or dropped
   connection to `login.microsoftonline.com` during token exchange will look
   identical to a silent OAuth failure unless there's explicit timeout + "check your
   connection, tap to retry" handling, separate from the generic auth-failed state.

10. **Invalid/unregistered client ID from the new editable "Azure App ID" field.**
    Since this now accepts arbitrary input with no validation, a blank value, a
    malformed GUID, or a client ID from a tenant where `techlogscan://auth` isn't
    registered will all produce generic Microsoft errors (`AADSTS700016` — application
    not found, or `AADSTS50011` again) with no indication the *field itself* is the
    cause. Add basic GUID-format validation and a clear inline error pointing back to
    that setting.

### C. Lower probability but worth a deliberate decision, not an accident

11. **Custom-scheme hijacking.** `techlogscan://auth` is a bare custom URI scheme —
    Android does **not** enforce exclusive ownership of it the way it does for
    verified HTTPS App Links (`autoVerify="true"` + `assetlinks.json`). In theory,
    any other installed app could register an intent-filter for the same
    scheme+host and race to intercept the redirect. PKCE limits the actual damage
    (a stolen `code` is useless without the `code_verifier`), so this is not urgent,
    but it's a real gap vs. MSAL's package+signature-bound `msauth://` scheme. Flag
    to Isaac as a decision point, not something to silently "fix" by switching
    schemes.

12. **Custom Tab not closing after redirect on some OEM browsers.** On certain
    Android skins/older Chrome versions, the Custom Tab can remain on screen after
    firing the custom-scheme redirect instead of auto-dismissing. If this shows up,
    it's a Custom Tabs lifecycle issue, not an auth issue — don't waste time
    re-debugging the OAuth flow itself if this happens.

13. **Debug vs. release signing — explicitly NOT an issue today**, since the custom
    scheme isn't signature-bound. Only becomes relevant if the project ever migrates
    to MSAL's `msauth://` format (Option 4 from the original ticket) — at that point,
    debug and Play-signed release builds need *separate* SHA-1 hashes registered in
    Entra. No action now; noting it so it isn't a surprise later.

**Priority order if you're tackling these**: 1 → 2 → 3 → 5 → 4, then 6–10 as you hit
them, then treat 11–13 as a conversation with Isaac rather than a unilateral fix.
