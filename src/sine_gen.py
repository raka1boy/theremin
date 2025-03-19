import numpy as np
import pyaudio
import keyboard
from pynput import mouse

SCREEN_X, SCREEN_Y = 1920, 1080  # Adjust to your screen resolution

class SineGen:
    def __init__(
        self,
        sample_rate=44100,
        min_freq=20,
        max_freq=20000,
        chunk_size=1024,
        harmonics=[1],  # Default: base frequency only
    ):
        self.sample_rate = sample_rate
        self.mouse_x = 0
        self.mouse_y = 0
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.chunk_size = chunk_size
        self.harmonics = harmonics  # List of multipliers (e.g., [1, 2, 3])
        self.phases = {h: 0.0 for h in self.harmonics}  # Track phases per harmonic

    def generate_sine_wave_chunk(self, frequency, amplitude, num_samples, phase):
        t = np.arange(num_samples) / self.sample_rate
        chunk = amplitude * np.sin(2 * np.pi * frequency * t + phase).astype(np.float32)
        new_phase = (phase + 2 * np.pi * frequency * num_samples / self.sample_rate) % (2 * np.pi)
        return chunk, new_phase

    def audio_callback(self, in_data, frame_count, time_info, status):
        _ = in_data, time_info, status
        if keyboard.is_pressed("space"):
            base_freq = (self.mouse_x / SCREEN_X) * self.max_freq
            amplitude = (self.mouse_y / SCREEN_Y) / 2 # Y-axis controls amplitude (0-1)
            print(note_from_freq(base_freq), base_freq)
            combined_wave = np.zeros(frame_count, dtype=np.float32)

            # Distribute amplitude across harmonics to prevent clipping
            num_harmonics = len(self.harmonics) if self.harmonics else 1
            amplitude_per_harmonic = amplitude / num_harmonics

            # Generate each harmonic
            for harmonic in self.harmonics:
                freq = base_freq * harmonic
                phase = self.phases[harmonic]
                chunk, new_phase = self.generate_sine_wave_chunk(
                    freq, amplitude_per_harmonic, frame_count, phase
                )
                combined_wave += chunk
                self.phases[harmonic] = new_phase

            # Remove normalization to preserve amplitude control
            return (combined_wave.tobytes(), pyaudio.paContinue)
        else:
            return (np.zeros(frame_count).astype(np.float32).tobytes(), pyaudio.paContinue)

    def on_move(self, x, y):
        self.mouse_x = x
        self.mouse_y = y
def note_from_freq(frequency):
    if(frequency <= 0):
        return None, None
    A4 = 440.0
    C0 = A4 * (2 ** (-4.75))
    half_steps = 12 * np.log2(frequency / C0)
    key_number = round(half_steps)
    note = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][key_number % 12]
    return note, (key_number // 12 ) 