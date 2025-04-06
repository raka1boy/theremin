import numpy as np
import pyaudio
import keyboard
import time
from utils import MusicUtils

class Harmonic:
    def __init__(self, multiplier, initial_amp=1.0, amp_smoothing=100, pitch_smoothing=50, trigger_key="space"):
        self.multiplier = float(multiplier)
        self.initial_amp = float(initial_amp)
        self.amp_smoothing = float(amp_smoothing)
        self.pitch_smoothing = float(pitch_smoothing)
        self.trigger_key = trigger_key
        self.phase = 0.0
        self.snap_enabled = False
        self.current_amp = 0.0
        self.target_amp = 0.0
        self.target_freq = 0.0
        self.current_freq = 0.0
        self.group = None

class Group:
    def __init__(self, name, trigger_key, harmonics=None):
        self.name = name
        self.trigger_key = trigger_key
        self.harmonics = harmonics or []

class SineGen:
    def __init__(self, sample_rate=44100, max_freq=3000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.max_freq = max_freq
        self.min_freq = 1
        self.chunk_size = chunk_size
        self.mouse_x = 1920 // 2
        self.mouse_y = 1080 // 2
        self.harmonics = []
        self.groups = {}
        self.group_assignments = {}
        self.master_amp = 0.5
        self.global_amp_smoothing = 100
        self.global_pitch_smoothing = 50
        self.last_key_check = time.time()
        self.key_check_interval = 0.02
        self.screen_x = 1920
        self.screen_y = 1080

    def _get_harmonic_index(self, multiplier):
        for i, h in enumerate(self.harmonics):
            if h.multiplier == multiplier:
                return i
        return -1

    def add_harmonic(self, multiplier, initial_amp=1.0, amp_smoothing=100, pitch_smoothing=50, trigger_key="space"):
        if self._get_harmonic_index(multiplier) == -1:
            self.harmonics.append(Harmonic(multiplier, initial_amp, amp_smoothing, pitch_smoothing, trigger_key))

    def remove_harmonic(self, multiplier):
        idx = self._get_harmonic_index(multiplier)
        if idx != -1:
            self.remove_from_group(multiplier)
            del self.harmonics[idx]

    def update_harmonic_multiplier(self, old_mult, new_mult):
        old_idx = self._get_harmonic_index(old_mult)
        if old_idx == -1 or self._get_harmonic_index(new_mult) != -1:
            return False
        
        # Create new harmonic with same settings
        old_harmonic = self.harmonics[old_idx]
        group = old_harmonic.group
        self.remove_harmonic(old_mult)
        
        self.add_harmonic(
            multiplier=new_mult,
            initial_amp=old_harmonic.initial_amp,
            amp_smoothing=old_harmonic.amp_smoothing,
            pitch_smoothing=old_harmonic.pitch_smoothing,
            trigger_key=old_harmonic.trigger_key
        )
        
        new_idx = self._get_harmonic_index(new_mult)
        new_harmonic = self.harmonics[new_idx]
        new_harmonic.snap_enabled = old_harmonic.snap_enabled
        new_harmonic.current_amp = old_harmonic.current_amp
        new_harmonic.target_amp = old_harmonic.target_amp
        new_harmonic.target_freq = old_harmonic.target_freq
        new_harmonic.current_freq = old_harmonic.current_freq
        
        if group:
            self.assign_to_group(new_mult, group)
        
        return True

    # Group management methods
    def create_group(self, group_name, trigger_key, harmonics=None):
        if group_name in self.groups:
            raise ValueError(f"Group '{group_name}' already exists")
        
        self.groups[group_name] = Group(group_name, trigger_key, harmonics)
        
        for mult in harmonics or []:
            if self._get_harmonic_index(mult) != -1:
                self.group_assignments[mult] = group_name

    def assign_to_group(self, multiplier, group_name):
        if group_name not in self.groups:
            raise ValueError(f"Group '{group_name}' doesn't exist")
        if self._get_harmonic_index(multiplier) == -1:
            raise ValueError(f"Harmonic {multiplier}x not found")
        
        self.remove_from_group(multiplier)
        self.groups[group_name].harmonics.append(multiplier)
        self.group_assignments[multiplier] = group_name
        self.harmonics[self._get_harmonic_index(multiplier)].group = group_name

    def remove_from_group(self, multiplier):
        if multiplier in self.group_assignments:
            group_name = self.group_assignments[multiplier]
            if group_name in self.groups and multiplier in self.groups[group_name].harmonics:
                self.groups[group_name].harmonics.remove(multiplier)
            del self.group_assignments[multiplier]
            idx = self._get_harmonic_index(multiplier)
            if idx != -1:
                self.harmonics[idx].group = None

    def remove_group(self, group_name):
        if group_name not in self.groups:
            raise ValueError(f"Group '{group_name}' doesn't exist")
        
        for mult in self.groups[group_name].harmonics[:]:
            self.remove_from_group(mult)
        
        del self.groups[group_name]

    def set_group_key(self, group_name, trigger_key):
        if group_name not in self.groups:
            raise ValueError(f"Group '{group_name}' doesn't exist")
        self.groups[group_name].trigger_key = trigger_key

    def get_group_for_harmonic(self, multiplier):
        return self.group_assignments.get(multiplier)

    def audio_callback(self, in_data, frame_count, time_info, status):
        # Convert mouse X position to logarithmic frequency scale
        if self.min_freq <= 0 or self.max_freq <= self.min_freq:
            current_freq = self.min_freq
        else:
            ratio = self.mouse_x / self.screen_x
            current_freq = self.min_freq * (self.max_freq / self.min_freq) ** ratio

        current_amp = (self.mouse_y / self.screen_y) / 2

        now = time.time()
        if now - self.last_key_check >= self.key_check_interval:
            self._update_triggered_harmonics(current_freq)
            self.last_key_check = now

        combined_wave = np.zeros(frame_count, dtype=np.float32)
        if self.harmonics:
            total_amps = sum(h.initial_amp for h in self.harmonics) or 1
            t = np.arange(frame_count) / self.sample_rate

            for harmonic in self.harmonics:
                freq, envelope = self._process_harmonic(harmonic, frame_count)
                phase = harmonic.phase
                amp = current_amp * (harmonic.initial_amp / total_amps) * envelope
                sine_wave = amp * np.sin(2 * np.pi * freq * t + phase)
                combined_wave += sine_wave
                harmonic.phase = (phase + 2 * np.pi * freq * frame_count / self.sample_rate) % (2 * np.pi)

        return (combined_wave.tobytes(), pyaudio.paContinue)

    def _update_triggered_harmonics(self, current_freq):
        triggered_harmonics = set()

        # First check group keys
        for group in self.groups.values():
            if keyboard.is_pressed(group.trigger_key):
                for mult in group.harmonics:
                    idx = self._get_harmonic_index(mult)
                    if idx != -1:
                        harmonic = self.harmonics[idx]
                        harmonic.target_amp = 1.0
                        raw_freq = current_freq * harmonic.multiplier
                        harmonic.target_freq = MusicUtils.snap_frequency(raw_freq) if harmonic.snap_enabled else raw_freq
                        if harmonic.pitch_smoothing <= 0:
                            harmonic.current_freq = harmonic.target_freq
                        triggered_harmonics.add(idx)

        # Then check individual harmonic keys
        for i, harmonic in enumerate(self.harmonics):
            if (harmonic.trigger_key and keyboard.is_pressed(harmonic.trigger_key) 
                    and not harmonic.group):
                harmonic.target_amp = 1.0
                raw_freq = current_freq * harmonic.multiplier
                harmonic.target_freq = MusicUtils.snap_frequency(raw_freq) if harmonic.snap_enabled else raw_freq
                if harmonic.pitch_smoothing <= 0:
                    harmonic.current_freq = harmonic.target_freq
                triggered_harmonics.add(i)

        # Turn off harmonics that aren't being triggered
        for i, harmonic in enumerate(self.harmonics):
            if i not in triggered_harmonics:
                harmonic.target_amp = 0.0

    def _process_harmonic(self, harmonic, frame_count):
        # Handle frequency smoothing
        pitch_smoothing = harmonic.pitch_smoothing if harmonic.pitch_smoothing > 0 else self.global_pitch_smoothing
        if pitch_smoothing > 0:
            freq_tau = pitch_smoothing / 1000
            freq_decay = np.exp(-1 / (freq_tau * self.sample_rate))
            harmonic.current_freq = (harmonic.current_freq * freq_decay + 
                                    harmonic.target_freq * (1 - freq_decay))
        else:
            harmonic.current_freq = harmonic.target_freq
        
        freq = harmonic.current_freq
        
        # Handle amplitude smoothing
        amp_smoothing = harmonic.amp_smoothing if harmonic.amp_smoothing > 0 else self.global_amp_smoothing
        if amp_smoothing > 0:
            amp_tau = amp_smoothing / 1000
            amp_decay = np.exp(-1 / (amp_tau * self.sample_rate))
            steps = np.arange(frame_count)
            envelope = (harmonic.current_amp * (amp_decay ** steps) + 
                       harmonic.target_amp * (1 - amp_decay ** steps))
            harmonic.current_amp = envelope[-1]
        else:
            envelope = np.full(frame_count, harmonic.target_amp, dtype=np.float32)
            harmonic.current_amp = harmonic.target_amp
        
        return freq, envelope