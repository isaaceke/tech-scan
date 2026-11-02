package com.example.enuguairscannertest

import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpServer
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.net.InetSocketAddress
import java.net.URLDecoder

/** Real APK transport against loopback fault injection. No live Microsoft identity. */
class MicrosoftGraphPdfClientTest {
    @get:Rule val temporary = TemporaryFolder()
    private lateinit var server: HttpServer
    private val files = linkedMapOf<String, Pair<JSONObject, ByteArray>>()
    private val folders = linkedMapOf<String, JSONObject>()
    private var puts = 0
    private var accountId = "synthetic-operator"
    private var permitted = true
    private var responseLostOnce = false
    private var corruptBytes = false
    private var wrongDrive = false
    private var folderConflictOnce = false

    @Before fun start() {
        server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        server.createContext("/v1.0") { exchange -> handle(exchange) }
        server.start()
    }
    @After fun stop() { server.stop(0) }
    private fun client() = MicrosoftGraphPdfClient("attair-drive", "scanner-root", "synthetic-operator", "synthetic-token",
        "http://127.0.0.1:${server.address.port}/v1.0")
    private fun queue() = ScanDeliveryStore(File(temporary.root, "pending"))
    private fun job(store: ScanDeliveryStore, patch: Boolean = false): ScanDeliveryJob {
        val pdf = File(temporary.root, "scan.pdf").apply { writeText("%PDF-1.4 synthetic PDF content") }
        return store.enqueue(pdf, "synthetic-operator", "operator@example.invalid", "attair-drive", "scanner-root", "LOG_001.pdf", "5N-ENO", patch)
    }
    private fun delivery(store: ScanDeliveryStore) = QueuedScanDelivery(store) { job, pdf -> client().upload(pdf, job.aircraft, job.remoteName, job.patch) }
    private fun send(exchange: HttpExchange, status: Int, value: Any) {
        val data = if (value is ByteArray) value else value.toString().toByteArray()
        exchange.sendResponseHeaders(status, data.size.toLong())
        exchange.responseBody.use { it.write(data) }
        exchange.close()
    }
    private fun item(id: String, name: String, parent: String, folder: Boolean): JSONObject = JSONObject().put("id", id).put("name", name)
        .put(if (folder) "folder" else "file", JSONObject())
        .put("parentReference", JSONObject().put("driveId", "attair-drive").put("id", parent))

    private fun handle(exchange: HttpExchange) {
        try {
            val path = URLDecoder.decode(exchange.requestURI.rawPath.removePrefix("/v1.0"), "UTF-8")
            val method = exchange.requestMethod
            val bytes = exchange.requestBody.use { it.readBytes() }
            assertEquals("Bearer synthetic-token", exchange.requestHeaders.getFirst("Authorization"))
            if (path == "/me") { send(exchange, 200, JSONObject().put("id", accountId)); return }
            if (!permitted) { send(exchange, 403, JSONObject().put("error", JSONObject().put("message", "Synthetic revoked permission"))); return }
            val prefix = "/drives/attair-drive/items/"
            if (path == prefix + "scanner-root") { send(exchange, 200, item("scanner-root", "scanner", "drive-root", true)); return }
            if (path.endsWith("/children") && method == "POST") {
                val parent = path.removePrefix(prefix).removeSuffix("/children")
                val name = JSONObject(String(bytes)).getString("name")
                val key = "$parent:/$name"
                val folder = item("folder-${folders.size}", name, parent, true)
                folders[key] = folder
                if (folderConflictOnce) {
                    folderConflictOnce = false
                    send(exchange, 409, JSONObject().put("error", JSONObject().put("message", "Synthetic folder race")))
                } else send(exchange, 201, folder)
                return
            }
            if (method == "PUT") {
                puts++
                val key = path.removePrefix(prefix).removeSuffix(":/content")
                val parent = key.substringBefore(":/")
                val name = key.substringAfter(":/")
                val id = files[key]?.first?.getString("id") ?: "pdf-${files.size}"
                val metadata = item(id, name, parent, false).put("size", bytes.size)
                files[key] = metadata to bytes
                if (responseLostOnce) {
                    responseLostOnce = false
                    send(exchange, 503, JSONObject().put("error", JSONObject().put("message", "Synthetic response lost after acceptance")))
                } else {
                    if (wrongDrive) metadata.getJSONObject("parentReference").put("driveId", "wrong-drive")
                    send(exchange, 201, metadata)
                }
                return
            }
            val relative = path.removePrefix(prefix)
            folders[relative]?.let { send(exchange, 200, it); return }
            val id = relative.removeSuffix("/content")
            val stored = files.values.firstOrNull { it.first.getString("id") == id }
            if (stored != null) {
                if (relative.endsWith("/content")) {
                    val content = stored.second.clone()
                    if (corruptBytes) content[0] = 0
                    send(exchange, 200, content)
                } else send(exchange, 200, stored.first)
                return
            }
            send(exchange, 404, JSONObject().put("error", JSONObject().put("message", "Synthetic item missing")))
        } catch (error: Throwable) {
            send(exchange, 500, JSONObject().put("error", JSONObject().put("message", error.message ?: "Synthetic handler error")))
        }
    }

