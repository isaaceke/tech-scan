package com.example.enuguairscannertest

import android.Manifest
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.pdf.PdfDocument
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.HapticFeedbackConstants
import android.view.Surface
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraControl
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.lifecycle.lifecycleScope
import androidx.camera.view.PreviewView
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.window.Dialog
import androidx.core.content.ContextCompat
import androidx.documentfile.provider.DocumentFile
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

val DEFAULT_FLEET = listOf("5N-ENO", "5N-ENP", "5N-ENQ", "5N-ENS", "5N-ENU")

fun loadFleet(prefs: SharedPreferences): List<String> {
    val raw = prefs.getString("fleet_aircraft_csv", null) ?: return DEFAULT_FLEET
    val list = raw.split(",").map { it.trim() }.filter { it.isNotEmpty() }
    return if (list.isNotEmpty()) list else DEFAULT_FLEET
}

fun saveFleet(prefs: SharedPreferences, fleet: List<String>) {
    prefs.edit().putString("fleet_aircraft_csv", fleet.joinToString(",")).apply()
}

// -------------------------------------------------------------------------
// PER-AIRCRAFT MEMORY (Matches Doyce's TECHLOG_RENAME.py Architecture)
// -------------------------------------------------------------------------
fun getLastLogForAircraft(prefs: SharedPreferences, ac: String): String {
    val saved = prefs.getString("ac_last_log_$ac", null)
    if (!saved.isNullOrBlank()) {
        val num = saved.toIntOrNull() ?: 1
        val width = maxOf(3, saved.length)
        return String.format("%0${width}d", num + 1)
    }
    return "000001"
}

fun saveLastLogForAircraft(prefs: SharedPreferences, ac: String, logNum: String) {
    prefs.edit()
        .putString("ac_last_log_$ac", logNum)
        .putString("last_active_aircraft", ac)
        .apply()
}

