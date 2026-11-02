package com.example.enuguairscannertest

import java.io.InputStream
import java.security.MessageDigest
import java.util.Locale
import java.text.ParsePosition
import java.text.SimpleDateFormat

/** Used by the real Graph path and by JVM tests; no Android stubs or mirror policy. */
object FolderAccessPolicy {
    const val RESOURCE_TENANT = "38de9dec-d800-439b-a669-60f628a90e72"
    const val AUTHORITY = "https://login.microsoftonline.com/$RESOURCE_TENANT/oauth2/v2.0/"
    fun signInError(description: String): String {
        val code = Regex("\\bAADSTS(?:90094|90093|900941)\\b").find(description)?.value ?: return description
        return "Microsoft requires ATTAIR administrator approval for this sign-in. " +
            "Approving an email in the Access Panel does not grant the app this Microsoft permission. " +
            "Sign-in cannot continue until ATTAIR authorizes the app. Error: $code."
    }
    data class Subject(val userId: String = "", val emails: List<String> = emptyList(), val group: Boolean = false)
    data class Grant(val roles: List<String>, val subjects: List<Subject>, val hasLink: Boolean = false,
                     val linkScope: String = "", val inherited: Boolean = false, val invitationEmail: String = "",
                     val expiration: String = "")

    fun matches(userId: String, email: String, grant: Grant): Boolean {
        if (userId.isBlank() || !email.contains('@') || "write" !in grant.roles || grant.inherited ||
            (grant.hasLink && grant.linkScope != "users") || grant.subjects.any { it.group } || !expiryAllows(grant.expiration)) return false
        val actual = email.trim().lowercase(Locale.ROOT)
        if (!grant.hasLink && grant.invitationEmail.trim().lowercase(Locale.ROOT) == actual) return true
        return grant.subjects.any { subject ->
            userIdMatches(subject.userId, userId) || subject.emails.any { it.trim().lowercase(Locale.ROOT) == actual }
        }
    }

    fun userIdMatches(first: String, second: String): Boolean {
        if (first.isBlank() || second.isBlank()) return false
        val guid = Regex("[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
        return if (guid.matches(first) && guid.matches(second)) first.equals(second, ignoreCase = true) else first == second
    }

    fun expiryAllows(expiration: String, now: Long = System.currentTimeMillis()): Boolean {
        if (expiration.isBlank()) return true
        val normalized = Regex("\\.(\\d+)(?=Z|[+-]\\d{2}:\\d{2}$)").replace(expiration) {
            "." + it.groupValues[1].take(3).padEnd(3, '0')
        }
        for (pattern in listOf("yyyy-MM-dd'T'HH:mm:ss.SSSXXX", "yyyy-MM-dd'T'HH:mm:ssXXX")) {
            val position = ParsePosition(0)
            val date = SimpleDateFormat(pattern, Locale.ROOT).apply { isLenient = false }.parse(normalized, position)
            if (date != null && position.index == normalized.length) return date.time > now
        }
        return false
    }

    fun hasWriteScope(scope: String): Boolean {
        val scopes = scope.split(' ').map { it.substringAfterLast('/').lowercase(Locale.ROOT) }
        return "files.readwrite.all" in scopes
    }

    fun uploadMatches(id: String, name: String, size: Long, isFile: Boolean, drive: String, parent: String,
                      expectedName: String, expectedSize: Long, expectedDrive: String, expectedParent: String): Boolean =
        id.isNotBlank() && isFile && name == expectedName && size == expectedSize &&
            drive == expectedDrive && parent == expectedParent

    fun contentDigest(input: InputStream, expectedSize: Long): ByteArray {
        val digest = MessageDigest.getInstance("SHA-256")
        var total = 0L
        val buffer = ByteArray(8192)
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            total += count
            require(total <= expectedSize) { "The downloaded PDF exceeds the expected size." }
            digest.update(buffer, 0, count)
        }
        require(total == expectedSize) { "Microsoft returned an incomplete PDF." }
        return digest.digest()
    }

    fun deliveryResult(localSaved: Boolean, selectedFolderSaved: Boolean, graphVerified: Boolean,
                       graphMessage: String): Triple<Boolean, Boolean, String> =
        Triple(localSaved || selectedFolderSaved || graphVerified, graphVerified, graphMessage)
}
