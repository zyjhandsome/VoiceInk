# VoiceInk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows desktop speech-to-text app that records voice on Alt+Space, transcribes locally with faster-whisper, optionally polishes with LLM, and auto-pastes to cursor position.

**Architecture:** PyQt6 desktop app with modular design — separate modules for hotkey detection, audio recording, speech recognition, LLM polishing, and text pasting, coordinated by a central App class using Qt signals/slots. UI consists of system tray icon, floating status window, and settings dialog.

**Tech Stack:** Python 3.11+, PyQt6, faster-whisper, sounddevice, pynput, httpx, pyperclip, pyautogui, pywin32, numpy

---

### Task 1: Project Setup & Configuration Module

**Files:**
- Create: `voiceink/main.py`
- Create: `voiceink/config.py`
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
PyQt6>=6.6.0
faster-whisper>=1.0.0
sounddevice>=0.4.6
pynput>=1.7.6
httpx>=0.27.0
pyperclip>=1.8.2
pyautogui>=0.9.54
pywin32>=306
numpy>=1.24.0
```

- [ ] **Step 2: Create config.py**

Config manager that reads/writes `~/.voiceink/config.json`. Default config includes hotkey, auto_start, sound_enabled, whisper_model, and llm settings. Provides get/set methods and saves on change.

- [ ] **Step 3: Create main.py entry point**

Minimal entry point that creates QApplication, initializes the App, and starts the event loop.

- [ ] **Step 4: Verify config module works**

Run: `python -c "from voiceink.config import Config; c = Config(); print(c.get_all())"`
Expected: Prints default config dict

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: project setup with config module"
```

---

### Task 2: Audio Recorder Module

**Files:**
- Create: `voiceink/audio_recorder.py`

- [ ] **Step 1: Implement AudioRecorder**

QObject subclass with signals: `volume_changed(float)`, `audio_chunk_ready(numpy.ndarray)`, `recording_finished(numpy.ndarray)`. Uses sounddevice.InputStream at 16kHz mono. Provides `start()`, `stop()`, `cancel()` methods. Accumulates audio chunks in a list, emits volume levels for waveform display.

- [ ] **Step 2: Verify audio recording**

Run: `python -c "from voiceink.audio_recorder import AudioRecorder; ..."`
Expected: Records 2 seconds of audio, prints volume levels

- [ ] **Step 3: Commit**

```bash
git add voiceink/audio_recorder.py
git commit -m "feat: audio recorder with volume monitoring"
```

---

### Task 3: Speech Recognizer Module

**Files:**
- Create: `voiceink/speech_recognizer.py`

- [ ] **Step 1: Implement SpeechRecognizer**

QObject subclass with signals: `partial_result(str)`, `final_result(str)`, `error(str)`, `model_download_progress(int)`. Wraps faster-whisper WhisperModel. Provides `transcribe_chunk(audio_data)` for streaming partial results and `transcribe_final(full_audio)` for final transcription. Auto-downloads model on first use. Runs inference in QThread to avoid blocking UI.

- [ ] **Step 2: Commit**

```bash
git add voiceink/speech_recognizer.py
git commit -m "feat: speech recognizer with streaming support"
```

---

### Task 4: LLM Text Polisher Module

**Files:**
- Create: `voiceink/text_polisher.py`

- [ ] **Step 1: Implement TextPolisher**

QObject subclass with signals: `polish_complete(str)`, `polish_error(str)`. Uses httpx async client to call OpenAI-compatible Chat Completions API. Built-in polishing prompt. 5-second timeout. Returns original text on failure. Runs in QThread.

- [ ] **Step 2: Commit**

```bash
git add voiceink/text_polisher.py
git commit -m "feat: LLM text polisher with graceful degradation"
```

---

### Task 5: Text Paster Module

**Files:**
- Create: `voiceink/text_paster.py`

- [ ] **Step 1: Implement TextPaster**

Uses win32gui.GetForegroundWindow() to detect active window. If valid target window exists: backup clipboard → set text → Ctrl+V → restore clipboard. If no target: just copy to clipboard. Returns status string for UI feedback.

- [ ] **Step 2: Commit**

```bash
git add voiceink/text_paster.py
git commit -m "feat: text paster with foreground window detection"
```

---

### Task 6: Hotkey Manager Module