class MainActivity : ComponentActivity() {
    private var authCallback: ((Boolean, String) -> Unit)? = null
    private var authVerifyingCallback: (() -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        handleOAuthIntent(intent)
        setContent {
            // Full Comprehensive Dark Theme (Eliminates white-on-white text bugs)
            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = Color.White,
                    onPrimary = Color.Black,
                    primaryContainer = Color(0xFF27272A),
                    onPrimaryContainer = Color.White,
                    secondary = Color(0xFFA1A1AA),
                    onSecondary = Color.Black,
                    background = Color.Black,
                    onBackground = Color.White,
                    surface = Color(0xFF141416),
                    onSurface = Color.White,
                    surfaceVariant = Color(0xFF27272A),
                    onSurfaceVariant = Color(0xFFE4E4E7),
                    surfaceContainer = Color(0xFF18181B),
                    surfaceContainerHigh = Color(0xFF27272A),
                    surfaceContainerHighest = Color(0xFF3F3F46),
                    surfaceContainerLow = Color(0xFF141416),
                    surfaceContainerLowest = Color(0xFF09090B),
                    inverseSurface = Color.White,
                    inverseOnSurface = Color.Black,
                    outline = Color(0xFF3F3F46),
                    outlineVariant = Color(0xFF27272A)
                )
            ) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color.Black
                ) {
                    EnuguAirScannerApp(
                        onRegisterAuthCallback = { cb -> authCallback = cb },
                        onRegisterVerifyingCallback = { cb -> authVerifyingCallback = cb }
                    )
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleOAuthIntent(intent)
    }

    private fun handleOAuthIntent(intent: Intent?) {
        val data = intent?.data ?: return
        if (data.scheme == "techlogscan" && data.host == "auth") {
            authVerifyingCallback?.invoke()
            val prefs = getSharedPreferences("techlog_scanner_prefs", Context.MODE_PRIVATE)
            lifecycleScope.launch {
                val (success, result) = MicrosoftOAuthManager.handleAuthRedirect(intent, prefs)
                authCallback?.invoke(success, result)
                if (success) {
                    Toast.makeText(this@MainActivity, "Connected: $result", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@MainActivity, "Sign-in error: $result", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
}

class ScannedPage(
    val sequenceNumber: Int,
    var bitmap: Bitmap,
    val isLandscape: Boolean,
    var isHighResReady: Boolean = false
)

data class SaveProgressState(
    val fileName: String,
    val stage: String,
    val inProgress: Boolean,
    val isSuccess: Boolean = false,
    val isError: Boolean = false,
    val errorMessage: String? = null
)

data class AuditorTask(
    val id: String,
    val aircraft: String,
    val logNumber: String,
    val description: String,
    val date: String,
    val isPatchNeeded: Boolean
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EnuguAirScannerApp(
    onRegisterAuthCallback: (((Boolean, String) -> Unit) -> Unit)? = null,
    onRegisterVerifyingCallback: ((() -> Unit) -> Unit)? = null
) {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("techlog_scanner_prefs", Context.MODE_PRIVATE) }

    // Microsoft 365 Cloud Ingestion State
    var isMicrosoftConnected by remember {
        mutableStateOf(MicrosoftOAuthManager.isConnected(prefs))
    }
    var microsoftConnectedEmail by remember {
        mutableStateOf(MicrosoftOAuthManager.getConnectedEmail(prefs))
    }
    var authState by remember { mutableStateOf("IDLE") } // "IDLE", "SIGNING_IN", "VERIFYING", "TIMEOUT", "ERROR"
    var authErrorMessage by remember { mutableStateOf<String?>(null) }

    // Auto-timeout: If in SIGNING_IN for > 14 seconds without intent, reset to TIMEOUT
    LaunchedEffect(authState) {
        if (authState == "SIGNING_IN") {
            kotlinx.coroutines.delay(14000L)
            if (authState == "SIGNING_IN") {
                authState = "TIMEOUT"
                authErrorMessage = "Sign-in didn't complete. Tap to retry."
            }
        }
    }

    LaunchedEffect(Unit) {
        onRegisterVerifyingCallback?.invoke {
            authState = "VERIFYING"
        }
        onRegisterAuthCallback?.invoke { success, result ->
            if (success) {
                isMicrosoftConnected = true
                microsoftConnectedEmail = result
                authState = "IDLE"
                authErrorMessage = null
            } else {
                isMicrosoftConnected = false
                authState = "ERROR"
                authErrorMessage = result
            }
        }
    }

    // Fleet list
    var fleetList by remember { mutableStateOf(loadFleet(prefs)) }
    var showSettingsDialog by remember { mutableStateOf(false) }

    // Active Aircraft Memory: Remembers last aircraft selected from previous session
    val lastActiveAc = prefs.getString("last_active_aircraft", null)
    var selectedAircraft by remember {
        mutableStateOf(if (lastActiveAc != null && fleetList.contains(lastActiveAc)) lastActiveAc else (fleetList.firstOrNull() ?: "5N-ENO"))
    }

    // Active Log Number Memory: Remembers each aircraft's independent last log number (+1)
    var logNumber by remember {
        mutableStateOf(getLastLogForAircraft(prefs, selectedAircraft))
    }

    // Navigation state: "START_SESSION", "CAMERA_SCANNER", "AUDITOR_TASKS"
    var currentScreen by remember { mutableStateOf("START_SESSION") }

    // Ensure selected aircraft stays valid if fleet changes
    LaunchedEffect(fleetList) {
        if (!fleetList.contains(selectedAircraft) && fleetList.isNotEmpty()) {
            selectedAircraft = fleetList.first()
            logNumber = getLastLogForAircraft(prefs, selectedAircraft)
        }
    }

    // Date: ALWAYS DEFAULTS TO PREVIOUS DAY (Yesterday)
    val yesterdayCalendar = remember {
        Calendar.getInstance().apply { add(Calendar.DAY_OF_YEAR, -1) }
    }
    var logDateFormatted by remember {
        mutableStateOf(formatDisplayDate(yesterdayCalendar))
    }

    // Mode: Normal Scan vs Patch
    var isPatchMode by remember { mutableStateOf(false) }
    var patchReason by remember { mutableStateOf("PREFLIGHT") }

    // Auditor Tasks (Clean real list)
    val auditorTasks = remember { mutableStateListOf<AuditorTask>() }

    // OneDrive / SharePoint SAF folder picker
    var linkedTreeUriString by remember { mutableStateOf(prefs.getString("onedrive_tree_uri", null)) }
    val folderPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocumentTree()
    ) { uri: Uri? ->
        if (uri != null) {
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
                prefs.edit().putString("onedrive_tree_uri", uri.toString()).apply()
                linkedTreeUriString = uri.toString()
                Toast.makeText(context, "SharePoint SPLIT folder linked!", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Toast.makeText(context, "Link error: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    if (showSettingsDialog) {
        SettingsDialog(
            currentFleet = fleetList,
            onUpdateFleet = { updated ->
                fleetList = updated
                saveFleet(prefs, updated)
            },
            isMicrosoftConnected = isMicrosoftConnected,
            microsoftEmail = microsoftConnectedEmail,
            authState = authState,
            authErrorMessage = authErrorMessage,
            onConnectMicrosoft = {
                authState = "SIGNING_IN"
                authErrorMessage = null
                MicrosoftOAuthManager.startSignIn(context, prefs)
            },
            onCancelAuth = {
                authState = "IDLE"
                authErrorMessage = null
            },
            onDisconnectMicrosoft = {
                MicrosoftOAuthManager.disconnect(prefs)
                isMicrosoftConnected = false
                microsoftConnectedEmail = null
                authState = "IDLE"
                authErrorMessage = null
                Toast.makeText(context, "Disconnected Microsoft account", Toast.LENGTH_SHORT).show()
            },
            isOneDriveLinked = linkedTreeUriString != null,
            onLinkOneDrive = { folderPickerLauncher.launch(null) },
            onDismiss = { showSettingsDialog = false }
        )
    }

    when (currentScreen) {
        "START_SESSION" -> {
            StartSessionScreen(
                aircraftOptions = fleetList,
                selectedAircraft = selectedAircraft,
                onAircraftSelected = { ac ->
                    selectedAircraft = ac
                    // Switch to this specific aircraft's remembered log number (from renamer memory)
                    logNumber = getLastLogForAircraft(prefs, ac)
                    prefs.edit().putString("last_active_aircraft", ac).apply()
                },
                logDateFormatted = logDateFormatted,
                onDateChanged = { logDateFormatted = it },
                logNumber = logNumber,
                onLogNumberChanged = { newNum ->
                    logNumber = newNum
                    saveLastLogForAircraft(prefs, selectedAircraft, newNum)
                },
                openTaskCount = auditorTasks.size,
                onOpenSettings = { showSettingsDialog = true },
                onViewTasks = { currentScreen = "AUDITOR_TASKS" },
                onStartScanning = { currentScreen = "CAMERA_SCANNER" }
            )
        }
        "CAMERA_SCANNER" -> {
            CameraScannerScreen(
                aircraft = selectedAircraft,
                onAircraftChange = { ac ->
                    selectedAircraft = ac
                    logNumber = getLastLogForAircraft(prefs, ac)
                    prefs.edit().putString("last_active_aircraft", ac).apply()
                },
                aircraftOptions = fleetList,
                dateText = logDateFormatted,
                logNumber = logNumber,
                onLogNumberChange = { newNum ->
                    logNumber = newNum
                    saveLastLogForAircraft(prefs, selectedAircraft, newNum)
                },
                isPatchMode = isPatchMode,
                patchReason = patchReason,
                onExitToSetup = { currentScreen = "START_SESSION" }
            )
        }
        "AUDITOR_TASKS" -> {
            AuditorTasksScreen(
                tasks = auditorTasks,
                onSelectCompleteRescan = { task ->
                    selectedAircraft = task.aircraft
                    logNumber = task.logNumber
                    logDateFormatted = task.date
                    isPatchMode = false
                    currentScreen = "CAMERA_SCANNER"
                },
                onSelectPatchScan = { task ->
                    selectedAircraft = task.aircraft
                    logNumber = task.logNumber
                    logDateFormatted = task.date
                    isPatchMode = true
                    patchReason = "DEFECT_CORRECTION"
                    currentScreen = "CAMERA_SCANNER"
                },
                onBack = { currentScreen = "START_SESSION" }
            )
        }
    }
}

// =========================================================================
// 1. SETTINGS DIALOG (Fleet Management & SharePoint Sync)
// =========================================================================
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsDialog(
    currentFleet: List<String>,
    onUpdateFleet: (List<String>) -> Unit,
    isMicrosoftConnected: Boolean,
    microsoftEmail: String?,
    authState: String,
    authErrorMessage: String?,
    onConnectMicrosoft: () -> Unit,
    onCancelAuth: () -> Unit,
    onDisconnectMicrosoft: () -> Unit,
    isOneDriveLinked: Boolean,
    onLinkOneDrive: () -> Unit,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("techlog_scanner_prefs", Context.MODE_PRIVATE) }
    var newRegInput by remember { mutableStateOf("5N-") }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(16.dp),
            color = Color(0xFF18181B),
            border = BorderStroke(1.dp, Color(0xFF27272A)),
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 16.dp)
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "SETTINGS",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                    Text(
                        text = "DONE",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        modifier = Modifier.clickable { onDismiss() }
                    )
                }

                Spacer(modifier = Modifier.height(18.dp))

                // Microsoft 365 Direct Ingestion (1-Tap SSO, Zero Recurring Validation)
                Text(
                    text = "MICROSOFT 365 / SHAREPOINT",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFA1A1AA),
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(8.dp))

                if (isMicrosoftConnected) {
                    Surface(
                        color = Color(0xFF27272A),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 14.dp, vertical = 12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = microsoftEmail ?: "Connected",
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                                val opStatus = MicrosoftOAuthManager.getOperatorStatus(prefs)
                                val statusText = when (opStatus) {
                                    "APPROVED" -> "APPROVED OPERATOR"
                                    "REJECTED" -> "APPROVAL REJECTED"
                                    else -> "APPROVAL PENDING"
                                }
                                val statusColor = when (opStatus) {
                                    "APPROVED" -> Color(0xFF10B981)
                                    "REJECTED" -> Color(0xFFEF4444)
                                    else -> Color(0xFFF59E0B)
                                }
                                Text(
                                    text = statusText,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = statusColor
                                )
                            }
                            Text(
                                text = "DISCONNECT",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFFEF4444),
                                modifier = Modifier.clickable { onDisconnectMicrosoft() }
                            )
                        }
                    }
                } else when (authState) {
                    "SIGNING_IN" -> {
                        Surface(
                            color = Color(0xFF27272A),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(14.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Text(
                                    text = "SIGNING YOU IN...",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                LinearProgressIndicator(
                                    color = Color.White,
                                    trackColor = Color(0xFF3F3F46),
                                    modifier = Modifier.fillMaxWidth()
                                )
                                Spacer(modifier = Modifier.height(10.dp))
                                Text(
                                    text = "CANCEL",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFFA1A1AA),
                                    modifier = Modifier.clickable { onCancelAuth() }
                                )
                            }
                        }
                    }
                    "VERIFYING" -> {
                        Surface(
                            color = Color(0xFF27272A),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(14.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Text(
                                    text = "VERIFYING ACCOUNT & TOKEN...",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                LinearProgressIndicator(
                                    color = Color(0xFF10B981),
                                    trackColor = Color(0xFF3F3F46),
                                    modifier = Modifier.fillMaxWidth()
                                )
                            }
                        }
                    }
                    else -> {
                        // IDLE, TIMEOUT, or ERROR
                        Column(modifier = Modifier.fillMaxWidth()) {
                            if (!authErrorMessage.isNullOrBlank()) {
                                Surface(
                                    color = Color(0xFF3F1D1D),
                                    shape = RoundedCornerShape(6.dp),
                                    border = BorderStroke(1.dp, Color(0xFF7F1D1D)),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(bottom = 8.dp)
                                ) {
                                    Text(
                                        text = authErrorMessage,
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Medium,
                                        color = Color(0xFFFCA5A5),
                                        modifier = Modifier.padding(10.dp)
                                    )
                                }
                            }
                            Button(
                                onClick = { onConnectMicrosoft() },
                                colors = ButtonDefaults.buttonColors(containerColor = Color.White),
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(48.dp)
                            ) {
                                Text(
                                    text = if (authState == "TIMEOUT" || authState == "ERROR") "TRY CONNECTING AGAIN" else "CONNECT MICROSOFT 365",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )
                            }
                        }
                    }
                }

                // Azure App (Client) ID Configuration
                var clientIdInput by remember { mutableStateOf(MicrosoftOAuthManager.getClientId(prefs)) }
                var showClientConfig by remember { mutableStateOf(false) }

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "AZURE APP ID",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFA1A1AA)
                    )
                    Text(
                        text = if (showClientConfig) "DONE" else "EDIT",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        modifier = Modifier.clickable { showClientConfig = !showClientConfig }
                    )
                }

                if (showClientConfig) {
                    Spacer(modifier = Modifier.height(6.dp))
                    OutlinedTextField(
                        value = clientIdInput,
                        onValueChange = {
                            clientIdInput = it
                            MicrosoftOAuthManager.setCustomClientId(prefs, it)
                        },
                        singleLine = true,
                        placeholder = { Text("Paste Azure Application (Client) ID", color = Color(0xFF71717A), fontSize = 12.sp) },
                        textStyle = LocalTextStyle.current.copy(
                            fontSize = 12.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Medium,
                            color = Color.White
                        ),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = Color(0xFF27272A),
                            unfocusedContainerColor = Color(0xFF27272A),
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedBorderColor = Color.White,
                            unfocusedBorderColor = Color(0xFF3F3F46)
                        ),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp)
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Redirect URI: techlogscan://auth",
                        fontSize = 10.sp,
                        color = Color(0xFFA1A1AA)
                    )
                }

                // Backend Server URL Configuration
                var backendUrlInput by remember { mutableStateOf(MicrosoftOAuthManager.getBackendUrl(prefs)) }
                var showBackendConfig by remember { mutableStateOf(false) }

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "BACKEND SERVER URL",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFA1A1AA)
                    )
                    Text(
                        text = if (showBackendConfig) "DONE" else "EDIT",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        modifier = Modifier.clickable { showBackendConfig = !showBackendConfig }
                    )
                }

                if (showBackendConfig) {
                    Spacer(modifier = Modifier.height(6.dp))
                    OutlinedTextField(
                        value = backendUrlInput,
                        onValueChange = {
                            backendUrlInput = it
                            MicrosoftOAuthManager.setBackendUrl(prefs, it)
                        },
                        singleLine = true,
                        placeholder = { Text("http://10.0.2.2:8000 or https://...", color = Color(0xFF71717A), fontSize = 12.sp) },
                        textStyle = LocalTextStyle.current.copy(
                            fontSize = 12.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Medium,
                            color = Color.White
                        ),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = Color(0xFF27272A),
                            unfocusedContainerColor = Color(0xFF27272A),
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedBorderColor = Color.White,
                            unfocusedBorderColor = Color(0xFF3F3F46)
                        ),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp)
                    )
                }

                Spacer(modifier = Modifier.height(18.dp))

                // Active Fleet
                Text(
                    text = "ACTIVE FLEET",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFA1A1AA),
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(8.dp))

                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    currentFleet.forEach { reg ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(Color(0xFF27272A), RoundedCornerShape(8.dp))
                                .padding(horizontal = 14.dp, vertical = 10.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = reg,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                            if (currentFleet.size > 1) {
                                Text(
                                    text = "REMOVE",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFFEF4444),
                                    modifier = Modifier.clickable {
                                        val updated = currentFleet.filter { it != reg }
                                        onUpdateFleet(updated)
                                    }
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Add Aircraft
                Text(
                    text = "ADD AIRCRAFT",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFA1A1AA),
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(6.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedTextField(
                        value = newRegInput,
                        onValueChange = {
                            newRegInput = it.uppercase(Locale.US)
                            errorMessage = null
                        },
                        singleLine = true,
                        placeholder = { Text("5N-XXX", color = Color(0xFF71717A)) },
                        textStyle = LocalTextStyle.current.copy(
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        ),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = Color(0xFF121212),
                            unfocusedContainerColor = Color(0xFF121212),
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedBorderColor = Color.White,
                            unfocusedBorderColor = Color(0xFF3F3F46)
                        ),
                        modifier = Modifier.weight(1f)
                    )

                    Button(
                        onClick = {
                            val clean = newRegInput.trim().uppercase(Locale.US)
                            if (clean.length < 3) {
                                errorMessage = "Registration too short"
                            } else if (currentFleet.contains(clean)) {
                                errorMessage = "Aircraft already exists"
                            } else {
                                val updated = currentFleet + clean
                                onUpdateFleet(updated)
                                newRegInput = "5N-"
                                errorMessage = null
                            }
                        },
                        shape = RoundedCornerShape(8.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color.White)
                    ) {
                        Text(
                            text = "ADD",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )
                    }
                }

                if (errorMessage != null) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = errorMessage ?: "",
                        fontSize = 11.sp,
                        color = Color(0xFFEF4444),
                        modifier = Modifier.fillMaxWidth()
                    )
                }

                Spacer(modifier = Modifier.height(14.dp))

                TextButton(
                    onClick = {
                        onUpdateFleet(DEFAULT_FLEET)
                    }
                ) {
                    Text(
                        text = "Reset to Default Fleet",
                        fontSize = 12.sp,
                        color = Color(0xFFA1A1AA)
                    )
                }

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = "DEVELOPER: DOYCE",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF71717A),
                    letterSpacing = 1.sp
                )
            }
        }
    }
}

