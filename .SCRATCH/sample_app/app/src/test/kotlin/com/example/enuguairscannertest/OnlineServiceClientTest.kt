package com.example.enuguairscannertest

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

/** Actual native HTTP transport and journal, against synthetic loopback receipts. */
class OnlineServiceClientTest {
    @get:Rule val temporary = TemporaryFolder()
    private lateinit var server: HttpServer
    private lateinit var job: ScanDeliveryJob
    private var wrongAccount = false
    private var wrongDigest = false
    private var unavailable = false
    private var requests = 0
    @Before fun start() {
        server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        server.createContext("/api/scans/") { exchange ->
            requests++
            assertEquals("Bearer synthetic-service-session", exchange.requestHeaders.getFirst("Authorization"))
            assertEquals("application/pdf", exchange.requestHeaders.getFirst("Content-Type"))
            assertEquals(job.sha256, exchange.requestHeaders.getFirst("X-Scan-SHA256"))
            assertEquals(job.size, exchange.requestBody.use { it.readBytes().size.toLong() })
            val result = if (unavailable) JSONObject().put("error", "Synthetic service interruption") else JSONObject()
                .put("id", job.id).put("account_id", if (wrongAccount) "another-account" else job.accountId)
                .put("item_id", "verified-item").put("drive_id", job.driveId).put("root_folder_id", job.rootFolderId)
                .put("parent_id", "aircraft-folder").put("name", job.remoteName).put("size", job.size)
                .put("sha256", if (wrongDigest) "0".repeat(64) else job.sha256).put("verified_at", System.currentTimeMillis())
            val bytes = result.toString().toByteArray()
            exchange.responseHeaders.add("Content-Type", "application/json")
            exchange.sendResponseHeaders(if (unavailable) 503 else 200, bytes.size.toLong())
            exchange.responseBody.use { it.write(bytes) }; exchange.close()
        }
        server.start()
    }
    @After fun stop() { server.stop(0) }
    private fun store() = ScanDeliveryStore(File(temporary.root, "outbox"))
    private fun prepare(): ScanDeliveryStore {
        val pdf = File(temporary.root, "local.pdf").apply { writeText("%PDF-1.4 synthetic relay transport document") }
        val store = store()
        job = store.enqueue(pdf, "synthetic-account", "staff@example.invalid", "owner-drive", "owner-root", "LOG_001.pdf", "ENO", false)
        return store
    }
    private fun deliver(store: ScanDeliveryStore): Pair<Boolean, String> = QueuedScanDelivery(store) { pending, pdf ->
        OnlineServiceClient("http://127.0.0.1:${server.address.port}", "synthetic-service-session").upload(pending, pdf)
    }.deliver(job, job.accountId, job.driveId, job.rootFolderId)
    @Test fun verifiedServiceReceiptCompletesTheDurableNativeJournal() {
        val store = prepare(); assertTrue(deliver(store).first)
        assertTrue(store().snapshot().jobs.single().delivered)
        assertEquals(job.sha256, store().snapshot().jobs.single().receipt!!.sha256)
    }
    @Test fun interruptionRetainsPdfAndRecoversAfterJournalRestart() {
        val store = prepare(); unavailable = true
        assertFalse(deliver(store).first); assertTrue(store.pdf(job).isFile)
        unavailable = false; assertTrue(deliver(store()).first); assertEquals(2, requests)
    }
    @Test fun wrongAccountReceiptCannotCompleteOrDeleteRetainedPdf() {
        val store = prepare(); wrongAccount = true
        assertFalse(deliver(store).first); assertTrue(store.pdf(job).isFile)
        assertFalse(store().snapshot().jobs.single().delivered)
    }
    @Test fun wrongBytesReceiptCannotCompleteOrDeleteRetainedPdf() {
        val store = prepare(); wrongDigest = true
        assertFalse(deliver(store).first); assertTrue(store.pdf(job).isFile)
        assertFalse(store().snapshot().jobs.single().delivered)
    }
}
