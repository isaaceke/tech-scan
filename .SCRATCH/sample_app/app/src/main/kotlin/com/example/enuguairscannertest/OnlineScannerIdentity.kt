package com.example.enuguairscannertest

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.URL
import java.util.concurrent.atomic.AtomicLong

/** Microsoft codes are redeemed by the online service, never by an operator's storage client. */
object OnlineScannerIdentity {
    private const val SESSION = "relay_access_session"
    private const val EXPIRES = "relay_session_expires_at"
    private const val EMAIL = "relay_account_email"
    private const val ACCOUNT = "relay_account_id"
    private const val STATE = "relay_auth_state"
    private const val SECRET = "relay_auth_device_secret"
    private const val PROVIDER = "relay_auth_provider"
    private var config = JSONObject()
    private var destination = JSONObject()
    private val generation = AtomicLong()
    fun initialize(context: Context) {
        config = context.assets.open("scanner_service.json").bufferedReader().use { JSONObject(it.readText()) }
        destination = context.assets.open("scanner_folder.json").bufferedReader().use { JSONObject(it.readText()) }
    }
    fun enabled() = config.optString("mode") == "online"
    fun serverUrl(): String {
        val value = config.optString("server_url").trimEnd('/')
        require(value.isNotBlank()) { "Online scanner service setup is incomplete." }
        val url = URL(value)
        require(url.protocol == "https" && url.userInfo == null && url.query == null && url.ref == null && url.path.isBlank()) {
            "Online scanner service setup is invalid."
        }
        return value
    }
    fun connected(prefs: SharedPreferences) = !prefs.getString(SESSION, null).isNullOrBlank()
    fun email(prefs: SharedPreferences): String? = prefs.getString(EMAIL, null)
    fun account(prefs: SharedPreferences): String? = prefs.getString(ACCOUNT, null)
    fun bearer(prefs: SharedPreferences): String? = if (System.currentTimeMillis() < prefs.getLong(EXPIRES, 0)) prefs.getString(SESSION, null) else null
    fun cancel(prefs: SharedPreferences) { generation.incrementAndGet(); prefs.edit().remove(STATE).remove(SECRET).remove(PROVIDER).apply() }
    fun disconnect(prefs: SharedPreferences) {
        prefs.edit().remove(SESSION).remove(EXPIRES).remove(EMAIL).remove(ACCOUNT).remove(STATE).remove(SECRET).remove(PROVIDER).apply()
    }
    suspend fun startSignIn(context: Context, prefs: SharedPreferences) {
        val requestGeneration = generation.incrementAndGet()
        val result = withContext(Dispatchers.IO) { OnlineServiceClient(serverUrl()).request("/api/auth/start", JSONObject()) }
        if (generation.get() != requestGeneration) return
        val state = result.getString("state")
        val secret = result.getString("device_secret")
        val uri = Uri.parse(result.getString("authorization_url"))
        require(uri.scheme == "https" && uri.host == "login.microsoftonline.com" && uri.path == "/common/oauth2/v2.0/authorize" &&
            uri.getQueryParameter("state") == state && uri.getQueryParameter("client_id") == MicrosoftOAuthManager.DEFAULT_CLIENT_ID &&
            uri.getQueryParameter("redirect_uri") == MicrosoftOAuthManager.REDIRECT_URI &&
            uri.getQueryParameter("scope")?.split(' ')?.toSet() == setOf("User.Read", "offline_access") &&
            state.matches(Regex("[A-Za-z0-9_-]{43}")) && secret.matches(Regex("[A-Za-z0-9_-]{43}"))) { "The online service returned an unexpected sign-in request." }
        require(prefs.edit().putString(STATE, state).putString(SECRET, secret).putString(PROVIDER, "microsoft").commit()) { "Cannot save the sign-in request on this phone." }
        withContext(Dispatchers.Main) {
            if (generation.get() == requestGeneration) CustomTabsIntent.Builder().setShowTitle(true).build().launchUrl(context, uri)
        }
    }
    suspend fun startGoogleSignIn(context: Context, prefs: SharedPreferences) {
        val requestGeneration = generation.incrementAndGet()
        val result = withContext(Dispatchers.IO) {
            OnlineServiceClient(serverUrl()).request("/api/auth/google/start", JSONObject().put("callback_mode", "web"))
        }
        if (generation.get() != requestGeneration) return
        val state = result.getString("state")
        val secret = result.getString("device_secret")
        val uri = Uri.parse(result.getString("authorization_url"))
        require(uri.scheme == "https" && uri.host == "accounts.google.com" && uri.path == "/o/oauth2/v2/auth" &&
            uri.getQueryParameter("state") == state &&
            state.matches(Regex("[A-Za-z0-9_-]{43}")) && secret.matches(Regex("[A-Za-z0-9_-]{43}"))) {
            "The online service returned an unexpected Google sign-in request."
        }
        require(prefs.edit().putString(STATE, state).putString(SECRET, secret).putString(PROVIDER, "google").commit()) {
            "Cannot save the sign-in request on this phone."
        }
        withContext(Dispatchers.Main) {
            if (generation.get() == requestGeneration) CustomTabsIntent.Builder().setShowTitle(true).build().launchUrl(context, uri)
        }
    }
    suspend fun finish(intent: Intent, prefs: SharedPreferences): Pair<Boolean, String> = withContext(Dispatchers.IO) {
        try {
            val uri = intent.data ?: return@withContext false to "No sign-in response."
            val state = prefs.getString(STATE, null)
            val secret = prefs.getString(SECRET, null)
            val provider = prefs.getString(PROVIDER, "microsoft")
            require(uri.scheme == "techlogscan" && uri.host == "auth") { "Sign-in response did not match this app." }

            if (uri.getQueryParameter("error") != null) {
                cancel(prefs)
                return@withContext false to FolderAccessPolicy.signInError(
                    uri.getQueryParameter("error_description") ?: uri.getQueryParameter("error") ?: "Sign-in was declined."
                )
            }

            val sessionToken = uri.getQueryParameter("session_token")
            if (!sessionToken.isNullOrBlank()) {
                val email = uri.getQueryParameter("email") ?: ""
                val accountId = uri.getQueryParameter("account_id") ?: email
                val expiresAt = uri.getQueryParameter("expires_at")?.toLongOrNull() ?: (System.currentTimeMillis() + 30L * 86400000L)
                cancel(prefs)
                require(email.contains('@') && sessionToken.matches(Regex("[A-Za-z0-9_-]{43}")) && expiresAt > System.currentTimeMillis()) {
                    "The online service did not confirm sign-in."
                }
                disconnect(prefs)
                require(prefs.edit().putString(SESSION, sessionToken).putLong(EXPIRES, expiresAt)
                    .putString(EMAIL, email).putString(ACCOUNT, accountId).commit()) {
                    "Cannot retain the scanner sign-in on this phone."
                }
                return@withContext true to email
            }

            require(!state.isNullOrBlank() && !secret.isNullOrBlank() && uri.getQueryParameter("state") == state) {
                "Sign-in response did not match this phone."
            }
            cancel(prefs)
            val code = uri.getQueryParameter("code") ?: return@withContext false to "Authentication service did not return a sign-in code."
            val endpoint = if (provider == "google") "/api/auth/google/finish" else "/api/auth/finish"
            val result = OnlineServiceClient(serverUrl()).request(
                endpoint,
                JSONObject().put("state", state).put("device_secret", secret).put("code", code)
            )
            checkDestination(result.getJSONObject("destination"))
            val profile = result.getJSONObject("profile")
            val token = result.getString("session_token")
            require(profile.getString("id").isNotBlank() && profile.getString("email").contains('@') &&
                token.matches(Regex("[A-Za-z0-9_-]{43}")) && result.getLong("expires_at") > System.currentTimeMillis()) {
                "The online service did not confirm sign-in."
            }
            disconnect(prefs)
            require(prefs.edit().putString(SESSION, token).putLong(EXPIRES, result.getLong("expires_at"))
                .putString(EMAIL, profile.getString("email")).putString(ACCOUNT, profile.getString("id")).commit()) {
                "Cannot retain the scanner sign-in on this phone."
            }
            true to profile.getString("email")
        } catch (error: Exception) { false to (error.message ?: "Sign-in did not complete.") }
    }
    private fun checkDestination(observed: JSONObject) {
        require(listOf("drive_id", "folder_id", "owner_id").all { observed.optString(it).isNotBlank() && observed.optString(it) == destination.optString(it) }) {
            "The online service addresses a different scanner folder."
        }
    }
    suspend fun status(prefs: SharedPreferences): MicrosoftOAuthManager.OperatorSyncResult = withContext(Dispatchers.IO) {
        if (!connected(prefs)) return@withContext MicrosoftOAuthManager.OperatorSyncResult("NOT_SIGNED_IN", "Sign in with the Microsoft or Google email approved in the owner panel.")
        val token = bearer(prefs) ?: return@withContext MicrosoftOAuthManager.OperatorSyncResult("SIGN_IN_REQUIRED", "Sign in again to reconnect your scanner account.")
        try {
            val result = OnlineServiceClient(serverUrl(), token).request("/api/auth/status")
            checkDestination(result.getJSONObject("destination"))
            val profile = result.getJSONObject("profile")
            require(profile.optString("id") == account(prefs) && profile.optString("email") == email(prefs)) { "The service returned a different operator account." }
            val status = result.getString("status")
            require(status in listOf("APPROVED", "DENIED", "NOT_CONFIGURED")) { "Invalid scanner access status." }
            MicrosoftOAuthManager.OperatorSyncResult(status, result.optString("message"))
        } catch (error: OnlineServiceClient.Failure) {
            MicrosoftOAuthManager.OperatorSyncResult(if (error.status == 401) "SIGN_IN_REQUIRED" else if (error.status == 403) "DENIED" else "CONNECTION_ERROR", error.message)
        } catch (error: Exception) { MicrosoftOAuthManager.OperatorSyncResult("CONNECTION_ERROR", error.message ?: "The online scanner service is unreachable.") }
    }
}
