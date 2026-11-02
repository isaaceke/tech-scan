package com.example.enuguairscannertest

import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream
import java.security.MessageDigest

class FolderAccessPolicyTest {
    private val person = FolderAccessPolicy.Subject("person-id", listOf("person@example.invalid"))
    private val grant = FolderAccessPolicy.Grant(listOf("write"), listOf(person))
    private fun matches(value: FolderAccessPolicy.Grant) = FolderAccessPolicy.matches("person-id", "person@example.invalid", value)

    @Test fun individualIdentityIsAllowed() { assertTrue(matches(grant)) }
    @Test fun wrongAccountIsDenied() { assertFalse(FolderAccessPolicy.matches("wrong", "wrong@example.invalid", grant)) }
    @Test fun missingIdentityIsDenied() { assertFalse(FolderAccessPolicy.matches("", "person@example.invalid", grant)) }
    @Test fun exactEmailIsRequired() {
        assertFalse(FolderAccessPolicy.matches("wrong", "other-person@example.invalid", grant))
        assertTrue(FolderAccessPolicy.matches("different", " PERSON@EXAMPLE.INVALID ", grant))
    }
    @Test fun specificPersonLinkIsAllowed() { assertTrue(matches(grant.copy(hasLink = true, linkScope = "users"))) }
    @Test fun invitationCannotBypassSpecificPersonList() {
        assertFalse(matches(grant.copy(subjects = emptyList(), hasLink = true, linkScope = "users", invitationEmail = "person@example.invalid")))
    }
    @Test fun broadLinksAreDenied() {
        for (scope in listOf("organization", "anonymous", "existingAccess", ""))
            assertFalse(matches(grant.copy(hasLink = true, linkScope = scope)))
    }
    @Test fun groupPermissionIsDenied() { assertFalse(matches(grant.copy(subjects = listOf(person.copy(group = true))))) }
    @Test fun inheritedPermissionIsDenied() { assertFalse(matches(grant.copy(inherited = true))) }
    @Test fun readOnlyPermissionIsDenied() { assertFalse(matches(grant.copy(roles = listOf("read")))) }
    @Test fun revocationBlocksNextCheck() {
        assertTrue(matches(grant))
        assertFalse(emptyList<FolderAccessPolicy.Grant>().any { matches(it) })
    }
    @Test fun scopesRequireWritePermission() {
        assertFalse(FolderAccessPolicy.hasWriteScope("User.Read Files.ReadWrite"))
        assertTrue(FolderAccessPolicy.hasWriteScope("https://graph.microsoft.com/Files.ReadWrite.All"))
        assertFalse(FolderAccessPolicy.hasWriteScope("User.Read Files.Read"))
        assertFalse(FolderAccessPolicy.hasWriteScope("Files.ReadWrite.AppFolder"))
    }
    @Test fun guestSignInUsesResourceTenant() {
        assertEquals("https://login.microsoftonline.com/38de9dec-d800-439b-a669-60f628a90e72/oauth2/v2.0/", FolderAccessPolicy.AUTHORITY)
    }
    @Test fun correctUploadMetadataIsAccepted() {
        assertTrue(FolderAccessPolicy.uploadMatches("pdf-id", "scan.pdf", 10, true, "drive", "folder", "scan.pdf", 10, "drive", "folder"))
    }
    @Test fun wrongDriveParentNameSizeAndMissingFileAreRejected() {
        assertFalse(FolderAccessPolicy.uploadMatches("pdf-id", "scan.pdf", 10, true, "wrong", "folder", "scan.pdf", 10, "drive", "folder"))
        assertFalse(FolderAccessPolicy.uploadMatches("pdf-id", "scan.pdf", 10, true, "drive", "wrong", "scan.pdf", 10, "drive", "folder"))
        assertFalse(FolderAccessPolicy.uploadMatches("pdf-id", "wrong.pdf", 10, true, "drive", "folder", "scan.pdf", 10, "drive", "folder"))
        assertFalse(FolderAccessPolicy.uploadMatches("pdf-id", "scan.pdf", 9, true, "drive", "folder", "scan.pdf", 10, "drive", "folder"))
        assertFalse(FolderAccessPolicy.uploadMatches("pdf-id", "scan.pdf", 10, false, "drive", "folder", "scan.pdf", 10, "drive", "folder"))
    }
    @Test fun completeBytesHaveMatchingDigest() {
        val contents = "%PDF-1.4 synthetic test".toByteArray()
        assertArrayEquals(MessageDigest.getInstance("SHA-256").digest(contents),
            FolderAccessPolicy.contentDigest(ByteArrayInputStream(contents), contents.size.toLong()))
        val corrupted = contents.clone().apply { this[0] = 0 }
        assertFalse(MessageDigest.isEqual(FolderAccessPolicy.contentDigest(ByteArrayInputStream(contents), contents.size.toLong()),
            FolderAccessPolicy.contentDigest(ByteArrayInputStream(corrupted), corrupted.size.toLong())))
    }
    @Test(expected = IllegalArgumentException::class) fun truncatedBytesAreRejected() {
        FolderAccessPolicy.contentDigest(ByteArrayInputStream(byteArrayOf(1, 2)), 3)
    }
    @Test(expected = IllegalArgumentException::class) fun oversizedBytesAreRejected() {
        FolderAccessPolicy.contentDigest(ByteArrayInputStream(byteArrayOf(1, 2, 3)), 2)
    }
    @Test fun selectedFolderCannotMasqueradeAsAttairDelivery() {
        val result = FolderAccessPolicy.deliveryResult(false, true, false, "Graph denied access")
        assertTrue(result.first)
        assertFalse(result.second)
        assertEquals("Graph denied access", result.third)
    }
    @Test fun confirmedGraphDeliveryCountsAsCloudSuccess() {
        assertTrue(FolderAccessPolicy.deliveryResult(true, false, true, "Verified").second)
        assertFalse(FolderAccessPolicy.deliveryResult(true, false, false, "Unverified").second)
    }
    @Test fun microsoftGuidCasingMatchesTheSameAccount() {
        assertTrue(FolderAccessPolicy.userIdMatches("42F177F1-22C0-4BE3-900D-4507125C5C20", "42f177f1-22c0-4be3-900d-4507125c5c20"))
        assertFalse(FolderAccessPolicy.userIdMatches("Different", "different"))
    }
    @Test fun expiredAndMalformedPermissionsAreDenied() {
        assertFalse(matches(grant.copy(expiration = "2000-01-01T00:00:00Z")))
        assertFalse(matches(grant.copy(expiration = "invalid")))
        assertTrue(matches(grant.copy(expiration = "2999-01-01T00:00:00.0000000Z")))
    }
    @Test fun microsoftFractionalExpiryAndTimezoneAreParsedPrecisely() {
        assertTrue(FolderAccessPolicy.expiryAllows("1970-01-01T00:00:00.5Z", 499))
        assertFalse(FolderAccessPolicy.expiryAllows("1970-01-01T00:00:00.5Z", 500))
        assertFalse(FolderAccessPolicy.expiryAllows("1970-01-01T01:00:00+01:00", 0))
    }
}
