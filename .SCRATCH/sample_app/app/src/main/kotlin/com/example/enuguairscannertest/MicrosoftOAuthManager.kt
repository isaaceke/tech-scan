package com.example.enuguairscannertest

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.util.Base64
import androidx.browser.customtabs.CustomTabsIntent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.security.MessageDigest
import java.security.SecureRandom

object MicrosoftOAuthManager {

    // Microsoft multi-tenant public client ID (or configured custom client ID)
    const val DEFAULT_CLIENT_ID = "dc7101d3-3bb7-462f-92e8-374958f4ddb5"
    const val REDIRECT_URI = "techlogscan://auth"
    const val SCOPES = "offline_access Files.ReadWrite User.Read"

    private const val PREFS_KEY_ACCESS_TOKEN = "ms_access_token"
    private const val PREFS_KEY_REFRESH_TOKEN = "ms_refresh_token"
    private const val PREFS_KEY_EXPIRES_AT = "ms_token_expires_at"
    private const val PREFS_KEY_USER_EMAIL = "ms_user_email"
    private const val PREFS_KEY_CODE_VERIFIER = "ms_code_verifier"
    private const val PREFS_KEY_CUSTOM_CLIENT_ID = "ms_custom_client_id"

    fun getClientId(prefs: SharedPreferences): String {
        val custom = prefs.getString(PREFS_KEY_CUSTOM_CLIENT_ID, null)
        return if (!custom.isNullOrBlank() && custom != "d3590ed6-52b3-4102-aeff-aad2292ab01c") custom.trim() else DEFAULT_CLIENT_ID
    }

    fun setCustomClientId(prefs: SharedPreferences, id: String?) {
        prefs.edit().putString(PREFS_KEY_CUSTOM_CLIENT_ID, id?.trim()).apply()
    }

    fun isConnected(prefs: SharedPreferences): Boolean {
        return !prefs.getString(PREFS_KEY_REFRESH_TOKEN, null).isNullOrBlank()
    }

    fun getConnectedEmail(prefs: SharedPreferences): String? {
        return prefs.getString(PREFS_KEY_USER_EMAIL, null)
    }

    fun disconnect(prefs: SharedPreferences) {
        prefs.edit()
            .remove(PREFS_KEY_ACCESS_TOKEN)
            .remove(PREFS_KEY_REFRESH_TOKEN)
            .remove(PREFS_KEY_EXPIRES_AT)
            .remove(PREFS_KEY_USER_EMAIL)
            .remove(PREFS_KEY_CODE_VERIFIER)
            .apply()
    }

