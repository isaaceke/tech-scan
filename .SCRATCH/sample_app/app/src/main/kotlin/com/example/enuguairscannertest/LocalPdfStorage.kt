package com.example.enuguairscannertest

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest

/** Publishes a complete local copy before the app attempts any network delivery. */
object LocalPdfStorage {
    fun save(context: Context, pdf: File, aircraft: String, name: String, patch: Boolean) {
        val subPath = "EnuguAirScanner/SPLIT/$aircraft" + if (patch) "/patches" else ""
        val size = pdf.length()
        val expected = pdf.inputStream().use { FolderAccessPolicy.contentDigest(it, size) }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, name)
                put(MediaStore.MediaColumns.MIME_TYPE, "application/pdf")
                put(MediaStore.MediaColumns.RELATIVE_PATH, "${Environment.DIRECTORY_DOCUMENTS}/$subPath")
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            }
            val resolver = context.contentResolver
            val uri = requireNotNull(resolver.insert(MediaStore.Files.getContentUri("external"), values)) {
                "Android could not create the local PDF."
            }
            try {
                requireNotNull(resolver.openOutputStream(uri)) { "Android could not open the local PDF." }.use { output ->
                    pdf.inputStream().use { require(it.copyTo(output) == size) { "The local PDF copy is incomplete." } }
                    output.flush()
                }
                val actual = requireNotNull(resolver.openInputStream(uri)).use { FolderAccessPolicy.contentDigest(it, size) }
                require(MessageDigest.isEqual(expected, actual)) { "The local PDF copy differs from the scan." }
                require(resolver.update(uri, ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }, null, null) == 1) {
                    "Android could not publish the local PDF."
                }
            } catch (error: Exception) {
                resolver.delete(uri, null, null)
                throw error
            }
        } else {
            val directory = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS), subPath)
            check(directory.isDirectory || directory.mkdirs()) { "Android could not create the local documents folder." }
            val target = File(directory, name)
            val temporary = File.createTempFile("scan-", ".pending", directory)
            try {
                FileOutputStream(temporary).use { output ->
                    pdf.inputStream().use { require(it.copyTo(output) == size) }
                    output.fd.sync()
                }
                val actual = temporary.inputStream().use { FolderAccessPolicy.contentDigest(it, size) }
                require(MessageDigest.isEqual(expected, actual)) { "The local PDF copy differs from the scan." }
                if (target.exists()) {
                    val backup = File(directory, "$name.bak")
                    check(!backup.exists() || backup.delete()) { "Cannot preserve the previous local PDF." }
                    check(target.renameTo(backup)) { "Cannot preserve the previous local PDF." }
                }
                check(temporary.renameTo(target)) { "Android could not publish the local PDF." }
            } finally { temporary.delete() }
        }
    }
}
