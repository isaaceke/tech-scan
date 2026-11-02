"""Build the scanner with public folder IDs; no owner token enters the APK."""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / ".SCRATCH/sample_app"
CONFIG = PROJECT / "app/src/main/assets/scanner_folder.json"
SERVICE_CONFIG = PROJECT / "app/src/main/assets/scanner_service.json"


def validate_online_service(config, service, opener=urllib.request.urlopen):
    if service.get("mode") != "online":
        raise RuntimeError("The updated scanner must use the online upload service.")
    url = service.get("server_url", "").strip().rstrip("/")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        raise RuntimeError("Online scanner hosting is not configured. The existing APK has not been replaced.")
    with opener(urllib.request.Request(url + "/health", headers={"Accept": "application/json", "User-Agent": "EnuguTechlogScanner/1.4"}), timeout=20) as response:
        if "application/json" not in response.headers.get("Content-Type", ""):
            raise RuntimeError("The configured address is not the scanner upload service.")
        health = json.load(response)
    if health.get("service") != "enugu-scanner-relay" or not health.get("storage_connected"):
        raise RuntimeError("Sign in as owner in the online panel before publishing the APK.")
    if service.get("hosting") == "firebase-google-cloud":
        if health.get("hosting") != "firebase-google-cloud" or not parsed.hostname.endswith(".run.app"):
            raise RuntimeError("The scanner must use its verified Google Cloud Run address for uploads.")
        if health.get("delivery_mode") != "direct":
            raise RuntimeError("The scanner service does not match the approved direct-delivery workflow.")
    if service.get("hosting") == "cloudflare":
        if health.get("hosting") != "cloudflare" or not parsed.hostname.endswith(".workers.dev"):
            raise RuntimeError("The scanner must use its verified Cloudflare Workers address for uploads.")
        if health.get("delivery_mode") != "direct":
            raise RuntimeError("The scanner service does not match the approved direct-delivery workflow.")
    if any(health.get("destination", {}).get(key) != config.get(key) for key in ("drive_id", "folder_id", "owner_id")):
        raise RuntimeError("The online service addresses a different scanner folder.")
    return url


def source_snapshot():
    paths = list((PROJECT / "app/src").rglob("*"))
    paths += [PROJECT / path for path in ("app/build.gradle.kts", "build.gradle.kts", "settings.gradle.kts", "gradle/libs.versions.toml")]
    return {str(path.relative_to(PROJECT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file()}


def build_apk(progress=lambda line: None, preview=False):
    config_bytes = CONFIG.read_bytes()
    sources = source_snapshot()
    config = json.loads(config_bytes)
    if not preview and not all(config.get(key) for key in ("drive_id", "folder_id", "owner_id")):
        raise RuntimeError("Sign in as owner in the panel to connect the folder before building the APK.")
    service_bytes = SERVICE_CONFIG.read_bytes()
    if not preview:
        validate_online_service(config, json.loads(service_bytes))
    jdk = Path(r"C:\Users\HP\AppData\Local\Java\jdk-17")
    if not (jdk / "bin/java.exe").is_file():
        raise RuntimeError("The installed Java 17 runtime was not found.")
    output_dir = Path(tempfile.mkdtemp(prefix="EnuguScannerBuild_")) / "app"
    env = {**os.environ, "JAVA_HOME": str(jdk)}
    command = ["cmd.exe", "/d", "/c", "gradlew.bat", "--no-daemon",
               "--no-configuration-cache", "--no-build-cache", f"-PscannerBuildDir={output_dir}", "testDebugUnitTest", "assembleDebug"]
    progress("Building the APK in a fresh temporary directory…")
    with subprocess.Popen(command, cwd=PROJECT, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                          creationflags=subprocess.CREATE_NO_WINDOW) as process:
        for line in process.stdout:
            if line.strip():
                progress(line.strip())
        code = process.wait()
    if code:
        raise RuntimeError("APK build failed. The existing TECHLOG SCAN.apk has not been replaced.")
    if source_snapshot() != sources:
        raise RuntimeError("The app source changed during the build. Build again before distributing it.")
    results = output_dir / "test-results/testDebugUnitTest"
    if not list(results.glob("TEST-*.xml")):
        raise RuntimeError("Android authorization test results are missing. The existing APK has not been replaced.")
    evidence = ROOT / ".build/android-unit-test-results"
    evidence.mkdir(parents=True, exist_ok=True)
    for result in results.glob("TEST-*.xml"):
        shutil.copy2(result, evidence / result.name)
    apk = output_dir / "outputs/apk/debug/app-debug.apk"
    with zipfile.ZipFile(apk) as archive:
        if archive.read("assets/scanner_folder.json") != config_bytes:
            raise RuntimeError("The APK folder configuration did not match the panel.")
        if archive.read("assets/scanner_service.json") != service_bytes:
            raise RuntimeError("The APK online service configuration did not match the panel.")
    if CONFIG.read_bytes() != config_bytes:
        raise RuntimeError("The folder configuration changed during the build. Build again.")
    target = ROOT / (".build/TECHLOG SCAN.folder-preview.apk" if preview else "TECHLOG SCAN.apk")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not preview:
        backup_dir = ROOT / ".build/apk-backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        shutil.copy2(target, backup_dir / ("TECHLOG SCAN." + timestamp + ".apk"))
    temporary = target.with_suffix(".building.apk")
    shutil.copy2(apk, temporary)
    temporary.replace(target)
    return str(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="Compile a clearly marked preview before owner setup")
    arguments = parser.parse_args()
    try:
        print(build_apk(print, preview=arguments.preview))
    except Exception as error:
        print(str(error))
        raise SystemExit(1)