// =========================================================================
// 2. START SESSION SCREEN (Material 3 Calendar Dialog Date Picker)
// =========================================================================
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StartSessionScreen(
    aircraftOptions: List<String>,
    selectedAircraft: String,
    onAircraftSelected: (String) -> Unit,
    logDateFormatted: String,
    onDateChanged: (String) -> Unit,
    logNumber: String,
    onLogNumberChanged: (String) -> Unit,
    openTaskCount: Int,
    onOpenSettings: () -> Unit,
    onViewTasks: () -> Unit,
    onStartScanning: () -> Unit
) {
    var aircraftMenuExpanded by remember { mutableStateOf(false) }

    // MATERIAL 3 CALENDAR DATE PICKER MODAL (NO KEYBOARD)
    var showDatePickerDialog by remember { mutableStateOf(false) }
    val datePickerState = rememberDatePickerState(
        initialSelectedDateMillis = Calendar.getInstance().apply { add(Calendar.DAY_OF_YEAR, -1) }.timeInMillis
    )

    if (showDatePickerDialog) {
        DatePickerDialog(
            onDismissRequest = { showDatePickerDialog = false },
            confirmButton = {
                TextButton(
                    onClick = {
                        datePickerState.selectedDateMillis?.let { millis ->
                            val cal = Calendar.getInstance().apply { timeInMillis = millis }
                            onDateChanged(formatDisplayDate(cal))
                        }
                        showDatePickerDialog = false
                    }
                ) {
                    Text("OK", color = Color.White, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDatePickerDialog = false }) {
                    Text("CANCEL", color = Color(0xFFA1A1AA), fontWeight = FontWeight.Bold)
                }
            },
            colors = DatePickerDefaults.colors(
                containerColor = Color(0xFF18181B)
            )
        ) {
            DatePicker(
                state = datePickerState,
                showModeToggle = false,
                colors = DatePickerDefaults.colors(
                    containerColor = Color(0xFF18181B),
                    titleContentColor = Color.White,
                    headlineContentColor = Color.White,
                    weekdayContentColor = Color(0xFFA1A1AA),
                    subheadContentColor = Color.White,
                    yearContentColor = Color.White,
                    currentYearContentColor = Color.White,
                    selectedYearContentColor = Color.Black,
                    selectedYearContainerColor = Color.White,
                    dayContentColor = Color.White,
                    selectedDayContentColor = Color.Black,
                    selectedDayContainerColor = Color.White,
                    todayContentColor = Color(0xFF10B981),
                    todayDateBorderColor = Color(0xFF10B981)
                )
            )
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.SpaceBetween
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(8.dp))

            // Header Bar: App Name, Developer Credit, Settings Button
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "TECHLOG SCAN",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Black,
                        color = Color.White,
                        letterSpacing = 0.5.sp
                    )
                    Text(
                        text = "DOYCE",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFA1A1AA),
                        letterSpacing = 1.sp
                    )
                }

                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFF27272A),
                    modifier = Modifier.clickable { onOpenSettings() }
                ) {
                    Text(
                        text = "SETTINGS",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            // 1. Aircraft Selector
            Column(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "AIRCRAFT",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFA1A1AA),
                    letterSpacing = 0.5.sp
                )
                Spacer(modifier = Modifier.height(6.dp))

                Box(modifier = Modifier.fillMaxWidth()) {
                    Surface(
                        shape = RoundedCornerShape(10.dp),
                        color = Color(0xFF18181B),
                        border = BorderStroke(1.dp, Color(0xFF27272A)),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp)
                            .clickable { aircraftMenuExpanded = true }
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(horizontal = 16.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = selectedAircraft,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                            Text(text = "▼", fontSize = 11.sp, color = Color(0xFFA1A1AA))
                        }
                    }

                    DropdownMenu(
                        expanded = aircraftMenuExpanded,
                        onDismissRequest = { aircraftMenuExpanded = false },
                        modifier = Modifier.background(Color(0xFF18181B))
                    ) {
                        aircraftOptions.forEach { reg ->
                            DropdownMenuItem(
                                text = {
                                    Text(
                                        text = reg,
                                        fontSize = 16.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color.White
                                    )
                                },
                                onClick = {
                                    onAircraftSelected(reg)
                                    aircraftMenuExpanded = false
                                }
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            // 2. Date Input (CALENDAR PICKER MODAL - STRICTLY NO KEYBOARD)
            Column(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "DATE",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFA1A1AA),
                    letterSpacing = 0.5.sp
                )
                Spacer(modifier = Modifier.height(6.dp))

                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = Color(0xFF18181B),
                    border = BorderStroke(1.dp, Color(0xFF27272A)),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp)
                        .clickable { showDatePickerDialog = true }
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = logDateFormatted,
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        Text(text = "▼", fontSize = 11.sp, color = Color(0xFFA1A1AA))
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            // 3. Log Number Input (Inherited & Saved Per Aircraft from Renamer Memory)
            Column(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "LOG NUMBER",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFA1A1AA),
                    letterSpacing = 0.5.sp
                )
                Spacer(modifier = Modifier.height(6.dp))

                OutlinedTextField(
                    value = logNumber,
                    onValueChange = onLogNumberChanged,
                    singleLine = true,
                    textStyle = LocalTextStyle.current.copy(
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Black,
                        fontFamily = FontFamily.Monospace,
                        color = Color.White
                    ),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedContainerColor = Color(0xFF18181B),
                        unfocusedContainerColor = Color(0xFF18181B),
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        focusedBorderColor = Color.White,
                        unfocusedBorderColor = Color(0xFF27272A)
                    ),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp)
                )
            }
        }

        // Bottom Action Group
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Auditor Tasks Banner (Only if tasks exist)
            if (openTaskCount > 0) {
                Surface(
                    color = Color(0xFF27272A),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onViewTasks() }
                        .padding(bottom = 14.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 14.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "AUDIT TASKS ($openTaskCount)",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFFBBF24)
                        )
                        Text(
                            text = "VIEW >",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }
            }

            // Start Scanning Session
            Button(
                onClick = onStartScanning,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(54.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color.White)
            ) {
                Text(
                    text = "START SCAN",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Black,
                    color = Color.Black,
                    letterSpacing = 0.5.sp
                )
            }

            Spacer(modifier = Modifier.height(10.dp))
        }
    }
}

