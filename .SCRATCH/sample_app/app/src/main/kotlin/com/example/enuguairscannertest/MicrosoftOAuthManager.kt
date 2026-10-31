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
    const val SCOPES = "User.Read"

    const val DEFAULT_BACKEND_URL = "http://10.0.2.2:8000"
    private const val PREFS_KEY_BACKEND_URL = "backend_server_url"
    private const val PREFS_KEY_OPERATOR_STATUS = "operator_approval_status"

    private const val PREFS_KEY_ACCESS_TOKEN = "ms_access_token"
    private const val PREFS_KEY_REFRESH_TOKEN = "ms_refresh_token"
    private const val PREFS_KEY_EXPIRES_AT = "ms_token_expires_at"
    private const val PREFS_KEY_USER_EMAIL = "ms_user_email"
    private const val PREFS_KEY_CODE_VERIFIER = "ms_code_verifier"
    private const val PREFS_KEY_CUSTOM_CLIENT_ID = "ms_custom_client_id"

    fun getBackendUrl(prefs: SharedPreferences): String {
        val url = prefs.getString(PREFS_KEY_BACKEND_URL, null)
        return if (!url.isNullOrBlank()) url.trim().trimEnd('/') else DEFAULT_BACKEND_URL
    }

    fun setBackendUrl(prefs: SharedPreferences, url: String?) {
        prefs.edit().putString(PREFS_KEY_BACKEND_URL, url?.trim()?.trimEnd('/')).apply()
    }

    fun getOperatorStatus(prefs: SharedPreferences): String {
        val email = getConnectedEmail(prefs)
        if (email.equals("isaac.eke@attair.com.ng", ignoreCase = true)) return "APPROVED"
        return prefs.getString(PREFS_KEY_OPERATOR_STATUS, "PENDING") ?: "PENDING"
    }

    fun setOperatorStatus(prefs: SharedPreferences, status: String) {
        prefs.edit().putString(PREFS_KEY_OPERATOR_STATUS, status).apply()
    }

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
            .remove(PREFS_KEY_OPERATOR_STATUS)
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

            // Automatically register operator with backend
            val backendUrl = getBackendUrl(prefs)
            val operatorStatus = registerWithBackend(backendUrl, email)
            setOperatorStatus(prefs, operatorStatus)

            return@withContext Pair(true, "$email ($operatorStatus)")
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
    // 5. BACKEND UPLOAD PIPELINE (STREAMS DIRECTLY TO ISAAC EKE'S ONEDRIVE APPFOLDER)
    // -------------------------------------------------------------------------
    suspend fun uploadPdfToBackend(
        prefs: SharedPreferences,
        pdfFile: File,
        aircraftFolder: String,
        fileName: String,
        isPatch: Boolean
    ): Pair<Boolean, String> = withContext(Dispatchers.IO) {
        val email = getConnectedEmail(prefs) ?: return@withContext Pair(false, "Operator not signed in")
        val status = getOperatorStatus(prefs)
        if (status != "APPROVED" && !email.equals("isaac.eke@attair.com.ng", ignoreCase = true)) {
            return@withContext Pair(false, "Upload blocked: awaiting approval from Isaac Eke")
        }

        val backendUrl = getBackendUrl(prefs)
        val uploadUrl = "$backendUrl/api/scans/upload"

        try {
            val boundary = "==EnuguScanner${System.currentTimeMillis()}=="
            val conn = URL(uploadUrl).openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            conn.connectTimeout = 15000
            conn.readTimeout = 45000

            conn.outputStream.use { os ->
                writeFormField(os, boundary, "operator_email", email)
                writeFormField(os, boundary, "aircraft", aircraftFolder)
                writeFormField(os, boundary, "log_number", fileName)
                writeFormField(os, boundary, "is_patch", if (isPatch) "true" else "false")
                writeFileField(os, boundary, "file", fileName, pdfFile)
                os.write("--$boundary--\r\n".toByteArray(Charsets.UTF_8))
            }

            val respCode = conn.responseCode
            val respBody = (if (respCode in 200..299) conn.inputStream else conn.errorStream)?.bufferedReader()?.readText() ?: ""

            if (respCode in 200..299) {
                val json = JSONObject(respBody)
                val msg = json.optString("message", "Uploaded to Isaac Eke's OneDrive AppFolder")
                return@withContext Pair(true, msg)
            } else if (respCode == 403) {
                return@withContext Pair(false, "Upload blocked: awaiting approval from Isaac Eke")
            } else {
                return@withContext Pair(false, "Backend ($respCode): $respBody")
            }
        } catch (e: Exception) {
            e.printStackTrace()
            return@withContext Pair(false, "Connection to backend failed (${e.message ?: "network error"})")
        }
    }

    private fun registerWithBackend(backendUrl: String, email: String): String {
        try {
            val conn = URL("$backendUrl/api/auth/register").openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/json")
            conn.connectTimeout = 8000
            conn.readTimeout = 8000
            val json = JSONObject().apply {
                put("email", email)
                put("name", email.substringBefore("@"))
            }
            conn.outputStream.use { os ->
                os.write(json.toString().toByteArray(Charsets.UTF_8))
            }
            if (conn.responseCode in 200..299) {
                val resp = conn.inputStream.bufferedReader().readText()
                val respJson = JSONObject(resp)
                return respJson.optString("status", "PENDING")
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return if (email.equals("isaac.eke@attair.com.ng", ignoreCase = true)) "APPROVED" else "PENDING"
    }

    private fun writeFormField(os: java.io.OutputStream, boundary: String, name: String, value: String) {
        val header = "--$boundary\r\nContent-Disposition: form-data; name=\"$name\"\r\n\r\n$value\r\n"
        os.write(header.toByteArray(Charsets.UTF_8))
    }

    private fun writeFileField(os: java.io.OutputStream, boundary: String, name: String, filename: String, file: File) {
        val header = "--$boundary\r\nContent-Disposition: form-data; name=\"$name\"; filename=\"$filename\"\r\nContent-Type: application/pdf\r\n\r\n"
        os.write(header.toByteArray(Charsets.UTF_8))
        file.inputStream().use { it.copyTo(os) }
        os.write("\r\n".toByteArray(Charsets.UTF_8))
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
