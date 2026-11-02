package com.example.enuguairscannertest

import java.io.File
import java.io.FileOutputStream
import java.util.Properties
import java.util.UUID

data class ScanDeliveryJob(
    val id: String, val accountId: String, val email: String, val driveId: String, val rootFolderId: String,
    val sourceName: String, val remoteName: String, val aircraft: String, val patch: Boolean,
    val size: Long, val sha256: String, val createdAt: Long, val revision: Long = 0,
    val delivered: Boolean = false, val lastError: String = "", val receipt: ScanDeliveryReceipt? = null
)

data class ScanDeliveryReceipt(
    val itemId: String, val accountId: String, val driveId: String, val rootFolderId: String,
    val parentId: String, val name: String, val size: Long, val sha256: String, val verifiedAt: Long
)

/** Durable PDF journal. The Android app and JVM recovery tests use this same code. */
class ScanDeliveryStore(private val root: File, private val clock: () -> Long = System::currentTimeMillis) {
    init { check(root.isDirectory || root.mkdirs()) { "Cannot create private PDF delivery storage." } }

    data class Snapshot(val jobs: List<ScanDeliveryJob>, val unreadable: Int)

    @Synchronized fun snapshot(): Snapshot {
        val directories = root.listFiles()?.filter { it.isDirectory && validId(it.name) } ?: emptyList()
        var unreadable = 0
        val jobs = directories.mapNotNull { directory ->
            try { read(directory) } catch (_: Exception) { unreadable++; null }
        }.sortedBy { it.createdAt }
        return Snapshot(jobs, unreadable)
    }

    @Synchronized fun enqueue(pdf: File, accountId: String, email: String, driveId: String, folderId: String,
                              sourceName: String, aircraft: String, patch: Boolean): ScanDeliveryJob {
        require(accountId.isNotBlank() && email.contains('@') && driveId.isNotBlank() && folderId.isNotBlank()) {
            "Microsoft must identify the account and destination before a scan can be queued."
        }
        require(Regex("[A-Z0-9-]{2,16}").matches(aircraft) && sourceName.endsWith(".pdf", true) &&
            sourceName.length in 5..200 && sourceName.none { it in "\\/:*?\"<>|" || it.code < 32 }) { "Invalid scan filename or aircraft." }
        require(pdf.length() in 1..250L * 1024 * 1024) { "Invalid PDF size." }
        val size = pdf.length()
        val digest = digest(pdf, size)
        snapshot().jobs.firstOrNull { !it.delivered && it.accountId == accountId && it.driveId == driveId &&
            it.rootFolderId == folderId && it.sourceName == sourceName && it.aircraft == aircraft &&
            it.patch == patch && it.sha256 == digest && runCatching { pdf(it) }.isSuccess }?.let { return it }
        val id = UUID.randomUUID().toString()
        // Stable for retries and unique across devices; a later scan cannot overwrite this PDF.
        val remoteName = sourceName.dropLast(4).take(180) + "__" + id.replace("-", "").take(12) + ".pdf"
        val job = ScanDeliveryJob(id, accountId, email, driveId, folderId, sourceName, remoteName, aircraft, patch, size, digest, clock())
        val staging = File(root, ".new-$id")
        check(staging.mkdir()) { "Cannot retain the PDF before upload." }
        val copy = File(staging, "scan.pdf")
        try {
            FileOutputStream(copy).use { output ->
                pdf.inputStream().use { it.copyTo(output) }
                output.fd.sync()
            }
            require(digest(copy, size) == digest) { "The saved pending PDF is incomplete." }
            write(staging, job)
            check(staging.renameTo(File(root, id))) { "Cannot publish the pending PDF journal." }
            return job
        } catch (error: Exception) {
            // Only files created inside this private staging directory are touched.
            staging.listFiles()?.forEach { if (it.isFile) it.delete() }
            staging.delete()
            throw error
        }
    }

    @Synchronized fun pdf(job: ScanDeliveryJob): File {
        val file = File(directory(job.id), "scan.pdf")
        require(file.isFile && file.length() == job.size && digest(file, job.size) == job.sha256) {
            "A pending PDF is damaged. Its retained copy has not been deleted."
        }
        return file
    }

