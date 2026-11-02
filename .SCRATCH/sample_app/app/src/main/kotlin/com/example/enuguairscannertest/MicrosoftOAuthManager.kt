package com.example.enuguairscannertest

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.util.Base64
import androidx.browser.customtabs.CustomTabsIntent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.security.MessageDigest
import java.security.SecureRandom

object MicrosoftOAuthManager {
    const val DEFAULT_CLIENT_ID = "dc7101d3-3bb7-462f-92e8-374958f4ddb5"
    const val REDIRECT_URI = "techlogscan://auth"
    // Requested only by the human sign-in action. Microsoft must grant consent.
    const val SCOPES = "offline_access User.Read Files.ReadWrite.All"
    private const val GRAPH = "https://graph.microsoft.com/v1.0"
    private const val ACCESS = "ms_access_token"
    private const val REFRESH = "ms_refresh_token"
    private const val EXPIRES = "ms_token_expires_at"
    private const val EMAIL = "ms_user_email"
    private const val SCOPE = "ms_granted_scope"
    private const val VERIFIER = "ms_code_verifier"
    private const val STATE = "ms_auth_state"
    private const val STATUS = "operator_approval_status"
    private val statusMutex = Mutex()
    private val tokenMutex = Mutex()
    private var folderConfig = JSONObject()
    data class OperatorSyncResult(val status: String, val message: String? = null)
    private class GraphException(val statusCode: Int, message: String) : Exception(message)

    fun initialize(context: Context) {
        OnlineScannerIdentity.initialize(context)
        folderConfig = try {
            context.assets.open("scanner_folder.json").bufferedReader().use { JSONObject(it.readText()) }
        } catch (_: Exception) { JSONObject() }
    }

    fun isConnected(prefs: SharedPreferences): Boolean = if (OnlineScannerIdentity.enabled()) OnlineScannerIdentity.connected(prefs)
        else !prefs.getString(ACCESS, null).isNullOrBlank() || !prefs.getString(REFRESH, null).isNullOrBlank()

    fun getConnectedEmail(prefs: SharedPreferences): String? = if (OnlineScannerIdentity.enabled()) OnlineScannerIdentity.email(prefs) else prefs.getString(EMAIL, null)

    // Access is checked again on app entry and before every upload.
    fun getOperatorStatus(prefs: SharedPreferences): String = if (isConnected(prefs)) "CHECKING" else "NOT_SIGNED_IN"

    fun disconnect(prefs: SharedPreferences) {
        OnlineScannerIdentity.disconnect(prefs)
        val editor = prefs.edit()
        for (key in listOf(ACCESS, REFRESH, EXPIRES, EMAIL, SCOPE, VERIFIER, STATE, STATUS, "scanner_server_session", "ms_resource_tenant", "ms_user_id")) editor.remove(key)
        editor.apply()
    }

