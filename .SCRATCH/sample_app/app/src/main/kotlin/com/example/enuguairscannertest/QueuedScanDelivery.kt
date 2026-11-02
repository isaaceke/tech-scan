package com.example.enuguairscannertest

import java.io.File

/** A failed operation keeps its PDF. Only a matching verified receipt completes it. */
class QueuedScanDelivery(private val store: ScanDeliveryStore,
                         private val upload: (ScanDeliveryJob, File) -> ScanDeliveryReceipt) {
    fun deliver(job: ScanDeliveryJob, accountId: String, driveId: String, rootFolderId: String): Pair<Boolean, String> {
        val current = store.snapshot().jobs.firstOrNull { it.id == job.id } ?: return false to "Saved PDF record is unavailable."
        if (current.delivered) return true to "PDF already verified in ATTAIR OneDrive."
        if (current.accountId != accountId || current.driveId != driveId || current.rootFolderId != rootFolderId) {
            val message = "This pending PDF requires its original Microsoft account and ATTAIR folder."
            store.failed(current, message)
            return false to message
        }
        return try {
            val receipt = upload(current, store.pdf(current))
            store.delivered(current, receipt)
            true to "PDF verified in ATTAIR OneDrive: ${current.remoteName}"
        } catch (error: Exception) {
            val message = error.message ?: "OneDrive delivery did not complete."
            store.failed(current, message)
            false to message
        }
    }
}
