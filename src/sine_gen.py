import numpy as np
import pyaudio
import keyboard
import time

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
        self.harmonics = []
        self.phases = []
        self.harmonic_amps = []
        self.snap_enabled = []
        self.harmonic_amp_smoothing = []  # Amplitude smoothing (ms)
        self.harmonic_pitch_smoothing = []  # Pitch smoothing (ms)
        self.harmonic_keys = []
        self.master_amp = 0.5
        self.global_amp_smoothing = 100  # Global amplitude smoothing
        self.global_pitch_smoothing = 100  # Global pitch smoothing
        self.current_amps = []
        self.target_amps = []
        self.last_key_check = time.time()
        self.key_check_interval = 0.02
        self.target_freqs = []
        self.current_freqs = []

    def add_harmonic(self, multiplier, initial_amp=1.0, amp_smoothing=100, pitch_smoothing=100, trigger_key=None):
        try:
            mult = float(multiplier)
            if mult not in self.harmonics:
                self.harmonics.append(mult)
                self.phases.append(0.0)
                self.harmonic_amps.append(float(initial_amp))
                self.snap_enabled.append(False)
                self.harmonic_amp_smoothing.append(float(amp_smoothing))
                self.harmonic_pitch_smoothing.append(float(pitch_smoothing))
                self.harmonic_keys.append(trigger_key)
                self.current_amps.append(0.0)
                self.target_amps.append(0.0)
                self.target_freqs.append(0.0)
                self.current_freqs.append(0.0)
        except ValueError:
            pass

    def remove_harmonic(self, multiplier):
        if multiplier in self.harmonics:
            idx = self.harmonics.index(multiplier)
            del self.harmonics[idx]
            del self.phases[idx]
            del self.harmonic_amps[idx]
            del self.snap_enabled[idx]
            del self.harmonic_amp_smoothing[idx]
            del self.harmonic_pitch_smoothing[idx]
            del self.harmonic_keys[idx]
            del self.current_amps[idx]
            del self.target_amps[idx]
            del self.target_freqs[idx]
            del self.current_freqs[idx]

    def set_harmonic_amp(self, multiplier, amplitude):
        if multiplier in self.harmonics:
            idx = self.harmonics.index(multiplier)
            self.harmonic_amps[idx] = max(0.0, min(1.0, float(amplitude)))

    def set_harmonic_snap(self, multiplier, snap_enabled):
        if multiplier in self.harmonics:
            idx = self.harmonics.index(multiplier)
            self.snap_enabled[idx] = bool(snap_enabled)

    def set_harmonic_amp_smoothing(self, multiplier, smoothing):
        if multiplier in self.harmonics:
            idx = self.harmonics.index(multiplier)
            self.harmonic_amp_smoothing[idx] = max(0.0, float(smoothing))

    def set_harmonic_pitch_smoothing(self, multiplier, smoothing):
        if multiplier in self.harmonics:
            idx = self.harmonics.index(multiplier)
            self.harmonic_pitch_smoothing[idx] = max(0.0, float(smoothing))

    def set_harmonic_key(self, multiplier, trigger_key):
        if multiplier in self.harmonics:
            idx = self.harmonics.index(multiplier)
            self.harmonic_keys[idx] = trigger_key

    def audio_callback(self, in_data, frame_count, time_info, status):
        current_freq = (self.mouse_x / 1920) * (self.max_freq - self.min_freq) + self.min_freq
        current_amp = (self.mouse_y / 1080) / 2

        now = time.time()
        if now - self.last_key_check >= self.key_check_interval:
            for i, key in enumerate(self.harmonic_keys):
                if key and keyboard.is_pressed(key):
                    self.target_amps[i] = 1.0
                    raw_freq = current_freq * self.harmonics[i]
                    self.target_freqs[i] = snap_frequency(raw_freq) if self.snap_enabled[i] else raw_freq
                    # Immediate frequency when pitch smoothing is 0
                    if self.harmonic_pitch_smoothing[i] <= 0:
                        self.current_freqs[i] = self.target_freqs[i]
                else:
                    self.target_amps[i] = 0.0
            self.last_key_check = now

        combined_wave = np.zeros(frame_count, dtype=np.float32)
        if self.harmonics:
            total_amps = sum(self.harmonic_amps) or 1
            t = np.arange(frame_count) / self.sample_rate

            for i, mult in enumerate(self.harmonics):
                # Handle frequency smoothing
                pitch_smoothing = self.harmonic_pitch_smoothing[i] if self.harmonic_pitch_smoothing[i] > 0 else self.global_pitch_smoothing
                if pitch_smoothing > 0:
                    freq_tau = pitch_smoothing / 1000
                    freq_decay = np.exp(-1 / (freq_tau * self.sample_rate))
                    self.current_freqs[i] = self.current_freqs[i] * freq_decay + self.target_freqs[i] * (1 - freq_decay)
                else:
                    self.current_freqs[i] = self.target_freqs[i]
                
                freq = self.current_freqs[i]
                
                # Handle amplitude smoothing
                amp_smoothing = self.harmonic_amp_smoothing[i] if self.harmonic_amp_smoothing[i] > 0 else self.global_amp_smoothing
                if amp_smoothing > 0:
                    amp_tau = amp_smoothing / 1000
                    amp_decay = np.exp(-1 / (amp_tau * self.sample_rate))
                    steps = np.arange(frame_count)
                    envelope = self.current_amps[i] * (amp_decay ** steps) + self.target_amps[i] * (1 - amp_decay ** steps)
                    self.current_amps[i] = envelope[-1]
                else:
                    envelope = np.full(frame_count, self.target_amps[i], dtype=np.float32)
                    self.current_amps[i] = self.target_amps[i]
                
                # Generate waveform
                phase = self.phases[i]
                amp = current_amp * (self.harmonic_amps[i] / total_amps) * envelope
                sine_wave = amp * np.sin(2 * np.pi * freq * t + phase)
                combined_wave += sine_wave
                self.phases[i] = (phase + 2 * np.pi * freq * frame_count / self.sample_rate) % (2 * np.pi)

        return (combined_wave.tobytes(), pyaudio.paContinue)