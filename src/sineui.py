# sineui.py
import numpy as np
import pyaudio
import keyboard
from pynput import mouse
import tkinter as tk
from tkinter import ttk

SCREEN_X, SCREEN_Y = 1920, 1080

def snap_frequency(freq):
    """Snap frequency to nearest note in 12-TET scale"""
    if freq <= 0:
        return freq
    A4 = 440.0
    C0 = A4 * (2 ** (-4.75))
    half_steps = 12 * np.log2(freq / C0)
    key_number = round(half_steps)
    return C0 * (2 ** (key_number / 12))

def note_from_freq(frequency):
    if frequency <= 0:
        return None
    A4 = 440.0
    C0 = A4 * (2 ** (-4.75))
    half_steps = 12 * np.log2(frequency / C0)
    key_number = round(half_steps)
    note = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][key_number % 12]
    octave = key_number // 12
    return (note, octave)

class HarmonicControl(ttk.Frame):
    def __init__(self, parent, generator, multiplier, on_remove=None):
        super().__init__(parent)
        self.generator = generator
        self.multiplier = multiplier
        self.on_remove = on_remove
        self.snap_to_note = tk.BooleanVar(value=False)
        
        ttk.Label(self, text=f"{multiplier}x").grid(row=0, column=0, padx=5)
        
        self.amp_slider = ttk.Scale(
            self, from_=0, to=1, value=1.0,
            command=lambda v: [self.generator.set_harmonic_amp(self.multiplier, float(v)),
                               self.update_display()]
        )
        self.amp_slider.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.note_var = tk.StringVar()
        ttk.Label(self, textvariable=self.note_var, width=10).grid(row=0, column=2, padx=5)
        
        self.freq_var = tk.StringVar()
        ttk.Label(self, textvariable=self.freq_var, width=10).grid(row=0, column=3, padx=5)
        
        self.snap_cb = ttk.Checkbutton(
            self, text="Snap", variable=self.snap_to_note,
            command=lambda: [self.generator.set_harmonic_snap(self.multiplier, self.snap_to_note.get()),
                             self.update_display()]
        )
        self.snap_cb.grid(row=0, column=4, padx=5)
        
        ttk.Button(self, text="×", width=2, command=self.remove_harmonic).grid(row=0, column=5, padx=5)
        self.columnconfigure(1, weight=1)

    def remove_harmonic(self):
        self.generator.remove_harmonic(self.multiplier)
        if self.on_remove:
            self.on_remove(self.multiplier)

    def update_display(self):
        if hasattr(self.generator, 'mouse_x'):
            base_freq = (self.generator.mouse_x / 1920) * (self.generator.max_freq - self.generator.min_freq) + self.generator.min_freq
            raw_freq = base_freq * self.multiplier
            display_freq = snap_frequency(raw_freq) if self.snap_to_note.get() else raw_freq
            
            note_info = note_from_freq(display_freq)
            self.note_var.set(f"{note_info[0]}{note_info[1]}" if note_info else "")
            self.freq_var.set(f"{display_freq:.1f} Hz")
