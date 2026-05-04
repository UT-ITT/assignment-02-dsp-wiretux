import sounddevice as sd
import numpy as np
import pyglet
import random
import mido
from mido import MidiFile


# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 4096 # Number of audio frames per buffer
SAMPLERATE = 44100 # Audio sampling rate (HZ)
CHANNELS = 1 # Mono audio
MINFREQUENCY = 20
RED = (255, 55, 55)
YELLOW = (212, 198, 0)
GREEN = (55, 255, 55)
LIGHTBLUE = (126, 233, 237)
MIDIFILEPATH = '../read_midi/freude.mid'

# print info about audio devices

print("Available input devices:\n")
devices = sd.query_devices()

input_devices = []
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f"{i}: {dev['name']}")
        input_devices.append(i)

# let user select audio device
input_device = int(input("\nSelect input device: "))

currentMicPitch = 0

# audio callback to safe data
def audio_callback(indata, frames, time, status):
    global currentMicPitch
    if status:
        print(status)

    data = indata[:, 0]  # mono

    rms = np.sqrt(np.mean(data ** 2))
    volume = 20 * np.log10(rms + 1e-12)
    if volume < -46.0:
        currentMicPitch = 0
        return

    sample = data - np.mean(data)
    corr = np.correlate(sample, sample, mode='full')
    corr = corr[len(corr)//2:]
    d = np.diff(corr)
    start = np.where(d > 0)[0][0]
    peak = np.argmax(corr[start:]) + start
    currentMicPitch = SAMPLERATE / peak if peak != 0 else 0

# open audio input stream
stream = sd.InputStream(
    device=input_device,
    channels=CHANNELS,
    samplerate=SAMPLERATE,
    blocksize=CHUNK_SIZE,
    callback=audio_callback,
    latency='low'
)

started = False
ended = False

title = 'Karaoke Game'
window = pyglet.window.Window(width=1024, height=600, caption=title)
pyglet.gl.glClearColor(1,1,1,1)

startScreenTitleLabel = pyglet.text.Label(title,
                          font_name='Times New Roman',
                          font_size=48,
                          x=window.width//2, y=window.height//2+50,
                          anchor_x='center', anchor_y='center',
                          color=(0,0,0)
                          )

startScreenStartLabel = pyglet.text.Label('Press Space to start',
                          font_name='Times New Roman',
                          font_size=24,
                          x=window.width//2, y=window.height//2 - 150,
                          anchor_x='center', anchor_y='center',
                          color=(0,0,0)
                          )

startScreenDescriptionLabel = pyglet.text.Label('Sing the tones and hit the notes',
                          font_name='Times New Roman',
                          font_size=24,
                          x=window.width//2, y=window.height//2 - 50,
                          anchor_x='center', anchor_y='center',
                          color=(0,0,0)
                          )

endScreenLabel = pyglet.text.Label('Your final score was',
                          font_name='Times New Roman',
                          font_size=24,
                          x=window.width//2, y=window.height//2,
                          anchor_x='center', anchor_y='center',
                          color=(0,0,0)
                          )

endScreen2Label = pyglet.text.Label('Press Space to restart',
                          font_name='Times New Roman',
                          font_size=24,
                          x=window.width//2, y=window.height//2 - 50,
                          anchor_x='center', anchor_y='center',
                          color=(0,0,0)
                          )

# Label for score in a game
scoreLabel = pyglet.text.Label('Score: 0',
                          font_name='Times New Roman',
                          font_size=24,
                          x=window.width//2, y= window.height - 50,
                          anchor_x='center', anchor_y='top',
                          color=(0,0,0)
                          )

@window.event
def on_key_press(symbol, modifiers):
    global started, score, ended
    # To start the game
    if not started and symbol == pyglet.window.key.SPACE:
        started = True
    elif ended and symbol == pyglet.window.key.SPACE:
        notes.clear()
        drawNotes(loadMidi(MIDIFILEPATH))
        score = 0
        ended = False

# Draw the note grid
noteGrid = []
gridDistance = 40
gridThickness = 8
baseY = window.height / 2 - gridDistance * 3.5
lines = 8
for i in range(lines):
    y = baseY + i * gridDistance
    line = pyglet.shapes.Line(50, y, window.width-50, y, thickness=gridThickness, color=(100, 100, 100))
    noteGrid.append(line)

noteDistance = 150
verticalLine = pyglet.shapes.Line(noteDistance * 1.5, baseY- (gridThickness/2), noteDistance * 1.5, baseY + gridDistance * (lines-1) + (gridThickness/2), thickness=12, color=(100, 100, 100))
noteGrid.append(verticalLine)

voiceCircle = pyglet.shapes.Circle(x=verticalLine.x, y=baseY, radius=20, color=(50, 225, 30))
noteGrid.append(voiceCircle)

def loadMidi(filename):
    midi = MidiFile(filename)
    track = midi.tracks[0]

    ticksPerBeat = midi.ticks_per_beat
    bpm = 110
    tempo = 60000000/bpm
    for info in track:
        if info.type == 'set_tempo':
            tempo = info.tempo
            break

    loadedNotes = []
    currentNode = None
    ticks = 0

    for info in track:
        if info.is_meta:
            continue
        ticks += info.time
        time = ticks * (tempo / 1000000) / ticksPerBeat

        if info.velocity > 0:
            # Capture and lock in the first note
            if currentNode is None:
                currentNode = {
                        "note": info.note,
                        "start": time
                        }
        elif currentNode is not None and info.note is currentNode['note']:
            duration = time - currentNode['start']

            if(duration > 0.005):
                loadedNotes.append({'note': currentNode['note'],
                                    'start': currentNode['start'],
                                    'duration': duration})
                currentNode = None
    return loadedNotes

def getGridPitch(note, minNote, maxNote):
    notenRange = maxNote - minNote
    if notenRange <= 0:
        return (lines - 1) / 2 # Fallback

    # Set relativePos to the middle
    relativePos = (note - minNote) / notenRange

    # Clamping
    relativePos = max(0.0, min(1.0, relativePos))

    # Remap 0 to 1 to the arrea 0 to lines-1
    return relativePos * (lines - 1)

speed = 120
notes = []
noteMin = 0
noteMax = 0
def drawNotes(notesToDraw):
    global noteMin, noteMax
    midiValues = [note['note'] for note in notesToDraw]
    padding = 2
    noteMin = min(midiValues) - padding
    noteMax = max(midiValues) + padding
    for note in notesToDraw:
        height = gridDistance - gridThickness
        width = note['duration'] * speed
        x = 600 +  speed * note['start']

        #Value mapping here
        mappedNote = getGridPitch(note['note'], noteMin, noteMax)

        y = (mappedNote + 0.5) * gridDistance + baseY
        square = pyglet.shapes.Rectangle(x=x, y=y-height/2, width=width, height=height, color=(55, 55, 255))

        # Properties
        square.activeTime = 0
        square.hitTime = 0
        square.scored = False
        square.note = note['note']

        notes.append(square)

drawNotes(loadMidi(MIDIFILEPATH))

# Using the formular from https://sengpielaudio.com/Rechner-notennamen.htm to convert the frequencyToMidi
def frequencyToMidi(freq):
    if freq <= MINFREQUENCY:
        return 0
    return 69 + 12 * np.log2(freq / 440.0)

score = 0
def update(delta):
    global score, speed, currentMicPitch, noteMin, noteMax, gridDistance, baseY, ended

    if not started or ended:
        return

    if all(note.x < 150 for note in notes): return

    # Current Frequenzy
    currentVoiceMidi = frequencyToMidi(currentMicPitch)

    if currentVoiceMidi > 0:
        # Mapp the currentVoiceMidi to one Octave
        note = currentVoiceMidi % 12

        midNote = (noteMin + noteMax) / 2
        offset = round((midNote - note) / 12)
        noteWithOffset = note + offset * 12

        mappedVoice = getGridPitch(noteWithOffset, noteMin, noteMax)
        targetY = (mappedVoice + 0.5) * gridDistance + baseY

        # Make the ball go up slower
        voiceCircle.y += (targetY - voiceCircle.y) * 0.15
    else:
        # Make the ball drop slower
        voiceCircle.y += (baseY - voiceCircle.y) * 0.05

    for note in notes:
        note.x -= speed * delta

        if note.x < verticalLine.x < (note.x + note.width):
            note.activeTime += 1

            # Hit logic
            targetMidi = note.note
            diff = abs(currentVoiceMidi - targetMidi)

            if (diff % 12 < 1 or diff % 12 > 11) and currentMicPitch > 0:
                note.hitTime += 1

            # Mark the current note
            note.color = LIGHTBLUE
        elif (note.x + note.width) < verticalLine.x and not note.scored:
            note.scored = True

            accuracy = 0
            if(note.activeTime > 0):
                accuracy = note.hitTime / note.activeTime

            if accuracy >= 0.6:
                # We got all points
                score += 100
                note.color = GREEN
            elif accuracy >= 0.2:
                # Still some points
                note.color = YELLOW
                score += 50
            else:
                # No hit or too much missed
                note.color = RED

    # Update score
    scoreLabel.text = f"Score: {score}"

    if all(note.x < 150 for note in notes):
        ended = True

@window.event
def on_draw():
    window.clear()
    if ended:
        endScreenLabel.text = f"Your final score was {score}"
        endScreenLabel.draw()
        endScreen2Label.draw()
        return

    if not started:
        startScreenTitleLabel.draw()
        startScreenStartLabel.draw()
        startScreenDescriptionLabel.draw()
    else:
        for line in noteGrid:
            line.draw()
        for note in notes:
            note.draw()
        scoreLabel.draw()

with stream:
    pyglet.clock.schedule_interval(update, 1/60.)
    pyglet.app.run()