    @Test fun actualUploadTransportCreatesFolderUploadsReadsBackAndCompletesJournal() {
        val store = queue()
        val job = job(store)
        assertTrue(delivery(store).deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
        assertEquals(1, puts)
        assertEquals(1, files.size)
        assertTrue(queue().snapshot().jobs.single().delivered)
        assertEquals(job.sha256, queue().snapshot().jobs.single().receipt!!.sha256)
    }
    @Test fun responseLostAfterServerAcceptanceRetriesSameFileAfterRestart() {
        val store = queue()
        val job = job(store)
        responseLostOnce = true
        assertFalse(delivery(store).deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
        assertTrue(queue().pdf(job).isFile)
        val restarted = queue()
        assertTrue(delivery(restarted).deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
        assertEquals(2, puts)
        assertEquals(1, files.size)
    }
    @Test fun corruptReadbackNeverCompletesOrDeletesPendingPdf() {
        val store = queue()
        val job = job(store)
        corruptBytes = true
        assertFalse(delivery(store).deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
        assertTrue(queue().pdf(job).isFile)
        assertFalse(queue().snapshot().jobs.single().delivered)
        corruptBytes = false
        assertTrue(delivery(queue()).deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
        assertEquals(1, files.size)
    }
    @Test fun wrongMicrosoftAccountCannotPerformAnyUpload() {
        val store = queue()
        val job = job(store)
        accountId = "different-microsoft-account"
        assertFalse(delivery(store).deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
        assertEquals(0, puts)
    }
    @Test fun revokedFolderPermissionCannotPerformAnyUpload() {
        val store = queue()
        val job = job(store)
        permitted = false
        assertFalse(delivery(store).deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
        assertEquals(0, puts)
        assertTrue(queue().pdf(job).exists())
    }
    @Test fun mismatchingDriveIsNotDeliveryProof() {
        val store = queue()
        val job = job(store)
        wrongDrive = true
        assertFalse(delivery(store).deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
        assertFalse(queue().snapshot().jobs.single().delivered)
        assertTrue(queue().pdf(job).exists())
    }
    @Test fun concurrentFolderCreationConflictResolvesToVerifiedFolder() {
        val store = queue()
        val job = job(store)
        folderConflictOnce = true
        assertTrue(delivery(store).deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
    }
    @Test fun patchPdfRemainsInsideAircraftPatchesFolder() {
        val store = queue()
        val job = job(store, patch = true)
        assertTrue(delivery(store).deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
        val aircraft = folders["scanner-root:/5N-ENO"]!!.getString("id")
        val patches = folders["$aircraft:/patches"]!!.getString("id")
        assertEquals(patches, store.snapshot().jobs.single().receipt!!.parentId)
    }
}
