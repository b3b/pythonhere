## MIDI playback using `midistream`

Use this addon when the user asks for:
- MIDI playback.
- Playing notes, chords, scales, melodies, arpeggios, drums, percussion, tones, or generated music.
- Synthesizer output.
- Instrument selection.
- General MIDI sounds.
- Volume, pan, modulation, reverb, or all-sound-off controls.
- A PythonHere/Kivy UI that plays MIDI sound.
- Debugging or introspecting MIDI playback on Android.

Target library:
- Prefer the midistream package.
- midistream is intended for Android / Python-for-Android MIDI playback.
- midistream is installed, do not need to check for import errors

Core API:
- Import the synthesizer with:
  from midistream import Synthesizer, MIDIException, ReverbPreset
- Create one Synthesizer instance and keep it alive for as long as sound is needed:
  synthesizer = Synthesizer()
- Stop playback and release resources with:
  synthesizer.close()
- Write MIDI command bytes/lists with:
  synthesizer.write(command)
- synthesizer.write accepts byte-like data.
- Helper functions return lists of integers.
- Several helper-message lists may be concatenated before writing.
- Read configuration with:
  synthesizer.config
- Set master volume with:
  synthesizer.volume = value
  where value is normally an integer from 0 to 100; 100 is maximum.
- Set reverb with:
  synthesizer.reverb = ReverbPreset.OFF
  synthesizer.reverb = ReverbPreset.LARGE_HALL
  synthesizer.reverb = ReverbPreset.HALL
  synthesizer.reverb = ReverbPreset.CHAMBER
  synthesizer.reverb = ReverbPreset.ROOM

MIDI helper API:
- Prefer helpers instead of hand-written status bytes unless raw MIDI bytes are specifically useful.
- Import helpers with:
  from midistream.helpers import (
      Control,
      Note,
      midi_channels,
      midi_control_change,
      midi_instruments,
      midi_note_off,
      midi_note_on,
      midi_program_change,
      note_name,
      parse_note,
  )
- Use midi_note_on(note, channel=0, velocity=64) for note-on messages.
- Use midi_note_off(note, channel=0, velocity=0) for note-off messages.
- Use midi_program_change(program, channel=0) to select a General MIDI instrument.
- Use midi_control_change(controller, value=0, channel=0) for control-change messages.
- Useful Control values:
  Control.volume
  Control.pan
  Control.modulation
  Control.all_sound_off
- Use midi_instruments, a dict mapping program numbers 0..127 to instrument names, for menus/spinners and readable labels.
- Use parse_note("C4"), parse_note("Fs4"), parse_note("Bb3"), etc. for user note input.
- Use note_name(note_number) for readable display.
- Use Note.C4, Note.Cs4, Note.Bb3, etc. when a constant-like note name is clearer.
- MIDI note numbers must stay in 0..127.
- MIDI program numbers must stay in 0..127.
- MIDI velocity values must stay in 0..127.
- MIDI controller values must stay in 0..127.
- MIDI channels are 0..15.
- Channel 9 is the General MIDI percussion channel.
- midi_channels() intentionally yields melodic channels excluding channel 9.

midistream-specific state:
- Use a global variable named synthesizer for the shared midistream Synthesizer instance.
- Reuse synthesizer across cells when it already exists.
- Create synthesizer only when needed:
  if "synthesizer" not in globals() or synthesizer is None:
      synthesizer = Synthesizer()
- Keep synthesizer globally inspectable so later cells can run:
  synthesizer.config
  synthesizer.volume = 80
  synthesizer.close()
- For safe cleanup, use these optional global tracking sets:
  midistream_active_notes
  midistream_used_channels
- midistream_active_notes tracks notes that generated code has sent note-on for but has not yet sent note-off for.
- midistream_active_notes is best-effort bookkeeping for cleanup, not a query of the synthesizer's real internal state.
- midistream_active_notes should contain (channel, note) tuples.
- midistream_used_channels should contain integer channel numbers.
- Add a note to midistream_active_notes immediately after a successful midi_note_on write.
- Remove a note from midistream_active_notes after sending midi_note_off for that note.
- Initialize tracking sets only if they do not already exist.
- Do not create a new Synthesizer for every note.
- Do not store the only Synthesizer reference inside a local function, widget callback, or temporary object.
- If Synthesizer creation fails, print or display a clear diagnostic.

Recommended midistream helpers:
- For MIDI-generating cells, prefer small helper functions such as:
  get_synthesizer()
  send_midi(command, description="MIDI command")
  note_on(note, channel=0, velocity=100)
  note_off(note, channel=0, velocity=0)
  play_note(note, duration=0.5, channel=0, velocity=100)
  set_instrument(program, channel=0)
  set_channel_volume(value, channel=0)
  set_reverb(preset)
  all_sound_off()
  close_synthesizer()
- get_synthesizer should create or reuse the global synthesizer.
- send_midi should call get_synthesizer().write(command).
- note_on should:
  1. validate note, channel, and velocity,
  2. send midi_note_on(...),
  3. add (channel, note) to midistream_active_notes,
  4. add channel to midistream_used_channels.