    private fun encode(value: String): String = URLEncoder.encode(value, "UTF-8")
    private fun randomCode(): String {
        val bytes = ByteArray(48)
        SecureRandom().nextBytes(bytes)
        return Base64.encodeToString(bytes, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
    }

    fun cancelSignIn(prefs: SharedPreferences) {
        OnlineScannerIdentity.cancel(prefs)
        prefs.edit().remove(STATE).remove(VERIFIER).apply()
    }

    fun onlineServiceEnabled() = OnlineScannerIdentity.enabled()
    fun onlineServerUrl() = OnlineScannerIdentity.serverUrl()

    suspend fun startSignIn(context: Context, prefs: SharedPreferences) {
        if (OnlineScannerIdentity.enabled()) { OnlineScannerIdentity.startSignIn(context, prefs); return }
        val verifier = randomCode()
        val state = randomCode()
        val digest = MessageDigest.getInstance("SHA-256").digest(verifier.toByteArray(Charsets.US_ASCII))
        val challenge = Base64.encodeToString(digest, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
        prefs.edit().putString(VERIFIER, verifier).putString(STATE, state).apply()
        val url = FolderAccessPolicy.AUTHORITY + "authorize?" +
            "client_id=" + encode(DEFAULT_CLIENT_ID) + "&response_type=code&response_mode=query" +
            "&redirect_uri=" + encode(REDIRECT_URI) + "&scope=" + encode(SCOPES) +
            "&code_challenge=" + encode(challenge) + "&code_challenge_method=S256&state=" + encode(state) +
            "&prompt=select_account"
        CustomTabsIntent.Builder().setShowTitle(true).build().launchUrl(context, Uri.parse(url))
    }

    private fun tokenPost(fields: String): JSONObject {
        val conn = URL(FolderAccessPolicy.AUTHORITY + "token").openConnection() as HttpURLConnection
        try {
            conn.connectTimeout = 12000
            conn.readTimeout = 20000
            conn.instanceFollowRedirects = false
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
            conn.outputStream.use { it.write(fields.toByteArray(Charsets.UTF_8)) }
            val code = conn.responseCode
            val text = (if (code in 200..299) conn.inputStream else conn.errorStream)?.bufferedReader()?.use { it.readText() } ?: "{}"
            val json = JSONObject(text)
            if (code !in 200..299) throw Exception(FolderAccessPolicy.signInError(json.optString("error_description", "Microsoft sign-in failed.")))
            return json
        } finally { conn.disconnect() }
    }

    private fun saveTokens(prefs: SharedPreferences, result: JSONObject) {
        val access = result.getString("access_token")
        require(access.isNotBlank()) { "Microsoft did not confirm sign-in." }
        val lifetime = result.getLong("expires_in")
        require(lifetime > 0) { "Microsoft did not return valid token expiry metadata." }
        val editor = prefs.edit().putString(ACCESS, access)
            .putLong(EXPIRES, System.currentTimeMillis() + (lifetime - 60).coerceAtLeast(0) * 1000)
            .putString("ms_resource_tenant", FolderAccessPolicy.RESOURCE_TENANT)
            .putString(SCOPE, result.optString("scope", prefs.getString(SCOPE, "") ?: ""))
        if (result.optString("refresh_token").isNotBlank()) editor.putString(REFRESH, result.getString("refresh_token"))
        editor.apply()
    }

    suspend fun handleAuthRedirect(intent: Intent, prefs: SharedPreferences): Pair<Boolean, String> = withContext(Dispatchers.IO) {
        if (OnlineScannerIdentity.enabled()) return@withContext OnlineScannerIdentity.finish(intent, prefs)
        val data = intent.data ?: return@withContext Pair(false, "No Microsoft sign-in response.")
        if (data.scheme != "techlogscan" || data.host != "auth") return@withContext Pair(false, "Unexpected sign-in response.")
        val expectedState = prefs.getString(STATE, null)
        if (expectedState.isNullOrBlank() || data.getQueryParameter("state") != expectedState)
            return@withContext Pair(false, "Sign-in response did not match this request.")
        val verifier = prefs.getString(VERIFIER, null) ?: return@withContext Pair(false, "Sign in again.")
        prefs.edit().remove(STATE).remove(VERIFIER).apply()
        if (data.getQueryParameter("error") != null)
            return@withContext Pair(false, FolderAccessPolicy.signInError(data.getQueryParameter("error_description") ?: "Microsoft sign-in was declined."))
        val code = data.getQueryParameter("code") ?: return@withContext Pair(false, "Microsoft did not return a sign-in code.")
        try {
            val result = tokenPost("client_id=" + encode(DEFAULT_CLIENT_ID) + "&grant_type=authorization_code" +
                "&code=" + encode(code) + "&redirect_uri=" + encode(REDIRECT_URI) + "&code_verifier=" + encode(verifier))
            val token = result.getString("access_token")
            val profile = graphJson("/me?" + "\u0024select=id,mail,userPrincipalName", token)
            val email = verifiedEmail(profile)
            disconnect(prefs)
            saveTokens(prefs, result)
            prefs.edit().putString(EMAIL, email).putString("ms_user_id", profile.getString("id")).apply()
            refreshOperatorStatus(prefs)
            Pair(true, email)
        } catch (error: Exception) {
            Pair(false, FolderAccessPolicy.signInError(error.message ?: "Microsoft sign-in failed."))
        }
    }

    suspend fun getValidAccessToken(prefs: SharedPreferences): String? = withContext(Dispatchers.IO) {
        if (OnlineScannerIdentity.enabled()) return@withContext OnlineScannerIdentity.bearer(prefs)
        tokenMutex.withLock {
        if (prefs.getString("ms_resource_tenant", "") != FolderAccessPolicy.RESOURCE_TENANT) return@withLock null
        val access = prefs.getString(ACCESS, null)
        if (!access.isNullOrBlank() && System.currentTimeMillis() < prefs.getLong(EXPIRES, 0L)) return@withLock access
        val refresh = prefs.getString(REFRESH, null) ?: return@withLock null
        try {
            val result = tokenPost("client_id=" + encode(DEFAULT_CLIENT_ID) + "&grant_type=refresh_token" +
                "&refresh_token=" + encode(refresh))
            saveTokens(prefs, result)
            result.getString("access_token")
        } catch (_: Exception) { null }
        }
    }

    private fun graphJson(path: String, token: String, method: String = "GET", payload: JSONObject? = null): JSONObject {
        val conn = URL(GRAPH + path).openConnection() as HttpURLConnection
        try {
            conn.connectTimeout = 12000
            conn.readTimeout = 20000
            conn.instanceFollowRedirects = false
            conn.requestMethod = method
            conn.setRequestProperty("Authorization", "Bearer " + token)
            conn.setRequestProperty("Accept", "application/json")
            if (payload != null) {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json")
                conn.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
            }
            val code = conn.responseCode
            val text = (if (code in 200..299) conn.inputStream else conn.errorStream)?.bufferedReader()?.use { it.readText() } ?: "{}"
            val result = JSONObject(text)
            if (code !in 200..299) throw GraphException(code, result.optJSONObject("error")?.optString("message") ?: "Microsoft folder access failed (HTTP " + code + ").")
            return result
        } finally { conn.disconnect() }
    }

    private fun verifiedEmail(profile: JSONObject): String {
        require(profile.optString("id").isNotBlank()) { "Microsoft did not verify the account identity." }
        val email = profile.optString("mail").ifBlank { profile.optString("userPrincipalName") }.trim().lowercase()
        require(email.contains("@") && !email.contains(" ")) { "Microsoft did not return the account email." }
        return email
    }

    private fun folderPath(): String = "/drives/" + Uri.encode(folderConfig.getString("drive_id")) +
        "/items/" + Uri.encode(folderConfig.getString("folder_id"))

    private fun permissionMatches(profile: JSONObject, permission: JSONObject): Boolean {
        val roles = permission.optJSONArray("roles") ?: JSONArray()
        val people = mutableListOf<JSONObject>()
        for (key in listOf("grantedToV2", "grantedTo")) permission.optJSONObject(key)?.let { people.add(it) }
        for (key in listOf("grantedToIdentitiesV2", "grantedToIdentities")) {
            val values = permission.optJSONArray(key) ?: continue
            for (index in 0 until values.length()) values.optJSONObject(index)?.let { people.add(it) }
        }
        val link = permission.optJSONObject("link")
        val grant = FolderAccessPolicy.Grant(
            roles = (0 until roles.length()).map { roles.optString(it) },
            subjects = people.map { person -> FolderAccessPolicy.Subject(
                userId = person.optJSONObject("user")?.optString("id") ?: "",
                emails = listOf("user", "siteUser").flatMap { key ->
                    val identity = person.optJSONObject(key)
                    listOf(identity?.optString("email") ?: "", identity?.optString("loginName") ?: "")
                }, group = person.has("group") || person.has("siteGroup")) },
            hasLink = link != null, linkScope = link?.optString("scope") ?: "",
            inherited = permission.optJSONObject("inheritedFrom") != null,
            invitationEmail = permission.optJSONObject("invitation")?.optString("email") ?: "",
            expiration = permission.optString("expirationDateTime"))
        return FolderAccessPolicy.matches(profile.optString("id"), verifiedEmail(profile), grant)
    }

    private fun hasFolderScope(prefs: SharedPreferences): Boolean {
        return FolderAccessPolicy.hasWriteScope(prefs.getString(SCOPE, "") ?: "")
    }

    suspend fun refreshOperatorStatus(prefs: SharedPreferences): OperatorSyncResult = withContext(Dispatchers.IO) {
        if (OnlineScannerIdentity.enabled()) return@withContext OnlineScannerIdentity.status(prefs)
        statusMutex.withLock {
            if (!isConnected(prefs)) return@withLock OperatorSyncResult("NOT_SIGNED_IN", "Sign in with the Microsoft email approved by the owner.")
            if (listOf("drive_id", "folder_id", "owner_id").any { folderConfig.optString(it).isBlank() })
                return@withLock OperatorSyncResult("NOT_CONFIGURED", "The owner must connect the scanner folder and build the app from the access panel.")
            if (!hasFolderScope(prefs)) return@withLock OperatorSyncResult("SIGN_IN_REQUIRED", "Sign out and review Microsoft's shared-file consent when signing in again.")
            try {
                val token = getValidAccessToken(prefs) ?: return@withLock OperatorSyncResult("SIGN_IN_REQUIRED", "Microsoft sign-in expired. Sign in again.")
                val profile = graphJson("/me?" + "\u0024select=id,mail,userPrincipalName", token)
                val email = verifiedEmail(profile)
                prefs.edit().putString(EMAIL, email).putString("ms_user_id", profile.getString("id")).apply()
                val folder = graphJson(folderPath() + "?" + "\u0024select=id,folder,parentReference", token)
                require(folder.optString("id") == folderConfig.getString("folder_id") && folder.has("folder") &&
                    folder.optJSONObject("parentReference")?.optString("driveId") == folderConfig.getString("drive_id")) { "Microsoft returned a different scanner folder." }
                var approved = profile.getString("id") == folderConfig.getString("owner_id")
                if (!approved) {
                    var next: String? = folderPath() + "/permissions"
                    while (next != null && !approved) {
                        val page = graphJson(next, token)
                        val permissions = page.optJSONArray("value") ?: JSONArray()
                        approved = (0 until permissions.length()).any { index ->
                            permissions.optJSONObject(index)?.let { permissionMatches(profile, it) } == true
                        }
                        val link = page.optString("@odata.nextLink")
                        next = if (link.isBlank()) null else {
                            require(link.startsWith(GRAPH + "/")) { "Unexpected Microsoft permissions page." }
                            link.removePrefix(GRAPH)
                        }
                    }
                }
                val status = if (approved) "APPROVED" else "DENIED"
                prefs.edit().putString(STATUS, status).apply()
                OperatorSyncResult(status, if (approved) "Access granted to the ATTAIR scanner folder." else
                    "This Microsoft account is not individually approved for the scanner folder.")
            } catch (error: GraphException) {
                OperatorSyncResult(if (error.statusCode == 401) "SIGN_IN_REQUIRED" else if (error.statusCode in listOf(403, 404)) "DENIED" else "CONNECTION_ERROR",
                    error.message ?: "Microsoft could not confirm folder access.")
            } catch (error: Exception) {
                OperatorSyncResult("CONNECTION_ERROR", error.message ?: "Folder access could not be verified.")
            }
        }
    }

    fun getConnectedAccountId(prefs: SharedPreferences): String? = if (OnlineScannerIdentity.enabled()) OnlineScannerIdentity.account(prefs) else prefs.getString("ms_user_id", null)

    fun destination(): Pair<String, String>? {
        val drive = folderConfig.optString("drive_id")
        val folder = folderConfig.optString("folder_id")
        return if (drive.isNotBlank() && folder.isNotBlank()) drive to folder else null
    }
}
