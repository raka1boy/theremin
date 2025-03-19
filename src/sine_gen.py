import numpy as np
import pyaudio
from pynput import mouse

class SineGen:
    def __init__(self, sample_rate = 44100, mouse_x=0, mouse_y=0, min_freq=20, max_freq=20000, chunk_size=1024, loudness_amp=1.0):
        self.sample_rate = sample_rate
        self.mouse_x = mouse_x
        self.mouse_y = mouse_y
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.chunk_size = chunk_size
        self.loudness_amp = loudness_amp
        self.phase = 0
    

    def __str__(self):
        return (f"SineGen(mouse_x={self.mouse_x}, mouse_y={self.mouse_y}, "
                f"min_freq={self.min_freq}, max_freq={self.max_freq}, "
                f"chunk_size={self.chunk_size}, loudness_amp={self.loudness_amp})")
    
    def generate_sine_wave_chunk(self, frequency, amplitude, num_samples):
        t = np.arange(num_samples) / self.sample_rate
        return amplitude * np.sin(2 * np.pi * frequency * t + self.phase).astype(np.float32)
        