- note_off should:
  1. send midi_note_off(...),
  2. remove (channel, note) from midistream_active_notes if present.
- play_note should:
  1. call note_on(...),
  2. schedule note_off(...) with Clock.schedule_once,
  3. avoid time.sleep().
- all_sound_off should:
  1. send note-off for tracked notes,
  2. send midi_control_change(Control.all_sound_off, 0, channel=channel) for used channels,
  3. clear midistream_active_notes.
- close_synthesizer should:
  1. call all_sound_off(),
  2. call synthesizer.close(),
  3. set synthesizer = None.

Timing rules:
- Do not use time.sleep() for note durations, melodies, or sequences.
- Do not use long blocking loops.
- Use kivy.clock.Clock.schedule_once for delayed note-off events.
- Use Clock.schedule_once for each event in a melody or sequence.
- Use Clock.schedule_interval only for repeated playback that the user can stop.
- For endless or repeating music, store every scheduled `ClockEvent` for note
  starts, note stops, and next-step callbacks in a global or controller list,
  and cancel those events in the Stop / All Sound Off handler.
- Do not leave recursive `Clock.schedule_once(...)` callbacks running after the
  user presses Stop.
- Keep scheduled callbacks short.
- Do not rely on `print(...)` inside scheduled callbacks as the only output.
  Scheduled callbacks may run after notebook output capture has ended. Store
  playback status and errors in globals, and update a visible Kivy label when
  the user asked for UI feedback.
- For one-shot notes, prefer:
  note_on(note, channel, velocity)
  Clock.schedule_once(lambda dt: note_off(note, channel), duration)
- For sequences, schedule each note-on and note-off at offsets from the start of the sequence.

Kivy UI integration:
- Useful controls include:
  Button for playing notes/chords.
  Button for Stop / All Sound Off.
  Slider for volume.
  Slider for note duration.
  Spinner for instrument selection.
  Spinner for reverb preset.
  TextInput for note names such as C4, Fs4, Bb3.
  Label for diagnostics.
- Bind UI controls to helper functions after Builder.load_string(KV) returns the layout.
- Keep callbacks short and catch exceptions.
- Show MIDI status and errors in a Label when the user asked for visible UI.

Recommended simple UI behavior:
- Always include a Stop or All Sound Off button in interactive MIDI UIs.
- For note buttons, schedule note-off automatically.
- For instrument selection, display readable names from midi_instruments.
- For volume sliders, update synthesizer.volume or send Control.volume depending on the requested behavior.
- For reverb controls, map readable names to ReverbPreset values.
- For percussion, use channel 9 and explain through labels or code comments that channel 9 is the General MIDI percussion channel.

MIDI diagnostics:
- For debugging, print readable labels.
- Useful diagnostics include:
  - whether Synthesizer() initializes successfully,
  - synthesizer.config,
  - current volume,
  - current reverb,
  - selected channel,
  - selected program number and instrument name,
  - selected note number and note name,
  - tracked notes in midistream_active_notes,
  - used channels in midistream_used_channels,
  - exception type and message.
- Catch MIDIException separately where useful.

Good command examples:
- Initialize or reuse:
  if "synthesizer" not in globals() or synthesizer is None:
      synthesizer = Synthesizer()

  if "midistream_active_notes" not in globals():
      midistream_active_notes = set()

  if "midistream_used_channels" not in globals():
      midistream_used_channels = set()

- Play middle C:
  synthesizer.write(midi_note_on(60, channel=0, velocity=100))
  later send:
  synthesizer.write(midi_note_off(60, channel=0))

- Play a note without blocking:
  note_on(60, channel=0, velocity=100)
  Clock.schedule_once(lambda dt: note_off(60, channel=0), 0.5)

- Change instrument:
  synthesizer.write(midi_program_change(0, channel=0))

- Change channel volume:
  synthesizer.write(midi_control_change(Control.volume, 100, channel=0))

- Send multiple MIDI messages in one write:
  synthesizer.write(
      midi_program_change(0, channel=0) +
      midi_control_change(Control.volume, 100, channel=0) +
      midi_note_on(60, channel=0, velocity=100)
  )

- Stop sound immediately on a channel:
  synthesizer.write(midi_control_change(Control.all_sound_off, 0, channel=0))

Avoid:
- Do not generate code that starts notes without ever turning them off.
- Do not create a new Synthesizer for every note.
- Do not block the Kivy event loop with sleep calls or long loops.
- Do not assume audio output is available before Synthesizer() succeeds.

For simple user requests:
- If the user asks to play a note, generate a minimal self-contained cell that imports midistream, initializes or reuses synthesizer, plays the note, schedules note-off with Clock.schedule_once, and prints diagnostics.
- If the user asks to play a melody, generate a cell that schedules all notes with Clock.schedule_once and provides all_sound_off cleanup.
- If the user asks for a Kivy UI, generate a PythonHere-compatible UI using the existing root object and include Stop / All Sound Off.
- If the user asks for an instrument picker, use midi_instruments for labels and midi_program_change for selection.
- If the user asks for drums, use channel 9.
- If the user asks for cleanup, generate close_synthesizer() code that stops tracked notes and closes the global synthesizer.
