# sine_gen.py
import numpy as np
import pyaudio
import keyboard

class SineGen:
    def __init__(self, sample_rate=44100, max_freq=3000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.max_freq = max_freq
        self.min_freq = 1
        self.chunk_size = chunk_size
        self.mouse_x = 1920 // 2
        self.mouse_y = 1080 // 2
        self.harmonics = []     # List of harmonic multipliers
        self.phases = []        # Parallel list of phase values
        self.harmonic_amps = [] # Relative amplitudes for each harmonic (0.0-1.0)
        self.master_amp = 0.5
        self.smoothing_time = 100  # ms
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
                self.harmonic_amps.append(float(initial_amp))  # Default to full amplitude
        except ValueError:
            pass

    def remove_harmonic(self, multiplier):
        if multiplier in self.harmonics:
            idx = self.harmonics.index(multiplier)
            del self.harmonics[idx]
            del self.phases[idx]
            del self.harmonic_amps[idx]

    def set_harmonic_amp(self, multiplier, amplitude):
        if multiplier in self.harmonics:
            idx = self.harmonics.index(multiplier)
            self.harmonic_amps[idx] = max(0.0, min(1.0, float(amplitude)))

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
            total_amps = sum(self.harmonic_amps) or 1  # Avoid division by zero
            t = np.arange(frame_count) / self.sample_rate

            for i, mult in enumerate(self.harmonics):
                freq = base_freq * mult
                phase = self.phases[i]
                # Apply individual harmonic amplitude
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
# import numpy as np
# import pyaudio
# import keyboard

# class SineGen:
#     def __init__(self, sample_rate=44100, max_freq=3000, chunk_size=1024):
#         self.sample_rate = sample_rate
#         self.max_freq = max_freq
#         self.min_freq = 1
#         self.chunk_size = chunk_size
#         self.mouse_x = 1920 // 2  # Default screen resolution
#         self.mouse_y = 1080 // 2
#         self.harmonics = []     # List of harmonic multipliers
#         self.phases = []        # Parallel list of phase values
#         self.master_amp = 0.5
#         self.smoothing_time = 100  # ms
#         self.current_amp = 0.0
#         self.target_amp = 0.0
#         self.frozen_freq = 0.0
#         self.frozen_amp = 0.0
#         self.is_frozen = False

#     def add_harmonic(self, multiplier):
#         try:
#             mult = float(multiplier)
#             if mult not in self.harmonics:
#                 self.harmonics.append(mult)
#                 self.phases.append(0.0)  # Initialize phase for this harmonic
#         except ValueError:
#             pass

#     def remove_harmonic(self, multiplier):
#         if multiplier in self.harmonics:
#             idx = self.harmonics.index(multiplier)
#             del self.harmonics[idx]
#             del self.phases[idx]

#     def audio_callback(self, in_data, frame_count, time_info, status):
#         # Get current parameters
#         current_freq = (self.mouse_x / 1920) * (self.max_freq - self.min_freq) + self.min_freq
#         current_amp = (self.mouse_y / 1080) / 2

#         # Update state based on space key
#         if keyboard.is_pressed("space"):
#             self.target_amp = 1.0
#             self.frozen_freq = current_freq
#             self.frozen_amp = current_amp
#             self.is_frozen = False
#         else:
#             self.target_amp = 0.0
#             if not self.is_frozen:
#                 self.is_frozen = True

#         # Use frozen parameters if needed
#         base_freq = self.frozen_freq if self.is_frozen else current_freq
#         amplitude = self.frozen_amp if self.is_frozen else current_amp

#         # Generate harmonics
#         combined_wave = np.zeros(frame_count, dtype=np.float32)
#         if self.harmonics:
#             num_harmonics = len(self.harmonics)
#             amp_per = amplitude / num_harmonics
#             t = np.arange(frame_count) / self.sample_rate  # Time array for this chunk

#             for i, mult in enumerate(self.harmonics):
#                 freq = base_freq * mult
#                 phase = self.phases[i]
#                 # Generate sine wave for this harmonic
#                 sine_wave = amp_per * np.sin(2 * np.pi * freq * t + phase)
#                 combined_wave += sine_wave
#                 # Update phase for the next chunk
#                 self.phases[i] = (phase + 2 * np.pi * freq * frame_count / self.sample_rate) % (2 * np.pi)

#         # Apply amplitude envelope
#         if self.smoothing_time > 0:
#             tau = self.smoothing_time / 1000  # Convert ms to seconds
#             decay = np.exp(-1 / (tau * self.sample_rate)) if tau > 0 else 0
#             steps = np.arange(frame_count)
#             envelope = self.current_amp * (decay ** steps) + self.target_amp * (1 - decay ** steps)
#             self.current_amp = envelope[-1]  # Store the last envelope value for the next chunk
#         else:
#             envelope = np.full(frame_count, self.target_amp, dtype=np.float32)
#             self.current_amp = self.target_amp

#         combined_wave *= envelope.astype(np.float32)
#         return (combined_wave.tobytes(), pyaudio.paContinue)