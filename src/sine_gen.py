# sine_gen.py
import numpy as np
import pyaudio
import keyboard

def snap_frequency(freq):
    """Snap frequency to nearest note in 12-TET scale"""
    if freq <= 0:
        return freq
    A4 = 440.0
    C0 = A4 * (2 ** (-4.75))
    half_steps = 12 * np.log2(freq / C0)
    key_number = round(half_steps)
    return C0 * (2 ** (key_number / 12))

class SineGen:
    def __init__(self, sample_rate=44100, max_freq=3000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.max_freq = max_freq
        self.min_freq = 1
        self.chunk_size = chunk_size
        self.mouse_x = 1920 // 2
        self.mouse_y = 1080 // 2
        self.harmonics = []     # List of harmonic multipliers
        self.phases = []        # Phase values for each harmonic
        self.harmonic_amps = [] # Amplitude for each harmonic
        self.snap_enabled = [] # Whether to snap frequency for each harmonic
        self.master_amp = 0.5
        self.smoothing_time = 100
        self.current_amp = 0.0
        self.target_amp = 0.0
        self.frozen_freq = 0.0
        self.frozen_amp = 0.0
        self.is_frozen = False

    def add_harmonic(self, multiplier, initial_amp=1.0):
        try:
            mult = float(multiplier)
            if mult not in self.harmonics:
                self.harmonics.append(mult)
                self.phases.append(0.0)
                self.harmonic_amps.append(float(initial_amp))
                self.snap_enabled.append(False)
        except ValueError:
            pass

    def remove_harmonic(self, multiplier):
        if multiplier in self.harmonics:
            idx = self.harmonics.index(multiplier)
            del self.harmonics[idx]
            del self.phases[idx]
            del self.harmonic_amps[idx]
            del self.snap_enabled[idx]

    def set_harmonic_amp(self, multiplier, amplitude):
        if multiplier in self.harmonics:
            idx = self.harmonics.index(multiplier)
            self.harmonic_amps[idx] = max(0.0, min(1.0, float(amplitude)))

    def set_harmonic_snap(self, multiplier, snap_enabled):
        if multiplier in self.harmonics:
            idx = self.harmonics.index(multiplier)
            self.snap_enabled[idx] = bool(snap_enabled)

    def audio_callback(self, in_data, frame_count, time_info, status):
        current_freq = (self.mouse_x / 1920) * (self.max_freq - self.min_freq) + self.min_freq
        current_amp = (self.mouse_y / 1080) / 2

        if keyboard.is_pressed("space"):
            self.target_amp = 1.0
            self.frozen_freq = current_freq
            self.frozen_amp = current_amp
            self.is_frozen = False
        else:
            self.target_amp = 0.0
            if not self.is_frozen:
                self.is_frozen = True

        base_freq = self.frozen_freq if self.is_frozen else current_freq
        amplitude = self.frozen_amp if self.is_frozen else current_amp

        combined_wave = np.zeros(frame_count, dtype=np.float32)
        if self.harmonics:
            total_amps = sum(self.harmonic_amps) or 1
            t = np.arange(frame_count) / self.sample_rate

            for i, mult in enumerate(self.harmonics):
                raw_freq = base_freq * mult
                
                # Apply frequency snapping if enabled
                freq = snap_frequency(raw_freq) if self.snap_enabled[i] else raw_freq
                
                phase = self.phases[i]
                amp = amplitude * (self.harmonic_amps[i] / total_amps)
                sine_wave = amp * np.sin(2 * np.pi * freq * t + phase)
                combined_wave += sine_wave
                self.phases[i] = (phase + 2 * np.pi * freq * frame_count / self.sample_rate) % (2 * np.pi)

        if self.smoothing_time > 0:
            tau = self.smoothing_time / 1000
            decay = np.exp(-1 / (tau * self.sample_rate)) if tau > 0 else 0
            steps = np.arange(frame_count)
            envelope = self.current_amp * (decay ** steps) + self.target_amp * (1 - decay ** steps)
            self.current_amp = envelope[-1]
        else:
            envelope = np.full(frame_count, self.target_amp, dtype=np.float32)
            self.current_amp = self.target_amp

        combined_wave *= envelope.astype(np.float32)
        return (combined_wave.tobytes(), pyaudio.paContinue)