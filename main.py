import numpy as np
import pyaudio
import threading
from pynput import mouse
import random
SAMPLE_RATE = 44100 
CHUNK = 3
MAX_FREQ = 2000
MAX_AMPLITUDE = 0.5

mouse_x = 0
mouse_y = 0
phase = 0

def generate_sine_wave_chunk(frequency, amplitude, num_samples):
    global phase
    t = np.arange(num_samples) / SAMPLE_RATE
    wave = amplitude * np.sin(2 * np.pi * frequency * t + phase)
      # Update phase
    return wave.astype(np.float32)

def audio_callback(in_data, frame_count, time_info, status):
    global mouse_x, mouse_y, phase

    frequency = (mouse_x / 1920) * MAX_FREQ
    amplitude = (mouse_y / 1080) * MAX_AMPLITUDE
    
    sine_wave = generate_sine_wave_chunk(frequency, amplitude, frame_count)
    phase = (phase + 2 * np.pi * frequency * frame_count / SAMPLE_RATE) % (2 * np.pi)
    return (sine_wave.tobytes(), pyaudio.paContinue)

def distortion(signal,threshold):
    return np.where(np.abs(signal) > threshold, np.sign(signal) * threshold, signal)

def on_move(x, y):
    global mouse_x, mouse_y
    mouse_x = x
    mouse_y = y

mouse_listener = mouse.Listener(on_move=on_move)
mouse_listener.start()

p = pyaudio.PyAudio()

stream = p.open(format=pyaudio.paFloat32,
                channels=1,
                rate=SAMPLE_RATE,
                output=True,
                frames_per_buffer=CHUNK,
                stream_callback=audio_callback)

stream.start_stream()

try:
    while stream.is_active():
        pass
except KeyboardInterrupt:
    pass

stream.stop_stream()
stream.close()
p.terminate()

mouse_listener.stop()