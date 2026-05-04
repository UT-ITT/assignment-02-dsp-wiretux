import sounddevice as sd
import numpy as np
from time import sleep
from pynput.keyboard import Key, Controller

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024 # Number of audio frames per buffer
RATE = 44100 # Audio sampling rate (HZ)
CHANNELS = 1 # Mono audio
MINVOL = -45 # Minimum Volume needed to register as a sound
MINFREQ = 300 # Minimum frequency of a Whistle
MAXFREQ = 3000 # Maximum frequency of a Whistle
MINDIFF = 20 # Maximum difference between frequency needed to detect as a Whistle
REQUIREDCOUNT = 5 # Numer of times the sound must go in one direction to detect as a Whistle
COOLDOWN = 1.0 # Cooldown between inputs

lastFreq = None # The last detected frequency
counter = 0 # The more negative the more Whistle downs in a row and the more possitive the more Whistle up in a row
lastTime = 0 # Timestamp of the last input

keyboard = Controller()


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

# audio callback to safe data
def audio_callback(indata, frames, time, status):
    if status:
        print(status)

    data = indata[:, 0]  # mono

    global lastFreq, counter, lastTime

    timestamp = time.inputBufferAdcTime

    # Detect
    rms = np.sqrt(np.mean(data ** 2))
    volume = 20 * np.log10(rms + 1e-12)
    if volume < MINVOL:
        counter = 0
        lastFreq = None
        return

    window = data * np.hanning(len(data))
    fftData = np.abs(np.fft.rfft(window))
    freqs = np.fft.rfftfreq(len(data), 1/RATE)

    # Major Frequency
    freq = freqs[np.argmax(fftData)]

    # Check if it is in whistle range
    if MINFREQ < freq < MAXFREQ:

        # Check if a Frequency was detected before and there is no cool down active
        if lastFreq is not None and timestamp - lastTime > COOLDOWN:
            diff = freq - lastFreq

            # Filter out if the same frequency was detected twice
            if diff == 0:
                return

            # Filter out too small jumps
            if(np.abs(diff) < MINDIFF):
                return

            # Set the counter
            if(diff > 0):
                counter = counter + 1 if counter > 0 else 1
            else:
                counter = counter - 1 if counter < 0 else -1

            # If the counter has reached the required count press the key
            if counter >= REQUIREDCOUNT:
                print(f"Whistling up detected. Pressed UP")
                keyboard.press(Key.up)
                keyboard.release(Key.up)
                lastTime = time.inputBufferAdcTime
            elif counter <= -REQUIREDCOUNT:
                print(f"Whistling down detected. Pressed Down")
                keyboard.press(Key.down)
                keyboard.release(Key.down)
                lastTime = time.inputBufferAdcTime

        # Store the current major frequency as the new last frequency
        lastFreq = freq


# open audio input stream
stream = sd.InputStream(
    device=input_device,
    channels=CHANNELS,
    samplerate=RATE,
    blocksize=CHUNK_SIZE,
    callback=audio_callback,
    latency='low'
)


# continously capture and plot audio signal
with stream:
    print("\nStreaming... (Ctrl+C to stop)")
    while True:
        sleep(1)
