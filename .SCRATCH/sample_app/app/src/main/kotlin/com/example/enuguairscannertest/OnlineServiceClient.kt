package com.example.enuguairscannertest

import org.json.JSONObject
import java.io.File
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/** Production relay transport; the durable outbox validates every returned receipt. */
class OnlineServiceClient(private val baseUrl: String, private val session: String? = null) {
    class Failure(val status: Int, message: String) : Exception(message)
    init {
        val url = URL(baseUrl)
        require((url.protocol == "https" || (url.protocol == "http" && url.host == "127.0.0.1")) &&
            url.userInfo == null && url.query == null && url.ref == null && url.path in listOf("", "/")) {
            "Invalid scanner service address."
        }
    }
    fun request(path: String, body: JSONObject? = null): JSONObject = send(path, if (body == null) "GET" else "POST", body)
    private fun send(path: String, method: String, body: JSONObject? = null, pdf: File? = null, digest: String? = null): JSONObject {
        require(path.startsWith("/") && !path.startsWith("//"))
        val connection = URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 15000
            connection.readTimeout = 180000
            connection.instanceFollowRedirects = false
            connection.requestMethod = method
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("User-Agent", "EnuguTechlogScanner/1.4")
            if (session != null) connection.setRequestProperty("Authorization", "Bearer " + session)
            if (pdf != null) {
                connection.doOutput = true
                connection.setFixedLengthStreamingMode(pdf.length())
                connection.setRequestProperty("Content-Type", "application/pdf")
                connection.setRequestProperty("X-Scan-SHA256", digest)
                connection.outputStream.use { output -> pdf.inputStream().use { it.copyTo(output) } }
            } else if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val status = connection.responseCode
            require(connection.getHeaderField("Content-Type")?.startsWith("application/json") == true) {
                "The scanner service returned an unexpected response (HTTP $status)."
            }
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val bytes = stream?.use { input ->
                val output = ByteArrayOutputStream()
                val buffer = ByteArray(4096)
                while (output.size() <= 65536) {
                    val count = input.read(buffer, 0, minOf(buffer.size, 65537 - output.size()))
                    if (count < 0) break
                    output.write(buffer, 0, count)
                }
                output.toByteArray()
            } ?: ByteArray(0)
            require(bytes.size <= 65536) { "The scanner service response is too large." }
            val result = JSONObject(String(bytes, Charsets.UTF_8))
            if (status !in 200..299) throw Failure(status, result.optString("error", "Scanner service request failed (HTTP $status)."))
            return result
        } finally { connection.disconnect() }
    }
    fun upload(job: ScanDeliveryJob, pdf: File): ScanDeliveryReceipt {
        require(pdf.length() == job.size && job.size in 1..32L * 1024 * 1024) { "The online service accepts PDFs up to 32 MB. The local PDF remains saved." }
        val encode: (String) -> String = { URLEncoder.encode(it, "UTF-8").replace("+", "%20") }
        val result = send("/api/scans/" + encode(job.id) + "?name=" + encode(job.remoteName) +
            "&aircraft=" + encode(job.aircraft) + "&patch=" + job.patch, "PUT", pdf = pdf, digest = job.sha256)
        val receipt = ScanDeliveryReceipt(result.getString("item_id"), result.getString("account_id"),
            result.getString("drive_id"), result.getString("root_folder_id"), result.getString("parent_id"),
            result.getString("name"), result.getLong("size"), result.getString("sha256"), result.getLong("verified_at"))
        require(result.optString("id") == job.id && receipt.accountId == job.accountId && receipt.driveId == job.driveId &&
            receipt.rootFolderId == job.rootFolderId && receipt.name == job.remoteName && receipt.size == job.size &&
            receipt.sha256 == job.sha256 && receipt.itemId.isNotBlank() && receipt.parentId.isNotBlank() && receipt.verifiedAt > 0) {
            "The service receipt does not match this saved PDF and its destination."
        }
        return receipt
    }
}