class ControlUI(tk.Tk):
    def __init__(self, generator):
        super().__init__()
        self.generator = generator
        self.title("Терменбокс")
        self.geometry("700x600")
        
        self.setup_ui()
        self.setup_audio()
        self.setup_updater()

    def setup_updater(self):
        def update_all():
            for child in self.inner_harmonics_frame.winfo_children():
                if isinstance(child, HarmonicControl):
                    child.update_display()
            self.after(100, update_all)
        update_all()

    def setup_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top section - harmonic controls
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(top_frame, text="умножатель").pack(side=tk.LEFT)
        self.harmonic_entry = ttk.Entry(top_frame)
        self.harmonic_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.harmonic_entry.bind('<Return>', lambda event: self.add_harmonic())
        
        ttk.Button(
            top_frame, 
            text="+", 
            command=self.add_harmonic
        ).pack(side=tk.LEFT)
        
        # Middle section - harmonics list
        mid_frame = ttk.Frame(main_frame)
        mid_frame.pack(fill=tk.BOTH, expand=True)
        
        harmonics_container = ttk.LabelFrame(mid_frame, text="Гармоники", height=200)
        harmonics_container.pack(fill=tk.BOTH, expand=True)
        harmonics_container.pack_propagate(False)
        
        # Add column headers
        header_frame = ttk.Frame(harmonics_container)
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text="Multiplier", width=10).grid(row=0, column=0)
        ttk.Label(header_frame, text="Amplitude", width=15).grid(row=0, column=1)
        ttk.Label(header_frame, text="Note", width=10).grid(row=0, column=2)
        ttk.Label(header_frame, text="Frequency", width=10).grid(row=0, column=3)
        ttk.Label(header_frame, text="Snap", width=10).grid(row=0, column=4)
        
        # Scrollable area for harmonics
        canvas_frame = ttk.Frame(harmonics_container)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.harmonics_canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.harmonics_canvas.yview)
        self.harmonics_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.harmonics_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.inner_harmonics_frame = ttk.Frame(self.harmonics_canvas)
        self.harmonics_canvas.create_window((0, 0), window=self.inner_harmonics_frame, anchor="nw")
        
        self.inner_harmonics_frame.bind(
            "<Configure>",
            lambda e: self.harmonics_canvas.configure(
                scrollregion=self.harmonics_canvas.bbox("all")
            )
        )
        
        # Bottom section - global controls
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=5)
        
        # Smoothing control
        smoothing_frame = ttk.Frame(bottom_frame)
        smoothing_frame.pack(fill=tk.X, pady=5)
        ttk.Label(smoothing_frame, text="Smoothing (ms):").pack(side=tk.LEFT)
        self.smoothing_slider = ttk.Scale(
            smoothing_frame,
            from_=0,
            to=1000,
            command=lambda v: setattr(self.generator, 'smoothing_time', float(v))
        )
        self.smoothing_slider.set(100)
        self.smoothing_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Min frequency control
        min_freq_frame = ttk.Frame(bottom_frame)
        min_freq_frame.pack(fill=tk.X, pady=5)
        ttk.Label(min_freq_frame, text="Min Frequency:").pack(side=tk.LEFT)
        self.min_freq_slider = ttk.Scale(
            min_freq_frame,
            from_=1,
            to=10000,
            command=lambda v: setattr(self.generator, 'min_freq', float(v))
        )
        self.min_freq_slider.set(10)
        self.min_freq_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Max frequency control
        max_freq_frame = ttk.Frame(bottom_frame)
        max_freq_frame.pack(fill=tk.X, pady=5)
        ttk.Label(max_freq_frame, text="Max Frequency:").pack(side=tk.LEFT)
        self.max_freq_slider = ttk.Scale(
            max_freq_frame,
            from_=1,
            to=10000,
            command=lambda v: setattr(self.generator, 'max_freq', float(v))
        )
        self.max_freq_slider.set(1500)
        self.max_freq_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    def add_harmonic(self):
        try:
            mult = float(self.harmonic_entry.get())
            if mult not in self.generator.harmonics:
                self.generator.add_harmonic(mult)
                self.add_harmonic_control(mult)
                self.harmonic_entry.delete(0, tk.END)
        except ValueError:
            pass

    def add_harmonic_control(self, multiplier):
        """Add a new harmonic control widget"""
        def remove_callback(mult):
            for child in self.inner_harmonics_frame.winfo_children():
                if hasattr(child, 'multiplier') and child.multiplier == mult:
                    child.destroy()
        
        control = HarmonicControl(
            self.inner_harmonics_frame,
            self.generator,
            multiplier,
            on_remove=remove_callback
        )
        control.pack(fill=tk.X, pady=2)
        control.update_display()
        self.harmonics_canvas.configure(scrollregion=self.harmonics_canvas.bbox("all"))

    def setup_note_updater(self):
        """Set up periodic updates for note displays"""
        def update_notes():
            for child in self.inner_harmonics_frame.winfo_children():
                if hasattr(child, 'update_display'):
                    child.update_display()
            self.after(100, update_notes)
        
        update_notes()

    def setup_audio(self):
        def on_move(x, y):
            self.generator.mouse_x = x
            self.generator.mouse_y = y
            self.note = str(note_from_freq(x))

        self.mouse_listener = mouse.Listener(on_move=on_move)
        self.mouse_listener.start()
        
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=self.generator.sample_rate,
            output=True,
            frames_per_buffer=self.generator.chunk_size,
            stream_callback=self.generator.audio_callback
        )
        self.stream.start_stream()

    def on_closing(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
        self.mouse_listener.stop()
        self.destroy()

def note_from_freq(frequency):
    if frequency <= 0:
        return None
    A4 = 440.0
    C0 = A4 * (2 ** (-4.75))
    half_steps = 12 * np.log2(frequency / C0)
    key_number = round(half_steps)
    note = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][key_number % 12]
    octave = key_number // 12
    return (note, octave)