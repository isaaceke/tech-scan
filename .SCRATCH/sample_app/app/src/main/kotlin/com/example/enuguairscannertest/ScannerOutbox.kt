package com.example.enuguairscannertest

import android.app.Application
import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.File
import java.util.concurrent.TimeUnit

class ScannerApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        MicrosoftOAuthManager.initialize(this)
        ScannerOutbox.initialize(this)
    }
}

object ScannerOutbox {
    data class Status(val pending: Int = 0, val lastError: String = "", val lastReceipt: ScanDeliveryReceipt? = null)
    private val mutableStatus = MutableStateFlow(Status())
    val status = mutableStatus.asStateFlow()
    private lateinit var application: Context
    private lateinit var store: ScanDeliveryStore
    private val deliveryMutex = Mutex()
    private val network = Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()

    fun initialize(context: Context) {
        if (!::application.isInitialized) {
            application = context.applicationContext
            store = ScanDeliveryStore(File(application.noBackupFilesDir, "pending-scans"))
        }
        publish()
        WorkManager.getInstance(application).enqueueUniquePeriodicWork("scanner-pdf-recovery", ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<ScanDeliveryWorker>(15, TimeUnit.MINUTES).setConstraints(network)
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS).build())
        if (mutableStatus.value.pending > 0) kick()
    }

    fun kick() {
        if (!::application.isInitialized) return
        WorkManager.getInstance(application).enqueueUniqueWork("scanner-pdf-delivery", ExistingWorkPolicy.KEEP,
            OneTimeWorkRequestBuilder<ScanDeliveryWorker>().setConstraints(network)
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS).build())
    }

    suspend fun saveAndDeliver(context: Context, pdf: File, aircraft: String, name: String, patch: Boolean): Pair<Boolean, String> = withContext(Dispatchers.IO) {
        val prefs = context.getSharedPreferences("techlog_scanner_prefs", Context.MODE_PRIVATE)
        val accountId = MicrosoftOAuthManager.getConnectedAccountId(prefs)
            ?: return@withContext false to "Microsoft must confirm the signed-in account. The local PDF remains saved."
        val email = MicrosoftOAuthManager.getConnectedEmail(prefs)
            ?: return@withContext false to "Microsoft account email is unavailable. The local PDF remains saved."
        val destination = MicrosoftOAuthManager.destination()
            ?: return@withContext false to "Owner folder setup is incomplete. The local PDF remains saved."
        val job = store.enqueue(pdf, accountId, email, destination.first, destination.second, name, aircraft, patch)
        publish()
        kick()
        // All delivery paths use the same lock and the same durable job.
        val result = attempt(job)
        kick()
        if (result.first) result else false to "PDF retained for automatic delivery. ${result.second}"
    }

    private suspend fun attempt(job: ScanDeliveryJob): Pair<Boolean, String> = deliveryMutex.withLock {
        val prefs = application.getSharedPreferences("techlog_scanner_prefs", Context.MODE_PRIVATE)
        val access = MicrosoftOAuthManager.refreshOperatorStatus(prefs)
        if (access.status != "APPROVED") {
            val message = access.message ?: "Microsoft folder access is unavailable."
            store.failed(job, message)
            publish()
            return@withLock false to message
        }
        val token = MicrosoftOAuthManager.getValidAccessToken(prefs)
        val account = MicrosoftOAuthManager.getConnectedAccountId(prefs)
        val destination = MicrosoftOAuthManager.destination()
        if (token == null || account == null || destination == null) {
            store.failed(job, "Microsoft sign-in or folder configuration is unavailable.")
            publish()
            return@withLock false to "Microsoft sign-in or folder configuration is unavailable."
        }
        val delivery = QueuedScanDelivery(store) { pending, pdf ->
            if (MicrosoftOAuthManager.onlineServiceEnabled()) OnlineServiceClient(MicrosoftOAuthManager.onlineServerUrl(), token).upload(pending, pdf)
            else MicrosoftGraphPdfClient(pending.driveId, pending.rootFolderId, pending.accountId, token)
                .upload(pdf, pending.aircraft, pending.remoteName, pending.patch)
        }
        val result = delivery.deliver(job, account, destination.first, destination.second)
        publish()
        result
    }

    suspend fun retryBatch(): Boolean = withContext(Dispatchers.IO) {
        val prefs = application.getSharedPreferences("techlog_scanner_prefs", Context.MODE_PRIVATE)
        val account = MicrosoftOAuthManager.getConnectedAccountId(prefs)
        val destination = MicrosoftOAuthManager.destination()
        // A retained scan from another signed-in account must not starve this account's deliveries.
        val pending = store.snapshot().jobs.filter { !it.delivered && it.accountId == account &&
            it.driveId == destination?.first && it.rootFolderId == destination?.second }.take(3)
        for (job in pending) attempt(job)
        publish()
        mutableStatus.value.pending == 0
    }

    private fun publish() {
        val snapshot = store.snapshot()
        val pending = snapshot.jobs.filter { !it.delivered }
        mutableStatus.value = Status(pending.size + snapshot.unreadable,
            if (snapshot.unreadable > 0) "A retained PDF record cannot be read. Its copy remains on this phone."
            else pending.lastOrNull { it.lastError.isNotBlank() }?.lastError ?: "",
            snapshot.jobs.mapNotNull { it.receipt }.maxByOrNull { it.verifiedAt })
    }
}

class ScanDeliveryWorker(context: Context, parameters: WorkerParameters) : CoroutineWorker(context, parameters) {
    override suspend fun doWork(): Result = try {
        if (ScannerOutbox.retryBatch()) Result.success() else Result.retry()
    } catch (cancelled: kotlinx.coroutines.CancellationException) {
        throw cancelled
    } catch (_: Exception) {
        Result.retry()
    }
}
