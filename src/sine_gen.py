import numpy as np
import pyaudio
import keyboard
from pynput import mouse
import tkinter as tk
from tkinter import ttk

SCREEN_X, SCREEN_Y = 1920, 1080  # Adjust to your screen resolution

class SineGen:
    def __init__(self, sample_rate=44100, max_freq=3000, chunk_size=16):
        self.sample_rate = sample_rate
        self.max_freq = max_freq
        self.min_freq = 1
        self.chunk_size = chunk_size
        self.mouse_x = SCREEN_X // 2
        self.mouse_y = SCREEN_Y // 2
        self.harmonics = []
        self.phases = {}
        self.master_amp = 0.5
        self.smoothing_time = 100  # ms
        self.current_amp = 0.0
        self.target_amp = 0.0
        self.frozen_freq = 0.0  # Store frequency when releasing space
        self.frozen_amp = 0.0   # Store amplitude when releasing space
        self.is_frozen = False  # Track if we're in release phase

    def add_harmonic(self, multiplier):
        try:
            multiplier = float(multiplier)
            if multiplier not in self.harmonics:
                self.harmonics.append(multiplier)
                self.phases[multiplier] = 0.0
        except ValueError:
            pass  # Ignore invalid input

    def remove_harmonic(self, multiplier):
        if multiplier in self.harmonics:
            self.harmonics.remove(multiplier)
            del self.phases[multiplier]

    def generate_sine_wave_chunk(self, frequency, amplitude, num_samples, phase):
        t = np.arange(num_samples) / self.sample_rate
        chunk = amplitude * np.sin(2 * np.pi * frequency * t + phase).astype(np.float32)
        new_phase = (phase + 2 * np.pi * frequency * num_samples / self.sample_rate) % (2 * np.pi)
        return chunk, new_phase

    def audio_callback(self, in_data, frame_count, time_info, status):
        # Store current mouse position values
        current_freq = (self.mouse_x / SCREEN_X) * (self.max_freq - self.min_freq) + self.min_freq
        current_amp = (self.mouse_y / SCREEN_Y) / 2
        
        # Update target amplitude and capture parameters
        if keyboard.is_pressed("space"):
            self.target_amp = 1.0
            self.frozen_freq = current_freq
            self.frozen_amp = current_amp
            self.is_frozen = False
        else:
            self.target_amp = 0.0
            if not self.is_frozen:
                # Capture values only once when first releasing space
                self.is_frozen = True

        # Generate audio using frozen parameters if in release phase
        if self.is_frozen:
            base_freq = self.frozen_freq
            amplitude = self.frozen_amp
        else:
            base_freq = current_freq
            amplitude = current_amp

        combined_wave = np.zeros(frame_count, dtype=np.float32)
        
        if self.harmonics:
            amp_per_harmonic = amplitude / len(self.harmonics)
            for harmonic in self.harmonics:
                freq = base_freq * harmonic
                phase = self.phases[harmonic]
                chunk, new_phase = self.generate_sine_wave_chunk(freq, amp_per_harmonic, frame_count, phase)
                combined_wave += chunk
                self.phases[harmonic] = new_phase

        # Apply smoothing envelope
        if self.smoothing_time > 0:
            tau = self.smoothing_time / 1000  # Convert ms to seconds
            decay = np.exp(-1/(tau * self.sample_rate)) if tau > 0 else 0
            envelope = np.zeros(frame_count)
            
            for i in range(frame_count):
                self.current_amp = self.current_amp * decay + self.target_amp * (1 - decay)
                envelope[i] = self.current_amp
            
            combined_wave *= envelope.astype(np.float32)
        else:
            combined_wave *= self.target_amp

        return (combined_wave.tobytes(), pyaudio.paContinue)

    def on_move(self, x, y):
        self.mouse_x = x
        self.mouse_y = y
        
def note_from_freq(frequency):
    if frequency <= 0:
        return None, None
    A4 = 440.0
    C0 = A4 * (2 ** (-4.75))
    half_steps = 12 * np.log2(frequency / C0)
    key_number = round(half_steps)
    note = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][key_number % 12]
    return note, (key_number // 12)