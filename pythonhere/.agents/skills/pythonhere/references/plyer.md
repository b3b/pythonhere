## Plyer helpers

Use this addon for Plyer-backed Android/device features:
notification, Android toast-style messages, vibration, audio recording, camera capture,
file chooser, GPS/location, battery, accelerometer, compass, text-to-speech,
and similar Plyer facades.

`plyer` is installed; do not need to check for import errors before normal use.

Rules:
- `plyer` is installed; do not need to check for import errors before normal use.
- Prefer the `plyer` package for the supported device facades listed here.
- Plyer does not have a separate `toast` facade. Do not write
  `from plyer import toast`.
- For Android toast-style messages, use
  `from plyer import notification` and call
  `notification.notify(..., toast=True)`.
- Do not request permissions here unless the user explicitly asks; use the separate Android permissions prompt.
- Do not access camera, microphone, GPS/location, sensors, contacts, SMS, call logs, or private files unless the user requested that specific capability.
- Do not delete, overwrite, upload, or make network requests with selected files unless explicitly requested.
- For asynchronous Plyer callbacks, store results in globals. If a Kivy UI is
  involved, update visible UI through the Kivy runtime pattern.
- For microphone recording, Android normally needs
  `android.permission.RECORD_AUDIO` declared in the app manifest and granted at
  runtime. Use the Android permissions prompt when the user asks to request or
  check microphone permission.

Text-to-speech rules:
- For simple text-to-speech, use exactly this API shape:

    from plyer import tts
    tts.speak(message=text_to_read)

- Do not use low-level Android framework speech APIs through Pyjnius for
  ordinary read-aloud, speech, voice output, poem reading, or narration
  requests. Use Pyjnius speech only when the user explicitly asks for lower-level
  Android speech controls that Plyer does not expose.
- Do not use legacy SL4A-style Android helper speech APIs.
- Do not use desktop speech packages or platform shell commands for
  Android/PythonHere TTS snippets.
- Do not generate `TTS_AVAILABLE` fallback scaffolding or probe multiple TTS
  backends unless the user explicitly asks for cross-platform desktop code.
- Do not run `tts.speak(...)` inside a background Python thread. Use the Plyer
  call directly from the `there run` program or from a short Kivy callback.
- For a Kivy UI button or delayed speech start, the callback should call
  `tts.speak(message=text)` directly and update UI state through the Kivy
  runtime pattern.

Plyer audio recording rules:
- Use `plyer.audio` for audio recording workflows.
- Do not use `plyer.audio` as a general local-file playback API.
- Never call `audio.play(path)` or `audio.play("file.wav")`.
- For Android Plyer recording, prefer `.3gp` output paths unless this runtime has
  verified another format.
- Do not name Plyer Android recordings `.wav` unless the backend is known to
  write real WAV PCM data.
- Replay audio recorded through Plyer with `audio.play()` and no arguments after
  `audio.stop()`.
- Stop recording or Plyer-managed playback with `audio.stop()`.
- Do not use Kivy SoundLoader to replay audio just recorded through Plyer on
  Android. Kivy SoundLoader is for normal existing local audio files and is
  covered by the Kivy Runtime prompt.

Toast example:
    from plyer import notification

    notification.notify(
        title="",
        message="Hello",
        app_name="PythonHere",
        toast=True,
    )

Notification example:
    from plyer import notification

    notification.notify(
        title="PythonHere",
        message="Done",
        app_name="PythonHere",
        timeout=5,
    )

Toast plus notification example:
    from plyer import notification

    notification.notify(
        title="",
        message="Done",
        app_name="PythonHere",
        toast=True,
    )
    notification.notify(
        title="PythonHere",
        message="Done",
        app_name="PythonHere",
        timeout=5,
    )

Vibration example:
    from plyer import vibrator

    vibrator.vibrate(0.2)

Text-to-speech example:
    from plyer import tts

    tts.speak(message="Hello from PythonHere.")

File chooser example:
    from plyer import filechooser

    def on_selection(paths):
        plyer_filechooser_result = {
            "paths": list(paths or []),
            "cancelled_or_empty": not bool(paths),
        }
        globals()["plyer_filechooser_result"] = plyer_filechooser_result

    filechooser.open_file(on_selection=on_selection)

Audio recording start example:
    from pathlib import Path
    from datetime import datetime

    from plyer import audio

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plyer_audio_recording_path = str(Path.cwd() / f"pythonhere-recording-{timestamp}.3gp")
    audio.file_path = plyer_audio_recording_path
    audio.start()
    plyer_audio_recording_status = {
        "recording": True,
        "path": plyer_audio_recording_path,
    }

Audio recording stop example:
    from plyer import audio

    audio.stop()
    plyer_audio_recording_status = {
        "recording": False,
        "path": plyer_audio_recording_path,
    }

Audio recording replay example:
    from plyer import audio

    audio.play()

Camera example:
    from plyer import camera

    camera.take_picture(
        filename="photo.jpg",
        on_complete=lambda path: globals().__setitem__(
            "plyer_camera_result",
            {"path": path, "cancelled_or_empty": not bool(path)},
        ),
    )

GPS example:
    from plyer import gps

    def on_location(**kwargs):
        globals()["plyer_gps_last_location"] = dict(kwargs)

    gps.configure(on_location=on_location)
    gps.start()

GPS stop example:
    from plyer import gps

    gps.stop()

Battery example:
    from plyer import battery

    status = battery.status

Accelerometer example:
    from plyer import accelerometer

    accelerometer.enable()
    acceleration = accelerometer.acceleration

Compass example:
    from plyer import compass

    compass.enable()
    heading = compass.orientation

Plyer callback state pattern:
- For every asynchronous Plyer facade, store callback results in a named global
  such as `plyer_filechooser_result`, `plyer_camera_result`, or
  `plyer_gps_last_location`.
- If a Kivy UI is involved, update a visible status widget from the callback
  using `Clock.schedule_once(...)` when needed.
- Do not treat a callback returning an empty selection or `None` as an
  exception; report it as a cancelled/empty result.
- Keep file chooser behavior read-only unless the user explicitly asks to open,
  process, copy, upload, delete, or overwrite selected files.
