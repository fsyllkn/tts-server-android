from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old in text:
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        print(f"[OK] {label}: patched {path}")
        return
    if new in text:
        print(f"[OK] {label}: already patched {path}")
        return
    raise SystemExit(f"[{label}] neither old nor patched source block found in {path}")


# Compile against Android 16, but keep targetSdk 35 for now. The app does not
# need targetSdk 36 merely to run on Android 16, and keeping 35 avoids changing
# TTS/background-service behavior while we are repairing compatibility.
versions = ROOT / "libs.versions.toml"
replace_once(versions, 'compileSdk = "35"', 'compileSdk = "36"', "compileSdk 36")
replace_once(versions, 'targetSdk = "36"', 'targetSdk = "35"', "targetSdk 35 compatibility")
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

# Android Settings enables its Play/rate/pitch controls only when the engine's
# default locale is also returned by CHECK_TTS_DATA. Keep the engine's default
# voice deterministic (zh-CN) instead of tying it to the phone UI locale, and
# accept both ISO-639-1 and ISO-639-2 language/country forms.
system_tts = ROOT / "app/src/main/java/com/github/jing332/tts_server_android/service/systts/SystemTtsService.kt"
replace_once(
    system_tts,
    '''    private val mTextProcessor = TextProcessor()
    private var mTtsManager: MixSynthesizer? = null
''',
    '''    private val mTextProcessor = TextProcessor()
    private var mTtsManager: MixSynthesizer? = null
    private var mInitManagerJob: Job? = null
''',
    "Track TTS manager initialization",
)
replace_once(
    system_tts,
    '''    fun initManager() {
        logger.debug { "initialize or load configruation" }
        mScope.launch {''',
    '''    fun initManager() {
        logger.debug { "initialize or load configruation" }
        mInitManagerJob = mScope.launch {''',
    "Store TTS manager init job",
)
replace_once(
    system_tts,
    '''    override fun onIsLanguageAvailable(lang: String?, country: String?, variant: String?): Int {
        return if (Locale.SIMPLIFIED_CHINESE.isO3Language == lang || Locale.US.isO3Language == lang) {
            if (Locale.SIMPLIFIED_CHINESE.isO3Country == country || Locale.US.isO3Country == country) TextToSpeech.LANG_COUNTRY_AVAILABLE else TextToSpeech.LANG_AVAILABLE
        } else TextToSpeech.LANG_NOT_SUPPORTED
    }''',
    '''    override fun onIsLanguageAvailable(lang: String?, country: String?, variant: String?): Int {
        val language = lang?.lowercase(Locale.ROOT)
        val region = country?.uppercase(Locale.ROOT)
        val isChinese = language == "zho" || language == "zh"
        val isEnglish = language == "eng" || language == "en"

        if (!isChinese && !isEnglish) return TextToSpeech.LANG_NOT_SUPPORTED
        if (region.isNullOrBlank()) return TextToSpeech.LANG_AVAILABLE

        val countryMatches =
            (isChinese && (region == "CHN" || region == "CN")) ||
                (isEnglish && (region == "USA" || region == "US"))
        return if (countryMatches) TextToSpeech.LANG_COUNTRY_AVAILABLE
        else TextToSpeech.LANG_AVAILABLE
    }''',
    "Robust TTS language availability",
)
replace_once(
    system_tts,
    '''            mutableListOf(Voice(DEFAULT_VOICE_NAME, Locale.getDefault(), 0, 0, true, emptySet()))''',
    '''            mutableListOf(Voice(DEFAULT_VOICE_NAME, Locale.SIMPLIFIED_CHINESE, 0, 0, true, emptySet()))''',
    "Stable default TTS voice locale",
)
replace_once(
    system_tts,
    '''            callback.done()
            return
        }

        mNotificationJob?.cancel()''',
    '''            callback.done()
            return
        }

        // initManager() is asynchronous. A client can request speech immediately
        // after binding; wait for initialization instead of silently doing nothing
        // while mTtsManager is still null.
        runBlocking { mInitManagerJob?.join() }
        if (mTtsManager == null) {
            logger.error { "TTS manager is unavailable after initialization" }
            callback.error(TextToSpeech.ERROR_SYNTHESIS)
            callback.done()
            return
        }

        mNotificationJob?.cancel()''',
    "Wait for TTS manager before synthesis",
)

# Make CHECK_TTS_DATA agree with the engine's two supported locales. This is
# what Android Settings uses to decide whether the Play button should be active.
check_voice = ROOT / "app/src/main/java/com/github/jing332/tts_server_android/service/systts/CheckVoiceData.kt"
replace_once(
    check_voice,
    '''        val available: ArrayList<String> = arrayListOf("zho-CHN")''',
    '''        val available: ArrayList<String> = arrayListOf(
            "zho-CHN",
            "zho",
            "eng-USA",
            "eng"
        )''',
    "Advertise supported TTS locales",
)

# Android Settings asks the selected engine for sample text through
# ACTION_GET_SAMPLE_TEXT. The upstream app does not provide this activity, so
# add a minimal implementation for a reliable system Settings audition.
sample_text = ROOT / "app/src/main/java/com/github/jing332/tts_server_android/service/systts/GetSampleText.kt"
sample_text_content = '''package com.github.jing332.tts_server_android.service.systts

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.speech.tts.TextToSpeech

class GetSampleText : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val language = intent.getStringExtra("language")?.lowercase().orEmpty()
        val sample = if (language == "eng" || language == "en") {
            "This is a text to speech sample."
        } else {
            "这是一段文字转语音测试。"
        }

        setResult(
            TextToSpeech.LANG_AVAILABLE,
            Intent().putExtra("sampleText", sample)
        )
        finish()
    }
}
'''
if sample_text.exists():
    if sample_text.read_text(encoding="utf-8") != sample_text_content:
        sample_text.write_text(sample_text_content, encoding="utf-8")
        print(f"[OK] TTS sample text activity: updated {sample_text}")
    else:
        print(f"[OK] TTS sample text activity: already present {sample_text}")
else:
    sample_text.write_text(sample_text_content, encoding="utf-8")
    print(f"[OK] TTS sample text activity: created {sample_text}")

replace_once(
    manifest,
    '''        <activity
            android:name=".service.systts.CheckVoiceData"
            android:exported="true"
            android:label="CheckVoiceData">
            <intent-filter>
                <action android:name="android.speech.tts.engine.CHECK_TTS_DATA" />

                <category android:name="android.intent.category.DEFAULT" />
            </intent-filter>
        </activity>

        <activity
            android:name=".compose.DebugSystemTtsActivity"''',
    '''        <activity
            android:name=".service.systts.CheckVoiceData"
            android:exported="true"
            android:label="CheckVoiceData">
            <intent-filter>
                <action android:name="android.speech.tts.engine.CHECK_TTS_DATA" />

                <category android:name="android.intent.category.DEFAULT" />
            </intent-filter>
        </activity>

        <activity
            android:name=".service.systts.GetSampleText"
            android:exported="true"
            android:theme="@android:style/Theme.NoDisplay">
            <intent-filter>
                <action android:name="android.speech.tts.engine.GET_SAMPLE_TEXT" />
                <category android:name="android.intent.category.DEFAULT" />
            </intent-filter>
        </activity>

        <activity
            android:name=".compose.DebugSystemTtsActivity"''',
    "Register TTS sample text activity",
)

print("Android 16 compatibility patch is present.")