    @Synchronized fun failed(job: ScanDeliveryJob, message: String) {
        val current = read(directory(job.id))
        if (!current.delivered) write(directory(job.id), current.copy(revision = current.revision + 1, lastError = message.take(1000)))
    }

    @Synchronized fun delivered(job: ScanDeliveryJob, receipt: ScanDeliveryReceipt) {
        val current = read(directory(job.id))
        require(receipt.itemId.isNotBlank() && receipt.parentId.isNotBlank() && receipt.verifiedAt > 0 &&
            receipt.accountId == current.accountId && receipt.driveId == current.driveId &&
            receipt.rootFolderId == current.rootFolderId && receipt.name == current.remoteName &&
            receipt.size == current.size && receipt.sha256 == current.sha256) { "The delivery receipt does not match this pending PDF." }
        // Publish proof before deleting bytes. A crash before this point leaves the PDF retryable.
        write(directory(job.id), current.copy(revision = current.revision + 1, delivered = true, lastError = "", receipt = receipt))
        File(directory(job.id), "scan.pdf").delete()
    }

    private fun directory(id: String): File {
        require(validId(id)) { "Invalid delivery record ID." }
        return File(root, id)
    }

    private fun validId(id: String) = Regex("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}").matches(id)

    private fun read(directory: File): ScanDeliveryJob {
        val records = directory.listFiles()?.filter { it.name.startsWith("record-") && it.name.endsWith(".properties") } ?: emptyList()
        val decoded = records.mapNotNull { file ->
            try {
                val p = Properties().apply { file.inputStream().use { load(it) } }
                fun field(key: String): String = p.getProperty(key) ?: error("Missing delivery field: $key")
                val receipt = if (field("delivered").toBoolean()) ScanDeliveryReceipt(
                    field("itemId"), field("accountId"), field("driveId"), field("rootFolderId"), field("parentId"),
                    field("remoteName"), field("size").toLong(), field("sha256"), field("verifiedAt").toLong()) else null
                ScanDeliveryJob(field("id"), field("accountId"), field("email"), field("driveId"), field("rootFolderId"),
                    field("sourceName"), field("remoteName"), field("aircraft"), field("patch").toBoolean(), field("size").toLong(),
                    field("sha256"), field("createdAt").toLong(), field("revision").toLong(), field("delivered").toBoolean(),
                    p.getProperty("lastError", ""), receipt).also { require(it.id == directory.name) }
            } catch (_: Exception) { null }
        }
        return decoded.maxByOrNull { it.revision } ?: error("Unreadable saved delivery record")
    }

    private fun write(directory: File, job: ScanDeliveryJob) {
        val p = Properties()
        mapOf("id" to job.id, "accountId" to job.accountId, "email" to job.email, "driveId" to job.driveId,
            "rootFolderId" to job.rootFolderId, "sourceName" to job.sourceName, "remoteName" to job.remoteName,
            "aircraft" to job.aircraft, "patch" to job.patch.toString(), "size" to job.size.toString(), "sha256" to job.sha256,
            "createdAt" to job.createdAt.toString(), "revision" to job.revision.toString(), "delivered" to job.delivered.toString(),
            "lastError" to job.lastError).forEach { (key, value) -> p.setProperty(key, value) }
        job.receipt?.let { p.setProperty("itemId", it.itemId); p.setProperty("parentId", it.parentId); p.setProperty("verifiedAt", it.verifiedAt.toString()) }
        val suffix = UUID.randomUUID().toString()
        val temporary = File(directory, "record-$suffix.tmp")
        FileOutputStream(temporary).use { output -> p.store(output, null); output.fd.sync() }
        check(temporary.renameTo(File(directory, "record-${job.revision}-$suffix.properties"))) { "Cannot save PDF delivery state." }
        // Keep the newest two complete records as recovery journals.
        directory.listFiles()?.filter { it.name.startsWith("record-") && it.name.endsWith(".properties") }
            ?.sortedByDescending { it.name.substringAfter("record-").substringBefore('-').toLongOrNull() ?: -1 }
            ?.drop(2)?.forEach { it.delete() }
    }

    companion object {
        fun digest(file: File, size: Long): String = file.inputStream().use { FolderAccessPolicy.contentDigest(it, size) }
            .joinToString("") { "%02x".format(it.toInt() and 255) }
    }
}
