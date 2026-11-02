package com.example.enuguairscannertest

import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

class ScanDeliveryStoreTest {
    @get:Rule val temporary = TemporaryFolder()
    private fun store() = ScanDeliveryStore(File(temporary.root, "queue"))
    private fun pdf() = File(temporary.root, "original.pdf").apply { writeBytes("%PDF-1.4 retained test PDF".toByteArray()) }
    private fun enqueue(store: ScanDeliveryStore) = store.enqueue(pdf(), "operator-id", "operator@example.invalid", "drive", "root", "LOG_001.pdf", "5N-ENO", false)
    private fun receipt(job: ScanDeliveryJob) = ScanDeliveryReceipt("cloud-item", job.accountId, job.driveId, job.rootFolderId,
        "aircraft-folder", job.remoteName, job.size, job.sha256, 1000)

    @Test fun restartRecoversPendingPdfAfterOriginalFileIsGone() {
        val initial = store()
        val job = enqueue(initial)
        File(temporary.root, "original.pdf").delete()
        val recovered = store()
        assertEquals(job, recovered.snapshot().jobs.single())
        assertEquals(job.sha256, ScanDeliveryStore.digest(recovered.pdf(job), job.size))
    }
    @Test fun noReceiptKeepsPdfRetryableAcrossRestart() {
        val initial = store()
        val job = enqueue(initial)
        val delivery = QueuedScanDelivery(initial) { _, _ -> throw IllegalStateException("Synthetic connection lost") }
        assertFalse(delivery.deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
        val recovered = store()
        assertFalse(recovered.snapshot().jobs.single().delivered)
        assertTrue(recovered.pdf(job).isFile)
    }
    @Test fun matchingReceiptIsPersistedBeforePendingBytesAreRemoved() {
        val initial = store()
        val job = enqueue(initial)
        initial.delivered(job, receipt(job))
        val recovered = store().snapshot().jobs.single()
        assertTrue(recovered.delivered)
        assertEquals(receipt(job), recovered.receipt)
        assertFalse(File(File(temporary.root, "queue/${job.id}"), "scan.pdf").exists())
    }
    @Test fun wrongAccountCannotSendAnOldAccountsPendingScan() {
        val initial = store()
        val job = enqueue(initial)
        var uploads = 0
        val delivery = QueuedScanDelivery(initial) { j, _ -> uploads++; receipt(j) }
        assertFalse(delivery.deliver(job, "different-account", job.driveId, job.rootFolderId).first)
        assertEquals(0, uploads)
        assertTrue(initial.pdf(job).exists())
    }
    @Test fun changedDestinationCannotRedirectRetainedScan() {
        val initial = store()
        val job = enqueue(initial)
        var uploads = 0
        val delivery = QueuedScanDelivery(initial) { j, _ -> uploads++; receipt(j) }
        assertFalse(delivery.deliver(job, job.accountId, "other-drive", job.rootFolderId).first)
        assertFalse(delivery.deliver(job, job.accountId, job.driveId, "other-folder").first)
        assertEquals(0, uploads)
    }
    @Test fun incorrectReceiptsNeverDeleteRetainedBytes() {
        val initial = store()
        val job = enqueue(initial)
        for (bad in listOf(receipt(job).copy(accountId = "wrong"), receipt(job).copy(driveId = "wrong"),
            receipt(job).copy(rootFolderId = "wrong"), receipt(job).copy(sha256 = "wrong"), receipt(job).copy(name = "wrong.pdf"))) {
            try { initial.delivered(job, bad); fail("Incorrect receipt was accepted") } catch (_: IllegalArgumentException) { }
            assertTrue(initial.pdf(job).isFile)
        }
    }
    @Test fun requeueingSamePendingPdfUsesItsOriginalStableFilename() {
        val initial = store()
        val first = enqueue(initial)
        val second = enqueue(initial)
        assertEquals(first.id, second.id)
        assertEquals(first.remoteName, second.remoteName)
        assertEquals(1, initial.snapshot().jobs.size)
    }
    @Test fun distinctScansHaveDistinctCloudNames() {
        val initial = store()
        val first = enqueue(initial)
        initial.delivered(first, receipt(first))
        val next = enqueue(initial)
        assertNotEquals(first.remoteName, next.remoteName)
        assertTrue(next.remoteName.startsWith("LOG_001__"))
    }
    @Test fun changingOriginalCannotChangeRetainedUploadBytes() {
        val initial = store()
        val job = enqueue(initial)
        File(temporary.root, "original.pdf").writeText("A different document")
        assertEquals(job.sha256, ScanDeliveryStore.digest(initial.pdf(job), job.size))
    }
    @Test fun corruptedPrivatePdfIsNotSentAndIsNotDeleted() {
        val initial = store()
        val job = enqueue(initial)
        val retained = File(temporary.root, "queue/${job.id}/scan.pdf")
        retained.writeText("damaged")
        var uploads = 0
        val delivery = QueuedScanDelivery(initial) { j, _ -> uploads++; receipt(j) }
        assertFalse(delivery.deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
        assertEquals(0, uploads)
        assertTrue(retained.exists())
    }
    @Test fun incompleteStateWriteUsesPreviousCompleteJournal() {
        val initial = store()
        val job = enqueue(initial)
        initial.failed(job, "Original retry error")
        File(temporary.root, "queue/${job.id}/record-999-incomplete.properties").writeText("incomplete=true")
        assertEquals("Original retry error", store().snapshot().jobs.single().lastError)
        assertTrue(store().pdf(job).exists())
    }
    @Test fun unreadableJournalNeverAppearsAsDelivered() {
        val initial = store()
        val job = enqueue(initial)
        File(temporary.root, "queue/${job.id}").listFiles()!!.filter { it.extension == "properties" }.forEach { it.writeText("damaged") }
        assertEquals(1, store().snapshot().unreadable)
        assertTrue(File(temporary.root, "queue/${job.id}/scan.pdf").exists())
    }
    @Test fun completedJobDoesNotUploadAgain() {
        val initial = store()
        val job = enqueue(initial)
        initial.delivered(job, receipt(job))
        val delivery = QueuedScanDelivery(initial) { _, _ -> error("Completed PDF was uploaded twice") }
        assertTrue(delivery.deliver(job, job.accountId, job.driveId, job.rootFolderId).first)
    }
    @Test fun goodReplacementCanBeRetainedWhenPreviousCopyIsDamaged() {
        val initial = store()
        val previous = enqueue(initial)
        File(temporary.root, "queue/${previous.id}/scan.pdf").writeText("damaged")
        val replacement = enqueue(initial)
        assertNotEquals(previous.id, replacement.id)
        assertTrue(initial.pdf(replacement).exists())
    }
}