**Files:**
- Create: `voiceink/hotkey_manager.py`

- [ ] **Step 1: Implement HotKeyManager**

QObject subclass with signals: `recording_start()`, `recording_stop()`, `recording_cancel()`. Uses pynput keyboard listener. Tracks key-down/key-up for push-to-talk behavior. Supports configurable hotkey combo. Esc detection during recording.

- [ ] **Step 2: Commit**

```bash
git add voiceink/hotkey_manager.py
git commit -m "feat: global hotkey manager with push-to-talk"
```

---

### Task 7: Floating Window UI

**Files:**
- Create: `voiceink/ui/floating_window.py`
- Create: `voiceink/ui/__init__.py`

- [ ] **Step 1: Implement FloatingWindow**

Frameless, translucent, always-on-top QWidget. Rounded corners with dark semi-transparent background. Shows status text, waveform animation (volume bars), and transcription preview. States: recording, recognizing, polishing, success, cancelled, error. Auto-hides after timeout. Positioned at bottom-center of screen.

- [ ] **Step 2: Commit**

```bash
git add voiceink/ui/
git commit -m "feat: floating window with waveform animation"
```

---

### Task 8: Settings Window UI

**Files:**
- Create: `voiceink/ui/settings_window.py`

- [ ] **Step 1: Implement SettingsWindow**

QDialog with QTabWidget containing 3 tabs: Basic Settings (hotkey, auto-start, sound), Speech Recognition (model selection with download buttons), LLM Polishing (enable toggle, API URL, API Key, Model Name, test connection button). Reads/writes via Config module.

- [ ] **Step 2: Commit**

```bash
git add voiceink/ui/settings_window.py
git commit -m "feat: settings window with 3 config tabs"
```

---

### Task 9: System Tray Icon

**Files:**
- Create: `voiceink/ui/tray_icon.py`
- Create: `voiceink/resources/`

- [ ] **Step 1: Implement TrayIcon**

QSystemTrayIcon with context menu: Open Settings, separator, Auto-start toggle, Exit. Icon changes color between normal (gray) and recording (red) states. Generates icons programmatically using QPainter (no external files needed).

- [ ] **Step 2: Commit**

```bash
git add voiceink/ui/tray_icon.py voiceink/resources/
git commit -m "feat: system tray with context menu and dynamic icon"
```

---

### Task 10: App Orchestrator & Sound Effects

**Files:**
- Create: `voiceink/app.py`
- Create: `voiceink/sound_manager.py`

- [ ] **Step 1: Implement SoundManager**

Generates simple beep sounds programmatically using numpy (sine waves) and plays them via sounddevice. Two sounds: start_recording (high pitch short beep) and stop_recording (lower pitch short beep).

- [ ] **Step 2: Implement App class**

Central orchestrator that creates and connects all modules. Signal flow: HotKeyManager → AudioRecorder → SpeechRecognizer → TextPolisher → TextPaster. Updates FloatingWindow state at each stage. Manages TrayIcon and SettingsWindow. Handles the complete recording→transcribe→polish→paste pipeline.

- [ ] **Step 3: Wire up main.py**

Update main.py to create App instance, set up single-instance check, and start the application.

- [ ] **Step 4: Commit**

```bash
git add voiceink/app.py voiceink/sound_manager.py voiceink/main.py
git commit -m "feat: app orchestrator connecting all modules"
```

---

### Task 11: Integration Testing & Polish

- [ ] **Step 1: End-to-end manual test**

Run the full application, test: hotkey detection, recording, transcription, pasting. Fix any integration issues.

- [ ] **Step 2: Commit fixes**

```bash
git add -A
git commit -m "fix: integration issues from end-to-end testing"
```

---

### Task 12: PyInstaller Packaging

**Files:**
- Create: `voiceink.spec` or use command-line
- Create: `build.py` (build script)

- [ ] **Step 1: Create build script**

PyInstaller config to package as single .exe with all dependencies. Exclude Whisper models (downloaded at runtime). Include generated sound data.

- [ ] **Step 2: Build and test .exe**

Run: `python build.py`
Expected: Creates `dist/VoiceInk.exe`

- [ ] **Step 3: Commit**

```bash
git add build.py voiceink.spec
git commit -m "feat: PyInstaller packaging as single exe"
```