    // -------------------------------------------------------------------------
    // 1. PKCE GENERATION
    // -------------------------------------------------------------------------
    private fun generateCodeVerifier(): String {
        val bytes = ByteArray(48)
        SecureRandom().nextBytes(bytes)
        return Base64.encodeToString(bytes, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
    }

    private fun generateCodeChallenge(verifier: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(verifier.toByteArray(Charsets.US_ASCII))
        return Base64.encodeToString(digest, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
    }

    // -------------------------------------------------------------------------
    // 2. LAUNCH SIGN-IN VIA CHROME CUSTOM TABS (SSO 1-TAP PICKER)
    // -------------------------------------------------------------------------
    fun startSignIn(context: Context, prefs: SharedPreferences) {
        val verifier = generateCodeVerifier()
        val challenge = generateCodeChallenge(verifier)

        prefs.edit().putString(PREFS_KEY_CODE_VERIFIER, verifier).apply()

        val clientId = getClientId(prefs)
        val authUrl = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?" +
                "client_id=${URLEncoder.encode(clientId, "UTF-8")}" +
                "&response_type=code" +
                "&redirect_uri=${URLEncoder.encode(REDIRECT_URI, "UTF-8")}" +
                "&response_mode=query" +
                "&scope=${URLEncoder.encode(SCOPES, "UTF-8")}" +
                "&code_challenge=${URLEncoder.encode(challenge, "UTF-8")}" +
                "&code_challenge_method=S256" +
                "&prompt=select_account"

        val customTabsIntent = CustomTabsIntent.Builder()
            .setShowTitle(true)
            .build()

        customTabsIntent.launchUrl(context, Uri.parse(authUrl))
    }

    // -------------------------------------------------------------------------
    // 3. HANDLE DEEP LINK REDIRECT (techlogscan://auth?code=...)
    // -------------------------------------------------------------------------
    suspend fun handleAuthRedirect(
        intent: Intent,
        prefs: SharedPreferences
    ): Pair<Boolean, String> = withContext(Dispatchers.IO) {
        val data = intent.data ?: return@withContext Pair(false, "No redirect data")
        if (data.scheme != "techlogscan" || data.host != "auth") {
            return@withContext Pair(false, "Unknown scheme")
        }

        val error = data.getQueryParameter("error")
        val errorDescription = data.getQueryParameter("error_description")
        if (error != null) {
            return@withContext Pair(false, errorDescription ?: error)
        }

        val code = data.getQueryParameter("code") ?: return@withContext Pair(false, "No auth code returned")
        val verifier = prefs.getString(PREFS_KEY_CODE_VERIFIER, null)
            ?: return@withContext Pair(false, "Missing code verifier")

        val clientId = getClientId(prefs)

        try {
            val tokenUrl = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            val postData = "client_id=${URLEncoder.encode(clientId, "UTF-8")}" +
                    "&grant_type=authorization_code" +
                    "&code=${URLEncoder.encode(code, "UTF-8")}" +
                    "&redirect_uri=${URLEncoder.encode(REDIRECT_URI, "UTF-8")}" +
                    "&code_verifier=${URLEncoder.encode(verifier, "UTF-8")}"

            val (codeStatus, responseText) = executeHttpPost(tokenUrl, postData)
            if (codeStatus !in 200..299) {
                return@withContext Pair(false, "Token error ($codeStatus): $responseText")
            }

            val json = JSONObject(responseText)
            val accessToken = json.getString("access_token")
            val refreshToken = json.getString("refresh_token")
            val expiresIn = json.optLong("expires_in", 3600L)
            val expiresAt = System.currentTimeMillis() + (expiresIn - 300) * 1000

            prefs.edit()
                .putString(PREFS_KEY_ACCESS_TOKEN, accessToken)
                .putString(PREFS_KEY_REFRESH_TOKEN, refreshToken)
                .putLong(PREFS_KEY_EXPIRES_AT, expiresAt)
                .apply()

            // Fetch user identity from Graph /me
            val email = fetchUserEmail(accessToken) ?: "Microsoft Account"
            prefs.edit().putString(PREFS_KEY_USER_EMAIL, email).apply()

            return@withContext Pair(true, email)
        } catch (e: Exception) {
            e.printStackTrace()
            return@withContext Pair(false, e.message ?: "Authentication failed")
        }
    }

    // -------------------------------------------------------------------------
    // 4. AUTOMATIC BACKGROUND TOKEN REFRESH
    // -------------------------------------------------------------------------
    suspend fun getValidAccessToken(prefs: SharedPreferences): String? = withContext(Dispatchers.IO) {
        val refreshToken = prefs.getString(PREFS_KEY_REFRESH_TOKEN, null) ?: return@withContext null
        val expiresAt = prefs.getLong(PREFS_KEY_EXPIRES_AT, 0L)
        val currentAccessToken = prefs.getString(PREFS_KEY_ACCESS_TOKEN, null)

        if (!currentAccessToken.isNullOrBlank() && System.currentTimeMillis() < expiresAt) {
            return@withContext currentAccessToken
        }

        // Token expired or close to expiration -> Auto refresh with zero user intervention!
        val clientId = getClientId(prefs)
        try {
            val tokenUrl = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            val postData = "client_id=${URLEncoder.encode(clientId, "UTF-8")}" +
                    "&grant_type=refresh_token" +
                    "&refresh_token=${URLEncoder.encode(refreshToken, "UTF-8")}" +
                    "&scope=${URLEncoder.encode(SCOPES, "UTF-8")}"

            val (status, responseText) = executeHttpPost(tokenUrl, postData)
            if (status in 200..299) {
                val json = JSONObject(responseText)
                val newAccessToken = json.getString("access_token")
                val newRefreshToken = json.optString("refresh_token", refreshToken)
                val expiresIn = json.optLong("expires_in", 3600L)
                val newExpiresAt = System.currentTimeMillis() + (expiresIn - 300) * 1000

                prefs.edit()
                    .putString(PREFS_KEY_ACCESS_TOKEN, newAccessToken)
                    .putString(PREFS_KEY_REFRESH_TOKEN, newRefreshToken)
                    .putLong(PREFS_KEY_EXPIRES_AT, newExpiresAt)
                    .apply()

                return@withContext newAccessToken
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }

        return@withContext currentAccessToken
    }

    private fun fetchUserEmail(accessToken: String): String? {
        try {
            val conn = URL("https://graph.microsoft.com/v1.0/me").openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.setRequestProperty("Authorization", "Bearer $accessToken")
            conn.setRequestProperty("Accept", "application/json")
            if (conn.responseCode in 200..299) {
                val body = conn.inputStream.bufferedReader().readText()
                val json = JSONObject(body)
                return json.optString("userPrincipalName").ifBlank {
                    json.optString("mail").ifBlank {
                        json.optString("displayName").ifBlank { null }
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return null
    }

    // -------------------------------------------------------------------------
    // 5. DIRECT GRAPH API UPLOAD TO SPLIT/<AIRCRAFT>/<FILENAME>.pdf
    // -------------------------------------------------------------------------
    suspend fun uploadPdfToSharePoint(
        prefs: SharedPreferences,
        pdfFile: File,
        aircraftFolder: String,
        fileName: String
    ): Pair<Boolean, String> = withContext(Dispatchers.IO) {
        val accessToken = getValidAccessToken(prefs)
            ?: return@withContext Pair(false, "Not connected to Microsoft")

        val fileBytes = pdfFile.readBytes()

        try {
            // First Attempt: Target /me/drive/root:/SPLIT/{aircraft}/{fileName}:/content
            val encodedDirectPath = Uri.encode("SPLIT/$aircraftFolder/$fileName", "/")
            val directUrl = "https://graph.microsoft.com/v1.0/me/drive/root:/$encodedDirectPath:/content"

            val (directStatus, directResp) = executeHttpPut(directUrl, accessToken, fileBytes)
            if (directStatus in 200..299) {
                return@withContext Pair(true, "Uploaded to SPLIT/$aircraftFolder on SharePoint!")
            }

            // Second Attempt: If SPLIT is in "Shared With Me" (Isaac Eke shared it with this user)
            val sharedWithMeUrl = "https://graph.microsoft.com/v1.0/me/drive/sharedWithMe"
            val (sharedStatus, sharedBody) = executeHttpGet(sharedWithMeUrl, accessToken)
            if (sharedStatus in 200..299) {
                val sharedJson = JSONObject(sharedBody)
                val valueArray = sharedJson.optJSONArray("value")
                if (valueArray != null) {
                    for (i in 0 until valueArray.length()) {
                        val item = valueArray.getJSONObject(i)
                        val name = item.optString("name")
                        if (name.equals("SPLIT", ignoreCase = true)) {
                            val remoteItem = item.optJSONObject("remoteItem")
                            val remoteDriveId = remoteItem?.optJSONObject("parentReference")?.optString("driveId")
                            val remoteFolderId = remoteItem?.optString("id")

                            if (!remoteDriveId.isNullOrBlank() && !remoteFolderId.isNullOrBlank()) {
                                val encodedSharedPath = Uri.encode("$aircraftFolder/$fileName", "/")
                                val sharedTargetUrl = "https://graph.microsoft.com/v1.0/drives/$remoteDriveId/items/$remoteFolderId:/$encodedSharedPath:/content"
                                val (targetStatus, targetResp) = executeHttpPut(sharedTargetUrl, accessToken, fileBytes)
                                if (targetStatus in 200..299) {
                                    return@withContext Pair(true, "Uploaded to shared SPLIT/$aircraftFolder on SharePoint!")
                                }
                            }
                        }
                    }
                }
            }

            return@withContext Pair(false, "SharePoint upload error ($directStatus): $directResp")
        } catch (e: Exception) {
            e.printStackTrace()
            return@withContext Pair(false, e.message ?: "Upload failed")
        }
    }

    // -------------------------------------------------------------------------
    // HTTP UTILITIES
    // -------------------------------------------------------------------------
    private fun executeHttpPost(urlString: String, postData: String): Pair<Int, String> {
        val conn = URL(urlString).openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
        conn.outputStream.use { os ->
            os.write(postData.toByteArray(Charsets.UTF_8))
        }
        val status = conn.responseCode
        val stream = if (status in 200..299) conn.inputStream else conn.errorStream
        val text = stream?.bufferedReader()?.readText() ?: ""
        return Pair(status, text)
    }

    private fun executeHttpGet(urlString: String, token: String): Pair<Int, String> {
        val conn = URL(urlString).openConnection() as HttpURLConnection
        conn.requestMethod = "GET"
        conn.setRequestProperty("Authorization", "Bearer $token")
        conn.setRequestProperty("Accept", "application/json")
        val status = conn.responseCode
        val stream = if (status in 200..299) conn.inputStream else conn.errorStream
        val text = stream?.bufferedReader()?.readText() ?: ""
        return Pair(status, text)
    }

    private fun executeHttpPut(urlString: String, token: String, body: ByteArray): Pair<Int, String> {
        val conn = URL(urlString).openConnection() as HttpURLConnection
        conn.requestMethod = "PUT"
        conn.doOutput = true
        conn.setRequestProperty("Authorization", "Bearer $token")
        conn.setRequestProperty("Content-Type", "application/pdf")
        conn.outputStream.use { os ->
            os.write(body)
        }
        val status = conn.responseCode
        val stream = if (status in 200..299) conn.inputStream else conn.errorStream
        val text = stream?.bufferedReader()?.readText() ?: ""
        return Pair(status, text)
    }
}