// =========================================================================
// 3. CAMERA SCANNER SCREEN (Zero-Delay Shutter, Vector Icon, Edge Mode Flash)
// =========================================================================
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CameraScannerScreen(
    aircraft: String,
    onAircraftChange: (String) -> Unit,
    aircraftOptions: List<String>,
    dateText: String,
    logNumber: String,
    onLogNumberChange: (String) -> Unit,
    isPatchMode: Boolean,
    patchReason: String,
    onExitToSetup: () -> Unit
) {
    val context = LocalContext.current
    val view = LocalView.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val coroutineScope = rememberCoroutineScope()
    val prefs = remember { context.getSharedPreferences("techlog_scanner_prefs", Context.MODE_PRIVATE) }

    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasCameraPermission = granted
    }

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    // 1-TAP VIEWFINDER TOGGLE: PORTRAIT (0°) VS LANDSCAPE (-90°)
    var isLandscapeMode by remember { mutableStateOf(false) }

    var currentLogNumber by remember { mutableStateOf(logNumber) }
    var aircraftMenuExpanded by remember { mutableStateOf(false) }

    // Captured pages dock (Strict FIFO order)
    val capturedPages = remember { mutableStateListOf<ScannedPage>() }
    val sequenceCounter = remember { AtomicInteger(1) }

    // Instant Shutter Flash effect trigger
    var shutterFlashTrigger by remember { mutableStateOf(false) }
    LaunchedEffect(shutterFlashTrigger) {
        if (shutterFlashTrigger) {
            delay(75)
            shutterFlashTrigger = false
        }
    }

    // Background upload & save status and shutter debounce
    var activeSaveState by remember { mutableStateOf<SaveProgressState?>(null) }
    var lastShutterTapTime by remember { mutableStateOf(0L) }
    var modeFlashText by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(modeFlashText) {
        if (modeFlashText != null) {
            delay(1200)
            modeFlashText = null
        }
    }

    // Camera executor & controls
    val cameraExecutor = remember { Executors.newSingleThreadExecutor() }
    var cameraControl by remember { mutableStateOf<CameraControl?>(null) }
    var previewViewInstance by remember { mutableStateOf<PreviewView?>(null) }
    var isTorchOn by remember { mutableStateOf(false) }

    val imageCapture = remember {
        ImageCapture.Builder()
            .setTargetRotation(Surface.ROTATION_0)
            .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
            .setFlashMode(ImageCapture.FLASH_MODE_OFF)
            .build()
    }

    val targetFileName = remember(aircraft, dateText, currentLogNumber, isPatchMode, patchReason) {
        if (isPatchMode) {
            "${aircraft}_TL${currentLogNumber.padStart(6, '0')}_PATCH_${patchReason}.pdf"
        } else {
            buildDoyceTechlogFilename(aircraft, dateText, currentLogNumber)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .navigationBarsPadding()
    ) {
        // TOP BAR: SWITCHER, CONTROLS & EXIT
        Surface(
            color = Color(0xFF141416),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 14.dp, vertical = 8.dp)
            ) {
                // Top Row: Setup link, Torch Toggle, and Orientation Indicator
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "< SETUP",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White,
                            modifier = Modifier
                                .clickable { onExitToSetup() }
                                .padding(end = 12.dp)
                        )
                        if (isPatchMode) {
                            Text(
                                text = "PATCH",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFFF59E0B)
                            )
                        }
                    }

                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        // Torch Toggle
                        Surface(
                            color = if (isTorchOn) Color.White else Color(0xFF27272A),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.clickable {
                                val next = !isTorchOn
                                cameraControl?.enableTorch(next)
                                isTorchOn = next
                            }
                        ) {
                            Text(
                                text = if (isTorchOn) "TORCH ON" else "TORCH",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isTorchOn) Color.Black else Color.White,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                            )
                        }

                        // Orientation badge (Single-Tap to toggle)
                        Surface(
                            color = if (isLandscapeMode) Color(0xFF8B5CF6) else Color(0xFF27272A),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.clickable {
                                isLandscapeMode = !isLandscapeMode
                                modeFlashText = if (isLandscapeMode) "LANDSCAPE" else "PORTRAIT"
                            }
                        ) {
                            Text(
                                text = if (isLandscapeMode) "LANDSCAPE" else "PORTRAIT",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Metadata Quick Controls Row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Aircraft Selector Dropdown
                    Box(modifier = Modifier.weight(1.2f)) {
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFF27272A),
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(40.dp)
                                .clickable { aircraftMenuExpanded = true }
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(horizontal = 10.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    text = aircraft,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                                Text(text = "▼", fontSize = 9.sp, color = Color(0xFFA1A1AA))
                            }
                        }

                        DropdownMenu(
                            expanded = aircraftMenuExpanded,
                            onDismissRequest = { aircraftMenuExpanded = false },
                            modifier = Modifier.background(Color(0xFF18181B))
                        ) {
                            aircraftOptions.forEach { reg ->
                                DropdownMenuItem(
                                    text = { Text(reg, fontWeight = FontWeight.Bold, fontSize = 15.sp, color = Color.White) },
                                    onClick = {
                                        onAircraftChange(reg)
                                        aircraftMenuExpanded = false
                                    }
                                )
                            }
                        }
                    }

                    // Date Label
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = Color(0xFF1C1C1E),
                        modifier = Modifier
                            .weight(1.5f)
                            .height(40.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(
                                text = dateText,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFFA1A1AA)
                            )
                        }
                    }

                    // Log Number Field
                    OutlinedTextField(
                        value = currentLogNumber,
                        onValueChange = {
                            currentLogNumber = it
                            onLogNumberChange(it)
                        },
                        singleLine = true,
                        textStyle = LocalTextStyle.current.copy(
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Black,
                            fontFamily = FontFamily.Monospace,
                            color = Color.White
                        ),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = Color(0xFF27272A),
                            unfocusedContainerColor = Color(0xFF27272A),
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedBorderColor = Color.White,
                            unfocusedBorderColor = Color.Transparent
                        ),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier
                            .weight(1.1f)
                            .height(48.dp)
                    )
                }

                // Elevated Background Save & Sync Status Card
                activeSaveState?.let { state ->
                    Spacer(modifier = Modifier.height(6.dp))
                    Surface(
                        color = when {
                            state.isSuccess -> Color(0xFF064E3B)
                            state.isError -> Color(0xFF450A0A)
                            else -> Color(0xFF131B2E)
                        },
                        shape = RoundedCornerShape(10.dp),
                        border = BorderStroke(
                            1.dp,
                            when {
                                state.isSuccess -> Color(0xFF10B981)
                                state.isError -> Color(0xFFEF4444)
                                else -> Color(0xFF2563EB)
                            }
                        ),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = when {
                                        state.isSuccess -> "SAVE COMPLETED"
                                        state.isError -> "SAVE FAILED — PAGES RESTORED"
                                        else -> "BACKGROUND SAVE ACTIVE"
                                    },
                                    color = when {
                                        state.isSuccess -> Color(0xFF34D399)
                                        state.isError -> Color(0xFFF87171)
                                        else -> Color(0xFF60A5FA)
                                    },
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.ExtraBold,
                                    letterSpacing = 0.5.sp
                                )

                                Surface(
                                    color = if (state.inProgress) Color(0xFF064E3B) else Color(0xFF27272A),
                                    shape = RoundedCornerShape(4.dp)
                                ) {
                                    Text(
                                        text = if (state.inProgress) "CAMERA IS LIVE" else "READY",
                                        color = if (state.inProgress) Color(0xFFA7F3D0) else Color(0xFF94A3B8),
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.Bold,
                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(4.dp))

                            Text(
                                text = state.fileName,
                                color = Color.White,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold
                            )

                            Text(
                                text = state.errorMessage ?: state.stage,
                                color = if (state.isError) Color(0xFFFCA5A5) else Color(0xFFCBD5E1),
                                fontSize = 11.sp
                            )

                            if (state.inProgress) {
                                Spacer(modifier = Modifier.height(6.dp))
                                LinearProgressIndicator(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(3.dp),
                                    color = Color(0xFF10B981),
                                    trackColor = Color(0xFF1E293B)
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "Camera is live and ready for next scan — zero waiting needed",
                                    color = Color(0xFF6EE7B7),
                                    fontSize = 10.sp,
                                    fontStyle = androidx.compose.ui.text.font.FontStyle.Italic
                                )
                            }
                        }
                    }
                }
            }
        }

        // CENTER VIEWFINDER: HARDWARE PREVIEWVIEW + PACKAGING VECTOR ICON + INSTANT FEEDBACK
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .background(Color.Black)
                .clickable {
                    // Tap on viewfinder toggles Portrait vs Landscape
                    isLandscapeMode = !isLandscapeMode
                    modeFlashText = if (isLandscapeMode) "LANDSCAPE" else "PORTRAIT"
                },
            contentAlignment = Alignment.Center
        ) {
            if (hasCameraPermission) {
                AndroidView(
                    factory = { ctx ->
                        val previewView = PreviewView(ctx).apply {
                            layoutParams = ViewGroup.LayoutParams(
                                ViewGroup.LayoutParams.MATCH_PARENT,
                                ViewGroup.LayoutParams.MATCH_PARENT
                            )
                            implementationMode = PreviewView.ImplementationMode.COMPATIBLE
                            scaleType = PreviewView.ScaleType.FILL_CENTER
                        }
                        previewViewInstance = previewView

                        val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
                        cameraProviderFuture.addListener({
                            val cameraProvider = cameraProviderFuture.get()
                            val preview = Preview.Builder()
                                .setTargetRotation(Surface.ROTATION_0)
                                .build()
                                .also {
                                    it.setSurfaceProvider(previewView.surfaceProvider)
                                }

                            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

                            try {
                                cameraProvider.unbindAll()
                                val camera = cameraProvider.bindToLifecycle(
                                    lifecycleOwner,
                                    cameraSelector,
                                    preview,
                                    imageCapture
                                )
                                cameraControl = camera.cameraControl
                            } catch (e: Exception) {
                                e.printStackTrace()
                            }
                        }, ContextCompat.getMainExecutor(ctx))

                        previewView
                    },
                    modifier = Modifier.fillMaxSize()
                )
            }

            // UNIFIED VECTOR DRAWABLE: "THIS SIDE UP" + ROTATION ARROW (NEVER SCATTERS)
            ThisSideUpPackagingSign(
                isLandscape = isLandscapeMode,
                modifier = Modifier.align(Alignment.Center)
            )

            // INSTANT WHITE SHUTTER FLASH OVERLAY (75ms NATIVE CAMERA FEEL)
            if (shutterFlashTrigger) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.White)
                )
            }

            // 1-SECOND TRANSIENT MODE FLASH: TOWARDS TOP OF RESPECTIVE ORIENTATION
            if (modeFlashText != null) {
                if (isLandscapeMode) {
                    // TOP OF LANDSCAPE IS PHYSICALLY THE RIGHT EDGE OF PORTRAIT SCREEN
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(end = 20.dp),
                        contentAlignment = Alignment.CenterEnd
                    ) {
                        Surface(
                            color = Color(0xDD000000),
                            shape = RoundedCornerShape(12.dp),
                            border = BorderStroke(1.5.dp, Color(0xFF8B5CF6)),
                            modifier = Modifier.graphicsLayer {
                                rotationZ = 90f
                            }
                        ) {
                            Text(
                                text = "LANDSCAPE",
                                color = Color.White,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Black,
                                letterSpacing = 1.2.sp,
                                modifier = Modifier.padding(horizontal = 22.dp, vertical = 9.dp)
                            )
                        }
                    }
                } else {
                    // TOP OF PORTRAIT SCREEN
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(top = 28.dp),
                        contentAlignment = Alignment.TopCenter
                    ) {
                        Surface(
                            color = Color(0xDD000000),
                            shape = RoundedCornerShape(12.dp),
                            border = BorderStroke(1.5.dp, Color.White),
                            modifier = Modifier.graphicsLayer {
                                rotationZ = 0f
                            }
                        ) {
                            Text(
                                text = "PORTRAIT",
                                color = Color.White,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Black,
                                letterSpacing = 1.2.sp,
                                modifier = Modifier.padding(horizontal = 22.dp, vertical = 9.dp)
                            )
                        }
                    }
                }
            }
        }

        // BOTTOM THUMBNAIL DOCK & SHUTTER ACTION BAR
        Surface(
            color = Color(0xFF000000),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 14.dp, vertical = 8.dp)
            ) {
                // Pages counter
                if (capturedPages.isNotEmpty()) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "${capturedPages.size} PAGES",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFA1A1AA)
                        )
                        Text(
                            text = targetFileName,
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            color = Color(0xFFA1A1AA),
                            maxLines = 1
                        )
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                }

                // Horizontal Thumbnails Strip (STRICT FIFO ORDER)
                if (capturedPages.isNotEmpty()) {
                    LazyRow(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(64.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        items(capturedPages, key = { it.sequenceNumber }) { page ->
                            val displayIndex = capturedPages.indexOf(page) + 1
                            Box(
                                modifier = Modifier
                                    .width(if (page.isLandscape) 64.dp else 48.dp)
                                    .height(60.dp)
                            ) {
                                Surface(
                                    shape = RoundedCornerShape(6.dp),
                                    color = Color(0xFF18181B),
                                    border = BorderStroke(1.dp, Color(0xFF27272A)),
                                    modifier = Modifier
                                        .fillMaxSize()
                                        .padding(top = 4.dp, end = 4.dp)
                                ) {
                                    Box {
                                        Image(
                                            bitmap = page.bitmap.asImageBitmap(),
                                            contentDescription = "Page $displayIndex",
                                            contentScale = ContentScale.Crop,
                                            modifier = Modifier.fillMaxSize()
                                        )
                                        Surface(
                                            color = Color(0xDD000000),
                                            shape = RoundedCornerShape(topStart = 4.dp),
                                            modifier = Modifier.align(Alignment.BottomEnd)
                                        ) {
                                            Text(
                                                text = "P$displayIndex",
                                                fontSize = 9.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = Color.White,
                                                modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
                                            )
                                        }
                                    }
                                }

                                // Instant Single-Tap 'X' Delete
                                Surface(
                                    color = Color(0xFFEF4444),
                                    shape = CircleShape,
                                    modifier = Modifier
                                        .size(18.dp)
                                        .align(Alignment.TopEnd)
                                        .clickable {
                                            capturedPages.remove(page)
                                        }
                                ) {
                                    Box(contentAlignment = Alignment.Center) {
                                        Text(
                                            text = "✕",
                                            color = Color.White,
                                            fontSize = 9.sp,
                                            fontWeight = FontWeight.ExtraBold
                                        )
                                    }
                                }
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                }

                // Bottom Action Bar: Reset (Left), Perfectly Centered Shutter (Center), Save PDF (Right)
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp),
                    contentAlignment = Alignment.Center
                ) {
                    // Reset Button (Pinned to Left)
                    Text(
                        text = "RESET",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (capturedPages.isNotEmpty()) Color(0xFFEF4444) else Color(0xFF3F3F46),
                        modifier = Modifier
                            .align(Alignment.CenterStart)
                            .clickable(enabled = capturedPages.isNotEmpty()) {
                                capturedPages.clear()
                                sequenceCounter.set(1)
                            }
                            .padding(8.dp)
                    )

                    // PROMINENT SHUTTER BUTTON (STRICT DEAD CENTER HORIZONTALLY)
                    Box(
                        modifier = Modifier
                            .align(Alignment.Center)
                            .size(66.dp)
                            .background(Color.Transparent, CircleShape)
                            .border(3.dp, Color.White, CircleShape)
                            .clickable {
                                // 450ms Shutter Debounce (Prevents accidental double taps in hangar)
                                val now = android.os.SystemClock.uptimeMillis()
                                if (now - lastShutterTapTime < 450L) return@clickable
                                lastShutterTapTime = now

                                val currentSeq = sequenceCounter.getAndIncrement()
                                val snapInLandscape = isLandscapeMode

                                // 1. INSTANT WHITE FLASH & HAPTIC VIBRATION
                                shutterFlashTrigger = true
                                view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)

                                // 2. INSTANT PREVIEW THUMBNAIL DOCKING (0ms WAIT)
                                val liveFrame = previewViewInstance?.bitmap
                                val thumbBitmap = if (liveFrame != null) {
                                    val scaled = Bitmap.createScaledBitmap(liveFrame, 160, 213, true)
                                    if (snapInLandscape) {
                                        val mat = Matrix().apply { postRotate(-90f) }
                                        Bitmap.createBitmap(scaled, 0, 0, scaled.width, scaled.height, mat, true)
                                    } else {
                                        scaled
                                    }
                                } else {
                                    Bitmap.createBitmap(160, 213, Bitmap.Config.ARGB_8888)
                                }

                                val pageEntry = ScannedPage(
                                    sequenceNumber = currentSeq,
                                    bitmap = thumbBitmap,
                                    isLandscape = snapInLandscape,
                                    isHighResReady = false
                                )
                                capturedPages.add(pageEntry)

                                // 3. BACKGROUND HIGH-RES SENSOR CAPTURE
                                imageCapture.takePicture(
                                    cameraExecutor,
                                    object : ImageCapture.OnImageCapturedCallback() {
                                        override fun onCaptureSuccess(image: ImageProxy) {
                                            val rawBitmap = imageProxyToRawBitmap(image)
                                            image.close()
                                            ContextCompat.getMainExecutor(context).execute {
                                                pageEntry.bitmap = rawBitmap
                                                pageEntry.isHighResReady = true
                                            }
                                        }

                                        override fun onError(exception: ImageCaptureException) {
                                            exception.printStackTrace()
                                        }
                                    }
                                )
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Box(
                            modifier = Modifier
                                .size(50.dp)
                                .background(Color.White, CircleShape)
                        )
                    }

                    // SAVE PDF BUTTON (Pinned to Right)
                    Button(
                        onClick = {
                            if (capturedPages.isNotEmpty()) {
                                val pagesToSave = capturedPages.toList()
                                val lastPagesBackup = pagesToSave.toList()
                                val fileNameToSave = targetFileName
                                val acFolder = aircraft.removePrefix("5N-")

                                // 1. INSTANTLY CLEAR DOCK & RE-ENABLE CONTINUOUS SNAPPING
                                capturedPages.clear()
                                sequenceCounter.set(1)

                                // 2. AUTO-INCREMENT & PERSIST IN PER-AIRCRAFT MEMORY (RENAMER ARCHITECTURE)
                                if (!isPatchMode) {
                                    saveLastLogForAircraft(prefs, aircraft, currentLogNumber)
                                    val currentNum = currentLogNumber.toIntOrNull() ?: 1
                                    val nextLog = String.format("%0${currentLogNumber.length}d", currentNum + 1)
                                    currentLogNumber = nextLog
                                    onLogNumberChange(nextLog)
                                }

                                // 3. NON-BLOCKING POST-PRODUCTION: ROTATION, COMPRESSION & PDF EXPORT
                                val isCloudActive = MicrosoftOAuthManager.isConnected(prefs)
                                activeSaveState = SaveProgressState(
                                    fileName = fileNameToSave,
                                    stage = if (isCloudActive) "Optimizing & uploading to OneDrive..." else "Optimizing & saving locally...",
                                    inProgress = true
                                )

                                coroutineScope.launch(Dispatchers.IO) {
                                    // Ensure high-res sensor buffers have finished decoding if tapped immediately
                                    var waitMs = 0
                                    while (pagesToSave.any { !it.isHighResReady } && waitMs < 2500) {
                                        delay(100)
                                        waitMs += 100
                                    }

                                    val (saved, savedToCloud, cloudMsg) = compileAndSaveOptimizedPdf(
                                        context = context,
                                        pages = pagesToSave,
                                        aircraftFolder = acFolder,
                                        fileName = fileNameToSave,
                                        isPatch = isPatchMode,
                                        onProgress = { stepDesc ->
                                            activeSaveState = activeSaveState?.copy(stage = stepDesc)
                                        }
                                    )

                                    withContext(Dispatchers.Main) {
                                        if (saved) {
                                            view.performHapticFeedback(HapticFeedbackConstants.CONFIRM)
                                            val successMsg = if (savedToCloud) {
                                                "Uploaded to SPLIT/$acFolder on OneDrive"
                                            } else if (isCloudActive) {
                                                "Saved locally. Cloud: $cloudMsg"
                                            } else {
                                                "Saved locally to Documents"
                                            }
                                            activeSaveState = SaveProgressState(
                                                fileName = fileNameToSave,
                                                stage = successMsg,
                                                inProgress = false,
                                                isSuccess = true
                                            )
                                            // Persistent 4-second success badge before auto-clearing
                                            delay(4000)
                                            if (activeSaveState?.isSuccess == true) {
                                                activeSaveState = null
                                            }
                                        } else {
                                            // DATA-LOSS GUARD: Restore pages so user can retry!
                                            capturedPages.clear()
                                            capturedPages.addAll(lastPagesBackup)
                                            sequenceCounter.set(capturedPages.size + 1)
                                            view.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)

                                            activeSaveState = SaveProgressState(
                                                fileName = fileNameToSave,
                                                stage = "Save failed",
                                                inProgress = false,
                                                isError = true,
                                                errorMessage = "Failed to save PDF. Pages restored to camera dock."
                                            )
                                            Toast.makeText(context, "Save failed. Scanned pages restored to dock for retry.", Toast.LENGTH_LONG).show()
                                        }
                                    }
                                }
                            }
                        },
                        enabled = capturedPages.isNotEmpty(),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF10B981),
                            disabledContainerColor = Color(0xFF27272A)
                        ),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.align(Alignment.CenterEnd)
                    ) {
                        Text(
                            text = if (isPatchMode) "SAVE PATCH" else "SAVE PDF",
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp,
                            color = if (capturedPages.isNotEmpty()) Color.White else Color(0xFF71717A)
                        )
                    }
                }
            }
        }
    }
}

