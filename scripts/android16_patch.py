from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"[{label}] expected source block not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"[OK] {label}: {path}")


# Android 16 / API 36 toolchain.
versions = ROOT / "libs.versions.toml"
replace_once(versions, 'compileSdk = "35"', 'compileSdk = "36"', "compileSdk 36")
replace_once(versions, 'targetSdk = "35"', 'targetSdk = "36"', "targetSdk 36")
replace_once(versions, 'agp = "8.8.1"', 'agp = "8.10.1"', "AGP 8.10.1")

wrapper = ROOT / "gradle/wrapper/gradle-wrapper.properties"
replace_once(
    wrapper,
    "gradle-8.10.2-bin.zip",
    "gradle-8.11.1-bin.zip",
    "Gradle 8.11.1",
)

# BGM permission UI: READ_EXTERNAL_STORAGE is a legacy permission and must not be
# requested/checked on Android 13+, where READ_MEDIA_AUDIO is used instead.
bgm = ROOT / "app/src/main/java/com/github/jing332/tts_server_android/compose/systts/list/ui/BgmConfigUI.kt"
replace_once(
    bgm,
    '''            val storagePermission =
                rememberPermissionState(Manifest.permission.READ_EXTERNAL_STORAGE)
            if (!storagePermission.status.isGranted)
                warnButton(text = stringResource(R.string.grant_permission_storage_file)) {
                    storagePermission.launchPermissionRequest()
                }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) { // A13
                val audioPermission = rememberPermissionState(Manifest.permission.READ_MEDIA_AUDIO)

                if (!audioPermission.status.isGranted)
                    warnButton(text = stringResource(R.string.grant_permission_audio_file)) {
                        audioPermission.launchPermissionRequest()
                    }
            }''',
    '''            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) { // Android 12L and below
                val storagePermission =
                    rememberPermissionState(Manifest.permission.READ_EXTERNAL_STORAGE)
                if (!storagePermission.status.isGranted)
                    warnButton(text = stringResource(R.string.grant_permission_storage_file)) {
                        storagePermission.launchPermissionRequest()
                    }
            } else { // Android 13+ (including Android 16)
                val audioPermission = rememberPermissionState(Manifest.permission.READ_MEDIA_AUDIO)

                if (!audioPermission.status.isGranted)
                    warnButton(text = stringResource(R.string.grant_permission_audio_file)) {
                        audioPermission.launchPermissionRequest()
                    }
            }''',
    "BGM storage permission split",
)

# Built-in file picker: request the permission appropriate for the Android
# version. WRITE_EXTERNAL_STORAGE is only meaningful through Android 9.
picker = ROOT / "app/src/main/java/com/github/jing332/tts_server_android/ui/FilePickerActivity.kt"
replace_once(
    picker,
    '''        checkPermission(Manifest.permission.READ_EXTERNAL_STORAGE)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            checkPermission(Manifest.permission.READ_MEDIA_AUDIO)
        }''',
    '''        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            checkPermission(Manifest.permission.READ_MEDIA_AUDIO)
        } else {
            checkPermission(Manifest.permission.READ_EXTERNAL_STORAGE)
        }''',
    "FilePicker read permission split",
)
replace_once(
    picker,
    '''        if (requestData is RequestSaveFile) {
            val permission = ActivityCompat.checkSelfPermission(
                this, Manifest.permission.WRITE_EXTERNAL_STORAGE
            )
            if (permission != PackageManager.PERMISSION_GRANTED)
                ActivityCompat.requestPermissions(
                    this, arrayOf(
                        Manifest.permission.WRITE_EXTERNAL_STORAGE,
                    ), 1
                )

            docCreate =''',
    '''        if (requestData is RequestSaveFile) {
            if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P) {
                val permission = ActivityCompat.checkSelfPermission(
                    this, Manifest.permission.WRITE_EXTERNAL_STORAGE
                )
                if (permission != PackageManager.PERMISSION_GRANTED)
                    ActivityCompat.requestPermissions(
                        this, arrayOf(
                            Manifest.permission.WRITE_EXTERNAL_STORAGE,
                        ), 1
                    )
            }

            docCreate =''',
    "FilePicker legacy write permission gate",
)

# Manifest: prevent legacy storage permissions from being considered on modern
# Android while keeping the existing all-files access feature for BGM folders.
manifest = ROOT / "app/src/main/AndroidManifest.xml"
replace_once(
    manifest,
    '''    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />''',
    '''    <uses-permission
        android:name="android.permission.READ_EXTERNAL_STORAGE"
        android:maxSdkVersion="32" />
    <uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />
    <uses-permission
        android:name="android.permission.WRITE_EXTERNAL_STORAGE"
        android:maxSdkVersion="28" />''',
    "Manifest legacy storage maxSdkVersion",
)

print("Android 16 compatibility patch applied successfully.")
