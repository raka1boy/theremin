import numpy as np

class MusicUtils:
    @staticmethod
    def snap_frequency(freq):
        """Snap frequency to nearest note in 24-TET scale"""
        if freq <= 0:
            return freq
        A4 = 440.0
        C0 = A4 * (2 ** (-4.75))
        quarter_steps = 24 * np.log2(freq / C0)
        key_number = round(quarter_steps)
        return C0 * (2 ** (key_number / 24))

    @staticmethod
    def note_from_freq(frequency):
        """Get note name in 24-TET (including quarter tones)"""
        if frequency <= 0:
            return None
        C0 = 16.35  # C0 frequency
        quarter_steps = 24 * np.log2(frequency / C0)
        key_number = round(quarter_steps)
        
        # Base note names
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        
        # Determine if it's a quarter tone (halfway between two standard notes)
        mod = key_number % 24
        if mod % 2 == 1:  # It's a quarter tone
            base_note = notes[(key_number // 2) % 12]
            if mod % 2 == 1:
                return (f"{base_note}↑", key_number // 24)  # Upward quarter tone
        else:  # Standard semitone
            return (notes[(key_number // 2) % 12], key_number // 24)

    @staticmethod
    def snap_to_c(freq):
        return 16.35 * (2 ** round(np.log2(freq / 16.35))) if freq > 0 else 0
    
    @staticmethod
    def log_scale(value, min_val, max_val):
        """Convert a linear 0-1 value to logarithmic scale between min and max"""
        min_log = np.log10(min_val)
        max_log = np.log10(max_val)
        return 10 ** (min_log + value * (max_log - min_log))

    @staticmethod
    def inv_log_scale(value, min_val, max_val):
        """Convert a logarithmic value to linear 0-1 scale"""
        min_log = np.log10(min_val)
        max_log = np.log10(max_val)
        return (np.log10(value) - min_log) / (max_log - min_log)