// =========================================================================
// PACKAGING "THIS SIDE UP" SIGN COMPONENT (Unified Vector Resource)
// =========================================================================
@Composable
fun ThisSideUpPackagingSign(
    isLandscape: Boolean,
    modifier: Modifier = Modifier
) {
    val rotationAngle by animateFloatAsState(
        targetValue = if (isLandscape) 90f else 0f,
        animationSpec = tween(durationMillis = 350)
    )

    Image(
        painter = painterResource(id = R.drawable.ic_this_side_up),
        contentDescription = null,
        modifier = modifier
            .size(100.dp, 70.dp)
            .graphicsLayer {
                rotationZ = rotationAngle
            }
    )
}

// =========================================================================
// 4. AUDITOR TASKS SCREEN (Reviewer Comments, Complete Re-scan & Patches)
// =========================================================================
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AuditorTasksScreen(
    tasks: List<AuditorTask>,
    onSelectCompleteRescan: (AuditorTask) -> Unit,
    onSelectPatchScan: (AuditorTask) -> Unit,
    onBack: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "< BACK",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White,
                modifier = Modifier
                    .clickable { onBack() }
                    .padding(end = 12.dp)
            )
            Text(
                text = "AUDIT TASKS",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (tasks.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(top = 40.dp),
                contentAlignment = Alignment.TopCenter
            ) {
                Surface(
                    color = Color(0xFF18181B),
                    shape = RoundedCornerShape(12.dp),
                    border = BorderStroke(1.dp, Color(0xFF27272A)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "NO OPEN AUDIT TASKS",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(tasks) { task ->
                    Card(
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF18181B)),
                        border = BorderStroke(1.dp, Color(0xFF27272A)),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    text = "${task.aircraft} • LOG #${task.logNumber}",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    color = Color.White
                                )
                                Text(
                                    text = task.date,
                                    fontSize = 11.sp,
                                    color = Color(0xFFA1A1AA)
                                )
                            }

                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = task.description,
                                fontSize = 13.sp,
                                color = Color(0xFFA1A1AA)
                            )

                            Spacer(modifier = Modifier.height(12.dp))

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                OutlinedButton(
                                    onClick = { onSelectPatchScan(task) },
                                    shape = RoundedCornerShape(8.dp),
                                    modifier = Modifier.weight(1f)
                                ) {
                                    Text("Patch", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color.White)
                                }
                                Button(
                                    onClick = { onSelectCompleteRescan(task) },
                                    shape = RoundedCornerShape(8.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color.White),
                                    modifier = Modifier.weight(1f)
                                ) {
                                    Text("Re-Scan", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color.Black)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// =========================================================================
// 5. UTILITIES & POST-PRODUCTION PROCESSING
// =========================================================================

fun formatDisplayDate(cal: Calendar): String {
    val day = cal.get(Calendar.DAY_OF_MONTH)
    val month = SimpleDateFormat("MMMM", Locale.US).format(cal.time).uppercase(Locale.US)
    val year = cal.get(Calendar.YEAR)
    return "$day $month $year"
}

fun buildDoyceTechlogFilename(reg: String, dateText: String, numStr: String): String {
    val cleanNum = numStr.padStart(6, '0')
    val parts = dateText.split(" ")
    val day = parts.getOrNull(0)?.toIntOrNull() ?: 28
    val month = parts.getOrNull(1)?.uppercase(Locale.US) ?: "OCTOBER"
    val year = parts.getOrNull(2) ?: "2026"

    val daySuffix = when {
        day in 11..13 -> "TH"
        day % 10 == 1 -> "ST"
        day % 10 == 2 -> "ND"
        day % 10 == 3 -> "RD"
        else -> "TH"
    }
    val dayRepr = "${day}${daySuffix}"

    // Exact Doyce formula: 5N-<REG> <DAY>, <MONTH> <YEAR> TECHLOG B  <LOGNUM>.pdf
    return "$reg $dayRepr, $month $year TECHLOG B  $cleanNum.pdf"
}

/**
 * 100% LIGHTWEIGHT RAW CAPTURE: Zero sensor work and zero rotation during capture.
 */
fun imageProxyToRawBitmap(image: ImageProxy): Bitmap {
    val buffer = image.planes[0].buffer
    val bytes = ByteArray(buffer.remaining())
    buffer.get(bytes)
    val original = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)

    val sensorRotation = image.imageInfo.rotationDegrees
    val matrix = Matrix()
    if (sensorRotation != 0) {
        matrix.postRotate(sensorRotation.toFloat())
    }

    return if (!matrix.isIdentity) {
        Bitmap.createBitmap(original, 0, 0, original.width, original.height, matrix, true)
    } else {
        original
    }
}

/**
 * ALL ROTATION AND COMPRESSION DONE STRICTLY IN POST-PRODUCTION (BACKGROUND THREAD).
 * Rotates -90° if tagged Landscape, downsamples to 1600px, compresses via JPEG 78%,
 * writes to PDF, and immediately discards all raw images to free phone memory.
 */
suspend fun compileAndSaveOptimizedPdf(
    context: Context,
    pages: List<ScannedPage>,
    aircraftFolder: String,
    fileName: String,
    isPatch: Boolean,
    onProgress: ((String) -> Unit)? = null
): Triple<Boolean, Boolean, String> = withContext(Dispatchers.IO) {
    val pdfDocument = PdfDocument()

    try {
        val sortedPages = pages.sortedBy { it.sequenceNumber }

        for ((index, page) in sortedPages.withIndex()) {
            onProgress?.invoke("Optimizing & rendering page ${index + 1}/${sortedPages.size}...")
            val raw = page.bitmap

            // POST-PRODUCTION STEP 1: Downscale to clean document resolution (1600px max)
            val maxDim = 1600
            val w = raw.width
            val h = raw.height
            val scale = if (w > maxDim || h > maxDim) {
                maxDim.toFloat() / maxOf(w, h)
            } else 1.0f
            val scaledW = (w * scale).toInt()
            val scaledH = (h * scale).toInt()
            val scaled = Bitmap.createScaledBitmap(raw, scaledW, scaledH, true)

            // POST-PRODUCTION STEP 2: Rotate by -90° if operator flagged as Landscape
            val finalBitmap = if (page.isLandscape) {
                val rotMatrix = Matrix().apply { postRotate(-90f) }
                Bitmap.createBitmap(scaled, 0, 0, scaled.width, scaled.height, rotMatrix, true)
            } else {
                scaled
            }

            // POST-PRODUCTION STEP 3: DIRECT CANVAS EMBEDDING (Zero redundant JPEG encode-decode loop)
            val pageW = finalBitmap.width
            val pageH = finalBitmap.height

            val pageInfo = PdfDocument.PageInfo.Builder(pageW, pageH, index + 1).create()
            val pdfPage = pdfDocument.startPage(pageInfo)
            val canvas = pdfPage.canvas

            val destRect = Rect(0, 0, pageW, pageH)
            val paint = Paint().apply { isFilterBitmap = true }
            canvas.drawBitmap(finalBitmap, null, destRect, paint)

            pdfDocument.finishPage(pdfPage)

            // Discard bitmaps immediately
            if (finalBitmap != scaled) finalBitmap.recycle()
            if (scaled != raw) scaled.recycle()
            raw.recycle()
        }

        onProgress?.invoke("Writing PDF file...")
        // Cache PDF file for multi-destination distribution
        val tempPdfFile = File(context.cacheDir, "scan_${System.currentTimeMillis()}_$fileName")
        FileOutputStream(tempPdfFile).use { outputStream ->
            pdfDocument.writeTo(outputStream)
        }

        val prefs = context.getSharedPreferences("techlog_scanner_prefs", Context.MODE_PRIVATE)

        // 1. UPLOAD TO BACKEND (WHICH STREAMS INTO ISAAC EKE'S ONEDRIVE APPFOLDER)
        var savedToCloud = false
        var cloudMessage = ""
        if (MicrosoftOAuthManager.isConnected(prefs)) {
            onProgress?.invoke("Streaming to Isaac Eke's OneDrive...")
            val (cloudSuccess, msg) = MicrosoftOAuthManager.uploadPdfToBackend(
                prefs = prefs,
                pdfFile = tempPdfFile,
                aircraftFolder = aircraftFolder,
                fileName = fileName,
                isPatch = isPatch
            )
            savedToCloud = cloudSuccess
            cloudMessage = msg
        }

        // 2. SAF SYNC WRITE (If external tree is optionally linked)
        val treeUriStr = prefs.getString("onedrive_tree_uri", null)
        if (treeUriStr != null) {
            try {
                val treeUri = Uri.parse(treeUriStr)
                val rootDoc = DocumentFile.fromTreeUri(context, treeUri)
                if (rootDoc != null && rootDoc.canWrite()) {
                    val aircraftDir = rootDoc.findFile(aircraftFolder) ?: rootDoc.createDirectory(aircraftFolder)
                    val targetDir = if (isPatch) {
                        aircraftDir?.findFile("patches") ?: aircraftDir?.createDirectory("patches")
                    } else {
                        aircraftDir
                    }

                    if (targetDir != null) {
                        val existing = targetDir.findFile(fileName)
                        existing?.delete()

                        val newFile = targetDir.createFile("application/pdf", fileName)
                        if (newFile != null) {
                            context.contentResolver.openOutputStream(newFile.uri)?.use { outputStream ->
                                tempPdfFile.inputStream().use { it.copyTo(outputStream) }
                            }
                            savedToCloud = true
                        }
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }

        // 3. LOCAL DOCUMENTS STORAGE
        val subPath = if (isPatch) {
            "EnuguAirScanner/SPLIT/$aircraftFolder/patches"
        } else {
            "EnuguAirScanner/SPLIT/$aircraftFolder"
        }

        var savedLocally = false
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val contentValues = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, fileName)
                put(MediaStore.MediaColumns.MIME_TYPE, "application/pdf")
                put(MediaStore.MediaColumns.RELATIVE_PATH, "${Environment.DIRECTORY_DOCUMENTS}/$subPath")
            }

            val uri = context.contentResolver.insert(MediaStore.Files.getContentUri("external"), contentValues)
            if (uri != null) {
                context.contentResolver.openOutputStream(uri)?.use { outputStream ->
                    tempPdfFile.inputStream().use { it.copyTo(outputStream) }
                }
                savedLocally = true
            }
        }

        if (!savedLocally) {
            val docDir = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS), subPath)
            if (!docDir.exists()) docDir.mkdirs()

            val targetFile = File(docDir, fileName)
            if (targetFile.exists()) {
                val backupFile = File(docDir, "$fileName.bak")
                if (backupFile.exists()) backupFile.delete()
                targetFile.renameTo(backupFile)
            }

            FileOutputStream(targetFile).use { outputStream ->
                tempPdfFile.inputStream().use { it.copyTo(outputStream) }
            }
            savedLocally = true
        }

        // Clean up temporary cache file
        if (tempPdfFile.exists()) {
            tempPdfFile.delete()
        }

        return@withContext Triple(savedLocally || savedToCloud, savedToCloud, cloudMessage)
    } catch (e: Exception) {
        e.printStackTrace()
        return@withContext Triple(false, false, e.message ?: "PDF generation error")
    } finally {
        pdfDocument.close()
    }
}
