import numpy as np
import pyaudio
from screeninfo import get_monitors
import keyboard
SCREEN_X = get_monitors()[0].width
SCREEN_Y = get_monitors()[0].height
class SineGen:
    def __init__(self, sample_rate = 44100, min_freq=20, max_freq=20000, chunk_size=1024, smooth_factor = 0.0001):
        self.sample_rate = sample_rate
        self.mouse_x = 0
        self.mouse_y = 0
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.chunk_size = chunk_size
        self.loudness_amp = 0.5
        self.phase = 0
        self.smooth_val = 0
        self.smooth_factor = smooth_factor
    
    def __str__(self):
        return (f"SineGen(mouse_x={self.mouse_x}, mouse_y={self.mouse_y}, "
                f"min_freq={self.min_freq}, max_freq={self.max_freq}, "
                f"chunk_size={self.chunk_size}, loudness_amp={self.loudness_amp})")
    
    def generate_sine_wave_chunk(self, frequency, amplitude, num_samples):
        t = np.arange(num_samples) / self.sample_rate
        return amplitude * np.sin(2 * np.pi * frequency * t + self.phase).astype(np.float32)
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        _ = in_data,time_info,status
        if keyboard.is_pressed("space"):
            frequency = (self.mouse_x / SCREEN_X) * self.max_freq
            amplitude = (self.mouse_y / SCREEN_Y) * self.loudness_amp - self.smooth_val
            sine_wave = self.generate_sine_wave_chunk(frequency, amplitude, frame_count)
            self.phase = (self.phase + 2 * np.pi * frequency * frame_count / self.sample_rate) % (2 * np.pi)
            self.smooth_val = max(self.smooth_val - self.smooth_factor, 0)
            return (( sine_wave - self.smooth_val).tobytes(), pyaudio.paContinue)
        else:
            return (np.zeros(frame_count).astype(np.float32).tobytes(), pyaudio.paContinue)

        
    def on_move(self, x, y):
        self.mouse_x = x
        self.mouse_y = y