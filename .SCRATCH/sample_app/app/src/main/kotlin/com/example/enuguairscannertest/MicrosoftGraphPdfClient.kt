package com.example.enuguairscannertest

import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.security.MessageDigest

/** The actual APK upload transport. JVM tests exercise it through local HTTP. */
class MicrosoftGraphPdfClient(private val driveId: String, private val rootFolderId: String,
                             private val accountId: String, private val token: String,
                             private val graphRoot: String = "https://graph.microsoft.com/v1.0") {
    init {
        require(graphRoot == "https://graph.microsoft.com/v1.0" || URL(graphRoot).host == "127.0.0.1")
        require(listOf(driveId, rootFolderId, accountId, token).all { it.isNotBlank() })
    }
    class Failure(val status: Int, message: String) : Exception(message)
    private fun path(id: String) = "/drives/" + encode(driveId) + "/items/" + encode(id)
    private fun encode(value: String) = URLEncoder.encode(value, "UTF-8").replace("+", "%20")

    fun upload(pdf: File, aircraft: String, name: String, patch: Boolean): ScanDeliveryReceipt {
        require(Regex("[A-Z0-9-]{2,16}").matches(aircraft) && name.endsWith(".pdf", true) &&
            name.length <= 200 && name.none { it in "\\/:*?\"<>|" || it.code < 32 }) { "Invalid PDF destination." }
        val size = pdf.length()
        require(size in 1..250L * 1024 * 1024) { "Invalid PDF size." }
        val me = json("/me?\u0024select=id")
        require(me.optString("id") == accountId) { "The pending PDF belongs to a different Microsoft account." }
        val root = json(path(rootFolderId) + "?\u0024select=id,folder,parentReference")
        require(root.optString("id") == rootFolderId && root.has("folder") &&
            root.optJSONObject("parentReference")?.optString("driveId") == driveId) { "Microsoft returned a different scanner folder." }
        var parentId = ensureFolder(rootFolderId, aircraft)
        if (patch) parentId = ensureFolder(parentId, "patches")
        val source = pdf.inputStream().use { FolderAccessPolicy.contentDigest(it, size) }
        val uploaded = json(path(parentId) + ":/" + encode(name) + ":/content", "PUT", file = pdf)
        requireItem(uploaded, name, size, parentId)
        val itemId = uploaded.getString("id")
        val observed = json(path(itemId) + "?\u0024select=id,name,size,file,parentReference")
        requireItem(observed, name, size, parentId)
        require(observed.optString("id") == itemId) { "Microsoft returned a different uploaded PDF." }
        val downloaded = downloadDigest(itemId, size)
        require(MessageDigest.isEqual(source, downloaded)) { "The PDF read back from Microsoft differs from the scan." }
        return ScanDeliveryReceipt(itemId, accountId, driveId, rootFolderId, parentId, name, size,
            source.joinToString("") { "%02x".format(it.toInt() and 255) }, System.currentTimeMillis())
    }

    private fun requireItem(item: JSONObject, name: String, size: Long, parentId: String) {
        val parent = item.optJSONObject("parentReference") ?: JSONObject()
        require(FolderAccessPolicy.uploadMatches(item.optString("id"), item.optString("name"), item.optLong("size", -1),
            item.has("file"), parent.optString("driveId"), parent.optString("id"), name, size, driveId, parentId)) {
            "Microsoft did not confirm the PDF's exact ATTAIR destination, name and size."
        }
    }

    private fun ensureFolder(parentId: String, name: String): String {
        val folder = try { json(path(parentId) + ":/" + encode(name) + "?\u0024select=id,name,folder,parentReference") }
        catch (error: Failure) {
            if (error.status != 404) throw error
            try {
                json(path(parentId) + "/children", "POST", JSONObject().put("name", name).put("folder", JSONObject())
                    .put("@microsoft.graph.conflictBehavior", "fail"))
            } catch (race: Failure) {
                if (race.status != 409) throw race
                json(path(parentId) + ":/" + encode(name))
            }
        }
        val parent = folder.optJSONObject("parentReference") ?: JSONObject()
        require(folder.optString("id").isNotBlank() && folder.optString("name") == name && folder.has("folder") &&
            parent.optString("driveId") == driveId && parent.optString("id") == parentId) { "Microsoft returned a different aircraft or patches folder." }
        return folder.getString("id")
    }

    private fun json(relative: String, method: String = "GET", body: JSONObject? = null, file: File? = null): JSONObject {
        val connection = connect(URL(graphRoot + relative), authenticated = true)
        try {
            connection.requestMethod = method
            connection.setRequestProperty("Accept", "application/json")
            if (file != null) {
                connection.doOutput = true
                connection.setFixedLengthStreamingMode(file.length())
                connection.setRequestProperty("Content-Type", "application/pdf")
                connection.outputStream.use { output -> file.inputStream().use { it.copyTo(output) } }
            } else if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val status = connection.responseCode
            val text = (if (status in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader()?.use { it.readText() } ?: "{}"
            val result = JSONObject(text)
            if (status !in 200..299) throw Failure(status, result.optJSONObject("error")?.optString("message") ?: "Microsoft request failed ($status).")
            return result
        } finally { connection.disconnect() }
    }

    private fun connect(url: URL, authenticated: Boolean): HttpURLConnection = (url.openConnection() as HttpURLConnection).apply {
        connectTimeout = 15000
        readTimeout = 60000
        instanceFollowRedirects = false
        if (authenticated) setRequestProperty("Authorization", "Bearer " + token)
    }

    private fun downloadDigest(itemId: String, size: Long): ByteArray {
        var connection = connect(URL(graphRoot + path(itemId) + "/content"), authenticated = true)
        try {
            if (connection.responseCode == 302) {
                val location = URL(connection.getHeaderField("Location"))
                require(location.protocol == "https" && location.userInfo == null) { "Unexpected Microsoft PDF download address." }
                connection.disconnect()
                connection = connect(location, authenticated = false)
                // Follow only bounded HTTPS redirects, and never forward the Graph bearer token.
                var redirects = 0
                while (connection.responseCode in listOf(301, 302, 303, 307, 308)) {
                    require(redirects++ < 5) { "Too many PDF download redirects." }
                    val next = URL(connection.url, connection.getHeaderField("Location"))
                    require(next.protocol == "https" && next.userInfo == null) { "Unexpected PDF download redirect." }
                    connection.disconnect()
                    connection = connect(next, authenticated = false)
                }
            }
            if (connection.responseCode != 200) throw Failure(connection.responseCode, "Microsoft could not read back the uploaded PDF.")
            return connection.inputStream.use { FolderAccessPolicy.contentDigest(it, size) }
        } finally { connection.disconnect() }
    }
}
